#!/usr/bin/env python3
"""
DREAM EXPERIMENTAL - Advanced Cognitive Features

╔════════════════════════════════════════════════════════════════════════════╗
║  Experimental neuroscience-inspired features for Ira's dream cycle:        ║
║                                                                            ║
║  HIGH IMPACT:                                                              ║
║  1. FORGETTING ENGINE - Prune low-value memories to reduce noise           ║
║  2. MEMORY CONFLICT DETECTION - Detect contradictions in knowledge         ║
║  3. PREDICTIVE PRELOADING - Predict what info is needed tomorrow           ║
║  4. ACTIVE LEARNING SUGGESTIONS - Identify valuable info to learn          ║
║                                                                            ║
║  MEDIUM IMPACT:                                                            ║
║  5. SOURCE ATTRIBUTION - Track where each fact came from                   ║
║  6. LEARNING VELOCITY - Track learning speed by domain                     ║
║  7. MEMORY COMPRESSION - Compress old memories into abstractions           ║
║  8. DREAM REPLAY VIEWER - Web dashboard for dream visualization            ║
║                                                                            ║
║  EXPERIMENTAL:                                                             ║
║  9. SLEEP STAGES - Mimic brain sleep stages (light/deep/REM)               ║
║  10. COUNTERFACTUAL REASONING - Stress test knowledge with "what ifs"      ║
╚════════════════════════════════════════════════════════════════════════════╝
"""

import json
import os
import hashlib
import math
import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Set
from collections import defaultdict
from enum import Enum

# Project root
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent.parent

# Load environment
env_file = PROJECT_ROOT / ".env"
if env_file.exists():
    for line in env_file.read_text().splitlines():
        if line.strip() and not line.startswith('#') and '=' in line:
            key, _, value = line.partition('=')
            os.environ[key.strip()] = value.strip().strip('"').strip("'")


# =============================================================================
# 1. FORGETTING ENGINE - Intentional memory pruning
# =============================================================================

@dataclass
class MemoryCandidate:
    """A memory candidate for forgetting."""
    memory_id: str
    content: str
    last_accessed: str
    access_count: int
    importance_score: float
    forgetting_score: float  # Higher = more likely to forget


class ForgettingEngine:
    """
    Intentionally forgets low-value memories to:
    - Reduce noise in retrieval
    - Speed up search
    - Free up storage
    - Prevent information overload
    
    Based on Ebbinghaus forgetting curve + utility scoring.
    """
    
    def __init__(self):
        self._forgotten_file = PROJECT_ROOT / "data" / "forgotten_memories.json"
        self._forgotten: List[Dict] = []
        self._load()
    
    def _load(self):
        """Load forgotten memories log."""
        if self._forgotten_file.exists():
            try:
                self._forgotten = json.loads(self._forgotten_file.read_text())
            except:
                self._forgotten = []
    
    def _save(self):
        """Save forgotten memories log."""
        self._forgotten_file.parent.mkdir(parents=True, exist_ok=True)
        # Keep last 1000 entries
        self._forgotten_file.write_text(json.dumps(self._forgotten[-1000:], indent=2))
    
    def calculate_forgetting_score(
        self,
        content: str,
        last_accessed: datetime,
        access_count: int,
        importance: float = 0.5,
    ) -> float:
        """
        Calculate forgetting score (0-1). Higher = more forgettable.
        
        Factors:
        - Time since last access (older = more forgettable)
        - Access frequency (less accessed = more forgettable)
        - Importance score (less important = more forgettable)
        - Content specificity (too specific = more forgettable)
        """
        now = datetime.now()
        days_since_access = (now - last_accessed).days
        
        # Time decay factor (sigmoid curve)
        time_factor = 1 / (1 + math.exp(-0.1 * (days_since_access - 30)))
        
        # Access frequency factor (log scale)
        freq_factor = 1 / (1 + math.log(1 + access_count))
        
        # Importance inverse
        importance_factor = 1 - importance
        
        # Content specificity (very short or very long = more forgettable)
        content_len = len(content)
        if content_len < 20:
            specificity_factor = 0.8  # Too short, probably noise
        elif content_len > 500:
            specificity_factor = 0.6  # Too long, should be compressed
        else:
            specificity_factor = 0.3  # Good length
        
        # Weighted combination
        score = (
            0.35 * time_factor +
            0.25 * freq_factor +
            0.30 * importance_factor +
            0.10 * specificity_factor
        )
        
        return min(1.0, max(0.0, score))
    
    def identify_forgettable_memories(
        self,
        memories: List[Dict],
        threshold: float = 0.7,
        max_forget: int = 100,
    ) -> List[MemoryCandidate]:
        """
        Identify memories that should be forgotten.
        """
        candidates = []
        
        for mem in memories:
            content = mem.get("content") or mem.get("text") or mem.get("memory", "")
            last_accessed_str = mem.get("last_accessed") or mem.get("updated_at") or mem.get("created_at", "")
            
            try:
                if last_accessed_str:
                    last_accessed = datetime.fromisoformat(last_accessed_str.replace("Z", ""))
                else:
                    last_accessed = datetime.now() - timedelta(days=60)
            except:
                last_accessed = datetime.now() - timedelta(days=60)
            
            access_count = mem.get("access_count", 1)
            importance = mem.get("importance", 0.5)
            
            forgetting_score = self.calculate_forgetting_score(
                content, last_accessed, access_count, importance
            )
            
            if forgetting_score >= threshold:
                candidates.append(MemoryCandidate(
                    memory_id=mem.get("id", hashlib.md5(content.encode()).hexdigest()[:12]),
                    content=content[:200],
                    last_accessed=last_accessed.isoformat(),
                    access_count=access_count,
                    importance_score=importance,
                    forgetting_score=forgetting_score,
                ))
        
        # Sort by forgetting score (most forgettable first)
        candidates.sort(key=lambda x: x.forgetting_score, reverse=True)
        
        return candidates[:max_forget]
    
    def forget_memories(
        self,
        candidates: List[MemoryCandidate],
        dry_run: bool = True,
    ) -> Dict[str, Any]:
        """
        Actually forget (archive/delete) memories.
        """
        forgotten = []
        
        for candidate in candidates:
            if not dry_run:
                # In production, would delete from mem0/qdrant
                # For now, just log
                pass
            
            forgotten.append({
                "memory_id": candidate.memory_id,
                "content_snippet": candidate.content[:100],
                "forgetting_score": candidate.forgetting_score,
                "forgotten_at": datetime.now().isoformat(),
            })
        
        self._forgotten.extend(forgotten)
        self._save()
        
        return {
            "candidates_found": len(candidates),
            "forgotten": len(forgotten) if not dry_run else 0,
            "dry_run": dry_run,
            "top_forgettable": [
                {"content": c.content[:50], "score": c.forgetting_score}
                for c in candidates[:5]
            ],
        }


# =============================================================================
# 2. MEMORY CONFLICT DETECTION - Find contradictions
# =============================================================================

@dataclass
class MemoryConflict:
    """A detected conflict between memories."""
    memory_1_id: str
    memory_1_content: str
    memory_2_id: str
    memory_2_content: str
    conflict_type: str  # "price", "spec", "date", "capability", "other"
    severity: str  # "critical", "moderate", "minor"
    suggested_resolution: str
    detected_at: str


class MemoryConflictDetector:
    """
    Detects contradictions in Ira's knowledge.
    
    Examples:
    - "PF1 costs $100,000" vs "PF1 costs $150,000"
    - "Delivery is 8 weeks" vs "Delivery is 12 weeks"
    - "Machine can do X" vs "Machine cannot do X"
    """
    
    def __init__(self):
        self._conflicts_file = PROJECT_ROOT / "data" / "memory_conflicts.json"
        self._conflicts: List[MemoryConflict] = []
        self._openai = None
        self._load()
    
    def _get_openai(self):
        if self._openai is None:
            from openai import OpenAI
            self._openai = OpenAI()
        return self._openai
    
    def _load(self):
        """Load detected conflicts."""
        if self._conflicts_file.exists():
            try:
                data = json.loads(self._conflicts_file.read_text())
                for c in data:
                    self._conflicts.append(MemoryConflict(**c))
            except:
                pass
    
    def _save(self):
        """Save detected conflicts."""
        self._conflicts_file.parent.mkdir(parents=True, exist_ok=True)
        data = [
            {
                "memory_1_id": c.memory_1_id,
                "memory_1_content": c.memory_1_content,
                "memory_2_id": c.memory_2_id,
                "memory_2_content": c.memory_2_content,
                "conflict_type": c.conflict_type,
                "severity": c.severity,
                "suggested_resolution": c.suggested_resolution,
                "detected_at": c.detected_at,
            }
            for c in self._conflicts[-100:]
        ]
        self._conflicts_file.write_text(json.dumps(data, indent=2))
    
    def _extract_entities(self, text: str) -> Set[str]:
        """Extract entities/keywords from text."""
        # Simple extraction - could be enhanced with NER
        words = text.lower().split()
        
        # Look for product names, numbers, units
        entities = set()
        for word in words:
            # Product patterns
            if any(p in word for p in ["pf1", "pf2", "img", "fcs", "am-"]):
                entities.add(word)
            # Numbers with units
            if any(c.isdigit() for c in word):
                entities.add(word)
        
        return entities
    
    def _check_numeric_conflict(self, text1: str, text2: str) -> Optional[Tuple[str, str]]:
        """Check if two texts have conflicting numbers for same entity."""
        import re
        
        # Extract numbers with context
        pattern = r'(\d+(?:,\d+)?(?:\.\d+)?)\s*(usd|eur|euro|\$|€|weeks?|days?|mm|cm|m|kg|kw|hp)?'
        
        nums1 = re.findall(pattern, text1.lower())
        nums2 = re.findall(pattern, text2.lower())
        
        for n1, u1 in nums1:
            for n2, u2 in nums2:
                # Same unit but different value
                if u1 and u1 == u2:
                    v1 = float(n1.replace(",", ""))
                    v2 = float(n2.replace(",", ""))
                    if abs(v1 - v2) / max(v1, v2, 1) > 0.1:  # >10% difference
                        return (f"{n1} {u1}", f"{n2} {u2}")
        
        return None
    
    def detect_conflicts(
        self,
        memories: List[Dict],
        use_llm: bool = True,
    ) -> List[MemoryConflict]:
        """
        Detect conflicts between memories.
        """
        new_conflicts = []
        
        # Group memories by entity
        entity_memories = defaultdict(list)
        for mem in memories:
            content = mem.get("content") or mem.get("text") or mem.get("memory", "")
            entities = self._extract_entities(content)
            for entity in entities:
                entity_memories[entity].append(mem)
        
        # Check for conflicts within each entity group
        for entity, mems in entity_memories.items():
            if len(mems) < 2:
                continue
            
            # Compare pairs
            for i, mem1 in enumerate(mems[:-1]):
                for mem2 in mems[i+1:]:
                    content1 = mem1.get("content") or mem1.get("text") or mem1.get("memory", "")
                    content2 = mem2.get("content") or mem2.get("text") or mem2.get("memory", "")
                    
                    # Quick numeric check
                    numeric_conflict = self._check_numeric_conflict(content1, content2)
                    
                    if numeric_conflict:
                        conflict = MemoryConflict(
                            memory_1_id=mem1.get("id", "unknown"),
                            memory_1_content=content1[:200],
                            memory_2_id=mem2.get("id", "unknown"),
                            memory_2_content=content2[:200],
                            conflict_type="numeric",
                            severity="critical" if any(w in content1.lower() for w in ["price", "cost"]) else "moderate",
                            suggested_resolution=f"Verify which is correct: {numeric_conflict[0]} vs {numeric_conflict[1]}",
                            detected_at=datetime.now().isoformat(),
                        )
                        new_conflicts.append(conflict)
        
        # Use LLM for deeper conflict detection if enabled
        if use_llm and len(memories) >= 5:
            llm_conflicts = self._detect_conflicts_llm(memories[:50])
            new_conflicts.extend(llm_conflicts)
        
        self._conflicts.extend(new_conflicts)
        self._save()
        
        return new_conflicts
    
    def _detect_conflicts_llm(self, memories: List[Dict]) -> List[MemoryConflict]:
        """Use LLM to detect subtle conflicts."""
        try:
            client = self._get_openai()
            
            # Format memories
            mem_texts = []
            for i, mem in enumerate(memories):
                content = mem.get("content") or mem.get("text") or mem.get("memory", "")
                mem_texts.append(f"{i+1}. {content[:150]}")
            
            response = client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[
                    {
                        "role": "system",
                        "content": """You are checking a knowledge base for contradictions.
Find facts that contradict each other (different prices, specs, capabilities).

Output JSON array of conflicts found:
[{"mem1_idx": 1, "mem2_idx": 5, "type": "price", "description": "Different prices for PF1"}]

If no conflicts, return empty array [].
Only report clear contradictions, not just different topics."""
                    },
                    {
                        "role": "user",
                        "content": f"Check these facts for contradictions:\n\n" + "\n".join(mem_texts)
                    }
                ],
                max_tokens=500,
            )
            
            result_text = response.choices[0].message.content
            
            # Parse JSON
            import re
            json_match = re.search(r'\[.*\]', result_text, re.DOTALL)
            if json_match:
                conflicts_data = json.loads(json_match.group())
                
                llm_conflicts = []
                for c in conflicts_data:
                    idx1 = c.get("mem1_idx", 1) - 1
                    idx2 = c.get("mem2_idx", 2) - 1
                    
                    if 0 <= idx1 < len(memories) and 0 <= idx2 < len(memories):
                        content1 = memories[idx1].get("content") or memories[idx1].get("text", "")
                        content2 = memories[idx2].get("content") or memories[idx2].get("text", "")
                        
                        llm_conflicts.append(MemoryConflict(
                            memory_1_id=memories[idx1].get("id", "unknown"),
                            memory_1_content=content1[:200],
                            memory_2_id=memories[idx2].get("id", "unknown"),
                            memory_2_content=content2[:200],
                            conflict_type=c.get("type", "other"),
                            severity="moderate",
                            suggested_resolution=c.get("description", "Review both facts"),
                            detected_at=datetime.now().isoformat(),
                        ))
                
                return llm_conflicts
                
        except Exception as e:
            print(f"[conflict_detector] LLM error: {e}")
        
        return []
    
    def get_unresolved_conflicts(self) -> List[MemoryConflict]:
        """Get all unresolved conflicts."""
        return self._conflicts


# =============================================================================
# 3. PREDICTIVE PRELOADING - Predict tomorrow's needs
# =============================================================================

@dataclass
class PredictedNeed:
    """A predicted information need."""
    topic: str
    probability: float
    reason: str
    suggested_preload: List[str]


class PredictivePreloader:
    """
    Predicts what information will be needed tomorrow.
    
    Based on:
    - Day of week patterns (Monday = more quotes)
    - Recent conversation trends
    - Seasonal patterns
    - Upcoming events
    """
    
    def __init__(self):
        self._patterns_file = PROJECT_ROOT / "data" / "access_patterns.json"
        self._predictions_file = PROJECT_ROOT / "data" / "predicted_needs.json"
        self._patterns = self._load_patterns()
    
    def _load_patterns(self) -> Dict:
        """Load historical access patterns."""
        if self._patterns_file.exists():
            try:
                return json.loads(self._patterns_file.read_text())
            except:
                pass
        
        # Default patterns based on B2B sales
        return {
            "day_of_week": {
                "monday": ["quotes", "pricing", "new_inquiries"],
                "tuesday": ["specifications", "technical"],
                "wednesday": ["follow_up", "delivery"],
                "thursday": ["specifications", "technical"],
                "friday": ["quotes", "summary", "closing"],
                "saturday": [],
                "sunday": [],
            },
            "topics": {
                "quotes": {"peak_hour": 10, "frequency": 0.3},
                "pricing": {"peak_hour": 11, "frequency": 0.25},
                "specifications": {"peak_hour": 14, "frequency": 0.2},
                "delivery": {"peak_hour": 15, "frequency": 0.15},
                "technical": {"peak_hour": 14, "frequency": 0.1},
            },
        }
    
    def _save_patterns(self):
        """Save access patterns."""
        self._patterns_file.parent.mkdir(parents=True, exist_ok=True)
        self._patterns_file.write_text(json.dumps(self._patterns, indent=2))
    
    def record_access(self, topic: str, timestamp: datetime = None):
        """Record an information access for pattern learning."""
        if timestamp is None:
            timestamp = datetime.now()
        
        day = timestamp.strftime("%A").lower()
        hour = timestamp.hour
        
        # Update patterns
        if "accesses" not in self._patterns:
            self._patterns["accesses"] = []
        
        self._patterns["accesses"].append({
            "topic": topic,
            "day": day,
            "hour": hour,
            "timestamp": timestamp.isoformat(),
        })
        
        # Keep last 1000 accesses
        self._patterns["accesses"] = self._patterns["accesses"][-1000:]
        self._save_patterns()
    
    def predict_tomorrow(self) -> List[PredictedNeed]:
        """
        Predict what information will be needed tomorrow.
        """
        tomorrow = datetime.now() + timedelta(days=1)
        day = tomorrow.strftime("%A").lower()
        
        predictions = []
        
        # Day-of-week based predictions
        day_topics = self._patterns.get("day_of_week", {}).get(day, [])
        for topic in day_topics:
            topic_info = self._patterns.get("topics", {}).get(topic, {})
            
            predictions.append(PredictedNeed(
                topic=topic,
                probability=topic_info.get("frequency", 0.2),
                reason=f"Historically common on {day.capitalize()}s",
                suggested_preload=[
                    f"Latest {topic} information",
                    f"Recent {topic} inquiries",
                ],
            ))
        
        # Analyze recent access patterns
        accesses = self._patterns.get("accesses", [])
        recent = [a for a in accesses if a.get("day") == day]
        
        if recent:
            topic_counts = defaultdict(int)
            for a in recent:
                topic_counts[a.get("topic", "general")] += 1
            
            for topic, count in sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)[:3]:
                if topic not in [p.topic for p in predictions]:
                    predictions.append(PredictedNeed(
                        topic=topic,
                        probability=min(0.8, count / len(recent)),
                        reason=f"Frequently accessed on past {day.capitalize()}s",
                        suggested_preload=[f"Pre-cache {topic} data"],
                    ))
        
        # Sort by probability
        predictions.sort(key=lambda x: x.probability, reverse=True)
        
        # Save predictions
        self._predictions_file.parent.mkdir(parents=True, exist_ok=True)
        self._predictions_file.write_text(json.dumps([
            {
                "topic": p.topic,
                "probability": p.probability,
                "reason": p.reason,
                "suggested_preload": p.suggested_preload,
            }
            for p in predictions
        ], indent=2))
        
        return predictions
    
    def get_preload_suggestions(self) -> List[str]:
        """Get specific items to preload."""
        predictions = self.predict_tomorrow()
        
        suggestions = []
        for pred in predictions[:5]:
            suggestions.extend(pred.suggested_preload)
        
        return suggestions


# =============================================================================
# 4. ACTIVE LEARNING SUGGESTIONS - What to learn next
# =============================================================================

@dataclass
class LearningSuggestion:
    """A suggestion for what to learn next."""
    topic: str
    priority: str  # "critical", "high", "medium", "low"
    reason: str
    suggested_sources: List[str]
    expected_value: float  # Expected value of learning this


class ActiveLearningSuggester:
    """
    Suggests what information would be most valuable to learn.
    
    Based on:
    - Knowledge gaps identified
    - Question patterns from users
    - Confidence weaknesses
    - Business priorities
    """
    
    def __init__(self):
        self._suggestions_file = PROJECT_ROOT / "data" / "learning_suggestions.json"
        self._openai = None
    
    def _get_openai(self):
        if self._openai is None:
            from openai import OpenAI
            self._openai = OpenAI()
        return self._openai
    
    def _analyze_knowledge_gaps(self) -> List[Dict]:
        """Analyze existing knowledge gaps."""
        gaps_file = PROJECT_ROOT / "data" / "knowledge_gaps.json"
        if gaps_file.exists():
            try:
                data = json.loads(gaps_file.read_text())
                # Handle both list and dict formats
                if isinstance(data, list):
                    return data
                elif isinstance(data, dict):
                    return data.get("gaps", [])
            except:
                pass
        return []
    
    def _analyze_question_patterns(self) -> Dict[str, int]:
        """Analyze what users frequently ask about."""
        episodes_file = PROJECT_ROOT / "data" / "mem0_storage" / "episodes.json"
        patterns = defaultdict(int)
        
        if episodes_file.exists():
            try:
                data = json.loads(episodes_file.read_text())
                for identity_id, eps in data.items():
                    for ep_id, ep in eps.items():
                        summary = ep.get("summary", "").lower()
                        
                        # Categorize
                        if "price" in summary or "cost" in summary or "quote" in summary:
                            patterns["pricing"] += 1
                        if "spec" in summary or "feature" in summary:
                            patterns["specifications"] += 1
                        if "delivery" in summary or "lead time" in summary:
                            patterns["delivery"] += 1
                        if "compare" in summary or "vs" in summary or "competitor" in summary:
                            patterns["competitors"] += 1
                        if "install" in summary or "setup" in summary:
                            patterns["installation"] += 1
            except:
                pass
        
        return dict(patterns)
    
    def generate_suggestions(self) -> List[LearningSuggestion]:
        """
        Generate learning suggestions.
        """
        suggestions = []
        
        # From knowledge gaps
        gaps = self._analyze_knowledge_gaps()
        if isinstance(gaps, list):
            for gap in gaps[:5]:
                if isinstance(gap, dict):
                    suggestions.append(LearningSuggestion(
                        topic=gap.get("topic", "Unknown"),
                        priority="high" if gap.get("severity") == "critical" else "medium",
                        reason=f"Knowledge gap: {gap.get('description', 'Missing information')}",
                        suggested_sources=["Internal documentation", "Product team"],
                        expected_value=0.8 if gap.get("severity") == "critical" else 0.5,
                    ))
        
        # From question patterns
        patterns = self._analyze_question_patterns()
        top_topics = sorted(patterns.items(), key=lambda x: x[1], reverse=True)[:3]
        
        for topic, count in top_topics:
            if topic not in [s.topic for s in suggestions]:
                suggestions.append(LearningSuggestion(
                    topic=topic,
                    priority="medium",
                    reason=f"Frequently asked about ({count} times)",
                    suggested_sources=[f"Latest {topic} documents", "Sales team updates"],
                    expected_value=min(0.7, count * 0.1),
                ))
        
        # Default suggestions for B2B sales context
        defaults = [
            LearningSuggestion(
                topic="competitor_analysis",
                priority="medium",
                reason="Competitive intelligence helps close deals",
                suggested_sources=["Market reports", "Sales feedback"],
                expected_value=0.6,
            ),
            LearningSuggestion(
                topic="case_studies",
                priority="medium",
                reason="Customer success stories build trust",
                suggested_sources=["Customer interviews", "Project reports"],
                expected_value=0.5,
            ),
            LearningSuggestion(
                topic="market_trends",
                priority="low",
                reason="Industry context improves conversations",
                suggested_sources=["Industry publications", "Trade shows"],
                expected_value=0.4,
            ),
        ]
        
        for default in defaults:
            if default.topic not in [s.topic for s in suggestions]:
                suggestions.append(default)
        
        # Sort by expected value
        suggestions.sort(key=lambda x: x.expected_value, reverse=True)
        
        # Save suggestions
        self._suggestions_file.parent.mkdir(parents=True, exist_ok=True)
        self._suggestions_file.write_text(json.dumps([
            {
                "topic": s.topic,
                "priority": s.priority,
                "reason": s.reason,
                "suggested_sources": s.suggested_sources,
                "expected_value": s.expected_value,
            }
            for s in suggestions
        ], indent=2))
        
        return suggestions


# =============================================================================
# 5. SOURCE ATTRIBUTION - Track where facts came from
# =============================================================================

@dataclass
class SourceAttribution:
    """Attribution for a piece of knowledge."""
    fact_id: str
    fact_content: str
    source_type: str  # "document", "conversation", "inferred", "external"
    source_name: str
    source_date: str
    confidence: float
    chain_of_custody: List[str]  # How it got here


class SourceAttributionTracker:
    """
    Tracks where each piece of knowledge came from.
    
    Enables:
    - "Where did you learn that?"
    - Confidence based on source quality
    - Identifying stale sources
    """
    
    def __init__(self):
        self._attributions_file = PROJECT_ROOT / "data" / "source_attributions.json"
        self._attributions: Dict[str, SourceAttribution] = {}
        self._load()
    
    def _load(self):
        """Load attributions."""
        if self._attributions_file.exists():
            try:
                data = json.loads(self._attributions_file.read_text())
                for fact_id, attr_data in data.items():
                    self._attributions[fact_id] = SourceAttribution(**attr_data)
            except:
                pass
    
    def _save(self):
        """Save attributions."""
        self._attributions_file.parent.mkdir(parents=True, exist_ok=True)
        data = {
            fact_id: {
                "fact_id": attr.fact_id,
                "fact_content": attr.fact_content,
                "source_type": attr.source_type,
                "source_name": attr.source_name,
                "source_date": attr.source_date,
                "confidence": attr.confidence,
                "chain_of_custody": attr.chain_of_custody,
            }
            for fact_id, attr in self._attributions.items()
        }
        self._attributions_file.write_text(json.dumps(data, indent=2))
    
    def _generate_fact_id(self, content: str) -> str:
        """Generate a unique ID for a fact."""
        return hashlib.md5(content.encode()).hexdigest()[:12]
    
    def attribute_fact(
        self,
        content: str,
        source_type: str,
        source_name: str,
        source_date: str = None,
        confidence: float = 0.8,
    ) -> SourceAttribution:
        """
        Attribute a fact to its source.
        """
        fact_id = self._generate_fact_id(content)
        
        if source_date is None:
            source_date = datetime.now().isoformat()
        
        # Calculate confidence based on source type
        source_confidence = {
            "document": 0.9,
            "conversation": 0.7,
            "inferred": 0.5,
            "external": 0.6,
        }.get(source_type, 0.5)
        
        adjusted_confidence = min(1.0, confidence * source_confidence)
        
        attribution = SourceAttribution(
            fact_id=fact_id,
            fact_content=content[:500],
            source_type=source_type,
            source_name=source_name,
            source_date=source_date,
            confidence=adjusted_confidence,
            chain_of_custody=[f"Created from {source_type}: {source_name}"],
        )
        
        self._attributions[fact_id] = attribution
        self._save()
        
        return attribution
    
    def get_attribution(self, content: str) -> Optional[SourceAttribution]:
        """Get attribution for a fact."""
        fact_id = self._generate_fact_id(content)
        return self._attributions.get(fact_id)
    
    def get_facts_by_source(self, source_name: str) -> List[SourceAttribution]:
        """Get all facts from a specific source."""
        return [
            attr for attr in self._attributions.values()
            if source_name.lower() in attr.source_name.lower()
        ]
    
    def get_stale_facts(self, days: int = 90) -> List[SourceAttribution]:
        """Get facts from old sources."""
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        return [
            attr for attr in self._attributions.values()
            if attr.source_date < cutoff
        ]
    
    def scan_and_attribute(self, memories: List[Dict]) -> Dict[str, Any]:
        """Scan memories and attribute sources."""
        attributed = 0
        by_type = defaultdict(int)
        
        for mem in memories:
            content = mem.get("content") or mem.get("text") or mem.get("memory", "")
            if not content:
                continue
            
            # Determine source type
            metadata = mem.get("metadata", {})
            source = metadata.get("source") or mem.get("source", "")
            
            if "document" in source.lower() or "pdf" in source.lower():
                source_type = "document"
            elif "conversation" in source.lower() or "chat" in source.lower():
                source_type = "conversation"
            elif "inferred" in source.lower():
                source_type = "inferred"
            else:
                source_type = "external"
            
            source_name = source or "Unknown"
            
            self.attribute_fact(content, source_type, source_name)
            attributed += 1
            by_type[source_type] += 1
        
        return {
            "attributed": attributed,
            "by_type": dict(by_type),
            "total_tracked": len(self._attributions),
        }


# =============================================================================
# 6. LEARNING VELOCITY - Track learning speed
# =============================================================================

@dataclass
class LearningMetric:
    """Learning metric for a domain."""
    domain: str
    facts_per_day: float
    quality_score: float  # 0-1
    coverage_score: float  # 0-1
    trend: str  # "improving", "stable", "declining"


class LearningVelocityTracker:
    """
    Tracks how fast Ira is learning in different domains.
    
    Identifies:
    - Fast learning areas
    - Slow/stuck areas needing attention
    - Learning trends over time
    """
    
    def __init__(self):
        self._velocity_file = PROJECT_ROOT / "data" / "learning_velocity.json"
        self._history: List[Dict] = []
        self._load()
    
    def _load(self):
        """Load velocity history."""
        if self._velocity_file.exists():
            try:
                data = json.loads(self._velocity_file.read_text())
                self._history = data.get("history", [])
            except:
                pass
    
    def _save(self):
        """Save velocity history."""
        self._velocity_file.parent.mkdir(parents=True, exist_ok=True)
        self._velocity_file.write_text(json.dumps({
            "history": self._history[-100:],
            "last_updated": datetime.now().isoformat(),
        }, indent=2))
    
    def record_learning(self, domain: str, facts_count: int, quality: float = 0.8):
        """Record a learning event."""
        self._history.append({
            "domain": domain,
            "facts_count": facts_count,
            "quality": quality,
            "timestamp": datetime.now().isoformat(),
        })
        self._save()
    
    def calculate_velocity(self, domain: str = None, days: int = 7) -> Dict[str, LearningMetric]:
        """
        Calculate learning velocity by domain.
        """
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        recent = [h for h in self._history if h.get("timestamp", "") >= cutoff]
        
        # Group by domain
        by_domain = defaultdict(list)
        for h in recent:
            by_domain[h.get("domain", "general")].append(h)
        
        if domain:
            by_domain = {domain: by_domain.get(domain, [])}
        
        metrics = {}
        for dom, events in by_domain.items():
            if not events:
                continue
            
            total_facts = sum(e.get("facts_count", 0) for e in events)
            avg_quality = sum(e.get("quality", 0.5) for e in events) / len(events)
            facts_per_day = total_facts / days
            
            # Determine trend
            if len(events) >= 3:
                first_half = events[:len(events)//2]
                second_half = events[len(events)//2:]
                
                first_rate = sum(e.get("facts_count", 0) for e in first_half) / max(1, len(first_half))
                second_rate = sum(e.get("facts_count", 0) for e in second_half) / max(1, len(second_half))
                
                if second_rate > first_rate * 1.2:
                    trend = "improving"
                elif second_rate < first_rate * 0.8:
                    trend = "declining"
                else:
                    trend = "stable"
            else:
                trend = "stable"
            
            metrics[dom] = LearningMetric(
                domain=dom,
                facts_per_day=facts_per_day,
                quality_score=avg_quality,
                coverage_score=min(1.0, total_facts / 100),  # Assuming 100 facts = full coverage
                trend=trend,
            )
        
        return metrics
    
    def identify_slow_areas(self) -> List[str]:
        """Identify domains with slow learning."""
        metrics = self.calculate_velocity()
        
        slow = []
        for domain, metric in metrics.items():
            if metric.facts_per_day < 1 or metric.trend == "declining":
                slow.append(domain)
        
        return slow


# =============================================================================
# 7. MEMORY COMPRESSION - Compress old memories
# =============================================================================

@dataclass
class CompressedMemory:
    """A compressed memory representation."""
    original_ids: List[str]
    compressed_content: str
    original_count: int
    compression_ratio: float
    domain: str
    created_at: str


class MemoryCompressor:
    """
    Compresses old memories into abstract summaries.
    
    100 individual PF1 facts → 1 comprehensive PF1 schema
    """
    
    def __init__(self):
        self._compressed_file = PROJECT_ROOT / "data" / "compressed_memories.json"
        self._compressed: List[CompressedMemory] = []
        self._openai = None
        self._load()
    
    def _get_openai(self):
        if self._openai is None:
            from openai import OpenAI
            self._openai = OpenAI()
        return self._openai
    
    def _load(self):
        """Load compressed memories."""
        if self._compressed_file.exists():
            try:
                data = json.loads(self._compressed_file.read_text())
                for c in data:
                    self._compressed.append(CompressedMemory(**c))
            except:
                pass
    
    def _save(self):
        """Save compressed memories."""
        self._compressed_file.parent.mkdir(parents=True, exist_ok=True)
        data = [
            {
                "original_ids": c.original_ids,
                "compressed_content": c.compressed_content,
                "original_count": c.original_count,
                "compression_ratio": c.compression_ratio,
                "domain": c.domain,
                "created_at": c.created_at,
            }
            for c in self._compressed
        ]
        self._compressed_file.write_text(json.dumps(data, indent=2))
    
    def compress_memories(
        self,
        memories: List[Dict],
        domain: str = "general",
        min_memories: int = 5,
    ) -> Optional[CompressedMemory]:
        """
        Compress a group of related memories into an abstract summary.
        """
        if len(memories) < min_memories:
            return None
        
        try:
            client = self._get_openai()
            
            # Format memories
            mem_texts = []
            mem_ids = []
            total_chars = 0
            
            for mem in memories[:50]:
                content = mem.get("content") or mem.get("text") or mem.get("memory", "")
                mem_texts.append(content[:200])
                mem_ids.append(mem.get("id", "unknown"))
                total_chars += len(content)
            
            response = client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[
                    {
                        "role": "system",
                        "content": """You are compressing multiple related facts into a single comprehensive summary.
Preserve all important information but eliminate redundancy.
Output a clear, structured summary that captures the essence of all facts."""
                    },
                    {
                        "role": "user",
                        "content": f"Domain: {domain}\n\nFacts to compress:\n" + "\n".join([f"- {t}" for t in mem_texts])
                    }
                ],
                max_tokens=500,
            )
            
            compressed_text = response.choices[0].message.content
            
            compressed = CompressedMemory(
                original_ids=mem_ids,
                compressed_content=compressed_text,
                original_count=len(memories),
                compression_ratio=len(compressed_text) / max(1, total_chars),
                domain=domain,
                created_at=datetime.now().isoformat(),
            )
            
            self._compressed.append(compressed)
            self._save()
            
            return compressed
            
        except Exception as e:
            print(f"[memory_compressor] Error: {e}")
            return None
    
    def get_compressed_by_domain(self, domain: str) -> List[CompressedMemory]:
        """Get compressed memories for a domain."""
        return [c for c in self._compressed if c.domain == domain]


# =============================================================================
# 8. DREAM REPLAY VIEWER - Web dashboard
# =============================================================================

class DreamReplayViewer:
    """
    Generates a web dashboard to visualize dream cycles.
    """
    
    def __init__(self):
        self._dashboard_dir = PROJECT_ROOT / "data" / "dream_dashboard"
        self._dashboard_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_dashboard(self) -> str:
        """
        Generate an HTML dashboard showing dream history.
        """
        # Load dream journal
        journal_file = PROJECT_ROOT / "data" / "dream_journal.json"
        journal_entries = []
        if journal_file.exists():
            try:
                journal_entries = json.loads(journal_file.read_text())
            except:
                pass
        
        # Load velocity data
        velocity_file = PROJECT_ROOT / "data" / "learning_velocity.json"
        velocity_data = {}
        if velocity_file.exists():
            try:
                velocity_data = json.loads(velocity_file.read_text())
            except:
                pass
        
        # Load conflicts
        conflicts_file = PROJECT_ROOT / "data" / "memory_conflicts.json"
        conflicts = []
        if conflicts_file.exists():
            try:
                conflicts = json.loads(conflicts_file.read_text())
            except:
                pass
        
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Ira Dream Dashboard</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #e0e0e0;
            min-height: 100vh;
            padding: 2rem;
        }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        h1 {{
            font-size: 2.5rem;
            margin-bottom: 0.5rem;
            background: linear-gradient(90deg, #00d9ff, #00ff88);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        .subtitle {{ color: #888; margin-bottom: 2rem; }}
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 1.5rem;
        }}
        .card {{
            background: rgba(255,255,255,0.05);
            border-radius: 16px;
            padding: 1.5rem;
            border: 1px solid rgba(255,255,255,0.1);
        }}
        .card h2 {{
            font-size: 1.2rem;
            margin-bottom: 1rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }}
        .stat {{
            font-size: 2.5rem;
            font-weight: bold;
            color: #00d9ff;
        }}
        .stat-label {{ color: #888; font-size: 0.9rem; }}
        ul {{ list-style: none; }}
        li {{
            padding: 0.5rem 0;
            border-bottom: 1px solid rgba(255,255,255,0.05);
        }}
        .tag {{
            display: inline-block;
            padding: 0.2rem 0.5rem;
            border-radius: 4px;
            font-size: 0.8rem;
            margin-right: 0.3rem;
        }}
        .tag-critical {{ background: #ff4757; }}
        .tag-moderate {{ background: #ffa502; color: #1a1a2e; }}
        .tag-low {{ background: #2ed573; color: #1a1a2e; }}
        .timestamp {{ color: #666; font-size: 0.8rem; }}
        .empty {{ color: #666; font-style: italic; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Ira Dream Dashboard</h1>
        <p class="subtitle">Generated {datetime.now().strftime("%Y-%m-%d %H:%M")}</p>
        
        <div class="grid">
            <div class="card">
                <h2>📔 Recent Dreams</h2>
                <div class="stat">{len(journal_entries)}</div>
                <div class="stat-label">Total dream sessions logged</div>
                <ul style="margin-top: 1rem;">
"""
        
        for entry in journal_entries[-5:][::-1]:
            date = entry.get("date", "Unknown")
            docs = entry.get("documents_processed", 0)
            facts = len(entry.get("facts_learned", []))
            html += f"""
                    <li>
                        <strong>{date}</strong><br>
                        <span class="timestamp">{docs} docs, {facts} facts learned</span>
                    </li>"""
        
        if not journal_entries:
            html += '<li class="empty">No dream sessions yet</li>'
        
        html += f"""
                </ul>
            </div>
            
            <div class="card">
                <h2>⚠️ Memory Conflicts</h2>
                <div class="stat">{len(conflicts)}</div>
                <div class="stat-label">Contradictions detected</div>
                <ul style="margin-top: 1rem;">
"""
        
        for conflict in conflicts[-5:][::-1]:
            severity = conflict.get("severity", "moderate")
            ctype = conflict.get("conflict_type", "unknown")
            html += f"""
                    <li>
                        <span class="tag tag-{severity}">{severity}</span>
                        <span class="tag tag-low">{ctype}</span><br>
                        <span class="timestamp">{conflict.get("suggested_resolution", "")[:50]}...</span>
                    </li>"""
        
        if not conflicts:
            html += '<li class="empty">No conflicts detected</li>'
        
        html += f"""
                </ul>
            </div>
            
            <div class="card">
                <h2>📈 Learning Velocity</h2>
"""
        
        history = velocity_data.get("history", [])
        if history:
            recent = history[-7:]
            total_facts = sum(h.get("facts_count", 0) for h in recent)
            avg_quality = sum(h.get("quality", 0) for h in recent) / max(1, len(recent))
            html += f"""
                <div class="stat">{total_facts}</div>
                <div class="stat-label">Facts learned in last 7 days</div>
                <div style="margin-top: 1rem;">
                    <strong>Avg Quality:</strong> {avg_quality:.1%}
                </div>
"""
        else:
            html += '<p class="empty">No learning data yet</p>'
        
        html += """
            </div>
            
            <div class="card">
                <h2>🧠 Memory Health</h2>
                <ul>
                    <li>
                        <strong>Compression</strong><br>
                        <span class="timestamp">Memories optimized for retrieval</span>
                    </li>
                    <li>
                        <strong>Forgetting</strong><br>
                        <span class="timestamp">Low-value memories pruned</span>
                    </li>
                    <li>
                        <strong>Attribution</strong><br>
                        <span class="timestamp">Sources tracked for facts</span>
                    </li>
                </ul>
            </div>
        </div>
    </div>
</body>
</html>
"""
        
        # Save dashboard
        dashboard_path = self._dashboard_dir / "index.html"
        dashboard_path.write_text(html)
        
        return str(dashboard_path)


# =============================================================================
# 9. SLEEP STAGES - Mimic brain sleep cycles
# =============================================================================

class SleepStage(Enum):
    LIGHT = "light"  # Triage and sorting
    DEEP = "deep"    # Consolidation and strengthening
    REM = "rem"      # Creative connections


@dataclass
class SleepStageResult:
    """Result from a sleep stage."""
    stage: SleepStage
    duration_ms: int
    items_processed: int
    summary: str


class SleepStageSimulator:
    """
    Simulates different brain sleep stages.
    
    LIGHT SLEEP: Triage incoming information
    - Sort by importance
    - Flag for further processing
    - Quick duplicate detection
    
    DEEP SLEEP: Consolidation
    - Strengthen important memories
    - Connect to existing knowledge
    - Build schemas
    
    REM SLEEP: Creativity
    - Novel connections
    - Problem solving
    - Pattern discovery
    """
    
    def __init__(self):
        self._openai = None
    
    def _get_openai(self):
        if self._openai is None:
            from openai import OpenAI
            self._openai = OpenAI()
        return self._openai
    
    def run_light_sleep(self, memories: List[Dict]) -> SleepStageResult:
        """
        LIGHT SLEEP: Triage and sort.
        """
        import time
        start = time.time()
        
        processed = 0
        high_priority = []
        duplicates = []
        
        seen_hashes = set()
        
        for mem in memories:
            content = mem.get("content") or mem.get("text") or mem.get("memory", "")
            
            # Quick hash for duplicate detection
            content_hash = hashlib.md5(content.lower()[:100].encode()).hexdigest()
            
            if content_hash in seen_hashes:
                duplicates.append(mem)
            else:
                seen_hashes.add(content_hash)
                
                # Quick importance check
                importance_keywords = ["price", "cost", "spec", "delivery", "urgent", "critical"]
                if any(kw in content.lower() for kw in importance_keywords):
                    high_priority.append(mem)
            
            processed += 1
        
        duration = int((time.time() - start) * 1000)
        
        return SleepStageResult(
            stage=SleepStage.LIGHT,
            duration_ms=duration,
            items_processed=processed,
            summary=f"Triaged {processed} items. {len(high_priority)} high priority, {len(duplicates)} duplicates.",
        )
    
    def run_deep_sleep(self, memories: List[Dict]) -> SleepStageResult:
        """
        DEEP SLEEP: Consolidation and strengthening.
        """
        import time
        start = time.time()
        
        processed = 0
        consolidated = 0
        
        # Group by entity/topic
        groups = defaultdict(list)
        
        for mem in memories:
            content = mem.get("content") or mem.get("text") or mem.get("memory", "")
            
            # Simple entity extraction
            words = content.lower().split()
            for word in words:
                if any(p in word for p in ["pf1", "pf2", "img", "fcs", "am-"]):
                    groups[word].append(mem)
                    break
            else:
                groups["general"].append(mem)
            
            processed += 1
        
        # Consolidate groups with 3+ items
        for group, items in groups.items():
            if len(items) >= 3:
                consolidated += 1
        
        duration = int((time.time() - start) * 1000)
        
        return SleepStageResult(
            stage=SleepStage.DEEP,
            duration_ms=duration,
            items_processed=processed,
            summary=f"Consolidated {processed} items into {len(groups)} groups. {consolidated} ready for schema building.",
        )
    
    def run_rem_sleep(self, memories: List[Dict]) -> SleepStageResult:
        """
        REM SLEEP: Creative connections.
        """
        import time
        start = time.time()
        
        connections = []
        
        # Find unexpected connections using random sampling
        if len(memories) >= 10:
            sample = random.sample(memories, min(10, len(memories)))
            
            try:
                client = self._get_openai()
                
                contents = [
                    (m.get("content") or m.get("text") or m.get("memory", ""))[:100]
                    for m in sample
                ]
                
                response = client.chat.completions.create(
                    model="gpt-4.1-mini",
                    messages=[
                        {
                            "role": "system",
                            "content": """You are in REM sleep, making creative connections.
Find 2-3 unexpected but useful connections between these random facts.
Output brief insights only."""
                        },
                        {
                            "role": "user",
                            "content": "Facts:\n" + "\n".join([f"- {c}" for c in contents])
                        }
                    ],
                    max_tokens=200,
                )
                
                insight = response.choices[0].message.content
                connections.append(insight)
                
            except Exception as e:
                print(f"[rem_sleep] Error: {e}")
        
        duration = int((time.time() - start) * 1000)
        
        return SleepStageResult(
            stage=SleepStage.REM,
            duration_ms=duration,
            items_processed=len(memories),
            summary=f"Generated {len(connections)} creative insights from {len(memories)} memories.",
        )
    
    def run_full_cycle(self, memories: List[Dict]) -> Dict[str, Any]:
        """
        Run a full sleep cycle: Light → Deep → REM.
        """
        results = {
            "stages": [],
            "total_duration_ms": 0,
        }
        
        # Stage 1: Light Sleep
        light = self.run_light_sleep(memories)
        results["stages"].append({
            "stage": light.stage.value,
            "duration_ms": light.duration_ms,
            "items": light.items_processed,
            "summary": light.summary,
        })
        results["total_duration_ms"] += light.duration_ms
        
        # Stage 2: Deep Sleep
        deep = self.run_deep_sleep(memories)
        results["stages"].append({
            "stage": deep.stage.value,
            "duration_ms": deep.duration_ms,
            "items": deep.items_processed,
            "summary": deep.summary,
        })
        results["total_duration_ms"] += deep.duration_ms
        
        # Stage 3: REM Sleep
        rem = self.run_rem_sleep(memories)
        results["stages"].append({
            "stage": rem.stage.value,
            "duration_ms": rem.duration_ms,
            "items": rem.items_processed,
            "summary": rem.summary,
        })
        results["total_duration_ms"] += rem.duration_ms
        
        return results


# =============================================================================
# 10. COUNTERFACTUAL REASONING - Stress test knowledge
# =============================================================================

@dataclass
class Counterfactual:
    """A counterfactual scenario."""
    scenario: str
    impact: str
    confidence: float
    recommendations: List[str]


class CounterfactualReasoner:
    """
    Stress tests knowledge with "what if" scenarios.
    
    Examples:
    - "What if a competitor had faster delivery?"
    - "What if prices increased 20%?"
    - "What if a key feature wasn't available?"
    """
    
    def __init__(self):
        self._scenarios_file = PROJECT_ROOT / "data" / "counterfactuals.json"
        self._openai = None
    
    def _get_openai(self):
        if self._openai is None:
            from openai import OpenAI
            self._openai = OpenAI()
        return self._openai
    
    def generate_scenarios(self, context: str = "B2B thermoforming sales") -> List[Counterfactual]:
        """
        Generate relevant counterfactual scenarios.
        """
        default_scenarios = [
            Counterfactual(
                scenario="What if a competitor offered 30% faster delivery?",
                impact="Would lose time-sensitive deals",
                confidence=0.7,
                recommendations=["Emphasize quality over speed", "Highlight total cost of ownership"],
            ),
            Counterfactual(
                scenario="What if prices increased by 15%?",
                impact="May lose price-sensitive customers",
                confidence=0.6,
                recommendations=["Prepare value justification", "Bundle services for value"],
            ),
            Counterfactual(
                scenario="What if key raw materials became scarce?",
                impact="Delivery times would extend",
                confidence=0.5,
                recommendations=["Diversify supplier base", "Stock critical components"],
            ),
            Counterfactual(
                scenario="What if a customer asked for a feature we don't have?",
                impact="Could lose deal to competitor",
                confidence=0.8,
                recommendations=["Propose custom solution", "Highlight alternative features"],
            ),
        ]
        
        return default_scenarios
    
    def stress_test(self, scenario: str, knowledge_base: List[Dict]) -> Dict[str, Any]:
        """
        Stress test knowledge against a specific scenario.
        """
        try:
            client = self._get_openai()
            
            # Sample relevant knowledge
            kb_sample = []
            for mem in knowledge_base[:20]:
                content = mem.get("content") or mem.get("text") or mem.get("memory", "")
                kb_sample.append(content[:150])
            
            response = client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[
                    {
                        "role": "system",
                        "content": """You are stress-testing a knowledge base against a hypothetical scenario.

Analyze:
1. How well would current knowledge handle this scenario?
2. What gaps exist?
3. What should be prepared?

Output JSON:
{
    "readiness_score": 0.0-1.0,
    "gaps": ["gap1", "gap2"],
    "preparations": ["prep1", "prep2"]
}"""
                    },
                    {
                        "role": "user",
                        "content": f"Scenario: {scenario}\n\nKnowledge sample:\n" + "\n".join([f"- {k}" for k in kb_sample])
                    }
                ],
                max_tokens=300,
            )
            
            result_text = response.choices[0].message.content
            
            import re
            json_match = re.search(r'\{[^{}]+\}', result_text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            
        except Exception as e:
            print(f"[counterfactual] Error: {e}")
        
        return {
            "readiness_score": 0.5,
            "gaps": ["Unable to analyze"],
            "preparations": ["Review scenario manually"],
        }
    
    def run_all_scenarios(self, knowledge_base: List[Dict]) -> Dict[str, Any]:
        """
        Run all stress test scenarios.
        """
        scenarios = self.generate_scenarios()
        results = []
        
        for scenario in scenarios:
            test_result = self.stress_test(scenario.scenario, knowledge_base)
            results.append({
                "scenario": scenario.scenario,
                "impact": scenario.impact,
                "readiness": test_result.get("readiness_score", 0.5),
                "gaps": test_result.get("gaps", []),
                "preparations": test_result.get("preparations", []),
            })
        
        # Calculate overall readiness
        avg_readiness = sum(r["readiness"] for r in results) / max(1, len(results))
        
        # Save results
        self._scenarios_file.parent.mkdir(parents=True, exist_ok=True)
        self._scenarios_file.write_text(json.dumps({
            "results": results,
            "overall_readiness": avg_readiness,
            "timestamp": datetime.now().isoformat(),
        }, indent=2))
        
        return {
            "scenarios_tested": len(results),
            "overall_readiness": avg_readiness,
            "critical_gaps": [
                r["gaps"][0] for r in results
                if r.get("gaps") and r["readiness"] < 0.5
            ],
            "results": results,
        }


# =============================================================================
# UNIFIED RUNNER
# =============================================================================

class DreamExperimentalRunner:
    """Run all experimental dream features."""
    
    def __init__(self):
        self.forgetting = ForgettingEngine()
        self.conflicts = MemoryConflictDetector()
        self.preloader = PredictivePreloader()
        self.learner = ActiveLearningSuggester()
        self.attribution = SourceAttributionTracker()
        self.velocity = LearningVelocityTracker()
        self.compressor = MemoryCompressor()
        self.dashboard = DreamReplayViewer()
        self.sleep_sim = SleepStageSimulator()
        self.counterfactual = CounterfactualReasoner()
    
    def run_all(
        self,
        memories: List[Dict] = None,
        verbose: bool = True,
    ) -> Dict[str, Any]:
        """
        Run all experimental features.
        """
        if memories is None:
            memories = []
        
        results = {}
        
        # 1. Forgetting Engine
        if verbose:
            print("\n🗑️  Phase E1: Forgetting Engine...")
        forget_candidates = self.forgetting.identify_forgettable_memories(memories, threshold=0.7)
        forget_result = self.forgetting.forget_memories(forget_candidates, dry_run=True)
        results["forgetting"] = forget_result
        if verbose:
            print(f"   Candidates for forgetting: {forget_result.get('candidates_found', 0)}")
        
        # 2. Conflict Detection
        if verbose:
            print("\n⚠️  Phase E2: Memory Conflict Detection...")
        conflicts = self.conflicts.detect_conflicts(memories, use_llm=len(memories) >= 5)
        results["conflicts"] = {
            "detected": len(conflicts),
            "critical": len([c for c in conflicts if c.severity == "critical"]),
        }
        if verbose:
            print(f"   Conflicts detected: {len(conflicts)}")
        
        # 3. Predictive Preloading
        if verbose:
            print("\n🔮 Phase E3: Predictive Preloading...")
        predictions = self.preloader.predict_tomorrow()
        results["predictions"] = {
            "topics": len(predictions),
            "top_prediction": predictions[0].topic if predictions else None,
        }
        if verbose:
            print(f"   Tomorrow's predicted needs: {len(predictions)}")
        
        # 4. Active Learning
        if verbose:
            print("\n📚 Phase E4: Active Learning Suggestions...")
        suggestions = self.learner.generate_suggestions()
        results["learning"] = {
            "suggestions": len(suggestions),
            "top_priority": suggestions[0].topic if suggestions else None,
        }
        if verbose:
            print(f"   Learning suggestions: {len(suggestions)}")
        
        # 5. Source Attribution
        if verbose:
            print("\n🔗 Phase E5: Source Attribution...")
        attr_result = self.attribution.scan_and_attribute(memories)
        results["attribution"] = attr_result
        if verbose:
            print(f"   Facts attributed: {attr_result.get('attributed', 0)}")
        
        # 6. Learning Velocity
        if verbose:
            print("\n📈 Phase E6: Learning Velocity...")
        velocity_metrics = self.velocity.calculate_velocity()
        slow_areas = self.velocity.identify_slow_areas()
        results["velocity"] = {
            "domains_tracked": len(velocity_metrics),
            "slow_areas": slow_areas,
        }
        if verbose:
            print(f"   Domains tracked: {len(velocity_metrics)}")
            print(f"   Slow areas: {slow_areas or 'None'}")
        
        # 7. Memory Compression
        if verbose:
            print("\n🗜️  Phase E7: Memory Compression...")
        # Group memories by potential domain
        if len(memories) >= 10:
            compressed = self.compressor.compress_memories(memories[:20], domain="general")
            results["compression"] = {
                "compressed": 1 if compressed else 0,
                "ratio": compressed.compression_ratio if compressed else 0,
            }
        else:
            results["compression"] = {"compressed": 0, "reason": "Not enough memories"}
        if verbose:
            print(f"   Compression: {results['compression']}")
        
        # 8. Dream Dashboard
        if verbose:
            print("\n📊 Phase E8: Dream Dashboard...")
        dashboard_path = self.dashboard.generate_dashboard()
        results["dashboard"] = {"path": dashboard_path}
        if verbose:
            print(f"   Dashboard: {dashboard_path}")
        
        # 9. Sleep Stages
        if verbose:
            print("\n😴 Phase E9: Sleep Stage Simulation...")
        if memories:
            sleep_results = self.sleep_sim.run_full_cycle(memories)
            results["sleep_stages"] = sleep_results
            if verbose:
                for stage in sleep_results.get("stages", []):
                    print(f"   {stage['stage'].upper()}: {stage['summary']}")
        else:
            results["sleep_stages"] = {"skipped": "No memories"}
        
        # 10. Counterfactual Reasoning
        if verbose:
            print("\n🤔 Phase E10: Counterfactual Reasoning...")
        cf_results = self.counterfactual.run_all_scenarios(memories)
        results["counterfactual"] = {
            "scenarios": cf_results.get("scenarios_tested", 0),
            "readiness": cf_results.get("overall_readiness", 0),
        }
        if verbose:
            print(f"   Overall readiness: {cf_results.get('overall_readiness', 0):.1%}")
        
        return results


# =============================================================================
# CLI
# =============================================================================

def run_experimental_dream(memories: List[Dict] = None, verbose: bool = True) -> Dict[str, Any]:
    """Convenience function to run all experimental features."""
    runner = DreamExperimentalRunner()
    return runner.run_all(memories=memories, verbose=verbose)


if __name__ == "__main__":
    print("=" * 60)
    print("DREAM EXPERIMENTAL - Running all features")
    print("=" * 60)
    
    # Create some test memories
    test_memories = [
        {"content": "PF1-C-3020 base price is EUR 180,000", "id": "1"},
        {"content": "PF1-C-3020 base price is EUR 175,000", "id": "2"},  # Conflict!
        {"content": "Delivery time is 16-18 weeks standard", "id": "3"},
        {"content": "IMG-1350 can produce 35 cycles per minute", "id": "4"},
        {"content": "Machinecraft was founded in 1995", "id": "5"},
        {"content": "PF1 series supports up to 850mm forming depth", "id": "6"},
        {"content": "FCS-6070 is optimized for food packaging", "id": "7"},
        {"content": "Standard warranty is 12 months", "id": "8"},
        {"content": "Installation takes 2-3 days on site", "id": "9"},
        {"content": "Training program lasts 5 days", "id": "10"},
    ]
    
    results = run_experimental_dream(memories=test_memories, verbose=True)
    
    print("\n" + "=" * 60)
    print("COMPLETE")
    print("=" * 60)
