"""
Agent State Management

Unified state management for Ira across all channels and components.

Provides:
- Persistent state storage (JSON-based)
- Thread-safe state updates
- State versioning and migration
- Channel-specific state namespaces
"""

import json
import threading
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# State file location
STATE_DIR = Path(__file__).parent.parent / "workspace"
STATE_FILE = STATE_DIR / "agent_state.json"
LEGACY_STATE_FILE = STATE_DIR / "state.json"


@dataclass
class ChannelState:
    """State for a specific channel."""
    channel: str
    last_activity: Optional[str] = None
    active_threads: Dict[str, Dict] = field(default_factory=dict)
    pending_actions: List[Dict] = field(default_factory=list)
    error_count: int = 0
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, d: Dict) -> "ChannelState":
        return cls(
            channel=d.get("channel", "unknown"),
            last_activity=d.get("last_activity"),
            active_threads=d.get("active_threads", {}),
            pending_actions=d.get("pending_actions", []),
            error_count=d.get("error_count", 0),
        )


@dataclass
class CognitiveState:
    """State for cognitive components."""
    brain_last_query: Optional[str] = None
    memory_last_consolidation: Optional[str] = None
    memory_last_decay: Optional[str] = None
    episodic_consolidation_count: int = 0
    semantic_memory_count: int = 0
    procedural_memory_count: int = 0
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, d: Dict) -> "CognitiveState":
        return cls(
            brain_last_query=d.get("brain_last_query"),
            memory_last_consolidation=d.get("memory_last_consolidation"),
            memory_last_decay=d.get("memory_last_decay"),
            episodic_consolidation_count=d.get("episodic_consolidation_count", 0),
            semantic_memory_count=d.get("semantic_memory_count", 0),
            procedural_memory_count=d.get("procedural_memory_count", 0),
        )


@dataclass
class AgentState:
    """Complete agent state."""
    version: str = "2.0.0"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    # Operational state
    startup_time: Optional[str] = None
    shutdown_time: Optional[str] = None
    total_requests: int = 0
    total_errors: int = 0
    
    # Channel states
    channels: Dict[str, ChannelState] = field(default_factory=dict)
    
    # Cognitive state
    cognitive: CognitiveState = field(default_factory=CognitiveState)
    
    # Custom state (for extensions)
    custom: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "version": self.version,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "startup_time": self.startup_time,
            "shutdown_time": self.shutdown_time,
            "total_requests": self.total_requests,
            "total_errors": self.total_errors,
            "channels": {k: v.to_dict() for k, v in self.channels.items()},
            "cognitive": self.cognitive.to_dict(),
            "custom": self.custom,
        }
    
    @classmethod
    def from_dict(cls, d: Dict) -> "AgentState":
        state = cls(
            version=d.get("version", "2.0.0"),
            created_at=d.get("created_at", datetime.now().isoformat()),
            updated_at=d.get("updated_at", datetime.now().isoformat()),
            startup_time=d.get("startup_time"),
            shutdown_time=d.get("shutdown_time"),
            total_requests=d.get("total_requests", 0),
            total_errors=d.get("total_errors", 0),
            custom=d.get("custom", {}),
        )
        
        # Parse channel states
        for channel, channel_data in d.get("channels", {}).items():
            state.channels[channel] = ChannelState.from_dict(channel_data)
        
        # Parse cognitive state
        state.cognitive = CognitiveState.from_dict(d.get("cognitive", {}))
        
        return state


class AgentStateManager:
    """
    Thread-safe agent state manager.
    
    Provides centralized state management for all Ira components
    with automatic persistence and recovery.
    """
    
    def __init__(self, state_file: Path = STATE_FILE):
        self.state_file = state_file
        self._lock = threading.RLock()
        self._state: AgentState = AgentState()
        self._dirty = False
        self._auto_save_interval = 30  # seconds
        self._last_save = time.time()
        
        # Ensure state directory exists
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Load existing state
        self._load()
        
        # Mark startup
        self._state.startup_time = datetime.now().isoformat()
        self._dirty = True
    
    def _load(self):
        """Load state from file."""
        # Try new state file first
        if self.state_file.exists():
            try:
                data = json.loads(self.state_file.read_text())
                self._state = AgentState.from_dict(data)
                return
            except Exception as e:
                print(f"[state] Error loading state: {e}")
        
        # Fall back to legacy state file
        if LEGACY_STATE_FILE.exists():
            try:
                data = json.loads(LEGACY_STATE_FILE.read_text())
                # Migrate legacy state
                self._state = AgentState()
                self._state.cognitive.brain_last_query = data.get("brain_last_query")
                self._dirty = True
            except Exception as e:
                print(f"[state] Error loading legacy state: {e}")
    
    def _save(self, force: bool = False):
        """Save state to file."""
        if not self._dirty and not force:
            return
        
        # Check auto-save interval
        now = time.time()
        if not force and (now - self._last_save) < self._auto_save_interval:
            return
        
        self._state.updated_at = datetime.now().isoformat()
        
        try:
            self.state_file.write_text(
                json.dumps(self._state.to_dict(), indent=2)
            )
            self._dirty = False
            self._last_save = now
        except Exception as e:
            print(f"[state] Error saving state: {e}")
    
    def get_state(self) -> AgentState:
        """Get current state (read-only view)."""
        with self._lock:
            return self._state
    
    def update(self, **kwargs):
        """Update top-level state fields."""
        with self._lock:
            for key, value in kwargs.items():
                if hasattr(self._state, key):
                    setattr(self._state, key, value)
            self._dirty = True
            self._save()
    
    def increment_requests(self, count: int = 1):
        """Increment request counter."""
        with self._lock:
            self._state.total_requests += count
            self._dirty = True
            self._save()
    
    def increment_errors(self, count: int = 1):
        """Increment error counter."""
        with self._lock:
            self._state.total_errors += count
            self._dirty = True
            self._save()
    
    # Channel state management
    
    def get_channel_state(self, channel: str) -> ChannelState:
        """Get state for a specific channel."""
        with self._lock:
            if channel not in self._state.channels:
                self._state.channels[channel] = ChannelState(channel=channel)
            return self._state.channels[channel]
    
    def update_channel(self, channel: str, **kwargs):
        """Update channel-specific state."""
        with self._lock:
            if channel not in self._state.channels:
                self._state.channels[channel] = ChannelState(channel=channel)
            
            channel_state = self._state.channels[channel]
            channel_state.last_activity = datetime.now().isoformat()
            
            for key, value in kwargs.items():
                if hasattr(channel_state, key):
                    setattr(channel_state, key, value)
            
            self._dirty = True
            self._save()
    
    def add_pending_action(self, channel: str, action: Dict):
        """Add a pending action to a channel."""
        with self._lock:
            channel_state = self.get_channel_state(channel)
            channel_state.pending_actions.append({
                **action,
                "added_at": datetime.now().isoformat()
            })
            self._dirty = True
            self._save()
    
    def get_pending_actions(self, channel: str) -> List[Dict]:
        """Get pending actions for a channel."""
        with self._lock:
            return self.get_channel_state(channel).pending_actions.copy()
    
    def clear_pending_action(self, channel: str, action_id: str):
        """Clear a pending action."""
        with self._lock:
            channel_state = self.get_channel_state(channel)
            channel_state.pending_actions = [
                a for a in channel_state.pending_actions
                if a.get("id") != action_id
            ]
            self._dirty = True
            self._save()
    
    # Cognitive state management
    
    def update_cognitive(self, **kwargs):
        """Update cognitive state."""
        with self._lock:
            for key, value in kwargs.items():
                if hasattr(self._state.cognitive, key):
                    setattr(self._state.cognitive, key, value)
            self._dirty = True
            self._save()
    
    def record_brain_query(self):
        """Record a brain query timestamp."""
        with self._lock:
            self._state.cognitive.brain_last_query = datetime.now().isoformat()
            self._dirty = True
            self._save()
    
    def record_consolidation(self, memories_created: int = 0):
        """Record a consolidation run."""
        with self._lock:
            self._state.cognitive.memory_last_consolidation = datetime.now().isoformat()
            self._state.cognitive.episodic_consolidation_count += memories_created
            self._dirty = True
            self._save()
    
    def record_decay(self, memories_decayed: int = 0):
        """Record a decay run."""
        with self._lock:
            self._state.cognitive.memory_last_decay = datetime.now().isoformat()
            self._dirty = True
            self._save()
    
    # Custom state management
    
    def set_custom(self, key: str, value: Any):
        """Set a custom state value."""
        with self._lock:
            self._state.custom[key] = value
            self._dirty = True
            self._save()
    
    def get_custom(self, key: str, default: Any = None) -> Any:
        """Get a custom state value."""
        with self._lock:
            return self._state.custom.get(key, default)
    
    # Lifecycle management
    
    def shutdown(self):
        """Record shutdown and save final state."""
        with self._lock:
            self._state.shutdown_time = datetime.now().isoformat()
            self._save(force=True)
    
    def to_dict(self) -> Dict:
        """Get full state as dictionary."""
        with self._lock:
            return self._state.to_dict()


# Singleton instance
_state_manager: Optional[AgentStateManager] = None


def get_state_manager() -> AgentStateManager:
    """Get singleton state manager."""
    global _state_manager
    if _state_manager is None:
        _state_manager = AgentStateManager()
    return _state_manager


def load_state() -> AgentState:
    """Load and return agent state."""
    return get_state_manager().get_state()


def save_state():
    """Force save current state."""
    get_state_manager()._save(force=True)


# Convenience functions for common operations

def record_request(channel: str = "unknown"):
    """Record a request and update channel activity."""
    manager = get_state_manager()
    manager.increment_requests()
    manager.update_channel(channel)


def record_error(channel: str = "unknown", error: str = None):
    """Record an error."""
    manager = get_state_manager()
    manager.increment_errors()
    if channel:
        state = manager.get_channel_state(channel)
        state.error_count += 1
