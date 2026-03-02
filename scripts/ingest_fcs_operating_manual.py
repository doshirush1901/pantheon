#!/usr/bin/env python3
"""
Ingest FCS Inline Pressure Forming Machine Operating Manual

Complete operating manual for Form-Cut-Stack machines covering:
- Tool mounting procedures
- HMI/PLC settings
- Process timing parameters
- Troubleshooting guide
- Maintenance schedule

Source: Abu Dhabi Inline manual (Ridat OEM partnership)
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from openclaw.agents.ira.src.brain.knowledge_ingestor import KnowledgeIngestor, KnowledgeItem

SOURCE_FILE = "Abudhabi-Inline.pdf"


def create_knowledge_items() -> list[KnowledgeItem]:
    """Create structured knowledge items from the FCS operating manual."""
    items = []

    # 1. Machine Overview & Process Flow
    items.append(KnowledgeItem(
        text="""FCS Inline Pressure Forming Machine - Process Overview

MACHINE TYPE: Inline Pressure Forming Machine (Form-Cut-Stack)
OEM PARTNER: Ridat (Abu Dhabi installation)

THREE STATIONS:
1. FORMING STATION - Pressure forming of sheet
2. PUNCHING STATION - Cutting/trimming formed parts
3. STACKING STATION - Automatic stacking of finished parts

MACHINE PROCESS FLOW:

Step 1: SHEET LOADING
- Sheet loaded on roll shaft
- Passed through guides to spike chain entry
- Sheet advance button loads onto conveying chain

Step 2: SHEET INDEXING
- Servo-driven chain advances sheet
- Index length programmable (up to 999.9mm)
- Index speed adjustable (100-800 mm/s)

Step 3: HEATING
- IR heaters (top and bottom - sandwich heating)
- 8 temperature zones
- 6 elements per line, 8 lines total (48 per side)
- PID temperature control

Step 4: PRESSURE FORMING
- Upper clamp comes down
- Mould platen moves up
- Forming air applied (up to 6 bar)
- Vacuum assists forming
- Part cools in mould

Step 5: PUNCHING/CUTTING
- Sheet indexes to punching station
- Top and bottom platens operate via crank mechanism
- Steel rule die cuts parts from web
- Servo-driven oscillating motion (CW/CCW)

Step 6: STACKING
- Vacuum pads pick cut parts
- Servo moves parts to conveyor
- Parts stacked to set count
- Conveyor advances stack

Step 7: OUTPUT
- Stacked parts conveyed to front
- Skeleton web exits rear
- Continuous operation""",
        knowledge_type="operational",
        source_file=SOURCE_FILE,
        entity="FCS Process",
        summary="FCS process: Sheet index → Heat (sandwich) → Pressure form → Punch/cut → Stack → Conveyor output",
        metadata={
            "topic": "process_overview",
            "stations": ["forming", "punching", "stacking"],
            "heating": "sandwich"
        }
    ))

    # 2. Tool Mounting Procedures
    items.append(KnowledgeItem(
        text="""FCS Tool Mounting Procedures

MOUNTING THE FORMING MOULD:

1. Preparation:
   - Remove water cooling pipes
   - Remove air pipe
   - Remove vacuum/release pipe

2. Access mould:
   - Move top forming platen down
   - Move bottom forming platen up
   - Open bolts of upper pressure box and lower mould

3. Remove old mould:
   - Place 2 mould slide guides for easy removal
   - Pull lower mould with pressure box onto slide guides
   - Remove mould once out of forming area

4. Install new mould:
   - Adjust chain conveying width if needed
   - Place mould with pressure box on slide guides
   - Slide onto platen
   - Center mould between chains
   - Bring mould up

5. Secure mould:
   - Move top platen down, bottom platen up
   - Bolt mould and upper pressure box
   - Adjust chain width (3-10mm gap from mould)

6. Connect utilities:
   - Connect water cooling lines
   - Connect release lines
   - Connect forming air to upper pressure box
   - Adjust heater gap (5-10mm from mould)

MOUNTING PUNCHING TOOL:

1. Remove upper and lower punching fixtures
2. Place lower fixture centered on platen, clamp
3. Run forming until sheet reaches punching station
4. Stop machine, adjust punching station to sheet center
5. Move bottom platen up
6. Place upper cutting die on formed sheet
7. Align die to center of sheet
8. Adjust upper platen so tool doesn't touch lower
9. Move top platen down
10. Adjust until cutting die presses against cutting plate
11. Increase cutting depth for proper cut at all 4 corners

MOUNTING STACKING TOOL:

1. Remove stacker vacuum pad frame
2. Fit new frame aligned with formed cavities
3. Bolt in place
4. Connect vacuum pipe to stacker frame""",
        knowledge_type="operational",
        source_file=SOURCE_FILE,
        entity="FCS Tool Mounting",
        summary="Tool mounting: mould via slide guides, punch alignment to sheet center, stacker vacuum pads",
        metadata={
            "topic": "tool_mounting",
            "procedures": ["mould", "punching", "stacking"]
        }
    ))

    # 3. Forming Station Parameters
    items.append(KnowledgeItem(
        text="""FCS Forming Station Timer Settings

FORMING STATION SEQUENCE & TIMERS:

Timer sequence (in order):

a) CHAIN ADVANCE DELAY
   - Starts when platens begin moving to home
   - After timer ends, chain advance starts

b) UPPER CLAMP DOWN DELAY
   - Starts after chain advance delay
   - Upper clamp moves down after timer

c) UPPER PLATE DOWN DELAY
   - Starts after chain advance delay
   - Upper plate moves down after timer

d) MOULD UP DELAY
   - Starts after chain advance delay
   - Mould platen moves up after timer

e) EJECTOR UP DELAY
   - Starts after chain advance delay
   - Ejector cylinder pushes ejector plate

f) FORMING DELAY
   - Starts after mould up delay timer
   - Wait before forming air

g) FORMING ON TIME
   - Forming air starts with this timer
   - Pressure applied to sheet

h) RELEASE DELAY TIME
   - Starts after forming ON time
   - Air from pressure box released through valve

i) RELEASE TIME
   - Release air (reverse ejection) active
   - Works if mould has reverse air ejection

j) UPPER CLAMP DELAY
   - After release timer, starts this
   - Upper clamp plate moves up after

k) TOP PLATE UP DELAY
   - After release timer, starts this
   - Top plate moves up after

l) MOULD DOWN DELAY
   - After release timer, starts this
   - Mould platen moves down after

m) EJECTOR DOWN DELAY
   - After release timer, starts this
   - Ejector cylinder moves down

CYCLE REPEATS: After timers j-m complete, chain advance (a) starts again

SETTING THE FORMING STATION:
- Top plate must lock fully with pressure box
- If plate too high: air leaks from pressure box
- If plate too low: toggles won't lock, no forming
- Toggles MUST fully lock for forming to work""",
        knowledge_type="operational",
        source_file=SOURCE_FILE,
        entity="FCS Forming Timers",
        summary="13 forming timers in sequence: clamp/plate delays, mould up, forming air, release, return cycle",
        metadata={
            "topic": "forming_parameters",
            "timer_count": 13
        }
    ))

    # 4. Punching Station Parameters
    items.append(KnowledgeItem(
        text="""FCS Punching Station Settings

PUNCHING STATION - SERVO CRANK MECHANISM:

The punching press uses oscillating crank motion:
- One cycle: Clockwise (CW)
- Next cycle: Counter-clockwise (CCW)
- Crank shaft degree controls position

PUNCHING PARAMETERS:

a) TOP PLATE DOWN DELAY
   - Timer for top platen movement
   - Driven by crank system

b) SERVO CW END DEGREE (5-100)
   - Clockwise rotation end point
   - 0 degrees = vertical straight up
   - Range: 5 to 100 degrees

c) SERVO CCW END DEGREE (260-355)
   - Counter-clockwise rotation end point
   - 360 degrees = vertical straight up
   - Range: 260 to 355 degrees

d) SERVO CW WAITING DEGREE (175-270)
   - CW rotation pause point
   - Allows floating die to align
   - Allows heating if heated tool used

e) SERVO CCW WAITING DEGREE (90-175)
   - CCW rotation pause point
   - Same purpose as CW waiting

f) WAITING TIME
   - Time crank stops at waiting degree
   - For alignment and heating

g) BOTTOM PLATE UP DELAY
   - Timer for bottom platen movement
   - Option: Lock bottom plate up (YES/NO)
   - Locked up = good for male formed parts

h) SPEED (RPM)
   - Motor speed for forward/reverse
   - Range: 50-3000 RPM
   - Typical: 1000-1500 RPM

SETTING PUNCHING STATION:
- Adjust at 4 corners for even cutting
- Ensure platens are parallel
- Don't set too low (tool damage)
- Slowly adjust platen height
- Check proper cut at all 4 corners

ADJUST PUNCH PRESS POSITION:
- Arrow keys move press position
- Must adjust when index length changes
- Center punch on indexed sheet""",
        knowledge_type="operational",
        source_file=SOURCE_FILE,
        entity="FCS Punching Settings",
        summary="Punching: servo crank oscillation (CW/CCW), degree settings for position, 1000-1500 RPM typical",
        metadata={
            "topic": "punching_parameters",
            "mechanism": "servo_crank_oscillating",
            "typical_rpm": "1000-1500"
        }
    ))

    # 5. Stacking Station Parameters
    items.append(KnowledgeItem(
        text="""FCS Stacking Station Settings

STACKING STATION PARAMETERS:

a) STACKER DOWN DELAY TIME
   - After cycle start, wait before moving down

b) STACKER MID POSITION DISTANCE
   - Distance where vacuum pads touch part
   - Critical for part pickup

c) STACKER MID POSITION SPEED
   - Speed from top to mid position
   - Controls approach to part

d) STACKER VACUUM DELAY TIME
   - Time from cycle start to vacuum ON
   - Ensures pads contact part first

e) STACKER VACUUM WAIT TIME
   - Wait at mid position with vacuum
   - Ensures part is gripped

f) STACKER DOWN DISTANCE
   - Distance to move toward conveyor
   - After vacuum wait time

g) STACKER DOWN SPEED
   - Speed moving toward conveyor

h) STACKER VACUUM RELEASE DELAY TIME
   - Timer starts when moving from mid to down
   - Vacuum turns OFF after timer

i) STACKER VACUUM RELEASE TIME
   - Wait at down position after vacuum OFF
   - Before returning to top

j) STACKING HEIGHT
   - Incremental height increase per part
   - Prevents pushing parts into each other
   - Protects stacked parts

k) STACK COUNT
   - Parts per stack before conveyor moves
   - Set based on part height and handling

l) STACKER UP SPEED
   - Speed returning to top position

m) CONVEYOR TIME
   - Duration conveyor runs after stack complete
   - Moves stack to front for pickup

SETTING STACKING STATION:
- Set platen strokes for specific part
- Adjust vacuum ON/OFF for proper grip
- Part must be held during full movement
- Test with actual parts""",
        knowledge_type="operational",
        source_file=SOURCE_FILE,
        entity="FCS Stacking Settings",
        summary="Stacking: vacuum pads, mid/down positions, stack count, conveyor timing; 13 parameters",
        metadata={
            "topic": "stacking_parameters",
            "parameter_count": 13,
            "mechanism": "vacuum_pads"
        }
    ))

    # 6. Heater Control System
    items.append(KnowledgeItem(
        text="""FCS Heater Control System

HEATER CONFIGURATION:
- Type: IR (Infrared) elements
- Arrangement: Top and Bottom (sandwich heating)
- Elements per line: 6
- Total lines: 8
- Total elements: 48 per side (96 total)

TEMPERATURE ZONES:
- 8 temperature zones total
- Each line typically = 1 zone
- Zone 1 = back of machine
- Zone 8 = front (toward operator)
- Thermocouple in 5th element from roll feed side

HEATER PERCENT ZONES:
- 3 percent zones per line
- First 2 elements = Zone A
- Last 4 elements = Zone B (with thermocouple)
- Individual element percentages adjustable

ZONE ASSIGNMENT:
- Each element can be assigned a zone
- Default: Line number = Zone number
- Zone "0" = percent control only (no temp feedback)
- Customize groupings as needed

HEATER SETTINGS:
- Temperature setpoint per zone
- Percent power per element (typical 90%)
- Fine-tune individual elements if needed
- PID control for temperature stability

PID TUNING:
- Kp, Ti, Kd, Td parameters available
- Default values can be restored
- Fine-tune for specific materials/conditions

AUTO HEATER POWER OFF:
- Safety feature
- Heaters turn OFF after set time if not used
- Prevents overheating during idle

HEATER STATUS INDICATORS:
- Yellow = Heaters ON
- Green = Heaters OFF
- Displayed on all HMI screens

HEATER MOVEMENT:
- Heaters slide forward/backward
- Position near mould for operation
- Move back when stopping
- 5-10mm gap from mould when forming""",
        knowledge_type="operational",
        source_file=SOURCE_FILE,
        entity="FCS Heater Control",
        summary="FCS heaters: 96 IR elements (48/side), 8 temp zones, PID control, zone assignment configurable",
        metadata={
            "topic": "heater_control",
            "elements_total": 96,
            "zones": 8,
            "control": "PID"
        }
    ))

    # 7. Troubleshooting Guide
    items.append(KnowledgeItem(
        text="""FCS Troubleshooting Guide

PROBLEM 1: HEATER DOES NOT SLIDE SMOOTHLY
Causes & Remedies:
- Grease the rails well
- Check machine level
- Ensure smooth movement

PROBLEM 2: FAILURE OF HEATER TO HEAT
Possible Causes:
1. Blown fuse on supply line or MCB tripped
2. Heater switch in "OFF" position
3. Temperature controller set to 0 or low
4. Incorrect percentage and zone assignment
5. Heater element faulty
6. Auto power off timer activated

PROBLEM 3: POOR FORMING DETAILS
Possible Causes:
1. Heater not fully warmed up
2. Heater not near the mould (move closer)
3. Insufficient heat exposure (increase cycle time)
4. Improper clamping
5. Poor moulds and dies
6. Air vent holes insufficient or improperly drilled

PROBLEM 4: PART DEFORMING AFTER FORMING
Cause: Insufficient cooling in mould
Remedies:
- Increase cooling time
- Provide air blast for cooling
- Increase air blast flow
- Check mould cooling water lines not blocked
- Ensure sufficient water circulation

PROBLEM 5: NO FORMING AIR DURING AUTO CYCLE
Cause: Toggles of forming station not locking fully
Remedy: Move top plate of forming station up slightly until toggles lock

PROBLEM 6: SHEET NOT ADVANCING IN MANUAL MODE
Cause: Stations not in Home position
Remedy: Check all stations are at Home position

DIAGNOSTIC TOOLS:
- INPUT STATUS screen shows all PLC inputs
- OUTPUT STATUS screen shows all PLC outputs
- Useful for identifying sensor/actuator issues
- DOG and LIMIT proximity switches for homing""",
        knowledge_type="operational",
        source_file=SOURCE_FILE,
        entity="FCS Troubleshooting",
        summary="Common issues: heater problems, poor forming, part deformation, toggle lock, sheet advance",
        metadata={
            "topic": "troubleshooting",
            "common_issues": 6
        }
    ))

    # 8. Maintenance Schedule
    items.append(KnowledgeItem(
        text="""FCS Maintenance Schedule

PRESS TOGGLES:
- Frequency: Every 20 hours OR every 3 days (whichever first)
- Action: Grease all moving parts (bushes)
- Note: Critical for smooth operation

LEAKAGE PREVENTION:
- Check: Rubber of forming station
- Action: Inspect for damage
- Replace if needed

HEATER RAILINGS:
- Frequency: Every 3 months or as required
- Action: Lubricate guides and slides
- Note: Pre-lubricated at factory

FRL UNIT (Filter-Regulator-Lubricator):
- Oil refill: Once per week or as required
- Water drain: Every 4 hours of operation
- Note: Critical for pneumatic system

PLATEN GUIDES:
- Frequency: Once per week
- Action: Grease with general-purpose grease
- Note: Ensures smooth platen movement

SAFETY CHECKS (Before operation):
- Verify all safety mechanisms working
- Check guards secured in place
- Test micro-switches and sensors
- Verify emergency stops function

GENERAL GUIDELINES:
- Maintenance by specialized personnel only
- Power OFF, air OFF, water OFF for most work
- Wait for machine to cool before maintenance
- Mark off work zone with tape
- Post warning signs during maintenance
- Function check after completing maintenance

LUBRICATION POINTS:
- Toggle bushings
- Heater slide rails
- Platen guide rails
- Chain guides
- All moving pivot points""",
        knowledge_type="operational",
        source_file=SOURCE_FILE,
        entity="FCS Maintenance",
        summary="Maintenance: toggles every 20hrs, FRL oil weekly, water drain 4hrs, platen guides weekly",
        metadata={
            "topic": "maintenance",
            "toggle_grease": "20 hours",
            "frl_oil": "weekly",
            "water_drain": "4 hours"
        }
    ))

    # 9. HMI Features & Recipe Management
    items.append(KnowledgeItem(
        text="""FCS HMI Features & Recipe Management

PLC/HMI SYSTEM:
- Mitsubishi PLC (typical)
- Touchscreen HMI
- Remote connectivity option (GOT IP address)

MAIN SCREEN FEATURES:
- Status indicators: Top heater, Bottom heater
- Machine status: Running/Tripped
- Home position indicator
- Operating mode: Auto/Manual
- Time display

HOME POSITION PROCEDURE:
- Required at power-up
- Press HOME for each servo platen
- Platen crosses DOG proximity switch
- When DOG turns OFF = HOME position reached
- Shows "HOME OVER" when complete

RECIPE MANAGEMENT:
- Save/Load function for product settings
- Up to 40 recipes storable
- Product number 1-40
- Saves all parameters for quick changeover
- Pop-up confirmation for save/load

SET VALUES SCREEN:
- Index Length: Up to 999.9mm
- Index Speed: 100-800 mm/s (500 max for thick sheets)
- Max Cycle Timer Overrun: Safety timeout
- Session Counter: Resets each startup
- Product Counter: Operator resetable
- Tool heating ON/OFF and percent

MANUAL MODE FEATURES:
- Individual platen control (up/down)
- Forming station: clamp, ejector, release, air bleed
- Punching station: CW/CCW crank control
- Stacking station: up/down/middle
- Chain bars: expand/contract
- Sheet advance, conveyor, pad vacuum

ALARM SCREEN:
- List of machine alarms
- Time of occurrence shown
- Must acknowledge alarms
- Continuous indication until cleared

REMOTE ACCESS:
- LAN connection to HMI
- Port 5015 for HMI programming
- Port 5014 for PLC programming/monitoring
- Static IP for remote connection""",
        knowledge_type="operational",
        source_file=SOURCE_FILE,
        entity="FCS HMI",
        summary="HMI: 40 recipes, home procedure, manual mode controls, alarm management, remote access option",
        metadata={
            "topic": "hmi_features",
            "recipe_capacity": 40,
            "remote_ports": [5014, 5015]
        }
    ))

    return items


def main():
    """Main ingestion function."""
    print("=" * 60)
    print("FCS Inline Operating Manual Ingestion")
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
