#!/usr/bin/env python3
"""
HUMAN TRAINING LOOP
===================

The complete training system that:
1. Uses HumanCreativeAgent to generate realistic customer emails
2. Sends REAL emails to IRA 
3. IRA responds using her full pipeline
4. Creative Agent evaluates and provides coaching
5. Learnings are injected into IRA's memory
6. Loop continues until proposal achieved (machine + specs + price)

GOAL: Train IRA to efficiently guide customers to a final proposal.

HUMANNESS FORMULA:
H = (Mess × 1.5 + Context × 1.5 + Emo × 1.0 + Spec × 1.2 + 
     Pers × 1.0 + Obj × 1.3 + Tech × 1.0) / 7 × 10

Target: H ≥ 15/100 for human-like conversations
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

from human_creative_agent import HumanCreativeAgent, HUMAN_PERSONAS
from conversation_humanness import calculate_humanness, HumannessScore

# Try to import memory injection
try:
    from mem0 import Memory
    MEM0_AVAILABLE = True
except ImportError:
    MEM0_AVAILABLE = False


# =============================================================================
# CONFIG
# =============================================================================

IRA_EMAIL = "ira@machinecraft.org"
RUSHABH_EMAIL = "rushabh@machinecraft.org"
REPLY_WAIT_SECONDS = 60
MAX_WAIT_RETRIES = 10
HUMANNESS_TARGET = 15.0  # Target score for human-like conversation

client = openai.OpenAI()


# =============================================================================
# LEARNING INJECTOR
# =============================================================================

class IraLearningInjector:
    """Inject learnings into IRA's memory for immediate improvement."""
    
    def __init__(self):
        self.learnings_file = PROJECT_ROOT / "data" / "training" / "human_loop_learnings.json"
        self.learnings_file.parent.mkdir(parents=True, exist_ok=True)
        self.learnings = []
        
        self.memory = None
        if MEM0_AVAILABLE:
            try:
                self.memory = Memory.from_config({
                    "llm": {"provider": "openai", "config": {"model": "gpt-4o-mini"}},
                    "version": "v1.1"
                })
            except:
                pass
    
    def inject(self, learning: str, stage: str, score: int):
        """Inject a learning into IRA's memory."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "stage": stage,
            "score": score,
            "learning": learning,
        }
        self.learnings.append(entry)
        self._save()
        
        if self.memory:
            try:
                self.memory.add(
                    messages=[{"role": "user", "content": f"SALES TRAINING [{stage}]: {learning}"}],
                    user_id="ira_training",
                    metadata={"type": "sales_training", "stage": stage}
                )
                return True
            except:
                pass
        return False
    
    def _save(self):
        with open(self.learnings_file, 'w') as f:
            json.dump(self.learnings, f, indent=2)


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


def send_email(service, subject: str, body: str, thread_id: str = None) -> dict:
    """Send email from Rushabh to IRA."""
    msg = MIMEText(body)
    msg['to'] = IRA_EMAIL
    msg['from'] = RUSHABH_EMAIL
    msg['subject'] = subject
    
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    body_data = {'raw': raw}
    if thread_id:
        body_data['threadId'] = thread_id
    
    return service.users().messages().send(userId='me', body=body_data).execute()


def wait_for_reply(service, thread_id: str) -> Optional[str]:
    """Wait for IRA's reply in the thread."""
    for attempt in range(MAX_WAIT_RETRIES):
        time.sleep(REPLY_WAIT_SECONDS)
        
        thread = service.users().threads().get(userId='me', id=thread_id).execute()
        messages = thread.get('messages', [])
        
        for msg in reversed(messages):
            headers = {h['name'].lower(): h['value'] for h in msg['payload']['headers']}
            if 'ira' in headers.get('from', '').lower():
                body = extract_body(msg['payload'])
                if body and len(body) > 50:
                    return body
        
        print(f"   ⏳ Waiting... ({attempt + 1}/{MAX_WAIT_RETRIES})")
    
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
# EVALUATOR
# =============================================================================

def evaluate_ira_response(ira_response: str, customer_email: Dict, persona) -> Dict:
    """Evaluate IRA's response as Rushabh coaching."""
    
    prompt = f"""You are Rushabh, the sales expert at Machinecraft, coaching IRA.

CUSTOMER: {persona.name} ({persona.company})
BUDGET: {persona.budget_display}
REQUIREMENTS: {persona.forming_area}, {persona.materials}, {persona.thickness}

SUITABLE MACHINES: {', '.join(persona.expected_machines)}
NOT SUITABLE (too big/expensive): {', '.join(persona.not_suitable)}

CUSTOMER'S EMAIL:
{customer_email.get('body', '')[:400]}

IRA'S RESPONSE:
{ira_response[:600]}

GOAL: Guide customer to FINAL PROPOSAL with:
1. Machine model recommendation
2. Technical specifications  
3. Price quote

Evaluate IRA's response honestly. Be critical where needed.

Output JSON:
{{
    "score": 1-10,
    "machine_correct": true/false,
    "machine_mentioned": "which machine IRA recommended",
    "proposal_progress": {{
        "machine_model": true/false,
        "specs_provided": true/false,
        "price_quoted": true/false
    }},
    "strengths": ["what IRA did well"],
    "weaknesses": ["what needs improvement"],
    "learning": "One concise lesson for IRA to apply in the next response",
    "advance_stage": true/false
}}"""
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You coach AI sales assistants. Be direct and helpful."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"Evaluation error: {e}")
        return {"score": 5, "advance_stage": True, "learning": "Continue improving."}


# =============================================================================
# MAIN TRAINING LOOP
# =============================================================================

def run_human_training(persona_key: str = "mike_chen", max_turns: int = 5):
    """Run the complete human training loop."""
    
    persona_obj = HUMAN_PERSONAS.get(persona_key)
    if not persona_obj:
        print(f"Unknown persona: {persona_key}")
        return
    
    print(f"""
╔══════════════════════════════════════════════════════════════════════╗
║       🧠 HUMAN TRAINING LOOP - Realistic Sales Simulation           ║
╠══════════════════════════════════════════════════════════════════════╣
║  Customer: {persona_obj.name:<56} ║
║  Style:    {persona_obj.cultural_style:<56} ║
║  Budget:   {persona_obj.budget_display:<56} ║
║  Target:   {', '.join(persona_obj.expected_machines[:3]):<56} ║
╠══════════════════════════════════════════════════════════════════════╣
║  📊 Humanness Target: {HUMANNESS_TARGET}/100                              ║
║  📧 Real emails to: {IRA_EMAIL:<49} ║
╚══════════════════════════════════════════════════════════════════════╝
""")
    
    gmail = get_gmail_service()
    agent = HumanCreativeAgent(persona_key)
    injector = IraLearningInjector()
    
    log = {
        "persona": persona_key,
        "started": datetime.now().isoformat(),
        "turns": [],
        "learnings": [],
        "proposal_achieved": False,
        "humanness_scores": [],
    }
    
    thread_id = None
    ira_last_response = None
    turn = 0
    
    while turn < max_turns and not agent.is_proposal_ready():
        turn += 1
        
        print(f"\n{'═' * 70}")
        print(f"  TURN {turn} | Stage: {agent.current_stage.upper()}")
        print(f"{'═' * 70}")
        
        # 1. Generate human-like customer email
        email = agent.generate_email(ira_last_response)
        
        # Calculate humanness score
        h_score = calculate_humanness(email['body'])
        log['humanness_scores'].append(h_score.total_score)
        
        print(f"\n📧 CUSTOMER ({persona_obj.name}):")
        print(f"   Subject: {email['subject']}")
        print(f"   Humanness: {h_score.total_score:.1f}/100 {'✅' if h_score.total_score >= HUMANNESS_TARGET else '⚠️'}")
        print(f"   Body: {email['body'][:150]}...")
        
        # 2. Send real email
        subject = email['subject']
        if turn > 1 and not subject.startswith('Re:'):
            subject = f"Re: {subject}"
        
        training_id = datetime.now().strftime("%m%d%H%M")
        if '[HUMAN' not in subject:
            subject = f"[HUMAN-{training_id}] {subject}"
        
        result = send_email(gmail, subject, email['body'], thread_id)
        
        if not thread_id:
            thread_id = result.get('threadId')
        
        print(f"   ✉️ Sent to IRA")
        
        # 3. Wait for IRA's response
        print(f"\n⏳ Waiting for IRA...")
        ira_response = wait_for_reply(gmail, thread_id)
        
        if not ira_response:
            print("   ❌ No response from IRA")
            break
        
        print(f"\n🤖 IRA's Response:")
        print(f"   {ira_response[:200]}...")
        
        # 4. Evaluate IRA's response
        print(f"\n📊 EVALUATION (Rushabh coaching):")
        evaluation = evaluate_ira_response(ira_response, email, persona_obj)
        
        score = evaluation.get('score', 5)
        print(f"   Score: {'█' * score}{'░' * (10-score)} {score}/10")
        
        if not evaluation.get('machine_correct', True):
            print(f"   ⚠️ Wrong machine: {evaluation.get('machine_mentioned', 'N/A')}")
        
        # Proposal progress
        progress = evaluation.get('proposal_progress', {})
        print(f"\n   📋 Proposal Progress:")
        print(f"      Machine Model: {'✅' if progress.get('machine_model') else '⬜'}")
        print(f"      Tech Specs:    {'✅' if progress.get('specs_provided') else '⬜'}")
        print(f"      Price Quote:   {'✅' if progress.get('price_quoted') else '⬜'}")
        
        # 5. Inject learning into IRA's memory
        learning = evaluation.get('learning', '')
        if learning:
            print(f"\n💡 LEARNING INJECTION:")
            print(f"   {learning[:100]}...")
            injector.inject(learning, agent.current_stage, score)
            log['learnings'].append(learning)
        
        # 6. Update state
        agent.record_ira_response(ira_response, evaluation)
        
        if evaluation.get('advance_stage', True):
            agent.advance_stage()
        
        ira_last_response = ira_response
        
        log['turns'].append({
            "turn": turn,
            "stage": agent.current_stage,
            "customer": email['body'][:500],
            "ira": ira_response[:500],
            "score": score,
            "humanness": h_score.total_score,
            "evaluation": evaluation,
        })
    
    # Completion
    log['proposal_achieved'] = agent.is_proposal_ready()
    log['ended'] = datetime.now().isoformat()
    
    # Save log
    output_dir = PROJECT_ROOT / "data" / "human_training"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"human_{persona_key}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    with open(output_file, 'w') as f:
        json.dump(log, f, indent=2)
    
    avg_humanness = sum(log['humanness_scores']) / len(log['humanness_scores']) if log['humanness_scores'] else 0
    
    print(f"""
╔══════════════════════════════════════════════════════════════════════╗
║                    🏁 TRAINING COMPLETE                              ║
╠══════════════════════════════════════════════════════════════════════╣
║  Turns Completed:     {turn:<49} ║
║  Learnings Injected:  {len(log['learnings']):<49} ║
║  Avg Humanness:       {avg_humanness:.1f}/100 {'✅' if avg_humanness >= HUMANNESS_TARGET else '⚠️':<42} ║
║  Proposal Achieved:   {'✅ YES' if log['proposal_achieved'] else '⬜ NO':<49} ║
╚══════════════════════════════════════════════════════════════════════╝
""")
    
    return log


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Human Training Loop")
    parser.add_argument("--persona", default="mike_chen", 
                       choices=list(HUMAN_PERSONAS.keys()))
    parser.add_argument("--turns", type=int, default=5)
    parser.add_argument("--auto", action="store_true")
    
    args = parser.parse_args()
    
    if not args.auto:
        print("\n⚠️  Make sure IRA's email bridge is running:")
        print("   python scripts/email_openclaw_bridge.py --loop\n")
        input("Press Enter to start...")
    
    run_human_training(args.persona, args.turns)
