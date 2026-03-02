#!/usr/bin/env python3
"""
UNIFIED MEMORY SERVICE - Conversation Context and State Management
===================================================================

Provides conversation history, identity mapping, and context retrieval.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
import json
import sys

# Add conversation skills to path for entity extraction
SKILL_DIR = Path(__file__).parent
sys.path.insert(0, str(SKILL_DIR.parent / "conversation"))


class Channel(Enum):
    TELEGRAM = "telegram"
    EMAIL = "email"


@dataclass
class MessageTurn:
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    channel: str = "telegram"
    
    def to_dict(self) -> Dict:
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "channel": self.channel,
        }


@dataclass
class ConversationState:
    channel: str
    identifier: str  # chat_id or email
    recent_messages: List[MessageTurn] = field(default_factory=list)
    rolling_summary: str = ""
    key_entities: Dict = field(default_factory=dict)
    open_questions: List[Dict] = field(default_factory=list)
    kg_facts: List[Dict] = field(default_factory=list)
    identity: Optional[Dict] = None
    is_internal: bool = False
    current_mode: str = "general"
    current_stage: str = "new"
    message_count: int = 0
    last_user_message: str = ""
    
    def to_dict(self) -> Dict:
        return {
            "channel": self.channel,
            "identifier": self.identifier,
            "recent_messages": [m.to_dict() if hasattr(m, 'to_dict') else m for m in self.recent_messages],
            "rolling_summary": self.rolling_summary,
            "key_entities": self.key_entities,
            "open_questions": self.open_questions,
            "kg_facts": self.kg_facts,
            "identity": self.identity,
            "is_internal": self.is_internal,
            "current_mode": self.current_mode,
            "current_stage": self.current_stage,
            "message_count": self.message_count,
            "last_user_message": self.last_user_message,
        }


@dataclass
class ContextPack:
    """Context pack for response generation."""
    recent_messages: List[Dict] = field(default_factory=list)
    rolling_summary: str = ""
    open_questions: List[Dict] = field(default_factory=list)
    key_entities: Dict = field(default_factory=dict)
    kg_facts: List[Dict] = field(default_factory=list)
    rag_chunks: List[Dict] = field(default_factory=list)
    identity: Optional[Dict] = None
    is_internal: bool = False
    thread_id: str = ""
    current_mode: str = "general"
    current_stage: str = "new"
    user_memories: List[Dict] = field(default_factory=list)


@dataclass
class UserIdentity:
    """Represents a user's cross-channel identity."""
    identity_id: str
    telegram_chat_id: Optional[str] = None
    email: Optional[str] = None
    name: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            "identity_id": self.identity_id,
            "telegram_chat_id": self.telegram_chat_id,
            "email": self.email,
            "name": self.name,
        }


class MemoryService:
    """
    Unified memory service for conversation state management.
    """
    
    def __init__(self, storage_path: Optional[str] = None):
        self.storage_path = storage_path or str(Path(__file__).parent / "state")
        self.states: Dict[str, ConversationState] = {}
        Path(self.storage_path).mkdir(parents=True, exist_ok=True)
    
    def _state_key(self, channel: str, identifier: str) -> str:
        return f"{channel}:{identifier}"
    
    def load_state(self, channel: str, identifier: str) -> ConversationState:
        """Load or create conversation state."""
        key = self._state_key(channel, identifier)
        
        if key in self.states:
            return self.states[key]
        
        # Try to load from file
        state_file = Path(self.storage_path) / f"{key.replace(':', '_')}.json"
        if state_file.exists():
            try:
                data = json.loads(state_file.read_text())
                state = ConversationState(
                    channel=data.get("channel", channel),
                    identifier=data.get("identifier", identifier),
                    rolling_summary=data.get("rolling_summary", ""),
                    key_entities=data.get("key_entities", {}),
                    open_questions=data.get("open_questions", []),
                    identity=data.get("identity"),
                    is_internal=data.get("is_internal", False),
                    current_mode=data.get("current_mode", "general"),
                    current_stage=data.get("current_stage", "new"),
                    message_count=data.get("message_count", 0),
                    last_user_message=data.get("last_user_message", ""),
                )
                # Convert recent_messages
                for msg in data.get("recent_messages", []):
                    state.recent_messages.append(MessageTurn(
                        role=msg.get("role", "user"),
                        content=msg.get("content", ""),
                        channel=msg.get("channel", channel),
                    ))
                self.states[key] = state
                return state
            except Exception:
                pass
        
        # Create new state
        state = ConversationState(channel=channel, identifier=identifier)
        self.states[key] = state
        return state
    
    def save_state(self, state: ConversationState) -> None:
        """Save conversation state."""
        key = self._state_key(state.channel, state.identifier)
        self.states[key] = state
        
        # Save to file
        state_file = Path(self.storage_path) / f"{key.replace(':', '_')}.json"
        try:
            state_file.write_text(json.dumps(state.to_dict(), indent=2, default=str))
        except Exception as e:
            print(f"[MemoryService] Failed to save state: {e}")
    
    def get_context_pack(self, channel: str, identifier: str, message: str) -> ContextPack:
        """Get context pack for response generation."""
        state = self.load_state(channel, identifier)
        
        return ContextPack(
            recent_messages=[m.to_dict() if hasattr(m, 'to_dict') else m for m in state.recent_messages],
            rolling_summary=state.rolling_summary,
            open_questions=state.open_questions,
            key_entities=state.key_entities,
            kg_facts=state.kg_facts,
            identity=state.identity,
            is_internal=state.is_internal,
            thread_id=identifier,
            current_mode=state.current_mode,
            current_stage=state.current_stage,
        )
    
    def link_identities(
        self,
        channel1: str,
        id1: str,
        channel2: str,
        id2: str,
        confidence: float = 0.8
    ) -> Optional[str]:
        """
        Link two identities across channels.
        
        Returns the shared identity_id if successful.
        """
        if not id1 or not id2:
            return None
        
        links_file = Path(self.storage_path) / "identity_links.json"
        
        try:
            if links_file.exists():
                links = json.loads(links_file.read_text())
            else:
                links = {"identities": {}, "mappings": {}}
            
            key1 = f"{channel1}:{id1}"
            key2 = f"{channel2}:{id2}"
            
            # Check if either is already mapped
            existing_id = links["mappings"].get(key1) or links["mappings"].get(key2)
            
            if existing_id:
                # Use existing identity, add new mapping
                identity_id = existing_id
            else:
                # Create new identity
                import uuid
                identity_id = f"id_{uuid.uuid4().hex[:12]}"
                links["identities"][identity_id] = {
                    "created_at": datetime.now().isoformat(),
                    "channels": {}
                }
            
            # Add mappings
            links["mappings"][key1] = identity_id
            links["mappings"][key2] = identity_id
            
            # Update identity record
            links["identities"][identity_id]["channels"][channel1] = id1
            links["identities"][identity_id]["channels"][channel2] = id2
            links["identities"][identity_id]["confidence"] = confidence
            links["identities"][identity_id]["updated_at"] = datetime.now().isoformat()
            
            links_file.write_text(json.dumps(links, indent=2))
            
            # Update state identities for both channels
            for ch, ident in [(channel1, id1), (channel2, id2)]:
                state = self.load_state(ch, ident)
                state.identity = {
                    "identity_id": identity_id,
                    channel1: id1,
                    channel2: id2
                }
                self.save_state(state)
            
            print(f"[MemoryService] Linked: {key1} ↔ {key2} → {identity_id}")
            return identity_id
            
        except Exception as e:
            print(f"[MemoryService] Link identities error: {e}")
            return None
    
    def get_identity_id(self, channel: str, identifier: str) -> Optional[str]:
        """Get the shared identity_id for a channel:identifier pair."""
        links_file = Path(self.storage_path) / "identity_links.json"
        
        try:
            if not links_file.exists():
                return None
            
            links = json.loads(links_file.read_text())
            key = f"{channel}:{identifier}"
            return links["mappings"].get(key)
            
        except Exception:
            return None
    
    def get_identity(self, telegram_chat_id: str = None, email: str = None) -> Optional["UserIdentity"]:
        """
        Get identity object for a user by telegram chat ID or email.
        Returns UserIdentity object or None.
        """
        channel = None
        identifier = None
        
        if telegram_chat_id:
            channel = "telegram"
            identifier = telegram_chat_id
        elif email:
            channel = "email"
            identifier = email.lower()
        else:
            return None
        
        identity_id = self.get_identity_id(channel, identifier)
        if not identity_id:
            # Try to create one from existing state
            state = self.load_state(channel, identifier)
            if state.identity and state.identity.get("identity_id"):
                identity_id = state.identity["identity_id"]
            else:
                # Create a new identity
                identity_id = self.create_or_update_identity(
                    telegram_chat_id=telegram_chat_id,
                    email=email
                )
                if not identity_id:
                    return None
        
        return UserIdentity(identity_id=identity_id, telegram_chat_id=telegram_chat_id, email=email)
    
    def create_or_update_identity(
        self, 
        telegram_chat_id: str = None, 
        email: str = None,
        name: str = None
    ) -> Optional[str]:
        """
        Create or update a user identity.
        Returns the identity_id.
        """
        import uuid
        
        channel = None
        identifier = None
        
        if telegram_chat_id:
            channel = "telegram"
            identifier = telegram_chat_id
        elif email:
            channel = "email"
            identifier = email.lower()
        else:
            return None
        
        # Check if identity already exists
        existing_id = self.get_identity_id(channel, identifier)
        if existing_id:
            return existing_id
        
        # Create new identity
        links_file = Path(self.storage_path) / "identity_links.json"
        
        try:
            if links_file.exists():
                links = json.loads(links_file.read_text())
            else:
                links = {"identities": {}, "mappings": {}}
            
            identity_id = f"id_{uuid.uuid4().hex[:12]}"
            key = f"{channel}:{identifier}"
            
            links["mappings"][key] = identity_id
            links["identities"][identity_id] = {
                "created_at": datetime.now().isoformat(),
                "channels": {channel: identifier},
                "name": name
            }
            
            links_file.write_text(json.dumps(links, indent=2))
            
            # Update state
            state = self.load_state(channel, identifier)
            state.identity = {"identity_id": identity_id, channel: identifier}
            self.save_state(state)
            
            print(f"[MemoryService] Created identity: {identity_id} for {key}")
            return identity_id
            
        except Exception as e:
            print(f"[MemoryService] Create identity error: {e}")
            return None
    
    def update_context_after_response(
        self,
        channel: str,
        identifier: str,
        user_message: str,
        response_text: str,
        mode: str = "general",
        intent: str = "",
        questions_asked: List[str] = None,
        entities_extracted: Dict = None
    ) -> None:
        """Update context after a response is generated."""
        state = self.load_state(channel, identifier)
        
        # Add messages
        state.recent_messages.append(MessageTurn(
            role="user",
            content=user_message,
            channel=channel
        ))
        state.recent_messages.append(MessageTurn(
            role="assistant", 
            content=response_text[:500],
            channel=channel
        ))
        
        # Keep only recent messages
        if len(state.recent_messages) > 12:
            state.recent_messages = state.recent_messages[-12:]
        
        state.message_count += 1
        state.last_user_message = user_message
        state.current_mode = mode
        
        # Auto-extract entities if not provided
        if entities_extracted:
            state.key_entities.update(entities_extracted)
        else:
            # Automatically extract entities from user message
            try:
                from entity_extractor import extract_entities
                extracted = extract_entities(user_message)
                if not extracted.is_empty():
                    # Merge with existing entities
                    for key, values in extracted.to_dict().items():
                        if values:
                            existing = state.key_entities.get(key, [])
                            merged = list(set(existing + values))
                            state.key_entities[key] = merged
            except ImportError:
                pass  # Entity extractor not available
            except Exception as e:
                print(f"[MemoryService] Entity extraction error: {e}")
        
        # Track open questions
        if questions_asked:
            state.open_questions = [{"question": q, "asked_at": datetime.now().isoformat()} 
                                   for q in questions_asked]
        
        self.save_state(state)


# Singleton instance
_memory_service: Optional[MemoryService] = None


def get_memory_service() -> MemoryService:
    """Get or create memory service singleton."""
    global _memory_service
    if _memory_service is None:
        _memory_service = MemoryService()
    return _memory_service
