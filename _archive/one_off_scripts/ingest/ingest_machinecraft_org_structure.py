#!/usr/bin/env python3
"""
Ingest Machinecraft Organizational Structure

HR & Org Structure document containing:
- Executive leadership
- Department structure
- All employees and their roles
- Reporting matrix
- Open positions
- Skills gap analysis

Using knowledge_type="organization" for people-related knowledge.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from openclaw.agents.ira.src.brain.knowledge_ingestor import KnowledgeIngestor, KnowledgeItem

SOURCE_FILE = "_Finalized Org Structure – Machinecraft Technologies.pdf"


def create_knowledge_items() -> list[KnowledgeItem]:
    """Create structured knowledge items from the org structure document."""
    items = []

    # 1. Executive Leadership
    items.append(KnowledgeItem(
        text="""Machinecraft Technologies - Executive Leadership (May 2025)

THE DOSHI FAMILY - EXECUTIVE TEAM:

1. DEEPAK DOSHI - Chairman & Finance Director
   - Role: Company governance, accounts, financial planning
   - Generation: Founder/Senior leader
   - Direct Reports: Finance, Accounts team

2. RUSHABH DOSHI - Director of Sales & Marketing
   - Role: Customer development, market entry strategy, strategic alliances
   - Focus: Sales, marketing, customer relationships
   - Direct Reports: Sales & Marketing team (planned expansion)
   - Note: Primary external-facing leader
   - Email: rushabh@machinecraft.org
   - Mobile: +91 9833112903

3. MANAN DOSHI - Director of Engineering
   - Role: CAD, CAM, Production, Procurement
   - Focus: Technical execution, manufacturing operations
   - Direct Reports: Suraj (Design), Brijesh (CAM), Manish (Production), Ketan (Purchase)
   - Location: Primarily Umbergaon factory

4. RAJESH DOSHI - Technical Director
   - Role: Electrical, PLC, Pneumatic, Controls
   - Focus: Automation, electrical systems, machine controls
   - Direct Reports: Salim (Electrical), Bhavesh (PLC), Pneumatics team
   - Expertise: Technical problem-solving, controls engineering

FAMILY BUSINESS STRUCTURE:
- Third-generation family business (since 1976)
- Four Doshi family members in leadership
- Clear division of responsibilities:
  * Deepak: Finance & governance
  * Rushabh: Sales & external
  * Manan: Engineering & production
  * Rajesh: Technical & controls""",
        knowledge_type="organization",
        source_file=SOURCE_FILE,
        entity="Machinecraft Leadership",
        summary="Doshi family leadership: Deepak (Chairman), Rushabh (Sales), Manan (Eng), Rajesh (Tech)",
        metadata={
            "topic": "executive_leadership",
            "people": ["Deepak Doshi", "Rushabh Doshi", "Manan Doshi", "Rajesh Doshi"],
            "type": "leadership"
        }
    ))

    # 2. Engineering & Design Team
    items.append(KnowledgeItem(
        text="""Machinecraft Engineering & Design Teams

CAD / DESIGN DEPARTMENT:
Reports to: Manan Doshi (Director of Engineering)

SURAJ VISHWAKARMA - Senior Design Engineer
- Role: Lead 3D modeling, BOMs, 2D detailing, drawing reviews
- Manages: Ramiz Patani
- Software: SolidWorks, Excel
- KPIs: Drawing acceptance %, BOM accuracy
- Status: Key technical resource

RAMIZ PATANI - Design Engineer
- Role: Support 3D/2D outputs, drawing version control
- Reports to: Suraj Vishwakarma
- Software: SolidWorks, Excel
- KPIs: Drawing output/month, design error count

CAM DEPARTMENT:
Reports to: Manan Doshi

BRIJESH - CAM Programmer
- Role: Generate toolpaths, CNC programs, setup sheets
- Software: Mastercam
- KPIs: Toolpath cycle time, delivery accuracy
- Note: Only CAM programmer - critical resource, identified as skills gap

ENGINEERING CAPACITY NOTE:
- Only 2 CAD engineers (1 senior + 1 junior)
- Only 1 CAM programmer
- Identified need for:
  * Additional CAD Design Engineer (SolidWorks)
  * Backup CAM Programmer (high urgency)
  * Mid-level Design engineer""",
        knowledge_type="organization",
        source_file=SOURCE_FILE,
        entity="Machinecraft Design Team",
        summary="Design: Suraj (Sr), Ramiz; CAM: Brijesh (only one - critical); reports to Manan",
        metadata={
            "topic": "engineering_team",
            "department": "Design/CAM",
            "people": ["Suraj Vishwakarma", "Ramiz Patani", "Brijesh"],
            "reports_to": "Manan Doshi"
        }
    ))

    # 3. Electrical & Controls Team
    items.append(KnowledgeItem(
        text="""Machinecraft Electrical & Controls Teams

ELECTRICAL & PLC DEPARTMENT:
Reports to: Rajesh Doshi (Technical Director)

SALIM - Electrical Engineer
- Role: Create wiring layouts, panel wiring, testing
- KPIs: Wiring error count, completion time
- Software: AutoCAD (optional)

BHAVESH - PLC + HMI Programmer
- Role: Develop PLC logic and HMI screens
- Software: Siemens/Delta PLC software, HMI designer
- KPIs: Cycle time, usability, fault rate
- Skills: Mitsubishi PLCs, ladder logic
- Note: Key automation resource

ELECTRICIANS:
- BHAVIK - Electrician
- SONAL - Electrician
- VASANT - Electrical Technician
- Role: Wiring as per layout, panel work
- KPIs: Wiring accuracy, inspection pass rate

WIRING & PANELS:
- ROHIT DUBEY - Wiring & Panels
- RAJESH MORE - Wiring & Panels

PNEUMATICS DEPARTMENT:
Reports to: Rajesh Doshi

- DHRUVANT - Pneumatic Fitter
- CHANDRABALI - Pneumatic Fitter
- Role: Fit pneumatic cylinders, route airline systems
- KPIs: Leak rate, integration readiness

TEAM SIZE: ~9 people in Electrical/Controls/Pneumatics
IDENTIFIED GAPS:
- Need Senior Electrical Engineer (AutoCAD/Eplan for panel design)
- Need Senior PLC Programmer (Mitsubishi) - high urgency""",
        knowledge_type="organization",
        source_file=SOURCE_FILE,
        entity="Machinecraft Electrical Team",
        summary="Electrical: Salim (Eng), Bhavesh (PLC); 4 electricians; Pneumatics: 2 fitters",
        metadata={
            "topic": "electrical_team",
            "department": "Electrical/PLC/Pneumatics",
            "people": ["Salim", "Bhavesh", "Bhavik", "Sonal", "Vasant", "Rohit Dubey", "Rajesh More", "Dhruvant", "Chandrabali"],
            "reports_to": "Rajesh Doshi"
        }
    ))

    # 4. Production Team
    items.append(KnowledgeItem(
        text="""Machinecraft Production Team

PRODUCTION DEPARTMENT:
Reports to: Manan Doshi (Director of Engineering)

MANISH - Production Manager
- Role: Overall shopfloor & assembly head
- Responsibilities: Allocate tasks, oversee assembly, coordinate departments
- Direct Reports: 35+ production floor staff
- KPIs: Daily output, absenteeism, rework %

FITTER LINE LEADERS (7 people):
- NAGENDRA SAROJ
- MURARI SHARMA
- RAJU JAISWAL
- SHEETLA PRASAD (Guddu)
- PAL
- SURESH YADAV
- SURESH PANCHAL
Role: Lead mechanical assembly, interpret drawings
KPIs: Assembly time, quality pass rate

FITTERS (2 named):
- SUNIL PANCHAL
- MUKESH KAMLI
Role: Fit parts as per SOPs and drawings

WELDERS (11 people):
- RAHUL SAWANT
- BHARAT
- MANOJ
- ROHIT
- VASANT
- GANESH
- DINESH
- MUKUL
- RAKESH
- ARJUN
- GOPAL
Role: MIG/TIG welding
KPIs: Weld rejection %, time/part

PAINTERS (3 people):
- VINOD
- RAJESH BHARTI
- KAUSHIK
Role: Paint application, prep, finish coat
KPIs: Paint finish quality, rework rate

MACHINISTS:
- NILESH PAWAR - Lathe Operator
- MAHESH BHATT - Slotting Machine
- HARISH PATEL - VMC Operator
- VIJAY GIRI - Drilling
- RAKESH CHAVAN - Keyway Machine
Role: Machining shafts, keyways, 3D contours
KPIs: Dimensional accuracy, tool life

TOTAL PRODUCTION STAFF: 35+ people""",
        knowledge_type="organization",
        source_file=SOURCE_FILE,
        entity="Machinecraft Production Team",
        summary="Production: Manish (Manager), 7 line leaders, 11 welders, 3 painters, 5 machinists, 35+ total",
        metadata={
            "topic": "production_team",
            "department": "Production",
            "manager": "Manish",
            "team_size": "35+",
            "reports_to": "Manan Doshi"
        }
    ))

    # 5. Procurement & Stores
    items.append(KnowledgeItem(
        text="""Machinecraft Procurement & Stores Team

PROCUREMENT & STORES DEPARTMENT:
Reports to: Manan Doshi (Director of Engineering)

KETAN GORE - Purchase Executive
- Role: Follow up POs, vendor negotiation, order tracking
- Responsibilities:
  * Understand BOM and technical items
  * Identify, negotiate with vendors
  * Place POs for panels, steel, pneumatics, hardware
  * Follow up on lead times and delivery
  * Coordinate with stores and design team
  * Maintain cost control
- KPIs: Lead time, vendor rating, PO-to-delivery time
- Software: Excel, Email, Google Sheets
- Reports to: Manan Doshi

SACHIN - Store Executive
- Role: Manage stock, issue material, maintain records
- Responsibilities:
  * Receive and inspect incoming materials
  * Maintain digital stock register
  * Issue items with tracking against project codes
  * Conduct monthly inventory audits
  * Ensure FIFO, labeling, clean storage
- KPIs: Stock accuracy, inventory turnaround
- Reports to: Ketan Gore
- Software: Excel

IDENTIFIED GAPS:
- Need Senior Procurement Executive (machine-building focus)
- Need Senior Store & Inventory Manager (ERP skills)
- Current process is Excel/manual - needs software integration""",
        knowledge_type="organization",
        source_file=SOURCE_FILE,
        entity="Machinecraft Procurement",
        summary="Procurement: Ketan Gore (Purchase), Sachin (Stores); need ERP/software upgrade",
        metadata={
            "topic": "procurement_team",
            "department": "Procurement/Stores",
            "people": ["Ketan Gore", "Sachin"],
            "reports_to": "Manan Doshi"
        }
    ))

    # 6. Reporting Matrix Summary
    items.append(KnowledgeItem(
        text="""Machinecraft Reporting Matrix & Organization Summary

REPORTING STRUCTURE:

DEEPAK DOSHI (Chairman):
└── Finance & Accounts team

RUSHABH DOSHI (Sales Director):
└── Sales & Marketing (planned expansion)

MANAN DOSHI (Engineering Director):
├── Suraj Vishwakarma (Sr Design Engineer)
│   └── Ramiz Patani (Design Engineer)
├── Brijesh (CAM Programmer)
├── Manish (Production Manager)
│   └── 35+ production floor staff
└── Ketan Gore (Purchase Executive)
    └── Sachin (Store Executive)

RAJESH DOSHI (Technical Director):
├── Salim (Electrical Engineer)
├── Bhavesh (PLC + HMI Programmer)
├── Bhavik, Sonal (Electricians)
├── Vasant (Electrical Technician)
├── Rohit Dubey, Rajesh More (Wiring & Panels)
└── Dhruvant, Chandrabali (Pneumatic Fitters)

TOTAL HEADCOUNT SUMMARY:
- Executive Leadership: 4 (Doshi family)
- Engineering/Design: 3 (Suraj, Ramiz, Brijesh)
- Electrical/Controls: 9 (including pneumatics)
- Production: 35+ (under Manish)
- Procurement/Stores: 2 (Ketan, Sachin)
- TOTAL: ~55+ employees

LOCATIONS:
- Head Office: Mumbai (505 Palm Springs, Malad W)
- Factory: Umbergaon, Gujarat (Plot 92 Dehri Road)""",
        knowledge_type="organization",
        source_file=SOURCE_FILE,
        entity="Machinecraft Org Chart",
        summary="~55+ employees: 4 directors, 3 eng, 9 electrical, 35+ production, 2 procurement",
        metadata={
            "topic": "reporting_matrix",
            "total_employees": "55+",
            "locations": ["Mumbai", "Umbergaon"]
        }
    ))

    # 7. Open Positions & Skills Gaps
    items.append(KnowledgeItem(
        text="""Machinecraft Open Positions & Skills Gaps (May 2025)

CURRENT OPEN POSITIONS:

1. SENIOR ELECTRICAL ENGINEER (Control Panel Design)
   - Location: Umbergaon
   - Reports to: Rajesh Doshi
   - Skills: AutoCAD Electrical or Eplan
   - Urgency: HIGH
   - Reason: Control panels designed informally currently

2. CAD DESIGN ENGINEER (SolidWorks) - 2 POSITIONS
   - Location: Umbergaon
   - Reports to: Suraj Vishwakarma
   - Skills: SolidWorks 3D+2D, GD&T, Excel
   - Urgency: HIGH
   - Reason: Only 2 CAD engineers, 1 senior

3. SENIOR PLC PROGRAMMER (Mitsubishi)
   - Location: Umbergaon
   - Reports to: Rajesh Doshi
   - Skills: GX Works/GX Developer, Ladder Logic, HMI
   - Urgency: HIGH
   - Reason: Need for scale-up

4. SENIOR PROCUREMENT EXECUTIVE
   - Location: Umbergaon
   - Reports to: Manan Doshi
   - Skills: Vendor management, technical BOM reading
   - Urgency: HIGH
   - Reason: Machine-building focus needed

5. SENIOR STORE & INVENTORY MANAGER
   - Location: Umbergaon
   - Reports to: Purchase/Production Head
   - Skills: Excel, ERP, inventory software
   - Urgency: MEDIUM
   - Reason: Current process is manual/Excel

IDENTIFIED SKILLS GAPS:

| Gap | Reason | Urgency |
|-----|--------|---------|
| Senior CAM Programmer (backup) | Only Brijesh handles toolpaths | HIGH |
| Electrical Drafter (AutoCAD/Eplan) | Panel designs informal | HIGH |
| QC & Documentation Engineer | No stage inspection process | MEDIUM |
| Mid-level Design (SolidWorks) | Only 2 CAD engineers | HIGH |
| Storekeeper with ERP skill | Excel/manual process | MEDIUM |
| Mechatronics/R&D Assistant | For testing, innovation | OPTIONAL |

SCALING QUESTION:
"If we build 10 machines/month or hit ₹30 Cr revenue..."
- Can 1 CAM programmer handle it? NO
- Do we have Mechatronics expert for R&D? NO
- Can store system scale without software? NO
- Do we need QC engineer? YES""",
        knowledge_type="organization",
        source_file=SOURCE_FILE,
        entity="Machinecraft Hiring",
        summary="Hiring: Sr Electrical, 2x CAD, Sr PLC, Sr Procurement, Store Manager; key gaps identified",
        metadata={
            "topic": "open_positions",
            "open_roles": 6,
            "urgency_high": ["Electrical Engineer", "CAD Engineer", "PLC Programmer", "Procurement"]
        }
    ))

    # 8. Key Contacts Quick Reference
    items.append(KnowledgeItem(
        text="""Machinecraft Key Contacts Quick Reference

EXECUTIVE CONTACTS:

RUSHABH DOSHI - Director Sales & Marketing
- Email: rushabh@machinecraft.org
- Mobile: +91 9833112903
- Phone: +91-22-28817785
- Role: Primary sales contact, customer relationships
- Use for: Sales inquiries, strategic discussions, partnerships

COMPANY CONTACTS:
- Sales: sales@machinecraft.org
- Technical Support: support@machinecraft.org
- Phone: +91-22-28817785
- Website: www.machinecraft.org

KEY INTERNAL CONTACTS BY FUNCTION:

For Design Questions:
→ Suraj Vishwakarma (Sr Design Engineer)

For CAM/Programming:
→ Brijesh (CAM Programmer)

For Electrical/Controls:
→ Salim (Electrical Engineer)
→ Bhavesh (PLC Programmer)

For Production Status:
→ Manish (Production Manager)

For Procurement/Delivery:
→ Ketan Gore (Purchase Executive)

For Technical Direction:
→ Rajesh Doshi (Technical Director)

For Engineering Direction:
→ Manan Doshi (Director of Engineering)

ADDRESSES:

Mumbai Office:
505 Palm Springs, Link Road
Malad West, Mumbai 400064, India

Factory (Umbergaon):
Plot 92, Dehri Road
Umbergaon, Dist. Valsad
Gujarat 396170, India""",
        knowledge_type="organization",
        source_file=SOURCE_FILE,
        entity="Machinecraft Contacts",
        summary="Key contacts: Rushabh (sales), Suraj (design), Bhavesh (PLC), Manish (production)",
        metadata={
            "topic": "contacts",
            "sales_email": "rushabh@machinecraft.org",
            "sales_phone": "+91-22-28817785"
        }
    ))

    return items


def main():
    """Main ingestion function."""
    print("=" * 60)
    print("Machinecraft Org Structure & People Ingestion")
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
