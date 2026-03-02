#!/usr/bin/env python3
"""
REAL EMAIL TRAINING LOOP
========================

Creates ACTUAL email conversations between Creative Agent (as customer) and IRA.

Flow:
1. Creative Agent drafts customer email based on persona & sales stage
2. Sends REAL email from rushabh@machinecraft.org TO ira@machinecraft.org
3. Waits for IRA to respond (via email_openclaw_bridge)
4. Creative Agent evaluates IRA's response, extracts learnings
5. Generates next customer email continuing the sales cycle
6. Loop until deal closes or max turns

All emails are visible in Rushabh's Gmail inbox for review.

Usage:
    # Make sure IRA's email bridge is running first:
    python scripts/email_openclaw_bridge.py --loop &
    
    # Then run training:
    python agents/apollo/real_email_training.py --persona startup
    python agents/apollo/real_email_training.py --persona european --turns 6
"""

import os
import sys
import json
import time
import base64
import re
from pathlib import Path
from datetime import datetime
from email.mime.text import MIMEText
from typing import List, Dict, Optional

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

import openai
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# IRA's memory for learning injection
try:
    from mem0 import Memory
    MEM0_AVAILABLE = True
except ImportError:
    MEM0_AVAILABLE = False
    Memory = None


# =============================================================================
# LIVE LEARNING INJECTOR
# =============================================================================

class IraLearningInjector:
    """
    Injects learnings directly into IRA's memory so she can use them
    immediately in subsequent responses.
    
    Goal: Help IRA guide customers efficiently to a final proposal
    (machine model + specs + price).
    """
    
    def __init__(self):
        self.memory = None
        self.learnings_file = PROJECT_ROOT / "data" / "training" / "live_learnings.json"
        self.learnings_file.parent.mkdir(parents=True, exist_ok=True)
        self.accumulated_learnings = []
        
        if MEM0_AVAILABLE:
            try:
                self.memory = Memory.from_config({
                    "llm": {"provider": "openai", "config": {"model": "gpt-4o-mini"}},
                    "version": "v1.1"
                })
                print("   ✅ Memory injector connected")
            except Exception as e:
                print(f"   ⚠️ Memory init failed: {e}")
    
    def inject_learning(self, learning: str, context: Dict) -> bool:
        """
        Inject a learning into IRA's memory for immediate use.
        
        Returns True if successfully injected.
        """
        # Format the learning with context
        formatted_learning = self._format_learning(learning, context)
        
        # Store in file (always works)
        self.accumulated_learnings.append({
            "timestamp": datetime.now().isoformat(),
            "learning": learning,
            "formatted": formatted_learning,
            "context": {
                "persona": context.get("persona", "unknown"),
                "stage": context.get("stage", "unknown"),
                "score": context.get("score", 0),
            }
        })
        self._save_learnings()
        
        # Try to inject into Mem0
        if self.memory:
            try:
                self.memory.add(
                    messages=[{"role": "user", "content": formatted_learning}],
                    user_id="ira_training",
                    metadata={
                        "type": "sales_learning",
                        "source": "apollo_training",
                        "stage": context.get("stage", ""),
                    }
                )
                return True
            except Exception as e:
                print(f"   ⚠️ Memory injection failed: {e}")
        
        return False
    
    def _format_learning(self, learning: str, context: Dict) -> str:
        """Format learning for memory storage."""
        stage = context.get("stage", "general")
        persona_type = context.get("persona_type", "startup")
        
        return f"""SALES TRAINING LEARNING [{stage.upper()}]:
Customer Type: {persona_type}
Learning: {learning}

Apply this in future {stage} conversations to guide customers efficiently to a proposal."""
    
    def _save_learnings(self):
        """Save accumulated learnings to file."""
        try:
            with open(self.learnings_file, 'w') as f:
                json.dump(self.accumulated_learnings, f, indent=2)
        except Exception as e:
            print(f"   ⚠️ Failed to save learnings: {e}")
    
    def inject_proposal_guidance(self, machine_recommended: str, was_correct: bool, 
                                  customer_budget: str, customer_needs: Dict):
        """
        Inject specific guidance about machine recommendations and proposals.
        
        This helps IRA learn which machines to recommend for specific budgets
        and how to move customers toward a proposal.
        """
        if was_correct:
            guidance = f"""SUCCESSFUL RECOMMENDATION:
Machine: {machine_recommended}
Budget: {customer_budget}
Needs: {customer_needs}
Result: Customer accepted recommendation. Continue this pattern for similar requirements."""
        else:
            guidance = f"""RECOMMENDATION IMPROVEMENT NEEDED:
Machine Recommended: {machine_recommended}
Budget: {customer_budget}
Needs: {customer_needs}
Issue: Machine didn't match customer requirements.
Action: For this budget/requirement profile, recommend smaller/more affordable options first."""
        
        self.inject_learning(guidance, {
            "stage": "proposal",
            "persona_type": customer_needs.get("industry", "general"),
            "score": 10 if was_correct else 3,
        })


# =============================================================================
# CONFIG
# =============================================================================

IRA_EMAIL = "ira@machinecraft.org"
RUSHABH_EMAIL = "rushabh@machinecraft.org"
REPLY_WAIT_SECONDS = 90  # Wait for IRA to process and reply
MAX_WAIT_RETRIES = 8

client = openai.OpenAI()


# =============================================================================
# PERSONAS WITH CORRECT MACHINE EXPECTATIONS
# =============================================================================

TRAINING_PERSONAS = {
    "startup": {
        "name": "Mike Chen",
        "company": "PackForm Solutions",
        "role": "Founder",
        "location": "Toronto, Canada",
        "industry": "Sustainable Packaging Startup",
        "email_style": "Casual, enthusiastic, asks for guidance",
        "requirements": {
            "forming_area": "600 x 900 mm",
            "depth": "300 mm",
            "thickness": "up to 3mm",
            "materials": "PETG, rPET (recycled)",
        },
        "budget": "USD 60,000",
        "budget_inr": 5000000,  # ~50L INR / ~$60K USD
        "expected_machines": ["PF1-C-1309", "PF1-C-1008"],  # Entry-level PF1 fits $60K budget for 600x900mm
        "NOT_suitable": ["PF1-C-2515", "PF1-X-2015", "PF2-P2020"],  # Too big/expensive
        "sales_cycle": ["first_contact", "discovery", "technical", "quote", "negotiation", "closing"],
        "personality_prompt": """You are Mike Chen, a startup founder with limited budget but big dreams.
You're new to thermoforming and need guidance. You ask practical questions about:
- Entry-level machines that fit your budget
- Training and support for beginners
- Financing options
- Total cost of ownership
You're enthusiastic but budget-conscious. You push back on expensive options.""",
    },
    "european": {
        "name": "Jean-François Deltenre",
        "company": "Plastiform Belgium NV",
        "role": "Technical Director",
        "location": "Belgium",
        "industry": "Automotive Interior",
        "email_style": "Formal, technical, detail-oriented",
        "requirements": {
            "forming_area": "2000 x 1500 mm",
            "depth": "650 mm",
            "thickness": "up to 8mm",
            "materials": "ABS, TPO, PP",
        },
        "budget": "EUR 200,000",
        "budget_inr": 18000000,  # ~1.8Cr INR
        "expected_machines": ["PF1-X-2015", "PF1-X-2116", "PF1-C-2015"],
        "NOT_suitable": ["AM series", "UNO", "DUO"],  # Too small
        "sales_cycle": ["first_contact", "discovery", "technical", "factory_visit", "quote", "negotiation", "closing"],
        "personality_prompt": """You are Jean-François, a technical director replacing an old ILLIG machine.
You're experienced and ask detailed technical questions about:
- Servo vs pneumatic systems
- Energy consumption comparisons
- Cycle times for specific materials
- European service support
- References in automotive sector
You compare to competitors (ILLIG, Kiefel) and want data to justify the purchase.""",
    },
    "indian_auto": {
        "name": "Rajesh Sharma",
        "company": "AutoPlast Components Pvt Ltd",
        "role": "VP Operations",
        "location": "Pune, India",
        "industry": "Automotive Tier-1 Supplier",
        "email_style": "Professional, price-focused, deadline-driven",
        "requirements": {
            "forming_area": "1500 x 1200 mm",
            "depth": "500 mm",
            "thickness": "up to 6mm",
            "materials": "ABS+PMMA, TPO",
        },
        "budget": "INR 1 Crore",
        "budget_inr": 10000000,
        "expected_machines": ["PF1-X-1510", "PF1-C-1510", "PF1-X-1208"],
        "NOT_suitable": ["AM series", "PF2"],
        "sales_cycle": ["first_contact", "discovery", "technical", "quote", "negotiation", "closing"],
        "personality_prompt": """You are Rajesh, setting up a new thermoforming line for dashboard components.
You have OEM approval pressure and tight deadlines. You ask about:
- OEM certifications and quality standards
- Delivery timeline
- Installation and training
- Payment terms
You negotiate hard on price and want best value.""",
    },
}


# =============================================================================
# SALES STAGE PROMPTS
# =============================================================================

STAGE_PROMPTS = {
    "first_contact": """This is your FIRST email to Machinecraft.
Introduce yourself, your company, and your basic requirements.
Ask about suitable machines and request initial information.
Keep it concise - this is just an inquiry.""",

    "discovery": """IRA has responded to your initial inquiry.
Now ask more specific questions about:
- Materials compatibility
- Technical specifications
- Application suitability
Show you're seriously evaluating options.""",

    "technical": """You're in technical discussions now.
Ask detailed technical questions about:
- Cycle times, heater systems, vacuum capacity
- Specific features relevant to your application
- Comparisons if IRA mentioned multiple options
Request spec sheets or technical documentation.""",

    "factory_visit": """You're interested and want to see the machine.
Ask about:
- Factory visit or reference site visit
- Demo or video of the machine running
- Customer references you can contact
This is a strong buying signal.""",

    "quote": """You want pricing now.
Request a formal quotation with:
- Complete pricing breakdown
- Payment terms
- Delivery timeline
- What's included (installation, training, warranty)""",

    "negotiation": """You've received the quote. Now negotiate.
Depending on your persona:
- Push back on price
- Ask for better payment terms
- Request additional inclusions
- Compare to competitor pricing
But stay realistic - don't be unreasonable.""",

    "closing": """You're ready to move forward (or decline).
Either:
- Accept and ask for proforma invoice
- Request final adjustments before confirming
- OR politely decline with a reason
Make this the natural conclusion of the conversation.""",
}


# =============================================================================
# GMAIL HELPERS  
# =============================================================================

def get_gmail_service():
    """Get Gmail service using Rushabh's token."""
    token_file = PROJECT_ROOT / "token_rushabh.json"
    if not token_file.exists():
        token_file = PROJECT_ROOT / "token.json"
    
    creds = Credentials.from_authorized_user_file(str(token_file))
    return build('gmail', 'v1', credentials=creds)


def send_email(service, subject: str, body: str, thread_id: str = None, 
               message_id: str = None) -> dict:
    """Send email from Rushabh to IRA."""
    
    msg = MIMEText(body)
    msg['to'] = IRA_EMAIL
    msg['from'] = RUSHABH_EMAIL
    msg['subject'] = subject
    
    # Add threading headers if replying
    if message_id:
        msg['In-Reply-To'] = message_id
        msg['References'] = message_id
    
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    
    body_data = {'raw': raw}
    if thread_id:
        body_data['threadId'] = thread_id
    
    result = service.users().messages().send(userId='me', body=body_data).execute()
    print(f"   ✉️  Sent email: {subject[:50]}...")
    return result


def wait_for_ira_reply(service, thread_id: str, sent_time: datetime) -> Optional[Dict]:
    """Wait for IRA to reply to the thread."""
    
    print(f"   ⏳ Waiting for IRA's response...")
    
    for attempt in range(MAX_WAIT_RETRIES):
        time.sleep(REPLY_WAIT_SECONDS)
        
        # Get thread messages
        thread = service.users().threads().get(userId='me', id=thread_id).execute()
        messages = thread.get('messages', [])
        
        # Look for IRA's reply (after our sent time)
        for msg in reversed(messages):
            headers = {h['name'].lower(): h['value'] for h in msg['payload']['headers']}
            from_addr = headers.get('from', '')
            
            # Check if this is from IRA
            if 'ira' in from_addr.lower():
                msg_date = headers.get('date', '')
                
                # Get message body
                body = extract_body(msg['payload'])
                
                if body and len(body) > 50:  # Valid response
                    print(f"   ✅ IRA replied! ({len(body)} chars)")
                    return {
                        'id': msg['id'],
                        'body': body,
                        'subject': headers.get('subject', ''),
                    }
        
        print(f"   ⏳ Still waiting... (attempt {attempt + 1}/{MAX_WAIT_RETRIES})")
    
    print(f"   ❌ No reply from IRA after {MAX_WAIT_RETRIES * REPLY_WAIT_SECONDS}s")
    return None


def extract_body(payload: dict) -> str:
    """Extract plain text body from email payload."""
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
# CREATIVE AGENT
# =============================================================================

class CreativeCustomerAgent:
    """Generates customer emails and evaluates IRA's responses."""
    
    def __init__(self, persona_key: str):
        self.persona = TRAINING_PERSONAS[persona_key]
        self.conversation_history: List[Dict] = []
        self.current_stage_idx = 0
        self.stages = self.persona["sales_cycle"]
        self.learnings: List[str] = []
    
    @property
    def current_stage(self) -> str:
        if self.current_stage_idx < len(self.stages):
            return self.stages[self.current_stage_idx]
        return "closing"
    
    def generate_customer_email(self, ira_last_response: str = None) -> Dict:
        """Generate the next customer email based on persona and stage."""
        
        history_text = ""
        if self.conversation_history:
            for turn in self.conversation_history[-3:]:
                role = "CUSTOMER" if turn['role'] == 'customer' else "IRA"
                history_text += f"\n[{role}]: {turn['content'][:300]}...\n"
        
        stage_prompt = STAGE_PROMPTS.get(self.current_stage, "Continue the conversation naturally.")
        
        prompt = f"""You are playing the role of a customer emailing Machinecraft about thermoforming machines.

{self.persona['personality_prompt']}

YOUR REQUIREMENTS:
- Forming area: {self.persona['requirements']['forming_area']}
- Materials: {self.persona['requirements']['materials']}
- Budget: {self.persona['budget']}

MACHINES THAT WOULD FIT YOUR NEEDS:
{', '.join(self.persona['expected_machines'])}

MACHINES TOO BIG/EXPENSIVE FOR YOU:
{', '.join(self.persona['NOT_suitable'])}

CURRENT SALES STAGE: {self.current_stage}
{stage_prompt}

CONVERSATION SO FAR:
{history_text}

{f"IRA'S LAST RESPONSE:{chr(10)}{ira_last_response[:800]}" if ira_last_response else "This is your first email."}

Write a realistic email as {self.persona['name']}.
Style: {self.persona['email_style']}

Output JSON:
{{
    "subject": "Email subject line",
    "body": "Full email body with greeting and signature",
    "questions_asked": ["List of questions"],
    "buying_signals": ["Any positive signals"],
    "objections": ["Any concerns raised"]
}}"""
        
        try:
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You write realistic B2B sales emails."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.7,
            )
            
            result = json.loads(response.choices[0].message.content)
            
            # Add signature with training tag
            body = result.get('body', '')
            if '[TRAINING' not in body:
                body += f"\n\n---\n{self.persona['name']}\n{self.persona['role']}\n{self.persona['company']}\n{self.persona['location']}\n[APOLLO Training Simulation]"
            result['body'] = body
            
            # Record in history
            self.conversation_history.append({
                'role': 'customer',
                'content': result['body'],
                'stage': self.current_stage,
            })
            
            return result
            
        except Exception as e:
            print(f"Error generating email: {e}")
            return self._fallback_email()
    
    def _fallback_email(self) -> Dict:
        """Fallback template email."""
        return {
            "subject": f"Inquiry from {self.persona['company']}",
            "body": f"""Dear Machinecraft Team,

I am {self.persona['name']}, {self.persona['role']} at {self.persona['company']}.

We are looking for a thermoforming machine with:
- Forming area: {self.persona['requirements']['forming_area']}
- Materials: {self.persona['requirements']['materials']}
- Budget: {self.persona['budget']}

Please advise on suitable options.

Best regards,
{self.persona['name']}
{self.persona['company']}
[APOLLO Training Simulation]""",
            "questions_asked": ["What machines do you recommend?"],
            "buying_signals": [],
            "objections": [],
        }
    
    def evaluate_ira_response(self, ira_response: str, customer_email: Dict) -> Dict:
        """Evaluate IRA's response and extract learnings."""
        
        prompt = f"""You are Rushabh, the sales expert at Machinecraft, evaluating IRA's email response.

CUSTOMER: {self.persona['name']} ({self.persona['company']})
REQUIREMENTS: {self.persona['requirements']}
BUDGET: {self.persona['budget']}

SUITABLE MACHINES FOR THIS CUSTOMER:
{', '.join(self.persona['expected_machines'])}

NOT SUITABLE (too big/expensive):
{', '.join(self.persona['NOT_suitable'])}

CUSTOMER'S EMAIL:
{customer_email.get('body', '')[:500]}

Questions asked: {customer_email.get('questions_asked', [])}

IRA'S RESPONSE:
{ira_response}

GOAL: Help customer arrive at a FINAL PROPOSAL with:
1. Machine model recommendation
2. Technical specifications
3. Price quote

Evaluate IRA's response:

1. Did IRA recommend appropriate machines for this customer's size/budget?
2. Did IRA address the customer's questions?
3. Is IRA moving the customer toward a proposal?
4. Did IRA provide specs and pricing when appropriate?
5. Any incorrect information or missed opportunities?

Output JSON:
{{
    "score": 1-10,
    "machine_recommendation_correct": true/false,
    "machine_recommended": "What machine IRA recommended (if any)",
    "should_have_recommended": "What machine would be best",
    "questions_addressed": ["Which questions were answered"],
    "questions_missed": ["Which questions were not answered"],
    "what_ira_did_well": ["Positives"],
    "improvements_needed": ["Areas to improve"],
    "learning_for_ira": "A concise lesson for IRA to improve",
    "advance_stage": true/false,
    "proposal_progress": {{
        "machine_model_given": true/false,
        "specs_provided": true/false,
        "price_quoted": true/false,
        "ready_for_proposal": true/false
    }},
    "coaching_feedback": "Specific actionable advice for IRA's next response"
}}"""
        
        try:
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You evaluate sales responses objectively."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.3,
            )
            
            result = json.loads(response.choices[0].message.content)
            
            # Store learning
            if result.get('learning_for_ira'):
                self.learnings.append({
                    'stage': self.current_stage,
                    'learning': result['learning_for_ira'],
                    'score': result.get('score', 5),
                })
            
            return result
            
        except Exception as e:
            print(f"Error evaluating: {e}")
            return {"score": 5, "advance_stage": True}
    
    def record_ira_response(self, response: str):
        """Record IRA's response in history."""
        self.conversation_history.append({
            'role': 'ira',
            'content': response,
            'stage': self.current_stage,
        })
    
    def advance_stage(self, evaluation: Dict):
        """Move to next stage based on evaluation."""
        if evaluation.get('advance_stage', True):
            self.current_stage_idx += 1
    
    def is_complete(self) -> bool:
        """Check if conversation is complete."""
        return self.current_stage_idx >= len(self.stages)


# =============================================================================
# MAIN TRAINING LOOP
# =============================================================================

def run_real_email_training(
    persona_key: str = "startup",
    max_turns: int = 6,
):
    """Run the real email training loop."""
    
    persona = TRAINING_PERSONAS.get(persona_key)
    if not persona:
        print(f"Unknown persona: {persona_key}")
        return
    
    print(f"""
╔══════════════════════════════════════════════════════════════════════╗
║            📧 REAL EMAIL TRAINING SIMULATION                         ║
╠══════════════════════════════════════════════════════════════════════╣
║  Customer: {persona['name']:<56} ║
║  Company:  {persona['company']:<56} ║
║  Budget:   {persona['budget']:<56} ║
║  Expected: {', '.join(persona['expected_machines'][:3]):<56} ║
╠══════════════════════════════════════════════════════════════════════╣
║  ⚠️  REAL EMAILS will be sent to ira@machinecraft.org               ║
║  📬 All emails visible in Rushabh's Gmail inbox                     ║
╚══════════════════════════════════════════════════════════════════════╝
""")
    
    # Initialize
    gmail = get_gmail_service()
    agent = CreativeCustomerAgent(persona_key)
    learning_injector = IraLearningInjector()
    
    training_log = {
        "persona": persona_key,
        "started_at": datetime.now().isoformat(),
        "turns": [],
        "proposal_achieved": False,
        "final_machine": None,
        "total_learnings_injected": 0,
    }
    
    thread_id = None
    message_id = None
    ira_last_response = None
    turn = 0
    
    while not agent.is_complete() and turn < max_turns:
        turn += 1
        
        print(f"\n{'═'*70}")
        print(f"  TURN {turn} | Stage: {agent.current_stage.upper()}")
        print(f"{'═'*70}")
        
        # 1. Generate customer email
        print(f"\n📝 Generating customer email...")
        customer_email = agent.generate_customer_email(ira_last_response)
        
        print(f"\n📧 CUSTOMER ({persona['name']}):")
        print(f"   Subject: {customer_email['subject']}")
        print(f"   {customer_email['body'][:200]}...")
        
        # 2. Send real email
        print(f"\n📤 Sending to {IRA_EMAIL}...")
        
        subject = customer_email['subject']
        if turn > 1 and not subject.startswith('Re:'):
            subject = f"Re: {subject}"
        
        # Add training identifier to subject
        training_id = datetime.now().strftime("%m%d%H%M")
        if '[TRAINING' not in subject:
            subject = f"[TRAINING-{training_id}] {subject}"
        
        result = send_email(
            gmail,
            subject=subject,
            body=customer_email['body'],
            thread_id=thread_id,
            message_id=message_id,
        )
        
        if not thread_id:
            thread_id = result.get('threadId')
        message_id = result.get('id')
        
        # 3. Wait for IRA's response
        ira_reply = wait_for_ira_reply(gmail, thread_id, datetime.now())
        
        if not ira_reply:
            print(f"   ⚠️ No response from IRA, stopping simulation")
            break
        
        ira_response = ira_reply['body']
        agent.record_ira_response(ira_response)
        
        print(f"\n🤖 IRA's Response:")
        print(f"   {ira_response[:300]}...")
        
        # 4. Evaluate response
        print(f"\n📊 EVALUATION:")
        evaluation = agent.evaluate_ira_response(ira_response, customer_email)
        
        score = evaluation.get('score', 5)
        print(f"   Score: {'█' * score}{'░' * (10-score)} {score}/10")
        
        if not evaluation.get('machine_recommendation_correct', True):
            print(f"   ❌ Wrong machine: {evaluation.get('machine_recommended', 'N/A')}")
            print(f"   ✅ Should be: {evaluation.get('should_have_recommended', 'N/A')}")
        
        if evaluation.get('what_ira_did_well'):
            print(f"   ✓ Good: {evaluation['what_ira_did_well'][0] if evaluation['what_ira_did_well'] else 'N/A'}")
        
        if evaluation.get('improvements_needed'):
            print(f"   → Improve: {evaluation['improvements_needed'][0] if evaluation['improvements_needed'] else 'N/A'}")
        
        # Proposal progress tracking
        proposal = evaluation.get('proposal_progress', {})
        print(f"\n📋 PROPOSAL PROGRESS:")
        print(f"   Machine Model: {'✅' if proposal.get('machine_model_given') else '⬜'}")
        print(f"   Tech Specs:    {'✅' if proposal.get('specs_provided') else '⬜'}")
        print(f"   Price Quote:   {'✅' if proposal.get('price_quoted') else '⬜'}")
        
        if proposal.get('ready_for_proposal'):
            print(f"   🎯 READY FOR FINAL PROPOSAL!")
            training_log["proposal_achieved"] = True
            training_log["final_machine"] = evaluation.get('machine_recommended', 'N/A')
        
        # 5. INJECT LEARNING INTO IRA'S MEMORY
        if evaluation.get('learning_for_ira'):
            print(f"\n💡 INJECTING LEARNING:")
            print(f"   {evaluation['learning_for_ira'][:100]}...")
            
            learning_injector.inject_learning(
                learning=evaluation['learning_for_ira'],
                context={
                    "stage": agent.current_stage,
                    "persona": persona['name'],
                    "persona_type": persona.get('industry', 'general'),
                    "score": score,
                }
            )
            training_log["total_learnings_injected"] += 1
            
            # Inject machine recommendation guidance
            if evaluation.get('machine_recommended'):
                learning_injector.inject_proposal_guidance(
                    machine_recommended=evaluation.get('machine_recommended', ''),
                    was_correct=evaluation.get('machine_recommendation_correct', False),
                    customer_budget=persona['budget'],
                    customer_needs=persona['requirements'],
                )
        
        # Coaching feedback for next turn
        if evaluation.get('coaching_feedback'):
            print(f"\n🎯 COACHING FOR NEXT TURN:")
            print(f"   {evaluation['coaching_feedback'][:150]}...")
        
        # Log turn
        training_log["turns"].append({
            "turn": turn,
            "stage": agent.current_stage,
            "customer_email": customer_email,
            "ira_response": ira_response[:1000],
            "evaluation": evaluation,
        })
        
        # 5. Advance stage
        agent.advance_stage(evaluation)
        ira_last_response = ira_response
        
        print(f"\n   → {'Advancing to: ' + agent.current_stage if evaluation.get('advance_stage') else 'Staying at: ' + agent.current_stage}")
    
    # Complete
    training_log["ended_at"] = datetime.now().isoformat()
    training_log["total_turns"] = turn
    training_log["learnings"] = agent.learnings
    
    # Save log
    output_dir = PROJECT_ROOT / "data" / "simulations"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"real_email_{persona_key}_{timestamp}.json"
    
    with open(output_file, 'w') as f:
        json.dump(training_log, f, indent=2)
    
    proposal_status = "✅ ACHIEVED" if training_log["proposal_achieved"] else "⬜ NOT YET"
    final_machine = training_log.get("final_machine", "N/A")
    
    print(f"""
╔══════════════════════════════════════════════════════════════════════╗
║                    🏁 TRAINING COMPLETE                              ║
╠══════════════════════════════════════════════════════════════════════╣
║  Total Turns: {turn:<57} ║
║  Learnings Injected: {training_log['total_learnings_injected']:<49} ║
║  Proposal Status: {proposal_status:<52} ║
║  Final Machine: {final_machine:<54} ║
╠══════════════════════════════════════════════════════════════════════╣
║  Log saved: {str(output_file)[-55:]:<55} ║
╚══════════════════════════════════════════════════════════════════════╝
""")
    
    # Print learnings summary
    if agent.learnings:
        print("\n📚 LEARNINGS SUMMARY:")
        for i, l in enumerate(agent.learnings, 1):
            print(f"   {i}. [{l['stage']}] (Score: {l['score']}/10)")
            print(f"      {l['learning'][:80]}...")
    
    return training_log


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Real Email Training Loop")
    parser.add_argument("--persona", type=str, default="startup",
                       choices=list(TRAINING_PERSONAS.keys()),
                       help="Customer persona")
    parser.add_argument("--turns", type=int, default=6, help="Max conversation turns")
    parser.add_argument("--auto", action="store_true", help="Skip confirmation prompt")
    
    args = parser.parse_args()
    
    if not args.auto:
        print("\n⚠️  IMPORTANT: Make sure IRA's email bridge is running!")
        print("   Run in another terminal: python scripts/email_openclaw_bridge.py --loop\n")
        
        input("Press Enter to start the real email training simulation...")
    
    run_real_email_training(
        persona_key=args.persona,
        max_turns=args.turns,
    )
