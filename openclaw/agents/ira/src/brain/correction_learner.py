#!/usr/bin/env python3
"""
Correction Learner - Closed-loop learning from user feedback
=============================================================

Detects and stores user corrections to improve future responses.
Patterns detected:
- "No, it's actually X" / "No!!!! Its X"
- "That's wrong, X is Y"
- "X is our customer already"
- "X is a competitor, not a prospect"
- "Please correct this"

Corrections are stored and used to:
1. Filter out wrong suggestions (competitors, existing customers)
2. Override incorrect facts in responses
3. Improve truth hints over time
"""

import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

SKILL_DIR = Path(__file__).parent
CORRECTIONS_FILE = SKILL_DIR / "learned_corrections.json"


@dataclass
class Correction:
    """A learned correction from user feedback."""
    id: str
    correction_type: str  # 'fact', 'competitor', 'customer', 'filter'
    original: str  # What the bot said wrong
    corrected: str  # What the user said is correct
    entity: str  # The entity being corrected (company name, product, etc)
    context: str  # Query context
    timestamp: str
    confidence: float = 1.0
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "correction_type": self.correction_type,
            "original": self.original,
            "corrected": self.corrected,
            "entity": self.entity,
            "context": self.context,
            "timestamp": self.timestamp,
            "confidence": self.confidence,
        }


class CorrectionLearner:
    """Learn from user corrections to improve responses."""
    
    def __init__(self):
        self.corrections: Dict[str, Correction] = {}
        self.competitors: set = set()
        self.existing_customers: set = set()
        self._load()
    
    def _load(self):
        """Load corrections from file."""
        if CORRECTIONS_FILE.exists():
            try:
                data = json.loads(CORRECTIONS_FILE.read_text())
                for c in data.get("corrections", []):
                    valid_fields = {f.name for f in Correction.__dataclass_fields__.values()}
                    filtered = {k: v for k, v in c.items() if k in valid_fields}
                    correction = Correction(**filtered)
                    self.corrections[correction.id] = correction
                    
                    if correction.correction_type == "competitor":
                        self.competitors.add(correction.entity.lower())
                    elif correction.correction_type == "customer":
                        self.existing_customers.add(correction.entity.lower())
                        
                # Also load explicit lists
                self.competitors.update(data.get("competitors", []))
                self.existing_customers.update(data.get("existing_customers", []))
            except Exception as e:
                print(f"[correction_learner] Load error: {e}")
    
    def _save(self):
        """Save corrections to file."""
        try:
            data = {
                "corrections": [c.to_dict() for c in self.corrections.values()],
                "competitors": list(self.competitors),
                "existing_customers": list(self.existing_customers),
                "last_updated": datetime.now().isoformat(),
            }
            CORRECTIONS_FILE.write_text(json.dumps(data, indent=2))
        except Exception as e:
            print(f"[correction_learner] Save error: {e}")
    
    def detect_correction(
        self,
        user_message: str,
        previous_bot_response: str,
        context: Dict = None
    ) -> Optional[Correction]:
        """
        Detect if user message is a correction.
        
        Returns Correction object if detected, None otherwise.
        """
        msg_lower = user_message.lower()
        
        # Pattern 1: "No, it's X" / "No!!!! Its X"
        no_pattern = re.match(
            r'^no[!.]*\s*(it\'?s|that\'?s|this is|actually|wrong)?\s*(.+)',
            msg_lower,
            re.IGNORECASE
        )
        if no_pattern:
            corrected_info = no_pattern.group(2).strip()
            return self._create_fact_correction(
                corrected_info, previous_bot_response, context
            )
        
        # Pattern 2: "X is a competitor" / "X is competitor"
        competitor_pattern = re.search(
            r'(\w+(?:\s+\w+)?)\s+is\s+(?:a\s+)?competitor',
            user_message,
            re.IGNORECASE
        )
        if competitor_pattern:
            company = competitor_pattern.group(1).strip()
            return self._create_competitor_correction(company, context)
        
        # Pattern 3: "X is our customer already" / "X is already a customer"
        customer_pattern = re.search(
            r'(\w+(?:\s+\w+)?)\s+is\s+(?:our\s+)?(?:a\s+)?customer\s*(?:already)?|'
            r'(\w+(?:\s+\w+)?)\s+(?:is\s+)?already\s+(?:a\s+)?(?:our\s+)?customer',
            user_message,
            re.IGNORECASE
        )
        if customer_pattern:
            company = (customer_pattern.group(1) or customer_pattern.group(2)).strip()
            return self._create_customer_correction(company, context)
        
        # Pattern 4: "Please correct this" / "Pls correct this in your memory"
        if re.search(r'correct\s+this|fix\s+this|remember\s+this', msg_lower):
            # Generic correction request - extract from context
            return self._create_generic_correction(user_message, previous_bot_response, context)
        
        return None
    
    def _create_fact_correction(
        self,
        corrected_info: str,
        bot_response: str,
        context: Dict
    ) -> Correction:
        """Create a fact correction."""
        correction_id = f"fact_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        correction = Correction(
            id=correction_id,
            correction_type="fact",
            original=bot_response[:200] if bot_response else "",
            corrected=corrected_info,
            entity=self._extract_entity(corrected_info),
            context=context.get("query", "") if context else "",
            timestamp=datetime.now().isoformat(),
        )
        
        self.corrections[correction_id] = correction
        self._save()
        
        return correction
    
    def _create_competitor_correction(self, company: str, context: Dict) -> Correction:
        """Mark a company as competitor."""
        correction_id = f"competitor_{company.lower().replace(' ', '_')}"
        
        correction = Correction(
            id=correction_id,
            correction_type="competitor",
            original="Suggested as prospect",
            corrected="Is a competitor",
            entity=company,
            context=context.get("query", "") if context else "",
            timestamp=datetime.now().isoformat(),
        )
        
        self.competitors.add(company.lower())
        self.corrections[correction_id] = correction
        self._save()
        
        print(f"[correction_learner] Learned: {company} is a COMPETITOR")
        return correction
    
    def _create_customer_correction(self, company: str, context: Dict) -> Correction:
        """Mark a company as existing customer."""
        correction_id = f"customer_{company.lower().replace(' ', '_')}"
        
        correction = Correction(
            id=correction_id,
            correction_type="customer",
            original="Suggested as prospect",
            corrected="Is existing customer",
            entity=company,
            context=context.get("query", "") if context else "",
            timestamp=datetime.now().isoformat(),
        )
        
        self.existing_customers.add(company.lower())
        self.corrections[correction_id] = correction
        self._save()
        
        print(f"[correction_learner] Learned: {company} is an EXISTING CUSTOMER")
        return correction
    
    def _create_generic_correction(
        self,
        user_message: str,
        bot_response: str,
        context: Dict
    ) -> Correction:
        """Create a generic correction from user request."""
        correction_id = f"generic_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        correction = Correction(
            id=correction_id,
            correction_type="fact",
            original=bot_response[:200] if bot_response else "",
            corrected=user_message,
            entity="",
            context=context.get("query", "") if context else "",
            timestamp=datetime.now().isoformat(),
        )
        
        self.corrections[correction_id] = correction
        self._save()
        
        return correction
    
    def _extract_entity(self, text: str) -> str:
        """Extract main entity from correction text."""
        # Look for product names
        product_match = re.search(r'(PF\d?[-\s]?\w*|AM[-\s]?\d+|RE[-\s]?\d+)', text, re.IGNORECASE)
        if product_match:
            return product_match.group(1).upper()
        
        # First capitalized word
        words = text.split()
        for word in words[:3]:
            if word[0].isupper():
                return word
        
        return text[:30]
    
    def is_competitor(self, company: str) -> bool:
        """Check if company is a known competitor."""
        return company.lower() in self.competitors
    
    def is_existing_customer(self, company: str) -> bool:
        """Check if company is an existing customer."""
        return company.lower() in self.existing_customers
    
    def filter_prospects(self, companies: List[str]) -> List[str]:
        """Filter out competitors and existing customers from prospect list."""
        filtered = []
        for company in companies:
            company_lower = company.lower()
            if company_lower in self.competitors:
                print(f"[correction_learner] Filtered competitor: {company}")
                continue
            if company_lower in self.existing_customers:
                print(f"[correction_learner] Filtered existing customer: {company}")
                continue
            filtered.append(company)
        return filtered
    
    def get_relevant_corrections(self, query: str) -> List[Correction]:
        """Get corrections relevant to a query."""
        relevant = []
        query_lower = query.lower()
        
        for correction in self.corrections.values():
            if correction.entity.lower() in query_lower:
                relevant.append(correction)
            elif any(word in query_lower for word in correction.context.lower().split()[:5]):
                relevant.append(correction)
        
        return relevant
    
    def add_known_competitor(self, company: str):
        """Manually add a known competitor."""
        self.competitors.add(company.lower())
        self._save()
    
    def add_known_customer(self, company: str):
        """Manually add a known customer."""
        self.existing_customers.add(company.lower())
        self._save()


# Singleton
_learner = None


def get_learner() -> CorrectionLearner:
    global _learner
    if _learner is None:
        _learner = CorrectionLearner()
    return _learner


def detect_and_learn(
    user_message: str,
    previous_bot_response: str = "",
    context: Dict = None
) -> Optional[Correction]:
    """Detect correction and learn from it."""
    return get_learner().detect_correction(user_message, previous_bot_response, context)


def is_competitor(company: str) -> bool:
    return get_learner().is_competitor(company)


def is_customer(company: str) -> bool:
    return get_learner().is_existing_customer(company)


def filter_prospects(companies: List[str]) -> List[str]:
    return get_learner().filter_prospects(companies)


# Pre-populate with known competitors
KNOWN_COMPETITORS = [
    "formech", "formech international",
    "ridat", 
    "belovac",
    "maac machinery",
    "illig",
    "kiefel",
    "geiss",
    "cannon",
]

KNOWN_CUSTOMERS = [
    "minerex",
]


def initialize_known_entities():
    """Initialize with known competitors and customers."""
    learner = get_learner()
    for c in KNOWN_COMPETITORS:
        learner.competitors.add(c.lower())
    for c in KNOWN_CUSTOMERS:
        learner.existing_customers.add(c.lower())
    learner._save()


if __name__ == "__main__":
    # Initialize and test
    initialize_known_entities()
    
    learner = get_learner()
    print(f"Known competitors: {learner.competitors}")
    print(f"Known customers: {learner.existing_customers}")
    
    # Test detection
    test_messages = [
        ("No!!!! Its a vacuum forming machine", "PF1 is a pressure forming machine"),
        ("Formech is a competitor, not a prospect", "Here are prospects: Formech, ..."),
        ("Minerex is our customer already", "Prospects: Minerex, Polyplast, ..."),
    ]
    
    for msg, bot_resp in test_messages:
        correction = learner.detect_correction(msg, bot_resp, {"query": "test"})
        if correction:
            print(f"\nDetected: {correction.correction_type}")
            print(f"  Entity: {correction.entity}")
            print(f"  Corrected: {correction.corrected[:50]}")
