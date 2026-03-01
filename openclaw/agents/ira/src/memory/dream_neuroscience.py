#!/usr/bin/env python3
"""
DREAM NEUROSCIENCE - Brain-Inspired Memory Processing

╔════════════════════════════════════════════════════════════════════════════╗
║  Implements neuroscience principles in Ira's dream cycle:                  ║
║                                                                            ║
║  1. SPACED REPETITION DECAY (Ebbinghaus Forgetting Curve)                 ║
║     - Memories decay exponentially: retention = e^(-t/strength)            ║
║     - Each recall increases strength, slowing future decay                 ║
║     - Optimal review intervals calculated per memory                       ║
║                                                                            ║
║  2. KNOWLEDGE GAP DETECTION                                                ║
║     - Track questions answered with low confidence                         ║
║     - Identify topics users ask about that Ira struggles with              ║
║     - Generate "learning priorities" for knowledge acquisition             ║
║                                                                            ║
║  3. DREAM CREATIVITY (REM-like processing)                                 ║
║     - Find semantically distant but potentially related concepts           ║
║     - Use LLM to discover novel connections                                ║
║     - Generate insights that wouldn't emerge from direct retrieval         ║
╚════════════════════════════════════════════════════════════════════════════╝
"""

import json
import math
import os
import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict

# Project root
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent.parent

# Load environment variables (force override to ensure clean values)
env_file = PROJECT_ROOT / ".env"
if env_file.exists():
    for line in env_file.read_text().splitlines():
        if line.strip() and not line.startswith('#') and '=' in line:
            key, _, value = line.partition('=')
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            os.environ[key] = value  # Force set, not setdefault


# =============================================================================
# 1. SPACED REPETITION DECAY (Ebbinghaus Curve)
# =============================================================================

@dataclass
class MemoryStrength:
    """Track memory strength for spaced repetition."""
    memory_id: str
    content: str
    strength: float = 1.0  # Initial strength
    recall_count: int = 0
    last_recall: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)
    
    # Ebbinghaus parameters
    DECAY_CONSTANT: float = 0.5  # How fast memories decay (higher = faster decay)
    STRENGTH_BOOST: float = 1.5  # How much each recall boosts strength
    MIN_RETENTION: float = 0.1  # Minimum retention threshold
    
    def calculate_retention(self, at_time: Optional[datetime] = None) -> float:
        """
        Calculate current retention using Ebbinghaus forgetting curve.
        
        Formula: R = e^(-t/S)
        Where:
            R = retention (0-1)
            t = time since last recall (in days)
            S = memory strength
        """
        at_time = at_time or datetime.now()
        reference_time = self.last_recall or self.created_at
        
        days_elapsed = (at_time - reference_time).total_seconds() / 86400
        
        # Ebbinghaus forgetting curve
        retention = math.exp(-self.DECAY_CONSTANT * days_elapsed / max(self.strength, 0.1))
        
        return max(self.MIN_RETENTION, retention)
    
    def record_recall(self):
        """Record that this memory was recalled (used)."""
        self.recall_count += 1
        self.last_recall = datetime.now()
        
        # Each recall strengthens the memory
        # Diminishing returns: strength grows slower with each recall
        self.strength *= self.STRENGTH_BOOST
        self.strength = min(self.strength, 100.0)  # Cap at 100
    
    def optimal_review_interval(self) -> timedelta:
        """
        Calculate optimal time to review this memory.
        
        Based on when retention would drop to ~70%.
        """
        # Solve for t when R = 0.7: t = -S * ln(0.7) / DECAY_CONSTANT
        target_retention = 0.7
        days = -self.strength * math.log(target_retention) / self.DECAY_CONSTANT
        return timedelta(days=days)


class SpacedRepetitionEngine:
    """
    Manages memory decay using spaced repetition principles.
    """
    
    def __init__(self):
        self._storage_file = PROJECT_ROOT / "data" / "memory_strength.json"
        self._memories: Dict[str, MemoryStrength] = {}
        self._load()
    
    def _load(self):
        """Load memory strengths from disk."""
        if self._storage_file.exists():
            try:
                data = json.loads(self._storage_file.read_text())
                for mid, mdata in data.items():
                    self._memories[mid] = MemoryStrength(
                        memory_id=mid,
                        content=mdata.get("content", ""),
                        strength=mdata.get("strength", 1.0),
                        recall_count=mdata.get("recall_count", 0),
                        last_recall=datetime.fromisoformat(mdata["last_recall"]) if mdata.get("last_recall") else None,
                        created_at=datetime.fromisoformat(mdata.get("created_at", datetime.now().isoformat())),
                    )
            except Exception as e:
                print(f"[spaced_rep] Load error: {e}")
    
    def _save(self):
        """Save memory strengths to disk."""
        self._storage_file.parent.mkdir(parents=True, exist_ok=True)
        data = {}
        for mid, mem in self._memories.items():
            data[mid] = {
                "content": mem.content,
                "strength": mem.strength,
                "recall_count": mem.recall_count,
                "last_recall": mem.last_recall.isoformat() if mem.last_recall else None,
                "created_at": mem.created_at.isoformat(),
            }
        self._storage_file.write_text(json.dumps(data, indent=2))
    
    def register_memory(self, memory_id: str, content: str):
        """Register a new memory for tracking."""
        if memory_id not in self._memories:
            self._memories[memory_id] = MemoryStrength(
                memory_id=memory_id,
                content=content,
            )
            self._save()
    
    def record_recall(self, memory_id: str):
        """Record that a memory was recalled/used."""
        if memory_id in self._memories:
            self._memories[memory_id].record_recall()
            self._save()
    
    def apply_decay(self) -> Dict[str, Any]:
        """
        Apply Ebbinghaus decay to all memories.
        
        Returns stats about the decay process.
        """
        stats = {
            "total_memories": len(self._memories),
            "decayed": 0,
            "strong": 0,
            "weak": 0,
            "critical": 0,  # Below 20% retention
        }
        
        for mid, mem in self._memories.items():
            retention = mem.calculate_retention()
            
            if retention < 0.2:
                stats["critical"] += 1
            elif retention < 0.5:
                stats["weak"] += 1
            else:
                stats["strong"] += 1
            
            stats["decayed"] += 1
        
        self._save()
        return stats
    
    def get_memories_due_for_review(self, limit: int = 10) -> List[MemoryStrength]:
        """Get memories that are due for review (low retention)."""
        memories_with_retention = [
            (mem, mem.calculate_retention())
            for mem in self._memories.values()
        ]
        
        # Sort by retention (lowest first)
        memories_with_retention.sort(key=lambda x: x[1])
        
        return [m for m, r in memories_with_retention[:limit]]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get overall memory strength statistics."""
        if not self._memories:
            return {"total": 0, "avg_retention": 0, "avg_strength": 0}
        
        retentions = [m.calculate_retention() for m in self._memories.values()]
        strengths = [m.strength for m in self._memories.values()]
        
        return {
            "total": len(self._memories),
            "avg_retention": sum(retentions) / len(retentions),
            "avg_strength": sum(strengths) / len(strengths),
            "strong_memories": sum(1 for r in retentions if r > 0.7),
            "weak_memories": sum(1 for r in retentions if r < 0.3),
        }


# =============================================================================
# 2. KNOWLEDGE GAP DETECTION
# =============================================================================

@dataclass
class KnowledgeGap:
    """A detected gap in Ira's knowledge."""
    topic: str
    query_examples: List[str]
    occurrence_count: int
    avg_confidence: float
    first_seen: datetime
    last_seen: datetime
    severity: str  # "critical", "high", "medium", "low"
    suggested_sources: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "topic": self.topic,
            "query_examples": self.query_examples[:5],
            "occurrence_count": self.occurrence_count,
            "avg_confidence": round(self.avg_confidence, 2),
            "first_seen": self.first_seen.isoformat(),
            "last_seen": self.last_seen.isoformat(),
            "severity": self.severity,
            "suggested_sources": self.suggested_sources,
        }


class KnowledgeGapDetector:
    """
    Detect and track knowledge gaps - topics Ira struggles with.
    """
    
    def __init__(self):
        self._gaps_file = PROJECT_ROOT / "data" / "knowledge_gaps.json"
        self._interactions_file = PROJECT_ROOT / "data" / "low_confidence_interactions.json"
        self._gaps: Dict[str, KnowledgeGap] = {}
        self._low_conf_interactions: List[Dict] = []
        self._load()
    
    def _load(self):
        """Load gaps from disk."""
        if self._gaps_file.exists():
            try:
                data = json.loads(self._gaps_file.read_text())
                for topic, gdata in data.items():
                    self._gaps[topic] = KnowledgeGap(
                        topic=topic,
                        query_examples=gdata.get("query_examples", []),
                        occurrence_count=gdata.get("occurrence_count", 0),
                        avg_confidence=gdata.get("avg_confidence", 0),
                        first_seen=datetime.fromisoformat(gdata.get("first_seen", datetime.now().isoformat())),
                        last_seen=datetime.fromisoformat(gdata.get("last_seen", datetime.now().isoformat())),
                        severity=gdata.get("severity", "medium"),
                        suggested_sources=gdata.get("suggested_sources", []),
                    )
            except Exception as e:
                print(f"[gap_detector] Load error: {e}")
        
        if self._interactions_file.exists():
            try:
                self._low_conf_interactions = json.loads(self._interactions_file.read_text())
            except:
                self._low_conf_interactions = []
    
    def _save(self):
        """Save gaps to disk."""
        self._gaps_file.parent.mkdir(parents=True, exist_ok=True)
        data = {topic: gap.to_dict() for topic, gap in self._gaps.items()}
        self._gaps_file.write_text(json.dumps(data, indent=2))
    
    def record_low_confidence_response(
        self,
        query: str,
        response: str,
        confidence: float,
        topics: List[str],
    ):
        """Record an interaction where Ira had low confidence."""
        interaction = {
            "query": query,
            "response": response[:200],
            "confidence": confidence,
            "topics": topics,
            "timestamp": datetime.now().isoformat(),
        }
        self._low_conf_interactions.append(interaction)
        
        # Keep last 500 interactions
        self._low_conf_interactions = self._low_conf_interactions[-500:]
        
        # Save interactions
        self._interactions_file.parent.mkdir(parents=True, exist_ok=True)
        self._interactions_file.write_text(json.dumps(self._low_conf_interactions, indent=2))
    
    def analyze_gaps(self) -> List[KnowledgeGap]:
        """
        Analyze low-confidence interactions to detect knowledge gaps.
        """
        # Group by topics
        topic_stats = defaultdict(lambda: {
            "queries": [],
            "confidences": [],
            "first_seen": datetime.now(),
            "last_seen": datetime.now(),
        })
        
        for interaction in self._low_conf_interactions:
            conf = interaction.get("confidence", 1.0)
            if conf >= 0.7:  # Only care about low confidence
                continue
            
            topics = interaction.get("topics", [])
            if not topics:
                # Extract topic from query
                topics = [self._extract_topic(interaction.get("query", ""))]
            
            for topic in topics:
                if not topic:
                    continue
                topic_lower = topic.lower()
                stats = topic_stats[topic_lower]
                stats["queries"].append(interaction.get("query", ""))
                stats["confidences"].append(conf)
                
                ts = datetime.fromisoformat(interaction.get("timestamp", datetime.now().isoformat()))
                if ts < stats["first_seen"]:
                    stats["first_seen"] = ts
                if ts > stats["last_seen"]:
                    stats["last_seen"] = ts
        
        # Create/update gaps
        gaps = []
        for topic, stats in topic_stats.items():
            if len(stats["queries"]) < 2:  # Need at least 2 occurrences
                continue
            
            avg_conf = sum(stats["confidences"]) / len(stats["confidences"])
            count = len(stats["queries"])
            
            # Determine severity
            if avg_conf < 0.3 and count >= 5:
                severity = "critical"
            elif avg_conf < 0.4 and count >= 3:
                severity = "high"
            elif avg_conf < 0.5:
                severity = "medium"
            else:
                severity = "low"
            
            gap = KnowledgeGap(
                topic=topic,
                query_examples=stats["queries"][:5],
                occurrence_count=count,
                avg_confidence=avg_conf,
                first_seen=stats["first_seen"],
                last_seen=stats["last_seen"],
                severity=severity,
                suggested_sources=self._suggest_sources(topic),
            )
            
            self._gaps[topic] = gap
            gaps.append(gap)
        
        self._save()
        
        # Sort by severity
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        gaps.sort(key=lambda g: (severity_order.get(g.severity, 4), -g.occurrence_count))
        
        return gaps
    
    def _extract_topic(self, query: str) -> str:
        """Extract main topic from a query."""
        # Simple extraction - take first noun phrase
        stop_words = {"what", "how", "when", "where", "why", "is", "are", "the", "a", "an", "do", "does", "can", "could", "would", "should"}
        words = query.lower().replace("?", "").replace(".", "").split()
        meaningful = [w for w in words if w not in stop_words and len(w) > 2]
        return " ".join(meaningful[:3]) if meaningful else ""
    
    def _suggest_sources(self, topic: str) -> List[str]:
        """Suggest where to learn about a topic."""
        suggestions = []
        
        topic_lower = topic.lower()
        
        if any(w in topic_lower for w in ["price", "cost", "quote", "pricing"]):
            suggestions.append("Check pricing spreadsheets in data/pricing/")
            suggestions.append("Review recent quotes in CRM")
        
        if any(w in topic_lower for w in ["machine", "pf1", "thermoform", "spec"]):
            suggestions.append("Check machine manuals in data/documents/")
            suggestions.append("Review FRIMO technical specs")
        
        if any(w in topic_lower for w in ["customer", "company", "contact"]):
            suggestions.append("Check CRM database")
            suggestions.append("Review email history")
        
        if not suggestions:
            suggestions.append("Search company documents")
            suggestions.append("Ask Rushabh for clarification")
        
        return suggestions
    
    def get_priority_gaps(self, limit: int = 5) -> List[KnowledgeGap]:
        """Get the highest priority knowledge gaps."""
        self.analyze_gaps()
        
        gaps = list(self._gaps.values())
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        gaps.sort(key=lambda g: (severity_order.get(g.severity, 4), -g.occurrence_count))
        
        return gaps[:limit]
    
    def generate_learning_report(self) -> str:
        """Generate a report of knowledge gaps for review."""
        gaps = self.get_priority_gaps(10)
        
        if not gaps:
            return "No significant knowledge gaps detected."
        
        lines = ["📚 KNOWLEDGE GAP REPORT", "=" * 40, ""]
        
        for gap in gaps:
            emoji = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}.get(gap.severity, "⚪")
            lines.append(f"{emoji} [{gap.severity.upper()}] {gap.topic}")
            lines.append(f"   Occurrences: {gap.occurrence_count}, Avg confidence: {gap.avg_confidence:.0%}")
            lines.append(f"   Example: \"{gap.query_examples[0][:60]}...\"" if gap.query_examples else "")
            lines.append(f"   Suggested: {gap.suggested_sources[0]}" if gap.suggested_sources else "")
            lines.append("")
        
        return "\n".join(lines)


# =============================================================================
# 3. DREAM CREATIVITY (REM-like Novel Connections)
# =============================================================================

@dataclass
class CreativeInsight:
    """A novel connection discovered during dream creativity."""
    concept_a: str
    concept_b: str
    connection: str
    insight: str
    confidence: float
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict:
        return {
            "concept_a": self.concept_a,
            "concept_b": self.concept_b,
            "connection": self.connection,
            "insight": self.insight,
            "confidence": self.confidence,
            "created_at": self.created_at.isoformat(),
        }


class DreamCreativity:
    """
    REM-like creative processing - finding novel connections between distant concepts.
    
    Like dreams that mix unrelated experiences to generate insights.
    """
    
    def __init__(self):
        self._insights_file = PROJECT_ROOT / "data" / "creative_insights.json"
        self._insights: List[CreativeInsight] = []
        self._openai = None
        self._load()
    
    def _load(self):
        """Load previous insights."""
        if self._insights_file.exists():
            try:
                data = json.loads(self._insights_file.read_text())
                for idata in data:
                    self._insights.append(CreativeInsight(
                        concept_a=idata.get("concept_a", ""),
                        concept_b=idata.get("concept_b", ""),
                        connection=idata.get("connection", ""),
                        insight=idata.get("insight", ""),
                        confidence=idata.get("confidence", 0.5),
                        created_at=datetime.fromisoformat(idata.get("created_at", datetime.now().isoformat())),
                    ))
            except Exception as e:
                print(f"[dream_creativity] Load error: {e}")
    
    def _save(self):
        """Save insights to disk."""
        self._insights_file.parent.mkdir(parents=True, exist_ok=True)
        data = [i.to_dict() for i in self._insights[-100:]]  # Keep last 100
        self._insights_file.write_text(json.dumps(data, indent=2))
    
    def _get_openai(self):
        """Get OpenAI client."""
        if self._openai is None:
            from openai import OpenAI
            # Use default env var (OPENAI_API_KEY) - OpenAI lib handles this
            self._openai = OpenAI()
        return self._openai
    
    def _get_diverse_concepts(self, count: int = 10) -> List[Tuple[str, str]]:
        """
        Get pairs of semantically distant concepts from Ira's knowledge.
        """
        # Load various knowledge sources
        concepts_by_domain = defaultdict(list)
        
        # Machine concepts
        concepts_by_domain["machines"].extend([
            "PF1 thermoforming machine",
            "vacuum forming process",
            "heating zones",
            "forming pressure",
            "cycle time optimization",
        ])
        
        # Customer concepts
        concepts_by_domain["customers"].extend([
            "customer retention",
            "quote follow-up",
            "delivery timeline",
            "payment terms",
        ])
        
        # Business concepts
        concepts_by_domain["business"].extend([
            "market expansion",
            "competitive advantage",
            "pricing strategy",
            "European regulations",
        ])
        
        # Technical concepts
        concepts_by_domain["technical"].extend([
            "material thickness",
            "mold design",
            "automation integration",
            "quality control",
        ])
        
        # Load from knowledge files if available
        knowledge_dir = PROJECT_ROOT / "data" / "knowledge"
        if knowledge_dir.exists():
            for f in knowledge_dir.glob("*.json"):
                try:
                    data = json.loads(f.read_text())
                    if isinstance(data, list):
                        for item in data[:10]:
                            if isinstance(item, dict) and "entity" in item:
                                concepts_by_domain["entities"].append(item["entity"])
                except:
                    pass
        
        # Generate cross-domain pairs (most creative)
        pairs = []
        domains = list(concepts_by_domain.keys())
        
        for _ in range(count):
            # Pick two different domains
            domain_a, domain_b = random.sample(domains, 2)
            concept_a = random.choice(concepts_by_domain[domain_a])
            concept_b = random.choice(concepts_by_domain[domain_b])
            pairs.append((concept_a, concept_b))
        
        return pairs
    
    def generate_insights(self, count: int = 5) -> List[CreativeInsight]:
        """
        Generate creative insights by finding connections between distant concepts.
        """
        pairs = self._get_diverse_concepts(count * 2)  # Get more pairs, filter later
        new_insights = []
        
        client = self._get_openai()
        
        for concept_a, concept_b in pairs[:count]:
            try:
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {
                            "role": "system",
                            "content": """You are a creative insight generator for a B2B sales AI assistant for Machinecraft (thermoforming machines).

Your job is to find NON-OBVIOUS but USEFUL connections between two concepts.

Rules:
1. The connection must be actionable for sales/customer success
2. Avoid obvious connections - find surprising links
3. Be specific to the thermoforming/manufacturing domain
4. Rate your confidence (0-1) in the insight's usefulness

Respond in JSON:
{
    "connection": "How these concepts relate (1 sentence)",
    "insight": "The actionable insight for Ira (2-3 sentences)",
    "confidence": 0.7
}"""
                        },
                        {
                            "role": "user",
                            "content": f"Find a creative connection between:\nConcept A: {concept_a}\nConcept B: {concept_b}"
                        }
                    ],
                    temperature=0.9,  # Higher temperature for creativity
                    max_tokens=300,
                )
                
                result_text = response.choices[0].message.content
                
                # Parse JSON
                import re
                json_match = re.search(r'\{[^}]+\}', result_text, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group())
                    
                    insight = CreativeInsight(
                        concept_a=concept_a,
                        concept_b=concept_b,
                        connection=result.get("connection", ""),
                        insight=result.get("insight", ""),
                        confidence=result.get("confidence", 0.5),
                    )
                    
                    if insight.confidence >= 0.5:  # Only keep confident insights
                        new_insights.append(insight)
                        self._insights.append(insight)
                
            except Exception as e:
                print(f"[dream_creativity] Error generating insight: {e}")
                continue
        
        self._save()
        
        print(f"[dream_creativity] Generated {len(new_insights)} creative insights")
        return new_insights
    
    def get_recent_insights(self, days: int = 7) -> List[CreativeInsight]:
        """Get insights from the last N days."""
        cutoff = datetime.now() - timedelta(days=days)
        return [i for i in self._insights if i.created_at > cutoff]
    
    def format_insights_report(self, insights: List[CreativeInsight] = None) -> str:
        """Format insights for display."""
        insights = insights or self.get_recent_insights()
        
        if not insights:
            return "No creative insights generated yet."
        
        lines = ["💡 CREATIVE INSIGHTS (Dream Mode)", "=" * 40, ""]
        
        for i, insight in enumerate(insights[:10], 1):
            lines.append(f"{i}. {insight.concept_a} ↔ {insight.concept_b}")
            lines.append(f"   Connection: {insight.connection}")
            lines.append(f"   Insight: {insight.insight}")
            lines.append(f"   Confidence: {insight.confidence:.0%}")
            lines.append("")
        
        return "\n".join(lines)


# =============================================================================
# UNIFIED DREAM NEUROSCIENCE RUNNER
# =============================================================================

class DreamNeuroscienceRunner:
    """
    Run all neuroscience-inspired dream processes.
    """
    
    def __init__(self):
        self.spaced_rep = SpacedRepetitionEngine()
        self.gap_detector = KnowledgeGapDetector()
        self.creativity = DreamCreativity()
    
    def run_all(self, verbose: bool = True) -> Dict[str, Any]:
        """
        Run all neuroscience dream phases.
        """
        results = {
            "spaced_repetition": {},
            "knowledge_gaps": {},
            "creative_insights": {},
            "timestamp": datetime.now().isoformat(),
        }
        
        # 1. Spaced Repetition Decay
        if verbose:
            print("\n🧠 Phase N1: Spaced Repetition Decay...")
        decay_stats = self.spaced_rep.apply_decay()
        results["spaced_repetition"] = decay_stats
        if verbose:
            print(f"   Memories: {decay_stats.get('total_memories', 0)}")
            print(f"   Strong (>70%): {decay_stats.get('strong', 0)}")
            print(f"   Weak (<50%): {decay_stats.get('weak', 0)}")
            print(f"   Critical (<20%): {decay_stats.get('critical', 0)}")
        
        # 2. Knowledge Gap Detection
        if verbose:
            print("\n🔍 Phase N2: Knowledge Gap Detection...")
        gaps = self.gap_detector.analyze_gaps()
        results["knowledge_gaps"] = {
            "total_gaps": len(gaps),
            "critical": sum(1 for g in gaps if g.severity == "critical"),
            "high": sum(1 for g in gaps if g.severity == "high"),
            "top_gaps": [g.topic for g in gaps[:5]],
        }
        if verbose:
            print(f"   Total gaps: {len(gaps)}")
            print(f"   Critical: {results['knowledge_gaps']['critical']}")
            print(f"   High: {results['knowledge_gaps']['high']}")
            if gaps:
                print(f"   Top gap: {gaps[0].topic}")
        
        # 3. Dream Creativity
        if verbose:
            print("\n💡 Phase N3: Dream Creativity...")
        insights = self.creativity.generate_insights(count=3)
        results["creative_insights"] = {
            "generated": len(insights),
            "insights": [i.to_dict() for i in insights],
        }
        if verbose:
            print(f"   Insights generated: {len(insights)}")
            for insight in insights:
                print(f"   • {insight.concept_a} ↔ {insight.concept_b}")
        
        return results


# =============================================================================
# CLI
# =============================================================================

def run_neuroscience_dream(verbose: bool = True) -> Dict[str, Any]:
    """Convenience function to run all neuroscience dream phases."""
    runner = DreamNeuroscienceRunner()
    return runner.run_all(verbose=verbose)


if __name__ == "__main__":
    print("=" * 60)
    print("DREAM NEUROSCIENCE - Running all phases")
    print("=" * 60)
    
    results = run_neuroscience_dream(verbose=True)
    
    print("\n" + "=" * 60)
    print("COMPLETE")
    print("=" * 60)
