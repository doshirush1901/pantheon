#!/usr/bin/env python3
"""
AMBIVO CRM CONNECTOR
====================

Imports leads, contacts, and conversation history from Rushabh's Ambivo CRM
into Ira's campaign system.

Two import methods:
1. CSV/JSON file export — drop files into data/imports/ambivo/
2. Gmail thread scan — find all emails to/from known contacts

The imported data enriches:
- European campaign state (new leads, updated contact info)
- Conversation history (for personalized drip emails)
- Lead intelligence (company details, deal stage, notes)
- Ira's memory (Mem0 + Qdrant for RAG)

Usage:
    # Import from CSV export
    python ambivo_connector.py --import-csv /path/to/ambivo_export.csv

    # Import from JSON export
    python ambivo_connector.py --import-json /path/to/ambivo_export.json

    # Scan Gmail for conversation history with known leads
    python ambivo_connector.py --scan-gmail

    # Full sync: import + scan + enrich
    python ambivo_connector.py --full-sync
"""

import csv
import json
import logging
import os
import re
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

logger = logging.getLogger("ira.ambivo_connector")

SKILL_DIR = Path(__file__).parent
SKILLS_DIR = SKILL_DIR.parent
AGENT_DIR = SKILLS_DIR.parent
PROJECT_ROOT = AGENT_DIR.parent.parent.parent

sys.path.insert(0, str(SKILL_DIR))
sys.path.insert(0, str(SKILLS_DIR / "brain"))

env_file = PROJECT_ROOT / ".env"
if env_file.exists():
    for line in env_file.read_text().splitlines():
        if line.strip() and not line.startswith('#') and '=' in line:
            key, _, value = line.partition('=')
            os.environ.setdefault(key.strip(), value.strip().strip('"'))

# Data files
AMBIVO_IMPORT_DIR = PROJECT_ROOT / "data" / "imports" / "ambivo"
AMBIVO_STATE_FILE = PROJECT_ROOT / "data" / "ambivo_sync_state.json"
CAMPAIGN_STATE_FILE = PROJECT_ROOT / "data" / "european_campaign_state.json"
CONVERSATIONS_FILE = PROJECT_ROOT / "data" / "european_lead_conversations.json"
LEADS_FILE = PROJECT_ROOT / "data" / "imports" / "european_leads_structured.json"

IRA_EMAIL = os.getenv("IRA_EMAIL", "ira@machinecraft.org")
RUSHABH_EMAIL = os.getenv("RUSHABH_EMAIL", "rushabh@machinecraft.org")

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


@dataclass
class AmbivoContact:
    """A contact imported from Ambivo."""
    email: str
    first_name: str = ""
    last_name: str = ""
    company: str = ""
    country: str = ""
    phone: str = ""
    title: str = ""
    industry: str = ""
    source: str = ""
    # Ambivo-specific fields
    deal_stage: str = ""  # "new", "contacted", "qualified", "proposal", "won", "lost"
    deal_value: float = 0.0
    deal_currency: str = "EUR"
    tags: List[str] = field(default_factory=list)
    notes: str = ""
    last_activity: str = ""
    created_at: str = ""
    # Conversation history from Ambivo
    conversations: List[Dict[str, str]] = field(default_factory=list)

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip() or self.email.split("@")[0]

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class ImportResult:
    """Result of an import operation."""
    source: str
    contacts_imported: int = 0
    contacts_updated: int = 0
    contacts_skipped: int = 0
    conversations_imported: int = 0
    leads_created: int = 0
    leads_enriched: int = 0
    errors: List[str] = field(default_factory=list)
    timestamp: str = ""

    def to_dict(self) -> Dict:
        return asdict(self)


class AmbivoConnector:
    """
    Connector for importing data from Ambivo CRM into Ira's systems.

    Supports CSV export, JSON export, Gmail scanning, and Zapier webhooks.
    """

    # Common CSV column name mappings (Ambivo export format)
    COLUMN_MAP = {
        "email": ["email", "email address", "e-mail", "contact email", "email_address"],
        "first_name": ["first name", "first_name", "firstname", "given name"],
        "last_name": ["last name", "last_name", "lastname", "surname", "family name"],
        "company": ["company", "company name", "organization", "company_name", "account"],
        "country": ["country", "country/region", "location", "country_code"],
        "phone": ["phone", "phone number", "telephone", "mobile", "phone_number"],
        "title": ["title", "job title", "position", "role", "job_title"],
        "industry": ["industry", "sector", "vertical"],
        "deal_stage": ["stage", "deal stage", "pipeline stage", "status", "lead status", "deal_stage"],
        "deal_value": ["value", "deal value", "amount", "revenue", "deal_value"],
        "tags": ["tags", "labels", "categories"],
        "notes": ["notes", "comments", "description", "remarks"],
        "source": ["source", "lead source", "origin", "channel"],
        "last_activity": ["last activity", "last_activity", "last contact", "updated at", "updated_at"],
        "created_at": ["created", "created at", "created_at", "date added", "date_added"],
    }

    def __init__(self):
        AMBIVO_IMPORT_DIR.mkdir(parents=True, exist_ok=True)
        self.sync_state = self._load_sync_state()

    def _load_sync_state(self) -> Dict:
        if AMBIVO_STATE_FILE.exists():
            try:
                return json.loads(AMBIVO_STATE_FILE.read_text())
            except Exception:
                pass
        return {
            "last_csv_import": None,
            "last_json_import": None,
            "last_gmail_scan": None,
            "total_contacts": 0,
            "known_emails": [],
        }

    def _save_sync_state(self):
        AMBIVO_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        AMBIVO_STATE_FILE.write_text(json.dumps(self.sync_state, indent=2))

    # =========================================================================
    # CSV IMPORT
    # =========================================================================

    def import_csv(self, csv_path: str) -> ImportResult:
        """
        Import contacts from an Ambivo CSV export.

        Handles various CSV formats by fuzzy-matching column names.
        """
        result = ImportResult(source=f"csv:{csv_path}", timestamp=datetime.now().isoformat())
        csv_path = Path(csv_path)

        if not csv_path.exists():
            result.errors.append(f"File not found: {csv_path}")
            return result

        logger.info(f"Importing contacts from CSV: {csv_path}")

        contacts = []
        encodings = ["utf-8", "utf-8-sig", "latin-1", "cp1252", "iso-8859-1"]

        for encoding in encodings:
            try:
                with open(csv_path, "r", encoding=encoding) as f:
                    reader = csv.DictReader(f)
                    col_mapping = self._map_columns(reader.fieldnames or [])
                    logger.info(f"Column mapping: {col_mapping}")

                    for row in reader:
                        contact = self._row_to_contact(row, col_mapping)
                        if contact and contact.email:
                            contacts.append(contact)

                break
            except UnicodeDecodeError:
                continue
            except Exception as e:
                result.errors.append(f"CSV parse error ({encoding}): {e}")
                continue

        if not contacts:
            result.errors.append("No valid contacts found in CSV")
            return result

        logger.info(f"Parsed {len(contacts)} contacts from CSV")

        # Process contacts
        result = self._process_contacts(contacts, result)

        # Save a copy of the import
        backup_path = AMBIVO_IMPORT_DIR / f"csv_import_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        backup_path.write_text(json.dumps([c.to_dict() for c in contacts], indent=2))

        self.sync_state["last_csv_import"] = datetime.now().isoformat()
        self._save_sync_state()

        return result

    def _map_columns(self, fieldnames: List[str]) -> Dict[str, str]:
        """Map CSV column names to our standard fields using fuzzy matching."""
        mapping = {}
        fieldnames_lower = {fn: fn.lower().strip() for fn in fieldnames}

        for our_field, possible_names in self.COLUMN_MAP.items():
            for fn, fn_lower in fieldnames_lower.items():
                if fn_lower in possible_names:
                    mapping[our_field] = fn
                    break

        return mapping

    def _row_to_contact(self, row: Dict, col_mapping: Dict) -> Optional[AmbivoContact]:
        """Convert a CSV row to an AmbivoContact."""
        def get(field_name: str) -> str:
            csv_col = col_mapping.get(field_name)
            if csv_col:
                return (row.get(csv_col) or "").strip()
            return ""

        email = get("email")
        if not email or "@" not in email:
            return None

        tags_raw = get("tags")
        tags = [t.strip() for t in tags_raw.split(",") if t.strip()] if tags_raw else []

        deal_value_str = get("deal_value")
        deal_value = 0.0
        if deal_value_str:
            try:
                deal_value = float(re.sub(r"[^\d.]", "", deal_value_str))
            except ValueError:
                pass

        return AmbivoContact(
            email=email.lower(),
            first_name=get("first_name"),
            last_name=get("last_name"),
            company=get("company"),
            country=get("country"),
            phone=get("phone"),
            title=get("title"),
            industry=get("industry"),
            deal_stage=get("deal_stage"),
            deal_value=deal_value,
            tags=tags,
            notes=get("notes"),
            source=get("source") or "ambivo_csv",
            last_activity=get("last_activity"),
            created_at=get("created_at"),
        )

    # =========================================================================
    # JSON IMPORT
    # =========================================================================

    def import_json(self, json_path: str) -> ImportResult:
        """Import contacts from an Ambivo JSON export."""
        result = ImportResult(source=f"json:{json_path}", timestamp=datetime.now().isoformat())
        json_path = Path(json_path)

        if not json_path.exists():
            result.errors.append(f"File not found: {json_path}")
            return result

        logger.info(f"Importing contacts from JSON: {json_path}")

        try:
            data = json.loads(json_path.read_text())
        except Exception as e:
            result.errors.append(f"JSON parse error: {e}")
            return result

        # Handle various JSON structures
        contacts_data = []
        if isinstance(data, list):
            contacts_data = data
        elif isinstance(data, dict):
            contacts_data = (
                data.get("contacts", [])
                or data.get("leads", [])
                or data.get("data", [])
                or data.get("results", [])
            )

        contacts = []
        for item in contacts_data:
            if not isinstance(item, dict):
                continue
            contact = AmbivoContact(
                email=(item.get("email") or item.get("email_address") or "").lower().strip(),
                first_name=item.get("first_name", item.get("firstName", "")),
                last_name=item.get("last_name", item.get("lastName", "")),
                company=item.get("company", item.get("organization", "")),
                country=item.get("country", item.get("location", "")),
                phone=item.get("phone", item.get("phone_number", "")),
                title=item.get("title", item.get("job_title", "")),
                industry=item.get("industry", item.get("sector", "")),
                deal_stage=item.get("deal_stage", item.get("stage", item.get("status", ""))),
                deal_value=float(item.get("deal_value", item.get("value", 0)) or 0),
                tags=item.get("tags", []),
                notes=item.get("notes", item.get("comments", "")),
                source=item.get("source", "ambivo_json"),
                last_activity=item.get("last_activity", item.get("updated_at", "")),
                created_at=item.get("created_at", item.get("created", "")),
                conversations=item.get("conversations", item.get("activities", [])),
            )
            if contact.email:
                contacts.append(contact)

        if not contacts:
            result.errors.append("No valid contacts found in JSON")
            return result

        logger.info(f"Parsed {len(contacts)} contacts from JSON")
        result = self._process_contacts(contacts, result)

        backup_path = AMBIVO_IMPORT_DIR / f"json_import_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        backup_path.write_text(json.dumps([c.to_dict() for c in contacts], indent=2))

        self.sync_state["last_json_import"] = datetime.now().isoformat()
        self._save_sync_state()

        return result

    # =========================================================================
    # GMAIL CONVERSATION SCAN
    # =========================================================================

    def scan_gmail_conversations(self, max_contacts: int = 50) -> ImportResult:
        """
        Scan Gmail for conversation history with known leads.

        Finds all email threads between Rushabh/Ira and lead contacts,
        extracts conversation summaries, and stores them for drip
        personalization.
        """
        result = ImportResult(source="gmail_scan", timestamp=datetime.now().isoformat())

        try:
            sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
            from email_openclaw_bridge import GmailClient, GMAIL_AVAILABLE
            if not GMAIL_AVAILABLE:
                result.errors.append("Gmail API not available")
                return result
            gmail = GmailClient()
        except Exception as e:
            result.errors.append(f"Gmail init failed: {e}")
            return result

        # Get known lead emails from campaign state + Ambivo imports
        known_emails = self._get_all_lead_emails()
        if not known_emails:
            result.errors.append("No lead emails found to scan for")
            return result

        logger.info(f"Scanning Gmail for conversations with {len(known_emails)} contacts")

        conversations = self._load_conversations()
        scanned = 0

        for email_addr, lead_info in list(known_emails.items())[:max_contacts]:
            try:
                threads = gmail.service.users().messages().list(
                    userId="me",
                    q=f"from:{email_addr} OR to:{email_addr}",
                    maxResults=20,
                ).execute()

                messages = threads.get("messages", [])
                if not messages:
                    continue

                thread_summaries = []
                for msg_info in messages[:10]:
                    try:
                        details = gmail._get_email_details(msg_info["id"])
                        if details:
                            sender = details.get("from", "")
                            is_lead = email_addr.lower() in sender.lower()
                            thread_summaries.append({
                                "type": "genuine_reply" if is_lead else "outbound",
                                "from": sender,
                                "subject": details.get("subject", ""),
                                "date": details.get("date", ""),
                                "preview": (details.get("body") or details.get("snippet", ""))[:200],
                            })
                    except Exception:
                        continue

                if thread_summaries:
                    company = lead_info.get("company", "")
                    lead_id = lead_info.get("lead_id", "")
                    inbound = [t for t in thread_summaries if t["type"] == "genuine_reply"]

                    conv_entry = {
                        "company": company,
                        "lead_id": lead_id,
                        "contact_email": email_addr,
                        "emails_sent": len(thread_summaries) - len(inbound),
                        "emails_received": len(inbound),
                        "genuine_replies": len(inbound),
                        "auto_replies": 0,
                        "first_contact": thread_summaries[-1].get("date", "") if thread_summaries else "",
                        "last_contact": thread_summaries[0].get("date", "") if thread_summaries else "",
                        "conversation_threads": thread_summaries[:10],
                        "source": "gmail_scan",
                    }

                    # Update or add to conversations
                    self._upsert_conversation(conversations, conv_entry, lead_id, company)
                    result.conversations_imported += 1
                    scanned += 1

            except Exception as e:
                logger.debug(f"Gmail scan error for {email_addr}: {e}")
                continue

        # Save updated conversations
        CONVERSATIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
        conversations["checked_at"] = datetime.now().isoformat()
        CONVERSATIONS_FILE.write_text(json.dumps(conversations, indent=2, ensure_ascii=False))

        self.sync_state["last_gmail_scan"] = datetime.now().isoformat()
        self._save_sync_state()

        logger.info(f"Gmail scan: {scanned} contacts scanned, {result.conversations_imported} conversations updated")
        return result

    def _load_conversations(self) -> Dict:
        if CONVERSATIONS_FILE.exists():
            try:
                return json.loads(CONVERSATIONS_FILE.read_text())
            except Exception:
                pass
        return {
            "checked_at": "",
            "genuine_conversations": [],
            "contacted_no_reply": [],
            "not_contacted": [],
        }

    def _upsert_conversation(self, conversations: Dict, entry: Dict, lead_id: str, company: str):
        """Update or insert a conversation entry."""
        genuine = conversations.get("genuine_conversations", [])

        for i, existing in enumerate(genuine):
            if (existing.get("lead_id") == lead_id and lead_id) or \
               (existing.get("company", "").lower() == company.lower() and company):
                genuine[i] = entry
                return

        if entry.get("genuine_replies", 0) > 0:
            genuine.append(entry)
        else:
            contacted = conversations.get("contacted_no_reply", [])
            contacted.append(entry)

    def _get_all_lead_emails(self) -> Dict[str, Dict]:
        """Get all known lead emails from campaign state and imports."""
        emails = {}

        # From campaign state
        if CAMPAIGN_STATE_FILE.exists():
            try:
                state = json.loads(CAMPAIGN_STATE_FILE.read_text())
                for lead_id, lead_data in state.get("leads", {}).items():
                    company = lead_data.get("company", "")
                    # Try to find email from leads file
                    email = self._find_email_for_company(company)
                    if email:
                        emails[email] = {"lead_id": lead_id, "company": company}
            except Exception:
                pass

        # From Ambivo imports
        for import_file in sorted(AMBIVO_IMPORT_DIR.glob("*.json")):
            try:
                contacts = json.loads(import_file.read_text())
                for contact in contacts:
                    email = contact.get("email", "")
                    if email and "@" in email:
                        emails[email.lower()] = {
                            "lead_id": contact.get("lead_id", ""),
                            "company": contact.get("company", ""),
                        }
            except Exception:
                continue

        # From existing contacts CSV
        contacts_csv = PROJECT_ROOT / "data" / "imports" / "European & US Contacts for Single Station Nov 203.csv"
        if contacts_csv.exists():
            for encoding in ["utf-8", "latin-1", "cp1252"]:
                try:
                    with open(contacts_csv, "r", encoding=encoding) as f:
                        reader = csv.DictReader(f)
                        for row in reader:
                            email = (row.get("Email Address") or row.get("Email") or "").strip().lower()
                            company = (row.get("Company Name") or row.get("Company") or "").strip()
                            if email and "@" in email:
                                emails[email] = {"lead_id": "", "company": company}
                    break
                except (UnicodeDecodeError, Exception):
                    continue

        return emails

    def _find_email_for_company(self, company: str) -> Optional[str]:
        """Try to find an email address for a company from various sources."""
        if not company:
            return None

        company_lower = company.lower()

        # Check contacts CSV
        contacts_csv = PROJECT_ROOT / "data" / "imports" / "European & US Contacts for Single Station Nov 203.csv"
        if contacts_csv.exists():
            for encoding in ["utf-8", "latin-1", "cp1252"]:
                try:
                    with open(contacts_csv, "r", encoding=encoding) as f:
                        reader = csv.DictReader(f)
                        for row in reader:
                            csv_company = (row.get("Company Name") or "").strip().lower()
                            if csv_company and (csv_company in company_lower or company_lower in csv_company):
                                email = (row.get("Email Address") or "").strip()
                                if email:
                                    return email.lower()
                    break
                except (UnicodeDecodeError, Exception):
                    continue

        # Check Ambivo imports
        for import_file in sorted(AMBIVO_IMPORT_DIR.glob("*.json")):
            try:
                contacts = json.loads(import_file.read_text())
                for contact in contacts:
                    c_company = (contact.get("company") or "").lower()
                    if c_company and (c_company in company_lower or company_lower in c_company):
                        email = contact.get("email", "")
                        if email:
                            return email.lower()
            except Exception:
                continue

        return None

    # =========================================================================
    # PROCESS & ENRICH
    # =========================================================================

    def _process_contacts(self, contacts: List[AmbivoContact], result: ImportResult) -> ImportResult:
        """Process imported contacts: create leads, enrich campaign, store in memory."""

        # Load existing campaign state
        campaign_state = {}
        if CAMPAIGN_STATE_FILE.exists():
            try:
                campaign_state = json.loads(CAMPAIGN_STATE_FILE.read_text())
            except Exception:
                pass

        existing_leads = campaign_state.get("leads", {})
        existing_companies = {
            v.get("company", "").lower(): k
            for k, v in existing_leads.items()
        }

        # Load existing leads file
        leads_data = {"leads": [], "metadata": {}}
        if LEADS_FILE.exists():
            try:
                leads_data = json.loads(LEADS_FILE.read_text())
            except Exception:
                pass

        existing_lead_ids = {l.get("id") for l in leads_data.get("leads", [])}
        next_id = max(
            (int(lid.split("-")[-1]) for lid in existing_lead_ids if lid.startswith("eu-")),
            default=33,
        ) + 1

        new_emails = []

        for contact in contacts:
            company_lower = contact.company.lower() if contact.company else ""

            # Check if this company already exists in campaign
            if company_lower and company_lower in existing_companies:
                # Enrich existing lead
                lead_id = existing_companies[company_lower]
                self._enrich_existing_lead(existing_leads[lead_id], contact)
                result.contacts_updated += 1
                result.leads_enriched += 1
            else:
                # Create new lead
                lead_id = f"eu-{next_id:03d}"
                next_id += 1

                priority = self._determine_priority(contact)
                industries = [contact.industry] if contact.industry else ["general"]

                # Add to campaign state
                existing_leads[lead_id] = {
                    "lead_id": lead_id,
                    "company": contact.company or f"Contact: {contact.full_name}",
                    "country": contact.country or "Unknown",
                    "priority": priority,
                    "current_stage": 0,
                    "last_email_sent": None,
                    "emails_sent": 0,
                    "opened": 0,
                    "replied": False,
                    "unsubscribed": False,
                    "notes": contact.notes,
                    "reply_quality": "",
                    "reply_at": None,
                    "thread_id": "",
                    "last_batch_id": "",
                }

                # Add to leads file
                leads_data["leads"].append({
                    "id": lead_id,
                    "company": contact.company or f"Contact: {contact.full_name}",
                    "country": contact.country or "Unknown",
                    "priority": priority,
                    "industries": industries,
                    "email": contact.email,
                    "contact_name": contact.full_name,
                    "contact_title": contact.title,
                    "phone": contact.phone,
                    "deal_stage": contact.deal_stage,
                    "deal_value": contact.deal_value,
                    "tags": contact.tags,
                    "source": contact.source,
                    "imported_at": datetime.now().isoformat(),
                })

                result.contacts_imported += 1
                result.leads_created += 1
                new_emails.append(contact.email)

            # Store conversations if present
            if contact.conversations:
                result.conversations_imported += len(contact.conversations)

        # Save updated campaign state
        campaign_state["leads"] = existing_leads
        campaign_state["updated_at"] = datetime.now().isoformat()
        CAMPAIGN_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        CAMPAIGN_STATE_FILE.write_text(json.dumps(campaign_state, indent=2))

        # Save updated leads file
        leads_data["metadata"]["last_ambivo_import"] = datetime.now().isoformat()
        leads_data["metadata"]["total_leads"] = len(leads_data["leads"])
        LEADS_FILE.parent.mkdir(parents=True, exist_ok=True)
        LEADS_FILE.write_text(json.dumps(leads_data, indent=2, ensure_ascii=False))

        # Update sync state
        self.sync_state["total_contacts"] = len(existing_leads)
        known = set(self.sync_state.get("known_emails", []))
        known.update(new_emails)
        self.sync_state["known_emails"] = list(known)[:500]
        self._save_sync_state()

        # Store in Ira's memory for RAG
        self._store_in_memory(contacts)

        logger.info(
            f"Processed: {result.contacts_imported} new, "
            f"{result.contacts_updated} updated, "
            f"{result.leads_created} leads created"
        )

        return result

    def _enrich_existing_lead(self, lead_data: Dict, contact: AmbivoContact):
        """Enrich an existing lead with new Ambivo data."""
        if contact.notes and not lead_data.get("notes"):
            lead_data["notes"] = contact.notes
        if contact.deal_stage:
            lead_data["notes"] = (
                (lead_data.get("notes") or "") +
                f"\n[Ambivo] Deal stage: {contact.deal_stage}"
            ).strip()

    def _determine_priority(self, contact: AmbivoContact) -> str:
        """Determine lead priority based on Ambivo data."""
        stage = (contact.deal_stage or "").lower()

        if stage in ("qualified", "proposal"):
            return "critical"
        if stage in ("contacted", "negotiation"):
            return "high"
        if contact.deal_value > 50000:
            return "high"
        if contact.deal_value > 10000:
            return "medium"
        if any(t in (contact.tags or []) for t in ["hot", "priority", "urgent"]):
            return "high"

        return "medium"

    def _store_in_memory(self, contacts: List[AmbivoContact]):
        """Store imported contacts in Ira's Mem0 memory for RAG access."""
        try:
            from openclaw.agents.ira.src.memory.mem0_memory import get_mem0_service
            mem0 = get_mem0_service()

            for contact in contacts[:50]:
                if not contact.company:
                    continue

                memory_text = (
                    f"Contact: {contact.full_name} at {contact.company} ({contact.country}). "
                    f"Email: {contact.email}. "
                )
                if contact.title:
                    memory_text += f"Title: {contact.title}. "
                if contact.industry:
                    memory_text += f"Industry: {contact.industry}. "
                if contact.deal_stage:
                    memory_text += f"Deal stage: {contact.deal_stage}. "
                if contact.deal_value:
                    memory_text += f"Deal value: {contact.deal_currency} {contact.deal_value:,.0f}. "
                if contact.notes:
                    memory_text += f"Notes: {contact.notes[:200]}. "

                memory_text += "Source: Ambivo CRM import."

                try:
                    mem0.add_memory(
                        text=memory_text,
                        user_id="machinecraft_customers",
                        metadata={
                            "source": "ambivo_import",
                            "company": contact.company,
                            "email": contact.email,
                            "timestamp": datetime.now().isoformat(),
                        },
                    )
                except Exception:
                    pass

            logger.info(f"Stored {min(len(contacts), 50)} contacts in Mem0")

        except ImportError:
            logger.debug("Mem0 not available for contact storage")
        except Exception as e:
            logger.warning(f"Mem0 storage error: {e}")

    # =========================================================================
    # FULL SYNC
    # =========================================================================

    def full_sync(self) -> Dict[str, Any]:
        """
        Run a full sync: import any new files + scan Gmail + enrich.

        This is the recommended daily sync operation.
        """
        results = {"timestamp": datetime.now().isoformat(), "operations": []}

        # 1. Import any new CSV/JSON files in the import directory
        for f in sorted(AMBIVO_IMPORT_DIR.glob("*.csv")):
            if f.stem.startswith("csv_import_"):
                continue
            logger.info(f"Found new CSV to import: {f}")
            r = self.import_csv(str(f))
            results["operations"].append({"type": "csv_import", "file": f.name, **r.to_dict()})

        for f in sorted(AMBIVO_IMPORT_DIR.glob("*.json")):
            if f.stem.startswith(("csv_import_", "json_import_")):
                continue
            logger.info(f"Found new JSON to import: {f}")
            r = self.import_json(str(f))
            results["operations"].append({"type": "json_import", "file": f.name, **r.to_dict()})

        # 2. Scan Gmail for conversation history
        logger.info("Scanning Gmail for conversation history...")
        r = self.scan_gmail_conversations()
        results["operations"].append({"type": "gmail_scan", **r.to_dict()})

        # Summary
        total_imported = sum(
            op.get("contacts_imported", 0) for op in results["operations"]
        )
        total_conversations = sum(
            op.get("conversations_imported", 0) for op in results["operations"]
        )
        results["summary"] = {
            "contacts_imported": total_imported,
            "conversations_imported": total_conversations,
            "operations_run": len(results["operations"]),
        }

        logger.info(
            f"Full sync complete: {total_imported} contacts, "
            f"{total_conversations} conversations"
        )

        return results


if __name__ == "__main__":
    import argparse

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")

    parser = argparse.ArgumentParser(description="Ambivo CRM Connector")
    parser.add_argument("--import-csv", type=str, help="Import from CSV file")
    parser.add_argument("--import-json", type=str, help="Import from JSON file")
    parser.add_argument("--scan-gmail", action="store_true", help="Scan Gmail for conversations")
    parser.add_argument("--full-sync", action="store_true", help="Full sync (import + scan + enrich)")
    parser.add_argument("--status", action="store_true", help="Show sync status")
    args = parser.parse_args()

    connector = AmbivoConnector()

    if args.import_csv:
        result = connector.import_csv(args.import_csv)
        print(json.dumps(result.to_dict(), indent=2))

    elif args.import_json:
        result = connector.import_json(args.import_json)
        print(json.dumps(result.to_dict(), indent=2))

    elif args.scan_gmail:
        result = connector.scan_gmail_conversations()
        print(json.dumps(result.to_dict(), indent=2))

    elif args.full_sync:
        result = connector.full_sync()
        print(json.dumps(result, indent=2))

    elif args.status:
        print(json.dumps(connector.sync_state, indent=2))

    else:
        parser.print_help()
        print("\nExamples:")
        print("  python ambivo_connector.py --import-csv ~/Downloads/ambivo_contacts.csv")
        print("  python ambivo_connector.py --import-json ~/Downloads/ambivo_leads.json")
        print("  python ambivo_connector.py --scan-gmail")
        print("  python ambivo_connector.py --full-sync")
