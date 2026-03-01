#!/usr/bin/env python3
"""
PROCEDURAL MEMORY - Learning HOW to Do Things

╔════════════════════════════════════════════════════════════════════╗
║  User/Entity Memory = WHAT (facts)                                 ║
║  Procedural Memory  = HOW (skills, workflows, processes)           ║
╚════════════════════════════════════════════════════════════════════╝

This module enables Ira to:
1. Learn workflows from successful task completions
2. Remember step-by-step procedures
3. Apply learned skills to similar future tasks
4. Improve procedures based on feedback

Example:
- User teaches: "When someone asks for a quote, first check inventory,
                 then check pricing, then format the quote."
- Ira learns: procedure "generate_quote" with steps [check_inventory, 
              check_pricing, format_quote]
- Next time: Automatically applies this workflow
"""

import json
import os
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import hashlib

# Import from centralized config via brain_orchestrator
try:
    from config import DATABASE_URL
except ImportError:
    import os
    DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://ira:ira_password@localhost:5432/ira_db")


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class ProcedureStep:
    """A single step in a procedure."""
    order: int
    action: str
    description: str
    required: bool = True
    parameters: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "order": self.order,
            "action": self.action,
            "description": self.description,
            "required": self.required,
            "parameters": self.parameters,
        }
    
    @classmethod
    def from_dict(cls, d: Dict) -> "ProcedureStep":
        return cls(
            order=d.get("order", 0),
            action=d.get("action", ""),
            description=d.get("description", ""),
            required=d.get("required", True),
            parameters=d.get("parameters", {}),
        )


@dataclass
class Procedure:
    """
    A learned procedure/workflow.
    
    Procedures are named sequences of steps that accomplish a task.
    """
    id: str
    name: str
    trigger_patterns: List[str]  # Patterns that activate this procedure
    steps: List[ProcedureStep]
    description: str = ""
    success_count: int = 0
    failure_count: int = 0
    confidence: float = 0.5
    last_used: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)
    source: str = "learned"  # "learned", "taught", "default"
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "trigger_patterns": self.trigger_patterns,
            "steps": [s.to_dict() for s in self.steps],
            "description": self.description,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "confidence": self.confidence,
            "last_used": self.last_used.isoformat() if self.last_used else None,
            "created_at": self.created_at.isoformat(),
            "source": self.source,
            "tags": self.tags,
        }
    
    @classmethod
    def from_dict(cls, d: Dict) -> "Procedure":
        return cls(
            id=d.get("id", ""),
            name=d.get("name", ""),
            trigger_patterns=d.get("trigger_patterns", []),
            steps=[ProcedureStep.from_dict(s) for s in d.get("steps", [])],
            description=d.get("description", ""),
            success_count=d.get("success_count", 0),
            failure_count=d.get("failure_count", 0),
            confidence=d.get("confidence", 0.5),
            last_used=datetime.fromisoformat(d["last_used"]) if d.get("last_used") else None,
            created_at=datetime.fromisoformat(d["created_at"]) if d.get("created_at") else datetime.now(),
            source=d.get("source", "learned"),
            tags=d.get("tags", []),
        )
    
    def update_success(self):
        """Record successful use of this procedure."""
        self.success_count += 1
        self.last_used = datetime.now()
        total = self.success_count + self.failure_count
        self.confidence = self.success_count / total if total > 0 else 0.5
    
    def update_failure(self):
        """Record failed use of this procedure."""
        self.failure_count += 1
        self.last_used = datetime.now()
        total = self.success_count + self.failure_count
        self.confidence = self.success_count / total if total > 0 else 0.5


# =============================================================================
# SCHEMA
# =============================================================================

PROCEDURAL_MEMORY_SCHEMA = """
CREATE TABLE IF NOT EXISTS ira_memory.procedures (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    trigger_patterns JSONB NOT NULL DEFAULT '[]',
    steps JSONB NOT NULL DEFAULT '[]',
    description TEXT,
    success_count INTEGER DEFAULT 0,
    failure_count INTEGER DEFAULT 0,
    confidence REAL DEFAULT 0.5,
    last_used TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    source TEXT DEFAULT 'learned',
    tags JSONB DEFAULT '[]',
    is_active BOOLEAN DEFAULT TRUE
);

CREATE INDEX IF NOT EXISTS idx_procedures_name ON ira_memory.procedures(name);
CREATE INDEX IF NOT EXISTS idx_procedures_confidence ON ira_memory.procedures(confidence DESC);
CREATE INDEX IF NOT EXISTS idx_procedures_active ON ira_memory.procedures(is_active);
"""


# =============================================================================
# PROCEDURAL MEMORY MANAGER
# =============================================================================

class ProceduralMemory:
    """
    Manages procedural memories - learned skills and workflows.
    
    Key capabilities:
    - Learn procedures from demonstrations
    - Match queries to relevant procedures
    - Execute procedure steps
    - Track success/failure for confidence
    """
    
    # Default procedures (built-in knowledge)
    DEFAULT_PROCEDURES = [
        {
            "name": "generate_quote",
            "trigger_patterns": ["quote for", "pricing for", "how much", "cost of", "price of"],
            "description": "Generate a price quote for a customer",
            "steps": [
                {"order": 1, "action": "identify_product", "description": "Identify the product(s) requested"},
                {"order": 2, "action": "check_pricing", "description": "Look up current pricing"},
                {"order": 3, "action": "check_availability", "description": "Verify inventory/availability"},
                {"order": 4, "action": "format_quote", "description": "Format the quote response"},
            ],
            "tags": ["sales", "pricing"],
        },
        {
            "name": "handle_complaint",
            "trigger_patterns": ["problem with", "issue with", "not working", "broken", "complaint"],
            "description": "Handle a customer complaint",
            "steps": [
                {"order": 1, "action": "acknowledge", "description": "Acknowledge the issue empathetically"},
                {"order": 2, "action": "gather_details", "description": "Ask for specific details"},
                {"order": 3, "action": "check_history", "description": "Check customer history"},
                {"order": 4, "action": "propose_solution", "description": "Propose a resolution"},
            ],
            "tags": ["support", "customer_service"],
        },
        {
            "name": "schedule_followup",
            "trigger_patterns": ["follow up", "remind me", "schedule", "check back"],
            "description": "Schedule a follow-up action",
            "steps": [
                {"order": 1, "action": "confirm_timing", "description": "Confirm when to follow up"},
                {"order": 2, "action": "note_context", "description": "Record what to follow up about"},
                {"order": 3, "action": "set_reminder", "description": "Create the reminder"},
            ],
            "tags": ["workflow", "reminder"],
        },
    ]
    
    def __init__(self):
        self._procedures: Dict[str, Procedure] = {}
        self._schema_ensured = False
        self._load_defaults()
    
    def _load_defaults(self):
        """Load default built-in procedures."""
        for proc_data in self.DEFAULT_PROCEDURES:
            proc_id = hashlib.md5(proc_data["name"].encode()).hexdigest()[:12]
            steps = [ProcedureStep.from_dict(s) for s in proc_data["steps"]]
            proc = Procedure(
                id=proc_id,
                name=proc_data["name"],
                trigger_patterns=proc_data["trigger_patterns"],
                steps=steps,
                description=proc_data["description"],
                source="default",
                tags=proc_data.get("tags", []),
                confidence=0.7,  # Reasonable default confidence
            )
            self._procedures[proc_id] = proc
    
    def _get_db_connection(self):
        """Get PostgreSQL connection."""
        if not DATABASE_URL:
            return None
        try:
            import psycopg2
            import psycopg2.extras
            conn = psycopg2.connect(DATABASE_URL)
            psycopg2.extras.register_uuid()
            return conn
        except Exception as e:
            print(f"[procedural_memory] DB connection error: {e}")
            return None
    
    def ensure_schema(self):
        """Ensure the database schema exists."""
        if self._schema_ensured:
            return
        
        conn = self._get_db_connection()
        if not conn:
            return
        
        try:
            with conn.cursor() as cur:
                cur.execute("CREATE SCHEMA IF NOT EXISTS ira_memory")
                cur.execute(PROCEDURAL_MEMORY_SCHEMA)
                conn.commit()
            self._schema_ensured = True
            self._load_from_db(conn)
        except Exception as e:
            print(f"[procedural_memory] Schema error: {e}")
            conn.rollback()
        finally:
            conn.close()
    
    def _load_from_db(self, conn):
        """Load procedures from database."""
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, name, trigger_patterns, steps, description,
                           success_count, failure_count, confidence,
                           last_used, created_at, source, tags
                    FROM ira_memory.procedures
                    WHERE is_active = TRUE
                """)
                for row in cur.fetchall():
                    proc = Procedure(
                        id=row[0],
                        name=row[1],
                        trigger_patterns=row[2] or [],
                        steps=[ProcedureStep.from_dict(s) for s in (row[3] or [])],
                        description=row[4] or "",
                        success_count=row[5] or 0,
                        failure_count=row[6] or 0,
                        confidence=row[7] or 0.5,
                        last_used=row[8],
                        created_at=row[9] or datetime.now(),
                        source=row[10] or "learned",
                        tags=row[11] or [],
                    )
                    self._procedures[proc.id] = proc
        except Exception as e:
            print(f"[procedural_memory] Load error: {e}")
    
    def teach_procedure(
        self,
        name: str,
        steps: List[Dict],
        trigger_patterns: List[str],
        description: str = "",
        tags: List[str] = None
    ) -> Procedure:
        """
        Teach Ira a new procedure.
        
        Example:
            teach_procedure(
                name="handle_pf1_inquiry",
                steps=[
                    {"action": "check_stock", "description": "Check PF1 stock levels"},
                    {"action": "get_pricing", "description": "Get current PF1 pricing"},
                    {"action": "respond", "description": "Respond with availability and price"},
                ],
                trigger_patterns=["pf1", "thermoforming machine"],
                description="Handle inquiries about PF1 thermoforming machines"
            )
        """
        self.ensure_schema()
        
        proc_id = hashlib.md5(f"{name}_{datetime.now().isoformat()}".encode()).hexdigest()[:12]
        proc_steps = []
        for i, step in enumerate(steps):
            proc_steps.append(ProcedureStep(
                order=i + 1,
                action=step.get("action", f"step_{i+1}"),
                description=step.get("description", ""),
                required=step.get("required", True),
                parameters=step.get("parameters", {}),
            ))
        
        procedure = Procedure(
            id=proc_id,
            name=name,
            trigger_patterns=trigger_patterns,
            steps=proc_steps,
            description=description,
            source="taught",
            tags=tags or [],
            confidence=0.6,  # Start with moderate confidence for taught procedures
        )
        
        self._procedures[proc_id] = procedure
        self._save_procedure(procedure)
        
        return procedure
    
    def _save_procedure(self, procedure: Procedure):
        """Save procedure to database."""
        conn = self._get_db_connection()
        if not conn:
            return
        
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO ira_memory.procedures 
                    (id, name, trigger_patterns, steps, description,
                     success_count, failure_count, confidence,
                     last_used, created_at, source, tags)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE SET
                        trigger_patterns = EXCLUDED.trigger_patterns,
                        steps = EXCLUDED.steps,
                        description = EXCLUDED.description,
                        success_count = EXCLUDED.success_count,
                        failure_count = EXCLUDED.failure_count,
                        confidence = EXCLUDED.confidence,
                        last_used = EXCLUDED.last_used,
                        source = EXCLUDED.source,
                        tags = EXCLUDED.tags
                """, (
                    procedure.id,
                    procedure.name,
                    json.dumps(procedure.trigger_patterns),
                    json.dumps([s.to_dict() for s in procedure.steps]),
                    procedure.description,
                    procedure.success_count,
                    procedure.failure_count,
                    procedure.confidence,
                    procedure.last_used,
                    procedure.created_at,
                    procedure.source,
                    json.dumps(procedure.tags),
                ))
                conn.commit()
        except Exception as e:
            print(f"[procedural_memory] Save error: {e}")
            conn.rollback()
        finally:
            conn.close()
    
    def match_procedure(self, query: str, min_confidence: float = 0.3) -> Optional[Procedure]:
        """
        Find a procedure that matches the query.
        
        Returns the highest-confidence matching procedure.
        """
        self.ensure_schema()
        
        query_lower = query.lower()
        matches = []
        
        for proc in self._procedures.values():
            if proc.confidence < min_confidence:
                continue
            
            # Check trigger patterns
            for pattern in proc.trigger_patterns:
                if pattern.lower() in query_lower:
                    matches.append((proc, proc.confidence))
                    break
        
        if not matches:
            return None
        
        # Return highest confidence match
        matches.sort(key=lambda x: x[1], reverse=True)
        return matches[0][0]
    
    def get_procedure_guidance(self, procedure: Procedure) -> str:
        """
        Format procedure as guidance for the LLM.
        """
        lines = [f"PROCEDURE: {procedure.name}"]
        lines.append(f"Description: {procedure.description}")
        lines.append(f"Confidence: {procedure.confidence:.0%}")
        lines.append("\nSTEPS TO FOLLOW:")
        
        for step in procedure.steps:
            required = "(required)" if step.required else "(optional)"
            lines.append(f"  {step.order}. {step.action}: {step.description} {required}")
        
        return "\n".join(lines)
    
    def record_outcome(self, procedure_id: str, success: bool):
        """Record the outcome of using a procedure."""
        if procedure_id not in self._procedures:
            return
        
        proc = self._procedures[procedure_id]
        if success:
            proc.update_success()
        else:
            proc.update_failure()
        
        self._save_procedure(proc)
        print(f"[procedural_memory] {proc.name}: {'success' if success else 'failure'} (confidence: {proc.confidence:.0%})")
    
    def learn_from_conversation(
        self,
        user_message: str,
        assistant_response: str,
        was_successful: bool,
        extracted_steps: List[str] = None
    ) -> Optional[Procedure]:
        """
        Learn a new procedure from a successful conversation.
        
        This is called when a task is completed successfully.
        If steps can be extracted, creates a new procedure.
        """
        if not was_successful or not extracted_steps:
            return None
        
        # Try to identify what kind of task this was
        task_patterns = [
            (r"quote|pricing|price", "pricing_task"),
            (r"follow.?up|remind", "followup_task"),
            (r"complaint|issue|problem", "support_task"),
            (r"order|purchase|buy", "order_task"),
        ]
        
        task_type = "general_task"
        for pattern, ttype in task_patterns:
            if re.search(pattern, user_message, re.IGNORECASE):
                task_type = ttype
                break
        
        # Create procedure from extracted steps
        proc_name = f"learned_{task_type}_{datetime.now().strftime('%Y%m%d_%H%M')}"
        steps = [
            {"action": f"step_{i+1}", "description": step}
            for i, step in enumerate(extracted_steps)
        ]
        
        # Extract trigger patterns from user message
        words = user_message.lower().split()
        trigger_patterns = [w for w in words if len(w) > 4 and w.isalpha()][:3]
        
        if not trigger_patterns:
            return None
        
        return self.teach_procedure(
            name=proc_name,
            steps=steps,
            trigger_patterns=trigger_patterns,
            description=f"Learned from conversation: {user_message[:50]}...",
            tags=["auto_learned", task_type],
        )
    
    def list_procedures(self, include_defaults: bool = True) -> List[Procedure]:
        """List all procedures."""
        self.ensure_schema()
        
        if include_defaults:
            return list(self._procedures.values())
        else:
            return [p for p in self._procedures.values() if p.source != "default"]
    
    def get_stats(self) -> Dict:
        """Get procedural memory statistics."""
        procedures = list(self._procedures.values())
        return {
            "total": len(procedures),
            "by_source": {
                "default": len([p for p in procedures if p.source == "default"]),
                "taught": len([p for p in procedures if p.source == "taught"]),
                "learned": len([p for p in procedures if p.source == "learned"]),
            },
            "avg_confidence": sum(p.confidence for p in procedures) / len(procedures) if procedures else 0,
            "total_executions": sum(p.success_count + p.failure_count for p in procedures),
        }


# Singleton
_procedural_memory: Optional[ProceduralMemory] = None


def get_procedural_memory() -> ProceduralMemory:
    global _procedural_memory
    if _procedural_memory is None:
        _procedural_memory = ProceduralMemory()
    return _procedural_memory


# =============================================================================
# CLI / TESTING
# =============================================================================

if __name__ == "__main__":
    pm = get_procedural_memory()
    
    print("=" * 60)
    print("PROCEDURAL MEMORY TEST")
    print("=" * 60)
    
    # Test matching
    test_queries = [
        "Can you give me a quote for 5 PF1 machines?",
        "I have a problem with my order",
        "Please follow up with ABC Company next week",
        "What's the weather today?",  # No match
    ]
    
    print("\n📋 Procedure Matching:")
    for query in test_queries:
        proc = pm.match_procedure(query)
        if proc:
            print(f"\n  Query: '{query[:40]}...'")
            print(f"  Match: {proc.name} (confidence: {proc.confidence:.0%})")
            print(f"  Steps: {len(proc.steps)}")
        else:
            print(f"\n  Query: '{query[:40]}...'")
            print(f"  Match: None")
    
    # Test teaching
    print("\n\n📚 Teaching New Procedure:")
    new_proc = pm.teach_procedure(
        name="handle_machine_inquiry",
        steps=[
            {"action": "identify_model", "description": "Identify which machine model"},
            {"action": "check_specs", "description": "Look up specifications"},
            {"action": "provide_info", "description": "Provide detailed information"},
        ],
        trigger_patterns=["machine info", "tell me about", "specs for"],
        description="Handle inquiries about machine specifications"
    )
    print(f"  Created: {new_proc.name}")
    print(f"  ID: {new_proc.id}")
    
    # Test guidance format
    print("\n\n📝 Procedure Guidance Format:")
    proc = pm.match_procedure("give me a quote")
    if proc:
        print(pm.get_procedure_guidance(proc))
    
    # Stats
    print("\n\n📊 Stats:")
    stats = pm.get_stats()
    for k, v in stats.items():
        print(f"  {k}: {v}")
    
    print("\n" + "=" * 60)
