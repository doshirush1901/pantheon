#!/usr/bin/env python3
"""
CREATIVE CUSTOMER AGENT for Apollo Sales Training

Generates realistic customer emails by learning from actual Rushabh conversations.
Uses the extracted sales flow patterns to create authentic multi-turn dialogues.

The training loop:
1. Creative Agent generates "customer" email (based on real patterns)
2. Ira responds through her full pipeline
3. Evaluator scores the response
4. Both sides learn from the interaction

This creates high-quality training data showing realistic sales progressions.
"""

import json
import random
import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent.parent.parent

# Load environment
from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

import openai


# =============================================================================
# LOAD REAL SALES PATTERNS (from our email extraction)
# =============================================================================

def load_sales_patterns() -> Dict:
    """Load the extracted sales flow patterns."""
    patterns_file = PROJECT_ROOT / "data" / "training" / "sales_flow_patterns.json"
    if patterns_file.exists():
        with open(patterns_file) as f:
            return json.load(f)
    return {}


def load_stage_training() -> Dict:
    """Load stage-specific training data."""
    stage_file = PROJECT_ROOT / "data" / "training" / "sales_stage_training.json"
    if stage_file.exists():
        with open(stage_file) as f:
            return json.load(f)
    return {}


def load_action_training() -> Dict:
    """Load action recommendations for each stage."""
    action_file = PROJECT_ROOT / "data" / "training" / "sales_action_training.json"
    if action_file.exists():
        with open(action_file) as f:
            return json.load(f)
    return {}


# =============================================================================
# CUSTOMER PERSONAS (Enhanced with real data)
# =============================================================================

ENHANCED_PERSONAS = {
    "dutch_hydroponics": {
        "name": "Jurriaan van der Berg",
        "company": "Dutch Tides BV",
        "role": "Technical Director",
        "location": "Netherlands",
        "currency": "EUR",
        "industry": "Hydroponics",
        "materials": "HIPS, PET",
        "forming_area": "6500 x 2000 mm",
        "application": "Growing trays for vertical farming",
        "personality": "Technical, eco-focused, long decision cycle",
        "based_on": "DutchTides real customer journey - 22 months to close",
        "typical_questions": [
            "What's the energy consumption compared to old machines?",
            "Can we visit a reference site in Netherlands?",
            "How does your machine handle recycled HIPS?",
            "What's the lead time for spare parts in Europe?",
        ],
        "objections": [
            "Your competitor ILLIG quoted 15% less",
            "We need to wait for our subsidy approval",
            "22 months lead time is too long",
        ],
    },
    "polish_automotive": {
        "name": "Piotr Kowalski",
        "company": "JoPlast Sp. z o.o.",
        "role": "Production Manager",
        "location": "Poland",
        "currency": "EUR",
        "industry": "Automotive Interior",
        "materials": "ABS, TPO",
        "forming_area": "2000 x 1500 mm",
        "application": "Dashboard components, door panels",
        "personality": "Price-conscious, needs OEM approval, quick decider",
        "based_on": "JoPlast real customer - 7 months to close",
        "typical_questions": [
            "What's the cycle time for 4mm ABS?",
            "Do you have automotive OEM certifications?",
            "Can you handle in-mold graining?",
            "What's included in commissioning support?",
        ],
        "objections": [
            "Our OEM customer prefers European machines",
            "We need financing options",
            "Can you beat the Chinese machine price?",
        ],
    },
    "belgian_manufacturer": {
        "name": "Jean-François Deltenre",
        "company": "Batelaan Kunststoffen",
        "role": "Plant Manager",
        "location": "Belgium",
        "currency": "EUR",
        "industry": "Industrial Parts",
        "materials": "HDPE, PP",
        "forming_area": "1800 x 1200 mm",
        "application": "Industrial trays, containers",
        "personality": "Conservative, wants local service, references critical",
        "based_on": "Batelaan real customer - 3 months fast close",
        "typical_questions": [
            "Who provides service support in Benelux?",
            "Can we see the machine at K-Show?",
            "What's your warranty period?",
            "How fast can you deliver spare parts?",
        ],
        "objections": [
            "We've always used German machines",
            "What if there's a breakdown - how fast is your response?",
            "Budget approval takes time",
        ],
    },
    "irish_fabricator": {
        "name": "Declan O'Brien",
        "company": "Donite Plastics",
        "role": "Operations Director",
        "location": "Ireland",
        "currency": "EUR",
        "industry": "Aerospace/Medical",
        "materials": "ABS, PMMA, PEEK",
        "forming_area": "2500 x 1800 mm",
        "application": "Aerospace interior panels, medical housings",
        "personality": "Quality-focused, needs certifications, deliberate",
        "based_on": "Donite real customer journey",
        "typical_questions": [
            "What quality certifications do you have?",
            "Can you provide material traceability?",
            "What's your tolerance capability?",
            "Do you have aerospace customer references?",
        ],
        "objections": [
            "We need AS9100 compliant suppliers",
            "Lead time doesn't fit our project timeline",
            "Need to validate with our customer first",
        ],
    },
    "italian_skeptic": {
        "name": "Carlo Minini",
        "company": "Minini Plastic SRL",
        "role": "Purchasing Manager",
        "location": "Italy",
        "currency": "EUR",
        "industry": "Packaging",
        "materials": "PET, HIPS, PP",
        "forming_area": "1500 x 1200 mm",
        "application": "Food packaging, blister packs",
        "personality": "Skeptical of Asian machines, needs convincing",
        "based_on": "European sales conversations",
        "typical_questions": [
            "How do you compare to ILLIG and Kiefel?",
            "What's your installed base in Europe?",
            "Who does local service in Italy?",
            "Can I speak to a European reference?",
        ],
        "objections": [
            "We've had bad experiences with Asian machines",
            "Your price is competitive but quality concerns remain",
            "We prefer to buy from established European brands",
        ],
    },
    "tough_negotiator": {
        "name": "Viktor Petrov",
        "company": "EuroPack Industries",
        "role": "CEO",
        "location": "Czech Republic",
        "currency": "EUR",
        "industry": "Consumer Packaging",
        "materials": "Various",
        "forming_area": "3000 x 2000 mm",
        "application": "High-volume consumer packaging",
        "personality": "Aggressive negotiator, plays competitors, delays",
        "based_on": "Tough negotiation scenarios",
        "typical_questions": [
            "Why should I buy from you instead of Chinese?",
            "ILLIG gave me 25% discount - can you match?",
            "What's the absolute best price you can do?",
            "I need 2 machines - what's the volume discount?",
        ],
        "objections": [
            "Your competitor just reduced their price",
            "Management rejected the budget",
            "We're reconsidering the project entirely",
            "Another supplier offered better payment terms",
        ],
    },
}


# =============================================================================
# SALES STAGE PROGRESSIONS (from real data)
# =============================================================================

STAGE_PROGRESSIONS = {
    "fast_track": {
        "description": "Buyer has clear requirements and budget - closes in 2-4 months",
        "stages": ["first_contact", "discovery", "technical", "quote_request", "closing"],
        "typical_turns": 5,
        "win_rate": 0.85,
    },
    "standard_with_visit": {
        "description": "Standard cycle with factory visit - 4-8 months",
        "stages": ["first_contact", "discovery", "technical", "factory_visit_offer", 
                  "factory_visit_confirmed", "negotiation", "closing"],
        "typical_turns": 8,
        "win_rate": 0.90,
    },
    "long_cycle": {
        "description": "Budget-constrained or complex decision - 12-24 months",
        "stages": ["first_contact", "discovery", "nurture", "discovery", "technical",
                  "quote_request", "objection_handling", "negotiation", "closing"],
        "typical_turns": 12,
        "win_rate": 0.60,
    },
    "objection_recovery": {
        "description": "Customer raises objections, needs convincing",
        "stages": ["technical", "objection_handling", "factory_visit_offer",
                  "negotiation", "closing"],
        "typical_turns": 6,
        "win_rate": 0.50,
    },
}


# =============================================================================
# CREATIVE CUSTOMER AGENT
# =============================================================================

@dataclass
class GeneratedEmail:
    """A generated customer email."""
    stage: str
    subject: str
    body: str
    expected_response_type: str
    key_questions: List[str]
    objections_raised: List[str]
    buying_signals: List[str]


class CreativeCustomerAgent:
    """
    LLM-powered agent that generates realistic customer emails.
    
    Uses extracted patterns from real Rushabh conversations to create
    authentic multi-turn dialogues for training Ira.
    """
    
    def __init__(self, persona_key: str = "dutch_hydroponics"):
        self.persona = ENHANCED_PERSONAS.get(persona_key, ENHANCED_PERSONAS["dutch_hydroponics"])
        self.sales_patterns = load_sales_patterns()
        self.stage_training = load_stage_training()
        self.action_training = load_action_training()
        
        self.conversation_history: List[Dict] = []
        self.current_stage = "first_contact"
        self.turn_count = 0
        
        # Select a progression pattern
        self.progression = random.choice(list(STAGE_PROGRESSIONS.values()))
        
        # Initialize OpenAI client
        self.client = openai.OpenAI()
    
    def _build_context_prompt(self, ira_last_response: Optional[str] = None) -> str:
        """Build the context prompt for email generation."""
        
        context = f"""You are role-playing as a customer in a B2B thermoforming machine sales conversation.

## YOUR PERSONA
Name: {self.persona['name']}
Company: {self.persona['company']}
Role: {self.persona['role']}
Location: {self.persona['location']}
Industry: {self.persona['industry']}
Application: {self.persona['application']}
Materials: {self.persona['materials']}
Forming Area: {self.persona['forming_area']}
Currency: {self.persona['currency']}
Personality: {self.persona['personality']}

## CURRENT SALES STAGE: {self.current_stage}
Turn: {self.turn_count + 1}

## STAGE-SPECIFIC BEHAVIOR

"""
        # Add stage-specific guidance from training data
        stage_def = self.stage_training.get("stage_definitions", {}).get(self.current_stage, {})
        if stage_def:
            context += f"""This stage ({self.current_stage}) is about: {stage_def.get('description', '')}

Typical patterns at this stage: {', '.join(stage_def.get('patterns', [])[:5])}

"""
        
        # Add conversation history
        if self.conversation_history:
            context += "## CONVERSATION HISTORY\n"
            for turn in self.conversation_history[-4:]:  # Last 4 turns
                context += f"\n[{turn['role'].upper()}]: {turn['content'][:300]}...\n"
        
        # Add last IRA response
        if ira_last_response:
            context += f"\n## IRA'S LAST RESPONSE\n{ira_last_response[:500]}\n"
        
        # Add realistic behaviors
        context += f"""
## YOUR REALISTIC BEHAVIORS

Typical questions you ask:
{chr(10).join(f'- {q}' for q in self.persona['typical_questions'][:3])}

Objections you might raise:
{chr(10).join(f'- {o}' for o in self.persona['objections'][:2])}

## INSTRUCTIONS

Generate a realistic customer email that:
1. Fits the current sales stage ({self.current_stage})
2. Responds naturally to IRA's last message (if any)
3. Asks relevant questions for your persona
4. Shows realistic buying behavior (enthusiasm, hesitation, or objections)
5. Moves the conversation forward or sideways realistically

DO NOT:
- Be too eager or too negative
- Ask questions already answered
- Ignore IRA's response
- Write unrealistically long emails

Write the email as if you are really this customer writing to Machinecraft.
"""
        return context
    
    def generate_customer_email(self, ira_last_response: Optional[str] = None) -> GeneratedEmail:
        """Generate a realistic customer email using LLM."""
        
        context_prompt = self._build_context_prompt(ira_last_response)
        
        system_prompt = """You are an expert at role-playing B2B customers in sales scenarios.
Generate realistic, professional business emails that mirror how real customers communicate.
Output JSON with the email content and metadata."""
        
        user_prompt = f"""{context_prompt}

Generate a customer email for this stage. Output as JSON:
{{
    "subject": "Email subject line",
    "body": "The full email body",
    "key_questions": ["List of main questions asked"],
    "objections_raised": ["Any objections or concerns expressed"],
    "buying_signals": ["Any positive buying signals shown"]
}}"""
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.8,  # Some creativity
            )
            
            result = json.loads(response.choices[0].message.content)
            
            email = GeneratedEmail(
                stage=self.current_stage,
                subject=result.get("subject", "Inquiry"),
                body=result.get("body", ""),
                expected_response_type=self._get_expected_response_type(),
                key_questions=result.get("key_questions", []),
                objections_raised=result.get("objections_raised", []),
                buying_signals=result.get("buying_signals", []),
            )
            
            # Record in history
            self.conversation_history.append({
                "role": "customer",
                "content": email.body,
                "stage": self.current_stage,
            })
            
            return email
            
        except Exception as e:
            print(f"Error generating email: {e}")
            # Fallback to template
            return self._generate_template_email()
    
    def _get_expected_response_type(self) -> str:
        """Get what type of response IRA should give at this stage."""
        stage_actions = {
            "first_contact": "introduction_and_qualification",
            "discovery": "needs_assessment_questions",
            "technical": "specs_and_recommendations",
            "quote_request": "prepare_quotation",
            "factory_visit_offer": "arrange_visit",
            "negotiation": "handle_terms",
            "objection_handling": "address_concerns",
            "closing": "facilitate_order",
        }
        return stage_actions.get(self.current_stage, "general_response")
    
    def _generate_template_email(self) -> GeneratedEmail:
        """Fallback template-based generation."""
        templates = {
            "first_contact": f"""Dear Sir/Madam,

We are {self.persona['company']} based in {self.persona['location']}. We are looking for a thermoforming machine for {self.persona['application']}.

Our requirements:
- Forming area: {self.persona['forming_area']}
- Materials: {self.persona['materials']}

Please send your catalog and pricing.

Best regards,
{self.persona['name']}
{self.persona['role']}""",
        }
        
        body = templates.get(self.current_stage, templates["first_contact"])
        
        return GeneratedEmail(
            stage=self.current_stage,
            subject=f"Inquiry from {self.persona['company']}",
            body=body,
            expected_response_type=self._get_expected_response_type(),
            key_questions=["Pricing?", "Catalog?"],
            objections_raised=[],
            buying_signals=["Initial interest"],
        )
    
    def record_ira_response(self, response: str):
        """Record IRA's response in conversation history."""
        self.conversation_history.append({
            "role": "ira",
            "content": response,
            "stage": self.current_stage,
        })
    
    def advance_stage(self, ira_response: str) -> str:
        """Determine next stage based on IRA's response and conversation flow."""
        self.turn_count += 1
        
        # Use progression pattern
        stages = self.progression["stages"]
        if self.turn_count < len(stages):
            self.current_stage = stages[self.turn_count]
        else:
            self.current_stage = "closing"
        
        return self.current_stage
    
    def should_continue(self) -> bool:
        """Determine if simulation should continue."""
        # Check if we've reached natural end
        if self.current_stage == "closing":
            return False
        
        # Max turns
        if self.turn_count >= self.progression.get("typical_turns", 8):
            return False
        
        return True
    
    def determine_outcome(self) -> str:
        """Determine final outcome based on conversation."""
        # Use win rate from progression
        win_rate = self.progression.get("win_rate", 0.5)
        return "won" if random.random() < win_rate else "lost"


# =============================================================================
# TRAINING LOOP
# =============================================================================

async def run_training_simulation(
    persona_key: str = "dutch_hydroponics",
    max_turns: int = 6,
    save_output: bool = True
) -> Dict:
    """
    Run a complete training simulation:
    1. Creative agent generates customer emails
    2. Ira responds through her full pipeline
    3. Results are saved for training
    """
    import sys
    sys.path.insert(0, str(PROJECT_ROOT))
    sys.path.insert(0, str(PROJECT_ROOT / "openclaw" / "agents" / "ira"))
    
    # Import IRA's response generator
    try:
        from src.agents import research, write, verify
        from src.agents.chief_of_staff.agent import analyze_intent
        IRA_AVAILABLE = True
    except ImportError:
        IRA_AVAILABLE = False
        print("Warning: IRA not available, will use mock responses")
    
    # Initialize creative agent
    creative_agent = CreativeCustomerAgent(persona_key)
    
    print(f"\n{'='*70}")
    print(f"APOLLO CREATIVE TRAINING SIMULATION")
    print(f"{'='*70}")
    print(f"Persona: {creative_agent.persona['name']} ({creative_agent.persona['company']})")
    print(f"Progression: {creative_agent.progression['description']}")
    print(f"Expected turns: {creative_agent.progression['typical_turns']}")
    print(f"{'='*70}\n")
    
    simulation_data = {
        "persona": creative_agent.persona,
        "progression": creative_agent.progression["description"],
        "started_at": datetime.now().isoformat(),
        "turns": [],
    }
    
    ira_last_response = None
    
    while creative_agent.should_continue() and creative_agent.turn_count < max_turns:
        # Generate customer email
        customer_email = creative_agent.generate_customer_email(ira_last_response)
        
        print(f"\n{'─'*50}")
        print(f"TURN {creative_agent.turn_count + 1} - Stage: {customer_email.stage}")
        print(f"{'─'*50}")
        print(f"\n📧 CUSTOMER ({creative_agent.persona['name']}):")
        print(f"Subject: {customer_email.subject}")
        print(f"\n{customer_email.body}")
        
        if customer_email.key_questions:
            print(f"\n❓ Key Questions: {', '.join(customer_email.key_questions)}")
        if customer_email.objections_raised:
            print(f"⚠️ Objections: {', '.join(customer_email.objections_raised)}")
        if customer_email.buying_signals:
            print(f"✅ Buying Signals: {', '.join(customer_email.buying_signals)}")
        
        # Get IRA's response
        print(f"\n🤖 IRA's Response:")
        
        if IRA_AVAILABLE:
            try:
                intent = analyze_intent(customer_email.body)
                research_output = await research(customer_email.body, {
                    "intent": intent,
                    "customer_name": creative_agent.persona["name"],
                })
                context = {
                    "intent": intent,
                    "channel": "email",
                    "research_output": research_output,
                    "customer_name": creative_agent.persona["name"],
                    "customer_company": creative_agent.persona["company"],
                }
                draft = await write(customer_email.body, context)
                ira_response = await verify(draft, customer_email.body, context)
            except Exception as e:
                ira_response = f"[IRA Error: {e}]"
        else:
            ira_response = f"[Mock IRA response for stage: {customer_email.stage}]"
        
        print(ira_response)
        
        # Record
        creative_agent.record_ira_response(ira_response)
        ira_last_response = ira_response
        
        turn_data = {
            "turn": creative_agent.turn_count,
            "stage": customer_email.stage,
            "customer_email": {
                "subject": customer_email.subject,
                "body": customer_email.body,
                "key_questions": customer_email.key_questions,
                "objections": customer_email.objections_raised,
                "buying_signals": customer_email.buying_signals,
            },
            "ira_response": ira_response,
            "expected_response_type": customer_email.expected_response_type,
        }
        simulation_data["turns"].append(turn_data)
        
        # Advance stage
        creative_agent.advance_stage(ira_response)
    
    # Determine outcome
    outcome = creative_agent.determine_outcome()
    simulation_data["outcome"] = outcome
    simulation_data["ended_at"] = datetime.now().isoformat()
    simulation_data["total_turns"] = len(simulation_data["turns"])
    
    print(f"\n{'='*70}")
    print(f"SIMULATION COMPLETE")
    print(f"{'='*70}")
    print(f"Total turns: {simulation_data['total_turns']}")
    print(f"Outcome: {outcome.upper()}")
    print(f"{'='*70}\n")
    
    # Save output
    if save_output:
        output_dir = PROJECT_ROOT / "data" / "simulations"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = output_dir / f"creative_sim_{persona_key}_{timestamp}.json"
        
        with open(output_file, 'w') as f:
            json.dump(simulation_data, f, indent=2)
        
        print(f"Saved to: {output_file}")
    
    return simulation_data


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    import argparse
    import asyncio
    
    parser = argparse.ArgumentParser(description="Apollo Creative Customer Agent")
    parser.add_argument("--persona", type=str, default="dutch_hydroponics",
                       choices=list(ENHANCED_PERSONAS.keys()),
                       help="Customer persona")
    parser.add_argument("--turns", type=int, default=6, help="Max turns")
    parser.add_argument("--no-save", action="store_true", help="Don't save output")
    
    args = parser.parse_args()
    
    asyncio.run(run_training_simulation(
        persona_key=args.persona,
        max_turns=args.turns,
        save_output=not args.no_save,
    ))
