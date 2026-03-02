#!/usr/bin/env python3
"""
Ingest Dezet Story - EU Sales Strategy

Case study of how Machinecraft sells in Europe:
- Target: Companies with aging machines (1980s-2000s)
- Value prop: Swap-in upgrade with 40% output increase
- Process: Week-Zero Audit, trade-in, 72-hour install
- Customer: Dezet (Netherlands) - replaced 42-year-old Illig

Key insights:
- €150,000 investment for PF1-X-1210
- 40% throughput increase
- 20-25% energy savings
- CE-ready machines
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from openclaw.agents.ira.src.brain.knowledge_ingestor import KnowledgeIngestor, KnowledgeItem

SOURCE_FILE = "Dezet Story (1).pdf"


def create_knowledge_items() -> list[KnowledgeItem]:
    """Create structured knowledge items from the Dezet EU sales story."""
    items = []

    # 1. Dezet Customer Profile
    items.append(KnowledgeItem(
        text="""Dezet - European Customer Profile (Netherlands)

COMPANY: Dezet
LOCATION: South Holland, Netherlands
TYPE: Family-owned thermoforming company
EXPERIENCE: 40+ years in thermoforming
VALUES: Dutch principles - precision, reliability, quality
PHILOSOPHY: "Quality over quantity, relationships over transactions"

PRODUCTS THEY MAKE:
- Components for elderly mobility vehicles
- Precision parts for aircraft training simulators
- First aid ECR kit boxes
- Specialized industrial components

THEIR OLD MACHINE:
- Brand: Illig (German)
- Year: 1983
- Service life: 42 years
- Status: Retired in 2025
- Issues before retirement:
  * Maintenance visits more frequent
  * Downtime creeping into schedule
  * Manual sheet loading = bottleneck
  * Not keeping up with modern demands

WHY THEY UPGRADED:
- Aging infrastructure couldn't keep pace
- Manual processes becoming competitive disadvantage
- Need for automation
- Chose progress over status quo

WHAT THEY BOUGHT:
- Machine: Machinecraft PF1-X-1210
- Year: 2025
- Investment: €150,000""",
        knowledge_type="customer_story",
        source_file=SOURCE_FILE,
        entity="Dezet",
        summary="Dezet (Netherlands): 40+ yr thermoformer, replaced 1983 Illig with PF1-X-1210, precision parts",
        metadata={
            "topic": "customer_profile",
            "customer": "Dezet",
            "location": "Netherlands",
            "old_machine": "Illig 1983",
            "new_machine": "PF1-X-1210"
        }
    ))

    # 2. Results & Transformation
    items.append(KnowledgeItem(
        text="""Dezet Transformation Results - PF1-X-1210

BEFORE (1983 Illig):
- Output: 14-16 sheets/hour
- Drive: Mechanical components
- Heating: Older technology
- Control: Limited
- Maintenance: Frequent issues
- Sheet loading: Manual

AFTER (PF1-X-1210):
- Output: 20-22 sheets/hour
- Drive: Fully servo-driven
- Heating: Dual-sided IR Quartz
- Control: Mitsubishi PLC + HMI
- Maintenance: Modern reliability
- Sheet loading: Automated option

PERFORMANCE IMPROVEMENTS:
- Throughput increase: 40%
- Output: From 14-16 to 20-22 sheets/hour
- Energy efficiency: 20-25% reduction
- Processing: More consistent

KEY FEATURES THAT MADE THE DIFFERENCE:
1. Fully servo-driven system
   - Intelligence in every movement
   - Precise positioning
   - Energy efficient

2. Dual-sided IR Quartz heating
   - Consistent heating
   - Energy efficient
   - Better temperature control

3. Mitsubishi PLC + HMI control
   - Unprecedented operator control
   - Profiling capabilities
   - Recipe storage

4. Closed chamber design
   - Pre-blow capability
   - Vacuum profiling
   - Improved precision
   - Better sheet utilization

HUMAN IMPACT:
- Operators felt: Pride, relief, curiosity
- Pride: Company investing in future
- Relief: Maintenance headaches over
- Curiosity: New possibilities
- Quote: "It's a joy to see precision reborn" """,
        knowledge_type="customer_story",
        source_file=SOURCE_FILE,
        entity="Dezet Results",
        summary="Dezet results: 40% more output (14-16 → 20-22 sheets/hr), servo, quartz heating, €150k",
        metadata={
            "topic": "results",
            "throughput_increase_percent": 40,
            "before_sheets_hr": "14-16",
            "after_sheets_hr": "20-22",
            "investment_eur": 150000
        }
    ))

    # 3. Machinecraft EU Sales Strategy
    items.append(KnowledgeItem(
        text="""Machinecraft EU Sales Strategy

TARGET MARKET:
- Manufacturers with machines from 1980s-2000s
- Companies with aging Illig, Kiefel, or similar equipment
- Those experiencing:
  * Increasing maintenance
  * Downtime issues
  * Manual process bottlenecks
  * Competitive pressure

VALUE PROPOSITION:
"Swap-in upgrade" through PF1-X series
- Boost output by up to 40%
- Cut energy use by 20-25%
- Modern automation
- CE-ready for European compliance

SALES PROCESS:

STEP 1: WEEK-ZERO AUDIT (Free)
- Measure current machine performance
- Calculate savings potential:
  * Power savings
  * Time savings
  * Scrap reduction
- No obligation assessment

STEP 2: PROPOSAL
- Custom solution based on audit findings
- Trade-in value for old machine
- ROI calculation
- Financing options

STEP 3: DELIVERY
- CE-ready machine
- Often producing parts within 72 hours of installation
- Quick swap-in minimizes downtime

TRADE-IN PROGRAM:
- Old machines can be traded in
- Reduces capital outlay
- Handles disposal of old equipment

EU MARKET POSITIONING:
"From India to Europe's factory floors"
"Help Europe's factories keep their traditions
— just with faster, cleaner, smarter machines"

SALES TARGETS (Annual):
- Audits target: 40 per year
- Replacement target: 20 machines per year
- Revenue target: €3-4 million
- Focus markets: Netherlands, Germany initially""",
        knowledge_type="sales_strategy",
        source_file=SOURCE_FILE,
        entity="EU Sales Strategy",
        summary="EU strategy: Target 1980s-2000s machines, free Week-Zero Audit, swap-in upgrade, 40% output boost",
        metadata={
            "topic": "eu_strategy",
            "target_audits": 40,
            "target_replacements": 20,
            "revenue_target_eur": "3-4 million"
        }
    ))

    # 4. Investment Justification
    items.append(KnowledgeItem(
        text="""PF1-X Investment Justification for European Customers

INVESTMENT VALUE (Dezet example: €150,000)

The investment isn't just in a machine. It's in:

1. COMPETITIVENESS
   - Stay relevant in fast-moving market
   - 40% more output = more capacity
   - Faster response to customer orders
   - Win contracts against competitors

2. SAFETY
   - Modern systems protect operators better
   - Updated safety interlocks
   - CE compliance built-in
   - Reduced manual handling risks

3. SUSTAINABILITY
   - 20-25% more energy efficient
   - Lower carbon footprint
   - Meets EU sustainability expectations
   - Future-proofs against regulations

4. CAPABILITY
   - Unlock possibilities not feasible before
   - Process materials previously difficult
   - Tighter tolerances
   - More complex geometries

ROI CALCULATION ELEMENTS:

Energy Savings:
- 20-25% reduction in power consumption
- At European energy prices = significant €€€

Throughput Increase:
- 40% more output
- Same labor, more product
- Reduces per-part cost

Scrap Reduction:
- Consistent processing
- Better temperature control
- Closed chamber = less waste

Maintenance Reduction:
- New servo systems vs 40-year-old mechanicals
- Warranty coverage
- Global spare parts availability

Labor Efficiency:
- Automation reduces manual steps
- Operators freed for value-add work
- Faster setup/changeover

PAYBACK PERIOD:
- Varies by utilization and local costs
- Typical: 2-4 years for high-volume users
- Trade-in reduces initial outlay""",
        knowledge_type="commercial",
        source_file=SOURCE_FILE,
        entity="EU Investment Case",
        summary="€150k investment justification: competitiveness, safety, sustainability, capability; 20-25% energy savings",
        metadata={
            "topic": "investment_justification",
            "price_eur": 150000,
            "energy_savings_percent": "20-25",
            "throughput_increase_percent": 40
        }
    ))

    # 5. Ideal EU Customer Profile
    items.append(KnowledgeItem(
        text="""Ideal European Customer Profile for Machinecraft

WHO TO TARGET IN EUROPE:

MACHINE AGE:
- Running thermoforming machines from 1980s-2000s
- Brands: Illig, Kiefel, ZMD, CMS, or similar European OEMs
- 20-40+ years old equipment
- Mechanical drives (not servo)

COMPANY TYPE:
- Family-owned or medium-sized enterprises
- Strong tradition of quality
- Pride in craftsmanship
- Not commodity producers (quality over volume)

INDUSTRY SECTORS:
- Medical/healthcare products
- Mobility/accessibility equipment
- Aerospace components (non-flight)
- Industrial enclosures
- Specialty packaging
- Signage and displays

PAIN POINTS TO IDENTIFY:
- Increasing maintenance costs
- More frequent breakdowns
- Difficulty finding spare parts
- Manual sheet loading bottleneck
- Energy costs rising
- Losing bids due to capacity constraints
- Young workforce doesn't want to run old machines

GEOGRAPHY (Initial Focus):
- Netherlands (proven with Dezet)
- Germany (many aging machines)
- Belgium, Denmark, Sweden (similar profiles)
- UK (post-Brexit trade opportunity)

DECISION MAKERS:
- Owner/Managing Director (family businesses)
- Production Manager
- Technical Director
- Financial Controller (for ROI discussion)

CONVERSATION STARTERS:
- "When was your machine installed?"
- "How often do you need maintenance visits?"
- "What's your current output per hour?"
- "Have you considered what happens when parts are unavailable?"

QUALIFICATION CRITERIA:
- Machine >15 years old
- Running at least 1 shift/day
- Quality-focused (not lowest-price)
- Budget for €100-200k investment
- Decision maker accessible""",
        knowledge_type="sales_strategy",
        source_file=SOURCE_FILE,
        entity="EU Customer Profile",
        summary="Target EU: 1980s-2000s machines (Illig/Kiefel), family firms, medical/industrial sectors, Netherlands/Germany",
        metadata={
            "topic": "ideal_customer",
            "machine_age": "20-40+ years",
            "brands_to_replace": ["Illig", "Kiefel", "ZMD", "CMS"],
            "target_countries": ["Netherlands", "Germany"]
        }
    ))

    # 6. Week-Zero Audit Process
    items.append(KnowledgeItem(
        text="""Week-Zero Audit - Machinecraft EU Sales Tool

WHAT IS WEEK-ZERO AUDIT:
- Free performance assessment
- No obligation
- On-site or remote evaluation
- Baseline measurement of current machine

WHAT GETS MEASURED:

1. CURRENT PERFORMANCE:
   - Sheets/parts per hour
   - Cycle time breakdown
   - Uptime vs downtime
   - Scrap rate

2. ENERGY CONSUMPTION:
   - kWh per shift
   - Heater efficiency
   - Motor loads
   - Standby consumption

3. MAINTENANCE HISTORY:
   - Breakdown frequency
   - Spare parts costs
   - Technician visits
   - Downtime hours

4. PROCESS CAPABILITY:
   - Material types run
   - Thickness range
   - Temperature consistency
   - Forming quality

DELIVERABLES FROM AUDIT:

1. CURRENT STATE REPORT:
   - Documented baseline performance
   - Identified bottlenecks
   - Maintenance cost summary

2. POTENTIAL SAVINGS CALCULATION:
   - Power savings (€/year)
   - Time savings (hours/year)
   - Scrap reduction (€/year)
   - Maintenance savings (€/year)

3. UPGRADE PROPOSAL:
   - Recommended PF1-X model
   - Price including trade-in
   - Projected ROI
   - Implementation timeline

WHY IT WORKS:
- Low barrier to engagement (free)
- Creates data-driven conversation
- Quantifies pain points
- Builds trust before purchase
- Demonstrates expertise

FOLLOW-UP:
- Within 2 weeks of audit
- Present findings to decision makers
- Compare old vs new scenarios
- Discuss financing options""",
        knowledge_type="sales_strategy",
        source_file=SOURCE_FILE,
        entity="Week-Zero Audit",
        summary="Week-Zero Audit: Free assessment of old machine, measure output/energy/maintenance, calculate ROI",
        metadata={
            "topic": "sales_process",
            "audit_type": "Week-Zero",
            "cost": "Free",
            "deliverables": ["baseline", "savings", "proposal"]
        }
    ))

    # 7. EU Value Messaging
    items.append(KnowledgeItem(
        text="""Machinecraft EU Value Messaging

CORE MESSAGE:
"Help Europe's factories keep their traditions
— just with faster, cleaner, smarter machines"

KEY THEMES:

1. RESPECT FOR HERITAGE:
   - Not abandoning the past
   - Building on it
   - Honoring craftsmanship
   - "Progress that never forgets where it came from"

2. EVOLUTION NOT REVOLUTION:
   - Same purpose: quality products
   - Transformed means
   - "Industrial evolution"
   - Smooth transition

3. MODERNIZATION MADE PAINLESS:
   - Swap-in upgrade
   - Trade-in old equipment
   - 72-hour installation
   - CE-ready

4. MEASURABLE RESULTS:
   - 40% throughput increase
   - 20-25% energy reduction
   - Quantified in Week-Zero Audit
   - Clear ROI

EMOTIONAL APPEALS:

For Operators:
- "It's a joy to see precision reborn"
- Pride in modern equipment
- Relief from maintenance headaches
- Excitement about new capabilities

For Owners:
- Invest in the future
- Protect legacy
- Stay competitive
- Sustainability credentials

For Engineers:
- Technical excellence
- Servo precision
- Advanced controls
- Global component brands

SOCIAL PROOF:
- Dezet story as reference
- Netherlands and Germany trials
- 42 years of machine life respected
- Family business to family business

HASHTAGS (LinkedIn presence):
#Manufacturing #IndustrialTransformation #Thermoforming
#ProcessImprovement #Engineering #Innovation #Automation
#ManufacturingExcellence #Industry40 #ContinuousImprovement""",
        knowledge_type="sales_strategy",
        source_file=SOURCE_FILE,
        entity="EU Messaging",
        summary="EU message: 'Keep traditions with faster, cleaner, smarter machines'; respect heritage + modernize",
        metadata={
            "topic": "messaging",
            "core_message": "traditions with modern machines",
            "themes": ["heritage", "evolution", "painless", "measurable"]
        }
    ))

    return items


def main():
    """Main ingestion function."""
    print("=" * 60)
    print("Dezet Story - EU Sales Strategy Ingestion")
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
