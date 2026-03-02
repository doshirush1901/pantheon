#!/usr/bin/env python3
"""
Ingest Machinecraft Infrared Heating System

Technical explanation of how Machinecraft's heating logic works.
Covers thermodynamics, flux calculation, and heater options.

Source: Machinecraft - Infrared Heating System.pptx
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

SOURCE_FILE = "Machinecraft - Infrared Heating System.pptx"


def create_knowledge_items() -> list[KnowledgeItem]:
    """Create structured knowledge items from IR heating system presentation."""
    items = []

    # 1. Heating System Overview
    items.append(KnowledgeItem(
        text="""Machinecraft Infrared Heating System - Overview

AIM: Heat the plastic sheet and draw it into desired shape

FUNDAMENTAL PRINCIPLE:
Energy Required to raise sheet temp from Ts to UFT = Energy radiated by Heater

Where:
- Ts = Starting temperature (ambient)
- UFT = Upper Forming Temperature (material specific)
- Radiation is the primary heat transfer mechanism

STEFAN-BOLTZMANN EQUATION:
Energy radiated = σ × Fg × F × A × (Th⁴ - Ts⁴)

Where:
- σ = Stefan-Boltzmann constant (J/s·m²·K⁴)
- Fg = Geometric view factor
- F = Emissivity factor
- A = Area (m²)
- Th = Heater temperature (K)
- Ts = Sheet temperature (K)

HEATING TIME CALCULATION:
Apply integration:
- LHS limits: T_initial to T_UFT
- RHS limits: 0 to Θ (time)
- Result: Time required for heating (seconds)

KEY CONCEPT:
Maintaining CONSTANT FLUX is critical for uniform heating.
Flux = Energy / Area (W/m² or J/s·m²)""",
        knowledge_type="operational",
        source_file=SOURCE_FILE,
        entity="IR Heating System Overview",
        summary="IR heating: Stefan-Boltzmann radiation; constant flux for uniform heating; Ts to UFT calculation",
        metadata={
            "topic": "ir_heating_overview",
            "principle": "Radiation heat transfer",
            "key_concept": "Constant flux"
        }
    ))

    # 2. Flux Distribution & Zone Control
    items.append(KnowledgeItem(
        text="""IR Heating - Flux Distribution & Zone Control Logic

FLUX CALCULATION GEOMETRY:

Consider a heater element grid relative to a point on the sheet:
- x direction: Movement relative to pivot element
- y direction: Movement relative to pivot element
- z: Distance between heater and sheet

LOCAL FLUX CONTRIBUTION:
Each heater element contributes to heating based on distance.
Closer elements contribute more, farther elements less.

EXAMPLE 3x3 GRID FLUX DISTRIBUTION:
Position contributions (normalized to center = 1.00):

| 0.11 | 0.16 | 0.11 |
| 0.16 | 1.00 | 0.16 |
| 0.11 | 0.16 | 0.11 |

Total flux at center point = sum of all contributions
Example: 1.00 + 0.50 + 0.20 + 0.50 + 0.30 + 0.16 + 0.20 + 0.16 + 0.11 = 3.13

INVERSE RELATIONSHIP:
Q/A = Constant (target flux)
- Higher temperature needed at edges (lower natural flux)
- Lower temperature at center (higher natural flux)

TEMPERATURE PROFILE (3x3 example - % of center):
| 151% | 128% | 151% |
| 128% | 100% | 128% |
| 151% | 128% | 151% |

This means edge/corner heaters need higher power settings
to achieve uniform sheet heating.

ZONE CONTROL PURPOSE:
- Compensate for edge effects
- Achieve uniform temperature across sheet
- Adjust for different sheet sizes
- Material-specific heating profiles""",
        knowledge_type="operational",
        source_file=SOURCE_FILE,
        entity="IR Flux Distribution",
        summary="IR flux: Grid contribution calculation; inverse relationship; edge heaters need higher power",
        metadata={
            "topic": "ir_flux_distribution",
            "concept": "Zone control for uniform heating",
            "edge_compensation": "151% of center temperature"
        }
    ))

    # 3. Software Control System
    items.append(KnowledgeItem(
        text="""IR Heating - Software Control & Grid Calculation

MACHINECRAFT DEVELOPED SOFTWARE:

OBJECTIVES ACHIEVED:
1. Computer program that self-generates flux distribution grid
2. Follows set algorithm for heat distribution
3. Generalized for all grid sizes
4. Accommodates various geometrical dimensions
5. User-interactive program developed in Scilab

FUNCTIONALITY:
- Input: Grid size, heater spacing, sheet size
- Output: Temperature profile for each heater zone
- Calculates required power per zone for uniform heating

EXAMPLE OUTPUT (3x3 Grid):
Final temperature grid calculated by software
to achieve uniform heating across sheet surface.

WHY THIS MATTERS:
- Different sheet sizes need different zone settings
- Different materials have different UFT values
- Automatic calculation vs manual trial-and-error
- Consistent, repeatable heating profiles
- Faster setup for new products

PRACTICAL APPLICATION:
1. Operator inputs sheet size and material
2. Software calculates zone temperatures
3. Machine automatically adjusts heater power
4. Result: Uniform heating regardless of sheet size

This is part of Machinecraft's "quick changeover"
capability - automatic sheet size adjustment.""",
        knowledge_type="operational",
        source_file=SOURCE_FILE,
        entity="IR Software Control",
        summary="IR software: Scilab-based; auto-generates zone temps for uniform heating; any grid size",
        metadata={
            "topic": "ir_software_control",
            "software": "Scilab",
            "feature": "Automatic zone calculation"
        }
    ))

    # 4. Ceramic Heater Option (Elstein FSR)
    items.append(KnowledgeItem(
        text="""Machinecraft Heater Option 1: Ceramic (Elstein FSR)

SUPPLIER: Elstein (Germany)
MODEL: FSR Series Panel Heaters

SPECIFICATIONS:
- Type: Ceramic infrared heaters
- Max Operating Temperature: 750°C
- Surface Rating: Up to 64 kW/m²
- Construction: Full-pour casting ceramic process
- Design: Concave shape

CONSTRUCTION ADVANTAGE:
The concave design creates space between heaters and mounting plate.
This reduces heat absorbed by the wiring space behind the heaters.
Result: More efficient heat transfer to sheet, less wasted heat.

CERAMIC CHARACTERISTICS:
- Longer wavelength IR radiation
- More gradual heating
- Better for thick sheets (deeper penetration)
- Good thermal mass (stable temperature)
- Durable construction

BLIND SPOT ISSUE (Disadvantage):
Ceramic elements heat neighboring elements due to material properties.
Heat conducts through ceramic, affecting adjacent zones.
This can cause "blind spots" in zone control precision.

BEST FOR:
- Thick gauge thermoforming
- Materials needing gradual heating
- Applications where precise zone control less critical
- Cost-sensitive applications (lower initial cost)""",
        knowledge_type="machine_spec",
        source_file=SOURCE_FILE,
        entity="Ceramic Heater (Elstein FSR)",
        summary="Ceramic heaters: Elstein FSR; 750°C max, 64kW/m²; concave design; blind spot issue",
        metadata={
            "topic": "ceramic_heaters",
            "supplier": "Elstein (Germany)",
            "max_temp": "750°C",
            "rating": "64 kW/m²"
        }
    ))

    # 5. Quartz Heater Option
    items.append(KnowledgeItem(
        text="""Machinecraft Heater Option 2: Quartz Elements

TWO SUPPLIERS:

1. CERAMICX (Ireland) - STANDARD
   - Standard quartz tube heaters
   - Good performance, reliable
   - More economical option

2. TQS (Germany) - FAST
   - High-performance quartz
   - Faster response time
   - Premium option

QUARTZ CHARACTERISTICS:
- Shorter wavelength IR radiation
- Faster heating response
- Better for thin sheets (surface heating)
- No thermal mass (instant on/off)
- More precise zone control

NO BLIND SPOT ISSUE:
Unlike ceramic, quartz elements do NOT heat neighboring elements.
Each zone operates independently.
Result: More precise zone control, better uniformity.

QUARTZ vs CERAMIC COMPARISON:

| Feature | Ceramic | Quartz |
|---------|---------|--------|
| Response Time | Slow | Fast |
| Zone Independence | Poor (blind spots) | Good (no bleed) |
| Wavelength | Long (deep heat) | Short (surface) |
| Best For | Thick sheets | Thin sheets |
| Energy Efficiency | Good | Better |
| Initial Cost | Lower | Higher |
| Control Precision | Moderate | High |

MACHINECRAFT RECOMMENDATION:
- Standard machines: Ceramicx quartz (Ireland)
- High-speed/precision: TQS quartz (Germany)
- Budget applications: Elstein ceramic

Most PF1 machines use QUARTZ for faster cycles
and better zone control.""",
        knowledge_type="machine_spec",
        source_file=SOURCE_FILE,
        entity="Quartz Heater Options",
        summary="Quartz heaters: Ceramicx (Ireland) standard, TQS (Germany) fast; no blind spots; better control",
        metadata={
            "topic": "quartz_heaters",
            "suppliers": ["Ceramicx (Ireland)", "TQS (Germany)"],
            "advantage": "No blind spot, precise zone control"
        }
    ))

    # 6. Practical Heating Knowledge
    items.append(KnowledgeItem(
        text="""IR Heating - Practical Knowledge for Sales & Support

CUSTOMER QUESTIONS & ANSWERS:

Q: How does Machinecraft achieve uniform heating?
A: Zone-controlled IR heaters with software-calculated temperature 
   profiles. Edge zones run hotter to compensate for heat loss.
   Closed chamber design prevents drafts affecting uniformity.

Q: Why quartz instead of ceramic heaters?
A: Quartz offers faster response (shorter cycles), no "blind spot" 
   issue between zones, and more precise control. Better for thin 
   gauge and materials requiring exact temperature profiles.

Q: What's the "blind spot" issue?
A: In ceramic heaters, heat conducts through the ceramic material 
   to adjacent elements. This blurs zone boundaries. Quartz elements
   are thermally independent - no cross-contamination.

Q: How fast can the sheet be heated?
A: Depends on material and thickness. Software calculates optimal
   time based on Stefan-Boltzmann radiation equations. Quartz heaters
   (especially TQS) enable faster cycles than ceramic.

Q: Can I change sheet sizes easily?
A: Yes - Universal frames + automatic zone calculation. Machine
   adjusts heater power distribution for each sheet size. 
   Changeover time: ~10-15 minutes.

Q: What heater brands does Machinecraft use?
A: Ceramic: Elstein FSR (Germany) - 750°C, 64kW/m²
   Quartz Standard: Ceramicx (Ireland)
   Quartz Fast: TQS (Germany) - premium option

MATERIAL-SPECIFIC HEATING:
- ABS: Even heating, moderate temp
- PC: Slower heating, avoid hot spots
- PMMA: Careful - narrow forming window
- PP/PE: Lower temps, watch for sagging
- PETG: Medium temps, uniform critical""",
        knowledge_type="operational",
        source_file=SOURCE_FILE,
        entity="IR Heating Practical Knowledge",
        summary="IR practical: Zone control logic, quartz vs ceramic choice, uniform heating Q&A for sales",
        metadata={
            "topic": "ir_heating_practical",
            "use": "Sales and support knowledge",
            "heater_brands": ["Elstein", "Ceramicx", "TQS"]
        }
    ))

    return items


def main():
    """Main ingestion function."""
    print("=" * 60)
    print("Machinecraft IR Heating System Ingestion")
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
