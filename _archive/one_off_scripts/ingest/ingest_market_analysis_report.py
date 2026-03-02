#!/usr/bin/env python3
"""
Ingest Machinecraft Thermoforming Market Analysis Report

Comprehensive analysis of 535 thermoforming companies across Europe and US.
Critical market intelligence for sales strategy and prospecting.

Key findings:
- 535 companies analyzed
- 33 existing customers
- 502 potential prospects
- 289 high-priority opportunities
- German market largest (280+ companies)
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from openclaw.agents.ira.src.brain.knowledge_ingestor import KnowledgeIngestor, KnowledgeItem

SOURCE_FILE = "Machinecraft Thermoforming Market Analysis Report.pdf"


def create_knowledge_items() -> list[KnowledgeItem]:
    """Create structured knowledge items from the market analysis report."""
    items = []

    # 1. Executive Summary
    items.append(KnowledgeItem(
        text="""Machinecraft Market Analysis Report - Executive Summary (June 2025)

ANALYSIS SCOPE:
- Companies Analyzed: 535 (Europe and US markets)
- Existing Machinecraft Customers: 33 identified
- Potential Prospects: 502 mapped to suitable machine series
- High-Priority Opportunities: 289 identified
- Analysis Period: Comprehensive market review

KEY FINDINGS:

1. PF1 Series is Most Versatile:
   - Suitable for 534 companies (99.8% of database)
   - Universal workhorse across all applications

2. German Market is Largest Opportunity:
   - 280+ companies identified
   - Highest concentration of thermoforming companies

3. Market Segments Identified:
   - Industrial Fabrication & Custom Parts: 227 companies (42%)
   - Plastics Manufacturing: 154 companies (29%)
   - Packaging Solutions: 15 companies (3%)
   - Automotive Components: 8 companies (1.5%)
   - Medical/Healthcare: 2 companies
   - Specialized (luggage, wellness): Small niche

4. Machine Series Market Fit:
   - PF1 Series: 534 companies (99.8%)
   - PF1-X Series: 383 companies (71.6%) - premium automation
   - UNO Series: 129 companies (24.1%) - compact/entry level
   - PF1-R Series: 16 companies - packaging/roll-fed
   - PF1-M/AMV-M: 8 companies each - automotive mats
   - PF1-W: 2 companies - wellness
   - PF1-L: 1 company - luggage""",
        knowledge_type="market_intelligence",
        source_file=SOURCE_FILE,
        entity="Machinecraft",
        summary="Market analysis: 535 companies, 289 high-priority, German market largest",
        metadata={
            "topic": "executive_summary",
            "companies_analyzed": 535,
            "existing_customers": 33,
            "prospects": 502,
            "high_priority": 289
        }
    ))

    # 2. Machine Portfolio Market Fit
    items.append(KnowledgeItem(
        text="""Machinecraft Machine Portfolio - Market Fit Analysis

PF1 SERIES - UNIVERSAL WORKHORSE
- Target Companies: 534 (99.8% of database)
- Forming Areas: 1000x800mm to 4800x2500mm
- Max Depths: 400-1050mm
- Key Applications:
  * Industrial covers and housings
  * Transport trays and packaging
  * Automotive interior/exterior parts
  * Signage and displays
  * Custom fabricated components
- Market Position: Most versatile, fits nearly all prospects

PF1-X SERIES - PREMIUM AUTOMATION
- Target Companies: 383 (71.6% of database)
- Primary Markets: Western Europe, North America
- Key Features: Full automation, universal frames, pyrometer control
- Ideal For: High-volume manufacturers, premium applications
- Market Position: Premium solution for automation-focused buyers

UNO SERIES - COMPACT SOLUTIONS
- Target Companies: 129 (24.1% of database)
- Forming Area: 800x1000mm
- Ideal For: Small manufacturers, prototyping, cost-sensitive markets
- Market Position: Entry-level, accessible price point

SPECIALIZED SERIES:

PF1-R Series (Roll-Fed):
- Target: 16 companies
- Applications: Packaging trays, electronics
- Market Position: High-volume thin gauge

PF1-M/AMV-M Series (Car Mats):
- Target: 8 companies each
- Applications: Automotive floor mats
- Market Position: Niche automotive specialist

PF1-W Series (Wellness):
- Target: 2 companies
- Applications: Spa, medical, wellness
- Market Position: Specialty hygienic

PF1-L/DUO-L Series (Luggage):
- Target: 1 company
- Applications: Suitcase shells
- Market Position: Niche specialist""",
        knowledge_type="market_intelligence",
        source_file=SOURCE_FILE,
        entity="Machinecraft",
        summary="Machine market fit: PF1 99.8%, PF1-X 71.6%, UNO 24.1% of 535 companies",
        metadata={
            "topic": "machine_market_fit",
            "pf1_target": 534,
            "pf1x_target": 383,
            "uno_target": 129
        }
    ))

    # 3. German Market Analysis
    items.append(KnowledgeItem(
        text="""GERMAN MARKET ANALYSIS - PRIMARY TARGET (280+ Companies)

MARKET CHARACTERISTICS:
- Largest concentration of thermoforming companies in Europe
- High automation requirements
- Premium quality expectations
- Strong automotive and industrial sectors
- Engineering excellence culture

RECOMMENDED APPROACH:
1. Focus on PF1-X Series for automation benefits
2. Emphasize German engineering quality alignment
3. Target automotive and industrial applications
4. Leverage existing European success stories

KEY ACTIONS FOR GERMAN MARKET:
- Develop German-language marketing materials
- Establish local technical support presence
- Partner with German distributors/agents
- Attend German trade shows:
  * K-Fair (Düsseldorf) - World's largest plastics trade fair
  * Fakuma (Friedrichshafen) - International plastics processing

OPPORTUNITY SIZE:
- 216 German companies directly identified
- 64 additional Germany-listed companies
- Total: 280+ target companies
- High automation = Higher value sales (PF1-X Series)

COMPETITIVE LANDSCAPE:
- Competition from established European players
- German buyers expect premium service and support
- Technical competence is table stakes
- Local presence important for credibility""",
        knowledge_type="market_intelligence",
        source_file=SOURCE_FILE,
        entity="Machinecraft",
        summary="German market: 280+ companies, highest priority, focus PF1-X automation",
        metadata={
            "topic": "german_market",
            "company_count": 280,
            "priority": "highest",
            "recommended_series": "PF1-X",
            "trade_shows": ["K-Fair", "Fakuma"]
        }
    ))

    # 4. Netherlands Market & Batelaan Success Story
    items.append(KnowledgeItem(
        text="""NETHERLANDS MARKET ANALYSIS - HIGH-VALUE MARKET (10+ Companies)

KEY SUCCESS STORY: BATELAAN KUNSTSTOFFEN B.V.

Company Profile:
- 60+ years of thermoforming experience
- Major clients: ASML, VDL, Philips
- Comprehensive in-house capabilities
- European-wide distribution
- Existing Machinecraft customer SUCCESS

Applications with Machinecraft:
- Machine Covers: Large format PF1 Series for industrial equipment
- Transport Trays: PF1-R Series for high-volume tray production
- ESD Trays: Specialized materials for electronics applications
- Light Covers: Infrastructure applications requiring precision

Key Success Factors:
- Strategic supplier partnerships
- Complete in-house capabilities (design to delivery)
- Technical sales team with development support
- Modern, energy-efficient production

MACHINECRAFT OPPORTUNITY IN NETHERLANDS:
- Leverage Batelaan success as reference case
- Target high-tech manufacturing (ASML ecosystem)
- Focus on precision and automation
- Develop Batelaan case study for marketing

KEY ACTIONS:
- Develop Batelaan case study materials
- Target ASML supplier network (huge ecosystem)
- Attend Dutch manufacturing exhibitions
- Establish local technical partnerships

ASML CONNECTION:
ASML (€20B+ revenue) has extensive supplier network in Netherlands.
Thermoformed parts used in semiconductor equipment housings, 
transport trays, and cleanroom applications. High-value opportunity.""",
        knowledge_type="market_intelligence",
        source_file=SOURCE_FILE,
        entity="Machinecraft",
        summary="Netherlands: Batelaan success story (ASML, Philips clients), high-tech market",
        metadata={
            "topic": "netherlands_market",
            "success_story": "Batelaan",
            "major_clients": ["ASML", "VDL", "Philips"],
            "priority": "high"
        }
    ))

    # 5. Sweden Market & Success Stories
    items.append(KnowledgeItem(
        text="""SWEDEN MARKET ANALYSIS - SPECIALIZED APPLICATIONS (18+ Companies)

KEY SUCCESS STORIES:

1. ALLPRYL AB
Company Profile:
- Family-owned with 40+ years vacuum forming experience
- 5 fully equipped automated thermoforming machines
- Specializes in packaging solutions
- Complete in-house tooling capabilities

Applications with Machinecraft Potential:
- Packaging Solutions: Custom development from concept to production
- Prototyping: Direct ureol model forming for rapid development
- Aluminum Tooling: Integration with sand casting capabilities

Key Success Factors:
- Complete process control (3D design to finished product)
- Flexible production solutions
- Strong customer development partnerships
- Multi-industry application experience

Machinecraft Opportunity:
- Technology upgrade for increased efficiency
- Capacity expansion for growing demand
- Enhanced automation with PF1-X Series

---

2. ANATOMIC SITT AB
Company Profile:
- 30 years of specialized seating solutions
- Medical device manufacturing standards
- Custom/semi-custom production focus
- Therapeutic and mobility applications

Applications with Machinecraft Potential:
- Seating Shells: Custom contoured surfaces for medical applications
- Support Components: Lateral and back support elements
- Hygiene Applications: Waterproof formed surfaces for medical use

Key Success Factors:
- Specialized medical market knowledge
- High customization capabilities
- Therapeutic benefit focus
- Premium quality requirements

Machinecraft Opportunity:
- PF1-W Series: Perfect fit for wellness/medical applications
- Thermoregulation system for flatness control
- Custom tooling for patient-specific solutions

SWEDEN MARKET STRATEGY:
- Focus on specialized applications (medical, packaging)
- Leverage ALLPRYL and ANATOMIC SITT success
- Emphasize custom development capabilities""",
        knowledge_type="market_intelligence",
        source_file=SOURCE_FILE,
        entity="Machinecraft",
        summary="Sweden: ALLPRYL (packaging), ANATOMIC SITT (medical seating) success stories",
        metadata={
            "topic": "sweden_market",
            "success_stories": ["ALLPRYL AB", "ANATOMIC SITT AB"],
            "specializations": ["packaging", "medical"],
            "company_count": 18
        }
    ))

    # 6. UK and France Markets
    items.append(KnowledgeItem(
        text="""UK AND FRANCE MARKET ANALYSIS

UK MARKET - INDUSTRIAL FOCUS (13+ Companies)

Key Success Story: ABG RUBBER & PLASTICS
- Industrial fabrication and drape forming
- Commercial applications
- Material diversity: PC, PETG, Acrylic, PP, PE, PVC

Market Strategy:
- Target industrial fabrication sector
- Focus on material versatility
- Emphasize post-Brexit manufacturing opportunities
- UK companies looking to localize supply chains

UK Market Characteristics:
- Strong industrial base
- Cost-conscious buyers
- Quality expectations moderate to high
- Brexit driving reshoring interest

---

FRANCE MARKET - MANUFACTURING SECTOR (14+ Companies)

Market Strategy:
- Target automotive and aerospace applications
- Focus on precision and quality
- Develop French market partnerships

French Market Characteristics:
- Strong aerospace sector (Airbus ecosystem)
- Automotive manufacturing presence
- Premium quality expectations
- French language support important

KEY APPLICATIONS:
- Aerospace interior components
- Automotive parts
- Industrial equipment housings
- Custom fabrication

Recommended Approach:
- Partner with French distributors
- Attend French trade shows
- Develop French-language materials
- Target aerospace supply chain""",
        knowledge_type="market_intelligence",
        source_file=SOURCE_FILE,
        entity="Machinecraft",
        summary="UK: 13+ industrial companies; France: 14+ with aerospace/automotive focus",
        metadata={
            "topic": "uk_france_markets",
            "uk_companies": 13,
            "france_companies": 14,
            "uk_focus": "industrial",
            "france_focus": "aerospace_automotive"
        }
    ))

    # 7. Application Segment Analysis
    items.append(KnowledgeItem(
        text="""APPLICATION SEGMENT ANALYSIS BY COMPANY COUNT

1. INDUSTRIAL FABRICATION & CUSTOM PARTS (227 companies - 42%)

Typical Applications:
- Machine covers and protective housings
- Industrial equipment enclosures
- Custom fabricated components
- Protective panels and shields

Materials: ABS, PC, PMMA, HDPE
Production: Medium to high volume, custom tooling, quality focus
Machines: PF1 Series, PF1-X Series, UNO Series

---

2. PLASTICS MANUFACTURING (154 companies - 29%)

Typical Applications:
- Thermoformed components for assembly
- Semi-finished products for further processing
- Custom plastic parts and components
- Replacement parts and repairs

Materials: Wide range, engineering plastics, recycled, specialty
Production: Varied volumes, technical expertise, quality certifications
Machines: PF1 Series, PF1-X Series, PF1-R Series

---

3. PACKAGING SOLUTIONS (15 companies - 3%)

Typical Applications:
- Transport trays and containers
- Protective packaging inserts
- Electronic component trays
- Food packaging containers

Materials: PP, PET, PS, ESD materials
Production: High volume, cost sensitivity, regulatory compliance
Machines: PF1-R Series (primary), PF1 Series (alternative)

---

4. AUTOMOTIVE COMPONENTS (8 companies - 1.5%)

Typical Applications:
- Interior trim panels
- Exterior body components
- Under-hood covers and shields
- 3D car mats and floor liners

Materials: ABS, TPO, PC, PP
Production: High volume, strict quality, JIT delivery, OEM specs
Machines: PF1-M Series, AMV-M Series, PF1 Series

---

5. MEDICAL/HEALTHCARE (2 companies)

Applications: Medical device housings, therapeutic seating
Machines: PF1-W Series, IMG Series""",
        knowledge_type="market_intelligence",
        source_file=SOURCE_FILE,
        entity="Machinecraft",
        summary="Segments: Industrial(227), Plastics Mfg(154), Packaging(15), Automotive(8)",
        metadata={
            "topic": "application_segments",
            "industrial": 227,
            "plastics_mfg": 154,
            "packaging": 15,
            "automotive": 8,
            "medical": 2
        }
    ))

    # 8. Material Market Analysis
    items.append(KnowledgeItem(
        text="""MATERIAL APPLICATIONS - MARKET ANALYSIS

ABS (Acrylonitrile Butadiene Styrene) - DOMINANT MATERIAL
- Potential Users: 200+ companies
- Applications: Automotive parts, industrial housings, consumer products
- Machines: PF1 Series, PF1-X Series, PF1-M Series
- Characteristics: High volume, cost-sensitive, durability requirements
- Market Position: Most commonly requested material

PC (Polycarbonate) - PREMIUM SEGMENT
- Potential Users: 150+ companies
- Applications: Optical components, safety applications, high-impact parts
- Machines: PF1 Series, PF1-X Series
- Characteristics: Premium applications, precision requirements
- Market Position: Higher margins, technical selling

PMMA (Polymethyl Methacrylate/Acrylic) - OPTICAL/DISPLAY
- Potential Users: 100+ companies
- Applications: Optical applications, signage, architectural elements
- Machines: PF1 Series, PF1-X Series
- Characteristics: High precision, optical quality, weather resistance
- Market Position: Specialty applications, design-focused

TPO (Thermoplastic Olefin) - AUTOMOTIVE
- Potential Users: 50+ companies
- Applications: Automotive exterior, car mats, industrial applications
- Machines: AMV-M Series, PF1-M Series, PF1 Series
- Characteristics: Automotive standards, thick material processing
- Market Position: OEM relationships important

PP (Polypropylene) - PACKAGING/CHEMICAL
- Potential Users: 100+ companies
- Applications: Packaging, food contact, chemical resistance
- Machines: PF1-R Series, PF1 Series
- Characteristics: High volume, cost-effective, regulatory compliance
- Market Position: Price-driven, volume-focused""",
        knowledge_type="market_intelligence",
        source_file=SOURCE_FILE,
        entity="Machinecraft",
        summary="Materials: ABS(200+), PC(150+), PMMA(100+), TPO(50+), PP(100+) target companies",
        metadata={
            "topic": "material_analysis",
            "abs_users": 200,
            "pc_users": 150,
            "pmma_users": 100,
            "tpo_users": 50,
            "pp_users": 100
        }
    ))

    # 9. Strategic Priorities & Opportunities
    items.append(KnowledgeItem(
        text="""STRATEGIC OPPORTUNITIES - PRIORITY RANKING

IMMEDIATE OPPORTUNITIES (HIGH PRIORITY - 289 companies)

1. GERMAN MARKET EXPANSION
Target: 280+ German companies
Strategy:
- Focus on PF1-X Series for automation requirements
- Emphasize precision engineering and quality
- Target automotive and industrial sectors
- Leverage existing European success stories
Actions:
- German-language marketing materials
- Local technical support presence
- Partner with German distributors
- Attend K-Fair and Fakuma trade shows

2. EXISTING CUSTOMER EXPANSION
Target: 33 existing customers
Strategy:
- Analyze current machine utilization
- Identify capacity expansion needs
- Propose technology upgrades
- Cross-sell complementary machine series
Actions:
- Customer satisfaction surveys
- Technical review meetings
- Upgrade/expansion proposals
- Customer success case studies

3. NETHERLANDS MARKET DEEPENING
Target: 10+ Dutch companies + ASML ecosystem
Strategy:
- Leverage Batelaan success as reference
- Target high-tech manufacturing
- Focus on precision and automation
Actions:
- Batelaan case study development
- Target ASML supplier network
- Dutch manufacturing exhibitions
- Local technical partnerships

---

MEDIUM-TERM OPPORTUNITIES (55 companies)

1. Swedish Specialization Market (18+ companies)
   - Medical and packaging focus
   - Leverage ALLPRYL, ANATOMIC SITT

2. UK Industrial Market (13+ companies)
   - Industrial fabrication focus
   - Post-Brexit opportunity

3. French Manufacturing (14+ companies)
   - Automotive and aerospace
   - Precision applications""",
        knowledge_type="market_intelligence",
        source_file=SOURCE_FILE,
        entity="Machinecraft",
        summary="Priorities: German(280+), existing customers(33), Netherlands(ASML ecosystem)",
        metadata={
            "topic": "strategic_priorities",
            "immediate_opportunities": 289,
            "german_target": 280,
            "existing_customers": 33,
            "medium_term": 55
        }
    ))

    # 10. Implementation Plan
    items.append(KnowledgeItem(
        text="""IMPLEMENTATION ACTION PLAN

PHASE 1: IMMEDIATE ACTIONS (0-3 months)

Database Development:
- Complete detailed research on top 50 high-priority companies
- Develop individual company profiles and contact strategies
- Create targeted marketing materials for each market segment
- Establish CRM system for opportunity tracking

Market Entry Preparation:
- Develop German market entry strategy
- Create localized marketing materials (German, French)
- Identify potential partners/distributors
- Plan German trade show participation (K-Fair, Fakuma)

Customer Success Program:
- Interview existing customers for success stories
- Develop case study materials (Batelaan priority)
- Create customer reference program
- Plan customer expansion initiatives

---

PHASE 2: MARKET PENETRATION (3-6 months)

Direct Sales Activities:
- Launch targeted email campaigns to high-priority prospects
- Schedule technical webinars for key market segments
- Conduct virtual factory tours and demonstrations
- Develop proposal templates for common applications

Partnership Development:
- Establish distributor relationships in key markets
- Develop technical support partnerships
- Create channel partner training programs
- Implement partner incentive programs

Trade Show Strategy:
- Participate in key European thermoforming exhibitions
- Develop application-specific booth demonstrations
- Create interactive machine selection tools
- Implement lead capture and follow-up systems

---

PHASE 3: MARKET EXPANSION (6-12 months)

Product Development:
- Enhance PF1-X Series automation features
- Develop application-specific machine variants
- Create Industry 4.0 connectivity solutions
- Implement sustainability improvements

Market Consolidation:
- Establish European technical support centers
- Develop local inventory and spare parts programs
- Create customer training and certification programs
- Implement customer success management systems""",
        knowledge_type="market_intelligence",
        source_file=SOURCE_FILE,
        entity="Machinecraft",
        summary="3-phase plan: Database/prep(0-3mo), Penetration(3-6mo), Expansion(6-12mo)",
        metadata={
            "topic": "implementation_plan",
            "phase1": "0-3 months",
            "phase2": "3-6 months",
            "phase3": "6-12 months"
        }
    ))

    # 11. KPIs and Success Metrics
    items.append(KnowledgeItem(
        text="""KEY PERFORMANCE INDICATORS (KPIs)

SALES METRICS:
- Lead Generation: Target 100 qualified leads per quarter
- Conversion Rate: Achieve 15% quote-to-order conversion
- Market Share: Increase European market presence by 25%
- Customer Retention: Maintain 95% existing customer satisfaction

MARKET PENETRATION:
- German Market: Achieve 10 new installations in first year
- Application Diversity: Expand into 3 new application segments
- Geographic Coverage: Establish presence in 5 new countries
- Partnership Network: Develop 10 active channel partners

CUSTOMER SUCCESS:
- Reference Customers: Develop 20 active reference accounts
- Case Studies: Create 10 detailed application case studies
- Customer Expansion: Achieve 30% growth from existing customers
- Technical Support: Maintain 24-hour response time for technical issues

---

RISK ASSESSMENT AND MITIGATION:

MARKET RISKS:
1. Competition from Established Players
   - Mitigation: Superior technology and customer service
   - Leverage 40+ years of experience and innovation

2. Economic Uncertainty
   - Mitigation: Diversify across multiple markets and applications
   - Offer flexible financing and leasing options

3. Currency Fluctuations
   - Mitigation: Currency hedging strategies
   - Consider local manufacturing partnerships

TECHNICAL RISKS:
1. Technology Obsolescence
   - Mitigation: Continuous R&D investment
   - Regular technology roadmap updates

2. Quality Issues
   - Mitigation: Robust quality control systems
   - Comprehensive customer support programs

OPERATIONAL RISKS:
1. Supply Chain Disruptions
   - Mitigation: Diversified supplier base
   - Local sourcing strategies

2. Skilled Labor Shortage
   - Mitigation: Comprehensive training programs
   - Partnership with technical schools""",
        knowledge_type="market_intelligence",
        source_file=SOURCE_FILE,
        entity="Machinecraft",
        summary="KPIs: 100 leads/quarter, 15% conversion, 10 German installations Year 1",
        metadata={
            "topic": "kpis_risks",
            "lead_target": "100/quarter",
            "conversion_target": "15%",
            "german_installs_y1": 10,
            "customer_retention": "95%"
        }
    ))

    return items


def main():
    """Main ingestion function."""
    print("=" * 60)
    print("Machinecraft Market Analysis Report Ingestion")
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
