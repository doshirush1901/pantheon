#!/usr/bin/env python3
"""
Ingest Machinecraft Complete Applications List

This is a comprehensive document listing 73 distinct applications across 12 
industry sectors that are achievable with Machinecraft's single sheet vacuum
forming machines.

Critical for sales: Maps applications to recommended machine series.
Key data: 73 applications, 12 industries, 8 machine series, 3 market tiers.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Direct import to avoid circular dependencies
from openclaw.agents.ira.src.brain.knowledge_ingestor import KnowledgeIngestor, KnowledgeItem

SOURCE_FILE = "machinecraft_complete_applications_list.pdf"


def create_knowledge_items() -> list[KnowledgeItem]:
    """Create structured knowledge items from the applications list."""
    items = []

    # 1. Executive Summary & Machine Portfolio Overview
    items.append(KnowledgeItem(
        text="""Machinecraft Complete Applications List - Executive Summary:

SCOPE OF DOCUMENT:
- Total Applications Analyzed: 85
- Suitable for Machinecraft Single Sheet Machines: 73 (86%)
- Excluded Applications: 12 (14%) - twin sheet, complex composites, advanced undercuts
- Industries Covered: 12 different sectors
- Machine Series: 8 series across 3 market tiers

MACHINE PORTFOLIO CATEGORIES:

MID-TIER MACHINES (Entry/Standard):
- AM Series: 2 models - Entry level machines
- PF1 Classic: 21 models - Standard production machines

PREMIUM MACHINES:
- FCS Series: 2 models (FCS-C-5060, FCS-S-6090) - Inline series
- IMG Series: 2 models (0512, 1220) - Advanced imaging/automation
- PF1 X Series: 22 models - Premium production machines

SPECIALIZED MACHINES:
- PF1 L Series: 1 model - Luggage shells specialist
- PF1 M Series: 3 models - 3D Car Mats specialist
- PF1 W Series: 3 models - Wellness/Spa applications

TECHNICAL CAPABILITIES:

Heavy Gauge Single Sheet Vacuum Forming:
- Materials: ABS, PMMA, PC, TPO, HDPE
- Processing: Sheet fed
- Sheet thickness: 1.5mm to 8mm
- Features: Custom automation, 3/4/5 axis trimming

Light Gauge Single Sheet Vacuum Forming:
- Materials: PET, PP, PS, PVC, PLA
- Processing: Roll fed
- Sheet thickness: 0.2mm to 1.5mm
- Features: High speed production, packaging focus""",
        knowledge_type="general",
        source_file=SOURCE_FILE,
        entity="Machinecraft",
        summary="Complete applications overview: 73 apps, 12 industries, 8 machine series",
        metadata={
            "topic": "applications_overview",
            "total_applications": 73,
            "industries": 12,
            "machine_series": 8
        }
    ))

    # 2. Commercial Vehicle/Transportation Applications (15)
    items.append(KnowledgeItem(
        text="""COMMERCIAL VEHICLE/TRANSPORTATION APPLICATIONS (15 applications)

Market Share: 18% of total applications (LARGEST SECTOR)
Primary Materials: ABS with UV stabilization, PP/ABS, reinforced ABS
Recommended Machines: PF1 Classic, PF1 X Series, FCS Series
Production Volumes: Up to 2000 vehicles/year

COMPLETE APPLICATION LIST:

1. CAR ROOF LINER
   - Material: ABS with UV stabilization
   - Application: Interior automotive component
   - Machines: PF1 Classic, PF1 X Series

2. LCV EXTERIOR PARTS
   - Material: ABS with UV stabilization
   - Application: Light Commercial Vehicle exterior components
   - Machines: PF1 Classic, PF1 X Series, FCS Series

3. LCV MIDDLE PARTS
   - Material: ABS
   - Application: Light Commercial Vehicle structural components
   - Machines: PF1 Classic, PF1 X Series

4. BUS SEATS
   - Material: PP/ABS
   - Application: Public transportation seating
   - Machines: PF1 Classic, PF1 X Series

5. REAR CARRIER
   - Material: ABS
   - Application: Vehicle cargo components
   - Machines: PF1 Classic, PF1 X Series

6. DOOR PANELS
   - Material: ABS
   - Application: Vehicle interior panels
   - Machines: PF1 Classic, PF1 X Series

7. INSTRUMENT PANEL
   - Material: ABS
   - Application: Vehicle dashboard components
   - Machines: PF1 X Series (Class A surfaces required)

8. FIRE EXIT CASING
   - Material: ABS (flame retardant)
   - Application: Safety equipment housing
   - Machines: PF1 Classic, PF1 X Series

9. BUS INTERIOR COMPONENTS
   - Material: ABS/PP (flame retardant)
   - Application: Public transportation interiors
   - Machines: PF1 Classic, PF1 X Series

10. AC COOLER CASING
    - Material: ABS
    - Application: Air conditioning system housing
    - Machines: PF1 Classic, PF1 X Series

11. MUDGUARDS
    - Material: ABS with UV stabilization
    - Application: Vehicle protection components
    - Machines: PF1 Classic, PF1 X Series

12. EXTERIOR COVERING PANELS
    - Material: ABS with UV stabilization
    - Application: Vehicle exterior protection
    - Machines: PF1 Classic, PF1 X Series, FCS Series

13. VEHICLE FAIRINGS
    - Material: ABS
    - Application: Aerodynamic vehicle components
    - Machines: PF1 Classic, PF1 X Series

14. TRACTOR BODY PARTS
    - Material: Reinforced ABS
    - Application: Agricultural vehicle components
    - Machines: PF1 X Series

15. COMMERCIAL VEHICLE INTERIORS
    - Material: Flame retardant materials
    - Application: Interior trim and panels
    - Machines: PF1 Classic, PF1 X Series""",
        knowledge_type="application",
        source_file=SOURCE_FILE,
        entity="Machinecraft",
        summary="Commercial vehicle apps (15): roof liners, bus seats, door panels, instrument panels",
        metadata={
            "topic": "commercial_vehicle_applications",
            "application_count": 15,
            "market_share": "18%",
            "primary_material": "ABS",
            "machines": ["PF1 Classic", "PF1 X Series", "FCS Series"]
        }
    ))

    # 3. Automotive/Microcar Applications (9)
    items.append(KnowledgeItem(
        text="""AUTOMOTIVE/MICROCAR APPLICATIONS (9 applications)

Market Share: 11% of total applications
Primary Materials: ABS, ABS/PMMA combinations, dual material construction
Recommended Machines: PF1 Classic, PF1 X Series
Notable History: First thermoformed ABS body panels in 1984 (Aixam)

COMPLETE APPLICATION LIST:

1. AIXAM BODY PARTS
   - Material: ABS
   - Application: Microcar body panels
   - Machines: PF1 Classic, PF1 X Series
   - Note: Historic significance - first thermoformed ABS automotive parts (1984)

2. MEGA BRAND CAR PARTS
   - Material: ABS/PMMA
   - Application: Microcar components
   - Machines: PF1 X Series

3. MICROCAR PANELS
   - Material: ABS
   - Application: Small vehicle body panels
   - Machines: PF1 Classic, PF1 X Series

4. MICROCAR DOORS
   - Material: ABS/PMMA
   - Application: Vehicle door panels
   - Machines: PF1 X Series
   - Note: 14kg weight specification achievable

5. MICROCAR BUMPERS
   - Material: ABS
   - Application: Vehicle impact protection
   - Machines: PF1 Classic, PF1 X Series

6. CLASS A AUTOMOTIVE SURFACES
   - Material: ABS/PMMA
   - Application: High-quality visible surfaces
   - Machines: PF1 X Series (premium finish required)
   - Note: Requires premium machine for surface quality

7. E-SCOOTER COVERS
   - Material: Weather resistant ABS
   - Application: Electric vehicle protection
   - Machines: PF1 Classic, AM Series

8. MOTORCYCLE COMPONENTS
   - Material: Impact resistant plastics
   - Application: Two-wheeler parts
   - Machines: PF1 Classic, PF1 X Series

9. VEHICLE INTERIOR TRIM
   - Material: Aesthetic thermoplastics
   - Application: Interior decoration and function
   - Machines: PF1 Classic, PF1 X Series

KEY SELLING POINT:
Machinecraft has 40+ years experience in automotive thermoforming,
starting with Aixam microcar body panels in 1984.""",
        knowledge_type="application",
        source_file=SOURCE_FILE,
        entity="Machinecraft",
        summary="Automotive/microcar apps (9): body panels, doors, bumpers, Class A surfaces",
        metadata={
            "topic": "automotive_applications",
            "application_count": 9,
            "market_share": "11%",
            "primary_material": "ABS/PMMA",
            "machines": ["PF1 Classic", "PF1 X Series"]
        }
    ))

    # 4. Agricultural Equipment Applications (8)
    items.append(KnowledgeItem(
        text="""AGRICULTURAL EQUIPMENT APPLICATIONS (8 applications)

Market Share: 11% of total applications
Primary Materials: ABS/PMMA, chemical resistant ABS, bio-based reinforced materials
Recommended Machines: PF1 X Series, FCS Series
Key Features: Chemical resistance, UV resistance, bio-based options

COMPLETE APPLICATION LIST:

1. AGRICULTURAL SIDE PANELS
   - Material: ABS/PMMA
   - Application: Equipment side protection
   - Machines: PF1 X Series

2. AGRICULTURAL EQUIPMENT SHIELDS
   - Material: Chemical resistant ABS
   - Application: Protection from chemicals and weather
   - Machines: PF1 X Series
   - Note: Must withstand fertilizers, pesticides

3. A-CLASS AGRICULTURAL PANELS
   - Material: In-mold colored thermoplastics
   - Application: High-quality visible surfaces
   - Machines: PF1 X Series
   - Note: Premium finish for branded equipment

4. CHEMICAL RESISTANT COMPONENTS
   - Material: Specialized polymers
   - Application: Parts exposed to fertilizers and chemicals
   - Machines: PF1 X Series

5. INTEGRATED FIXATION SYSTEMS
   - Material: Reinforced thermoplastics
   - Application: Mounting and attachment components
   - Machines: PF1 X Series

6. ACOUSTICAL AGRICULTURAL PANELS
   - Material: Sound-absorbing materials
   - Application: Noise reduction components
   - Machines: PF1 X Series
   - Note: Operator comfort improvement

7. AGRICULTURAL GRAIN TANK (single sheet version)
   - Material: ABS/PMMA
   - Application: Storage components
   - Machines: PF1 X Series
   - Note: Single sheet version only (twin sheet excluded)

8. BIO-BASED AGRICULTURAL COMPONENTS
   - Material: Bio-based reinforced materials
   - Application: Sustainable agricultural parts
   - Machines: PF1 X Series
   - Note: Growing demand for sustainability""",
        knowledge_type="application",
        source_file=SOURCE_FILE,
        entity="Machinecraft",
        summary="Agricultural apps (8): side panels, shields, grain tanks, chemical resistant parts",
        metadata={
            "topic": "agricultural_applications",
            "application_count": 8,
            "market_share": "11%",
            "key_features": ["chemical_resistance", "UV_resistance", "bio-based"],
            "machines": ["PF1 X Series", "FCS Series"]
        }
    ))

    # 5. Industrial/Equipment Applications (7)
    items.append(KnowledgeItem(
        text="""INDUSTRIAL/EQUIPMENT APPLICATIONS (7 applications)

Market Share: 9% of total applications
Primary Materials: Engineering plastics, reinforced materials, anti-static materials
Recommended Machines: PF1 Classic, PF1 X Series, IMG Series
Key Features: Durability, weather resistance, precision

COMPLETE APPLICATION LIST:

1. TECHNICAL EQUIPMENT HOUSINGS
   - Material: Engineering plastics
   - Application: Industrial equipment protection
   - Machines: PF1 Classic, PF1 X Series

2. PROTECTIVE COVERS
   - Material: Durable thermoplastics
   - Application: Equipment protection
   - Machines: PF1 Classic, PF1 X Series

3. MACHINERY ENCLOSURES
   - Material: Reinforced materials
   - Application: Industrial machinery housing
   - Machines: PF1 X Series

4. ELECTRONIC HOUSINGS
   - Material: Anti-static materials
   - Application: Electronic equipment protection
   - Machines: IMG Series, PF1 X Series
   - Note: Anti-static critical for electronics

5. INDUSTRIAL EQUIPMENT COVERS
   - Material: Weather resistant materials
   - Application: Outdoor equipment protection
   - Machines: PF1 Classic, PF1 X Series

6. TECHNICAL SYSTEM HOUSINGS
   - Material: Engineering grade plastics
   - Application: Technical system protection
   - Machines: PF1 X Series, IMG Series

7. PRECISION EQUIPMENT ENCLOSURES
   - Material: High tolerance materials
   - Application: Precision equipment housing
   - Machines: IMG Series, PF1 X Series
   - Note: IMG Series recommended for quality-critical apps""",
        knowledge_type="application",
        source_file=SOURCE_FILE,
        entity="Machinecraft",
        summary="Industrial apps (7): equipment housings, protective covers, electronic enclosures",
        metadata={
            "topic": "industrial_applications",
            "application_count": 7,
            "market_share": "9%",
            "key_features": ["durability", "weather_resistance", "anti-static"],
            "machines": ["PF1 Classic", "PF1 X Series", "IMG Series"]
        }
    ))

    # 6. Medical/Wellness Applications (4)
    items.append(KnowledgeItem(
        text="""MEDICAL/WELLNESS APPLICATIONS (4 applications)

Market Share: 5% of total applications
Primary Materials: Medical grade plastics, hygienic materials
Recommended Machines: PF1 W Series (Wellness), PF1 X Series, IMG Series
Key Features: Medical grade certification, hygienic properties

COMPLETE APPLICATION LIST:

1. MEDICAL EQUIPMENT HOUSINGS
   - Material: Medical grade plastics
   - Application: Medical device protection
   - Machines: IMG Series, PF1 X Series
   - Note: Requires medical grade certification

2. WELLNESS APPLICATIONS
   - Material: Hygienic materials
   - Application: Spa and wellness equipment
   - Machines: PF1 W Series (specialist)

3. SPA COMPONENTS
   - Material: Specialized polymers
   - Application: Spa equipment parts
   - Machines: PF1 W Series (specialist)

4. MEDICAL DEVICE COVERINGS
   - Material: Medical grade materials
   - Application: Medical equipment housing
   - Machines: IMG Series, PF1 X Series

SPECIALIST MACHINE: PF1 W Series
The PF1 W Series is specifically optimized for wellness and spa applications,
with features designed for hygienic material handling and smooth surfaces.""",
        knowledge_type="application",
        source_file=SOURCE_FILE,
        entity="Machinecraft",
        summary="Medical/wellness apps (4): medical housings, spa components, wellness equipment",
        metadata={
            "topic": "medical_wellness_applications",
            "application_count": 4,
            "market_share": "5%",
            "specialist_machine": "PF1 W Series",
            "machines": ["PF1 W Series", "PF1 X Series", "IMG Series"]
        }
    ))

    # 7. Specialized Applications (8)
    items.append(KnowledgeItem(
        text="""SPECIALIZED APPLICATIONS (8 applications)

Market Share: 11% of total applications
Primary Materials: PC (Polycarbonate), various specialized materials
Recommended Machines: PF1 L Series, PF1 M Series, PF1 W Series, PF1 X Series
Key Features: Application-specific machine optimization

COMPLETE APPLICATION LIST:

1. LUGGAGE SHELLS (PF1 L Series - SPECIALIST)
   - Material: PC (Polycarbonate)
   - Application: Suitcase shells and travel luggage
   - Machines: PF1 L Series (specialist)
   - Note: Superior impact and aesthetic properties for luggage

2. 3D CAR MATS (PF1 M Series - SPECIALIST)
   - Material: Various materials
   - Application: Automotive floor mats
   - Machines: PF1 M Series (specialist)
   - Note: Dedicated machine series for this application

3. SANITARY BATHTUBS
   - Material: Hygienic thermoplastics
   - Application: Bathroom fixtures
   - Machines: PF1 W Series

4. AEROSPACE INTERIORS
   - Material: Lightweight materials
   - Application: Aircraft interior components
   - Machines: PF1 X Series
   - Note: Weight-critical, high quality requirements

5. TRAIN INTERIORS
   - Material: Fire retardant materials
   - Application: Railway interior components
   - Machines: PF1 X Series
   - Note: Fire safety certification required (DIN 5510-2)

6. KAYAKS
   - Material: Thermoformed plastics
   - Application: Recreational watercraft
   - Machines: PF1 Classic, PF1 X Series

7. BARBECUE ISLANDS
   - Material: Weather resistant plastics
   - Application: Outdoor cooking equipment
   - Machines: PF1 Classic, PF1 X Series

8. BETTER SHELTER COMPONENTS (single sheet version)
   - Material: PP (single sheet version)
   - Application: Emergency housing components
   - Machines: PF1 Classic, PF1 X Series
   - Note: 17.5m² modular units, humanitarian applications""",
        knowledge_type="application",
        source_file=SOURCE_FILE,
        entity="Machinecraft",
        summary="Specialized apps (8): luggage shells, 3D car mats, bathtubs, aerospace, train interiors",
        metadata={
            "topic": "specialized_applications",
            "application_count": 8,
            "market_share": "11%",
            "specialist_machines": ["PF1 L Series", "PF1 M Series", "PF1 W Series"]
        }
    ))

    # 8. Light Gauge Food Packaging Applications (12)
    items.append(KnowledgeItem(
        text="""LIGHT GAUGE APPLICATIONS - FOOD PACKAGING (12 applications)

Market Share: 16% of total applications (SECOND LARGEST)
Primary Materials: PET, PP, PS, PVC, PLA, biodegradable materials
Recommended Machines: Roll fed machines, light gauge systems
Key Features: High speed production, food grade materials, sustainability

COMPLETE APPLICATION LIST:

1. FRESH MEAT SKIN PACK TRAYS
   - Material: Advanced polymers
   - Application: Meat packaging with extended shelf life
   - Machines: Light gauge roll fed systems

2. ACTIVE PACKAGING WITH CO2 ABSORBERS
   - Material: Specialized polymers with active components
   - Application: Extended food preservation
   - Machines: Light gauge roll fed systems
   - Note: 21-day shelf life extension achievable

3. DARFRESH SYSTEM
   - Material: Advanced barrier materials
   - Application: Fresh food packaging system
   - Machines: Light gauge roll fed systems

4. SPACE OPTIMIZATION TRAYS
   - Material: Lightweight polymers
   - Application: Efficient packaging design
   - Machines: Light gauge roll fed systems

5. COFFEE CAPSULES
   - Material: Food grade polymers
   - Application: Single-serve coffee packaging
   - Machines: Light gauge roll fed systems

6. BEVERAGE PACKAGING
   - Material: Barrier materials
   - Application: Drink containers and lids
   - Machines: Light gauge roll fed systems

7. THICK WALL PACKAGING
   - Material: High barrier materials
   - Application: Premium food packaging
   - Machines: Light gauge roll fed systems

8. FOOD WASTE REDUCTION PACKAGING
   - Material: Advanced barrier films
   - Application: Extended freshness packaging
   - Machines: Light gauge roll fed systems

9. SUSTAINABLE FOOD PACKAGING
   - Material: Biodegradable materials (PLA)
   - Application: Environmentally friendly packaging
   - Machines: Light gauge roll fed systems

10. EXTENDED SHELF LIFE PACKAGING
    - Material: Active packaging systems
    - Application: Long-term food preservation
    - Machines: Light gauge roll fed systems

11. ADVANCED PACKAGING SYSTEMS
    - Material: Multi-layer barrier materials
    - Application: High-performance food packaging
    - Machines: Light gauge roll fed systems

12. HIGH PERFORMANCE FOOD PACKAGING
    - Material: Extended barrier properties
    - Application: Premium food protection
    - Machines: Light gauge roll fed systems""",
        knowledge_type="application",
        source_file=SOURCE_FILE,
        entity="Machinecraft",
        summary="Food packaging apps (12): meat trays, coffee capsules, sustainable packaging",
        metadata={
            "topic": "food_packaging_applications",
            "application_count": 12,
            "market_share": "16%",
            "materials": ["PET", "PP", "PS", "PVC", "PLA"],
            "processing": "roll_fed"
        }
    ))

    # 9. Consumer & Industrial Packaging Applications (10)
    items.append(KnowledgeItem(
        text="""LIGHT GAUGE APPLICATIONS - CONSUMER PACKAGING (6 applications)

Market Share: 8% of total applications
Primary Materials: PET, PP, PS, clear polymers, anti-static materials
Recommended Machines: Roll fed machines, light gauge systems

CONSUMER PACKAGING LIST:

1. FRUIT & VEGETABLE PACKAGING
   - Material: PET/PP/PS
   - Application: Fresh produce packaging
   - Machines: Light gauge roll fed systems

2. MEDICAL PACKAGING
   - Material: Specialized polymers
   - Application: Pharmaceutical and medical device packaging
   - Machines: Light gauge roll fed systems

3. ELECTRONICS PACKAGING
   - Material: Anti-static materials
   - Application: Electronic component protection
   - Machines: Light gauge roll fed systems

4. BLISTER PACKAGING
   - Material: Clear polymers
   - Application: Product display packaging
   - Machines: Light gauge roll fed systems

5. MEAL TRAYS
   - Material: Food grade materials
   - Application: Ready meal containers
   - Machines: Light gauge roll fed systems

6. DRINK CUPS & LIDS
   - Material: Food grade polymers
   - Application: Beverage containers
   - Machines: Light gauge roll fed systems

---

LIGHT GAUGE APPLICATIONS - INDUSTRIAL PACKAGING (4 applications)

Market Share: 5% of total applications
Primary Materials: Reinforced polymers, recycled materials, bio-based materials

INDUSTRIAL PACKAGING LIST:

1. INDUSTRIAL PACKAGING
   - Material: Reinforced polymers
   - Application: Industrial component packaging
   - Machines: Light gauge roll fed systems

2. PROTECTIVE PACKAGING
   - Material: Impact resistant materials
   - Application: Product protection during transport
   - Machines: Light gauge roll fed systems

3. RECYCLED CONTENT PACKAGING
   - Material: Recycled polymers
   - Application: Sustainable packaging solutions
   - Machines: Light gauge roll fed systems

4. SUSTAINABLE PACKAGING SOLUTIONS
   - Material: Bio-based materials
   - Application: Environmentally friendly packaging
   - Machines: Light gauge roll fed systems""",
        knowledge_type="application",
        source_file=SOURCE_FILE,
        entity="Machinecraft",
        summary="Consumer packaging (6) + Industrial packaging (4): blister packs, meal trays, cups",
        metadata={
            "topic": "consumer_industrial_packaging",
            "consumer_count": 6,
            "industrial_count": 4,
            "processing": "roll_fed"
        }
    ))

    # 10. Construction/Building Applications (6)
    items.append(KnowledgeItem(
        text="""CONSTRUCTION/BUILDING APPLICATIONS (6 applications)

Market Share: 8% of total applications
Primary Materials: Fire retardant materials, UV resistant materials, modular components
Recommended Machines: PF1 Classic, PF1 X Series

COMPLETE APPLICATION LIST:

1. HEATING SYSTEMS
   - Material: Heat resistant thermoplastics
   - Application: HVAC system components
   - Machines: PF1 Classic, PF1 X Series

2. HVAC COMPONENTS
   - Material: Engineering plastics
   - Application: Air conditioning and ventilation parts
   - Machines: PF1 Classic, PF1 X Series

3. CONSTRUCTION MACHINERY FAIRINGS
   - Material: Reinforced ABS
   - Application: Construction equipment protection
   - Machines: PF1 X Series

4. FIRE SAFETY COMPONENTS
   - Material: Fire retardant materials
   - Application: Safety equipment housing
   - Machines: PF1 Classic, PF1 X Series

5. UV RESISTANT BUILDING COMPONENTS
   - Material: UV stabilized materials
   - Application: Outdoor building elements
   - Machines: PF1 Classic, PF1 X Series

6. MODULAR BUILDING COMPONENTS
   - Material: Structural thermoplastics
   - Application: Modular construction elements
   - Machines: PF1 Classic, PF1 X Series""",
        knowledge_type="application",
        source_file=SOURCE_FILE,
        entity="Machinecraft",
        summary="Construction apps (6): HVAC components, fire safety, UV resistant building parts",
        metadata={
            "topic": "construction_applications",
            "application_count": 6,
            "market_share": "8%",
            "key_features": ["fire_retardant", "UV_resistant"],
            "machines": ["PF1 Classic", "PF1 X Series"]
        }
    ))

    # 11. Recreation/Marine & Railway Applications (5)
    items.append(KnowledgeItem(
        text="""RECREATION/MARINE APPLICATIONS (3 applications)

Market Share: 4% of total applications
Primary Materials: UV-resistant materials, marine-grade plastics
Recommended Machines: PF1 Classic, PF1 X Series

RECREATION/MARINE LIST:

1. KAYAKS
   - Material: UV-resistant thermoplastics
   - Application: Recreational watercraft
   - Machines: PF1 Classic, PF1 X Series

2. BARBECUE ISLANDS
   - Material: Weather resistant plastics
   - Application: Outdoor cooking equipment
   - Machines: PF1 Classic, PF1 X Series

3. MARINE COMPONENTS
   - Material: Marine-grade plastics
   - Application: Boat and marine equipment parts
   - Machines: PF1 Classic, PF1 X Series

---

RAILWAY/TRANSPORTATION APPLICATIONS (2 applications)

Market Share: 3% of total applications
Primary Materials: Fire safety certified materials (DIN 5510-2)
Recommended Machines: PF1 X Series

RAILWAY LIST:

1. RAILWAY SEAT COVERS
   - Material: Fire safety DIN 5510-2 compliant
   - Application: Train seating components
   - Machines: PF1 X Series
   - Note: Must meet European fire safety standards

2. TRAIN INTERIORS
   - Material: Fire retardant certified materials
   - Application: Railway interior components
   - Machines: PF1 X Series
   - Note: Stringent certification requirements""",
        knowledge_type="application",
        source_file=SOURCE_FILE,
        entity="Machinecraft",
        summary="Recreation/marine apps (3) + Railway apps (2): kayaks, marine parts, train interiors",
        metadata={
            "topic": "recreation_railway_applications",
            "recreation_count": 3,
            "railway_count": 2,
            "railway_certification": "DIN 5510-2"
        }
    ))

    # 12. Machine-Application Matching Guide
    items.append(KnowledgeItem(
        text="""MACHINE-APPLICATION MATCHING GUIDE

Use this guide to recommend the right machine based on the application:

---

AM SERIES (Entry Level) - 25 Suitable Applications
Production Volume: Up to 500 units/year

RECOMMENDED FOR:
- Basic commercial vehicle parts
- Simple automotive components
- Standard packaging applications
- Entry-level industrial housings
- Small production volumes

---

PF1 CLASSIC (Standard Production) - 35 Suitable Applications
Production Volume: 500-1000 units/year

RECOMMENDED FOR:
- Full range of commercial vehicle applications
- Automotive interior/exterior parts
- Agricultural equipment panels
- Standard industrial applications
- Food packaging (light gauge)
- Medium production volumes

---

PF1 X SERIES (Premium Production) - 40 Suitable Applications
Production Volume: 1000-2000 units/year
MOST VERSATILE MACHINE SERIES

RECOMMENDED FOR:
- All PF1 Classic applications PLUS:
- Class A automotive surfaces
- Precision agricultural components
- Advanced medical housings
- High-performance packaging
- High production volumes

---

FCS SERIES (Inline Production) - 30 Suitable Applications
Production Volume: Above 2000 units/year

RECOMMENDED FOR:
- High-volume production applications
- Automotive mass production
- Large-scale packaging
- Industrial volume production
- Very high production volumes

---

IMG SERIES (Advanced Imaging) - 25 Suitable Applications

RECOMMENDED FOR:
- Quality-critical applications
- Precision automotive parts
- Medical device housings
- Advanced packaging systems
- Applications requiring advanced quality control

---

SPECIALIZED SERIES:

PF1 L SERIES: Luggage shells and travel applications (1 application)
- PC material specialist
- Impact resistance focus

PF1 M SERIES: 3D car mats and automotive floor applications (1 application)
- Dedicated mat production
- Multiple material capability

PF1 W SERIES: Wellness, spa, and sanitary applications (3 applications)
- Hygienic surface specialist
- Bathtub and spa focus""",
        knowledge_type="general",
        source_file=SOURCE_FILE,
        entity="Machinecraft",
        summary="Machine selection guide: AM(25), PF1 Classic(35), PF1 X(40), FCS(30), IMG(25) apps",
        metadata={
            "topic": "machine_selection_guide",
            "am_series_apps": 25,
            "pf1_classic_apps": 35,
            "pf1_x_series_apps": 40,
            "fcs_series_apps": 30,
            "img_series_apps": 25
        }
    ))

    # 13. Material Recommendations
    items.append(KnowledgeItem(
        text="""MATERIAL RECOMMENDATIONS BY APPLICATION TYPE

HEAVY GAUGE MATERIALS (Sheet Fed Processing):

ABS - Most Versatile (42% of applications)
- Commercial vehicle parts
- Automotive components
- Industrial housings
- General purpose applications

ABS/PMMA - Automotive Aesthetics (23% of applications)
- Class A surfaces
- Visible automotive parts
- Agricultural premium panels
- High gloss finish required

PC (Polycarbonate) - Premium Luggage (8% of applications)
- Suitcase shells
- High impact resistance needed
- Clear/transparent parts

TPO - Automotive Exterior
- Exterior body panels
- Weather resistance
- Impact resistance

HDPE - Chemical Resistant
- Chemical exposure applications
- Agricultural equipment
- Industrial containers

---

LIGHT GAUGE MATERIALS (Roll Fed Processing):

PET - Food Packaging, Clear Applications
- Food trays
- Blister packaging
- Clear containers

PP - General Packaging, Chemical Resistance
- Food containers
- Industrial packaging
- Cost-effective applications

PS - Disposable Packaging, Cost-Effective
- Single-use containers
- Budget packaging
- High volume production

PVC - Specialized Packaging
- Specific barrier requirements
- Medical packaging

PLA - Biodegradable Solutions
- Sustainable packaging
- Eco-friendly applications
- Growing market demand

---

MATERIAL SELECTION CRITERIA:
1. Application environment (indoor/outdoor)
2. Chemical exposure requirements
3. Fire retardancy needs (e.g., DIN 5510-2 for railway)
4. UV resistance for outdoor use
5. Surface finish requirements (Class A vs standard)
6. Impact resistance needs
7. Temperature range requirements
8. Cost considerations""",
        knowledge_type="general",
        source_file=SOURCE_FILE,
        entity="Machinecraft",
        summary="Material guide: ABS(42%), ABS/PMMA(23%), PC(8%) for heavy gauge; PET/PP/PS for light",
        metadata={
            "topic": "material_recommendations",
            "abs_share": "42%",
            "abs_pmma_share": "23%",
            "pc_share": "8%",
            "light_gauge": ["PET", "PP", "PS", "PVC", "PLA"]
        }
    ))

    # 14. Excluded Applications (What Machinecraft Can't Do)
    items.append(KnowledgeItem(
        text="""EXCLUDED APPLICATIONS - NOT SUITABLE FOR MACHINECRAFT SINGLE SHEET MACHINES

The following 12 applications (14% of total analyzed) are NOT suitable for 
Machinecraft's single sheet vacuum forming machines:

---

TWIN SHEET APPLICATIONS (4 excluded):

1. GRAIN TANK COVER (John Deere)
   - Reason: Twin sheet ABS+PMMA construction
   - Requires twin sheet forming process

2. STORAGE BOXES
   - Reason: Twin-sheet construction required
   - Hollow structure needs two sheets fused

3. TRANSPORT CONTAINERS
   - Reason: Twin-sheet ABS construction
   - Double-wall strength requirement

4. MACHINERY COVERS
   - Reason: Twin-sheet construction
   - Insulation/structural requirements

---

ADVANCED COMPOSITE APPLICATIONS (4 excluded):

1. S-RIM COMPOSITE PANELS
   - Reason: Thermoforming over S-RIM process
   - Complex composite integration

2. BONDED BUILD-UP PANELS
   - Reason: Foam core composites
   - Multi-layer bonded construction

3. STRUCTURAL INSULATION PANELS
   - Reason: Composite materials
   - Foam/insulation integration

4. COMPOSITE SANDWICH PANELS
   - Reason: Multi-layer construction
   - Structural composite requirements

---

COMPLEX UNDERCUT APPLICATIONS (1 excluded):

1. CAT FENDER WITH UNDERCUT (CNH Industrial)
   - Reason: Complex geometry
   - Advanced undercuts not achievable with single sheet

---

OTHER ADVANCED PROCESSES (3 excluded):

1. Advanced multi-layer composite applications
2. Structural foam integration applications
3. Complex 3D undercut geometries

---

IMPORTANT SALES NOTE:
If a customer asks about these excluded applications, recommend:
- Twin sheet specialist manufacturers
- Composite forming specialists
- Multi-process solution providers

Machinecraft focuses on SINGLE SHEET vacuum forming excellence.""",
        knowledge_type="general",
        source_file=SOURCE_FILE,
        entity="Machinecraft",
        summary="Excluded apps (12): twin sheet, composites, complex undercuts - NOT suitable",
        metadata={
            "topic": "excluded_applications",
            "excluded_count": 12,
            "twin_sheet_excluded": 4,
            "composite_excluded": 4,
            "undercut_excluded": 1,
            "other_excluded": 3
        }
    ))

    # 15. Quick Reference Summary Statistics
    items.append(KnowledgeItem(
        text="""MACHINECRAFT APPLICATIONS - QUICK REFERENCE SUMMARY

TOTAL STATISTICS:
- Total Applications Analyzed: 85
- Suitable for Machinecraft: 73 (86%)
- Excluded Applications: 12 (14%)

APPLICATIONS BY INDUSTRY (Ranked by Count):

1. Commercial Vehicle/Transportation: 15 apps (18%) - LARGEST
2. Food Packaging (Light Gauge): 12 apps (16%)
3. Automotive/Microcar: 9 apps (11%)
4. Agricultural Equipment: 8 apps (11%)
5. Specialized Applications: 8 apps (11%)
6. Industrial/Equipment: 7 apps (9%)
7. Construction/Building: 6 apps (8%)
8. Consumer Packaging: 6 apps (8%)
9. Industrial Packaging: 4 apps (5%)
10. Medical/Wellness: 4 apps (5%)
11. Recreation/Marine: 3 apps (4%)
12. Railway/Transportation: 2 apps (3%)

APPLICATIONS BY MACHINE SERIES:

1. PF1 X Series: 40 applications - MOST VERSATILE
2. PF1 Classic: 35 applications - WORKHORSE
3. FCS Series: 30 applications - HIGH VOLUME
4. AM Series: 25 applications - ENTRY LEVEL
5. IMG Series: 25 applications - QUALITY CRITICAL
6. PF1 W Series: 3 applications - WELLNESS SPECIALIST
7. PF1 M Series: 1 application - CAR MATS SPECIALIST
8. PF1 L Series: 1 application - LUGGAGE SPECIALIST

COMPANY CREDENTIALS:
- Global Presence: 35+ countries worldwide
- Experience: 40+ years in thermoforming
- Specialization: Custom tailor-made single sheet vacuum forming machines
- Headquarters: Mumbai, India
- Factory: Umargam, Gujarat, India""",
        knowledge_type="general",
        source_file=SOURCE_FILE,
        entity="Machinecraft",
        summary="Summary: 73 apps suitable, PF1 X most versatile (40 apps), commercial vehicle largest sector",
        metadata={
            "topic": "summary_statistics",
            "suitable_apps": 73,
            "excluded_apps": 12,
            "largest_sector": "commercial_vehicle",
            "most_versatile_machine": "PF1 X Series"
        }
    ))

    return items


def main():
    """Main ingestion function."""
    print("=" * 60)
    print("Machinecraft Complete Applications List Ingestion")
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
    print(f"  Items stored: {results.stored}")
    print(f"  Duplicates skipped: {results.duplicates}")

    return results


if __name__ == "__main__":
    main()
