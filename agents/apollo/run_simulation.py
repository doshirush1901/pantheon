#!/usr/bin/env python3
"""
APOLLO Interactive Sales Simulation
====================================

Run a live conversation simulation between a customer (APOLLO) and IRA.

Usage:
    python agents/apollo/run_simulation.py
"""

import os
import sys
import json
import random
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Load environment
from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

# OpenAI for creative generation
import openai

client = openai.OpenAI()

# =============================================================================
# PERSONAS
# =============================================================================

PERSONAS = {
    "european": {
        "name": "Jean-François Deltenre",
        "company": "Plastiform Belgium NV",
        "email": "jf.deltenre@plastiform.be",
        "role": "Technical Director",
        "industry": "Automotive Interior (dashboard covers, door panels)",
        "location": "Belgium",
        "currency": "EUR",
        "budget": "200,000",
        "current_machine": "ILLIG UA 100g (15 years old, high maintenance)",
        "requirements": {
            "forming_area": "2000 x 1500 mm",
            "depth": "650 mm", 
            "thickness": "up to 8mm",
            "materials": "ABS, TPO, PP",
        },
        "personality": "Technical, detail-oriented, compares to competitors",
        "pain_points": "High energy costs, slow cycles, frequent breakdowns",
    },
    "indian_auto": {
        "name": "Rajesh Sharma",
        "company": "AutoPlast Components Pvt Ltd",
        "email": "rajesh.sharma@autoplast.co.in",  
        "role": "VP Operations",
        "industry": "Tier-1 Automotive Supplier",
        "location": "Pune, India",
        "currency": "INR",
        "budget": "1 Crore",
        "current_machine": "None (new project)",
        "requirements": {
            "forming_area": "1500 x 1200 mm",
            "depth": "500 mm",
            "thickness": "up to 6mm",
            "materials": "ABS+PMMA, TPO",
        },
        "personality": "Price-focused, needs OEM approval, decision-maker",
        "pain_points": "Tight deadline, cost pressure from OEM",
    },
    "startup": {
        "name": "Mike Chen",
        "company": "PackForm Solutions",
        "email": "mike@packform.io",
        "role": "Founder",
        "industry": "Sustainable Packaging Startup",
        "location": "Toronto, Canada",
        "currency": "USD",
        "budget": "60,000",
        "current_machine": "None (first machine)",
        "requirements": {
            "forming_area": "600 x 900 mm",
            "depth": "300 mm",
            "thickness": "up to 3mm",
            "materials": "PETG, rPET",
        },
        "personality": "Enthusiastic, budget-conscious, needs guidance",
        "pain_points": "Limited capital, no thermoforming experience",
    },
    "us_distributor": {
        "name": "Josh Szabo",
        "company": "Plastics Machinery Group LLC",
        "email": "joshs@plasticsmg.com",
        "role": "Sales Manager",
        "industry": "Machinery Distribution (US & Canada)",
        "location": "Cleveland, Ohio, USA",
        "currency": "USD",
        "budget": "150,000 (demo unit)",
        "current_machine": "Representing multiple brands",
        "requirements": {
            "forming_area": "Various (customer dependent)",
            "depth": "Various",
            "thickness": "up to 12mm",
            "materials": "All standard materials",
        },
        "personality": "Business-focused, wants margins and exclusivity, NPE show focus",
        "pain_points": "Need competitive dealer pricing, demo machine for showroom, strong after-sales support",
    },
    "large_project": {
        "name": "Dr. Ahmed Al-Rashid",
        "company": "Gulf Industrial Solutions",
        "email": "ahmed.rashid@gulfind.ae",
        "role": "Procurement Director",
        "industry": "Industrial Manufacturing (turnkey facility)",
        "location": "Dubai, UAE",
        "currency": "USD",
        "budget": "750,000",
        "current_machine": "New facility - need 3-4 machines",
        "requirements": {
            "forming_area": "3000 x 2000 mm",
            "depth": "800 mm",
            "thickness": "up to 15mm",
            "materials": "HDPE, ABS, Acrylic, PMMA",
        },
        "personality": "Formal, process-driven, needs compliance docs and references",
        "pain_points": "Tender process, local service support required, payment terms (LC)",
    },
    "tough_negotiator": {
        "name": "Viktor Petrov",
        "company": "EuroPack Industries",
        "email": "v.petrov@europack.pl",
        "role": "CEO",
        "industry": "Food Packaging (trays, containers)",
        "location": "Warsaw, Poland",
        "currency": "EUR",
        "budget": "180,000",
        "current_machine": "Kiefel KMD 78 (competitor machine)",
        "requirements": {
            "forming_area": "1800 x 1200 mm",
            "depth": "400 mm",
            "thickness": "up to 2mm",
            "materials": "PP, PS, PET",
        },
        "personality": "Aggressive negotiator, price-focused, will compare to competitors, threatens to walk away",
        "pain_points": "Kiefel quoted 15% less, concerned about Indian machine quality, wants extended warranty",
    },
}

# =============================================================================
# APOLLO - CREATIVE CUSTOMER AGENT
# =============================================================================

APOLLO_SYSTEM_PROMPT = """You are APOLLO, a sales simulation agent for Machinecraft Technologies.

Your job is to ROLEPLAY as a customer named {name} from {company} in {location}.

CUSTOMER PROFILE:
- Name: {name}
- Company: {company}
- Role: {role}
- Industry: {industry}
- Current situation: {current_machine}
- Budget: {currency} {budget}
- Requirements: {requirements}
- Personality: {personality}
- Pain points: {pain_points}

SIMULATION RULES:
1. Stay in character as this customer - NEVER break character
2. Write realistic emails a real customer would write
3. Progress naturally through the sales cycle:
   - Start with initial inquiry
   - Ask technical questions based on IRA's responses
   - Discuss pricing and terms
   - Raise realistic objections
   - Eventually move toward a decision (buy or not buy)
4. Be realistic - not every deal closes
5. Reference specific Machinecraft machines when IRA mentions them
6. Ask follow-up questions based on what IRA says

CURRENT STAGE: {stage}
TURN NUMBER: {turn}

Based on the conversation so far, write your next email to IRA.

Guidelines for each stage:
- turns 1-2: Ask about machines, specs, pricing
- turns 3-4: Deep technical questions, compare to competitors
- turns 5-6: Negotiate price/terms, raise objections
- turns 7+: Move toward closing (positive or negative)

Write ONLY the email content. No explanations or meta-commentary."""


def generate_customer_email(persona: dict, conversation: list, turn: int) -> str:
    """Use GPT to generate a realistic customer email."""
    
    # Determine stage
    if turn <= 2:
        stage = "initial_inquiry"
    elif turn <= 4:
        stage = "technical_discussion"
    elif turn <= 6:
        stage = "commercial_negotiation"
    else:
        stage = "closing"
    
    # Build conversation context
    conv_context = ""
    for entry in conversation:
        conv_context += f"\n---\nCustomer ({persona['name']}):\n{entry['customer']}\n"
        conv_context += f"\nIRA (Machinecraft):\n{entry['ira']}\n"
    
    # Generate with GPT
    system_prompt = APOLLO_SYSTEM_PROMPT.format(
        name=persona["name"],
        company=persona["company"],
        role=persona["role"],
        industry=persona["industry"],
        location=persona["location"],
        currency=persona["currency"],
        budget=persona["budget"],
        current_machine=persona["current_machine"],
        requirements=json.dumps(persona["requirements"], indent=2),
        personality=persona["personality"],
        pain_points=persona["pain_points"],
        stage=stage,
        turn=turn,
    )
    
    user_prompt = f"""Conversation so far:
{conv_context if conv_context else "(This is the first email - start with initial inquiry)"}

Write your next email as {persona['name']}. Be realistic and stay in character."""
    
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.8,
        max_tokens=500,
    )
    
    return response.choices[0].message.content


# =============================================================================
# IRA INTEGRATION
# =============================================================================

def get_ira_response(customer_email: str, persona: dict, use_real_ira: bool = True) -> str:
    """Get IRA's response using the unified pipeline."""
    if not use_real_ira:
        return simulate_ira_response(customer_email, persona)
    
    try:
        # Try importing IRA's pipeline
        sys.path.insert(0, str(PROJECT_ROOT / "openclaw" / "agents" / "ira"))
        
        from src.brain.generate_answer import generate_answer
        
        # Build context as ContextPack dict
        context = {
            "conversation_history": [],
            "rag_chunks": [],
            "user_info": {
                "name": persona["name"],
                "email": persona["email"],
                "company": persona["company"],
            },
            "metadata": {
                "mode": "training",
                "simulation": True,
            },
        }
        
        # Get IRA's response
        result = generate_answer(
            intent=customer_email,
            context_pack=context,
            channel="email",
        )
        
        # Extract text from ResponseObject
        if hasattr(result, 'final_text'):
            return result.final_text
        elif hasattr(result, 'text'):
            return result.text
        elif isinstance(result, dict):
            return result.get('final_text') or result.get('text') or str(result)
        else:
            return str(result)
        
    except Exception as e:
        # Fallback: Use GPT to simulate IRA's style
        print(f"[Note: Using simulated IRA - {type(e).__name__}: {e}]")
        return simulate_ira_response(customer_email, persona)


def simulate_ira_response(customer_email: str, persona: dict) -> str:
    """Simulate IRA's response using GPT (fallback)."""
    
    ira_prompt = """You are IRA, the AI sales assistant for Machinecraft Technologies.
    
Machinecraft makes thermoforming machines since 1976. Key products:
- AM series: Automatic roll-fed, ≤1.5mm thickness
- PF series: Sheet-fed pressure forming, heavy gauge (up to 15mm)
- BF series: Blister forming
- SP series: Skin packing

STYLE (Based on ATHENA training):
- Start with "Hi!" - warm greeting
- Be concise (100-150 words)
- Use action language: "Let me...", "I'll..."
- End with short CTA: "Let me know.", "Questions?"

PRICING GUIDELINES:
- AM machines: EUR 80,000-150,000
- PF machines: EUR 120,000-300,000
- Always add "subject to configuration"

Lead time: 3-5 months

Respond to this customer inquiry:"""
    
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": ira_prompt},
            {"role": "user", "content": customer_email},
        ],
        temperature=0.7,
        max_tokens=400,
    )
    
    return response.choices[0].message.content


# =============================================================================
# MAIN SIMULATION
# =============================================================================

def run_simulation(persona_type: str = "european", max_turns: int = 6, interactive: bool = True, use_real_ira: bool = True):
    """Run sales simulation."""
    
    persona = PERSONAS.get(persona_type, PERSONAS["european"])
    conversation = []
    
    print("\n" + "="*70)
    print("🎭 APOLLO SALES SIMULATION")
    print("="*70)
    print(f"\n📋 Customer Profile:")
    print(f"   Name: {persona['name']}")
    print(f"   Company: {persona['company']}")
    print(f"   Industry: {persona['industry']}")
    print(f"   Location: {persona['location']}")
    print(f"   Budget: {persona['currency']} {persona['budget']}")
    print(f"   Requirements: {persona['requirements']}")
    print("="*70)
    
    for turn in range(1, max_turns + 1):
        print(f"\n{'─'*70}")
        print(f"📧 TURN {turn}")
        print(f"{'─'*70}")
        
        # Generate customer email
        print(f"\n👤 {persona['name']} ({persona['company']}):\n")
        customer_email = generate_customer_email(persona, conversation, turn)
        print(customer_email)
        
        # Get IRA's response
        print(f"\n🤖 IRA (Machinecraft):\n")
        ira_response = get_ira_response(customer_email, persona, use_real_ira=use_real_ira)
        print(ira_response)
        
        # Store conversation
        conversation.append({
            "turn": turn,
            "customer": customer_email,
            "ira": ira_response,
            "timestamp": datetime.now().isoformat(),
        })
        
        # Optional: Interactive mode
        if interactive and turn < max_turns:
            try:
                user_input = input("\n[Press Enter to continue, 'q' to quit, 's' to save] ").strip().lower()
                if user_input == 'q':
                    break
                elif user_input == 's':
                    save_simulation(persona, conversation)
            except EOFError:
                pass  # Non-interactive mode
    
    # Final save
    print("\n" + "="*70)
    print("✅ SIMULATION COMPLETE")
    print(f"   Total turns: {len(conversation)}")
    print("="*70)
    
    save_simulation(persona, conversation)
    
    return conversation


def save_simulation(persona: dict, conversation: list):
    """Save simulation to file."""
    output_dir = PROJECT_ROOT / "data" / "simulations"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    persona_name = persona["name"].replace(" ", "_").lower()
    output_file = output_dir / f"sim_{persona_name}_{timestamp}.json"
    
    data = {
        "persona": persona,
        "turns": len(conversation),
        "conversation": conversation,
        "generated_at": datetime.now().isoformat(),
    }
    
    with open(output_file, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"💾 Saved to: {output_file}")


# =============================================================================
# CLI
# =============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="APOLLO Sales Simulation")
    parser.add_argument("--persona", "-p", type=str, default="european",
                       choices=list(PERSONAS.keys()),
                       help="Customer persona to simulate")
    parser.add_argument("--turns", "-t", type=int, default=6,
                       help="Number of conversation turns")
    parser.add_argument("--auto", "-a", action="store_true",
                       help="Auto mode (non-interactive)")
    parser.add_argument("--simulate-ira", action="store_true",
                       help="Use GPT to simulate IRA (instead of real IRA)")
    parser.add_argument("--list", "-l", action="store_true",
                       help="List available personas")
    
    args = parser.parse_args()
    
    if args.list:
        print("\n📋 Available Personas:\n")
        for key, p in PERSONAS.items():
            print(f"  {key}:")
            print(f"    {p['name']} - {p['company']}")
            print(f"    {p['industry']}, {p['location']}")
            print()
    else:
        run_simulation(
            persona_type=args.persona, 
            max_turns=args.turns,
            interactive=not args.auto,
            use_real_ira=not args.simulate_ira,
        )
