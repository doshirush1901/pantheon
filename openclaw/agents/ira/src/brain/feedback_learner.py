#!/usr/bin/env python3
"""
FEEDBACK LEARNER - Learn from corrections
==========================================

When Rushabh corrects Ira:
1. Detect that it's a correction (not a new question)
2. Extract what was wrong and what's correct
3. Store the lesson in Mem0
4. Update machine database if it's a spec correction

Usage:
    from feedback_learner import FeedbackLearner
    learner = FeedbackLearner()
    learner.process_feedback(original_email, correction_email)
"""

import os
import sys
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

# Setup paths
BRAIN_DIR = Path(__file__).parent
SKILLS_DIR = BRAIN_DIR.parent
AGENT_DIR = SKILLS_DIR.parent
PROJECT_ROOT = AGENT_DIR.parent.parent.parent

sys.path.insert(0, str(AGENT_DIR))

# Import from centralized config
try:
    from config import OPENAI_API_KEY, MEM0_API_KEY, get_logger
    CONFIG_AVAILABLE = True
except ImportError:
    CONFIG_AVAILABLE = False
    # Fallback: Load environment manually
    env_file = PROJECT_ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if line.strip() and not line.startswith('#') and '=' in line:
                key, _, value = line.partition('=')
                os.environ.setdefault(key.strip(), value.strip().strip('"'))
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
    MEM0_API_KEY = os.environ.get("MEM0_API_KEY", "")

import openai
from mem0 import MemoryClient


@dataclass
class Correction:
    """A correction extracted from feedback."""
    topic: str  # e.g., "PF1-C-2015 price", "vacuum pump capacity"
    incorrect: str  # What was wrong
    correct: str  # What's correct
    context: str  # Full context
    is_spec: bool  # Is this a machine spec correction?
    model: Optional[str] = None  # Machine model if applicable
    spec_field: Optional[str] = None  # e.g., "price_inr", "vacuum_pump_capacity"


class FeedbackLearner:
    """
    Learns from corrections to improve future responses.
    
    Detects corrections in replies and stores lessons in Mem0.
    """
    
    def __init__(self):
        self.mem0 = MemoryClient()
        self.openai = openai.OpenAI()
        self.user_id = "system_ira_corrections"
        
        # Patterns that indicate a correction
        self.correction_patterns = [
            r"actually",
            r"not correct",
            r"wrong",
            r"should be",
            r"it's actually",
            r"that's not right",
            r"the correct",
            r"correction:",
            r"fix:",
            r"update:",
            r"no,\s+it",
            r"incorrect",
        ]
    
    def is_correction(self, message: str) -> bool:
        """Detect if a message is a correction."""
        message_lower = message.lower()
        
        for pattern in self.correction_patterns:
            if re.search(pattern, message_lower):
                return True
        
        return False
    
    def extract_corrections(self, original_reply: str, feedback: str) -> List[Correction]:
        """Use LLM to extract specific corrections from feedback."""
        
        prompt = f"""Analyze this feedback to extract specific corrections.

ORIGINAL REPLY FROM IRA:
{original_reply[:2000]}

FEEDBACK/CORRECTION FROM RUSHABH:
{feedback}

Extract any corrections mentioned. For each correction, identify:
1. What topic/subject is being corrected
2. What was incorrect in the original
3. What is the correct information
4. Is this a machine specification correction?
5. If it's about a machine, which model?
6. If it's a spec, which field? (price_inr, heater_power_kw, vacuum_pump_capacity, forming_area_mm, etc.)

Return as JSON array:
[
  {{
    "topic": "PF1-C-2015 price",
    "incorrect": "₹65,00,000",
    "correct": "₹60,00,000",
    "is_spec": true,
    "model": "PF1-C-2015",
    "spec_field": "price_inr"
  }}
]

If there are no clear corrections, return: []
"""

        try:
            response = self.openai.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "Extract corrections from feedback. Return valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1000,
                temperature=0.2
            )
            
            text = response.choices[0].message.content
            
            # Clean JSON
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]
            
            import json
            corrections_data = json.loads(text)
            
            corrections = []
            for c in corrections_data:
                corrections.append(Correction(
                    topic=c.get("topic", ""),
                    incorrect=c.get("incorrect", ""),
                    correct=c.get("correct", ""),
                    context=feedback[:500],
                    is_spec=c.get("is_spec", False),
                    model=c.get("model"),
                    spec_field=c.get("spec_field"),
                ))
            
            return corrections
            
        except Exception as e:
            print(f"Error extracting corrections: {e}")
            return []
    
    def store_correction(self, correction: Correction):
        """Store a correction in Mem0 for future reference."""
        
        memory_text = f"""CORRECTION LEARNED ({datetime.now().strftime('%Y-%m-%d')}):
Topic: {correction.topic}
Previously said (WRONG): {correction.incorrect}
Correct information: {correction.correct}
Context: {correction.context[:200]}

REMEMBER: When discussing {correction.topic}, use {correction.correct} not {correction.incorrect}."""

        try:
            self.mem0.add(
                memory_text,
                user_id=self.user_id,
                metadata={
                    "type": "correction",
                    "topic": correction.topic,
                    "model": correction.model or "",
                    "spec_field": correction.spec_field or "",
                    "timestamp": datetime.now().isoformat(),
                }
            )
            print(f"✓ Stored correction in Mem0: {correction.topic}")
        except Exception as e:
            print(f"Error storing to Mem0: {e}")
    
    def update_database(self, correction: Correction) -> bool:
        """
        Update machine database if it's a spec correction.
        
        NOTE: This modifies the source file - use with caution.
        """
        if not correction.is_spec or not correction.model or not correction.spec_field:
            return False
        
        # For now, just log - manual update recommended
        print(f"⚠️  DATABASE UPDATE NEEDED:")
        print(f"   Model: {correction.model}")
        print(f"   Field: {correction.spec_field}")
        print(f"   Old: {correction.incorrect}")
        print(f"   New: {correction.correct}")
        
        # Could auto-update in future, but risky
        return False
    
    def process_feedback(self, original_reply: str, feedback: str) -> List[Correction]:
        """
        Main entry point: Process feedback and learn from it.
        
        Returns list of corrections found and processed.
        """
        # Check if this is actually a correction
        if not self.is_correction(feedback):
            print("No correction patterns detected in feedback")
            return []
        
        print("Correction detected! Analyzing...")
        
        # Extract specific corrections
        corrections = self.extract_corrections(original_reply, feedback)
        
        if not corrections:
            print("Could not extract specific corrections")
            return []
        
        print(f"Found {len(corrections)} correction(s)")
        
        # Process each correction
        for correction in corrections:
            print(f"\nProcessing: {correction.topic}")
            
            # Store in Mem0
            self.store_correction(correction)
            
            # Flag for database update if needed
            if correction.is_spec:
                self.update_database(correction)
        
        return corrections
    
    def get_past_corrections(self, topic: str = None) -> List[Dict]:
        """Retrieve past corrections from Mem0."""
        try:
            query = f"corrections about {topic}" if topic else "corrections and lessons learned"
            results = self.mem0.search(query, user_id=self.user_id, limit=10)
            return results.get("results", [])
        except Exception as e:
            print(f"Error searching Mem0: {e}")
            return []


def check_for_corrections_in_thread(messages: List[Dict]) -> Optional[Tuple[str, str]]:
    """
    Check if the latest message is a correction to a previous Ira reply.
    
    Returns (original_reply, correction) if found, None otherwise.
    """
    if len(messages) < 2:
        return None
    
    # Get last two messages
    prev_msg = messages[-2]  # Ira's reply
    current_msg = messages[-1]  # Rushabh's response
    
    # Check if prev was from Ira and current is from Rushabh
    # (Headers check would go here)
    
    return None  # Placeholder


if __name__ == "__main__":
    # Test
    learner = FeedbackLearner()
    
    original = """
    The PF1-C-2015 has a forming area of 2000 x 1500 mm and costs ₹65,00,000.
    The heater power is 125 kW.
    """
    
    feedback = """
    Actually, the price is wrong. It should be ₹60,00,000 not ₹65,00,000.
    Also, please update your records.
    """
    
    print("Testing feedback learner...")
    corrections = learner.process_feedback(original, feedback)
    
    print(f"\nProcessed {len(corrections)} correction(s)")
    for c in corrections:
        print(f"  - {c.topic}: {c.incorrect} → {c.correct}")
