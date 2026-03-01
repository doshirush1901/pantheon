#!/usr/bin/env python3
"""
Feedback Learner - Learning from Corrections
=============================================

Implements Strategy 6 from DEEP_REPLY_IMPROVEMENT_STRATEGY.md:
- Extract lessons from corrections
- Store corrections as high-priority memories
- Improve future responses based on feedback

This enables IRA to continuously learn and improve from user feedback,
creating a virtuous cycle of correction → memory → better responses.

Usage:
    from openclaw.agents.ira.src.memory.feedback_learner import (
        FeedbackLearner, process_feedback, extract_lesson
    )
    
    # Process a correction
    lesson = process_feedback(
        original_reply="The PF1-2015 has a 50 kW heater",
        correction="Actually it's a 40 kW heater"
    )
    
    # Lesson is now stored in Mem0 and will influence future replies
"""

import json
import sys
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

SKILLS_DIR = Path(__file__).parent.parent
AGENT_DIR = SKILLS_DIR.parent

try:
    sys.path.insert(0, str(AGENT_DIR))
    from config import get_openai_client, get_logger, FAST_LLM_MODEL, append_jsonl, PROJECT_ROOT
    CONFIG_AVAILABLE = True
    logger = get_logger(__name__)
except ImportError:
    CONFIG_AVAILABLE = False
    import logging
    logger = logging.getLogger(__name__)
    FAST_LLM_MODEL = "gpt-4o-mini"
    PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent.parent


class CorrectionType(str, Enum):
    """Type of correction being made."""
    SPEC_CORRECTION = "spec_correction"
    PRICE_CORRECTION = "price_correction"
    FACT_CORRECTION = "fact_correction"
    TONE_CORRECTION = "tone_correction"
    FORMAT_CORRECTION = "format_correction"
    MISSING_INFO = "missing_info"
    OUTDATED_INFO = "outdated_info"
    HALLUCINATION = "hallucination"
    OTHER = "other"


class CorrectionSeverity(str, Enum):
    """Severity of the correction."""
    CRITICAL = "critical"
    IMPORTANT = "important"
    MINOR = "minor"
    STYLE = "style"


@dataclass
class ExtractedLesson:
    """A lesson extracted from a correction."""
    topic: str
    incorrect_info: str
    correct_info: str
    correction_type: CorrectionType
    severity: CorrectionSeverity
    entity: Optional[str] = None
    reasoning: str = ""
    should_update_database: bool = False
    memory_text: str = ""
    confidence: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "topic": self.topic,
            "incorrect_info": self.incorrect_info,
            "correct_info": self.correct_info,
            "correction_type": self.correction_type.value,
            "severity": self.severity.value,
            "entity": self.entity,
            "reasoning": self.reasoning,
            "should_update_database": self.should_update_database,
            "memory_text": self.memory_text,
            "confidence": self.confidence,
            "timestamp": self.timestamp,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExtractedLesson":
        return cls(
            topic=data.get("topic", ""),
            incorrect_info=data.get("incorrect_info", ""),
            correct_info=data.get("correct_info", ""),
            correction_type=CorrectionType(data.get("correction_type", "other")),
            severity=CorrectionSeverity(data.get("severity", "minor")),
            entity=data.get("entity"),
            reasoning=data.get("reasoning", ""),
            should_update_database=data.get("should_update_database", False),
            memory_text=data.get("memory_text", ""),
            confidence=data.get("confidence", 0.0),
            timestamp=data.get("timestamp", datetime.now().isoformat()),
        )


LESSON_EXTRACTION_PROMPT = """You are analyzing a correction to IRA's response.

Original reply by IRA:
{original_reply}

User's correction:
{correction}

Additional context (if any):
{context}

Extract the lesson from this correction. Return a JSON object with:
{{
    "topic": "What topic/area does this correction relate to?",
    "incorrect_info": "What was wrong in the original reply?",
    "correct_info": "What is the correct information?",
    "correction_type": "spec_correction|price_correction|fact_correction|tone_correction|format_correction|missing_info|outdated_info|hallucination|other",
    "severity": "critical|important|minor|style",
    "entity": "Entity this relates to (e.g., 'PF1-C-2015', 'HDPE processing', null if general)",
    "reasoning": "Brief explanation of why this correction matters",
    "should_update_database": true/false,
    "memory_text": "A natural language memory to store, formatted as: 'CORRECTION: When discussing [topic], remember that [correct_info]. Previously incorrectly stated: [incorrect_info]'"
}}

Severity guide:
- critical: Customer-facing factual errors, wrong prices, safety issues
- important: Significant inaccuracies that affect decisions
- minor: Small details, minor inaccuracies
- style: Tone, format, or style preferences

Be precise in extracting what was wrong and what is correct."""


class FeedbackLearner:
    """
    Learns from feedback and corrections to improve future responses.
    
    Workflow:
    1. User provides correction
    2. LLM extracts the lesson
    3. Lesson is stored in Mem0 with high priority
    4. Future queries retrieve relevant corrections
    5. Responses incorporate learned lessons
    """
    
    CORRECTION_USER_ID = "system_corrections"
    
    def __init__(self, model: str = None):
        """
        Initialize the feedback learner.
        
        Args:
            model: LLM model to use (defaults to FAST_LLM_MODEL)
        """
        self.model = model or FAST_LLM_MODEL
        self._client = None
        self._mem0 = None
        self._lessons_log_path = PROJECT_ROOT / "data" / "knowledge" / "correction_log.jsonl"
    
    @property
    def client(self):
        """Get OpenAI client lazily."""
        if self._client is None:
            if CONFIG_AVAILABLE:
                self._client = get_openai_client()
            else:
                try:
                    from openai import OpenAI
                    import os
                    self._client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
                except Exception:
                    self._client = None
        return self._client
    
    @property
    def mem0(self):
        """Get Mem0 service lazily."""
        if self._mem0 is None:
            try:
                from mem0_memory import get_mem0_service
            except ImportError:
                try:
                    from .mem0_memory import get_mem0_service
                except ImportError:
                    return None
            self._mem0 = get_mem0_service()
        return self._mem0
    
    def process_feedback(
        self,
        original_reply: str,
        correction: str,
        context: Optional[Dict[str, Any]] = None,
        identity_id: Optional[str] = None,
    ) -> Optional[ExtractedLesson]:
        """
        Process user feedback/correction and learn from it.
        
        Args:
            original_reply: IRA's original response that was corrected
            correction: The user's correction or feedback
            context: Additional context (query, entities, etc.)
            identity_id: ID of user providing correction
        
        Returns:
            ExtractedLesson if successful, None otherwise
        """
        if not original_reply or not correction:
            logger.warning("Empty original_reply or correction provided")
            return None
        
        try:
            lesson = self._extract_lesson(original_reply, correction, context)
            
            if lesson:
                self._store_lesson(lesson, identity_id)
                self._log_correction(lesson, original_reply, correction, identity_id)
                
                if lesson.should_update_database:
                    self._queue_database_update(lesson)
                
                logger.info(
                    f"Learned from correction: {lesson.correction_type.value} - "
                    f"{lesson.topic} (severity: {lesson.severity.value})"
                )
            
            return lesson
            
        except Exception as e:
            logger.error(f"Failed to process feedback: {e}")
            return None
    
    def _extract_lesson(
        self,
        original_reply: str,
        correction: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Optional[ExtractedLesson]:
        """Extract a structured lesson from the correction."""
        if not self.client:
            logger.warning("LLM client not available for lesson extraction")
            return self._extract_lesson_simple(original_reply, correction)
        
        context_str = json.dumps(context, default=str) if context else "None"
        
        prompt = LESSON_EXTRACTION_PROMPT.format(
            original_reply=original_reply[:2000],
            correction=correction[:1000],
            context=context_str[:500],
        )
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            response_format={"type": "json_object"},
        )
        
        result = json.loads(response.choices[0].message.content)
        
        lesson = ExtractedLesson(
            topic=result.get("topic", "general"),
            incorrect_info=result.get("incorrect_info", ""),
            correct_info=result.get("correct_info", ""),
            correction_type=CorrectionType(result.get("correction_type", "other")),
            severity=CorrectionSeverity(result.get("severity", "minor")),
            entity=result.get("entity"),
            reasoning=result.get("reasoning", ""),
            should_update_database=result.get("should_update_database", False),
            memory_text=result.get("memory_text", ""),
            confidence=0.9,
        )
        
        if not lesson.memory_text:
            lesson.memory_text = (
                f"CORRECTION: When discussing {lesson.topic}, "
                f"remember that {lesson.correct_info}. "
                f"Previously incorrectly stated: {lesson.incorrect_info}"
            )
        
        return lesson
    
    def _extract_lesson_simple(
        self,
        original_reply: str,
        correction: str,
    ) -> ExtractedLesson:
        """Simple rule-based lesson extraction (fallback)."""
        lesson = ExtractedLesson(
            topic="general",
            incorrect_info=original_reply[:200],
            correct_info=correction[:200],
            correction_type=CorrectionType.OTHER,
            severity=CorrectionSeverity.MINOR,
            confidence=0.5,
        )
        
        correction_lower = correction.lower()
        
        if any(w in correction_lower for w in ["price", "cost", "$", "inr", "usd"]):
            lesson.correction_type = CorrectionType.PRICE_CORRECTION
            lesson.severity = CorrectionSeverity.CRITICAL
        elif any(w in correction_lower for w in ["spec", "kw", "mm", "size", "dimension"]):
            lesson.correction_type = CorrectionType.SPEC_CORRECTION
            lesson.severity = CorrectionSeverity.IMPORTANT
        elif any(w in correction_lower for w in ["actually", "wrong", "incorrect", "not true"]):
            lesson.correction_type = CorrectionType.FACT_CORRECTION
            lesson.severity = CorrectionSeverity.IMPORTANT
        elif any(w in correction_lower for w in ["tone", "formal", "casual", "friendly"]):
            lesson.correction_type = CorrectionType.TONE_CORRECTION
            lesson.severity = CorrectionSeverity.STYLE
        
        lesson.memory_text = (
            f"CORRECTION: User corrected previous response. "
            f"The correction was: {correction[:300]}"
        )
        
        return lesson
    
    def _store_lesson(
        self,
        lesson: ExtractedLesson,
        identity_id: Optional[str] = None,
    ) -> Optional[str]:
        """Store the lesson in Mem0 with appropriate metadata."""
        if not self.mem0:
            logger.warning("Mem0 service not available for storing lesson")
            return None
        
        priority = {
            CorrectionSeverity.CRITICAL: "highest",
            CorrectionSeverity.IMPORTANT: "high",
            CorrectionSeverity.MINOR: "normal",
            CorrectionSeverity.STYLE: "low",
        }.get(lesson.severity, "normal")
        
        metadata = {
            "source": "correction",
            "correction_type": lesson.correction_type.value,
            "severity": lesson.severity.value,
            "priority": priority,
            "entity": lesson.entity,
            "timestamp": lesson.timestamp,
            "corrected_by": identity_id,
        }
        
        memory_id = self.mem0.add_memory(
            text=lesson.memory_text,
            user_id=self.CORRECTION_USER_ID,
            metadata=metadata,
        )
        
        if lesson.entity:
            entity_type = "machine" if "pf1" in lesson.entity.lower() or "am" in lesson.entity.lower() else "general"
            self.mem0.add_entity_memory(
                entity_type=entity_type,
                entity_name=lesson.entity,
                memory_text=lesson.memory_text,
                source_user_id=identity_id,
            )
        
        logger.info(f"Stored correction memory: {memory_id}")
        return memory_id
    
    def _log_correction(
        self,
        lesson: ExtractedLesson,
        original_reply: str,
        correction: str,
        identity_id: Optional[str],
    ) -> None:
        """Log the correction for audit purposes."""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "lesson": lesson.to_dict(),
            "original_reply_preview": original_reply[:500],
            "correction": correction[:500],
            "corrected_by": identity_id,
        }
        
        if CONFIG_AVAILABLE:
            append_jsonl(self._lessons_log_path, log_entry)
        else:
            self._lessons_log_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._lessons_log_path, "a") as f:
                f.write(json.dumps(log_entry, default=str) + "\n")
    
    def _queue_database_update(self, lesson: ExtractedLesson) -> None:
        """Queue a database update based on the correction."""
        if lesson.correction_type == CorrectionType.SPEC_CORRECTION and lesson.entity:
            update_entry = {
                "timestamp": datetime.now().isoformat(),
                "entity": lesson.entity,
                "field": "specification",
                "old_value": lesson.incorrect_info,
                "new_value": lesson.correct_info,
                "source": "user_correction",
                "status": "pending_review",
            }
            
            queue_path = PROJECT_ROOT / "data" / "knowledge" / "pending_db_updates.jsonl"
            if CONFIG_AVAILABLE:
                append_jsonl(queue_path, update_entry)
            else:
                queue_path.parent.mkdir(parents=True, exist_ok=True)
                with open(queue_path, "a") as f:
                    f.write(json.dumps(update_entry, default=str) + "\n")
            
            logger.info(f"Queued database update for {lesson.entity}")
    
    def get_relevant_corrections(
        self,
        query: str,
        limit: int = 5,
        threshold: float = 0.3,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant past corrections for a query.
        
        Args:
            query: The current user query
            limit: Maximum corrections to retrieve
            threshold: Minimum relevance score
        
        Returns:
            List of relevant corrections
        """
        if not self.mem0:
            return []
        
        try:
            memories = self.mem0.search(
                query=query,
                user_id=self.CORRECTION_USER_ID,
                limit=limit,
                threshold=threshold,
            )
            
            corrections = []
            for mem in memories:
                if mem.metadata.get("source") == "correction":
                    corrections.append({
                        "memory": mem.memory,
                        "correction_type": mem.metadata.get("correction_type"),
                        "severity": mem.metadata.get("severity"),
                        "entity": mem.metadata.get("entity"),
                        "score": mem.score,
                    })
            
            return corrections
            
        except Exception as e:
            logger.error(f"Failed to retrieve corrections: {e}")
            return []
    
    def get_correction_stats(self) -> Dict[str, Any]:
        """Get statistics about corrections."""
        stats = {
            "total_corrections": 0,
            "by_type": {},
            "by_severity": {},
            "recent_corrections": [],
        }
        
        if not self._lessons_log_path.exists():
            return stats
        
        try:
            with open(self._lessons_log_path) as f:
                for line in f:
                    try:
                        entry = json.loads(line)
                        lesson = entry.get("lesson", {})
                        
                        stats["total_corrections"] += 1
                        
                        ctype = lesson.get("correction_type", "other")
                        stats["by_type"][ctype] = stats["by_type"].get(ctype, 0) + 1
                        
                        severity = lesson.get("severity", "minor")
                        stats["by_severity"][severity] = stats["by_severity"].get(severity, 0) + 1
                        
                        if len(stats["recent_corrections"]) < 10:
                            stats["recent_corrections"].append({
                                "timestamp": entry.get("timestamp"),
                                "topic": lesson.get("topic"),
                                "type": ctype,
                            })
                    except json.JSONDecodeError:
                        continue
            
            stats["recent_corrections"] = stats["recent_corrections"][-10:]
            
        except Exception as e:
            logger.error(f"Failed to get correction stats: {e}")
        
        return stats


_learner: Optional[FeedbackLearner] = None


def get_feedback_learner() -> FeedbackLearner:
    """Get singleton FeedbackLearner instance."""
    global _learner
    if _learner is None:
        _learner = FeedbackLearner()
    return _learner


def process_feedback(
    original_reply: str,
    correction: str,
    context: Optional[Dict[str, Any]] = None,
    identity_id: Optional[str] = None,
) -> Optional[ExtractedLesson]:
    """
    Convenience function to process feedback.
    
    Args:
        original_reply: IRA's original response
        correction: User's correction
        context: Additional context
        identity_id: User providing correction
    
    Returns:
        ExtractedLesson if successful
    """
    return get_feedback_learner().process_feedback(
        original_reply, correction, context, identity_id
    )


def extract_lesson(
    original_reply: str,
    correction: str,
) -> Optional[ExtractedLesson]:
    """
    Convenience function to extract a lesson without storing.
    
    Useful for testing or preview.
    """
    return get_feedback_learner()._extract_lesson(original_reply, correction, None)


if __name__ == "__main__":
    learner = get_feedback_learner()
    
    print("Feedback Learner Test")
    print("=" * 60)
    
    test_cases = [
        {
            "original": "The PF1-C-2015 has a 50 kW ceramic heater system.",
            "correction": "Actually, the PF1-C-2015 has a 40 kW IR quartz heater, not ceramic.",
        },
        {
            "original": "The machine costs approximately $45,000.",
            "correction": "The price is actually $52,000 for the standard configuration.",
        },
        {
            "original": "Here's a detailed technical breakdown...",
            "correction": "Please keep responses shorter and more concise.",
        },
    ]
    
    for i, test in enumerate(test_cases):
        print(f"\nTest {i + 1}:")
        print(f"Original: {test['original'][:50]}...")
        print(f"Correction: {test['correction'][:50]}...")
        
        lesson = learner._extract_lesson_simple(test["original"], test["correction"])
        
        print(f"Type: {lesson.correction_type.value}")
        print(f"Severity: {lesson.severity.value}")
        print(f"Memory: {lesson.memory_text[:100]}...")
    
    print("\n" + "=" * 60)
    stats = learner.get_correction_stats()
    print(f"Total corrections logged: {stats['total_corrections']}")
