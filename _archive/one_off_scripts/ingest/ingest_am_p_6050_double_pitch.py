#!/usr/bin/env python3
"""
Ingest AM-P-6050 Double Pitch Heaters Quotation

AM-P with DOUBLE PITCH heating system - top heaters only with 2-pitch length.
This configuration is ideal for:
- Polycarbonate (PC) - needs longer heating time
- Polypropylene (PP) - needs uniform heating
- Deep draw applications
- Parts requiring fine detail

Price: ₹62 Lakhs (~$74K USD) - premium over standard AM-P due to double pitch
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from openclaw.agents.ira.src.brain.knowledge_ingestor import KnowledgeIngestor, KnowledgeItem

SOURCE_FILE = "AM-P-6050 Double Pitch Heaters.pdf"


def create_knowledge_items() -> list[KnowledgeItem]:
    """Create structured knowledge items from the AM-P double pitch quotation."""
    items = []

    # 1. Double Pitch Heater Concept
    items.append(KnowledgeItem(
        text="""AM-P Double Pitch Heater Configuration - Technical Explanation

WHAT IS DOUBLE PITCH HEATING:
"Pitch" refers to the indexing distance the material moves per cycle.
- Single Pitch: Material moves one forming area length per cycle
- Double Pitch: Heater oven is 2x the forming area length

DOUBLE PITCH CONFIGURATION:
- Heater Zone: 2 × forming pitch length
- Material spends TWO cycles under heaters before forming
- Longer dwell time = more uniform heating
- Better for thick materials and demanding plastics

WHY DOUBLE PITCH FOR PC AND PP:

POLYCARBONATE (PC):
- High heat resistance (Tg ~147°C)
- Needs longer heating time to reach forming temperature
- Risk of uneven heating with single pitch
- Double pitch ensures thorough, uniform heating
- Better for deep draws in PC

POLYPROPYLENE (PP):
- Semi-crystalline material
- Narrow forming temperature window
- Needs precise, uniform temperature distribution
- Double pitch provides extended, controlled heating
- Reduces risk of cold spots

CONFIGURATION IN THIS MACHINE:
- Single Heating: TOP OVEN ONLY (not sandwich)
- Double Pitch: 2-pitch heater length
- IR Ceramic elements in grid formation
- Individual element percentage control
- PID temperature control per zone

TRADE-OFF:
- Longer machine footprint (2-pitch heater length)
- Higher cost (₹62L vs ₹35L for standard)
- But: Better quality parts in PC/PP materials""",
        knowledge_type="process",
        source_file=SOURCE_FILE,
        entity="AM-P",
        summary="Double pitch heaters: 2x heating length for PC/PP, longer dwell time, uniform heat",
        metadata={
            "topic": "double_pitch_concept",
            "heater_type": "top_only_2_pitch",
            "ideal_materials": ["PC", "PP"],
            "benefit": "uniform_heating"
        }
    ))

    # 2. Technical Specifications
    items.append(KnowledgeItem(
        text="""AM-P-6050 Double Pitch - Technical Specifications

FORMING CAPABILITIES:
- Forming Area: 500 × 600 mm (same as standard AM-P-5060)
- Max Forming Depth: Up to 60 mm
- Sheet Width: 670 mm maximum
- Sheet Thickness: 0.5 - 2.0 mm

MATERIALS OPTIMIZED FOR:
- HIPS (High Impact Polystyrene)
- ABS
- PVC
- PET
- PC (Polycarbonate) ⭐ Enhanced capability
- PP (Polypropylene) ⭐ Enhanced capability

PRODUCTION:
- Speed: Up to 10 cycles/min
- Note: Effective heating time is 2x due to double pitch

HEATING SYSTEM (KEY DIFFERENCE):
- Configuration: Single heating, TOP ONLY
- Pitch Length: DOUBLE (2-pitch)
- Heater Type: IR Ceramic elements in grid
- Control: Individual element percentage control
- Temperature: PID control per zone
- Movement: Pneumatic heater positioning

FORMING STATION:
- Type: Pressure forming press
- Mechanism: Toggle mechanism (for high pressure)
- Capability: Sustains up to 6 bar compressed air
- Features: Vacuum + compressed air capability

MATERIAL HANDLING:
- Roll Feeding: Servo-driven spike chain
- Spike Chain: 1/2" duplex with 1" spike spacing
- Servo Motor: 2kW with precision gearbox
- Roll Loading: Manual with automatic unwinding
- Loop Sensing: For continuous operation
- Eye Mark Detection: For pre-printed sheets

CUTTING:
- Automatic pneumatic shear at exit

POWER:
- Electrical: 100 kW, 415V 3-Phase
- Air Pressure: 6 bar, clean & dry

ANCILLARY REQUIREMENTS:
- Chiller: 5 ton + MTC
- Air Compressor: 20 HP, 60 cfm at 6 bar""",
        knowledge_type="machine_spec",
        source_file=SOURCE_FILE,
        entity="AM-P-6050",
        summary="AM-P-6050 double pitch: top heaters 2-pitch, 6 bar toggle press, PC/PP optimized",
        metadata={
            "topic": "specifications",
            "forming_area_mm": "500x600",
            "heater_config": "top_only_double_pitch",
            "max_pressure_bar": 6,
            "ideal_materials": ["PC", "PP"]
        }
    ))

    # 3. Pricing Comparison
    items.append(KnowledgeItem(
        text="""AM-P Double Pitch Pricing vs Standard AM-P

DOUBLE PITCH VERSION (AM-P-6050):
- Base Machine: ₹62,00,000 (~$74,000 USD)
- Installation: ₹2,00,000
- Training: ₹1,00,000
- Shipping (India): ₹1,50,000
- Total Package: ₹66,50,000 + 18% GST (~$80,000 USD)

STANDARD VERSION (AM-P-5060):
- Base Machine: ₹35,00,000 (~$42,000 USD)
- Total Package: ₹39,50,000 + 18% GST (~$47,000 USD)

PRICE DIFFERENCE:
- Base machine: ₹27,00,000 more (77% premium)
- Total package: ₹27,00,000 more
- USD difference: ~$32,000 more

WHY THE PREMIUM:
1. Double pitch heater oven (larger, more elements)
2. Toggle mechanism forming station (higher pressure capability)
3. Enhanced for demanding materials (PC, PP)
4. Better part quality for deep draws
5. Longer machine footprint

WHEN TO RECOMMEND DOUBLE PITCH (Higher Price):
- Customer processing PC (polycarbonate)
- Customer processing PP (polypropylene)
- Deep draw requirements with fine detail
- Quality-critical applications
- Parts competing with injection molding aesthetics
- Thick gauge PC/PP materials

WHEN STANDARD IS SUFFICIENT (Lower Price):
- HIPS, ABS, PET, PVC processing
- Standard draw depths
- Less demanding surface quality
- Cost-sensitive applications
- Thinner gauge materials""",
        knowledge_type="commercial",
        source_file=SOURCE_FILE,
        entity="AM-P-6050",
        summary="AM-P double pitch: ₹62L (~$74K) vs standard ₹35L - 77% premium for PC/PP capability",
        metadata={
            "topic": "pricing_comparison",
            "double_pitch_price_inr": 6200000,
            "standard_price_inr": 3500000,
            "premium_percent": 77,
            "double_pitch_usd": 74000
        }
    ))

    # 4. Application Guide - When to Use Double Pitch
    items.append(KnowledgeItem(
        text="""AM-P Double Pitch - Application Guide

IDEAL APPLICATIONS FOR DOUBLE PITCH:

1. POLYCARBONATE (PC) PARTS:
- Transparent/translucent containers
- Electronic device housings
- Safety equipment covers
- Medical device components
- Parts requiring optical clarity + deep draw

2. POLYPROPYLENE (PP) PARTS:
- Chemical-resistant containers
- Food-grade packaging (hot fill capable)
- Automotive under-hood components
- Industrial containers
- Parts requiring chemical resistance + deep draw

3. DEEP DRAW + FINE DETAIL:
- Parts with draw depth approaching 60mm
- Sharp corner definition needed
- Fine texture reproduction
- Complex geometry
- Thin wall sections in deep areas

4. THICK GAUGE PROCESSING:
- Materials 1.5mm - 2.0mm thick
- PC sheets requiring thorough heating
- PP sheets with crystalline structure

TYPICAL PRODUCTS:
- Automotive dashboard components (PC)
- Food storage containers (PP)
- Electronic housings (PC)
- Chemical containers (PP)
- Safety guards (PC)
- Medical trays (PC/PP)

WHY PC AND PP NEED DOUBLE PITCH:

PC (Polycarbonate):
- Glass transition temp: ~147°C
- Processing temp: 175-195°C
- Needs uniform through-thickness heating
- Single pitch risks surface heating only
- Double pitch ensures core reaches temperature

PP (Polypropylene):
- Semi-crystalline polymer
- Melting point: ~165°C
- Narrow forming window (10-15°C range)
- Needs very uniform temperature distribution
- Cold spots cause forming failures
- Double pitch eliminates temperature gradients""",
        knowledge_type="application",
        source_file=SOURCE_FILE,
        entity="AM-P",
        summary="Double pitch for PC/PP: thick gauge, deep draw, fine detail, uniform heating critical",
        metadata={
            "topic": "application_guide",
            "pc_processing_temp_c": "175-195",
            "pp_melting_point_c": 165,
            "applications": ["electronics", "automotive", "medical", "food_packaging"]
        }
    ))

    # 5. Toggle Mechanism & 6 Bar Capability
    items.append(KnowledgeItem(
        text="""AM-P Double Pitch - Toggle Mechanism & High Pressure Forming

TOGGLE MECHANISM FOR FORMING STATION:

What is a Toggle Mechanism:
- Mechanical linkage system that multiplies force
- Locks at full extension with high mechanical advantage
- Maintains constant pressure during forming cycle
- Can sustain up to 6 bar compressed air pressure

Why Toggle for Pressure Forming:
- Standard pneumatic cylinders flex under pressure
- Toggle provides rigid, locked position
- Maintains exact forming pressure throughout cycle
- Better part consistency and detail reproduction

6 BAR PRESSURE CAPABILITY:
- Standard vacuum forming: ~0.9 bar differential
- Pressure forming with 6 bar: ~7 bar total differential
- Nearly 8x the forming force vs vacuum-only

BENEFITS OF HIGH PRESSURE FORMING:
1. Deeper draws without thinning
2. Sharper detail definition
3. Better texture reproduction from mold
4. Tighter corner radii
5. Faster cycle times (material moves faster into mold)
6. Thicker materials can be formed precisely

FOR PC AND PP SPECIFICALLY:
- PC: High melt strength, needs pressure to form fine details
- PP: Semi-crystalline, pressure helps achieve sharp definition
- Both benefit from locked toggle position during cooling

COMPARISON:
| Feature | Standard Pneumatic | Toggle Mechanism |
|---------|-------------------|------------------|
| Max Pressure | ~3-4 bar | 6 bar sustained |
| Position Hold | Slight flex | Rigid lock |
| Detail Definition | Good | Excellent |
| Deep Draw | Limited | Enhanced |
| Cost | Lower | Higher |""",
        knowledge_type="machine_spec",
        source_file=SOURCE_FILE,
        entity="AM-P",
        summary="Toggle mechanism sustains 6 bar pressure, rigid lock for PC/PP deep draw detail",
        metadata={
            "topic": "toggle_mechanism",
            "max_pressure_bar": 6,
            "mechanism": "toggle",
            "benefit": "rigid_lock_high_pressure"
        }
    ))

    # 6. Commercial Terms
    items.append(KnowledgeItem(
        text="""AM-P-6050 Double Pitch - Commercial Terms

PRICING SUMMARY:
- Base Machine: ₹62,00,000 (~$74,000 USD)
- Installation: ₹2,00,000
- Training (3 days): ₹1,00,000
- Shipping (India): ₹1,50,000
- TOTAL: ₹66,50,000 + GST 18%

LEAD TIME:
- 4 months from PO & advance payment

PAYMENT TERMS:
- 50% advance with purchase order
- 50% before dispatch from Machinecraft

SHIPPING:
- EXW Machinecraft plant, Gujarat, India
- India shipping included in package price
- International: Quote separately

INSTALLATION & TRAINING:
- Installation: 1 technician, 3 days on-site
- Training: 2-3 days operator training
- Client provides: Utilities (power, air), test material

WARRANTY:
- 12 months from date of commissioning

QUOTATION VALIDITY:
- 30 days from date of issue

ANCILLARY EQUIPMENT NEEDED:
- Chiller: 5 ton capacity + MTC
- Air Compressor: 20 HP, 60 cfm at 6 bar
- Electrical: 100 kW, 415V 3-Phase connection

CONTACT:
- Sales Team: +91-22-28817785
- Email: sales@machinecraft.org""",
        knowledge_type="commercial",
        source_file=SOURCE_FILE,
        entity="AM-P-6050",
        summary="AM-P-6050 double pitch: ₹62L base, ₹66.5L package, 4mo lead, 50/50 payment",
        metadata={
            "topic": "commercial_terms",
            "base_price_inr": 6200000,
            "package_price_inr": 6650000,
            "lead_time_months": 4,
            "warranty_months": 12
        }
    ))

    return items


def main():
    """Main ingestion function."""
    print("=" * 60)
    print("AM-P-6050 Double Pitch Heaters Quotation Ingestion")
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
