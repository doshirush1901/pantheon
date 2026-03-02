#!/usr/bin/env python3
"""
Ingest AM-P-5060 Quotation - Pressure Forming Machine

AM-P series = AM series with PRESSURE FORMING capability
Key difference: Vacuum + Compressed Air for deep draws and fine details

Specs: 500x600mm forming, roll-fed, up to 60mm depth, 10 cycles/min
Price: ₹35 Lakhs base (~$42K USD)
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from openclaw.agents.ira.src.brain.knowledge_ingestor import KnowledgeIngestor, KnowledgeItem

SOURCE_FILE = "Machinecraft_AM-P-5060 Quote .pdf"


def create_knowledge_items() -> list[KnowledgeItem]:
    """Create structured knowledge items from the AM-P-5060 quotation."""
    items = []

    # 1. Machine Overview - What is AM-P Series
    items.append(KnowledgeItem(
        text="""AM-P-5060 Machine Overview - Pressure Forming Series

MODEL NAMING:
- AM = Entry/compact series
- P = PRESSURE FORMING capability (vacuum + compressed air)
- 5060 = 500mm × 600mm forming area

WHAT MAKES IT "PRESSURE FORMING":
Unlike standard vacuum forming that only uses vacuum (~0.9 bar differential),
pressure forming uses BOTH:
- Vacuum from below (pulls material down)
- Compressed air from above (pushes material into mold)

Combined pressure differential can be 4-6 bar, enabling:
- Deeper draws (up to 60mm)
- Sharper detail definition
- Better texture reproduction
- Tighter corners and radii
- Thicker material processing

MACHINE TYPE:
- Continuous Roll-Fed operation
- Pressure Forming capability
- Single integrated process line

TARGET APPLICATIONS:
- Thick gauge packaging
- Automotive parts
- Deep draw containers
- Parts requiring fine surface detail
- Pre-printed material forming (eye mark detection)

MATERIALS SUITED:
- HIPS (High Impact Polystyrene)
- ABS
- PVC
- PET
- PC (Polycarbonate)
- Thickness range: 0.5 - 2.0 mm""",
        knowledge_type="machine_spec",
        source_file=SOURCE_FILE,
        entity="AM-P-5060",
        summary="AM-P-5060: Pressure forming (vacuum+air) roll-fed, 500x600mm, for deep draws",
        metadata={
            "topic": "machine_overview",
            "model": "AM-P-5060",
            "forming_type": "pressure_forming",
            "material_feed": "roll_fed"
        }
    ))

    # 2. Technical Specifications
    items.append(KnowledgeItem(
        text="""AM-P-5060 Technical Specifications

FORMING CAPABILITIES:
- Forming Area: 500 × 600 mm
- Max Forming Depth: Up to 60 mm (enhanced by pressure)
- Sheet Width: 670 mm maximum
- Sheet Thickness: 0.5 - 2.0 mm

PRODUCTION PERFORMANCE:
- Production Speed: Up to 10 cycles/minute
- Indexing Accuracy: ±0.3mm (servo-driven)
- Operation: Continuous roll-fed

MATERIAL HANDLING:
- Roll Feeding: Servo-driven spike chain
- Spike Chain: 1/2" duplex with 1" spike spacing
- Servo Motor: 2kW with precision gearbox
- Roll Loading: Manual with automatic unwinding
- Loop Sensing: For continuous operation
- Eye Mark Detection: For pre-printed sheet alignment

HEATING SYSTEM:
- Configuration: Sandwich (top and bottom)
- Heater Type: Infrared ceramic elements in grid
- Control: Individual element percentage control
- Temperature: PID control for each zone
- Safety: Light sensor for sheet sag detection
- Movement: Pneumatic heater positioning

FORMING STATION:
- Type: Pressure forming press
- Vacuum: Yes (standard)
- Compressed Air: Yes (pressure forming capability)
- Max Depth: 60mm
- Tool Change: Pneumatic assistance
- Tool Clamping: Quick clamp with Segen cylinders

CUTTING SYSTEM:
- Type: Automatic pneumatic shear
- Location: Exit of forming station

POWER REQUIREMENTS:
- Electrical: 100 kW, 415V 3-Phase
- Air Pressure: 6 bar, clean & dry

ANCILLARY EQUIPMENT NEEDED:
- Chiller: 5 ton + MTC (Mold Temperature Controller)
- Air Compressor: 20 HP, 60 cfm at 6 bar""",
        knowledge_type="machine_spec",
        source_file=SOURCE_FILE,
        entity="AM-P-5060",
        summary="AM-P-5060 specs: 60mm depth, 10 cycles/min, 100kW, servo spike chain ±0.3mm",
        metadata={
            "topic": "specifications",
            "forming_area_mm": "500x600",
            "max_depth_mm": 60,
            "cycles_per_min": 10,
            "power_kw": 100,
            "sheet_thickness_mm": "0.5-2.0"
        }
    ))

    # 3. Key Features & Capabilities
    items.append(KnowledgeItem(
        text="""AM-P-5060 Key Features & Capabilities

1. ROLL-FED SYSTEM:
- Continuous operation (no sheet-by-sheet loading)
- Servo-driven spike chain for precise indexing
- ±0.3mm accuracy
- Manual roll loading, automatic unwinding
- Loop sensing for uninterrupted production

2. PRESSURE FORMING:
- Vacuum PLUS compressed air capability
- Enhanced forming depth (up to 60mm)
- Better detail reproduction than vacuum-only
- Sharper corners and finer textures
- Suitable for deeper draws and complex shapes

3. SANDWICH HEATING:
- Top and bottom infrared heaters
- Uniform heating through material thickness
- Multi-pitch heater arrangement
- Individual element percentage control
- PID temperature control per zone

4. EYE MARK DETECTION:
- Automatic alignment for pre-printed materials
- Sensor detects registration marks
- Ensures print-to-form alignment
- Critical for branded packaging

5. PRECISION CONTROL:
- Servo indexing with ±0.3mm accuracy
- PLC-based control system
- HMI touchscreen interface
- Recipe storage and recall
- Production monitoring and diagnostics

6. AUTOMATIC CUTTING:
- Pneumatic shot cutter at exit
- Integrated into production line
- No separate cutting operation needed

7. SAFETY SYSTEMS:
- Compliant with international standards
- Safety interlocks
- Emergency stops
- Light sensor sag detection""",
        knowledge_type="machine_spec",
        source_file=SOURCE_FILE,
        entity="AM-P-5060",
        summary="Key features: pressure forming, eye mark detection, ±0.3mm servo, auto cutting",
        metadata={
            "topic": "key_features",
            "pressure_forming": True,
            "eye_mark": True,
            "auto_cutting": True,
            "servo_accuracy_mm": 0.3
        }
    ))

    # 4. Pricing
    items.append(KnowledgeItem(
        text="""AM-P-5060 Pricing (January 2025)

BASE MACHINE PRICING:
- Base Machine (AM-P-5060 Standard Configuration): ₹35,00,000
- Installation (by Machinecraft technicians): ₹2,00,000
- Training (3 days operator training): ₹1,00,000
- Shipping (within India): ₹1,50,000

TOTAL PACKAGE: ₹39,50,000 + GST @ 18%
(Approximately $47,000 USD complete)

BASE MACHINE ONLY: ₹35,00,000
(Approximately $42,000 USD)

PRICE CONTEXT:
- Entry/mid-level pressure forming machine
- Roll-fed continuous operation
- Includes pressure forming capability
- Good for thick gauge packaging production

PRICE PER SQ METER FORMING AREA:
- Forming area: 500 × 600 = 0.3 sq meters
- Price per sq meter: ₹116.67 Lakhs/m² (~$140K/m²)
- Note: Smaller machines have higher price/area ratio

COMPARISON:
- AM-P (pressure) vs AM-V (vacuum only):
  AM-P adds compressed air capability for deeper draws
- AM series is entry level; PF1 series is premium
- Roll-fed is more automated than cut-sheet

WHAT'S INCLUDED IN BASE PRICE:
- Roll feeding system with servo spike chain
- Sandwich heating with IR ceramic heaters
- Pressure forming station (vacuum + air)
- Automatic cutting system
- PLC control with HMI touchscreen
- Safety systems

NOT INCLUDED:
- Chiller (5 ton + MTC) - customer to provide
- Air compressor (20 HP, 60 cfm) - customer to provide
- Additional tooling/molds
- GST (18%)""",
        knowledge_type="commercial",
        source_file=SOURCE_FILE,
        entity="AM-P-5060",
        summary="AM-P-5060 price: ₹35L base (~$42K), ₹39.5L complete package, 4mo lead time",
        metadata={
            "topic": "pricing",
            "base_price_inr": 3500000,
            "total_package_inr": 3950000,
            "base_price_usd_approx": 42000,
            "gst": "18%"
        }
    ))

    # 5. Commercial Terms
    items.append(KnowledgeItem(
        text="""AM-P-5060 Commercial Terms & Conditions

LEAD TIME:
- 4 months from PO & advance payment
- (Note: Document mentions both 3 and 4 months - confirm 4 months)

PAYMENT TERMS:
- 50% advance with purchase order
- 50% before dispatch from Machinecraft

SHIPPING:
- EXW Machinecraft plant, Gujarat, India
- Shipping within India: ₹1,50,000 (included in package)
- International shipping: Quoted separately

INSTALLATION:
- By 1 technician from Machinecraft
- Duration: 3 days on-site
- Cost: ₹2,00,000 (included in package)
- Client responsibility: Utilities ready (power, air)

TRAINING:
- Operator training included
- Duration: 2-3 days
- Cost: ₹1,00,000 (included in package)

WARRANTY:
- 12 months from date of commissioning
- Covers manufacturing defects
- Excludes consumables and wear parts

QUOTATION VALIDITY:
- 30 days from date of issue
- Prices subject to change after validity

ANCILLARY REQUIREMENTS (Customer to Provide):
- Chiller: 5 ton capacity + MTC
- Air Compressor: 20 HP, 60 cfm at 6 bar
- Electrical connection: 100 kW, 415V 3-Phase
- Clean, dry compressed air supply

CONTACT:
- Sales Team: +91-22-28817785
- Email: sales@machinecraft.org""",
        knowledge_type="commercial",
        source_file=SOURCE_FILE,
        entity="AM-P-5060",
        summary="Terms: 50/50 payment, 4mo lead time, 12mo warranty, 30-day quote validity",
        metadata={
            "topic": "commercial_terms",
            "lead_time_months": 4,
            "payment_advance": "50%",
            "warranty_months": 12,
            "quote_validity_days": 30
        }
    ))

    # 6. Pressure Forming vs Vacuum Forming Comparison
    items.append(KnowledgeItem(
        text="""Pressure Forming vs Vacuum Forming - Why Choose AM-P

VACUUM FORMING (Standard):
- Uses vacuum only (~0.9 bar differential)
- Material pulled down into mold
- Limited draw depth
- Softer detail definition
- Simpler tooling requirements

PRESSURE FORMING (AM-P Series):
- Uses vacuum AND compressed air (4-6 bar total)
- Material pushed AND pulled into mold
- Deeper draws possible (up to 60mm on AM-P-5060)
- Sharper detail and texture reproduction
- Tighter corners and radii achievable
- More complex tooling (sealed for pressure)

WHEN TO RECOMMEND AM-P (PRESSURE):
1. Deep draw requirements (>40mm)
2. Fine surface detail needed
3. Sharp corners and defined edges
4. Texture reproduction from mold
5. Thick gauge materials (>1mm)
6. Parts competing with injection molding aesthetics

WHEN STANDARD VACUUM IS SUFFICIENT:
1. Shallow draws (<40mm)
2. Simple shapes
3. Less critical surface detail
4. Thin gauge materials (<1mm)
5. Cost-sensitive applications
6. Simple trays and covers

AM-P-5060 SWEET SPOT:
- Thick gauge packaging (0.5-2.0mm)
- Automotive interior parts
- Deep draw containers
- Pre-printed packaging (eye mark capability)
- Medium volume production (~10 cycles/min)
- Parts requiring better aesthetics than vacuum-only""",
        knowledge_type="process",
        source_file=SOURCE_FILE,
        entity="AM-P",
        summary="Pressure forming: vacuum+air for deeper draws, sharper detail, tighter corners",
        metadata={
            "topic": "pressure_vs_vacuum",
            "pressure_advantage": ["deeper_draws", "sharper_detail", "tighter_corners"],
            "typical_depth_mm": 60
        }
    ))

    return items


def main():
    """Main ingestion function."""
    print("=" * 60)
    print("AM-P-5060 Quotation Ingestion")
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
