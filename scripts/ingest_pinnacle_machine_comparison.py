#!/usr/bin/env python3
"""
Ingest Machine Comparison for Pinnacle

Shows how Machinecraft presents PF1 machine tiers to Indian customers.
Tiered approach: Basic → Universal → Auto → Pro with clear feature upgrades.

Source: Machine Comparison - for Pinnacle.xlsx
"""

import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Import directly from the module file
import importlib.util
spec = importlib.util.spec_from_file_location(
    "knowledge_ingestor",
    os.path.join(project_root, "openclaw/agents/ira/src/brain/knowledge_ingestor.py")
)
knowledge_ingestor_module = importlib.util.module_from_spec(spec)
sys.modules["knowledge_ingestor"] = knowledge_ingestor_module
spec.loader.exec_module(knowledge_ingestor_module)

KnowledgeIngestor = knowledge_ingestor_module.KnowledgeIngestor
KnowledgeItem = knowledge_ingestor_module.KnowledgeItem

SOURCE_FILE = "Machine Comparison - for Pinnacle.xlsx"


def create_knowledge_items() -> list[KnowledgeItem]:
    """Create structured knowledge items from Pinnacle machine comparison."""
    items = []

    # 1. Comparison Overview
    items.append(KnowledgeItem(
        text="""PF1 Machine Tier Comparison - Pinnacle India Example

CUSTOMER: Pinnacle (India)
APPLICATION: Large format thermoforming (2500 x 5000 mm)
MARKET: India (prices in INR Crore)

MACHINE SPECS:
- Max. Forming Area: 2500 x 5000 mm (very large format)
- Max. Tool Height: 500 mm
- Connected Load: 500 KW (all tiers)
- Vacuum: Oil-Rotary Vane (Busch/Becker) 300 m³/hr

FOUR TIER OPTIONS:

| Tier | Price | Lead Time | Key Features |
|------|-------|-----------|--------------|
| Basic | ₹1.5 CR | 5 months | Manual, ceramic heaters, bolt tooling |
| Universal | ₹2.0 CR | 6.5 months | Universal frames, quartz heaters |
| Auto | ₹2.7 CR | 6.5 months | Auto loader, all servo drives |
| Pro | ₹3.4 CR | 8 months | Full auto + ducted cooling |

PRICE INCREMENTS:
- Basic → Universal: +₹0.5 CR (+33%)
- Universal → Auto: +₹0.7 CR (+35%)
- Auto → Pro: +₹0.7 CR (+26%)
- Basic → Pro total: +₹1.9 CR (+127%)

KEY INSIGHT:
This tiered approach lets customer choose based on:
1. Budget constraints
2. Production volume requirements
3. Desired automation level
4. Changeover frequency needs""",
        knowledge_type="commercial",
        source_file=SOURCE_FILE,
        entity="Pinnacle Tier Comparison Overview",
        summary="Pinnacle India: 4 PF1 tiers ₹1.5-3.4 CR, 2500x5000mm, Basic/Universal/Auto/Pro",
        metadata={
            "topic": "pinnacle_comparison_overview",
            "customer": "Pinnacle",
            "market": "India",
            "price_range": "₹1.5-3.4 CR"
        }
    ))

    # 2. Basic Tier Details
    items.append(KnowledgeItem(
        text="""PF1 BASIC Tier Specifications - Pinnacle

PRICE: ₹1.5 CR (≈$180K USD)
LEAD TIME: 5 months
FOOTPRINT: 6 x 5 x 4.5 m (smallest)

FEATURES:
✓ Closed Chamber (preblow & sag control)
✓ IR Ceramic Heaters
✓ IR Probe for heating/cooling cycles
✓ Servo Motor Driven bottom table
✓ Oil-Rotary Vane vacuum pump (Busch/Becker 300 m³/hr)

MANUAL OPERATIONS:
✗ Welded Steel Frames (fixed size)
✗ Manual sheet loading
✗ Pneumatic top table, clamping, heater movement
✗ Tool clamping using bolts
✗ Centrifugal blower cooling

TIME METRICS:
- Sheet size changeover: 3 hours
- Sheet load/unload: 15 mins
- Tool setup: 2 hours

BEST FOR:
- Low volume production
- Single product runs (no changeover needed)
- Budget-conscious buyers
- Customers with skilled labor available
- Applications where manual handling is acceptable""",
        knowledge_type="machine_spec",
        source_file=SOURCE_FILE,
        entity="PF1 Basic Tier",
        summary="PF1 Basic ₹1.5CR: Manual load, ceramic heaters, 3hr changeover, bolt tooling, budget option",
        metadata={
            "topic": "pf1_basic_tier",
            "tier": "Basic",
            "price_inr": "1.5 CR"
        }
    ))

    # 3. Universal Tier Details
    items.append(KnowledgeItem(
        text="""PF1 UNIVERSAL Tier Specifications - Pinnacle

PRICE: ₹2.0 CR (≈$240K USD)
LEAD TIME: 6.5 months
FOOTPRINT: 9 x 8 x 4.5 m

UPGRADES FROM BASIC (+₹0.5 CR):
✓ IR Quartz Heaters (faster, more efficient vs ceramic)
✓ Universal Frames (Brass & Aluminium, servo adjusted)
✓ Min. Forming Area: 1500 x 2000 mm (flexible sizing)

KEY IMPROVEMENT - CHANGEOVER:
- Sheet size changeover: 15 mins (vs 3 hours on Basic)
- This is the MAIN value add of Universal tier

STILL MANUAL:
✗ Manual sheet loading
✗ Pneumatic top table, clamping, heater movement
✗ Tool clamping using bolts (but reduced to 30 mins)
✗ Centrifugal blower cooling

TIME METRICS:
- Sheet size changeover: 15 mins (12x faster!)
- Sheet load/unload: 15 mins
- Tool setup: 30 mins (4x faster than Basic)

BEST FOR:
- Multiple product sizes
- Frequent changeovers needed
- Medium volume production
- Customers who value flexibility
- Growing businesses that may add products""",
        knowledge_type="machine_spec",
        source_file=SOURCE_FILE,
        entity="PF1 Universal Tier",
        summary="PF1 Universal ₹2.0CR: Quartz heaters, universal frames, 15min changeover (vs 3hr Basic)",
        metadata={
            "topic": "pf1_universal_tier",
            "tier": "Universal",
            "price_inr": "2.0 CR"
        }
    ))

    # 4. Auto Tier Details
    items.append(KnowledgeItem(
        text="""PF1 AUTO Tier Specifications - Pinnacle

PRICE: ₹2.7 CR (≈$325K USD)
LEAD TIME: 6.5 months
FOOTPRINT: 9 x 5 x 5 m

UPGRADES FROM UNIVERSAL (+₹0.7 CR):
✓ Automatic Sheet Loader (Servo Motor Driven)
✓ ALL movements now Servo Motor Driven:
  - Bottom table (already servo)
  - Top table (was pneumatic)
  - Sheet clamping (was pneumatic)
  - Heater movement (was pneumatic)
✓ Pneumatic Locking for tools (vs bolts)

KEY IMPROVEMENTS:
1. AUTOMATION - Sheet loading is automatic
2. ALL SERVO - Precision, energy efficiency, soft release
3. FASTER TOOL CHANGE - Pneumatic vs bolt clamping

TIME METRICS:
- Sheet size changeover: 3 hours (back to Basic level - welded frames)
- Sheet load/unload: 3 mins (5x faster than Universal!)
- Tool setup: 30 mins

NOTE: Auto tier uses Welded Steel Frames (not universal)
This is intentional - for high volume single product runs
where auto-loading matters more than size flexibility.

BEST FOR:
- High volume production
- Single product focus
- Labor cost reduction priority
- Consistent cycle time needs
- 24/7 operation requirements""",
        knowledge_type="machine_spec",
        source_file=SOURCE_FILE,
        entity="PF1 Auto Tier",
        summary="PF1 Auto ₹2.7CR: Auto loader, all servo drives, 3min load time, high volume focus",
        metadata={
            "topic": "pf1_auto_tier",
            "tier": "Auto",
            "price_inr": "2.7 CR"
        }
    ))

    # 5. Pro Tier Details
    items.append(KnowledgeItem(
        text="""PF1 PRO Tier Specifications - Pinnacle

PRICE: ₹3.4 CR (≈$410K USD)
LEAD TIME: 8 months (longest)
FOOTPRINT: 16 x 8 x 5 m (largest)

THE COMPLETE PACKAGE - ALL FEATURES:
✓ Automatic Sheet Loader (Servo Motor Driven)
✓ ALL movements Servo Motor Driven
✓ Universal Frames (Brass & Aluminium, servo adjusted)
✓ Pneumatic Tool Locking
✓ Central Ducted Cooling (fastest cooling)
✓ IR Quartz Heaters

TIME METRICS - ALL BEST IN CLASS:
- Sheet size changeover: 15 mins (Universal frames)
- Sheet load/unload: 3 mins (Auto loader)
- Tool setup: 30 mins (Pneumatic locking)

COMPARISON TO OTHER TIERS:
| Feature | Basic | Universal | Auto | Pro |
|---------|-------|-----------|------|-----|
| Universal Frames | ✗ | ✓ | ✗ | ✓ |
| Auto Loader | ✗ | ✗ | ✓ | ✓ |
| All Servo | ✗ | ✗ | ✓ | ✓ |
| Ducted Cooling | ✗ | ✗ | ✗ | ✓ |

PRO = Universal + Auto + Ducted Cooling

BEST FOR:
- Premium production needs
- Maximum flexibility + automation
- Multiple products, high volumes
- Fastest cycle times required
- Companies prioritizing efficiency over cost""",
        knowledge_type="machine_spec",
        source_file=SOURCE_FILE,
        entity="PF1 Pro Tier",
        summary="PF1 Pro ₹3.4CR: Full auto + universal frames + ducted cooling, best-in-class everything",
        metadata={
            "topic": "pf1_pro_tier",
            "tier": "Pro",
            "price_inr": "3.4 CR"
        }
    ))

    # 6. Sales Strategy - Tier Selling
    items.append(KnowledgeItem(
        text="""PF1 Tiered Sales Strategy - Pinnacle Example

PRESENTING OPTIONS TO INDIAN CUSTOMERS:

1. GOOD-BETTER-BEST-PREMIUM Approach:
   - Basic: Entry point, proves capability
   - Universal: Sweet spot for flexibility
   - Auto: High volume automation
   - Pro: No compromise option

2. PRICE ANCHORING:
   - Show Pro first (₹3.4 CR) to anchor high
   - Then show Basic (₹1.5 CR) as affordable
   - Customer often lands on Universal/Auto middle ground

3. FEATURE-BASED SELLING:

   If customer needs FLEXIBILITY (multiple sizes):
   → Recommend Universal or Pro
   → Highlight 15-min changeover vs 3-hour

   If customer needs VOLUME (single product):
   → Recommend Auto or Pro
   → Highlight 3-min load time vs 15-min

   If customer needs BOTH:
   → Pro is the only option
   → Worth the premium

4. ROI CALCULATION POINTS:
   - Universal saves 2.75 hours per changeover
   - Auto saves 12 mins per cycle (sheet handling)
   - Pro combines both savings

5. UPGRADE PATH:
   - Start with Basic, upgrade later possible
   - But Pro components harder to retrofit
   - Better to buy right tier upfront

COMPARISON VS COMPETITORS:
- Similar Cannon/Geiss machine: ₹5-6 CR
- Machinecraft Pro at ₹3.4 CR = 40% savings
- Even Pro tier is cheaper than competitor basic""",
        knowledge_type="commercial",
        source_file=SOURCE_FILE,
        entity="PF1 Tier Sales Strategy",
        summary="PF1 tier selling: Good-better-best approach, feature-based recommendation, 40% vs competitors",
        metadata={
            "topic": "pf1_tier_sales_strategy",
            "approach": "tiered_selling"
        }
    ))

    return items


def main():
    """Main ingestion function."""
    print("=" * 60)
    print("Pinnacle Machine Comparison Ingestion")
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
