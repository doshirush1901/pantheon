#!/usr/bin/env python3
"""
Ingest European Sales Cycle Analysis into Ira's Knowledge Base

Key learnings:
- Sales cycle durations by deal type
- Email frequency patterns
- Country-specific insights
- Conversion techniques by stage
"""

import sys
import os
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from openclaw.agents.ira.src.brain.knowledge_ingestor import KnowledgeIngestor, KnowledgeItem

SOURCE_FILE = "european_sales_cycle_analysis.md"


def create_knowledge_items() -> list[KnowledgeItem]:
    items = []

    # 1. Overall sales cycle metrics
    items.append(KnowledgeItem(
        text="""EUROPEAN SALES CYCLE METRICS (Based on 14 Won Deals)

KEY NUMBERS:
• Average Sales Cycle: 492 days (~16.4 months)
• Median Sales Cycle: ~6 months (excluding outliers)
• Average Emails per Deal: 32 emails
• Average Deal Size: €175,000
• Total Analyzed: €2.10M in closed sales (12 customers)

Notes: 
- Forma Plast (Sweden) excluded - second-hand machine only
- Romind T&G SRL (Romania) excluded - not a confirmed customer

CYCLE DURATION RANGES:
• Fast Closers (<3 months): 5 deals - urgent needs or referrals
• Medium Cycle (3-12 months): 4 deals - standard enterprise sales
• Long Nurture (>12 months): 4 deals - relationship building

FASTEST CLOSES:
• Ridat (UK): 9 days - €100,000
• Romind (Romania): 6 days - €90,000
• Donite (Ireland): 14 days - €90,000
• JoPlast (Denmark): 38 days - €290,000

LONGEST CYCLES (but still won):
• BD-Plastindustri (Sweden): 1548 days (4+ years) - €90,000
• Batelaan (Netherlands): 902 days (2.5 years) - €150,000
• Anatomic Sitt (Sweden): 721 days (2 years) - €70,000

KEY INSIGHT: Long cycles can still close. Never give up on a lead.
Swedish market in particular requires patience.""",
        knowledge_type="sales_knowledge",
        source_file=SOURCE_FILE,
        entity="Machinecraft",
        summary="Sales cycle metrics: Avg 16.4 months, 32 emails, €168K deal size (13 customers)",
        metadata={
            "topic": "sales_cycle_metrics",
            "avg_cycle_days": 492,
            "avg_emails": 32,
            "avg_deal_size": 168000
        }
    ))

    # 2. Fast closer patterns
    items.append(KnowledgeItem(
        text="""FAST CLOSERS - How to Close in Under 3 Months

DEALS THAT CLOSED FAST:
• Ridat (UK): 9 days, 18 emails, €100,000
• Donite (Ireland): 14 days, 19 emails, €90,000
• JoPlast (Denmark): 38 days, 36 emails, €290,000
• Soehner (Germany): <30 days, 15 emails, €270,000

COMMON PATTERNS FOR FAST CLOSES:
1. Urgent production need (replacing broken machine)
2. Previous relationship or referral from existing customer
3. Trade show connection (met at K exhibition)
4. Customer had clear specifications upfront
5. Single decision maker with budget authority

TECHNIQUES TO ACCELERATE:
• Immediate video call to build rapport (same day if possible)
• Same-day quote turnaround
• Factory visit offer within first week
• Reference customer in same country provided immediately
• Create urgency: "We have a production slot available in [month]"
• Decision deadline: "This price is valid until [date]"

RESPONSE TIME TARGETS:
• Initial inquiry: Same day (within 4 hours)
• Technical questions: Within 24 hours
• Quote requests: Within 48 hours
• Post-visit follow-up: Within 24 hours""",
        knowledge_type="sales_knowledge",
        source_file=SOURCE_FILE,
        entity="Machinecraft",
        summary="Fast closer techniques: 9-38 days possible with urgency and clear specs",
        metadata={
            "topic": "fast_close_techniques",
            "min_days": 6,
            "max_days": 38
        }
    ))

    # 3. Long nurture patterns
    items.append(KnowledgeItem(
        text="""LONG NURTURE DEALS - Patience Wins (12+ Month Cycles)

DEALS THAT TOOK YEARS BUT STILL CLOSED:
• BD-Plastindustri (Sweden): 51.6 months - €90,000 - Multiple expansion phases
• Forma Plast (Sweden): 42.1 months - €110,000 - Long-term relationship
• Batelaan (Netherlands): 30.1 months - €150,000 - Capacity planning cycle
• Anatomic Sitt (Sweden): 24.0 months - €70,000 - Product development timeline
• DutchTides (Netherlands): 19.9 months - €650,000 - Startup waited for funding

KEY INSIGHT: Swedish market averages 35 months. Don't give up!

NURTURE TECHNIQUES FOR LONG CYCLES:
• Quarterly newsletters with industry updates
• Share relevant case studies periodically
• Price protection offers ("Lock in 2024 pricing")
• Relationship building over transactions
• "When you're ready, we're here" approach
• Annual check-in calls

EMAIL FREQUENCY FOR NURTURE:
• 1 email per month (not more, not less)
• Quarterly phone/video call
• Annual face-to-face if possible

REASONS DEALS TAKE LONG:
• Startup scaling - waiting for funding round
• Budget cycle alignment - fiscal year timing
• Capacity expansion timing - tied to business growth
• Economic cycle dependencies
• Multiple stakeholder approval process
• Product development timeline (machine needed for new product)

NEVER DELETE THESE LEADS - They may convert years later!""",
        knowledge_type="sales_knowledge",
        source_file=SOURCE_FILE,
        entity="Machinecraft",
        summary="Long nurture deals: 2-4 years possible, Swedish market needs patience",
        metadata={
            "topic": "long_nurture_techniques",
            "avg_months_sweden": 35
        }
    ))

    # 4. Email cadence guidelines
    items.append(KnowledgeItem(
        text="""EMAIL CADENCE & FREQUENCY GUIDELINES

OPTIMAL TOUCH FREQUENCY BY STAGE:
• Active inquiry: 2-3 emails per week
• Post-quote waiting: 1 email per week
• Negotiation phase: As needed (be responsive)
• Long-term nurture: 1 email per month

EMAILS PER DEAL (ACTUAL DATA):
• Highest: Plastochim (France) - 65 emails
• Average: 32 emails per closed deal
• Lowest: Romind (Romania) - 13 emails
• Ratio: Rushabh sends ~60% (proactive follow-up)

RESPONSE TIME TARGETS:
• Initial inquiry: Same day (within 4 hours ideal)
• Technical questions: Within 24 hours
• Quote requests: Within 48 hours
• Post-visit follow-up: Within 24 hours
• Price negotiation: Same day

RE-ENGAGEMENT TRIGGERS:
• After 30 days silence: Share relevant case study
• After 60 days: Ask if requirements changed
• After 90 days: Offer updated pricing
• After 6 months: Timeline check-in
• After 12 months: "Thinking of you" with industry news

THE 60/40 RULE:
Rushabh sends ~60% of emails in successful deals.
This means PROACTIVE follow-up wins. Don't wait for the customer.

If you've sent 3 emails with no response:
• Try a different subject line
• Try a different time of day
• Try a phone call
• Try LinkedIn message
• Wait 2 weeks, then try again""",
        knowledge_type="sales_knowledge",
        source_file=SOURCE_FILE,
        entity="Machinecraft",
        summary="Email cadence: 32 avg per deal, 60% sent by Rushabh (proactive wins)",
        metadata={
            "topic": "email_cadence",
            "avg_emails": 32,
            "proactive_ratio": 0.6
        }
    ))

    # 5. Country-specific insights
    items.append(KnowledgeItem(
        text="""COUNTRY-SPECIFIC SALES INSIGHTS (Europe)

SWEDEN (4 customers - €360,000 total)
• Longest average cycle: ~35 months
• Relationship-driven market - trust takes time
• Quality over price focus
• Strong repeat business potential
• Customers: BD-Plastindustri, Forma Plast, Anatomic Sitt + others
• Approach: Patient, build long-term relationship

GERMANY (2 customers - €450,000 total)
• Medium cycle: ~2 months average
• Technical evaluation is critical
• Competitive with CMS, Illig (local manufacturers)
• Value proposition: Indian efficiency + European quality standards
• Approach: Lead with technical specs and quality certifications

NETHERLANDS (2 customers - €800,000 total)
• Highest value market per customer (€400K avg)
• Strong reference site value now: DutchTides
• Innovative applications (hydroponics, sustainable)
• Note: Batelaan closed in 2026
• Approach: Emphasize innovation and reference visits

UK & IRELAND (2 customers - €190,000 total)
• Fastest closers (9-14 days possible)
• Direct decision-making culture
• Price competitive market
• Good reference potential
• Approach: Quick response, competitive pricing

FRANCE (1 customer - €65,000)
• Most emails exchanged (65 emails for Plastochim)
• Requires detailed technical discussion
• Factory visit was conversion point
• Approach: Thorough documentation, patience

ITALY (1 customer - €80,000)
• New market being developed
• Trust building required
• CMS is strong local competitor
• Approach: Reference sites, factory visits crucial

DENMARK (1 customer - €290,000)
• Fast closer (38 days)
• Trade show lead converted well
• Technical quality focus
• Approach: Trade show presence important""",
        knowledge_type="sales_knowledge",
        source_file=SOURCE_FILE,
        entity="Europe",
        summary="Country insights: Sweden=35mo cycle, Netherlands=highest value, UK=fastest",
        metadata={
            "topic": "country_insights",
            "markets": ["Sweden", "Germany", "Netherlands", "UK", "France", "Italy", "Denmark"]
        }
    ))

    # 6. Sales stage flow
    items.append(KnowledgeItem(
        text="""TYPICAL WINNING SALES FLOW

STANDARD STAGE PROGRESSION:
Inquiry → Technical Discussion → Quote → Factory Visit → Negotiation → PO

STAGE 1: INQUIRY (Days 1-7)
• Initial contact via email, website, or trade show
• Customer describes application and requirements
• Rushabh responds within 24 hours with preliminary info
• Send brochure, video links, general capabilities

STAGE 2: TECHNICAL DISCUSSION (Days 7-30)
• Detailed specification exchange
• Machine sizing based on part dimensions
• Material compatibility confirmation
• Typically 3-5 technical emails
• Questions about heaters, servo, forming area, cycle time

STAGE 3: QUOTE (Days 14-60)
• Formal quotation with all specs and options
• Configurations explained clearly
• Video links to similar machines in operation
• Price validity period stated
• Payment terms included (typically 30-40-30)

STAGE 4: FACTORY VISIT (Days 30-90) - KEY DIFFERENTIATOR
• Offer to visit European reference site
  - Netherlands: DutchTides (6x2m hydroponics), Dezet
  - Sweden: Multiple options
• Or invitation to Mumbai factory
• Converts ~40% of visitors to buyers
• Critical for deals >€100,000

STAGE 5: NEGOTIATION (Days 60-180)
• Price discussion and discount requests
• Payment terms negotiation
• Delivery timeline confirmation
• Training and installation scope
• Warranty terms

STAGE 6: CLOSING/PO
• Purchase order received
• Proforma invoice issued within 24 hours
• Production slot confirmed
• Kick-off call scheduled

KEY CONVERSION POINTS:
• After quote → Offer factory visit
• After factory visit → Ask for PO timeline
• After 30 days silence → Share case study
• After 90 days → Check if requirements changed""",
        knowledge_type="sales_knowledge",
        source_file=SOURCE_FILE,
        entity="Machinecraft",
        summary="Sales flow: Inquiry→Technical→Quote→Factory Visit→Negotiation→PO",
        metadata={
            "topic": "sales_stage_flow",
            "factory_visit_conversion": 0.4
        }
    ))

    return items


def main():
    print("=" * 60)
    print("Ingesting European Sales Cycle Analysis")
    print("=" * 60)

    items = create_knowledge_items()

    print(f"\nCreated {len(items)} knowledge items:")
    for i, item in enumerate(items, 1):
        print(f"  {i}. [{item.knowledge_type}] {item.summary}")

    ingestor = KnowledgeIngestor()
    results = ingestor.ingest_batch(items)

    print("\n" + "=" * 60)
    print("INGESTION COMPLETE")
    print("=" * 60)

    return results


if __name__ == "__main__":
    main()
