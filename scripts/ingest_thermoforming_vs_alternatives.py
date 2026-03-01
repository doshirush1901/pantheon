#!/usr/bin/env python3
"""
Ingest Thermoforming vs Alternative Technologies
By Andy Eavis, Thompson Plastics Group, UK (SPE 2008)

Comprehensive comparison of thermoforming against injection molding,
SMC, DCPD, rotational molding, RTM, fibreglass, and steel.
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

SOURCE_FILE = "14 Thermoforming vs Alternative TechnologiesTHOMPSON PLASTICS, Andy Eavis.pdf"


def create_knowledge_items() -> list:
    """Create knowledge items from Thompson Plastics presentation."""
    items = []

    # 1. Overview Comparison
    items.append(KnowledgeItem(
        text="""Thermoforming vs Alternative Technologies Overview:

SOURCE: Thompson Plastics Group, UK
PRESENTER: Andy Eavis
EVENT: Society of Plastics Engineers (SPE) 2008

PROCESSES COMPARED:
1. Thermoforming (Vacuum Forming, High Pressure Forming)
2. Injection Moulding
3. High Pressure SMC (Sheet Moulding Compound)
4. Low Pressure SMC
5. DCPD (Dicyclopentadiene - RIM process)
6. Rotational Moulding
7. RTM (Resin Transfer Moulding)
8. Lay-Up Fibreglass
9. Spray-Up Fibreglass
10. Pressed Steel

PROPERTIES COMPARISON (Generalities):

| Property | Injection | HP SMC | DCPD | Steel | Thermoforming |
|----------|-----------|--------|------|-------|---------------|
| Impact Strength | Medium | Upper-Med | Upper-Med | Very High | Medium |
| Heat Resistance | Medium | Upper-Med | Upper-Med | Very High | Medium |
| Surface Finish | High | Have to paint | Have to paint | Have to paint | Very High |
| Weatherability | High | Have to paint | Have to paint | Have to paint | Very High |
| Tooling Cost | Very High | Very High | High | Very High | Very Low |
| Tooling Adaptability | Very Difficult | Very Difficult | Difficult | Very Difficult | Very Easy |
| Project Lead Time | Long | Long | Medium | Long-Med | Short |
| Unit Cost | Low | Medium | Medium | Low | Medium |

KEY INSIGHT: Thermoforming wins on tooling cost, adaptability, lead time, 
and surface finish - but has medium unit cost (best for medium volumes).""",
        knowledge_type="operational",
        source_file=SOURCE_FILE,
        entity="Thermoforming vs Alternatives Overview",
        summary="Thompson Plastics comparison: thermoforming wins on tooling cost, adaptability, lead time, surface finish vs injection/SMC/steel",
        metadata={
            "source": "Thompson Plastics Group UK",
            "presenter": "Andy Eavis",
            "event": "SPE 2008",
            "processes_compared": 10,
            "thermoforming_wins": ["tooling_cost", "adaptability", "lead_time", "surface_finish"]
        }
    ))

    # 2. Detailed Attribute Matrix
    items.append(KnowledgeItem(
        text="""Thermoforming Process Attribute Comparison (10-Point Scale):

SCORING: 10 = Most Advantageous, 1 = Least Advantageous

| Attribute | High Pressure | Vacuum | Injection | Compression | Rotomold | RTM | Lay-Up | Steel |
|-----------|---------------|--------|-----------|-------------|----------|-----|--------|-------|
| Part Cost | 8 | 9 | 10 | 9 | 6 | 3 | 3 | 1 |
| Cycle Time | 6 | 5 | 10 | 8 | 6 | 1 | 1 | 3 |
| Part Weight | 9 | 10 | 8 | 4 | 6 | 5 | 5 | 1 |
| Processing Pressure | 4 | 8 | 1 | 2 | 5 | 10 | 10 | N/A |
| Tool Cost | 8 | 9 | 1 | 2 | 5 | 10 | 10 | 2 |
| Tool Delivery | 7 | 8 | 1 | 2 | 5 | 10 | 10 | 3 |
| Machine Cost | 6 | 7 | 2 | 5 | 1 | 10 | 10 | 5 |
| Maximum Size | 7 | 8 | 1 | 2 | 6 | 10 | 10 | 2 |
| Material Limitations | 8 | 7 | 10 | 6 | 1 | 3 | 3 | N/A |
| Moulded-In Stress | 7 | 8 | 1 | 5 | 10 | 3 | 3 | 5 |
| Stiffness | 4 | 3 | 8 | 9 | 1 | 9 | 9 | 10 |
| Impact Strength | 6 | 7 | 2 | 5 | 9 | 3 | 3 | 10 |
| Surface Quality | 8 | 6 | 10 | 9 | 7 | 2 | 2 | 4 |
| Textured Surfaces | 8 | 4 | 10 | 9 | 7 | 2 | 2 | N/A |
| Sharp Corners | 7 | 4 | 10 | 10 | 6 | 2 | 2 | 1 |
| Wall Gauge Uniformity | 4 | 3 | 9 | 8 | 5 | 1 | 1 | 10 |
| Finished Both Sides | 3 | N/A | 10 | 10 | 10 | N/A | N/A | 10 |
| Shape Complexity | 6 | 5 | 10 | 8 | 7 | 2 | 2 | 1 |
| Dimensional Stability | 5 | 3 | 9 | 10 | 7 | 1 | 1 | 4 |

THERMOFORMING STRENGTHS (Score 7-10):
- Part Cost: Vacuum 9, HP 8
- Part Weight: Vacuum 10, HP 9 (lightweight parts)
- Tool Cost: Vacuum 9, HP 8
- Tool Delivery: Vacuum 8, HP 7
- Machine Cost: Vacuum 7, HP 6
- Maximum Size: Vacuum 8, HP 7
- Material Options: HP 8, Vacuum 7
- Low Moulded-In Stress: Vacuum 8, HP 7
- Surface Quality: HP 8
- Textured Surfaces: HP 8

THERMOFORMING WEAKNESSES (Score 1-5):
- Stiffness: Vacuum 3, HP 4
- Wall Uniformity: Vacuum 3, HP 4
- Finished Both Sides: Vacuum N/A, HP 3
- Dimensional Stability: Vacuum 3, HP 5
- Sharp Corners: Vacuum 4""",
        knowledge_type="operational",
        source_file=SOURCE_FILE,
        entity="Process Attribute Matrix",
        summary="10-point attribute matrix: thermoforming scores highest on tool cost (9), part weight (10), max size (8); lowest on wall uniformity (3)",
        metadata={
            "scoring_scale": "1-10 (10=best)",
            "vacuum_forming_strengths": ["part_cost", "part_weight", "tool_cost", "tool_delivery", "max_size"],
            "vacuum_forming_weaknesses": ["stiffness", "wall_uniformity", "dimensional_stability", "sharp_corners"],
            "hp_forming_strengths": ["surface_quality", "textured_surfaces", "material_options"]
        }
    ))

    # 3. Production Volume Sweet Spots
    items.append(KnowledgeItem(
        text="""Production Volume Sweet Spots by Process:

VOLUME RANGES AND BEST-FIT PROCESSES:

1. VERY LOW NUMBERS (Under 500 per item):
   - Fibreglass (lay-up, spray-up) *
   - RTM (Resin Transfer Moulding) *
   * Low cost tools, can easily multi-tool

2. LOW NUMBERS (500 to 5,000 units):
   - Rotational Moulding *
   - Low Pressure SMC
   - PU Integral Skin
   * Low cost tools, can easily multi-tool

3. MEDIUM NUMBERS (5,000 to 25,000 units):
   - THERMOFORMING * ← SWEET SPOT
   - DCPD
   * Low cost tools, can easily multi-tool

4. HIGH NUMBERS (Over 25,000 units):
   - High Pressure SMC
   - Injection Moulding

KEY INSIGHT FOR MACHINECRAFT SALES:

Thermoforming is IDEAL for:
- Annual volumes: 5,000 to 25,000 parts
- Multiple part variants (easy tool changes)
- Projects where tooling amortization is critical
- Products with shorter lifecycle
- When design changes are expected

Thermoforming is LESS IDEAL for:
- Very high volumes (>25,000/year) - injection wins
- Very low volumes (<500) - fibreglass/RTM wins
- Parts requiring extreme dimensional accuracy

MULTI-TOOLING ADVANTAGE:
- Thermoforming tools are cheap enough to duplicate
- Run multiple cavities or multiple part variants
- Quick tool changeover on same machine
- PF1 can run different tools same day""",
        knowledge_type="commercial",
        source_file=SOURCE_FILE,
        entity="Production Volume Sweet Spots",
        summary="Thermoforming sweet spot: 5,000-25,000 units/year; below 500 use fibreglass; above 25,000 use injection",
        metadata={
            "thermoforming_sweet_spot": "5000-25000 units",
            "below_500": ["fibreglass", "RTM"],
            "500_to_5000": ["rotational_moulding", "low_pressure_SMC"],
            "above_25000": ["injection_moulding", "high_pressure_SMC"],
            "multi_tool_advantage": True
        }
    ))

    # 4. Maximum Part Size Capability
    items.append(KnowledgeItem(
        text="""Maximum Part Size by Manufacturing Process:

PRACTICAL MAXIMUM SIZES:

| Process | Max Part Size | Notes |
|---------|---------------|-------|
| Fibreglass | 30m+ | Boats, wind turbine blades |
| RTM | 30m+ | Large composite structures |
| THERMOFORMING | 5m | Large panels, bath tubs |
| Rotational Moulding | 3-4m | Tanks, large housings |
| DCPD | 3m | Automotive panels |
| Low Pressure SMC | 2m | Medium panels |
| High Pressure SMC | 2m | Press size limited |
| Injection Moulding | 2m | Machine size limited |
| Pressed Steel | 2m | Press size limited |

THERMOFORMING SIZE ADVANTAGE:

- Can produce parts up to 5m length
- Only fibreglass/RTM can go larger
- Much larger than injection (2m max)
- Larger than SMC (2m max)
- No expensive large press required

MACHINECRAFT MACHINE SIZES:
- PF1-2030: 2000 x 3000mm (2m x 3m)
- PF1-2525: 2500 x 2500mm
- PF1-3020: 3000 x 2000mm
- Custom sizes available up to 4m+

LARGE PART APPLICATIONS:
- Caravan/RV body panels (3-4m)
- Bath tubs (1.8-2.2m)
- Tractor hoods (1.5-2.5m)
- Bus interior panels (2-3m)
- Refrigerator doors (1-1.5m)
- Signage (any size)

COMPETITIVE POSITIONING:
"For parts 2-5m, thermoforming is the most cost-effective 
rigid plastic forming process. Injection is limited to 2m, 
and fibreglass requires hand labor."

SIZE vs COST SWEET SPOT:
- Small parts (<0.5m): Injection often wins
- Medium parts (0.5-2m): Thermoforming competitive
- Large parts (2-5m): Thermoforming wins clearly""",
        knowledge_type="operational",
        source_file=SOURCE_FILE,
        entity="Maximum Part Size Capability",
        summary="Thermoforming max size 5m - larger than injection/SMC (2m), only fibreglass goes bigger; PF1 up to 3m+",
        metadata={
            "thermoforming_max": "5m",
            "injection_max": "2m",
            "smc_max": "2m",
            "only_larger": ["fibreglass", "RTM"],
            "machinecraft_max": "4m+"
        }
    ))

    # 5. Cost and Cycle Comparison
    items.append(KnowledgeItem(
        text="""Process Cost and Cycle Time Comparison:

TOOL COST, CYCLES, AND TOOL LIFE:

| Process | Tool Cost | Cycles/Week* | Tool Life |
|---------|-----------|--------------|-----------|
| Rotational Moulding | Low | 120 | 50,000 cycles |
| DCPD | Medium | 1,200 | 100,000 (aluminum) |
| RTM | Medium | 80 | 50,000 (aluminum), 3,000 (resin) |
| SMC Low Pressure | Medium | 600 | 100,000 (aluminum) |
| PU Integral Skin | Medium | 600 | 50,000 (aluminum), 200,000 (steel) |
| SMC High Pressure | High | 2,000 | 1,000,000 (steel) |
| THERMOFORMING | LOW | 1,500 | 100,000 (aluminum), 25,000 (resin) |

* One shift, one cavity

THERMOFORMING ECONOMICS:

Tool Cost: LOW (aluminum or resin/composite)
- Aluminum mould: 10-20% of injection tool cost
- Resin/composite mould: 5-10% of injection tool cost
- Fast to manufacture: 2-6 weeks vs 12-20 weeks

Cycles/Week: 1,500 (competitive)
- Only HP SMC (2,000) and DCPD (1,200) are close
- Much faster than rotomold (120) or RTM (80)
- Supports medium-high volumes

Tool Life: 100,000 cycles (aluminum)
- Good durability
- 25,000 cycles for resin tools (prototyping)
- Can refurbish/repair tools easily

COST BREAKDOWN INSIGHT:

For 10,000 parts/year:
| Process | Tool Cost | Tool Amortization/Part |
|---------|-----------|------------------------|
| Injection | $100,000 | $10.00 |
| Thermoforming | $15,000 | $1.50 |

Thermoforming tool payback: 6x faster

WHEN THERMOFORMING WINS ON COST:
- Volumes under 25,000/year
- Multiple part variants
- Design likely to change
- Large parts (>1m)
- Project timeline is short""",
        knowledge_type="commercial",
        source_file=SOURCE_FILE,
        entity="Cost and Cycle Comparison",
        summary="Thermoforming: LOW tool cost, 1,500 cycles/week, 100K tool life; tool cost 10-20% of injection",
        metadata={
            "tool_cost": "10-20% of injection",
            "cycles_per_week": 1500,
            "tool_life_aluminum": 100000,
            "tool_life_resin": 25000,
            "volume_breakeven": "~25000 units"
        }
    ))

    # 6. Surface Quality Ranking
    items.append(KnowledgeItem(
        text="""Surface Quality Ranking by Process:

SURFACE FINISH AND WEATHER RESISTANCE (Best to Worst):

1. THERMOFORMING - BEST
   - No painting required
   - Weather resistant (ABS/ASA, ABS/PMMA)
   - High gloss achievable
   - Huge variety of textures and patterns
   - Even photo-realistic finishes possible
   - Class A surface with right materials

2. INJECTION MOULDING
   - Excellent surface from tool
   - Can have texture
   - Generally good weatherability
   - May need painting for premium finish

3. FIBREGLASS (Hand Lay-Up)
   - Gel coat provides good finish
   - Can achieve high gloss
   - Weather resistant with gel coat

4. RTM
   - Good gel coat surface
   - Less consistent than injection

5. ROTATIONAL MOULDING
   - Reasonable surface
   - Limited texture options
   - Good for utility parts

6. DCPD
   - NEEDS PAINTING
   - Surface not suitable for show

7. SMC (All types)
   - NEEDS PAINTING
   - Surface porosity issues
   - Class A requires significant finishing

8. STEEL - WORST
   - NEEDS PAINTING
   - Corrosion protection required
   - Paint adds cost and process steps

KEY SALES POINT:
"Thermoforming delivers Class A surface quality without painting.
SMC, DCPD, and steel ALL require painting to achieve 
equivalent surface finish - adding cost and lead time."

SURFACE OPTIONS IN THERMOFORMING:
- High gloss (mirror finish)
- Matte/satin
- Textured (leather, wood grain, geometric)
- Metallic appearance
- Photo prints under clear
- Soft touch (TPU surface)

WEATHER RESISTANCE:
- ABS/ASA: 10+ year outdoor UV stability
- ABS/PMMA: High gloss maintained outdoor
- Standard ABS: Indoor use, will yellow outdoor""",
        knowledge_type="operational",
        source_file=SOURCE_FILE,
        entity="Surface Quality Ranking",
        summary="Surface quality ranking: Thermoforming BEST (no paint needed), then injection; SMC/DCPD/steel need painting",
        metadata={
            "ranking": ["thermoforming", "injection", "fibreglass", "RTM", "rotomold", "DCPD", "SMC", "steel"],
            "no_paint_required": ["thermoforming", "injection"],
            "painting_required": ["DCPD", "SMC", "steel"],
            "outdoor_materials": ["ABS/ASA", "ABS/PMMA"]
        }
    ))

    # 7. Advantages and Limitations
    items.append(KnowledgeItem(
        text="""Thermoforming Advantages and Limitations Summary:

ADVANTAGES OF THERMOFORMING:

1. CHEAP TOOLING
   a) Variety of materials for tools
      - Aluminum (production)
      - Resin/composite (prototyping)
      - MDF/wood (short runs)
   b) Adaptability of moulds
      - Easy to modify
      - Add/remove features simply
   c) Fast to design and make tools
      - 2-6 weeks typical
      - vs 12-20 weeks for injection
   d) Cheap and easy to prototype
      - Resin tools for testing
      - Low risk iterations

2. VERY HIGH QUALITY FINISH
   a) Weather resistance
      - ABS/ASA, ABS/PMMA outdoor rated
   b) High gloss achievable
      - Class A without painting
   c) Huge variety of textures and patterns
      - Leather, wood grain, custom
      - Even photos can be incorporated
   d) Reliable and easy process
      - Consistent results

3. REASONABLY EFFICIENT PROCESS
   a) Medium cycle time
      - Faster than rotomold, RTM
      - Competitive with SMC
   b) Edge trim recyclable
      - Regrind back into sheet
      - Minimal waste
   c) Good utilization of material
      - Optimize nesting
      - Multiple parts per sheet
   d) Wide variety of materials
      - ABS, PP, PC, PETG, HDPE, etc.

LIMITATIONS OF THERMOFORMING:

1. Can only control ONE surface
   - Other side is air-formed
   - Not suitable for both-sides cosmetic

2. Nearly always has second finishing operation
   - Trimming/routing required
   - Holes, cutouts needed post-forming

3. Limited with undercuts and inserts
   - No core pulls like injection
   - Inserts must be post-installed

4. Limited shapes
   - Deep draws challenging
   - Wall thinning on deep parts

5. Some limits on temperature and fire resistance
   - Material dependent
   - FR grades available but limited
   - Not for high-temp applications

WHEN TO RECOMMEND THERMOFORMING:
✓ Medium volumes (5,000-25,000)
✓ Large parts (>0.5m)
✓ Surface quality matters
✓ Short lead time needed
✓ Design may change
✓ Tooling budget limited

WHEN TO RECOMMEND ALTERNATIVES:
✗ Very high volumes (>50,000) → Injection
✗ Both-sides cosmetic → Injection
✗ Complex shapes with undercuts → Injection
✗ Very low volumes (<500) → Fibreglass
✗ Extreme stiffness needed → SMC/Steel""",
        knowledge_type="operational",
        source_file=SOURCE_FILE,
        entity="Thermoforming Advantages and Limitations",
        summary="Advantages: cheap tooling, fast, high finish quality, recyclable. Limitations: one surface, needs trimming, limited undercuts",
        metadata={
            "key_advantages": ["cheap_tooling", "fast_delivery", "high_surface_quality", "recyclable_trim", "material_variety"],
            "limitations": ["one_surface_only", "needs_trimming", "limited_undercuts", "wall_thinning"],
            "recommend_for": ["medium_volumes", "large_parts", "surface_quality", "short_lead_time"],
            "alternatives_for": ["high_volumes", "both_sides_cosmetic", "complex_undercuts"]
        }
    ))

    # 8. Sales Battle Card
    items.append(KnowledgeItem(
        text="""Thermoforming Sales Battle Card - vs Competitors:

VS INJECTION MOULDING:

Thermoforming WINS when:
- Volume < 25,000 parts/year
- Part size > 1m
- Design changes expected
- Short lead time needed
- Tooling budget limited

Injection WINS when:
- Volume > 50,000 parts/year
- Both sides need finish
- Complex undercuts/inserts
- Tight tolerances critical
- Small parts (<0.3m)

Key Argument: "Our tooling is 10-20% of injection cost, 
delivered in 3-6 weeks vs 4-6 months."

VS SMC (Sheet Moulding Compound):

Thermoforming WINS when:
- Surface finish matters (no paint)
- Larger parts needed (>2m)
- Lower volumes
- Faster delivery needed

SMC WINS when:
- High stiffness required
- High temperature exposure
- Very high volumes
- Fire rating critical

Key Argument: "SMC always needs painting. Our parts 
come off the machine ready to assemble."

VS FIBREGLASS/RTM:

Thermoforming WINS when:
- Volume > 500 parts/year
- Consistent quality needed
- Faster cycle times needed
- Labor cost matters

Fibreglass WINS when:
- Very low volumes (<500)
- Extremely large parts (>5m)
- One-off or custom shapes
- Tooling budget near zero

Key Argument: "At 1,000+ parts/year, our automated 
process beats hand layup on cost and consistency."

VS ROTATIONAL MOULDING:

Thermoforming WINS when:
- Cycle time matters
- Surface quality critical
- Wall control needed
- Medium-high volumes

Rotomold WINS when:
- Hollow parts needed
- Very large tanks
- No seams required
- Low volumes acceptable

Key Argument: "We deliver 1,500 cycles/week vs 
rotomold's 120. That's 12x faster output."

VS STEEL/METAL:

Thermoforming WINS when:
- Weight reduction needed
- Corrosion resistance
- Complex curves
- No painting preferred
- Lower tooling budget

Steel WINS when:
- Maximum stiffness needed
- High impact/abuse
- Very high volumes
- Fire/temperature critical

Key Argument: "Plastic parts don't rust, weigh 50% less, 
and don't need painting for weather protection."

UNIVERSAL CLOSING STATEMENT:
"Thermoforming offers the best balance of tooling cost, 
surface quality, and lead time for parts in the 5,000-25,000 
volume range. Let's discuss your specific requirements."
""",
        knowledge_type="commercial",
        source_file=SOURCE_FILE,
        entity="Sales Battle Card",
        summary="Sales battle card: vs Injection (tooling 10-20%, faster delivery), vs SMC (no paint needed), vs Fibreglass (faster cycles)",
        metadata={
            "vs_injection": ["lower_volume", "larger_parts", "faster_delivery", "cheaper_tooling"],
            "vs_smc": ["better_surface", "larger_parts", "no_painting"],
            "vs_fibreglass": ["higher_volume", "faster_cycles", "consistent_quality"],
            "vs_rotomold": ["faster_cycles", "better_surface", "wall_control"],
            "vs_steel": ["lighter_weight", "no_corrosion", "no_painting", "cheaper_tooling"]
        }
    ))

    return items


def main():
    """Main ingestion function."""
    print("=" * 60)
    print("Thermoforming vs Alternative Technologies Ingestion")
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
