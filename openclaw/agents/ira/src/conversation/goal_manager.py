#!/usr/bin/env python3
"""
GOAL-ORIENTED DIALOGUE MANAGER - Proactive Conversation Steering
================================================================

Enables IRA to proactively steer conversations towards predefined goals:
- Lead qualification
- Meeting booking
- Quote preparation
- Follow-up scheduling

The GoalManager tracks conversation goals per identity and provides
proactive prompts to advance conversations towards completion.

Usage:
    from goal_manager import GoalManager, get_goal_manager
    
    gm = get_goal_manager()
    
    # Start a goal for a user
    gm.start_goal("user_123", "qualify_lead")
    
    # Update progress based on conversation
    gm.update_goal_progress("user_123", {"budget": "$50,000"})
    
    # Get next proactive prompt
    prompt = gm.get_next_proactive_prompt("user_123")

Integration:
    - Integrates with BrainOrchestrator (Phase 6.5: Goal-Directed Reasoning)
    - Works with ProactiveQuestionEngine for slot-based questions
    - Persists goal state in SQLite for durability
"""

import json
import sqlite3
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import threading


# =============================================================================
# GOAL DATA STRUCTURES
# =============================================================================

class GoalStatus(Enum):
    """Status of a conversation goal."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


@dataclass
class GoalStep:
    """A single step in achieving a goal."""
    step_id: str
    description: str
    prompt: str
    required: bool = True
    completed: bool = False
    completed_at: Optional[datetime] = None
    extracted_value: Optional[str] = None


@dataclass
class Goal:
    """
    Represents a conversation goal.
    
    A goal has:
    - A unique identifier (e.g., "qualify_lead", "book_meeting")
    - A status indicating progress
    - Steps required to complete the goal
    - Context gathered so far
    """
    goal_id: str
    status: GoalStatus = GoalStatus.NOT_STARTED
    steps: List[GoalStep] = field(default_factory=list)
    current_step_index: int = 0
    context: Dict[str, Any] = field(default_factory=dict)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    priority: int = 1
    max_attempts_per_step: int = 3
    attempts_on_current_step: int = 0
    
    @property
    def current_step(self) -> Optional[GoalStep]:
        """Get the current step."""
        if 0 <= self.current_step_index < len(self.steps):
            return self.steps[self.current_step_index]
        return None
    
    @property
    def completion_percentage(self) -> float:
        """Calculate completion percentage."""
        if not self.steps:
            return 100.0
        completed = sum(1 for s in self.steps if s.completed)
        return (completed / len(self.steps)) * 100
    
    @property
    def remaining_steps(self) -> List[GoalStep]:
        """Get remaining uncompleted steps."""
        return [s for s in self.steps if not s.completed]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "goal_id": self.goal_id,
            "status": self.status.value,
            "steps": [
                {
                    "step_id": s.step_id,
                    "description": s.description,
                    "prompt": s.prompt,
                    "required": s.required,
                    "completed": s.completed,
                    "extracted_value": s.extracted_value,
                }
                for s in self.steps
            ],
            "current_step_index": self.current_step_index,
            "context": self.context,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "priority": self.priority,
            "completion_percentage": self.completion_percentage,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Goal":
        """Create from dictionary."""
        goal = cls(
            goal_id=data["goal_id"],
            status=GoalStatus(data["status"]),
            current_step_index=data.get("current_step_index", 0),
            context=data.get("context", {}),
            priority=data.get("priority", 1),
        )
        goal.steps = [
            GoalStep(
                step_id=s["step_id"],
                description=s["description"],
                prompt=s["prompt"],
                required=s.get("required", True),
                completed=s.get("completed", False),
                extracted_value=s.get("extracted_value"),
            )
            for s in data.get("steps", [])
        ]
        if data.get("started_at"):
            goal.started_at = datetime.fromisoformat(data["started_at"])
        if data.get("completed_at"):
            goal.completed_at = datetime.fromisoformat(data["completed_at"])
        return goal


@dataclass
class GoalTemplate:
    """Template for creating goals."""
    goal_id: str
    name: str
    description: str
    steps: List[Dict[str, Any]]
    prompts: Dict[str, str]
    extraction_patterns: Dict[str, List[str]] = field(default_factory=dict)
    priority: int = 1
    trigger_keywords: List[str] = field(default_factory=list)


# =============================================================================
# GOAL STORAGE (SQLite Persistence)
# =============================================================================

class GoalStore:
    """SQLite-based storage for conversation goals."""
    
    def __init__(self, db_path: Optional[Path] = None):
        if db_path is None:
            db_path = Path(__file__).parent.parent.parent.parent.parent.parent / "crm" / "goals.db"
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._init_db()
    
    def _init_db(self):
        """Initialize the database schema."""
        with self._lock:
            conn = sqlite3.connect(str(self.db_path))
            try:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS active_goals (
                        identity_id TEXT PRIMARY KEY,
                        goal_data TEXT NOT NULL,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS goal_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        identity_id TEXT NOT NULL,
                        goal_id TEXT NOT NULL,
                        status TEXT NOT NULL,
                        context TEXT,
                        started_at TIMESTAMP,
                        completed_at TIMESTAMP,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_goal_history_identity 
                    ON goal_history(identity_id)
                """)
                conn.commit()
            finally:
                conn.close()
    
    def save_goal(self, identity_id: str, goal: Goal):
        """Save or update a goal for an identity."""
        with self._lock:
            conn = sqlite3.connect(str(self.db_path))
            try:
                conn.execute("""
                    INSERT OR REPLACE INTO active_goals (identity_id, goal_data, updated_at)
                    VALUES (?, ?, ?)
                """, (identity_id, json.dumps(goal.to_dict()), datetime.utcnow().isoformat()))
                conn.commit()
            finally:
                conn.close()
    
    def get_goal(self, identity_id: str) -> Optional[Goal]:
        """Retrieve the active goal for an identity."""
        with self._lock:
            conn = sqlite3.connect(str(self.db_path))
            try:
                cursor = conn.execute(
                    "SELECT goal_data FROM active_goals WHERE identity_id = ?",
                    (identity_id,)
                )
                row = cursor.fetchone()
                if row:
                    return Goal.from_dict(json.loads(row[0]))
                return None
            finally:
                conn.close()
    
    def delete_goal(self, identity_id: str):
        """Delete the active goal for an identity."""
        with self._lock:
            conn = sqlite3.connect(str(self.db_path))
            try:
                conn.execute("DELETE FROM active_goals WHERE identity_id = ?", (identity_id,))
                conn.commit()
            finally:
                conn.close()
    
    def archive_goal(self, identity_id: str, goal: Goal):
        """Archive a completed/failed goal to history."""
        with self._lock:
            conn = sqlite3.connect(str(self.db_path))
            try:
                conn.execute("""
                    INSERT INTO goal_history 
                    (identity_id, goal_id, status, context, started_at, completed_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    identity_id,
                    goal.goal_id,
                    goal.status.value,
                    json.dumps(goal.context),
                    goal.started_at.isoformat() if goal.started_at else None,
                    goal.completed_at.isoformat() if goal.completed_at else None,
                ))
                conn.commit()
            finally:
                conn.close()
    
    def get_history(self, identity_id: str, limit: int = 10) -> List[Dict]:
        """Get goal history for an identity."""
        with self._lock:
            conn = sqlite3.connect(str(self.db_path))
            try:
                cursor = conn.execute("""
                    SELECT goal_id, status, context, started_at, completed_at
                    FROM goal_history
                    WHERE identity_id = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (identity_id, limit))
                return [
                    {
                        "goal_id": row[0],
                        "status": row[1],
                        "context": json.loads(row[2]) if row[2] else {},
                        "started_at": row[3],
                        "completed_at": row[4],
                    }
                    for row in cursor.fetchall()
                ]
            finally:
                conn.close()


# =============================================================================
# GOAL MANAGER
# =============================================================================

class GoalManager:
    """
    Manages conversation goals and proactive prompts.
    
    Core responsibilities:
    1. Track active goals per identity
    2. Update goal progress based on conversation
    3. Generate proactive prompts to advance goals
    4. Detect when goals are triggered
    """
    
    def __init__(self, goals_config_path: Optional[Path] = None):
        self.store = GoalStore()
        self._templates: Dict[str, GoalTemplate] = {}
        self._load_goal_templates(goals_config_path)
    
    def _load_goal_templates(self, config_path: Optional[Path] = None):
        """Load goal templates from JSON configuration."""
        if config_path is None:
            config_path = Path(__file__).parent / "goals.json"
        
        if not config_path.exists():
            self._templates = self._get_default_templates()
            return
        
        try:
            with open(config_path) as f:
                data = json.load(f)
            
            for goal_id, config in data.items():
                steps = []
                for step_id in config.get("steps", []):
                    steps.append({
                        "step_id": step_id,
                        "description": config.get("step_descriptions", {}).get(step_id, step_id),
                        "required": config.get("required_steps", {}).get(step_id, True),
                    })
                
                self._templates[goal_id] = GoalTemplate(
                    goal_id=goal_id,
                    name=config.get("name", goal_id),
                    description=config.get("description", ""),
                    steps=steps,
                    prompts=config.get("prompts", {}),
                    extraction_patterns=config.get("extraction_patterns", {}),
                    priority=config.get("priority", 1),
                    trigger_keywords=config.get("trigger_keywords", []),
                )
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Could not load goals.json: {e}")
            self._templates = self._get_default_templates()
    
    def _get_default_templates(self) -> Dict[str, GoalTemplate]:
        """Get default goal templates if config file not found."""
        return {
            "qualify_lead": GoalTemplate(
                goal_id="qualify_lead",
                name="Lead Qualification",
                description="Qualify a potential customer",
                steps=[
                    {"step_id": "ask_application", "description": "Understand application", "required": True},
                    {"step_id": "ask_budget", "description": "Understand budget", "required": True},
                    {"step_id": "ask_timeline", "description": "Understand timeline", "required": True},
                ],
                prompts={
                    "ask_application": "What specific application will you be using the machine for?",
                    "ask_budget": "To help me recommend the right machine, could you share a bit about your budget?",
                    "ask_timeline": "What is your expected timeline for this project?",
                },
                extraction_patterns={
                    "ask_application": [r"(thermoform|vacuum form|blister|packaging|automotive|signage)", r"(?:for|making|producing)\s+(\w+(?:\s+\w+){0,3})"],
                    "ask_budget": [r"\$[\d,]+", r"(?:budget|spend|invest)\s+(?:is|of|around|about)?\s*[\d,]+", r"(?:INR|USD|EUR)\s*[\d,]+"],
                    "ask_timeline": [r"(urgent|asap|immediate|this (?:week|month|quarter|year))", r"(Q[1-4]|H[12])\s*\d{4}", r"(?:by|within|in)\s+(\d+)\s*(?:days?|weeks?|months?)"],
                },
                trigger_keywords=["machine", "thermoforming", "vacuum forming", "quote", "inquiry"],
            ),
            "book_meeting": GoalTemplate(
                goal_id="book_meeting",
                name="Meeting Booking",
                description="Schedule a meeting with the prospect",
                steps=[
                    {"step_id": "propose_meeting", "description": "Propose a meeting", "required": True},
                    {"step_id": "confirm_time", "description": "Confirm meeting time", "required": True},
                    {"step_id": "get_contact", "description": "Get contact details", "required": False},
                ],
                prompts={
                    "propose_meeting": "Would you be available for a quick call this week to discuss your requirements in detail?",
                    "confirm_time": "What times work best for you? I'm flexible with my schedule.",
                    "get_contact": "Could you share your preferred contact number or email for the meeting invite?",
                },
                extraction_patterns={
                    "confirm_time": [r"(monday|tuesday|wednesday|thursday|friday|saturday|sunday)", r"(\d{1,2}(?::\d{2})?\s*(?:am|pm))", r"(morning|afternoon|evening)"],
                    "get_contact": [r"[\w.-]+@[\w.-]+\.\w+", r"\+?\d[\d\s-]{8,}"],
                },
                trigger_keywords=["meeting", "call", "discuss", "demo", "visit"],
            ),
        }
    
    def get_active_goal(self, identity_id: str) -> Optional[Goal]:
        """
        Retrieve the current active goal for a user.
        
        Args:
            identity_id: Unique identifier for the user
            
        Returns:
            The active Goal object, or None if no goal is active
        """
        return self.store.get_goal(identity_id)
    
    def start_goal(self, identity_id: str, goal_id: str, initial_context: Optional[Dict] = None) -> Goal:
        """
        Start a new goal for a user.
        
        Args:
            identity_id: Unique identifier for the user
            goal_id: The goal template ID to start
            initial_context: Any initial context to seed the goal
            
        Returns:
            The newly created Goal object
        """
        template = self._templates.get(goal_id)
        if not template:
            raise ValueError(f"Unknown goal: {goal_id}")
        
        existing = self.store.get_goal(identity_id)
        if existing and existing.status == GoalStatus.IN_PROGRESS:
            existing.status = GoalStatus.PAUSED
            self.store.archive_goal(identity_id, existing)
        
        steps = []
        for step_config in template.steps:
            step_id = step_config["step_id"]
            steps.append(GoalStep(
                step_id=step_id,
                description=step_config.get("description", step_id),
                prompt=template.prompts.get(step_id, ""),
                required=step_config.get("required", True),
            ))
        
        goal = Goal(
            goal_id=goal_id,
            status=GoalStatus.IN_PROGRESS,
            steps=steps,
            context=initial_context or {},
            started_at=datetime.utcnow(),
            priority=template.priority,
        )
        
        self.store.save_goal(identity_id, goal)
        return goal
    
    def update_goal_progress(
        self,
        identity_id: str,
        message: str,
        context: Optional[Dict] = None,
    ) -> Tuple[Optional[Goal], bool]:
        """
        Update goal progress based on conversation.
        
        Analyzes the message to extract relevant information and
        advances the goal state accordingly.
        
        Args:
            identity_id: Unique identifier for the user
            message: The user's message to analyze
            context: Additional context from the conversation
            
        Returns:
            Tuple of (updated Goal, whether step was completed)
        """
        goal = self.store.get_goal(identity_id)
        if not goal or goal.status != GoalStatus.IN_PROGRESS:
            return goal, False
        
        template = self._templates.get(goal.goal_id)
        if not template:
            return goal, False
        
        step_completed = False
        current_step = goal.current_step
        
        if current_step:
            patterns = template.extraction_patterns.get(current_step.step_id, [])
            extracted = self._extract_information(message, patterns)
            
            if extracted:
                current_step.completed = True
                current_step.completed_at = datetime.utcnow()
                current_step.extracted_value = extracted
                goal.context[current_step.step_id] = extracted
                step_completed = True
                
                goal.current_step_index += 1
                goal.attempts_on_current_step = 0
            else:
                goal.attempts_on_current_step += 1
        
        if context:
            goal.context.update(context)
        
        all_required_complete = all(
            s.completed for s in goal.steps if s.required
        )
        if all_required_complete:
            goal.status = GoalStatus.COMPLETED
            goal.completed_at = datetime.utcnow()
            self.store.archive_goal(identity_id, goal)
            self.store.delete_goal(identity_id)
        else:
            self.store.save_goal(identity_id, goal)
        
        return goal, step_completed
    
    def _extract_information(self, message: str, patterns: List[str]) -> Optional[str]:
        """Extract information from message using regex patterns."""
        for pattern in patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                return match.group(0) if match.lastindex is None else match.group(1)
        return None
    
    def get_next_proactive_prompt(
        self,
        identity_id: str,
        emotional_state: str = "neutral",
    ) -> Optional[str]:
        """
        Get the next proactive prompt to advance the goal.
        
        Args:
            identity_id: Unique identifier for the user
            emotional_state: Current emotional state of user
            
        Returns:
            The prompt string, or None if no prompt should be given
        """
        if emotional_state in ["frustrated", "angry", "stressed"]:
            return None
        
        goal = self.store.get_goal(identity_id)
        if not goal or goal.status != GoalStatus.IN_PROGRESS:
            return None
        
        current_step = goal.current_step
        if not current_step:
            return None
        
        if goal.attempts_on_current_step >= goal.max_attempts_per_step:
            if not current_step.required:
                current_step.completed = True
                goal.current_step_index += 1
                goal.attempts_on_current_step = 0
                self.store.save_goal(identity_id, goal)
                return self.get_next_proactive_prompt(identity_id, emotional_state)
            return None
        
        return current_step.prompt
    
    def detect_goal_trigger(
        self,
        message: str,
        context: Optional[Dict] = None,
    ) -> Optional[str]:
        """
        Detect if a message should trigger a new goal.
        
        Args:
            message: The user's message
            context: Additional context
            
        Returns:
            The goal_id to trigger, or None
        """
        message_lower = message.lower()
        
        for goal_id, template in self._templates.items():
            for keyword in template.trigger_keywords:
                if keyword.lower() in message_lower:
                    return goal_id
        
        return None
    
    def get_goal_status(self, identity_id: str) -> Dict[str, Any]:
        """
        Get comprehensive status of user's goal.
        
        Returns dict with:
        - has_active_goal: bool
        - goal_id: str or None
        - completion_percentage: float
        - remaining_steps: list
        - context: dict
        """
        goal = self.store.get_goal(identity_id)
        
        if not goal:
            return {
                "has_active_goal": False,
                "goal_id": None,
                "completion_percentage": 0,
                "remaining_steps": [],
                "context": {},
            }
        
        return {
            "has_active_goal": True,
            "goal_id": goal.goal_id,
            "status": goal.status.value,
            "completion_percentage": goal.completion_percentage,
            "remaining_steps": [s.step_id for s in goal.remaining_steps],
            "context": goal.context,
            "current_step": goal.current_step.step_id if goal.current_step else None,
        }
    
    def cancel_goal(self, identity_id: str, reason: str = "user_cancelled") -> bool:
        """Cancel the active goal for an identity."""
        goal = self.store.get_goal(identity_id)
        if not goal:
            return False
        
        goal.status = GoalStatus.FAILED
        goal.context["cancellation_reason"] = reason
        goal.completed_at = datetime.utcnow()
        
        self.store.archive_goal(identity_id, goal)
        self.store.delete_goal(identity_id)
        return True
    
    def get_goal_templates(self) -> List[Dict[str, Any]]:
        """Get all available goal templates."""
        return [
            {
                "goal_id": t.goal_id,
                "name": t.name,
                "description": t.description,
                "steps": [s["step_id"] for s in t.steps],
                "priority": t.priority,
            }
            for t in self._templates.values()
        ]


# =============================================================================
# SINGLETON INSTANCE
# =============================================================================

_goal_manager: Optional[GoalManager] = None


def get_goal_manager() -> GoalManager:
    """Get singleton GoalManager instance."""
    global _goal_manager
    if _goal_manager is None:
        _goal_manager = GoalManager()
    return _goal_manager


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def get_active_goal(identity_id: str) -> Optional[Goal]:
    """Get the active goal for an identity."""
    return get_goal_manager().get_active_goal(identity_id)


def start_goal(identity_id: str, goal_id: str, context: Optional[Dict] = None) -> Goal:
    """Start a new goal for an identity."""
    return get_goal_manager().start_goal(identity_id, goal_id, context)


def update_goal(identity_id: str, message: str, context: Optional[Dict] = None) -> Tuple[Optional[Goal], bool]:
    """Update goal progress based on message."""
    return get_goal_manager().update_goal_progress(identity_id, message, context)


def get_proactive_prompt(identity_id: str, emotional_state: str = "neutral") -> Optional[str]:
    """Get the next proactive prompt for an identity."""
    return get_goal_manager().get_next_proactive_prompt(identity_id, emotional_state)


def detect_goal(message: str, context: Optional[Dict] = None) -> Optional[str]:
    """Detect if a message should trigger a goal."""
    return get_goal_manager().detect_goal_trigger(message, context)


# =============================================================================
# CLI TESTING
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("GOAL MANAGER TEST")
    print("=" * 60)
    
    gm = GoalManager()
    
    print("\nAvailable goal templates:")
    for template in gm.get_goal_templates():
        print(f"  - {template['goal_id']}: {template['name']}")
    
    test_identity = "test_user_123"
    
    print(f"\n[Test 1] Starting 'qualify_lead' goal for {test_identity}")
    goal = gm.start_goal(test_identity, "qualify_lead")
    print(f"  Status: {goal.status.value}")
    print(f"  Steps: {[s.step_id for s in goal.steps]}")
    
    print("\n[Test 2] Getting proactive prompt")
    prompt = gm.get_next_proactive_prompt(test_identity)
    print(f"  Prompt: {prompt}")
    
    print("\n[Test 3] Updating with application info")
    goal, completed = gm.update_goal_progress(
        test_identity, 
        "We need this for thermoforming automotive interior parts"
    )
    print(f"  Step completed: {completed}")
    print(f"  Completion: {goal.completion_percentage:.0f}%")
    print(f"  Context: {goal.context}")
    
    print("\n[Test 4] Getting next prompt")
    prompt = gm.get_next_proactive_prompt(test_identity)
    print(f"  Prompt: {prompt}")
    
    print("\n[Test 5] Updating with budget")
    goal, completed = gm.update_goal_progress(
        test_identity,
        "Our budget is around $75,000"
    )
    print(f"  Step completed: {completed}")
    print(f"  Completion: {goal.completion_percentage:.0f}%")
    
    print("\n[Test 6] Final update with timeline")
    goal, completed = gm.update_goal_progress(
        test_identity,
        "We need this operational by Q2 2026"
    )
    print(f"  Step completed: {completed}")
    print(f"  Goal status: {goal.status.value}")
    print(f"  Final context: {goal.context}")
    
    print("\n[Test 7] Detecting goal trigger")
    trigger_msg = "I'm looking for a thermoforming machine for packaging"
    detected = gm.detect_goal_trigger(trigger_msg)
    print(f"  Message: '{trigger_msg}'")
    print(f"  Detected goal: {detected}")
    
    print("\n" + "=" * 60)
    print("Goal Manager ready!")
    print("=" * 60)
