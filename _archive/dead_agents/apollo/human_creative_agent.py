#!/usr/bin/env python3
"""
HUMAN CREATIVE AGENT
====================

Generates REALISTIC customer emails that feel human, not AI-generated.

Based on the Humanness Model analysis:
- Real conversations score 22+/100
- Simulated conversations score ~11/100
- We need to close that 52% gap

KEY HUMANNESS FACTORS:
1. Messiness - fragments, typos, casual language
2. External Context - bosses, deadlines, competitors
3. Emotions - frustration, excitement, skepticism
4. Specificity - concrete numbers, dates, part numbers
5. Personality - cultural markers, humor, unique voice
6. Objections - real pushback, negotiation tactics
7. Technical Depth - attachments, drawings, specs
8. Timing - realistic gaps, not instant responses
"""

import os
import sys
import json
import random
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, field

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

import openai

client = openai.OpenAI()


# =============================================================================
# HUMANNESS INJECTION TEMPLATES
# =============================================================================

SENTENCE_FRAGMENTS = [
    "Got it.",
    "No problem,",
    "Thanks,",
    "Sure -",
    "OK so",
    "Right.",
    "Understood.",
    "Hmm,",
    "Well,",
    "Anyway,",
]

EXTERNAL_CONTEXT_INJECTIONS = {
    "boss_reference": [
        "I'll need to run this by {boss_name}.",
        "My {boss_title} wants to see the specs.",
        "{boss_name} asked me to get more details.",
        "I'll discuss with {boss_name} and get back to you.",
        "Need to present this to {boss_title} next week.",
    ],
    "deadline_pressure": [
        "We need this by end of {month}.",
        "There's a deadline on our end - {deadline}.",
        "Our production schedule requires delivery by {date}.",
        "We're in a bit of a time crunch here.",
        "Can we speed this up? Management is pushing hard.",
    ],
    "competitor_mention": [
        "We've also been talking to {competitor}.",
        "I got a quote from {competitor} too.",
        "{competitor} is offering something similar.",
        "How do you compare to {competitor}?",
        "Your competitor quoted us {price}.",
    ],
    "economic_context": [
        "Given the current market situation,",
        "Our budget got cut this quarter.",
        "We're being more careful with spending right now.",
        "The economic situation is making us cautious.",
    ],
}

EMOTION_INJECTIONS = {
    "frustration": [
        "Honestly, this price is higher than expected.",
        "I'm a bit concerned about the delivery time.",
        "That's disappointing to hear.",
        "We were hoping for better pricing.",
        "This doesn't quite work for us.",
    ],
    "excitement": [
        "This looks really promising!",
        "I'm excited about this option.",
        "Our team is very interested.",
        "This could be exactly what we need.",
        "Great, this is encouraging.",
    ],
    "skepticism": [
        "Are you sure about those specs?",
        "That seems quite high.",
        "How can we verify this?",
        "I'd want to see that in writing.",
        "Is that actually achievable?",
    ],
    "urgency": [
        "We need a quick decision here.",
        "Can you expedite this?",
        "Time is really tight on our end.",
        "We're under pressure to move fast.",
    ],
}

OBJECTION_TEMPLATES = {
    "price": [
        "The price is above our budget. We were looking at {budget}.",
        "Can you do better on the price? We're talking to others at {competitor_price}.",
        "I can't present this price to management. Is there room for negotiation?",
        "This is more than we expected. What can you do?",
        "{competitor} quoted us {lower_price}. Can you match?",
    ],
    "timing": [
        "The delivery time is too long. We need it by {deadline}.",
        "Can you speed up production? We have a tight schedule.",
        "6 months is too long. What's the fastest you can do?",
    ],
    "specs": [
        "These specs don't quite match what we need.",
        "Can you adjust the {spec} to {requirement}?",
        "We need {specific_feature}. Is that possible?",
    ],
    "trust": [
        "We haven't worked together before. Can you provide references?",
        "How do we know the quality will be consistent?",
        "What guarantees do you offer?",
    ],
}

TECHNICAL_REQUESTS = [
    "Please find the attached drawing for reference.",
    "I've attached our current specs - can you match these?",
    "See the 3D data in the ZIP file.",
    "Here's the technical sheet we're working from.",
    "Can you send me a detailed spec sheet?",
    "Do you have CAD drawings for this model?",
    "What's the tolerance on the forming area?",
    "Can you send the electrical diagrams?",
]

PERSONALITY_MARKERS = {
    "german_formal": {
        "greeting": ["Sehr geehrte Damen und Herren,", "Sehr geehrter Herr {name},"],
        "closing": ["Mit freundlichen Grüßen", "Freundliche Grüße"],
        "style": "formal and precise",
    },
    "american_casual": {
        "greeting": ["Hey there,", "Hi team,", "Hello,"],
        "closing": ["Thanks!", "Best,", "Cheers,"],
        "style": "casual and direct",
    },
    "indian_professional": {
        "greeting": ["Dear Sir/Madam,", "Respected Sir,"],
        "closing": ["Thanking you,", "With regards,"],
        "style": "formal but warm",
    },
    "british_polite": {
        "greeting": ["Good morning,", "Hello,"],
        "closing": ["Kind regards,", "Best regards,"],
        "style": "polite and measured",
    },
}


# =============================================================================
# PERSONAS WITH REALISTIC DEPTH
# =============================================================================

@dataclass
class HumanPersona:
    """A realistic customer persona with depth and quirks."""
    name: str
    company: str
    role: str
    location: str
    industry: str
    
    # Communication style
    cultural_style: str = "american_casual"
    email_length: str = "short"  # short, medium, long
    formality: str = "casual"  # casual, professional, formal
    
    # External context
    boss_name: str = "Sarah"
    boss_title: str = "VP Operations"
    competitor_talking_to: str = "ILLIG"
    deadline: str = "end of Q2"
    
    # Requirements
    budget_inr: int = 5000000
    budget_display: str = "USD 60K"
    forming_area: str = "600 x 900 mm"
    materials: str = "PETG, rPET"
    thickness: str = "3mm"
    
    # Expected machines
    expected_machines: List[str] = field(default_factory=list)
    not_suitable: List[str] = field(default_factory=list)
    
    # Personality quirks
    typo_frequency: float = 0.1  # 10% of emails have typos
    fragment_frequency: float = 0.3  # 30% of emails have fragments
    emotional_tendency: str = "neutral"  # frustrated, excited, skeptical, neutral
    
    # Sales progression
    objection_strength: str = "medium"  # soft, medium, hard


HUMAN_PERSONAS = {
    "mike_chen": HumanPersona(
        name="Mike Chen",
        company="PackForm Solutions",
        role="Founder",
        location="Toronto",
        industry="Sustainable Packaging Startup",
        cultural_style="american_casual",
        email_length="short",
        formality="casual",
        boss_name="himself",
        boss_title="CEO",
        competitor_talking_to="Ridat",
        deadline="before our Series A in Q3",
        budget_inr=5000000,
        budget_display="$60K USD",
        forming_area="600 x 900 mm",
        materials="PETG, rPET",
        thickness="3mm",
        expected_machines=["PF1-C-1309", "PF1-C-1008"],  # Entry-level PF1 fits budget
        not_suitable=["PF1-C-2515", "PF2-P2020", "AM series"],  # Too big/expensive
        typo_frequency=0.15,
        fragment_frequency=0.4,
        emotional_tendency="excited",
        objection_strength="medium",
    ),
    "jean_francois": HumanPersona(
        name="Jean-François Deltenre",
        company="Plastiform Belgium NV",
        role="Technical Director",
        location="Liège, Belgium",
        industry="Automotive Interior",
        cultural_style="german_formal",
        email_length="medium",
        formality="formal",
        boss_name="Marc Van der Berg",
        boss_title="Managing Director",
        competitor_talking_to="Kiefel",
        deadline="before the new model year starts in September",
        budget_inr=18000000,
        budget_display="€200K EUR",
        forming_area="2000 x 1500 mm",
        materials="ABS, TPO, PP",
        thickness="8mm",
        expected_machines=["PF1-X-2015", "PF1-X-2116"],
        not_suitable=["AM series", "UNO", "DUO"],
        typo_frequency=0.05,
        fragment_frequency=0.1,
        emotional_tendency="skeptical",
        objection_strength="hard",
    ),
    "rajesh_sharma": HumanPersona(
        name="Rajesh Sharma",
        company="AutoPlast Components Pvt Ltd",
        role="VP Operations",
        location="Pune",
        industry="Automotive Tier-1",
        cultural_style="indian_professional",
        email_length="medium",
        formality="professional",
        boss_name="Mr. Patel",
        boss_title="Chairman",
        competitor_talking_to="GN Thermoforming",
        deadline="OEM approval deadline in 3 months",
        budget_inr=10000000,
        budget_display="₹1 Crore",
        forming_area="1500 x 1200 mm",
        materials="ABS+PMMA, TPO",
        thickness="6mm",
        expected_machines=["PF1-X-1510", "PF1-C-1510"],
        not_suitable=["AM series", "UNO", "DUO"],
        typo_frequency=0.1,
        fragment_frequency=0.2,
        emotional_tendency="frustrated",
        objection_strength="hard",
    ),
}


# =============================================================================
# HUMAN EMAIL GENERATOR
# =============================================================================

class HumanCreativeAgent:
    """
    Generates realistic, human-like customer emails.
    
    Uses the Humanness Model to ensure emails feel authentic:
    - Injects messiness (fragments, typos)
    - Adds external context (bosses, deadlines)
    - Includes emotions and objections
    - References competitors and technical details
    """
    
    def __init__(self, persona_key: str):
        if persona_key not in HUMAN_PERSONAS:
            raise ValueError(f"Unknown persona: {persona_key}")
        
        self.persona = HUMAN_PERSONAS[persona_key]
        self.conversation_history: List[Dict] = []
        self.current_stage_idx = 0
        self.stages = ["first_contact", "discovery", "technical", "quote", "negotiation", "closing"]
        self.proposal_elements = {"machine": False, "specs": False, "price": False}
    
    @property
    def current_stage(self) -> str:
        return self.stages[min(self.current_stage_idx, len(self.stages) - 1)]
    
    def _inject_humanness(self, base_email: str) -> str:
        """Inject humanness factors into the email."""
        result = base_email
        
        # Inject sentence fragment at start (30% chance based on persona)
        if random.random() < self.persona.fragment_frequency:
            fragment = random.choice(SENTENCE_FRAGMENTS)
            result = f"{fragment}\n\n{result}"
        
        # Inject typos (based on persona frequency)
        if random.random() < self.persona.typo_frequency:
            typo_spots = [
                ("the ", "teh "),
                ("and ", "adn "),
                ("with ", "wiht "),
                (" a ", "  a "),
            ]
            typo = random.choice(typo_spots)
            result = result.replace(typo[0], typo[1], 1)
        
        return result
    
    def _get_stage_specific_content(self) -> Dict:
        """Get content elements specific to current stage."""
        
        stage = self.current_stage
        persona = self.persona
        
        content = {
            "external_context": "",
            "emotion": "",
            "objection": "",
            "technical": "",
        }
        
        # External context (increases as conversation progresses)
        if stage in ["discovery", "technical", "quote"]:
            if persona.boss_name != "himself":
                template = random.choice(EXTERNAL_CONTEXT_INJECTIONS["boss_reference"])
                content["external_context"] = template.format(
                    boss_name=persona.boss_name,
                    boss_title=persona.boss_title,
                )
        
        if stage in ["quote", "negotiation"]:
            if random.random() > 0.5:
                template = random.choice(EXTERNAL_CONTEXT_INJECTIONS["competitor_mention"])
                content["external_context"] += " " + template.format(
                    competitor=persona.competitor_talking_to,
                    price="15% less",
                )
        
        # Emotions (based on persona tendency)
        emotion_type = persona.emotional_tendency
        if emotion_type != "neutral" and random.random() > 0.4:
            content["emotion"] = random.choice(EMOTION_INJECTIONS.get(emotion_type, [""]))
        
        # Objections (intensify as we reach negotiation)
        if stage == "negotiation":
            objection_type = random.choice(["price", "timing", "specs"])
            template = random.choice(OBJECTION_TEMPLATES[objection_type])
            content["objection"] = template.format(
                budget=persona.budget_display,
                competitor_price="20% less",
                competitor=persona.competitor_talking_to,
                lower_price="$45K",
                deadline=persona.deadline,
                spec="forming area",
                requirement="larger",
                specific_feature="servo drives",
            )
        
        # Technical requests (in technical stage)
        if stage == "technical":
            content["technical"] = random.choice(TECHNICAL_REQUESTS)
        
        return content
    
    def generate_email(self, ira_last_response: str = None) -> Dict:
        """Generate a realistic customer email."""
        
        persona = self.persona
        style = PERSONALITY_MARKERS.get(persona.cultural_style, PERSONALITY_MARKERS["american_casual"])
        stage_content = self._get_stage_specific_content()
        
        # Build conversation context
        history_text = ""
        if self.conversation_history:
            for turn in self.conversation_history[-2:]:
                role = "ME" if turn['role'] == 'customer' else "IRA"
                history_text += f"\n{role}: {turn['content'][:200]}...\n"
        
        prompt = f"""Generate a realistic B2B sales email from a customer.

PERSONA:
- Name: {persona.name}
- Company: {persona.company}
- Role: {persona.role}
- Location: {persona.location}
- Style: {style['style']} ({persona.cultural_style})
- Email length: {persona.email_length}

REQUIREMENTS:
- Forming area: {persona.forming_area}
- Materials: {persona.materials}
- Thickness: {persona.thickness}
- Budget: {persona.budget_display}

SUITABLE MACHINES: {', '.join(persona.expected_machines)}
NOT SUITABLE: {', '.join(persona.not_suitable)}

SALES STAGE: {self.current_stage}

EXTERNAL CONTEXT TO INCLUDE:
- Boss: {persona.boss_name} ({persona.boss_title})
- Deadline: {persona.deadline}
- Competitor: {persona.competitor_talking_to}

PREVIOUS CONVERSATION:
{history_text}

{f"IRA'S LAST RESPONSE:{chr(10)}{ira_last_response[:500]}" if ira_last_response else "This is the first email."}

HUMANNESS REQUIREMENTS:
1. Use {persona.email_length} email length (not essay-like)
2. Include ONE of these naturally: {stage_content}
3. Start with: {random.choice(style['greeting']).format(name='Team')}
4. End with: {random.choice(style['closing'])}
5. {f"Add a minor typo" if random.random() < persona.typo_frequency else "No typos needed"}
6. {f"Start with a fragment like 'Got it.' or 'Thanks,'" if random.random() < persona.fragment_frequency else "Normal start"}

Write a SHORT, REALISTIC email. NOT a template. Make it feel like a real person wrote it quickly.

Output JSON:
{{
    "subject": "Email subject (short, realistic)",
    "body": "The email body",
    "humanness_elements": ["what human elements you included"]
}}"""
        
        try:
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You write realistic, human B2B emails. Keep them SHORT and natural."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.9,  # Higher temperature for more variety
            )
            
            result = json.loads(response.choices[0].message.content)
            
            # Post-process for humanness
            result['body'] = self._inject_humanness(result.get('body', ''))
            
            # Add signature
            closing = random.choice(style['closing'])
            if closing not in result['body']:
                result['body'] += f"\n\n{closing}\n{persona.name}"
            
            # Record in history
            self.conversation_history.append({
                'role': 'customer',
                'content': result['body'],
                'stage': self.current_stage,
            })
            
            return result
            
        except Exception as e:
            print(f"Error generating email: {e}")
            return self._fallback_email()
    
    def _fallback_email(self) -> Dict:
        """Fallback simple email."""
        persona = self.persona
        return {
            "subject": f"Quick question - {persona.company}",
            "body": f"""Hi,

{random.choice(SENTENCE_FRAGMENTS)}

Looking for a thermoforming machine - {persona.forming_area}, budget around {persona.budget_display}.

What do you have?

{persona.name}""",
            "humanness_elements": ["short", "fragment", "casual"],
        }
    
    def record_ira_response(self, response: str, evaluation: Dict = None):
        """Record IRA's response and track proposal progress."""
        self.conversation_history.append({
            'role': 'ira',
            'content': response,
            'stage': self.current_stage,
        })
        
        # Track proposal elements
        if evaluation:
            progress = evaluation.get('proposal_progress', {})
            if progress.get('machine_model_given'):
                self.proposal_elements['machine'] = True
            if progress.get('specs_provided'):
                self.proposal_elements['specs'] = True
            if progress.get('price_quoted'):
                self.proposal_elements['price'] = True
    
    def advance_stage(self):
        """Move to next stage."""
        self.current_stage_idx += 1
    
    def is_proposal_ready(self) -> bool:
        """Check if we have all proposal elements."""
        return all(self.proposal_elements.values())


# =============================================================================
# TEST
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("HUMAN CREATIVE AGENT TEST")
    print("=" * 60)
    
    agent = HumanCreativeAgent("mike_chen")
    
    print(f"\nPersona: {agent.persona.name} ({agent.persona.company})")
    print(f"Style: {agent.persona.cultural_style}")
    print(f"Budget: {agent.persona.budget_display}")
    print()
    
    # Generate first email
    email1 = agent.generate_email()
    print(f"STAGE: {agent.current_stage}")
    print(f"SUBJECT: {email1['subject']}")
    print(f"BODY:\n{email1['body']}")
    print(f"\nHumanness elements: {email1.get('humanness_elements', [])}")
    
    # Simulate IRA response
    agent.record_ira_response("Thank you for your inquiry. For your requirements...")
    agent.advance_stage()
    
    # Generate follow-up
    print("\n" + "=" * 60)
    email2 = agent.generate_email("Thank you for your inquiry. Based on your 600x900mm requirement, I recommend the UNO-1208 at approximately $24,000 USD...")
    print(f"STAGE: {agent.current_stage}")
    print(f"SUBJECT: {email2['subject']}")
    print(f"BODY:\n{email2['body']}")
