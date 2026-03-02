#!/usr/bin/env python3
"""
KNOWLEDGE VALIDATOR - Proactive Learning via Email

IRA proactively asks questions to validate and improve its knowledge.
Sends emails with smart questions about specific topics to learn from experts.

Usage:
    python knowledge_validator.py --topic "PF1 machines" --to "rushabh@machinecraft.org"
"""

import json
import os
import re
import smtplib
import sys
from dataclasses import dataclass
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Setup paths
SKILL_DIR = Path(__file__).parent
SKILLS_DIR = SKILL_DIR.parent
PROJECT_ROOT = SKILL_DIR.parent.parent.parent.parent.parent

# Load environment
env_file = PROJECT_ROOT / ".env"
if env_file.exists():
    for line in env_file.read_text().splitlines():
        if line.strip() and not line.startswith('#') and '=' in line:
            key, _, value = line.partition('=')
            os.environ.setdefault(key.strip(), value.strip().strip('"'))


@dataclass
class KnowledgeGap:
    """A piece of knowledge that needs validation."""
    topic: str
    current_belief: str
    confidence: float  # 0-1, lower = more uncertain
    question: str
    category: str  # "specification", "pricing", "application", "feature"
    source: str  # Where the current belief came from


@dataclass
class ValidationEmail:
    """An email asking for knowledge validation."""
    subject: str
    body: str
    gaps: List[KnowledgeGap]


def get_pf1_knowledge_gaps() -> List[KnowledgeGap]:
    """
    Identify knowledge gaps about PF1 machines.
    
    These are areas where IRA is uncertain or might have outdated info.
    """
    gaps = [
        KnowledgeGap(
            topic="PF1-C-1200-800 Forming Area",
            current_belief="The forming area is 1200mm x 800mm",
            confidence=0.7,
            question="Can you confirm the exact forming area dimensions for the PF1-C-1200-800? Is it 1200mm x 800mm or different?",
            category="specification",
            source="product_docs"
        ),
        KnowledgeGap(
            topic="PF1 Maximum Sheet Thickness",
            current_belief="Maximum sheet thickness is 6mm for most materials",
            confidence=0.6,
            question="What is the actual maximum sheet thickness for PF1 machines? Does it vary by material type (ABS, HDPE, PP)?",
            category="specification",
            source="inference"
        ),
        KnowledgeGap(
            topic="PF1 Heating System",
            current_belief="Uses ceramic heaters in top and bottom zones",
            confidence=0.5,
            question="What type of heating elements does the PF1 use? Ceramic, quartz, or infrared? How many heating zones?",
            category="feature",
            source="general_knowledge"
        ),
        KnowledgeGap(
            topic="PF1 Cycle Time",
            current_belief="Typical cycle time is 15-30 seconds depending on material",
            confidence=0.4,
            question="What's the typical cycle time range for PF1 machines? Does it vary significantly by material thickness?",
            category="specification",
            source="estimation"
        ),
        KnowledgeGap(
            topic="PF1 Lead Time",
            current_belief="Standard lead time is 8-12 weeks",
            confidence=0.3,
            question="What is the current lead time for PF1 machines? Has this changed recently?",
            category="pricing",
            source="outdated_info"
        ),
        KnowledgeGap(
            topic="PF1 Standard vs Optional Features",
            current_belief="Auto-leveling and material thickness sensor are optional",
            confidence=0.5,
            question="Which features come standard on PF1 machines vs optional? Specifically: auto-leveling, thickness sensors, cooling fans?",
            category="feature",
            source="unclear"
        ),
        KnowledgeGap(
            topic="PF1 Power Requirements",
            current_belief="Requires 3-phase power, approximately 30-50 kW",
            confidence=0.6,
            question="What are the exact power requirements for PF1-C-1200-800? Voltage, phases, and kW rating?",
            category="specification",
            source="general_knowledge"
        ),
        KnowledgeGap(
            topic="PF1 Applications",
            current_belief="Used for automotive parts, packaging, and medical trays",
            confidence=0.8,
            question="What are the main application areas for PF1 machines? Are there any industries we should highlight more?",
            category="application",
            source="customer_data"
        ),
        KnowledgeGap(
            topic="PF1 Competitive Positioning",
            current_belief="Positioned as mid-range, good value for money",
            confidence=0.4,
            question="How should I position PF1 machines vs competitors? What are our key differentiators?",
            category="pricing",
            source="unclear"
        ),
        KnowledgeGap(
            topic="PF1 Common Issues",
            current_belief="No known common issues",
            confidence=0.3,
            question="Are there any common issues or FAQs about PF1 machines I should know about for customer support?",
            category="feature",
            source="none"
        ),
    ]
    
    return gaps


def generate_validation_email(
    topic: str,
    recipient_name: str = "Team",
    gaps: List[KnowledgeGap] = None
) -> ValidationEmail:
    """
    Generate a knowledge validation email.
    
    Args:
        topic: Main topic (e.g., "PF1 machines")
        recipient_name: Name to address
        gaps: List of knowledge gaps to ask about
    
    Returns:
        ValidationEmail with subject, body, and gaps
    """
    if gaps is None:
        gaps = get_pf1_knowledge_gaps()
    
    # Sort by confidence (ask about most uncertain first)
    gaps_sorted = sorted(gaps, key=lambda g: g.confidence)
    
    # Select top 5-7 questions (not too many)
    selected_gaps = gaps_sorted[:7]
    
    # Group by category
    by_category = {}
    for gap in selected_gaps:
        by_category.setdefault(gap.category, []).append(gap)
    
    # Build email body
    subject = f"🧠 Ira Knowledge Check: {topic} - Help me learn!"
    
    body_parts = [
        f"Hi {recipient_name},",
        "",
        f"I'm Ira, your sales assistant, and I want to make sure I have accurate information about **{topic}**.",
        "",
        "I've identified some areas where I'm uncertain or might have outdated knowledge. Could you help me verify or correct these?",
        "",
        "---",
        "",
    ]
    
    # Add questions by category
    category_names = {
        "specification": "📐 Technical Specifications",
        "feature": "⚙️ Features & Capabilities",
        "pricing": "💰 Pricing & Lead Times",
        "application": "🏭 Applications & Use Cases"
    }
    
    question_num = 1
    for category, category_gaps in by_category.items():
        category_name = category_names.get(category, category.title())
        body_parts.append(f"### {category_name}")
        body_parts.append("")
        
        for gap in category_gaps:
            confidence_indicator = "⚠️" if gap.confidence < 0.5 else "❓"
            body_parts.append(f"**{question_num}. {gap.topic}** {confidence_indicator}")
            body_parts.append(f"   *What I think:* {gap.current_belief}")
            body_parts.append(f"   *My question:* {gap.question}")
            body_parts.append("")
            question_num += 1
    
    body_parts.extend([
        "---",
        "",
        "**How to respond:**",
        "Just reply to this email with corrections or confirmations. For example:",
        "- \"Q1: Correct, it's 1200x800mm\"",
        "- \"Q3: Actually, we use quartz heaters, not ceramic\"",
        "- \"Q5: Lead time is now 10 weeks\"",
        "",
        "I'll learn from your corrections and use this knowledge in future customer conversations!",
        "",
        "Thanks for helping me improve! 🙏",
        "",
        "Best,",
        "**Ira**",
        "_Intelligent Revenue Assistant_",
        "_Machinecraft Technologies_",
        "",
        "---",
        f"_Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}_",
        f"_Topic: {topic}_",
        f"_Questions: {len(selected_gaps)}_"
    ])
    
    body = "\n".join(body_parts)
    
    return ValidationEmail(
        subject=subject,
        body=body,
        gaps=selected_gaps
    )


def send_email_gmail(
    to_email: str,
    subject: str,
    body: str,
    from_email: str = "ira@machinecraft.in"
) -> bool:
    """
    Send email using Gmail API.
    
    Returns True if successful.
    """
    try:
        # Try Google API first
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build
        import base64
        
        SCOPES = ['https://www.googleapis.com/auth/gmail.send']
        creds = None
        token_path = PROJECT_ROOT / 'token.json'
        creds_path = PROJECT_ROOT / 'credentials.json'
        
        if token_path.exists():
            creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            elif creds_path.exists():
                flow = InstalledAppFlow.from_client_secrets_file(str(creds_path), SCOPES)
                creds = flow.run_local_server(port=0)
                token_path.write_text(creds.to_json())
            else:
                print("[validator] No Gmail credentials found")
                return False
        
        service = build('gmail', 'v1', credentials=creds)
        
        # Create message
        message = MIMEMultipart('alternative')
        message['to'] = to_email
        message['from'] = from_email
        message['subject'] = subject
        
        # Plain text version
        message.attach(MIMEText(body, 'plain'))
        
        # HTML version (convert markdown-style to HTML)
        html_body = body.replace('\n', '<br>')
        html_body = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html_body)
        html_body = re.sub(r'\*(.+?)\*', r'<em>\1</em>', html_body)
        html_body = re.sub(r'###\s*(.+?)<br>', r'<h3>\1</h3>', html_body)
        html_body = f"<html><body style='font-family: Arial, sans-serif;'>{html_body}</body></html>"
        message.attach(MIMEText(html_body, 'html'))
        
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        
        service.users().messages().send(
            userId='me',
            body={'raw': raw}
        ).execute()
        
        print(f"[validator] Email sent to {to_email}")
        return True
        
    except ImportError:
        print("[validator] Google API not installed, trying SMTP...")
        return send_email_smtp(to_email, subject, body, from_email)
    except Exception as e:
        print(f"[validator] Gmail API error: {e}")
        return send_email_smtp(to_email, subject, body, from_email)


def send_email_smtp(
    to_email: str,
    subject: str,
    body: str,
    from_email: str = "ira@machinecraft.in"
) -> bool:
    """
    Fallback: Send email using SMTP.
    """
    try:
        smtp_host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
        smtp_port = int(os.environ.get("SMTP_PORT", "587"))
        smtp_user = os.environ.get("SMTP_USER", "")
        smtp_pass = os.environ.get("SMTP_PASSWORD", "")
        
        if not smtp_user or not smtp_pass:
            print("[validator] SMTP credentials not configured")
            return False
        
        msg = MIMEMultipart()
        msg['From'] = from_email
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
        
        print(f"[validator] Email sent via SMTP to {to_email}")
        return True
        
    except Exception as e:
        print(f"[validator] SMTP error: {e}")
        return False


def send_via_telegram(body: str) -> bool:
    """
    Send the email content via Telegram as a fallback.
    """
    try:
        import requests
        
        bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
        chat_id = os.environ.get("TELEGRAM_CHAT_ID")
        
        if not bot_token or not chat_id:
            print("[validator] Telegram not configured")
            return False
        
        # Truncate if too long
        if len(body) > 4000:
            body = body[:3900] + "\n\n... (truncated)"
        
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        response = requests.post(url, json={
            "chat_id": chat_id,
            "text": body,
            "parse_mode": "Markdown"
        })
        
        if response.ok:
            print(f"[validator] Sent via Telegram to {chat_id}")
            return True
        else:
            print(f"[validator] Telegram error: {response.text}")
            return False
            
    except Exception as e:
        print(f"[validator] Telegram error: {e}")
        return False


def main():
    """Main CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Knowledge Validator - Proactive Learning")
    parser.add_argument("--topic", default="PF1 machines", help="Topic to validate")
    parser.add_argument("--to", default="rushabh@machinecraft.org", help="Recipient email")
    parser.add_argument("--name", default="Rushabh", help="Recipient name")
    parser.add_argument("--preview", action="store_true", help="Preview only, don't send")
    parser.add_argument("--telegram", action="store_true", help="Send via Telegram instead")
    
    args = parser.parse_args()
    
    print(f"[validator] Generating knowledge validation email for: {args.topic}")
    
    # Generate email
    email = generate_validation_email(
        topic=args.topic,
        recipient_name=args.name
    )
    
    print(f"[validator] Subject: {email.subject}")
    print(f"[validator] Questions: {len(email.gaps)}")
    
    if args.preview:
        print("\n" + "=" * 60)
        print("PREVIEW MODE")
        print("=" * 60)
        print(f"\nTo: {args.to}")
        print(f"Subject: {email.subject}")
        print("\n" + "-" * 60)
        print(email.body)
        print("-" * 60)
        return
    
    # Send
    if args.telegram:
        success = send_via_telegram(f"**{email.subject}**\n\n{email.body}")
    else:
        success = send_email_gmail(args.to, email.subject, email.body)
        if not success:
            print("[validator] Email failed, trying Telegram fallback...")
            success = send_via_telegram(f"**{email.subject}**\n\n{email.body}")
    
    if success:
        print("\n✅ Knowledge validation request sent!")
        print("Reply with corrections and I'll learn from them.")
    else:
        print("\n❌ Failed to send. Here's the content:\n")
        print(email.body)


if __name__ == "__main__":
    main()
