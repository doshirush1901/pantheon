#!/usr/bin/env python3
"""
Ingest Rushabh Doshi LinkedIn Posts (June 2025)

Captures LinkedIn posting style, content themes, and technical/commercial
knowledge shared across Rushabh's posts promoting Machinecraft.

Source: 17 LinkedIn posts from rdd0101 profile
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from openclaw.agents.ira.src.brain.knowledge_ingestor import KnowledgeIngestor, KnowledgeItem

SOURCE_FILE = "LinkedIn Posts Rushabh Doshi Machinecraft June 2025.pdf"


def create_knowledge_items() -> list[KnowledgeItem]:
    """Create structured knowledge items from LinkedIn posts."""
    items = []

    # 1. LinkedIn Posting Style Overview
    items.append(KnowledgeItem(
        text="""Rushabh Doshi LinkedIn Posting Style Overview

PROFILE: linkedin.com/in/rdd0101
FOLLOWERS: 3,639+
POSTS: 188+
ARTICLES: 3 long-form articles

POSTING THEMES:
1. Machine product launches & specs
2. Factory/company growth announcements
3. Industry thought leadership (IMG, EV interiors)
4. Trade show/conference highlights
5. Hiring & team growth
6. Video content (machine demos)

TONE CHARACTERISTICS:
- Confident, technical authority
- Conversational yet professional
- Uses direct questions to hook readers
- Bold claims backed by specs
- Calls to action (DM, video links)
- Family pride + industrial heritage

FORMATTING PATTERNS:
- Emojis for visual breaks (📣, 🚀, 🏭, ⚙️, etc.)
- Bullet points with checkmarks (✅)
- Hashtag clusters at end
- Video/link embeds
- Provocative opening lines""",
        knowledge_type="user_style",
        source_file=SOURCE_FILE,
        entity="Rushabh LinkedIn Style",
        summary="Rushabh LinkedIn: 3.6K followers, 188 posts, confident tone, technical authority, emoji+bullets",
        metadata={
            "topic": "linkedin_style_overview",
            "followers": 3639,
            "posts": 188
        }
    ))

    # 2. Post Opening Hooks
    items.append(KnowledgeItem(
        text="""Rushabh Doshi LinkedIn Post Opening Hooks

PROVOCATIVE QUESTION OPENERS:
- "Spa OEMs: What's your thermoformer doing when asked to pull a 2800x2800 mm acrylic shell? Ours says, 'Bring it on.'"
- "What's the Machinecraft Group? Listen to this podcast..."

ANNOUNCEMENT OPENERS:
- "📣 BIG NEWS from the Doshi Family Group 🇮🇳"
- "At the ETD Conference in Amsterdam last week, we presented..."
- "Introducing the PF1-S by Machinecraft:"

ACTION/DEMO OPENERS:
- "Programming our compact #Vacuumforming machine for Factory approval test."
- "Quick Tool Loading + Centering, now possible on the 2024 #VacuumForming Machine"

THOUGHT LEADERSHIP OPENERS:
- "Soft-touch, lightweight, and premium textures—IMG thermoforming is revolutionizing EV interiors."

PATTERN: Start with either a challenge/question, big news, or demonstration of capability. Never boring intro.""",
        knowledge_type="user_style",
        source_file=SOURCE_FILE,
        entity="LinkedIn Opening Hooks",
        summary="LinkedIn hooks: provocative questions, 📣 announcements, demo/action, thought leadership openers",
        metadata={
            "topic": "post_openings"
        }
    ))

    # 3. Technical Spec Presentation Style
    items.append(KnowledgeItem(
        text="""Rushabh Doshi: How to Present Machine Specs on LinkedIn

EXAMPLE (PF1-3030 Spa Machine Post):
"Specs that slap:
• Forming area: 3000 x 3000 mm
• Draw depth: 1100 mm (ABS/PMMA-ready)
• Heater load: 316.8 kW across 2 precision-controlled zones
• Quartz elements: 245×60 mm, 2 per zone
• Supports max spa size: 2800 × 2800 mm
• Universal clamp frame: No mold-specific jigging
• Top & bottom heaters: Yes, because sag control isn't optional"

STYLE ELEMENTS:
1. "Specs that slap" - casual confidence
2. Bullet points with specific numbers
3. Technical but accessible
4. Parenthetical context (ABS/PMMA-ready)
5. Benefit statement after spec ("because sag control isn't optional")
6. Target application mentioned (spa size)

BENEFIT SUMMARY PATTERN:
"What it means:
No hot spots. No guesswork. No slowdowns.
Just repeatable, mirror-finish spa shells — cycle after cycle."

TARGET AUDIENCE CALLOUT:
"Who's it for?
ABS/PMMA processors building high-margin tubs and spa shells in India, MENA, and SEA."

CTA PATTERN:
"Video → [link]
Want to stop burning energy on old presses and start printing ROI? Let's talk." """,
        knowledge_type="user_style",
        source_file=SOURCE_FILE,
        entity="Spec Presentation Style",
        summary="Specs style: 'Specs that slap', bullets, benefits after each, target audience callout, video CTA",
        metadata={
            "topic": "spec_presentation"
        }
    ))

    # 4. Company Growth Announcement Style
    items.append(KnowledgeItem(
        text="""Rushabh Doshi: Company Growth Announcement Style

EXAMPLE (Doshi Family Group Expansion):

"📣 BIG NEWS from the Doshi Family Group 🇮🇳 #IndiaIsRising | #MakeInIndia | #GlobalPartnersWelcome

What started in 2019 as a modest 3-acre industrial plot has now become a fully integrated manufacturing campus — and we're just getting started!

📍 Updated on Google Maps 📍
You can now spot our state-of-the-art facilities from space! 🛰️

🏭 Formpack – One of India's leading custom vacuum formers
⚙️ Machinecraft – Specialist in polymer processing machinery with global reach
🧱 Indu – Manufacturing high-quality ABS, HDPE, and PS sheets for industrial use
🔧 In-house Tooling & Engineering – Designing and building turnkey solutions for:
→ 🚚 Commercial Vehicles | 🚜 Agriculture | ⚡ New Energy | 🚌 e-Bus | 💆‍♀️ Wellness

And guess what? We've just acquired more land next to our current setup to double down on our vision. 🚀

💥 The Indian manufacturing story is just beginning.
We're inviting global partners, OEMs, and innovators who want to build the future — together — right here in India.

📩 DM us if you're ready to ride this wave 🌊

We're also #Hiring Engineering 👷‍♂️ Talent from across India who want to live a life in the manufacturing heartland of India - #Gujarat, Umargam"

STYLE ELEMENTS:
- Big announcement emoji (📣)
- Origin story ("What started in 2019...")
- Visual proof ("Google Maps", "from space")
- Company portfolio with emojis
- Application sectors with arrows
- Growth news ("just acquired more land")
- Invitation to partners
- Hiring callout
- Location pride (Gujarat, Umargam)""",
        knowledge_type="user_style",
        source_file=SOURCE_FILE,
        entity="Growth Announcement Style",
        summary="Growth posts: origin story, emoji portfolio, visual proof, partner invitation, hiring CTA, location pride",
        metadata={
            "topic": "growth_announcements"
        }
    ))

    # 5. IMG/EV Thought Leadership Style
    items.append(KnowledgeItem(
        text="""Rushabh Doshi: Thought Leadership Posts (IMG Thermoforming)

EXAMPLE POST:
"Soft-touch, lightweight, and premium textures—IMG thermoforming is revolutionizing EV interiors.

Unlike traditional methods, IMG ensures:
✅ Perfect, distortion-free textures (leather grain, geometric patterns)
✅ Up to 60% weight reduction for better EV efficiency
✅ Faster production—2X to 3X quicker than slush molding
✅ Sustainable, recyclable materials—no PVC, no VOCs

🚀 Machinecraft is leading this shift with cutting-edge IMG technology.

Read our long-post article to know-more"

THOUGHT LEADERSHIP ELEMENTS:
1. Industry trend statement (EV interiors)
2. Technology positioning (IMG vs traditional)
3. Checkmark benefit list (✅)
4. Quantified advantages (60%, 2-3X)
5. Sustainability angle (no PVC, no VOCs)
6. Machinecraft positioning ("leading this shift")
7. Link to deeper content (article)

COMMENTS ENGAGEMENT:
- Industry experts respond with technical additions
- Example: Edgar Nimmergut added IMGL and real stitching processes
- Simon Kaiser discussed design constraints
- Shows Rushabh engaging with global industry network

HASHTAG PATTERN:
#thermoforming #automotive #autocomp #ev""",
        knowledge_type="user_style",
        source_file=SOURCE_FILE,
        entity="Thought Leadership Style",
        summary="Thought leadership: trend statement, checkmark benefits, quantified claims, Machinecraft positioning",
        metadata={
            "topic": "thought_leadership"
        }
    ))

    # 6. Hashtag Strategy
    items.append(KnowledgeItem(
        text="""Rushabh Doshi LinkedIn Hashtag Strategy

CORE BRAND HASHTAGS:
- #Machinecraft
- #Formpack
- #InduPolymers
- #DoshiGroup

INDUSTRY HASHTAGS:
- #Thermoforming
- #VacuumForming
- #PlasticProcessing
- #PolymerProcessing
- #FormingTech

APPLICATION HASHTAGS:
- #Spas #Bathtubs #AcrylicShells
- #Automotive #Autocomp #EV
- #CommercialVehicles #Agriculture
- #Medical #Wellness
- #NewEnergy #EVIndia

MATERIAL HASHTAGS:
- #PMMA #ABS #HDPE #PS
- #TPO #PC

GEOGRAPHIC/MARKET HASHTAGS:
- #MakeInIndia #MadeInIndia
- #India2025 #IndiaIsRising
- #Gujarat

BUSINESS HASHTAGS:
- #Hiring #JobOpening
- #PartnershipOpportunities
- #GlobalManufacturing
- #GlobalPartnersWelcome
- #CapexThatPerforms

PATTERN: 10-20 hashtags per post, mix of brand + industry + application + geography""",
        knowledge_type="user_style",
        source_file=SOURCE_FILE,
        entity="Hashtag Strategy",
        summary="Hashtags: brand (#Machinecraft) + industry + application + #MakeInIndia + business, 10-20 per post",
        metadata={
            "topic": "hashtag_strategy"
        }
    ))

    # 7. Video/Demo Post Style
    items.append(KnowledgeItem(
        text="""Rushabh Doshi: Video & Demo Post Style

PATTERN 1 - SHORT DEMO INTRO:
"Programming our compact #Vacuumforming machine for Factory approval test. The machine will be producing medical equipment parts!"
[Video embed]

PATTERN 2 - FEATURE HIGHLIGHT:
"Quick Tool Loading + Centering, now possible on the 2024 #VacuumForming Machine from Machinecraft Thermoforming OEM with Universal Frames"
[YouTube link: https://lnkd.in/dutJt6vb]

PATTERN 3 - SPEC POST WITH VIDEO CTA:
[Full spec breakdown]
"Video → https://lnkd.in/dj53i77d
Want to stop burning energy on old presses and start printing ROI? Let's talk."

VIDEO PLATFORMS USED:
- Vimeo (for product videos)
- YouTube (for machine demos)
- Native LinkedIn video

CONTENT TYPES:
- Machine in operation
- Factory approval tests
- Quick tool loading demos
- Zero sag demonstrations

KEY: Videos show machine capability, text provides context and specs""",
        knowledge_type="user_style",
        source_file=SOURCE_FILE,
        entity="Video Post Style",
        summary="Video posts: short demo intro, feature highlight with link, or spec breakdown + video CTA",
        metadata={
            "topic": "video_posts",
            "platforms": ["Vimeo", "YouTube", "LinkedIn"]
        }
    ))

    # 8. Conference/Trade Show Post Style
    items.append(KnowledgeItem(
        text="""Rushabh Doshi: Conference & Trade Show Post Style

EXAMPLE (ETD Amsterdam):
"At the ETD Conference in Amsterdam last week, we presented Machinecraft Thermoforming OEM's progress with XXL #thermoforming machinery production over the past 5 years. Check out our presentation copy for an in-depth look at our growth and achievements in the industry. Exciting times ahead!"

OTHER MENTIONS:
- NPE2024 (#npe2024)
- K2022 (router launch reference)

STYLE ELEMENTS:
1. Location + event name
2. What was presented/shown
3. Timeframe context (past 5 years)
4. Link to presentation/materials
5. Forward-looking statement ("Exciting times ahead!")

TRADE SHOW HASHTAGS:
- #NPE2024
- #ETDConference
- Event-specific tags

PURPOSE: Position Machinecraft as global player, share knowledge, attract international leads""",
        knowledge_type="user_style",
        source_file=SOURCE_FILE,
        entity="Trade Show Post Style",
        summary="Trade show posts: event+location, what presented, timeframe, materials link, forward statement",
        metadata={
            "topic": "trade_show_posts"
        }
    ))

    # 9. PF1-S 3030 Spa Machine Knowledge
    items.append(KnowledgeItem(
        text="""PF1-S 3030 Spa/Bathtub Thermoforming Machine (from LinkedIn)

TARGET APPLICATION:
- Outdoor spa shells
- Bathtubs
- Acrylic shells
- Max spa size: 2800 × 2800 mm

SPECIFICATIONS:
- Forming area: 3000 x 3000 mm
- Draw depth: 1100 mm
- Materials: ABS/PMMA-ready
- Heater load: 316.8 kW total
- Heater zones: 2 precision-controlled
- Quartz elements: 245×60 mm, 2 per zone
- Top & bottom heaters: Yes
- Universal clamp frame: No mold-specific jigging needed

KEY FEATURES:
- Zero sag control (top & bottom heaters)
- No hot spots
- Repeatable mirror-finish
- Cycle after cycle consistency

TARGET MARKETS:
- India
- MENA (Middle East & North Africa)
- SEA (Southeast Asia)

VALUE PROPOSITION:
"Stop burning energy on old presses and start printing ROI"
- High-margin tub/spa production
- ABS/PMMA processors""",
        knowledge_type="machine_spec",
        source_file=SOURCE_FILE,
        entity="PF1-S 3030",
        summary="PF1-S 3030: 3000x3000mm forming, 1100mm draw, 316.8kW heaters, for spas/bathtubs, India/MENA/SEA",
        metadata={
            "topic": "pf1_s_3030",
            "forming_area_mm": "3000x3000",
            "draw_depth_mm": 1100,
            "heater_kw": 316.8,
            "applications": ["spas", "bathtubs", "acrylic_shells"]
        }
    ))

    # 10. IMG Thermoforming Benefits (from LinkedIn)
    items.append(KnowledgeItem(
        text="""IMG Thermoforming Benefits for EV Interiors (from LinkedIn Posts)

WHY IMG FOR EV INTERIORS:
- EV brands demand premium feel at lower weight
- Interior quality is key differentiator
- Range anxiety drives weight reduction focus

IMG ADVANTAGES vs TRADITIONAL:
1. Perfect, distortion-free textures
   - Leather grain patterns
   - Geometric patterns
   - No texture distortion

2. Weight Reduction: Up to 60%
   - Critical for EV efficiency/range
   - Lighter than slush molding

3. Production Speed: 2X to 3X faster
   - Faster than slush molding
   - Better economics

4. Sustainability:
   - Recyclable materials
   - No PVC
   - No VOCs (volatile organic compounds)

ADVANCED PROCESSES (from comments):
- IMGL: In-mold graining + direct lamination in one process
- IMG with real stitching + die-pressing
- TPO foils with PP foam backing
- Eliminates traditional PU-foaming process
- End-of-life recyclability

DESIGN CONSTRAINTS:
- Sharp corners can be challenging
- Intricate design lines need care
- Undercuts require special consideration
- Feasibility depends on: design complexity, part size, volumes""",
        knowledge_type="application",
        source_file=SOURCE_FILE,
        entity="IMG EV Interiors",
        summary="IMG for EVs: 60% weight reduction, 2-3X faster than slush, no PVC/VOC, recyclable, premium textures",
        metadata={
            "topic": "img_ev_interiors",
            "weight_reduction": "60%",
            "speed_improvement": "2-3X",
            "vs_process": "slush_molding"
        }
    ))

    # 11. Doshi Polymer Park Structure
    items.append(KnowledgeItem(
        text="""Doshi Polymer Park: Integrated Manufacturing Campus

ORIGIN: Started 2019 with 3-acre plot
LOCATION: Umargam, Gujarat, India
STATUS: State-of-the-art facilities, visible on Google Maps/satellite

COMPANIES IN THE GROUP:

1. FORMPACK
   - Custom vacuum forming
   - One of India's leading thermoformers
   - Production/parts manufacturing

2. MACHINECRAFT
   - Polymer processing machinery OEM
   - Global reach (Europe, MENA, SEA, Americas)
   - Thermoforming machines (PF1, FCS, AM, IMG)

3. INDU POLYMERS
   - Sheet extrusion
   - ABS, HDPE, PS sheets
   - Industrial-grade materials

4. IN-HOUSE TOOLING & ENGINEERING
   - Turnkey solutions design
   - Mould/tool manufacturing

APPLICATION SECTORS SERVED:
- 🚚 Commercial Vehicles
- 🚜 Agriculture
- ⚡ New Energy
- 🚌 e-Bus
- 💆‍♀️ Wellness (spas, bathtubs)

EXPANSION: Additional land acquired adjacent to current campus
HIRING: Engineering talent, manufacturing heartland appeal""",
        knowledge_type="organization",
        source_file=SOURCE_FILE,
        entity="Doshi Polymer Park",
        summary="Doshi Polymer Park: Formpack+Machinecraft+Indu+Tooling, Umargam Gujarat, integrated campus since 2019",
        metadata={
            "topic": "doshi_polymer_park",
            "location": "Umargam, Gujarat",
            "founded": 2019,
            "companies": ["Formpack", "Machinecraft", "Indu Polymers", "Tooling"]
        }
    ))

    return items


def main():
    """Main ingestion function."""
    print("=" * 60)
    print("Rushabh Doshi LinkedIn Posts Ingestion")
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
