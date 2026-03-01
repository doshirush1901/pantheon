#!/usr/bin/env python3
"""
Ingest PF1 Process Animation - Operator Workflow Knowledge

This document provides a scene-by-scene storyboard showing the practical
step-by-step workflow for operating a PF1-X thermoforming machine in an
industrial factory setting.

Key workflow stages:
1. Tool Loading - Using forklift, ball transfer units, pneumatic clamping
2. Sheet Material Selection & Loading - From magazine to automatic loader
3. Heater Setup - Using touchscreen HMI
4. Cycle Tuning - Manual mode fine-tuning (5-10 trial cycles)
5. Production - Auto mode continuous operation
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from openclaw.agents.ira.src.brain.knowledge_ingestor import KnowledgeIngestor, KnowledgeItem

SOURCE_FILE = "PF1 Process Anime.pdf"


def create_knowledge_items() -> list[KnowledgeItem]:
    """Create structured knowledge items from the PF1 process animation document."""
    items = []

    # 1. Complete Operator Workflow Overview
    items.append(KnowledgeItem(
        text="""PF1-X Thermoforming Machine Complete Operator Workflow (Industrial Factory Setting):

The PF1-X machine operation follows a structured workflow from setup to continuous production:

PHASE 1: TOOL LOADING (Scenes 1-7)
- Operator uses forklift to retrieve tool from tool magazine
- Drives tool to PF1-X machine with doors open for loading access
- Machine platen features ball transfer units for easy tool positioning
- Pneumatic clamp system for secure tool holding
- Tool is slid over ball transfer units until bolster locates and locks (audible "thud")
- Forklift lever dropped to place tool on bottom platen
- Tool easily adjusted on ball transfer units
- Two knobs turned to pneumatically clamp tool to machine

PHASE 2: SHEET MATERIAL PREPARATION (Scenes 8-11)
- Operator goes to cut sheet magazine
- Selects appropriate sheets from pallet storage
- Different materials available with varying properties:
  * Thicknesses
  * Gloss levels
  * Colors
  * Textures
  * Special properties
  * Opacity options
- Sheets loaded onto automatic sheet loader (located right side of machine)
- System includes automatic unloading for formed parts

PHASE 3: HEATER SETUP (Scene 12)
- Operator sets heater profile using touchscreen HMI
- Zone-by-zone temperature configuration

PHASE 4: CYCLE TUNING - MANUAL MODE (Human Ingenuity Phase)
- Machine run in manual mode for testing and fine-tuning
- Parameters adjusted:
  * Heating time
  * Sag control
  * Vacuum timing
  * Forming pressure
  * Cooling time
- Typically requires 5-10 trial cycles to find optimal process recipe
- This phase represents operator expertise and experience

PHASE 5: PRODUCTION - AUTO MODE
- Once optimal recipe found, parameters are locked and stored
- Operator switches to Auto Mode
- Machine runs continuous production with stored recipe
- Minimal operator intervention required during production""",
        knowledge_type="process",
        source_file=SOURCE_FILE,
        entity="PF1-X",
        summary="Complete PF1-X operator workflow from tool loading through sheet setup, cycle tuning, to auto production",
        metadata={
            "topic": "operator_workflow",
            "phases": 5,
            "trial_cycles": "5-10"
        }
    ))

    # 2. Tool Loading Process Details
    items.append(KnowledgeItem(
        text="""PF1-X Tool Loading Process - Detailed Steps:

EQUIPMENT REQUIRED:
- Forklift for tool transport
- Tool magazine for tool storage
- PF1-X machine with front doors open

STEP-BY-STEP TOOL LOADING:

Step 1: Tool Retrieval
- Operator uses forklift to access tool magazine
- Selects correct tool for scheduled production run
- Tool mounted on forklift for transport

Step 2: Machine Approach
- Operator drives forklift to PF1-X machine area
- Machine doors must be open to allow tool loading access
- Operator can see into the machine chamber

Step 3: Platen Features Visible (POV from operator):
- Ball transfer units on platen surface for easy sliding
- Pneumatic clamp system visible
- Locating features for precise positioning

Step 4: Tool Insertion
- Forklift enters chamber area (side view)
- Tool slid over ball transfer units
- Operator listens for audible "THUD" indicating:
  * Bolster below tool has found its location
  * Tool positioned correctly on platen for locking

Step 5: Tool Placement
- Forklift lever dropped down
- Tool drops onto bottom platen
- Ball transfer units allow easy final adjustment

Step 6: Tool Clamping (POV scene)
- Operator manually adjusts tool position using ball transfers
- Two knobs turned to engage pneumatic clamps
- Tool securely locked to machine platen

KEY FEATURES OF THIS SYSTEM:
- Ball transfer units eliminate need for heavy lifting
- Pneumatic clamping is fast (no manual bolting)
- Audible feedback confirms correct positioning
- Single operator can complete entire tool change
- Forklift accessibility designed into machine layout""",
        knowledge_type="process",
        source_file=SOURCE_FILE,
        entity="PF1-X",
        summary="Detailed tool loading process with forklift, ball transfer units, and pneumatic clamping",
        metadata={
            "topic": "tool_loading",
            "features": ["ball_transfer_units", "pneumatic_clamps", "forklift_accessible"]
        }
    ))

    # 3. Sheet Material Management
    items.append(KnowledgeItem(
        text="""PF1-X Sheet Material Selection and Loading Process:

SHEET MAGAZINE SYSTEM:
- Cut sheets stored on pallets in organized magazine
- Material options available:
  * Different thicknesses (varies by application)
  * Gloss levels (high gloss, matte, satin)
  * Colors (full color range)
  * Textures (smooth, textured, embossed)
  * Special properties (UV resistant, flame retardant, food-grade)
  * Opacity options (transparent, translucent, opaque)

MATERIAL SELECTION PROCESS:
1. Operator goes to cut sheet magazine
2. Reviews production requirements (material spec, thickness, finish)
3. Selects appropriate pallet of sheets
4. Loads pallet onto forklift

AUTOMATIC SHEET LOADER SYSTEM:
- Located on right side of PF1-X machine
- Dual function design:
  * Automatic sheet loading (input)
  * Automatic part unloading (output)
- Previous formed part sits on top of system after cycle
- Servo-driven for precision handling
- Multi-sheet detection prevents double-feeding

WORKFLOW:
1. Pallet with sheets moved to autoloader position
2. Autoloader picks individual sheets
3. Sheets fed into clamping frame automatically
4. After forming, finished parts ejected to autoloader top
5. Continuous operation with minimal manual intervention

ADVANTAGES OF AUTOMATIC LOADING:
- Reduces operator fatigue
- Consistent sheet positioning
- Faster cycle times
- Allows operator to monitor quality rather than material handling""",
        knowledge_type="process",
        source_file=SOURCE_FILE,
        entity="PF1-X",
        summary="Sheet material selection from magazine and automatic loading/unloading system",
        metadata={
            "topic": "sheet_handling",
            "material_options": ["thickness", "gloss", "color", "texture", "properties", "opacity"],
            "loader_position": "right_side"
        }
    ))

    # 4. Heater Profile Setup
    items.append(KnowledgeItem(
        text="""PF1-X Heater Profile Setup via Touchscreen:

TOUCHSCREEN HMI INTERFACE:
- Operator uses touchscreen to configure heating parameters
- Zone-based heater control for precise temperature distribution
- Visual representation of heater zones on screen

HEATER CONFIGURATION PARAMETERS:
- Individual zone temperatures
- Heating time (dwell time in heating position)
- Pre-heat settings
- Temperature ramp rates
- Zone groupings for material type

RECIPE MANAGEMENT:
- Multiple recipes can be stored in HMI memory
- Recipes linked to specific tools/products
- Quick recall for repeat jobs
- Recipe modification and saving capability

TYPICAL SETUP WORKFLOW:
1. Select existing recipe OR create new profile
2. Set temperature for each heater zone based on:
   - Material type (ABS, HDPE, PC, etc.)
   - Material thickness
   - Tool geometry (deep draw areas need more heat)
3. Set heating dwell time
4. Save configuration before proceeding to trial cycles

HEATER TYPES CONTROLLED:
- Ceramic heaters (standard)
- Quartz heaters (option)
- Halogen heaters (option)
All controlled through same touchscreen interface""",
        knowledge_type="process",
        source_file=SOURCE_FILE,
        entity="PF1-X",
        summary="Touchscreen-based heater profile configuration with zone control and recipe management",
        metadata={
            "topic": "heater_setup",
            "interface": "touchscreen_HMI",
            "control_type": "zone_based"
        }
    ))

    # 5. Cycle Tuning - Manual Mode (Human Ingenuity)
    items.append(KnowledgeItem(
        text="""PF1-X Cycle Tuning in Manual Mode - Human Ingenuity Phase:

PURPOSE:
This phase represents where operator skill and experience combine with 
machine capability to achieve optimal part quality.

MANUAL MODE OPERATION:
- Machine switched to manual control
- Operator has direct control over each process step
- Single cycles run with parameter observation
- Real-time adjustments made based on part quality

PARAMETERS TO FINE-TUNE:

1. HEATING TIME
- Duration sheet remains in heating position
- Too short: incomplete forming, thin spots
- Too long: sagging, burning, bubbling
- Adjust based on material response

2. SAG CONTROL (Pre-blow/Zero-sag)
- Air pressure to prevent/control sheet drooping
- Critical for even material distribution
- Adjust pressure and timing

3. VACUUM TIMING
- When vacuum is applied during forming
- Multi-step vacuum sequence tuning
- Delay timing relative to table movement

4. FORMING PRESSURE
- Intensity of vacuum/pressure during forming
- Affects detail definition
- Impacts cooling rate

5. COOLING TIME
- Duration before part ejection
- Too short: part distortion
- Too long: wasted cycle time
- May use temperature-based ejection trigger

TYPICAL TUNING PROCESS:
- Run 5-10 trial cycles minimum
- Inspect each part for defects
- Make incremental adjustments
- Document successful parameters
- Note material lot variations

THIS PHASE CAPTURES:
- Operator experience and intuition
- Material-specific behavior knowledge
- Tool-specific forming characteristics
- Quality standard requirements""",
        knowledge_type="process",
        source_file=SOURCE_FILE,
        entity="PF1-X",
        summary="Manual mode cycle tuning process requiring 5-10 trial cycles to optimize heating, sag, vacuum, pressure, and cooling",
        metadata={
            "topic": "cycle_tuning",
            "mode": "manual",
            "trial_cycles": "5-10",
            "parameters": ["heating_time", "sag_control", "vacuum_timing", "forming_pressure", "cooling_time"]
        }
    ))

    # 6. Auto Mode Production
    items.append(KnowledgeItem(
        text="""PF1-X Auto Mode Production - Continuous Operation:

TRANSITION FROM MANUAL TO AUTO:
Once cycle tuning is complete and optimal recipe found:
1. Parameters are locked in HMI
2. Recipe is saved for future use
3. Operator switches machine to Auto Mode
4. Machine takes over continuous production

AUTO MODE OPERATION:
- Machine executes complete cycle automatically:
  * Sheet loading (via autoloader)
  * Clamping
  * Heating
  * Pre-blow/sag control
  * Table up/forming
  * Vacuum/pressure application
  * Cooling
  * Part ejection (to autoloader)
- Cycle repeats continuously until:
  * Sheet stack depleted
  * Operator intervention
  * Fault condition

OPERATOR ROLE DURING AUTO:
- Monitor part quality (visual inspection)
- Remove finished parts from unload station
- Replenish sheet material as needed
- Watch for abnormal conditions
- Record production data

PRODUCTION BENEFITS:
- Consistent quality (stored parameters)
- High throughput (optimized cycle)
- Reduced operator fatigue
- Reproducible results
- Efficient material usage

RECIPE RECALL FOR FUTURE JOBS:
- When same tool/material combination returns
- Recall stored recipe from HMI
- Minimal re-tuning required (1-2 verification cycles)
- Fast changeover between jobs""",
        knowledge_type="process",
        source_file=SOURCE_FILE,
        entity="PF1-X",
        summary="Auto mode continuous production after recipe lock with operator monitoring role",
        metadata={
            "topic": "auto_mode",
            "transition": "manual_to_auto",
            "benefits": ["consistency", "throughput", "reproducibility"]
        }
    ))

    # 7. Key Operator Skills & Best Practices
    items.append(KnowledgeItem(
        text="""PF1-X Key Operator Skills and Best Practices:

ESSENTIAL OPERATOR SKILLS:

1. FORKLIFT OPERATION
- Safe tool transport
- Precise positioning in machine chamber
- Pallet handling for sheet materials

2. TOOL MANAGEMENT
- Tool identification from magazine
- Understanding tool requirements (material, thickness)
- Proper clamping verification

3. MATERIAL KNOWLEDGE
- Recognizing different plastic types
- Understanding thickness effects on forming
- Material storage and handling

4. HMI PROFICIENCY
- Touchscreen navigation
- Recipe creation and modification
- Parameter adjustment
- Alarm acknowledgment and troubleshooting

5. PROCESS UNDERSTANDING
- Recognizing quality defects
- Correlating defects to parameters
- Systematic troubleshooting approach

6. QUALITY ASSESSMENT
- Visual inspection skills
- Dimensional awareness
- Surface finish evaluation

BEST PRACTICES:

BEFORE PRODUCTION:
✓ Verify correct tool loaded and clamped
✓ Check material matches specification
✓ Confirm heater profile set correctly
✓ Inspect safety guards and interlocks

DURING CYCLE TUNING:
✓ Make one change at a time
✓ Document each adjustment
✓ Save known-good recipes immediately
✓ Keep sample parts for reference

DURING AUTO PRODUCTION:
✓ Regular quality spot-checks
✓ Monitor material supply levels
✓ Listen for unusual sounds
✓ Watch temperature displays

SHIFT HANDOVER:
✓ Document current recipe in use
✓ Note any quality observations
✓ Report any machine issues
✓ Brief incoming operator""",
        knowledge_type="general",
        source_file=SOURCE_FILE,
        entity="PF1-X",
        summary="Essential operator skills and best practices for PF1-X machine operation",
        metadata={
            "topic": "operator_skills",
            "skill_areas": ["forklift", "tool_management", "materials", "HMI", "process", "quality"]
        }
    ))

    # 8. PF1-X Machine Features for Easy Operation
    items.append(KnowledgeItem(
        text="""PF1-X Design Features Enabling Efficient Operator Workflow:

TOOL CHANGE SYSTEM:
- Ball transfer units on platen: Enable single-operator tool changes
- Pneumatic quick clamping: Two knobs vs. manual bolting
- Locating bolster: Audible feedback confirms position
- Front door access: Forklift can enter chamber directly

AUTOMATIC SHEET HANDLING:
- Integrated autoloader on right side
- Combined loading AND unloading function
- Multi-sheet detection prevents jams
- Servo-driven for reliability

TOUCHSCREEN HMI:
- Intuitive graphical interface
- Recipe storage and recall
- Visual heater zone display
- Clear alarm/fault messaging

MANUAL/AUTO MODE SWITCHING:
- Smooth transition between modes
- Parameters preserved when switching
- Safe mode transitions with interlocks

EUROPEAN FACTORY ENVIRONMENT:
- Designed for industrial production floors
- Forklift-accessible layout
- Tool magazine integration
- Organized material storage areas

OPERATOR-CENTRIC DESIGN BENEFITS:
1. Reduced physical strain (ball transfers, automation)
2. Faster changeovers (pneumatic clamping, recipe recall)
3. Consistent quality (stored recipes, auto mode)
4. Clear feedback (touchscreen, audible indicators)
5. Safety integration (interlocks, guarding)

This workflow design minimizes operator fatigue while maximizing
productivity and quality consistency across shifts.""",
        knowledge_type="machine_spec",
        source_file=SOURCE_FILE,
        entity="PF1-X",
        summary="PF1-X design features that enable efficient operator workflow including quick tool change and automation",
        metadata={
            "topic": "operator_centric_design",
            "features": ["ball_transfers", "pneumatic_clamps", "autoloader", "touchscreen_HMI"]
        }
    ))

    return items


def main():
    """Main ingestion function."""
    print("=" * 60)
    print("PF1 Process Animation Knowledge Ingestion")
    print("Source: PF1 Process Anime.pdf")
    print("=" * 60)

    items = create_knowledge_items()

    print(f"\nCreated {len(items)} knowledge items:")
    for i, item in enumerate(items, 1):
        print(f"  {i}. [{item.knowledge_type}] {item.summary[:60]}...")

    ingestor = KnowledgeIngestor()
    results = ingestor.ingest_batch(items)

    print("\n" + "=" * 60)
    print("INGESTION RESULTS")
    print("=" * 60)

    print(f"  Total items processed: {results.total_processed}")
    print(f"  Items stored: {results.stored}")
    print(f"  Duplicates skipped: {results.duplicates}")
    print(f"  Qdrant main: {'✓' if results.qdrant_main else '✗'}")
    print(f"  Qdrant discovered: {'✓' if results.qdrant_discovered else '✗'}")
    print(f"  Mem0: {'✓' if results.mem0 else '✗'}")
    print(f"  JSON backup: {'✓' if results.json_backup else '✗'}")

    print("\n" + "=" * 60)
    print("INGESTION COMPLETE")
    print("=" * 60)

    return results


if __name__ == "__main__":
    main()
