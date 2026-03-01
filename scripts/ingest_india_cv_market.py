#!/usr/bin/env python3
"""
Ingest India CV Market Development - Contacts & Applications

18 key contacts from India's Commercial Vehicle industry (OEMs, cabin makers, bus OEMs)
Combined with vacuum forming applications guide for CV parts.

Sources: 
- India - CV Market Dev Links.xlsx
- Applications using VF Machinecraft PPT.pdf
"""

import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Import directly from the module file to avoid __init__.py issues
import importlib.util
spec = importlib.util.spec_from_file_location(
    "knowledge_ingestor",
    os.path.join(project_root, "openclaw/agents/ira/src/brain/knowledge_ingestor.py")
)
knowledge_ingestor_module = importlib.util.module_from_spec(spec)
sys.modules["knowledge_ingestor"] = knowledge_ingestor_module
spec.loader.exec_module(knowledge_ingestor_module)

KnowledgeIngestor = knowledge_ingestor_module.KnowledgeIngestor
KnowledgeItem = knowledge_ingestor_module.KnowledgeItem

SOURCE_FILE = "India - CV Market Dev Links.xlsx + Applications using VF Machinecraft PPT.pdf"


def create_knowledge_items() -> list[KnowledgeItem]:
    """Create structured knowledge items from CV market data."""
    items = []

    # 1. CV Market Overview
    items.append(KnowledgeItem(
        text="""India Commercial Vehicle Market - Development Overview

TARGET MARKET: India CV OEMs, Tractor OEMs, Bus OEMs, eBus OEMs, Cabin Makers
OBJECTIVE: Influence development of more parts using vacuum forming process
TOTAL CONTACTS: 18 key decision makers

CV INDUSTRY SEGMENTS:
1. CV OEMs: Daimler, Mahindra, Tata, JCB, John Deere
2. Tractor OEMs: Sonalika (ITL), Mahindra Farm Equipment
3. Bus OEMs: JBM Auto, JCBL Limited
4. eBus OEMs: Olectra-BYD Greentech
5. Cabin Makers: Fritzmeier Motherson

KEY OPPORTUNITY:
- Indian CV industry shifting from FRP/metal to thermoplastics
- Weight reduction critical for eBus and EV platforms
- Cost savings vs injection molding for low-medium volumes
- Machinecraft already supplies to Alphafoam (Sonalika supplier) with 12 machines

EXISTING MACHINECRAFT CV CUSTOMERS:
- Alphafoam Pune: 12 machines, supplies Sonalika tractors
- Maini Composites Bangalore: PF1 series + 5-axis router, supplies Mahindra Treo
- BI Composites UK (Linecross): 2.5x3m machine, supplies JCB UK""",
        knowledge_type="market_intelligence",
        source_file=SOURCE_FILE,
        entity="India CV Market Overview",
        summary="India CV market: 18 contacts, 5 segments (CV/Tractor/Bus/eBus/Cabin), thermoplastic shift opportunity",
        metadata={
            "topic": "cv_market_overview",
            "total_contacts": 18,
            "market": "India"
        }
    ))

    # 2. OEM Contacts - Tier 1 (Major CV/Tractor)
    items.append(KnowledgeItem(
        text="""India CV Market - Tier 1 OEM Contacts

DAIMLER INDIA COMMERCIAL VEHICLES:
- Contact: Vasantha Kumar
- Position: Manager
- Location: Oragadam
- LinkedIn: linkedin.com/in/vasantha-kumar-218bb14b/
- Note: German parent, high quality standards

EICHER TRUCKS AND BUSES:
- Contact: Pradeep Mishra, CEC
- Position: Senior Vice President Purchasing
- LinkedIn: linkedin.com/in/pradeep-mishra-cec-757a585/
- Note: Key purchasing decision maker

MAHINDRA AND MAHINDRA (Multiple contacts):
1. Tarun Agarwal
   - Position: Global Business Development Head - Farm Machinery
   - LinkedIn: linkedin.com/in/tarun-agarwal-553543aa/
   - Note: Tractor/Farm equipment focus

2. Nilay Dembi
   - Position: Principal Designer
   - LinkedIn: linkedin.com/in/nilaydembi/
   - Note: Design influence for new parts

3. Rohit Bhatia
   - Position: Vice President
   - LinkedIn: linkedin.com/in/rohit-bhatia-450958147/
   - Note: Senior decision maker

SONALIKA (International Tractors Limited):
- Contact: Akshay Sangwan
- Position: Director - Development & Commercial (Sonalika), Executive Director (Sonalika Industries)
- LinkedIn: linkedin.com/in/akshay-sangwan-82370a6/
- Note: Already buying from Alphafoam (Machinecraft customer)""",
        knowledge_type="market_intelligence",
        source_file=SOURCE_FILE,
        entity="CV OEM Contacts Tier 1",
        summary="Tier 1: Daimler (Vasantha), Eicher (Pradeep SVP), Mahindra (3), Sonalika (Akshay Director)",
        metadata={
            "topic": "oem_contacts_tier1",
            "segment": ["CV OEM", "Tractor OEM"],
            "contact_count": 6
        }
    ))

    # 3. OEM Contacts - Construction & Agriculture
    items.append(KnowledgeItem(
        text="""India CV Market - Construction & Agriculture OEM Contacts

JCB INDIA (3 contacts):
1. Ashok Asodariya
   - Position: Business Head
   - LinkedIn: linkedin.com/in/ashok-asodariya-b0617a32/
   - Note: Key decision maker

2. Umesh Puri
   - Position: DM
   - LinkedIn: linkedin.com/in/umesh-puri-5120621b0/

3. Rakesh Kumar
   - Position: GM - Procurement, PPC & SCM
   - LinkedIn: linkedin.com/in/rakesh-kumar-33755b25/
   - Note: Procurement decision maker

JOHN DEERE INDIA (2 contacts):
1. Biswaranjan Dash
   - Position: DGM Global Sourcing
   - LinkedIn: linkedin.com/in/biswaranjan-dash-b2810315/
   - Note: Global sourcing authority

2. Mukesh Sinha
   - Position: Lead Engineer
   - LinkedIn: linkedin.com/in/mukesh-sinha-7395bab/
   - Note: Technical influence

JCB PARTS OPPORTUNITY:
- Engine Hoods (currently made by BI Composites UK on Machinecraft 2.5x3m)
- Fenders / Mud Guards
- Roofs
- Note: Can replicate UK success in India""",
        knowledge_type="market_intelligence",
        source_file=SOURCE_FILE,
        entity="Construction Agriculture OEM Contacts",
        summary="Construction/Agri: JCB (3 contacts incl GM Procurement), John Deere (2 incl DGM Sourcing)",
        metadata={
            "topic": "construction_agri_contacts",
            "segment": "CV OEM",
            "contact_count": 5
        }
    ))

    # 4. Bus & eBus OEM Contacts
    items.append(KnowledgeItem(
        text="""India CV Market - Bus & eBus OEM Contacts

JBM AUTO LIMITED:
- Contact: Shyam Sunder Parashar
- Position: Sourcing Lead in Electrical & Electronics
- LinkedIn: linkedin.com/in/shyamsunder-parashar-60a30723/
- Note: E&E sourcing, potential for interior parts

JCBL LIMITED:
- Contact: Sanjeev Babbar
- Position: CEO
- LinkedIn: linkedin.com/in/sanjeev-babbar-00466a11a/
- Note: Top decision maker

OLECTRA-BYD GREENTECH (eBus - 2 contacts):
1. Sreedhar Reddy
   - Position: Head of R&D
   - LinkedIn: linkedin.com/in/sreedhar-reddy-41524811/
   - Note: R&D influence for new materials

2. Snehasish Dutta
   - Position: Zonal Head - South and East
   - LinkedIn: linkedin.com/in/snehasish-dutta-37223259/
   - Note: Regional business development

PINNACLE INDUSTRIES LTD:
- Contact: Sudhir Mehta
- Position: Chairman & Managing Director
- LinkedIn: linkedin.com/in/sudhir-mehta-79a2839/
- Note: Top decision maker, also in PlastIndia leads
- Cross-ref: Dhiraj Suryawanshi (PlastIndia 2023)

EVAGE VENTURES (EV Startup):
- Contact: Inderveer Singh
- Position: Founder CEO
- LinkedIn: linkedin.com/in/inderveer-singh-7767b67/
- Note: EV startup, lightweight parts critical

FRITZMEIER MOTHERSON CABIN ENGINEERING:
- Contact: Giridhar Kancheepuram
- Position: Head - Programme Management
- LinkedIn: linkedin.com/in/giridhar-kancheepuram-46119643/
- Note: Cabin interiors specialist""",
        knowledge_type="market_intelligence",
        source_file=SOURCE_FILE,
        entity="Bus eBus OEM Contacts",
        summary="Bus/eBus: JBM, JCBL (CEO), Olectra (2, R&D Head), Pinnacle (CMD), Evage, Fritzmeier Motherson",
        metadata={
            "topic": "bus_ebus_contacts",
            "segment": ["Bus OEM", "eBus OEM", "Cabin Maker"],
            "contact_count": 8
        }
    ))

    # 5. CV Parts Applications - Interiors
    items.append(KnowledgeItem(
        text="""CV Vacuum Forming Applications - Interior Parts

INSTRUMENT PANELS (IP):
- Material: PP (to avoid rattling sound)
- Sheet: Pre-textured available
- Process: Vacuum Forming
- Examples: Mahindra Furio, Mahindra Cruzio, Olectra eBus
- Note: High volume opportunity

DOOR PANELS (DP):
- Material: PP or ABS with texture
- Process: Vacuum Forming
- Examples: LCV Middle Part, Mahindra Blazo
- Note: Multiple panels per vehicle

A-PILLARS & B-PILLARS:
- Material: ABS or PP
- Process: Vacuum Forming + CNC trimming
- Examples: Visible in Mahindra CV range
- Note: Manual cutting can be replaced with CNC router

SIDE TRIMS:
- Material: PP (anti-rattle)
- Sheet: Pre-textured
- Process: Vacuum Forming
- Location: Near door panels

ARM-RESTS:
- Material: PP
- Sheet: Pre-textured
- Process: Vacuum Forming

TOP GLOVE BOX:
- Material: PP with textured sheet
- Process: Vacuum Forming
- Examples: Mahindra Furio interiors

BUS INTERIORS:
- Parts: IP, Seat Backs, Pillars
- Material: ABS or PP (pre-textured)
- Process: Vacuum Forming
- Examples: Mahindra Cruzio, Olectra eBus
- Note: FR rated materials for metro/trains""",
        knowledge_type="application",
        source_file=SOURCE_FILE,
        entity="CV Interior Parts",
        summary="CV interiors: IP, DP, Pillars, Trims, Arm-rests - PP/ABS, pre-textured sheets, vacuum forming",
        metadata={
            "topic": "cv_interior_applications",
            "parts": ["IP", "DP", "Pillars", "Trims", "Arm-rests"],
            "materials": ["PP", "ABS"]
        }
    ))

    # 6. CV Parts Applications - Exteriors
    items.append(KnowledgeItem(
        text="""CV Vacuum Forming Applications - Exterior Parts

ENGINE HOODS:
- Material: ABS or HDPE
- Process: Vacuum Forming
- Examples: JCB UK (BI Composites on Machinecraft 2.5x3m)
- Note: Large format parts

FENDERS / MUD GUARDS:
- Material: HDPE thermoplastic
- Process: Vacuum Forming
- Examples: JCB, Mahindra Treo, Mahindra Blazo X
- Size: Various, often large format

ROOFS:
- Material: ABS, HDPE
- Process: Vacuum Forming
- Examples: JCB construction equipment
- Note: Large format machine required (2.5x3m+)

FRONT GRILL AREA PARTS:
- Material: ABS (matte) or ABS/PMMA (glossy)
- Process: Vacuum Forming + CNC
- Examples: Mahindra Blazo X, Tata Signa

WIPER HOUSING:
- Material: ABS
- Process: Vacuum Forming

TOP CANOPY (3-wheelers):
- Material: HDPE thermoplastic
- Process: Vacuum Forming
- Examples: Mahindra Treo eRick (by Maini Composites)

EXTERIOR GLOSSY PARTS:
- Material: ABS/PMMA high gloss with UV protection
- Process: Vacuum Forming
- Examples: Mahindra Furio, Tata Signa (blue parts)
- Note: Can replace FRP for weight and cost savings

AC COOLER CASINGS:
- Material: ABS with UV protection
- Process: Vacuum Forming
- Reference: ThermoKing, Valeo (Motherson) makes globally""",
        knowledge_type="application",
        source_file=SOURCE_FILE,
        entity="CV Exterior Parts",
        summary="CV exteriors: Hoods, Fenders, Roofs, Grills, Canopy - HDPE/ABS/PMMA, large format VF",
        metadata={
            "topic": "cv_exterior_applications",
            "parts": ["Hoods", "Fenders", "Roofs", "Grills", "Canopy", "AC Casings"],
            "materials": ["HDPE", "ABS", "ABS/PMMA"]
        }
    ))

    # 7. Mahindra Vehicle Specific Applications
    items.append(KnowledgeItem(
        text="""Mahindra Vehicles - Vacuum Forming Applications Analysis

MAHINDRA TREO (eRick):
- Top Canopy: HDPE thermoplastic, VF
- Side Trims: ABS, VF
- Mudguards: ABS, VF
- Inside IP: ABS, VF
- Supplier: Maini Composites Bangalore
- Machines: Machinecraft PF1 + 5-axis router

MAHINDRA FURIO (LCV):
- Exterior Glossy: ABS/PMMA, VF + CNC
- Exterior Black: ABS/HDPE, VF
- Interior (Glove box, DP): PP textured, VF

MAHINDRA BLAZO X (HCV):
- Front Grill Parts: ABS, VF
- Wiper Housing: ABS, VF
- Mud Guards: ABS, VF
- Blue Glossy: Currently FRP, can convert to ABS/PMMA VF

MAHINDRA CRUZIO (Bus):
- Fire Exit Casing: ABS, VF
- Bus Interiors: ABS, VF
- IP: ABS, VF

MAHINDRA MESMA (EV Platform):
- Battery Casing: Special material from PROPEX Germany
- Process: Thermoforming
- Note: Lightweight critical for EV range

MAHINDRA LCV (General):
- IP: PP, VF
- DP: PP, VF
- A-Pillar: PP textured, VF (currently manual cut)

MACHINE RECOMMENDATION:
- Small parts (Treo): PF1-C series
- Medium parts (Furio/Blazo): PF1-X series
- Large parts (Bus interiors): PF1-X-2020 or larger""",
        knowledge_type="application",
        source_file=SOURCE_FILE,
        entity="Mahindra VF Applications",
        summary="Mahindra: Treo (Maini), Furio, Blazo X, Cruzio, Mesma EV - multiple VF parts per vehicle",
        metadata={
            "topic": "mahindra_applications",
            "vehicles": ["Treo", "Furio", "Blazo X", "Cruzio", "Mesma"],
            "existing_supplier": "Maini Composites"
        }
    ))

    # 8. Sales Strategy for CV Market
    items.append(KnowledgeItem(
        text="""CV Market Development - Sales Strategy

TARGET APPROACH BY SEGMENT:

CV OEMs (Daimler, Eicher, Mahindra, Tata):
- Lead with: Cost comparison vs injection molding
- Highlight: Tooling cost 10-20% of IM
- Machine: PF1-X series for flexibility

Tractor OEMs (Sonalika, John Deere, Mahindra Farm):
- Lead with: Alphafoam success story (12 machines)
- Highlight: Cabin interior parts opportunity
- Reference: BI Composites UK for JCB

Bus/eBus OEMs (JBM, JCBL, Olectra, Pinnacle):
- Lead with: Weight reduction for eBus range
- Highlight: FR rated materials available
- Machine: PF1-X large format

Construction (JCB, John Deere):
- Lead with: UK success story (BI Composites)
- Parts: Hoods, Fenders, Roofs
- Machine: PF1-X-2020 or 2.5x3m

CONVERSION OPPORTUNITIES:
- FRP parts → ABS/PMMA VF (weight, consistency, cycle time)
- Injection molding → VF (lower tooling cost for medium volumes)
- Metal → HDPE VF (weight reduction, corrosion resistance)

KEY TALKING POINTS:
1. Tooling cost: 10-20% of injection molding
2. Lead time: 4-6 weeks vs 12-16 weeks for IM tools
3. Design flexibility: Easy modifications
4. Weight: 30-50% lighter than FRP
5. Consistency: Better than FRP hand layup
6. Local support: Machinecraft service in India

REFERENCE CUSTOMERS TO MENTION:
- Alphafoam Pune (Sonalika): 12 machines
- Maini Composites (Mahindra Treo): PF1 + 5-axis
- BI Composites UK (JCB): 2.5x3m machine""",
        knowledge_type="commercial",
        source_file=SOURCE_FILE,
        entity="CV Sales Strategy",
        summary="CV strategy: Alphafoam/Maini/BI success stories, FRP→VF conversion, tooling cost advantage",
        metadata={
            "topic": "cv_sales_strategy",
            "reference_customers": ["Alphafoam", "Maini Composites", "BI Composites"]
        }
    ))

    return items


def main():
    """Main ingestion function."""
    print("=" * 60)
    print("India CV Market Development Ingestion")
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
