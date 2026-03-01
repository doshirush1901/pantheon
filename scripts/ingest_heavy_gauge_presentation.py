#!/usr/bin/env python3
"""
Ingest 02 Heavy Gauge - Presentation about thick gauge thermoforming

Source: Solera-Thermoform Group presentation from SPE 2008
Covers heavy gauge technologies, applications, and processes.
"""

import sys
import os
import importlib.util

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

spec = importlib.util.spec_from_file_location(
    "knowledge_ingestor",
    os.path.join(project_root, "openclaw/agents/ira/src/brain/knowledge_ingestor.py")
)
knowledge_ingestor_module = importlib.util.module_from_spec(spec)
sys.modules["knowledge_ingestor"] = knowledge_ingestor_module
spec.loader.exec_module(knowledge_ingestor_module)

KnowledgeIngestor = knowledge_ingestor_module.KnowledgeIngestor
KnowledgeItem = knowledge_ingestor_module.KnowledgeItem

SOURCE_FILE = "02 Heavy Gauge.pdf"


def create_knowledge_items() -> list:
    """Create knowledge items from heavy gauge presentation."""
    items = []

    # 1. Heavy Gauge Overview
    items.append(KnowledgeItem(
        text="""Heavy Gauge Thermoforming Overview:

SOURCE: Solera-Thermoform Group presentation by Daniele Versolato
EVENT: Society of Plastics Engineers (SPE) 2008

WHAT IS HEAVY GAUGE THERMOFORMING?
- Also called "thick gauge" or "thick sheet" thermoforming
- Uses plastic sheets typically 1.5mm to 12mm thick
- Produces structural parts, housings, panels, enclosures
- Contrasts with "thin gauge" (0.2-1.5mm) used for packaging

WHY CHOOSE HEAVY GAUGE THERMOFORMING?

1. DESIGN FREEDOM
   - Complex 3D shapes possible
   - Large parts without joints
   - Integrated functions (mounting points, ribs)

2. FASTER PROTOTYPING
   - Quick mould development vs injection
   - Lower tooling cost for iterations

3. NO CORROSION
   - Replaces metal parts
   - Weather resistant

4. NO DIMENSIONAL LIMITS
   - Parts up to 4m+ possible
   - Single-piece large housings

5. RECYCLING POSSIBILITIES
   - Thermoplastics are recyclable
   - Regrind possible

6. ENVIRONMENTALLY FRIENDLY
   - Lower energy than injection molding
   - Less material waste

7. FASTER PRODUCTION CYCLES
   - Compared to hand layup composites
   - Simpler than RTM/SMC

8. LOWER MOULD INVESTMENT
   - Aluminum moulds typical
   - 10-20% of injection mould cost

9. COLORED "INSIDE"
   - Sheet can be colored throughout
   - Easier painting if needed

SOLERA-THERMOFORM GROUP (Example Heavy Gauge Specialist):
- Facilities: 120,000 sqm (Veneto), 15,000 sqm (Tuscany)
- Material: 4 million kg/year processed
- Equipment: 30 vacuum forming machines (TVF, HPF, TSF)
- Post-processing: 21 CNC robots
- Tooling: 5,000+ moulds in stock""",
        knowledge_type="operational",
        source_file=SOURCE_FILE,
        entity="Heavy Gauge Thermoforming",
        summary="Heavy gauge (1.5-12mm) thermoforming overview - design freedom, no corrosion, lower tooling cost, large parts possible",
        metadata={
            "source": "Solera-Thermoform Group",
            "presenter": "Daniele Versolato",
            "event": "SPE 2008",
            "sheet_thickness": "1.5-12mm",
            "key_advantages": ["design_freedom", "fast_prototyping", "no_corrosion", "no_size_limits", "recyclable", "lower_tooling_cost"]
        }
    ))

    # 2. Heavy Gauge Applications
    items.append(KnowledgeItem(
        text="""Heavy Gauge Thermoforming Applications:

INDUSTRY SECTORS FOR HEAVY GAUGE:

1. CARAVAN AND CAMPERS
   - Exterior body panels
   - Interior wall panels
   - Roof sections
   - Wheel arches
   - Materials: ABS, ABS/PMMA, ABS/ASA

2. BEAUTY & FITNESS EQUIPMENT
   - Spa/jacuzzi shells
   - Tanning bed housings
   - Gym equipment covers
   - Materials: ABS, Acrylic

3. CAR WASHES
   - Equipment housings
   - Panels, covers
   - Chemical resistant materials

4. REFRIGERATION
   - Door liners
   - Interior panels
   - Display cases
   - Materials: ABS, HIPS, PP

5. INDUSTRIAL & AGRICULTURE VEHICLES
   - Tractor hoods, fenders
   - Combine harvester panels
   - Sprayer hoods
   - Materials: ABS/PMMA, ABS/ASA (UV stable)

6. BATHROOM FURNISHING
   - Bath tubs
   - Shower trays
   - Vanity tops
   - Materials: Acrylic, ABS

7. PROMOTION & ADVERTISING
   - 3D signage
   - Display units
   - Point-of-sale displays
   - Materials: PETG, Acrylic, ABS

8. MEDICAL APPARATUS
   - Equipment housings
   - Diagnostic machine covers
   - MRI/CT scanner panels
   - Materials: PC, ABS, FR grades

9. RIGID PACKAGING
   - Large containers
   - Pallets
   - Industrial bins
   - Materials: HDPE, PP, ABS

10. AUTOMOTIVE
    - Interior panels
    - Trunk liners
    - Wheel arch liners
    - Engine covers
    - Materials: ABS, PP, ABS/PC

11. MASS TRANSPORT - ROAD
    - Bus interior panels
    - Dashboard components
    - Luggage compartments
    - Materials: ABS, PP (flame retardant)

12. MASS TRANSPORT - RAILWAYS
    - Train interior panels
    - Seat backs
    - Ceiling panels
    - Wall cladding
    - Materials: FR ABS, FR PC (fire rated)

MACHINECRAFT PF1 SUITABILITY:
All above applications can be produced on PF1 machines:
- Vacuum forming: All applications
- Pressure forming (AM series): Detailed parts, automotive
- Twin sheet: NOT on standard PF1 (requires twin sheet machine)""",
        knowledge_type="application",
        source_file=SOURCE_FILE,
        entity="Heavy Gauge Applications",
        summary="12 industry sectors for heavy gauge: caravan, beauty/fitness, car wash, refrigeration, agriculture, bathroom, advertising, medical, packaging, automotive, bus, railway",
        metadata={
            "application_count": 12,
            "pf1_compatible": ["caravan", "beauty", "carwash", "refrigeration", "agriculture", "bathroom", "advertising", "medical", "packaging", "automotive", "bus", "railway"],
            "requires_twin_sheet": ["hollow_parts", "structural_panels"],
            "key_materials": ["ABS", "ABS/PMMA", "ABS/ASA", "Acrylic", "PC", "HDPE", "PP"]
        }
    ))

    # 3. Heavy Gauge Technologies
    items.append(KnowledgeItem(
        text="""Heavy Gauge Thermoforming Technologies:

THREE MAIN HEAVY GAUGE TECHNOLOGIES:

1. VACUUM FORMING (TVF - Traditional Vacuum Forming)
   
   Process Steps:
   a) CLAMPING - Sheet clamped in frame
   b) HEATING - IR heaters soften sheet
   c) BUBBLE - Pre-stretch with air (optional)
   d) VACUUM - Sheet pulled onto mould
   e) COOLING - Part cools on mould
   f) RELEASE - Part ejected
   
   Characteristics:
   - Simplest process
   - Lower pressure (atmospheric ~1 bar)
   - Good for large parts
   - Less definition than pressure forming
   - Lower tooling cost
   
   Machinecraft Machine: PF1 Series

2. HIGH PRESSURE FORMING (HPF)
   
   Process:
   - Same as vacuum forming BUT
   - Additional air pressure applied (3-6 bar)
   - Pressure pushes sheet into mould details
   
   Advantages:
   - Dimensional stability
   - More definition of forms and angles
   - Similar quality to injection molding
   - Lower tooling cost vs injection
   - Sharp corners, textures possible
   
   Applications:
   - Automotive interior panels
   - Medical equipment housings
   - Any part needing crisp details
   
   Machinecraft Machine: AM Series (Pressure Forming)

3. TWIN SHEET FORMING (TSF)
   
   Process:
   - Two sheets heated simultaneously
   - Each formed into separate moulds
   - Moulds close together
   - Sheets welded at contact points
   - Creates hollow structure
   
   Advantages:
   - Increased structural integrity and rigidity
   - Enclosed cross-section capability
   - Low tooling cost (vs blow molding)
   - Internal reinforcement options (foam fill)
   - Most thermoplastics compatible
   - Can mold different materials together
   
   Materials for Twin Sheet:
   - ABS ASA
   - ABS PMMA
   - ABS TPU (Soft Touch)
   - Polycarbonate
   - ABS/PC blend
   - ABS/PC + PVDF film
   - HDPE
   - PS (Polystyrene)
   
   Applications:
   - Pallets
   - Fuel tanks
   - Air ducts
   - Structural panels
   - Hollow housings
   
   Note: Machinecraft does NOT currently offer twin sheet machines.
   PF1 is single sheet only.""",
        knowledge_type="operational",
        source_file=SOURCE_FILE,
        entity="Heavy Gauge Technologies",
        summary="3 heavy gauge technologies: Vacuum Forming (PF1), High Pressure Forming (AM series), Twin Sheet Forming (not MC)",
        metadata={
            "technologies": ["vacuum_forming", "high_pressure_forming", "twin_sheet_forming"],
            "machinecraft_offers": ["vacuum_forming", "high_pressure_forming"],
            "not_offered": ["twin_sheet_forming"],
            "pressure_forming_pressure": "3-6 bar",
            "vacuum_forming_pressure": "~1 bar atmospheric"
        }
    ))

    # 4. Forming Methods - Male vs Female
    items.append(KnowledgeItem(
        text="""Heavy Gauge Forming Methods - Male vs Female Mould:

TWO FUNDAMENTAL FORMING APPROACHES:

1. DRAPE FORMING (Positive / Male Mould)
   
   Description:
   - Mould protrudes upward (convex)
   - Sheet drapes OVER the mould
   - Outside surface contacts mould
   
   Characteristics:
   - INSIDE surface is the "A" surface (show side)
   - Outside has mould texture/finish
   - Inside is smooth (air side)
   - Better wall distribution on inside corners
   - Thicker material at top of part
   - Thinner material at bottom/edges
   
   Best For:
   - Parts where inside appearance matters
   - Bath tubs, shower trays
   - Containers (inside visible)
   - When outside will be painted/covered
   
   Wall Thickness Pattern:
   - Thickest at top/center
   - Progressively thinner toward edges
   - Inside corners maintain thickness

2. CAVITY FORMING (Negative / Female Mould)
   
   Description:
   - Mould is recessed (concave cavity)
   - Sheet is drawn INTO the mould
   - Inside surface contacts mould
   
   Characteristics:
   - OUTSIDE surface is the "A" surface
   - Inside has mould texture/finish
   - Outside is smooth (air side)
   - Better wall distribution on outside corners
   - Thinner at bottom of cavity
   - More stretching in deep draws
   
   Best For:
   - Parts where outside appearance matters
   - Vehicle panels (exterior)
   - Enclosures, housings
   - Signage (viewed from outside)
   
   Wall Thickness Pattern:
   - Thinnest at bottom of cavity
   - Thicker at top/rim
   - Outside corners maintain thickness

WALL THICKNESS DISTRIBUTION COMPARISON:

                    MALE (Drape)    FEMALE (Cavity)
Top/Rim             Thickest        Thickest
Sidewalls           Medium          Medium  
Bottom/Center       Medium          Thinnest
Inside Corners      Good            Thin
Outside Corners     Thin            Good

PLUG ASSIST:
- Used with both methods
- Pre-stretches material before vacuum
- Improves wall distribution
- Essential for deep draws

MACHINECRAFT PF1 CAPABILITY:
- Supports both male and female moulds
- Plug assist optional
- Bottom table rises for male forming
- Top table descends for female forming
- Bubble (pre-stretch) available""",
        knowledge_type="operational",
        source_file=SOURCE_FILE,
        entity="Male vs Female Forming",
        summary="Male (drape) vs Female (cavity) forming - affects A-surface location, wall thickness distribution, application suitability",
        metadata={
            "forming_methods": ["male_drape", "female_cavity"],
            "male_best_for": ["bath_tubs", "containers", "inside_visible_parts"],
            "female_best_for": ["vehicle_panels", "enclosures", "signage"],
            "wall_distribution": "thinnest at deepest point of draw"
        }
    ))

    # 5. Materials for Heavy Gauge
    items.append(KnowledgeItem(
        text="""Materials for Heavy Gauge Thermoforming:

COMMON HEAVY GAUGE MATERIALS:

1. ABS (Acrylonitrile Butadiene Styrene)
   - Most common heavy gauge material
   - Good impact resistance
   - Easy to form, paint, bond
   - Sheet thickness: 1.5-12mm typical
   - Applications: Automotive, luggage, enclosures
   - Machinecraft: Primary material

2. ABS/ASA (ASA Cap Layer)
   - ABS with UV-stable ASA surface
   - Outdoor use without painting
   - Weather resistant
   - Applications: Agriculture equipment, outdoor panels
   - Premium pricing

3. ABS/PMMA (Acrylic Cap Layer)
   - ABS with high-gloss acrylic surface
   - Class A finish possible
   - Automotive exterior quality
   - Applications: Caravan panels, automotive
   - Can eliminate painting

4. ABS/TPU (Soft Touch)
   - ABS with soft TPU surface layer
   - Tactile, premium feel
   - Applications: Automotive interiors, consumer products

5. POLYCARBONATE (PC)
   - High impact resistance
   - Transparent/translucent options
   - Flame retardant grades
   - Applications: Medical, lighting, safety
   - More difficult to form than ABS

6. ABS/PC BLEND
   - Combines ABS formability with PC strength
   - Better impact than pure ABS
   - Applications: Automotive, medical

7. ABS/PC + PVDF FILM
   - Chemical resistant surface
   - For harsh environments

8. HDPE (High Density Polyethylene)
   - Chemical resistant
   - Lower cost
   - Applications: Tanks, containers, pallets
   - Weldable for twin sheet

9. PP (Polypropylene)
   - Chemical resistant
   - Lower cost than ABS
   - Living hinge capability
   - Applications: Automotive, packaging

10. PS/HIPS (Polystyrene / High Impact PS)
    - Lowest cost option
    - Good for refrigerator liners
    - Less impact than ABS

11. ACRYLIC (PMMA)
    - High gloss, clarity
    - Sanitaryware (bath tubs)
    - Requires careful heating

12. PETG
    - Clear, tough
    - FDA compliant
    - Applications: Medical, food, displays

MATERIAL SELECTION FOR MACHINECRAFT PF1:

Best Results:
- ABS (all variants): Ideal
- PP: Good, lower temperatures
- HDPE: Good for tanks
- PETG: Good for displays

More Challenging:
- PC: Higher temperatures, slower cooling
- Acrylic: Careful heat control needed

SHEET THICKNESS GUIDELINES:
- Light duty enclosures: 2-3mm
- Automotive panels: 3-5mm
- Structural parts: 5-8mm
- Heavy industrial: 8-12mm""",
        knowledge_type="operational",
        source_file=SOURCE_FILE,
        entity="Heavy Gauge Materials",
        summary="12 heavy gauge materials: ABS (most common), ABS/ASA, ABS/PMMA, PC, HDPE, PP, PETG - thickness 1.5-12mm",
        metadata={
            "primary_material": "ABS",
            "outdoor_materials": ["ABS/ASA", "ABS/PMMA"],
            "chemical_resistant": ["HDPE", "PP", "PVDF"],
            "transparent_options": ["PC", "PETG", "Acrylic"],
            "thickness_range": "1.5-12mm"
        }
    ))

    # 6. Heavy Gauge Sales Strategy
    items.append(KnowledgeItem(
        text="""Heavy Gauge Thermoforming - Sales Strategy for Machinecraft:

TARGET CUSTOMER IDENTIFICATION:

Based on heavy gauge applications, target these customer types:

1. CARAVAN/RV MANUFACTURERS
   - Need: Large panels, body parts
   - Machine: PF1 2000x2500 or larger
   - Materials: ABS/PMMA, ABS/ASA
   - Geography: Europe (strong market), Australia
   - Competitors: Injection, hand layup

2. SANITARYWARE MANUFACTURERS
   - Need: Bath tubs, shower trays
   - Machine: PF1 1500x2000+
   - Materials: Acrylic, ABS
   - Geography: Worldwide
   - Reference: Jaquar (Machinecraft customer)

3. AGRICULTURAL EQUIPMENT OEMs
   - Need: Tractor hoods, sprayer panels
   - Machine: PF1 1500x2000 to 2500x3000
   - Materials: ABS/PMMA, ABS/ASA (UV stable)
   - Geography: USA, Europe, India
   - Reference: SPE Ag Equipment study

4. BUS/COACH MANUFACTURERS
   - Need: Interior panels, luggage racks
   - Machine: PF1 1000x2000+
   - Materials: ABS (flame retardant)
   - Geography: India, Europe
   - Reference: Smartline Coach (customer)

5. RAILWAY INTERIOR SUPPLIERS
   - Need: Wall panels, ceiling panels
   - Machine: PF1 large format
   - Materials: FR ABS, FR PC
   - Certifications: Fire ratings required
   - Geography: Europe, India

6. MEDICAL EQUIPMENT MANUFACTURERS
   - Need: Equipment housings, covers
   - Machine: AM series (pressure forming)
   - Materials: ABS, PC, FR grades
   - Reference: Motherson Phillips SPM

7. REFRIGERATION COMPANIES
   - Need: Door liners, interior panels
   - Machine: PF1 medium sizes
   - Materials: ABS, HIPS
   - Volume: Can be high

COMPETITIVE POSITIONING:

Heavy Gauge vs Injection Molding:
- Lower tooling cost (10-20% of injection)
- Faster mould development
- Better for larger parts
- Lower volume economics
- Design changes easier

Heavy Gauge vs FRP/Composites:
- Faster cycle times
- More consistent quality
- Lower labor cost
- Recyclable material
- Automated process

SALES TALKING POINTS:

1. "Design freedom without injection tooling cost"
2. "Prototype to production in weeks, not months"
3. "Large parts as single piece - no joints"
4. "Class A surface with ABS/PMMA - no painting"
5. "Replace corroding metal parts with plastic"
6. "Lower total cost for volumes under 10,000/year"

MACHINE RECOMMENDATIONS BY APPLICATION:

| Application | Machine | Size Range |
|-------------|---------|------------|
| Caravan panels | PF1 | 2000x2500+ |
| Bath tubs | PF1 | 1500x2000+ |
| Tractor hoods | PF1 | 1500x2500+ |
| Bus interiors | PF1 | 1000x2000+ |
| Medical housings | AM | 600x800 to 1000x1500 |
| Signage | PF1/SAM | Various |
| Refrigerator | PF1 | 1000x1500 |""",
        knowledge_type="commercial",
        source_file=SOURCE_FILE,
        entity="Heavy Gauge Sales Strategy",
        summary="Sales strategy for heavy gauge: target caravan, sanitaryware, agriculture, bus, railway, medical, refrigeration sectors",
        metadata={
            "target_sectors": ["caravan", "sanitaryware", "agriculture", "bus", "railway", "medical", "refrigeration"],
            "competitive_advantages": ["lower_tooling_cost", "faster_development", "large_parts", "recyclable"],
            "key_talking_points": ["design_freedom", "fast_prototyping", "no_joints", "class_a_surface", "replace_metal"]
        }
    ))

    return items


def main():
    """Main ingestion function."""
    print("=" * 60)
    print("Heavy Gauge Thermoforming Presentation Ingestion")
    print("Source: " + SOURCE_FILE)
    print("=" * 60)

    items = create_knowledge_items()

    print(f"\nCreated {len(items)} knowledge items:")
    for i, item in enumerate(items, 1):
        print(f"  {i}. [{item.knowledge_type}] {item.summary[:60]}...")

    ingestor = KnowledgeIngestor()
    results = ingestor.ingest_batch(items)

    print("\n" + "=" * 60)
    print("INGESTION COMPLETE")
    print("=" * 60)

    return results


if __name__ == "__main__":
    main()
