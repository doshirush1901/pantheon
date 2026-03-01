#!/usr/bin/env python3
"""
Ingest Maruti Suzuki YFG IMG Machine Case Study (2022)

Documents how Machinecraft built India's first IMG thermoforming machine
in partnership with FRIMO for automotive soft-touch interiors.

Key learnings:
- IMG process flow (thermoforming + lamination + edge folding)
- Cost comparison: localized vs imported
- ROI analysis and breakeven
- Why projects succeed or fail
- FRIMO-Machinecraft partnership model
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from openclaw.agents.ira.src.brain.knowledge_ingestor import KnowledgeIngestor, KnowledgeItem

SOURCE_FILE = "Appendix A_ Case Study – 2022 Feasibility Study for Maruti Suzuki YFG Interior Project (Instrument Panel Mid-Panels).pdf"


def create_knowledge_items() -> list[KnowledgeItem]:
    """Create structured knowledge items from the Maruti IMG case study."""
    items = []

    # 1. Project Overview
    items.append(KnowledgeItem(
        text="""Maruti Suzuki YFG IMG Project - Overview (2022)

PROJECT BACKGROUND:
- Customer: International Automotive Components (IAC) Bangalore
- End OEM: Maruti Suzuki + Toyota (twin model)
- Vehicle: YFG SUV (Urban Cruiser type)
- Part: Instrument Panel (IP) Mid-Panels
- Requirement: Soft-touch, grained surface (premium feel)
- Volume: 160,000 car sets per year
- Production Start: Mid-2024 (planned)
- Program Duration: ~5 years (~800,000 total parts)

WHY SOFT-TOUCH:
- To rival competitors like Hyundai Creta
- Premium interior feel demanded by OEM
- Soft, grained surface vs hard plastic
- Enhanced perceived quality

KEY PLAYERS:
- IAC: Tier-1 automotive interior supplier (customer)
- FRIMO: German tooling/equipment specialist (technology partner)
- Machinecraft: Indian machine builder (local manufacturing partner)
- Kolon Korea: TPO foil supplier

PROJECT SIGNIFICANCE:
- First IMG thermoforming machine built in India
- Test case for FRIMO-Machinecraft partnership
- Proof of concept for localized premium manufacturing
- Template for future automotive interior projects

OUTCOME:
- Prototype machine built successfully
- 100 sample parts produced
- Project paused due to OEM indecision
- Lessons learned for future opportunities""",
        knowledge_type="case_study",
        source_file=SOURCE_FILE,
        entity="Maruti YFG IMG Project",
        summary="YFG project: 160k/yr IP mid-panels for Maruti/Toyota, first India IMG machine, FRIMO+Machinecraft",
        metadata={
            "topic": "project_overview",
            "customer": "IAC",
            "oem": "Maruti Suzuki",
            "volume_per_year": 160000,
            "part": "IP mid-panel"
        }
    ))

    # 2. IMG Process Flow
    items.append(KnowledgeItem(
        text="""IMG (In-Mold Graining) Process Flow Explained

WHAT IS IMG:
IMG = In-Mold Graining
Creates premium soft-touch automotive interior parts
Three sequential steps to achieve "luxury soft-touch"

STEP 1: IMG THERMOFORMING (Skin Formation)
- Material: Thin TPO (Thermoplastic Olefin) foil
- Process: Heated and vacuum formed
- Tooling: Precision nickel-shell tool
- Result: Contoured skin with "perfect grain" surface
- Key: Nickel shell imparts the grain texture directly

How it works:
1. Flat decorative foil (TPO with color and grain)
2. Heated to forming temperature
3. Vacuum formed into shape
4. Nickel tool transfers grain pattern to skin

STEP 2: PRESS LAMINATION (Bonding)
- Pre-formed skin placed with injection-molded substrate
- Substrate: Rigid plastic structure of the mid-panel
- Adhesive layer (hotmelt) activated
- Heat + pressure bonds skin to substrate uniformly
- Result: Soft, padded appearance

STEP 3: EDGE FOLDING (Finishing)
- Excess skin material at edges
- Wrapped around to backside
- Glued down for clean seams
- Uses specialized tooling sliders
- Heat-sealed without wrinkles
- Result: No visible cut edges, high-quality finish

COMBINED RESULT:
- Premium grained surface
- Cushioned feel
- Invisible seams
- Meets OEM design intent for premium interiors

EQUIPMENT USED:
- Single-station IMG thermoforming press
- Integrated: heating + vacuum forming + press lamination
- Edge folding via tooling attachments
- All in one machine cycle""",
        knowledge_type="process",
        source_file=SOURCE_FILE,
        entity="IMG Process",
        summary="IMG process: TPO skin thermoforming (nickel grain) → press lamination → edge folding = premium interior",
        metadata={
            "topic": "img_process",
            "steps": ["thermoforming", "lamination", "edge_folding"],
            "material": "TPO foil",
            "tooling": "nickel_shell"
        }
    ))

    # 3. Equipment Options Evaluated
    items.append(KnowledgeItem(
        text="""Equipment Options Evaluated for YFG Project

OPTION 1: RE-USE OLD KIEFEL PRESS (Mumbai)

Concept:
- IAC had existing Kiefel laminating press in Mumbai
- Repurpose with new tooling for YFG

Advantages:
- Lower capital investment (machine already owned)
- Near-zero new machine cost

Disadvantages:
- Legacy press, limited automation
- Not designed for IMG vacuum forming
- Skin forming would be sub-optimal (manual or slow)
- Mumbai to Bangalore logistics (900 km transport)
- Longer cycle times, less consistency
- Higher scrap risk
- Finding spare parts difficult
- Maintenance issues

OPTION 2: NEW FRIMO/MACHINECRAFT IMG MACHINE (Bangalore)

Concept:
- New integrated IMG thermoforming + laminating system
- Built locally by Machinecraft with FRIMO design
- Installed at/near IAC Bangalore plant

Advantages:
- Purpose-built for part geometry
- Optimal cycle time and quality
- Just-in-time production for OEM
- No inter-city transport
- Modern automation and controls
- State-of-the-art capability
- Local support from Machinecraft

Disadvantages:
- Higher initial investment (~€250k)
- New capital expenditure required

LOCALIZATION STRATEGY:
- Machine frame and basic components: Machinecraft India
- Process know-how and critical components: FRIMO Germany
- Cost: ~40% lower than full European import
- FRIMO-Machinecraft collaboration enabled this

DECISION FACTORS:
- Operational cost over program life
- Quality consistency requirements
- Logistics complexity
- Long-term efficiency
- Volume commitment confidence""",
        knowledge_type="case_study",
        source_file=SOURCE_FILE,
        entity="Equipment Options",
        summary="Option 1: reuse old Kiefel (low cost, high risk); Option 2: new FRIMO/Machinecraft (€250k, optimal)",
        metadata={
            "topic": "equipment_options",
            "options": ["Kiefel reuse", "New FRIMO/Machinecraft"],
            "chosen_approach": "New localized machine"
        }
    ))

    # 4. FRIMO Machine Specifications
    items.append(KnowledgeItem(
        text="""FRIMO IMG Machine Specifications (as quoted for YFG)

MACHINE TYPE:
- Single-station IMG thermoforming and laminating system
- Based on FRIMO EcoForm/IMG technology
- Dual function: vacuum forming + press lamination

TECHNICAL SPECIFICATIONS:
- Clamping Force: ~15 tons
- Heating: Infrared heating oven integrated
- Vacuum: Vacuum forming capability for TPO foil
- Drive: Servo-driven, electrically actuated press
- Tables: Double-table movement (shuttle system)
- Automation: Automatic foil feed from roll

PROCESS CAPABILITY:
- Deep-draw forming of skin
- Press lamination in same station
- Edge folding via tooling provisions
- All in one machine, one station

TOOLING:
- Precision nickel-shell IMG forming tool
- Grain pattern transferred from nickel shell
- Matching press lamination tool for substrate
- Edge-fold sliders integrated
- Nickel shell imported (Galvanoform or KTX)
- Tool assembly done in India

PERFORMANCE:
- Cycle Time: <2 minutes per part
- Output: ~30 parts/hour
- Capacity: 160k/year volume with shifts + buffer

AUTOMATION FEATURES:
- Automatic foil feed and cut unit
- Integrated PLC controls
- Recipe settings for heating profiles
- Pre-blow/vacuum for foil
- Time-Shifted Heat Control (FRIMO tech)
- HMI interface for quick changeovers

ANCILLARY:
- Safety enclosures
- Quick tool change capability
- Compact footprint (single-station press size)

QUOTED PRICE:
- €250,000 ex-works India (localized build)
- Compare: €400k+ for European import
- Savings: ~40% through local manufacturing""",
        knowledge_type="machine_spec",
        source_file=SOURCE_FILE,
        entity="FRIMO IMG Machine",
        summary="FRIMO IMG: 15-ton press, servo, <2min cycle, €250k localized (vs €400k import)",
        metadata={
            "topic": "frimo_specs",
            "clamping_tons": 15,
            "cycle_time_min": 2,
            "price_eur": 250000,
            "import_price_eur": 400000
        }
    ))

    # 5. Cost Comparison & ROI Analysis
    items.append(KnowledgeItem(
        text="""Cost Comparison & ROI Analysis - YFG Project

TOOLING COSTS (Similar for both options):
- IMG forming tool (nickel shell + structure)
- Lamination/edgefold tool
- Estimate: €200k-€250k (hybrid local/import)
- Full import would be €300k-€350k

MACHINE CAPITAL COST:
| Option | Machine Cost |
|--------|--------------|
| Option 1 (Kiefel reuse) | ~€0 (existing asset) |
| Option 2 (New FRIMO) | €250,000 |
| Full import (comparison) | €400,000+ |

OPERATIONAL COSTS COMPARISON:

Factor | Option 1 (Old) | Option 2 (New)
-------|----------------|---------------
Cycle Time | Longer | ~2 min
Labor | More manual | 1 operator
Scrap Rate | Higher risk | Lower, consistent
Logistics | €0.50/part transport | None (on-site)
Maintenance | Higher (old machine) | Lower (warranty)

PER-PART COST AT FULL VOLUME:
- Option 1: ~€0.85 per part
- Option 2: ~€0.70 per part
- Savings: 15-18% with new machine

BREAKEVEN ANALYSIS:
- Crossover point: ~500,000 parts
- Program total: ~800,000 parts (5 years)
- Payback period: 2.5-3 years at 160k/yr

ROI METRICS:
- IRR: Above hurdle rate (attractive)
- Simple payback: 2.5-3 years
- After payback: Every part saves money
- 5-year total savings: 15-20% vs Option 1

VOLUME SENSITIVITY:
- Full volume (800k): Strong ROI
- Low volume: ROI diminishes
- Program cancellation: Stranded capital risk

FINANCIAL MODELS PROPOSED:
- Machine lease/rental option
- Pay per part model
- Lower upfront burden
- Align costs with actual production
- Protect against volume shortfall""",
        knowledge_type="commercial",
        source_file=SOURCE_FILE,
        entity="YFG ROI Analysis",
        summary="ROI: €0.70 vs €0.85/part, breakeven ~500k parts (3 yrs), 15-18% savings with new machine",
        metadata={
            "topic": "roi_analysis",
            "breakeven_parts": 500000,
            "payback_years": 3,
            "cost_savings_percent": "15-18"
        }
    ))

    # 6. What Stopped the Project
    items.append(KnowledgeItem(
        text="""Why the YFG Project Did Not Proceed to Mass Production

FACTOR 1: OEM DECISION CHANGES
- Maruti/Toyota delayed commitment to soft-skin mid-panel
- Cost pressures from OEM
- Supply chain risk concerns
- Considered reverting to hard plastic panel
- OEM dropped/postponed soft IP insert plan
- IAC couldn't invest without OEM firm commitment

FACTOR 2: COST VS BUDGET GAP
- Target price extremely aggressive (~half of import)
- Even with localization, at upper limit of IAC budget
- ROI not convincing without volume guarantee
- Perceived as high risk (new process for IAC)
- Management hesitant to approve capital expenditure

FACTOR 3: SUPPORT AND TIMING CONCERNS
- OEM SOP looming (mid-2024)
- Equipment needed by late 2022
- FRIMO Germany team stretched thin globally
- Limited bandwidth for India support
- No established local FRIMO engineering presence
- IAC needed fast reassurance and on-ground support
- Delays in finalizing proposals
- Momentum lost by late 2022

FACTOR 4: PARTNERSHIP STRUCTURE UNCLEAR
- FRIMO-Machinecraft roles not firmly structured
- Responsibilities for execution unclear
- Partnership entered limbo period

WHAT DID HAPPEN:
- Prototype IMG machine was built by Machinecraft
- Delivered to IAC/Lumax for trials
- 100 trial parts made successfully
- Proved technical concept
- But: Development prototype, not fully productionized
- No series order placed

LESSONS FOR FUTURE:
1. Need firm OEM commitment before investing
2. Need local engineering presence for confidence
3. Need clear partnership structure
4. Need flexible financing models
5. Need faster proposal turnaround""",
        knowledge_type="case_study",
        source_file=SOURCE_FILE,
        entity="YFG Project Failure Analysis",
        summary="Project paused: OEM indecision, cost gap, no local FRIMO support, unclear partnership",
        metadata={
            "topic": "failure_analysis",
            "reasons": ["OEM indecision", "cost gap", "support concerns", "partnership unclear"],
            "outcome": "prototype_only"
        }
    ))

    # 7. Lessons Learned & Future Implications
    items.append(KnowledgeItem(
        text="""Lessons Learned & Future Pipeline Implications

VALIDATED DEMAND:
- Major Indian OEMs want soft-touch premium interiors
- Maruti/Toyota, Tata, Mahindra, Hyundai all interested
- YFG was near miss, but demand is growing
- Other programs: Tata Harrier, Nexon face-lifts
- Trend: Stitched or wrapped panels increasing

KEY TAKEAWAYS FOR FRIMO:
1. Need stronger local footprint in India
2. World-class tech available, but customers need:
   - Rapid, local response
   - Lower-cost structure
3. Result: Plan for dedicated FRIMO India engineering team (2025)
4. Local pre-engineering = faster RFQ turnaround
5. "Make in India" vision: tools + machines locally

MACHINECRAFT PARTNERSHIP VALIDATED:
- Delivered complex IMG press in 4 months
- Cost: ~€250,000 (vs €400k+ import)
- Remarkable achievement
- Proved localization model works
- Future: Machinecraft as official build partner
- Clear structure: FRIMO design/quality, Machinecraft fabrication

COMMERCIAL APPROACH LESSONS:
- Innovative models needed: leasing, per-part pricing
- Flexible financing helps win orders
- Align costs with customer's financial comfort
- Phased tool payments option

IAC PERSPECTIVE:
- Interest in soft-trim hasn't disappeared
- YFG feasibility data = baseline for future RFQs
- Aware of what it takes to implement process
- Ready when next opportunity arises

THE "PILOT" VALUE:
- YFG tested the waters for India interior trim market
- Technical, financial, and cultural knowledge gained
- "Groundwork is done, risk is lower, upside is higher"
- Next similar RFQ: FRIMO + Machinecraft will be ready

PROTOTYPE MACHINE IMPACT:
- India's first IMG thermoforming press exists
- Built by Machinecraft with FRIMO guidance
- Proved concept with 100 sample parts
- Foundation for future projects
- Demonstrated Machinecraft capability""",
        knowledge_type="case_study",
        source_file=SOURCE_FILE,
        entity="IMG Project Lessons",
        summary="Lessons: need local presence, validated Machinecraft partnership, demand is real, ready for next RFQ",
        metadata={
            "topic": "lessons_learned",
            "key_learnings": ["local_presence", "partnership_validated", "demand_exists", "flexible_financing"]
        }
    ))

    # 8. IMG Machine as Machinecraft Product
    items.append(KnowledgeItem(
        text="""IMG Machine - Machinecraft Product Line Addition

ORIGIN STORY:
- First IMG machine built for Maruti Suzuki YFG project (2022)
- Partnership with FRIMO Germany
- Proof of concept: 100 sample parts produced
- Capability established for automotive interiors

WHAT IMG MACHINE DOES:
- In-Mold Graining thermoforming
- Creates premium soft-touch automotive parts
- Combines: heating + vacuum forming + press lamination
- Optional: integrated edge folding

TARGET APPLICATIONS:
- Instrument panel (IP) mid-panels
- Door trim panels
- Console covers
- Any soft-touch interior component
- Premium automotive interiors

TARGET CUSTOMERS:
- Automotive Tier-1 suppliers (IAC, Lumax, etc.)
- OEM-direct in some cases
- Companies serving: Maruti, Toyota, Tata, Mahindra, Hyundai

COMPETITIVE ADVANTAGE:
- Localized build: 40% cost savings vs European import
- €250k vs €400k+ for equivalent capability
- 4-month delivery possible
- Local support from Machinecraft
- FRIMO technology heritage

MARKET OPPORTUNITY:
- Growing demand for soft interiors in India
- Premium SUV segment expanding
- EV interiors increasingly premium
- OEMs differentiating on interior quality

PRICING REFERENCE:
- IMG machine (YFG spec): ~€250,000 (~₹2.3 Cr)
- Tooling (nickel shell + lamination): €200-250k additional
- Total project investment: ~€450-500k

RELATIONSHIP TO PF1:
- IMG is specialized version of PF1-type machine
- Same base platform capabilities
- Added: higher press force (15+ tons)
- Added: lamination capability
- Added: precision nickel tooling interface
- Added: edge folding provisions

FUTURE DEVELOPMENT:
- FRIMO-Machinecraft partnership formalized
- Local engineering support planned
- Ready for next automotive interior RFQ
- Pipeline includes multiple OEM programs""",
        knowledge_type="machine_spec",
        source_file=SOURCE_FILE,
        entity="Machinecraft IMG Machine",
        summary="IMG machine: €250k (40% less than import), soft-touch auto interiors, FRIMO partnership",
        metadata={
            "topic": "img_product",
            "price_eur": 250000,
            "applications": "automotive_interiors",
            "partnership": "FRIMO"
        }
    ))

    return items


def main():
    """Main ingestion function."""
    print("=" * 60)
    print("Maruti Suzuki YFG IMG Case Study Ingestion")
    print("Source: " + SOURCE_FILE)
    print("=" * 60)

    items = create_knowledge_items()

    print(f"\nCreated {len(items)} knowledge items:")
    for i, item in enumerate(items, 1):
        print(f"  {i}. [{item.knowledge_type}] {item.summary[:55]}...")

    ingestor = KnowledgeIngestor()
    results = ingestor.ingest_batch(items)

    print("\n" + "=" * 60)
    print("INGESTION COMPLETE")
    print("=" * 60)

    return results


if __name__ == "__main__":
    main()
