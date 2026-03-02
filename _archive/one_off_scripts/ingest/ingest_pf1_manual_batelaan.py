#!/usr/bin/env python3
"""
Ingest PF1 Technical Manual - Batelaan - March 2019.

Source: data/imports/PF1 - Machinecraft - Manual - Batelaan - March 2019.docx.pdf
This is a comprehensive 53-page technical manual explaining how the PF1 vacuum forming 
machine works - covering architecture, process sequence, control systems, and operations.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "openclaw" / "agents" / "ira" / "skills" / "brain"))

from knowledge_ingestor import KnowledgeIngestor, KnowledgeItem

SOURCE_FILE = "PF1 - Machinecraft - Manual - Batelaan - March 2019.docx.pdf"


def create_knowledge_items() -> list[KnowledgeItem]:
    """Extract structured knowledge from PF1 technical manual."""
    items = []
    
    # Machine overview and architecture
    items.append(KnowledgeItem(
        text="""PF1 Machine Architecture Overview:

The PF1 (Polymer Forming 1) Series is Machinecraft's proprietary single-station vacuum forming 
machine design for processing large thermoplastic sheets. The 5th generation (2018) evolved since 1998.

KEY SUBSYSTEMS:
1. SHEET LOADING UNIT (ASL - Automatic Sheet Loader):
   - Servo-driven chain mechanism
   - Vacuum pad end-effector on telescopic rail
   - Handles cut sheets 2-12mm thickness
   - Sheet sizes up to 1080 x 1550mm
   - Max load: 16kg per sheet
   - Loading time: <10 seconds
   - Pneumatic push-off for part exit

2. FRAME ADJUSTMENT SYSTEMS:
   - Bottom Frame: 4 servo motors, 4 independent plates on ball-roller bearings
   - Top Frame: 2 servo motors, includes part holders for automatic release
   - Universal adjustment range: 550x550mm to 1000x1500mm
   - Changeover time: 1-2 minutes (vs 60+ mins for fixed frames)

3. TABLE 1 (Bottom - Mould Table):
   - Pneumatic driven with 4 cylinders + rack-pinion synchronization
   - Carries vacuum forming tool (MDF, Epoxy, or Aluminium)
   - Max mould weight: 500kg
   - Max part height: 500mm
   - Travel time: ~10 seconds
   - Optional pneumatic quick-clamping and cooling base

4. TABLE 2 (Top - Plug Assist Table):
   - 2 pneumatic cylinders
   - AC motor for height adjustment via HMI
   - Max load: 250kg
   - For plug assist materials (Nylon, CMT)
   - CE safety cylinder equipped

5. HEATING SYSTEM:
   - Sandwich configuration (top + bottom heaters)
   - Pneumatically actuated heater banks
   - Elstein Germany ceramic IR elements (245x60mm)
   - Top heater: 500W elements, 1:1 individual SSR control
   - Bottom heater: 350W elements, 1:2 paired SSR control
   - Zone-by-zone percentage and temperature control
   - Master-slave PID configuration with thermocouples""",
        knowledge_type="machine_spec",
        source_file=SOURCE_FILE,
        entity="PF1",
        summary="PF1 architecture: servo sheet loader, universal frames, pneumatic tables, sandwich heaters - 5th gen 2018",
        metadata={"topic": "machine_architecture", "generation": "5th", "year": 2018}
    ))
    
    # The vacuum forming process - complete cycle
    items.append(KnowledgeItem(
        text="""PF1 Vacuum Forming Process - Complete Cycle Sequence:

The PF1 operates in a precisely timed sequence. Here's how thermoforming works step-by-step:

PHASE 1: SHEET LOADING
- Vacuum pads pick sheet from stack
- Servo chain transports sheet into forming station via telescopic rail
- Sheet positioned over mould chamber

PHASE 2: CLAMPING
- Top frame moves down (pneumatic)
- Sheet clamped between top and bottom frames
- Creates air-tight seal for chamber pressurization

PHASE 3: HEATING
- Top heater bank moves forward over sheet
- Bottom heater bank moves forward under sheet (if enabled)
- Infrared heating - non-contact
- Zone-controlled for even heat distribution
- SAG CONTROL: Photocell detects sheet drooping
  - Air blown into chamber to push sheet back up
  - Maintains "zero-sag" for uniform heating
- Heating continues until sheet reaches forming temperature

PHASE 4: PRE-BLOW (Critical for even thickness)
- Heaters retract to park position
- Air blown INTO chamber from below
- Sheet forms UPWARD bubble (pre-blow bubble)
- Photocell monitors bubble height
- Purpose: Pre-stretches material BEFORE mould contact
- Result: More uniform wall thickness distribution

PHASE 5: FORMING
- Mould table rises (pneumatic)
- Mould pushes into pre-blown bubble
- Optional: Plug assist descends from top to push material into deep areas
- VACUUM activated - air evacuated through mould holes
- Atmospheric pressure forces sheet against mould surface
- Sheet conforms to mould geometry

PHASE 6: COOLING
- High-speed blowers activated
- Optional: Water mist spray for faster cooling
- Part solidifies on mould
- IR temperature sensor monitors part temperature

PHASE 7: RELEASE & EJECTION
- Release air blown through mould (reverse of vacuum)
- Part lifts off mould surface
- Mould table descends
- Top frame opens
- Formed part pushed out to exit chute
- Cycle repeats

WHY PRE-BLOW MATTERS:
Without pre-blow, the sheet would thin excessively where it first contacts the mould.
Pre-blow ensures the sheet is already stretched uniformly before mould contact,
resulting in consistent wall thickness across the part.""",
        knowledge_type="process",
        source_file=SOURCE_FILE,
        entity="PF1 Process",
        summary="PF1 vacuum forming cycle: load→clamp→heat→pre-blow→form→vacuum→cool→release - 7 phases explained",
        metadata={"topic": "forming_process", "phases": 7}
    ))
    
    # Cycle time breakdown
    items.append(KnowledgeItem(
        text="""PF1 Cycle Time Analysis (Example: ABS 2.5mm sheet):

DETAILED CYCLE BREAKDOWN:
| Step                        | Time (seconds) |
|-----------------------------|----------------|
| Sheet pickup & separation   | 6              |
| Sheet transport & part out  | 20             |
| Upper clamp frame down      | 8              |
| Heating unit forward        | 10             |
| Heating time                | 40             |
| Heating unit back           | 10             |
| Pre-blow active             | 5              |
| Lower table (mould) up      | 10             |
| Vacuum active               | 5              |
| Release air active          | 5              |
| Lower table down            | 10             |
| Cooling time                | 15             |
| Upper clamp frame up        | 8              |
|-----------------------------|----------------|
| TOTAL CYCLE                 | ~152 seconds   |

FACTORS AFFECTING CYCLE TIME:
- Material type: ABS, HDPE, PC, etc. have different heating requirements
- Sheet thickness: 2mm vs 8mm requires very different heating times
- Part geometry: Deep draws need longer vacuum and cooling
- Part size: Larger parts = longer heating, cooling
- Tool type: Aluminium tools cool faster than MDF/Epoxy

TYPICAL RANGES:
- Thin sheets (2-3mm): 90-150 seconds
- Medium sheets (4-6mm): 150-240 seconds
- Thick sheets (8-12mm): 240-400+ seconds

OUTPUT CALCULATION EXAMPLE:
- 152 second cycle = ~24 cycles/hour
- 8-hour shift = ~190 parts/day
- With efficient changeovers = 150-200 parts/day typical""",
        knowledge_type="machine_spec",
        source_file=SOURCE_FILE,
        entity="PF1",
        summary="PF1 cycle time: ~152s for 2.5mm ABS - heating 40s, cooling 15s, 24 cycles/hour",
        metadata={"topic": "cycle_time", "example_material": "ABS_2.5mm", "total_seconds": 152}
    ))
    
    # Heating system technical details
    items.append(KnowledgeItem(
        text="""PF1 Heating System - Technical Deep Dive:

HEATER ELEMENT SPECIFICATIONS:
- Type: Infrared (IR) ceramic elements
- Brand: Elstein Germany (premium quality)
- Element size: 245mm x 60mm
- Top heater power: 500W per element
- Bottom heater power: 350W per element
- Total heater capacity: 61-71 KW depending on model

CONTROL ARCHITECTURE:

TOP HEATER - 1:1 Control:
- Each element has its own SSR (Solid State Relay)
- Individual percentage control (0-100%)
- Maximum flexibility for heat distribution
- 36-54 zones depending on machine size

BOTTOM HEATER - 1:2 Control:
- Each SSR controls 2 elements (paired)
- More economical but less granular
- Still provides zone control
- 36-54 zones depending on machine size

ZONE CONTROL LOGIC:
1. Percentage Mode: Operator sets power % for each zone (e.g., 80%)
   - SSR switches element ON/OFF at set duty cycle
   
2. Temperature Mode (PID Control):
   - 4 thermocouples embedded in heater bank (P1-P4)
   - Zones assigned to follow a thermocouple (master-slave)
   - PID algorithm adjusts power to maintain setpoint
   - Auto-compensation: If temp rises above setpoint, reduces power
   - Max auto-increase: 10% above set percentage

HEATER SAFETY FEATURES:
- Forward/backward movement safety timers
- Auto power-off timer (heaters off if idle too long)
- Power save timer (reduces power between cycles)
- Emergency stop retracts heaters immediately

HEATER MOVEMENT:
- Pneumatically driven (or electric in some variants)
- Travel time: ~10 seconds each direction
- Interlock: Won't move forward unless frame locked, mould down, plug up""",
        knowledge_type="machine_spec",
        source_file=SOURCE_FILE,
        entity="PF1 Heaters",
        summary="PF1 heating: Elstein IR ceramic, 500W/350W elements, 1:1 top / 1:2 bottom SSR control, PID temperature control",
        metadata={"topic": "heating_system", "brand": "Elstein", "top_element_power": "500W", "bottom_element_power": "350W"}
    ))
    
    # Sag control and pre-blow systems
    items.append(KnowledgeItem(
        text="""PF1 Sag Control and Pre-Blow Systems - Technical Explanation:

WHY SAG CONTROL IS CRITICAL:
When plastic sheet heats up, it softens and droops (sags) due to gravity.
Uncontrolled sag causes:
- Uneven heating (sagged areas closer to bottom heater)
- Risk of sheet touching bottom heater (damage)
- Inconsistent forming results

SAG CONTROL MECHANISM:
1. Infrared photocell (transmitter + receiver) positioned below sheet
2. When sheet sags and breaks the beam → sag detected
3. PLC triggers air injection into chamber
4. Air pressure pushes sheet back up
5. Cycle repeats to maintain "zero-sag"

Components:
- Pepperl+Fuchs IR photocell (IRSAG)
- Air support control cylinder (SCOH mechanism on front door)
- Pneumatic cylinder for controlled air pulses

PRE-BLOW SYSTEM - THE KEY TO EVEN THICKNESS:

Purpose: Pre-stretch the sheet BEFORE mould contact for uniform wall distribution.

HOW IT WORKS:
1. After heating complete, heaters retract
2. Pre-blow delay timer starts (adjustable)
3. Air blown INTO sealed chamber from below
4. Sheet forms an UPWARD dome/bubble
5. Bubble height monitored by photocell (IRPB)
6. Air regulated to achieve target bubble height
7. Mould then rises into the pre-formed bubble

TIMING STRATEGY:
- Pre-blow delay: Adjust so bubble forms just as mould starts rising
- This prevents bubble from cooling/collapsing before forming
- If air leaks, delay pre-blow so mould catches bubble immediately

TECHNICAL SPECIFICATIONS:
- Pre-blow photocell: Pepperl+Fuchs (height sensing)
- Bubble height: Adjustable via transmitter/receiver positioning
- Air pressure: Separately regulated from main pneumatics
- Chamber seal: Critical - must be air-tight for proper bubble formation

TROUBLESHOOTING POOR PRE-BLOW:
- Check gaskets on all chamber openings
- Verify chamber door seals properly
- Check bottom frame rubber gaskets
- Inspect chamber open cylinder function""",
        knowledge_type="process",
        source_file=SOURCE_FILE,
        entity="PF1 Sag/Pre-blow",
        summary="PF1 sag control: IR photocell detects droop, air maintains zero-sag; Pre-blow creates bubble for even thickness",
        metadata={"topic": "sag_preblow_systems", "sensor": "Pepperl+Fuchs"}
    ))
    
    # Vacuum and forming system
    items.append(KnowledgeItem(
        text="""PF1 Vacuum System - Technical Details:

VACUUM SYSTEM COMPONENTS:
- Vacuum pump: Busch Germany, 100 m³/hr capacity
- Vacuum reservoir/tank: Stores vacuum for instant draw
- Vacuum solenoid valve: Controls vacuum release to mould
- Piping: From tank → chamber → mould

HOW VACUUM FORMING WORKS:
1. Mould has many small holes drilled throughout surface
2. These holes connect to vacuum chamber below mould
3. When vacuum valve opens, air evacuated from mould surface
4. Atmospheric pressure (1 bar = 14.7 psi) pushes soft sheet
5. Sheet conforms tightly to every mould detail
6. Vacuum held until part cools and solidifies

VACUUM TIMING SEQUENCE:
1. Mould reaches UP position
2. Vacuum delay timer runs (allows plug to stretch if used)
3. Vacuum valve opens
4. Vacuum ON timer runs (typically 5-10 seconds)
5. Sheet fully conformed
6. Vacuum valve closes
7. Vacuum held in chamber by check valves until release

VACUUM TROUBLESHOOTING:
- No vacuum buildup: Check pump, solenoid, piping leaks
- Part doesn't form: Check mould holes (blocked?), gaskets, sheet heating
- Vacuum gauge readings: Monitor for consistent performance

VACUUM SPECIFICATIONS:
- Pump capacity: 100 m³/hr
- Tank: Sized for instant vacuum draw
- Typical vacuum level: -0.8 to -0.9 bar
- Draw time: 3-5 seconds typical for full vacuum""",
        knowledge_type="machine_spec",
        source_file=SOURCE_FILE,
        entity="PF1 Vacuum",
        summary="PF1 vacuum: Busch 100m³/hr pump, reservoir tank, solenoid valve - atmospheric pressure (14.7psi) forms sheet",
        metadata={"topic": "vacuum_system", "pump_brand": "Busch", "capacity": "100m3/hr"}
    ))
    
    # Plug assist system
    items.append(KnowledgeItem(
        text="""PF1 Plug Assist System - Technical Explanation:

WHAT IS PLUG ASSIST?
A secondary tool (plug) that descends from above to mechanically push/stretch
the heated sheet into deep mould cavities BEFORE vacuum is applied.

WHY PLUG ASSIST IS NEEDED:
- Deep draw parts (height > 50% of width) get very thin at bottom
- Vacuum alone pulls material from edges, leaving bottom thin
- Plug physically pushes material DOWN into cavity
- Results in more uniform wall thickness in deep parts

PLUG ASSIST MECHANISM:
- Table 2 (top table) holds the plug
- 2 pneumatic cylinders drive plug down/up
- AC motor allows stroke height adjustment via HMI
- Max plug load: 250kg
- CE safety cylinder prevents uncontrolled drop

PLUG MATERIALS:
- Nylon: Good all-around material, low friction
- CMT (Composite Mould Technology): Insulating, won't cool sheet
- Syntactic foam: Lightweight, good insulation
- Wood with felt covering: Economic option

PLUG TIMING (Critical for quality):
1. Heaters retract → Mould up delay + Plug down delay timers start
2. Plug delay usually shorter than mould delay
3. Plug descends FIRST, stretches sheet into cavity
4. Mould rises and meets plug-stretched sheet
5. Vacuum applied - sheet conforms to mould
6. Plug retracts (optional: stays for support during release)

PLUG STROKE ADJUSTMENT:
- Set via HMI screen (Set Plug function)
- Proximity switches at stroke ends
- Adjust stroke to match part depth
- Too much stroke: Sheet too thin
- Too little stroke: Poor material distribution

PLUG SUPPORT OPTION:
- Plug can stay down during release to support part
- Prevents part deformation on deep draws
- Plug retracts only after part stabilized""",
        knowledge_type="machine_spec",
        source_file=SOURCE_FILE,
        entity="PF1 Plug Assist",
        summary="PF1 plug assist: top table pushes sheet into deep cavities before vacuum, 250kg capacity, Nylon/CMT materials",
        metadata={"topic": "plug_assist", "max_load": "250kg", "materials": ["nylon", "cmt", "syntactic_foam"]}
    ))
    
    # Control system and HMI
    items.append(KnowledgeItem(
        text="""PF1 Control System and HMI - Technical Overview:

PLC SYSTEM:
- Brand: Mitsubishi
- Controls all machine operations via programmed logic
- Manages interlocks (safety conditions that must be met)
- Stores timing parameters and sequences
- Provides diagnostic and alarm functions

HMI (Human Machine Interface):
- Brand: Mitsubishi 10" touch screen
- Right-swinging console mount
- User-friendly interface designed for operators
- Multiple screens for different functions

KEY HMI SCREENS:

1. START SCREEN - Status indicators:
   - Light guard (cut/through)
   - Mould door (open/closed)
   - Frame position (down/safe/unsafe)
   - Plug position (safe/unsafe)
   - Machine health (healthy/tripped)
   - Heater status (ON/OFF)
   - Vacuum pump status
   - Sheet sag indicator
   - Pre-blow status
   - Operating mode (Auto/Manual)

2. OPERATOR PANEL - Manual controls:
   - Top/Bottom heater forward/back
   - Mould up/down (jog and full stroke)
   - Plug up/down
   - Vacuum ON/OFF
   - Water spray
   - Blowers
   - Release air
   - Pre-blow
   - Frame lock/open
   - Mode selection (Auto/Manual)

3. SET VALUES - Timers and parameters:
   - Heating times (top and bottom)
   - Pre-blow delay and duration
   - Mould up delay
   - Plug down delay and duration
   - Vacuum delay and duration
   - Cooling time
   - Release air time
   - Water mist timing
   - Power save timers
   - Safety movement timers

4. HEATER SCREENS - Zone control:
   - Percentage setting for each zone (0-100%)
   - Temperature setpoints for thermocouple zones
   - Zone grouping (assign to P1-P4 thermocouples)
   - PID tuning parameters

5. ADVANCED FUNCTIONS:
   - Cycle counter
   - Hour meter
   - Recipe save/load (store settings for different products)
   - Password-protected levels (1-4)
   - Date/time settings
   - Speed indicators
   - PID tuning

6. I/O STATUS - Diagnostics:
   - Shows all PLC input states (limit switches, photocells)
   - Shows all PLC output states (solenoids, contactors)
   - Critical for troubleshooting

7. ALARMS - History and diagnostics:
   - Records all alarm events
   - Helps identify recurring issues""",
        knowledge_type="machine_spec",
        source_file=SOURCE_FILE,
        entity="PF1 Controls",
        summary="PF1 controls: Mitsubishi PLC + 10\" HMI, recipe storage, zone heater control, I/O diagnostics, alarm history",
        metadata={"topic": "control_system", "plc_brand": "Mitsubishi", "hmi_size": "10_inch"}
    ))
    
    # Component brands and specifications
    items.append(KnowledgeItem(
        text="""PF1 Component Brands and Specifications:

PREMIUM INTERNATIONAL BRANDS USED:

HEATING SYSTEM:
- Infrared Elements: Elstein Germany (ceramic IR)
- SSR (Solid State Relays): Crydom
- IR Temperature Reader: Raytek

CONTROL & AUTOMATION:
- PLC: Mitsubishi
- HMI: Mitsubishi 10" touch screen
- Servo Drive System: Mitsubishi

PNEUMATICS:
- Valves: Festo
- Cylinders: Festo

VACUUM:
- Vacuum Pump: Busch Germany (100 m³/hr)

COOLING:
- Blowers: Ebm Papst (India) Pvt. Ltd
- Specs: 26 m³/min each, 700 watts

ELECTRICAL:
- Panel Enclosure: Eldon
- Power Electronics: Schneider Electric
- Wires: Polycab India
- Switches: Teknic

SAFETY:
- Light Guards: Pepperl+Fuchs (Type 4 CE grade)
- Photocells (Sag/Pre-blow): Pepperl+Fuchs

MACHINE SPECIFICATIONS (PF1 1x1.5 example):
- Sheet size: 1050mm x 1550mm
- Max forming area: 1000mm x 1500mm
- Max stroke (draw depth): 500-625mm
- Heater capacity: 61-76 KW
- Top heater zones: 36-54
- Bottom heater zones: 36-54
- Total SSRs: 72-108
- Vacuum pump: 100 m³/hr
- Cooling: 6 x high-speed blowers + water mist option
- Total connected load: 76 KW
- Power supply: 380V ±5%, 3-phase, 50 Hz

WARRANTY: 12 months from dispatch, extendable""",
        knowledge_type="machine_spec",
        source_file=SOURCE_FILE,
        entity="PF1 Components",
        summary="PF1 brands: Elstein heaters, Mitsubishi PLC/servo, Festo pneumatics, Busch vacuum, Pepperl+Fuchs safety",
        metadata={
            "topic": "components",
            "heaters": "Elstein",
            "plc": "Mitsubishi",
            "pneumatics": "Festo",
            "vacuum": "Busch",
            "safety": "Pepperl+Fuchs"
        }
    ))
    
    # Safety systems and interlocks
    items.append(KnowledgeItem(
        text="""PF1 Safety Systems and Interlocks:

CE GRADE SAFETY COMPLIANCE:

1. LIGHT GUARDS (Type 4):
   - Brand: Pepperl+Fuchs
   - Location: Sheet entry area
   - Function: Stops machine if beam broken during operation
   - CE compliant safety relay integration

2. DOOR INTERLOCKS:
   - Mould chamber door safety switches (LSMDO1, LSMDO2)
   - Machine won't operate with door open
   - Prevents access during forming cycle

3. FRAME SAFETY:
   - Frame position indication (Down/Safe/Unsafe)
   - Frame latch cylinders with position feedback
   - "Frame Unsafe" = frame can drop due to air leaks
   - "Frame Safe" = frame latched in up position
   - Never enter machine when frame unsafe!

4. PLUG SAFETY:
   - Plug up safety latch cylinder
   - Plug Safe/Unsafe status on HMI
   - CE safety cylinder prevents uncontrolled descent

5. EMERGENCY STOP (SWEMS):
   - Immediately stops all operations
   - Heaters move back to park position
   - Air supply exhausted via dump valve
   - Auxiliary tank provides air for heater retract
   - Safety relay (SR1) cuts all dangerous motion

KEY ELECTRICAL INTERLOCKS (programmed in PLC):

HEATER FORWARD requires:
- Frame locked (down)
- Mould down
- Plug up

MOULD UP requires:
- Both heaters back
- Frame locked

PLUG DOWN requires:
- Both heaters back
- Frame locked

FRAME OPEN requires:
- Mould down
- Both heaters back

FRAME LOCK requires:
- Mould down

CRITICAL SAFETY RULES:
- Never enter mould chamber unless frame is latched safe
- Never enter when plug shows unsafe
- Never insert body parts when mould stopped at limit switch
- Always move mould fully down before entering chamber
- Wait for machine to cool before maintenance
- Depressurize pneumatics before cylinder maintenance""",
        knowledge_type="machine_spec",
        source_file=SOURCE_FILE,
        entity="PF1 Safety",
        summary="PF1 safety: CE Type 4 light guards, door interlocks, frame/plug latches, E-stop, PLC interlocks",
        metadata={"topic": "safety_systems", "compliance": "CE", "light_guard": "Type_4"}
    ))
    
    # Tool changing and setup procedure
    items.append(KnowledgeItem(
        text="""PF1 Tool Changing Procedure:

MOULD CHANGE PROCESS (Standard machines):

PREPARATION:
1. Read safety regulations first
2. Ensure mould is down, plug is up
3. Move plug stroke control plate fully up
4. Set mould stopping option to "NO"
5. Verify mould is fully down

STEP-BY-STEP PROCEDURE:
1. Switch OFF electric supply with frame down
2. Verify plug fully up, mould fully down
3. Remove plug from top table
4. Remove mould from bottom table
5. Open bottom frame clamping brackets
6. Restart electric supply
7. Press "Frame Open" switch
8. Place wooden spacer on mould platen
9. Move platen up - spacer lifts frame above surface
10. Remove bottom clamping frame with forklift (from FRONT only)
11. Place new frame (correct size for new mould)
12. Center frame precisely
13. Place spacers for 10-20mm gap between top/bottom frames
14. Press "Frame Lock" - frame moves down to spacers
15. Switch OFF electric, adjust top frame brackets
16. Place mould centered on platen
17. Fix plug to center of upper platen
18. Switch ON electric, press "Frame Open"
19. Remove wooden spacers
20. Press "Frame Lock"
21. Move mould up/down to check for interference
22. Measure required plug stroke, set accordingly
23. Center plug over mould
24. Shut off air and electric
25. Clamp mould, frame, and plug firmly
26. Restart air and electric supply

LIMIT SWITCH ADJUSTMENTS:
- Mould UP limit: Set for full up position + chamber open
- Pre-blow photocell: Align transmitter/receiver for bubble height
- Sag photocell: Align for proper sag detection
- Mould DOWN limit: Set per mould depth requirement

UNIVERSAL FRAME ADVANTAGE:
With servo-driven universal frames, steps 8-15 are replaced by:
- Enter sheet size on HMI
- Press adjust - frames move automatically
- Time: 1-2 minutes vs 60+ minutes for fixed frames""",
        knowledge_type="process",
        source_file=SOURCE_FILE,
        entity="PF1 Tool Change",
        summary="PF1 tool change: 26-step procedure for fixed frames (~60min), or 2min with universal servo frames",
        metadata={"topic": "tool_changing", "fixed_time": "60min", "universal_time": "2min"}
    ))
    
    # Troubleshooting guide
    items.append(KnowledgeItem(
        text="""PF1 Troubleshooting Guide - Common Problems and Solutions:

HEATER PROBLEMS:

1. Heater trolley doesn't slide smoothly:
   - Check rail lubrication (grease)
   - Check machine level
   - Adjust flow control on solenoid for smooth movement

2. Heater doesn't heat at all:
   - Check main power supply
   - Verify heater switches ON on control panel
   - Check heater percentage not set to zero
   - Check power save/auto power-off timers
   - Verify no emergency stop or alarm active

3. Some zones don't heat:
   - Check SSR for that zone (test/replace)
   - Check wiring connections
   - If single element: likely faulty heater element

4. Heaters stay ON continuously:
   - SSR short-circuited (common failure mode)
   - Replace faulty SSR

VACUUM PROBLEMS:

1. No vacuum buildup in tank:
   - Check vacuum solenoid is OFF
   - Check solenoid for leaks (clean diaphragm)
   - Check piping from pump to tank
   - Test pump suction directly

2. Vacuum OK but part doesn't form:
   - Vacuum solenoid not operating (check coil/supply)
   - Piping leaks or cylinder seal leaks
   - Rubber gaskets worn on mould box or frame
   - Vacuum holes in mould blocked (clean with wire)
   - Insufficient vacuum holes (drill more)
   - Sheet not heated properly
   - Mould not coming up fully (check clearance)

3. Vacuum pump doesn't run:
   - No power supply
   - Overload relay tripped
   - See pump manual for other issues

MACHINE OPERATION PROBLEMS:

1. Heater won't come forward:
   - Check: Mould down? Plug up? Frame locked?
   - Check limit switches on I/O status screen

2. Mould won't come up:
   - Check: Heaters back? Frame locked?
   - Verify limit switches pressed

3. Plug won't come down:
   - Check: Heaters back? Frame locked?
   - Verify limit switches

4. Frame won't lock:
   - Check: Mould down?
   - Check limit switches

5. Frame won't open:
   - Check: Mould down? Heaters back?

6. Pre-blow not working in auto:
   - Align pre-blow photocell (check LED or PLC input)

7. Bottom heater won't come forward:
   - Sag photocell misaligned (align and verify)

8. Jerky pneumatic movement:
   - Check air pressure regulator (should be 5 bar)
   - Clean air filter
   - Fill lubricator with proper oil

PRE-BLOW PROBLEMS:
- Poor bubble: Check all chamber seals
- Gaskets on: bottom frame, front cover, heater box seals
- Chamber open cylinder function
- All seal points must be air-tight""",
        knowledge_type="process",
        source_file=SOURCE_FILE,
        entity="PF1 Troubleshooting",
        summary="PF1 troubleshooting: heater (SSR, zones), vacuum (pump, seals, holes), operations (interlocks, sensors)",
        metadata={"topic": "troubleshooting"}
    ))
    
    # Maintenance schedule
    items.append(KnowledgeItem(
        text="""PF1 Maintenance Schedule and Procedures:

CRITICAL: Always depressurize machine, switch off power, and wait for cooling 
before maintenance. Ensure all cylinders at full stroke before disconnecting.

DAILY (Every 8 hours):
- Clean FRL (Filter/Regulator/Lubricator) filter
- Drain FRL cup
- Check lubricator oil level
- Verify air pressure at 5 bar

WEEKLY:
- Clean heater tracks with cloth
- Check heater trolley wheels - grease if needed (high-temp grease for 300°C)
- Tighten heater piston nuts
- Visual inspection of all rubber gaskets

EVERY 8 WEEKS:
- Grease frame rack and pinion guides
- Grease frame bearings
- Grease plug mechanism

MONTHLY:
- Clean mould table racks
- Wipe rack surfaces with machine oil
- Apply grease to chains (full coverage)

EVERY 3 MONTHS:
- General grease all moving parts
- Check all cylinders/valves for leakages
- Inspect all mechanical parts for fit and wear
- Check chain tension
- Inspect chain links for wear/breakage

AS NEEDED:
- Replace rubber gaskets (inspect regularly)
- Replace worn heater elements
- Replace faulty SSRs
- See vacuum pump manual for pump maintenance

FRL SETTINGS:
- Regulator pressure: 5 bar (5 kg/cm²)
- Use proper pneumatic lubricant oil
- Clean filter when restricted

HIGH-TEMPERATURE GREASE:
- Required for heater trolley wheels
- Must be rated for 300°C
- Standard grease will fail at heater temperatures

CHAINS AND RACKS:
- Keep clean and lubricated
- Check for stretch and adjust tension
- Replace if links worn or damaged""",
        knowledge_type="process",
        source_file=SOURCE_FILE,
        entity="PF1 Maintenance",
        summary="PF1 maintenance: daily FRL check, weekly heater clean, monthly rack grease, 3-month full inspection",
        metadata={"topic": "maintenance_schedule"}
    ))
    
    # Abbreviations and wiring reference
    items.append(KnowledgeItem(
        text="""PF1 Technical Abbreviations and Wiring Reference:

LIMIT SWITCHES (LS):
- LSTHF: Top Heater Forward
- LSTHB: Top Heater Backward
- LSBHF: Bottom Heater Forward
- LSBHB1/2: Bottom Heater Backward 1/2
- LSMU: Mould Up
- LSMD: Mould Down
- LSPU: Plug Up
- LSPD: Plug Down
- LSFL: Frame Lock
- LSFO1/2: Frame Open 1/2
- LSPM: Plug Mid-position
- LSPSU/D: Plug Stroke plate Up/Down
- LSFLL/O: Frame Lock safety Lock/Open
- LSPUL/O: Plug Up Lock/Open
- LSMDO1/2: Mould Door safety

SENSORS:
- IRPB: Pre-blow infrared photocell
- IRSAG: Sheet sag infrared photocell

SOLENOIDS (S):
- SMA: Dump valve (electrical)
- SHT: Top Heater Forward
- SHB: Bottom Heater Forward
- SV: Vacuum
- SA: Release Air
- SPB: Pre-blow Air
- SWMT: Water Mist
- SFL: Frame Lock
- SFO: Frame Open
- SCO: Chamber Open
- SMU/SMD: Mould Up/Down
- SPU/SPD: Plug Up/Down
- SFOL/O: Frame safety Lock/Open
- SPUL/O: Plug safety Lock/Open

CONTACTORS & RELAYS:
- C1: Fan Contactor
- C2: Vacuum Pump Contactor
- C3: Main Contactor
- C4/C5: Plug stroke motor Up/Down
- R1-R23: Electromechanical relays for various functions
- SR1/SR2: Safety Relays (E-stop/Light Guard)
- SSR1-84: Solid State Relays for heater zones

HEATER ZONES:
- T1-T42: Top heater zones (varies by model)
- B1-B42: Bottom heater zones
- P1-P4: Thermocouple probe positions

SWITCHES:
- SWCON: Control ON
- SWFL: Frame Lock
- SWPB: Pre-blow
- SWRES: Reset
- SWEMS: Emergency Stop""",
        knowledge_type="machine_spec",
        source_file=SOURCE_FILE,
        entity="PF1 Wiring",
        summary="PF1 wiring abbreviations: LS (limit switches), S (solenoids), SSR (heater relays), C/R (contactors/relays)",
        metadata={"topic": "wiring_reference", "total_ssr": "72-84"}
    ))
    
    return items


def main():
    print("=" * 70)
    print("Ingesting PF1 Technical Manual - Batelaan - Comprehensive Knowledge")
    print("=" * 70)
    print(f"\nSource: {SOURCE_FILE}")
    print("This is a 53-page technical manual covering all PF1 machine systems.\n")
    
    items = create_knowledge_items()
    print(f"Extracted {len(items)} comprehensive knowledge items:\n")
    
    for i, item in enumerate(items, 1):
        print(f"  {i:2}. [{item.knowledge_type:12}] {item.entity}: {item.summary[:50]}...")
    
    print("\n" + "-" * 70)
    print("Starting ingestion to all storage systems...")
    
    ingestor = KnowledgeIngestor(verbose=True)
    result = ingestor.ingest_batch(items)
    
    print("\n" + "=" * 70)
    print(f"RESULT: {result}")
    print("=" * 70)
    
    if result.success:
        print("\n✓ PF1 Technical Knowledge ingested successfully!")
        print(f"  - Items ingested: {result.items_ingested}")
        print(f"  - Qdrant main: {result.qdrant_main}")
        print(f"  - Qdrant discovered: {result.qdrant_discovered}")
        print(f"  - Mem0: {result.mem0}")
        print(f"  - JSON backup: {result.json_backup}")
        if result.items_chunked:
            print(f"  - Large items chunked: {result.items_chunked}")
    else:
        print("\n✗ Ingestion failed")
        if result.errors:
            print(f"  Errors: {result.errors}")
    
    return 0 if result.success else 1


if __name__ == "__main__":
    sys.exit(main())
