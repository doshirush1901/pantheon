#!/usr/bin/env python3
"""
REALISTIC SALES SIMULATION
==========================

Simulates a natural sales conversation flow:
1. Customer sends ONE-LINE inquiry
2. IRA asks qualifying questions (from Google Form questionnaire)
3. Customer gradually provides specs
4. IRA recommends machine
5. Customer asks about features
6. IRA provides details
7. Customer asks for price
8. IRA sends offer

Based on REAL inquiry data from single sheet thermoforming form.
IRA learns and adapts from each reply.

REAL CUSTOMER: Vignesh Kumar, SRK Tele Energy (Telecom)
- Forming area: 1000 x 1500 mm
- Depth: 750 mm  
- Thickness: up to 6 mm
- Material: PMMA
"""

import os
import sys
import json
import time
import base64
from pathlib import Path
from datetime import datetime
from email.mime.text import MIMEText
from typing import Dict, List, Optional

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

import openai
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

client = openai.OpenAI()


# =============================================================================
# REAL CUSTOMER DATA (from inquiry form)
# =============================================================================

REAL_CUSTOMERS = {
    "vignesh_telecom": {
        "name": "Vignesh Kumar",
        "company": "SRK Tele Energy India Pvt Ltd",
        "email": "vignesh.kumar@flexsol.in",
        "industry": "Telecom",
        "location": "India",
        # Full specs (revealed gradually)
        "forming_area": "1000 x 1500 mm",
        "depth": "750 mm",
        "thickness": "up to 6 mm",
        "materials": "PMMA",
        # Expected machine
        "expected_machine": "PF1-C-1510",
        "expected_price_range": "₹40-50 lakh",
    },
    "yogesh_aerospace": {
        "name": "Yogesh Amte",
        "company": "Metrolab Engineering Pvt Ltd",
        "email": "yogesh.amte@metrolab.engineering",
        "industry": "Aerospace",
        "location": "India",
        "forming_area": "800 x 1000 mm",
        "depth": "400 mm",
        "thickness": "up to 6 mm",
        "materials": "Kydex",
        "expected_machine": "PF1-C-1008",
        "expected_price_range": "₹33-40 lakh",
    },
    "aleksandr_sanitary": {
        "name": "Aleksandr Tanonov",
        "company": "VIZ/Reimar",
        "email": "tanonov@foliplast.ru",
        "industry": "Sanitary-ware",
        "location": "Russia",
        "forming_area": "1200 x 2000 mm",
        "depth": "650 mm",
        "thickness": "up to 6 mm",
        "materials": "ABS+PMMA",
        "expected_machine": "PF1-C-2015",
        "expected_price_range": "₹60-70 lakh",
    },
}


# =============================================================================
# QUALIFYING QUESTIONS (from Google Form)
# =============================================================================

QUALIFYING_QUESTIONS = [
    "What industry/application is this machine for?",
    "What is your required forming area (L x W in mm)?",
    "What maximum draw depth do you need?",
    "What sheet thickness will you be working with?",
    "What materials will you be forming? (ABS, PC, PMMA, etc.)",
    "Do you have an existing machine you're replacing?",
    "What is your target budget range?",
    "What is your timeline for this purchase?",
]


# =============================================================================
# CONVERSATION STAGES
# =============================================================================

CONVERSATION_FLOW = [
    {
        "stage": "initial_inquiry",
        "customer_action": "Send vague one-line inquiry",
        "ira_action": "Ask qualifying questions",
    },
    {
        "stage": "qualification",
        "customer_action": "Provide some specs (not all)",
        "ira_action": "Ask follow-up for missing details",
    },
    {
        "stage": "full_specs",
        "customer_action": "Provide remaining specs",
        "ira_action": "Recommend specific machine",
    },
    {
        "stage": "feature_questions",
        "customer_action": "Ask about machine features",
        "ira_action": "Explain features and benefits",
    },
    {
        "stage": "pricing_request",
        "customer_action": "Ask for price quote",
        "ira_action": "Provide pricing with terms",
    },
    {
        "stage": "negotiation",
        "customer_action": "Negotiate or ask for clarification",
        "ira_action": "Respond professionally",
    },
]


# =============================================================================
# GMAIL HELPERS
# =============================================================================

IRA_EMAIL = "ira@machinecraft.org"
RUSHABH_EMAIL = "rushabh@machinecraft.org"
REPLY_WAIT_SECONDS = 60
MAX_WAIT_RETRIES = 8


def get_gmail_service():
    token_file = PROJECT_ROOT / "token_rushabh.json"
    if not token_file.exists():
        token_file = PROJECT_ROOT / "token.json"
    creds = Credentials.from_authorized_user_file(str(token_file))
    return build('gmail', 'v1', credentials=creds)


def send_email(service, subject: str, body: str, thread_id: str = None) -> dict:
    msg = MIMEText(body)
    msg['to'] = IRA_EMAIL
    msg['from'] = RUSHABH_EMAIL
    msg['subject'] = subject
    
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    body_data = {'raw': raw}
    if thread_id:
        body_data['threadId'] = thread_id
    
    return service.users().messages().send(userId='me', body=body_data).execute()


def wait_for_reply(service, thread_id: str, subject_pattern: str = None, prev_ira_ids: set = None) -> Optional[str]:
    """Wait for IRA's reply - check by subject pattern since Gmail threading can fail."""
    
    if prev_ira_ids is None:
        prev_ira_ids = set()
    
    for attempt in range(MAX_WAIT_RETRIES):
        time.sleep(REPLY_WAIT_SECONDS)
        
        # First try thread-based lookup
        try:
            thread = service.users().threads().get(userId='me', id=thread_id).execute()
            messages = thread.get('messages', [])
            
            for msg in reversed(messages):
                headers = {h['name'].lower(): h['value'] for h in msg['payload']['headers']}
                if 'ira' in headers.get('from', '').lower():
                    body = extract_body(msg['payload'])
                    if body and len(body) > 50:
                        return body
        except Exception as e:
                logger = __import__('logging').getLogger(__name__)
                logger.warning("Gmail search failed: %s", e, exc_info=True)
        
        # Fallback: search for ANY recent reply from IRA with matching subject
        if subject_pattern:
            try:
                # Search for recent IRA emails
                q = f"from:ira@machinecraft.org newer_than:5m"
                results = service.users().messages().list(userId='me', q=q, maxResults=10).execute()
                msgs = results.get('messages', [])
                
                for msg_info in msgs:
                    if msg_info['id'] in prev_ira_ids:
                        continue
                    
                    msg = service.users().messages().get(userId='me', id=msg_info['id']).execute()
                    headers = {h['name'].lower(): h['value'] for h in msg['payload']['headers']}
                    subject = headers.get('subject', '')
                    
                    # Check if this matches our simulation
                    if subject_pattern in subject and 'ira' in headers.get('from', '').lower():
                        body = extract_body(msg['payload'])
                        if body and len(body) > 50:
                            prev_ira_ids.add(msg_info['id'])
                            print(f"   ✅ Found IRA reply")
                            return body
            except Exception as e:
                print(f"   Search error: {e}")
        
        print(f"   ⏳ Waiting... ({attempt + 1}/{MAX_WAIT_RETRIES})")
    
    return None


def extract_body(payload: dict) -> str:
    if 'body' in payload and payload['body'].get('data'):
        return base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8', errors='ignore')
    
    if 'parts' in payload:
        for part in payload['parts']:
            if part['mimeType'] == 'text/plain' and part['body'].get('data'):
                return base64.urlsafe_b64decode(part['body']['data']).decode('utf-8', errors='ignore')
            if 'parts' in part:
                result = extract_body(part)
                if result:
                    return result
    return ""


# =============================================================================
# CREATIVE CUSTOMER AGENT (plays as Rushabh)
# =============================================================================

class CreativeRushabh:
    """
    Plays the role of the customer (Rushabh simulating a real inquiry).
    Generates realistic emails based on current stage and IRA's responses.
    """
    
    def __init__(self, customer_key: str):
        self.customer = REAL_CUSTOMERS[customer_key]
        self.stage_idx = 0
        self.conversation = []
        self.specs_revealed = set()  # Track what info has been shared
    
    @property
    def current_stage(self) -> str:
        if self.stage_idx < len(CONVERSATION_FLOW):
            return CONVERSATION_FLOW[self.stage_idx]["stage"]
        return "complete"
    
    def generate_email(self, ira_last_response: str = None) -> Dict:
        """Generate the next customer email based on stage."""
        
        stage = self.current_stage
        customer = self.customer
        
        if stage == "initial_inquiry":
            # ONE LINE inquiry - vague, no specs
            return self._generate_initial_inquiry()
        
        elif stage == "qualification":
            # Respond to IRA's questions with SOME specs
            return self._generate_partial_specs(ira_last_response)
        
        elif stage == "full_specs":
            # Provide remaining specs
            return self._generate_full_specs(ira_last_response)
        
        elif stage == "feature_questions":
            # Ask about specific features
            return self._generate_feature_question(ira_last_response)
        
        elif stage == "pricing_request":
            # Ask for price
            return self._generate_price_request(ira_last_response)
        
        elif stage == "negotiation":
            # Final negotiation or acceptance
            return self._generate_negotiation(ira_last_response)
        
        return {"subject": "Thanks", "body": "Thanks for your help!"}
    
    def _generate_initial_inquiry(self) -> Dict:
        """Generate a vague one-line inquiry."""
        customer = self.customer
        
        one_liners = [
            f"Hi, I'm looking for a thermoforming machine for {customer['industry'].lower()} applications. Can you help?",
            f"We need a vacuum forming machine. Please share details.",
            f"Looking for a single sheet forming machine for our {customer['industry'].lower()} parts.",
            f"Hi team, need a quote for a thermoforming machine.",
            f"Interested in your PF1 series for {customer['industry'].lower()} industry.",
        ]
        
        import random
        body = random.choice(one_liners)
        body += f"\n\nThanks,\n{customer['name']}\n{customer['company']}"
        
        return {
            "subject": f"Inquiry - Thermoforming Machine",
            "body": body,
        }
    
    def _generate_partial_specs(self, ira_response: str) -> Dict:
        """Respond with some but not all specs."""
        customer = self.customer
        
        # Reveal forming area and material (not depth and thickness yet)
        self.specs_revealed.add("forming_area")
        self.specs_revealed.add("materials")
        
        body = f"""Thanks for the quick response.

Our requirements:
- Forming area: {customer['forming_area']}
- Material: {customer['materials']}
- Industry: {customer['industry']}

Can you suggest something?

{customer['name']}"""
        
        return {
            "subject": "Re: Inquiry - Thermoforming Machine",
            "body": body,
        }
    
    def _generate_full_specs(self, ira_response: str) -> Dict:
        """Provide remaining specs."""
        customer = self.customer
        
        self.specs_revealed.add("depth")
        self.specs_revealed.add("thickness")
        
        body = f"""Hi,

Sorry, missed some details. Here's the complete requirement:

- Forming area: {customer['forming_area']}
- Draw depth: {customer['depth']}
- Sheet thickness: {customer['thickness']}
- Material: {customer['materials']}

This is for {customer['industry'].lower()} enclosures. We need good surface finish.

What machine do you recommend?

{customer['name']}"""
        
        return {
            "subject": "Re: Inquiry - Thermoforming Machine",
            "body": body,
        }
    
    def _generate_feature_question(self, ira_response: str) -> Dict:
        """Ask about specific machine features."""
        customer = self.customer
        
        questions = [
            "What heating system does this use? Is it ceramic or quartz?",
            "What's the vacuum pump capacity? We need good draw for PMMA.",
            "Does it have servo drives or pneumatic?",
            "What's the cycle time for 6mm PMMA sheets?",
            "Is the heater system zoned for better control?",
        ]
        
        import random
        question = random.choice(questions)
        
        body = f"""Thanks for the recommendation.

{question}

Also, what's the typical delivery time?

{customer['name']}"""
        
        return {
            "subject": "Re: Inquiry - Thermoforming Machine",
            "body": body,
        }
    
    def _generate_price_request(self, ira_response: str) -> Dict:
        """Ask for pricing."""
        customer = self.customer
        
        body = f"""Thanks for the details.

Please share the price for this machine with:
- Full installation
- Training
- Warranty terms

What are your payment terms?

{customer['name']}
{customer['company']}"""
        
        return {
            "subject": "Re: Inquiry - Thermoforming Machine",
            "body": body,
        }
    
    def _generate_negotiation(self, ira_response: str) -> Dict:
        """Final negotiation."""
        customer = self.customer
        
        body = f"""Thank you for the offer.

The specs look good. Can you give us a better price? We're planning to order this quarter if the numbers work.

Also, what's included in the installation cost?

{customer['name']}"""
        
        return {
            "subject": "Re: Inquiry - Thermoforming Machine",
            "body": body,
        }
    
    def record_ira_response(self, response: str):
        """Record IRA's response and advance stage."""
        self.conversation.append({
            "role": "ira",
            "content": response,
            "stage": self.current_stage,
        })
    
    def advance_stage(self):
        """Move to next stage."""
        self.stage_idx += 1


# =============================================================================
# EVALUATOR (Rushabh coaching IRA)
# =============================================================================

def evaluate_ira_response(ira_response: str, stage: str, customer: Dict) -> Dict:
    """Evaluate IRA's response and extract learning."""
    
    prompt = f"""You are Rushabh, coaching IRA on her sales response.

CUSTOMER: {customer['name']} ({customer['company']})
INDUSTRY: {customer['industry']}
FULL REQUIREMENTS:
- Forming area: {customer['forming_area']}
- Depth: {customer['depth']}
- Thickness: {customer['thickness']}
- Material: {customer['materials']}

EXPECTED MACHINE: {customer['expected_machine']}
EXPECTED PRICE RANGE: {customer['expected_price_range']}

CURRENT STAGE: {stage}

IRA'S RESPONSE:
{ira_response[:800]}

Evaluate IRA's response:

1. Did IRA ask the right qualifying questions? (for early stages)
2. Did IRA recommend the correct machine? (for recommendation stage)
3. Was the pricing appropriate? (for pricing stage)
4. Was the response professional and helpful?

Output JSON:
{{
    "score": 1-10,
    "did_right": ["What IRA did well"],
    "needs_improvement": ["What to improve"],
    "learning_for_ira": "One specific lesson for IRA to apply next time",
    "machine_recommended": "Which machine IRA recommended (if any)",
    "machine_correct": true/false
}}"""
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You evaluate sales AI responses. Be constructive."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"Evaluation error: {e}")
        return {"score": 5, "learning_for_ira": "Continue improving."}


# =============================================================================
# LEARNING INJECTOR
# =============================================================================

class LearningInjector:
    """Inject learnings into IRA's memory."""
    
    def __init__(self):
        self.learnings_file = PROJECT_ROOT / "data" / "training" / "realistic_sim_learnings.json"
        self.learnings_file.parent.mkdir(parents=True, exist_ok=True)
        self.learnings = []
    
    def inject(self, learning: str, stage: str, score: int):
        self.learnings.append({
            "timestamp": datetime.now().isoformat(),
            "stage": stage,
            "score": score,
            "learning": learning,
        })
        self._save()
    
    def _save(self):
        with open(self.learnings_file, 'w') as f:
            json.dump(self.learnings, f, indent=2)


# =============================================================================
# MAIN SIMULATION
# =============================================================================

def run_realistic_simulation(customer_key: str = "vignesh_telecom", max_turns: int = 6):
    """Run a realistic sales conversation simulation."""
    
    customer = REAL_CUSTOMERS.get(customer_key)
    if not customer:
        print(f"Unknown customer: {customer_key}")
        return
    
    print(f"""
╔══════════════════════════════════════════════════════════════════════╗
║     🎭 REALISTIC SALES SIMULATION - Natural Conversation Flow       ║
╠══════════════════════════════════════════════════════════════════════╣
║  Customer: {customer['name']:<56} ║
║  Company:  {customer['company']:<56} ║
║  Industry: {customer['industry']:<56} ║
║  Location: {customer['location']:<56} ║
╠══════════════════════════════════════════════════════════════════════╣
║  Expected: {customer['expected_machine']:<56} ║
║  Price:    {customer['expected_price_range']:<56} ║
╚══════════════════════════════════════════════════════════════════════╝

CONVERSATION FLOW:
  1. One-line inquiry → IRA asks questions
  2. Partial specs → IRA asks for more
  3. Full specs → IRA recommends machine
  4. Feature Q&A → IRA explains
  5. Price request → IRA sends offer
  6. Negotiation → IRA responds
""")
    
    gmail = get_gmail_service()
    agent = CreativeRushabh(customer_key)
    injector = LearningInjector()
    
    log = {
        "customer": customer_key,
        "started": datetime.now().isoformat(),
        "turns": [],
        "learnings": [],
    }
    
    thread_id = None
    ira_last_response = None
    turn = 0
    
    while turn < max_turns and agent.current_stage != "complete":
        turn += 1
        stage = agent.current_stage
        
        print(f"\n{'═' * 70}")
        print(f"  TURN {turn} | Stage: {stage.upper()}")
        print(f"{'═' * 70}")
        
        # Generate customer email
        email = agent.generate_email(ira_last_response)
        
        print(f"\n📧 CUSTOMER ({customer['name']}):")
        print(f"   {email['body'][:200]}...")
        
        # Send real email
        subject = email['subject']
        if turn > 1 and not subject.startswith('Re:'):
            subject = f"Re: {subject}"
        
        training_id = datetime.now().strftime("%m%d%H%M")
        sim_tag = f"SIM-{training_id}"
        if '[SIM' not in subject:
            subject = f"[{sim_tag}] {subject}"
        else:
            # Extract existing sim tag from subject
            import re
            match = re.search(r'\[SIM-(\d+)\]', subject)
            if match:
                sim_tag = f"SIM-{match.group(1)}"
        
        result = send_email(gmail, subject, email['body'], thread_id)
        
        if not thread_id:
            thread_id = result.get('threadId')
        
        print(f"   ✉️ Sent to IRA")
        
        # Record customer email
        agent.conversation.append({
            "role": "customer",
            "content": email['body'],
            "stage": stage,
        })
        
        # Wait for IRA
        print(f"\n⏳ Waiting for IRA...")
        ira_response = wait_for_reply(gmail, thread_id, subject_pattern=sim_tag)
        
        if not ira_response:
            print("   ❌ No response from IRA")
            break
        
        print(f"\n🤖 IRA:")
        print(f"   {ira_response[:300]}...")
        
        # Record and evaluate
        agent.record_ira_response(ira_response)
        
        print(f"\n📊 EVALUATION:")
        evaluation = evaluate_ira_response(ira_response, stage, customer)
        
        score = evaluation.get('score', 5)
        print(f"   Score: {'█' * score}{'░' * (10-score)} {score}/10")
        
        if evaluation.get('did_right'):
            print(f"   ✓ Good: {evaluation['did_right'][0]}")
        
        if evaluation.get('needs_improvement'):
            print(f"   → Improve: {evaluation['needs_improvement'][0]}")
        
        # Inject learning
        learning = evaluation.get('learning_for_ira', '')
        if learning:
            print(f"\n💡 LEARNING: {learning[:80]}...")
            injector.inject(learning, stage, score)
            log['learnings'].append(learning)
        
        # Log turn
        log['turns'].append({
            "turn": turn,
            "stage": stage,
            "customer": email['body'][:300],
            "ira": ira_response[:500],
            "score": score,
            "evaluation": evaluation,
        })
        
        # Advance
        agent.advance_stage()
        ira_last_response = ira_response
    
    # Save log
    log['ended'] = datetime.now().isoformat()
    output_dir = PROJECT_ROOT / "data" / "realistic_simulations"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"sim_{customer_key}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    with open(output_file, 'w') as f:
        json.dump(log, f, indent=2)
    
    print(f"""
╔══════════════════════════════════════════════════════════════════════╗
║                    🏁 SIMULATION COMPLETE                            ║
╠══════════════════════════════════════════════════════════════════════╣
║  Turns: {turn:<61} ║
║  Learnings: {len(log['learnings']):<57} ║
║  Log: {str(output_file)[-60:]:<60} ║
╚══════════════════════════════════════════════════════════════════════╝
""")
    
    return log


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Realistic Sales Simulation")
    parser.add_argument("--customer", default="vignesh_telecom",
                       choices=list(REAL_CUSTOMERS.keys()))
    parser.add_argument("--turns", type=int, default=6)
    parser.add_argument("--auto", action="store_true")
    
    args = parser.parse_args()
    
    if not args.auto:
        print("\n⚠️  Make sure IRA's email bridge is running:")
        print("   python scripts/email_openclaw_bridge.py --loop\n")
        input("Press Enter to start...")
    
    run_realistic_simulation(args.customer, args.turns)
