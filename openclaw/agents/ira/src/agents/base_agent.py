# src/agents/base_agent.py
"""
Base Agent Class for Autonomous Agents

All agents in the Pantheon inherit from BaseAgent, which provides:
- Message bus integration for inter-agent communication
- Lifecycle management (start, stop)
- Logging with agent identity
- Response handling with proper async routing
"""

import asyncio
import logging
import time
import uuid
from abc import ABC, abstractmethod
from typing import Any, Optional

from .message_bus import get_message_bus, Message, MessageBus


class BaseAgent(ABC):
    """
    Base class for all autonomous agents in the IRA Pantheon.
    
    Each agent is a self-contained, message-driven entity that:
    - Listens for messages on the bus
    - Processes messages through its handle_message method
    - Sends responses back to requesters
    - Can initiate communication with other agents
    
    To create a new agent:
    1. Inherit from BaseAgent
    2. Set self.name in __init__
    3. Implement handle_message()
    """
    
    def __init__(self, name: str, role: str = "agent"):
        """
        Initialize the base agent.
        
        Args:
            name: The agent's unique name (e.g., "Athena", "Clio")
            role: The agent's role description
        """
        self.name = name
        self.role = role
        self.bus: MessageBus = get_message_bus()
        self.logger = logging.getLogger(f"ira.agent.{self.name}")
        
        self._active = False
        self._message_count = 0
        self._total_processing_time = 0.0
        self._pending_responses: dict[str, asyncio.Queue] = {}
        
        self.logger.info({
            "agent": self.name,
            "event": "initialized",
            "role": self.role
        })
    
    async def start(self) -> None:
        """
        Start the agent's message processing loop.
        
        The agent will continuously listen for messages and process them
        until stop() is called.
        """
        self._active = True
        self.logger.info({
            "agent": self.name,
            "event": "starting",
            "status": "listening"
        })
        
        while self._active:
            try:
                message = await self.bus.listen_with_timeout(self.name, timeout=1.0)
                
                if message is None:
                    continue
                
                # Check if this is a response to a pending request
                if message.message_type == "response" and message.correlation_id:
                    if message.correlation_id in self._pending_responses:
                        response_queue = self._pending_responses[message.correlation_id]
                        await response_queue.put(message.content)
                        continue
                
                # Otherwise, process as a new message
                await self._process_message(message)
                
            except asyncio.CancelledError:
                self.logger.info(f"Agent {self.name} was cancelled")
                break
            except Exception as e:
                self.logger.error(f"Error in message loop: {e}", exc_info=True)
    
    async def _process_message(self, message: Message) -> None:
        """Internal message processor with metrics and response handling."""
        start_time = time.time()
        self._message_count += 1
        
        self.logger.info({
            "agent": self.name,
            "event": "message_received",
            "from": message.sender,
            "type": message.message_type,
            "content_preview": str(message.content)[:100]
        })
        
        try:
            response_content = await self.handle_message(message)
            
            if message.message_type == "request" and message.sender != self.name:
                response = Message(
                    sender=self.name,
                    recipient=message.sender,
                    content=response_content,
                    message_type="response",
                    correlation_id=message.correlation_id,
                    metadata={"processing_time": time.time() - start_time}
                )
                await self.bus.send(response)
            
        except Exception as e:
            self.logger.error(f"Error handling message: {e}", exc_info=True)
            
            if message.message_type == "request" and message.sender != self.name:
                error_response = Message(
                    sender=self.name,
                    recipient=message.sender,
                    content=f"Error: {str(e)}",
                    message_type="error",
                    correlation_id=message.correlation_id
                )
                await self.bus.send(error_response)
        
        processing_time = time.time() - start_time
        self._total_processing_time += processing_time
        
        self.logger.info({
            "agent": self.name,
            "event": "message_processed",
            "processing_time": round(processing_time, 3)
        })
    
    @abstractmethod
    async def handle_message(self, message: Message) -> Any:
        """
        Handle an incoming message.
        
        This is the agent's "brain" - implement this method to define
        how the agent responds to different messages.
        """
        raise NotImplementedError("Agents must implement handle_message")
    
    async def send_message(
        self,
        recipient: str,
        content: Any,
        message_type: str = "request",
        wait_for_response: bool = False,
        timeout: float = 30.0
    ) -> Optional[Any]:
        """Send a message to another agent."""
        correlation_id = str(uuid.uuid4()) if wait_for_response else None
        
        message = Message(
            sender=self.name,
            recipient=recipient,
            content=content,
            message_type=message_type,
            correlation_id=correlation_id
        )
        
        if wait_for_response:
            response_queue = asyncio.Queue(maxsize=1)
            self._pending_responses[correlation_id] = response_queue
            
            try:
                await self.bus.send(message)
                response = await asyncio.wait_for(response_queue.get(), timeout=timeout)
                return response
            except asyncio.TimeoutError:
                self.logger.warning(f"Timeout waiting for response from {recipient}")
                return None
            finally:
                self._pending_responses.pop(correlation_id, None)
        else:
            await self.bus.send(message)
            return None
    
    async def delegate(
        self,
        agent_name: str,
        task: str,
        context: Optional[dict] = None,
        timeout: float = 60.0
    ) -> Optional[str]:
        """Delegate a task to another agent and wait for completion."""
        content = {"task": task, "context": context or {}}
        
        self.logger.info({
            "agent": self.name,
            "event": "delegating",
            "to": agent_name,
            "task_preview": task[:100]
        })
        
        return await self.send_message(
            recipient=agent_name,
            content=content,
            wait_for_response=True,
            timeout=timeout
        )
    
    def stop(self) -> None:
        """Stop the agent's message processing loop."""
        self._active = False
        self.logger.info({
            "agent": self.name,
            "event": "stopping",
            "messages_processed": self._message_count,
            "avg_processing_time": (
                self._total_processing_time / self._message_count
                if self._message_count > 0 else 0
            )
        })
    
    def get_stats(self) -> dict:
        """Get agent statistics."""
        return {
            "name": self.name,
            "role": self.role,
            "active": self._active,
            "messages_processed": self._message_count,
            "total_processing_time": round(self._total_processing_time, 2),
            "avg_processing_time": round(
                self._total_processing_time / self._message_count
                if self._message_count > 0 else 0,
                3
            ),
            "pending_responses": len(self._pending_responses),
            "queue_depth": self.bus.get_queue_depth(self.name)
        }
