#!/usr/bin/env python3
"""
INTERACTION LEARNER - Extract Learnings from Daily Conversations
================================================================

Every email and Telegram message contains potential learnings:
- Corrections ("No, that's wrong. The PF1 is a vacuum forming machine")
- New facts ("Minerex is our customer already")
- Preferences ("I prefer detailed specs over summaries")
- Entity knowledge ("The AM Series is for material up to 2mm thickness")

This module runs nightly to extract and store these learnings.

Usage:
    python interaction_learner.py              # Learn from today's conversations
    python interaction_learner.py --days 7     # Learn from last 7 days
    python interaction_learner.py --dry-run    # Preview without storing
"""

import json
import os
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum

# =============================================================================
# PATH SETUP
# =============================================================================

BRAIN_DIR = Path(__file__).parent
SKILLS_DIR = BRAIN_DIR.parent
AGENT_DIR = SKILLS_DIR.parent
PROJECT_ROOT = BRAIN_DIR.parent.parent.parent.parent.parent

sys.path.insert(0, str(AGENT_DIR))
sys.path.insert(0, str(BRAIN_DIR))

# Load environment
env_file = PROJECT_ROOT / ".env"
if env_file.exists():
    for line in env_file.read_text().splitlines():
        if line.strip() and not line.startswith('#') and '=' in line:
            key, _, value = line.partition('=')
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if not os.environ.get(key):
                os.environ[key] = value

# Config
try:
    from config import get_logger, COLLECTIONS, EMBEDDING_MODEL_VOYAGE
    logger = get_logger("interaction_learner")
except ImportError:
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("interaction_learner")
    COLLECTIONS = {"dream_knowledge": "ira_dream_knowledge_v1"}
    EMBEDDING_MODEL_VOYAGE = "voyage-3"

# Memory Controller
try:
    sys.path.insert(0, str(SKILLS_DIR / "memory"))
    from memory_controller import remember, MemoryType
    MEMORY_CONTROLLER_AVAILABLE = True
except ImportError:
    MEMORY_CONTROLLER_AVAILABLE = False
    logger.warning("Memory controller not available")

# Log paths
TELEGRAM_ACTIVITY_LOG = PROJECT_ROOT / "crm" / "logs" / "telegram_activity_log.json"
EMAIL_REQUESTS_LOG = PROJECT_ROOT / "crm" / "logs" / "requests.jsonl"
LEARNINGS_STATE_FILE = PROJECT_ROOT / "openclaw" / "agents" / "ira" / "workspace" / "interaction_learner_state.json"

# OpenAI for extraction
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")


class LearningType(Enum):
    """Types of learnings we can extract."""
    CORRECTION = "correction"           # User corrected Ira's response
    FACT = "fact"                       # New factual information
    PREFERENCE = "preference"           # User preference revealed
    ENTITY_KNOWLEDGE = "entity"         # Knowledge about an entity (customer, product)
    PROCESS = "process"                 # How to do something
    CONSTRAINT = "constraint"           # What NOT to do


@dataclass
class ExtractedLearning:
    """A learning extracted from a conversation."""
    learning_type: LearningType
    content: str                        # The learning itself
    confidence: float                   # How confident we are (0-1)
    source_channel: str                 # "telegram" or "email"
    source_message: str                 # The original message
    source_response: str                # Ira's response that was corrected/supplemented
    user_id: str
    timestamp: datetime
    entity: Optional[str] = None        # Related entity (product, customer, etc.)
    
    def to_memory_text(self) -> str:
        """Convert to a storable memory fact."""
        prefix_map = {
            LearningType.CORRECTION: "CORRECTION",
            LearningType.FACT: "FACT",
            LearningType.PREFERENCE: "USER PREFERS",
            LearningType.ENTITY_KNOWLEDGE: "ENTITY KNOWLEDGE",
            LearningType.PROCESS: "PROCESS",
            LearningType.CONSTRAINT: "CONSTRAINT",
        }
        prefix = prefix_map.get(self.learning_type, "LEARNING")
        return f"{prefix}: {self.content}"


@dataclass
class LearningResult:
    """Result of a learning extraction run."""
    conversations_analyzed: int = 0
    learnings_extracted: int = 0
    learnings_stored: int = 0
    learnings_by_type: Dict[str, int] = field(default_factory=dict)
    duration_seconds: float = 0.0
    errors: List[str] = field(default_factory=list)
    sample_learnings: List[str] = field(default_factory=list)


class InteractionLearner:
    """
    Extract and store learnings from daily interactions.
    
    Analyzes Telegram and email conversations to find:
    - Corrections (when user corrects Ira)
    - New facts shared by users
    - User preferences
    - Entity-specific knowledge
    """
    
    # Patterns that indicate a correction
    CORRECTION_PATTERNS = [
        r"no[,!.]+\s*(that'?s|it'?s|you'?re)\s*(wrong|incorrect|not right)",
        r"no[!]+",  # Strong no
        r"(wrong|incorrect|mistake|error)",
        r"(actually|in fact|to clarify|correction)",
        r"(should be|is actually|is really|meant to be)",
        r"(pls|please)\s*(correct|fix|update|change)",
        r"(can'?t be|not|never)\s+\w+\s*[-–—]\s*(it|should|must)",
        r"that'?s not (true|correct|right|accurate)",
    ]
    
    # Patterns that indicate sharing new information
    INFO_SHARING_PATTERNS = [
        r"(is|are)\s+(our|a|an|the)\s+(customer|client|partner|supplier)",
        r"(we|i)\s+(use|have|own|bought|purchased)",
        r"(always|usually|typically|normally)\s+\w+",
        r"(prefer|like|want)\s+\w+",
        r"(maximum|minimum|up to|at least)\s+\d+",
        r"(for|used for|designed for)\s+(material|thickness|size)",
    ]
    
    def __init__(self):
        self._openai = None
        self._qdrant = None
        self._voyage = None
        self.state = self._load_state()
    
    def _get_openai(self):
        """Get OpenAI client (lazy init)."""
        if self._openai is None and OPENAI_API_KEY:
            import openai
            self._openai = openai.OpenAI(api_key=OPENAI_API_KEY)
        return self._openai
    
    def _get_qdrant(self):
        """Get Qdrant client (lazy init)."""
        if self._qdrant is None:
            try:
                from qdrant_client import QdrantClient
                qdrant_url = os.environ.get("QDRANT_URL", "http://localhost:6333")
                self._qdrant = QdrantClient(url=qdrant_url, timeout=30)
            except Exception as e:
                logger.warning(f"Qdrant unavailable: {e}")
        return self._qdrant
    
    def _get_voyage(self):
        """Get Voyage client (lazy init)."""
        if self._voyage is None:
            voyage_key = os.environ.get("VOYAGE_API_KEY", "")
            if voyage_key:
                try:
                    import voyageai
                    self._voyage = voyageai.Client(api_key=voyage_key)
                except Exception as e:
                    logger.warning(f"Voyage unavailable: {e}")
        return self._voyage
    
    def _load_state(self) -> Dict:
        """Load learner state."""
        if LEARNINGS_STATE_FILE.exists():
            try:
                return json.loads(LEARNINGS_STATE_FILE.read_text())
            except Exception:
                pass
        return {
            "last_run": None,
            "last_telegram_timestamp": None,
            "last_email_timestamp": None,
            "total_learnings": 0,
        }
    
    def _save_state(self):
        """Save learner state."""
        LEARNINGS_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        LEARNINGS_STATE_FILE.write_text(json.dumps(self.state, indent=2, default=str))
    
    def _load_telegram_conversations(self, since: datetime) -> List[Dict]:
        """Load Telegram conversations since a given time."""
        conversations = []
        
        if not TELEGRAM_ACTIVITY_LOG.exists():
            logger.debug("Telegram activity log not found")
            return conversations
        
        try:
            data = json.loads(TELEGRAM_ACTIVITY_LOG.read_text())
            
            for entry in data:
                ts_str = entry.get("timestamp", "")
                if not ts_str:
                    continue
                
                try:
                    ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                    ts = ts.replace(tzinfo=None)  # Remove timezone for comparison
                except ValueError:
                    continue
                
                if ts >= since and entry.get("message"):
                    conversations.append({
                        "channel": "telegram",
                        "timestamp": ts,
                        "user_id": entry.get("from_user", ""),
                        "message": entry.get("message", ""),
                        "response": "",  # Will try to match from requests.jsonl
                        "trace_id": entry.get("trace_id", ""),
                    })
        except Exception as e:
            logger.error(f"Error loading Telegram log: {e}")
        
        return conversations
    
    def _load_email_conversations(self, since: datetime) -> List[Dict]:
        """Load email/request conversations since a given time."""
        conversations = []
        
        if not EMAIL_REQUESTS_LOG.exists():
            logger.debug("Email requests log not found")
            return conversations
        
        try:
            with open(EMAIL_REQUESTS_LOG, 'r') as f:
                for line in f:
                    if not line.strip():
                        continue
                    
                    try:
                        entry = json.loads(line)
                        ts_str = entry.get("timestamp", "")
                        if not ts_str:
                            continue
                        
                        ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                        ts = ts.replace(tzinfo=None)
                        
                        if ts >= since:
                            conversations.append({
                                "channel": entry.get("channel", "unknown"),
                                "timestamp": ts,
                                "user_id": entry.get("user_id", ""),
                                "message": entry.get("message_preview", ""),
                                "response": entry.get("response_preview", ""),
                                "trace_id": entry.get("trace_id", ""),
                            })
                    except (json.JSONDecodeError, ValueError):
                        continue
        except Exception as e:
            logger.error(f"Error loading email log: {e}")
        
        return conversations
    
    def _is_correction(self, message: str) -> bool:
        """Check if a message looks like a correction."""
        message_lower = message.lower()
        for pattern in self.CORRECTION_PATTERNS:
            if re.search(pattern, message_lower):
                return True
        return False
    
    def _extract_learnings_llm(
        self,
        message: str,
        response: str,
        context: Dict
    ) -> List[ExtractedLearning]:
        """Use LLM to extract learnings from a conversation turn."""
        client = self._get_openai()
        if not client:
            return []
        
        # Skip very short or trivial messages
        if len(message) < 10:
            return []
        
        # Skip greetings/commands
        trivial_patterns = [r'^(hi|hey|hello|bye|thanks|ok|yes|no|/\w+)$']
        for pattern in trivial_patterns:
            if re.match(pattern, message.lower().strip()):
                return []
        
        prompt = f"""Analyze this conversation between a user and Ira (AI sales assistant for Machinecraft thermoforming machines).
Extract any learnings that Ira should remember for future conversations.

User message: {message[:500]}
Ira's response: {response[:500] if response else "(no response recorded)"}

Extract learnings in these categories:
1. CORRECTION: User corrected something Ira said wrong
2. FACT: User shared a factual piece of information
3. ENTITY_KNOWLEDGE: Information about a specific entity (customer, product, etc.)
4. PREFERENCE: User's preference or style
5. CONSTRAINT: Something Ira should NOT do

Return JSON array (empty if no learnings):
[
  {{
    "type": "correction|fact|entity|preference|constraint",
    "content": "The specific learning to remember",
    "entity": "entity name if applicable (product model, customer name)",
    "confidence": 0.8
  }}
]

Rules:
- Only extract substantive learnings (not "user said hi")
- Be specific and actionable
- If user corrected Ira, capture what the correct information is
- Return empty array [] if nothing worth learning"""

        try:
            response_obj = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Extract learnings as JSON only. Return [] if nothing to learn."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1000,
                temperature=0.3,
            )
            
            text = response_obj.choices[0].message.content.strip()
            
            # Parse JSON
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]
            
            learnings_data = json.loads(text)
            
            if not isinstance(learnings_data, list):
                return []
            
            learnings = []
            type_map = {
                "correction": LearningType.CORRECTION,
                "fact": LearningType.FACT,
                "entity": LearningType.ENTITY_KNOWLEDGE,
                "entity_knowledge": LearningType.ENTITY_KNOWLEDGE,
                "preference": LearningType.PREFERENCE,
                "constraint": LearningType.CONSTRAINT,
                "process": LearningType.PROCESS,
            }
            
            for item in learnings_data:
                learning_type = type_map.get(item.get("type", "").lower(), LearningType.FACT)
                
                learnings.append(ExtractedLearning(
                    learning_type=learning_type,
                    content=item.get("content", ""),
                    confidence=item.get("confidence", 0.7),
                    source_channel=context.get("channel", "unknown"),
                    source_message=message[:200],
                    source_response=response[:200] if response else "",
                    user_id=context.get("user_id", ""),
                    timestamp=context.get("timestamp", datetime.now()),
                    entity=item.get("entity"),
                ))
            
            return learnings
            
        except Exception as e:
            logger.error(f"LLM extraction error: {e}")
            return []
    
    def _store_learning(self, learning: ExtractedLearning) -> bool:
        """Store a learning in memory systems."""
        stored = False
        memory_text = learning.to_memory_text()
        
        # 1. Try Memory Controller (intelligent routing)
        if MEMORY_CONTROLLER_AVAILABLE:
            try:
                result = remember(
                    content=memory_text,
                    source="interaction_learning",
                    entity_name=learning.entity,
                    context={
                        "learning_type": learning.learning_type.value,
                        "channel": learning.source_channel,
                        "confidence": learning.confidence,
                        "timestamp": learning.timestamp.isoformat(),
                    }
                )
                
                if result.get("action") in ["create", "reinforce"]:
                    stored = True
                    logger.debug(f"Stored via MemoryController: {memory_text[:50]}...")
            except Exception as e:
                logger.warning(f"MemoryController error: {e}")
        
        # 2. Store in Qdrant for RAG retrieval
        qdrant = self._get_qdrant()
        voyage = self._get_voyage()
        
        if qdrant and voyage:
            try:
                import uuid
                from qdrant_client.models import PointStruct
                
                # Generate embedding
                embedding = voyage.embed(
                    [memory_text],
                    model=EMBEDDING_MODEL_VOYAGE,
                    input_type="document"
                ).embeddings[0]
                
                # Store in dream knowledge collection
                collection = COLLECTIONS.get("dream_knowledge", "ira_dream_knowledge_v1")
                
                qdrant.upsert(
                    collection_name=collection,
                    points=[PointStruct(
                        id=uuid.uuid4().hex,
                        vector=embedding,
                        payload={
                            "text": memory_text,
                            "raw_text": memory_text,
                            "source": "interaction_learning",
                            "learning_type": learning.learning_type.value,
                            "channel": learning.source_channel,
                            "entity": learning.entity,
                            "confidence": learning.confidence,
                            "indexed_at": datetime.now().isoformat(),
                        }
                    )]
                )
                stored = True
                logger.debug(f"Stored in Qdrant: {memory_text[:50]}...")
                
            except Exception as e:
                logger.warning(f"Qdrant store error: {e}")
        
        return stored
    
    def learn(
        self,
        days: int = 1,
        dry_run: bool = False
    ) -> LearningResult:
        """
        Extract and store learnings from recent conversations.
        
        Args:
            days: How many days back to look
            dry_run: If True, extract but don't store
        
        Returns:
            LearningResult with statistics
        """
        import time
        start_time = time.time()
        result = LearningResult()
        
        logger.info("=" * 60)
        logger.info("INTERACTION LEARNER - Extracting learnings from conversations")
        logger.info("=" * 60)
        
        since = datetime.now() - timedelta(days=days)
        logger.info(f"Analyzing conversations since: {since}")
        
        # Load conversations from both channels
        conversations = []
        conversations.extend(self._load_email_conversations(since))
        
        # Sort by timestamp
        conversations.sort(key=lambda x: x["timestamp"])
        
        logger.info(f"Found {len(conversations)} conversations to analyze")
        result.conversations_analyzed = len(conversations)
        
        if not conversations:
            logger.info("No conversations to analyze")
            result.duration_seconds = time.time() - start_time
            return result
        
        # Analyze conversations for learnings
        all_learnings = []
        
        # Process in batches to avoid rate limits
        batch_size = 20
        for i in range(0, len(conversations), batch_size):
            batch = conversations[i:i+batch_size]
            
            for conv in batch:
                # Quick pre-filter: skip trivial messages
                message = conv.get("message", "").strip()
                if len(message) < 15:
                    continue
                
                # Check if this looks like it contains learnings
                response = conv.get("response", "")
                
                # Higher priority for corrections
                is_likely_correction = self._is_correction(message)
                
                # Extract learnings
                learnings = self._extract_learnings_llm(
                    message=message,
                    response=response,
                    context=conv
                )
                
                for learning in learnings:
                    if is_likely_correction and learning.learning_type != LearningType.CORRECTION:
                        learning.confidence = min(0.9, learning.confidence + 0.1)
                    
                    if learning.confidence >= 0.5:
                        all_learnings.append(learning)
        
        result.learnings_extracted = len(all_learnings)
        logger.info(f"Extracted {len(all_learnings)} learnings")
        
        # Count by type
        for learning in all_learnings:
            type_name = learning.learning_type.value
            result.learnings_by_type[type_name] = result.learnings_by_type.get(type_name, 0) + 1
        
        # Store learnings
        if not dry_run:
            for learning in all_learnings:
                if self._store_learning(learning):
                    result.learnings_stored += 1
                    
                    # Sample for report
                    if len(result.sample_learnings) < 5:
                        result.sample_learnings.append(learning.to_memory_text()[:100])
            
            # Update state
            self.state["last_run"] = datetime.now().isoformat()
            self.state["total_learnings"] = self.state.get("total_learnings", 0) + result.learnings_stored
            self._save_state()
        else:
            # In dry run, show what would be stored
            for learning in all_learnings[:10]:
                result.sample_learnings.append(learning.to_memory_text()[:100])
        
        result.duration_seconds = time.time() - start_time
        
        # Summary
        logger.info("")
        logger.info("=" * 60)
        logger.info("INTERACTION LEARNING COMPLETE")
        logger.info("=" * 60)
        logger.info(f"Conversations analyzed: {result.conversations_analyzed}")
        logger.info(f"Learnings extracted: {result.learnings_extracted}")
        logger.info(f"Learnings stored: {result.learnings_stored}")
        logger.info(f"By type: {result.learnings_by_type}")
        logger.info(f"Duration: {result.duration_seconds:.1f}s")
        
        if result.sample_learnings:
            logger.info("\nSample learnings:")
            for sample in result.sample_learnings[:3]:
                logger.info(f"  • {sample}")
        
        return result


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

_learner: Optional[InteractionLearner] = None


def get_interaction_learner() -> InteractionLearner:
    """Get singleton learner instance."""
    global _learner
    if _learner is None:
        _learner = InteractionLearner()
    return _learner


def run_interaction_learning(days: int = 1, dry_run: bool = False) -> LearningResult:
    """Run interaction learning."""
    return get_interaction_learner().learn(days=days, dry_run=dry_run)


# =============================================================================
# CLI
# =============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Extract learnings from daily conversations")
    parser.add_argument("--days", type=int, default=1, help="Days to look back")
    parser.add_argument("--dry-run", action="store_true", help="Extract but don't store")
    args = parser.parse_args()
    
    learner = InteractionLearner()
    result = learner.learn(days=args.days, dry_run=args.dry_run)
    
    print(f"\nResult: {json.dumps({
        'conversations_analyzed': result.conversations_analyzed,
        'learnings_extracted': result.learnings_extracted,
        'learnings_stored': result.learnings_stored,
        'by_type': result.learnings_by_type,
        'duration': f'{result.duration_seconds:.1f}s',
    }, indent=2)}")
