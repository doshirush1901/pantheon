"""
Ira - Intelligent Revenue Assistant

The central agent for Machinecraft Technologies, providing:
- Multi-channel communication (Telegram, Email, API)
- Cognitive memory (semantic, episodic, procedural)
- Knowledge retrieval (RAG)
- Conversational AI (emotion, relationship, proactive)

Usage:
    from openclaw.agents.ira import get_agent, process
    
    # Get agent instance
    agent = get_agent()
    
    # Process a message
    response = agent.process("What's the price for PF1?", channel="telegram", user_id="123")
    
    # Or use convenience function
    response = process("What's the price for PF1?", channel="telegram", user_id="123")
"""

from .agent import (
    IraAgent,
    AgentConfig,
    AgentRequest,
    AgentResponse,
    AgentHealth,
    AgentState,
    Channel,
    get_agent,
    process,
)

__all__ = [
    "IraAgent",
    "AgentConfig",
    "AgentRequest",
    "AgentResponse",
    "AgentHealth",
    "AgentState",
    "Channel",
    "get_agent",
    "process",
]

__version__ = "2.0.0"
