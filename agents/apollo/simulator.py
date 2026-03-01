#!/usr/bin/env python3
"""
APOLLO - Sales Simulation Agent
===============================

Generates realistic customer personas and simulates multi-turn sales
conversations with IRA to test and train her responses.

Usage:
    python agents/apollo/simulator.py
    python agents/apollo/simulator.py --persona european
    python agents/apollo/simulator.py --rounds 5
"""

import json
import random
import asyncio
import sys
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "openclaw" / "agents" / "ira"))

# Try to import OpenAI for creative generation
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

# Try to import IRA
try:
    from src.brain.generate_answer import generate_answer
    IRA_AVAILABLE = True
except ImportError:
    IRA_AVAILABLE = False


# =============================================================================
# CUSTOMER PERSONAS (Based on Real Training Data)
# =============================================================================

PERSONAS = {
    "european": {
        "name": "Jean-François Deltenre",
        "company": "Plastiform Belgium NV",
        "email": "jf.deltenre@plastiform.be",
        "role": "Technical Director",
        "industry": "Automotive Interior",
        "location": "Belgium",
        "currency": "EUR",
        "budget_range": "150,000 - 280,000",
        "current_machine": "ILLIG UA 100g (15 years old)",
        "interest": "Replace aging machine with modern servo-driven system",
        "materials": "ABS, TPO, PP",
        "forming_area": "2000 x 1500 mm",
        "depth": "650 mm",
        "thickness": "up to 8mm",
        "personality": "Technical, detail-oriented, wants references",
        "pain_points": ["High maintenance costs", "Energy consumption", "Slow cycle times"],
        "decision_timeline": "6 months",
    },
    "indian_auto": {
        "name": "Rajesh Sharma",
        "company": "AutoPlast Components Pvt Ltd",
        "email": "rajesh.sharma@autoplast.co.in",
        "role": "VP Operations",
        "industry": "Automotive Supplier",
        "location": "Pune, India",
        "currency": "INR",
        "budget_range": "80 Lakhs - 1.2 Crore",
        "current_machine": "None (new line)",
        "interest": "New thermoforming line for dashboard components",
        "materials": "ABS+PMMA, TPO",
        "forming_area": "1500 x 1200 mm",
        "depth": "500 mm",
        "thickness": "up to 6mm",
        "personality": "Price-conscious, wants OEM approvals, fast decision",
        "pain_points": ["Need OEM qualification", "Tight project timeline", "Cost pressure"],
        "decision_timeline": "3 months",
    },
    "us_distributor": {
        "name": "Josh Szabo",
        "company": "Plastics Machinery Group",
        "email": "joshs@plasticsmg.com",
        "role": "Sales Manager",
        "industry": "Machinery Distribution",
        "location": "Ohio, USA",
        "currency": "USD",
        "budget_range": "Varies by customer",
        "current_machine": "N/A - Reseller",
        "interest": "Partnership, stock machine for showroom",
        "materials": "All types",
        "forming_area": "Various",
        "depth": "Various",
        "thickness": "Various",
        "personality": "Business-focused, wants margins and exclusivity",
        "pain_points": ["Need competitive pricing", "Demo machine for customers", "After-sales support"],
        "decision_timeline": "Ongoing",
    },
    "startup": {
        "name": "Mike Chen",
        "company": "PackForm Solutions",
        "email": "mike@packform.io",
        "role": "Founder",
        "industry": "Packaging Startup",
        "location": "Toronto, Canada",
        "currency": "USD",
        "budget_range": "50,000 - 80,000",
        "current_machine": "None",
        "interest": "Entry-level machine for custom packaging",
        "materials": "PETG, HIPS",
        "forming_area": "600 x 900 mm",
        "depth": "300 mm",
        "thickness": "up to 3mm",
        "personality": "Enthusiastic but budget-constrained, needs hand-holding",
        "pain_points": ["Limited capital", "No thermoforming experience", "Need training"],
        "decision_timeline": "1-2 months if price is right",
    },
    "large_project": {
        "name": "Dr. Ahmed Al-Rashid",
        "company": "Gulf Industrial Solutions",
        "email": "ahmed.rashid@gulfind.ae",
        "role": "Procurement Director",
        "industry": "Industrial Manufacturing",
        "location": "Dubai, UAE",
        "currency": "USD",
        "budget_range": "500,000 - 1,000,000",
        "current_machine": "Multiple requirements",
        "interest": "Turnkey thermoforming facility (3-4 machines)",
        "materials": "HDPE, ABS, Acrylic",
        "forming_area": "3000 x 2000 mm",
        "depth": "800 mm",
        "thickness": "up to 15mm",
        "personality": "Formal, process-driven, needs compliance docs",
        "pain_points": ["Need international references", "Local service support", "Payment terms"],
        "decision_timeline": "9-12 months (tender process)",
    },
}

# =============================================================================
# SALES STAGE TEMPLATES
# =============================================================================

STAGE_TEMPLATES = {
    "initial_inquiry": [
        """Dear Sir,

We are {company} based in {location}. We are looking for a thermoforming machine with the following specifications:
- Forming area: {forming_area}
- Maximum depth: {depth}
- Materials: {materials}

Could you please send us your catalog and pricing information?

Best regards,
{name}
{role}""",

        """Hi,

I found your company online while searching for thermoforming machines. We currently have a {current_machine} but are looking to upgrade.

Our requirements:
- Sheet size: {forming_area}
- Material thickness: {thickness}
- Application: {industry}

What models would you recommend and what's the budget we should expect?

Thanks,
{name}""",

        """Hello Machinecraft Team,

We are evaluating suppliers for our new {industry} project. We need a machine capable of:
- {forming_area} forming area
- {materials} processing
- {depth} draw depth

Please provide quotation and lead time.

{name}
{company}""",
    ],
    
    "technical_followup": [
        """Thank you for the information.

A few technical questions:
1. What is the cycle time for {thickness} {materials}?
2. Is servo drive standard or optional?
3. Do you have any reference sites in {location} or nearby?

Also, can you share a video of a similar machine in operation?

{name}""",

        """Hi,

Thanks for the quote. Before we proceed, we need clarification on:
- Heater type: ceramic vs quartz - what do you recommend for {materials}?
- Vacuum system: what CFM/capacity?
- Frame system: universal or fixed?

Our engineering team will review once we have these details.

Best,
{name}""",
    ],
    
    "commercial_discussion": [
        """Dear Rushabh,

We've reviewed your technical proposal and it looks good. Now let's discuss commercial terms:

1. Your quoted price of {currency} {budget_range} - is there room for negotiation?
2. Payment terms - can you do 30% advance, 60% before shipment, 10% after commissioning?
3. What's included in the price? Installation? Training?

We have {decision_timeline} to make a decision.

Regards,
{name}""",

        """Hi,

The specs look fine. However, we've received a quote from [competitor] that is about 15-20% lower.

Can you review your pricing? We prefer to work with Machinecraft based on your reputation, but budget is a concern.

{name}""",
    ],
    
    "objection": [
        """Dear Rushabh,

Thank you for the revised quote. Unfortunately, we have some concerns:

1. Lead time of 4-5 months is longer than we expected
2. We don't have a reference site nearby to visit
3. What happens if there are issues after warranty?

Can you address these?

{name}""",

        """Hi,

We need to put this on hold for now. {random_delay_reason}

I'll get back to you once we have clarity. Please keep the quote valid.

Thanks,
{name}""",
    ],
    
    "positive_progress": [
        """Dear Rushabh,

Good news - we've received internal approval to proceed!

Next steps:
1. Can we schedule a video call to finalize specs?
2. We'd like to visit your factory or a reference site
3. Please prepare the proforma invoice

When are you available?

{name}""",

        """Hi,

We're ready to move forward. A few final questions:
1. Can you deliver in 3 months instead of 4?
2. Can we do a factory acceptance test (FAT)?
3. What's your commissioning support?

Looking forward to working together.

{name}""",
    ],
    
    "closing": [
        """Dear Rushabh,

Please send the proforma invoice with the following details:
- Machine: {machine_model}
- Price: As quoted
- Payment terms: As discussed
- Delivery: {delivery_timeline}

We'll process the advance payment upon receipt.

Best regards,
{name}
{company}""",

        """Hi Rushabh,

After much deliberation, we've decided to go with another supplier this time. The main reasons were:
- {decline_reason}

However, we'll keep Machinecraft in mind for future projects. Thank you for your time and effort.

Best,
{name}""",
    ],
}

DELAY_REASONS = [
    "Our budget has been frozen until next quarter.",
    "We're waiting for government subsidy approval.",
    "Our main customer has delayed their project.",
    "Management wants to evaluate more options.",
    "We need to complete our factory expansion first.",
]

DECLINE_REASONS = [
    "Price was slightly higher than competitor",
    "Lead time didn't fit our project schedule",
    "We decided to postpone the investment",
    "Another supplier offered better local support",
]


# =============================================================================
# APOLLO AGENT
# =============================================================================

@dataclass
class ConversationTurn:
    """A single turn in the conversation."""
    turn_number: int
    stage: str
    customer_email: str
    ira_response: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class SimulationResult:
    """Result of a complete simulation."""
    persona: Dict
    conversation: List[ConversationTurn]
    outcome: str  # "won", "lost", "ongoing"
    total_turns: int
    started_at: str
    ended_at: str


class ApolloSimulator:
    """
    APOLLO - The Sales Simulation Agent
    
    Generates realistic customer conversations to test IRA.
    """
    
    def __init__(self, persona_type: str = "european"):
        self.persona = PERSONAS.get(persona_type, PERSONAS["european"])
        self.conversation: List[ConversationTurn] = []
        self.current_stage = "initial_inquiry"
        self.turn_count = 0
        
        # Stage progression (realistic sales flow)
        self.stage_flow = [
            "initial_inquiry",
            "technical_followup", 
            "technical_followup",
            "commercial_discussion",
            "objection",
            "positive_progress",
            "closing",
        ]
    
    def generate_customer_email(self, stage: str = None, ira_response: str = None) -> str:
        """Generate a customer email for the current stage."""
        if stage is None:
            stage = self.current_stage
        
        templates = STAGE_TEMPLATES.get(stage, STAGE_TEMPLATES["initial_inquiry"])
        template = random.choice(templates)
        
        # Fill in persona details
        email = template.format(
            name=self.persona["name"],
            company=self.persona["company"],
            role=self.persona["role"],
            location=self.persona["location"],
            industry=self.persona["industry"],
            currency=self.persona["currency"],
            budget_range=self.persona["budget_range"],
            current_machine=self.persona.get("current_machine", "None"),
            forming_area=self.persona["forming_area"],
            depth=self.persona["depth"],
            thickness=self.persona["thickness"],
            materials=self.persona["materials"],
            decision_timeline=self.persona["decision_timeline"],
            random_delay_reason=random.choice(DELAY_REASONS),
            decline_reason=random.choice(DECLINE_REASONS),
            machine_model="PF1-X-2015",  # Placeholder
            delivery_timeline="4 months",
        )
        
        return email
    
    async def get_ira_response(self, customer_email: str) -> str:
        """Get IRA's response to the customer email."""
        if not IRA_AVAILABLE:
            return "[IRA response would appear here - IRA not available]"
        
        try:
            # Import IRA's response generator
            from src.agents import research, write, verify
            from src.agents.chief_of_staff.agent import analyze_intent
            
            # Process through IRA's pipeline
            intent = analyze_intent(customer_email)
            research_output = await research(customer_email, {"intent": intent})
            context = {
                "intent": intent,
                "channel": "email",
                "research_output": research_output,
                "customer_name": self.persona["name"],
                "customer_company": self.persona["company"],
            }
            draft = await write(customer_email, context)
            response = await verify(draft, customer_email, context)
            
            return response
            
        except Exception as e:
            return f"[IRA Error: {e}]"
    
    def advance_stage(self):
        """Move to next stage in the sales cycle."""
        self.turn_count += 1
        
        if self.turn_count < len(self.stage_flow):
            self.current_stage = self.stage_flow[self.turn_count]
        else:
            self.current_stage = "closing"
    
    def should_continue(self) -> bool:
        """Determine if simulation should continue."""
        # Random chance to end early (realistic - not all leads convert)
        if self.turn_count >= 3 and random.random() < 0.1:
            return False
        
        # Max turns
        if self.turn_count >= 8:
            return False
        
        return True
    
    async def run_simulation(self, max_turns: int = 6) -> SimulationResult:
        """Run a complete sales simulation."""
        started_at = datetime.now().isoformat()
        
        print(f"\n{'='*70}")
        print(f"APOLLO SALES SIMULATION")
        print(f"{'='*70}")
        print(f"Persona: {self.persona['name']} ({self.persona['company']})")
        print(f"Industry: {self.persona['industry']}")
        print(f"Location: {self.persona['location']}")
        print(f"{'='*70}\n")
        
        while self.turn_count < max_turns and self.should_continue():
            # Generate customer email
            customer_email = self.generate_customer_email()
            
            print(f"\n{'─'*50}")
            print(f"TURN {self.turn_count + 1} - Stage: {self.current_stage}")
            print(f"{'─'*50}")
            print(f"\n📧 CUSTOMER ({self.persona['name']}):\n")
            print(customer_email)
            
            # Get IRA's response
            print(f"\n🤖 IRA's Response:\n")
            ira_response = await self.get_ira_response(customer_email)
            print(ira_response)
            
            # Record turn
            turn = ConversationTurn(
                turn_number=self.turn_count + 1,
                stage=self.current_stage,
                customer_email=customer_email,
                ira_response=ira_response,
            )
            self.conversation.append(turn)
            
            # Advance
            self.advance_stage()
        
        # Determine outcome
        outcome = "ongoing"
        if self.current_stage == "closing":
            outcome = random.choice(["won", "lost"])
        
        ended_at = datetime.now().isoformat()
        
        result = SimulationResult(
            persona=self.persona,
            conversation=self.conversation,
            outcome=outcome,
            total_turns=len(self.conversation),
            started_at=started_at,
            ended_at=ended_at,
        )
        
        # Print summary
        print(f"\n{'='*70}")
        print(f"SIMULATION COMPLETE")
        print(f"{'='*70}")
        print(f"Total turns: {result.total_turns}")
        print(f"Outcome: {result.outcome.upper()}")
        print(f"{'='*70}\n")
        
        return result
    
    def save_simulation(self, result: SimulationResult, output_dir: Path = None):
        """Save simulation results to JSON."""
        if output_dir is None:
            output_dir = PROJECT_ROOT / "data" / "simulations"
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        persona_name = self.persona["name"].replace(" ", "_").lower()
        output_file = output_dir / f"simulation_{persona_name}_{timestamp}.json"
        
        # Convert to serializable format
        data = {
            "persona": result.persona,
            "outcome": result.outcome,
            "total_turns": result.total_turns,
            "started_at": result.started_at,
            "ended_at": result.ended_at,
            "conversation": [
                {
                    "turn": t.turn_number,
                    "stage": t.stage,
                    "customer": t.customer_email,
                    "ira": t.ira_response,
                    "timestamp": t.timestamp,
                }
                for t in result.conversation
            ],
        }
        
        with open(output_file, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"Saved to: {output_file}")
        return output_file


# =============================================================================
# MAIN
# =============================================================================

async def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="APOLLO Sales Simulator")
    parser.add_argument("--persona", type=str, default="european",
                       choices=list(PERSONAS.keys()),
                       help="Customer persona to simulate")
    parser.add_argument("--rounds", type=int, default=5,
                       help="Maximum conversation rounds")
    parser.add_argument("--save", action="store_true",
                       help="Save simulation results")
    
    args = parser.parse_args()
    
    # Create simulator
    apollo = ApolloSimulator(persona_type=args.persona)
    
    # Run simulation
    result = await apollo.run_simulation(max_turns=args.rounds)
    
    # Save if requested
    if args.save:
        apollo.save_simulation(result)


if __name__ == "__main__":
    asyncio.run(main())
