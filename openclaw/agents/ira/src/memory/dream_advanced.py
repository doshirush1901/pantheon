#!/usr/bin/env python3
"""
DREAM ADVANCED - Advanced Sleep Processing Features

╔════════════════════════════════════════════════════════════════════════════╗
║  Additional neuroscience-inspired features for Ira's dream cycle:          ║
║                                                                            ║
║  1. DREAM JOURNAL - Human-readable summary of what was learned             ║
║  2. MEMORY REPLAY - Compress and consolidate today's conversations         ║
║  3. CONFIDENCE CALIBRATION - Track prediction accuracy over time           ║
║  4. WAKE-UP SELF-TEST - Verify knowledge integrity after dreaming          ║
║  5. SCHEMA BUILDER - Group related facts into mental models                ║
║  6. EMOTIONAL MEMORY TAGGING - Prioritize by sentiment significance        ║
╚════════════════════════════════════════════════════════════════════════════╝
"""

import json
import os
import random
import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)

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
# 1. DREAM JOURNAL - Human-readable learning summary
# =============================================================================

@dataclass
class DreamJournalEntry:
    """A single dream journal entry."""
    date: str
    facts_learned: List[str]
    patterns_discovered: List[str]
    insights_generated: List[str]
    documents_processed: int
    memories_consolidated: int
    knowledge_gaps_found: List[str]
    emotional_highlights: List[str]
    self_test_results: Dict[str, Any]
    
    def to_telegram_message(self) -> str:
        """Format as a Telegram message (HTML mode for better compatibility)."""
        def escape_html(text: str) -> str:
            """Escape HTML special characters."""
            return (
                str(text)
                .replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
            )
        
        def truncate(text: str, max_len: int = 80) -> str:
            """Truncate and escape text."""
            text = escape_html(str(text)[:max_len])
            return text + "..." if len(str(text)) > max_len else text
        
        lines = [
            f"📔 <b>IRA DREAM JOURNAL</b> - {self.date}",
            "",
            "🌙 <i>Last night I processed:</i>",
            f"  • {self.documents_processed} documents",
            f"  • {self.memories_consolidated} memories consolidated",
            "",
        ]
        
        if self.facts_learned:
            lines.append("📚 <i>New facts learned:</i>")
            for fact in self.facts_learned[:5]:
                lines.append(f"  • {truncate(fact)}")
            if len(self.facts_learned) > 5:
                lines.append(f"  <i>...and {len(self.facts_learned) - 5} more</i>")
            lines.append("")
        
        if self.patterns_discovered:
            lines.append("🔍 <i>Patterns I noticed:</i>")
            for pattern in self.patterns_discovered[:3]:
                lines.append(f"  • {truncate(pattern)}")
            lines.append("")
        
        if self.insights_generated:
            lines.append("💡 <i>Creative insights:</i>")
            for insight in self.insights_generated[:3]:
                lines.append(f"  • {truncate(insight, 100)}")
            lines.append("")
        
        if self.knowledge_gaps_found:
            lines.append("⚠️ <i>Knowledge gaps to address:</i>")
            for gap in self.knowledge_gaps_found[:3]:
                lines.append(f"  • {truncate(gap)}")
            lines.append("")
        
        if self.emotional_highlights:
            lines.append("❤️ <i>Important interactions:</i>")
            for highlight in self.emotional_highlights[:2]:
                lines.append(f"  • {truncate(highlight)}")
            lines.append("")
        
        if self.self_test_results:
            score = self.self_test_results.get("score", 0)
            total = self.self_test_results.get("total", 0)
            lines.append(f"🧪 <i>Self-test: {score}/{total} correct</i>")
        
        lines.append("")
        lines.append("<i>Ready for a new day! 🌅</i>")
        
        return "\n".join(lines)
    
    def to_dict(self) -> Dict:
        return {
            "date": self.date,
            "facts_learned": self.facts_learned,
            "patterns_discovered": self.patterns_discovered,
            "insights_generated": self.insights_generated,
            "documents_processed": self.documents_processed,
            "memories_consolidated": self.memories_consolidated,
            "knowledge_gaps_found": self.knowledge_gaps_found,
            "emotional_highlights": self.emotional_highlights,
            "self_test_results": self.self_test_results,
        }


class DreamJournal:
    """Creates and manages dream journal entries."""
    
    def __init__(self):
        self._journal_file = PROJECT_ROOT / "data" / "dream_journal.json"
        self._entries: List[DreamJournalEntry] = []
        self._load()
    
    def _load(self):
        """Load journal entries."""
        if self._journal_file.exists():
            try:
                data = json.loads(self._journal_file.read_text())
                for entry_data in data:
                    self._entries.append(DreamJournalEntry(**entry_data))
            except Exception as e:
                print(f"[dream_journal] Load error: {e}")
    
    def _save(self):
        """Save journal entries."""
        self._journal_file.parent.mkdir(parents=True, exist_ok=True)
        data = [e.to_dict() for e in self._entries[-30:]]  # Keep last 30 days
        self._journal_file.write_text(json.dumps(data, indent=2))
    
    def create_entry(
        self,
        facts_learned: List[str] = None,
        patterns_discovered: List[str] = None,
        insights_generated: List[str] = None,
        documents_processed: int = 0,
        memories_consolidated: int = 0,
        knowledge_gaps_found: List[str] = None,
        emotional_highlights: List[str] = None,
        self_test_results: Dict = None,
    ) -> DreamJournalEntry:
        """Create a new journal entry for tonight's dream."""
        entry = DreamJournalEntry(
            date=datetime.now().strftime("%Y-%m-%d"),
            facts_learned=facts_learned or [],
            patterns_discovered=patterns_discovered or [],
            insights_generated=insights_generated or [],
            documents_processed=documents_processed,
            memories_consolidated=memories_consolidated,
            knowledge_gaps_found=knowledge_gaps_found or [],
            emotional_highlights=emotional_highlights or [],
            self_test_results=self_test_results or {},
        )
        
        self._entries.append(entry)
        self._save()
        
        return entry
    
    def send_to_telegram(self, entry: DreamJournalEntry) -> bool:
        """Send journal entry to Telegram."""
        try:
            import requests
            
            bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
            chat_id = os.environ.get("TELEGRAM_ADMIN_CHAT_ID") or os.environ.get("TELEGRAM_CHAT_ID")
            
            if not bot_token or not chat_id:
                print("[dream_journal] Telegram not configured")
                return False
            
            message = entry.to_telegram_message()
            
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            response = requests.post(url, json={
                "chat_id": chat_id,
                "text": message,
                "parse_mode": "HTML",
            }, timeout=10)
            
            if response.status_code == 200:
                print("[dream_journal] Sent to Telegram")
                return True
            else:
                print(f"[dream_journal] Telegram error: {response.text}")
                return False
                
        except Exception as e:
            print(f"[dream_journal] Telegram send error: {e}")
            return False
    
    def get_recent_entries(self, days: int = 7) -> List[DreamJournalEntry]:
        """Get entries from the last N days."""
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        return [e for e in self._entries if e.date >= cutoff]


# =============================================================================
# 2. MEMORY REPLAY - Compress today's conversations
# =============================================================================

@dataclass
class ReplayInsight:
    """An insight from replaying conversations."""
    category: str  # "frequent_question", "confusion", "success", "escalation"
    description: str
    frequency: int
    examples: List[str]
    action_suggested: str


class MemoryReplay:
    """
    Replays and compresses today's conversations.
    Like sleep replay in the brain - fast-forward through experiences.
    """
    
    def __init__(self):
        self._conversations_dir = PROJECT_ROOT / "data" / "conversations"
        self._replay_file = PROJECT_ROOT / "data" / "replay_insights.json"
        self._openai = None
    
    def _get_openai(self):
        if self._openai is None:
            from openai import OpenAI
            self._openai = OpenAI()
        return self._openai
    
    def _load_today_conversations(self) -> List[Dict]:
        """Load today's conversation logs."""
        conversations = []
        
        # Check episodes file
        episodes_file = PROJECT_ROOT / "data" / "mem0_storage" / "episodes.json"
        if episodes_file.exists():
            try:
                data = json.loads(episodes_file.read_text())
                today = datetime.now().strftime("%Y-%m-%d")
                
                for identity_id, eps in data.items():
                    for ep_id, ep in eps.items():
                        ts = ep.get("timestamp", "")
                        if ts.startswith(today):
                            conversations.append({
                                "user": identity_id,
                                "summary": ep.get("summary", ""),
                                "channel": ep.get("channel", ""),
                                "timestamp": ts,
                            })
            except Exception as e:
                print(f"[memory_replay] Load error: {e}")
        
        # Also check conversation logs if they exist
        if self._conversations_dir.exists():
            today = datetime.now().strftime("%Y-%m-%d")
            for f in self._conversations_dir.glob(f"*{today}*.json"):
                try:
                    conv_data = json.loads(f.read_text())
                    if isinstance(conv_data, list):
                        conversations.extend(conv_data)
                except Exception as e:
                    logger.error(f"Error in _load_today_conversations: {e}", exc_info=True)
        
        return conversations
    
    def replay_and_compress(self) -> Dict[str, Any]:
        """
        Replay today's conversations and extract compressed insights.
        """
        conversations = self._load_today_conversations()
        
        if not conversations:
            return {
                "conversations_replayed": 0,
                "insights": [],
                "summary": "No conversations to replay today.",
            }
        
        # Group by patterns
        question_types = defaultdict(list)
        channels = defaultdict(int)
        users = set()
        
        for conv in conversations:
            summary = conv.get("summary", "").lower()
            users.add(conv.get("user", "unknown"))
            channels[conv.get("channel", "unknown")] += 1
            
            # Categorize questions
            if "price" in summary or "cost" in summary or "quote" in summary:
                question_types["pricing"].append(summary)
            elif "spec" in summary or "feature" in summary or "capability" in summary:
                question_types["specifications"].append(summary)
            elif "delivery" in summary or "timeline" in summary or "when" in summary:
                question_types["delivery"].append(summary)
            elif "support" in summary or "help" in summary or "issue" in summary:
                question_types["support"].append(summary)
            else:
                question_types["general"].append(summary)
        
        # Generate insights
        insights = []
        
        for qtype, questions in question_types.items():
            if len(questions) >= 2:
                insights.append(ReplayInsight(
                    category="frequent_question",
                    description=f"Users frequently asked about {qtype} ({len(questions)} times)",
                    frequency=len(questions),
                    examples=questions[:3],
                    action_suggested=f"Ensure {qtype} information is easily accessible",
                ))
        
        # Use LLM for deeper compression if many conversations
        llm_summary = ""
        if len(conversations) >= 5:
            try:
                client = self._get_openai()
                
                conv_text = "\n".join([
                    f"- {c.get('summary', '')}" 
                    for c in conversations[:20]
                ])
                
                response = client.chat.completions.create(
                    model="gpt-4.1-mini",
                    messages=[
                        {
                            "role": "system",
                            "content": """You are analyzing a day's worth of customer conversations for a B2B sales AI.
Compress into 3-5 key learnings. Be specific and actionable.
Format: bullet points, each starting with an emoji."""
                        },
                        {
                            "role": "user",
                            "content": f"Today's conversations:\n{conv_text}\n\nWhat should I remember from today?"
                        }
                    ],
                    max_tokens=300,
                )
                
                llm_summary = response.choices[0].message.content
                
            except Exception as e:
                print(f"[memory_replay] LLM compression error: {e}")
        
        result = {
            "conversations_replayed": len(conversations),
            "unique_users": len(users),
            "channels": dict(channels),
            "insights": [
                {
                    "category": i.category,
                    "description": i.description,
                    "frequency": i.frequency,
                    "action": i.action_suggested,
                }
                for i in insights
            ],
            "llm_summary": llm_summary,
            "question_distribution": {k: len(v) for k, v in question_types.items()},
        }
        
        # Save replay results
        self._replay_file.parent.mkdir(parents=True, exist_ok=True)
        self._replay_file.write_text(json.dumps(result, indent=2))
        
        return result


# =============================================================================
# 3. CONFIDENCE CALIBRATION - Track accuracy over time
# =============================================================================

@dataclass
class CalibrationDataPoint:
    """A single prediction with stated confidence and actual outcome."""
    query: str
    response_snippet: str
    stated_confidence: float  # What Ira said (0-1)
    was_correct: bool  # Was the answer actually correct?
    timestamp: str
    source: str  # How we know it was correct/incorrect


class ConfidenceCalibrator:
    """
    Tracks prediction accuracy to calibrate confidence estimates.
    
    Goal: If Ira says "80% confident", it should be right 80% of the time.
    """
    
    def __init__(self):
        self._calibration_file = PROJECT_ROOT / "data" / "confidence_calibration.json"
        self._data_points: List[CalibrationDataPoint] = []
        self._load()
    
    def _load(self):
        """Load calibration data."""
        if self._calibration_file.exists():
            try:
                data = json.loads(self._calibration_file.read_text())
                for dp in data.get("data_points", []):
                    self._data_points.append(CalibrationDataPoint(**dp))
            except Exception as e:
                print(f"[calibrator] Load error: {e}")
    
    def _save(self):
        """Save calibration data."""
        self._calibration_file.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "data_points": [
                {
                    "query": dp.query,
                    "response_snippet": dp.response_snippet,
                    "stated_confidence": dp.stated_confidence,
                    "was_correct": dp.was_correct,
                    "timestamp": dp.timestamp,
                    "source": dp.source,
                }
                for dp in self._data_points[-500:]  # Keep last 500
            ],
            "last_updated": datetime.now().isoformat(),
        }
        self._calibration_file.write_text(json.dumps(data, indent=2))
    
    def record_prediction(
        self,
        query: str,
        response_snippet: str,
        stated_confidence: float,
        was_correct: bool,
        source: str = "feedback",
    ):
        """Record a prediction outcome for calibration."""
        self._data_points.append(CalibrationDataPoint(
            query=query,
            response_snippet=response_snippet[:200],
            stated_confidence=stated_confidence,
            was_correct=was_correct,
            timestamp=datetime.now().isoformat(),
            source=source,
        ))
        self._save()
    
    def get_calibration_curve(self) -> Dict[str, float]:
        """
        Calculate calibration curve.
        
        Returns accuracy for each confidence bucket.
        """
        if len(self._data_points) < 10:
            return {"insufficient_data": True}
        
        # Bucket by confidence level
        buckets = {
            "0.0-0.2": {"correct": 0, "total": 0},
            "0.2-0.4": {"correct": 0, "total": 0},
            "0.4-0.6": {"correct": 0, "total": 0},
            "0.6-0.8": {"correct": 0, "total": 0},
            "0.8-1.0": {"correct": 0, "total": 0},
        }
        
        for dp in self._data_points:
            conf = dp.stated_confidence
            if conf < 0.2:
                bucket = "0.0-0.2"
            elif conf < 0.4:
                bucket = "0.2-0.4"
            elif conf < 0.6:
                bucket = "0.4-0.6"
            elif conf < 0.8:
                bucket = "0.6-0.8"
            else:
                bucket = "0.8-1.0"
            
            buckets[bucket]["total"] += 1
            if dp.was_correct:
                buckets[bucket]["correct"] += 1
        
        # Calculate accuracy per bucket
        curve = {}
        for bucket, counts in buckets.items():
            if counts["total"] > 0:
                curve[bucket] = {
                    "accuracy": counts["correct"] / counts["total"],
                    "sample_size": counts["total"],
                }
            else:
                curve[bucket] = {"accuracy": None, "sample_size": 0}
        
        return curve
    
    def get_calibration_score(self) -> float:
        """
        Calculate overall calibration score.
        
        Perfect calibration = 1.0 (stated confidence matches actual accuracy)
        """
        curve = self.get_calibration_curve()
        
        if "insufficient_data" in curve:
            return 0.5  # Default when no data
        
        # Calculate mean absolute error between stated and actual
        errors = []
        bucket_midpoints = {
            "0.0-0.2": 0.1,
            "0.2-0.4": 0.3,
            "0.4-0.6": 0.5,
            "0.6-0.8": 0.7,
            "0.8-1.0": 0.9,
        }
        
        for bucket, data in curve.items():
            if data.get("accuracy") is not None and data["sample_size"] >= 3:
                expected = bucket_midpoints[bucket]
                actual = data["accuracy"]
                errors.append(abs(expected - actual))
        
        if not errors:
            return 0.5
        
        # Convert MAE to a 0-1 score (lower error = higher score)
        mae = sum(errors) / len(errors)
        score = 1.0 - mae
        
        return max(0.0, min(1.0, score))
    
    def suggest_adjustment(self, stated_confidence: float) -> float:
        """
        Suggest adjusted confidence based on calibration data.
        
        If Ira is overconfident, dial it back.
        """
        curve = self.get_calibration_curve()
        
        if "insufficient_data" in curve:
            return stated_confidence
        
        # Find the bucket
        if stated_confidence < 0.2:
            bucket = "0.0-0.2"
        elif stated_confidence < 0.4:
            bucket = "0.2-0.4"
        elif stated_confidence < 0.6:
            bucket = "0.4-0.6"
        elif stated_confidence < 0.8:
            bucket = "0.6-0.8"
        else:
            bucket = "0.8-1.0"
        
        data = curve.get(bucket, {})
        actual_accuracy = data.get("accuracy")
        
        if actual_accuracy is None or data.get("sample_size", 0) < 5:
            return stated_confidence
        
        # Adjust towards actual accuracy
        adjustment_factor = 0.3  # How much to adjust
        adjusted = stated_confidence + adjustment_factor * (actual_accuracy - stated_confidence)
        
        return max(0.0, min(1.0, adjusted))


# =============================================================================
# 4. WAKE-UP SELF-TEST - Verify knowledge after dreaming
# =============================================================================

@dataclass
class SelfTestQuestion:
    """A self-test question."""
    question: str
    expected_answer: str
    category: str
    source: str


@dataclass
class SelfTestResult:
    """Result of a single test."""
    question: str
    expected: str
    actual: str
    is_correct: bool
    confidence: float


class WakeUpSelfTest:
    """
    Tests Ira's knowledge after dreaming to verify integrity.
    Like a morning self-check before starting the day.
    """
    
    def __init__(self):
        self._test_bank_file = PROJECT_ROOT / "data" / "self_test_bank.json"
        self._results_file = PROJECT_ROOT / "data" / "self_test_results.json"
        self._test_bank: List[SelfTestQuestion] = []
        self._openai = None
        self._load_test_bank()
    
    def _get_openai(self):
        if self._openai is None:
            from openai import OpenAI
            self._openai = OpenAI()
        return self._openai
    
    def _load_test_bank(self):
        """Load or generate test questions."""
        if self._test_bank_file.exists():
            try:
                data = json.loads(self._test_bank_file.read_text())
                for q in data:
                    self._test_bank.append(SelfTestQuestion(**q))
            except Exception as e:
                print(f"[self_test] Load error: {e}")
        
        # Add some default questions if bank is empty
        if not self._test_bank:
            self._generate_default_questions()
    
    def _generate_default_questions(self):
        """Generate default test questions about core knowledge."""
        defaults = [
            SelfTestQuestion(
                question="What company does Ira work for?",
                expected_answer="Machinecraft",
                category="identity",
                source="core",
            ),
            SelfTestQuestion(
                question="What type of machines does Machinecraft make?",
                expected_answer="thermoforming machines",
                category="product",
                source="core",
            ),
            SelfTestQuestion(
                question="What is PF1?",
                expected_answer="A thermoforming machine series by Machinecraft",
                category="product",
                source="core",
            ),
            SelfTestQuestion(
                question="Who is Ira's creator?",
                expected_answer="Sales Director",
                category="identity",
                source="core",
            ),
        ]
        self._test_bank.extend(defaults)
        self._save_test_bank()
    
    def _save_test_bank(self):
        """Save test bank."""
        self._test_bank_file.parent.mkdir(parents=True, exist_ok=True)
        data = [
            {
                "question": q.question,
                "expected_answer": q.expected_answer,
                "category": q.category,
                "source": q.source,
            }
            for q in self._test_bank
        ]
        self._test_bank_file.write_text(json.dumps(data, indent=2))
    
    def add_question(self, question: str, expected_answer: str, category: str = "learned"):
        """Add a new test question to the bank."""
        self._test_bank.append(SelfTestQuestion(
            question=question,
            expected_answer=expected_answer,
            category=category,
            source="dream",
        ))
        self._save_test_bank()
    
    def run_test(self, num_questions: int = 5) -> Dict[str, Any]:
        """
        Run a self-test with random questions.
        """
        if not self._test_bank:
            return {"error": "No test questions available"}
        
        # Select random questions
        questions = random.sample(
            self._test_bank,
            min(num_questions, len(self._test_bank))
        )
        
        results = []
        client = self._get_openai()
        
        for q in questions:
            try:
                # Ask Ira (via LLM) to answer
                response = client.chat.completions.create(
                    model="gpt-4.1-mini",
                    messages=[
                        {
                            "role": "system",
                            "content": """You are Ira, an AI sales assistant for Machinecraft (thermoforming machines).
Answer the question briefly and directly. If unsure, say "I'm not sure"."""
                        },
                        {"role": "user", "content": q.question}
                    ],
                    max_tokens=100,
                )
                
                actual_answer = response.choices[0].message.content.strip()
                
                # Check if correct (semantic similarity)
                is_correct = self._check_answer(actual_answer, q.expected_answer)
                
                results.append(SelfTestResult(
                    question=q.question,
                    expected=q.expected_answer,
                    actual=actual_answer,
                    is_correct=is_correct,
                    confidence=0.8 if is_correct else 0.3,
                ))
                
            except Exception as e:
                print(f"[self_test] Question error: {e}")
                results.append(SelfTestResult(
                    question=q.question,
                    expected=q.expected_answer,
                    actual=f"Error: {e}",
                    is_correct=False,
                    confidence=0.0,
                ))
        
        # Calculate score
        correct = sum(1 for r in results if r.is_correct)
        total = len(results)
        
        test_result = {
            "score": correct,
            "total": total,
            "percentage": correct / total if total > 0 else 0,
            "results": [
                {
                    "question": r.question,
                    "expected": r.expected,
                    "actual": r.actual,
                    "correct": r.is_correct,
                }
                for r in results
            ],
            "timestamp": datetime.now().isoformat(),
        }
        
        # Save results
        self._results_file.parent.mkdir(parents=True, exist_ok=True)
        self._results_file.write_text(json.dumps(test_result, indent=2))
        
        return test_result
    
    def _check_answer(self, actual: str, expected: str) -> bool:
        """Check if actual answer matches expected (fuzzy match)."""
        actual_lower = actual.lower()
        expected_lower = expected.lower()
        
        # Direct containment
        if expected_lower in actual_lower:
            return True
        
        # Key word matching
        expected_words = set(expected_lower.split())
        actual_words = set(actual_lower.split())
        
        # At least 50% of expected words should be in actual
        overlap = len(expected_words & actual_words)
        if len(expected_words) > 0 and overlap / len(expected_words) >= 0.5:
            return True
        
        return False


# =============================================================================
# 5. SCHEMA BUILDER - Group facts into mental models
# =============================================================================

@dataclass
class KnowledgeSchema:
    """A mental model grouping related facts."""
    name: str
    entity_type: str  # "product", "customer", "process", "market"
    core_facts: List[str]
    related_entities: List[str]
    common_questions: List[str]
    last_updated: str
    
    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "entity_type": self.entity_type,
            "core_facts": self.core_facts,
            "related_entities": self.related_entities,
            "common_questions": self.common_questions,
            "last_updated": self.last_updated,
        }


class SchemaBuilder:
    """
    Builds mental models (schemas) from scattered facts.
    
    Instead of 50 separate PF1 facts, creates a unified PF1 schema.
    """
    
    def __init__(self):
        self._schemas_file = PROJECT_ROOT / "data" / "knowledge_schemas.json"
        self._schemas: Dict[str, KnowledgeSchema] = {}
        self._openai = None
        self._load()
    
    def _get_openai(self):
        if self._openai is None:
            from openai import OpenAI
            self._openai = OpenAI()
        return self._openai
    
    def _load(self):
        """Load existing schemas."""
        if self._schemas_file.exists():
            try:
                data = json.loads(self._schemas_file.read_text())
                for name, schema_data in data.items():
                    self._schemas[name] = KnowledgeSchema(**schema_data)
            except Exception as e:
                print(f"[schema_builder] Load error: {e}")
    
    def _save(self):
        """Save schemas."""
        self._schemas_file.parent.mkdir(parents=True, exist_ok=True)
        data = {name: schema.to_dict() for name, schema in self._schemas.items()}
        self._schemas_file.write_text(json.dumps(data, indent=2))
    
    def build_schema_from_facts(
        self,
        entity_name: str,
        facts: List[str],
        entity_type: str = "product",
    ) -> KnowledgeSchema:
        """
        Build a schema from a list of facts about an entity.
        """
        if not facts:
            return None
        
        # Use LLM to organize facts into a coherent schema
        try:
            client = self._get_openai()
            
            facts_text = "\n".join([f"- {f}" for f in facts[:20]])
            
            response = client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[
                    {
                        "role": "system",
                        "content": """You are organizing facts about an entity into a coherent mental model.

Output JSON:
{
    "core_facts": ["most important fact 1", "fact 2", ...],
    "related_entities": ["related thing 1", ...],
    "common_questions": ["question users might ask 1", ...]
}

Keep core_facts to 5-7 most important. Be concise."""
                    },
                    {
                        "role": "user",
                        "content": f"Entity: {entity_name}\nType: {entity_type}\n\nFacts:\n{facts_text}"
                    }
                ],
                max_tokens=500,
            )
            
            result_text = response.choices[0].message.content
            
            # Parse JSON
            import re
            json_match = re.search(r'\{[^{}]+\}', result_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                
                schema = KnowledgeSchema(
                    name=entity_name,
                    entity_type=entity_type,
                    core_facts=result.get("core_facts", facts[:5]),
                    related_entities=result.get("related_entities", []),
                    common_questions=result.get("common_questions", []),
                    last_updated=datetime.now().isoformat(),
                )
                
                self._schemas[entity_name] = schema
                self._save()
                
                return schema
                
        except Exception as e:
            print(f"[schema_builder] Build error: {e}")
        
        # Fallback: simple schema
        schema = KnowledgeSchema(
            name=entity_name,
            entity_type=entity_type,
            core_facts=facts[:5],
            related_entities=[],
            common_questions=[],
            last_updated=datetime.now().isoformat(),
        )
        
        self._schemas[entity_name] = schema
        self._save()
        
        return schema
    
    def get_schema(self, entity_name: str) -> Optional[KnowledgeSchema]:
        """Get schema for an entity."""
        return self._schemas.get(entity_name)
    
    def list_schemas(self) -> List[str]:
        """List all schema names."""
        return list(self._schemas.keys())
    
    def auto_discover_schemas(self) -> List[KnowledgeSchema]:
        """
        Auto-discover entities and build schemas from knowledge files.
        """
        discovered = []
        
        # Scan knowledge files for entities
        knowledge_dir = PROJECT_ROOT / "data" / "knowledge"
        if not knowledge_dir.exists():
            return discovered
        
        entity_facts = defaultdict(list)
        
        for f in knowledge_dir.glob("*.json"):
            try:
                data = json.loads(f.read_text())
                if isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict):
                            entity = item.get("entity") or item.get("name") or item.get("model")
                            text = item.get("text") or item.get("content") or item.get("fact")
                            if entity and text:
                                entity_facts[entity].append(text)
            except Exception as e:
                logger.error(f"Error in auto_discover_schemas: {e}", exc_info=True)
        
        # Build schemas for entities with enough facts
        for entity, facts in entity_facts.items():
            if len(facts) >= 3 and entity not in self._schemas:
                schema = self.build_schema_from_facts(entity, facts)
                if schema:
                    discovered.append(schema)
        
        return discovered


# =============================================================================
# 6. EMOTIONAL MEMORY TAGGING - Prioritize by sentiment
# =============================================================================

@dataclass
class EmotionalTag:
    """Emotional tag for a memory/interaction."""
    memory_id: str
    content_snippet: str
    emotion: str  # "positive", "negative", "frustrated", "excited", "neutral"
    intensity: float  # 0-1
    priority_boost: float  # How much to boost retention
    timestamp: str


class EmotionalMemoryTagger:
    """
    Tags memories with emotional significance.
    
    Frustrated customer interaction = HIGH priority retention
    Routine question = normal decay
    """
    
    def __init__(self):
        self._tags_file = PROJECT_ROOT / "data" / "emotional_tags.json"
        self._tags: Dict[str, EmotionalTag] = {}
        self._openai = None
        self._load()
    
    def _get_openai(self):
        if self._openai is None:
            from openai import OpenAI
            self._openai = OpenAI()
        return self._openai
    
    def _load(self):
        """Load emotional tags."""
        if self._tags_file.exists():
            try:
                data = json.loads(self._tags_file.read_text())
                for mid, tag_data in data.items():
                    self._tags[mid] = EmotionalTag(**tag_data)
            except Exception as e:
                print(f"[emotional_tagger] Load error: {e}")
    
    def _save(self):
        """Save emotional tags."""
        self._tags_file.parent.mkdir(parents=True, exist_ok=True)
        data = {
            mid: {
                "memory_id": tag.memory_id,
                "content_snippet": tag.content_snippet,
                "emotion": tag.emotion,
                "intensity": tag.intensity,
                "priority_boost": tag.priority_boost,
                "timestamp": tag.timestamp,
            }
            for mid, tag in self._tags.items()
        }
        self._tags_file.write_text(json.dumps(data, indent=2))
    
    def analyze_emotion(self, content: str) -> Tuple[str, float]:
        """
        Analyze emotional content of text.
        Returns (emotion, intensity).
        """
        # Simple keyword-based detection first
        content_lower = content.lower()
        
        negative_words = ["frustrated", "angry", "disappointed", "problem", "issue", "wrong", "bad", "terrible", "horrible", "unhappy", "complaint"]
        positive_words = ["happy", "great", "excellent", "thank", "appreciate", "wonderful", "amazing", "perfect", "love", "fantastic"]
        urgent_words = ["urgent", "asap", "immediately", "critical", "emergency"]
        
        negative_count = sum(1 for w in negative_words if w in content_lower)
        positive_count = sum(1 for w in positive_words if w in content_lower)
        urgent_count = sum(1 for w in urgent_words if w in content_lower)
        
        if urgent_count > 0:
            return "urgent", 0.9
        elif negative_count > positive_count and negative_count >= 2:
            return "frustrated", min(0.9, 0.5 + negative_count * 0.1)
        elif negative_count > positive_count:
            return "negative", min(0.7, 0.4 + negative_count * 0.1)
        elif positive_count > negative_count and positive_count >= 2:
            return "excited", min(0.8, 0.5 + positive_count * 0.1)
        elif positive_count > 0:
            return "positive", min(0.6, 0.3 + positive_count * 0.1)
        else:
            return "neutral", 0.3
    
    def tag_memory(self, memory_id: str, content: str) -> EmotionalTag:
        """
        Tag a memory with emotional significance.
        """
        emotion, intensity = self.analyze_emotion(content)
        
        # Calculate priority boost based on emotion
        priority_boost = {
            "urgent": 2.0,
            "frustrated": 1.8,
            "negative": 1.5,
            "excited": 1.3,
            "positive": 1.1,
            "neutral": 1.0,
        }.get(emotion, 1.0)
        
        tag = EmotionalTag(
            memory_id=memory_id,
            content_snippet=content[:200],
            emotion=emotion,
            intensity=intensity,
            priority_boost=priority_boost,
            timestamp=datetime.now().isoformat(),
        )
        
        self._tags[memory_id] = tag
        self._save()
        
        return tag
    
    def get_high_priority_memories(self, threshold: float = 1.3) -> List[EmotionalTag]:
        """Get memories with high emotional priority."""
        return [
            tag for tag in self._tags.values()
            if tag.priority_boost >= threshold
        ]
    
    def tag_todays_interactions(self) -> Dict[str, Any]:
        """
        Tag all of today's interactions with emotions.
        """
        episodes_file = PROJECT_ROOT / "data" / "mem0_storage" / "episodes.json"
        if not episodes_file.exists():
            return {"tagged": 0}
        
        try:
            data = json.loads(episodes_file.read_text())
            today = datetime.now().strftime("%Y-%m-%d")
            
            tagged_count = 0
            emotions_found = defaultdict(int)
            
            for identity_id, eps in data.items():
                for ep_id, ep in eps.items():
                    ts = ep.get("timestamp", "")
                    if ts.startswith(today):
                        content = ep.get("summary", "")
                        tag = self.tag_memory(ep_id, content)
                        tagged_count += 1
                        emotions_found[tag.emotion] += 1
            
            return {
                "tagged": tagged_count,
                "emotions": dict(emotions_found),
                "high_priority": len(self.get_high_priority_memories()),
            }
            
        except Exception as e:
            print(f"[emotional_tagger] Tagging error: {e}")
            return {"error": str(e)}


# =============================================================================
# UNIFIED RUNNER
# =============================================================================

class DreamAdvancedRunner:
    """Run all advanced dream features."""
    
    def __init__(self):
        self.journal = DreamJournal()
        self.replay = MemoryReplay()
        self.calibrator = ConfidenceCalibrator()
        self.self_test = WakeUpSelfTest()
        self.schema_builder = SchemaBuilder()
        self.emotional_tagger = EmotionalMemoryTagger()
    
    def run_all(
        self,
        facts_learned: List[str] = None,
        patterns_discovered: List[str] = None,
        insights_generated: List[str] = None,
        documents_processed: int = 0,
        send_telegram: bool = True,
        verbose: bool = True,
    ) -> Dict[str, Any]:
        """
        Run all advanced dream features.
        """
        results = {}
        
        # 1. Memory Replay
        if verbose:
            print("\n📼 Phase A1: Memory Replay...")
        replay_results = self.replay.replay_and_compress()
        results["replay"] = replay_results
        if verbose:
            print(f"   Conversations replayed: {replay_results.get('conversations_replayed', 0)}")
            print(f"   Insights: {len(replay_results.get('insights', []))}")
        
        # 2. Emotional Tagging
        if verbose:
            print("\n❤️ Phase A2: Emotional Memory Tagging...")
        emotion_results = self.emotional_tagger.tag_todays_interactions()
        results["emotions"] = emotion_results
        if verbose:
            print(f"   Tagged: {emotion_results.get('tagged', 0)} interactions")
            print(f"   High priority: {emotion_results.get('high_priority', 0)}")
        
        # 3. Schema Discovery
        if verbose:
            print("\n🧩 Phase A3: Schema Building...")
        new_schemas = self.schema_builder.auto_discover_schemas()
        results["schemas"] = {
            "discovered": len(new_schemas),
            "total": len(self.schema_builder.list_schemas()),
        }
        if verbose:
            print(f"   New schemas: {len(new_schemas)}")
            print(f"   Total schemas: {results['schemas']['total']}")
        
        # 4. Confidence Calibration Check
        if verbose:
            print("\n📊 Phase A4: Confidence Calibration...")
        calibration_score = self.calibrator.get_calibration_score()
        results["calibration"] = {
            "score": calibration_score,
            "curve": self.calibrator.get_calibration_curve(),
        }
        if verbose:
            print(f"   Calibration score: {calibration_score:.2f}")
        
        # 5. Wake-up Self-Test
        if verbose:
            print("\n🧪 Phase A5: Wake-up Self-Test...")
        test_results = self.self_test.run_test(num_questions=5)
        results["self_test"] = test_results
        if verbose:
            score = test_results.get("score", 0)
            total = test_results.get("total", 0)
            print(f"   Score: {score}/{total}")
        
        # 6. Create Dream Journal
        if verbose:
            print("\n📔 Phase A6: Creating Dream Journal...")
        
        # Gather emotional highlights
        high_priority = self.emotional_tagger.get_high_priority_memories()
        emotional_highlights = [
            f"[{t.emotion.upper()}] {t.content_snippet[:50]}..."
            for t in high_priority[:3]
        ]
        
        # Get knowledge gaps from replay
        knowledge_gaps = [
            i.get("description", "")
            for i in replay_results.get("insights", [])
            if i.get("category") == "confusion"
        ]
        
        journal_entry = self.journal.create_entry(
            facts_learned=facts_learned or [],
            patterns_discovered=patterns_discovered or [],
            insights_generated=insights_generated or [],
            documents_processed=documents_processed,
            memories_consolidated=emotion_results.get("tagged", 0),
            knowledge_gaps_found=knowledge_gaps,
            emotional_highlights=emotional_highlights,
            self_test_results=test_results,
        )
        
        results["journal"] = journal_entry.to_dict()
        
        if verbose:
            print("   Journal entry created")
        
        # Send to Telegram
        if send_telegram:
            if verbose:
                print("\n📱 Sending journal to Telegram...")
            sent = self.journal.send_to_telegram(journal_entry)
            results["telegram_sent"] = sent
        
        return results


# =============================================================================
# CLI
# =============================================================================

def run_advanced_dream(
    facts_learned: List[str] = None,
    patterns: List[str] = None,
    insights: List[str] = None,
    docs_processed: int = 0,
    verbose: bool = True,
) -> Dict[str, Any]:
    """Convenience function to run all advanced dream features."""
    runner = DreamAdvancedRunner()
    return runner.run_all(
        facts_learned=facts_learned,
        patterns_discovered=patterns,
        insights_generated=insights,
        documents_processed=docs_processed,
        verbose=verbose,
    )


if __name__ == "__main__":
    print("=" * 60)
    print("DREAM ADVANCED - Running all features")
    print("=" * 60)
    
    results = run_advanced_dream(
        facts_learned=["Test fact 1", "Test fact 2"],
        patterns=["Test pattern"],
        insights=["Test insight"],
        docs_processed=5,
        verbose=True,
    )
    
    print("\n" + "=" * 60)
    print("COMPLETE")
    print("=" * 60)
