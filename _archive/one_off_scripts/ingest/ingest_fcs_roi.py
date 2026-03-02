#!/usr/bin/env python3
"""
Ingest FCS ROI Sheet - PET Lid Production Example

ROI comparison between FCS5065 and FCS6080U for producing PET flat and dome lids.
Key business case: FCS6080U has 3x capacity and 7-8 month payback vs 15-16 months.

Product: 102.45mm OD lids for drink cups
Materials: 0.25mm PET (flat) and 0.40mm PET (dome)
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from openclaw.agents.ira.src.brain.knowledge_ingestor import KnowledgeIngestor, KnowledgeItem

SOURCE_FILE = "FCS ROI.pdf"


def create_knowledge_items() -> list[KnowledgeItem]:
    """Create structured knowledge items from the FCS ROI sheet."""
    items = []

    # 1. Product & Application Overview
    items.append(KnowledgeItem(
        text="""FCS Series ROI Analysis - PET Lid Production Application

APPLICATION: PET Flat & Dome Lids for Drink Cups
Target Product: 102.45 mm outer diameter lids

PRODUCT SPECIFICATIONS:

1. FLAT LID:
   - Material: PET
   - Thickness: 0.25 mm
   - Weight: ~2.9 grams per lid
   - Application: Cold drink cups

2. DOME LID:
   - Material: PET
   - Thickness: 0.40 mm
   - Weight: ~4.3 grams per lid
   - Application: Cold drink cups (with straw slot)

MOLD SPECIFICATIONS:
- Mold Pitch: 115 mm x 115 mm
- FCS5065 Cavitation: 20 cavities
- FCS6080U Cavitation: 30 cavities

This is a HIGH-VOLUME packaging application typical of:
- Beverage industry suppliers
- Disposable foodservice packaging
- Export-oriented lid manufacturers""",
        knowledge_type="commercial",
        source_file=SOURCE_FILE,
        entity="FCS",
        summary="FCS ROI for PET lid production: 102.45mm OD, flat 0.25mm, dome 0.40mm",
        metadata={
            "topic": "application_overview",
            "product": "PET_lids",
            "lid_diameter_mm": 102.45,
            "flat_thickness_mm": 0.25,
            "dome_thickness_mm": 0.40
        }
    ))

    # 2. Machine Comparison
    items.append(KnowledgeItem(
        text="""FCS5065 vs FCS6080U Machine Comparison

MACHINE SPECIFICATIONS:

FCS5065 (Entry/Mid-Level):
- Usable Mold Block: 500 x 600 mm
- Max Sheet Width: ~650 mm
- Max Forming Depth: 100 mm
- Cycle Speed: 12-18 cycles/minute
- Cavities (for 102.45mm lids): 20 cavities
- Machine Price (EXW): $160,000

FCS6080U (High-Volume):
- Usable Mold Block: 600 x 700 mm
- Max Sheet Width: ~870 mm
- Max Forming Depth: 150 mm
- Cycle Speed: 25-30 cycles/minute
- Cavities (for 102.45mm lids): 30 cavities
- Machine Price (EXW): $240,000

KEY DIFFERENCES:
- FCS6080U has 50% more cavities (30 vs 20)
- FCS6080U runs nearly 2x faster (25-30 vs 12-18 cycles/min)
- FCS6080U costs 50% more ($240K vs $160K)
- Combined effect: FCS6080U produces 3x more output
- FCS6080U has 50% more forming depth (150mm vs 100mm)

PRICE PREMIUM ANALYSIS:
- Price difference: $80,000 (50% more)
- Output difference: 3x more capacity
- Result: Much better value per lid capacity""",
        knowledge_type="machine_spec",
        source_file=SOURCE_FILE,
        entity="FCS",
        summary="FCS5065 ($160K, 20 cav) vs FCS6080U ($240K, 30 cav, 2x speed)",
        metadata={
            "topic": "machine_comparison",
            "fcs5065_price": 160000,
            "fcs6080u_price": 240000,
            "fcs5065_cavities": 20,
            "fcs6080u_cavities": 30
        }
    ))

    # 3. Output Estimates
    items.append(KnowledgeItem(
        text="""FCS Series Output Estimates - PET Lid Production

PRODUCTION OUTPUT BY MACHINE AND LID TYPE:

FCS5065 - FLAT LID (0.25mm PET):
- Cycle Time: 5.5 - 6.5 seconds
- Output: 11,000 - 13,000 lids/hour
- Cavities: 20
- Calculation: 20 cavities × 9-11 cycles/min × 60 min

FCS5065 - DOME LID (0.40mm PET):
- Cycle Time: 6.5 - 7.5 seconds
- Output: 9,500 - 11,000 lids/hour
- Cavities: 20
- Note: Thicker material requires longer cycle

FCS6080U - FLAT LID (0.25mm PET):
- Cycle Time: 4.5 - 5.5 seconds
- Output: 19,500 - 24,000 lids/hour
- Cavities: 30
- Calculation: 30 cavities × 11-13 cycles/min × 60 min

FCS6080U - DOME LID (0.40mm PET):
- Cycle Time: 5.5 - 6.5 seconds
- Output: 16,500 - 19,500 lids/hour
- Cavities: 30
- Note: Thicker material requires longer cycle

OUTPUT COMPARISON:
- Flat lids: FCS6080U produces ~85% more than FCS5065
- Dome lids: FCS6080U produces ~75% more than FCS5065
- Overall: FCS6080U delivers approximately 3x monthly volume

CYCLE TIME FACTORS:
- Thinner material (0.25mm) = faster cycles
- Thicker material (0.40mm) = slower cycles (more heat needed)
- Dome shape may require slightly longer forming time""",
        knowledge_type="commercial",
        source_file=SOURCE_FILE,
        entity="FCS",
        summary="Output: FCS5065 11-13K/hr flat, FCS6080U 19.5-24K/hr flat (~3x monthly)",
        metadata={
            "topic": "output_estimates",
            "fcs5065_flat_output": "11000-13000/hr",
            "fcs6080u_flat_output": "19500-24000/hr",
            "fcs5065_dome_output": "9500-11000/hr",
            "fcs6080u_dome_output": "16500-19500/hr"
        }
    ))

    # 4. ROI & Payback Analysis
    items.append(KnowledgeItem(
        text="""FCS Series ROI & Payback Analysis - PET Lid Production

FINANCIAL ASSUMPTIONS:
- Selling Price per Lid: $0.007 (0.7 cents)
- Contribution Margin: $0.0035/lid (0.35 cents = 50% margin)
- Operating Schedule: 16 hours/day × 26 days/month = 416 hours/month
- Mold Cost FCS5065: $35,000
- Mold Cost FCS6080U: $45,000

---

FCS5065 ROI ANALYSIS:

Total Investment:
- Machine: $160,000
- Mold: $35,000
- TOTAL: $195,000

Monthly Production:
- Output: ~3.5 million lids/month
- Calculation: ~8,400 lids/hr avg × 416 hrs

Monthly Profit:
- Margin: ~$12,250/month
- Calculation: 3.5M lids × $0.0035

Payback Period: ~15-16 months

---

FCS6080U ROI ANALYSIS:

Total Investment:
- Machine: $240,000
- Mold: $45,000
- TOTAL: $285,000

Monthly Production:
- Output: ~10.5 million lids/month
- Calculation: ~25,200 lids/hr avg × 416 hrs

Monthly Profit:
- Margin: ~$36,750/month
- Calculation: 10.5M lids × $0.0035

Payback Period: ~7-8 months

---

ROI COMPARISON:
| Metric | FCS5065 | FCS6080U |
|--------|---------|----------|
| Investment | $195,000 | $285,000 |
| Monthly Output | 3.5M lids | 10.5M lids |
| Monthly Margin | $12,250 | $36,750 |
| Payback | 15-16 months | 7-8 months |

KEY INSIGHT:
FCS6080U costs 46% more ($90K) but:
- Produces 3x more volume
- Pays back in HALF the time
- Generates 3x monthly profit""",
        knowledge_type="commercial",
        source_file=SOURCE_FILE,
        entity="FCS",
        summary="ROI: FCS5065 payback 15-16mo ($195K), FCS6080U payback 7-8mo ($285K, 3x output)",
        metadata={
            "topic": "roi_analysis",
            "fcs5065_investment": 195000,
            "fcs6080u_investment": 285000,
            "fcs5065_payback_months": "15-16",
            "fcs6080u_payback_months": "7-8",
            "margin_per_lid": 0.0035
        }
    ))

    # 5. Recommendations & Decision Logic
    items.append(KnowledgeItem(
        text="""FCS Machine Selection Recommendations - Decision Logic

RECOMMENDATION SUMMARY:

✅ FCS5065 - RECOMMENDED FOR:
- Budget-conscious operations
- Monthly volumes up to ~4 million lids
- Smaller initial investment preference
- Testing new markets before scaling
- Lower risk entry point

✅✅ FCS6080U - STRONGLY RECOMMENDED FOR:
- Larger contracts requiring high volume
- Export-oriented production
- Faster ROI priority
- Operations targeting >4 million lids/month
- Companies with established customer base

---

DECISION FRAMEWORK:

Choose FCS5065 when:
1. Capital budget limited to ~$200K
2. Monthly demand is under 4M lids
3. First-time thermoforming operation
4. Want to minimize initial risk
5. Space constraints exist

Choose FCS6080U when:
1. Have secured high-volume contracts
2. Monthly demand exceeds 4M lids
3. Want fastest payback (under 8 months)
4. Planning for export/multiple customers
5. Prioritize long-term profitability

---

UPGRADE PATH:
- Start with FCS5065 to validate market
- Add FCS6080U when demand exceeds 4M/month
- Two FCS5065 ≈ One FCS6080U output but costs more

VALUE PROPOSITION:
- FCS6080U: 50% more expensive, 3x more productive
- Per-lid cost significantly lower on FCS6080U
- Faster payback = lower risk despite higher investment""",
        knowledge_type="commercial",
        source_file=SOURCE_FILE,
        entity="FCS",
        summary="FCS5065 for <4M lids/mo budget ops; FCS6080U for high-volume, 7-8mo payback",
        metadata={
            "topic": "recommendations",
            "fcs5065_max_volume": "4M lids/month",
            "fcs6080u_advantage": "3x output, faster payback",
            "decision_threshold": "4M lids/month"
        }
    ))

    # 6. Sales Talking Points
    items.append(KnowledgeItem(
        text="""FCS Series Sales Talking Points - Lid Production ROI

KEY SELLING POINTS FOR FCS6080U:

1. FASTER PAYBACK:
   "The FCS6080U pays for itself in 7-8 months vs 15-16 months 
   for the smaller machine. That's HALF the payback time."

2. BETTER INVESTMENT EFFICIENCY:
   "For only 50% more investment ($90K), you get 3x the output.
   That's the best capacity-per-dollar in the market."

3. MONTHLY PROFIT COMPARISON:
   "FCS6080U generates $36,750/month profit vs $12,250/month.
   That extra $24,500/month pays off the price difference in under 4 months."

4. VOLUME CAPABILITY:
   "10.5 million lids per month means you can serve major accounts
   and export contracts that smaller machines simply can't handle."

---

OBJECTION HANDLING:

"The FCS6080U costs too much."
→ "Yes, but it pays back in 7-8 months. After payback, you're 
   making $36,750/month profit. The smaller machine takes twice 
   as long to pay back and makes 1/3 the profit."

"We don't need that much capacity."
→ "If your volumes are under 4 million lids/month, the FCS5065 
   is perfect. But if you're planning to grow or take larger 
   contracts, the FCS6080U is significantly more cost-effective."

"Can we start smaller and upgrade later?"
→ "Yes, the FCS5065 is a great entry point. Many customers start 
   there and add capacity later. But if you already have volume 
   commitments, starting with FCS6080U is smarter economics."

---

USE THIS ROI MODEL FOR OTHER PRODUCTS:
This calculation framework applies to any high-volume packaging:
- Change cavitation based on product size
- Adjust material cost/weight
- Modify selling price and margin
- Recalculate payback accordingly""",
        knowledge_type="commercial",
        source_file=SOURCE_FILE,
        entity="FCS",
        summary="Sales talking points: 7-8mo payback, 3x output for 50% more, $24.5K/mo extra profit",
        metadata={
            "topic": "sales_talking_points",
            "key_message": "50% more cost, 3x output, half payback time",
            "monthly_profit_difference": 24500
        }
    ))

    return items


def main():
    """Main ingestion function."""
    print("=" * 60)
    print("FCS ROI Sheet Ingestion")
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
