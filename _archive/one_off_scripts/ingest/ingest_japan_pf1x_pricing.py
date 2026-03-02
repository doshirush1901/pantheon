#!/usr/bin/env python3
"""
Ingest MC Machine Line-up - Japan PF1-X Series Pricing

PF1-X series pricing for Japan market in JPY (Japanese Yen).
Through FVF (OEM partner) distribution channel.

Source: MC Machine Line-up (1).xlsx
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from openclaw.agents.ira.src.brain.knowledge_ingestor import KnowledgeIngestor, KnowledgeItem

SOURCE_FILE = "MC Machine Line-up (1).xlsx"


def create_knowledge_items() -> list[KnowledgeItem]:
    """Create structured knowledge items from the Japan price list."""
    items = []

    # 1. Japan Market Overview
    items.append(KnowledgeItem(
        text="""Japan PF1-X Series Market Overview

DOCUMENT: MC Machine Line-up (Confidential)
MARKET: Japan
CURRENCY: Japanese Yen (JPY / ¥)
DISTRIBUTION: OEM through FVF partner
SERIES: PF1-X (Premium Servo Thermoforming)

MODEL NAMING CONVENTION (FVF Method):
- CUVF = Custom Vacuum Forming
- XXYY = Dimensions (e.g., 1325 = 1300x2500mm)
- PWB = Pre-blow capable
- U/S = Universal/Static frame type
- A/M = Auto/Manual sheet loading
- S = Servo drive (all servo)

PRICE COMPONENTS:
- Body price (base machine)
- Packaging (5%)
- Transportation to Japan (10%)
- SV fee - Service/Support (8%)
- Total: Quote price in JPY

PRICE RANGE:
- Entry: ¥22.7M (Static, Manual, Pneumatic)
- Mid: ¥26-58M (Various configs)
- Premium: ¥64-96M (Large format, Auto, Servo)

LEAD TIMES:
- Small machines: 5-6 months
- Standard: 6-8 months
- Large format: 9-11 months

EXCHANGE RATE REFERENCE: ¥150 = $1 USD""",
        knowledge_type="commercial",
        source_file=SOURCE_FILE,
        entity="Japan PF1-X Overview",
        summary="Japan PF1-X: ¥22.7M to ¥96M via FVF OEM, includes 5% pack + 10% transport + 8% SV",
        metadata={
            "topic": "japan_market_overview",
            "market": "Japan",
            "currency": "JPY",
            "partner": "FVF"
        }
    ))

    # 2. Complete Japan Price Table
    items.append(KnowledgeItem(
        text="""Japan PF1-X Series Complete Price Table (JPY)

ALL PRICES INCLUDE: Base + 5% Packing + 10% Transport + 8% SV Fee

| Model           | FVF Code          | Frame     | Loader | Drive     | Price (¥)    | Price (~USD) | Lead  |
|-----------------|-------------------|-----------|--------|-----------|--------------|--------------|-------|
| PF1 1x1.5       | CUVF1510PWB-UMS   | Universal | Manual | All Servo | ¥26,445,000  | ~$176K       | 6 mo  |
| PF1 1x1.5       | CUVF1510PWB-UAS   | Universal | Auto   | All Servo | ¥36,285,000  | ~$242K       | 7 mo  |
| PF1 2.5x1.3     | CUVF1325PWB-UMS   | Universal | Manual | All Servo | ¥44,895,000  | ~$299K       | 6.5 mo|
| PF1 2.5x1.3     | CUVF1325PWB-UAS   | Universal | Auto   | All Servo | ¥55,965,000  | ~$373K       | 8 mo  |
| PF1 2.5x1.5     | CUVF1525PWB-SM    | Static    | Manual | Pneumatic | ¥22,755,000  | ~$152K       | 5 mo  |
| PF1 2.5x1.5     | CUVF1525PWB-SMS   | Static    | Manual | All Servo | ¥30,135,000  | ~$201K       | 6 mo  |
| PF1 2.5x1.5     | CUVF1525PWB-UMS   | Universal | Manual | All Servo | ¥39,975,000  | ~$266K       | 6 mo  |
| PF1 2.5x1.5     | CUVF1525PWB-UAS   | Universal | Auto   | All Servo | ¥58,425,000  | ~$390K       | 8.5 mo|
| PF1 2x1.5       | CUVF1520PWB-UAS   | Universal | Auto   | All Servo | ¥55,350,000  | ~$369K       | 8 mo  |
| PF1 3.5x2.5     | CUVF2535PWB-SAS   | Static    | Auto   | All Servo | ¥64,575,000  | ~$431K       | 6 mo  |
| PF1 4x2         | CUVF3040PWB-UAS   | Universal | Auto   | All Servo | ¥76,875,000  | ~$513K       | 9 mo  |
| PF1 4.8x2.5     | CUVF2548PWB-UAS   | Universal | Auto   | All Servo | ¥96,555,000  | ~$644K       | 11 mo |

NOTE: USD estimates at ¥150/$1 exchange rate""",
        knowledge_type="commercial",
        source_file=SOURCE_FILE,
        entity="Japan Price Table",
        summary="Japan PF1-X: 12 configs from ¥22.7M (manual pneumatic) to ¥96.5M (4.8x2.5 auto servo)",
        metadata={
            "topic": "japan_price_table",
            "models_count": 12,
            "min_price_jpy": 22755000,
            "max_price_jpy": 96555000
        }
    ))

    # 3. Frame Type & Loader Options Pricing Impact
    items.append(KnowledgeItem(
        text="""Japan PF1-X: Configuration Options & Pricing Impact

FRAME TYPE COMPARISON (Same Size 2.5x1.5):
| Config              | Frame     | Loader | Drive     | Price (¥)    |
|---------------------|-----------|--------|-----------|--------------|
| CUVF1525PWB-SM      | Static    | Manual | Pneumatic | ¥22,755,000  |
| CUVF1525PWB-SMS     | Static    | Manual | Servo     | ¥30,135,000  |
| CUVF1525PWB-UMS     | Universal | Manual | Servo     | ¥39,975,000  |
| CUVF1525PWB-UAS     | Universal | Auto   | Servo     | ¥58,425,000  |

UPGRADE COSTS (2.5x1.5 Example):
- Base (Static, Manual, Pneumatic): ¥22.75M
- + Servo drive: +¥7.38M (+32%)
- + Universal frame: +¥9.84M (+33% on top)
- + Auto loader: +¥18.45M (+46% on top)
- TOTAL upgrades: +¥35.67M (157% premium)

FRAME TYPE OPTIONS:
- Static (S): Fixed frame size, lower cost
- Universal (U): Adjustable frame size, flexible production

LOADER OPTIONS:
- Manual (M): Operator loads sheets, lower cost
- Auto (A): Automatic sheet loading/unloading robot

DRIVE OPTIONS:
- Pneumatic: Air cylinders, basic
- All Servo (S): Full servo motors, precision control

AUTO LOADER PREMIUM:
- PF1 1x1.5: ¥26.4M → ¥36.3M (+37% for auto)
- PF1 2.5x1.3: ¥44.9M → ¥56.0M (+25% for auto)
- PF1 2.5x1.5: ¥40.0M → ¥58.4M (+46% for auto)""",
        knowledge_type="commercial",
        source_file=SOURCE_FILE,
        entity="Japan Config Options",
        summary="Japan upgrades: Servo +32%, Universal frame +33%, Auto loader +25-46% over base",
        metadata={
            "topic": "configuration_pricing",
            "servo_premium_pct": 32,
            "universal_premium_pct": 33,
            "autoloader_premium_pct": "25-46"
        }
    ))

    # 4. Size-Based Pricing
    items.append(KnowledgeItem(
        text="""Japan PF1-X: Size-Based Pricing Analysis

SIZE PROGRESSION (All Servo, Universal, Auto Loader):
| Size      | Forming Area      | Price (¥)    | ¥/m² Area | Lead Time |
|-----------|-------------------|--------------|-----------|-----------|
| 1x1.5     | 1000x1500 (1.5m²) | ¥36,285,000  | ¥24.2M/m² | 7 mo      |
| 2x1.5     | 1500x2000 (3.0m²) | ¥55,350,000  | ¥18.5M/m² | 8 mo      |
| 2.5x1.3   | 1300x2500 (3.25m²)| ¥55,965,000  | ¥17.2M/m² | 8 mo      |
| 2.5x1.5   | 1500x2500 (3.75m²)| ¥58,425,000  | ¥15.6M/m² | 8.5 mo    |
| 3.5x2.5   | 2500x3500 (8.75m²)| ¥64,575,000  | ¥7.4M/m²  | 6 mo      |
| 4x2       | 2000x4000 (8.0m²) | ¥76,875,000  | ¥9.6M/m²  | 9 mo      |
| 4.8x2.5   | 2500x4800 (12m²)  | ¥96,555,000  | ¥8.0M/m²  | 11 mo     |

COST PER AREA DECREASES WITH SIZE:
- Small (1x1.5): ¥24.2M per m²
- Medium (2.5x1.5): ¥15.6M per m² (-35%)
- Large (4.8x2.5): ¥8.0M per m² (-67%)

ECONOMY OF SCALE:
Larger machines have better cost per forming area.
4.8x2.5 costs 2.7x the 1x1.5 price but has 8x the area.

XXL MACHINE SPECS (4.8x2.5):
- Forming area: 2500x4800mm (12 m²)
- Price: ¥96,555,000 (~$644K USD)
- Lead time: 11 months
- Gross weight: 40 tonnes
- Footprint: 14x9x6.5m""",
        knowledge_type="commercial",
        source_file=SOURCE_FILE,
        entity="Japan Size Pricing",
        summary="Japan size scaling: ¥24.2M/m² (small) to ¥8M/m² (XXL), economy of scale ~67% better",
        metadata={
            "topic": "size_based_pricing",
            "smallest_price_jpy": 36285000,
            "largest_price_jpy": 96555000
        }
    ))

    # 5. Technical Specifications
    items.append(KnowledgeItem(
        text="""Japan PF1-X Technical Specifications

COMMON FEATURES (All PF1-X Models):
- Pre-blow molding capability (PWB)
- Carbon heaters (main heater)
- Heater movement: F:3sec / R:3sec (servo models)
- Twin vacuum circuit
- Additional vacuum capability
- Air clamp tool fixing
- Sheet lift mechanism

FRAME SPECIFICATIONS:
- Universal (U): Adjustable frame
  - Max jig weight: Upper 500kg, Lower 1 ton
  - Multiple frame sizes supported
  
- Static (S): Fixed frame
  - Lower cost
  - Single frame size

BLOW MOLDING NOTE:
"During blow molding, the material can be inflated even when 
the lower heater is in the forward position."
(ブロー成型時は下ヒータが前に出ている状態でもブローで膨らませることができる)

MACHINE FOOTPRINTS:
| Model     | Footprint (WxDxH m) | Weight  |
|-----------|---------------------|---------|
| 1x1.5 Man | 4x4x5               | 10 to   |
| 1x1.5 Auto| 4x4x5.5             | 14 to   |
| 2.5x1.3 M | 5x6x6               | 15 to   |
| 2.5x1.3 A | 10x6x6.5            | 20 to   |
| 2.5x1.5   | 4-10x5-7x6-7        | 12-25 to|
| 3.5x2.5   | 10x6x6.5            | 30 to   |
| 4x2       | 12x8x6.5            | 35 to   |
| 4.8x2.5   | 14x9x6.5            | 40 to   |""",
        knowledge_type="machine_spec",
        source_file=SOURCE_FILE,
        entity="PF1-X Japan Specs",
        summary="PF1-X Japan: carbon heaters, pre-blow, twin vacuum, 3sec heater travel, up to 40 tonnes",
        metadata={
            "topic": "technical_specs",
            "heater_type": "Carbon",
            "features": ["pre_blow", "twin_vacuum", "air_clamp"]
        }
    ))

    # 6. Japan vs India Price Comparison
    items.append(KnowledgeItem(
        text="""Japan vs India PF1 Series Price Comparison

COMPARABLE MODELS (Similar Forming Area):

PF1 1500x1000 (1.5m²):
- India PF1-C-1510: ₹40L (~$48K USD)
- Japan PF1 1x1.5 Manual Servo: ¥26.4M (~$176K USD)
- Japan Premium: 3.7x India price

PF1 2000x1500 (3m²):
- India PF1-C-2015: ₹60L (~$72K USD)
- Japan PF1 2x1.5 Auto Servo: ¥55.4M (~$369K USD)
- Japan Premium: 5.1x India price

PF1 3000x2000 (6m²):
- India PF1-C-3020: ₹80L (~$96K USD)
- Japan PF1 4x2 Auto Servo: ¥76.9M (~$513K USD)
- Japan Premium: 5.3x India price

WHY JAPAN IS MORE EXPENSIVE:
1. Full servo drive (vs pneumatic in India base)
2. Auto sheet loader (vs manual in India base)
3. Universal frame (vs fixed in India base)
4. Carbon heaters (vs IR ceramic)
5. Partner margin (FVF OEM markup)
6. Import costs (5% pack + 10% transport + 8% SV)
7. Japanese market premium
8. Longer lead times (quality/compliance)

APPLE-TO-APPLE COMPARISON:
If adding all Japan features to India machine:
- India PF1-C-2015 base: ₹60L
- + Servo drive: +₹18L (estimate)
- + Auto loader: +₹60L (from options doc)
- + Universal frame: +₹40L
- Comparable India config: ~₹178L (~$214K)
- Still 42% less than Japan ¥55.4M (~$369K)

CONCLUSION:
Japan pricing includes premium features, partner margins,
and market positioning. India base prices are 4-5x lower
but need significant upgrades to match Japan spec.""",
        knowledge_type="commercial",
        source_file=SOURCE_FILE,
        entity="Japan vs India Pricing",
        summary="Japan 4-5x India base price, but includes servo+auto+universal; apple-to-apple ~42% gap",
        metadata={
            "topic": "japan_india_comparison",
            "japan_premium_factor": "4-5x",
            "comparable_gap_pct": 42
        }
    ))

    return items


def main():
    """Main ingestion function."""
    print("=" * 60)
    print("Japan PF1-X Series Price List Ingestion")
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
