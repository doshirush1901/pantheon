#!/usr/bin/env python3
"""
PROMETHEUS - Email-based Adversarial Test Agent for IRA Learning System

I am Prometheus. I test IRA through realistic email conversations and measure
whether the system learns from feedback.

Usage:
    python agents/prometheus/email_test_runner.py --scenario AM_THICKNESS_LEARNING
    python agents/prometheus/email_test_runner.py --all
    python agents/prometheus/email_test_runner.py --dry-run  # Test without sending emails
"""

import argparse
import asyncio
import base64
import json
import os
import re
import sys
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
PROMETHEUS_DIR = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

# Load environment
from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

# Configuration
SCENARIOS_FILE = PROMETHEUS_DIR / "test_scenarios.json"
RESULTS_FILE = PROJECT_ROOT / "email_test_results.md"
METRICS_FILE = PROJECT_ROOT / "learning_metrics.json"
REPORT_FILE = PROJECT_ROOT / "improvement_report.md"

# Gmail settings - Dual OAuth for two-way communication
GMAIL_SCOPES = ['https://www.googleapis.com/auth/gmail.modify']

# Rushabh's mailbox (sends questions TO IRA)
RUSHABH_CREDENTIALS = PROJECT_ROOT / "credentials_rushabh.json"
RUSHABH_TOKEN = PROJECT_ROOT / "token_rushabh.json"
RUSHABH_EMAIL = os.getenv("RUSHABH_EMAIL", "rushabh@machinecraft.org")

# IRA's mailbox (reads Rushabh's messages, sends replies)
IRA_CREDENTIALS = PROJECT_ROOT / "credentials.json"
IRA_TOKEN = PROJECT_ROOT / "token.json"
IRA_EMAIL = os.getenv("IRA_EMAIL", "ira@machinecraft.org")

# Timing
POLL_INTERVAL = 10  # seconds between checks for IRA's response
MAX_WAIT_TIME = 300  # 5 minutes max wait for response


@dataclass
class EvaluationResult:
    """Result of evaluating IRA's response."""
    score: float
    scores_breakdown: Dict[str, int]
    critical_rule_violated: Optional[str]
    keywords_found: int
    keywords_expected: int
    reasoning: str
    improvement_suggestion: str


@dataclass
class LearningMetric:
    """Metrics tracking IRA's learning."""
    scenario_id: str
    initial_score: float
    correction_sent: bool
    post_feedback_score: Optional[float]
    verification_score: Optional[float]
    learning_delta: float
    learned: bool
    timestamp: str


@dataclass
class ConversationLog:
    """Log of a test conversation."""
    scenario_id: str
    scenario_name: str
    messages: List[Dict] = field(default_factory=list)
    evaluations: List[EvaluationResult] = field(default_factory=list)
    learning_metric: Optional[LearningMetric] = None


class PrometheusJudge:
    """Evaluates IRA's responses using Nemesis-like scoring."""
    
    def evaluate(
        self,
        response: str,
        expected_keywords: List[str],
        critical_rule: Optional[str],
        original_question: str
    ) -> EvaluationResult:
        """Evaluate IRA's response."""
        scores = {
            "accuracy": 5,
            "completeness": 5,
            "clarity": 5,
            "rule_adherence": 5
        }
        reasoning_parts = []
        improvement_suggestion = None
        critical_rule_violated = None
        
        response_lower = response.lower()
        question_lower = original_question.lower()
        
        # Check critical rules
        if critical_rule == "AM_THICKNESS":
            thickness_match = re.search(r'(\d+(?:\.\d+)?)\s*mm', question_lower)
            if thickness_match:
                thickness = float(thickness_match.group(1))
                if thickness > 1.5:
                    # Check if IRA incorrectly recommends AM for thick material
                    recommends_am_incorrectly = any([
                        "am series" in response_lower and "recommend" in response_lower and "pf" not in response_lower,
                        "am series can handle" in response_lower,
                        "am series is suitable" in response_lower and str(thickness) in response_lower,
                    ])
                    
                    # Check if IRA correctly handles the thick material query
                    correct_response = any([
                        "pf1" in response_lower and "recommend" in response_lower,
                        "pf1 series" in response_lower,
                        "am series" in response_lower and ("cannot" in response_lower or "not suitable" in response_lower or "not recommend" in response_lower),
                        "1.5mm" in response_lower or "1.5 mm" in response_lower,
                        "thick" in response_lower and "pf" in response_lower,
                    ])
                    
                    if recommends_am_incorrectly:
                        scores["rule_adherence"] = 1
                        critical_rule_violated = "AM_THICKNESS"
                        reasoning_parts.append("CRITICAL: Incorrectly recommended AM series for thick material.")
                        improvement_suggestion = "Must warn that AM series is only for ≤1.5mm materials."
                    elif correct_response:
                        reasoning_parts.append("Correctly handled thick material query - recommended PF1.")
                    else:
                        reasoning_parts.append("Response about thick material needs clearer recommendation.")
        
        elif critical_rule == "PRICING_DISCLAIMER":
            has_price = any(x in response for x in ["₹", "Rs", "lakh", "crore", "INR"])
            if has_price:
                has_disclaimer = any([
                    "subject to" in response_lower,
                    "configuration" in response_lower,
                    "current pricing" in response_lower,
                ])
                if not has_disclaimer:
                    scores["rule_adherence"] = 1
                    critical_rule_violated = "PRICING_DISCLAIMER"
                    reasoning_parts.append("CRITICAL: Price without required disclaimer.")
                    improvement_suggestion = "Add 'subject to configuration and current pricing' to all prices."
                else:
                    reasoning_parts.append("Correctly included pricing disclaimer.")
        
        elif critical_rule == "NO_FABRICATION":
            fabrication_indicators = [
                len(response) > 300 and all(x not in response_lower for x in ["don't", "cannot", "no information", "not available"]),
                re.search(r'forming area.*\d+.*mm', response_lower) and "x-" in question_lower,
            ]
            if any(fabrication_indicators):
                scores["rule_adherence"] = 1
                critical_rule_violated = "NO_FABRICATION"
                reasoning_parts.append("CRITICAL: Appears to fabricate information.")
                improvement_suggestion = "Say 'I don't have information' for unknown products."
            elif any(x in response_lower for x in ["don't have", "cannot", "no information", "not available"]):
                reasoning_parts.append("Correctly declined to fabricate.")
        
        # Keyword matching
        keywords_found = sum(1 for kw in expected_keywords if kw.lower() in response_lower)
        keyword_ratio = keywords_found / len(expected_keywords) if expected_keywords else 1.0
        
        if keyword_ratio >= 0.8:
            scores["accuracy"] = 5
        elif keyword_ratio >= 0.6:
            scores["accuracy"] = 4
        elif keyword_ratio >= 0.4:
            scores["accuracy"] = 3
        elif keyword_ratio >= 0.2:
            scores["accuracy"] = 2
        else:
            scores["accuracy"] = 1
        
        reasoning_parts.append(f"Found {keywords_found}/{len(expected_keywords)} expected keywords.")
        
        # Completeness
        if len(response) > 300:
            scores["completeness"] = 5
        elif len(response) > 200:
            scores["completeness"] = 4
        elif len(response) > 100:
            scores["completeness"] = 3
        else:
            scores["completeness"] = 2
        
        # Clarity
        has_structure = any(["**" in response, "##" in response, "\n-" in response])
        if has_structure and len(response) > 100:
            scores["clarity"] = 5
        elif has_structure or len(response) > 150:
            scores["clarity"] = 4
        else:
            scores["clarity"] = 3
        
        # Final score
        if critical_rule_violated:
            final_score = min(2.0, sum(scores.values()) / 4)
        else:
            final_score = sum(scores.values()) / 4
        
        if not improvement_suggestion:
            if final_score >= 4.5:
                improvement_suggestion = "Excellent response."
            else:
                improvement_suggestion = "Continue improving knowledge retrieval."
        
        return EvaluationResult(
            score=round(final_score, 2),
            scores_breakdown=scores,
            critical_rule_violated=critical_rule_violated,
            keywords_found=keywords_found,
            keywords_expected=len(expected_keywords),
            reasoning=" ".join(reasoning_parts),
            improvement_suggestion=improvement_suggestion
        )


class GmailClient:
    """Gmail API client with dual mailbox support.
    
    Uses two OAuth tokens:
    - Rushabh's mailbox: For sending questions and reading IRA's replies
    - IRA's mailbox: For triggering IRA to process and respond
    """
    
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.rushabh_service = None  # Rushabh's mailbox
        self.ira_service = None      # IRA's mailbox
        if not dry_run:
            self._authenticate_both()
    
    def _authenticate_account(self, credentials_file: Path, token_file: Path, account_name: str):
        """Authenticate a single Gmail account."""
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build
        
        creds = None
        if token_file.exists():
            creds = Credentials.from_authorized_user_file(str(token_file), GMAIL_SCOPES)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
                token_file.write_text(creds.to_json())
            else:
                if not credentials_file.exists():
                    raise FileNotFoundError(f"Credentials not found: {credentials_file}")
                print(f"  Opening browser for {account_name} authentication...")
                flow = InstalledAppFlow.from_client_secrets_file(str(credentials_file), GMAIL_SCOPES)
                creds = flow.run_local_server(port=0)
                token_file.write_text(creds.to_json())
        
        service = build('gmail', 'v1', credentials=creds)
        
        # Verify
        profile = service.users().getProfile(userId='me').execute()
        print(f"✓ {account_name}: {profile.get('emailAddress')}")
        
        return service
    
    def _authenticate_both(self):
        """Authenticate both Rushabh and IRA mailboxes."""
        try:
            print("\nAuthenticating dual mailboxes...")
            
            # Rushabh's mailbox (sends questions, reads replies)
            self.rushabh_service = self._authenticate_account(
                RUSHABH_CREDENTIALS, RUSHABH_TOKEN, "Rushabh"
            )
            
            # IRA's mailbox (processes emails, sends replies)  
            self.ira_service = self._authenticate_account(
                IRA_CREDENTIALS, IRA_TOKEN, "IRA"
            )
            
            print("✓ Both mailboxes authenticated\n")
            
        except ImportError:
            print("⚠ Gmail API not available. Running in dry-run mode.")
            self.dry_run = True
        except Exception as e:
            print(f"⚠ Authentication error: {e}")
            print("  Run: python agents/prometheus/setup_dual_oauth.py")
            self.dry_run = True
    
    def send_email_as_rushabh(self, to: str, subject: str, body: str, thread_id: Optional[str] = None) -> Optional[str]:
        """Send an email FROM Rushabh TO the specified recipient."""
        if self.dry_run:
            print(f"  [DRY-RUN] Rushabh → {to}")
            print(f"  Subject: {subject}")
            print(f"  Body preview: {body[:100]}...")
            return f"dry-run-{time.time()}"
        
        try:
            message = MIMEText(body)
            message['to'] = to
            message['from'] = RUSHABH_EMAIL
            message['subject'] = subject
            
            raw = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
            
            send_body = {'raw': raw}
            if thread_id:
                send_body['threadId'] = thread_id
            
            result = self.rushabh_service.users().messages().send(
                userId='me',
                body=send_body
            ).execute()
            
            print(f"  ✓ Email sent from Rushabh to {to}")
            return result.get('id')
        except Exception as e:
            print(f"  ✗ Error sending email: {e}")
            return None
    
    def send_email(self, to: str, subject: str, body: str, thread_id: Optional[str] = None) -> Optional[str]:
        """Alias for send_email_as_rushabh for backward compatibility."""
        return self.send_email_as_rushabh(to, subject, body, thread_id)
    
    def trigger_ira_processing(self) -> bool:
        """Trigger IRA to process unread emails in her inbox."""
        if self.dry_run:
            print("  [DRY-RUN] Would trigger IRA processing")
            return True
        
        try:
            # Check IRA's unread emails
            results = self.ira_service.users().messages().list(
                userId='me',
                q='is:unread',
                maxResults=5
            ).execute()
            
            unread_count = len(results.get('messages', []))
            if unread_count > 0:
                print(f"  IRA has {unread_count} unread email(s) - triggering processing...")
                
                # Import and run IRA's email processing
                try:
                    sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
                    from email_openclaw_bridge import EmailIraBridge
                    
                    bridge = EmailIraBridge()
                    bridge.run_once()
                    print("  ✓ IRA processed emails")
                    return True
                except ImportError as e:
                    print(f"  ⚠ Could not import IRA bridge: {e}")
                    print("  IRA should process emails via her own email loop")
                    return True  # Assume IRA's email loop is running
            
            return True
        except Exception as e:
            print(f"  ⚠ Error triggering IRA: {e}")
            return False
    
    def wait_for_reply(self, subject: str, after_time: float, timeout: int = MAX_WAIT_TIME) -> Optional[Dict]:
        """Wait for IRA's reply in Rushabh's inbox."""
        if self.dry_run:
            print(f"  [DRY-RUN] Would wait for reply to: {subject}")
            return {
                "body": "[DRY-RUN] Simulated IRA response with PF1 series recommendation for thick materials. The PF1-C-2015 handles 1-8mm materials. AM series is only suitable for ≤1.5mm. Price: ₹45-55 lakhs (subject to configuration and current pricing).",
                "subject": f"Re: {subject}",
                "from": IRA_EMAIL,
            }
        
        start_time = time.time()
        search_subject = subject.replace("Re: ", "")
        
        print(f"  Waiting for IRA's reply (max {timeout}s)...")
        
        # First, trigger IRA to process the email
        self.trigger_ira_processing()
        
        while time.time() - start_time < timeout:
            try:
                # Check Rushabh's inbox for IRA's reply
                results = self.rushabh_service.users().messages().list(
                    userId='me',
                    q=f'from:{IRA_EMAIL} subject:"{search_subject}" after:{int(after_time)}',
                    maxResults=5
                ).execute()
                
                messages = results.get('messages', [])
                
                for msg in messages:
                    email_data = self._get_email_details(msg['id'], use_rushabh=True)
                    if email_data:
                        print(f"  ✓ IRA replied in {time.time() - start_time:.0f}s")
                        return email_data
                
            except Exception as e:
                print(f"  Error checking emails: {e}")
            
            # Periodically re-trigger IRA processing
            if int(time.time() - start_time) % 30 == 0 and time.time() - start_time > 5:
                self.trigger_ira_processing()
            
            time.sleep(POLL_INTERVAL)
        
        print(f"  ✗ No reply from IRA within {timeout}s")
        return None
    
    def _get_email_details(self, message_id: str, use_rushabh: bool = False) -> Optional[Dict]:
        """Get full email details from specified mailbox."""
        try:
            service = self.rushabh_service if use_rushabh else self.ira_service
            if not service:
                return None
                
            msg = service.users().messages().get(
                userId='me',
                id=message_id,
                format='full'
            ).execute()
            
            headers = {h['name'].lower(): h['value'] for h in msg['payload']['headers']}
            body = self._extract_body(msg['payload'])
            
            return {
                'id': message_id,
                'thread_id': msg.get('threadId'),
                'from': headers.get('from', ''),
                'subject': headers.get('subject', ''),
                'body': body,
            }
        except Exception as e:
            return None
    
    def _extract_body(self, payload: Dict) -> str:
        """Extract plain text body."""
        if 'body' in payload and payload['body'].get('data'):
            return base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8', errors='ignore')
        
        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain' and part['body'].get('data'):
                    return base64.urlsafe_b64decode(part['body']['data']).decode('utf-8', errors='ignore')
        return ""


class Prometheus:
    """
    Email-based Adversarial Test Agent for IRA Learning System.
    
    I am Prometheus. I bring the fire of feedback to make IRA stronger.
    """
    
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.gmail = GmailClient(dry_run=dry_run)
        self.judge = PrometheusJudge()
        self.scenarios = self._load_scenarios()
        self.conversation_logs: List[ConversationLog] = []
        self.learning_metrics: List[LearningMetric] = []
    
    def _load_scenarios(self) -> List[Dict]:
        """Load test scenarios."""
        with open(SCENARIOS_FILE, 'r') as f:
            return json.load(f)
    
    async def run_scenario(self, scenario: Dict) -> LearningMetric:
        """Run a complete test-evaluate-learn cycle for one scenario."""
        scenario_id = scenario["id"]
        scenario_name = scenario["name"]
        
        print(f"\n{'='*60}")
        print(f"  SCENARIO: {scenario_name}")
        print(f"  ID: {scenario_id}")
        print(f"{'='*60}")
        
        log = ConversationLog(
            scenario_id=scenario_id,
            scenario_name=scenario_name
        )
        
        # =====================================================================
        # PHASE 1: Initial Question
        # =====================================================================
        print("\n📤 PHASE 1: Sending initial question...")
        
        initial_q = scenario["initial_question"]
        send_time = time.time()
        
        msg_id = self.gmail.send_email(
            to=IRA_EMAIL,
            subject=initial_q["subject"],
            body=initial_q["body"]
        )
        
        log.messages.append({
            "phase": "initial_question",
            "direction": "outbound",
            "subject": initial_q["subject"],
            "body": initial_q["body"],
            "timestamp": datetime.now().isoformat()
        })
        
        # Wait for IRA's response
        print("⏳ Waiting for IRA's response...")
        response = self.gmail.wait_for_reply(initial_q["subject"], send_time)
        
        if not response:
            print("✗ No response from IRA")
            return LearningMetric(
                scenario_id=scenario_id,
                initial_score=0.0,
                correction_sent=False,
                post_feedback_score=None,
                verification_score=None,
                learning_delta=0.0,
                learned=False,
                timestamp=datetime.now().isoformat()
            )
        
        log.messages.append({
            "phase": "initial_response",
            "direction": "inbound",
            "body": response["body"],
            "timestamp": datetime.now().isoformat()
        })
        
        # Evaluate initial response
        initial_keywords = scenario.get("expected_keywords_verification", [])
        initial_eval = self.judge.evaluate(
            response=response["body"],
            expected_keywords=initial_keywords,
            critical_rule=scenario.get("critical_rule"),
            original_question=initial_q["body"]
        )
        log.evaluations.append(initial_eval)
        
        initial_score = initial_eval.score
        print(f"📊 Initial Score: {initial_score}/5.0")
        
        if initial_eval.critical_rule_violated:
            print(f"   ⚠ Critical Rule Violated: {initial_eval.critical_rule_violated}")
        
        # =====================================================================
        # PHASE 2: Correction Feedback (if needed)
        # =====================================================================
        correction_sent = False
        post_feedback_score = None
        
        if scenario.get("correction") and (initial_score < 4.0 or initial_eval.critical_rule_violated):
            print("\n📤 PHASE 2: Sending correction feedback...")
            
            correction = scenario["correction"]
            send_time = time.time()
            
            self.gmail.send_email(
                to=IRA_EMAIL,
                subject=correction["subject"],
                body=correction["body"]
            )
            correction_sent = True
            
            log.messages.append({
                "phase": "correction",
                "direction": "outbound",
                "subject": correction["subject"],
                "body": correction["body"],
                "timestamp": datetime.now().isoformat()
            })
            
            # Wait for acknowledgment
            ack_response = self.gmail.wait_for_reply(correction["subject"], send_time, timeout=120)
            
            if ack_response:
                log.messages.append({
                    "phase": "correction_ack",
                    "direction": "inbound",
                    "body": ack_response["body"],
                    "timestamp": datetime.now().isoformat()
                })
                print("✓ Correction acknowledged")
            
            # Small delay to let feedback be processed
            print("  Waiting for feedback to be processed...")
            await asyncio.sleep(5)
        else:
            print("\n⏭ PHASE 2: Skipped (initial response was good)")
        
        # =====================================================================
        # PHASE 3: Verification Question
        # =====================================================================
        verification_score = None
        
        if scenario.get("verification_question"):
            print("\n📤 PHASE 3: Sending verification question...")
            
            verify_q = scenario["verification_question"]
            send_time = time.time()
            
            self.gmail.send_email(
                to=IRA_EMAIL,
                subject=verify_q["subject"],
                body=verify_q["body"]
            )
            
            log.messages.append({
                "phase": "verification",
                "direction": "outbound",
                "subject": verify_q["subject"],
                "body": verify_q["body"],
                "timestamp": datetime.now().isoformat()
            })
            
            # Wait for response
            verify_response = self.gmail.wait_for_reply(verify_q["subject"], send_time)
            
            if verify_response:
                log.messages.append({
                    "phase": "verification_response",
                    "direction": "inbound",
                    "body": verify_response["body"],
                    "timestamp": datetime.now().isoformat()
                })
                
                # Evaluate verification response
                verify_eval = self.judge.evaluate(
                    response=verify_response["body"],
                    expected_keywords=scenario.get("expected_keywords_verification", []),
                    critical_rule=scenario.get("critical_rule"),
                    original_question=verify_q["body"]
                )
                log.evaluations.append(verify_eval)
                
                verification_score = verify_eval.score
                print(f"📊 Verification Score: {verification_score}/5.0")
        
        # =====================================================================
        # Calculate Learning Metrics
        # =====================================================================
        learning_delta = 0.0
        learned = False
        
        if verification_score is not None and correction_sent:
            learning_delta = verification_score - initial_score
            learned = learning_delta > 0 and verification_score >= 4.0
            
            if learned:
                print(f"\n🎉 LEARNING DETECTED! Delta: +{learning_delta:.2f}")
            else:
                print(f"\n📉 Learning delta: {learning_delta:.2f}")
        
        metric = LearningMetric(
            scenario_id=scenario_id,
            initial_score=initial_score,
            correction_sent=correction_sent,
            post_feedback_score=post_feedback_score,
            verification_score=verification_score,
            learning_delta=learning_delta,
            learned=learned,
            timestamp=datetime.now().isoformat()
        )
        
        log.learning_metric = metric
        self.conversation_logs.append(log)
        self.learning_metrics.append(metric)
        
        return metric
    
    async def run_all_scenarios(self):
        """Run all test scenarios."""
        print("\n" + "="*70)
        print("  PROMETHEUS - Email-based Adversarial Test Agent")
        print("  Mode:", "DRY-RUN" if self.dry_run else "LIVE")
        print("="*70)
        
        start_time = datetime.now()
        
        for scenario in self.scenarios:
            try:
                await self.run_scenario(scenario)
            except Exception as e:
                print(f"✗ Error in scenario {scenario['id']}: {e}")
                import traceback
                traceback.print_exc()
            
            # Pause between scenarios
            if not self.dry_run:
                print("\n  Pausing before next scenario...")
                await asyncio.sleep(10)
        
        # Generate reports
        self._write_results(start_time)
        self._write_metrics()
        self._write_improvement_report(start_time)
        
        # Summary
        print("\n" + "="*70)
        print("  PROMETHEUS TEST CYCLE COMPLETE")
        print("="*70)
        
        total = len(self.learning_metrics)
        learned = sum(1 for m in self.learning_metrics if m.learned)
        avg_delta = sum(m.learning_delta for m in self.learning_metrics) / total if total else 0
        
        print(f"  Scenarios tested: {total}")
        print(f"  Learning detected: {learned}/{total}")
        print(f"  Average learning delta: {avg_delta:+.2f}")
        print(f"\n  Reports written to:")
        print(f"    - {RESULTS_FILE}")
        print(f"    - {METRICS_FILE}")
        print(f"    - {REPORT_FILE}")
    
    async def run_single_scenario(self, scenario_id: str):
        """Run a specific scenario by ID."""
        scenario = next((s for s in self.scenarios if s["id"] == scenario_id), None)
        if not scenario:
            print(f"✗ Scenario '{scenario_id}' not found")
            print(f"  Available: {[s['id'] for s in self.scenarios]}")
            return
        
        await self.run_scenario(scenario)
        
        # Generate reports
        self._write_results(datetime.now())
        self._write_metrics()
    
    def _write_results(self, start_time: datetime):
        """Write detailed conversation logs."""
        with open(RESULTS_FILE, "w") as f:
            f.write("# Prometheus Email Test Results\n\n")
            f.write(f"**Date:** {start_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"**Mode:** {'DRY-RUN' if self.dry_run else 'LIVE'}\n\n")
            
            for log in self.conversation_logs:
                f.write(f"## {log.scenario_name}\n\n")
                f.write(f"**Scenario ID:** `{log.scenario_id}`\n\n")
                
                # Messages
                f.write("### Conversation\n\n")
                for msg in log.messages:
                    direction = "➡️ SENT" if msg["direction"] == "outbound" else "⬅️ RECEIVED"
                    f.write(f"**{direction}** ({msg['phase']})\n")
                    if msg.get("subject"):
                        f.write(f"- Subject: {msg['subject']}\n")
                    f.write(f"```\n{msg['body'][:500]}{'...' if len(msg['body']) > 500 else ''}\n```\n\n")
                
                # Evaluations
                if log.evaluations:
                    f.write("### Evaluations\n\n")
                    for i, eval in enumerate(log.evaluations, 1):
                        f.write(f"**Evaluation {i}:** Score {eval.score}/5.0\n")
                        if eval.critical_rule_violated:
                            f.write(f"- ⚠️ Critical Rule: {eval.critical_rule_violated}\n")
                        f.write(f"- Keywords: {eval.keywords_found}/{eval.keywords_expected}\n")
                        f.write(f"- Reasoning: {eval.reasoning}\n\n")
                
                # Learning
                if log.learning_metric:
                    m = log.learning_metric
                    f.write("### Learning Metrics\n\n")
                    f.write(f"| Metric | Value |\n")
                    f.write(f"|--------|-------|\n")
                    f.write(f"| Initial Score | {m.initial_score} |\n")
                    f.write(f"| Correction Sent | {'Yes' if m.correction_sent else 'No'} |\n")
                    f.write(f"| Verification Score | {m.verification_score or 'N/A'} |\n")
                    f.write(f"| Learning Delta | {m.learning_delta:+.2f} |\n")
                    f.write(f"| **Learned** | {'✅ Yes' if m.learned else '❌ No'} |\n\n")
                
                f.write("---\n\n")
    
    def _write_metrics(self):
        """Write structured metrics JSON."""
        metrics_data = {
            "timestamp": datetime.now().isoformat(),
            "dry_run": self.dry_run,
            "scenarios": [asdict(m) for m in self.learning_metrics],
            "summary": {
                "total_scenarios": len(self.learning_metrics),
                "scenarios_learned": sum(1 for m in self.learning_metrics if m.learned),
                "average_initial_score": sum(m.initial_score for m in self.learning_metrics) / len(self.learning_metrics) if self.learning_metrics else 0,
                "average_verification_score": sum(m.verification_score or 0 for m in self.learning_metrics) / len(self.learning_metrics) if self.learning_metrics else 0,
                "average_learning_delta": sum(m.learning_delta for m in self.learning_metrics) / len(self.learning_metrics) if self.learning_metrics else 0,
            }
        }
        
        with open(METRICS_FILE, "w") as f:
            json.dump(metrics_data, f, indent=2)
    
    def _write_improvement_report(self, start_time: datetime):
        """Write human-readable improvement report."""
        with open(REPORT_FILE, "w") as f:
            f.write("# IRA Learning Improvement Report\n\n")
            f.write(f"**Generated:** {start_time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            # Summary
            total = len(self.learning_metrics)
            learned = sum(1 for m in self.learning_metrics if m.learned)
            
            f.write("## Executive Summary\n\n")
            f.write(f"Prometheus tested IRA's ability to learn from feedback across {total} scenarios.\n\n")
            f.write(f"- **Learning Rate:** {learned}/{total} ({100*learned/total:.0f}%)\n")
            
            avg_initial = sum(m.initial_score for m in self.learning_metrics) / total if total else 0
            avg_final = sum(m.verification_score or m.initial_score for m in self.learning_metrics) / total if total else 0
            
            f.write(f"- **Average Initial Score:** {avg_initial:.2f}/5.0\n")
            f.write(f"- **Average Final Score:** {avg_final:.2f}/5.0\n")
            f.write(f"- **Overall Improvement:** {avg_final - avg_initial:+.2f}\n\n")
            
            # Detailed findings
            f.write("## Detailed Findings\n\n")
            
            # Scenarios where learning occurred
            learned_scenarios = [m for m in self.learning_metrics if m.learned]
            if learned_scenarios:
                f.write("### ✅ Successful Learning\n\n")
                for m in learned_scenarios:
                    f.write(f"- **{m.scenario_id}**: {m.initial_score} → {m.verification_score} (+{m.learning_delta:.2f})\n")
                f.write("\n")
            
            # Scenarios where learning did not occur
            not_learned = [m for m in self.learning_metrics if not m.learned and m.correction_sent]
            if not_learned:
                f.write("### ⚠️ Learning Needed\n\n")
                for m in not_learned:
                    f.write(f"- **{m.scenario_id}**: {m.initial_score} → {m.verification_score or 'N/A'}\n")
                f.write("\n")
            
            # Recommendations
            f.write("## Recommendations\n\n")
            
            critical_failures = [m for m in self.learning_metrics if m.initial_score < 3.0]
            if critical_failures:
                f.write("### High Priority\n\n")
                for m in critical_failures:
                    scenario = next((s for s in self.scenarios if s["id"] == m.scenario_id), {})
                    f.write(f"1. **{m.scenario_id}**: Review and strengthen rule enforcement.\n")
                    f.write(f"   - Critical rule: {scenario.get('critical_rule', 'N/A')}\n\n")
            
            f.write("### General Improvements\n\n")
            f.write("1. Enhance feedback processing pipeline to ensure corrections are stored persistently\n")
            f.write("2. Add more comprehensive testing for edge cases\n")
            f.write("3. Implement memory verification to confirm corrections are retrieved correctly\n")


async def main():
    parser = argparse.ArgumentParser(description="Prometheus - Email-based Adversarial Test Agent")
    parser.add_argument("--scenario", type=str, help="Run specific scenario by ID")
    parser.add_argument("--all", action="store_true", help="Run all scenarios")
    parser.add_argument("--dry-run", action="store_true", help="Test without sending emails")
    parser.add_argument("--list", action="store_true", help="List available scenarios")
    args = parser.parse_args()
    
    if args.list:
        with open(SCENARIOS_FILE, 'r') as f:
            scenarios = json.load(f)
        print("Available scenarios:")
        for s in scenarios:
            print(f"  - {s['id']}: {s['name']}")
        return
    
    prometheus = Prometheus(dry_run=args.dry_run)
    
    if args.scenario:
        await prometheus.run_single_scenario(args.scenario)
    elif args.all or args.dry_run:
        await prometheus.run_all_scenarios()
    else:
        parser.print_help()


if __name__ == "__main__":
    asyncio.run(main())
