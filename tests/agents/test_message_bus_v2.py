"""Unit tests for MessageBusV2."""

import asyncio
from unittest.mock import MagicMock

import pytest

from openclaw.agents.ira.src.agents.message_bus_v2 import (
    MessageBusV2,
    MessageV2,
    get_message_bus_v2,
    reset_message_bus_v2,
    DEFAULT_QUEUE_MAX_SIZE,
)


@pytest.fixture(autouse=True)
def reset_bus():
    yield
    reset_message_bus_v2()


@pytest.mark.asyncio
async def test_point_to_point_send_listen():
    """Test basic send/listen between agents."""
    bus = MessageBusV2(queue_max_size=10)

    async def receiver():
        bus._listeners.add("agent_b")
        msg = await bus.listen("agent_b")
        return msg

    task = asyncio.create_task(receiver())
    await asyncio.sleep(0.01)  # Let listener start

    sent = await bus.send(
        MessageV2(sender="agent_a", recipient="agent_b", content="hello")
    )
    assert sent is True

    msg = await asyncio.wait_for(task, timeout=1.0)
    assert msg.content == "hello"
    assert msg.sender == "agent_a"


@pytest.mark.asyncio
async def test_request_response_success():
    """Test request/respond correlation."""
    bus = MessageBusV2(queue_max_size=10)
    bus._listeners.add("worker")

    async def worker():
        msg = await bus.listen("worker")
        if msg.correlation_id:
            await bus.respond(msg.correlation_id, f"echo:{msg.content}", "worker")
        return msg

    worker_task = asyncio.create_task(worker())
    await asyncio.sleep(0.01)

    result = await bus.request("worker", "test payload", sender="client", timeout=2.0)
    assert result == "echo:test payload"

    worker_task.cancel()
    try:
        await worker_task
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio
async def test_request_response_timeout():
    """Test request times out when no response."""
    bus = MessageBusV2(queue_max_size=10)
    bus._listeners.add("slow_agent")

    async def slow_agent():
        await bus.listen("slow_agent")
        await asyncio.sleep(10)  # Never responds

    asyncio.create_task(slow_agent())
    await asyncio.sleep(0.01)

    with pytest.raises(asyncio.TimeoutError):
        await bus.request("slow_agent", "hi", sender="client", timeout=0.1)


@pytest.mark.asyncio
async def test_pub_sub():
    """Test topic-based publish/subscribe."""
    bus = MessageBusV2(queue_max_size=10)
    bus.subscribe("sub_a", "news")
    bus.subscribe("sub_b", "news")
    bus._listeners.add("sub_a")
    bus._listeners.add("sub_b")

    received_a = []
    received_b = []

    async def sub_a():
        while True:
            msg = await bus.listen("sub_a")
            received_a.append(msg.content)
            if len(received_a) >= 1:
                break

    async def sub_b():
        while True:
            msg = await bus.listen("sub_b")
            received_b.append(msg.content)
            if len(received_b) >= 1:
                break

    asyncio.create_task(sub_a())
    asyncio.create_task(sub_b())
    await asyncio.sleep(0.01)

    await bus.publish("news", {"headline": "Test"}, sender="publisher")
    await asyncio.sleep(0.2)

    assert len(received_a) == 1
    assert len(received_b) == 1
    assert received_a[0]["payload"]["headline"] == "Test"


@pytest.mark.asyncio
async def test_dead_letter_queue_no_listener():
    """Test message to agent with no listener goes to DLQ."""
    bus = MessageBusV2(queue_max_size=10)
    # "orphan" has no listener

    sent = await bus.send(
        MessageV2(sender="a", recipient="orphan", content="lost")
    )
    assert sent is False
    dlq = bus.get_dlq_messages()
    assert len(dlq) == 1
    assert dlq[0].content == "lost"
    assert dlq[0].metadata.get("dlq_reason") == "no_listener"


@pytest.mark.asyncio
async def test_backpressure_queue_full():
    """Test backpressure when queue exceeds bounded size."""
    bus = MessageBusV2(queue_max_size=2)
    bus._listeners.add("bottleneck")

    # Fill the queue
    for i in range(2):
        await bus.send(MessageV2(sender="a", recipient="bottleneck", content=i))

    # This should fail (queue full)
    sent = await bus.send(
        MessageV2(sender="a", recipient="bottleneck", content="overflow")
    )
    assert sent is False
    dlq = bus.get_dlq_messages()
    assert any(m.content == "overflow" for m in dlq)
    assert any(m.metadata.get("dlq_reason") == "queue_full" for m in dlq)
