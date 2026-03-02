#!/usr/bin/env python3
"""
Ingest Operating Manual – Machinecraft PF1-4022 Thermoforming Machine.

Source: data/imports/Operating Manual – Machinecraft PF1-4022 Thermoforming Machine.pdf
This is a 21-page operating manual for the advanced PF1-4022 - fully servo-driven
variant with automatic sheet loader and universal clamping frame.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "openclaw" / "agents" / "ira" / "skills" / "brain"))

from knowledge_ingestor import KnowledgeIngestor, KnowledgeItem

SOURCE_FILE = "Operating Manual – Machinecraft PF1-4022 Thermoforming Machine.pdf"


def create_knowledge_items() -> list[KnowledgeItem]:
    """Extract structured knowledge from PF1-4022 operating manual."""
    items = []
    
    # PF1-4022 Overview and key differentiators
    items.append(KnowledgeItem(
        text="""PF1-4022 Advanced Thermoforming Machine Overview:

The Machinecraft PF1-4022 is an ADVANCED single-station vacuum thermoforming machine
that builds upon the proven PF1-1522 platform with significant upgrades.

KEY DIFFERENTIATORS from basic PF1:
1. FULLY SERVO-DRIVEN: ALL primary movements are powered by servo motors (not pneumatic)
   - Forming table (platen) vertical motion
   - Clamp frame opening/closing
   - Sheet loader mechanisms
   - Upper platen/plug assist if equipped

2. AUTOMATIC SHEET LOADER: Eliminates manual sheet handling
   - Servo-driven arm with vacuum suction cups
   - Picks sheet from stack and positions precisely
   - Multi-sheet detection sensors (laser sensors)
   - Sheet separation device (vibrating frames or air blower)

3. UNIVERSAL CLAMPING FRAME: Automatically adjustable via HMI
   - Servo-driven frame sides move in/out to match any sheet size
   - No manual frame changes required
   - Quick changeovers between different products

4. CHAIN-DRIVEN MECHANISM: Unique to Machinecraft
   - Robust and reliable
   - Easy to maintain/reset if overload or misalignment occurs
   - User-friendly for maintenance personnel

ADVANTAGES OF SERVO OVER PNEUMATIC:
- Precise positioning and repeatability every cycle
- Programmable acceleration/deceleration profiles
- "Soft touch" motion - platen can slow down as it contacts sheet
- Can stop at any point in travel (useful for shallow parts)
- Lower noise operation
- Exact speed control for consistent part quality
- No air compressor required for main movements""",
        knowledge_type="machine_spec",
        source_file=SOURCE_FILE,
        entity="PF1-4022",
        summary="PF1-4022: fully servo-driven, auto sheet loader, universal frame - advanced PF1 variant",
        metadata={"model": "PF1-4022", "drive_type": "servo", "generation": "advanced"}
    ))
    
    # Closed chamber and pre-blow system
    items.append(KnowledgeItem(
        text="""PF1-4022 Closed Chamber and Pre-Blow System:

CLOSED CHAMBER DESIGN:
- Once sheet is clamped, space above AND below is sealed (airtight)
- Allows pressurization for pre-blow bubble formation
- Essential for uniform wall thickness in formed parts

PRE-BLOW (ZERO-SAG CONTROL) OPERATION:
1. Sheet clamped in universal frame
2. Heating begins (top and bottom IR heaters)
3. As sheet heats, it would normally sag under gravity
4. Small air pressure introduced below sheet
5. Sheet inflates UPWARD forming gentle bubble
6. Integrated sensor monitors bubble/sag height
7. Air pressure automatically regulated to maintain bubble
8. Prevents thinning in center of large sheets

WHY PRE-BLOW IS CRITICAL:
- Large sheets sag significantly when heated
- Sagging causes uneven heating (center closer to bottom heater)
- Without pre-blow, center of part becomes very thin
- Pre-blow keeps sheet evenly supported until vacuum forming
- Result: uniform wall thickness across entire part

TYPICAL SETTINGS:
- Pre-blow pressure: 0.05-0.1 bar (very gentle)
- Timing: Activates during heating phase
- Stops just before forming (vacuum overcomes it)

The PF1-4022's closed chamber with sensor-controlled pre-blow is particularly
valuable for large format parts where gravity sag is significant.""",
        knowledge_type="process",
        source_file=SOURCE_FILE,
        entity="PF1-4022 Pre-blow",
        summary="PF1-4022 pre-blow: closed chamber, sensor-controlled air bubble prevents sag for uniform wall thickness",
        metadata={"model": "PF1-4022", "feature": "preblow", "pressure": "0.05-0.1_bar"}
    ))
    
    # Automatic sheet loader details
    items.append(KnowledgeItem(
        text="""PF1-4022 Automatic Sheet Loader - Technical Details:

MECHANISM:
- Servo-driven arm with vacuum suction cups
- Moves both vertically (up/down) and horizontally (in/out)
- Picks sheet from stack, transports to forming station
- Positions sheet precisely over mold between clamping frame
- Releases sheet (vacuum off) and retracts

SHEET HANDLING FEATURES:
- Laser sensors detect if multiple sheets picked together
- Sheet separation device options:
  * Vibrating "dancing" frames
  * Air blower to separate top sheets
- Ensures only ONE sheet loaded at a time

STACK LOADING:
- Adjustable sheet guides for different sizes
- Side stops/pegs keep stack aligned under suction cups
- HMI input for sheet thickness (helps loader detect properly)
- Capacity: Recommended stack height limit applies

SAFETY FEATURES:
- Stay clear during operation - automatic movement
- Can cause injury/pinching if person too close
- Never reach into loader area while cycling
- If missfeed occurs: Press E-stop first, then approach

BENEFITS:
- Eliminates manual sheet handling
- Improves cycle time consistency
- Reduces operator fatigue
- Operator can load stack and let machine handle each sheet
- Safer - operator not reaching into hot forming area

ERROR HANDLING:
- "Sheet Load Error" alarm if pickup fails
- Causes: Empty stack, stuck sheets, vacuum cup issue
- Solution: Refill/realign stack, separate sheets, check cups""",
        knowledge_type="machine_spec",
        source_file=SOURCE_FILE,
        entity="PF1-4022 Loader",
        summary="PF1-4022 auto loader: servo arm + vacuum cups, laser multi-sheet detection, sheet separation device",
        metadata={"model": "PF1-4022", "feature": "auto_loader", "sensors": "laser"}
    ))
    
    # Universal clamping frame
    items.append(KnowledgeItem(
        text="""PF1-4022 Universal Clamping Frame System:

CONCEPT:
- Single frame accommodates ANY sheet size within machine range
- No manual frame changes required between products
- Servo-driven frame sides move in/out automatically

OPERATION:
1. Operator enters sheet dimensions on HMI (length x width)
2. OR uses manual jog to position frame sides
3. Servo motors move frame clamps to specified opening
4. Frame automatically positions for that sheet size
5. Same frame used for all products - just change settings

FRAME MECHANISM:
- Heavy-duty clamps with guided motion
- Applies uniform clamping force around sheet perimeter
- Creates air-tight seal for pre-blow/vacuum operation
- Servo control provides consistent clamping force every cycle

SETUP PROCEDURE:
- Navigate to frame/aperture adjustment screen on HMI
- Method A: Input sheet dimensions → machine auto-adjusts
- Method B: Manual jog each side while observing position
- Leave small clearance (sheet firmly gripped, not cut)
- Test close with no sheet to verify no mold interference

TIME SAVINGS:
- Traditional fixed frames: 60+ minutes to change
- Universal servo frame: 1-2 minutes to adjust via HMI
- Critical for high-mix production environments

SAFETY:
- Frame closes with significant servo-driven force
- Will not stop for obstructions unless E-stop triggered
- Use jog/setup mode with caution
- Always verify area clear before cycling""",
        knowledge_type="machine_spec",
        source_file=SOURCE_FILE,
        entity="PF1-4022 Frame",
        summary="PF1-4022 universal frame: servo-adjustable for any sheet size via HMI, no manual frame changes",
        metadata={"model": "PF1-4022", "feature": "universal_frame", "adjustment_time": "1-2min"}
    ))
    
    # Servo-driven motion system
    items.append(KnowledgeItem(
        text="""PF1-4022 Fully Servo-Driven Motion System:

ALL PRIMARY MOVEMENTS ARE SERVO-CONTROLLED:
1. Forming Table (Platen): Vertical motion up/down
2. Clamp Frame: Open/close motions
3. Sheet Loader: Pick and place movements
4. Upper Platen/Plug Assist: If equipped

SERVO CONTROL ADVANTAGES:

PRECISION:
- Exact positioning every cycle
- Programmable positions (not just end stops)
- Can stop at any point in travel
- Useful for shallow parts (shorter stroke)

SOFT TOUCH CAPABILITY:
- Programmable acceleration/deceleration profiles
- Platen can slow down as it contacts hot sheet
- Prevents impact damage to sheet or mold
- Gentle forming improves part quality

QUIET OPERATION:
- Much lower noise than pneumatic systems
- No loud air exhaust sounds
- Better working environment

FLEXIBILITY:
- Cycle timing easily adjusted via HMI
- Different speeds for different phases
- Recipe storage for instant changeover

CHAIN-DRIVEN MECHANISM:
- Machinecraft uses chain drive for servo axes
- Robust and reliable under load
- Easy to maintain and adjust
- If overload/jam occurs: Chain can be reset/realigned
- More forgiving than ball screw in harsh conditions

HOMING PROCEDURE:
- Machine requires homing each servo axis at startup
- "Home All Axes" button on HMI
- Each axis moves to home sensor to establish reference
- Must complete before production can start
- If axis fails to home: Alarm displayed""",
        knowledge_type="machine_spec",
        source_file=SOURCE_FILE,
        entity="PF1-4022 Servo",
        summary="PF1-4022 servo system: all-electric, programmable soft-touch motion, chain-driven for robustness",
        metadata={"model": "PF1-4022", "feature": "servo_drive", "mechanism": "chain"}
    ))
    
    # Heating system with zone control
    items.append(KnowledgeItem(
        text="""PF1-4022 Heating System - Twin IR Ovens:

CONFIGURATION:
- DUAL infrared heater ovens (top and bottom)
- Ensures even heating of plastic sheet
- Top oven: Primary heating
- Bottom oven: For thick materials (can be turned off for thin sheets)

ZONE CONTROL:
- Heating segmented into multiple zones
- Each zone's temperature/output individually controllable via HMI
- Allows tailored heat distribution based on:
  * Mold shape (more heat where needed)
  * Material thickness variations
  * Edge vs center heating requirements

HEATER ELEMENT OPTIONS:
- Ceramic IR elements (rugged, consistent)
- Quartz IR elements (faster response, energy saving)
- Halogen flash elements (fastest heating)
- Arranged in grid pattern for homogeneous coverage

TEMPERATURE CONTROL:
- PID controllers regulate heating
- Built-in IR thermocouple sensor (IR probe)
- Monitors sheet temperature in REAL TIME
- Closed-loop control: Adjusts heater output based on feedback
- Can trigger next phase when sheet reaches target temperature

HEATING MODES:
1. Timer-based: Heat for X seconds
2. Temperature-based: Heat until sheet reaches X°C
3. Combined: Maximum time with sensor cut-off

HEATER MOVEMENT:
- Heaters may swing or slide over clamped sheet
- Or may be fixed with on/off control
- Retract away before forming to make room for platen""",
        knowledge_type="machine_spec",
        source_file=SOURCE_FILE,
        entity="PF1-4022 Heating",
        summary="PF1-4022 heating: dual IR ovens (top+bottom), zone control, IR probe for real-time sheet temperature",
        metadata={"model": "PF1-4022", "feature": "heating", "control": "PID_with_IR_probe"}
    ))
    
    # Vacuum system with servo proportional valve
    items.append(KnowledgeItem(
        text="""PF1-4022 Vacuum System - Advanced Features:

COMPONENTS:
- High-capacity vacuum pump
- Vacuum reservoir tank (mounted in frame)
- SERVO-OPERATED PROPORTIONAL VALVE (key feature)
- Quick-connect fittings for mold
- Safety valves and pressure sensors

MULTI-STEP VACUUM (Unique Capability):
The servo proportional valve enables staged vacuum application:

Step 1: Gentle initial vacuum
- Lower pressure to start material draw-down gently
- Prevents shock/marking on sheet surface

Step 2: Full vacuum
- Complete vacuum applied after delay
- Pulls sheet tightly into all mold details

TIMING CONTROL:
- Vacuum delay settable (e.g., for plug assist timing)
- Multi-step trigger times programmable
- Vacuum level and duration in recipe

BENEFITS OF SERVO VACUUM VALVE:
- Digital control of vacuum profile
- Programmable stages for optimal forming
- Consistent vacuum application every cycle
- Can adjust based on material/part requirements

OPERATION SEQUENCE:
1. Mold contacts heated sheet
2. Vacuum valve opens (per programmed delay)
3. Air evacuated through mold holes
4. Atmospheric pressure forces sheet onto mold
5. Multi-step profile executes if programmed
6. Vacuum held during cooling
7. Vacuum vented for part release

PRESSURE FORMING OPTION:
- Compressed air connections available
- Filter-regulator-lubricator (FRL) unit
- For pressure forming: Air from above + vacuum from below
- Typical pressure: ~3 bar
- Achieves higher detail than vacuum alone""",
        knowledge_type="machine_spec",
        source_file=SOURCE_FILE,
        entity="PF1-4022 Vacuum",
        summary="PF1-4022 vacuum: servo proportional valve enables multi-step vacuum profiles for optimal forming",
        metadata={"model": "PF1-4022", "feature": "vacuum", "valve": "servo_proportional"}
    ))
    
    # Complete forming cycle sequence
    items.append(KnowledgeItem(
        text="""PF1-4022 Complete Forming Cycle Sequence:

AUTOMATIC CYCLE (after pressing Start):

1. SHEET LOADING:
   - Auto loader picks top sheet from stack (vacuum cups)
   - Arm transfers sheet into forming area
   - Positions sheet over mold, between clamp frame
   - Releases sheet and retracts

2. CLAMPING:
   - Universal frame closes (servo-driven)
   - Clamps sheet by edges
   - Creates air-tight chamber above and below
   - Sensors confirm frame locked

3. HEATING:
   - Heater ovens swing/slide into position
   - IR heaters activate at programmed settings
   - HMI shows heating timer countdown
   - Sheet gradually becomes pliable
   - PRE-BLOW: Air inflates sheet into gentle upward bulge
   - Sensor monitors bulge, maintains zero-sag
   - Continues until time/temperature target reached

4. END OF HEATING:
   - Heaters turn off and retract
   - Sheet now very flexible
   - Pre-blow stops (or vented)

5. FORMING:
   - Forming platen rises smoothly (servo-controlled)
   - Mold pushes into hot sheet
   - Soft-touch approach prevents impact
   - Vacuum valve opens (per timing)
   - Air evacuated through mold holes
   - Atmospheric pressure conforms sheet to mold
   - Multi-step vacuum if programmed
   - If pressure forming: Compressed air from above

6. COOLING (DWELL):
   - Platen stays up, vacuum continues
   - Cooling fans/mist system activate if equipped
   - Sheet solidifies on mold
   - HMI shows cooling countdown
   - DO NOT RUSH - prevents warping

7. VENT/RELEASE:
   - Vacuum turned off and vented
   - Optional: Air burst to help part release
   - Ejector pins/push-out if equipped

8. PLATEN DOWN:
   - Lower platen descends (controlled)
   - Mold and formed part move down

9. UNCLAMPING:
   - Clamp frame opens
   - Part is free
   - Indicator signals cycle complete

10. PART REMOVAL:
    - Manual: Operator removes part (heat gloves)
    - Auto: Robot/conveyor if equipped
    - In auto mode: Machine may wait for confirmation

11. NEXT CYCLE:
    - Loader picks next sheet
    - Cycle repeats""",
        knowledge_type="process",
        source_file=SOURCE_FILE,
        entity="PF1-4022 Cycle",
        summary="PF1-4022 cycle: 11-phase automatic sequence from sheet load to part removal, fully programmable",
        metadata={"model": "PF1-4022", "phases": 11, "mode": "automatic"}
    ))
    
    # Setup and operation procedure
    items.append(KnowledgeItem(
        text="""PF1-4022 Setup and Operation Procedure:

PREPARATION BEFORE OPERATION:

1. VERIFY INSTALLATION:
   - Electrical connected (main power OFF initially)
   - Vacuum pump connected and ready
   - Compressed air if needed (for pressure forming)
   - Machine clean, no obstructions
   - E-stops disengaged, no alarms

2. MOUNT FORMING MOLD:
   - Open clamp frame via jog controls
   - Place mold on platen, centered
   - Use QUICK-CLAMPING mechanism (no lengthy bolting)
   - Attach vacuum hose (quick-connect fitting)
   - Install plug assist if needed
   - Close frame, verify no interference

3. LOAD SHEET STACK:
   - Adjust loader guides to sheet size
   - Place stack on loader platform (flat, not sticking)
   - Within loader capacity
   - Enter sheet thickness on HMI if required

4. POWER ON:
   - Switch main power ON
   - HMI boots, initialization runs
   - Perform SERVO HOMING ("Home All Axes")
   - Watch all axes complete without obstruction
   - Machine shows ready/idle status

5. SET FRAME APERTURE:
   - Navigate to frame adjustment on HMI
   - Enter sheet dimensions (e.g., 2000mm x 1500mm)
   - OR manual jog each side
   - Frame servo-adjusts to correct opening
   - Leave small clearance for grip without cutting

6. HEATER WARM-UP:
   - Turn on heaters via HMI
   - Set zone temperatures/percentages
   - OR load pre-programmed recipe
   - Wait for heaters to reach target temperature

7. PROGRAM CYCLE PARAMETERS:
   - Heating time or temperature trigger
   - Pre-blow pressure and timing (0.05-0.1 bar typical)
   - Vacuum timing, multi-step if used
   - Pressure timing if pressure forming
   - Cooling time (5-15+ seconds based on thickness)
   - Cycle mode: Single or Auto (continuous)

8. VERIFY & START:
   - Review all settings on HMI summary
   - Area clear, guards closed
   - Press CYCLE START""",
        knowledge_type="process",
        source_file=SOURCE_FILE,
        entity="PF1-4022 Setup",
        summary="PF1-4022 setup: 8-step procedure - install mold, load stack, home axes, set frame, heat up, program, start",
        metadata={"model": "PF1-4022", "topic": "setup_procedure", "steps": 8}
    ))
    
    # Maintenance schedule
    items.append(KnowledgeItem(
        text="""PF1-4022 Maintenance Schedule:

DAILY MAINTENANCE (every shift):
- Lubricate all moving parts per chart
- Check mold platen lift mechanism for slack/play
- Inspect electrical cables/connectors for looseness
- Examine heater elements for cracks/failures
- Clean surfaces - remove plastic debris, dust

WEEKLY MAINTENANCE (every 40 hours):
- Check servo chain/belt drives for tension
- Apply chain lubricant if recommended
- Listen for unusual servo motor/gearbox noise
- Inspect pneumatic system (if equipped):
  * Drain water from filter bowl
  * Check air hoses for leaks
  * Tighten loose fittings
- Check vacuum pump oil level, top up as needed
- Drain vacuum tank moisture trap
- Clean/replace vacuum filter
- Test safety interlocks (doors, E-stops)
- Tighten loose bolts/nuts (frame, heater, loader)

MONTHLY MAINTENANCE (every 160 hours):
- Deep clean inside machine base
- Clean electrical cabinet with dry air
- Verify sensor calibration:
  * IR sheet temperature sensor accuracy
  * Limit sensor/encoder positions
- Review HMI alarm history for patterns
- Safety audit (warning labels, light curtains)
- Lubricate gearboxes, linear guides (per schedule)
- Inspect wear parts:
  * Vacuum seals on clamp frame
  * Heater reflectors (clean soot)
  * Suction cups on loader

POST-MAINTENANCE:
- Test run without material
- Verify homing and all movements
- Keep maintenance logs

CHAIN-DRIVEN SYSTEM ADVANTAGE:
- If chain skips or drive out of sync from jam
- Can be re-adjusted relatively quickly
- Easier than ball screw repair
- Contact Machinecraft for in-depth procedures""",
        knowledge_type="process",
        source_file=SOURCE_FILE,
        entity="PF1-4022 Maintenance",
        summary="PF1-4022 maintenance: daily lubrication, weekly servo/vacuum checks, monthly deep inspection",
        metadata={"model": "PF1-4022", "topic": "maintenance"}
    ))
    
    # Troubleshooting guide
    items.append(KnowledgeItem(
        text="""PF1-4022 Troubleshooting Guide:

PROBLEM: Machine won't start cycle
CAUSES & SOLUTIONS:
- Safety interlock open → Close all doors/guards
- E-stop pressed → Release and reset
- Axes not homed → Run "Home All Axes"
- Heater not at temperature → Wait for warm-up
- No sheet detected → Load sheet, reset sensor
- Check HMI for specific error message

PROBLEM: Sheet loader fails to pick/drops sheet
CAUSES & SOLUTIONS:
- Stack empty or misaligned → Refill, realign
- Multiple sheets picked → Separate sheets, reduce static
- Suction cups not holding → Check loader vacuum pump, clean cups
- Laser sensors obscured → Clean sensors
- Sheet separation blower not working → Check air supply
- Reset alarm on HMI, restart

PROBLEM: Sheet forms poorly (webbing, thin spots, incomplete)
CAUSES & SOLUTIONS:
Webbing (wrinkles):
- Sheet too hot → Reduce heating time/temperature
- Use less vacuum initially
- Consider pre-blow adjustment

Incomplete forming:
- Sheet too cold → Increase heating
- Vacuum holes blocked → Clean mold holes
- Vacuum leak → Check connections, gaskets

Thin spots in center:
- Pre-blow not working → Activate/adjust pre-blow
- Sheet sagging → Increase pre-blow pressure
- May be overheated → Reduce heat time slightly

PROBLEM: Slow/insufficient vacuum draw
CAUSES & SOLUTIONS:
- Pump not running → Check power, check HMI
- Valve not opening → Check timing program
- Vacuum hose loose/leaking → Tighten connections
- Pump worn/filter clogged → Service pump
- Mold holes blocked → Clean with wire
- Servo valve setting wrong → Set to full vacuum

PROBLEM: Servo drive error/alarm (overload, following error)
CAUSES & SOLUTIONS:
- Obstruction in path → Remove and reset alarm
- Sequence timing wrong → Verify heating complete before forming
- Axis not homed → Re-home all axes
- Interference between axes → Adjust timing/positions
- Chain jumped sprocket → Realign chain (easy reset)
- Persistent fault → Power cycle, if continues call service

PROBLEM: Part stuck on mold
CAUSES & SOLUTIONS:
- Insufficient cooling → Increase cooling time
- Enable air eject feature if available
- Add vent holes to mold (maintenance)
- Apply mold release spray (temporary)
- Adjust platen timing for gravity assist""",
        knowledge_type="process",
        source_file=SOURCE_FILE,
        entity="PF1-4022 Troubleshooting",
        summary="PF1-4022 troubleshooting: loader issues, forming defects, vacuum problems, servo alarms, stuck parts",
        metadata={"model": "PF1-4022", "topic": "troubleshooting"}
    ))
    
    # Safety systems
    items.append(KnowledgeItem(
        text="""PF1-4022 Safety Systems and Precautions:

BUILT-IN SAFETY FEATURES:
- Dual electrical/pneumatic interlocks on movements
- Light curtains (Type 4 safety)
- Safety locks on frame and platens
- Multiple Emergency Stop buttons
- CE/UL compliant electrical cabinet

INTERLOCK SYSTEM:
- Machine won't start if any safety circuit open
- Guards must be closed
- Doors interlocked
- Light curtains clear
- HMI displays which interlock is open

EMERGENCY STOP:
- Hit any E-stop button in emergency
- Electrically disables all servo drives
- Brings all motion to immediate halt
- Must identify and resolve cause before resuming

CRITICAL SAFETY RULES:

AUTOMATIC LOADER:
- Stay clear during operation
- Moves automatically (up/down, in/out)
- Can cause injury/pinching
- Never reach in while cycling
- If intervention needed: E-stop FIRST

CLAMPING FRAME:
- Closes with significant force
- Will not stop for obstructions (unless E-stop)
- Keep hands/tools away during cycling
- Use jog/setup mode with caution
- Verify area clear before starting

SERVO MOTION:
- Quiet and FAST - remain vigilant
- Keep safe distance during auto/jog modes
- Never place body parts in path of motion
- All movements can stop instantly via E-stop

HEATING:
- Elements become extremely hot
- Don't touch heater area
- Use heat-resistant gloves for parts
- Stand back when opening oven access (hot air rush)
- Wait for cool-down before heater maintenance

ELECTRICAL:
- Keep machine and panel dry
- Do not operate in wet conditions
- Water defeats insulation - shock hazard

LOCKOUT/TAGOUT:
- Always de-energize before maintenance
- Lock out power
- Release stored pneumatic energy
- Follow facility LOTO procedures""",
        knowledge_type="machine_spec",
        source_file=SOURCE_FILE,
        entity="PF1-4022 Safety",
        summary="PF1-4022 safety: dual interlocks, light curtains, E-stops, CE/UL compliant - critical precautions listed",
        metadata={"model": "PF1-4022", "topic": "safety", "compliance": "CE_UL"}
    ))
    
    # Tooling and platen specifications
    items.append(KnowledgeItem(
        text="""PF1-4022 Tooling and Platen System:

LOWER PLATEN (Forming Table):
- Where mold (tool) is mounted
- Moves up and down (servo-driven)
- Heavy-duty structure with linear bearings/rails
- Stable motion for precise forming

QUICK TOOL LOADING:
- Quick-clamping mechanism for mold
- Uses clamps or locking cylinders
- Fasten tool in center without lengthy manual bolting
- Single operator can swap molds in short time
- Significantly faster than traditional bolt-down

MOLD SPECIFICATIONS:
- Max mold height: 1000+ mm (configuration dependent)
- Allows deep-draw parts
- Vacuum connections integrated through platen
- Quick-connect fittings for convenience
- Pressure/blow lines if applicable

UPPER PLATEN:
- For plug assist or mating mold (if equipped)
- Also servo-driven
- Can be fitted with plug or pressure plate
- Height adjustable via HMI

MOLD INSTALLATION PROCEDURE:
1. Open clamp frame (manually or jog)
2. Place mold on platen, centered
3. Engage quick-clamping mechanism
4. Attach vacuum hose (quick-connect)
5. Install plug assist if needed
6. Close frame, verify no interference
7. For large/heavy tools: Use hoist
8. Ensure platen at convenient height

MOLD REMOVAL:
- Disconnect vacuum lines
- Release quick clamps
- Use lifting equipment if needed
- Mold may still be hot - use caution""",
        knowledge_type="machine_spec",
        source_file=SOURCE_FILE,
        entity="PF1-4022 Tooling",
        summary="PF1-4022 tooling: quick-clamping system, 1000mm+ mold height for deep draw, servo upper platen",
        metadata={"model": "PF1-4022", "topic": "tooling", "max_mold_height": "1000mm+"}
    ))
    
    # HMI and control system
    items.append(KnowledgeItem(
        text="""PF1-4022 Control System (HMI & PLC):

HMI (Human-Machine Interface):
- Intuitive touch panel on control station
- Menu-driven, operator-friendly design
- All parameters settable through screens

CONTROLLABLE PARAMETERS:
- Heater zone temperatures/percentages
- Heating time or temperature trigger
- Pre-blow pressure and timing
- Vacuum timing and levels (multi-step)
- Cooling time
- Clamp frame position (aperture size)
- Loader operation modes
- Cycle mode (single/auto)

RECIPE STORAGE:
- Save parameter sets for different materials/molds
- Quick setup for repeat jobs
- Load recipe → all settings applied instantly
- Essential for high-mix production

PHYSICAL CONTROLS:
- Emergency Stop buttons
- Manual override switches (configuration dependent)
- Jog buttons for setup
- Status indicator lights

HMI STATUS DISPLAYS:
- Current phase ("Heating", "Forming", "Cooling")
- Cycle progress/timers
- Temperature readings
- Alarms and error messages
- Axis positions

SAFETY INTEGRATION:
- Control system checks all interlocks before starting
- All guards must be closed
- Correct temperature reached
- Axes homed
- Will not run if conditions unsafe

PLC (Programmable Logic Controller):
- Manages all logic and sequencing
- Executes programmed cycle automatically
- Monitors sensors and safety circuits
- Generates alarms on fault conditions

ELECTRICAL CABINET:
- Built to CE/UL standards
- Proper grounding and overload protection
- Houses servo drives and heater controllers
- Should remain closed during operation""",
        knowledge_type="machine_spec",
        source_file=SOURCE_FILE,
        entity="PF1-4022 Controls",
        summary="PF1-4022 HMI: recipe storage, multi-step vacuum control, zone heating, CE/UL compliant PLC",
        metadata={"model": "PF1-4022", "topic": "controls", "compliance": "CE_UL"}
    ))
    
    return items


def main():
    print("=" * 70)
    print("Ingesting PF1-4022 Operating Manual - Advanced Servo-Driven Machine")
    print("=" * 70)
    print(f"\nSource: {SOURCE_FILE}")
    print("This is a 21-page operating manual for the advanced PF1-4022.\n")
    
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
        print("\n✓ PF1-4022 Knowledge ingested successfully!")
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
