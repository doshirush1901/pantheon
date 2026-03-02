#!/usr/bin/env python3
"""
LIVE LEARNING SALES SIMULATION

A complete sales cycle simulation where:
1. Creative Agent (Rushabh) generates realistic customer emails
2. IRA responds through her full cognitive pipeline  
3. Creative Agent provides FEEDBACK on each response
4. IRA LEARNS from the feedback immediately (stores in Mem0/knowledge)
5. The conversation flows naturally through sales stages

This creates a true learning loop - IRA improves in real-time.

Usage:
    python agents/apollo/live_learning_simulation.py
    python agents/apollo/live_learning_simulation.py --persona dutch_hydroponics
"""

import json
import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "openclaw" / "agents" / "ira"))

# Load environment
from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

import openai

# =============================================================================
# SALES CYCLE KNOWLEDGE
# =============================================================================

SALES_CYCLE_FLOW = """
MACHINECRAFT EUROPEAN SALES CYCLE (from real data)

TYPICAL PATTERNS:
1. FAST-TRACK (2-4 months): first_contact → discovery → technical → quote → close
   - Buyer has clear requirements and budget
   - Example: Batelaan (Belgium) - closed in 3 months
   
2. STANDARD (4-8 months): first_contact → discovery → technical → factory_visit → negotiation → close
   - Factory visit is the key accelerator
   - Example: JoPlast (Poland) - 7 months with factory visit
   
3. LONG-CYCLE (12-24 months): first_contact → nurture → discovery → technical → factory_visit → negotiation → close
   - Budget constraints or complex decision process
   - Example: DutchTides (Netherlands) - 22 months, multiple stakeholders

KEY INSIGHTS:
- Factory visits to reference sites accelerate deals 2-3x
- European buyers value local service support
- Competitor comparisons (vs ILLIG, Kiefel) are common
- Average cycle: 6-12 months
- Fastest deals: Clear requirements + budget authority + factory visit

STAGE BEHAVIORS:
- first_contact: Qualify, understand needs, share intro video
- discovery: Ask about application, materials, volumes, timeline
- technical: Provide specs, case studies, offer technical call
- quote_request: Prepare quote within 24-48h
- factory_visit_offer: Invite to Dutch Tides (Netherlands) or India
- negotiation: Understand position, offer value-adds, payment terms
- objection_handling: Address with facts, references, demonstrations
- closing: Proforma, payment terms, timeline
"""

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
        "personality": "Technical, eco-focused, asks detailed questions",
        "sales_cycle": "long",
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
        "application": "Dashboard components",
        "personality": "Price-conscious, needs quick decisions",
        "sales_cycle": "medium",
    },
    "belgian_manufacturer": {
        "name": "Jean-François Deltenre",
        "company": "Plastiform Belgium",
        "role": "Plant Manager",
        "location": "Belgium", 
        "currency": "EUR",
        "industry": "Industrial Parts",
        "materials": "HDPE, PP",
        "forming_area": "1800 x 1200 mm",
        "application": "Industrial trays",
        "personality": "Conservative, wants local service",
        "sales_cycle": "fast",
    },
}

STAGE_PROGRESSION = {
    "fast": ["first_contact", "discovery", "technical", "quote_request", "closing"],
    "medium": ["first_contact", "discovery", "technical", "factory_visit_offer", "negotiation", "closing"],
    "long": ["first_contact", "discovery", "technical", "factory_visit_offer", "objection_handling", "negotiation", "closing"],
}


# =============================================================================
# CREATIVE AGENT (RUSHABH)
# =============================================================================

class CreativeRushabh:
    """
    The Creative Agent that plays the role of a customer AND provides
    feedback/coaching to IRA on each response.
    """
    
    def __init__(self, persona_key: str = "dutch_hydroponics"):
        self.persona = ENHANCED_PERSONAS.get(persona_key, ENHANCED_PERSONAS["dutch_hydroponics"])
        self.client = openai.OpenAI()
        self.conversation_history: List[Dict] = []
        self.current_stage_idx = 0
        self.stages = STAGE_PROGRESSION[self.persona["sales_cycle"]]
        self.learnings_for_ira: List[str] = []
        
    @property
    def current_stage(self) -> str:
        if self.current_stage_idx < len(self.stages):
            return self.stages[self.current_stage_idx]
        return "closing"
    
    def generate_customer_email(self, ira_last_response: Optional[str] = None) -> Dict:
        """Generate a realistic customer email for the current stage."""
        
        history_text = ""
        if self.conversation_history:
            for turn in self.conversation_history[-3:]:
                history_text += f"\n[{turn['role'].upper()}]: {turn['content'][:200]}...\n"
        
        prompt = f"""You are role-playing as a B2B customer writing to Machinecraft (thermoforming machines).

SALES CYCLE KNOWLEDGE:
{SALES_CYCLE_FLOW}

YOUR PERSONA:
- Name: {self.persona['name']}
- Company: {self.persona['company']}
- Role: {self.persona['role']}
- Location: {self.persona['location']}
- Industry: {self.persona['industry']}
- Application: {self.persona['application']}
- Materials: {self.persona['materials']}
- Forming Area: {self.persona['forming_area']}
- Personality: {self.persona['personality']}

CURRENT STAGE: {self.current_stage}
TURN: {self.current_stage_idx + 1}

CONVERSATION SO FAR:
{history_text}

{"IRA'S LAST RESPONSE:" + chr(10) + ira_last_response[:500] if ira_last_response else "This is the first email in the thread."}

Generate a realistic customer email that:
1. Fits the {self.current_stage} stage naturally
2. Responds appropriately to IRA's last message (if any)
3. Shows your persona's personality
4. Asks relevant questions for this stage
5. Moves the sales cycle forward realistically

Output JSON:
{{
    "subject": "Email subject",
    "body": "Full email body",
    "questions_asked": ["List of questions"],
    "buying_signals": ["Any positive signals"],
    "concerns": ["Any concerns/objections"]
}}"""
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are an expert at role-playing B2B customers. Write authentic, professional emails."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.8,
            )
            
            result = json.loads(response.choices[0].message.content)
            
            # Record in history
            self.conversation_history.append({
                "role": "customer",
                "content": result.get("body", ""),
                "stage": self.current_stage,
            })
            
            return result
            
        except Exception as e:
            print(f"Error generating email: {e}")
            return {
                "subject": f"Inquiry from {self.persona['company']}",
                "body": f"We are looking for a thermoforming machine for {self.persona['application']}.",
                "questions_asked": ["What machines do you recommend?"],
                "buying_signals": [],
                "concerns": [],
            }
    
    def evaluate_and_coach(self, ira_response: str, customer_email: Dict) -> Dict:
        """
        Evaluate IRA's response and provide coaching feedback.
        This is where Rushabh teaches IRA how to improve.
        """
        
        prompt = f"""You are Rushabh, the sales expert at Machinecraft. You're evaluating IRA's response
and providing coaching feedback so she can learn and improve.

SALES CYCLE KNOWLEDGE:
{SALES_CYCLE_FLOW}

CURRENT STAGE: {self.current_stage}
CUSTOMER: {self.persona['name']} ({self.persona['company']})

CUSTOMER'S EMAIL:
{customer_email.get('body', '')}

Questions asked: {customer_email.get('questions_asked', [])}
Concerns raised: {customer_email.get('concerns', [])}
Buying signals: {customer_email.get('buying_signals', [])}

IRA'S RESPONSE:
{ira_response}

Evaluate IRA's response and provide coaching:

1. SCORE (1-10): How well did IRA handle this?
2. WHAT IRA DID WELL: Specific things to reinforce
3. WHAT IRA SHOULD IMPROVE: Specific actionable feedback
4. LEARNING FOR IRA: A concise lesson IRA should remember for future similar situations
5. NEXT STAGE READINESS: Is the customer ready to move forward? (yes/maybe/no)

Be specific and actionable. This feedback will be stored in IRA's memory.

Output JSON:
{{
    "score": 8,
    "what_ira_did_well": ["List of positives"],
    "improvements_needed": ["List of specific improvements"],
    "learning_for_ira": "A concise lesson IRA should remember (2-3 sentences max)",
    "stage_progress": "yes/maybe/no",
    "rushabh_would_add": "What Rushabh would add to this response (optional enhancement)"
}}"""
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are Rushabh, a sales expert coaching your AI assistant IRA."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.3,  # More consistent evaluation
            )
            
            result = json.loads(response.choices[0].message.content)
            
            # Store learning
            if result.get("learning_for_ira"):
                self.learnings_for_ira.append({
                    "stage": self.current_stage,
                    "learning": result["learning_for_ira"],
                    "context": f"{self.persona['industry']} customer",
                })
            
            return result
            
        except Exception as e:
            print(f"Error evaluating: {e}")
            return {"score": 5, "learning_for_ira": "Continue improving responses."}
    
    def advance_stage(self, evaluation: Dict):
        """Move to next stage based on evaluation."""
        if evaluation.get("stage_progress") == "yes":
            self.current_stage_idx += 1
        elif evaluation.get("stage_progress") == "maybe" and self.current_stage_idx > 2:
            # Sometimes advance on "maybe" in later stages
            import random
            if random.random() > 0.5:
                self.current_stage_idx += 1
    
    def record_ira_response(self, response: str):
        """Record IRA's response in history."""
        self.conversation_history.append({
            "role": "ira", 
            "content": response,
            "stage": self.current_stage,
        })
    
    def is_complete(self) -> bool:
        """Check if simulation is complete."""
        return self.current_stage_idx >= len(self.stages)


# =============================================================================
# IRA LEARNING INTEGRATION
# =============================================================================

class IraLearner:
    """Handles storing learnings from the simulation into IRA's memory."""
    
    def __init__(self):
        self.learnings: List[Dict] = []
        
        # Try to import Mem0 for persistent learning
        try:
            from src.memory.unified_mem0 import get_mem0_service
            self.mem0 = get_mem0_service()
            self.mem0_available = True
        except ImportError:
            self.mem0 = None
            self.mem0_available = False
            print("Note: Mem0 not available, learnings will be saved to file only")
    
    def learn(self, stage: str, learning: str, context: str):
        """Store a learning from the simulation."""
        learning_item = {
            "timestamp": datetime.now().isoformat(),
            "stage": stage,
            "learning": learning,
            "context": context,
            "source": "apollo_simulation",
        }
        self.learnings.append(learning_item)
        
        # Store in Mem0 if available
        if self.mem0_available and self.mem0:
            try:
                self.mem0.add_memory(
                    content=f"SALES LEARNING ({stage}): {learning}",
                    user_id="ira_training",
                    metadata={"stage": stage, "context": context, "source": "apollo"}
                )
                print(f"   💾 Stored in Mem0: {learning[:50]}...")
            except Exception as e:
                print(f"   ⚠️ Mem0 storage failed: {e}")
    
    def save_learnings(self, output_path: Path = None):
        """Save all learnings to file."""
        if output_path is None:
            output_path = PROJECT_ROOT / "data" / "training" / "simulation_learnings.json"
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        existing = []
        if output_path.exists():
            with open(output_path) as f:
                existing = json.load(f)
        
        # Append new learnings
        all_learnings = existing + self.learnings
        
        with open(output_path, 'w') as f:
            json.dump(all_learnings, f, indent=2)
        
        print(f"\n📚 Saved {len(self.learnings)} new learnings to {output_path}")
        return output_path


# =============================================================================
# LIVE SIMULATION
# =============================================================================

async def run_live_learning_simulation(
    persona_key: str = "dutch_hydroponics",
    max_turns: int = 8,
):
    """
    Run a complete sales simulation with live learning.
    """
    
    # Import IRA components
    try:
        from src.agents import research, write, verify
        from src.agents.chief_of_staff.agent import analyze_intent
        IRA_AVAILABLE = True
    except ImportError as e:
        print(f"Warning: IRA not fully available: {e}")
        IRA_AVAILABLE = False
    
    # Initialize
    creative_rushabh = CreativeRushabh(persona_key)
    ira_learner = IraLearner()
    
    print(f"""
╔══════════════════════════════════════════════════════════════════════╗
║            🎭 LIVE LEARNING SALES SIMULATION                         ║
╠══════════════════════════════════════════════════════════════════════╣
║  Customer: {creative_rushabh.persona['name']:<54} ║
║  Company:  {creative_rushabh.persona['company']:<54} ║
║  Industry: {creative_rushabh.persona['industry']:<54} ║
║  Sales Cycle: {creative_rushabh.persona['sales_cycle'].upper():<51} ║
╠══════════════════════════════════════════════════════════════════════╣
║  Sales Stages: {' → '.join(creative_rushabh.stages):<50} ║
╚══════════════════════════════════════════════════════════════════════╝
""")
    
    simulation_log = {
        "persona": creative_rushabh.persona,
        "started_at": datetime.now().isoformat(),
        "turns": [],
    }
    
    ira_last_response = None
    turn = 0
    
    while not creative_rushabh.is_complete() and turn < max_turns:
        turn += 1
        
        print(f"\n{'═'*70}")
        print(f"  TURN {turn} | Stage: {creative_rushabh.current_stage.upper()}")
        print(f"{'═'*70}")
        
        # 1. Creative Agent generates customer email
        print(f"\n📧 CUSTOMER ({creative_rushabh.persona['name']}):")
        print(f"─"*50)
        
        customer_email = creative_rushabh.generate_customer_email(ira_last_response)
        print(f"Subject: {customer_email.get('subject', 'No subject')}")
        print(f"\n{customer_email.get('body', '')}")
        
        if customer_email.get('questions_asked'):
            print(f"\n❓ Questions: {', '.join(customer_email['questions_asked'][:3])}")
        
        # 2. IRA responds
        print(f"\n🤖 IRA's Response:")
        print(f"─"*50)
        
        if IRA_AVAILABLE:
            try:
                intent = analyze_intent(customer_email.get('body', ''))
                research_output = await research(
                    customer_email.get('body', ''),
                    {
                        "intent": intent,
                        "customer_name": creative_rushabh.persona["name"],
                        "company": creative_rushabh.persona["company"],
                    }
                )
                context = {
                    "intent": intent,
                    "channel": "email",
                    "research_output": research_output,
                    "customer_name": creative_rushabh.persona["name"],
                }
                draft = await write(customer_email.get('body', ''), context)
                ira_response = await verify(draft, customer_email.get('body', ''), context)
            except Exception as e:
                ira_response = f"Thank you for your inquiry. I'd be happy to help you find the right thermoforming solution for {creative_rushabh.persona['application']}. [Error: {e}]"
        else:
            ira_response = f"""Dear {creative_rushabh.persona['name']},

Thank you for contacting Machinecraft about thermoforming solutions for {creative_rushabh.persona['application']}.

Based on your requirements ({creative_rushabh.persona['forming_area']} forming area, {creative_rushabh.persona['materials']} materials), I'd recommend our PF1-X series.

Would you like me to send detailed specifications and pricing?

Best regards,
IRA
Machinecraft Technologies"""
        
        print(ira_response)
        
        # Record IRA's response
        creative_rushabh.record_ira_response(ira_response)
        ira_last_response = ira_response
        
        # 3. Creative Agent (Rushabh) evaluates and coaches
        print(f"\n📊 RUSHABH'S COACHING:")
        print(f"─"*50)
        
        evaluation = creative_rushabh.evaluate_and_coach(ira_response, customer_email)
        
        score = evaluation.get('score', 5)
        score_bar = '█' * score + '░' * (10 - score)
        print(f"Score: [{score_bar}] {score}/10")
        
        if evaluation.get('what_ira_did_well'):
            print(f"\n✅ What IRA did well:")
            for item in evaluation['what_ira_did_well'][:2]:
                print(f"   • {item}")
        
        if evaluation.get('improvements_needed'):
            print(f"\n🔧 Improvements needed:")
            for item in evaluation['improvements_needed'][:2]:
                print(f"   • {item}")
        
        learning = evaluation.get('learning_for_ira', '')
        if learning:
            print(f"\n💡 LEARNING FOR IRA:")
            print(f"   \"{learning}\"")
            
            # Store the learning
            ira_learner.learn(
                stage=creative_rushabh.current_stage,
                learning=learning,
                context=f"{creative_rushabh.persona['industry']} customer from {creative_rushabh.persona['location']}"
            )
        
        if evaluation.get('rushabh_would_add'):
            print(f"\n💬 Rushabh would add:")
            print(f"   \"{evaluation['rushabh_would_add'][:200]}...\"")
        
        # Log turn
        simulation_log["turns"].append({
            "turn": turn,
            "stage": creative_rushabh.current_stage,
            "customer_email": customer_email,
            "ira_response": ira_response,
            "evaluation": evaluation,
        })
        
        # 4. Advance stage
        creative_rushabh.advance_stage(evaluation)
        
        print(f"\n   → Stage progress: {evaluation.get('stage_progress', 'unknown').upper()}")
        
        # Small delay for readability
        await asyncio.sleep(0.5)
    
    # Simulation complete
    outcome = "won" if creative_rushabh.current_stage == "closing" else "ongoing"
    
    print(f"""
╔══════════════════════════════════════════════════════════════════════╗
║                    🏁 SIMULATION COMPLETE                            ║
╠══════════════════════════════════════════════════════════════════════╣
║  Total Turns: {turn:<55} ║
║  Final Stage: {creative_rushabh.current_stage.upper():<55} ║
║  Outcome: {outcome.upper():<59} ║
║  Learnings Generated: {len(ira_learner.learnings):<47} ║
╚══════════════════════════════════════════════════════════════════════╝
""")
    
    # Save everything
    simulation_log["ended_at"] = datetime.now().isoformat()
    simulation_log["outcome"] = outcome
    simulation_log["total_turns"] = turn
    simulation_log["learnings"] = ira_learner.learnings
    
    # Save simulation log
    output_dir = PROJECT_ROOT / "data" / "simulations"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"live_learning_{persona_key}_{timestamp}.json"
    
    with open(output_file, 'w') as f:
        json.dump(simulation_log, f, indent=2)
    
    print(f"📁 Simulation saved to: {output_file}")
    
    # Save learnings
    ira_learner.save_learnings()
    
    # Print summary of learnings
    print(f"\n📚 LEARNINGS SUMMARY:")
    print(f"─"*50)
    for i, learning in enumerate(ira_learner.learnings, 1):
        print(f"{i}. [{learning['stage']}] {learning['learning']}")
    
    return simulation_log


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Live Learning Sales Simulation")
    parser.add_argument("--persona", type=str, default="dutch_hydroponics",
                       choices=list(ENHANCED_PERSONAS.keys()),
                       help="Customer persona")
    parser.add_argument("--turns", type=int, default=8, help="Max turns")
    
    args = parser.parse_args()
    
    asyncio.run(run_live_learning_simulation(
        persona_key=args.persona,
        max_turns=args.turns,
    ))
