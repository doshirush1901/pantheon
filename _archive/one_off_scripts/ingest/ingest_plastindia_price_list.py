#!/usr/bin/env python3
"""
Ingest Machinecraft Price List for Plastindia (India Market)

Complete INR pricing for all Machinecraft machine series.
This is the official India market price reference.

Source: Machinecraft Price List for Plastindia (1).pdf
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from openclaw.agents.ira.src.brain.knowledge_ingestor import KnowledgeIngestor, KnowledgeItem

SOURCE_FILE = "Machinecraft Price List for Plastindia (1).pdf"


def create_knowledge_items() -> list[KnowledgeItem]:
    """Create structured knowledge items from the price list."""
    items = []

    # 1. Complete Price List Overview
    items.append(KnowledgeItem(
        text="""Machinecraft India Price List Overview (Plastindia)

DOCUMENT: Official India Market Price List
CURRENCY: Indian Rupees (INR / Rs)
MARKET: India (domestic)
TOTAL MACHINES LISTED: 34 models across 10 series

SERIES COVERED:
1. AM Series (thin-gauge roll-fed)
2. AM Pressure Series (pressure forming)
3. FCS Inline Series (form-cut-stack)
4. UNO Series (single station)
5. DUO Series (double station)
6. IMG Series (in-mold graining)
7. PLAY Series (desktop/training)
8. PF1-C Pneumatic Series (cut-sheet)
9. PF1-R Roll Feeder Series
10. PF2 Series (open-type)

PRICE RANGE:
- Entry level: ₹3.5 Lakhs (PLAY 450 DT)
- Mid-range: ₹15-50 Lakhs (AM, UNO, DUO)
- Production: ₹50-80 Lakhs (PF1, PF2)
- High-volume: ₹1-1.75 Crore (FCS, IMG)

NOTE: Prices are base/indicative, actual quotes may vary with options.""",
        knowledge_type="commercial",
        source_file=SOURCE_FILE,
        entity="India Price List",
        summary="India price list: 34 machines, ₹3.5L to ₹1.75Cr, 10 series, Plastindia reference",
        metadata={
            "topic": "price_list_overview",
            "market": "India",
            "currency": "INR",
            "total_models": 34
        }
    ))

    # 2. AM Series Pricing
    items.append(KnowledgeItem(
        text="""AM Series India Pricing (Thin-Gauge Roll-Fed)

STANDARD AM MACHINES:
| Model      | Price (₹)   | Price (Lakhs) | Forming Area | Description |
|------------|-------------|---------------|--------------|-------------|
| AM-5060    | 7,50,000    | ₹7.5L         | 500 x 600mm  | Standard AM |
| AM-6060    | 9,00,000    | ₹9L           | 600 x 600mm  | Standard AM |

SPECIALTY AM MACHINES:
| Model        | Price (₹)   | Price (Lakhs) | Description |
|--------------|-------------|---------------|-------------|
| AM-5060-P    | 15,00,000   | ₹15L          | With inline hydro-pneumatic press |
| AM-7080-CM   | 28,00,000   | ₹28L          | 700x800mm for Car mat |
| AM-100180-CM | 50,00,000   | ₹50L          | 1000x1800mm for Car mat |

AM PRESSURE FORMING:
| Model      | Price (₹)   | Price (Lakhs) | Description |
|------------|-------------|---------------|-------------|
| AMP-5060   | 35,00,000   | ₹35L          | Pressure forming 500x600 |
| AMP-6070-S | 50,00,000   | ₹50L          | Pressure forming servo |

PRICING LOGIC:
- Base AM (500x600): ₹7.5L
- Size upgrade (+100mm): ~₹1.5L premium
- Inline press option: +₹7.5L (~100% premium)
- Car mat specialty: 3.7x to 6.7x base price
- Pressure forming: 4.7x base price
- Servo upgrade: +₹15L on pressure""",
        knowledge_type="commercial",
        source_file=SOURCE_FILE,
        entity="AM Series Pricing",
        summary="AM India: ₹7.5L base, ₹9L (6060), ₹35L pressure, ₹50L servo pressure, up to ₹50L car mat",
        metadata={
            "topic": "am_series_pricing",
            "base_price_inr": 750000,
            "series": "AM"
        }
    ))

    # 3. FCS Inline Series Pricing
    items.append(KnowledgeItem(
        text="""FCS Inline Series India Pricing (Form-Cut-Stack)

PNEUMATIC FCS MACHINES:
| Model         | Price (₹)    | Price (Crore) | Stations | Description |
|---------------|--------------|---------------|----------|-------------|
| FCS 6050-3ST  | 1,00,00,000  | ₹1 Cr         | 3        | Form, Cut, Stack - pneumatic |
| FCS 6050-4ST  | 1,25,00,000  | ₹1.25 Cr      | 4        | Form, Cut, Hole, Stack - pneumatic |

SERVO FCS MACHINES:
| Model         | Price (₹)    | Price (Crore) | Stations | Description |
|---------------|--------------|---------------|----------|-------------|
| S FCS 7060-3ST| 1,50,00,000  | ₹1.5 Cr       | 3        | Form, Cut, Stack - servo |
| S FCS 7060-4ST| 1,75,00,000  | ₹1.75 Cr      | 4        | Form, Cut, Hole, Stack - servo |

PRICING LOGIC:
- 3-station pneumatic base: ₹1 Cr
- 4th station (holing): +₹25L (+25%)
- Servo upgrade: +₹50L (+50%)
- Servo + 4 station: +₹75L total (+75%)

FORMING AREA:
- Pneumatic: 600 x 500mm (6050)
- Servo: 700 x 600mm (7060)

VALUE PROPOSITION:
- High-volume packaging production
- Automated inline process
- Food packaging, disposables, lids""",
        knowledge_type="commercial",
        source_file=SOURCE_FILE,
        entity="FCS Series Pricing",
        summary="FCS India: ₹1Cr (3-stn pneumatic) to ₹1.75Cr (4-stn servo), inline packaging machines",
        metadata={
            "topic": "fcs_series_pricing",
            "base_price_inr": 10000000,
            "series": "FCS"
        }
    ))

    # 4. UNO & DUO Series Pricing
    items.append(KnowledgeItem(
        text="""UNO & DUO Series India Pricing (Single/Double Station)

UNO SERIES (Single Station):
| Model       | Price (₹)   | Price (Lakhs) | Forming Area | Description |
|-------------|-------------|---------------|--------------|-------------|
| UNO 0806    | 15,00,000   | ₹15L          | 800 x 600mm  | Single cylinder mould, 2 cyl clamp, top heater only |
| UNO 1208    | 20,00,000   | ₹20L          | 1200 x 800mm | Single cylinder mould, 2 cyl clamp, top heater only |
| UNO 1208-2H | 25,00,000   | ₹25L          | 1200 x 800mm | Single cylinder mould, 2 cyl clamp, sandwich heater |

DUO SERIES (Double Station):
| Model    | Price (₹)   | Price (Lakhs) | Forming Area | Description |
|----------|-------------|---------------|--------------|-------------|
| DUO 0806 | 20,00,000   | ₹20L          | 800 x 600mm  | Double station, single heater |
| DUO 1208 | 25,00,000   | ₹25L          | 1200 x 800mm | Double station, single heater |

PRICING LOGIC:
- UNO base (800x600): ₹15L
- UNO size upgrade (1200x800): +₹5L
- UNO sandwich heater upgrade: +₹5L
- DUO vs UNO same size: +₹5L (double station premium)

UNO CHARACTERISTICS:
- Single cylinder mould movement
- 2 cylinder clamp system
- Entry-level cut-sheet option
- Top heater only (base) or sandwich

DUO CHARACTERISTICS:
- Double station = higher throughput
- Single heater serves both stations
- Good for medium volumes""",
        knowledge_type="commercial",
        source_file=SOURCE_FILE,
        entity="UNO DUO Pricing",
        summary="UNO India: ₹15-25L (single station), DUO: ₹20-25L (double station), entry cut-sheet",
        metadata={
            "topic": "uno_duo_pricing",
            "uno_base_inr": 1500000,
            "duo_base_inr": 2000000,
            "series": ["UNO", "DUO"]
        }
    ))

    # 5. IMG Series Pricing
    items.append(KnowledgeItem(
        text="""IMG Series India Pricing (In-Mold Graining)

IMG MACHINES:
| Model    | Price (₹)    | Price (Crore) | Forming Area  | Description |
|----------|--------------|---------------|---------------|-------------|
| IMG 1205 | 1,25,00,000  | ₹1.25 Cr      | 1200 x 500mm  | IMG machine |
| IMG 2012 | 1,75,00,000  | ₹1.75 Cr      | 2000 x 1200mm | IMG machine |

PRICING LOGIC:
- Base IMG (1200x500): ₹1.25 Cr
- Large IMG (2000x1200): ₹1.75 Cr (+40% for 3.3x area)
- Premium over PF1: 2-3x (for automotive-grade capability)

IMG APPLICATIONS:
- Automotive interior panels
- Instrument panel skins
- Door panel skins
- Soft-touch surfaces
- Premium textured parts

WHY IMG IS EXPENSIVE:
- High clamping force (10-15 tonnes)
- Full servo drives
- Precision temperature control
- Automotive quality requirements
- TPO/TPU material processing""",
        knowledge_type="commercial",
        source_file=SOURCE_FILE,
        entity="IMG Series Pricing",
        summary="IMG India: ₹1.25Cr (1200x500) to ₹1.75Cr (2000x1200), automotive interior machines",
        metadata={
            "topic": "img_series_pricing",
            "base_price_inr": 12500000,
            "series": "IMG"
        }
    ))

    # 6. PF1-C Pneumatic Series Pricing
    items.append(KnowledgeItem(
        text="""PF1-C Pneumatic Series India Pricing (Cut-Sheet)

COMPLETE PF1-C PRICE TABLE:
| Model      | Price (₹)   | Price (Lakhs) | Forming Area  |
|------------|-------------|---------------|---------------|
| PF1-C-1008 | 33,00,000   | ₹33L          | 1000 x 800mm  |
| PF1-C-1208 | 35,00,000   | ₹35L          | 1200 x 800mm  |
| PF1-C-1212 | 38,00,000   | ₹38L          | 1200 x 1200mm |
| PF1-C-1510 | 40,00,000   | ₹40L          | 1500 x 1000mm |
| PF1-C-1812 | 45,00,000   | ₹45L          | 1800 x 1200mm |
| PF1-C-2010 | 50,00,000   | ₹50L          | 2000 x 1000mm |
| PF1-C-2015 | 60,00,000   | ₹60L          | 2000 x 1500mm |
| PF1-C-2020 | 65,00,000   | ₹65L          | 2000 x 2000mm |
| PF1-C-2515 | 70,00,000   | ₹70L          | 2500 x 1500mm |
| PF1-C-3015 | 75,00,000   | ₹75L          | 3000 x 1500mm |
| PF1-C-3020 | 80,00,000   | ₹80L          | 3000 x 2000mm |

PRICING PATTERN:
- Base (1000x800): ₹33L
- Per 100mm width increase: ~₹1-2L
- Per 100mm height increase: ~₹2-3L
- Large format premium (3000mm): ~₹5-7L/step

MODEL NAMING: PF1-C-WWLL
- WW = Width in cm (e.g., 20 = 2000mm)
- LL = Length in cm (e.g., 15 = 1500mm)

CHARACTERISTICS:
- Pneumatic movements (standard)
- Cut-sheet feeding
- Heavy-gauge thermoforming
- Industrial/automotive applications""",
        knowledge_type="commercial",
        source_file=SOURCE_FILE,
        entity="PF1-C Series Pricing",
        summary="PF1-C India: ₹33L (1008) to ₹80L (3020), pneumatic cut-sheet, 11 sizes available",
        metadata={
            "topic": "pf1_c_pricing",
            "min_price_inr": 3300000,
            "max_price_inr": 8000000,
            "series": "PF1-C",
            "models_count": 11
        }
    ))

    # 7. PF1-R Roll Feeder & PF2 Series
    items.append(KnowledgeItem(
        text="""PF1-R Roll Feeder & PF2 Series India Pricing

PF1 WITH ROLL FEEDER:
| Model      | Price (₹)   | Price (Lakhs) | Forming Area  | Description |
|------------|-------------|---------------|---------------|-------------|
| PF1-R-1510 | 55,00,000   | ₹55L          | 1500 x 1000mm | PF1 with roll feeder |

ROLL FEEDER PREMIUM:
- PF1-C-1510: ₹40L (cut-sheet)
- PF1-R-1510: ₹55L (roll feeder)
- Premium: +₹15L (+37.5%) for roll feeder capability

PF2 SERIES (Open-Type):
| Model      | Price (₹)   | Price (Lakhs) | Forming Area  | Description |
|------------|-------------|---------------|---------------|-------------|
| PF2-P2010  | 35,00,000   | ₹35L          | 2000 x 1000mm | Open type standard |
| PF2-P2020  | 52,00,000   | ₹52L          | 2000 x 2000mm | Open type standard |
| PF2-P2424  | 60,00,000   | ₹60L          | 2400 x 2400mm | Open type standard |

PF2 vs PF1 COMPARISON (same forming area):
- PF1-C-2010: ₹50L vs PF2-P2010: ₹35L (PF2 is ₹15L cheaper)
- PF1-C-2020: ₹65L vs PF2-P2020: ₹52L (PF2 is ₹13L cheaper)

WHY PF2 IS CHEAPER:
- Open-type design (American concept)
- Simpler construction
- Best for HDPE forming
- No enclosed chamber

PF2 APPLICATIONS:
- Pallets
- Tanks
- Large HDPE parts
- Sanitary ware""",
        knowledge_type="commercial",
        source_file=SOURCE_FILE,
        entity="PF1-R PF2 Pricing",
        summary="PF1-R: ₹55L (roll feeder +37% over cut-sheet), PF2: ₹35-60L (open-type, cheaper than PF1)",
        metadata={
            "topic": "pf1r_pf2_pricing",
            "pf1r_price_inr": 5500000,
            "pf2_min_inr": 3500000,
            "pf2_max_inr": 6000000,
            "series": ["PF1-R", "PF2"]
        }
    ))

    # 8. PLAY Series (Desktop)
    items.append(KnowledgeItem(
        text="""PLAY Series India Pricing (Desktop/Training)

PLAY MACHINE:
| Model       | Price (₹)  | Price (Lakhs) | Description |
|-------------|------------|---------------|-------------|
| PLAY 450 DT | 3,50,000   | ₹3.5L         | Small desktop machine, all movements manual |

CHARACTERISTICS:
- Desktop form factor
- Manual movements
- 450mm forming area
- Entry-level / training use

TARGET USERS:
- Educational institutions
- Design studios
- Prototyping labs
- Small-scale production
- Training centers

VALUE PROPOSITION:
- Lowest cost entry to thermoforming
- Learn machine operation basics
- Quick prototyping
- Low space requirement

COMPARISON:
- PLAY 450 DT: ₹3.5L
- Next step up (AM-5060): ₹7.5L (2.1x price)
- PLAY is 47% of entry AM price""",
        knowledge_type="commercial",
        source_file=SOURCE_FILE,
        entity="PLAY Series Pricing",
        summary="PLAY India: ₹3.5L desktop manual machine, lowest entry point, training/prototyping",
        metadata={
            "topic": "play_series_pricing",
            "price_inr": 350000,
            "series": "PLAY"
        }
    ))

    # 9. Complete Price Reference Table
    items.append(KnowledgeItem(
        text="""Machinecraft India Complete Price Reference (All 34 Models)

ENTRY LEVEL (Under ₹20L):
| Model       | Price     | Series | Use Case |
|-------------|-----------|--------|----------|
| PLAY 450 DT | ₹3.5L     | PLAY   | Training/prototype |
| AM-5060     | ₹7.5L     | AM     | Entry roll-fed |
| AM-6060     | ₹9L       | AM     | Entry roll-fed |
| AM-5060-P   | ₹15L      | AM     | With press |
| UNO 0806    | ₹15L      | UNO    | Entry cut-sheet |

MID-RANGE (₹20L - ₹50L):
| Model       | Price     | Series | Use Case |
|-------------|-----------|--------|----------|
| UNO 1208    | ₹20L      | UNO    | Cut-sheet |
| DUO 0806    | ₹20L      | DUO    | Double station |
| UNO 1208-2H | ₹25L      | UNO    | Sandwich heater |
| DUO 1208    | ₹25L      | DUO    | Double station |
| AM-7080-CM  | ₹28L      | AM     | Car mat |
| PF1-C-1008  | ₹33L      | PF1-C  | Cut-sheet |
| PF1-C-1208  | ₹35L      | PF1-C  | Cut-sheet |
| PF2-P2010   | ₹35L      | PF2    | Open-type |
| AMP-5060    | ₹35L      | AMP    | Pressure |
| PF1-C-1212  | ₹38L      | PF1-C  | Cut-sheet |
| PF1-C-1510  | ₹40L      | PF1-C  | Cut-sheet |
| PF1-C-1812  | ₹45L      | PF1-C  | Cut-sheet |
| AM-100180   | ₹50L      | AM     | Car mat XL |
| AMP-6070-S  | ₹50L      | AMP    | Pressure servo |
| PF1-C-2010  | ₹50L      | PF1-C  | Cut-sheet |

PRODUCTION (₹50L - ₹1Cr):
| Model       | Price     | Series | Use Case |
|-------------|-----------|--------|----------|
| PF2-P2020   | ₹52L      | PF2    | Open-type |
| PF1-R-1510  | ₹55L      | PF1-R  | Roll feeder |
| PF1-C-2015  | ₹60L      | PF1-C  | Cut-sheet |
| PF2-P2424   | ₹60L      | PF2    | Open-type XL |
| PF1-C-2020  | ₹65L      | PF1-C  | Cut-sheet |
| PF1-C-2515  | ₹70L      | PF1-C  | Cut-sheet |
| PF1-C-3015  | ₹75L      | PF1-C  | Cut-sheet |
| PF1-C-3020  | ₹80L      | PF1-C  | Cut-sheet XXL |

HIGH-VOLUME (₹1Cr+):
| Model         | Price     | Series | Use Case |
|---------------|-----------|--------|----------|
| FCS 6050-3ST  | ₹1 Cr     | FCS    | Inline 3-station |
| FCS 6050-4ST  | ₹1.25 Cr  | FCS    | Inline 4-station |
| IMG 1205      | ₹1.25 Cr  | IMG    | Automotive |
| S FCS 7060-3ST| ₹1.5 Cr   | FCS    | Inline servo |
| S FCS 7060-4ST| ₹1.75 Cr  | FCS    | Inline servo |
| IMG 2012      | ₹1.75 Cr  | IMG    | Automotive XL |""",
        knowledge_type="commercial",
        source_file=SOURCE_FILE,
        entity="Complete Price Table",
        summary="All 34 models: ₹3.5L (PLAY) to ₹1.75Cr (IMG/FCS servo), segmented by price tier",
        metadata={
            "topic": "complete_price_table",
            "total_models": 34,
            "min_price_inr": 350000,
            "max_price_inr": 17500000
        }
    ))

    return items


def main():
    """Main ingestion function."""
    print("=" * 60)
    print("Machinecraft Plastindia Price List Ingestion")
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
