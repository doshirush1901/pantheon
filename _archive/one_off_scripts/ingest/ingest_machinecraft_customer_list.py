#!/usr/bin/env python3
"""
Ingest List of Customers - Machinecraft

Historical customer data from fiscal years 2014-15, 2015-16, and 2016-17.
Contains customer details, machines sold, moulds, and tooling.
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

SOURCE_FILE = "List of Customers - Machinecraft.xlsx"


def create_knowledge_items() -> list:
    """Create knowledge items from customer list."""
    items = []

    # 1. Customer List Overview
    items.append(KnowledgeItem(
        text="""Machinecraft Historical Customer List Overview (2014-2017):

PERIOD COVERAGE: FY 2014-15, 2015-16, 2016-17 (3 fiscal years)
TOTAL CUSTOMER ENTRIES: 47 unique customers
TOTAL MACHINES/EQUIPMENT SOLD: 54+ units

GEOGRAPHIC DISTRIBUTION:
- India: ~35 customers (75%)
- Europe: 6 customers (Hungary, Sweden, UK)
- Middle East: 2 customers (Kenya, UAE, Iran)

MACHINE TYPES SOLD:
1. PF-1 Series (Vacuum Forming): Most popular
   - Sizes: 600x600 to 2000x2500mm
   - Variants: Standard, with autoloader, servo

2. INP Series (Inline Pressure Forming):
   - INP-5060, INP-5065
   - For high-volume production

3. AM Series (Continuous Vacuum Forming):
   - AM/500x600/IR/Servo
   - For blister packaging

4. SAM Series (Semi-Automatic):
   - Various sizes for different applications

5. Ancillary Equipment:
   - Air Circulating Ovens
   - Trimming Machines
   - Hydro-Pneumatic Punching Press
   - Sheet Extruders
   - Chillers

KEY INDUSTRY SECTORS SERVED:
- Luggage/Bags: VIP Industries (4 machines)
- Sanitaryware: Jaquar & Co. (3 machines)
- Automotive: R.K. Manoj (Etios, KWID covers)
- Packaging: Delmore, Polypack
- Signage/Display: Anchor Media (Sweden)
- Construction: Saraswati Plastotech (domes)
- Education: UPES, ISDI""",
        knowledge_type="client",
        source_file=SOURCE_FILE,
        entity="Machinecraft Customer Overview",
        summary="47 customers over 3 years (2014-17); 75% India, machines from PF1 to INP series, key sectors: luggage, sanitaryware, automotive",
        metadata={
            "period": "FY 2014-15 to FY 2016-17",
            "total_customers": 47,
            "total_machines": 54,
            "india_percentage": 75,
            "key_sectors": ["luggage", "sanitaryware", "automotive", "packaging", "signage", "construction", "education"]
        }
    ))

    # 2. Indian Customer Details
    items.append(KnowledgeItem(
        text="""Machinecraft Indian Customers (2014-2017):

MAJOR REPEAT CUSTOMERS:

1. VIP Industries Ltd. - Nashik
   - Contact: Mr. Vishnudas Gujarathi
   - Email: vishnudas.gujarathi@vipbags.com
   - Web: www.vipbags.com
   - Machines: 4x PF-1 series
     * PF-1/980x720
     * PF-1/960x660
     * PF-1/800x1000 (2 units)
   - Application: Luggage manufacturing

2. Jaquar & Co. Pvt. Ltd. - Manesar
   - Contact: Mr. Ashish Gupta
   - Email: agupta@jaquar.com
   - Machines:
     * PF-1/2000x2500 (large bath tubs)
     * Trimming machine
     * Free standing Heating Oven
   - Application: Sanitaryware (bath tubs)

3. Saraswati Plastotech India Pvt. Ltd. - J&K/Jammu
   - Contact: Mr. Gopinath
   - Email: gopinath@saraswati-group.com
   - Machines:
     * PF-1/1550x2000
     * Air Circulating Oven
     * Trimmer
   - Application: Construction domes, skylights
   - Additional: Multiple mould orders

4. Smartline Coach & Components Pvt. Ltd. - Corlim, Goa
   - Machine: PF-1/1000x2200 with 6 moulds
   - Application: Bus/Coach components

AUTOMOTIVE SECTOR:

5. R.K. Manoj & Co. - Sonepat
   - Contact: Mr. Manoj Jain
   - Email: manoj@automat.in
   - Machines: Vacuum Forming Machine
   - Moulds: Etios parts, KWID Engine Cover
   - Application: Automotive interior/under-hood

PACKAGING SECTOR:

6. Delmore Trading Pvt. Ltd. - Andheri
   - Contact: Mr. Mahesh Khatwani
   - Email: delmore.exp@delmore.in
   - Machine: INP-5060
   - Application: Food packaging (Deli containers)

7. Mirek Thermoformers Pvt. Ltd. - Bhiwandi
   - Machine: INP-5060/Servo
   - Application: Packaging

8. N.S. Industries - Gondpur
   - Contact: Mr. Vijay Sharma
   - Email: nsindustries2008@yahoo.com
   - Machine: AM/500x600/IR/Servo
   - Application: Blister packaging

OTHER NOTABLE CUSTOMERS:

9. MM Aqua Technologies Ltd. - Gurgaon
   - Contact: Ms. Dolly Roy
   - Email: dollyroy@mmaqua.in
   - Machine: VFM-6160
   - Application: Water purifier components

10. MK Daylight Solutions Pvt. Ltd. - Hyderabad
    - Contact: Mr. Imran Khan
    - Email: imran_khan2k3@yahoo.co.in
    - Machines: PF-1/1200x1200, Air Circulating Oven
    - Application: Lighting/skylights

11. Lighting Technologies India Pvt. Ltd. - Bangalore
    - Machine: SAM/750x1350/IR/S/PB/PLC
    - Application: Lighting fixtures

12. University of Petroleum and Energy Studies - Dehradun
    - Contact: Mr. Rishi Dixit
    - Email: rdixit@ddn.upes.ac.in
    - Machine: SAM/1000x1000/IR
    - Application: Educational/R&D

13. Indian School of Design & Innovation - Mumbai
    - Contact: Mr. Harish Parab
    - Machine: MF-600x750, Sheet Bending Machine
    - Application: Educational""",
        knowledge_type="client",
        source_file=SOURCE_FILE,
        entity="Indian Customer Details",
        summary="35+ Indian customers including VIP Industries (4 machines), Jaquar (sanitaryware), Saraswati Plastotech (construction), automotive (R.K. Manoj)",
        metadata={
            "top_customers": ["VIP Industries", "Jaquar", "Saraswati Plastotech", "R.K. Manoj"],
            "sectors": ["luggage", "sanitaryware", "construction", "automotive", "packaging", "lighting", "education"],
            "key_regions": ["Nashik", "Manesar", "Jammu", "Gurgaon", "Hyderabad", "Bangalore"]
        }
    ))

    # 3. International Customers
    items.append(KnowledgeItem(
        text="""Machinecraft International Customers (2014-2017):

EUROPE:

1. Polypack Kft - Hungary (2 machines)
   - Contact: Mr. Tamas Pajor
   - Email: polypack@t-online.hu
   - Web: www.polypack.hu
   - Machines:
     * PF-1/1500x1200 (2016)
     * INP-5065 with Pre-heating Oven (2017)
   - Status: Repeat customer, reference account

2. Pro-form Kft - Hungary
   - Contact: Mr. Helmajer Laszlo
   - Email: hl@pro-form.hu
   - Web: www.pro-form.hu
   - Machine: PF-1/1000x1000 (2015)

3. Anchor Media Display AB - Sweden
   - Contact: Mr. Christer Carlsson
   - Email: christer@anchormedia.s
   - Machine: PF-1/1500x1500 with Additional frames (2016)
   - Application: Signage/Display

4. First Pride Ltd T/A Ridat Company - United Kingdom (3 machines)
   - Contact: Mr. Dipak Sen Gupta
   - Email: dsg@ridat.com
   - Web: www.ridat.com
   - Machines:
     * 6040AVF (2015, 2016)
     * 2416AFCS (2015)
   - Note: Distributor/reseller relationship

MIDDLE EAST & AFRICA:

5. Buyline Industries Ltd. - Kenya
   - Contact: Mr. Sanyal Shah
   - Email: sanyal@buylineindustries.com
   - Web: www.buylineindustries.com
   - Equipment Package:
     * Vacuum Forming Machine
     * Vacuum Forming Mould
     * Cutting Die
     * Industrial Chiller
   - Note: Turn-key project

6. Precision Plastic Products Co. (LLC) - UAE
   - Location: United Arab Emirates
   - Equipment: Various

7. Sci Teck Co. - Iran
   - Contact: Mr. Babak Akbarian
   - Email: scitechco.iran@gmail.com
   - Machine: PF-2/2000x2000 (large format)
   - Note: Large machine export

INTERNATIONAL SALES INSIGHTS:

- Hungary emerged as strong European market (3 machines to 2 customers)
- UK relationship with Ridat for smaller machines (OEM/distributor)
- Sweden for industrial/signage applications
- Kenya shows turn-key project capability
- Iran demonstrates large machine export capability
- Mix of direct sales and distributor relationships""",
        knowledge_type="client",
        source_file=SOURCE_FILE,
        entity="International Customer Details",
        summary="12 international customers - Hungary (3 machines), UK (3 via Ridat), Sweden, Kenya (turn-key), Iran (large format)",
        metadata={
            "regions": ["Hungary", "Sweden", "UK", "Kenya", "UAE", "Iran"],
            "european_customers": ["Polypack", "Pro-form", "Anchor Media", "Ridat"],
            "repeat_customers": ["Polypack (2)", "Ridat (3)"],
            "turn_key_projects": ["Buyline Kenya"]
        }
    ))

    # 4. Machine Sales Analysis
    items.append(KnowledgeItem(
        text="""Machinecraft Machine Sales Analysis (2014-2017):

MACHINE TYPE BREAKDOWN:

1. PF-1 SERIES (Vacuum Forming) - 18 units
   Sizes sold:
   - PF-1/600x600 to PF-1/2000x2500
   - Most popular: 800x1000, 1000x1000, 1500x1500
   
   Notable sales:
   - PF-1/2000x2500 to Jaquar (bath tubs) - largest
   - PF-1/2000x2000 to Sci Teck Iran
   - PF-1/1550x2000 to Saraswati Plastotech
   - PF-1/1500x1500 to Anchor Media Sweden
   - PF-1/1500x1200 to Polypack Hungary
   - PF-1/1200x1200 to MK Daylight
   - Multiple PF-1/800x1000 to VIP Industries

2. INP SERIES (Inline Pressure Forming) - 5 units
   Models:
   - INP-5060: Delmore, S.D. International, Mirek
   - INP-5065: Polypack Hungary, Jaswant Enterprises
   
   Applications: High-volume packaging

3. AM SERIES (Continuous Vacuum Forming) - 3 units
   Models:
   - AM/500x600/IR/Servo
   
   Applications: Blister packaging, small parts

4. SAM SERIES (Semi-Automatic) - 4 units
   Models:
   - SAM/600x900, SAM/750x1350, SAM/1000x1000
   
   Applications: Signage, retail displays, education

5. ANCILLARY EQUIPMENT - 8+ units
   - Air Circulating Ovens: 3 units
   - Trimming Machines: 3 units
   - Hydro-Pneumatic Punching Press: 2 units
   - Sheet Extruder: 1 unit
   - Chillers: 1 unit

SALES BY YEAR:

FY 2016-17: Most active
- 17 customer entries
- Mix of India and exports
- Larger machines trending

FY 2015-16: 
- 16 customer entries
- VIP Industries repeat orders
- UK distributor active

FY 2014-15:
- 14 customer entries
- Foundation customers
- Educational institutions

PRICING INSIGHTS (from orders):
- Small machines (600-800mm): Entry level
- Medium machines (1000-1500mm): Core business
- Large machines (2000mm+): Premium/export
- Turn-key projects: Higher value
- Moulds/tooling: Significant add-on revenue""",
        knowledge_type="commercial",
        source_file=SOURCE_FILE,
        entity="Machine Sales Analysis",
        summary="54 machines sold: PF-1 (18), INP (5), AM (3), SAM (4), ancillary (8+); sizes from 600mm to 2500mm",
        metadata={
            "pf1_count": 18,
            "inp_count": 5,
            "am_count": 3,
            "sam_count": 4,
            "ancillary_count": 8,
            "largest_machine": "PF-1/2000x2500",
            "most_popular_size": "800x1000 to 1500x1500"
        }
    ))

    # 5. Industry Applications
    items.append(KnowledgeItem(
        text="""Machinecraft Customer Applications by Industry (2014-2017):

1. LUGGAGE & BAGS INDUSTRY:
   Customer: VIP Industries Ltd.
   - India's largest luggage manufacturer
   - 4 PF-1 machines over 3 years
   - Sizes: 800x1000, 960x660, 980x720
   - Application: Hard shell luggage
   - Key contact: Mr. Vishnudas Gujarathi
   - Repeat customer - strong reference

2. SANITARYWARE INDUSTRY:
   Customer: Jaquar & Co. Pvt. Ltd.
   - Premium bath fittings brand
   - PF-1/2000x2500 (one of largest sold)
   - Trimming machine, Heating oven
   - Application: Acrylic bath tubs
   - Key contact: Mr. Ashish Gupta

3. AUTOMOTIVE INDUSTRY:
   Customer: R.K. Manoj & Co.
   - Tier supplier for Maruti, Renault
   - Vacuum forming machine
   - Moulds: Toyota Etios, Renault KWID
   - Application: Engine covers, interior trims
   - Key contact: Mr. Manoj Jain

   Customer: Smartline Coach & Components
   - Bus/Coach manufacturer supplier
   - PF-1/1000x2200 with 6 moulds
   - Application: Bus interior components

4. PACKAGING INDUSTRY:
   Customers: Delmore, Mirek, N.S. Industries
   - INP-5060 series for high volume
   - AM series for blister packaging
   - Applications: Food containers, blisters
   
5. CONSTRUCTION & ARCHITECTURE:
   Customer: Saraswati Plastotech
   - Multiple orders over years
   - PF-1/1550x2000, Ovens, Trimmers
   - Application: Domes, skylights, profiles
   
   Customer: MK Daylight Solutions
   - PF-1/1200x1200
   - Application: Skylights, rooflights

6. SIGNAGE & DISPLAY:
   Customer: Anchor Media Display AB (Sweden)
   - PF-1/1500x1500
   - Application: 3D signage, displays
   
   Customer: Vijas Digital
   - SAM/600x900
   - Application: Retail displays

7. LIGHTING INDUSTRY:
   Customer: Lighting Technologies India
   - SAM/750x1350
   - Application: Lighting diffusers, fixtures

8. EDUCATION & R&D:
   Customer: UPES Dehradun
   - SAM/1000x1000/IR
   - Application: Teaching, prototyping
   
   Customer: ISDI Mumbai
   - MF-600x750, Sheet bending
   - Application: Design education

9. WATER TREATMENT:
   Customer: MM Aqua Technologies
   - VFM-6160
   - Application: Water purifier housings""",
        knowledge_type="application",
        source_file=SOURCE_FILE,
        entity="Customer Applications by Industry",
        summary="9 industry sectors: luggage (VIP), sanitaryware (Jaquar), automotive (R.K.Manoj), packaging, construction, signage, lighting, education, water treatment",
        metadata={
            "industries": ["luggage", "sanitaryware", "automotive", "packaging", "construction", "signage", "lighting", "education", "water_treatment"],
            "reference_customers": {
                "luggage": "VIP Industries",
                "sanitaryware": "Jaquar",
                "automotive": "R.K. Manoj",
                "construction": "Saraswati Plastotech",
                "signage": "Anchor Media Sweden"
            }
        }
    ))

    # 6. Contact Database
    items.append(KnowledgeItem(
        text="""Machinecraft Customer Contact Database (2014-2017):

KEY CONTACTS FOR REFERENCE/TESTIMONIALS:

INDIA - MAJOR ACCOUNTS:

1. VIP Industries Ltd. (Luggage)
   - Mr. Vishnudas Gujarathi
   - vishnudas.gujarathi@vipbags.com
   - www.vipbags.com
   - Nashik, India
   - 4 machines purchased

2. Jaquar & Co. Pvt. Ltd. (Sanitaryware)
   - Mr. Ashish Gupta
   - agupta@jaquar.com
   - Manesar, India
   - Large format machine

3. Saraswati Plastotech (Construction)
   - Mr. Gopinath
   - gopinath@saraswati-group.com
   - Jammu, India
   - Multiple orders

4. R.K. Manoj & Co. (Automotive)
   - Mr. Manoj Jain
   - manoj@automat.in
   - Sonepat, India
   - OEM supplier

5. MM Aqua Technologies (Water)
   - Ms. Dolly Roy
   - dollyroy@mmaqua.in
   - Gurgaon, India

6. MK Daylight Solutions (Skylights)
   - Mr. Imran Khan
   - imran_khan2k3@yahoo.co.in
   - Hyderabad, India

7. Delmore Trading (Packaging)
   - Mr. Mahesh Khatwani
   - delmore.exp@delmore.in
   - Andheri, India

INTERNATIONAL ACCOUNTS:

8. Polypack Kft (Hungary)
   - Mr. Tamas Pajor
   - polypack@t-online.hu
   - www.polypack.hu
   - 2 machines, repeat customer

9. Pro-form Kft (Hungary)
   - Mr. Helmajer Laszlo
   - hl@pro-form.hu
   - www.pro-form.hu

10. Anchor Media Display AB (Sweden)
    - Mr. Christer Carlsson
    - christer@anchormedia.s
    - Signage industry

11. First Pride / Ridat Company (UK)
    - Mr. Dipak Sen Gupta
    - dsg@ridat.com
    - www.ridat.com
    - Distributor relationship

12. Buyline Industries (Kenya)
    - Mr. Sanyal Shah
    - sanyal@buylineindustries.com
    - www.buylineindustries.com
    - Turn-key project

13. Sci Teck Co. (Iran)
    - Mr. Babak Akbarian
    - scitechco.iran@gmail.com
    - Large format export""",
        knowledge_type="client",
        source_file=SOURCE_FILE,
        entity="Customer Contact Database",
        summary="13 key customer contacts with emails - India (VIP, Jaquar, Saraswati, R.K.Manoj) and International (Polypack, Pro-form, Ridat, Buyline)",
        metadata={
            "contact_count": 13,
            "india_contacts": 7,
            "international_contacts": 6,
            "repeat_customers": ["VIP Industries", "Polypack", "Ridat", "Saraswati"]
        }
    ))

    return items


def main():
    """Main ingestion function."""
    print("=" * 60)
    print("Machinecraft Customer List Ingestion")
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
