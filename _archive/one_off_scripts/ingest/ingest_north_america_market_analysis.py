#!/usr/bin/env python3
"""
Ingest North American Thermoforming Market Strategic Analysis

Authors: Cham Tailor & Rushabh Doshi, Machinecraft Technologies
Date: March 8, 2025

Strategic analysis of the USA/North American thermoforming market covering:
- Reshoring trends and macro factors
- Automation adoption drivers
- Machinecraft competitive advantages vs legacy machines
- ROI and cost-per-part economics
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from openclaw.agents.ira.src.brain.knowledge_ingestor import KnowledgeIngestor, KnowledgeItem

SOURCE_FILE = "Advanced Thermoforming in North American Manufacturing_ A Strategic Analysis.docx.pdf"


def create_knowledge_items() -> list[KnowledgeItem]:
    """Create structured knowledge items from the North America market analysis."""
    items = []

    # 1. Market Overview & Reshoring Trends
    items.append(KnowledgeItem(
        text="""North American Thermoforming Market: Reshoring Renaissance

DOCUMENT: Strategic Analysis by Cham Tailor & Rushabh Doshi (March 2025)

RESHORING TRENDS (USA):
- Manufacturing job announcements: ~364,000 in 2022
- 53% jump from 2021 - record high
- Dramatic reversal after decades of offshoring

KEY DRIVERS:
1. Supply chain vulnerabilities (pandemic disruptions)
2. Geopolitics (US-China tensions)
3. Desire for local production

POLICY SUPPORT:
- Inflation Reduction Act
- CHIPS Act
- Infrastructure bills
- Subsidies and incentives for domestic manufacturing

FACTORY CONSTRUCTION:
- Construction spending on US manufacturing: +40% in 2022
- 62% higher YoY by late 2023
- "Not seen in decades" pace of new plant builds
- Focus on supply chain resiliency

IMPLICATION FOR MACHINECRAFT:
- Growing demand for thermoforming equipment in USA
- New factories need modern machinery
- Opportunity to sell into reshored production""",
        knowledge_type="market_intelligence",
        source_file=SOURCE_FILE,
        entity="North America Market",
        summary="USA reshoring: 364K jobs 2022 (+53%), factory construction +40%, driven by supply chain & policy",
        metadata={
            "topic": "reshoring_trends",
            "region": "North America",
            "year": 2022
        }
    ))

    # 2. Automation & Labor Trends
    items.append(KnowledgeItem(
        text="""North American Manufacturing: Automation & Labor Dynamics

ROBOT INSTALLATIONS (North America):
- ~43,000 units in 2021
- Q1 2022: 11,600 robots ordered ($664M) - all-time high
- +28% from prior year
- Strong rebound after 2020 dip

LABOR MARKET PRESSURES (USA):
- 600,000+ manufacturing job openings (mid-2023)
- 45% of all job openings nationwide
- Persistent skills gap
- Retiring workforce

WAGE INFLATION:
- Average hourly earnings: $27.22 (early 2024)
- +5.3% year-on-year increase
- Rising wages = higher production costs

WHY AUTOMATION IS CRITICAL:
1. Labor scarcity makes staffing difficult
2. Rising wages squeeze margins
3. Skills gap limits capacity
4. Automation does more with fewer people
5. Reduces dependence on scarce skilled operators

MATERIAL COST VOLATILITY:
- Plastic resins: critical thermoforming input
- 2021: Soaring prices and shortages
- Polypropylene: spiked ~$0.34/lb
- Caused by pandemic + Gulf Coast weather

MACHINECRAFT VALUE PROPOSITION:
- Advanced machinery offsets labor costs
- Material efficiency reduces resin expense
- Automation addresses workforce shortage
- Technology = strategic necessity""",
        knowledge_type="market_intelligence",
        source_file=SOURCE_FILE,
        entity="North America Labor Market",
        summary="USA labor: 600K openings, $27.22/hr (+5.3%), 43K robots/yr - automation critical for competitiveness",
        metadata={
            "topic": "automation_labor_trends",
            "region": "North America",
            "robot_installations": 43000,
            "avg_hourly_wage": 27.22
        }
    ))

    # 3. Machinecraft vs Traditional Machines - Performance
    items.append(KnowledgeItem(
        text="""Machinecraft vs Traditional Thermoformers: Performance Comparison

CYCLE TIME & THROUGHPUT:
Traditional Machine:
- 4-5 minutes per cycle
- 12-15 parts per hour

Machinecraft Machine:
- 2-2.5 minutes per cycle
- 24-30 parts per hour (normal conditions)
- Up to 40 cycles/hour (optimized)
- 2x-3x output of older machines

MATERIAL UTILIZATION:
Traditional:
- Uneven heating causes sheet sag
- Requires thicker plastic (e.g., 0.125" ABS)
- More material waste

Machinecraft:
- Better sag control
- Same part with 0.115" thickness
- ~8% reduction in material thickness
- Example: 19,080 lbs vs 20,740 lbs for 1,200 parts
- Thousands of dollars saved per production run

SETUP & CHANGEOVER:
Traditional Machine:
- 1-2 hours setup time
- ~90 minutes typical
- Manual mold bolting
- Manual clamp frame adjustment
- 60+ minutes for mold/sheet change

Machinecraft:
- ~15 minutes setup
- Quick-lock mold mounts (no vacuum box)
- Computer-controlled auto-adjusting clamp frames
- ~10 minutes for mold change (servo motors)
- 40-50 minutes less downtime per changeover""",
        knowledge_type="commercial",
        source_file=SOURCE_FILE,
        entity="Machinecraft Performance",
        summary="Machinecraft vs legacy: 2x-3x throughput, 8% less material, 15min vs 90min setup",
        metadata={
            "topic": "performance_comparison",
            "throughput_improvement": "2-3x",
            "material_savings": "8%",
            "setup_time_minutes": 15
        }
    ))

    # 4. Automation & Labor Savings Details
    items.append(KnowledgeItem(
        text="""Machinecraft Automation: Labor Savings Analysis

TRADITIONAL MACHINE LABOR REQUIREMENTS:
- 1-2 workers for loading/unloading
- ~80 seconds handling time per cycle
- Manual sheet loading
- Manual part removal
- Operator-dependent process

MACHINECRAFT AUTOMATED PROCESS:
- Fully automated sheet loading
- Automated part ejection
- No human intervention required
- Loading happens parallel to heating
- Next sheet queued while previous forms
- Effective handling time: ~20 seconds
- 60 seconds saved per cycle

WORKFORCE ADVANTAGES:
- One operator can oversee multiple machines
- Reduces direct labor costs
- Less reliance on scarce skilled operators
- Addresses labor shortage problem
- More consistent output (not operator-dependent)

REAL-WORLD RESULTS:
- Daily downtime reduced: 4 hours → 1 hour
- Monthly output increase: 3,000 → 7,500 parts
- 150% improvement on single machine
- Scale production without adding labor

STRATEGIC VALUE:
- Throughput advantage wins contracts
- Faster delivery promises
- Accommodate larger volumes
- Excess capacity provides resilience
- Can absorb demand spikes
- Cover for other lines if needed""",
        knowledge_type="commercial",
        source_file=SOURCE_FILE,
        entity="Machinecraft Labor Savings",
        summary="Machinecraft automation: 80→20sec handling, 1 operator multi-machine, 3K→7.5K parts/month",
        metadata={
            "topic": "automation_labor_savings",
            "handling_time_reduction": "80 to 20 seconds",
            "output_improvement": "3000 to 7500 parts/month"
        }
    ))

    # 5. Quality & Pre-Blow Technology
    items.append(KnowledgeItem(
        text="""Machinecraft Quality Advantages: Pre-Blow Sag Control

TRADITIONAL VACUUM FORMING PROBLEMS:
- Hot plastic sheet sags under own weight
- Thinning at center
- Uneven wall thickness after forming
- When mold presses up, sag causes:
  - Thin corners
  - Weak vertical walls
  - Rejects and scrapped parts
  - Weaker finished parts

MACHINECRAFT PRE-BLOW SOLUTION:
- Before mold contacts plastic
- Sheet supported by air cushion
- Or inflated into controlled bubble
- Material stretches uniformly
- Prevents severe sag
- Results: even wall thickness across part

ADVANCED HEATING TECHNOLOGY:
- Halogen heating elements
- Closer heater positioning
- Sheet is supported so heaters can be closer
- Tighter temperature control
- More uniform heating

QUALITY OUTCOMES:
- Higher yield (fewer rejects)
- Fewer scrapped parts due to thin spots
- No warping issues
- Better product performance
- Consistent thickness = consistent strength

AUTOMATIC COOLING & EJECTION:
- Ejects at set temperature (not fixed time)
- Protects part quality
- Ensures dimensional stability
- Legacy machines risk warping if not fully cooled""",
        knowledge_type="operational",
        source_file=SOURCE_FILE,
        entity="Pre-Blow Technology",
        summary="Pre-blow sag control: air cushion supports sheet, even wall thickness, higher yield, fewer rejects",
        metadata={
            "topic": "quality_technology",
            "features": ["pre_blow", "halogen_heating", "auto_cooling"]
        }
    ))

    # 6. Cost Per Part & ROI Analysis
    items.append(KnowledgeItem(
        text="""Machinecraft ROI Analysis: Cost Per Part Economics (USA Market)

COST PER PART BREAKDOWN:

Operating Cost Assumption: $120/hour fully-loaded

Traditional Machine:
- 15 parts/hour
- Overhead per part: $8.00
- Total piece price: ~$56.55

Machinecraft Machine:
- 30 parts/hour
- Overhead per part: $4.00
- Total piece price: ~$48.52

SAVINGS:
- 14% reduction in unit cost
- $8.03 savings per part
- Goes directly to gross margin

PRODUCTION RUN EXAMPLE (1,200 parts):
- Additional profit: $9,636
- Material: 19,080 lbs vs 20,740 lbs
- Material savings: 1,660 lbs

CAPITAL COST COMPARISON:
- Machinecraft: ~$260,000
- Traditional machine: ~$255,000
- Virtually same investment

ROI IMPLICATIONS:
- One medium job can recoup price premium
- Few months of production = payback
- Lower costs + higher throughput + better quality
- Profit gain goes straight to ROI

CUMULATIVE LONG-TERM SAVINGS:
- Over years of operation
- Material savings + labor reduction + higher uptime
- Can amount to hundreds of thousands of dollars
- Lower total cost of ownership""",
        knowledge_type="commercial",
        source_file=SOURCE_FILE,
        entity="ROI Analysis USA",
        summary="USA ROI: $56.55→$48.52/part (-14%), $9,636 extra profit per 1,200 parts, ~$260K investment",
        metadata={
            "topic": "roi_analysis",
            "cost_reduction_percent": 14,
            "machine_cost_usd": 260000,
            "profit_per_1200_parts": 9636
        }
    ))

    # 7. Strategic Competitive Positioning
    items.append(KnowledgeItem(
        text="""Machinecraft Strategic Positioning in North American Market

COMPETITIVE ADVANTAGES:

1. COST LEADERSHIP:
- 14%+ cost advantage per part
- Can undercut competitors with legacy equipment
- Or maintain prices with higher margins
- Game-changing in cents-per-unit contract bids

2. THROUGHPUT SUPERIORITY:
- 2-3x more output per hour
- Take on more orders
- Shorter lead times than competitors
- Win contracts with delivery promises

3. FLEXIBILITY & AGILITY:
- Quick-change capabilities (minutes not hours)
- High-mix production strategy viable
- Diversify product offerings
- Capture niche markets
- Customize short runs profitably

MARKET POSITIONING OPTIONS:
- Price leadership without margin sacrifice
- Higher margin on each sale
- More cash flow for reinvestment
- "Do more with less"

CAPACITY ADVANTAGES:
- Scale without linear labor increase
- Absorb demand spikes
- Cover for other lines if down
- Run while competitors at full tilt

INVESTOR PERSPECTIVE:
- Lower cost base = better earnings
- Mitigate operational risks (labor, quality)
- Insulated from wage inflation
- Aligned with reshoring/automation trend
- Clear ROI case accelerates adoption""",
        knowledge_type="commercial",
        source_file=SOURCE_FILE,
        entity="Competitive Strategy",
        summary="Strategic positioning: cost leadership (-14%), throughput (2-3x), flexibility, scalability for USA market",
        metadata={
            "topic": "competitive_positioning",
            "region": "North America"
        }
    ))

    # 8. Key Strategic Takeaways
    items.append(KnowledgeItem(
        text="""North America Market: Key Strategic Takeaways for Machinecraft Sales

TAKEAWAY 1: EFFICIENCY = COMPETITIVE ADVANTAGE
- Substantially lower cost-per-part
- Higher throughput
- Outprice competitors OR higher margins
- Greater market share and pricing power
- Cost leadership is critical in this sector

TAKEAWAY 2: RESILIENCE THROUGH AUTOMATION
- Reduced dependence on manual labor
- Minimized setup/changeover times
- Resilience against labor shortages
- Maintain output with lean workforce
- Decisive advantage amid US skilled labor gap
- Consistent quality → brand reputation
- Customer trust over time

TAKEAWAY 3: SCALABLE & SUSTAINABLE GROWTH
- High-efficiency machinery = long-term play
- Fixed investment quickly amortized
- Per-unit savings compound with volume
- Scale up without commensurate cost rise
- Superior returns for investors
- Weather economic shifts (wages, materials)

SELLING POINTS FOR USA MARKET:
1. "Automation addresses your labor shortage"
2. "2-3x throughput = more contracts won"
3. "14% cost reduction = competitive pricing"
4. "15-minute changeovers = flexibility"
5. "Same capital cost as legacy machines"
6. "Payback in months, not years"
7. "Aligned with reshoring trend"

TARGET CUSTOMERS:
- Companies expanding/reshoring production
- Legacy equipment users (4-5 min cycles)
- Labor-constrained manufacturers
- High-volume contract shops
- Quick-turnaround service bureaus""",
        knowledge_type="commercial",
        source_file=SOURCE_FILE,
        entity="USA Sales Strategy",
        summary="USA sales strategy: automation solves labor, 14% cost advantage, 2-3x throughput, quick payback",
        metadata={
            "topic": "sales_strategy",
            "region": "North America",
            "key_messages": ["labor_shortage", "cost_advantage", "throughput", "payback"]
        }
    ))

    return items


def main():
    """Main ingestion function."""
    print("=" * 60)
    print("North American Thermoforming Market Analysis Ingestion")
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
