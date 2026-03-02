#!/usr/bin/env python3
"""
EMAIL-IRA BRIDGE
================
Polls Gmail inbox and routes emails to IRA Agent for processing.
Uses the FULL IRA PIPELINE (Mem0, RAG, Brain, Machine Recommender, etc.)
Sends responses back via Gmail.

This bridge uses IraAgent.process_email() directly, NOT OpenClaw CLI,
to ensure the complete cognitive pipeline is executed.

Usage:
    python scripts/email_openclaw_bridge.py --loop
    python scripts/email_openclaw_bridge.py --once
"""

import argparse
import base64
import json
import logging
import os
import random
import re
import sys
import threading
import time
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from pathlib import Path
from typing import Optional, Dict, List

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("email_bridge")

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "openclaw/agents/ira"))

# Load environment
from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

# Gmail API
try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    GMAIL_AVAILABLE = True
except ImportError:
    GMAIL_AVAILABLE = False
    logger.error("Gmail API not available. Install: pip install google-api-python-client google-auth-oauthlib")

# IRA Agent - Use the full pipeline
try:
    from agent import get_agent, IraAgent
    IRA_AGENT_AVAILABLE = True
    logger.info("IRA Agent module loaded successfully")
except ImportError as e:
    IRA_AGENT_AVAILABLE = False
    logger.error(f"IRA Agent not available: {e}")

# Telegram Gateway engine - reuse its rich processing pipeline for email
GATEWAY_ENGINE_AVAILABLE = False
_gateway_engine = None
try:
    sys.path.insert(0, str(PROJECT_ROOT / "_archive" / "pre_openclaw_legacy"))
    from telegram_gateway import TelegramGateway
    GATEWAY_ENGINE_AVAILABLE = True
    logger.info("Telegram Gateway engine loaded (shared processing pipeline)")
except ImportError as e:
    logger.warning(f"Gateway engine not available, email will use IraAgent fallback: {e}")

def get_gateway_engine():
    """Lazy-init the gateway engine (reuses Telegram's full pipeline for email)."""
    global _gateway_engine
    if _gateway_engine is None and GATEWAY_ENGINE_AVAILABLE:
        _gateway_engine = TelegramGateway()
    return _gateway_engine

try:
    from openclaw.agents.ira.src.conversation.chat_log import log_interaction
    CHAT_LOG_AVAILABLE = True
except ImportError:
    def log_interaction(*a, **k): pass
    CHAT_LOG_AVAILABLE = False

# CRM Integration - Quote tracking, follow-ups, customer health
CRM_DIR = PROJECT_ROOT / "openclaw/agents/ira/src/crm"
sys.path.insert(0, str(CRM_DIR))

try:
    from quote_lifecycle import get_tracker as get_quote_tracker, QuoteTracker, QuoteStatus
    QUOTE_TRACKER_AVAILABLE = True
    logger.info("Quote lifecycle tracker loaded")
except ImportError as e:
    QUOTE_TRACKER_AVAILABLE = False
    logger.warning(f"Quote tracker not available: {e}")

try:
    from follow_up_automation import get_engine as get_followup_engine, FollowUpEngine
    FOLLOWUP_ENGINE_AVAILABLE = True
    logger.info("Follow-up automation loaded")
except ImportError as e:
    FOLLOWUP_ENGINE_AVAILABLE = False
    logger.warning(f"Follow-up engine not available: {e}")

try:
    from customer_health import get_scorer as get_health_scorer, HealthScorer
    HEALTH_SCORER_AVAILABLE = True
    logger.info("Customer health scorer loaded")
except ImportError as e:
    HEALTH_SCORER_AVAILABLE = False
    logger.warning(f"Health scorer not available: {e}")

# Configuration
GMAIL_SCOPES = ['https://www.googleapis.com/auth/gmail.modify']
CREDENTIALS_FILE = PROJECT_ROOT / "credentials.json"
TOKEN_FILE = PROJECT_ROOT / "token.json"
POLL_INTERVAL = int(os.getenv("EMAIL_POLL_INTERVAL", "60"))  # seconds
IRA_EMAIL = os.getenv("IRA_EMAIL", "ira@machinecraft.org")
MAX_REFINEMENT_ROUNDS = int(os.getenv("IRA_MAX_REFINEMENT_ROUNDS", "3"))
MIN_RESPONSE_TIME = int(os.getenv("IRA_MIN_RESPONSE_TIME", "180"))  # minimum 3 minutes before replying
RUSHABH_EMAIL = os.getenv("RUSHABH_EMAIL", "rushabh@machinecraft.org")

# Proactive cadence configuration
PROACTIVE_WEEKLY_ENABLED = os.getenv("IRA_PROACTIVE_WEEKLY_ENABLED", "true").lower() in ("true", "1", "yes")
PROACTIVE_WEEKLY_DAY = int(os.getenv("IRA_PROACTIVE_WEEKLY_DAY", "0"))  # 0=Monday
PROACTIVE_WEEKLY_HOUR = int(os.getenv("IRA_PROACTIVE_WEEKLY_HOUR", "8"))
PROACTIVE_DAILY_ENABLED = os.getenv("IRA_PROACTIVE_DAILY_ENABLED", "true").lower() in ("true", "1", "yes")
PROACTIVE_DAILY_HOUR = int(os.getenv("IRA_PROACTIVE_DAILY_HOUR", "9"))
PROACTIVE_STATE_PATH = PROJECT_ROOT / "data" / "proactive_state.json"


def _load_proactive_state() -> Dict[str, str]:
    """Load proactive state from file. Returns dict with last_weekly, last_daily keys."""
    if not PROACTIVE_STATE_PATH.exists():
        return {}
    try:
        data = json.loads(PROACTIVE_STATE_PATH.read_text())
        return {
            "last_weekly": data.get("last_weekly", ""),
            "last_daily": data.get("last_daily", ""),
        }
    except Exception as e:
        logger.warning(f"Could not load proactive state: {e}")
        return {}


def _save_proactive_state(last_weekly: Optional[str] = None, last_daily: Optional[str] = None):
    """Update and save proactive state. Pass only keys to update."""
    state = _load_proactive_state()
    if last_weekly is not None:
        state["last_weekly"] = last_weekly
    if last_daily is not None:
        state["last_daily"] = last_daily
    try:
        PROACTIVE_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        PROACTIVE_STATE_PATH.write_text(json.dumps(state, indent=2))
    except Exception as e:
        logger.warning(f"Could not save proactive state: {e}")


class GmailClient:
    """Gmail API client for reading and sending emails."""
    
    def __init__(self):
        self.service = None
        self._authenticate()
    
    def _authenticate(self):
        """Authenticate with Gmail API using OAuth."""
        creds = None
        
        if TOKEN_FILE.exists():
            creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), GMAIL_SCOPES)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not CREDENTIALS_FILE.exists():
                    raise FileNotFoundError(f"credentials.json not found at {CREDENTIALS_FILE}")
                flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE), GMAIL_SCOPES)
                creds = flow.run_local_server(port=0)
            
            TOKEN_FILE.write_text(creds.to_json())
        
        self.service = build('gmail', 'v1', credentials=creds)
        logger.info("Gmail authenticated successfully")
    
    def get_unread_emails(self, max_results: int = 10) -> List[Dict]:
        """Fetch unread emails from inbox."""
        try:
            results = self.service.users().messages().list(
                userId='me',
                q='is:unread -from:me',
                maxResults=max_results
            ).execute()
            
            messages = results.get('messages', [])
            emails = []
            
            for msg in messages:
                email_data = self._get_email_details(msg['id'])
                if email_data:
                    emails.append(email_data)
            
            return emails
        except Exception as e:
            logger.error(f"Error fetching emails: {e}")
            return []
    
    def _get_email_details(self, message_id: str) -> Optional[Dict]:
        """Get full email details."""
        try:
            msg = self.service.users().messages().get(
                userId='me',
                id=message_id,
                format='full'
            ).execute()
            
            headers = {h['name'].lower(): h['value'] for h in msg['payload']['headers']}
            
            # Extract body
            body = self._extract_body(msg['payload'])
            
            return {
                'id': message_id,
                'thread_id': msg.get('threadId'),
                'from': headers.get('from', ''),
                'to': headers.get('to', ''),
                'subject': headers.get('subject', ''),
                'date': headers.get('date', ''),
                'body': body,
                'snippet': msg.get('snippet', ''),
            }
        except Exception as e:
            logger.error(f"Error getting email {message_id}: {e}")
            return None
    
    def _extract_body(self, payload: Dict) -> str:
        """Extract plain text body from email payload."""
        if 'body' in payload and payload['body'].get('data'):
            return base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8', errors='ignore')
        
        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    if part['body'].get('data'):
                        return base64.urlsafe_b64decode(part['body']['data']).decode('utf-8', errors='ignore')
                elif 'parts' in part:
                    result = self._extract_body(part)
                    if result:
                        return result
        
        return ""
    
    def get_thread_history(self, thread_id: str, max_messages: int = 10) -> List[Dict]:
        """Fetch full conversation thread from Gmail for context."""
        if not thread_id:
            return []
        try:
            thread = self.service.users().threads().get(
                userId='me',
                id=thread_id,
                format='full'
            ).execute()

            messages = thread.get('messages', [])
            history = []
            for msg in messages[-max_messages:]:
                headers = {h['name'].lower(): h['value'] for h in msg['payload']['headers']}
                body = self._extract_body(msg['payload'])
                sender = headers.get('from', '')
                is_ira = IRA_EMAIL.lower() in sender.lower()
                history.append({
                    'role': 'assistant' if is_ira else 'user',
                    'from': sender,
                    'body': body,
                    'date': headers.get('date', ''),
                    'subject': headers.get('subject', ''),
                })
            return history
        except Exception as e:
            logger.warning(f"Could not fetch thread {thread_id}: {e}")
            return []

    def send_new_email(self, to: str, subject: str, body: str) -> Optional[str]:
        """Send a new email (not a reply). Returns the thread_id of the new message."""
        try:
            message = MIMEText(body)
            message['to'] = to
            message['from'] = IRA_EMAIL
            message['subject'] = subject

            raw = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')

            result = self.service.users().messages().send(
                userId='me',
                body={'raw': raw}
            ).execute()

            thread_id = result.get('threadId', '')
            logger.info(f"New email sent to {to} (thread: {thread_id})")
            return thread_id
        except Exception as e:
            logger.error(f"Error sending new email: {e}")
            return None

    def send_reply(self, to: str, subject: str, body: str, thread_id: str, message_id: str) -> bool:
        """Send a reply email."""
        try:
            message = MIMEText(body)
            message['to'] = to
            message['from'] = IRA_EMAIL
            message['subject'] = subject if subject.startswith('Re:') else f"Re: {subject}"
            message['In-Reply-To'] = message_id
            message['References'] = message_id
            
            raw = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
            
            self.service.users().messages().send(
                userId='me',
                body={'raw': raw, 'threadId': thread_id}
            ).execute()
            
            logger.info(f"Reply sent to {to}")
            return True
        except Exception as e:
            logger.error(f"Error sending reply: {e}")
            return False
    
    def mark_as_read(self, message_id: str):
        """Mark email as read."""
        try:
            self.service.users().messages().modify(
                userId='me',
                id=message_id,
                body={'removeLabelIds': ['UNREAD']}
            ).execute()
        except Exception as e:
            logger.error(f"Error marking as read: {e}")


class IraAgentBridge:
    """Bridge that uses DEEP RESEARCH PIPELINE for processing emails.
    
    This is a thorough, multi-step pipeline that:
    1. CHUNKS & UNDERSTANDS the email (break down the real question)
    2. SEARCHES MEMORIES (Mem0, Qdrant, Machine DB in parallel)
    3. FINDS RELEVANT DOCUMENTS (nearest neighbor in data/imports/)
    4. REASONS about the answer (is this correct? confidence check)
    5. GENERATES RESPONSE with IRA's personality
    6. CREATES FOLLOW-UP QUESTIONS for Rushabh
    
    This pipeline TAKES TIME (30-60+ seconds) - quality over speed.
    """
    
    def __init__(self):
        if not IRA_AGENT_AVAILABLE:
            raise RuntimeError("IRA Agent not available")
        
        self.agent = get_agent()
        logger.info(f"IRA Agent initialized: {self.agent.config.name} v{self.agent.config.version}")
        
        # Initialize Deep Research Pipeline
        try:
            sys.path.insert(0, str(Path(__file__).parent.parent / "openclaw/agents/ira/src/brain"))
            from deep_research_pipeline import get_pipeline, DeepResearchPipeline
            self.deep_research = get_pipeline()
            self.deep_research_available = True
            logger.info("Deep Research Pipeline initialized")
        except Exception as e:
            logger.warning(f"Deep Research Pipeline not available: {e}")
            self.deep_research = None
            self.deep_research_available = False
        
        # Initialize Reply Packaging Pipeline
        try:
            from reply_packaging_pipeline import get_packager, ReplyPackager
            self.reply_packager = get_packager()
            self.packaging_available = True
            logger.info("Reply Packaging Pipeline initialized")
        except Exception as e:
            logger.warning(f"Reply Packaging Pipeline not available: {e}")
            self.reply_packager = None
            self.packaging_available = False
        
        # Initialize Feedback Processing Pipeline
        try:
            from feedback_processing_pipeline import get_processor, FeedbackProcessor
            self.feedback_processor = get_processor()
            self.feedback_pipeline_available = True
            logger.info("Feedback Processing Pipeline initialized")
        except Exception as e:
            logger.warning(f"Feedback Processing Pipeline not available: {e}")
            self.feedback_processor = None
            self.feedback_pipeline_available = False
        
        # Initialize Unified Pipeline Orchestrator (coordinates all 4 pipelines)
        try:
            from ira_pipeline_orchestrator import get_orchestrator, IraPipelineOrchestrator
            self.orchestrator = get_orchestrator()
            self.orchestrator_available = True
            logger.info("Unified Pipeline Orchestrator initialized")
        except Exception as e:
            logger.warning(f"Pipeline Orchestrator not available: {e}")
            self.orchestrator = None
            self.orchestrator_available = False
        
        # Initialize CRM components
        self._init_crm()
        
        # Log module availability
        status = self.agent.get_status()
        modules = status.get('modules', {})
        logger.info(f"Brain: {modules.get('brain', False)}, Memory: {modules.get('memory', False)}, RAG: {modules.get('rag', False)}")
        logger.info(f"Deep Research: {self.deep_research_available}")
        logger.info(f"CRM: Quote={self.quote_tracker_available}, FollowUp={self.followup_engine_available}, Health={self.health_scorer_available}")
    
    def _init_crm(self):
        """Initialize CRM components for quote tracking, follow-ups, and customer health."""
        # Quote Lifecycle Tracker
        self.quote_tracker = None
        self.quote_tracker_available = False
        if QUOTE_TRACKER_AVAILABLE:
            try:
                self.quote_tracker = get_quote_tracker()
                self.quote_tracker_available = True
                logger.info("Quote Lifecycle Tracker initialized")
            except Exception as e:
                logger.warning(f"Quote tracker init failed: {e}")
        
        # Follow-up Automation Engine
        self.followup_engine = None
        self.followup_engine_available = False
        if FOLLOWUP_ENGINE_AVAILABLE:
            try:
                self.followup_engine = get_followup_engine()
                self.followup_engine_available = True
                logger.info("Follow-up Automation Engine initialized")
            except Exception as e:
                logger.warning(f"Follow-up engine init failed: {e}")
        
        # Customer Health Scorer
        self.health_scorer = None
        self.health_scorer_available = False
        if HEALTH_SCORER_AVAILABLE:
            try:
                self.health_scorer = get_health_scorer()
                self.health_scorer_available = True
                logger.info("Customer Health Scorer initialized")
            except Exception as e:
                logger.warning(f"Health scorer init failed: {e}")
    
    def process_email(self, body: str, from_email: str, subject: str, thread_id: str) -> Optional[str]:
        """Process email through the DEEP RESEARCH PIPELINE.
        
        This comprehensive pipeline:
        1. Query Understanding - Break down the email to understand the real question
        2. Memory Search - Search Mem0, Qdrant, and Machine DB in parallel
        3. Document Selection - Use nearest neighbor to find relevant files in imports/
        4. Reasoning - Self-validate: "Is this the right answer?"
        5. Response Generation - Draft reply with IRA's personality
        6. Question Generation - Create follow-up questions for Rushabh
        
        The pipeline takes time (30-60+ seconds) - quality over speed!
        """
        try:
            logger.info("=" * 60)
            logger.info("DEEP RESEARCH PIPELINE - EMAIL PROCESSING")
            logger.info("=" * 60)
            logger.info(f"From: {from_email}")
            logger.info(f"Subject: {subject[:50] if subject else 'No subject'}")
            logger.info(f"Query: {body[:100]}...")
            
            start_time = time.time()
            
            # Combine subject and body for full context
            full_query = f"Subject: {subject}\n\n{body}" if subject else body
            
            # Use Deep Research Pipeline if available
            if self.deep_research_available and self.deep_research:
                logger.info("\n[USING DEEP RESEARCH PIPELINE]")
                
                # Run the deep research
                research_result = self.deep_research.research(
                    query=full_query,
                    user_id=from_email,
                    channel="email",
                    verbose=True
                )
                
                elapsed = time.time() - start_time
                
                # Log the results
                logger.info("\n" + "-" * 60)
                logger.info(f"DEEP RESEARCH COMPLETE in {elapsed:.1f}s")
                logger.info(f"  - Intent: {research_result.understanding.intent}")
                logger.info(f"  - Confidence: {research_result.confidence:.2f}")
                logger.info(f"  - Memory results: {len(research_result.memory_results)}")
                logger.info(f"  - Documents found: {len(research_result.document_matches)}")
                logger.info(f"  - Sources used: {len(research_result.sources_used)}")
                
                # Log follow-up questions for Rushabh
                if research_result.follow_up_questions:
                    logger.info("\n📝 QUESTIONS FOR RUSHABH:")
                    for q in research_result.follow_up_questions:
                        logger.info(f"  [{q.priority}] {q.question}")
                
                # =============================================================
                # REPLY PACKAGING PIPELINE - Transform to MBB-quality response
                # =============================================================
                if self.packaging_available and self.reply_packager:
                    logger.info("\n[RUNNING REPLY PACKAGING PIPELINE]")
                    logger.info("Transforming to MBB consultant quality...")
                    
                    # Extract recipient name from email
                    recipient_name = self._extract_name_from_email(from_email)
                    
                    # Package the reply
                    packaged = self.reply_packager.package(
                        research_result=research_result,
                        recipient_name=recipient_name,
                        recipient_email=from_email,
                        channel="email",
                        original_subject=subject,
                        verbose=True
                    )
                    
                    # Use the packaged response
                    response_text = packaged.full_text
                    
                    logger.info("\n" + "=" * 60)
                    logger.info("PACKAGED REPLY READY")
                    logger.info(f"  - Word count: {packaged.word_count}")
                    logger.info(f"  - Data points: {packaged.data_points_count}")
                    logger.info(f"  - Sources: {packaged.sources_count}")
                    logger.info(f"  - Reading time: {packaged.reading_time_seconds}s")
                    logger.info("=" * 60)
                else:
                    # Fall back to draft response
                    response_text = research_result.draft_response
                
                total_elapsed = time.time() - start_time
                logger.info(f"\n✅ COMPLETE PIPELINE finished in {total_elapsed:.1f}s")
                
                # Also record in IRA's episodic memory
                try:
                    if hasattr(self.agent, '_record_episode'):
                        from openclaw.agents.ira.agent import AgentRequest, Channel
                        request = AgentRequest(
                            message=body,
                            user_id=from_email,
                            channel=Channel.EMAIL,
                            thread_id=thread_id
                        )
                        self.agent._record_episode(
                            request, response_text, from_email,
                            research_result.understanding.entities
                        )
                except Exception as e:
                    logger.debug(f"Episode recording: {e}")
                
                return response_text
            
            else:
                # Fallback to standard IRA pipeline
                logger.info("\n[USING STANDARD IRA PIPELINE]")
                
                response = self.agent.process_email(
                    body=body,
                    from_email=from_email,
                    subject=subject,
                    thread_id=thread_id
                )
                
                elapsed = time.time() - start_time
                
                if response.success:
                    logger.info(f"IRA response generated in {elapsed:.1f}s")
                    logger.info(f"  - Memories used: {response.memories_used}")
                    logger.info(f"  - RAG chunks used: {response.rag_chunks_used}")
                    logger.info(f"  - Procedure: {response.procedure_used or 'None'}")
                    return response.message
                else:
                    logger.warning(f"IRA response not successful: {response.errors}")
                    return response.message if response.message else None
                
        except Exception as e:
            logger.error(f"Error in Deep Research Pipeline: {e}")
            import traceback
            logger.error(traceback.format_exc())
            
            # Final fallback: try basic IRA pipeline
            try:
                response = self.agent.process_email(
                    body=body, from_email=from_email,
                    subject=subject, thread_id=thread_id
                )
                return response.message if response.success else None
            except:
                return None
    
    def _extract_name_from_email(self, email: str) -> str:
        """Extract a name from email address for personalized greeting."""
        # Try to extract from "Name <email>" format
        if '<' in email:
            name_part = email.split('<')[0].strip()
            if name_part:
                # Get first name only
                return name_part.split()[0]
        
        # Extract from email address
        local_part = email.split('@')[0]
        
        # Remove common suffixes and clean up
        local_part = re.sub(r'\d+$', '', local_part)  # Remove trailing numbers
        local_part = local_part.replace('.', ' ').replace('_', ' ').replace('-', ' ')
        
        # Capitalize first letter
        if local_part:
            parts = local_part.split()
            if parts:
                return parts[0].capitalize()
        
        return "there"
    
    def store_feedback(self, from_email: str, feedback: str, original_response: str) -> str:
        """Process feedback through the FULL FEEDBACK PROCESSING PIPELINE.
        
        This comprehensive pipeline:
        1. DETECTS feedback type (correction, preference, entity update)
        2. EXTRACTS specific corrections using LLM
        3. VALIDATES the correction makes sense
        4. UPDATES KNOWLEDGE (Mem0, Qdrant, Machine DB, Truth Hints)
        5. UPDATES LOGIC (Guardrails, Procedures)
        6. GENERATES CONFIRMATION message
        7. PREVENTS recurrence (logs, flags for consolidation)
        
        Returns confirmation message to send back to user.
        """
        confirmation_message = ""
        
        try:
            # Try the full Feedback Processing Pipeline first
            if self.feedback_pipeline_available and self.feedback_processor:
                logger.info("\n" + "=" * 60)
                logger.info("FEEDBACK PROCESSING PIPELINE")
                logger.info("=" * 60)
                
                result = self.feedback_processor.process(
                    feedback_message=feedback,
                    original_response=original_response,
                    from_user=from_email,
                    channel="email",
                    verbose=True
                )
                
                if result.success and result.corrections_found:
                    confirmation_message = result.confirmation_message
                    logger.info(f"\n✅ Feedback processed: {len(result.corrections_found)} corrections")
                    logger.info(f"Updates applied: {result.updates_applied}")
                else:
                    logger.info("No specific corrections detected, but feedback noted")
                    confirmation_message = ""
            
            # Fallback: Also store via brain for redundancy
            if hasattr(self.agent, '_brain') and self.agent._brain:
                self.agent._brain.process(
                    message=f"CORRECTION FROM USER: {feedback}\n\nOriginal response: {original_response}",
                    identity_id=from_email,
                    context={"is_correction": True, "channel": "email"}
                )
                logger.info(f"Also stored via brain for {from_email}")
                
        except Exception as e:
            logger.error(f"Error processing feedback: {e}")
        
        return confirmation_message
    
    # =========================================================================
    # CRM INTEGRATION METHODS
    # =========================================================================
    
    def _handle_post_reply_crm(
        self,
        from_email: str,
        subject: str,
        body: str,
        response: str,
        success: bool
    ):
        """
        Handle CRM actions after a successful email reply.
        
        This method:
        1. Records quote activity if the response contains pricing
        2. Updates customer engagement metrics
        3. Schedules follow-ups if appropriate
        """
        if not success:
            return
        
        try:
            # 1. Check if this was a quote/pricing response
            if self._is_pricing_response(response):
                self._record_quote_activity(from_email, subject, body, response)
            
            # 2. Update customer engagement metrics
            if self.health_scorer_available and self.health_scorer:
                self._update_customer_engagement(from_email)
            
            # 3. Schedule follow-up if needed
            if self.followup_engine_available and self.followup_engine:
                self._maybe_schedule_followup(from_email, subject, response)
                
        except Exception as e:
            logger.warning(f"CRM post-reply handling error: {e}")
    
    def _is_pricing_response(self, response: str) -> bool:
        """Check if response contains pricing information."""
        pricing_indicators = [
            "₹", "price", "pricing", "quote", "quotation", 
            "lakhs", "lakh", "INR", "USD", "EUR",
            "ex-works", "FOB", "CIF"
        ]
        response_lower = response.lower()
        return any(indicator.lower() in response_lower for indicator in pricing_indicators)
    
    def _record_quote_activity(
        self,
        from_email: str,
        subject: str,
        body: str,
        response: str
    ):
        """Record quote activity in the CRM system."""
        if not self.quote_tracker_available or not self.quote_tracker:
            return
        
        try:
            import re
            
            # Try to extract machine model from subject/body
            machine_patterns = [
                r'PF[-\s]?1[-\s]?[A-Z]?[-\s]?\d+',
                r'PF[-\s]?2[-\s]?\d+',
                r'AM[-\s]?\d+',
            ]
            
            product = "General Inquiry"
            for pattern in machine_patterns:
                match = re.search(pattern, f"{subject} {body}", re.IGNORECASE)
                if match:
                    product = match.group(0).upper().replace(' ', '-')
                    break
            
            # Try to extract price from response
            price_match = re.search(r'₹?\s*([\d,]+(?:\.\d+)?)\s*(?:lakhs?|lakh)', response, re.IGNORECASE)
            amount = 0
            if price_match:
                amount_str = price_match.group(1).replace(',', '')
                amount = float(amount_str) * 100000  # Convert lakhs to INR
            
            # Generate quote ID
            quote_id = f"{product}-{from_email[:10]}-{datetime.now().strftime('%Y%m%d')}"
            
            # Record the quote
            self.quote_tracker.record_quote_sent(
                quote_id=quote_id,
                customer_email=from_email,
                product=product,
                amount=amount,
                currency="INR"
            )
            logger.info(f"CRM: Recorded quote {quote_id} for {from_email}")
            
        except Exception as e:
            logger.warning(f"Error recording quote: {e}")
    
    def _update_customer_engagement(self, from_email: str):
        """Update customer engagement metrics after interaction."""
        if not self.health_scorer_available or not self.health_scorer:
            return
        
        try:
            # Record the interaction
            self.health_scorer.record_interaction(
                customer_email=from_email,
                channel="email",
                interaction_type="response_sent"
            )
            logger.debug(f"CRM: Updated engagement for {from_email}")
        except Exception as e:
            logger.warning(f"Error updating engagement: {e}")
    
    def _maybe_schedule_followup(
        self,
        from_email: str,
        subject: str,
        response: str
    ):
        """Schedule a follow-up if this looks like a quote that needs tracking."""
        if not self.followup_engine_available or not self.followup_engine:
            return
        
        try:
            # Only schedule for pricing-related responses
            if not self._is_pricing_response(response):
                return
            
            # Check if follow-up should be scheduled (7 days default)
            logger.debug(f"CRM: Follow-up scheduling considered for {from_email}")
            # The follow-up engine's generate_suggestions() handles the logic
            # We just ensure the quote is tracked so it appears in suggestions
            
        except Exception as e:
            logger.warning(f"Error scheduling follow-up: {e}")
    
    def get_customer_context(self, from_email: str) -> Optional[Dict]:
        """
        Get customer health context to enrich pipeline processing.
        
        This provides:
        - Customer health score
        - Risk level
        - Engagement trend
        - Quote history
        """
        if not self.health_scorer_available or not self.health_scorer:
            return None
        
        try:
            health = self.health_scorer.get_customer_health(from_email)
            if health:
                return {
                    "health_score": health.score,
                    "risk_level": health.risk_level.value,
                    "engagement_trend": health.trend.value if health.trend else "unknown",
                    "days_since_contact": health.metrics.days_since_contact if health.metrics else 0,
                    "total_quotes": health.metrics.total_quotes if health.metrics else 0,
                    "active_quotes": health.metrics.active_quotes if health.metrics else 0,
                }
        except Exception as e:
            logger.debug(f"Error getting customer context: {e}")
        
        return None
    
    def process_with_orchestrator(
        self,
        body: str,
        from_email: str,
        subject: str = "",
        thread_id: str = "",
        previous_response: str = ""
    ) -> Optional[str]:
        """
        Process email through the UNIFIED PIPELINE ORCHESTRATOR.
        
        This is the recommended method that automatically routes through:
        
        ┌─────────────────────────────────────────────────────────────────┐
        │  1. QUERY ANALYSIS → Classify, detect intent, extract entities │
        │  2. IF FEEDBACK → FEEDBACK HANDLER → Learn & confirm           │
        │  3. IF QUESTION → ANSWER GENERATION → Deep research            │
        │  4. → ANSWER PACKAGING → MBB-quality formatting                │
        └─────────────────────────────────────────────────────────────────┘
        
        Returns the final response to send.
        """
        if not self.orchestrator_available or not self.orchestrator:
            logger.warning("Orchestrator not available, falling back to legacy pipeline")
            return self.process_email(body, from_email, subject, thread_id)
        
        try:
            logger.info("\n" + "=" * 70)
            logger.info("UNIFIED PIPELINE ORCHESTRATOR - EMAIL PROCESSING")
            logger.info("=" * 70)
            
            # Get customer context from CRM for enriched processing
            customer_context = self.get_customer_context(from_email)
            if customer_context:
                logger.info(f"  Customer Health: {customer_context.get('health_score', 'N/A')}/100")
                logger.info(f"  Risk Level: {customer_context.get('risk_level', 'unknown')}")
                logger.info(f"  Active Quotes: {customer_context.get('active_quotes', 0)}")
            
            result = self.orchestrator.process_email(
                body=body,
                from_email=from_email,
                subject=subject,
                thread_id=thread_id,
                previous_response=previous_response
            )
            
            logger.info(f"\n✅ ORCHESTRATOR COMPLETE")
            logger.info(f"  Type: {result.message_type.value}")
            logger.info(f"  Confidence: {result.confidence:.2f}")
            logger.info(f"  Time: {result.processing_time_seconds:.1f}s")
            logger.info(f"  Pipeline: {' → '.join(result.pipeline_log)}")
            
            return result.response
            
        except Exception as e:
            logger.error(f"Orchestrator error: {e}")
            return self.process_email(body, from_email, subject, thread_id)


class EmailIraBridge:
    """Main bridge that connects Gmail to IRA Agent with FULL PIPELINE."""
    
    def __init__(self):
        if not GMAIL_AVAILABLE:
            raise RuntimeError("Gmail API not available")
        
        if not IRA_AGENT_AVAILABLE:
            raise RuntimeError("IRA Agent not available")
        
        self.gmail = GmailClient()
        self.ira = IraAgentBridge()
        self.processed_ids = set()
        self.conversation_history = {}  # Track conversations for feedback detection
    
    def _is_feedback(self, body: str) -> bool:
        """Detect if email is feedback/correction to previous response."""
        feedback_indicators = [
            "that is not correct",
            "that's not right",
            "you are wrong",
            "wrong machine",
            "wrong answer",
            "not the atf",
            "not the pf1",
            "you need to fix",
            "correction:",
            "actually,",
            "no, the",
            "should be",
            "instead use",
            "fix this"
        ]
        body_lower = body.lower()
        return any(indicator in body_lower for indicator in feedback_indicators)

    def _deep_think(self, query: str, draft_response: str, from_email: str, start_time: float) -> str:
        """
        Full deliberation pipeline using Ira's actual sub-agents.

        Each stage delegates to the real agent — Clio researches, Calliope
        writes, Vera verifies, Sophia reflects. No raw LLM calls for work
        that an agent already knows how to do.

        Stages:
          1. CLIO      — Deep research across Qdrant, Mem0, Neo4j
          2. VERA      — Rule-based fact-check (AM thickness, pricing, hallucinations)
          3. RELEVANCE — LLM check: does the draft answer the actual question?
          4. CALLIOPE  — Rewrite using research if issues found (up to N rounds)
          5. VERA      — Re-verify each rewrite
          6. CALLIOPE  — Final packaging with brand voice
          7. SOPHIA    — Reflect and log learnings for next time
        """
        import asyncio

        logger.info("=" * 60)
        logger.info("DELIBERATION PIPELINE — All agents activated")
        logger.info("=" * 60)

        current_draft = draft_response

        # ─── Import the real agents ───
        clio_research = None
        try:
            from openclaw.agents.ira.src.agents.researcher.agent import research
            clio_research = research
            logger.info("  Clio (researcher): loaded")
        except ImportError:
            try:
                from src.agents.researcher.agent import research
                clio_research = research
                logger.info("  Clio (researcher): loaded (relative)")
            except ImportError:
                logger.warning("  Clio (researcher): unavailable")

        vera_verify = None
        vera_report = None
        try:
            from openclaw.agents.ira.src.agents.fact_checker.agent import verify, generate_verification_report
            vera_verify = verify
            vera_report = generate_verification_report
            logger.info("  Vera (fact-checker): loaded")
        except ImportError:
            try:
                from src.agents.fact_checker.agent import verify, generate_verification_report
                vera_verify = verify
                vera_report = generate_verification_report
                logger.info("  Vera (fact-checker): loaded (relative)")
            except ImportError:
                logger.warning("  Vera (fact-checker): unavailable")

        calliope_write = None
        try:
            from openclaw.agents.ira.src.agents.writer.agent import write
            calliope_write = write
            logger.info("  Calliope (writer): loaded")
        except ImportError:
            try:
                from src.agents.writer.agent import write
                calliope_write = write
                logger.info("  Calliope (writer): loaded (relative)")
            except ImportError:
                logger.warning("  Calliope (writer): unavailable")

        sophia_reflect = None
        try:
            from openclaw.agents.ira.src.agents.reflector.agent import reflect
            sophia_reflect = reflect
            logger.info("  Sophia (reflector): loaded")
        except ImportError:
            try:
                from src.agents.reflector.agent import reflect
                sophia_reflect = reflect
                logger.info("  Sophia (reflector): loaded (relative)")
            except ImportError:
                logger.warning("  Sophia (reflector): unavailable")

        openai_client = None
        try:
            from openai import OpenAI
            openai_client = OpenAI()
        except Exception:
            pass

        def _run_async(coro):
            """Run an async agent function from sync context."""
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as pool:
                        return pool.submit(asyncio.run, coro).result()
                return loop.run_until_complete(coro)
            except RuntimeError:
                return asyncio.run(coro)

        # ─────────────────────────────────────────────
        # STAGE 1: CLIO — Deep research
        # ─────────────────────────────────────────────
        logger.info("\n[STAGE 1/7] CLIO — Deep research across all knowledge sources...")
        research_output = ""

        if clio_research:
            try:
                research_output = _run_async(clio_research(
                    query,
                    context={"user_id": from_email, "channel": "email"}
                ))
                logger.info(f"  Clio returned {len(research_output)} chars of research")
            except Exception as e:
                logger.warning(f"  Clio research failed: {e}")

        # ─────────────────────────────────────────────
        # STAGE 2: VERA — Fact-check the initial draft
        # ─────────────────────────────────────────────
        logger.info("\n[STAGE 2/7] VERA — Fact-checking initial draft...")
        vera_issues = []

        if vera_report:
            try:
                report = vera_report(current_draft, query)
                current_draft = report.verified_draft
                vera_issues = report.issues + report.warnings
                if report.corrections_made:
                    logger.info(f"  Vera corrections: {report.corrections_made}")
                if vera_issues:
                    logger.info(f"  Vera issues: {vera_issues}")
                else:
                    logger.info(f"  Vera: passed (confidence {report.confidence:.2f})")
            except Exception as e:
                logger.warning(f"  Vera fact-check failed: {e}")

        # ─────────────────────────────────────────────
        # STAGE 3: RELEVANCE — Does the draft answer the question?
        # ─────────────────────────────────────────────
        logger.info("\n[STAGE 3/7] RELEVANCE — Checking if draft answers the actual question...")
        needs_rewrite = False

        if openai_client:
            try:
                relevance_check = openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": (
                            "You evaluate whether a response answers the question asked. "
                            'Reply ONLY with JSON: {"answers_question": true/false, "reason": "brief explanation"}'
                        )},
                        {"role": "user", "content": (
                            f"QUESTION:\n{query[:1500]}\n\nRESPONSE:\n{current_draft[:1500]}"
                        )},
                    ],
                    temperature=0.0,
                    max_tokens=150,
                )
                check_text = relevance_check.choices[0].message.content.strip()
                try:
                    check_data = json.loads(check_text)
                    if not check_data.get("answers_question", True):
                        needs_rewrite = True
                        reason = check_data.get("reason", "Draft does not answer the question")
                        logger.info(f"  RELEVANCE FAIL: {reason}")
                except (json.JSONDecodeError, AttributeError):
                    if '"answers_question": false' in check_text.lower():
                        needs_rewrite = True
                        logger.info(f"  RELEVANCE FAIL (parsed from text)")

                if not needs_rewrite:
                    logger.info("  Relevance check: PASSED")
            except Exception as e:
                logger.warning(f"  Relevance check failed: {e}")

        if vera_issues:
            needs_rewrite = True

        # Always synthesize from Clio's research when available — her research
        # is deeper than the initial RAG (more sources, more chunks, graph data).
        # Even if the initial draft "passed" relevance, Clio's version will be richer.
        if research_output and openai_client:
            needs_rewrite = True
            logger.info("  Forcing synthesis from Clio's research (always richer than initial draft)")

        # ─────────────────────────────────────────────
        # STAGE 4: REWRITE — Synthesize answer from Clio's research
        # ─────────────────────────────────────────────
        round_num = 0
        while needs_rewrite and round_num < MAX_REFINEMENT_ROUNDS:
            round_num += 1
            logger.info(f"\n[STAGE 4/7] REWRITE — Round {round_num}/{MAX_REFINEMENT_ROUNDS} (LLM synthesis from research)...")

            if openai_client and research_output:
                try:
                    rewrite_result = openai_client.chat.completions.create(
                        model="gpt-4o",
                        messages=[
                            {"role": "system", "content": (
                                "You are Ira, the Intelligent Revenue Assistant for Machinecraft Technologies. "
                                "You have been given research findings from your knowledge base. "
                                "Write a response that DIRECTLY answers the question using SPECIFIC data "
                                "from the research — names, numbers, companies, models, prices.\n\n"
                                "CRITICAL ANTI-HALLUCINATION RULES:\n"
                                "- ONLY state facts that are EXPLICITLY written in the research findings below.\n"
                                "- NEVER infer or fabricate connections between entities from different documents.\n"
                                "  For example, if Company A appears in one document and Event B in another,\n"
                                "  do NOT say 'Company A attended Event B' unless the research explicitly says so.\n"
                                "- Each fact you state must be traceable to a specific [Source] in the research.\n\n"
                                "CRITICAL DATA EXTRACTION RULES:\n"
                                "- ALWAYS extract and list SPECIFIC names, companies, contacts, numbers.\n"
                                "- NEVER summarize with counts like '25 leads from NCR' — list the actual names.\n"
                                "- NEVER say 'refer to the contact lists' — YOU are the contact list. Extract the data.\n"
                                "- If the research contains company names, list every single one.\n"
                                "- If the research contains contact names and emails, include them.\n"
                                "- If asked about leads/customers, give a structured list with:\n"
                                "  Company name, Contact person, Machine interest, Location, Status\n"
                                "- If the exact data requested isn't available, list what IS available\n"
                                "  with the same level of specificity (names, not summaries).\n\n"
                                "OTHER RULES:\n"
                                "- Answer the EXACT question. If they ask for leads, give lead names.\n"
                                "- If the sender is Rushabh (internal), this is a strategy request — be direct.\n"
                                "- Use plain text lists (dashes, not bullets or markdown).\n"
                                "- Be thorough. Include ALL relevant data from the research, not a subset.\n"
                                "- AM series is ALWAYS ≤1.5mm only.\n"
                                "- All prices subject to configuration and current pricing."
                            )},
                            {"role": "user", "content": (
                                f"QUESTION:\n{query}\n\n"
                                f"RESEARCH FINDINGS:\n{research_output[:12000]}\n\n"
                                "Extract ALL specific data from the research and write a detailed response. "
                                "List every company name, contact, and detail you can find."
                            )},
                        ],
                        temperature=0.2,
                        max_tokens=4000,
                    )
                    rewritten = rewrite_result.choices[0].message.content.strip()
                    if rewritten and len(rewritten) > 30:
                        current_draft = rewritten
                        logger.info(f"  LLM synthesis produced {len(current_draft)} chars")
                except Exception as e:
                    logger.warning(f"  LLM synthesis failed, falling back to Calliope: {e}")
                    if calliope_write:
                        try:
                            rewritten = _run_async(calliope_write(
                                query,
                                context={"research_output": research_output, "channel": "email", "intent": "general"}
                            ))
                            if rewritten and len(rewritten) > 30:
                                current_draft = rewritten
                        except Exception:
                            pass
            elif calliope_write:
                try:
                    rewritten = _run_async(calliope_write(
                        query,
                        context={"research_output": research_output, "channel": "email", "intent": "general"}
                    ))
                    if rewritten and len(rewritten) > 30:
                        current_draft = rewritten
                        logger.info(f"  Calliope produced {len(current_draft)} chars")
                except Exception as e:
                    logger.warning(f"  Calliope rewrite failed: {e}")

            # ─── STAGE 5: VERA — Re-verify the rewrite ───
            logger.info(f"\n[STAGE 5/7] VERA — Re-verifying rewrite...")
            if vera_report:
                try:
                    report = vera_report(current_draft, query)
                    current_draft = report.verified_draft
                    if report.issues:
                        logger.info(f"  Vera still found issues: {report.issues}")
                    else:
                        logger.info(f"  Vera: rewrite passed (confidence {report.confidence:.2f})")
                        needs_rewrite = False
                except Exception as e:
                    logger.warning(f"  Vera re-verify failed: {e}")
                    needs_rewrite = False
            else:
                needs_rewrite = False

            # Quick relevance re-check
            if openai_client and needs_rewrite:
                try:
                    re_check = openai_client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[
                            {"role": "system", "content": 'Does this answer the question? Reply: {"passes": true/false}'},
                            {"role": "user", "content": f"Q: {query[:500]}\nA: {current_draft[:1000]}"},
                        ],
                        temperature=0.0, max_tokens=50,
                    )
                    if '"passes": true' in re_check.choices[0].message.content.lower():
                        needs_rewrite = False
                        logger.info("  Relevance re-check: PASSED")
                except Exception:
                    needs_rewrite = False

        logger.info(f"\n[STAGE 4-5] REFINE — {'No rewrite needed' if round_num == 0 else f'{round_num} round(s) completed'}")

        # ─────────────────────────────────────────────
        # STAGE 6: PACKAGE — Clean plain-text email
        # ─────────────────────────────────────────────
        logger.info("\n[STAGE 6/7] PACKAGE — Final email formatting...")

        if openai_client:
            try:
                package_result = openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": (
                            "Convert this draft into a clean PLAIN TEXT email. Rules:\n"
                            "- NO markdown (no **, no ##, no bullet symbols like •)\n"
                            "- Use plain dashes (-) for lists\n"
                            "- Start with 'Hi Rushabh,' if internal, or 'Hi [Name],' if customer\n"
                            "- DO NOT add qualification questions (What size? What material? etc.)\n"
                            "- DO NOT add information not in the draft\n"
                            "- DO NOT invent connections between companies and events/exhibitions\n"
                            "- If the draft says 'I don't have X', keep that honest admission\n"
                            "- Keep all specific data (names, numbers, companies, prices)\n"
                            "- End with: Cheers,\\nIra\\n\\nMachinecraft Technologies\\nira@machinecraft.org\n"
                            "- Keep it concise but complete"
                        )},
                        {"role": "user", "content": current_draft},
                    ],
                    temperature=0.2,
                    max_tokens=2000,
                )
                packaged = package_result.choices[0].message.content.strip()
                if packaged and len(packaged) > 30:
                    current_draft = packaged
                    logger.info(f"  Packaged as plain text ({len(current_draft)} chars)")
            except Exception as e:
                logger.warning(f"  Packaging failed: {e}")

        # ─────────────────────────────────────────────
        # STAGE 7: SOPHIA — Reflect and learn
        # ─────────────────────────────────────────────
        logger.info("\n[STAGE 7/7] SOPHIA — Reflecting on this interaction...")

        if sophia_reflect:
            try:
                reflection = _run_async(sophia_reflect({
                    "user_message": query,
                    "response": current_draft,
                    "intent": "email",
                    "results": {
                        "research_length": len(research_output),
                        "refinement_rounds": round_num,
                        "vera_issues": vera_issues,
                    }
                }))
                if reflection.issues:
                    logger.info(f"  Sophia flagged: {reflection.issues}")
                if reflection.lessons:
                    logger.info(f"  Sophia learned: {reflection.lessons}")
                logger.info(f"  Quality score: {reflection.quality_score.overall:.2f}")
            except Exception as e:
                logger.warning(f"  Sophia reflection failed: {e}")

        # ─── Ensure minimum response time ───
        self._pad_to_min_time(start_time)

        elapsed_total = time.time() - start_time
        logger.info("\n" + "=" * 60)
        logger.info(f"DELIBERATION COMPLETE — {elapsed_total:.0f}s total")
        logger.info(f"  Agents used: Clio, Vera, Calliope, Sophia")
        logger.info(f"  Refinement rounds: {round_num}")
        logger.info(f"  Final response: {len(current_draft)} chars")
        logger.info("=" * 60)

        return current_draft

    def _pad_to_min_time(self, start_time: float):
        """Ensure minimum elapsed time so replies don't feel instant."""
        elapsed = time.time() - start_time
        remaining = MIN_RESPONSE_TIME - elapsed
        if remaining > 0:
            logger.info(f"  Padding {remaining:.0f}s to reach {MIN_RESPONSE_TIME}s minimum response time")
            time.sleep(remaining)
    
    @staticmethod
    def _strip_email_signature(body: str) -> str:
        """Remove email signatures, disclaimers, and quoted replies from body."""
        lines = body.split('\n')
        clean_lines = []
        for line in lines:
            stripped = line.strip()
            if stripped.startswith('With Best Regards'):
                break
            if stripped.startswith('Best Regards'):
                break
            if stripped.startswith('Kind Regards'):
                break
            if stripped.startswith('Regards,'):
                break
            if stripped.startswith('Cheers,'):
                break
            if stripped.startswith('--'):
                break
            if stripped.startswith('Sent from my'):
                break
            if re.match(r'^On .+ wrote:$', stripped):
                break
            if stripped.startswith('>'):
                continue
            if 'Director Responsible for Sales' in stripped:
                break
            if 'Click here' in stripped and 'linkedin' in stripped.lower():
                break
            clean_lines.append(line)

        result = '\n'.join(clean_lines).strip()
        return result if len(result) > 10 else body.strip()

    def _format_thread_context(self, thread_history: List[Dict], current_body: str) -> str:
        """Format thread history into context string for Ira."""
        if not thread_history or len(thread_history) <= 1:
            return current_body

        parts = ["=== CONVERSATION THREAD (oldest first) ===\n"]
        for i, msg in enumerate(thread_history[:-1]):
            role_label = "IRA" if msg['role'] == 'assistant' else "CUSTOMER"
            body_preview = msg.get('body', '')[:1000].strip()
            if body_preview:
                parts.append(f"[{role_label}]: {body_preview}\n")

        parts.append("=== LATEST MESSAGE (respond to this) ===\n")
        parts.append(current_body)
        return "\n".join(parts)

    def process_single_email(self, email: Dict) -> bool:
        """Process a single email through IRA's full pipeline."""
        email_id = email['id']
        thread_id = email['thread_id']
        process_start = time.time()

        if email_id in self.processed_ids:
            return False
        
        from_email = email['from']
        if '<' in from_email:
            from_email = from_email.split('<')[1].rstrip('>')
        
        subject = email['subject']
        body = email['body'] or email['snippet']
        
        logger.info(f"Processing email from {from_email}: {subject[:50] if subject else 'No subject'}")

        # Fetch full thread history for conversation context
        thread_history = self.gmail.get_thread_history(thread_id)
        if len(thread_history) > 1:
            logger.info(f"Thread context: {len(thread_history)} messages in conversation")
            body_with_context = self._format_thread_context(thread_history, body)
        else:
            body_with_context = body

        # Check if this is feedback/correction
        is_feedback = self._is_feedback(body) and thread_id in self.conversation_history
        
        if is_feedback:
            logger.info("\n" + "=" * 60)
            logger.info("FEEDBACK DETECTED - RUNNING FEEDBACK PIPELINE")
            logger.info("=" * 60)
            
            original_response = self.conversation_history.get(thread_id, {}).get('response', '')
            confirmation = self.ira.store_feedback(from_email, body, original_response)
            
            if confirmation:
                response = self._deep_think(body, confirmation, from_email, process_start)

                self.conversation_history[thread_id] = {
                    'question': body,
                    'response': response,
                    'timestamp': datetime.now().isoformat()
                }
                
                self.processed_ids.add(email_id)
                message_id = email.get('message_id', '')

                success = self.gmail.send_reply(
                    to=from_email,
                    subject=f"Re: {subject}" if subject else "Re: Your feedback",
                    body=response,
                    thread_id=thread_id,
                    message_id=message_id
                )
                self.gmail.mark_as_read(email_id)
                logger.info(f"Sent feedback confirmation to {from_email}")
                return success
            else:
                logger.info("No specific corrections - processing as normal message")
        
        # Build the query: strip signature noise, include subject
        clean_body = self._strip_email_signature(body)
        query_for_processing = clean_body
        if subject and not subject.lower().startswith("re:"):
            query_for_processing = f"{subject}: {query_for_processing}"

        # PRIMARY PATH: Use Telegram Gateway engine (same rich pipeline)
        # This gives email the same 15-phase processing as Telegram:
        # memory, coreference, RAG (top_k=10), brain orchestrator, Mem0,
        # cross-channel context, conversational enhancement, agentic tool loop,
        # adaptive retrieval, and generate_answer with full context pack.
        response = None
        gateway = get_gateway_engine()
        if gateway:
            try:
                logger.info("Using Gateway Engine (shared Telegram pipeline) for email processing")

                # Save thread history as conversation turns so the gateway has context
                if thread_history and len(thread_history) > 1:
                    for msg in thread_history[:-1]:
                        try:
                            gateway._save_conversation_turn(
                                chat_id=from_email,
                                user_message=msg['body'][:500] if msg['role'] == 'user' else '',
                                assistant_response=msg['body'][:500] if msg['role'] == 'assistant' else '',
                            )
                        except Exception:
                            pass

                gateway_result = gateway.handle_free_text(
                    text=query_for_processing,
                    chat_id=from_email,
                )

                if gateway_result and gateway_result.text and len(gateway_result.text.strip()) > 20:
                    response = gateway_result.text
                    logger.info(f"Gateway Engine produced {len(response)} chars")

                    # Save this turn for future context
                    try:
                        gateway._save_conversation_turn(
                            chat_id=from_email,
                            user_message=query_for_processing[:500],
                            assistant_response=response[:1000],
                        )
                    except Exception:
                        pass
                else:
                    logger.warning("Gateway Engine returned empty, falling back to IraAgent")
            except Exception as e:
                logger.warning(f"Gateway Engine failed, falling back to IraAgent: {e}")
                import traceback
                logger.debug(traceback.format_exc())

        # FALLBACK: Use IraAgent if gateway engine unavailable or failed
        if not response:
            logger.info("Using IraAgent fallback for email processing")
            agent_response = self.ira.process_email(
                body=body_with_context,
                from_email=from_email,
                subject=subject,
                thread_id=thread_id
            )
            if agent_response:
                response = agent_response if isinstance(agent_response, str) else getattr(agent_response, 'message', str(agent_response))

        if response:
            # Deep think: deliberation pipeline with all agents
            response = self._deep_think(query_for_processing, response, from_email, process_start)

        # Store in conversation history for feedback detection
        self.conversation_history[thread_id] = {
            'question': body[:500],
            'response': response[:500] if response else '',
            'timestamp': datetime.now().isoformat()
        }
        
        if response:
            # Send reply
            success = self.gmail.send_reply(
                to=from_email,
                subject=subject,
                body=response,
                thread_id=thread_id,
                message_id=email_id
            )
            
            if success:
                self.gmail.mark_as_read(email_id)
                self.processed_ids.add(email_id)
                logger.info(f"Successfully replied to {from_email}")
                if CHAT_LOG_AVAILABLE:
                    try:
                        log_interaction("email", from_email, "user", body or "", {"subject": subject})
                        log_interaction("email", from_email, "assistant", response or "", {"subject": subject})
                    except Exception as _e:
                        logger.debug("Chat log: %s", _e)
                
                # CRM Integration: Handle post-reply actions
                self.ira._handle_post_reply_crm(
                    from_email=from_email,
                    subject=subject,
                    body=body,
                    response=response,
                    success=True
                )
                
                return True
        else:
            logger.warning(f"No response from IRA for email from {from_email}")
            # Still mark as read to avoid reprocessing
            self.gmail.mark_as_read(email_id)
            self.processed_ids.add(email_id)
        
        return False
    
    def run_once(self):
        """Process all unread emails once."""
        logger.info("Checking for unread emails...")
        emails = self.gmail.get_unread_emails()
        
        if not emails:
            logger.info("No unread emails")
            return
        
        logger.info(f"Found {len(emails)} unread emails")
        
        for email in emails:
            try:
                self.process_single_email(email)
            except Exception as e:
                logger.error(f"Error processing email: {e}")
                import traceback
                logger.error(traceback.format_exc())
    
    def _send_proactive_email(
        self,
        email_type: str,  # "startup" | "daily" | "weekly"
        research_output: str = "",
    ) -> bool:
        """Send a proactive email to Rushabh. Uses different research prompts and templates per type."""
        import asyncio

        def _run(coro):
            try:
                return asyncio.run(coro)
            except RuntimeError:
                loop = asyncio.new_event_loop()
                try:
                    return loop.run_until_complete(coro)
                finally:
                    loop.close()

        research_prompts = {
            "startup": (
                "What are the most important pending leads, recent customer inquiries, "
                "and any follow-ups needed for Machinecraft this week? Limit to top 2-3 items."
            ),
            "daily": (
                "What are the top 3 most urgent pending items for Machinecraft today? "
                "Include: pending deals, follow-ups due, and any urgent customer inquiries. Be concise."
            ),
            "weekly": (
                "For Machinecraft's weekly briefing, research and summarize: "
                "1) Pipeline health and pending deals (top 5 by priority), "
                "2) Follow-ups due this week, "
                "3) Wins from last week. "
                "Include specific company names, contacts, and status where available."
            ),
        }
        research_query = research_prompts.get(email_type, research_prompts["startup"])

        try:
            from openclaw.agents.ira.src.agents.researcher.agent import research
            if not research_output:
                research_output = _run(research(
                    research_query,
                    context={"user_id": RUSHABH_EMAIL, "channel": "email"}
                )) or ""
        except Exception as e:
            logger.warning(f"Research for {email_type} proactive failed: {e}")

        templates = {
            "startup": (
                "You are Ira, the Intelligent Revenue Assistant for Machinecraft Technologies. "
                "Write a brief, warm check-in email to Rushabh (your boss). Include: "
                "1) A warm greeting, 2) Confirm you're online and all systems are running, "
                "3) If you found any pending items from research, mention the top 2-3 briefly, "
                "4) Ask if there's anything specific he'd like you to work on today. "
                "Keep it short (5-8 sentences max). Sign off as: Cheers,\\nIra"
            ),
            "daily": (
                "You are Ira, the Intelligent Revenue Assistant for Machinecraft Technologies. "
                "Write a short daily digest email to Rushabh. Start with 'Your daily digest:' "
                "then list the top 3 pending items from the research (use plain dashes, no markdown). "
                "End with: 'Full details in dashboard.' Keep it under 150 words. "
                "Sign off as: Cheers,\\nIra"
            ),
            "weekly": (
                "You are Ira, the Intelligent Revenue Assistant for Machinecraft Technologies. "
                "Write a longer weekly briefing email to Rushabh. Structure: "
                "'Week ahead:' then 1) Pipeline snapshot (top 5 deals with status), "
                "2) Follow-ups due this week, 3) Wins from last week. "
                "Use plain text with dashes for lists. Be thorough but scannable. "
                "Sign off as: Cheers,\\nIra"
            ),
        }
        system_prompt = templates.get(email_type, templates["startup"])
        if research_output:
            system_prompt += f"\n\nContext from your research:\n{research_output[:4000] if email_type == 'weekly' else research_output[:2000]}"

        try:
            from openai import OpenAI
            client = OpenAI()
            result = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": "Write the email now."},
                ],
                temperature=0.5,
                max_tokens=800 if email_type == "weekly" else 500,
            )
            email_body = result.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"LLM for {email_type} proactive failed: {e}")
            return False

        subjects = {
            "startup": f"Ira Check-in — {datetime.now().strftime('%b %d')}",
            "daily": f"Ira Daily Digest — {datetime.now().strftime('%b %d')}",
            "weekly": f"Ira Weekly Briefing — Week of {datetime.now().strftime('%b %d')}",
        }
        subject = subjects.get(email_type, subjects["startup"])

        thread_id = self.gmail.send_new_email(
            to=RUSHABH_EMAIL,
            subject=subject,
            body=email_body,
        )
        if thread_id:
            logger.info(f"Proactive {email_type} email sent to {RUSHABH_EMAIL} (thread: {thread_id})")
            return True
        logger.warning(f"Failed to send proactive {email_type} email")
        return False

    def send_proactive_checkin(self):
        """Send a proactive check-in email to Rushabh on startup (I'm online + top 2-3 pending)."""
        logger.info("Sending proactive check-in to Rushabh...")
        try:
            self._send_proactive_email("startup")
        except Exception as e:
            logger.error(f"Proactive check-in failed: {e}")
            import traceback
            logger.error(traceback.format_exc())

    def _run_proactive_scheduler(self):
        """Background thread: each cycle, check if weekly/daily proactive is due and send."""
        while True:
            try:
                now = datetime.now()
                today_str = now.strftime("%Y-%m-%d")
                state = _load_proactive_state()

                # Weekly: Monday PROACTIVE_WEEKLY_HOUR, haven't sent this week
                if PROACTIVE_WEEKLY_ENABLED:
                    monday_this_week = (now - timedelta(days=now.weekday())).strftime("%Y-%m-%d")
                    if (
                        now.weekday() == PROACTIVE_WEEKLY_DAY
                        and now.hour >= PROACTIVE_WEEKLY_HOUR
                        and state.get("last_weekly", "") < monday_this_week
                    ):
                        logger.info("Proactive scheduler: sending weekly briefing...")
                        if self._send_proactive_email("weekly"):
                            _save_proactive_state(last_weekly=today_str)

                # Daily: PROACTIVE_DAILY_HOUR, haven't sent today
                if PROACTIVE_DAILY_ENABLED:
                    if (
                        now.hour >= PROACTIVE_DAILY_HOUR
                        and state.get("last_daily", "") != today_str
                    ):
                        logger.info("Proactive scheduler: sending daily digest...")
                        if self._send_proactive_email("daily"):
                            _save_proactive_state(last_daily=today_str)

            except Exception as e:
                logger.warning(f"Proactive scheduler error: {e}")
            time.sleep(POLL_INTERVAL)

    def run_loop(self):
        """Continuously poll for new emails."""
        logger.info(f"Starting email polling loop (interval: {POLL_INTERVAL}s)")
        logger.info("Using FULL DELIBERATION PIPELINE (Clio, Vera, Calliope, Sophia)")

        # Log agent status
        status = self.ira.agent.get_status()
        logger.info(f"Agent: {status['agent']['name']} v{status['agent']['version']}")
        logger.info(f"Modules: {json.dumps(status['modules'], indent=2)}")

        # Send proactive check-in on startup (quick "I'm online" + top 2-3 pending)
        self.send_proactive_checkin()

        # Start proactive scheduler in background thread (weekly/daily cadence)
        scheduler = threading.Thread(
            target=self._run_proactive_scheduler,
            daemon=True,
            name="proactive_scheduler",
        )
        scheduler.start()
        logger.info("Proactive scheduler started (weekly/daily cadence)")

        while True:
            try:
                self.run_once()
            except Exception as e:
                logger.error(f"Loop error: {e}")
                import traceback
                logger.error(traceback.format_exc())

            logger.info(f"Sleeping for {POLL_INTERVAL}s...")
            time.sleep(POLL_INTERVAL)


# Keep backward compatibility alias
EmailOpenClawBridge = EmailIraBridge


def main():
    global POLL_INTERVAL
    
    parser = argparse.ArgumentParser(description="Email-IRA Bridge (Full Pipeline)")
    parser.add_argument("--loop", action="store_true", help="Run in continuous polling mode")
    parser.add_argument("--once", action="store_true", help="Process emails once and exit")
    parser.add_argument("--interval", type=int, default=POLL_INTERVAL, help="Poll interval in seconds")
    parser.add_argument("--status", action="store_true", help="Show IRA agent status")
    args = parser.parse_args()
    
    POLL_INTERVAL = args.interval
    
    # Status check
    if args.status:
        if IRA_AGENT_AVAILABLE:
            agent = get_agent()
            status = agent.get_status()
            print(json.dumps(status, indent=2))
        else:
            print("IRA Agent not available")
        return
    
    try:
        logger.info("="*60)
        logger.info("  EMAIL-IRA BRIDGE - Full Pipeline Mode")
        logger.info("="*60)
        logger.info("This bridge uses IRA's COMPLETE cognitive pipeline:")
        logger.info("  1. Mem0 memory recall")
        logger.info("  2. RAG document retrieval")
        logger.info("  3. Brain orchestration (machine recommender, etc.)")
        logger.info("  4. Episodic memory for learning")
        logger.info("")
        
        bridge = EmailIraBridge()
        
        if args.loop:
            bridge.run_loop()
        else:
            bridge.run_once()
            
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
