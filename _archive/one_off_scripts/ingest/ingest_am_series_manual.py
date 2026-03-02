#!/usr/bin/env python3
"""
Ingest AM Series Vacuum Forming Machine Operating Manual (Jan 2018)

Operating manual for AM Series roll-fed vacuum forming machines.
Covers setup, HMI operation, troubleshooting, and maintenance.

Key specs from manual:
- Model example: AM Ex 500x600
- Heater capacity: 16 kW
- Vacuum pump: 600 LPM
- Total power: 20 kW
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from openclaw.agents.ira.src.brain.knowledge_ingestor import KnowledgeIngestor, KnowledgeItem

SOURCE_FILE = "Manual for AM Series - Jan 2018.pdf"


def create_knowledge_items() -> list[KnowledgeItem]:
    """Create structured knowledge items from the AM Series manual."""
    items = []

    # 1. AM Series Overview
    items.append(KnowledgeItem(
        text="""AM Series Vacuum Forming Machine Overview

MACHINE TYPE: Roll-fed Vacuum Forming Machine
SERIES: AM (Entry-level/compact series)
DOCUMENT: Operating Manual, January 2018

EXAMPLE MODEL SPECS (AM Ex 500x600):
- Mould Platen Stroke: 150mm lower, 100mm upper
- Heater Capacity: 16 kW
- Vacuum Pump: 600 LPM
- Power: 380V, 3-phase, 50Hz
- Connected Power: 20 kW
- Total Wattage: 98 kW
- Weight: 1500 kg

STATIONS:
- Forming Station (top and bottom platens)
- Cross Cutting Station (optional)
- Sheet handling via spike chain conveyor

PROCESS FLOW:
1. Sheet loaded on roll shaft
2. Sheet passed through guides to spike chain
3. Sheet indexed (servo-driven chain)
4. Sheet heated (IR heaters)
5. Vacuum forming (mould up, frame down)
6. Cooling air applied
7. Release air for part ejection
8. Mould down, frame up
9. Sheet indexed to next cycle
10. Cross cutting (if equipped)

OPERATING MODES:
- Standard Mode: Sequential operation
- Optimized Mode: Overlapping operations for faster cycle""",
        knowledge_type="operational",
        source_file=SOURCE_FILE,
        entity="AM Series",
        summary="AM Series: roll-fed vacuum forming, 500x600 example, 16kW heaters, 600LPM vacuum, 20kW power",
        metadata={
            "topic": "machine_overview",
            "series": "AM",
            "example_model": "AM Ex 500x600",
            "power_kw": 20
        }
    ))

    # 2. Mould Mounting Procedure
    items.append(KnowledgeItem(
        text="""AM Series Mould Mounting Procedure

STEP-BY-STEP MOULD CHANGE:

1. PREPARATION:
   - Remove water cooling pipes (if connected)
   - Remove air cooling pipes (if connected)

2. ACCESS MOULD:
   - Move upper platen down fully
   - Move lower platen up via HMI mould up switch

3. REMOVE OLD MOULD:
   - Open bolts of upper frame clamping bracket
   - Move lower platen down
   - Upper frame moves down with mould
   - Move upper platen up
   - Remove upper frame
   - Open mould clamping bolts
   - Remove mould
   Note: Some machines have adjustable upper frame
   (only cross members need changing)

4. PREPARE FOR NEW MOULD:
   - Adjust chain conveying width if needed

5. INSTALL NEW MOULD:
   - Place mould on platen
   - Center between chains
   - Position edge near heater
   - Fit clamping brackets
   - Bring mould up

6. INSTALL UPPER FRAME:
   - Place upper frame on mould
   - Match frame with mould gasket
   - Move upper platen down
   - Clamp upper frame

7. FINAL ADJUSTMENTS:
   - Adjust chain width (2-3mm gap from mould)
   - Connect water cooling lines
   - Connect air cooling pipes
   - Test operation""",
        knowledge_type="operational",
        source_file=SOURCE_FILE,
        entity="AM Mould Mounting",
        summary="AM mould change: remove frame, swap mould, align gasket, set chain gap 2-3mm",
        metadata={
            "topic": "mould_mounting",
            "chain_gap_mm": "2-3"
        }
    ))

    # 3. Timer Settings & Cycle Parameters
    items.append(KnowledgeItem(
        text="""AM Series Timer Settings & Cycle Parameters

CYCLE TIMERS (in sequence):

1. CYCLE ADVANCE DELAY
   - Time before chain indexes
   - Standard: Waits for platens at home + timer
   - Optimized: Starts when platens pass middle switch

2. INDEX LENGTH
   - Sheet advance distance (mm)
   - Set per product/mould

3. INDEX SPEED
   - Chain movement speed
   - Range: 100-700 mm/s

4. FRAME DOWN DELAY
   - Time before top platen moves down
   - Standard: After chain fully indexed
   - Optimized: After indexing starts + timer

5. MOULD UP DELAY
   - Time before bottom platen moves up
   - Standard: After chain fully indexed
   - Optimized: After indexing starts + timer

6. VACUUM DELAY
   - Time before vacuum starts
   - Standard: After mould is up
   - Optimized: When mould starts moving up + timer

7. COOLING DELAY
   - Time before cooling air starts
   - Standard: After mould is up
   - Optimized: When mould starts moving up + timer

8. VACUUM ON TIME
   - Duration vacuum is applied
   - Set per part requirements

9. COOLING ON TIME
   - Duration cooling air runs
   - Set per part/material

10. RELEASE TIME
    - Duration of release air (ejection)
    - Starts after vacuum and cooling complete

11. MOULD DOWN DELAY
    - Time before platens return to home
    - After vacuum and cooling timers complete
    - Release continues if timer > this delay

ACTUAL CYCLE TIME:
- Displayed on HMI
- Use to optimize settings""",
        knowledge_type="operational",
        source_file=SOURCE_FILE,
        entity="AM Timers",
        summary="AM 11 timers: advance delay, index, frame/mould delays, vacuum/cooling on/delay, release",
        metadata={
            "topic": "timer_settings",
            "timer_count": 11,
            "index_speed_range": "100-700 mm/s"
        }
    ))

    # 4. Standard vs Optimized Mode
    items.append(KnowledgeItem(
        text="""AM Series: Standard vs Optimized Mode

TWO OPERATING MODES:

STANDARD MODE:
- Sequential operation
- Each step waits for previous to complete
- Chain waits for platens at home position
- Frame/mould wait for chain fully indexed
- Vacuum/cooling wait for mould fully up
- Safer, easier to set up
- Longer cycle time

OPTIMIZED MODE:
- Overlapping operations
- Faster cycle time
- Requires careful timer adjustment
- Risk of interference if set wrong

THREE LIMIT SWITCHES PER CYLINDER:
- Top (home position)
- Middle (optimization trigger)
- Bottom (full travel)

CHAIN ADVANCE OPTIMIZATION:
- Standard: Chain starts when platens at home (top switch)
- Optimized: Chain starts when platens pass middle switch
- Adjust middle switch so platens clear sheet path

FRAME/MOULD OPTIMIZATION:
- Standard: Platens move after chain fully indexed
- Optimized: Platens start moving during indexing
- Adjust delay so platens complete with chain movement
- If platens finish before chain = machine trips

VACUUM/COOLING OPTIMIZATION:
- Standard: Start after mould at top position
- Optimized: Start while mould moving up
- Vacuum ready just as mould contacts frame

OPTIMIZATION BENEFITS:
- Significantly faster cycle time
- More parts per hour
- Better productivity

OPTIMIZATION RISKS:
- Interference between sheet and platens
- Machine trips if timing wrong
- Requires experimentation to dial in""",
        knowledge_type="operational",
        source_file=SOURCE_FILE,
        entity="AM Operating Modes",
        summary="AM modes: Standard (sequential, safe) vs Optimized (overlapping, faster, needs careful setup)",
        metadata={
            "topic": "operating_modes",
            "modes": ["Standard", "Optimized"],
            "switches_per_cylinder": 3
        }
    ))

    # 5. Heater Control
    items.append(KnowledgeItem(
        text="""AM Series Heater Control System

HEATER POWER SCREEN:

TEMPERATURE ZONES:
- Multiple zones for uniform heating
- Set temperature per zone
- PLC calculates % power needed
- Heaters cycle ON/OFF per calculated %

THERMOCOUPLE ASSIGNMENT:
- Thermocouples placed row-wise
- Row 1 = back of machine
- Row 8 = front (toward operator)
- Normally: Sensor number = Zone number

SENSOR BYPASS FEATURE:
- If sensor fails, can assign working sensor
- Zone clones temperature of assigned sensor
- Allows continued operation with failed sensor

AUTO HEATER POWER OFF:
- Safety feature
- Heaters turn OFF if idle too long
- Prevents overheating during breaks
- Set timer for auto-off

HEATER STATUS INDICATORS:
- Yellow = Heaters ON
- Green = Heaters OFF
- Displayed on all HMI screens

HEATER MOVEMENT:
- Heaters slide on rails
- Forward position for forming
- Back position when stopped
- Control via HMI buttons

HEATER START SEQUENCE:
1. Set temperature per zone
2. Start heater power ON
3. Wait for heaters to warm up
4. Move heaters forward
5. Begin forming cycle""",
        knowledge_type="operational",
        source_file=SOURCE_FILE,
        entity="AM Heater Control",
        summary="AM heaters: zone temp control, PLC calculates %, auto-off safety, sensor bypass for failures",
        metadata={
            "topic": "heater_control",
            "zones": 8,
            "features": ["auto_off", "sensor_bypass"]
        }
    ))

    # 6. HMI Features
    items.append(KnowledgeItem(
        text="""AM Series HMI Features

MAIN SCREEN ELEMENTS:
- Shot counter (total cycles)
- Status indicators
- Navigation buttons

STATUS INDICATORS:
- Top heater power (Yellow=ON, Green=OFF)
- Machine status (Running/Stopped)
- Door status (Open/Closed)
- Vacuum pump (Yellow=ON, Green=OFF)
- Operating mode (Auto/Manual)
- Time display

MANUAL MODE FEATURES:
- Top platen up/down
- Bottom platen up/down
- Sheet advance button
- Sheet index button
- Sheet reverse button
- Cross cutter controls (if equipped)
- Vacuum ON/OFF
- Release air ON/OFF
- Cooling air ON/OFF

INPUT STATUS SCREEN:
- Shows all PLC input states
- Useful for diagnostics
- Verify sensor operation

OUTPUT STATUS SCREEN:
- Shows all PLC output states
- Useful for diagnostics
- Verify actuator commands

ADVANCED FUNCTIONS:
- Maximum cycle time setting
- Diagnostic functions
- Password protection (Levels 1-3)
- Passwords: "111", "222", "333"

RECIPE MANAGEMENT (LOAD/SAVE):
- Save all parameters to product number
- Load saved settings by product number
- Quick changeover between products

ALARM SCREEN:
- Shows fault conditions
- Alarm history stored
- Identifies cause of machine trips""",
        knowledge_type="operational",
        source_file=SOURCE_FILE,
        entity="AM HMI",
        summary="AM HMI: status display, manual controls, I/O diagnostics, recipe save/load, alarm history",
        metadata={
            "topic": "hmi_features",
            "password_levels": 3
        }
    ))

    # 7. Operating Sequence
    items.append(KnowledgeItem(
        text="""AM Series Operating Sequence

STARTUP SEQUENCE:

1. INITIAL STATE:
   - Heaters in back position
   - All platens at home position

2. START HEATERS:
   - Press "Heater Power" switch
   - Set temperatures per zone
   - Wait for heaters to reach temperature

3. PREPARE MACHINE:
   - Press "Operator Panel" switch
   - Start vacuum pump

4. LOAD SHEET:
   - Load sheet roll on shaft
   - Pass through guides
   - Position at spike chain entry

5. ADVANCE SHEET:
   - Press sheet advance button
   - Sheet loads onto chain rails
   - Adjust release air flow if needed

6. POSITION HEATERS:
   - Move heaters forward

7. VERIFY HOME POSITIONS:
   - Top platen up (Forming)
   - Bottom platen down (Forming)
   - Clamp bar up (Cross Cutting)
   - Blade forward/back fully (Cross Cutting)
   - Press "RESET STATIONS" if needed

8. START AUTO MODE:
   - Put machine in AUTO mode
   - Keep forming station switch OFF
   - Keep cross cutter switch OFF
   - Press "Cycle Start"

9. ACTIVATE STATIONS:
   - When sheet reaches forming station → Turn ON
   - When sheet exits cross cutter → Turn ON

SHUTDOWN SEQUENCE:

1. Press "Cycle Stop" (completes current cycle)
2. Or change to Manual mode (immediate stop)
3. Turn heaters OFF
4. Turn vacuum pump OFF
5. Move heaters backward
6. Turn main switch OFF""",
        knowledge_type="operational",
        source_file=SOURCE_FILE,
        entity="AM Operating Sequence",
        summary="AM startup: heaters→vacuum→load sheet→forward heaters→auto mode→activate stations sequentially",
        metadata={
            "topic": "operating_sequence"
        }
    ))

    # 8. Troubleshooting
    items.append(KnowledgeItem(
        text="""AM Series Troubleshooting Guide

PROBLEM 1: HEATER DOES NOT SLIDE SMOOTHLY
Solution:
- Grease the rails well
- Check machine level
- Oil heater trolley wheels

PROBLEM 2: FAILURE OF HEATER TO HEAT
Possible Causes:
1. MCB tripped in control panel
2. Heater switch in OFF position
3. Temperature set to 0 or low value
4. Heater element faulty
5. Auto power off timer activated

PROBLEM 3: POOR VACUUM FORMING DETAILS
Possible Causes:
1. Heater not fully warmed up
2. Insufficient heat exposure
   → Increase vacuum/cooling time (longer cycle)
3. Low voltage at input
4. Improper clamping
5. Poor moulds and dies
6. Insufficiently filled vacuum tank
7. Leakage in system (gaskets)
8. Vacuum holes insufficient or poorly drilled

PROBLEM 4: INSUFFICIENT VACUUM (per gauge)
Possible Causes:
1. Oil level in pump dropped
2. Vacuum valve not closing (dust on diaphragm)
   → Open valve and clean
3. Vacuum leakage from system
4. Plug under vacuum tank loose
5. Pump operating poorly
6. Faulty pipe to vacuum gauge

PROBLEM 5: NO VACUUM
Possible Causes:
1. Vacuum pipe blocked
2. No vacuum holes in mould

PROBLEM 6: PART DEFORMING AFTER FORMING
Cause: Insufficient cooling in mould
Solutions:
- Increase cooling time
- Provide blower for cooling
- Check mould cooling water lines
- Ensure sufficient water circulation""",
        knowledge_type="operational",
        source_file=SOURCE_FILE,
        entity="AM Troubleshooting",
        summary="AM issues: heater slide, no heat, poor forming, insufficient/no vacuum, part deformation",
        metadata={
            "topic": "troubleshooting",
            "common_issues": 6
        }
    ))

    # 9. Maintenance Schedule
    items.append(KnowledgeItem(
        text="""AM Series Maintenance Schedule

HEATER TRACK CLEANING:
- Clean tracks with cloth
- Check all 4 heater trolley wheels
- Oil wheels if not free moving
- Frequency: As needed

HEATER RAILINGS LUBRICATION:
- Pre-lubricated at factory
- Re-lubricate every 3 months
- Or as required

VACUUM PUMP:
- Fill with oil regularly
- Follow attached pump catalogue
- Check oil level frequently
- Critical for vacuum performance

FRL UNIT (Filter-Regulator-Lubricator):
- Oil refill: Every 4 weeks
- Water drain: Every 4 hours of operation
- Critical for pneumatic system

PLATEN GUIDES:
- Grease with general-purpose grease
- Frequency: Once per week
- Ensures smooth platen movement

VACUUM TANK:
- Drain tank weekly
- Open valve at bottom of tank
- Removes condensate and debris

GENERAL MAINTENANCE RULES:
- Power OFF for most maintenance
- Compressed air OFF
- Wait for machine to cool
- Use specialized personnel
- Mark off work zone
- Post warning signs
- Function check after maintenance

SAFETY CHECKS:
- Verify guards in place
- Test micro-switches and sensors
- Check emergency stops
- Ensure proper grounding""",
        knowledge_type="operational",
        source_file=SOURCE_FILE,
        entity="AM Maintenance",
        summary="AM maintenance: heater rails 3mo, FRL oil 4wks/water 4hrs, platen grease weekly, tank drain weekly",
        metadata={
            "topic": "maintenance",
            "heater_rails": "3 months",
            "frl_oil": "4 weeks",
            "frl_water": "4 hours",
            "platen_grease": "weekly",
            "tank_drain": "weekly"
        }
    ))

    return items


def main():
    """Main ingestion function."""
    print("=" * 60)
    print("AM Series Operating Manual Ingestion")
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
