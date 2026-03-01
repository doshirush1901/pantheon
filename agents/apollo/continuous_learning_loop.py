#!/usr/bin/env python3
"""
IRA CONTINUOUS LEARNING LOOP
=============================

Automated training system that:
1. Mines past customer interactions for realistic scenarios
2. Simulates email conversations (Creative Agent as customer, Ira responds)
3. Rates each conversation on multiple dimensions
4. Has a Coach Agent analyze and generate improvement lessons
5. Stores learnings so Ira and sub-agents get smarter

The Learning Loop:
    Past Interactions → Stress Tests → Simulations → Ratings → 
    Coach Feedback → Lessons Learned → Sub-Agent Upgrades → 
    Better Performance → New Interactions → Repeat

Usage:
    python continuous_learning_loop.py --sessions 5
    python continuous_learning_loop.py --scenario "price_negotiation"
    python continuous_learning_loop.py --auto  # Continuous background learning
"""

import os
import sys
import json
import random
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum

# Setup paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "openclaw/agents/ira/src/brain"))
sys.path.insert(0, str(PROJECT_ROOT / "agents/apollo"))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

import openai
client = openai.OpenAI()

# Import Ira's brain
try:
    from generate_answer import generate_answer, ResponseObject
    IRA_AVAILABLE = True
except ImportError:
    IRA_AVAILABLE = False
    print("Warning: Ira's brain not available")

try:
    from learning_engine import LearningEngine
    LEARNING_ENGINE_AVAILABLE = True
except ImportError:
    LEARNING_ENGINE_AVAILABLE = False


# =============================================================================
# DATA STRUCTURES
# =============================================================================

class ScenarioType(Enum):
    VAGUE_INQUIRY = "vague_inquiry"
    PRICE_NEGOTIATION = "price_negotiation"
    TECHNICAL_DEEP_DIVE = "technical_deep_dive"
    COMPETITOR_COMPARISON = "competitor_comparison"
    URGENT_REQUEST = "urgent_request"
    COMPLAINT_HANDLING = "complaint_handling"
    FOLLOW_UP = "follow_up"
    CLOSING_DEAL = "closing_deal"


@dataclass
class CustomerPersona:
    """A simulated customer personality."""
    name: str
    company: str
    role: str
    style: str  # assertive, friendly, technical, confused, demanding
    patience_level: int  # 1-5, how many exchanges before they get frustrated
    budget_sensitivity: str  # low, medium, high
    technical_knowledge: str  # novice, intermediate, expert
    hidden_requirements: List[str] = field(default_factory=list)


@dataclass
class ConversationTurn:
    """A single turn in the conversation."""
    role: str  # "customer" or "ira"
    message: str
    timestamp: str = ""
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


@dataclass
class SimulatedConversation:
    """A complete simulated conversation."""
    id: str
    scenario_type: ScenarioType
    persona: CustomerPersona
    turns: List[ConversationTurn] = field(default_factory=list)
    outcome: str = ""  # "success", "lost", "escalated", "ongoing"
    rating: Optional['ConversationRating'] = None
    lessons: List[Dict] = field(default_factory=list)


@dataclass
class ConversationRating:
    """Rating for a conversation."""
    overall_score: float  # 0-10
    qualification_quality: float  # Did Ira ask the right questions?
    technical_accuracy: float  # Were specs/prices correct?
    personality_warmth: float  # Did Ira sound human and warm?
    business_rule_compliance: float  # Did Ira follow rules (AM thickness, etc)?
    customer_satisfaction_proxy: float  # Would customer be happy?
    closing_effectiveness: float  # Did Ira move toward sale?
    specific_issues: List[str] = field(default_factory=list)
    specific_wins: List[str] = field(default_factory=list)


# =============================================================================
# PAST INTERACTION MINER
# =============================================================================

# Real scenarios extracted from typical customer interactions
REAL_SCENARIO_TEMPLATES = [
    {
        "type": ScenarioType.VAGUE_INQUIRY,
        "initial_message": "We need a thermoforming machine for our factory. Please send details.",
        "persona_style": "confused",
        "hidden_need": "Actually needs 1200x800mm for automotive parts",
        "expected_outcome": "Ira asks qualifying questions, customer reveals specs",
    },
    {
        "type": ScenarioType.PRICE_NEGOTIATION,
        "initial_message": "Your quote of ₹62 lakhs is too high. Our budget is 45 lakhs max.",
        "persona_style": "assertive",
        "context": "Customer received quote for PF1-C-2015",
        "expected_outcome": "Ira explains value or offers alternatives",
    },
    {
        "type": ScenarioType.TECHNICAL_DEEP_DIVE,
        "initial_message": "What's the temperature uniformity across the heating zone? We need ±2°C for medical applications.",
        "persona_style": "technical",
        "hidden_need": "Medical device housings, FDA compliance",
        "expected_outcome": "Ira provides technical specs, asks about certification needs",
    },
    {
        "type": ScenarioType.COMPETITOR_COMPARISON,
        "initial_message": "GEISS quoted €150,000 for similar specs. Why should we choose Machinecraft?",
        "persona_style": "assertive",
        "specs": "2000x1500mm, 8mm ABS, automotive",
        "expected_outcome": "Ira highlights value without badmouthing",
    },
    {
        "type": ScenarioType.URGENT_REQUEST,
        "initial_message": "URGENT - Our machine broke! We have orders due in 4 weeks. Can you help?",
        "persona_style": "demanding",
        "hidden_need": "1500x1000mm, 6mm PMMA, signage",
        "expected_outcome": "Ira shows empathy, explains realistic timelines, offers solutions",
    },
    {
        "type": ScenarioType.COMPLAINT_HANDLING,
        "initial_message": "The machine we bought last year keeps having heating issues. This is unacceptable!",
        "persona_style": "angry",
        "context": "Bought PF1-C-1510 in 2025",
        "expected_outcome": "Ira acknowledges, asks for details, offers support",
    },
    {
        "type": ScenarioType.FOLLOW_UP,
        "initial_message": "Following up on our discussion last month. We're ready to move forward but have a few more questions.",
        "persona_style": "friendly",
        "context": "Discussed PF1-C-2015 for sanitary ware",
        "expected_outcome": "Ira recalls context, answers questions, pushes toward close",
    },
    {
        "type": ScenarioType.CLOSING_DEAL,
        "initial_message": "OK, we've decided to go with the PF1-C-2015. What's next?",
        "persona_style": "decisive",
        "context": "Multiple previous emails about specs",
        "expected_outcome": "Ira handles order process smoothly",
    },
]


def generate_customer_persona(scenario_type: ScenarioType) -> CustomerPersona:
    """Generate a realistic customer persona for the scenario."""
    
    names = [
        ("Vikram Sharma", "Sharma Industries", "Managing Director"),
        ("Priya Venkatesh", "VenTech Plastics", "CEO"),
        ("Chen Wei", "Suzhou Precision", "Technical Director"),
        ("Aleksandr Petrov", "Petrov Plastik", "Chief Engineer"),
        ("Rajesh Patel", "Patel Polymers", "Owner"),
        ("Sarah Johnson", "US Thermoform Inc", "VP Operations"),
        ("Hans Mueller", "Mueller GmbH", "Production Manager"),
        ("Deepak Agarwal", "Agarwal Enterprises", "Director"),
    ]
    
    name, company, role = random.choice(names)
    
    style_map = {
        ScenarioType.VAGUE_INQUIRY: "confused",
        ScenarioType.PRICE_NEGOTIATION: "assertive",
        ScenarioType.TECHNICAL_DEEP_DIVE: "technical",
        ScenarioType.COMPETITOR_COMPARISON: "assertive",
        ScenarioType.URGENT_REQUEST: "demanding",
        ScenarioType.COMPLAINT_HANDLING: "angry",
        ScenarioType.FOLLOW_UP: "friendly",
        ScenarioType.CLOSING_DEAL: "decisive",
    }
    
    return CustomerPersona(
        name=name,
        company=company,
        role=role,
        style=style_map.get(scenario_type, "friendly"),
        patience_level=random.randint(3, 6),
        budget_sensitivity=random.choice(["low", "medium", "high"]),
        technical_knowledge=random.choice(["novice", "intermediate", "expert"]),
    )


# =============================================================================
# CREATIVE CUSTOMER AGENT
# =============================================================================

CUSTOMER_AGENT_PROMPT = """You are simulating a customer named {name} from {company}.
You are a {role} with a {style} communication style.

YOUR PERSONA:
- Technical knowledge: {technical_knowledge}
- Budget sensitivity: {budget_sensitivity}
- Patience level: {patience_level}/5

SCENARIO: {scenario_type}
{scenario_context}

YOUR GOAL:
Engage in a realistic email conversation with Ira (the sales AI).
- If {style} is "confused": Ask unclear questions, reveal info gradually
- If {style} is "assertive": Push back on price, ask tough questions
- If {style} is "technical": Ask detailed spec questions
- If {style} is "demanding": Express urgency, expect fast responses
- If {style} is "angry": Express frustration but remain professional
- If {style} is "friendly": Be warm but still have requirements
- If {style} is "decisive": Be ready to close the deal

HIDDEN REQUIREMENTS (reveal gradually):
{hidden_requirements}

PREVIOUS CONVERSATION:
{conversation_history}

IRA'S LAST MESSAGE:
{last_ira_message}

Generate your next email response as {name}. Be realistic - don't reveal everything at once.
If Ira asks good questions, reward with more information.
If Ira doesn't ask the right questions, be vague.
If the conversation reaches a natural conclusion (you're satisfied or frustrated), say so.

Write ONLY your email response, in character as {name}."""


def generate_customer_response(
    persona: CustomerPersona,
    scenario: Dict,
    conversation: List[ConversationTurn],
    last_ira_message: str,
) -> Tuple[str, bool]:
    """
    Generate a customer response using LLM.
    Returns (response_text, should_continue)
    """
    
    # Build conversation history
    history = "\n".join([
        f"{'CUSTOMER' if t.role == 'customer' else 'IRA'}: {t.message[:300]}..."
        for t in conversation[-6:]  # Last 6 turns
    ])
    
    prompt = CUSTOMER_AGENT_PROMPT.format(
        name=persona.name,
        company=persona.company,
        role=persona.role,
        style=persona.style,
        technical_knowledge=persona.technical_knowledge,
        budget_sensitivity=persona.budget_sensitivity,
        patience_level=persona.patience_level,
        scenario_type=scenario.get("type", "").value if hasattr(scenario.get("type", ""), "value") else str(scenario.get("type", "")),
        scenario_context=scenario.get("context", scenario.get("initial_message", "")),
        hidden_requirements="\n".join(persona.hidden_requirements) if persona.hidden_requirements else "None specified",
        conversation_history=history,
        last_ira_message=last_ira_message[:500],
    )
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a realistic customer simulator for sales training."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.8,
            max_tokens=500,
        )
        
        customer_message = response.choices[0].message.content.strip()
        
        # Check if conversation should end
        end_signals = [
            "thank you for your help",
            "we'll get back to you",
            "let me discuss internally",
            "this isn't going to work",
            "we've decided to go with",
            "please proceed with",
            "send me the quote",
            "i'm not interested",
        ]
        should_continue = not any(sig in customer_message.lower() for sig in end_signals)
        
        return customer_message, should_continue
        
    except Exception as e:
        print(f"Error generating customer response: {e}")
        return "Thank you for the information. We'll review and get back to you.", False


# =============================================================================
# COACH AGENT
# =============================================================================

COACH_AGENT_PROMPT = """You are Coach Rushabh - an expert sales trainer for Machinecraft Technologies.

You're reviewing a simulated sales conversation between Ira (the AI sales assistant) and a customer.

CONVERSATION TO REVIEW:
{conversation}

SCENARIO TYPE: {scenario_type}
CUSTOMER PERSONA: {persona_style} style, {technical_knowledge} technical knowledge
OUTCOME: {outcome}

CRITICAL BUSINESS RULES (check if violated):
1. AM Series can ONLY handle ≤1.5mm thickness
2. IMG process requires IMG series, not PF1/PF2
3. Lead time is 12-16 weeks (never promise faster)
4. Never badmouth competitors
5. Always qualify before recommending

EVALUATE AND PROVIDE:

1. OVERALL SCORE (0-10): How well did Ira handle this conversation?

2. SPECIFIC SCORES (0-10 each):
   - Qualification Quality: Did Ira ask the right questions?
   - Technical Accuracy: Were specs, prices, and capabilities correct?
   - Personality & Warmth: Did Ira sound human and helpful?
   - Business Rule Compliance: Were all rules followed?
   - Customer Satisfaction: Would the customer be happy?
   - Closing Effectiveness: Did Ira move toward the sale?

3. SPECIFIC ISSUES: List 2-3 things Ira did wrong or could improve

4. SPECIFIC WINS: List 2-3 things Ira did well

5. LESSON TO LEARN: One specific, actionable lesson Ira should learn from this conversation

6. SUB-AGENT FEEDBACK: Which sub-agent (Athena/Clio/Calliope/Vera/Sophia) needs improvement and what should they learn?

Format your response as JSON:
{{
    "overall_score": 7.5,
    "scores": {{
        "qualification_quality": 8,
        "technical_accuracy": 7,
        "personality_warmth": 8,
        "business_rule_compliance": 9,
        "customer_satisfaction": 7,
        "closing_effectiveness": 6
    }},
    "issues": ["Issue 1", "Issue 2"],
    "wins": ["Win 1", "Win 2"],
    "lesson": {{
        "id": "LESSON_XXX",
        "category": "category_name",
        "lesson": "The specific lesson",
        "trigger": "When this situation occurs",
        "correct_action": "What Ira should do",
        "incorrect_action": "What to avoid"
    }},
    "sub_agent_feedback": {{
        "agent": "calliope",
        "feedback": "What this agent should learn"
    }}
}}"""


def coach_evaluate_conversation(conversation: SimulatedConversation) -> Tuple[ConversationRating, Dict]:
    """
    Have the Coach Agent evaluate a conversation and generate lessons.
    """
    
    # Build conversation text
    conv_text = "\n\n".join([
        f"{'CUSTOMER' if t.role == 'customer' else 'IRA'}:\n{t.message}"
        for t in conversation.turns
    ])
    
    prompt = COACH_AGENT_PROMPT.format(
        conversation=conv_text,
        scenario_type=conversation.scenario_type.value,
        persona_style=conversation.persona.style,
        technical_knowledge=conversation.persona.technical_knowledge,
        outcome=conversation.outcome,
    )
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an expert sales coach. Respond only with valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=1000,
        )
        
        result_text = response.choices[0].message.content.strip()
        
        # Clean up JSON
        if "```json" in result_text:
            result_text = result_text.split("```json")[1].split("```")[0]
        elif "```" in result_text:
            result_text = result_text.split("```")[1].split("```")[0]
        
        result = json.loads(result_text)
        
        rating = ConversationRating(
            overall_score=result.get("overall_score", 5),
            qualification_quality=result.get("scores", {}).get("qualification_quality", 5),
            technical_accuracy=result.get("scores", {}).get("technical_accuracy", 5),
            personality_warmth=result.get("scores", {}).get("personality_warmth", 5),
            business_rule_compliance=result.get("scores", {}).get("business_rule_compliance", 5),
            customer_satisfaction_proxy=result.get("scores", {}).get("customer_satisfaction", 5),
            closing_effectiveness=result.get("scores", {}).get("closing_effectiveness", 5),
            specific_issues=result.get("issues", []),
            specific_wins=result.get("wins", []),
        )
        
        lesson = result.get("lesson", {})
        sub_agent_feedback = result.get("sub_agent_feedback", {})
        
        return rating, {"lesson": lesson, "sub_agent_feedback": sub_agent_feedback}
        
    except Exception as e:
        print(f"Error in coach evaluation: {e}")
        return ConversationRating(
            overall_score=5, qualification_quality=5, technical_accuracy=5,
            personality_warmth=5, business_rule_compliance=5,
            customer_satisfaction_proxy=5, closing_effectiveness=5,
        ), {}


# =============================================================================
# LEARNING INTEGRATOR
# =============================================================================

def store_lesson(lesson: Dict, conversation_id: str):
    """Store a learned lesson for future use."""
    
    lessons_dir = PROJECT_ROOT / "data" / "learned_lessons"
    lessons_dir.mkdir(parents=True, exist_ok=True)
    
    # Load existing lessons
    lessons_file = lessons_dir / "continuous_learnings.json"
    if lessons_file.exists():
        with open(lessons_file) as f:
            all_lessons = json.load(f)
    else:
        all_lessons = {"lessons": [], "sub_agent_upgrades": {}}
    
    # Add new lesson
    if lesson.get("lesson"):
        lesson_entry = lesson["lesson"]
        lesson_entry["learned_from"] = conversation_id
        lesson_entry["timestamp"] = datetime.now().isoformat()
        all_lessons["lessons"].append(lesson_entry)
    
    # Add sub-agent feedback
    if lesson.get("sub_agent_feedback"):
        agent = lesson["sub_agent_feedback"].get("agent", "unknown")
        feedback = lesson["sub_agent_feedback"].get("feedback", "")
        
        if agent not in all_lessons["sub_agent_upgrades"]:
            all_lessons["sub_agent_upgrades"][agent] = []
        all_lessons["sub_agent_upgrades"][agent].append({
            "feedback": feedback,
            "from_conversation": conversation_id,
            "timestamp": datetime.now().isoformat(),
        })
    
    # Save
    with open(lessons_file, 'w') as f:
        json.dump(all_lessons, f, indent=2)
    
    print(f"  💾 Stored lesson from conversation {conversation_id}")


# =============================================================================
# SIMULATION RUNNER
# =============================================================================

def run_simulation(
    scenario_template: Dict,
    max_turns: int = 8,
    verbose: bool = True,
) -> SimulatedConversation:
    """
    Run a full simulated conversation.
    """
    
    # Generate persona
    scenario_type = scenario_template.get("type", ScenarioType.VAGUE_INQUIRY)
    persona = generate_customer_persona(scenario_type)
    
    # Add hidden requirements
    if "hidden_need" in scenario_template:
        persona.hidden_requirements = [scenario_template["hidden_need"]]
    
    # Create conversation
    conversation_id = f"SIM_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{random.randint(1000, 9999)}"
    conversation = SimulatedConversation(
        id=conversation_id,
        scenario_type=scenario_type,
        persona=persona,
    )
    
    if verbose:
        print(f"\n{'='*70}")
        print(f"🎭 SIMULATION: {scenario_type.value}")
        print(f"👤 Customer: {persona.name} ({persona.company}) - {persona.style} style")
        print(f"{'='*70}")
    
    # Initial customer message
    initial_message = scenario_template.get("initial_message", "We need a thermoforming machine.")
    conversation.turns.append(ConversationTurn(role="customer", message=initial_message))
    
    if verbose:
        print(f"\n📧 CUSTOMER ({persona.name}):\n{initial_message}")
    
    # Conversation loop
    for turn in range(max_turns):
        # Get Ira's response
        if IRA_AVAILABLE:
            ira_response = generate_answer(
                conversation.turns[-1].message,
                channel='email'
            )
            ira_message = ira_response.text
        else:
            ira_message = "[Ira unavailable - simulated response]"
        
        conversation.turns.append(ConversationTurn(role="ira", message=ira_message))
        
        if verbose:
            print(f"\n🤖 IRA:\n{ira_message[:500]}{'...' if len(ira_message) > 500 else ''}")
        
        # Get customer response
        customer_message, should_continue = generate_customer_response(
            persona=persona,
            scenario=scenario_template,
            conversation=conversation.turns,
            last_ira_message=ira_message,
        )
        
        conversation.turns.append(ConversationTurn(role="customer", message=customer_message))
        
        if verbose:
            print(f"\n📧 CUSTOMER ({persona.name}):\n{customer_message}")
        
        if not should_continue:
            break
    
    # Determine outcome
    last_customer_msg = conversation.turns[-1].message.lower()
    if any(pos in last_customer_msg for pos in ["proceed", "quote", "order", "decided to go"]):
        conversation.outcome = "success"
    elif any(neg in last_customer_msg for neg in ["not interested", "won't work", "going elsewhere"]):
        conversation.outcome = "lost"
    else:
        conversation.outcome = "ongoing"
    
    if verbose:
        print(f"\n📊 OUTCOME: {conversation.outcome}")
    
    return conversation


def run_learning_session(
    num_simulations: int = 3,
    scenario_types: List[ScenarioType] = None,
    verbose: bool = True,
) -> Dict:
    """
    Run a complete learning session with multiple simulations.
    """
    
    if scenario_types is None:
        scenario_types = list(ScenarioType)
    
    session_results = {
        "session_id": f"SESSION_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "timestamp": datetime.now().isoformat(),
        "num_simulations": num_simulations,
        "conversations": [],
        "average_score": 0,
        "lessons_learned": [],
        "sub_agent_upgrades": {},
    }
    
    print("\n" + "="*70)
    print("🎓 IRA CONTINUOUS LEARNING SESSION")
    print("="*70)
    print(f"Running {num_simulations} simulated conversations...")
    
    total_score = 0
    
    for i in range(num_simulations):
        # Select scenario
        scenario_type = random.choice(scenario_types)
        scenario = next(
            (s for s in REAL_SCENARIO_TEMPLATES if s.get("type") == scenario_type),
            REAL_SCENARIO_TEMPLATES[0]
        )
        
        # Run simulation
        conversation = run_simulation(scenario, verbose=verbose)
        
        # Coach evaluation
        print(f"\n🧑‍🏫 COACH EVALUATION...")
        rating, lessons = coach_evaluate_conversation(conversation)
        conversation.rating = rating
        conversation.lessons = [lessons]
        
        print(f"  Overall Score: {rating.overall_score}/10")
        print(f"  Issues: {', '.join(rating.specific_issues[:2])}")
        print(f"  Wins: {', '.join(rating.specific_wins[:2])}")
        
        if lessons.get("lesson"):
            print(f"  📚 Lesson: {lessons['lesson'].get('lesson', 'N/A')[:60]}...")
        
        # Store lesson
        store_lesson(lessons, conversation.id)
        
        # Update session results
        total_score += rating.overall_score
        session_results["conversations"].append({
            "id": conversation.id,
            "scenario": scenario_type.value,
            "outcome": conversation.outcome,
            "score": rating.overall_score,
            "turns": len(conversation.turns),
        })
        session_results["lessons_learned"].append(lessons.get("lesson", {}))
    
    session_results["average_score"] = total_score / num_simulations
    
    # Summary
    print("\n" + "="*70)
    print("📊 SESSION SUMMARY")
    print("="*70)
    print(f"Simulations run: {num_simulations}")
    print(f"Average score: {session_results['average_score']:.1f}/10")
    print(f"Outcomes: {[c['outcome'] for c in session_results['conversations']]}")
    print(f"Lessons stored: {len([l for l in session_results['lessons_learned'] if l])}")
    
    # Save session
    sessions_dir = PROJECT_ROOT / "data" / "learning_sessions"
    sessions_dir.mkdir(parents=True, exist_ok=True)
    session_file = sessions_dir / f"{session_results['session_id']}.json"
    
    with open(session_file, 'w') as f:
        json.dump(session_results, f, indent=2, default=str)
    
    print(f"\n💾 Session saved to: {session_file}")
    
    return session_results


# =============================================================================
# CLI
# =============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Ira Continuous Learning Loop")
    parser.add_argument("--sessions", "-n", type=int, default=3, help="Number of simulations to run")
    parser.add_argument("--scenario", "-s", type=str, help="Specific scenario type to test")
    parser.add_argument("--verbose", "-v", action="store_true", default=True, help="Verbose output")
    parser.add_argument("--quiet", "-q", action="store_true", help="Quiet mode")
    parser.add_argument("--auto", action="store_true", help="Continuous learning mode")
    
    args = parser.parse_args()
    
    if args.quiet:
        args.verbose = False
    
    if args.scenario:
        scenario_types = [ScenarioType(args.scenario)]
    else:
        scenario_types = None
    
    if args.auto:
        print("🔄 Starting continuous learning mode (Ctrl+C to stop)...")
        session_count = 0
        try:
            while True:
                session_count += 1
                print(f"\n{'#'*70}")
                print(f"CONTINUOUS LEARNING - SESSION {session_count}")
                print(f"{'#'*70}")
                
                run_learning_session(
                    num_simulations=args.sessions,
                    scenario_types=scenario_types,
                    verbose=args.verbose,
                )
                
                print("\n⏳ Waiting 60 seconds before next session...")
                import time
                time.sleep(60)
                
        except KeyboardInterrupt:
            print(f"\n\n✅ Stopped after {session_count} sessions")
    else:
        run_learning_session(
            num_simulations=args.sessions,
            scenario_types=scenario_types,
            verbose=args.verbose,
        )
