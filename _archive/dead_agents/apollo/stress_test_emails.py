#!/usr/bin/env python3
"""
IRA STRESS TEST EMAIL SUITE
============================

Creative, challenging email scenarios to test Ira's ability to:
1. Handle vague/confusing inquiries gracefully
2. Guide customers toward providing needed information
3. Correct misconceptions without being condescending
4. Handle edge cases and unusual requests
5. Maintain personality under pressure

Each scenario includes:
- Customer persona
- Initial email
- Expected behavior from Ira
- Success criteria
"""

import sys
import os
import random
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum

# Add paths - handle running from any directory
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(os.path.dirname(SCRIPT_DIR))  # Go up to Ira/
if os.path.basename(BASE_DIR) != 'Ira':
    # If run from Ira directory directly
    BASE_DIR = os.path.dirname(SCRIPT_DIR)

# Add brain path
BRAIN_PATH = os.path.join(BASE_DIR, 'openclaw/agents/ira/src/brain')
if os.path.exists(BRAIN_PATH):
    sys.path.insert(0, BRAIN_PATH)
else:
    # Try relative from cwd
    sys.path.insert(0, 'openclaw/agents/ira/src/brain')

try:
    from generate_answer import generate_answer, ResponseObject
    GENERATE_AVAILABLE = True
except ImportError:
    GENERATE_AVAILABLE = False
    print("Warning: generate_answer not available")


class Difficulty(Enum):
    EASY = "easy"           # Clear intent, just needs qualification
    MEDIUM = "medium"       # Some confusion or missing info
    HARD = "hard"           # Misconceptions, conflicting requirements
    NIGHTMARE = "nightmare"  # Edge cases, unusual requests


class CustomerType(Enum):
    VAGUE_BUYER = "vague"              # "I need a machine"
    PRICE_HUNTER = "price_hunter"       # Only cares about price
    TECHNICAL_EXPERT = "expert"         # Knows specs, tests Ira
    CONFUSED_BOSS = "boss"              # Got sent by boss, knows nothing
    COMPETITOR_COMPARISON = "compare"   # Comparing with competitors
    IMPOSSIBLE_REQUEST = "impossible"   # Wants impossible specs
    WRONG_ASSUMPTIONS = "wrong"         # Has wrong info about products
    URGENT_BUYER = "urgent"             # Needs it yesterday
    TIRE_KICKER = "tire_kicker"         # Just browsing, wastes time
    NON_NATIVE = "non_native"           # Limited English
    MULTIPLE_NEEDS = "multiple"         # Needs several machines
    BUDGET_CONSTRAINED = "budget"       # Has specific budget limit


@dataclass
class StressTestScenario:
    """A stress test scenario for Ira."""
    id: str
    name: str
    difficulty: Difficulty
    customer_type: CustomerType
    persona: Dict[str, str]
    initial_email: str
    follow_ups: List[str] = field(default_factory=list)  # Potential follow-up responses
    expected_behaviors: List[str] = field(default_factory=list)
    success_criteria: List[str] = field(default_factory=list)
    trap_to_avoid: str = ""  # What Ira should NOT do
    ideal_machine: str = ""  # The machine Ira should eventually recommend
    notes: str = ""


# =============================================================================
# STRESS TEST SCENARIOS
# =============================================================================

STRESS_TESTS: List[StressTestScenario] = [
    
    # =========================================================================
    # EASY SCENARIOS
    # =========================================================================
    
    StressTestScenario(
        id="ST001",
        name="The Classic Vague Inquiry",
        difficulty=Difficulty.EASY,
        customer_type=CustomerType.VAGUE_BUYER,
        persona={
            "name": "Rajesh Patel",
            "company": "Patel Plastics Pvt Ltd",
            "role": "Owner",
            "location": "Ahmedabad",
        },
        initial_email="""Hi,

We are looking for thermoforming machine. Please send details and price.

Thanks,
Rajesh""",
        follow_ups=[
            "We make plastic trays for packaging. Size around 1 meter.",
            "HIPS material, 1-2mm thickness",
        ],
        expected_behaviors=[
            "Ask about forming area requirements",
            "Ask about material type",
            "Ask about sheet thickness",
            "Ask about application/industry",
        ],
        success_criteria=[
            "Does NOT immediately recommend a machine",
            "Asks at least 2-3 qualifying questions",
            "Maintains professional warmth",
        ],
        trap_to_avoid="Recommending a machine without sufficient information",
        ideal_machine="AM-Series (thin gauge packaging)",
        notes="Classic vague inquiry - Ira should ask qualifying questions"
    ),
    
    StressTestScenario(
        id="ST002",
        name="The Price-First Customer",
        difficulty=Difficulty.EASY,
        customer_type=CustomerType.PRICE_HUNTER,
        persona={
            "name": "Amit Sharma",
            "company": "Sharma Industries",
            "role": "Purchase Manager",
            "location": "Delhi",
        },
        initial_email="""What is the cheapest thermoforming machine you have?

Send me price list.

Amit""",
        follow_ups=[
            "Budget is 15 lakhs maximum",
            "We need to form small parts, maybe 500x600mm",
            "PVC sheets, 2mm max",
        ],
        expected_behaviors=[
            "Acknowledge price concern",
            "Explain that price depends on requirements",
            "Ask qualifying questions to find best value",
        ],
        success_criteria=[
            "Does NOT just send a price list",
            "Redirects to requirements discussion",
            "Eventually matches to budget-appropriate machine",
        ],
        trap_to_avoid="Just sending prices without understanding needs",
        ideal_machine="Entry-level PF1 or AM series",
        notes="Price-focused customer needs to be redirected to requirements"
    ),
    
    # =========================================================================
    # MEDIUM SCENARIOS
    # =========================================================================
    
    StressTestScenario(
        id="ST003",
        name="The Confused Boss",
        difficulty=Difficulty.MEDIUM,
        customer_type=CustomerType.CONFUSED_BOSS,
        persona={
            "name": "Vikram Mehta",
            "company": "Mehta Auto Components",
            "role": "Managing Director",
            "location": "Pune",
        },
        initial_email="""Hello,

My production manager told me we need a "vacuum forming machine" for our new project. 
I don't really understand these machines but we need to start production in 3 months.

What do you suggest? We make parts for Tata Motors.

Vikram Mehta
MD, Mehta Auto Components""",
        follow_ups=[
            "I'll ask my production guy... he says something about dashboard parts",
            "He said 1200 x 800 mm and ABS material",
            "Budget is not a problem if machine is good quality",
        ],
        expected_behaviors=[
            "Acknowledge the automotive context",
            "Gently explain what information is needed",
            "Be patient and professional",
            "Eventually guide to PF1 series for automotive",
        ],
        success_criteria=[
            "Does NOT overwhelm with technical jargon",
            "Explains simply what info is needed",
            "Recognizes automotive = likely PF1/PF2 series",
        ],
        trap_to_avoid="Being condescending or overly technical",
        ideal_machine="PF1-C-1510 or similar",
        notes="Boss doesn't know specs - needs gentle guidance"
    ),
    
    StressTestScenario(
        id="ST004",
        name="The Competitor Comparison",
        difficulty=Difficulty.MEDIUM,
        customer_type=CustomerType.COMPETITOR_COMPARISON,
        persona={
            "name": "Chen Wei",
            "company": "Suzhou Precision Plastics",
            "role": "Technical Director",
            "location": "China",
        },
        initial_email="""Hi Machinecraft,

We are comparing your machines with GEISS (Germany) and Formech (UK).

We need 2500 x 2000 mm forming area, 8mm ABS, for automotive interior parts.

Please send your best offer. GEISS quoted us €180,000.

Best regards,
Chen Wei""",
        follow_ups=[
            "GEISS machine has 150kW heaters. What about yours?",
            "What is your lead time? GEISS says 20 weeks.",
            "Do you have reference customers in automotive?",
        ],
        expected_behaviors=[
            "Acknowledge competitor comparison professionally",
            "Focus on Machinecraft strengths, not competitor weaknesses",
            "Provide detailed specs for comparison",
            "Highlight value proposition",
        ],
        success_criteria=[
            "Does NOT badmouth competitors",
            "Provides clear spec comparison",
            "Highlights Machinecraft advantages",
            "Confident but not arrogant",
        ],
        trap_to_avoid="Badmouthing GEISS or Formech",
        ideal_machine="PF2-P2520 or PF1-C-2520",
        notes="Competitor comparison - be confident, not defensive"
    ),
    
    StressTestScenario(
        id="ST005",
        name="The Technical Expert Test",
        difficulty=Difficulty.MEDIUM,
        customer_type=CustomerType.TECHNICAL_EXPERT,
        persona={
            "name": "Dr. Anand Krishnamurthy",
            "company": "IIT Madras - Materials Lab",
            "role": "Professor, Polymer Engineering",
            "location": "Chennai",
        },
        initial_email="""Dear Machinecraft,

We require a thermoforming machine for our polymer processing lab with the following specifications:

- Forming area: 600 x 400 mm (minimum)
- Sheet thickness capability: 0.5 to 6 mm
- Temperature uniformity: ±2°C across heating zone
- Vacuum: minimum 0.9 bar (90 kPa)
- Must support: PETG, ABS, PC, PMMA, PEEK

Additionally, we need data logging capability for research purposes.

Please confirm your machine specifications meet these requirements.

Dr. A. Krishnamurthy
Professor, Dept. of Polymer Engineering""",
        follow_ups=[
            "What is the heater response time?",
            "Can you provide thermal uniformity data?",
            "Is PLC data exportable to CSV?",
        ],
        expected_behaviors=[
            "Match technical level of inquiry",
            "Provide precise specifications",
            "Be honest about capabilities and limitations",
            "Note: PEEK is challenging material",
        ],
        success_criteria=[
            "Provides accurate technical specs",
            "Mentions PEEK temperature requirements (~400°C)",
            "Suggests appropriate machine model",
            "Offers to provide detailed technical documentation",
        ],
        trap_to_avoid="Overpromising on PEEK capability without caveats",
        ideal_machine="PF1-X-0806 with high-temp heater option",
        notes="Technical expert - must match expertise level"
    ),
    
    # =========================================================================
    # HARD SCENARIOS
    # =========================================================================
    
    StressTestScenario(
        id="ST006",
        name="The Wrong Assumptions",
        difficulty=Difficulty.HARD,
        customer_type=CustomerType.WRONG_ASSUMPTIONS,
        persona={
            "name": "Sandeep Reddy",
            "company": "Reddy Packaging Solutions",
            "role": "Production Head",
            "location": "Hyderabad",
        },
        initial_email="""Hi,

I need your AM-2000 machine for forming 5mm thick ABS sheets. 
Please send quote with delivery time.

We need to start production of bathtub liners next month.

Sandeep""",
        follow_ups=[
            "What do you mean AM can't do 5mm? The brochure says 'heavy duty'",
            "Ok what machine do I need then?",
            "That's more expensive... can you do discount?",
        ],
        expected_behaviors=[
            "Politely correct the misconception about AM series",
            "Explain AM is for thin gauge (≤1.5mm)",
            "Recommend correct machine (PF1/PF2) for 5mm ABS",
            "Handle the correction gracefully",
        ],
        success_criteria=[
            "Corrects AM series limitation clearly",
            "Does NOT just accept wrong order",
            "Redirects to appropriate machine",
            "Maintains customer relationship",
        ],
        trap_to_avoid="Accepting the order for wrong machine, or being condescending",
        ideal_machine="PF1-C-2015 or PF2 series",
        notes="Customer has wrong info - correct gently but firmly"
    ),
    
    StressTestScenario(
        id="ST007",
        name="The Impossible Request",
        difficulty=Difficulty.HARD,
        customer_type=CustomerType.IMPOSSIBLE_REQUEST,
        persona={
            "name": "Priya Venkatesh",
            "company": "VenTech Industries",
            "role": "CEO",
            "location": "Bangalore",
        },
        initial_email="""Hello,

We need a thermoforming machine with:
- 3000 x 3000 mm forming area
- 15mm sheet thickness
- Budget: 25 lakhs
- Delivery: 4 weeks

Is this possible?

Priya""",
        follow_ups=[
            "Why can't you do 4 weeks? It's urgent!",
            "Can you at least do 3000x2000?",
            "What's the minimum budget for large format?",
        ],
        expected_behaviors=[
            "Acknowledge the requirements professionally",
            "Explain what's realistic for each requirement",
            "Offer closest possible alternatives",
            "Be honest about limitations",
        ],
        success_criteria=[
            "Does NOT promise impossible specs",
            "Explains budget vs specs tradeoff",
            "Explains realistic lead times (12-16 weeks)",
            "Offers alternative solutions",
        ],
        trap_to_avoid="Promising impossible delivery or price",
        ideal_machine="PF2-P3020 (if budget increases) or PF2-P2520",
        notes="Impossible combination - must manage expectations"
    ),
    
    StressTestScenario(
        id="ST008",
        name="The Urgent Panic Buyer",
        difficulty=Difficulty.HARD,
        customer_type=CustomerType.URGENT_BUYER,
        persona={
            "name": "Mohammed Al-Rashid",
            "company": "Gulf Plastics Manufacturing",
            "role": "Operations Director",
            "location": "Dubai, UAE",
        },
        initial_email="""URGENT!!!

Our thermoforming machine broke down completely. We have orders due in 6 weeks.

We need a replacement IMMEDIATELY. 1500 x 1000 mm, 6mm ABS.

Can you ship one this week? Money is not an issue.

PLEASE RESPOND IMMEDIATELY.

Mohammed""",
        follow_ups=[
            "What do you mean 12 weeks? I need it NOW!",
            "Do you have any machines ready in stock?",
            "Can you recommend anyone who has stock machines?",
        ],
        expected_behaviors=[
            "Acknowledge urgency empathetically",
            "Be honest about lead times",
            "Offer any expedited options if available",
            "Suggest interim solutions if possible",
        ],
        success_criteria=[
            "Does NOT promise unrealistic delivery",
            "Shows empathy for urgent situation",
            "Explains manufacturing process/lead time",
            "Offers to check stock/expedited options",
        ],
        trap_to_avoid="Promising immediate delivery that's impossible",
        ideal_machine="PF1-C-1510 (if in stock) or expedited production",
        notes="Urgent situation - empathy + honesty"
    ),
    
    # =========================================================================
    # NIGHTMARE SCENARIOS
    # =========================================================================
    
    StressTestScenario(
        id="ST009",
        name="The Rambling Confused Email",
        difficulty=Difficulty.NIGHTMARE,
        customer_type=CustomerType.CONFUSED_BOSS,
        persona={
            "name": "Uncle Ji",
            "company": "Sharma & Sons Trading",
            "role": "Partner",
            "location": "Mumbai",
        },
        initial_email="""Dear Sir/Madam,

My nephew told me about your company. He works in plastic business.
We are thinking maybe to start some manufacturing. My brother-in-law 
has a factory in Bhiwandi, empty space is there.

What machines do you have? Plastic forming types. I saw on YouTube 
some vacuum machine making trays. Very interesting.

Also do you do training? My workers don't know anything about this.

How much investment is needed? My cousin also wants to know, he might 
be interested in partnership.

Please call me on WhatsApp: +91 98XXX XXXXX

Thanking you,
With regards,
Sharma Ji""",
        follow_ups=[
            "Yes yes, any machine is okay. What is cheapest?",
            "My nephew says HIPS is good material. 500 trays per day needed.",
            "Size? Medium size. Like food tray. You know?",
        ],
        expected_behaviors=[
            "Extract the key requirements from rambling email",
            "Be patient and professional",
            "Ask structured questions to clarify",
            "Eventually guide to appropriate machine",
        ],
        success_criteria=[
            "Does NOT dismiss the inquiry",
            "Extracts: wants to make trays, new to business",
            "Asks structured qualifying questions",
            "Offers training information",
        ],
        trap_to_avoid="Being dismissive or impatient",
        ideal_machine="Entry-level AM series for tray packaging",
        notes="Rambling email - extract key info patiently"
    ),
    
    StressTestScenario(
        id="ST010",
        name="The Material Expert Challenge",
        difficulty=Difficulty.NIGHTMARE,
        customer_type=CustomerType.TECHNICAL_EXPERT,
        persona={
            "name": "Hiroshi Tanaka",
            "company": "Toyota Boshoku",
            "role": "Senior Engineer, Interior Components",
            "location": "Japan",
        },
        initial_email="""Dear Machinecraft,

We are evaluating thermoforming solutions for a new interior component line.

Our requirements:
- TPO forming with grain retention (IMG process)
- Forming area: 2200 x 1800 mm
- Cycle time: under 90 seconds
- Sheet thickness: 2-4mm TPO/PP composite
- Must maintain class-A surface finish
- Integrated with existing MES system (FANUC protocol)

We have strict quality requirements (Toyota Production System).

Please provide:
1. Machine model recommendation
2. Cycle time data for similar applications
3. Reference list of automotive clients
4. Quality certifications (ISO, IATF)

Best regards,
Tanaka-san""",
        follow_ups=[
            "What is your Cpk capability for forming depth consistency?",
            "Do you support predictive maintenance IoT features?",
            "Can your PLC integrate with our Andon system?",
        ],
        expected_behaviors=[
            "Recognize this as IMG (In-Mold Graining) application",
            "Recommend IMG series machine",
            "Provide detailed technical specs",
            "Offer to connect with automotive team",
        ],
        success_criteria=[
            "Identifies IMG process requirement",
            "Recommends IMG series (not PF1/PF2)",
            "Addresses all technical questions",
            "Offers factory visit/reference calls",
        ],
        trap_to_avoid="Recommending wrong machine series (PF1 instead of IMG)",
        ideal_machine="IMG-2220 or custom IMG solution",
        notes="High-spec automotive - must recognize IMG requirement"
    ),
    
    StressTestScenario(
        id="ST011",
        name="The Passive-Aggressive Price Negotiator",
        difficulty=Difficulty.NIGHTMARE,
        customer_type=CustomerType.PRICE_HUNTER,
        persona={
            "name": "Deepak Agarwal",
            "company": "Agarwal Enterprises",
            "role": "Director",
            "location": "Kolkata",
        },
        initial_email="""Hi,

I got quote from your competitor for ₹45 lakhs for similar machine.
Your salesman quoted ₹62 lakhs. Why so expensive?

Is Machinecraft only for rich customers? We are also good customers but you 
don't want our business it seems.

My friend bought from China for ₹25 lakhs same capacity.

Please revise your quote or we will go to competition.

Deepak""",
        follow_ups=[
            "So you're saying Chinese machines are bad? That's not fair.",
            "What guarantee do you give that your machine is worth extra money?",
            "Ok give me best price. Final offer.",
        ],
        expected_behaviors=[
            "Stay professional and calm",
            "Explain value proposition without being defensive",
            "Highlight quality, service, warranty differences",
            "Don't badmouth competitors",
        ],
        success_criteria=[
            "Does NOT get defensive or emotional",
            "Explains value without attacking competitors",
            "Offers to discuss requirements to optimize price",
            "Maintains professional dignity",
        ],
        trap_to_avoid="Getting defensive, badmouthing China, or caving on price",
        ideal_machine="Whatever was quoted - focus on value discussion",
        notes="Difficult negotiator - stay professional, explain value"
    ),
    
    StressTestScenario(
        id="ST012",
        name="The Multi-Language Confusion",
        difficulty=Difficulty.NIGHTMARE,
        customer_type=CustomerType.NON_NATIVE,
        persona={
            "name": "Aleksandr Petrov",
            "company": "Petrov Plastik OOO",
            "role": "Chief Engineer",
            "location": "Yekaterinburg, Russia",
        },
        initial_email="""Hello Machinecraft!

We need machine for making... how to say... plastic cover for refrigerator?
Inside part. You understand?

Size we need 800 x 600 millimetr. Material is ABS, 3mm thick.

How much cost? We need maybe 2 machine if price is good.

Sorry my English not perfect. We can also write in Russian if you have translator?

Spasibo (thank you),
Aleksandr""",
        follow_ups=[
            "Da, refrigerator liner. Inside white part. You know?",
            "Temperature we need -20 degree working. ABS is ok for this?",
            "What is... how you say... warranty? Garantiya?",
        ],
        expected_behaviors=[
            "Be patient with language barrier",
            "Use simple, clear English",
            "Confirm understanding of requirements",
            "Focus on the actual technical need",
        ],
        success_criteria=[
            "Does NOT dismiss due to language",
            "Uses simple, clear communication",
            "Confirms: refrigerator liner, 800x600, ABS 3mm",
            "Addresses cold temp application concern",
        ],
        trap_to_avoid="Being impatient or using complex technical jargon",
        ideal_machine="PF1-X-1008 or PF1-C-1008",
        notes="Language barrier - simple clear communication"
    ),
]


# =============================================================================
# TEST RUNNER
# =============================================================================

def run_stress_test(scenario: StressTestScenario, verbose: bool = True) -> Dict:
    """
    Run a single stress test scenario and evaluate Ira's response.
    """
    if not GENERATE_AVAILABLE:
        return {"error": "generate_answer not available"}
    
    results = {
        "scenario_id": scenario.id,
        "scenario_name": scenario.name,
        "difficulty": scenario.difficulty.value,
        "customer_type": scenario.customer_type.value,
        "initial_email": scenario.initial_email,
        "ira_response": None,
        "evaluation": {},
        "passed": False,
    }
    
    if verbose:
        print(f"\n{'='*70}")
        print(f"STRESS TEST: {scenario.id} - {scenario.name}")
        print(f"Difficulty: {scenario.difficulty.value.upper()}")
        print(f"{'='*70}")
        print(f"\n📧 CUSTOMER EMAIL:")
        print("-" * 50)
        print(scenario.initial_email)
        print("-" * 50)
    
    # Generate Ira's response
    try:
        response = generate_answer(
            scenario.initial_email,
            channel='email'
        )
        results["ira_response"] = response.text
        
        if verbose:
            print(f"\n🤖 IRA'S RESPONSE:")
            print("-" * 50)
            print(response.text)
            print("-" * 50)
        
        # Evaluate response
        evaluation = evaluate_response(scenario, response.text)
        results["evaluation"] = evaluation
        results["passed"] = evaluation.get("overall_pass", False)
        
        if verbose:
            print(f"\n📊 EVALUATION:")
            for criterion, passed in evaluation.items():
                if criterion != "overall_pass":
                    status = "✅" if passed else "❌"
                    print(f"  {status} {criterion}")
            print(f"\n{'🎉 PASSED' if results['passed'] else '❌ FAILED'}")
    
    except Exception as e:
        results["error"] = str(e)
        if verbose:
            print(f"❌ ERROR: {e}")
    
    return results


def evaluate_response(scenario: StressTestScenario, response: str) -> Dict:
    """
    Evaluate Ira's response against success criteria.
    """
    evaluation = {}
    response_lower = response.lower()
    
    # Check for common failures
    
    # 1. Did NOT immediately recommend a machine for vague inquiries?
    if scenario.customer_type == CustomerType.VAGUE_BUYER:
        # Should contain questions, not immediate recommendation
        has_questions = any(q in response for q in ["?", "forming area", "material", "thickness"])
        immediate_rec = any(m in response_lower for m in ["pf1-", "pf2-", "am-", "img-", "recommend the"])
        evaluation["asked_qualifying_questions"] = has_questions
        evaluation["avoided_premature_recommendation"] = not immediate_rec or has_questions
    
    # 2. Maintained professional tone?
    unprofessional = any(bad in response_lower for bad in [
        "that's stupid", "you're wrong", "obviously", "as i already said"
    ])
    evaluation["professional_tone"] = not unprofessional
    
    # 3. For wrong assumptions, did Ira correct them?
    if scenario.customer_type == CustomerType.WRONG_ASSUMPTIONS:
        if "am series" in scenario.initial_email.lower() and "5mm" in scenario.initial_email.lower():
            corrected_am = any(c in response_lower for c in [
                "1.5mm", "thin gauge", "≤1.5", "pf1", "pf2", "heavy gauge"
            ])
            evaluation["corrected_am_misconception"] = corrected_am
    
    # 4. For impossible requests, did Ira manage expectations?
    if scenario.customer_type == CustomerType.IMPOSSIBLE_REQUEST:
        managed = any(m in response_lower for m in [
            "lead time", "12-16 weeks", "unfortunately", "however", "alternative"
        ])
        evaluation["managed_expectations"] = managed
    
    # 5. For technical experts, did Ira match the technical level?
    if scenario.customer_type == CustomerType.TECHNICAL_EXPERT:
        technical = any(t in response_lower for t in [
            "kw", "mm", "specifications", "temperature", "vacuum"
        ])
        evaluation["matched_technical_level"] = technical
    
    # 6. Did NOT badmouth competitors?
    badmouth = any(b in response_lower for b in [
        "geiss is", "formech is", "chinese machines are bad", "cheap chinese"
    ])
    evaluation["avoided_badmouthing_competitors"] = not badmouth
    
    # 7. Included signature/sign-off?
    has_signature = any(s in response_lower for s in ["ira", "machinecraft", "cheers", "best"])
    evaluation["included_signature"] = has_signature
    
    # Overall pass
    evaluation["overall_pass"] = all(v for v in evaluation.values())
    
    return evaluation


def run_all_stress_tests(difficulties: List[Difficulty] = None, verbose: bool = True) -> Dict:
    """
    Run all stress tests (or filtered by difficulty).
    """
    if difficulties:
        scenarios = [s for s in STRESS_TESTS if s.difficulty in difficulties]
    else:
        scenarios = STRESS_TESTS
    
    all_results = {
        "total": len(scenarios),
        "passed": 0,
        "failed": 0,
        "errors": 0,
        "results": [],
    }
    
    for scenario in scenarios:
        result = run_stress_test(scenario, verbose=verbose)
        all_results["results"].append(result)
        
        if result.get("error"):
            all_results["errors"] += 1
        elif result.get("passed"):
            all_results["passed"] += 1
        else:
            all_results["failed"] += 1
    
    # Summary
    if verbose:
        print(f"\n{'='*70}")
        print("STRESS TEST SUMMARY")
        print(f"{'='*70}")
        print(f"Total: {all_results['total']}")
        print(f"✅ Passed: {all_results['passed']}")
        print(f"❌ Failed: {all_results['failed']}")
        print(f"⚠️ Errors: {all_results['errors']}")
        print(f"Pass Rate: {all_results['passed']/all_results['total']*100:.1f}%")
    
    return all_results


# =============================================================================
# INTERACTIVE MODE
# =============================================================================

def interactive_stress_test():
    """
    Run stress tests interactively, showing each email and response.
    """
    print("\n" + "="*70)
    print("IRA STRESS TEST SUITE - INTERACTIVE MODE")
    print("="*70)
    print(f"\nTotal scenarios: {len(STRESS_TESTS)}")
    print("\nDifficulties:")
    for d in Difficulty:
        count = len([s for s in STRESS_TESTS if s.difficulty == d])
        print(f"  - {d.value.upper()}: {count} scenarios")
    
    print("\nOptions:")
    print("  1. Run all tests")
    print("  2. Run EASY tests only")
    print("  3. Run MEDIUM tests only")
    print("  4. Run HARD tests only")
    print("  5. Run NIGHTMARE tests only")
    print("  6. Run specific test by ID")
    print("  7. List all scenarios")
    print("  0. Exit")
    
    while True:
        choice = input("\nEnter choice: ").strip()
        
        if choice == "0":
            break
        elif choice == "1":
            run_all_stress_tests()
        elif choice == "2":
            run_all_stress_tests([Difficulty.EASY])
        elif choice == "3":
            run_all_stress_tests([Difficulty.MEDIUM])
        elif choice == "4":
            run_all_stress_tests([Difficulty.HARD])
        elif choice == "5":
            run_all_stress_tests([Difficulty.NIGHTMARE])
        elif choice == "6":
            test_id = input("Enter test ID (e.g., ST001): ").strip().upper()
            scenario = next((s for s in STRESS_TESTS if s.id == test_id), None)
            if scenario:
                run_stress_test(scenario)
            else:
                print(f"Test {test_id} not found")
        elif choice == "7":
            print("\n" + "-"*70)
            for s in STRESS_TESTS:
                print(f"{s.id}: {s.name} ({s.difficulty.value})")
            print("-"*70)
        else:
            print("Invalid choice")


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Ira Stress Test Suite")
    parser.add_argument("--all", action="store_true", help="Run all tests")
    parser.add_argument("--easy", action="store_true", help="Run easy tests")
    parser.add_argument("--medium", action="store_true", help="Run medium tests")
    parser.add_argument("--hard", action="store_true", help="Run hard tests")
    parser.add_argument("--nightmare", action="store_true", help="Run nightmare tests")
    parser.add_argument("--interactive", "-i", action="store_true", help="Interactive mode")
    parser.add_argument("--id", type=str, help="Run specific test by ID")
    parser.add_argument("--quiet", "-q", action="store_true", help="Quiet mode")
    
    args = parser.parse_args()
    
    if args.interactive:
        interactive_stress_test()
    elif args.id:
        scenario = next((s for s in STRESS_TESTS if s.id == args.id.upper()), None)
        if scenario:
            run_stress_test(scenario, verbose=not args.quiet)
        else:
            print(f"Test {args.id} not found")
    elif args.all:
        run_all_stress_tests(verbose=not args.quiet)
    elif args.easy:
        run_all_stress_tests([Difficulty.EASY], verbose=not args.quiet)
    elif args.medium:
        run_all_stress_tests([Difficulty.MEDIUM], verbose=not args.quiet)
    elif args.hard:
        run_all_stress_tests([Difficulty.HARD], verbose=not args.quiet)
    elif args.nightmare:
        run_all_stress_tests([Difficulty.NIGHTMARE], verbose=not args.quiet)
    else:
        # Default: show interactive menu
        interactive_stress_test()
