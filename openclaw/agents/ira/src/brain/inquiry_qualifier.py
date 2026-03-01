#!/usr/bin/env python3
"""
INQUIRY QUALIFIER - Drip Marketing Question Flow
=================================================

Instead of guessing, Ira asks the right qualifying questions
before making a machine recommendation.

Based on: Single Station Inquiry Form (Responses)

Flow:
1. Customer sends initial inquiry
2. Ira detects missing info → asks qualifying questions
3. Customer answers
4. Ira asks follow-up questions (drip)
5. Once qualified → generate tailored proposal
"""

import json
import re
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent.parent

# Import feature knowledge base for explanations
try:
    from machine_features_kb import get_feature_explanation, get_series_comparison
except ImportError:
    get_feature_explanation = lambda x: None
    get_series_comparison = lambda: None


@dataclass
class QualificationProfile:
    """Tracks what we know about a customer inquiry."""
    
    # Identity
    thread_id: str = ""
    customer_email: str = ""
    customer_name: str = ""
    company_name: str = ""
    
    # Core Requirements (MUST have for recommendation)
    max_forming_area: Optional[Tuple[int, int]] = None  # (width, height) mm
    max_forming_depth: Optional[int] = None  # mm
    max_sheet_thickness: Optional[float] = None  # mm
    materials: List[str] = field(default_factory=list)  # HDPE, ABS, PP, etc.
    
    # Automation Level (determines C vs X)
    sheet_loading: Optional[str] = None  # "manual" or "automatic"
    production_volume: Optional[str] = None  # "low", "medium", "high"
    
    # Technical Preferences
    heater_type: Optional[str] = None  # "IR Ceramic", "IR Quartz", "Halogen"
    cooling_system: Optional[str] = None  # "fan", "water", "both"
    tool_change: Optional[str] = None  # "manual", "ball_transfer", "auto"
    
    # Application
    application: Optional[str] = None  # "automotive", "packaging", etc.
    part_description: Optional[str] = None
    
    # Qualification Status
    qualification_stage: int = 0  # 0=new, 1=basic, 2=detailed, 3=ready
    questions_asked: List[str] = field(default_factory=list)
    last_updated: str = ""
    
    def to_dict(self) -> dict:
        d = asdict(self)
        d['max_forming_area'] = list(self.max_forming_area) if self.max_forming_area else None
        return d
    
    @classmethod
    def from_dict(cls, d: dict) -> 'QualificationProfile':
        if d.get('max_forming_area'):
            d['max_forming_area'] = tuple(d['max_forming_area'])
        return cls(**d)


# Questions organized by priority
QUALIFICATION_QUESTIONS = {
    "stage_1": [  # Core requirements - MUST ask first
        {
            "field": "max_forming_area",
            "question": "What is the maximum part size you need to form (Length × Width in mm)?",
            "extract_pattern": r"(\d+)\s*[xX×]\s*(\d+)",
            "example": "e.g., 1500 × 2000 mm"
        },
        {
            "field": "max_forming_depth",
            "question": "What is the maximum draw depth (forming depth) required?",
            "extract_pattern": r"(\d+)\s*(?:mm|depth)",
            "example": "e.g., 500 mm"
        },
        {
            "field": "materials",
            "question": "What materials will you be processing?",
            "extract_pattern": r"(HDPE|ABS|PP|PS|PVC|PMMA|PC|PET|PETG|TPO|HIPS)",
            "example": "e.g., HDPE, ABS, PP"
        }
    ],
    "stage_2": [  # Automation level - determines C vs X
        {
            "field": "sheet_loading",
            "question": "Do you need automatic sheet loading, or is manual loading acceptable?",
            "options": [
                "Automatic (PF1-X series) – Servo pick & place loads sheets automatically, reduces labor, ideal for >500 parts/day",
                "Manual is fine (PF1-C series) – Operator loads sheets, lower cost, good for <200 parts/day"
            ],
            "extract_pattern": r"(auto|manual)",
            "explanation_key": "autoloader"
        },
        {
            "field": "production_volume",
            "question": "What is your expected production volume?",
            "options": ["High volume (>1000 parts/day)", "Medium (100-1000/day)", "Low/Prototype (<100/day)"],
            "extract_pattern": r"(high|medium|low)",
        }
    ],
    "stage_3": [  # Technical details
        {
            "field": "heater_type",
            "question": "Do you have a preference for heater type?",
            "options": ["IR Ceramic (precise, uniform)", "IR Quartz (fast response)", "No preference"],
            "extract_pattern": r"(ceramic|quartz|halogen)",
        },
        {
            "field": "application",
            "question": "What is the application for these parts?",
            "options": ["Automotive", "Packaging", "Industrial", "Consumer products", "Other"],
            "extract_pattern": r"(automotive|packaging|industrial|consumer)",
        }
    ]
}


class InquiryQualifier:
    """Manages the qualification flow for customer inquiries."""
    
    STATE_FILE = PROJECT_ROOT / "data" / "qualification_states.json"
    
    def __init__(self):
        self.profiles: Dict[str, QualificationProfile] = {}
        self._load_states()
    
    def _load_states(self):
        """Load saved qualification states."""
        if self.STATE_FILE.exists():
            try:
                data = json.loads(self.STATE_FILE.read_text())
                for thread_id, profile_dict in data.items():
                    self.profiles[thread_id] = QualificationProfile.from_dict(profile_dict)
            except Exception:
                pass
    
    def _save_states(self):
        """Save qualification states."""
        self.STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        data = {tid: p.to_dict() for tid, p in self.profiles.items()}
        self.STATE_FILE.write_text(json.dumps(data, indent=2, default=str))
    
    def get_or_create_profile(self, thread_id: str, email: str = "") -> QualificationProfile:
        """Get existing profile or create new one."""
        if thread_id not in self.profiles:
            self.profiles[thread_id] = QualificationProfile(
                thread_id=thread_id,
                customer_email=email,
                last_updated=datetime.now().isoformat()
            )
        return self.profiles[thread_id]
    
    def extract_info_from_message(self, message: str, profile: QualificationProfile) -> QualificationProfile:
        """Extract qualification info from a customer message."""
        message_lower = message.lower()
        
        # Extract forming area
        size_match = re.search(r"(\d+)\s*[xX×]\s*(\d+)\s*(mm|m)?", message)
        if size_match:
            w, h = int(size_match.group(1)), int(size_match.group(2))
            unit = size_match.group(3) or "mm"
            if unit == "m":
                w, h = w * 1000, h * 1000
            profile.max_forming_area = (w, h)
        
        # Extract depth
        depth_match = re.search(r"(?:depth|draw|height)[:\s]*(\d+)\s*(?:mm)?", message_lower)
        if depth_match:
            profile.max_forming_depth = int(depth_match.group(1))
        elif re.search(r"(\d+)\s*mm\s*(?:depth|draw|deep)", message_lower):
            match = re.search(r"(\d+)\s*mm\s*(?:depth|draw|deep)", message_lower)
            profile.max_forming_depth = int(match.group(1))
        
        # Extract materials
        materials = re.findall(r"(HDPE|ABS|PP|PS|PVC|PMMA|PC|PET|PETG|TPO|HIPS|acrylic)", message, re.I)
        if materials:
            profile.materials = list(set([m.upper() for m in materials]))
        
        # Extract automation preference
        if "auto" in message_lower and "load" in message_lower:
            profile.sheet_loading = "automatic"
        elif "manual" in message_lower:
            profile.sheet_loading = "manual"
        
        # High volume indicators suggest automatic
        if any(word in message_lower for word in ["high volume", "mass production", "tier 1", "oem"]):
            profile.production_volume = "high"
            if not profile.sheet_loading:
                profile.sheet_loading = "automatic"  # Imply auto for high volume
        
        # Extract application
        if "bedliner" in message_lower or "truck" in message_lower:
            profile.application = "automotive"
            profile.part_description = "pickup truck bedliner"
        elif "packaging" in message_lower or "tray" in message_lower:
            profile.application = "packaging"
        elif "automotive" in message_lower or "car" in message_lower:
            profile.application = "automotive"
        
        # Update stage
        profile.qualification_stage = self._calculate_stage(profile)
        profile.last_updated = datetime.now().isoformat()
        
        self._save_states()
        return profile
    
    def _calculate_stage(self, profile: QualificationProfile) -> int:
        """Calculate qualification stage based on what we know."""
        # Stage 0: Nothing
        if not profile.max_forming_area:
            return 0
        
        # Stage 1: Have basic size
        if not profile.materials and not profile.max_forming_depth:
            return 1
        
        # Stage 2: Have core requirements, need automation level
        if not profile.sheet_loading:
            return 2
        
        # Stage 3: Ready for proposal
        return 3
    
    def get_missing_questions(self, profile: QualificationProfile, max_questions: int = 3) -> List[dict]:
        """Get the next questions to ask based on current stage."""
        questions = []
        
        # Stage 0/1: Ask core requirements
        if profile.qualification_stage <= 1:
            stage_qs = QUALIFICATION_QUESTIONS["stage_1"]
            for q in stage_qs:
                if not getattr(profile, q["field"], None) and q["field"] not in profile.questions_asked:
                    questions.append(q)
                    if len(questions) >= max_questions:
                        break
        
        # Stage 2: Ask automation level (C vs X decision)
        elif profile.qualification_stage == 2:
            stage_qs = QUALIFICATION_QUESTIONS["stage_2"]
            for q in stage_qs:
                if not getattr(profile, q["field"], None) and q["field"] not in profile.questions_asked:
                    questions.append(q)
                    if len(questions) >= max_questions:
                        break
        
        return questions
    
    def is_ready_for_proposal(self, profile: QualificationProfile) -> bool:
        """Check if we have enough info for a proposal."""
        # Minimum requirements for a proposal
        return (
            profile.max_forming_area is not None and
            (profile.sheet_loading is not None or profile.production_volume is not None)
        )
    
    def generate_qualification_message(self, profile: QualificationProfile) -> Optional[str]:
        """Generate the next qualification message to send."""
        questions = self.get_missing_questions(profile)
        
        if not questions:
            return None
        
        # Build friendly message
        intro = ""
        if profile.qualification_stage == 0:
            intro = "Thank you for your inquiry. To recommend the most suitable machine, I need a few details:\n\n"
        elif profile.qualification_stage == 1:
            intro = "Thank you for the information. A few more details will help me provide accurate specifications:\n\n"
        elif profile.qualification_stage == 2:
            intro = "Almost there! One important question to finalize the recommendation:\n\n"
        
        q_text = []
        for i, q in enumerate(questions, 1):
            text = f"**{i}. {q['question']}**"
            if q.get("options"):
                text += "\n   " + "\n   ".join(f"• {opt}" for opt in q["options"])
            elif q.get("example"):
                text += f"\n   ({q['example']})"
            q_text.append(text)
            profile.questions_asked.append(q["field"])
        
        self._save_states()
        
        closing = "\n\nOnce I have this information, I'll provide a detailed technical proposal with specifications and pricing."
        
        return intro + "\n\n".join(q_text) + closing
    
    def get_recommendation_type(self, profile: QualificationProfile) -> str:
        """Determine which machine series to recommend based on qualification."""
        # Automatic loading → PF1-X
        if profile.sheet_loading == "automatic":
            return "PF1-X"
        
        # High volume → PF1-X
        if profile.production_volume == "high":
            return "PF1-X"
        
        # Manual/low volume → PF1-C (cost effective)
        if profile.sheet_loading == "manual" or profile.production_volume == "low":
            return "PF1-C"
        
        # Default: offer both options
        return "BOTH"


# =============================================================================
# CLI for OpenClaw skill
# =============================================================================

if __name__ == "__main__":
    import argparse
    import json
    
    parser = argparse.ArgumentParser(description="Inquiry Qualifier Skill")
    parser.add_argument("--inquiry", required=True, help="The user inquiry to qualify")
    parser.add_argument("--thread-id", default="cli_thread", help="Thread/conversation ID")
    parser.add_argument("--user-id", default="cli_user", help="User ID")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()
    
    qualifier = InquiryQualifier()
    profile = qualifier.get_or_create_profile(args.thread_id, args.user_id)
    profile = qualifier.extract_info_from_message(args.inquiry, profile)
    
    is_ready = qualifier.is_ready_for_proposal(profile)
    recommendation = qualifier.get_recommendation_type(profile) if is_ready else None
    
    if args.json:
        print(json.dumps({
            "qualification_stage": profile.qualification_stage,
            "ready_for_proposal": is_ready,
            "recommendation": recommendation,
            "extracted": {
                "application": profile.application,
                "max_forming_area": profile.max_forming_area,
                "max_forming_depth": profile.max_forming_depth,
                "materials": profile.materials,
                "sheet_loading": profile.sheet_loading,
                "production_volume": profile.production_volume,
            },
            "next_questions": None if is_ready else "Follow-up questions needed",
        }, indent=2))
    else:
        print(f"Qualification Stage: {profile.qualification_stage}")
        print(f"Ready for Proposal: {is_ready}")
        if is_ready:
            print(f"Recommended Machine: {recommendation}")
        else:
            qualification_msg = qualifier.generate_qualification_message(profile)
            if qualification_msg:
                print(f"\nFollow-up Questions:\n{qualification_msg}")
