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
    
    def _gather_context(self, to: str, subject: str, intent: str) -> Dict[str, Any]:
        """Auto-enrich email draft with CRM, knowledge base, and Google Contacts data."""
        gathered: Dict[str, Any] = {"sources": []}

        recipient_name = to if "@" not in to else ""
        search_terms = [t for t in [recipient_name, subject, intent] if t]

        # 1. Google Contacts lookup (resolves names to emails)
        try:
            from openclaw.agents.ira.src.tools.google_tools import contacts_search
            for term in search_terms[:2]:
                result = contacts_search(term)
                if result and "not available" not in result.lower() and "no contacts" not in result.lower():
                    gathered["contacts"] = result
                    gathered["sources"].append("google_contacts")
                    break
        except Exception:
            pass

        # 2. CRM lookup
        try:
            from openclaw.agents.ira.src.crm.ira_crm import IraCRM
            crm = IraCRM()
            for term in search_terms[:2]:
                contacts = crm.search_contacts(term, limit=3)
                if contacts:
                    crm_lines = []
                    for c in contacts:
                        parts = [c.name or ""]
                        if c.company:
                            parts.append(f"at {c.company}")
                        if c.email:
                            parts.append(f"({c.email})")
                        crm_lines.append(" ".join(p for p in parts if p))
                    gathered["crm"] = "\n".join(crm_lines)
                    gathered["sources"].append("crm")
                    break
        except Exception:
            pass

        # 3. Knowledge base (Qdrant) for subject/intent context
        try:
            from openclaw.agents.ira.src.brain.qdrant_retriever import retrieve as qdrant_retrieve
            knowledge_query = f"{subject} {intent}".strip()
            rag = qdrant_retrieve(knowledge_query, top_k=5)
            if hasattr(rag, 'citations') and rag.citations:
                kb_parts = []
                for c in rag.citations[:3]:
                    kb_parts.append(f"[{c.filename}] {c.text[:500]}")
                gathered["knowledge"] = "\n\n".join(kb_parts)
                gathered["sources"].append("knowledge_base")
        except Exception:
            pass

        # 4. Mem0 memory
        try:
            from openclaw.agents.ira.src.memory.mem0_memory import get_mem0_service
            mem0 = get_mem0_service()
            for uid in ["machinecraft_customers", "machinecraft_knowledge"]:
                memories = mem0.search(f"{subject} {intent}", uid, limit=5)
                if memories:
                    mem_parts = [m.memory for m in memories[:3]]
                    gathered.setdefault("memory", "")
                    gathered["memory"] += "\n".join(mem_parts) + "\n"
                    gathered["sources"].append(f"mem0:{uid}")
        except Exception:
            pass

        return gathered

    def draft(
        self,
        to: str,
        subject: str,
        intent: str,
        context: Optional[str] = None,
        tone: str = "professional",
    ) -> EmailDraft:
        """
        Draft an email using Ira's voice, auto-enriched with real data from
        CRM, knowledge base, Google Contacts, and Mem0.
        """
        import os
        
        try:
            import openai
            client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
            
            enrichment = self._gather_context(to, subject, intent)
            
            context_sections = []
            if context:
                context_sections.append(f"USER-PROVIDED CONTEXT:\n{context}")
            if enrichment.get("contacts"):
                context_sections.append(f"GOOGLE CONTACTS (recipient info):\n{enrichment['contacts']}")
            if enrichment.get("crm"):
                context_sections.append(f"CRM DATA:\n{enrichment['crm']}")
            if enrichment.get("knowledge"):
                context_sections.append(f"KNOWLEDGE BASE (relevant documents):\n{enrichment['knowledge']}")
            if enrichment.get("memory"):
                context_sections.append(f"MEMORY (past interactions):\n{enrichment['memory']}")
            
            enriched_context = "\n\n".join(context_sections) if context_sections else "(No additional context found)"
            
            system_prompt = """You are Ira, the AI assistant for Machinecraft Technologies.
Draft a professional email grounded in the REAL DATA provided below.

RULES:
- Use ONLY facts from the provided context. NEVER invent statistics, percentages, or claims.
- If the context has specific numbers, specs, or details, use them verbatim.
- If context is thin, keep the email short and factual rather than padding with made-up data.
- Warm but professional tone (Machinecraft brand voice).
- Clear and concise — 3-5 short paragraphs max.
- End with a clear call to action.
- Do NOT include greeting line (that will be added separately)."""
            
            user_prompt = f"""Draft an email:
To: {to}
Subject: {subject}
Intent: {intent}

═══ ENRICHED CONTEXT (use this data — do NOT invent facts) ═══
{enriched_context}
═══════════════════════════════════════════════════════════════

Write only the email body. Ground every claim in the context above."""
            
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.4,
            )
            
            body = response.choices[0].message.content
            
            polisher = self._get_polisher()
            if polisher:
                polish_result = polisher.polish(body, use_llm=False)
                body = polish_result.polished
            
            return EmailDraft(
                to=to,
                subject=subject,
                body=body,
                context_used=enrichment.get("sources", []),
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
