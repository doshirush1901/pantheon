#!/usr/bin/env python3
"""
APOLLO Learning Engine
======================

Helps IRA improve over time by:
1. Tracking error patterns
2. Deciding when to ask Rushabh for clarification
3. Identifying which knowledge sources to search
4. Building corrections into memory

Learning Formula:
    Improvement = f(error_patterns, knowledge_gaps, feedback_history)

The engine maintains:
- Error Pattern Database: Common mistakes and their fixes
- Knowledge Gap Tracker: What IRA doesn't know
- Correction Memory: Rushabh's corrections stored for learning
- Search Priority Map: Which sources to check for what topics
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from collections import defaultdict

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

import openai
from accuracy_scorer import AccuracyReport, score_response

client = openai.OpenAI()


# =============================================================================
# LEARNING DATA STRUCTURES
# =============================================================================

@dataclass
class ErrorPattern:
    """A recurring error pattern."""
    pattern_id: str
    category: str  # "price", "spec", "style", "missing_info"
    description: str
    occurrences: int = 1
    last_seen: str = ""
    fix_applied: str = ""
    

@dataclass
class KnowledgeGap:
    """A gap in IRA's knowledge."""
    topic: str
    query_examples: List[str] = field(default_factory=list)
    suggested_sources: List[str] = field(default_factory=list)
    priority: str = "medium"  # low, medium, high, critical


@dataclass
class Correction:
    """A correction from Rushabh."""
    timestamp: str
    original_response: str
    corrected_response: str
    query: str
    correction_type: str  # "factual", "style", "completeness"
    learned: bool = False


@dataclass
class LearningState:
    """Current learning state for IRA."""
    error_patterns: Dict[str, ErrorPattern] = field(default_factory=dict)
    knowledge_gaps: List[KnowledgeGap] = field(default_factory=list)
    corrections: List[Correction] = field(default_factory=list)
    search_priority: Dict[str, List[str]] = field(default_factory=dict)
    confidence_threshold: float = 0.7
    total_queries_processed: int = 0
    accuracy_history: List[float] = field(default_factory=list)


# =============================================================================
# KNOWLEDGE SOURCE MAPPING
# =============================================================================

KNOWLEDGE_SOURCES = {
    "pricing": [
        "data/imports/Machinecraft Price List for Plastindia (1).pdf",
        "data/knowledge/customer_orders_history.md",
        "data/knowledge/verified_sales_cycles.md",
    ],
    "specifications": [
        "data/knowledge/sales_playbook.md",
        "data/imports/Machinecraft Price List for Plastindia (1).pdf",
    ],
    "competitors": [
        "data/knowledge/sales_playbook.md",
        "data/knowledge/european_sales_cycle_analysis.md",
    ],
    "delivery": [
        "data/knowledge/verified_sales_cycles.md",
        "data/knowledge/customer_orders_history.md",
    ],
    "warranty": [
        "data/knowledge/sales_playbook.md",
    ],
    "european_market": [
        "data/knowledge/european_sales_cycle_analysis.md",
        "data/imports/European & US Contacts for Single Station Nov 203.csv",
    ],
    "customer_history": [
        "data/knowledge/customer_orders_history.md",
        "data/knowledge/customer_orders.json",
    ],
}


# =============================================================================
# LEARNING ENGINE
# =============================================================================

class LearningEngine:
    """
    Core learning engine for IRA improvement.
    
    Capabilities:
    1. Process accuracy reports and learn from errors
    2. Decide when to escalate to Rushabh
    3. Recommend knowledge sources to search
    4. Store and apply corrections
    """
    
    def __init__(self, state_file: str = None):
        self.state_file = state_file or str(
            PROJECT_ROOT / "data" / "training" / "learning_state.json"
        )
        self.state = self._load_state()
    
    def _load_state(self) -> LearningState:
        """Load learning state from file."""
        try:
            if Path(self.state_file).exists():
                with open(self.state_file) as f:
                    data = json.load(f)
                return LearningState(**data)
        except Exception as e:
            print(f"Error loading state: {e}")
        
        return LearningState()
    
    def _save_state(self):
        """Save learning state to file."""
        Path(self.state_file).parent.mkdir(parents=True, exist_ok=True)
        
        # Convert to serializable dict
        data = {
            "error_patterns": {
                k: {
                    "pattern_id": v.pattern_id,
                    "category": v.category,
                    "description": v.description,
                    "occurrences": v.occurrences,
                    "last_seen": v.last_seen,
                    "fix_applied": v.fix_applied,
                }
                for k, v in self.state.error_patterns.items()
            },
            "knowledge_gaps": [
                {
                    "topic": g.topic,
                    "query_examples": g.query_examples,
                    "suggested_sources": g.suggested_sources,
                    "priority": g.priority,
                }
                for g in self.state.knowledge_gaps
            ],
            "corrections": [
                {
                    "timestamp": c.timestamp,
                    "original_response": c.original_response[:500],
                    "corrected_response": c.corrected_response[:500],
                    "query": c.query[:200],
                    "correction_type": c.correction_type,
                    "learned": c.learned,
                }
                for c in self.state.corrections[-100:]  # Keep last 100
            ],
            "search_priority": self.state.search_priority,
            "confidence_threshold": self.state.confidence_threshold,
            "total_queries_processed": self.state.total_queries_processed,
            "accuracy_history": self.state.accuracy_history[-1000:],  # Keep last 1000
        }
        
        with open(self.state_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    # =========================================================================
    # STRESS TEST LEARNINGS INTEGRATION
    # =========================================================================
    
    def load_stress_test_learnings(self, learnings_file: str = None) -> Dict:
        """
        Load lessons learned from stress test evaluations.
        These are critical business rules and patterns that IRA must follow.
        """
        if learnings_file is None:
            learnings_file = str(PROJECT_ROOT / "data" / "learned_lessons" / "stress_test_learnings_2026_02_28.json")
        
        try:
            with open(learnings_file) as f:
                learnings = json.load(f)
            
            # Extract and register critical error patterns
            for lesson in learnings.get("lessons_learned", []):
                pattern = ErrorPattern(
                    pattern_id=lesson["id"],
                    category=lesson["category"],
                    description=lesson["lesson"],
                    occurrences=1,
                    last_seen=learnings.get("learning_session", {}).get("date", ""),
                    fix_applied=lesson.get("code_enforcement", ""),
                )
                self.state.error_patterns[lesson["id"]] = pattern
            
            # Store sub-agent upgrades as knowledge
            sub_agent_upgrades = learnings.get("sub_agent_upgrades", {})
            self.state.search_priority["stress_test_learnings"] = [learnings_file]
            
            self._save_state()
            
            print(f"✅ Loaded {len(learnings.get('lessons_learned', []))} lessons from stress tests")
            print(f"✅ Sub-agent upgrades: {list(sub_agent_upgrades.keys())}")
            
            return learnings
            
        except FileNotFoundError:
            print(f"⚠️ No stress test learnings found at {learnings_file}")
            return {}
        except Exception as e:
            print(f"❌ Error loading stress test learnings: {e}")
            return {}
    
    def get_applicable_lesson(self, query: str) -> Optional[Dict]:
        """
        Check if any stress test lesson applies to the current query.
        Returns the most relevant lesson if found.
        """
        query_lower = query.lower()
        
        # Load learnings
        learnings_file = str(PROJECT_ROOT / "data" / "learned_lessons" / "stress_test_learnings_2026_02_28.json")
        try:
            with open(learnings_file) as f:
                learnings = json.load(f)
        except:
            return None
        
        for lesson in learnings.get("lessons_learned", []):
            # Check trigger keywords
            if "trigger_keywords" in lesson:
                if any(kw.lower() in query_lower for kw in lesson["trigger_keywords"]):
                    return lesson
            
            # Check trigger patterns
            if "trigger" in lesson:
                trigger = lesson["trigger"].lower()
                # Check for key phrases from trigger
                trigger_words = [w for w in trigger.split() if len(w) > 4]
                if sum(1 for w in trigger_words if w in query_lower) >= 2:
                    return lesson
            
            # Check impossible combinations
            if "impossible_combinations" in lesson:
                for combo in lesson["impossible_combinations"]:
                    combo_words = [w.lower() for w in combo.split() if len(w) > 3]
                    if sum(1 for w in combo_words if w in query_lower) >= 2:
                        return lesson
        
        return None

    # =========================================================================
    # ERROR PATTERN LEARNING
    # =========================================================================
    
    def learn_from_report(self, report: AccuracyReport, query: str):
        """Learn from an accuracy report."""
        
        self.state.total_queries_processed += 1
        self.state.accuracy_history.append(report.overall_score)
        
        # Track error patterns
        for fact_check in report.fact_checks:
            if not fact_check.correct:
                self._record_error_pattern(
                    category="factual",
                    description=f"Wrong {fact_check.fact}: expected {fact_check.expected}, got {fact_check.actual}",
                )
        
        for missing in report.missing_info:
            self._record_error_pattern(
                category="missing_info",
                description=f"Missing: {missing}",
            )
        
        for hallucination in report.hallucinations:
            self._record_error_pattern(
                category="hallucination",
                description=f"Hallucinated: {hallucination}",
            )
        
        for style_issue in report.style_issues:
            self._record_error_pattern(
                category="style",
                description=style_issue,
            )
        
        # Track knowledge gaps
        for gap in report.knowledge_gaps:
            self._record_knowledge_gap(gap, query)
        
        self._save_state()
    
    def _record_error_pattern(self, category: str, description: str):
        """Record or update an error pattern."""
        # Create pattern ID from description
        pattern_id = f"{category}_{hash(description) % 10000}"
        
        if pattern_id in self.state.error_patterns:
            self.state.error_patterns[pattern_id].occurrences += 1
            self.state.error_patterns[pattern_id].last_seen = datetime.now().isoformat()
        else:
            self.state.error_patterns[pattern_id] = ErrorPattern(
                pattern_id=pattern_id,
                category=category,
                description=description,
                last_seen=datetime.now().isoformat(),
            )
    
    def _record_knowledge_gap(self, gap_description: str, query: str):
        """Record a knowledge gap."""
        # Check if gap already exists
        for gap in self.state.knowledge_gaps:
            if gap_description.lower() in gap.topic.lower():
                gap.query_examples.append(query)
                return
        
        # Create new gap
        self.state.knowledge_gaps.append(KnowledgeGap(
            topic=gap_description,
            query_examples=[query],
            suggested_sources=self._suggest_sources(gap_description),
        ))
    
    # =========================================================================
    # DECISION ENGINE
    # =========================================================================
    
    def should_ask_rushabh(
        self,
        query: str,
        confidence: float,
        context: Dict = None
    ) -> Tuple[bool, str]:
        """
        Decide if IRA should ask Rushabh for help.
        
        Returns:
            (should_ask, reason)
        """
        reasons = []
        
        # Low confidence
        if confidence < self.state.confidence_threshold:
            reasons.append(f"Confidence ({confidence:.0%}) below threshold ({self.state.confidence_threshold:.0%})")
        
        # Check for known problem patterns
        query_lower = query.lower()
        problem_keywords = ["competitor", "kiefel", "illig", "discount", "negotiate", "special price"]
        for keyword in problem_keywords:
            if keyword in query_lower:
                reasons.append(f"Sensitive topic detected: {keyword}")
        
        # Check for knowledge gaps
        for gap in self.state.knowledge_gaps:
            if gap.priority in ["high", "critical"]:
                for example in gap.query_examples:
                    if self._query_similarity(query, example) > 0.7:
                        reasons.append(f"Known knowledge gap: {gap.topic}")
        
        # Check error history - if we've made this mistake before
        recent_errors = [
            p for p in self.state.error_patterns.values()
            if p.occurrences >= 2  # Recurring error
        ]
        if len(recent_errors) > 3:
            reasons.append(f"Multiple recurring error patterns ({len(recent_errors)})")
        
        should_ask = len(reasons) > 0
        reason = "; ".join(reasons) if reasons else "No issues detected"
        
        return should_ask, reason
    
    def _query_similarity(self, q1: str, q2: str) -> float:
        """Simple similarity check between queries."""
        words1 = set(q1.lower().split())
        words2 = set(q2.lower().split())
        if not words1 or not words2:
            return 0.0
        intersection = words1 & words2
        union = words1 | words2
        return len(intersection) / len(union)
    
    # =========================================================================
    # KNOWLEDGE SOURCE RECOMMENDATION
    # =========================================================================
    
    def recommend_sources(self, query: str) -> List[str]:
        """Recommend knowledge sources to search for this query."""
        query_lower = query.lower()
        
        sources = set()
        
        # Match keywords to sources
        keyword_mapping = {
            "price": "pricing",
            "cost": "pricing",
            "eur": "pricing",
            "inr": "pricing",
            "quote": "pricing",
            "spec": "specifications",
            "dimension": "specifications",
            "thickness": "specifications",
            "forming": "specifications",
            "kiefel": "competitors",
            "illig": "competitors",
            "competitor": "competitors",
            "deliver": "delivery",
            "lead time": "delivery",
            "ship": "delivery",
            "warrant": "warranty",
            "service": "warranty",
            "europe": "european_market",
            "german": "european_market",
            "netherland": "european_market",
            "customer": "customer_history",
            "previous": "customer_history",
            "order": "customer_history",
        }
        
        for keyword, source_key in keyword_mapping.items():
            if keyword in query_lower:
                sources.update(KNOWLEDGE_SOURCES.get(source_key, []))
        
        # If no matches, return general sources
        if not sources:
            sources.update(KNOWLEDGE_SOURCES["pricing"])
            sources.update(KNOWLEDGE_SOURCES["specifications"])
        
        return list(sources)
    
    def _suggest_sources(self, gap_description: str) -> List[str]:
        """Suggest sources for a knowledge gap."""
        return self.recommend_sources(gap_description)
    
    # =========================================================================
    # CORRECTION LEARNING
    # =========================================================================
    
    def record_correction(
        self,
        query: str,
        original_response: str,
        corrected_response: str,
        correction_type: str = "factual"
    ):
        """Record a correction from Rushabh."""
        correction = Correction(
            timestamp=datetime.now().isoformat(),
            original_response=original_response,
            corrected_response=corrected_response,
            query=query,
            correction_type=correction_type,
        )
        
        self.state.corrections.append(correction)
        self._save_state()
        
        # Also analyze what was wrong
        report = score_response(
            ira_response=original_response,
            expected_response=corrected_response,
            query=query,
        )
        
        self.learn_from_report(report, query)
    
    def get_relevant_corrections(self, query: str, limit: int = 3) -> List[Correction]:
        """Get corrections relevant to the current query."""
        relevant = []
        
        for correction in self.state.corrections:
            similarity = self._query_similarity(query, correction.query)
            if similarity > 0.3:
                relevant.append((similarity, correction))
        
        # Sort by similarity and return top N
        relevant.sort(key=lambda x: x[0], reverse=True)
        return [c for _, c in relevant[:limit]]
    
    # =========================================================================
    # ANALYTICS
    # =========================================================================
    
    def get_accuracy_trend(self, window: int = 20) -> Dict:
        """Get accuracy trend over recent queries."""
        history = self.state.accuracy_history
        
        if len(history) < 2:
            return {
                "current_avg": history[-1] if history else 0,
                "trend": "insufficient_data",
                "improvement": 0,
            }
        
        recent = history[-window:]
        older = history[-2*window:-window] if len(history) > window else history[:len(history)//2]
        
        current_avg = sum(recent) / len(recent)
        older_avg = sum(older) / len(older) if older else current_avg
        
        improvement = current_avg - older_avg
        
        if improvement > 0.05:
            trend = "improving"
        elif improvement < -0.05:
            trend = "declining"
        else:
            trend = "stable"
        
        return {
            "current_avg": current_avg,
            "previous_avg": older_avg,
            "trend": trend,
            "improvement": improvement,
            "total_queries": len(history),
        }
    
    def get_top_error_patterns(self, limit: int = 5) -> List[ErrorPattern]:
        """Get most common error patterns."""
        patterns = list(self.state.error_patterns.values())
        patterns.sort(key=lambda p: p.occurrences, reverse=True)
        return patterns[:limit]
    
    def get_learning_summary(self) -> str:
        """Get a summary of learning progress."""
        trend = self.get_accuracy_trend()
        top_errors = self.get_top_error_patterns()
        
        summary = f"""
LEARNING SUMMARY
================
Total Queries Processed: {self.state.total_queries_processed}
Current Accuracy: {trend['current_avg']:.1%}
Trend: {trend['trend'].upper()} ({trend['improvement']:+.1%})

TOP ERROR PATTERNS:
"""
        for i, err in enumerate(top_errors, 1):
            summary += f"  {i}. [{err.category}] {err.description[:50]}... ({err.occurrences}x)\n"
        
        summary += f"\nKNOWLEDGE GAPS: {len(self.state.knowledge_gaps)}"
        summary += f"\nCORRECTIONS LEARNED: {len(self.state.corrections)}"
        
        return summary


# =============================================================================
# INTEGRATION WITH IRA
# =============================================================================

def enhance_ira_response(
    query: str,
    draft_response: str,
    engine: LearningEngine
) -> Tuple[str, Dict]:
    """
    Enhance IRA's draft response using learning.
    
    Returns:
        (enhanced_response, metadata)
    """
    metadata = {
        "sources_recommended": [],
        "corrections_applied": [],
        "confidence_check": {},
    }
    
    # Check relevant corrections
    corrections = engine.get_relevant_corrections(query)
    
    if corrections:
        # Build correction context
        correction_context = "\n".join([
            f"Previous correction: '{c.original_response[:100]}...' → '{c.corrected_response[:100]}...'"
            for c in corrections
        ])
        
        # Ask LLM to apply learnings
        enhancement_prompt = f"""Review and improve this draft response based on previous corrections.

ORIGINAL DRAFT:
{draft_response}

RELEVANT PAST CORRECTIONS:
{correction_context}

Improve the draft to avoid similar mistakes. Return the improved response only."""

        try:
            result = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": enhancement_prompt}],
                temperature=0.3,
            )
            enhanced = result.choices[0].message.content
            metadata["corrections_applied"] = [c.query[:50] for c in corrections]
            return enhanced, metadata
        except Exception as e:
            print(f"Enhancement error: {e}")
    
    # Recommend sources
    metadata["sources_recommended"] = engine.recommend_sources(query)
    
    return draft_response, metadata


# =============================================================================
# CLI
# =============================================================================

if __name__ == "__main__":
    engine = LearningEngine()
    
    print(engine.get_learning_summary())
    
    # Demo: Check if should ask Rushabh
    test_queries = [
        "What's the price for PF1-C?",
        "How does your machine compare to Kiefel KMD 78?",
        "Can you give us a 25% discount?",
    ]
    
    print("\n\nESCALATION CHECK:")
    for query in test_queries:
        should_ask, reason = engine.should_ask_rushabh(query, confidence=0.6)
        print(f"\nQuery: {query}")
        print(f"  Ask Rushabh: {'YES' if should_ask else 'NO'}")
        print(f"  Reason: {reason}")
