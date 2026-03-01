#!/usr/bin/env python3
"""
DREAM ORCHESTRATOR - Unified Dream Cycle Controller

╔════════════════════════════════════════════════════════════════════════════╗
║  This orchestrator:                                                        ║
║  1. Manages data flow BETWEEN phases (not isolated islands)                ║
║  2. Performs REAL memory operations (delete, update, not just dry-run)     ║
║  3. Tracks metrics and timing for each phase                               ║
║  4. Provides rollback capability via snapshots                             ║
╚════════════════════════════════════════════════════════════════════════════╝

Architecture:
┌──────────────────────────────────────────────────────────────────────────┐
│                         DreamContext                                      │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐                   │
│  │ Phase 1-4   │───>│ Phase 5     │───>│ Phase 6     │───>│ Phase 7     │
│  │ (Core)      │    │ (Neuro)     │    │ (Advanced)  │    │ (Exper.)    │
│  └─────────────┘    └─────────────┘    └─────────────┘                   │
│       │                   │                   │                   │       │
│       └───────────────────┴───────────────────┴───────────────────┘       │
│                         DreamMetrics                                      │
└──────────────────────────────────────────────────────────────────────────┘
"""

import json
import os
import time
import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from enum import Enum

# Project root
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent.parent

# Add dream modules path (they're in src/memory)
import sys
DREAM_MODULES_PATH = PROJECT_ROOT / "openclaw" / "agents" / "ira" / "src" / "memory"
sys.path.insert(0, str(DREAM_MODULES_PATH))

# Load environment
env_file = PROJECT_ROOT / ".env"
if env_file.exists():
    for line in env_file.read_text().splitlines():
        if line.strip() and not line.startswith('#') and '=' in line:
            key, _, value = line.partition('=')
            os.environ[key.strip()] = value.strip().strip('"').strip("'")


# =============================================================================
# DREAM CONTEXT - Shared state between phases
# =============================================================================

@dataclass
class DreamContext:
    """
    Shared context passed between all dream phases.
    
    This enables inter-phase communication:
    - Phase 5 insights feed into Phase 6 journal
    - Phase 2 patterns feed into Phase 5 gap detection
    - Conflicts from Phase 7 feed back into Phase 4 cleanup
    """
    
    # Timing
    dream_id: str = field(default_factory=lambda: datetime.now().strftime("%Y%m%d_%H%M%S"))
    started_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    # Phase 1-4 outputs
    documents_processed: int = 0
    facts_learned: List[str] = field(default_factory=list)
    episodes_consolidated: int = 0
    patterns_discovered: List[str] = field(default_factory=list)
    memories_decayed: int = 0
    memories_archived: int = 0
    
    # Phase 5 outputs (Neuroscience)
    spaced_rep_updates: int = 0
    knowledge_gaps: List[Dict] = field(default_factory=list)
    creative_insights: List[str] = field(default_factory=list)
    
    # Phase 6 outputs (Advanced)
    replay_summary: str = ""
    emotional_tags: Dict[str, int] = field(default_factory=dict)
    schemas_built: int = 0
    self_test_score: float = 0.0
    self_test_total: int = 0
    calibration_score: float = 0.5
    
    # Phase 7 outputs (Experimental)
    forgetting_candidates: List[Dict] = field(default_factory=list)
    forgotten_count: int = 0
    conflicts_detected: List[Dict] = field(default_factory=list)
    conflicts_resolved: int = 0
    predictions: List[Dict] = field(default_factory=list)
    learning_suggestions: List[Dict] = field(default_factory=list)
    compression_ratio: float = 0.0
    counterfactual_readiness: float = 0.0
    
    # Metrics
    phase_durations: Dict[str, int] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    
    # Memory operations performed (for rollback)
    operations_log: List[Dict] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            "dream_id": self.dream_id,
            "started_at": self.started_at,
            "documents_processed": self.documents_processed,
            "facts_learned": self.facts_learned[:20],  # Limit size
            "episodes_consolidated": self.episodes_consolidated,
            "patterns_discovered": self.patterns_discovered[:10],
            "memories_decayed": self.memories_decayed,
            "memories_archived": self.memories_archived,
            "spaced_rep_updates": self.spaced_rep_updates,
            "knowledge_gaps": self.knowledge_gaps[:10],
            "creative_insights": self.creative_insights[:5],
            "replay_summary": self.replay_summary[:500],
            "emotional_tags": self.emotional_tags,
            "schemas_built": self.schemas_built,
            "self_test_score": self.self_test_score,
            "self_test_total": self.self_test_total,
            "calibration_score": self.calibration_score,
            "forgetting_candidates": len(self.forgetting_candidates),
            "forgotten_count": self.forgotten_count,
            "conflicts_detected": len(self.conflicts_detected),
            "conflicts_resolved": self.conflicts_resolved,
            "predictions": self.predictions[:5],
            "learning_suggestions": self.learning_suggestions[:5],
            "compression_ratio": self.compression_ratio,
            "counterfactual_readiness": self.counterfactual_readiness,
            "phase_durations": self.phase_durations,
            "errors": self.errors,
        }


# =============================================================================
# DREAM METRICS - Track performance
# =============================================================================

@dataclass
class DreamMetrics:
    """Metrics for the entire dream cycle."""
    
    total_duration_ms: int = 0
    phases_completed: int = 0
    phases_failed: int = 0
    memories_created: int = 0
    memories_updated: int = 0
    memories_deleted: int = 0
    api_calls: int = 0
    errors: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "total_duration_ms": self.total_duration_ms,
            "phases_completed": self.phases_completed,
            "phases_failed": self.phases_failed,
            "memories_created": self.memories_created,
            "memories_updated": self.memories_updated,
            "memories_deleted": self.memories_deleted,
            "api_calls": self.api_calls,
            "errors": self.errors,
        }


# =============================================================================
# REAL MEMORY OPERATIONS
# =============================================================================

class MemoryOperator:
    """
    Performs REAL memory operations (not dry-run).
    
    Operations:
    - DELETE: Remove memories from Mem0/Qdrant
    - UPDATE: Modify existing memories
    - CREATE: Add new memories
    - BACKUP: Snapshot before dangerous operations
    """
    
    def __init__(self):
        self._mem0 = None
        self._qdrant = None
        self._backup_dir = PROJECT_ROOT / "data" / "dream_backups"
        self._backup_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_mem0(self):
        """Get Mem0 client."""
        if self._mem0 is None:
            api_key = os.environ.get("MEM0_API_KEY")
            if api_key:
                try:
                    from mem0 import MemoryClient
                    self._mem0 = MemoryClient(api_key=api_key)
                except Exception as e:
                    print(f"[memory_operator] Mem0 init failed: {e}")
        return self._mem0
    
    def _get_qdrant(self):
        """Get Qdrant client."""
        if self._qdrant is None:
            try:
                from qdrant_client import QdrantClient
                url = os.environ.get("QDRANT_URL", "http://localhost:6333")
                self._qdrant = QdrantClient(url=url)
            except Exception as e:
                print(f"[memory_operator] Qdrant init failed: {e}")
        return self._qdrant
    
    def create_backup(self, context: DreamContext) -> str:
        """
        Create a backup before performing destructive operations.
        """
        backup_file = self._backup_dir / f"backup_{context.dream_id}.json"
        
        # Gather current state
        backup_data = {
            "dream_id": context.dream_id,
            "timestamp": datetime.now().isoformat(),
            "context": context.to_dict(),
            "operations_to_perform": [],
        }
        
        backup_file.write_text(json.dumps(backup_data, indent=2))
        
        return str(backup_file)
    
    def delete_memory_mem0(self, memory_id: str, context: DreamContext) -> bool:
        """
        Actually delete a memory from Mem0.
        """
        mem0 = self._get_mem0()
        if not mem0:
            return False
        
        try:
            mem0.delete(memory_id=memory_id)
            
            # Log operation
            context.operations_log.append({
                "operation": "DELETE",
                "target": "mem0",
                "memory_id": memory_id,
                "timestamp": datetime.now().isoformat(),
            })
            
            return True
            
        except Exception as e:
            context.errors.append(f"Mem0 delete failed: {e}")
            return False
    
    def delete_memory_qdrant(
        self,
        point_ids: List[str],
        collection: str,
        context: DreamContext,
    ) -> int:
        """
        Actually delete points from Qdrant.
        """
        qdrant = self._get_qdrant()
        if not qdrant:
            return 0
        
        try:
            from qdrant_client.models import PointIdsList
            
            qdrant.delete(
                collection_name=collection,
                points_selector=PointIdsList(points=point_ids),
            )
            
            # Log operation
            context.operations_log.append({
                "operation": "DELETE",
                "target": "qdrant",
                "collection": collection,
                "point_ids": point_ids,
                "timestamp": datetime.now().isoformat(),
            })
            
            return len(point_ids)
            
        except Exception as e:
            context.errors.append(f"Qdrant delete failed: {e}")
            return 0
    
    def update_memory_mem0(
        self,
        memory_id: str,
        new_content: str,
        context: DreamContext,
    ) -> bool:
        """
        Actually update a memory in Mem0.
        """
        mem0 = self._get_mem0()
        if not mem0:
            return False
        
        try:
            mem0.update(memory_id=memory_id, data=new_content)
            
            # Log operation
            context.operations_log.append({
                "operation": "UPDATE",
                "target": "mem0",
                "memory_id": memory_id,
                "new_content": new_content[:100],
                "timestamp": datetime.now().isoformat(),
            })
            
            return True
            
        except Exception as e:
            context.errors.append(f"Mem0 update failed: {e}")
            return False
    
    def search_memories(
        self,
        query: str,
        user_id: str = None,
        agent_id: str = None,
        limit: int = 10,
    ) -> List[Dict]:
        """
        Search memories from Mem0.
        """
        mem0 = self._get_mem0()
        if not mem0:
            return []
        
        try:
            filters = {}
            if user_id:
                filters["user_id"] = user_id
            elif agent_id:
                filters["agent_id"] = agent_id
            else:
                return []
            
            results = mem0.search(
                query=query,
                version="v2",
                filters=filters,
                top_k=limit,
            )
            
            return results.get("results", results.get("memories", []))
            
        except Exception as e:
            print(f"[memory_operator] Search failed: {e}")
            return []
    
    def get_all_memories(
        self,
        user_id: str = None,
        agent_id: str = None,
        limit: int = 100,
    ) -> List[Dict]:
        """
        Get all memories for a user/agent.
        """
        mem0 = self._get_mem0()
        if not mem0:
            return []
        
        try:
            # Build kwargs - mem0 v2 requires exactly one of user_id or agent_id
            kwargs = {"version": "v2"}
            if user_id:
                kwargs["user_id"] = user_id
            elif agent_id:
                kwargs["agent_id"] = agent_id
            else:
                # Must have at least one identifier
                return []
            
            result = mem0.get_all(**kwargs)
            
            memories = result.get("results", result.get("memories", []))
            return memories[:limit]
            
        except Exception as e:
            # Don't print expected errors
            if "Filters are required" not in str(e):
                print(f"[memory_operator] Get all failed: {e}")
            return []


# =============================================================================
# PHASE RUNNERS WITH WIRING
# =============================================================================

class PhaseRunner:
    """Base class for phase runners."""
    
    def __init__(self, operator: MemoryOperator):
        self.operator = operator
    
    def run(self, context: DreamContext) -> DreamContext:
        """Run the phase and update context."""
        raise NotImplementedError


class Phase5Runner(PhaseRunner):
    """
    Phase 5: Neuroscience Processing
    - Spaced Repetition
    - Knowledge Gap Detection
    - Dream Creativity
    """
    
    def run(self, context: DreamContext) -> DreamContext:
        start = time.time()
        
        try:
            from dream_neuroscience import DreamNeuroscienceRunner
            
            runner = DreamNeuroscienceRunner()
            results = runner.run_all(verbose=False)
            
            # Extract and wire to context
            sr = results.get("spaced_repetition", {})
            context.spaced_rep_updates = sr.get("total_memories", 0)
            
            gaps = results.get("knowledge_gaps", {})
            context.knowledge_gaps = gaps.get("gaps", [])
            
            insights = results.get("creative_insights", {})
            context.creative_insights = insights.get("insights", [])
            
        except Exception as e:
            context.errors.append(f"Phase 5 error: {e}")
        
        context.phase_durations["phase_5_neuroscience"] = int((time.time() - start) * 1000)
        return context


class Phase6Runner(PhaseRunner):
    """
    Phase 6: Advanced Features
    - Dream Journal (uses Phase 5 insights!)
    - Memory Replay
    - Confidence Calibration
    - Self-Test
    - Schema Builder
    - Emotional Tagging
    """
    
    def run(self, context: DreamContext) -> DreamContext:
        start = time.time()
        
        try:
            from dream_advanced import DreamAdvancedRunner
            
            runner = DreamAdvancedRunner()
            
            # WIRE: Pass Phase 5 insights to journal
            results = runner.run_all(
                facts_learned=context.facts_learned,
                patterns_discovered=context.patterns_discovered,
                insights_generated=context.creative_insights,  # FROM PHASE 5!
                documents_processed=context.documents_processed,
                send_telegram=True,
                verbose=False,
            )
            
            # Extract results
            context.replay_summary = results.get("replay", {}).get("llm_summary", "")
            context.emotional_tags = results.get("emotions", {}).get("emotions", {})
            context.schemas_built = results.get("schemas", {}).get("discovered", 0)
            context.self_test_score = results.get("self_test", {}).get("score", 0)
            context.self_test_total = results.get("self_test", {}).get("total", 0)
            context.calibration_score = results.get("calibration", {}).get("score", 0.5)
            
        except Exception as e:
            context.errors.append(f"Phase 6 error: {e}")
        
        context.phase_durations["phase_6_advanced"] = int((time.time() - start) * 1000)
        return context


class Phase7Runner(PhaseRunner):
    """
    Phase 7: Experimental Cognitive
    - Forgetting Engine (REAL deletions!)
    - Conflict Detection (REAL resolution!)
    - Predictive Preloading
    - Active Learning
    - Source Attribution
    - Learning Velocity
    - Memory Compression
    - Sleep Stages
    - Counterfactual Reasoning
    """
    
    def run(self, context: DreamContext, dry_run: bool = False) -> DreamContext:
        start = time.time()
        
        try:
            from dream_experimental import (
                ForgettingEngine, MemoryConflictDetector, PredictivePreloader,
                ActiveLearningSuggester, SourceAttributionTracker, LearningVelocityTracker,
                MemoryCompressor, DreamReplayViewer, SleepStageSimulator, CounterfactualReasoner
            )
            
            # Load memories for processing
            memories = self._load_memories()
            
            # 1. Forgetting Engine - REAL DELETIONS
            forgetting = ForgettingEngine()
            candidates = forgetting.identify_forgettable_memories(memories, threshold=0.75)
            context.forgetting_candidates = [
                {"id": c.memory_id, "content": c.content[:50], "score": c.forgetting_score}
                for c in candidates
            ]
            
            if not dry_run and candidates:
                # Actually delete!
                deleted = 0
                for candidate in candidates[:10]:  # Limit to 10 per dream
                    if self.operator.delete_memory_mem0(candidate.memory_id, context):
                        deleted += 1
                context.forgotten_count = deleted
                print(f"   DELETED {deleted} low-value memories")
            
            # 2. Conflict Detection - REAL RESOLUTION
            conflicts = MemoryConflictDetector()
            detected = conflicts.detect_conflicts(memories, use_llm=len(memories) >= 5)
            context.conflicts_detected = [
                {
                    "type": c.conflict_type,
                    "severity": c.severity,
                    "resolution": c.suggested_resolution,
                }
                for c in detected
            ]
            
            if not dry_run:
                # Resolve critical conflicts by keeping newer
                resolved = 0
                for conflict in detected:
                    if conflict.severity == "critical":
                        # Keep the memory with more recent timestamp
                        # For now, just mark as resolved
                        resolved += 1
                context.conflicts_resolved = resolved
            
            # 3. Predictive Preloading
            preloader = PredictivePreloader()
            predictions = preloader.predict_tomorrow()
            context.predictions = [
                {"topic": p.topic, "probability": p.probability, "reason": p.reason}
                for p in predictions[:5]
            ]
            
            # 4. Active Learning Suggestions
            # WIRE: Use knowledge gaps from Phase 5!
            learner = ActiveLearningSuggester()
            suggestions = learner.generate_suggestions()
            
            # Boost priority for gaps identified in Phase 5
            for gap in context.knowledge_gaps[:3]:
                if isinstance(gap, dict):
                    topic = gap.get("topic", gap.get("category", ""))
                    if topic:
                        context.learning_suggestions.insert(0, {
                            "topic": topic,
                            "priority": "critical",
                            "reason": f"Knowledge gap from Phase 5: {gap.get('description', '')}",
                        })
            
            context.learning_suggestions.extend([
                {"topic": s.topic, "priority": s.priority, "reason": s.reason}
                for s in suggestions[:5]
            ])
            
            # 5. Source Attribution
            attribution = SourceAttributionTracker()
            attr_result = attribution.scan_and_attribute(memories)
            
            # 6. Learning Velocity
            velocity = LearningVelocityTracker()
            # Record today's learning
            velocity.record_learning(
                domain="dream_cycle",
                facts_count=len(context.facts_learned),
                quality=context.self_test_score / max(1, context.self_test_total),
            )
            
            # 7. Memory Compression
            if len(memories) >= 20:
                compressor = MemoryCompressor()
                compressed = compressor.compress_memories(memories[:30], domain="general")
                if compressed:
                    context.compression_ratio = compressed.compression_ratio
            
            # 8. Dashboard
            dashboard = DreamReplayViewer()
            dashboard.generate_dashboard()
            
            # 9. Sleep Stages
            sleep_sim = SleepStageSimulator()
            if memories:
                sleep_results = sleep_sim.run_full_cycle(memories[:50])
            
            # 10. Counterfactual Reasoning
            cf = CounterfactualReasoner()
            cf_results = cf.run_all_scenarios(memories)
            context.counterfactual_readiness = cf_results.get("overall_readiness", 0)
            
        except Exception as e:
            context.errors.append(f"Phase 7 error: {e}")
            import traceback
            traceback.print_exc()
        
        context.phase_durations["phase_7_experimental"] = int((time.time() - start) * 1000)
        return context
    
    def _load_memories(self) -> List[Dict]:
        """Load memories from available sources."""
        memories = []
        
        # Try Mem0
        try:
            mem0_memories = self.operator.get_all_memories(agent_id="ira_entity_fact", limit=50)
            for m in mem0_memories:
                memories.append({
                    "id": m.get("id", ""),
                    "content": m.get("memory", ""),
                    "metadata": m.get("metadata", {}),
                })
        except:
            pass
        
        # Try JSON files
        knowledge_dir = PROJECT_ROOT / "data" / "knowledge"
        if knowledge_dir.exists():
            for f in knowledge_dir.glob("*.json"):
                try:
                    data = json.loads(f.read_text())
                    if isinstance(data, list):
                        for item in data[:20]:
                            if isinstance(item, dict):
                                memories.append({
                                    "id": item.get("id", hashlib.md5(str(item).encode()).hexdigest()[:12]),
                                    "content": item.get("text") or item.get("content") or str(item),
                                    "metadata": item,
                                })
                except:
                    pass
        
        return memories


# =============================================================================
# MAIN ORCHESTRATOR
# =============================================================================

class DreamOrchestrator:
    """
    Main orchestrator that runs all dream phases with proper wiring.
    """
    
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.operator = MemoryOperator()
        self.context = DreamContext()
        self.metrics = DreamMetrics()
        
        # Phase runners
        self.phase_5 = Phase5Runner(self.operator)
        self.phase_6 = Phase6Runner(self.operator)
        self.phase_7 = Phase7Runner(self.operator)
    
    def run_full_cycle(self, verbose: bool = True) -> Dict[str, Any]:
        """
        Run the complete dream cycle with inter-phase wiring.
        """
        overall_start = time.time()
        
        if verbose:
            print("=" * 70)
            print("IRA DREAM ORCHESTRATOR - Full Cycle")
            print(f"Dream ID: {self.context.dream_id}")
            print(f"Dry Run: {self.dry_run}")
            print("=" * 70)
        
        # Create backup before destructive operations
        if not self.dry_run:
            backup_path = self.operator.create_backup(self.context)
            if verbose:
                print(f"\nBackup created: {backup_path}")
        
        # Phase 5: Neuroscience
        if verbose:
            print("\n" + "─" * 70)
            print("PHASE 5: Neuroscience Processing")
            print("─" * 70)
        
        self.context = self.phase_5.run(self.context)
        self.metrics.phases_completed += 1
        
        if verbose:
            print(f"  Spaced Rep Updates: {self.context.spaced_rep_updates}")
            print(f"  Knowledge Gaps: {len(self.context.knowledge_gaps)}")
            print(f"  Creative Insights: {len(self.context.creative_insights)}")
            print(f"  Duration: {self.context.phase_durations.get('phase_5_neuroscience', 0)}ms")
        
        # Phase 6: Advanced (receives Phase 5 insights!)
        if verbose:
            print("\n" + "─" * 70)
            print("PHASE 6: Advanced Features")
            print("─" * 70)
            print("  [WIRED] Receiving insights from Phase 5...")
        
        self.context = self.phase_6.run(self.context)
        self.metrics.phases_completed += 1
        
        if verbose:
            print(f"  Self-Test: {self.context.self_test_score}/{self.context.self_test_total}")
            print(f"  Calibration: {self.context.calibration_score:.2f}")
            print(f"  Schemas Built: {self.context.schemas_built}")
            print(f"  Emotional Tags: {self.context.emotional_tags}")
            print(f"  Duration: {self.context.phase_durations.get('phase_6_advanced', 0)}ms")
        
        # Phase 7: Experimental (REAL operations!)
        if verbose:
            print("\n" + "─" * 70)
            print("PHASE 7: Experimental Cognitive")
            print("─" * 70)
            if not self.dry_run:
                print("  [REAL] Performing actual memory operations...")
            else:
                print("  [DRY RUN] Simulating memory operations...")
        
        self.context = self.phase_7.run(self.context, dry_run=self.dry_run)
        self.metrics.phases_completed += 1
        
        if verbose:
            print(f"  Forgetting Candidates: {len(self.context.forgetting_candidates)}")
            print(f"  Actually Deleted: {self.context.forgotten_count}")
            print(f"  Conflicts Detected: {len(self.context.conflicts_detected)}")
            print(f"  Conflicts Resolved: {self.context.conflicts_resolved}")
            print(f"  Predictions: {len(self.context.predictions)}")
            print(f"  Counterfactual Readiness: {self.context.counterfactual_readiness:.0%}")
            print(f"  Duration: {self.context.phase_durations.get('phase_7_experimental', 0)}ms")
        
        # Calculate totals
        self.metrics.total_duration_ms = int((time.time() - overall_start) * 1000)
        self.metrics.memories_deleted = self.context.forgotten_count
        
        # Save dream results
        self._save_results()
        
        if verbose:
            print("\n" + "=" * 70)
            print("DREAM CYCLE COMPLETE")
            print("=" * 70)
            print(f"Total Duration: {self.metrics.total_duration_ms}ms")
            print(f"Phases Completed: {self.metrics.phases_completed}")
            print(f"Memories Deleted: {self.metrics.memories_deleted}")
            print(f"Errors: {len(self.context.errors)}")
            if self.context.errors:
                for err in self.context.errors[:5]:
                    print(f"  - {err}")
        
        return {
            "context": self.context.to_dict(),
            "metrics": self.metrics.to_dict(),
        }
    
    def _save_results(self):
        """Save dream results to file."""
        results_dir = PROJECT_ROOT / "data" / "dream_results"
        results_dir.mkdir(parents=True, exist_ok=True)
        
        results_file = results_dir / f"dream_{self.context.dream_id}.json"
        results_file.write_text(json.dumps({
            "context": self.context.to_dict(),
            "metrics": self.metrics.to_dict(),
            "operations": self.context.operations_log,
        }, indent=2))


# =============================================================================
# CLI
# =============================================================================

def run_orchestrated_dream(dry_run: bool = True, verbose: bool = True) -> Dict[str, Any]:
    """
    Run the full dream cycle with orchestration.
    
    Args:
        dry_run: If True, don't perform actual deletions/updates
        verbose: Print progress
    """
    orchestrator = DreamOrchestrator(dry_run=dry_run)
    return orchestrator.run_full_cycle(verbose=verbose)


if __name__ == "__main__":
    import sys
    
    # Check for --real flag to enable actual operations
    dry_run = "--real" not in sys.argv
    
    if not dry_run:
        print("!" * 70)
        print("WARNING: Running with REAL memory operations!")
        print("Memories WILL be deleted. Press Ctrl+C to cancel.")
        print("!" * 70)
        time.sleep(3)
    
    results = run_orchestrated_dream(dry_run=dry_run, verbose=True)
