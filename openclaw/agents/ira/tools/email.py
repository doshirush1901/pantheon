"""
Ira Email Tool - Draft and send emails

Capabilities:
- Draft contextual emails using Ira's voice
- Polish drafts with brand guidelines
- Send via Gmail API

Usage:
    from openclaw.agents.ira.tools import ira_email_draft, ira_email_send
    
    draft = ira_email_draft(
        to="customer@example.com",
        subject="PF1 Quote",
        intent="Send pricing for PF1-C",
    )
    print(draft.body)
"""

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

TOOLS_DIR = Path(__file__).parent
AGENT_DIR = TOOLS_DIR.parent
SRC_DIR = AGENT_DIR / "src"
BRAIN_DIR = SRC_DIR / "brain"

sys.path.insert(0, str(AGENT_DIR))
sys.path.insert(0, str(BRAIN_DIR))


@dataclass
class EmailDraft:
    """A drafted email."""
    to: str
    subject: str
    body: str
    cc: List[str] = field(default_factory=list)
    context_used: List[str] = field(default_factory=list)
    tone: str = "professional"


@dataclass
class EmailSendResult:
    """Result of sending an email."""
    success: bool
    message_id: Optional[str] = None
    error: Optional[str] = None


class IraEmailTool:
    """
    Tool for drafting and sending emails with Ira's voice.
    """
    
    def __init__(self):
        self._polisher = None
    
    def _get_polisher(self):
        if self._polisher is None:
            try:
                from email_polish import EmailPolisher
                self._polisher = EmailPolisher()
            except ImportError:
                self._polisher = None
        return self._polisher
    
    def draft(
        self,
        to: str,
        subject: str,
        intent: str,
        context: Optional[str] = None,
        tone: str = "professional",
    ) -> EmailDraft:
        """
        Draft an email using Ira's voice.
        
        Args:
            to: Recipient email
            subject: Email subject
            intent: What the email should convey
            context: Additional context
            tone: Tone of the email
            
        Returns:
            EmailDraft ready for review/send
        """
        import os
        
        try:
            import openai
            client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
            
            system_prompt = """You are Ira, the AI assistant for Machinecraft Technologies.
Draft a professional email with these characteristics:
- Warm but professional tone
- Clear and concise
- Include relevant technical details
- End with a clear call to action"""
            
            user_prompt = f"""Draft an email:
To: {to}
Subject: {subject}
Intent: {intent}
{"Context: " + context if context else ""}

Write only the email body, no greeting line (that will be added)."""
            
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.7,
            )
            
            body = response.choices[0].message.content
            
            # Polish if available
            polisher = self._get_polisher()
            if polisher:
                polish_result = polisher.polish(body, use_llm=False)
                body = polish_result.polished
            
            return EmailDraft(
                to=to,
                subject=subject,
                body=body,
                tone=tone,
            )
            
        except Exception as e:
            return EmailDraft(
                to=to,
                subject=subject,
                body=f"[Draft generation failed: {e}]",
                tone=tone,
            )
    
    def send(
        self,
        to: str,
        subject: str,
        body: str,
        cc: Optional[List[str]] = None,
    ) -> EmailSendResult:
        """
        Send an email via Gmail API.
        
        Args:
            to: Recipient email
            subject: Email subject
            body: Email body
            cc: Optional CC list
            
        Returns:
            EmailSendResult with status
        """
        try:
            from knowledge_validator import send_email_gmail
            
            success = send_email_gmail(
                to_email=to,
                subject=subject,
                body=body,
            )

            # Holistic: record email send as muscle action
            if success:
                try:
                    from openclaw.agents.ira.src.holistic.musculoskeletal_system import get_musculoskeletal_system
                    get_musculoskeletal_system().record_action(
                        "email_sent",
                        context={"to": to, "subject": subject[:80]},
                    )
                except Exception:
                    pass
            
            return EmailSendResult(
                success=success,
                message_id="sent" if success else None,
            )
            
        except ImportError:
            return EmailSendResult(
                success=False,
                error="Gmail integration not available",
            )
        except Exception as e:
            return EmailSendResult(
                success=False,
                error=str(e),
            )


def ira_email_draft(
    to: str,
    subject: str,
    intent: str,
    context: Optional[str] = None,
    tone: str = "professional",
) -> EmailDraft:
    """Draft an email using Ira's voice."""
    tool = IraEmailTool()
    return tool.draft(to, subject, intent, context, tone)


def ira_email_send(
    to: str,
    subject: str,
    body: str,
    cc: Optional[List[str]] = None,
) -> EmailSendResult:
    """Send an email via Gmail API."""
    tool = IraEmailTool()
    return tool.send(to, subject, body, cc)
