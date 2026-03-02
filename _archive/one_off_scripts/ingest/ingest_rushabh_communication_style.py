#!/usr/bin/env python3
"""
Ingest Rushabh Doshi's Communication Style - Emails & LinkedIn

This captures Rushabh's personal communication style for:
- Cold emails
- Follow-up emails
- LinkedIn intros/messages
- Company introductions
- Pricing discussions
- Meeting requests

Ira should use this to match Rushabh's tone and approach when drafting communications.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from openclaw.agents.ira.src.brain.knowledge_ingestor import KnowledgeIngestor, KnowledgeItem

SOURCE_FILE = "Cold Emails MailChimp & LinkedIn Intro Copies - Machinecraft 2025 June.pdf"


def create_knowledge_items() -> list[KnowledgeItem]:
    """Create structured knowledge items capturing Rushabh's communication style."""
    items = []

    # 1. Rushabh's Email Signature & Identity
    items.append(KnowledgeItem(
        text="""Rushabh Doshi - Email Signature & Professional Identity

STANDARD SIGNATURE:
With Best Regards
Rushabh Doshi
Director Responsible for Sales & Marketing at Machinecraft
Click here, to add me on Linkedin

ALTERNATE SHORTER SIGNATURE:
Warm regards,
Rushabh Doshi
Director – Sales & Marketing
Machinecraft

CASUAL SIGNATURE:
BR
Rushabh

TITLE VARIATIONS USED:
- "Director Responsible for Sales & Marketing at Machinecraft"
- "Director – Sales & Marketing"
- Just "Rushabh" for follow-ups

EMAIL ADDRESS:
- rushabh@machinecraft.org
- contact@machinecraft.org (company)

KEY IDENTITY ELEMENTS RUSHABH ALWAYS MENTIONS:
1. 3rd generation family company
2. Founded 1976 by grandfather BP Doshi (polymer chemist from UDCT)
3. Father Deepak is Managing Director
4. Uncle Rajesh is Technical Director
5. Younger brother works in production
6. Rushabh handles Sales & Commissioning
7. Joint ventures with FRIMO (Germany) and FVF (Japan)""",
        knowledge_type="user_style",
        source_file=SOURCE_FILE,
        entity="Rushabh Doshi",
        summary="Rushabh's email signature, titles, and identity elements to include",
        metadata={
            "topic": "signature_identity",
            "user": "Rushabh Doshi",
            "title": "Director Sales & Marketing"
        }
    ))

    # 2. Email Opening Patterns
    items.append(KnowledgeItem(
        text="""Rushabh's Email Opening Patterns & Greetings

CASUAL/FRIENDLY OPENINGS (Most Common):
- "Hey [Name]!"
- "Hey [Name]! Nice to e-meet you."
- "Hi [Name],"
- "Dear [Name]"

FOLLOW-UP OPENINGS:
- "Thanks for your email."
- "Thanks for your time today for the introduction call."
- "Thank you so much for this kind gesture! Appreciate it."

FORMAL OPENINGS (European/German):
- "Dear Herr [Name]!"
- "Greetings from Mumbai, India. How are you?"

KEY PHRASE - "Nice to e-meet you":
Rushabh frequently uses "Nice to e-meet you" as his signature 
opening phrase for first-time contacts. This is distinctive to his style.

PATTERN FOR FIRST CONTACT:
1. Greeting ("Hey [Name]!")
2. "Nice to e-meet you" (signature phrase)
3. Company introduction (3rd gen family company)
4. Value proposition/reason for contact
5. Links to videos/resources
6. Call to action (meeting, form, reply)
7. Signature

TONE CHARACTERISTICS:
- Warm and friendly, not overly formal
- Uses exclamation points for enthusiasm
- Personal touch (mentions family)
- Direct but polite
- Action-oriented""",
        knowledge_type="user_style",
        source_file=SOURCE_FILE,
        entity="Rushabh Doshi",
        summary="Rushabh's email openings: 'Hey [Name]!', 'Nice to e-meet you' signature phrase",
        metadata={
            "topic": "email_openings",
            "signature_phrase": "Nice to e-meet you",
            "tone": "warm_friendly"
        }
    ))

    # 3. Company Introduction Template
    items.append(KnowledgeItem(
        text="""Rushabh's Standard Company Introduction (For Emails)

SHORT VERSION:
"We are a 3rd generation family-run company that manufactures 
thermoforming machines from our factories near Mumbai, India."

MEDIUM VERSION:
"We are 3rd gen. family-run company producing zero sag machines 
at our plant near the city of Mumbai, India. Our primary market 
after India is Europe - where we have 21 customers in Germany, 
Netherlands, UK, France, Sweden, etc."

FULL VERSION:
"Nice to e-meet you. We are a 3rd generation family-run company that 
manufactures thermoforming machines from our factories near Mumbai, India. 
We were started in 1976 by my grandfather - polymer chemist from UDCT - 
Mr BP Doshi - who built India's first thermoforming machine and then the 
business grew at large with the involvement from my father Mr Deepak who 
currently is our Managing Director and my uncle Mr Rajesh who is our 
Technical Director.

Today, it is my younger brother who works in the production and myself 
who takes care of the Sales & Commissioning. We have 2 x joint ventures - 
one with German company FRIMO & one with Japanese company FVF. Both these 
companies make thermoforming ++ decorative technologies. With FRIMO, we 
learnt how to add a soft touch TPE/TPO foil over hard plastic & with FVF 
we learnt how to add special PC based films with wooden / metallic texture 
over hard plastic - both for automotive interiors. Our main expertise is 
into building single station type fully automatic thermoforming machines."

KEY CREDIBILITY POINTS TO INCLUDE:
1. "3rd generation family-run company" (trust/stability)
2. "Started 1976" or "40+ years" (experience)
3. "Grandfather built India's first thermoforming machine" (legacy)
4. FRIMO and FVF joint ventures (international credibility)
5. Customer references in Europe (21 customers)
6. Specific client names when relevant (Jaquar, ASML suppliers, etc.)""",
        knowledge_type="user_style",
        source_file=SOURCE_FILE,
        entity="Rushabh Doshi",
        summary="Company intro templates: short/medium/full versions with credibility points",
        metadata={
            "topic": "company_introduction",
            "key_phrase": "3rd generation family-run",
            "founding_year": 1976
        }
    ))

    # 4. Video Links & Resources Pattern
    items.append(KnowledgeItem(
        text="""Rushabh's Pattern for Sharing Video Links & Resources

STANDARD RESOURCE BLOCK:
"Here are few reference videos about us:
- [Customer testimonial link]
- [Latest machine video link]
- [Technical demo link]"

TYPICAL LINKS RUSHABH SHARES:
1. Customer Testimonial: https://youtu.be/Ex6k9liY45w
2. Latest Machine Video: https://youtu.be/hBYvyDq0Rg0
3. Zero Sag Machine: https://vimeo.com/718980157
4. Quick Tool Loading: https://youtu.be/qusyacqBVgw
5. C&K Plastics Zero Sag explanation: https://youtube.com/watch?v=6LhZaZv_S1Q

BULLET POINT FORMAT (Preferred):
● Link to a short presentation about us: Click here
● and our YouTube channel link: Click here
● Zero Sag Machine Video: Click here
● Customer Testimonial: Click here

VIDEO CONTEXT RUSHABH PROVIDES:
- "here is a nice video by C&K plastics showing benefits of Zero Sag"
- "Here is a video of a machine we supplied to company Mirsant from Russia"
- "we plan to show this machine this year at the K2022 show"

GOOGLE FORMS FOR REQUIREMENTS:
Rushabh uses Google Forms to collect machine requirements:
- https://forms.gle/fsiZDY96ya7MSn6M8
- https://forms.gle/AiJM6tSpgayhvKuv5
- https://forms.gle/RP3L6C1HT3842tvi8

FORM REQUEST PHRASING:
"To help me prepare an offer for you, can you please fill this google 
form to help me understand the kind of machine you require?"

"If you have some time, then please fill this form, it will help me 
prepare the offer"

"kindly fill this google form to help me understand the kind of machine 
you are looking for""",
        knowledge_type="user_style",
        source_file=SOURCE_FILE,
        entity="Rushabh Doshi",
        summary="Rushabh's video/resource sharing pattern with bullet points and Google Forms",
        metadata={
            "topic": "resource_sharing",
            "format": "bullet_points",
            "uses_google_forms": True
        }
    ))

    # 5. Meeting Request Patterns
    items.append(KnowledgeItem(
        text="""Rushabh's Meeting Request Patterns & Call-to-Actions

VIDEO CALL REQUESTS:
- "If you are available for a video call this week on [date] or [date] at a time convenient to you, I would like to present what we do."
- "Alternatively if you like we can get on a video call tomorrow or anytime in the next week as per your convenience."
- "Would you like to do a video call on Wednesday this week?"
- "I could show you our company presentation via teams video call if it is interesting for you"
- "We can also set up a video call next week if you are available to deep dive into your inquiry"

IN-PERSON MEETING REQUESTS:
- "I plan to be in the US in the week of June 19-23, do you think we can meet at your plant either on June 20 or 22? Which day works best for you?"
- "I am planning to come to the US in 2023 Q2"
- "Incase you can plan a visit mid-Feb to our plant, we can show you the machine as well"
- "I'll be near your plant on Tuesday 09.04"
- "I am back in Germany in the week of March 25, maybe we can plan to meet?"

TRADE SHOW REFERENCES:
- "also participating at NPE in 2024"
- "we plan to show this machine this year at the K2022 show in Dusseldorf"
- "The latest machine we sold was at the NPE show in Orlando a few weeks ago!"
- "if you can come to the K-show, that would be brilliant - as you can see the machine LIVE"

CALL-TO-ACTION PHRASES:
- "Just reply to this email or book a time with our team."
- "Looking forward to hearing from you."
- "Looking forward to meeting you soon :)"
- "Looking forward to collaborating."

CLOSING ENTHUSIASM:
- "Let's build something extraordinary together"
- "hopefully working with [Company Name]!"
- Smiley faces used: :) """,
        knowledge_type="user_style",
        source_file=SOURCE_FILE,
        entity="Rushabh Doshi",
        summary="Meeting request patterns: video calls, plant visits, trade shows, CTAs",
        metadata={
            "topic": "meeting_requests",
            "uses_smileys": True,
            "trade_shows": ["K-Fair", "NPE"]
        }
    ))

    # 6. LinkedIn Messaging Style
    items.append(KnowledgeItem(
        text="""Rushabh's LinkedIn Messaging Style

INITIAL CONNECTION MESSAGE:
"Hey [Name]! Nice to e-meet you on LinkedIn. I am planning to come to 
the US in [timeframe] and also participating at [trade show], can I get 
your mail address? Maybe we could chat to mutually benefit both our 
companies"

SHORT INTRO MESSAGE:
"Hi [Name], nice to connect via LinkedIn. I am a thermoforming machine 
and mould maker in India, short video about us: [YouTube link]
Incase you have any request for thermoforming machines or moulds - 
please reach out to me on rushabh@machinecraft.org"

FOLLOW-UP MESSAGE:
"Hey [Name]! How are you? We are looking for a buyer for a new machine 
we are developing for the US market and want to show it at NPE 2024. 
Do you think we can talk about it for [Company]? Would you be the right 
person?"

EMAIL REQUEST:
"Could you share your email id with me?"
"Hey [Name], what's your email id? I am back in [location] in the week of 
[dates], maybe we can plan to meet?"

LINKEDIN CHARACTERISTICS:
- Shorter messages than email
- Gets to the point quickly
- Asks for email to continue conversation
- References upcoming travel/trade shows
- Uses emojis sparingly (👍 😊 👏)
- Casual tone, first-name basis
- Often references "mutual benefit"

CORONA/CURRENT EVENTS AWARENESS:
"Hey [Name]! How are things in the NL with the corona outbreak? Here in 
Mumbai we have a 8-day shutdown to contain the virus and are all working 
from home." (Shows personal touch and awareness)""",
        knowledge_type="user_style",
        source_file=SOURCE_FILE,
        entity="Rushabh Doshi",
        summary="LinkedIn style: short, casual, asks for email, references travel/trade shows",
        metadata={
            "topic": "linkedin_style",
            "tone": "casual_direct",
            "goal": "get_email_address"
        }
    ))

    # 7. Pricing Discussion Style
    items.append(KnowledgeItem(
        text="""Rushabh's Style for Discussing Pricing in Emails

INDICATIVE PRICING FORMAT:
"Machine Sizes & Indicative Pricing (Ex-Works India)
Mould Size          Standard Machine    With Universal Frame
1200 x 1200 mm      $90,000 USD         $120,000 USD
1800 x 1000 mm      $120,000 USD        $160,000 USD"

PRICE REFERENCE IN CONTEXT:
- "The machine you see in the video was sold for 90,000 EUR approx."
- "this was sold to a client in France - and costs 45,000 EUR approx."
- "We are usually less than 200 EUR for a bedliner set"

PRICE CONDITIONING:
- Always mentions "Ex-Works India" or "EXW"
- Uses "approx." or "indicative" to leave room for negotiation
- Provides price ranges rather than fixed prices
- References comparable sales for credibility

OFFER PREPARATION PHRASES:
- "PFA offer for our fully loaded machine with forming area [size] as per your request"
- "Happy to prepare a formal PDF quotation with layout drawings and full scope of supply"
- "if you have any ideas for a vacuum forming machine size for which you need an offer, then please let me know"
- "once you tell me basic specs, answers to questions below, I can prepare an offer for you"

QUESTIONS TO SCOPE PRICING:
"1. max. forming area
2. heater type: IR ceramic, quartz or halogen flash
3. machine movements: pneumatic or servo type
4. number of heater ovens: 1 (for max. sheet thk 4 mm) or 2 (for max. sheet thk 10 mm)"

LEAD TIME MENTIONS:
- "Lead Time: Without universal frame: 4 months from purchase order"
- "With universal frame: 6 months from purchase order"

INCOTERMS:
- "If we get a CAD model after NDA signing, then we can provide a perfect pricing with DAP inco-terms"
- Uses DAP for delivered pricing, EXW for factory pricing""",
        knowledge_type="user_style",
        source_file=SOURCE_FILE,
        entity="Rushabh Doshi",
        summary="Pricing style: indicative/approx, ex-works, table format, lead times included",
        metadata={
            "topic": "pricing_style",
            "terms": "ex-works",
            "format": "table_with_options"
        }
    ))

    # 8. Technical Recommendation Style
    items.append(KnowledgeItem(
        text="""Rushabh's Style for Technical Recommendations in Emails

RECOMMENDATION HEADER:
"Recommended Machine Configuration
Based on your requirement for [application], we recommend the following configuration:"

BULLET-POINT SPECIFICATION FORMAT:
● Forming Style: Single-station, pneumatic-driven
● Operation: Manual load/unload
● Heaters: IR Quartz (Top & Bottom) with Energy Saving Mode
● Chamber: Closed type with Pre-blow & Sag Control capability
● Cooling: Integrated Fan Cooling
● Plug Assist: Included
● Bottom Platen: With quick-slide system using air-lift ball transfer units
● Clamp Frames:
   ○ Standard pneumatic frame
   ○ Optional Universal Adjustable Frame for flexible tool sizes
● UI & Programmability:
   ○ English-language HMI
   ○ Control for heating zones, bubble size, cooling delay
● Documentation:
   ○ PLC fault translation
   ○ Electrical & pneumatic diagrams
   ○ Maintenance schedule

PRODUCT LAUNCH ANNOUNCEMENT STYLE:
"We're excited to share that Machinecraft has just launched our latest 
and most powerful vacuum forming machine yet — the [Model]!
Watch the video here: [Link]
With a massive forming area of [dimensions], the [Model] is designed 
to meet the toughest demands of [industries]."

HOW WE CAN SUPPORT FORMAT:
"How we can support your next project:
● Vacuum Forming Machines (standard or custom sizes)
● Molds & Tooling (built in-house)
● ABS / HDPE / PS Sheets (up to 2.4 meters wide)"

APPLICATION-SPECIFIC DETAILS:
- Mentions client references (Jaquar for bathtubs)
- Shows relevant videos
- Offers plant visits to see similar machines
- Provides size context ("max. sheet size 3 x 3 m and 1 m deep")""",
        knowledge_type="user_style",
        source_file=SOURCE_FILE,
        entity="Rushabh Doshi",
        summary="Technical recommendations: bullet-point specs, nested details, client references",
        metadata={
            "topic": "technical_recommendations",
            "format": "bullet_points_nested",
            "includes": ["specs", "options", "references"]
        }
    ))

    # 9. Overall Tone & Personality
    items.append(KnowledgeItem(
        text="""Rushabh Doshi's Overall Communication Tone & Personality

PERSONALITY TRAITS IN WRITING:
1. WARM & APPROACHABLE
   - Uses "Hey" instead of "Dear" for most contacts
   - First-name basis quickly
   - Smiley faces :) in appropriate contexts
   - "Nice to e-meet you" (signature phrase)

2. FAMILY-PROUD
   - Always mentions 3rd generation family business
   - References grandfather, father, uncle, brother
   - Personal stake in company reputation

3. GLOBALLY MINDED
   - References customers in multiple countries
   - Mentions travel plans and trade shows
   - Aware of current events (COVID, etc.)

4. ACTION-ORIENTED
   - Every email has a clear next step
   - Offers video calls, plant visits, forms
   - Provides multiple contact options

5. CREDIBILITY-FOCUSED
   - Links to videos as proof
   - References specific customers
   - Mentions joint ventures (FRIMO, FVF)

6. TECHNICALLY KNOWLEDGEABLE
   - Explains zero-sag, heater types, etc.
   - Provides specifications confidently
   - Can discuss materials and applications

7. RELATIONSHIP-BUILDER
   - "Let's build something extraordinary together"
   - "Looking forward to collaborating"
   - "hopefully working with [Company]!"
   - References mutual benefit

WHAT RUSHABH AVOIDS:
- Overly formal language
- Pushy sales tactics
- Generic templates (always personalized)
- Complex jargon without explanation
- Long emails without clear CTAs

UNIQUE PHRASES TO REUSE:
- "Nice to e-meet you"
- "3rd generation family-run company"
- "Let's build something extraordinary together"
- "Looking forward to hearing from you :)"
- "Happy to prepare a formal PDF quotation"
- "Do you think we can meet?"
- "Which day works best for you?"
- "as per your convenience"
- "If you are available for a video call"
- "We have 2 x joint ventures - one with German company FRIMO"
""",
        knowledge_type="user_style",
        source_file=SOURCE_FILE,
        entity="Rushabh Doshi",
        summary="Rushabh's tone: warm, family-proud, action-oriented, credibility-focused",
        metadata={
            "topic": "overall_style",
            "traits": ["warm", "family-proud", "action-oriented", "credibility-focused"],
            "signature_phrase": "Nice to e-meet you"
        }
    ))

    return items


def main():
    """Main ingestion function."""
    print("=" * 60)
    print("Rushabh Communication Style Ingestion")
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
