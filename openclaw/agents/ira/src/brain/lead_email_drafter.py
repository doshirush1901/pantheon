#!/usr/bin/env python3
"""
LEAD EMAIL DRAFTER
==================

Generates personalized follow-up emails for Plastindia exhibition leads.

Features:
- Parses structured lead data from exhibition PDF
- Generates personalized emails based on lead category and requirements
- Uses Ira's email polish system for brand voice
- Supports batch generation and on-demand Telegram queries

Usage:
    # Batch mode - generate all drafts
    python lead_email_drafter.py --batch --output drafts.csv
    
    # Single lead lookup
    python lead_email_drafter.py --lead "Dhanya Plastics"
    
    # Interactive mode
    python lead_email_drafter.py --interactive

Categories:
    A: High-Value Machine Sales
    B: Strategic OEM/Automotive
    C: Sheet Supply/Extrusion
    D: Tooling Prospects
    E: Raw Material Partners
    F: General Industrial
"""

import csv
import json
import os
import re
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum

# Path setup
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent.parent
BRAIN_DIR = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(BRAIN_DIR))

# Import email polish if available
try:
    from email_polish import EmailPolisher, polish_email
    EMAIL_POLISH_AVAILABLE = True
except ImportError:
    EMAIL_POLISH_AVAILABLE = False

# Import OpenAI for generation
try:
    from config import OPENAI_API_KEY
except ImportError:
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")


# =============================================================================
# LEAD DATA STRUCTURES
# =============================================================================

class LeadCategory(Enum):
    """Lead categories from Plastindia analysis."""
    A_MACHINE_SALES = "A"
    B_OEM_AUTOMOTIVE = "B"
    C_SHEET_SUPPLY = "C"
    D_TOOLING = "D"
    E_RAW_MATERIAL = "E"
    F_GENERAL_INDUSTRIAL = "F"
    G_VENDORS = "G"
    H_LOW_PRIORITY = "H"


@dataclass
class Lead:
    """Structured lead data."""
    lead_id: str
    company: str
    category: LeadCategory
    contacts: List[Dict[str, str]] = field(default_factory=list)  # [{name, role, phone, email}]
    location: str = ""
    business: str = ""
    requirement: str = ""
    remarks: List[str] = field(default_factory=list)
    analysis: str = ""
    revenue_potential: str = ""
    priority_action: str = ""
    owner: str = ""
    star_rating: int = 0
    website: str = ""
    
    @property
    def primary_contact(self) -> Dict[str, str]:
        """Get primary contact (first one)."""
        return self.contacts[0] if self.contacts else {}
    
    @property
    def primary_email(self) -> str:
        """Get primary email address."""
        for contact in self.contacts:
            if contact.get("email"):
                return contact["email"]
        return ""
    
    @property
    def primary_name(self) -> str:
        """Get primary contact name."""
        return self.primary_contact.get("name", "Sir/Madam")
    
    @property
    def all_phones(self) -> List[str]:
        """Get all phone numbers."""
        phones = []
        for contact in self.contacts:
            if contact.get("phone"):
                phones.append(contact["phone"])
        return phones


# =============================================================================
# PLASTINDIA LEADS DATABASE
# =============================================================================

PLASTINDIA_LEADS: List[Lead] = [
    # Category A: High-Value Machine Sales
    Lead(
        lead_id="A1",
        company="Engineering Plastic Industries",
        category=LeadCategory.A_MACHINE_SALES,
        contacts=[
            {"name": "Sanjay Gothi", "role": "Chief Executive", "phone": "+91 413 2271115", "email": "sanjay@enggplastic.in"},
            {"name": "Neetu Singh Mehta", "role": "COO", "phone": "+91 9976640044", "email": "neetusm@enggplastic.in"}
        ],
        location="Pondicherry",
        requirement="Sheet Line + Inline + Grinder for MAP (Modified Atmosphere Packaging)",
        analysis="Complete turnkey plant inquiry. Serious scale-up project.",
        revenue_potential="₹2–6 Cr (full line)",
        priority_action="Immediate technical call. Understand output width, material type (PET/PP/HIPS), grinder integration specs",
        owner="Machinecraft + Sheet Division",
        star_rating=6,
        website="www.enggplastic.in"
    ),
    Lead(
        lead_id="A2",
        company="Dhanya Plastics & Foams Pvt Ltd",
        category=LeadCategory.A_MACHINE_SALES,
        contacts=[
            {"name": "Manjunath V Hegde", "role": "Managing Director", "phone": "+91 98454 27172", "email": ""}
        ],
        location="Bangalore",
        business="PU Foam Sheet & Rolls, Self Adhesive Tapes",
        remarks=["Has 10–12 vacuum forming machines", "For bus interior parts (Red, Blue etc)", "Knows Navi", "NEEDS 2 MACHINES IMMEDIATELY", "Was in Ghana earlier, has factory in Arabini", "Now started forming work - 1 vacuum", "Dimensions: 800 x 850"],
        analysis="Gold. Active thermoformer with immediate machine need. Heavy industrial application (bus interiors = FR grades, ABS)",
        revenue_potential="₹1.5–3 Cr (2 machines)",
        priority_action="Call within 24 hours. Heavy gauge vacuum + FR ABS sheet + tooling combo",
        owner="Machinecraft Direct",
        star_rating=6
    ),
    Lead(
        lead_id="A3",
        company="SVP Polymers",
        category=LeadCategory.A_MACHINE_SALES,
        contacts=[
            {"name": "Siddharth Kiroti", "role": "", "phone": "7899227422", "email": ""}
        ],
        requirement="Thermoforming machines for manufacturing automotive parts",
        analysis="Automotive thermoforming = heavy gauge, likely ABS/PP/FR, interior trims, wheel arch liners, covers",
        revenue_potential="₹1–5 Cr (automotive line)",
        priority_action="Understand part size, thickness, volume, automotive certification requirements",
        owner="Machinecraft",
        star_rating=6
    ),
    Lead(
        lead_id="A4",
        company="Gourav (Cup Machine Lead)",
        category=LeadCategory.A_MACHINE_SALES,
        contacts=[
            {"name": "Gourav", "role": "", "phone": "9773503434", "email": ""}
        ],
        requirement="Cup machine (Sheet line) + Thermoforming machine",
        analysis="Disposable cup thermoforming + extrusion line. Full setup inquiry.",
        revenue_potential="₹1–3 Cr (cup line + sheet line)",
        priority_action="Call within 24 hours",
        owner="Machinecraft + Sheet Division",
        star_rating=5
    ),
    Lead(
        lead_id="A5",
        company="VISU Poly Products Pvt Ltd",
        category=LeadCategory.A_MACHINE_SALES,
        contacts=[
            {"name": "Sunil Das", "role": "", "phone": "", "email": ""}
        ],
        location="Bangalore",
        remarks=["PFI-A 1000 x 1000", "HAS OUR MACHINE 20 YEARS AGO"],
        analysis="Classic replacement cycle. 20-year-old machine needs upgrade.",
        revenue_potential="₹60L–1.5 Cr (replacement + upgrade)",
        priority_action="Pitch energy efficient heaters, PLC upgrade, Servo upgrade, Pressure forming version",
        owner="Machinecraft",
        star_rating=5
    ),
    Lead(
        lead_id="A6",
        company="Kosmic Kris Industries LLP",
        category=LeadCategory.A_MACHINE_SALES,
        contacts=[
            {"name": "Karan Verma", "role": "", "phone": "", "email": ""}
        ],
        location="Greater Noida",
        business="Injection moulding & assembly",
        remarks=["AM machine handle heavy – Give quote of height of roll. Details on WhatsApp"],
        analysis="Heavy duty thermoforming inquiry. Concerned about sheet roll handling capacity.",
        revenue_potential="₹70L–1.8 Cr",
        priority_action="Send video of heavy gauge machine, roll loading capacity, max sheet weight, forming depth",
        owner="Machinecraft",
        star_rating=5
    ),
    Lead(
        lead_id="A7",
        company="Nataraj U B (Saksatek)",
        category=LeadCategory.A_MACHINE_SALES,
        contacts=[
            {"name": "Nataraj U B", "role": "Director – Operations", "phone": "", "email": "nataraj@saksatek.com"}
        ],
        location="SIDCO Industrial Estate, Ambattur",
        remarks=["Heat pressure forming for ESD trays", "1.5–2 mm thickness", "15–20 AM machines"],
        analysis="VERY BIG. Already has 15–20 machines. ESD tray manufacturer (electronics segment). Needs pressure forming upgrade.",
        revenue_potential="₹1–3 Cr per machine, multiple units possible",
        priority_action="Position high-end pressure forming, ESD grade ABS sheet supply, tooling development, long-term partnership",
        owner="Machinecraft + Sheet + Tooling",
        star_rating=6
    ),
    Lead(
        lead_id="A8",
        company="Vintec Industries",
        category=LeadCategory.A_MACHINE_SALES,
        contacts=[
            {"name": "Manoj S", "role": "Quality/Plant Manager", "phone": "+91 9538888527", "email": "quality@vintecindustries.com"}
        ],
        location="Bengaluru",
        business="Manufacturers of Vacuumforming & Thermoforming Products",
        remarks=["Pressure AM"],
        analysis="Already thermoformers, want pressure forming upgrade",
        revenue_potential="₹1–3 Cr",
        priority_action="Push pressure forming superiority vs vacuum, automotive-grade finish, PC/ABS capability",
        owner="Machinecraft",
        star_rating=5,
        website="www.vintecindustries.com"
    ),
    Lead(
        lead_id="A9",
        company="AT Group",
        category=LeadCategory.A_MACHINE_SALES,
        contacts=[
            {"name": "Mr. Amardeep", "role": "", "phone": "98179 19911", "email": "opr.bawal@aggroup.com"}
        ],
        requirement="1000 x 1000 mm AM machine",
        analysis="Mid-size thermoforming machine, clear specifications",
        revenue_potential="₹35–70L",
        priority_action="Send machine video, technical sheet, budgetary price, lead time",
        owner="Machinecraft",
        star_rating=5
    ),
    Lead(
        lead_id="A10",
        company="Vacuum Pack",
        category=LeadCategory.A_MACHINE_SALES,
        contacts=[
            {"name": "Parth Patel", "role": "", "phone": "7620702202", "email": "vacuumpack01@gmail.com"}
        ],
        location="Chhatral",
        remarks=["6 machines – vacuum tech", "Needs AM with hydraulic press", "NCL PET sheet", "1 & 1.2mm – 40 ton press", "Avg moulds are 150 BT"],
        analysis="GOLD. Serious industrial thermoformer with 6 existing machines. Wants upgrade to automatic + hydraulic press. Large molds (150 BT).",
        revenue_potential="₹80L–1.5 Cr (machine + press + tooling)",
        priority_action="Sell AM + Pressure machine, sell PET sheet, sell aluminum molds",
        owner="Machinecraft + Sheet + Tooling",
        star_rating=6
    ),
    Lead(
        lead_id="A11",
        company="Advance Packaging",
        category=LeadCategory.A_MACHINE_SALES,
        contacts=[
            {"name": "Divyansh Rastogi", "role": "", "phone": "+91 7705011901", "email": "advancepackaging.info@gmail.com"}
        ],
        location="Kanpur",
        business="Protective Packaging Products (Air Bubble Bags, Customized Films, VCI Bags)",
        remarks=["Send video of AM machine"],
        analysis="Direct machine inquiry. Warm lead (asked for video = interest confirmed)",
        revenue_potential="₹60L–1.5 Cr",
        priority_action="Send video within 24 hours",
        owner="Machinecraft",
        star_rating=5
    ),
    Lead(
        lead_id="A12",
        company="Mystical Propack Pvt Ltd",
        category=LeadCategory.A_MACHINE_SALES,
        contacts=[
            {"name": "Vijay Parchure", "role": "Business Head", "phone": "+91 77100 10911", "email": "vmparchure@mysticalgroup.in"}
        ],
        location="Thane West / Chiplun, Ratnagiri",
        business="Propack + BRGS certified, Food/industrial packaging",
        analysis="Serious packaging player with certifications. Direct thermoforming relevance.",
        revenue_potential="₹80L–2 Cr (packaging line)",
        priority_action="Position as packaging thermoforming upgrade, sheet supply, tooling combo",
        owner="Machinecraft + Sheet + Tooling",
        star_rating=6
    ),
    Lead(
        lead_id="A13",
        company="Abhishek Innovative Concepts Pvt Ltd",
        category=LeadCategory.A_MACHINE_SALES,
        contacts=[
            {"name": "Mayur Sahane", "role": "General Manager", "phone": "+91 93707 16362", "email": "production@abhishekgroup.net.in"}
        ],
        location="MIDC Waluj, Aurangabad",
        business="House of Packaging Solutions (ISO 9001:2015)",
        analysis="Serious industrial packaging unit in MIDC Waluj. Likely upgrade/expansion candidate.",
        revenue_potential="₹60L–1.8 Cr",
        priority_action="Understand current capacity, pitch automation upgrade",
        owner="Machinecraft",
        star_rating=5,
        website="www.abhishekgroup.net.in"
    ),
    Lead(
        lead_id="A14",
        company="Hindustan Pack-Plast Industries",
        category=LeadCategory.A_MACHINE_SALES,
        contacts=[
            {"name": "Jignesh Parekh", "role": "", "phone": "+91 92272 08586", "email": ""},
            {"name": "Tarun Parekh", "role": "", "phone": "+91 94264 12002", "email": ""}
        ],
        business="Vacuum formed packages, Blister packing, Plastic products",
        analysis="Already doing vacuum forming. Direct upgrade opportunity.",
        revenue_potential="₹50L–1.5 Cr",
        priority_action="Pitch automatic line upgrade, pressure forming, high-speed blister machine",
        owner="Machinecraft + Sheet + Tooling",
        star_rating=5,
        website="www.hppindia.com"
    ),
    Lead(
        lead_id="A15",
        company="Sri Kanagalakshmi Industries",
        category=LeadCategory.A_MACHINE_SALES,
        contacts=[
            {"name": "Jayaprakash M", "role": "Partner", "phone": "+91 98412 87842", "email": "kanagind@gmail.com"}
        ],
        location="Chennai",
        business="Blister trays, Thermoforming trays, Automobile component packaging, ESD trays, Thick sheet forming, PVC boxes & pouches",
        analysis="Core thermoforming company. Thick sheet, automotive packaging, blister. Direct Machinecraft opportunity.",
        revenue_potential="₹70L–2 Cr",
        priority_action="Upgrade machines, add pressure forming, add automation",
        owner="Machinecraft + Sheet + Tooling",
        star_rating=5
    ),
    Lead(
        lead_id="A16",
        company="Formoplast",
        category=LeadCategory.A_MACHINE_SALES,
        contacts=[
            {"name": "Ronil Shah", "role": "", "phone": "", "email": ""}
        ],
        location="Indore",
        remarks=["AM machines chain"],
        analysis="Already running AM machines, looking to expand chain-type machine",
        revenue_potential="₹80L–2 Cr",
        priority_action="Position fully automatic chain-type heavy gauge machine",
        owner="Machinecraft",
        star_rating=5
    ),
    Lead(
        lead_id="A17",
        company="Blount Senani",
        category=LeadCategory.A_MACHINE_SALES,
        contacts=[
            {"name": "", "role": "", "phone": "8109780666", "email": "bsnaders.senani@gmail.com"}
        ],
        requirement="CUP machines",
        analysis="Disposable cup manufacturer inquiry",
        revenue_potential="₹50L–1.2 Cr",
        priority_action="Thin gauge cup forming machine pitch",
        owner="Machinecraft",
        star_rating=4
    ),
    Lead(
        lead_id="A18",
        company="Khandelwal Plastics",
        category=LeadCategory.A_MACHINE_SALES,
        contacts=[
            {"name": "Nitesh Khandelwal", "role": "MD", "phone": "", "email": ""}
        ],
        location="Raipur",
        requirement="AM seedling tray",
        analysis="GroFlo Opportunity. Direct agri thermoforming buyer.",
        revenue_potential="₹40L–1 Cr",
        priority_action="Position GroFlo partnership + machine sale",
        owner="Machinecraft + GroFlo",
        star_rating=4,
        website="www.khandelwalplastic.com"
    ),
    Lead(
        lead_id="A19",
        company="Sandeep Giridhar",
        category=LeadCategory.A_MACHINE_SALES,
        contacts=[
            {"name": "Sandeep Giridhar", "role": "", "phone": "912540000", "email": ""}
        ],
        location="Sonipat",
        requirement="AM + pressure – disposable containers for Namkeen",
        analysis="Food packaging lead. Pressure forming for snack packaging.",
        revenue_potential="₹50L–1.5 Cr",
        priority_action="Food-grade material capability pitch, food safety certifications",
        owner="Machinecraft",
        star_rating=4
    ),
    Lead(
        lead_id="A20",
        company="Ashapura Packaging",
        category=LeadCategory.A_MACHINE_SALES,
        contacts=[],
        location="Vapi",
        requirement="Small size AM machine",
        analysis="Entry level machine buyer",
        revenue_potential="₹18–30L",
        priority_action="Entry-level machine pitch, basic automation",
        owner="Machinecraft",
        star_rating=4
    ),
    Lead(
        lead_id="A21",
        company="Mother's Packaging",
        category=LeadCategory.A_MACHINE_SALES,
        contacts=[
            {"name": "Nirdosh Singh", "role": "", "phone": "", "email": ""}
        ],
        location="Kishanpole, Rajasthan",
        remarks=["Revenue AM 35L", "AM machine long moulding packaging"],
        analysis="Small scale running AM, revenue ~35L. Upgrade candidate.",
        revenue_potential="₹25–60L",
        priority_action="Scale-up pitch, faster machines, automation benefits",
        owner="Machinecraft",
        star_rating=4
    ),
    Lead(
        lead_id="A22",
        company="Hari Niranjan Agarwal (Punk Brand)",
        category=LeadCategory.A_MACHINE_SALES,
        contacts=[
            {"name": "Hari Niranjan Agarwal", "role": "", "phone": "", "email": ""}
        ],
        remarks=["AM Revenue 35L"],
        analysis="Small scale thermoformer, ~35L revenue. Growth potential.",
        revenue_potential="₹25–60L",
        priority_action="Position entry-level pressure forming as differentiation",
        owner="Machinecraft",
        star_rating=3
    ),
    
    # Category B: Strategic OEM/Automotive
    Lead(
        lead_id="B1",
        company="Maruti Suzuki India Limited",
        category=LeadCategory.B_OEM_AUTOMOTIVE,
        contacts=[
            {"name": "Vinay Tewatia", "role": "Senior Manager – Corporate Projects", "phone": "+91 95823 65610", "email": "vinay.tewatia@maruti.co.in"}
        ],
        location="New Delhi",
        analysis="Tier-0 automotive OEM. ABS heavy gauge, battery enclosures, interior trim panels, wheel arch liners, underbody shields, EV battery trays.",
        revenue_potential="₹2–20 Cr annually (even 1 approved part)",
        priority_action="NOT cold email. Structured OEM approach. Vendor registration process.",
        owner="Indu/Formpack (Parts), strategic relationship",
        star_rating=9,
        website="www.marutisuzuki.com"
    ),
    Lead(
        lead_id="B2",
        company="JBM Electric Vehicles Pvt Ltd",
        category=LeadCategory.B_OEM_AUTOMOTIVE,
        contacts=[
            {"name": "Ravi Kumar", "role": "DGM - Sourcing & Industrial Materials, Bus Division", "phone": "+91 9873990305", "email": "ravi.kumar@jbmgroup.com"}
        ],
        location="Faridabad",
        analysis="Electric bus manufacturer. Bus interiors require ceiling panels, side panels, battery covers, enclosures, HVAC ducts. Direct synergy with FR ABS capability.",
        revenue_potential="₹1–10 Cr annual (even 1 bus component)",
        priority_action="Professional approach. No small talk. Position as automotive thermoforming partner.",
        owner="Indu/Formpack (Parts)",
        star_rating=7,
        website="www.jbmgroup.com"
    ),
    Lead(
        lead_id="B3",
        company="Enkay Rubber Group",
        category=LeadCategory.B_OEM_AUTOMOTIVE,
        contacts=[
            {"name": "Abhinandan Jain", "role": "Director & Head Manufacturing, MSE Plastics Engineering", "phone": "+91 9810042350", "email": "abhinandanjain@enkayrub.com"}
        ],
        location="Gurugram",
        remarks=["Improve ingress rubber mould 11 thickness"],
        analysis="Large automotive supplier. Tier 1/2. Opportunities: liners, battery covers, underbody shields, interior panels, tooling, pressure forming.",
        revenue_potential="₹50L–5 Cr annual (if even 1 product cracks)",
        priority_action="Handle carefully. No casual sales pitch. Build relationship first.",
        owner="Indu/Formpack (Strategic)",
        star_rating=6,
        website="www.enkayrubber.com"
    ),
    Lead(
        lead_id="B4",
        company="IFB Industries Limited",
        category=LeadCategory.B_OEM_AUTOMOTIVE,
        contacts=[
            {"name": "Bharat Pandit", "role": "Assistant Manager - Structural Design, R&D, Home Appliances Division", "phone": "+91 9923043864", "email": "bharat@ifbglobal.com"}
        ],
        location="Goa",
        analysis="Appliances. Thermoforming fit: large covers, lower tooling vs injection, rapid development.",
        revenue_potential="₹50L–3 Cr annually (1 successful part)",
        priority_action="Position as appliance OEM thermoforming partner. Large ABS panels specialty.",
        owner="Indu/Formpack (Parts)",
        star_rating=6,
        website="www.ifbappliances.com"
    ),
    Lead(
        lead_id="B5",
        company="Tip Top Industries (GAF)",
        category=LeadCategory.B_OEM_AUTOMOTIVE,
        contacts=[
            {"name": "Karan Arora", "role": "", "phone": "9582333515", "email": "arorakaran225@gmail.com"},
            {"name": "Sheetiz Arora", "role": "", "phone": "9654801515", "email": ""},
            {"name": "Raj Kumar Arora", "role": "", "phone": "7827128908", "email": "gafprecleaners@gmail.com"}
        ],
        location="Delhi / Ghaziabad",
        business="Radiator Fans, Pre-cleaner Assembly, Suction Filters, Tool Box, Steering Covers, Seat Covers, Tractor/Truck/JCB/Excavator parts",
        remarks=["Hood parts requirement"],
        analysis="Heavy equipment segment. Injection tooling expensive for large parts. Thermoforming cost-effective.",
        revenue_potential="₹25L–2 Cr annually (if 1 hood project lands)",
        priority_action="Call within 48 hours. Heavy gauge capability pitch.",
        owner="Indu/Formpack (Parts) + Machinecraft",
        star_rating=5
    ),
    Lead(
        lead_id="B6",
        company="Suraj Plastic Industries",
        category=LeadCategory.B_OEM_AUTOMOTIVE,
        contacts=[
            {"name": "Tej Ram Singhal", "role": "", "phone": "+91 9810376304", "email": "info@surajplasticindustries.com"}
        ],
        location="New Delhi",
        remarks=["Sheets required", "4 x 8 ft 8mm ABS", "Pressure forming", "Hydro power piston", "Making injection moulding food containers", "Makes FRP parts for railways", "400 diff parts"],
        analysis="Not small. Railway/government supply. Heavy gauge 8mm ABS. Interested in pressure forming. End-to-end solution pitch.",
        revenue_potential="Machine: ₹80L–2 Cr, Sheet recurring: ₹20L–1 Cr annually, Tooling: ₹5–25L",
        priority_action="Full solution pitch: machine + 8mm ABS sheets + pressure forming tooling + parts outsourcing",
        owner="Machinecraft + Sheet + Tooling + Indu/Formpack (ALL)",
        star_rating=6,
        website="www.surajplasticindustries.com"
    ),
    Lead(
        lead_id="B7",
        company="Cosmos Fibre Glass Ltd",
        category=LeadCategory.B_OEM_AUTOMOTIVE,
        contacts=[
            {"name": "Rohit Rungta", "role": "Director", "phone": "+91 9818649116", "email": "rohit.rungta@cosmosfg.com"}
        ],
        location="Faridabad",
        remarks=["PF1-A 3020"],
        analysis="FRP automotive components. Likely plastic conversion. FR ABS conversion from FRP opportunity.",
        revenue_potential="₹50L–2 Cr",
        priority_action="Pitch material conversion strategy",
        owner="Machinecraft + Indu/Formpack",
        star_rating=5
    ),
    Lead(
        lead_id="B8",
        company="Imperia Industries India Pvt Ltd",
        category=LeadCategory.B_OEM_AUTOMOTIVE,
        contacts=[
            {"name": "Priyash Bhargava", "role": "Director", "phone": "+91 9810072702", "email": "imperiaindustries@gmail.com"}
        ],
        location="Bawana Industrial Area, Delhi",
        business="Pipes, hose pipes, general auto parts",
        remarks=["Bag machine"],
        analysis="Automotive component manufacturer. Potential OEM supplier.",
        revenue_potential="₹25L–1 Cr",
        priority_action="Conversion from injection to heavy gauge thermoforming",
        owner="Machinecraft + Parts",
        star_rating=4
    ),
    
    # Category E: Raw Material Partners (key ones)
    Lead(
        lead_id="E1",
        company="Indian Oil Corporation Limited",
        category=LeadCategory.E_RAW_MATERIAL,
        contacts=[
            {"name": "Robinson A", "role": "Senior Manager, Technical Services - Business Development, Petrochemicals Marketing", "phone": "9003263595", "email": "robinsona@indianoil.in"}
        ],
        location="Coimbatore",
        analysis="Strategic raw material contact. Potential polymer supply partnership.",
        revenue_potential="Strategic - better pricing, annual contracts",
        priority_action="Build relationship for polymer supply partnership",
        owner="Procurement + Management",
        star_rating=6
    ),
    Lead(
        lead_id="E2",
        company="Prime Poly",
        category=LeadCategory.E_RAW_MATERIAL,
        contacts=[
            {"name": "Pinki Kumari", "role": "Senior Sales Coordinator", "phone": "+91 9560923001", "email": "sc1@primepoly.in"}
        ],
        location="Delhi & Chennai",
        remarks=["FR ABS, PC ABS – Raw material supplier"],
        analysis="Key for OEM FR material requirements",
        priority_action="Build relationship for FR ABS/PC ABS sourcing",
        owner="Procurement",
        star_rating=5
    ),
    
    # Category F: General Industrial (select high-priority ones)
    Lead(
        lead_id="F5",
        company="Suresh Jambhalikar",
        category=LeadCategory.F_GENERAL_INDUSTRIAL,
        contacts=[
            {"name": "Suresh Jambhalikar", "role": "Managing Director", "phone": "+91 96040 69686", "email": "suresh.jambhalikar@gmail.com"}
        ],
        location="Chakan, Pune",
        analysis="Automotive cluster. Strategic.",
        priority_action="Build relationship",
        owner="Machinecraft + Indu/Formpack",
        star_rating=4,
        website="www.jambhalikar.com"
    ),
    Lead(
        lead_id="F6",
        company="Gold Star India Industries",
        category=LeadCategory.F_GENERAL_INDUSTRIAL,
        contacts=[
            {"name": "Manjinder Singh Dhiman", "role": "Managing Director", "phone": "98783 32201", "email": "goldstarsamana@gmail.com"}
        ],
        location="Samana, Punjab",
        analysis="Industrial scale. Tractor/agri covers, housings, heavy ABS/PP opportunity.",
        priority_action="Check website immediately for product line",
        owner="Machinecraft + Sheet",
        star_rating=4,
        website="www.goldstarsamana.com"
    ),
    Lead(
        lead_id="F19",
        company="Tulips - Superfine Swabs (I) Limited",
        category=LeadCategory.F_GENERAL_INDUSTRIAL,
        contacts=[
            {"name": "Rahul Jain", "role": "Director", "phone": "", "email": "rahul@superfineswabs.com"}
        ],
        remarks=["AM + press – export style", "Jumbo cotton type – small tray – chemical foam"],
        analysis="Medical/packaging prospect. Export packaging.",
        revenue_potential="₹40L–1.5 Cr",
        priority_action="Follow up on AM + press requirement",
        owner="Machinecraft + Sheet",
        star_rating=5
    ),
]


# =============================================================================
# EMAIL TEMPLATES BY CATEGORY
# =============================================================================

EMAIL_TEMPLATES = {
    LeadCategory.A_MACHINE_SALES: {
        "subject": "Following up from Plastindia – {requirement_short}",
        "template": """Thank you for visiting us at Plastindia. Great meeting you.

{personalized_opener}

Based on our conversation, here's what we can offer:

{solution_pitch}

Next steps:
{next_steps}

Happy to set up a call to discuss specifications and timeline. What works for you this week?""",
        
        "hot_lead_template": """Good speaking with you at Plastindia – following up as promised.

{personalized_opener}

You mentioned {requirement}. Here's the quick answer:

{solution_pitch}

{video_offer}

Let's talk. When works for a 15-minute call?""",
    },
    
    LeadCategory.B_OEM_AUTOMOTIVE: {
        "subject": "Thermoforming Solutions for {company} – Plastindia Follow-up",
        "template": """Thank you for your time at Plastindia.

{personalized_opener}

Machinecraft and our parts division (Indu/Formpack) specialize in thermoformed automotive components:
- Interior panels and trim
- Battery covers and enclosures  
- Underbody shields
- Large-format ABS/FR ABS parts

Advantages over injection molding:
- 70-80% lower tooling cost
- Faster development cycles
- Cost-effective for large panels

{oem_specific}

We'd welcome the opportunity to discuss how we can support {company}'s requirements. Would you be open to a brief call to explore this further?""",
    },
    
    LeadCategory.C_SHEET_SUPPLY: {
        "subject": "Sheet Supply Inquiry – {material_type}",
        "template": """Following up from Plastindia regarding your sheet requirements.

Based on our discussion:
- Material: {material_type}
- Size: {sheet_size}
- Thickness: {thickness}

We can supply this from our sheet division. Volume pricing available for regular orders.

Would you like a formal quotation? Let me know your monthly consumption estimate.""",
    },
    
    LeadCategory.D_TOOLING: {
        "subject": "Thermoforming Tooling – Following up from Plastindia",
        "template": """Good connecting at Plastindia.

Our tool room specializes in:
- Aluminum forming molds
- CNC trimming fixtures
- Pressure forming tools
- 5-axis machined components

{requirement_specific}

Happy to share our tooling portfolio. What type of tooling are you looking at currently?""",
    },
    
    LeadCategory.E_RAW_MATERIAL: {
        "subject": "Polymer Supply Partnership Discussion",
        "template": """Thank you for the conversation at Plastindia.

{partnership_opener}

We're looking to build strategic partnerships for consistent polymer supply:
- ABS (various grades including FR)
- PC/ABS blends
- HIPS, PET, PP sheets

{specific_interest}

Would be great to explore how we can work together. Open to a call?""",
    },
    
    LeadCategory.F_GENERAL_INDUSTRIAL: {
        "subject": "Thermoforming Solutions – Plastindia Follow-up",
        "template": """Good meeting you at Plastindia.

{personalized_opener}

Machinecraft offers complete thermoforming solutions:
- Vacuum forming machines (entry to heavy gauge)
- Pressure forming for premium finish
- Sheet supply (ABS, HIPS, PET, PP)
- Tooling and mold development

{specific_pitch}

Let me know if you'd like to discuss any specific requirements.""",
    },
}


# =============================================================================
# EMAIL GENERATION
# =============================================================================

class LeadEmailDrafter:
    """Generates personalized follow-up emails for exhibition leads."""
    
    def __init__(self):
        self.leads_by_company = {lead.company.lower(): lead for lead in PLASTINDIA_LEADS}
        self.leads_by_id = {lead.lead_id: lead for lead in PLASTINDIA_LEADS}
        self.polisher = EmailPolisher() if EMAIL_POLISH_AVAILABLE else None
    
    def find_lead(self, query: str) -> Optional[Lead]:
        """Find a lead by company name or ID (fuzzy matching)."""
        query_lower = query.lower().strip()
        
        # Exact ID match
        if query_lower.upper() in self.leads_by_id:
            return self.leads_by_id[query_lower.upper()]
        
        # Exact company match
        if query_lower in self.leads_by_company:
            return self.leads_by_company[query_lower]
        
        # Fuzzy company match
        for company_name, lead in self.leads_by_company.items():
            if query_lower in company_name or company_name in query_lower:
                return lead
        
        # Check contact names
        for lead in PLASTINDIA_LEADS:
            for contact in lead.contacts:
                if query_lower in contact.get("name", "").lower():
                    return lead
        
        return None
    
    def get_all_leads(self, category: Optional[LeadCategory] = None) -> List[Lead]:
        """Get all leads, optionally filtered by category."""
        if category:
            return [l for l in PLASTINDIA_LEADS if l.category == category]
        return PLASTINDIA_LEADS
    
    def _get_requirement_short(self, lead: Lead) -> str:
        """Get a short version of the requirement for subject line."""
        if lead.requirement:
            # Take first 30 chars
            req = lead.requirement[:40]
            if len(lead.requirement) > 40:
                req = req.rsplit(' ', 1)[0] + "..."
            return req
        if lead.remarks:
            return lead.remarks[0][:40]
        return "Thermoforming Machine Inquiry"
    
    def _get_personalized_opener(self, lead: Lead) -> str:
        """Generate personalized opener based on lead data."""
        openers = []
        
        if lead.remarks:
            if any("machine" in r.lower() for r in lead.remarks):
                if any("immediate" in r.lower() for r in lead.remarks):
                    openers.append("Understood you need machines urgently – let's move fast on this.")
                elif any(str(num) in r for r in lead.remarks for num in range(5, 20)):
                    openers.append("With your existing machine fleet, you know exactly what you need.")
        
        if lead.analysis and "gold" in lead.analysis.lower():
            openers.append("Your setup sounds solid – let's talk about the upgrade path.")
        
        if lead.business:
            openers.append(f"Your work in {lead.business.split(',')[0].strip()} aligns well with our capabilities.")
        
        if lead.location:
            openers.append(f"Great connecting with you from {lead.location}.")
        
        return openers[0] if openers else "Good connecting at Plastindia."
    
    def _get_solution_pitch(self, lead: Lead) -> str:
        """Generate solution pitch based on requirements."""
        pitch_points = []
        
        # Machine-specific pitches
        if lead.category == LeadCategory.A_MACHINE_SALES:
            if any("pressure" in str(r).lower() for r in [lead.requirement] + lead.remarks):
                pitch_points.append("• Pressure forming capability – automotive-grade surface finish")
            if any("heavy" in str(r).lower() for r in [lead.requirement] + lead.remarks):
                pitch_points.append("• Heavy gauge forming up to 12mm thickness")
            if any("cup" in str(r).lower() for r in [lead.requirement] + lead.remarks):
                pitch_points.append("• High-speed cup forming line with inline stacking")
            if any("esd" in str(r).lower() for r in [lead.requirement] + lead.remarks):
                pitch_points.append("• ESD-safe tray forming with controlled humidity")
            if any("sheet" in str(r).lower() or "line" in str(r).lower() for r in [lead.requirement] + lead.remarks):
                pitch_points.append("• Complete sheet extrusion + thermoforming integration")
            
            # Default machine capabilities
            if not pitch_points:
                pitch_points = [
                    "• PF1 series – precision vacuum forming",
                    "• AM series – automatic heavy gauge forming",
                    "• Full automation with servo drives",
                    "• PLC controlled, easy operation"
                ]
        
        # OEM-specific pitches
        elif lead.category == LeadCategory.B_OEM_AUTOMOTIVE:
            pitch_points = [
                "• Large format parts (up to 3.5m x 2m)",
                "• FR ABS, PC/ABS capability",
                "• IATF 16949 compatible processes",
                "• In-house tooling development"
            ]
        
        return "\n".join(pitch_points) if pitch_points else "Complete thermoforming solutions tailored to your needs."
    
    def _get_next_steps(self, lead: Lead) -> str:
        """Generate appropriate next steps."""
        steps = []
        
        if lead.priority_action:
            if "video" in lead.priority_action.lower():
                steps.append("1. Sending machine video separately on WhatsApp")
            if "call" in lead.priority_action.lower():
                steps.append("2. Schedule a technical discussion call")
            if "visit" in lead.priority_action.lower():
                steps.append("3. Arrange factory visit for demo")
        
        if not steps:
            steps = [
                "1. Share detailed specifications for your requirements",
                "2. Prepare budgetary quotation",
                "3. Schedule technical call to finalize"
            ]
        
        return "\n".join(steps)
    
    def _get_video_offer(self, lead: Lead) -> str:
        """Generate video offer if applicable."""
        if any("video" in str(r).lower() for r in lead.remarks + [lead.priority_action]):
            return "\nI'll send the machine video on WhatsApp shortly."
        return ""
    
    def generate_email(self, lead: Lead, use_llm: bool = True) -> Dict[str, str]:
        """
        Generate a personalized follow-up email for a lead.
        
        Returns:
            Dict with 'subject', 'body', 'to_email', 'to_name', 'lead_id'
        """
        template_data = EMAIL_TEMPLATES.get(lead.category, EMAIL_TEMPLATES[LeadCategory.F_GENERAL_INDUSTRIAL])
        
        # Choose hot lead template if applicable
        is_hot = lead.star_rating >= 5 or any(
            kw in str(lead.remarks).lower() 
            for kw in ["immediate", "urgent", "video", "2 machines"]
        )
        
        template_key = "hot_lead_template" if is_hot and "hot_lead_template" in template_data else "template"
        template = template_data[template_key]
        
        # Build email content
        email_body = template.format(
            company=lead.company,
            requirement=lead.requirement or (lead.remarks[0] if lead.remarks else "your thermoforming needs"),
            requirement_short=self._get_requirement_short(lead),
            personalized_opener=self._get_personalized_opener(lead),
            solution_pitch=self._get_solution_pitch(lead),
            next_steps=self._get_next_steps(lead),
            video_offer=self._get_video_offer(lead),
            material_type=lead.remarks[0] if lead.remarks else "ABS/PET/HIPS",
            sheet_size=next((r for r in lead.remarks if "x" in r.lower() and any(c.isdigit() for c in r)), "4x8 ft"),
            thickness=next((r for r in lead.remarks if "mm" in r.lower()), "1-3mm"),
            requirement_specific=lead.requirement or "Custom tooling development",
            partnership_opener="Your materials expertise could complement our manufacturing capabilities.",
            specific_interest=lead.remarks[0] if lead.remarks else "Exploring supply options.",
            specific_pitch=lead.priority_action or "Let's discuss your specific application.",
            oem_specific=f"For {lead.company}, we see potential in {lead.analysis.split('.')[0].lower()}." if lead.analysis else ""
        )
        
        # Subject line
        subject = template_data["subject"].format(
            company=lead.company,
            requirement_short=self._get_requirement_short(lead),
            material_type=lead.remarks[0] if lead.remarks else "Sheet Supply"
        )
        
        # Polish with brand voice if available
        if self.polisher and use_llm:
            try:
                result = self.polisher.polish(
                    draft_email=email_body,
                    recipient_style={"formality_score": 50, "technical_score": 60},
                    emotional_state="curious",
                    warmth="acquaintance",
                    use_llm=use_llm
                )
                email_body = result.polished
            except Exception as e:
                print(f"[lead_drafter] Polish failed: {e}")
        
        return {
            "lead_id": lead.lead_id,
            "company": lead.company,
            "to_name": lead.primary_name,
            "to_email": lead.primary_email,
            "to_phone": lead.all_phones[0] if lead.all_phones else "",
            "subject": subject,
            "body": email_body,
            "category": lead.category.value,
            "star_rating": lead.star_rating,
            "revenue_potential": lead.revenue_potential,
        }
    
    def generate_all_drafts(self, 
                           category: Optional[LeadCategory] = None,
                           min_stars: int = 0,
                           use_llm: bool = False) -> List[Dict[str, str]]:
        """
        Generate drafts for all leads (or filtered subset).
        
        Args:
            category: Filter by category
            min_stars: Minimum star rating
            use_llm: Use LLM polish (slower but better)
        
        Returns:
            List of email dicts
        """
        leads = self.get_all_leads(category)
        if min_stars > 0:
            leads = [l for l in leads if l.star_rating >= min_stars]
        
        drafts = []
        for lead in leads:
            print(f"[lead_drafter] Generating email for {lead.company}...")
            draft = self.generate_email(lead, use_llm=use_llm)
            drafts.append(draft)
        
        return drafts
    
    def export_to_csv(self, drafts: List[Dict], output_path: str):
        """Export drafts to CSV for review."""
        fieldnames = ["lead_id", "company", "category", "star_rating", "to_name", 
                     "to_email", "to_phone", "subject", "body", "revenue_potential"]
        
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(drafts)
        
        print(f"[lead_drafter] Exported {len(drafts)} drafts to {output_path}")


# =============================================================================
# TELEGRAM INTEGRATION HELPERS
# =============================================================================

def draft_email_for_lead(query: str) -> str:
    """
    Telegram-callable function to draft an email for a specific lead.
    
    Usage: "Draft email for Dhanya Plastics"
    
    Returns formatted email draft.
    """
    drafter = LeadEmailDrafter()
    lead = drafter.find_lead(query)
    
    if not lead:
        return f"Lead not found: '{query}'. Try company name or lead ID (e.g., A1, A2)."
    
    draft = drafter.generate_email(lead, use_llm=True)
    
    response = f"""📧 **Draft Email for {lead.company}**

**To:** {draft['to_name']} ({draft['to_email'] or 'No email - use phone'})
**Phone:** {draft['to_phone'] or 'Not available'}
**Subject:** {draft['subject']}

---
{draft['body']}
---

⭐ Rating: {lead.star_rating}/6 | 💰 Potential: {lead.revenue_potential}
📂 Category: {lead.category.name}

Reply "APPROVE {lead.lead_id}" to save this draft."""
    
    return response


def list_plastindia_leads(category: Optional[str] = None) -> str:
    """
    List Plastindia leads, optionally filtered by category.
    
    Usage: "List leads" or "List category A leads"
    """
    drafter = LeadEmailDrafter()
    
    cat_filter = None
    if category:
        cat_map = {
            "a": LeadCategory.A_MACHINE_SALES,
            "b": LeadCategory.B_OEM_AUTOMOTIVE,
            "c": LeadCategory.C_SHEET_SUPPLY,
            "d": LeadCategory.D_TOOLING,
            "e": LeadCategory.E_RAW_MATERIAL,
            "f": LeadCategory.F_GENERAL_INDUSTRIAL,
        }
        cat_filter = cat_map.get(category.lower().strip())
    
    leads = drafter.get_all_leads(cat_filter)
    
    # Group by category
    by_category = {}
    for lead in leads:
        cat = lead.category.name
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(lead)
    
    lines = ["📋 **Plastindia Leads**\n"]
    for cat_name, cat_leads in by_category.items():
        lines.append(f"\n**{cat_name}** ({len(cat_leads)} leads)")
        for lead in cat_leads[:10]:  # Limit display
            stars = "⭐" * min(lead.star_rating, 5)
            lines.append(f"  • {lead.lead_id}: {lead.company} {stars}")
        if len(cat_leads) > 10:
            lines.append(f"  ... and {len(cat_leads) - 10} more")
    
    lines.append(f"\n💡 Say 'Draft email for [company]' to generate a follow-up.")
    
    return "\n".join(lines)


# =============================================================================
# CLI
# =============================================================================

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Plastindia Lead Email Drafter")
    parser.add_argument("--batch", action="store_true", help="Generate all drafts")
    parser.add_argument("--output", default="plastindia_drafts.csv", help="Output CSV file")
    parser.add_argument("--lead", type=str, help="Generate for specific lead")
    parser.add_argument("--category", type=str, help="Filter by category (A/B/C/D/E/F)")
    parser.add_argument("--min-stars", type=int, default=0, help="Minimum star rating")
    parser.add_argument("--use-llm", action="store_true", help="Use LLM polish (slower)")
    parser.add_argument("--list", action="store_true", help="List all leads")
    
    args = parser.parse_args()
    
    drafter = LeadEmailDrafter()
    
    if args.list:
        print(list_plastindia_leads(args.category))
        return
    
    if args.lead:
        result = draft_email_for_lead(args.lead)
        print(result)
        return
    
    if args.batch:
        cat_filter = None
        if args.category:
            cat_map = {"a": LeadCategory.A_MACHINE_SALES, "b": LeadCategory.B_OEM_AUTOMOTIVE,
                      "c": LeadCategory.C_SHEET_SUPPLY, "d": LeadCategory.D_TOOLING,
                      "e": LeadCategory.E_RAW_MATERIAL, "f": LeadCategory.F_GENERAL_INDUSTRIAL}
            cat_filter = cat_map.get(args.category.lower())
        
        drafts = drafter.generate_all_drafts(
            category=cat_filter,
            min_stars=args.min_stars,
            use_llm=args.use_llm
        )
        drafter.export_to_csv(drafts, args.output)
        print(f"\n✅ Generated {len(drafts)} email drafts → {args.output}")
        return
    
    # Default: interactive demo
    print("=" * 60)
    print("PLASTINDIA LEAD EMAIL DRAFTER")
    print("=" * 60)
    
    # Show sample
    sample_lead = drafter.find_lead("Dhanya")
    if sample_lead:
        print(f"\nSample: {sample_lead.company}")
        draft = drafter.generate_email(sample_lead, use_llm=False)
        print(f"Subject: {draft['subject']}")
        print(f"\n{draft['body'][:500]}...")
    
    print("\n" + "=" * 60)
    print("Usage:")
    print("  --list              List all leads")
    print("  --lead 'company'    Generate email for one lead")
    print("  --batch             Generate all drafts to CSV")
    print("=" * 60)


if __name__ == "__main__":
    main()
