#!/usr/bin/env python3
"""
Ingest BOM Costing Analysis for PF1 machines.
Contains detailed bill of materials breakdown, component costs, and pricing analysis
for different PF1 machine sizes.
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

SOURCE_FILE = "BOM_Costing_Analysis.xlsx"


def create_knowledge_items() -> list:
    """Create knowledge items from BOM costing analysis."""
    knowledge_items = []
    
    # 1. BOM Costing Overview
    knowledge_items.append(KnowledgeItem(
        text="""PF1 Machine BOM (Bill of Materials) Costing Analysis Overview:
        
This comprehensive BOM analysis covers cost breakdowns for multiple PF1 machine sizes:

MACHINE CONFIGURATIONS ANALYZED:
- 600x800mm Model E: €50,000 (entry-level)
- 800x1000mm Model E: €80,000
- 1000x1500mm Model P: €140,000 (pneumatic)
- 1000x1500mm Model E: €190,000 (electric/servo)
- 1300x1300mm Model P: €120,000
- 1200x2000mm KTec (Austria): For clear plastics/non-automotive
- 2000x3000mm NTF: Large format ~₹1 Cr

Model E = Electric/Servo drive version (premium)
Model P = Pneumatic drive version (standard)

The analysis includes BOMs for European customers (Batelaan Netherlands, KTec Austria, NTF) 
with pricing in both INR and EUR, demonstrating international pricing strategy.""",
        knowledge_type="commercial",
        source_file=SOURCE_FILE,
        summary="PF1 BOM costing analysis overview - machine sizes and pricing tiers",
        entity="Machinecraft",
        metadata={
            "document_type": "bom_analysis",
            "machines_covered": ["PF1-0608", "PF1-0810", "PF1-1015", "PF1-1313", "PF1-1220", "PF1-2030"],
            "customers_referenced": ["Batelaan (Netherlands)", "KTec (Austria)", "NTF"],
            "currency_conversion": "80 INR = 1 EUR (approx)",
            "pricing_models": ["Model E (Electric)", "Model P (Pneumatic)"]
        }
    ))
    
    # 2. Cost Structure for 1000x1500mm PF1
    knowledge_items.append(KnowledgeItem(
        text="""PF1-1015 (1000x1500mm) Detailed Cost Structure - Total: ₹45.98 Lakhs (€57,472):

MAJOR COST CATEGORIES:

1. Universal Frame System - Bottom: ₹6,99,384 (€8,742)
   - Servo motors & drives (Mitsubishi): ₹1,09,920
   - Gearboxes (Bonfiglioli): ₹30,480
   - Linear guides (Hywin): ₹25,776
   - Ball bearings & chains: ₹26,108
   - Pneumatic cylinders: ₹35,100
   - Fabrication (Top plates, connectors, MS plates): ₹4,00,000

2. Motorised Frame System - Top: ₹1,04,630 (€1,308)
   - Servo motors (Mitsubishi): ₹54,960
   - Gearboxes (Bonfiglioli): ₹15,240
   - Cylinders (Festo): ₹10,725
   - Screw sets & part locks: ₹25,000

3. Heater System: ₹3,01,809 (€3,772)
   - Ceramic heaters (Elstein): ₹1,08,000
   - SSR controllers (Crydom): ₹34,335
   - Heater movement pneumatics (Festo): ₹94,554
   - Control PLCs (Mitsubishi): ₹36,120

4. Table 1 (Forming Table) - Pneumatic: ₹1,84,888 (€2,311)
   - Pneumatic cylinders & valves (Festo): ₹1,19,889
   - Fabrication: included

5. Table 2 (Mould Table) - Pneumatic: ₹3,88,595 (€4,857)
   - Pneumatics (Festo): ₹48,596
   - Vacuum system components: ₹65,000
   - Servo drives (Siemens): ₹5,000

6. Electrical Panel: ₹3,08,033 (€3,850)
   - Panel enclosure (Eldon): ₹50,000
   - PLCs & drives (Mitsubishi): ₹55,120
   - Electrical components (Schneider, Indo): ₹40,000
   - Sensors (Pepperl+Fuchs): ₹15,900
   - SSR & contactors: ₹34,335

7. Vacuum System: ₹1,66,608 (€2,083)
   - Vacuum pump (Busch): ₹65,000
   - Valves & fittings (Festo): ₹12,352
   - Vacuum tank & connections: ₹40,000

8. Cooling System: ₹21,180 (€265)
   - Cooling fans (EBM Papst): ₹21,180

9. Misc & Fabrication: ₹14,80,500 (€18,506)
   - Grid plate on mould table: ₹1,50,000
   - Base plate cooling: ₹2,50,000
   - Machine weight (10 tonnes): ₹10,00,000
   - Labour cost: 30 weeks
   - Gauges, switches, connectors: ₹60,500""",
        knowledge_type="commercial",
        source_file=SOURCE_FILE,
        summary="Detailed cost structure for PF1-1015 (1000x1500mm) machine",
        entity="Machinecraft",
        metadata={
            "machine_size": "1000x1500mm",
            "total_cost_inr": 4597771,
            "total_cost_eur": 57472,
            "cost_categories": ["frame_system", "heater_system", "tables", "electrical", "vacuum", "cooling", "fabrication"],
            "fabrication_weight_tonnes": 10,
            "assembly_time_weeks": 30
        }
    ))
    
    # 3. Key Component Brands and Costs
    knowledge_items.append(KnowledgeItem(
        text="""PF1 Machine Key Component Brands and Cost Distribution:

COMPONENT BRANDS BY COST (1000x1500mm reference):

1. Machinecraft (In-house fabrication): ₹8,43,500 (18.3%)
   - Top plates, frames, screws, bolsters
   - MS plates, brass connectors, cross members
   - Tooling plates, grid plates, base plates

2. Mitsubishi (Servo & Control): ₹4,84,230 (10.5%)
   - Servo motors: HG-KN43, HG-KN73
   - Servo drives: MR-JE-40A, MR-JE-70A
   - PLCs: FX5U series
   - HMI: GOT2000 series

3. Festo (Pneumatics): ₹4,05,486 (8.8%)
   - Cylinders: ADN, DSBC series
   - Valves: VUVG, VSVA series
   - FRL units, tubing, fittings

4. Elstein (Heaters): ₹1,08,000 (2.3%)
   - FSR ceramic heaters (650W/800W)
   - For uniform IR heating

5. PnF (Safety): ₹1,00,000 (2.2%)
   - Safety interlocks
   - Emergency stops
   - Light curtains

6. Eldon (Enclosures): ₹70,000 (1.5%)
   - Electrical panel body
   - Small panel enclosures

7. Busch (Vacuum): ₹65,000 (1.4%)
   - Vacuum pumps
   - 250-400 m³/hr capacity

8. Raytek (Temperature): ₹56,000 (1.2%)
   - Pyrometers for sheet temp monitoring
   - Non-contact IR sensors

9. Bonfiglioli (Gearboxes): ₹78,080 (1.7%)
   - VF series gearboxes
   - For servo motor reduction

10. Hywin (Linear Motion): ₹25,776 (0.6%)
    - HGH, HGR linear guides
    - For smooth table movement

11. Crydom (Power Control): ₹34,335 (0.7%)
    - Solid state relays for heaters
    - Phase angle control

12. Schneider (Electrical): ₹22,522 (0.5%)
    - MCCBs, contactors
    - Terminal blocks

OTHER BRANDS:
- EBM Papst (Fans): ₹21,180
- Indo Electricals: ₹21,156
- National Pneumatics: ₹54,100
- Pepperl+Fuchs (Sensors): ₹15,900
- Alwayse (Ball transfers): ₹10,908
- Siemens (Drives): ₹5,000
- Omron (Sensors): ₹2,400
- Euchner (Safety): ₹2,500""",
        knowledge_type="machine_spec",
        source_file=SOURCE_FILE,
        summary="Key component brands and their cost distribution in PF1 machines",
        entity="Machinecraft",
        metadata={
            "document_type": "component_analysis",
            "top_brands": ["Machinecraft", "Mitsubishi", "Festo", "Elstein", "Busch", "Bonfiglioli"],
            "in_house_percentage": 18.3,
            "servo_brand": "Mitsubishi",
            "pneumatics_brand": "Festo",
            "heater_brand": "Elstein",
            "vacuum_brand": "Busch"
        }
    ))
    
    # 4. Cost Scaling by Machine Size
    knowledge_items.append(KnowledgeItem(
        text="""PF1 Machine Cost Scaling by Size:

COST COMPARISON ACROSS SIZES:

1. PF1-1015 (1000x1500mm) - Batelaan Reference:
   - Model P (Pneumatic): ~€140,000 / ₹1.12 Cr
   - Model E (Electric): ~€190,000 / ₹1.52 Cr
   - BOM Cost: ₹45.98 Lakhs (€57,472)
   - Margin on Model P: ~60%
   - Margin on Model E: ~70%

2. PF1-2030 (2000x3000mm) - NTF Reference:
   - BOM Cost: ₹1.0 Cr (€125,000)
   - Estimated selling price: ₹1.8-2.2 Cr
   - Key cost increases:
     * Larger frame fabrication: +100%
     * More heaters required: +150%
     * Larger vacuum pump: +50%
     * Bigger servo motors: +80%

3. PF1-1220 (1200x2000mm) - KTec Austria:
   - Application: Clear plastics (non-automotive)
   - Stroke: 600mm
   - European pricing premium: ~20-30%

COST SCALING FACTORS:

Frame System:
- 1x1.5m to 2x3m: ~2.5x increase
- Linear guides, screws scale with length

Heater System:
- Scales with forming area
- 1x1.5m: ~₹3L heaters
- 2x3m: ~₹8L heaters (6 sq.m vs 1.5 sq.m)

Vacuum System:
- Larger pump for bigger area
- 1x1.5m: ₹65K pump
- 2x3m: ₹150K pump

Electrical:
- Relatively fixed cost
- Larger servos add ~30%

Fabrication:
- Scales roughly with weight
- 1x1.5m: ~10 tonnes
- 2x3m: ~25 tonnes

PRICING STRATEGY INSIGHT:
- BOM to Selling Price ratio: 2.5-3x for standard machines
- Premium features (servo drives) command 35-50% more
- European pricing includes logistics, compliance: +20-30%""",
        knowledge_type="commercial",
        source_file=SOURCE_FILE,
        summary="Cost scaling analysis for different PF1 machine sizes",
        entity="Machinecraft",
        metadata={
            "document_type": "cost_scaling_analysis",
            "reference_sizes": ["1000x1500mm", "1200x2000mm", "2000x3000mm"],
            "bom_to_price_ratio": "2.5-3x",
            "servo_premium": "35-50%",
            "european_premium": "20-30%"
        }
    ))
    
    # 5. Subsystem BOM Details
    knowledge_items.append(KnowledgeItem(
        text="""PF1 Machine Subsystem BOM Details:

FRAME SYSTEM (Bottom) - ₹6.99L:
Components:
- Servo motors (4x Mitsubishi HG-KN43): ₹1.10L
  * 1.3 Nm, 400W, 3000 RPM
  * Plain shaft without brake
- Servo drives (4x Mitsubishi MR-JE-40A): included
- Gearboxes (4x Bonfiglioli VF44): ₹30,480
  * U20 P71 B5 B3 configuration
- Linear guides (Hywin HGH20CAZAC): ₹13,080
- Linear rails (Hywin HGR20R): ₹12,696
- Ball screws & bearings: ₹13,600
- Chains & sprockets: ₹13,600
- Ball transfers (Alwayse 522-0-13): ₹10,908
- Pneumatic cylinders (National): ₹35,100
- Fabricated plates: ₹4,00,000

HEATER SYSTEM - ₹3.02L:
Components:
- Ceramic heaters (Elstein FSR):
  * Top zone: 36 pcs @ ₹1,500 = ₹54,000
  * Bottom zone: 36 pcs @ ₹1,500 = ₹54,000
- SSR controllers (Crydom): ₹34,335
  * Phase angle control for zone heating
- Heater movement (Festo ADN-40-50): ₹23,733
- PLC expansion (Mitsubishi): ₹36,120

FORMING TABLES - ₹5.73L:
Table 1 (Sheet clamping):
- Main cylinder (Festo DSBC): ₹71,873
- Guide cylinders (Festo): ₹48,016
- Vacuum connections: ₹15,000
- Fabrication: ₹50,000

Table 2 (Mould table):
- Lift cylinders (Festo DSBC-80): ₹35,000
- Proportional valves: ₹48,596
- Grid plate: ₹1,50,000
- Cooling plate: ₹2,50,000

ELECTRICAL PANEL - ₹3.08L:
- Enclosure (Eldon): ₹50,000
- PLC (Mitsubishi FX5U-64M): ₹28,400
- HMI (GOT2000): ₹16,800
- Servo drives: ₹55,120
- SSRs & contactors: ₹34,335
- Sensors (P+F): ₹15,900
- MCCBs (Schneider): ₹22,522
- Wiring & terminals: ₹30,000

VACUUM SYSTEM - ₹1.67L:
- Vacuum pump (Busch): ₹65,000
  * Oil-lubricated rotary vane
  * 250-400 m³/hr
- Vacuum tank: ₹25,000
- Valves (Festo): ₹12,352
- Pressure gauges: ₹5,000
- Piping: ₹15,000""",
        knowledge_type="machine_spec",
        source_file=SOURCE_FILE,
        summary="Detailed subsystem BOM breakdown for PF1 machines",
        entity="Machinecraft",
        metadata={
            "document_type": "subsystem_bom",
            "subsystems": ["frame", "heater", "tables", "electrical", "vacuum"],
            "servo_motor_model": "HG-KN43",
            "plc_model": "FX5U-64M",
            "heater_model": "Elstein FSR",
            "vacuum_pump_brand": "Busch"
        }
    ))
    
    # 6. Cost Optimization Insights
    knowledge_items.append(KnowledgeItem(
        text="""PF1 Machine Cost Optimization & Value Engineering Insights:

HIGH-COST AREAS FOR OPTIMIZATION:

1. In-house Fabrication (18.3% of BOM):
   - Largest cost component: ₹8.43L
   - Opportunities:
     * Standardize plate designs
     * Optimize cutting layouts
     * Reduce machine weight where possible
     * Consider outsourcing high-volume parts

2. Servo Systems (Mitsubishi) - 10.5%:
   - Total servo cost: ₹4.84L
   - Alternative options:
     * Delta for Indian market: 30-40% savings
     * Yaskawa for premium markets
     * Pneumatic for basic models (Model P)
   - Model P vs Model E shows ₹40L difference in selling price

3. Pneumatics (Festo) - 8.8%:
   - Premium German brand: ₹4.05L
   - Alternatives for cost markets:
     * SMC (Japanese): 10-15% savings
     * Indian brands: 40-50% savings
     * Janatics for domestic market

4. Heaters (Elstein) - 2.3%:
   - Premium ceramic: ₹1.08L
   - Alternatives:
     * Ceramicx (Ireland): Similar quality, competitive
     * TQS Halogen: Different technology, faster
     * Indian ceramics: 50% savings, quality variable

VALUE ENGINEERING DECISIONS:

For Model P (Budget):
- Pneumatic table drives instead of servo
- Fewer heater zones
- Manual clamp frame option
- Savings: 30-40% on BOM

For Model E (Premium):
- Full servo on all axes
- Zone-controlled heating
- Automatic everything
- Higher margin: 70% vs 60%

REGIONAL PRICING STRATEGY:
- India: Focus on Model P, price-sensitive
- Europe: Model E preferred, quality focus
- Japan: Premium features, local compliance
- USA: CE/CSA certification, Model E

BOM COST BENCHMARKS:
- Target BOM: 35-40% of selling price
- Current achieved: 40% for Model P, 30% for Model E
- Gross margin target: 50-60%""",
        knowledge_type="commercial",
        source_file=SOURCE_FILE,
        summary="Cost optimization insights and value engineering for PF1 machines",
        entity="Machinecraft",
        metadata={
            "document_type": "cost_optimization",
            "optimization_areas": ["fabrication", "servo_systems", "pneumatics", "heaters"],
            "target_bom_percentage": "35-40%",
            "model_p_margin": "60%",
            "model_e_margin": "70%"
        }
    ))
    
    # 7. European Customer BOM Analysis
    knowledge_items.append(KnowledgeItem(
        text="""European Customer BOM Analysis (Batelaan, KTec):

BATELAAN (NETHERLANDS) - 1000x1500mm:
Customer: Batelaan Kunststoffen
Location: Netherlands
Application: General thermoforming

BOM Summary:
- Base machine BOM: €57,472 (₹45.98L)
- Currency conversion: 80 INR = 1 EUR
- Total sections: 17 cost categories
- Major components all premium European/Japanese brands

Selling Price Analysis:
- Model P target: €140,000
- Model E target: €190,000
- Freight & logistics: ~€8,000-12,000
- Installation support: ~€5,000-8,000
- Total landed cost to customer: €150,000-210,000

KTEC (AUSTRIA) - 1200x2000mm:
Customer: KTec GmbH
Location: Austria
Application: Clear plastics, non-automotive
Specs: 1200x2000mm forming area, 600mm stroke

European Requirements:
- CE certification mandatory
- Documentation in local language
- Local electrical standards (400V/50Hz)
- Service response expectations: 24-48 hrs

Premium Component Selection for Europe:
- Mitsubishi preferred (German support)
- Festo (German pneumatics)
- Elstein (German heaters)
- Busch (German vacuum)
- All brands have European service networks

MARGIN ANALYSIS FOR EUROPE:
- BOM cost: ~€55,000-70,000
- Selling price: €140,000-190,000
- Gross margin: 55-65%
- After logistics: 45-55% net
- Higher than India due to:
  * Premium brand perception
  * Lower competition
  * Quality expectations match offering""",
        knowledge_type="commercial",
        source_file=SOURCE_FILE,
        summary="European customer BOM analysis for Batelaan and KTec",
        entity="Machinecraft",
        metadata={
            "document_type": "regional_analysis",
            "region": "Europe",
            "customers": ["Batelaan (Netherlands)", "KTec (Austria)"],
            "european_margin": "45-55%",
            "certification": "CE",
            "currency": "EUR"
        }
    ))
    
    return knowledge_items


def main():
    """Main ingestion function."""
    print("=" * 60)
    print("BOM Costing Analysis Ingestion")
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
