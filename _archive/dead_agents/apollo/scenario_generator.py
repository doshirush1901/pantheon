#!/usr/bin/env python3
"""
Algorithmic customer simulation scenario generator for training Ira.

Generates unique, never-repeating multi-turn sales conversations
that exercise each machine series with realistic customer personas,
industry contexts, and technical requirements.
"""

import hashlib
import json
import random
import uuid
from pathlib import Path
from typing import Dict, List, Optional

PROJECT_ROOT = Path(__file__).parent.parent.parent

import sys
sys.path.insert(0, str(PROJECT_ROOT))

from openclaw.agents.ira.src.brain.machine_database import MACHINE_SPECS

# =============================================================================
# REFERENCE DATA
# =============================================================================

INDUSTRIES = [
    # Automotive & transport
    "Automotive interior trim", "Automotive exterior panels", "EV battery enclosures",
    "Motorcycle fairings", "Truck bedliners", "Bus interior panels",
    "Railway seat backs", "Tractor fenders", "Recreational vehicle panels",
    "Electric scooter body panels",
    # Aerospace & defense
    "Aerospace cabin interiors", "Drone housings", "Military equipment cases",
    # Sanitary & bath
    "Bathtub manufacturing", "Shower tray production", "Spa shell forming",
    "Hot tub covers", "Washbasin production",
    # Packaging
    "Food tray packaging", "Blister packaging", "Clamshell packaging",
    "Medical device packaging", "Electronics blister packs", "Cosmetics packaging",
    "Fruit punnet production", "Dairy cup forming", "Ready-meal trays",
    # Industrial
    "Industrial equipment housings", "Machine guards and covers",
    "Electrical enclosures", "Rooftop HVAC covers", "Solar panel backsheets",
    "Refrigerator liners", "Vending machine panels",
    # Consumer goods
    "Luggage shell forming", "Sporting goods", "Playground equipment",
    "Point-of-sale displays", "Signage and lettering",
    # Medical
    "Medical device housings", "Prosthetic shells", "Hospital bed panels",
    # Agriculture
    "Agricultural equipment covers", "Greenhouse panels", "Seed trays",
]

COUNTRIES = [
    {"name": "India", "currency": "INR", "city": "Mumbai"},
    {"name": "India", "currency": "INR", "city": "Pune"},
    {"name": "India", "currency": "INR", "city": "Chennai"},
    {"name": "India", "currency": "INR", "city": "Ahmedabad"},
    {"name": "Germany", "currency": "EUR", "city": "Stuttgart"},
    {"name": "Germany", "currency": "EUR", "city": "Munich"},
    {"name": "United States", "currency": "USD", "city": "Detroit"},
    {"name": "United States", "currency": "USD", "city": "Houston"},
    {"name": "United States", "currency": "USD", "city": "Chicago"},
    {"name": "Mexico", "currency": "MXN", "city": "Querétaro"},
    {"name": "Mexico", "currency": "MXN", "city": "Monterrey"},
    {"name": "Brazil", "currency": "BRL", "city": "São Paulo"},
    {"name": "Turkey", "currency": "TRY", "city": "Istanbul"},
    {"name": "Turkey", "currency": "TRY", "city": "Bursa"},
    {"name": "United Kingdom", "currency": "GBP", "city": "Birmingham"},
    {"name": "Italy", "currency": "EUR", "city": "Turin"},
    {"name": "France", "currency": "EUR", "city": "Lyon"},
    {"name": "Spain", "currency": "EUR", "city": "Barcelona"},
    {"name": "Poland", "currency": "PLN", "city": "Wrocław"},
    {"name": "Czech Republic", "currency": "CZK", "city": "Brno"},
    {"name": "Japan", "currency": "JPY", "city": "Nagoya"},
    {"name": "South Korea", "currency": "KRW", "city": "Ulsan"},
    {"name": "China", "currency": "CNY", "city": "Shenzhen"},
    {"name": "Thailand", "currency": "THB", "city": "Bangkok"},
    {"name": "Vietnam", "currency": "VND", "city": "Ho Chi Minh City"},
    {"name": "Indonesia", "currency": "IDR", "city": "Jakarta"},
    {"name": "South Africa", "currency": "ZAR", "city": "Johannesburg"},
    {"name": "Egypt", "currency": "EGP", "city": "Cairo"},
    {"name": "UAE", "currency": "AED", "city": "Dubai"},
    {"name": "Saudi Arabia", "currency": "SAR", "city": "Riyadh"},
    {"name": "Australia", "currency": "AUD", "city": "Melbourne"},
    {"name": "Canada", "currency": "CAD", "city": "Toronto"},
    {"name": "Argentina", "currency": "ARS", "city": "Buenos Aires"},
    {"name": "Colombia", "currency": "COP", "city": "Bogotá"},
]

FIRST_NAMES = [
    "Rajesh", "Priya", "Amit", "Sunita", "Vikram", "Ananya", "Sanjay", "Deepa",
    "Arjun", "Kavitha", "Rahul", "Meera", "Suresh", "Lakshmi", "Anil", "Pooja",
    "James", "Sarah", "Michael", "Emily", "Robert", "Jennifer", "David", "Lisa",
    "Hans", "Claudia", "Stefan", "Monika", "Friedrich", "Ingrid",
    "Carlos", "Maria", "Diego", "Isabella", "Fernando", "Lucia",
    "Kenji", "Yuki", "Takeshi", "Akiko", "Hiroshi", "Sakura",
    "Ahmed", "Fatima", "Omar", "Layla", "Hassan", "Nour",
    "Pierre", "Sophie", "Luca", "Giulia", "Piotr", "Katarzyna",
    "Vignesh", "Aleksandr", "Yogesh", "Chen", "Wei", "Min-Jun",
]

LAST_NAMES = [
    "Sharma", "Patel", "Gupta", "Singh", "Kumar", "Reddy", "Nair", "Iyer",
    "Deshmukh", "Joshi", "Mehta", "Shah", "Verma", "Rao", "Pillai", "Menon",
    "Smith", "Johnson", "Williams", "Brown", "Davis", "Wilson", "Anderson", "Taylor",
    "Müller", "Schmidt", "Weber", "Fischer", "Becker", "Hoffmann",
    "García", "Rodríguez", "Martínez", "López", "Hernández", "Fernández",
    "Tanaka", "Suzuki", "Watanabe", "Yamamoto", "Nakamura", "Kobayashi",
    "Al-Rashid", "El-Sayed", "Okafor", "Van der Berg", "Petrov", "Kowalski",
    "Dubois", "Rossi", "Johansson", "Novak", "Kim", "Park",
]

ROLES = [
    "Production Manager", "Plant Manager", "VP of Manufacturing",
    "Procurement Head", "Technical Director", "Chief Engineer",
    "Operations Director", "Managing Director", "CEO",
    "Business Development Manager", "R&D Manager", "Quality Manager",
    "Supply Chain Director",
]

COMPANY_SUFFIXES = [
    "Industries", "Manufacturing", "Plastics", "Polymers", "Technologies",
    "Engineering", "Solutions", "Corp", "Ltd", "GmbH", "Pvt Ltd",
    "Group", "International", "Systems",
]

# =============================================================================
# SERIES TRIGGERS — keywords, thickness ranges, and materials per series
# =============================================================================

SERIES_TRIGGERS: Dict[str, dict] = {
    "PF1": {
        "keywords": [
            "closed chamber", "sag control", "automotive", "luggage",
            "servo driven", "truck bedliner", "enclosure", "tractor fender",
            "EV battery cover", "bus interior", "railway panel", "refrigerator liner",
            "single sheet", "thick gauge", "deep draw",
        ],
        "thickness_range": (1.0, 10.0),
        "materials": ["ABS", "PMMA", "PC", "HIPS", "HDPE", "PP"],
    },
    "PF2": {
        "keywords": [
            "bathtub", "spa", "shower tray", "negative cavity", "gravity sag",
            "open frame", "hot tub", "washbasin", "large signage",
            "architectural panel", "exhibition display", "pool cover",
        ],
        "thickness_range": (3.0, 10.0),
        "materials": ["Acrylic", "PMMA", "ABS"],
    },
    "AM": {
        "keywords": [
            "thin gauge", "packaging", "food tray", "blister", "roll-fed",
            "clamshell", "high volume", "disposable", "fruit punnet",
            "dairy cup", "cosmetics tray", "electronics blister",
        ],
        "thickness_range": (0.2, 1.5),
        "materials": ["PET", "HIPS", "PP", "PVC", "PETG"],
    },
    "IMG": {
        "keywords": [
            "grain retention", "in-mold graining", "Class-A surface",
            "TPO lamination", "automotive interior", "soft-touch finish",
            "dashboard", "door panel", "armrest", "console cover",
        ],
        "thickness_range": (2.0, 5.0),
        "materials": ["TPO", "PP"],
    },
}

# Industries that naturally align with each series
SERIES_INDUSTRY_MAP: Dict[str, List[str]] = {
    "PF1": [
        "Automotive interior trim", "Automotive exterior panels", "EV battery enclosures",
        "Truck bedliners", "Bus interior panels", "Railway seat backs",
        "Tractor fenders", "Luggage shell forming", "Industrial equipment housings",
        "Machine guards and covers", "Electrical enclosures", "Refrigerator liners",
        "Recreational vehicle panels", "Electric scooter body panels",
        "Motorcycle fairings", "Vending machine panels",
    ],
    "PF2": [
        "Bathtub manufacturing", "Shower tray production", "Spa shell forming",
        "Hot tub covers", "Washbasin production", "Point-of-sale displays",
        "Signage and lettering", "Playground equipment",
    ],
    "AM": [
        "Food tray packaging", "Blister packaging", "Clamshell packaging",
        "Medical device packaging", "Electronics blister packs", "Cosmetics packaging",
        "Fruit punnet production", "Dairy cup forming", "Ready-meal trays",
        "Seed trays",
    ],
    "IMG": [
        "Automotive interior trim", "Automotive exterior panels",
        "Hospital bed panels", "Sporting goods",
    ],
}

# Series selection weights (PF1 is most common)
SERIES_WEIGHTS = {"PF1": 40, "PF2": 20, "AM": 25, "IMG": 15}

# =============================================================================
# CONVERSATION TEMPLATES — per-series turn-2 detail generators
# =============================================================================

def _pf1_turn2(material: str, thickness: float, industry: str) -> str:
    details = random.choice([
        f"We need a closed-chamber machine with sag control for {thickness}mm {material}.",
        f"The parts require servo-driven forming — {thickness}mm {material} sheets, deep draw.",
        f"We're looking at {thickness}mm {material}. Need precise sag control and zone heating.",
        f"It's {thickness}mm {material}, single-sheet fed. Closed chamber is a must for us.",
    ])
    extras = random.choice([
        "We also need plug assist capability and automatic sheet loading.",
        "Zone heating control is important — the parts have varying draw depths.",
        "Cycle time matters; we're targeting 90-second cycles with cooling fans.",
        "We'd want ball-transfer tool change for quick mold swaps.",
    ])
    return f"{details} {extras}"


def _pf2_turn2(material: str, thickness: float, industry: str) -> str:
    details = random.choice([
        f"We use female cavity molds — gravity sag forming with {thickness}mm {material}.",
        f"The process relies on gravity sag into negative cavities, {thickness}mm {material}.",
        f"It's {thickness}mm {material} with deep negative-cavity tooling, gravity sag method.",
        f"We need open-frame access for large {material} parts, {thickness}mm thick.",
    ])
    extras = random.choice([
        "No automation needed — manual load/unload is fine for our volumes.",
        "We don't need roll-fed or automation, just reliable open-frame forming.",
        "Simple operation is key; our operators handle loading manually.",
        "We prefer the open design for easy part removal on these large shapes.",
    ])
    return f"{details} {extras}"


def _am_turn2(material: str, thickness: float, industry: str) -> str:
    details = random.choice([
        f"It's thin gauge — {thickness}mm {material}, roll-fed continuous production.",
        f"We run {thickness}mm {material} from rolls, high-volume inline forming.",
        f"Thin gauge {material} at {thickness}mm, roll-fed. We need fast cycle times.",
        f"The material is {thickness}mm {material} on rolls — blister/tray forming.",
    ])
    extras = random.choice([
        "Volume is critical — we need thousands of parts per shift.",
        "We're looking at multi-cavity tooling for maximum throughput.",
        "Inline trimming or a press station would be a big plus.",
        "We need servo chain indexing for precise registration.",
    ])
    return f"{details} {extras}"


def _img_turn2(material: str, thickness: float, industry: str) -> str:
    details = random.choice([
        f"We need Class-A surface finish with grain retention on {thickness}mm {material}.",
        f"It's in-mold graining — {thickness}mm {material}, soft-touch finish required.",
        f"The spec calls for grain transfer onto {thickness}mm {material} with vacuum lamination.",
        f"We're doing TPO lamination at {thickness}mm — grain retention is non-negotiable.",
    ])
    extras = random.choice([
        "The OEM requires Class-A surface on every part — no visible defects.",
        "Precision temperature zones are essential for consistent grain transfer.",
        "We supply Tier-1 automotive — the finish must meet OEM grain standards.",
        "Hot-melt compatibility and servo positioning are on our requirements list.",
    ])
    return f"{details} {extras}"


_TURN2_GENERATORS = {
    "PF1": _pf1_turn2,
    "PF2": _pf2_turn2,
    "AM": _am_turn2,
    "IMG": _img_turn2,
}

# =============================================================================
# USED-SCENARIO TRACKING
# =============================================================================

USED_SCENARIOS_FILE = PROJECT_ROOT / "data" / "training" / "used_scenarios.json"


def _load_used_hashes() -> set:
    if USED_SCENARIOS_FILE.exists():
        try:
            data = json.loads(USED_SCENARIOS_FILE.read_text())
            return set(data.get("hashes", []))
        except (json.JSONDecodeError, KeyError):
            return set()
    return set()


def _save_used_hashes(hashes: set) -> None:
    USED_SCENARIOS_FILE.parent.mkdir(parents=True, exist_ok=True)
    USED_SCENARIOS_FILE.write_text(json.dumps({
        "count": len(hashes),
        "hashes": sorted(hashes),
    }, indent=2))


def _scenario_hash(customer_name: str, industry: str, series: str, material: str, thickness: float) -> str:
    blob = f"{customer_name}|{industry}|{series}|{material}|{thickness}"
    return hashlib.sha256(blob.encode()).hexdigest()[:16]

# =============================================================================
# HELPERS
# =============================================================================

def _pick_weighted_series() -> str:
    population = list(SERIES_WEIGHTS.keys())
    weights = list(SERIES_WEIGHTS.values())
    return random.choices(population, weights=weights, k=1)[0]


def _random_company(last_name: str, country_name: str) -> str:
    style = random.choice(["surname", "geo", "brand"])
    suffix = random.choice(COMPANY_SUFFIXES)
    if style == "surname":
        return f"{last_name} {suffix}"
    if style == "geo":
        return f"{country_name} Thermoform {suffix}"
    word = random.choice(["Nova", "Apex", "Prime", "Vertex", "Zenith", "Atlas", "Titan"])
    return f"{word} {suffix}"


def _pick_machine_for_series(series: str) -> Optional[str]:
    candidates = [m for m in MACHINE_SPECS.values() if m.series == series]
    if not candidates:
        return None
    return random.choice(candidates).model

# =============================================================================
# MAIN GENERATOR
# =============================================================================

def generate_unique_scenarios(count: int = 10) -> List[Dict]:
    """
    Generate *count* unique customer simulation scenarios.

    Each scenario is a 3-turn sales conversation with a realistic customer
    persona, industry context, and technical requirements that should lead
    Ira to recommend the correct machine series.

    Returns a list of scenario dicts.
    """
    used_hashes = _load_used_hashes()
    scenarios: List[Dict] = []
    attempts = 0
    max_attempts = count * 20

    while len(scenarios) < count and attempts < max_attempts:
        attempts += 1

        series = _pick_weighted_series()
        trigger = SERIES_TRIGGERS[series]

        industry = random.choice(SERIES_INDUSTRY_MAP[series])
        country = random.choice(COUNTRIES)
        first = random.choice(FIRST_NAMES)
        last = random.choice(LAST_NAMES)
        role = random.choice(ROLES)
        material = random.choice(trigger["materials"])
        lo, hi = trigger["thickness_range"]
        thickness = round(random.uniform(lo, hi), 1)

        h = _scenario_hash(f"{first} {last}", industry, series, material, thickness)
        if h in used_hashes:
            continue

        company = _random_company(last, country["name"])
        machine_model = _pick_machine_for_series(series)

        # --- Turn 1: introduction + high-level need ---
        greetings = random.choice(["Hi", "Hello", "Hey there", "Good morning"])
        turn1 = (
            f"{greetings}, I'm {first} {last}, {role} at {company} "
            f"based in {country['city']}, {country['name']}. "
            f"We're in {industry.lower()} and looking for a thermoforming machine. "
            f"Can you help?"
        )

        # --- Turn 2: technical details (series-specific) ---
        turn2_gen = _TURN2_GENERATORS[series]
        turn2 = turn2_gen(material, thickness, industry)

        # --- Turn 3: ask for full specs + pricing ---
        turn3_variants = [
            f"Sounds promising. Can you send me the full specs and pricing in {country['currency']}?",
            f"Great. Please share detailed specifications and a budgetary quote in {country['currency']}.",
            f"That works. I'd like the complete technical datasheet and pricing ({country['currency']}) please.",
            f"Perfect. Could you put together a formal quotation with full specs? We budget in {country['currency']}.",
        ]
        turn3 = random.choice(turn3_variants)

        scenario = {
            "id": str(uuid.uuid4()),
            "title": f"{industry} — {company} ({country['name']})",
            "customer": {
                "name": f"{first} {last}",
                "company": company,
                "role": role,
                "country": country["name"],
                "city": country["city"],
                "currency": country["currency"],
            },
            "turns": [
                {"role": "customer", "content": turn1},
                {"role": "customer", "content": turn2},
                {"role": "customer", "content": turn3},
            ],
            "expected_machine_series": series,
            "expected_machine_model": machine_model,
            "expected_outcome": (
                f"Ira should recommend a {series}-series machine "
                f"(e.g. {machine_model}) suitable for {thickness}mm {material} "
                f"in {industry.lower()}, and provide specs + pricing in {country['currency']}."
            ),
        }

        used_hashes.add(h)
        scenarios.append(scenario)

    _save_used_hashes(used_hashes)
    return scenarios


# =============================================================================
# CLI
# =============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate training scenarios for Ira")
    parser.add_argument("-n", "--count", type=int, default=10, help="Number of scenarios")
    parser.add_argument("--dump", action="store_true", help="Pretty-print to stdout")
    args = parser.parse_args()

    results = generate_unique_scenarios(count=args.count)

    if args.dump:
        print(json.dumps(results, indent=2))
    else:
        for s in results:
            print(f"[{s['expected_machine_series']}] {s['title']}")
            for t in s["turns"]:
                print(f"  {t['role']}: {t['content'][:120]}...")
            print()

    print(f"\nGenerated {len(results)} unique scenarios.")
