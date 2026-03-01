# src/agents/message_bus.py
"""
Inter-Agent Communication Backbone

This message bus enables true multi-agent autonomy by allowing agents to
communicate with each other through natural language messages rather than
rigid function calls with complex data objects.

The bus is the nervous system of the Pantheon.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger("ira.message_bus")

# Power Level tracking for collaboration
try:
    from src.brain.power_levels import get_power_tracker
    POWER_LEVELS_AVAILABLE = True
except ImportError:
    POWER_LEVELS_AVAILABLE = False


@dataclass
class Message:
    """
    A message between agents.
    
    Messages are the atomic unit of inter-agent communication.
    Content should be simple strings or dictionaries, not complex objects.
    """
    sender: str
    recipient: str
    content: Any
    message_type: str = "request"  # request, response, broadcast, error
    correlation_id: Optional[str] = None  # For request-response tracking
    timestamp: float = field(default_factory=time.time)
    metadata: dict = field(default_factory=dict)
    
    def __repr__(self) -> str:
        preview = str(self.content)[:50] + "..." if len(str(self.content)) > 50 else str(self.content)
        return f"Message({self.sender} → {self.recipient}: {preview})"


class MessageBus:
    """
    Central message bus for inter-agent communication.
    
    Each agent gets its own async queue. Messages are routed by recipient name.
    This decouples agents from each other - they only need to know names, not implementations.
    """
    
    def __init__(self):
        self.queues: dict[str, asyncio.Queue] = {}
        self.message_log: list[Message] = []
        self.max_log_size = 1000
        self._subscribers: dict[str, list[str]] = {}  # For broadcast support
        logger.info({"event": "message_bus_initialized"})
    
    def get_queue(self, agent_name: str) -> asyncio.Queue:
        """Get or create a message queue for an agent."""
        if agent_name not in self.queues:
            self.queues[agent_name] = asyncio.Queue()
            logger.debug(f"Created queue for agent: {agent_name}")
        return self.queues[agent_name]
    
    async def send(self, message: Message) -> None:
        """
        Send a message to an agent.
        
        Args:
            message: The message to send (uses message.recipient for routing)
        """
        queue = self.get_queue(message.recipient)
        await queue.put(message)
        
        # Log the message
        self.message_log.append(message)
        if len(self.message_log) > self.max_log_size:
            self.message_log = self.message_log[-self.max_log_size:]
        
        logger.info({
            "event": "message_sent",
            "from": message.sender,
            "to": message.recipient,
            "type": message.message_type,
            "content_preview": str(message.content)[:100]
        })
    
    async def send_to(self, recipient: str, message: Message) -> None:
        """Convenience method to send to a specific recipient."""
        message.recipient = recipient
        await self.send(message)
    
    async def listen(self, agent_name: str) -> Message:
        """
        Listen for messages addressed to an agent.
        
        This is a blocking call that waits for the next message.
        
        Args:
            agent_name: The agent listening for messages
            
        Returns:
            The next message for this agent
        """
        queue = self.get_queue(agent_name)
        message = await queue.get()
        logger.debug(f"Agent {agent_name} received message from {message.sender}")
        return message
    
    async def listen_with_timeout(self, agent_name: str, timeout: float = 30.0) -> Optional[Message]:
        """Listen for messages with a timeout."""
        try:
            queue = self.get_queue(agent_name)
            message = await asyncio.wait_for(queue.get(), timeout=timeout)
            return message
        except asyncio.TimeoutError:
            return None
    
    async def broadcast(self, sender: str, content: Any, exclude: Optional[list[str]] = None) -> None:
        """
        Broadcast a message to all registered agents.
        
        Args:
            sender: The sending agent's name
            content: The message content
            exclude: List of agent names to exclude from broadcast
        """
        exclude = exclude or []
        exclude.append(sender)  # Don't send to self
        
        for agent_name in self.queues.keys():
            if agent_name not in exclude:
                message = Message(
                    sender=sender,
                    recipient=agent_name,
                    content=content,
                    message_type="broadcast"
                )
                await self.send(message)
    
    def get_queue_depth(self, agent_name: str) -> int:
        """Get the number of pending messages for an agent."""
        if agent_name in self.queues:
            return self.queues[agent_name].qsize()
        return 0
    
    def get_all_queue_depths(self) -> dict[str, int]:
        """Get queue depths for all agents."""
        return {name: q.qsize() for name, q in self.queues.items()}
    
    def get_recent_messages(self, count: int = 10) -> list[Message]:
        """Get the most recent messages for debugging."""
        return self.message_log[-count:]
    
    def record_successful_collaboration(self, agent1: str, agent2: str):
        """
        Record a successful collaboration between two agents.
        
        Call this when agents complete a task together successfully.
        Both agents get a synergy power boost.
        """
        if not POWER_LEVELS_AVAILABLE:
            return
        
        try:
            # Convert agent names to IDs
            name_to_id = {
                "Athena": "chief_of_staff",
                "Clio": "researcher",
                "Calliope": "writer",
                "Vera": "fact_checker",
                "Sophia": "reflector",
            }
            
            id1 = name_to_id.get(agent1, agent1.lower().replace(" ", "_"))
            id2 = name_to_id.get(agent2, agent2.lower().replace(" ", "_"))
            
            tracker = get_power_tracker()
            tracker.record_collaboration(id1, id2, success=True)
            
            logger.info({
                "event": "collaboration_recorded",
                "agents": [agent1, agent2],
                "success": True
            })
        except Exception as e:
            logger.debug(f"Failed to record collaboration: {e}")
    
    def record_failed_collaboration(self, agent1: str, agent2: str):
        """Record a failed collaboration between two agents."""
        if not POWER_LEVELS_AVAILABLE:
            return
        
        try:
            name_to_id = {
                "Athena": "chief_of_staff",
                "Clio": "researcher",
                "Calliope": "writer",
                "Vera": "fact_checker",
                "Sophia": "reflector",
            }
            
            id1 = name_to_id.get(agent1, agent1.lower().replace(" ", "_"))
            id2 = name_to_id.get(agent2, agent2.lower().replace(" ", "_"))
            
            tracker = get_power_tracker()
            tracker.record_collaboration(id1, id2, success=False)
        except Exception as e:
            _log = __import__('logging').getLogger('ira.message_bus')
            _log.warning("Power tracker collaboration failed: %s", e, exc_info=True)


# Singleton instance
_bus_instance: Optional[MessageBus] = None


def get_message_bus() -> MessageBus:
    """Get the singleton message bus instance."""
    global _bus_instance
    if _bus_instance is None:
        _bus_instance = MessageBus()
    return _bus_instance


def reset_message_bus() -> None:
    """Reset the message bus (useful for testing)."""
    global _bus_instance
    _bus_instance = None
