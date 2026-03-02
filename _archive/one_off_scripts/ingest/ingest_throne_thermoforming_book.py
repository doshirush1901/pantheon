#!/usr/bin/env python3
"""
Ingest Technology of Thermoforming - James L. Throne (Hanser Publishers)

900-page comprehensive technical reference covering all aspects of thermoforming.
This script extracts and summarizes key technical concepts for the knowledge base.
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

SOURCE_FILE = "Tehcnology of Thermoforming - book 900 pages.pdf"


def create_knowledge_items() -> list:
    """Create knowledge items from Throne's thermoforming textbook."""
    items = []

    # 1. Thermoforming Fundamentals
    items.append(KnowledgeItem(
        text="""Thermoforming Process Fundamentals (from Throne's Technology of Thermoforming):

DEFINITION:
Thermoforming is the process of heating a plastic sheet to its softening point, 
stretching it over or into a mold, and cooling it to retain the molded shape.

KEY PRINCIPLE: "Thermoforming is not an easy process. It just looks easy."

TWO MAIN CATEGORIES:

1. THIN-GAGE THERMOFORMING (< 1.5mm / 60 mils):
   - Roll-fed continuous process
   - High-speed production (seconds per cycle)
   - Multiple cavities per cycle
   - In-line trimming
   - Applications: Packaging, cups, lids, trays
   - Machinecraft machines: FCS series, AM series

2. HEAVY-GAGE THERMOFORMING (> 3mm / 120 mils):
   - Sheet-fed process
   - Slower cycles (minutes)
   - Single or few cavities
   - Separate trimming operation
   - Applications: Automotive, industrial, housings
   - Machinecraft machines: PF1 series

PROCESS STEPS:
1. CLAMPING - Sheet secured in frame
2. HEATING - Sheet heated to forming temperature
3. PRE-STRETCHING - Optional bubble or plug assist
4. FORMING - Vacuum/pressure draws sheet to mold
5. COOLING - Part solidifies on mold
6. TRIMMING - Part separated from web

FORMING TEMPERATURE RANGES:
- PS: 120-150°C (250-300°F)
- ABS: 140-180°C (285-355°F)
- HIPS: 135-165°C (275-330°F)
- PP: 150-170°C (300-340°F)
- PC: 175-210°C (350-410°F)
- PETG: 120-150°C (250-300°F)
- Acrylic: 150-180°C (300-355°F)""",
        knowledge_type="operational",
        source_file=SOURCE_FILE,
        entity="Thermoforming Fundamentals",
        summary="Thermoforming fundamentals: thin-gage (<1.5mm, packaging) vs heavy-gage (>3mm, industrial); process steps and temperature ranges",
        metadata={
            "source_book": "Technology of Thermoforming",
            "author": "James L. Throne",
            "publisher": "Hanser",
            "thin_gage_threshold": "1.5mm / 60 mils",
            "heavy_gage_threshold": "3mm / 120 mils"
        }
    ))

    # 2. Forming Methods
    items.append(KnowledgeItem(
        text="""Thermoforming Methods Classification:

ONE-STEP FORMING METHODS:

1. DRAPE FORMING (Male/Positive Mold)
   - Simplest method
   - Sheet drapes over convex mold
   - No pressure differential needed
   - Inside surface is show surface
   - Good for shallow parts

2. STRAIGHT VACUUM FORMING (Female/Negative Mold)
   - Most common method
   - Vacuum draws sheet into cavity
   - Pressure differential: 0.05-0.09 MPa (7-14 psi)
   - Outside surface is show surface
   - Thinning at bottom corners

3. PRESSURE FORMING
   - Air pressure applied (up to 0.6 MPa / 90 psi)
   - Better detail definition
   - Sharper corners possible
   - Faster forming
   - Closer to injection quality

TWO-STEP FORMING WITH PRESTRETCHING:

4. BILLOW/BUBBLE FORMING
   - Air bubble pre-stretches sheet
   - More uniform wall thickness
   - Used for deep draws
   - Bubble height = 60-80% of draw depth

5. PLUG-ASSIST FORMING
   - Mechanical plug pre-stretches
   - Best wall distribution
   - Essential for deep draws
   - Plug material: Syntactic foam, UHMWPE, wood

6. BILLOW DRAPE FORMING
   - Bubble + male mold
   - Combines both advantages

MULTI-STEP FORMING:

7. SNAP-BACK FORMING
   - Vacuum box creates bubble
   - Mold rises into bubble
   - Vacuum snaps sheet to mold
   - Excellent uniformity

8. REVERSE DRAW WITH PLUG
   - Bubble, plug, then vacuum
   - Most uniform distribution
   - Complex but best results

9. TWIN-SHEET FORMING
   - Two sheets formed simultaneously
   - Welded together at seams
   - Creates hollow structures
   - Note: Not available on Machinecraft PF1

DEPTH-OF-DRAW GUIDELINES:
- Simple vacuum: 0.5:1 to 1:1 ratio
- With plug assist: 1:1 to 2:1 ratio
- With billow + plug: 2:1 to 3:1 ratio
- Maximum practical: 4:1 with optimal setup""",
        knowledge_type="operational",
        source_file=SOURCE_FILE,
        entity="Forming Methods",
        summary="9 forming methods: drape, vacuum, pressure, billow, plug-assist, snap-back, reverse draw, twin-sheet; depth ratios up to 4:1",
        metadata={
            "one_step_methods": ["drape", "vacuum", "pressure"],
            "two_step_methods": ["billow", "plug_assist", "billow_drape"],
            "multi_step_methods": ["snap_back", "reverse_draw", "twin_sheet"],
            "max_depth_ratio": "4:1"
        }
    ))

    # 3. Heating Principles
    items.append(KnowledgeItem(
        text="""Sheet Heating Principles in Thermoforming:

THREE HEAT TRANSFER MODES:

1. CONDUCTION
   - Heat transfer through solid material
   - Controls heavy-gage heating time
   - Thermal diffusivity is key property
   - Contact heating uses conduction

2. CONVECTION
   - Heat transfer via air movement
   - Used in recirculating ovens
   - Gentler heating for thick sheets
   - Hot air at 150-250°C typical

3. RADIATION (Most Common)
   - Infrared energy transfer
   - Most efficient for thin-gage
   - Heater types: Ceramic, Quartz, Halogen
   - Stefan-Boltzmann law governs

INFRARED HEATER CHARACTERISTICS:

CERAMIC HEATERS (e.g., Elstein FSR):
- Temperature: 300-500°C
- Wavelength: 3-6 microns (medium wave)
- Response time: 2-4 minutes
- Advantages: Uniform heating, durability
- Best for: Most polymers, steady production

QUARTZ HEATERS (e.g., Ceramicx):
- Temperature: 600-900°C
- Wavelength: 1.5-3 microns (short-medium wave)
- Response time: 30-90 seconds
- Advantages: Fast response, zone control
- Best for: Quick changeovers, crystalline polymers

HALOGEN HEATERS:
- Temperature: 1000-2000°C
- Wavelength: 0.8-1.5 microns (short wave)
- Response time: 1-5 seconds
- Advantages: Instant on/off, deep penetration
- Best for: Clear materials, thick sheets

HEATING TIME FACTORS:
- Sheet thickness (squared relationship)
- Polymer thermal properties
- Heater temperature and spacing
- Target forming temperature
- Heating method (one-side vs two-side)

RULE OF THUMB - Heating Time:
- Thin-gage (<1mm): 2-10 seconds
- Medium-gage (1-3mm): 15-60 seconds
- Heavy-gage (3-6mm): 2-5 minutes
- Extra heavy (>6mm): 5-15+ minutes

TEMPERATURE UNIFORMITY:
- Critical for consistent forming
- ±5°C variation acceptable
- Zone control helps edges
- Pyrometer monitoring recommended

ENERGY ABSORPTION:
- Depends on polymer type
- Clear materials: More penetration
- Pigmented: Surface absorption
- Black: Nearly all absorbed at surface""",
        knowledge_type="operational",
        source_file=SOURCE_FILE,
        entity="Heating Principles",
        summary="3 heat transfer modes; ceramic (3-6μm), quartz (1.5-3μm), halogen (0.8-1.5μm) heaters; heating time scales with thickness squared",
        metadata={
            "heat_transfer_modes": ["conduction", "convection", "radiation"],
            "heater_types": ["ceramic", "quartz", "halogen"],
            "ceramic_wavelength": "3-6 microns",
            "quartz_wavelength": "1.5-3 microns",
            "halogen_wavelength": "0.8-1.5 microns",
            "temp_uniformity_target": "±5°C"
        }
    ))

    # 4. Polymer Materials for Thermoforming
    items.append(KnowledgeItem(
        text="""Polymeric Materials for Thermoforming:

POLYMER CLASSIFICATION:

AMORPHOUS POLYMERS (Easier to form):
- No crystalline structure
- Gradual softening over temperature range
- Wide forming window
- Examples: PS, ABS, PC, PMMA, PVC

SEMI-CRYSTALLINE POLYMERS (More challenging):
- Crystalline regions in amorphous matrix
- Sharp melting point
- Narrow forming window
- Examples: PP, PE, PET, PA

KEY POLYMER PROPERTIES:

1. GLASS TRANSITION (Tg):
   - Temperature where polymer softens
   - Below Tg: Glassy, rigid
   - Above Tg: Rubbery, formable
   - Amorphous polymers: Form above Tg

2. MELT TEMPERATURE (Tm):
   - Crystalline regions melt
   - Semi-crystalline: Form near Tm
   - Too hot: Excessive sag, degradation

3. HOT STRENGTH (Melt Strength):
   - Resistance to stretching when hot
   - Critical for deep draws
   - High MW = better hot strength
   - Too low: Sag, blowouts

4. THERMAL PROPERTIES:
   - Heat capacity: Energy to raise temp
   - Thermal conductivity: Heat flow rate
   - Thermal diffusivity: Heating uniformity

FORMING WINDOWS BY POLYMER:

| Polymer | Tg (°C) | Forming Range (°C) | Notes |
|---------|---------|-------------------|-------|
| PS | 100 | 120-150 | Easy, wide window |
| HIPS | 100 | 135-165 | Rubber modified |
| ABS | 105 | 140-180 | Most popular |
| PMMA | 105 | 150-180 | Careful heating |
| PC | 150 | 175-210 | High temp needed |
| PVC | 80 | 100-140 | Low temp, narrow |
| PP | -10 (Tm=165) | 150-170 | Near melt point |
| HDPE | -120 (Tm=130) | 120-140 | Difficult |
| PET | 75 (Tm=255) | 85-100 or 140-170 | Two windows |
| PETG | 80 | 120-150 | Amorphous PET |

CRYSTALLIZATION HALF-TIMES (Rate of crystallization):
- PE: 5000 μm/min (very fast)
- PA66: 1200 μm/min
- PP: 20 μm/min
- PET: 10 μm/min
- PVC: 0.01 μm/min (very slow)

EFFECT ON FORMING:
- Fast crystallizers: Form quickly, cool fast
- Slow crystallizers: More processing time
- PET: Special handling for CPET vs APET""",
        knowledge_type="operational",
        source_file=SOURCE_FILE,
        entity="Polymer Materials",
        summary="Amorphous (wide window) vs semi-crystalline (narrow window) polymers; forming temperatures from 100°C (PVC) to 210°C (PC)",
        metadata={
            "amorphous_polymers": ["PS", "ABS", "PC", "PMMA", "PVC", "PETG"],
            "semi_crystalline": ["PP", "PE", "PET", "PA"],
            "easiest_forming": ["PS", "HIPS", "ABS"],
            "challenging_forming": ["PP", "HDPE", "PET"]
        }
    ))

    # 5. Sheet Stretching and Wall Thickness
    items.append(KnowledgeItem(
        text="""Sheet Stretching and Wall Thickness Distribution:

FUNDAMENTAL PRINCIPLE:
When sheet stretches, it thins. Total volume remains constant.
Original thickness × Original area = Final thickness × Final area

DRAW RATIO DEFINITIONS:

1. AREAL DRAW RATIO:
   Final surface area / Original sheet area
   Example: 3:1 means 3x surface area, ~1/3 thickness

2. LINEAR DRAW RATIO:
   Part depth / Minimum opening dimension
   Example: 100mm deep into 100mm opening = 1:1

3. H:D RATIO (Height to Diameter):
   Common specification method
   0.5:1 = Shallow
   1:1 = Medium
   2:1 = Deep
   3:1+ = Very deep (requires plug assist)

WALL THICKNESS PREDICTION:

Simple Geometry Method:
For female mold: t_wall = t_original × (Original area / Final area)

For cylinder, depth H, diameter D:
Sidewall thickness ≈ t_original × D / (D + 4H)

Example: 3mm sheet, D=200mm, H=150mm
Sidewall ≈ 3 × 200/(200 + 600) = 0.75mm (75% thinning)

FACTORS AFFECTING DISTRIBUTION:

1. MOLD TYPE:
   - Male: Thickest at top, thinnest at base
   - Female: Thickest at rim, thinnest at bottom corners

2. PLUG ASSIST:
   - Improves uniformity
   - Plug contacts sheet first
   - Material retained in contact area
   - Optimal plug: 80-90% of cavity size

3. BILLOW/BUBBLE:
   - Pre-stretches uniformly
   - Reduces corner thinning
   - Height = 50-80% of draw depth

4. SHEET TEMPERATURE:
   - Hotter = more stretching
   - Cooler areas = thicker
   - Edge cooling helps rim

5. FORMING SPEED:
   - Fast: More uniform (less cooling time)
   - Slow: More thinning in first-contact areas

MINIMUM WALL THICKNESS GUIDELINES:

| Application | Min Wall (mm) | Notes |
|-------------|---------------|-------|
| Packaging cups | 0.15-0.30 | Thin-gage |
| Food trays | 0.20-0.50 | Thin-gage |
| Industrial trays | 1.0-2.0 | Heavy-gage |
| Equipment housings | 2.0-4.0 | Structural |
| Automotive panels | 2.5-5.0 | Impact requirements |
| Bath tubs | 4.0-8.0 | Reinforced back |

CORNER RADII AND THINNING:
- Sharp corners = extreme thinning
- Minimum radius = 3× sheet thickness
- Preferred radius = 5-10× sheet thickness
- Inside corners: More critical than outside""",
        knowledge_type="operational",
        source_file=SOURCE_FILE,
        entity="Stretching and Wall Thickness",
        summary="Draw ratios up to 3:1+; wall thinning follows area ratio; minimum corner radius = 3× sheet thickness",
        metadata={
            "max_draw_ratio": "3:1+ with plug assist",
            "wall_thinning_formula": "t_final = t_original × (A_original/A_final)",
            "min_corner_radius": "3× sheet thickness",
            "plug_size_guideline": "80-90% of cavity"
        }
    ))

    # 6. Mold Design Principles
    items.append(KnowledgeItem(
        text="""Thermoforming Mold Design Principles:

MOLD MATERIAL SELECTION:

1. ALUMINUM (Production):
   - Most common production material
   - Good thermal conductivity
   - 100,000+ cycle life
   - Cast or machined
   - Temperature rating to 200°C
   - Cost: Medium-high

2. CAST EPOXY/RESIN (Prototype):
   - Low cost, fast to make
   - 1,000-25,000 cycles
   - Limited thermal conductivity
   - Temperature limit: 100-150°C
   - Good for development

3. SPRAY METAL (Medium runs):
   - Kirksite, zinc alloy
   - 25,000-50,000 cycles
   - Faster than machined aluminum
   - Good detail reproduction

4. ELECTROFORMED NICKEL:
   - Excellent detail
   - Thin shell with backing
   - 50,000-100,000 cycles
   - Good for textures

5. WOOD/MDF (Short runs):
   - Very low cost
   - 100-1,000 cycles
   - Prototype and samples only
   - Sealed surface required

VACUUM/VENT HOLE DESIGN:

Hole Diameter Guidelines:
- Thin-gage: 0.5-1.0mm
- Heavy-gage: 1.0-2.0mm
- Maximum: 3mm (to avoid witness marks)

Hole Spacing:
- General: 25-50mm apart
- Corners: Closer spacing (15-25mm)
- Flat areas: Can be wider (50-75mm)

Hole Placement:
- At lowest points of cavity
- In corners and details
- Not on cosmetic surfaces
- Use slots for edges

Total Vent Area Formula:
A_vent = Q / (C × √(2 × ΔP / ρ))
Where Q = Volumetric flow rate
      C = Discharge coefficient (0.6-0.8)
      ΔP = Pressure differential

RULE OF THUMB: Total vent area = 0.5-1.0% of mold surface area

MOLD TEMPERATURE CONTROL:

Coolant Channel Guidelines:
- Channel diameter: 8-12mm typical
- Channel spacing: 2-3× diameter from surface
- Water temperature: 40-80°C for most polymers
- Temperature variation: <5°C across mold

Cooling Time Factors:
- Sheet thickness (major factor)
- Polymer thermal properties
- Mold material conductivity
- Coolant flow rate

MOLD DRAFT ANGLES:

| Mold Type | Minimum Draft | Preferred Draft |
|-----------|---------------|-----------------|
| Male, textured | 3-5° | 5-7° |
| Male, smooth | 1-2° | 2-3° |
| Female, textured | 2-4° | 4-6° |
| Female, smooth | 0.5-1° | 1-2° |

UNDERCUTS:
- Generally not possible in basic thermoforming
- Collapsible cores for small undercuts
- Flexible sheet can allow minor undercuts
- Post-forming assembly preferred""",
        knowledge_type="operational",
        source_file=SOURCE_FILE,
        entity="Mold Design",
        summary="Mold materials: aluminum (100K cycles), epoxy (25K), wood (1K); vent holes 0.5-2mm, 25-50mm apart; draft 1-7° depending on texture",
        metadata={
            "mold_materials": ["aluminum", "epoxy", "spray_metal", "electroformed_nickel", "wood"],
            "aluminum_life": "100,000+ cycles",
            "vent_hole_diameter": "0.5-2.0mm",
            "vent_spacing": "25-50mm",
            "vent_area_percentage": "0.5-1.0%"
        }
    ))

    # 7. Part Design Guidelines
    items.append(KnowledgeItem(
        text="""Thermoformed Part Design Guidelines:

FUNDAMENTAL DESIGN RULES:

1. UNIFORM WALL THICKNESS:
   - Design for consistent stretching
   - Avoid abrupt thickness changes
   - Use gentle transitions
   - Consider draw ratio at design stage

2. CORNER RADII:
   - Inside radius: Minimum 3× sheet thickness
   - Outside radius: Minimum 1× sheet thickness
   - Larger radii = better strength
   - Sharp corners = stress concentration

3. DRAFT ANGLES:
   - Essential for part release
   - Male molds: 2-5° minimum
   - Female molds: 1-3° minimum
   - Textured surfaces: Add 1-2° extra
   - Deep parts: May need more draft

4. RIB AND BOSS DESIGN:
   - Ribs: Width = 0.5-0.7× wall thickness
   - Rib height: Up to 3× wall thickness
   - Boss diameter: 2-3× wall thickness
   - Avoid thick sections (sink marks)

5. UNDERCUTS:
   - Avoid if possible
   - Max undercut: 0.5-1mm for flexible parts
   - Use snap-fits instead
   - Consider assembly design

DEPTH OF DRAW GUIDELINES:

| Part Type | Max H:D Ratio | Forming Method |
|-----------|---------------|----------------|
| Shallow tray | 0.3:1 | Straight vacuum |
| Food container | 0.5:1 | Vacuum forming |
| Cup/tumbler | 1:1 | Plug assist |
| Deep container | 1.5:1 | Billow + plug |
| Very deep part | 2-3:1 | Multi-step |

TOLERANCE GUIDELINES:

Dimensional Tolerances:
- Length/Width: ±0.5-1.0%
- Depth: ±1.0-2.0%
- Wall thickness: ±10-15%
- Hole location: ±0.5mm

Factors Affecting Tolerance:
- Sheet thickness variation
- Temperature uniformity
- Mold accuracy
- Material shrinkage
- Post-cooling distortion

SHRINKAGE COMPENSATION:

| Polymer | Shrinkage (%) | Mold Oversize |
|---------|---------------|---------------|
| PS | 0.4-0.6 | 0.5% |
| ABS | 0.4-0.7 | 0.6% |
| PP | 1.5-2.5 | 2.0% |
| HDPE | 2.0-4.0 | 3.0% |
| PC | 0.5-0.7 | 0.6% |
| PETG | 0.2-0.5 | 0.4% |

STIFFENING FEATURES:

- Crowns and domes add rigidity
- Corrugations for flat panels
- Flanges for edges
- Steps and offsets
- Rolled edges for safety

ASSEMBLY CONSIDERATIONS:

- Design for snap-fits where possible
- Allow for fastener bosses
- Consider adhesive bonding areas
- Plan for secondary operations
- Nesting for shipping efficiency""",
        knowledge_type="operational",
        source_file=SOURCE_FILE,
        entity="Part Design Guidelines",
        summary="Design rules: corner radius ≥3× thickness, draft 1-5°, tolerance ±0.5-2%, shrinkage 0.4-4% by polymer",
        metadata={
            "corner_radius_rule": "≥3× sheet thickness",
            "draft_male": "2-5°",
            "draft_female": "1-3°",
            "dimensional_tolerance": "±0.5-2%",
            "wall_thickness_tolerance": "±10-15%"
        }
    ))

    # 8. Trimming and Secondary Operations
    items.append(KnowledgeItem(
        text="""Trimming and Secondary Operations in Thermoforming:

TRIMMING METHODS:

1. STEEL RULE DIE:
   - Most common for thin-gage
   - Knife edge in plywood backing
   - Shearing action
   - Cost-effective for simple shapes
   - Tolerance: ±0.5mm

2. MATCHED METAL DIE:
   - Punch and die set
   - Best accuracy
   - High volume production
   - More expensive tooling
   - Tolerance: ±0.2mm

3. CNC ROUTING:
   - Heavy-gage primary method
   - 3-axis or 5-axis
   - Excellent flexibility
   - Per-part programming
   - Tolerance: ±0.3mm

4. LASER CUTTING:
   - Clean edges
   - No tool wear
   - Complex shapes easy
   - Not for all materials
   - Heat-affected zone

5. WATER JET:
   - No heat affected zone
   - All materials
   - Slower than laser
   - Edge quality good

6. HAND TRIMMING:
   - Router, saw, knife
   - Prototype and low volume
   - Labor intensive
   - Variable quality

TRIMMING TIMING:

In-Mold Trim (Thin-gage):
- Trim while part still on mold
- Fastest cycle time
- Steel rule or matched die
- Part stays registered

In-Line Trim:
- Separate trim station
- Part moves from forming
- Allows inspection before trim
- Common for roll-fed

Off-Line Trim (Heavy-gage):
- Separate operation
- CNC routing typical
- Most flexibility
- Additional handling

CUTTING MECHANICS:

Five Cutting Mechanisms:
1. Compression (die cutting) - Thin sheet
2. Shear (punch and die) - General
3. Abrasion (sanding, routing) - Heavy-gage
4. Melting (laser, hot wire) - Some polymers
5. Erosion (water jet) - All materials

SECONDARY OPERATIONS:

1. Drilling and Machining:
   - CNC for accuracy
   - Consider thermal expansion
   - Support thin walls

2. Adhesive Bonding:
   - Surface preparation critical
   - Solvent welding for same materials
   - Structural adhesives for dissimilar

3. Mechanical Fastening:
   - Self-tapping screws
   - Threaded inserts
   - Rivets
   - Snap-fits (designed in)

4. Painting/Decorating:
   - Often unnecessary with colored sheet
   - Surface prep for adhesion
   - In-mold decoration alternative

5. Assembly:
   - Hot plate welding
   - Ultrasonic welding
   - Mechanical assembly
   - Adhesive bonding

REGRIND AND RECYCLING:

Regrind Guidelines:
- Typical: 20-30% regrind in new sheet
- Maximum: 40-50% for non-critical
- Color matching consideration
- Property degradation monitoring

Property Changes with Regrind:
- Molecular weight decreases
- Impact strength decreases
- Color may shift
- Melt flow increases""",
        knowledge_type="operational",
        source_file=SOURCE_FILE,
        entity="Trimming and Secondary Operations",
        summary="Trimming: steel rule die (±0.5mm), CNC routing (±0.3mm), matched die (±0.2mm); regrind typically 20-30%",
        metadata={
            "trimming_methods": ["steel_rule", "matched_die", "cnc_routing", "laser", "water_jet"],
            "steel_rule_tolerance": "±0.5mm",
            "cnc_tolerance": "±0.3mm",
            "matched_die_tolerance": "±0.2mm",
            "typical_regrind": "20-30%"
        }
    ))

    # 9. Newer Technologies
    items.append(KnowledgeItem(
        text="""Newer Thermoforming Technologies:

1. CRYSTALLIZING PET (CPET):
   - PET heated above Tg, formed, then crystallized
   - Two forming windows: 85-100°C or 140-170°C
   - Mold temperature: 150-180°C for crystallization
   - Creates heat-resistant parts
   - Ovenable food containers
   - Requires special equipment

2. PRESSURE FORMING:
   - Air pressure up to 0.6 MPa (90 psi)
   - Sharper detail than vacuum
   - Near-injection quality surface
   - Shorter cycle times
   - Higher tooling cost
   - Machinecraft: AM series

3. FILLED AND REINFORCED POLYMERS:
   - Glass fiber (10-30%)
   - Mineral fillers
   - Reduced stretching capability
   - Higher forming pressures needed
   - Compression/drape forming preferred
   - Limited deep draw

4. LAMINATED SHEET FORMING:
   - Multiple layers (cap/substrate)
   - ABS/PMMA, ABS/ASA common
   - Special heating considerations
   - Different thermal properties
   - Delamination risk if overheated

5. TWIN-SHEET FORMING:
   - Two sheets formed simultaneously
   - Fused together under pressure
   - Creates hollow structures
   - Pallets, ducts, tanks
   - Specialized equipment required
   - NOT available on standard PF1

6. POLYPROPYLENE FORMING:
   - Narrow forming window
   - Near melt temperature forming
   - Fast crystallization
   - Requires precise temperature control
   - Plug assist usually needed

7. FOAM SHEET FORMING:
   - Lower density materials
   - Insulation applications
   - Different heating approach
   - Surface skin considerations
   - Cell structure preservation

8. IN-MOLD DECORATION (IMD):
   - Decorative film in mold
   - Forms with part
   - No secondary painting
   - High-end automotive
   - Machinecraft: IMG machines

9. VACUUM LAMINATION:
   - Film applied to substrate
   - Under vacuum and heat
   - Automotive interior trim
   - Different from traditional forming
   - Machinecraft: PF1 adaptable

PROCESS MONITORING ADVANCES:

- Pyrometer temperature sensing
- Real-time sag detection
- Automatic zone adjustment
- Process data logging
- Statistical process control
- Predictive maintenance""",
        knowledge_type="operational",
        source_file=SOURCE_FILE,
        entity="Newer Technologies",
        summary="9 newer technologies: CPET, pressure forming, reinforced polymers, laminates, twin-sheet, PP forming, foam, IMD, vacuum lamination",
        metadata={
            "newer_technologies": ["CPET", "pressure_forming", "reinforced", "laminates", "twin_sheet", "PP_forming", "foam", "IMD", "vacuum_lamination"],
            "pressure_forming_max": "0.6 MPa / 90 psi",
            "cpet_mold_temp": "150-180°C",
            "machinecraft_offers": ["pressure_forming", "IMD", "vacuum_lamination"]
        }
    ))

    # 10. Troubleshooting Guide
    items.append(KnowledgeItem(
        text="""Thermoforming Troubleshooting Guide:

HEATING PROBLEMS:

Problem: Uneven Heating
- Causes: Heater failure, zone imbalance, draft
- Solutions: Check heaters, adjust zones, reduce air movement
- Prevention: Regular heater testing, pyrometer monitoring

Problem: Sheet Sag (Excessive)
- Causes: Overheating, wrong material, too long cycle
- Solutions: Reduce temperature, check material, shorten cycle
- Prevention: Sag sensors, process monitoring

Problem: Sheet Not Reaching Temperature
- Causes: Heater spacing, power insufficient, cold sheet
- Solutions: Adjust heater distance, increase power, preheat
- Prevention: Process parameter logging

FORMING PROBLEMS:

Problem: Webbing/Bridging
- Causes: Insufficient vacuum, cold spots, fast forming
- Solutions: Check vacuum system, increase temp, slow forming
- Prevention: Adequate vent holes, temperature uniformity

Problem: Thin Corners
- Causes: Excessive draw, no plug assist, cold sheet
- Solutions: Reduce depth, add plug, increase temperature
- Prevention: Proper part design, plug optimization

Problem: Incomplete Forming
- Causes: Low vacuum, cold sheet, blocked vents
- Solutions: Check vacuum pump, increase temp, clean vents
- Prevention: Maintenance schedule, process monitoring

Problem: Blowouts/Holes
- Causes: Overheating, weak spots, sharp mold edges
- Solutions: Reduce temperature, check sheet, radius edges
- Prevention: Temperature uniformity, mold inspection

COOLING PROBLEMS:

Problem: Warping/Distortion
- Causes: Uneven cooling, early release, mold too hot
- Solutions: Balance cooling, extend cycle, lower mold temp
- Prevention: Proper coolant system, timer optimization

Problem: Stress Whitening
- Causes: Cold forming, too fast, excessive stretching
- Solutions: Increase temperature, slow down, reduce draw
- Prevention: Proper forming temperature

Problem: Shrinkage Issues
- Causes: Mold too hot, wrong shrinkage factor
- Solutions: Cool mold more, adjust mold dimensions
- Prevention: Correct shrinkage compensation in mold design

TRIMMING PROBLEMS:

Problem: Angel Hair/Stringers
- Causes: Dull die, wrong clearance, material issue
- Solutions: Sharpen/replace die, adjust clearance
- Prevention: Die maintenance schedule

Problem: Edge Cracking
- Causes: Stress from forming, cold trimming, dull tooling
- Solutions: Anneal part, warm before trim, sharpen tools
- Prevention: Proper forming, timely trimming

MATERIAL PROBLEMS:

Problem: Moisture Issues
- Causes: Hygroscopic material not dried
- Solutions: Dry sheet before forming
- Prevention: Proper storage, drying equipment

Problem: Surface Defects
- Causes: Contamination, sheet quality, handling
- Solutions: Clean sheet, check supplier, improve handling
- Prevention: Quality inspection, clean room practices

SETUP CHECKLIST:

New Mold Setup:
1. Check mold dimensions vs drawing
2. Verify vent hole placement and size
3. Connect and test cooling
4. Set initial temperatures (conservative)
5. Run first shots at slow speed
6. Measure part dimensions
7. Adjust temperatures and timing
8. Document optimal parameters

New Material Setup:
1. Check material data sheet
2. Set temperatures for forming window
3. Start with lower temp, increase gradually
4. Watch for sag characteristics
5. Evaluate formability
6. Check cooling requirements
7. Document optimal settings""",
        knowledge_type="operational",
        source_file=SOURCE_FILE,
        entity="Troubleshooting Guide",
        summary="Troubleshooting: heating (uneven, sag), forming (webbing, thin corners), cooling (warping), trimming (angel hair); setup checklists",
        metadata={
            "problem_categories": ["heating", "forming", "cooling", "trimming", "material"],
            "common_heating_issues": ["uneven_heating", "excessive_sag", "cold_sheet"],
            "common_forming_issues": ["webbing", "thin_corners", "incomplete", "blowouts"],
            "common_cooling_issues": ["warping", "stress_whitening", "shrinkage"]
        }
    ))

    # 11. Process Economics
    items.append(KnowledgeItem(
        text="""Thermoforming Process Economics:

COST COMPONENTS:

1. MATERIAL COST (Typically 40-60% of total):
   - Sheet cost per kg
   - Sheet utilization efficiency
   - Regrind value
   - Scrap rate

   Material Utilization Calculation:
   Net part weight / Gross sheet weight × 100%
   Typical: 50-70% for thin-gage
   Typical: 30-50% for heavy-gage

2. LABOR COST (10-25%):
   - Operators
   - Setup time
   - Inspection
   - Secondary operations

3. MACHINE COST (10-20%):
   - Depreciation
   - Maintenance
   - Energy
   - Floor space

4. TOOLING AMORTIZATION (5-15%):
   - Mold cost / Expected production
   - Tool maintenance
   - Tool modifications

5. OVERHEAD (10-20%):
   - Facility costs
   - Quality control
   - Management
   - Shipping

CYCLE TIME ECONOMICS:

Cycle Time Components:
- Load time: 5-30 seconds
- Heat time: 10 seconds - 10 minutes
- Form time: 2-30 seconds
- Cool time: 5-60 seconds
- Unload time: 5-30 seconds

Productivity Calculation:
Parts/hour = 3600 / Cycle time (seconds) × Cavities

Example: 60-second cycle, 4 cavities
Parts/hour = 3600/60 × 4 = 240 parts/hour

BREAKEVEN ANALYSIS:

Thermoforming vs Injection Molding:
- Lower tooling cost: 10-20% of injection
- Higher part cost at high volume
- Crossover typically: 10,000-50,000 parts

Breakeven Formula:
N = (Tool_injection - Tool_thermo) / (Part_thermo - Part_injection)

Example:
Injection tool: $100,000, Part: $1.00
Thermo tool: $15,000, Part: $1.50
Breakeven: (100,000-15,000)/(1.50-1.00) = 170,000 parts

ENERGY COSTS:

Typical Energy Consumption:
- Heaters: 60-80% of total
- Vacuum/pressure: 10-20%
- Controls/cooling: 10-15%

Energy per Part:
- Thin-gage: 0.1-0.3 kWh/kg
- Heavy-gage: 0.2-0.5 kWh/kg

MATERIAL COST OPTIMIZATION:

Strategies:
1. Optimize sheet nesting
2. Maximize regrind usage
3. Negotiate volume pricing
4. Reduce thickness where possible
5. Consider alternative materials

Sheet Utilization Improvement:
- Multi-cavity molds
- Optimal sheet size selection
- Minimize skeleton (web) width
- Consider roll-fed for high volume

QUALITY COST CONSIDERATIONS:

Cost of Poor Quality:
- Scrap and rework
- Customer returns
- Lost production time
- Reputation damage

Investment in Quality:
- Process monitoring equipment
- Temperature control systems
- Inspection equipment
- Training

Typical Scrap Rates:
- Good process: 2-5%
- Average: 5-10%
- Poor: 10-20%+""",
        knowledge_type="commercial",
        source_file=SOURCE_FILE,
        entity="Process Economics",
        summary="Cost breakdown: material 40-60%, labor 10-25%, machine 10-20%; tooling breakeven vs injection typically 10,000-50,000 parts",
        metadata={
            "material_cost_percentage": "40-60%",
            "labor_cost_percentage": "10-25%",
            "tooling_breakeven": "10,000-50,000 parts",
            "typical_utilization_thin": "50-70%",
            "typical_utilization_heavy": "30-50%",
            "good_scrap_rate": "2-5%"
        }
    ))

    return items


def main():
    """Main ingestion function."""
    print("=" * 60)
    print("Technology of Thermoforming - James L. Throne")
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
