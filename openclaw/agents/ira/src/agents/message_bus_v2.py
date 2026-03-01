"""
MessageBusV2 - Enhanced Inter-Agent Communication

Extends the message bus with:
- Request-response correlation with request()/respond() and timeout
- Topic-based pub/sub with publish()/subscribe()
- Dead-letter queue for undeliverable messages
- Bounded queues for backpressure
"""

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Optional

logger = logging.getLogger("ira.message_bus_v2")

# Default queue size for backpressure
DEFAULT_QUEUE_MAX_SIZE = 100


@dataclass
class MessageV2:
    """
    A message between agents (V2 format).
    """

    sender: str
    recipient: str
    content: Any
    message_type: str = "request"
    correlation_id: Optional[str] = None
    timestamp: float = field(default_factory=time.time)
    metadata: dict = field(default_factory=dict)
    reply_to: Optional[str] = None  # For request-response

    def __repr__(self) -> str:
        preview = (
            str(self.content)[:50] + "..."
            if len(str(self.content)) > 50
            else str(self.content)
        )
        return f"MessageV2({self.sender} → {self.recipient}: {preview})"


class MessageBusV2:
    """
    Enhanced message bus with request-response, pub/sub, DLQ, and backpressure.
    """

    def __init__(self, queue_max_size: int = DEFAULT_QUEUE_MAX_SIZE) -> None:
        self._queue_max_size = queue_max_size
        self._queues: dict[str, asyncio.Queue] = {}
        self._pending_requests: dict[str, asyncio.Future] = {}
        self._topic_subscribers: dict[str, list[str]] = {}
        self._dead_letter_queue: list[MessageV2] = []
        self._max_dlq_size = 1000
        self._listeners: set[str] = set()
        logger.info({"event": "message_bus_v2_initialized", "queue_max_size": queue_max_size})

    def _get_queue(self, name: str) -> asyncio.Queue:
        """Get or create a bounded queue for an agent."""
        if name not in self._queues:
            self._queues[name] = asyncio.Queue(maxsize=self._queue_max_size)
        return self._queues[name]

    async def send(self, message: MessageV2) -> bool:
        """
        Send a message to an agent (point-to-point).
        Returns False if queue is full (backpressure) or agent has no listener (DLQ).
        Messages to agents that have never called listen() go to the dead-letter queue.
        """
        if message.recipient not in self._listeners:
            self._add_to_dlq(message, reason="no_listener")
            logger.debug(f"No listener for {message.recipient}, message to DLQ")
            return False

        queue = self._get_queue(message.recipient)
        try:
            queue.put_nowait(message)
            logger.debug(f"Sent {message.sender} → {message.recipient}")
            return True
        except asyncio.QueueFull:
            self._add_to_dlq(message, reason="queue_full")
            logger.warning(f"Queue full for {message.recipient}, message to DLQ")
            return False

    async def listen(self, agent_name: str) -> MessageV2:
        """
        Listen for the next message for an agent (blocking).
        Register that this agent has a listener for DLQ purposes.
        """
        self._listeners.add(agent_name)
        queue = self._get_queue(agent_name)
        try:
            message = await queue.get()
            return message
        finally:
            pass  # Listener stays registered until process exits

    def _add_to_dlq(self, message: MessageV2, reason: str = "undeliverable") -> None:
        """Add message to dead-letter queue."""
        message.metadata["dlq_reason"] = reason
        message.metadata["dlq_timestamp"] = time.time()
        self._dead_letter_queue.append(message)
        if len(self._dead_letter_queue) > self._max_dlq_size:
            self._dead_letter_queue = self._dead_letter_queue[-self._max_dlq_size :]

    async def request(
        self,
        recipient: str,
        content: Any,
        sender: str = "system",
        timeout: float = 30.0,
    ) -> Any:
        """
        Send a request and wait for a correlated response.
        Raises asyncio.TimeoutError on timeout.
        """
        correlation_id = str(uuid.uuid4())
        future: asyncio.Future = asyncio.get_event_loop().create_future()
        self._pending_requests[correlation_id] = future

        message = MessageV2(
            sender=sender,
            recipient=recipient,
            content=content,
            message_type="request",
            correlation_id=correlation_id,
            reply_to=sender,
        )

        sent = await self.send(message)
        if not sent:
            self._pending_requests.pop(correlation_id, None)
            raise RuntimeError("Failed to send request (queue full)")

        try:
            return await asyncio.wait_for(future, timeout=timeout)
        finally:
            self._pending_requests.pop(correlation_id, None)

    async def respond(self, correlation_id: str, content: Any, sender: str = "system") -> None:
        """
        Send a response to a pending request.
        """
        if correlation_id not in self._pending_requests:
            logger.warning(f"No pending request for correlation_id={correlation_id}")
            return

        future = self._pending_requests[correlation_id]
        if not future.done():
            future.set_result(content)

    async def publish(self, topic: str, content: Any, sender: str = "system") -> None:
        """
        Publish a message to all subscribers of a topic.
        """
        if topic not in self._topic_subscribers:
            return

        for subscriber in list(self._topic_subscribers[topic]):
            msg = MessageV2(
                sender=sender,
                recipient=subscriber,
                content={"topic": topic, "payload": content},
                message_type="pubsub",
            )
            await self.send(msg)

    def subscribe(self, agent_name: str, topic: str) -> None:
        """Subscribe an agent to a topic."""
        if topic not in self._topic_subscribers:
            self._topic_subscribers[topic] = []
        if agent_name not in self._topic_subscribers[topic]:
            self._topic_subscribers[topic].append(agent_name)

    def unsubscribe(self, agent_name: str, topic: str) -> None:
        """Unsubscribe an agent from a topic."""
        if topic in self._topic_subscribers:
            try:
                self._topic_subscribers[topic].remove(agent_name)
            except ValueError:
                pass

    def get_dlq_messages(self, limit: int = 100) -> list[MessageV2]:
        """Get messages from the dead-letter queue."""
        return self._dead_letter_queue[-limit:]

    def get_queue_depth(self, agent_name: str) -> int:
        """Get pending message count for an agent."""
        if agent_name in self._queues:
            return self._queues[agent_name].qsize()
        return 0

    def get_all_queue_depths(self) -> dict[str, int]:
        """Get queue depths for all agents."""
        return {name: q.qsize() for name, q in self._queues.items()}


# Singleton for MessageBusV2
_bus_v2_instance: Optional[MessageBusV2] = None


def get_message_bus_v2(queue_max_size: int = DEFAULT_QUEUE_MAX_SIZE) -> MessageBusV2:
    """Get or create the MessageBusV2 singleton."""
    global _bus_v2_instance
    if _bus_v2_instance is None:
        _bus_v2_instance = MessageBusV2(queue_max_size=queue_max_size)
    return _bus_v2_instance


def reset_message_bus_v2() -> None:
    """Reset the MessageBusV2 singleton (for tests)."""
    global _bus_v2_instance
    _bus_v2_instance = None
