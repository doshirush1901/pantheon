#!/usr/bin/env python3
"""
Ingest AM-V-5060 Vacuum Forming Machine Quotation

Entry-level roll-fed vacuum forming machine.
Vacuum only (no pressure forming) - budget option for Indian market.

Key specs:
- Forming Area: 500 x 600 mm
- Vacuum only (no pressure)
- 12 cycles/min dry
- 16 kW power
- Price: ₹7.5 Lakhs (~$9K USD) - very affordable
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from openclaw.agents.ira.src.brain.knowledge_ingestor import KnowledgeIngestor, KnowledgeItem

SOURCE_FILE = "AM-V-5060 Quote Master Format.pdf"


def create_knowledge_items() -> list[KnowledgeItem]:
    """Create structured knowledge items from the AM-V-5060 quotation."""
    items = []

    # 1. Machine Overview
    items.append(KnowledgeItem(
        text="""AM-V-5060 - Vacuum Forming Machine Overview

MODEL: AM-V-5060
TYPE: Roll-Fed Vacuum Forming Machine (Vacuum Only)
CATEGORY: Entry-level continuous thermoformer

KEY DISTINCTION:
- "V" = Vacuum only (NO pressure forming)
- Compare to AM-P = Pressure + Vacuum
- Lower cost, simpler operation
- Suitable for products not requiring fine detail

APPLICATION:
- Thin gauge packaging
- Disposables
- Containers
- Food trays
- Simple packaging products

OPERATION CONCEPT:
- Roll-fed continuous operation
- Servo-driven spike chain advancement
- Automatic: heating → forming → cutting
- Minimal operator intervention

TARGET MARKET:
- India (primary market)
- Budget-conscious manufacturers
- Startups in packaging
- Simple product requirements
- Cost-sensitive applications

WHY CHOOSE AM-V OVER AM-P:
- 50% lower cost
- Simpler maintenance
- Adequate for basic shapes
- No compressed air complexity
- Good for HIPS, PVC, PET, ABS

WHY CHOOSE AM-P INSTEAD:
- Need fine detail/texture
- Deep draw applications
- Polycarbonate forming
- Tighter corners required
- Premium product appearance""",
        knowledge_type="machine_spec",
        source_file=SOURCE_FILE,
        entity="AM-V-5060",
        summary="AM-V-5060: Entry-level vacuum-only roll-fed thermoformer for thin gauge packaging",
        metadata={
            "topic": "machine_overview",
            "model": "AM-V-5060",
            "type": "vacuum_only",
            "market": "India"
        }
    ))

    # 2. Technical Specifications
    items.append(KnowledgeItem(
        text="""AM-V-5060 Technical Specifications

FORMING CAPABILITY:
- Forming Area: 500 × 600 mm
- Max Forming Depth: 100 mm (below sheet line)
- Max Forming Height: 90 mm (above sheet line)
- Total Draw: 190 mm combined

SHEET HANDLING:
- Max Sheet Width: 670 mm
- Sheet Thickness: 0.3 - 1.5 mm
- Feed Type: Roll-fed (continuous)

MATERIALS SUPPORTED:
- HIPS (High Impact Polystyrene)
- PVC (Polyvinyl Chloride)
- PET (Polyethylene Terephthalate)
- ABS (Acrylonitrile Butadiene Styrene)
- Note: PC and PP NOT recommended (need pressure forming)

SPEED:
- Dry Cycle: Up to 12 cycles per minute
- Actual production varies with material/depth

FORMING SYSTEM:
- Vacuum forming only
- Pneumatic forming press
- Vacuum pump: 600 LPM capacity
- No pressure assist (vacuum ~0.9 bar differential max)

POWER:
- Connected Load: 16 kW
- Supply: 400 V, 3-Phase

UTILITIES:
- Compressed Air: 6 bar (clean & dry)
- For pneumatics only (not forming)

INDEXING ACCURACY:
- Servo precision: ±0.5 mm""",
        knowledge_type="machine_spec",
        source_file=SOURCE_FILE,
        entity="AM-V-5060",
        summary="AM-V-5060: 500x600mm, 100mm depth, 0.3-1.5mm sheet, 12 cpm, 16kW, vacuum only",
        metadata={
            "topic": "specifications",
            "forming_area_mm": "500x600",
            "forming_depth_mm": 100,
            "sheet_thickness_mm": "0.3-1.5",
            "power_kw": 16,
            "cycles_per_min": 12,
            "vacuum_lpm": 600
        }
    ))

    # 3. System Components
    items.append(KnowledgeItem(
        text="""AM-V-5060 System Components

1. ROLL FEEDING SYSTEM:
- Servo-driven spike chain
- Chain spec: 1/2" duplex with 1" spike spacing
- Motor: 750 W servo with precision gearbox
- Automatic sheet advancement
- Precision indexing

2. HEATING SYSTEM:
- Type: Infrared ceramic elements
- Configuration: 32 elements (8 rows × 4 elements per row)
- Temperature Zones: 8 independent zones
- Control: PID for each row
- Heater Position: Top only (movable oven)
- Note: No bottom heating (simpler design)

3. FORMING STATION:
- Type: Pneumatic press
- Capability: Vacuum forming only
- Tool Change: Manual bolting
- No quick-change system (cost saving)

4. CUTTING SYSTEM:
- Type: Automatic pneumatic shear
- Location: At exit
- Operation: Integrated with cycle

5. CONTROL SYSTEM:
- PLC-based control
- HMI touchscreen interface
- Safety interlocks
- Emergency stops
- International safety standards

COMPARISON TO AM-P-5060:
| Feature | AM-V-5060 | AM-P-5060 |
|---------|-----------|-----------|
| Forming | Vacuum only | Vacuum + 6 bar |
| Heaters | Top only | Sandwich |
| Power | 16 kW | 35 kW |
| Price | ₹7.5L | ₹35L |
| Detail | Basic | Fine detail |""",
        knowledge_type="machine_spec",
        source_file=SOURCE_FILE,
        entity="AM-V-5060",
        summary="AM-V components: spike chain, 32 IR elements (8 zones), PLC/HMI, pneumatic shear",
        metadata={
            "topic": "components",
            "heater_elements": 32,
            "heater_zones": 8,
            "heater_position": "top_only",
            "servo_motor_w": 750
        }
    ))

    # 4. Pricing
    items.append(KnowledgeItem(
        text="""AM-V-5060 Pricing (2025)

BASE MACHINE:
- Price: ₹7,50,000 (Seven Lakhs Fifty Thousand INR)
- Equivalent: ~$9,000 USD
- Basis: EXW Machinecraft plant, Gujarat, India

OPTIONAL SERVICES:
- Installation by Machinecraft: ₹50,000 extra
- Operator Training (2 days): ₹50,000 extra
- Total with options: ₹8,50,000 (~$10,200 USD)

TAXES:
- GST @ 18% extra as applicable
- Total with GST: ~₹8,85,000 (base only)
- Total with options + GST: ~₹10,03,000

COMMERCIAL TERMS:
- Lead Time: 2 months from PO + advance
- Payment: 50% advance with order
- Balance: 50% before dispatch
- Shipping: EXW Gujarat, India
- Warranty: 12 months from commissioning
- Quote Validity: 30 days

PRICE COMPARISON - AM SERIES:
| Model | Forming | Price (₹) | Price ($) |
|-------|---------|-----------|-----------|
| AM-V-5060 | Vacuum only | 7.5L | ~$9K |
| AM-P-5060 | Pressure | 35L | ~$42K |
| AM-P-6050 Double Pitch | Pressure | 62L | ~$74K |

VALUE PROPOSITION:
- Most affordable Machinecraft machine
- Entry point for thermoforming
- Good for:
  * Startups
  * Low-volume production
  * Simple packaging products
  * Training/learning
- Upgrade path to AM-P available later""",
        knowledge_type="commercial",
        source_file=SOURCE_FILE,
        entity="AM-V-5060",
        summary="AM-V-5060: ₹7.5L (~$9K) EXW Gujarat, 2 months lead, 50/50 payment, 12 mo warranty",
        metadata={
            "topic": "pricing",
            "base_price_inr": 750000,
            "base_price_usd": 9000,
            "installation_inr": 50000,
            "training_inr": 50000,
            "lead_months": 2,
            "warranty_months": 12
        }
    ))

    # 5. AM-V vs AM-P Decision Guide
    items.append(KnowledgeItem(
        text="""AM-V-5060 vs AM-P-5060 - Selection Guide

CHOOSE AM-V-5060 WHEN:

1. BUDGET PRIORITY:
   - ₹7.5L vs ₹35L (78% savings!)
   - Limited capital available
   - Need to start small
   - Testing the market

2. SIMPLE PRODUCTS:
   - Basic containers/trays
   - No fine detail needed
   - Shallow draws (<60mm typical)
   - Rounded corners acceptable

3. STANDARD MATERIALS:
   - HIPS, PVC, PET, ABS
   - Thin gauge (0.3-1.5mm)
   - Easy-forming plastics

4. INDIAN MARKET:
   - Cost-competitive products
   - Disposable packaging
   - Local competition on price
   - Volume over premium

5. LOW RISK ENTRY:
   - First thermoforming machine
   - Learning the process
   - Proving the business model

CHOOSE AM-P-5060 INSTEAD WHEN:

1. QUALITY REQUIREMENTS:
   - Fine detail/texture needed
   - Sharp corners required
   - Premium appearance
   - Export quality products

2. DIFFICULT MATERIALS:
   - Polycarbonate (PC)
   - Polypropylene (PP)
   - Thick gauge materials
   - Deep draw applications

3. TECHNICAL PRODUCTS:
   - Industrial parts
   - Medical trays
   - Automotive interior
   - Technical precision needed

4. INTERNATIONAL MARKETS:
   - Export products
   - Higher margins
   - Quality differentiation

VACUUM VS PRESSURE FORMING - TECHNICAL DIFFERENCE:
- Vacuum: ~0.9 bar differential (atmospheric - vacuum)
- Pressure: 4-6 bar differential (vacuum + compressed air)
- 5-6x more force with pressure forming
- Pressure gives: sharper detail, tighter corners, better texture

UPGRADE PATH:
- Start with AM-V-5060 to learn
- Graduate to AM-P when demand grows
- Trade-in/upgrade programs available""",
        knowledge_type="application",
        source_file=SOURCE_FILE,
        entity="AM-V-5060",
        summary="AM-V for budget/simple products; AM-P for quality/difficult materials; ₹7.5L vs ₹35L",
        metadata={
            "topic": "selection_guide",
            "comparison": ["AM-V-5060", "AM-P-5060"],
            "price_difference": "78% savings"
        }
    ))

    # 6. Manufacturing Location Note
    items.append(KnowledgeItem(
        text="""AM-V-5060 Manufacturing & Support

MANUFACTURING LOCATION:
- Factory: Machinecraft Technologies
- Address: Plot 92 Dehri Road, Umbergaon, Dist. Valsad, Gujarat-396170, India
- Note: Different from Mumbai office

CONTACT:
- Sales: +91-22-28817785
- Email: sales@machinecraft.org
- Technical Support: support@machinecraft.org
- Website: www.machinecraft.org

SHIPPING POINT:
- EXW Machinecraft plant, Gujarat
- Customer arranges transport from factory
- Packing charges may apply extra

WARRANTY & SUPPORT:
- 12 months from commissioning
- Technical support included
- Spare parts available
- Training available (optional)

TARGET GEOGRAPHY:
- Primary: India domestic market
- Shipping point in Gujarat advantageous for:
  * Western India customers
  * Export via Mundra/Nhava Sheva ports
- For international: Consider AM-P series for broader capability

QUICK DELIVERY:
- 2 months is fast for thermoforming equipment
- Stock components may reduce further
- Check current availability""",
        knowledge_type="commercial",
        source_file=SOURCE_FILE,
        entity="AM-V-5060",
        summary="Made in Gujarat factory, EXW shipping, 12 mo warranty, India market focus",
        metadata={
            "topic": "manufacturing",
            "factory_location": "Umbergaon, Gujarat",
            "shipping_point": "Gujarat",
            "market": "India"
        }
    ))

    return items


def main():
    """Main ingestion function."""
    print("=" * 60)
    print("AM-V-5060 Vacuum Forming Machine Quotation Ingestion")
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
