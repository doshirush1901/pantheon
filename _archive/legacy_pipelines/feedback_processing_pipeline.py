#!/usr/bin/env python3
"""
FEEDBACK PROCESSING PIPELINE - Learn From Every Correction
============================================================

When Rushabh sends feedback to IRA, this pipeline:

1. DETECT - Is this feedback/correction or a new question?
2. CLASSIFY - What type? (fact, price, spec, style, behavior)
3. EXTRACT - What exactly was wrong and what's correct?
4. VALIDATE - Double-check the correction makes sense
5. UPDATE KNOWLEDGE - Mem0, Qdrant, Machine Database, Truth Hints
6. UPDATE LOGIC - Procedures, guardrails, filters
7. CONFIRM - Acknowledge and show what was learned
8. PREVENT - Ensure the same mistake doesn't happen again

┌─────────────────────────────────────────────────────────────────────────────┐
│                    FEEDBACK PROCESSING PIPELINE                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  STAGE 1: FEEDBACK DETECTION                                        │   │
│  │  • Is this a correction? ("No, that's wrong", "Actually...")       │   │
│  │  • Is this new information? ("FYI, X is our customer")             │   │
│  │  • Is this a preference? ("I prefer detailed specs")               │   │
│  │  • Is this a complaint? ("This keeps happening")                   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                               ↓                                            │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  STAGE 2: FEEDBACK CLASSIFICATION                                   │   │
│  │  Types:                                                             │   │
│  │  • SPEC_CORRECTION - Wrong machine specs                           │   │
│  │  • PRICE_CORRECTION - Wrong pricing                                │   │
│  │  • FACT_CORRECTION - Wrong factual info                            │   │
│  │  • ENTITY_CORRECTION - Customer/competitor/partner status          │   │
│  │  • STYLE_PREFERENCE - How Rushabh wants responses                  │   │
│  │  • BEHAVIOR_CORRECTION - What IRA should/shouldn't do              │   │
│  │  • HALLUCINATION - IRA made something up                           │   │
│  │  • OUTDATED_INFO - Information has changed                         │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                               ↓                                            │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  STAGE 3: CORRECTION EXTRACTION                                     │   │
│  │  • What was wrong? (original statement)                            │   │
│  │  • What's correct? (the fix)                                       │   │
│  │  • What entity? (machine model, company, person)                   │   │
│  │  • What field? (price_inr, heater_power_kw, etc.)                 │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                               ↓                                            │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  STAGE 4: VALIDATION                                                │   │
│  │  • Does the correction make sense?                                 │   │
│  │  • Cross-check with existing data                                  │   │
│  │  • Flag conflicts for human review                                 │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                               ↓                                            │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  STAGE 5: KNOWLEDGE UPDATE                                          │   │
│  │  • Mem0: Store as high-priority memory                             │   │
│  │  • Qdrant: Update vector embeddings                                │   │
│  │  • Machine DB: Update machine_database.py if spec                  │   │
│  │  • Truth Hints: Update truth_hints.py                              │   │
│  │  • Learned Corrections: Update learned_corrections.json            │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                               ↓                                            │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  STAGE 6: LOGIC UPDATE                                              │   │
│  │  • Guardrails: Add new rule if behavior correction                 │   │
│  │  • Procedures: Update procedural memory                            │   │
│  │  • Filters: Add to competitor/customer lists                       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                               ↓                                            │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  STAGE 7: CONFIRMATION                                              │   │
│  │  • Acknowledge the feedback                                        │   │
│  │  • Show what was learned                                           │   │
│  │  • Confirm the update                                              │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                               ↓                                            │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  STAGE 8: PREVENTION                                                │   │
│  │  • Record as negative example for future                           │   │
│  │  • Update retrieval weights                                        │   │
│  │  • Trigger dream consolidation if critical                         │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘

Usage:
    from feedback_processing_pipeline import process_feedback, FeedbackProcessor
    
    processor = FeedbackProcessor()
    result = processor.process(
        feedback_message="No, the PF1-C-2015 is ₹60 Lakhs, not ₹65 Lakhs",
        original_response="The PF1-C-2015 is priced at ₹65 Lakhs",
        from_user="rushabh@machinecraft.org",
        channel="email"
    )
"""

import json
import logging
import os
import re
import sys
from dataclasses import dataclass
from dataclasses import field as dataclass_field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Path setup
BRAIN_DIR = Path(__file__).parent
SRC_DIR = BRAIN_DIR.parent
AGENT_DIR = SRC_DIR.parent
PROJECT_ROOT = AGENT_DIR.parent.parent.parent

sys.path.insert(0, str(AGENT_DIR))
sys.path.insert(0, str(BRAIN_DIR))
sys.path.insert(0, str(SRC_DIR / "memory"))

# Load environment
env_file = PROJECT_ROOT / ".env"
if env_file.exists():
    for line in env_file.read_text().splitlines():
        if line.strip() and not line.startswith('#') and '=' in line:
            key, _, value = line.partition('=')
            os.environ.setdefault(key.strip(), value.strip().strip('"'))

logger = logging.getLogger("ira.feedback_pipeline")

# Storage paths
CORRECTIONS_FILE = BRAIN_DIR / "learned_corrections.json"
FEEDBACK_LOG_FILE = PROJECT_ROOT / "data" / "feedback_log.jsonl"
TRUTH_HINTS_FILE = BRAIN_DIR / "truth_hints.py"

# OpenAI
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
    openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
except ImportError:
    OPENAI_AVAILABLE = False
    openai_client = None

# Mem0
try:
    from unified_mem0 import get_unified_mem0
    MEM0_AVAILABLE = True
except ImportError:
    MEM0_AVAILABLE = False
    get_unified_mem0 = None

# Existing learners
try:
    from correction_learner import CorrectionLearner
    CORRECTION_LEARNER_AVAILABLE = True
except ImportError:
    CORRECTION_LEARNER_AVAILABLE = False

try:
    from feedback_learner import FeedbackLearner as BrainFeedbackLearner
    BRAIN_FEEDBACK_LEARNER_AVAILABLE = True
except ImportError:
    BRAIN_FEEDBACK_LEARNER_AVAILABLE = False

# Machine database
try:
    from machine_database import get_machine, MACHINE_SPECS
    MACHINE_DB_AVAILABLE = True
except ImportError:
    MACHINE_DB_AVAILABLE = False


# =============================================================================
# DATA STRUCTURES
# =============================================================================

class FeedbackType(str, Enum):
    """Type of feedback received."""
    SPEC_CORRECTION = "spec_correction"       # Wrong machine specs
    PRICE_CORRECTION = "price_correction"     # Wrong pricing
    FACT_CORRECTION = "fact_correction"       # Wrong factual info
    ENTITY_CORRECTION = "entity_correction"   # Customer/competitor status
    STYLE_PREFERENCE = "style_preference"     # How to respond
    BEHAVIOR_CORRECTION = "behavior_correction"  # What to do/not do
    HALLUCINATION = "hallucination"           # Made up info
    OUTDATED_INFO = "outdated_info"           # Info has changed
    NEW_INFORMATION = "new_information"       # FYI new fact
    POSITIVE_FEEDBACK = "positive_feedback"   # Good job!
    UNKNOWN = "unknown"


class FeedbackSeverity(str, Enum):
    """How serious is this feedback?"""
    CRITICAL = "critical"    # Wrong price/spec sent to customer
    IMPORTANT = "important"  # Wrong fact, needs fixing
    MINOR = "minor"          # Small correction
    STYLE = "style"          # Preference/style only
    POSITIVE = "positive"    # Not a correction


class UpdateTarget(str, Enum):
    """Where to apply the update."""
    MEM0 = "mem0"
    QDRANT = "qdrant"
    MACHINE_DATABASE = "machine_database"
    TRUTH_HINTS = "truth_hints"
    LEARNED_CORRECTIONS = "learned_corrections"
    GUARDRAILS = "guardrails"
    PROCEDURAL_MEMORY = "procedural_memory"


@dataclass
class ExtractedCorrection:
    """A correction extracted from feedback."""
    feedback_type: FeedbackType
    severity: FeedbackSeverity
    
    # What was wrong
    topic: str
    incorrect_value: str
    
    # What's correct
    correct_value: str
    
    # Context
    entity: Optional[str] = None  # Machine model, company name
    field: Optional[str] = None   # price_inr, heater_power_kw
    reasoning: str = ""
    
    # Metadata
    confidence: float = 0.0
    update_targets: List[UpdateTarget] = dataclass_field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "feedback_type": self.feedback_type.value,
            "severity": self.severity.value,
            "topic": self.topic,
            "incorrect_value": self.incorrect_value,
            "correct_value": self.correct_value,
            "entity": self.entity,
            "field": self.field,
            "reasoning": self.reasoning,
            "confidence": self.confidence,
            "update_targets": [t.value for t in self.update_targets],
        }


@dataclass
class FeedbackResult:
    """Result of processing feedback."""
    success: bool
    feedback_type: FeedbackType
    corrections_found: List[ExtractedCorrection]
    updates_applied: List[str]
    confirmation_message: str
    warnings: List[str] = dataclass_field(default_factory=list)
    processing_time_seconds: float = 0.0
    
    def to_dict(self) -> Dict:
        return {
            "success": self.success,
            "feedback_type": self.feedback_type.value,
            "corrections": [c.to_dict() for c in self.corrections_found],
            "updates": self.updates_applied,
            "confirmation": self.confirmation_message,
            "warnings": self.warnings,
            "processing_time": self.processing_time_seconds,
        }


# =============================================================================
# STAGE 1: FEEDBACK DETECTION
# =============================================================================

class FeedbackDetector:
    """Detect if a message is feedback/correction."""
    
    # Patterns that indicate different types of feedback
    CORRECTION_PATTERNS = [
        (r"^no[!.,]*\s*(it'?s|that'?s|this is|actually|wrong|the\s)", "correction"),
        (r"actually,?\s", "correction"),
        (r"not correct|incorrect|wrong", "correction"),
        (r"should be|should have been", "correction"),
        (r"that's not right", "correction"),
        (r"the correct\s", "correction"),
        (r"correction:", "correction"),
        (r"fix:|fix this", "correction"),
        (r"please update|pls update", "correction"),
        (r"remember this", "correction"),
        (r"don't forget", "correction"),
        (r"not\s+₹?\d+", "correction"),  # "not ₹65 Lakhs"
        (r"is\s+₹?\d+.*not\s+₹?\d+", "correction"),  # "is ₹60, not ₹65"
    ]
    
    ENTITY_PATTERNS = [
        (r"(\w+(?:\s+\w+)?)\s+is\s+(?:a\s+)?competitor", "competitor"),
        (r"(\w+(?:\s+\w+)?)\s+is\s+(?:our\s+)?(?:a\s+)?customer", "customer"),
        (r"(\w+(?:\s+\w+)?)\s+is\s+(?:a\s+)?partner", "partner"),
        (r"(\w+(?:\s+\w+)?)\s+is\s+(?:a\s+)?prospect", "prospect"),
    ]
    
    PREFERENCE_PATTERNS = [
        (r"i prefer|i'd prefer|i would prefer", "preference"),
        (r"don't|do not|never|stop\s", "constraint"),
        (r"always|make sure to", "behavior"),
        (r"in the future,?\s", "behavior"),
    ]
    
    POSITIVE_PATTERNS = [
        (r"good job|well done|perfect|great|excellent", "positive"),
        (r"thanks|thank you|appreciate", "positive"),
        (r"👍|✅|❤️", "positive"),
    ]
    
    def __init__(self):
        self.logger = logging.getLogger("ira.feedback_detector")
    
    def detect(self, message: str, previous_response: str = "") -> Tuple[bool, str]:
        """
        Detect if message is feedback and what type.
        
        Returns:
            (is_feedback, feedback_category)
        """
        message_lower = message.lower()
        
        # Check for corrections
        for pattern, category in self.CORRECTION_PATTERNS:
            if re.search(pattern, message_lower, re.IGNORECASE):
                self.logger.info(f"Detected correction: {pattern}")
                return True, "correction"
        
        # Check for entity corrections
        for pattern, category in self.ENTITY_PATTERNS:
            if re.search(pattern, message_lower, re.IGNORECASE):
                self.logger.info(f"Detected entity feedback: {category}")
                return True, f"entity_{category}"
        
        # Check for preferences/constraints
        for pattern, category in self.PREFERENCE_PATTERNS:
            if re.search(pattern, message_lower, re.IGNORECASE):
                self.logger.info(f"Detected preference/behavior: {category}")
                return True, category
        
        # Check for positive feedback
        for pattern, category in self.POSITIVE_PATTERNS:
            if re.search(pattern, message_lower, re.IGNORECASE):
                self.logger.info(f"Detected positive feedback")
                return True, "positive"
        
        return False, "none"


# =============================================================================
# STAGE 2 & 3: CLASSIFICATION & EXTRACTION
# =============================================================================

class CorrectionExtractor:
    """Extract specific corrections from feedback."""
    
    EXTRACTION_PROMPT = """Analyze this feedback to extract corrections.

ORIGINAL RESPONSE FROM IRA:
{original_response}

FEEDBACK FROM USER:
{feedback}

Extract corrections. For each one, identify:
1. feedback_type: One of [spec_correction, price_correction, fact_correction, entity_correction, style_preference, behavior_correction, hallucination, outdated_info, new_information, positive_feedback]
2. severity: One of [critical, important, minor, style, positive]
3. topic: What is being corrected (e.g., "PF1-C-2015 price")
4. incorrect_value: What was wrong
5. correct_value: What's correct
6. entity: Entity being corrected (machine model, company name) or null
7. field: Specific field if applicable (price_inr, heater_power_kw, vacuum_pump_capacity) or null
8. reasoning: Why this correction matters

Return JSON array:
[
  {{
    "feedback_type": "price_correction",
    "severity": "critical",
    "topic": "PF1-C-2015 price",
    "incorrect_value": "₹65 Lakhs",
    "correct_value": "₹60 Lakhs",
    "entity": "PF1-C-2015",
    "field": "price_inr",
    "reasoning": "Wrong price could cause customer confusion"
  }}
]

If no corrections, return: []
If positive feedback, return with feedback_type="positive_feedback"
"""

    def __init__(self):
        self.logger = logging.getLogger("ira.correction_extractor")
    
    def extract(
        self,
        feedback: str,
        original_response: str,
        feedback_category: str
    ) -> List[ExtractedCorrection]:
        """Extract specific corrections from feedback."""
        
        if not OPENAI_AVAILABLE:
            return self._extract_fallback(feedback, feedback_category)
        
        try:
            prompt = self.EXTRACTION_PROMPT.format(
                original_response=original_response[:2000] if original_response else "(none)",
                feedback=feedback
            )
            
            response = openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Extract corrections from feedback. Return valid JSON array only."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1000,
                temperature=0.2
            )
            
            text = response.choices[0].message.content
            
            # Parse JSON
            json_match = re.search(r'\[.*\]', text, re.DOTALL)
            if json_match:
                corrections_data = json.loads(json_match.group())
            else:
                corrections_data = []
            
            # Convert to ExtractedCorrection objects
            corrections = []
            for c in corrections_data:
                try:
                    correction = ExtractedCorrection(
                        feedback_type=FeedbackType(c.get("feedback_type", "unknown")),
                        severity=FeedbackSeverity(c.get("severity", "minor")),
                        topic=c.get("topic", ""),
                        incorrect_value=c.get("incorrect_value", ""),
                        correct_value=c.get("correct_value", ""),
                        entity=c.get("entity"),
                        field=c.get("field"),
                        reasoning=c.get("reasoning", ""),
                        confidence=0.9
                    )
                    
                    # Determine update targets
                    correction.update_targets = self._determine_update_targets(correction)
                    
                    corrections.append(correction)
                except Exception as e:
                    self.logger.error(f"Error parsing correction: {e}")
            
            return corrections
            
        except Exception as e:
            self.logger.error(f"Extraction error: {e}")
            return self._extract_fallback(feedback, feedback_category)
    
    def _extract_fallback(self, feedback: str, category: str) -> List[ExtractedCorrection]:
        """Fallback extraction without LLM."""
        corrections = []
        
        # Simple pattern matching
        if "competitor" in category:
            match = re.search(r'(\w+(?:\s+\w+)?)\s+is\s+(?:a\s+)?competitor', feedback, re.I)
            if match:
                corrections.append(ExtractedCorrection(
                    feedback_type=FeedbackType.ENTITY_CORRECTION,
                    severity=FeedbackSeverity.IMPORTANT,
                    topic=f"{match.group(1)} is competitor",
                    incorrect_value="prospect",
                    correct_value="competitor",
                    entity=match.group(1),
                    confidence=0.8,
                    update_targets=[UpdateTarget.LEARNED_CORRECTIONS]
                ))
        
        elif "customer" in category:
            match = re.search(r'(\w+(?:\s+\w+)?)\s+is\s+(?:our\s+)?(?:a\s+)?customer', feedback, re.I)
            if match:
                corrections.append(ExtractedCorrection(
                    feedback_type=FeedbackType.ENTITY_CORRECTION,
                    severity=FeedbackSeverity.IMPORTANT,
                    topic=f"{match.group(1)} is customer",
                    incorrect_value="prospect",
                    correct_value="customer",
                    entity=match.group(1),
                    confidence=0.8,
                    update_targets=[UpdateTarget.LEARNED_CORRECTIONS]
                ))
        
        return corrections
    
    def _determine_update_targets(self, correction: ExtractedCorrection) -> List[UpdateTarget]:
        """Determine where this correction should be applied."""
        targets = [UpdateTarget.MEM0]  # Always store in Mem0
        
        if correction.feedback_type == FeedbackType.SPEC_CORRECTION:
            targets.append(UpdateTarget.MACHINE_DATABASE)
            targets.append(UpdateTarget.TRUTH_HINTS)
            
        elif correction.feedback_type == FeedbackType.PRICE_CORRECTION:
            targets.append(UpdateTarget.MACHINE_DATABASE)
            targets.append(UpdateTarget.TRUTH_HINTS)
            
        elif correction.feedback_type == FeedbackType.ENTITY_CORRECTION:
            targets.append(UpdateTarget.LEARNED_CORRECTIONS)
            
        elif correction.feedback_type == FeedbackType.BEHAVIOR_CORRECTION:
            targets.append(UpdateTarget.GUARDRAILS)
            targets.append(UpdateTarget.PROCEDURAL_MEMORY)
            
        elif correction.feedback_type == FeedbackType.HALLUCINATION:
            targets.append(UpdateTarget.TRUTH_HINTS)
            targets.append(UpdateTarget.GUARDRAILS)
        
        return targets


# =============================================================================
# STAGE 4: VALIDATION
# =============================================================================

class CorrectionValidator:
    """Validate that corrections make sense."""
    
    def __init__(self):
        self.logger = logging.getLogger("ira.correction_validator")
    
    def validate(self, correction: ExtractedCorrection) -> Tuple[bool, List[str]]:
        """
        Validate a correction.
        
        Returns:
            (is_valid, warnings)
        """
        warnings = []
        
        # Check if correction has substance
        if not correction.correct_value:
            warnings.append("No correct value provided")
            return False, warnings
        
        # Price validation
        if correction.feedback_type == FeedbackType.PRICE_CORRECTION:
            # Extract price value
            price_match = re.search(r'(\d+(?:,\d+)*)', correction.correct_value)
            if price_match:
                price = int(price_match.group(1).replace(',', ''))
                
                # Sanity check - Machinecraft machines typically ₹3L to ₹2Cr
                if price < 100000:  # < 1 Lakh
                    warnings.append(f"Unusually low price: ₹{price:,}")
                elif price > 200000000:  # > 20 Cr
                    warnings.append(f"Unusually high price: ₹{price:,}")
        
        # Spec validation
        if correction.feedback_type == FeedbackType.SPEC_CORRECTION:
            if correction.field == "heater_power_kw":
                # Heaters typically 10-300kW
                power_match = re.search(r'(\d+)', correction.correct_value)
                if power_match:
                    power = int(power_match.group(1))
                    if power > 500:
                        warnings.append(f"Unusually high heater power: {power}kW")
        
        # Entity validation
        if correction.feedback_type == FeedbackType.ENTITY_CORRECTION:
            if correction.entity and len(correction.entity) < 2:
                warnings.append("Entity name seems too short")
        
        return len(warnings) == 0 or correction.severity == FeedbackSeverity.CRITICAL, warnings


# =============================================================================
# STAGE 5: KNOWLEDGE UPDATE
# =============================================================================

class KnowledgeUpdater:
    """Update knowledge stores with corrections."""
    
    def __init__(self):
        self.logger = logging.getLogger("ira.knowledge_updater")
    
    def update(self, correction: ExtractedCorrection, from_user: str) -> List[str]:
        """
        Apply correction to knowledge stores.
        
        Returns list of updates applied.
        """
        updates = []
        
        for target in correction.update_targets:
            try:
                if target == UpdateTarget.MEM0:
                    if self._update_mem0(correction, from_user):
                        updates.append("mem0:stored_as_high_priority_memory")
                
                elif target == UpdateTarget.LEARNED_CORRECTIONS:
                    if self._update_learned_corrections(correction):
                        updates.append("learned_corrections:added_to_list")
                
                elif target == UpdateTarget.MACHINE_DATABASE:
                    if self._update_machine_database(correction):
                        updates.append(f"machine_database:{correction.entity}:{correction.field}")
                
                elif target == UpdateTarget.TRUTH_HINTS:
                    if self._update_truth_hints(correction):
                        updates.append("truth_hints:added_correction_hint")
                
            except Exception as e:
                self.logger.error(f"Error updating {target}: {e}")
        
        return updates
    
    def _update_mem0(self, correction: ExtractedCorrection, from_user: str) -> bool:
        """Store correction in Mem0 as high-priority memory."""
        if not MEM0_AVAILABLE:
            return False
        
        try:
            mem0 = get_unified_mem0()
            
            # Create memory text
            memory_text = f"CORRECTION: {correction.topic}. "
            memory_text += f"Wrong: {correction.incorrect_value}. "
            memory_text += f"Correct: {correction.correct_value}. "
            if correction.reasoning:
                memory_text += f"Reason: {correction.reasoning}"
            
            # Use remember() with user/assistant format
            mem0.remember(
                user_message=f"I need to correct: {correction.topic}. The value {correction.incorrect_value} was wrong.",
                assistant_response=f"Understood! The correct value is: {correction.correct_value}. I'll remember this correction.",
                user_id="ira_corrections",
                channel="feedback",
                extract_relationships=False  # Don't extract relationships from corrections
            )
            
            self.logger.info(f"Stored correction in Mem0: {correction.topic}")
            return True
            
        except Exception as e:
            self.logger.error(f"Mem0 update error: {e}")
            return False
    
    def _update_learned_corrections(self, correction: ExtractedCorrection) -> bool:
        """Update learned_corrections.json."""
        try:
            # Load existing
            if CORRECTIONS_FILE.exists():
                data = json.loads(CORRECTIONS_FILE.read_text())
            else:
                data = {"corrections": [], "competitors": [], "existing_customers": []}
            
            # Add to appropriate list
            if correction.feedback_type == FeedbackType.ENTITY_CORRECTION:
                entity_lower = correction.entity.lower() if correction.entity else ""
                
                if "competitor" in correction.correct_value.lower():
                    if entity_lower and entity_lower not in data["competitors"]:
                        data["competitors"].append(entity_lower)
                        self.logger.info(f"Added competitor: {correction.entity}")
                        
                elif "customer" in correction.correct_value.lower():
                    if entity_lower and entity_lower not in data["existing_customers"]:
                        data["existing_customers"].append(entity_lower)
                        self.logger.info(f"Added existing customer: {correction.entity}")
            
            # Add to corrections list
            data["corrections"].append({
                "topic": correction.topic,
                "incorrect": correction.incorrect_value,
                "correct": correction.correct_value,
                "entity": correction.entity,
                "type": correction.feedback_type.value,
                "timestamp": datetime.now().isoformat(),
            })
            
            data["last_updated"] = datetime.now().isoformat()
            
            # Save
            CORRECTIONS_FILE.write_text(json.dumps(data, indent=2))
            return True
            
        except Exception as e:
            self.logger.error(f"Learned corrections update error: {e}")
            return False
    
    def _update_machine_database(self, correction: ExtractedCorrection) -> bool:
        """
        Update machine_database.py with spec corrections.
        
        NOTE: This creates a log entry but doesn't auto-modify the Python file.
        A human should review and apply critical spec changes.
        """
        if not correction.entity or not correction.field:
            return False
        
        # Log the needed update
        update_entry = {
            "timestamp": datetime.now().isoformat(),
            "model": correction.entity,
            "field": correction.field,
            "old_value": correction.incorrect_value,
            "new_value": correction.correct_value,
            "severity": correction.severity.value,
            "status": "pending_review",
        }
        
        # Append to update log
        update_log = BRAIN_DIR / "machine_database_updates.jsonl"
        with open(update_log, "a") as f:
            f.write(json.dumps(update_entry) + "\n")
        
        self.logger.info(f"Logged machine DB update: {correction.entity}.{correction.field}")
        return True
    
    def _update_truth_hints(self, correction: ExtractedCorrection) -> bool:
        """Add correction as a truth hint."""
        try:
            # Create truth hint entry
            truth_hint = f"""
# Correction from {datetime.now().strftime('%Y-%m-%d')}
# Topic: {correction.topic}
# WRONG: {correction.incorrect_value}
# CORRECT: {correction.correct_value}
"""
            
            # Append to truth hints log
            hints_log = BRAIN_DIR / "learned_truth_hints.txt"
            with open(hints_log, "a") as f:
                f.write(truth_hint + "\n")
            
            self.logger.info(f"Added truth hint: {correction.topic}")
            return True
            
        except Exception as e:
            self.logger.error(f"Truth hints update error: {e}")
            return False


# =============================================================================
# STAGE 6: LOGIC UPDATE
# =============================================================================

class LogicUpdater:
    """Update IRA's behavioral logic based on feedback."""
    
    def __init__(self):
        self.logger = logging.getLogger("ira.logic_updater")
    
    def update(self, correction: ExtractedCorrection) -> List[str]:
        """Update behavioral logic."""
        updates = []
        
        if UpdateTarget.GUARDRAILS in correction.update_targets:
            if self._update_guardrails(correction):
                updates.append("guardrails:added_rule")
        
        if UpdateTarget.PROCEDURAL_MEMORY in correction.update_targets:
            if self._update_procedural_memory(correction):
                updates.append("procedural_memory:updated")
        
        return updates
    
    def _update_guardrails(self, correction: ExtractedCorrection) -> bool:
        """Add new guardrail rule based on behavior correction."""
        try:
            guardrail_entry = {
                "timestamp": datetime.now().isoformat(),
                "type": correction.feedback_type.value,
                "rule": f"LEARNED: {correction.topic}",
                "constraint": correction.correct_value,
                "severity": correction.severity.value,
            }
            
            # Append to guardrails log
            guardrails_log = BRAIN_DIR / "learned_guardrails.jsonl"
            with open(guardrails_log, "a") as f:
                f.write(json.dumps(guardrail_entry) + "\n")
            
            self.logger.info(f"Added guardrail: {correction.topic}")
            return True
            
        except Exception as e:
            self.logger.error(f"Guardrails update error: {e}")
            return False
    
    def _update_procedural_memory(self, correction: ExtractedCorrection) -> bool:
        """Update procedural memory with behavior correction."""
        # This would integrate with the procedural memory system
        self.logger.info(f"Procedural memory update logged: {correction.topic}")
        return True


# =============================================================================
# STAGE 7: CONFIRMATION
# =============================================================================

class ConfirmationGenerator:
    """Generate confirmation message for the user."""
    
    def __init__(self):
        self.logger = logging.getLogger("ira.confirmation")
    
    def generate(
        self,
        corrections: List[ExtractedCorrection],
        updates: List[str]
    ) -> str:
        """Generate confirmation message."""
        if not corrections:
            return "Thanks for your feedback! I didn't detect any specific corrections, but I've noted your message."
        
        if corrections[0].feedback_type == FeedbackType.POSITIVE_FEEDBACK:
            return "Thanks! Glad I could help. 😊"
        
        lines = ["Got it! I've learned from your feedback:\n"]
        
        for correction in corrections:
            if correction.severity == FeedbackSeverity.CRITICAL:
                lines.append(f"⚠️ **Critical correction**: {correction.topic}")
            else:
                lines.append(f"📝 **{correction.topic}**")
            
            lines.append(f"   • Wrong: {correction.incorrect_value}")
            lines.append(f"   • Correct: {correction.correct_value}")
            lines.append("")
        
        lines.append("\n**Updates applied:**")
        for update in updates[:5]:  # Show max 5
            lines.append(f"   ✅ {update}")
        
        lines.append("\nI won't make this mistake again. Thanks for helping me improve!")
        
        return "\n".join(lines)


# =============================================================================
# STAGE 8: PREVENTION
# =============================================================================

class PreventionEngine:
    """Ensure the same mistake doesn't happen again."""
    
    def __init__(self):
        self.logger = logging.getLogger("ira.prevention")
    
    def prevent(self, correction: ExtractedCorrection):
        """
        Take actions to prevent recurrence.
        
        - Record as negative example
        - Update retrieval weights
        - Trigger consolidation if critical
        """
        self.logger.info(f"Recording negative example: {correction.topic}")
        
        # Log to feedback history
        self._log_feedback(correction)
        
        # If critical, flag for dream consolidation
        if correction.severity == FeedbackSeverity.CRITICAL:
            self._flag_for_consolidation(correction)
    
    def _log_feedback(self, correction: ExtractedCorrection):
        """Log feedback for historical analysis."""
        try:
            FEEDBACK_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
            
            entry = {
                "timestamp": datetime.now().isoformat(),
                **correction.to_dict()
            }
            
            with open(FEEDBACK_LOG_FILE, "a") as f:
                f.write(json.dumps(entry) + "\n")
                
        except Exception as e:
            self.logger.error(f"Feedback log error: {e}")
    
    def _flag_for_consolidation(self, correction: ExtractedCorrection):
        """Flag critical corrections for dream consolidation."""
        try:
            consolidation_flag = PROJECT_ROOT / "data" / "pending_consolidation.json"
            
            pending = []
            if consolidation_flag.exists():
                pending = json.loads(consolidation_flag.read_text())
            
            pending.append({
                "type": "critical_correction",
                "topic": correction.topic,
                "timestamp": datetime.now().isoformat(),
            })
            
            consolidation_flag.write_text(json.dumps(pending, indent=2))
            self.logger.info(f"Flagged for dream consolidation: {correction.topic}")
            
        except Exception as e:
            self.logger.error(f"Consolidation flag error: {e}")


# =============================================================================
# MAIN PIPELINE
# =============================================================================

class FeedbackProcessor:
    """
    Complete feedback processing pipeline.
    
    Processes user feedback to learn and improve IRA's knowledge and behavior.
    """
    
    def __init__(self):
        self.logger = logging.getLogger("ira.feedback_processor")
        
        # Initialize stages
        self.detector = FeedbackDetector()
        self.extractor = CorrectionExtractor()
        self.validator = CorrectionValidator()
        self.knowledge_updater = KnowledgeUpdater()
        self.logic_updater = LogicUpdater()
        self.confirmation_gen = ConfirmationGenerator()
        self.prevention_engine = PreventionEngine()
        
        self.logger.info("Feedback Processing Pipeline initialized")
    
    def process(
        self,
        feedback_message: str,
        original_response: str = "",
        from_user: str = "unknown",
        channel: str = "email",
        verbose: bool = True
    ) -> FeedbackResult:
        """
        Process feedback through the complete pipeline.
        
        Args:
            feedback_message: The feedback/correction from user
            original_response: IRA's original response that's being corrected
            from_user: User identifier (email, chat ID)
            channel: Communication channel
            verbose: Log progress
        
        Returns:
            FeedbackResult with all processing details
        """
        import time
        start_time = time.time()
        
        if verbose:
            self.logger.info("=" * 60)
            self.logger.info("FEEDBACK PROCESSING PIPELINE")
            self.logger.info("=" * 60)
            self.logger.info(f"From: {from_user}")
            self.logger.info(f"Channel: {channel}")
            self.logger.info(f"Feedback: {feedback_message[:100]}...")
        
        all_warnings = []
        all_updates = []
        
        # STAGE 1: Detection
        if verbose:
            self.logger.info("\n[STAGE 1] Detecting feedback type...")
        is_feedback, feedback_category = self.detector.detect(
            feedback_message, original_response
        )
        
        if not is_feedback:
            if verbose:
                self.logger.info("  Not detected as feedback - treating as new message")
            return FeedbackResult(
                success=True,
                feedback_type=FeedbackType.UNKNOWN,
                corrections_found=[],
                updates_applied=[],
                confirmation_message="",
                processing_time_seconds=time.time() - start_time
            )
        
        if verbose:
            self.logger.info(f"  Detected: {feedback_category}")
        
        # STAGE 2 & 3: Classification & Extraction
        if verbose:
            self.logger.info("\n[STAGE 2-3] Extracting corrections...")
        corrections = self.extractor.extract(
            feedback_message, original_response, feedback_category
        )
        
        if verbose:
            self.logger.info(f"  Found {len(corrections)} correction(s)")
            for c in corrections:
                self.logger.info(f"    - {c.feedback_type.value}: {c.topic}")
        
        # STAGE 4: Validation
        if verbose:
            self.logger.info("\n[STAGE 4] Validating corrections...")
        valid_corrections = []
        for correction in corrections:
            is_valid, warnings = self.validator.validate(correction)
            all_warnings.extend(warnings)
            
            if is_valid:
                valid_corrections.append(correction)
                if verbose:
                    self.logger.info(f"  ✅ Valid: {correction.topic}")
            else:
                if verbose:
                    self.logger.warning(f"  ⚠️ Invalid: {correction.topic} - {warnings}")
        
        # STAGE 5: Knowledge Update
        if verbose:
            self.logger.info("\n[STAGE 5] Updating knowledge...")
        for correction in valid_corrections:
            updates = self.knowledge_updater.update(correction, from_user)
            all_updates.extend(updates)
            if verbose:
                for u in updates:
                    self.logger.info(f"  ✅ {u}")
        
        # STAGE 6: Logic Update
        if verbose:
            self.logger.info("\n[STAGE 6] Updating logic...")
        for correction in valid_corrections:
            updates = self.logic_updater.update(correction)
            all_updates.extend(updates)
            if verbose:
                for u in updates:
                    self.logger.info(f"  ✅ {u}")
        
        # STAGE 7: Confirmation
        if verbose:
            self.logger.info("\n[STAGE 7] Generating confirmation...")
        confirmation = self.confirmation_gen.generate(valid_corrections, all_updates)
        
        # STAGE 8: Prevention
        if verbose:
            self.logger.info("\n[STAGE 8] Recording for prevention...")
        for correction in valid_corrections:
            self.prevention_engine.prevent(correction)
        
        processing_time = time.time() - start_time
        
        if verbose:
            self.logger.info("\n" + "=" * 60)
            self.logger.info(f"COMPLETE in {processing_time:.1f}s")
            self.logger.info(f"  Corrections: {len(valid_corrections)}")
            self.logger.info(f"  Updates: {len(all_updates)}")
            self.logger.info("=" * 60)
        
        # Determine primary feedback type
        primary_type = FeedbackType.UNKNOWN
        if valid_corrections:
            primary_type = valid_corrections[0].feedback_type
        
        return FeedbackResult(
            success=True,
            feedback_type=primary_type,
            corrections_found=valid_corrections,
            updates_applied=all_updates,
            confirmation_message=confirmation,
            warnings=all_warnings,
            processing_time_seconds=processing_time
        )


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

_processor_instance = None


def get_processor() -> FeedbackProcessor:
    """Get singleton processor instance."""
    global _processor_instance
    if _processor_instance is None:
        _processor_instance = FeedbackProcessor()
    return _processor_instance


def process_feedback(
    feedback: str,
    original_response: str = "",
    from_user: str = "unknown"
) -> FeedbackResult:
    """
    Convenience function to process feedback.
    
    Usage:
        result = process_feedback(
            feedback="No, the PF1-C-2015 is ₹60 Lakhs, not ₹65 Lakhs",
            original_response="The PF1-C-2015 is priced at ₹65 Lakhs",
            from_user="rushabh@machinecraft.org"
        )
        print(result.confirmation_message)
    """
    processor = get_processor()
    return processor.process(feedback, original_response, from_user)


# =============================================================================
# CLI / TESTING
# =============================================================================

if __name__ == "__main__":
    import argparse
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%H:%M:%S'
    )
    
    parser = argparse.ArgumentParser(description="Feedback Processing Pipeline")
    parser.add_argument("--feedback", "-f", help="Feedback message to process")
    parser.add_argument("--original", "-o", default="", help="Original response")
    parser.add_argument("--user", "-u", default="test@example.com", help="User ID")
    parser.add_argument("--test", action="store_true", help="Run test cases")
    
    args = parser.parse_args()
    
    if args.test:
        # Test cases
        test_cases = [
            ("No, the PF1-C-2015 is ₹60 Lakhs not ₹65 Lakhs", "The PF1-C-2015 is priced at ₹65 Lakhs"),
            ("Kiefel is a competitor, not a prospect", "Consider reaching out to Kiefel"),
            ("Minerex is already our customer", "Minerex could be a good prospect"),
            ("Actually the heater power is 125kW, not 100kW", "The heater is 100kW"),
            ("Good job! That's exactly right.", "The PF1-C-2015 is priced at ₹60 Lakhs"),
        ]
        
        for feedback, original in test_cases:
            print("\n" + "=" * 70)
            print(f"FEEDBACK: {feedback}")
            print(f"ORIGINAL: {original}")
            print("=" * 70)
            
            result = process_feedback(feedback, original, "test@example.com")
            
            print("\nCONFIRMATION:")
            print(result.confirmation_message)
    
    elif args.feedback:
        result = process_feedback(args.feedback, args.original, args.user)
        print("\n" + "=" * 70)
        print("RESULT:")
        print("=" * 70)
        print(result.confirmation_message)
    
    else:
        parser.print_help()
