#!/usr/bin/env python3
"""
BOOTSTRAP IRA CRM
=================

One-time script that loads all existing lead/contact data into Ira's
new unified CRM database (crm/ira_crm.db).

Sources:
1. European contacts CSV (emails, names, companies, meeting/quote history)
2. European campaign state JSON (lead priorities, stages)
3. European lead conversations JSON (email thread history)

Run once:
    python scripts/bootstrap_crm.py

Idempotent — safe to run multiple times (upserts, not duplicates).
"""

import csv
import json
import logging
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "openclaw/agents/ira/src/crm"))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("bootstrap_crm")

CONTACTS_CSV = PROJECT_ROOT / "data" / "imports" / "European & US Contacts for Single Station Nov 203.csv"
CAMPAIGN_STATE = PROJECT_ROOT / "data" / "european_campaign_state.json"
CONVERSATIONS = PROJECT_ROOT / "data" / "european_lead_conversations.json"


def main():
    from ira_crm import get_crm

    crm = get_crm()
    logger.info(f"CRM database: {crm.db_path}")

    contacts_loaded = 0
    leads_loaded = 0
    conversations_loaded = 0

    # =========================================================================
    # 1. CONTACTS CSV
    # =========================================================================
    if CONTACTS_CSV.exists():
        logger.info(f"\n[1/3] Loading contacts from CSV: {CONTACTS_CSV.name}")

        for encoding in ["utf-8", "utf-8-sig", "latin-1", "cp1252"]:
            try:
                with open(CONTACTS_CSV, "r", encoding=encoding) as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        email = (row.get("Email Address") or "").strip().lower()
                        if not email or "@" not in email:
                            continue

                        first_name = (row.get("First Name") or "").strip()
                        last_name = (row.get("Last Name") or "").strip()
                        name = f"{first_name} {last_name}".strip()
                        company = (row.get("Company Name") or "").strip()
                        country = (row.get("Address") or "").strip()
                        meeting = (row.get("Physical / Web Meeting") or "").strip()
                        quotes = (row.get("Quotes") or "").strip()
                        comments = (row.get("Comments") or "").strip()

                        notes_parts = []
                        if meeting:
                            notes_parts.append(f"Meeting: {meeting}")
                        if quotes:
                            notes_parts.append(f"Quote: {quotes}")
                        if comments:
                            notes_parts.append(f"Notes: {comments}")

                        crm.upsert_contact(
                            email,
                            name=name,
                            first_name=first_name,
                            last_name=last_name,
                            company=company,
                            country=country,
                            notes="; ".join(notes_parts),
                            source="contacts_csv",
                        )
                        contacts_loaded += 1
                break
            except UnicodeDecodeError:
                continue

        logger.info(f"  Loaded {contacts_loaded} contacts")
    else:
        logger.warning(f"  Contacts CSV not found: {CONTACTS_CSV}")

    # =========================================================================
    # 2. CAMPAIGN STATE (leads with priorities)
    # =========================================================================
    if CAMPAIGN_STATE.exists():
        logger.info(f"\n[2/3] Loading leads from campaign state: {CAMPAIGN_STATE.name}")

        state = json.loads(CAMPAIGN_STATE.read_text())
        leads_data = state.get("leads", {})

        # We need to match campaign leads (by company) to contacts (by email)
        # Build a company->email lookup from contacts we just loaded
        company_to_email = {}
        for contact in crm.get_all_contacts():
            if contact.company:
                company_to_email[contact.company.lower()] = contact.email

        for lead_id, lead_info in leads_data.items():
            company = lead_info.get("company", "")
            country = lead_info.get("country", "")
            priority = lead_info.get("priority", "medium")

            # Find email for this company
            email = company_to_email.get(company.lower())

            if not email:
                # Try partial match
                for c_lower, c_email in company_to_email.items():
                    if c_lower in company.lower() or company.lower() in c_lower:
                        email = c_email
                        break

            if not email:
                # No email found — create a placeholder contact
                # Use company name as a slug for the email placeholder
                slug = company.lower().replace(" ", "_").replace("&", "and")[:30]
                email = f"unknown_{slug}@placeholder.local"
                crm.upsert_contact(email, company=company, country=country, source="campaign_state")

            crm.upsert_lead(
                email,
                company=company,
                country=country,
                priority=priority,
                drip_stage=lead_info.get("current_stage", 0),
                emails_sent=lead_info.get("emails_sent", 0),
                notes=lead_info.get("notes", ""),
            )
            leads_loaded += 1

        logger.info(f"  Loaded {leads_loaded} leads")
    else:
        logger.warning(f"  Campaign state not found: {CAMPAIGN_STATE}")

    # =========================================================================
    # 3. CONVERSATION HISTORY
    # =========================================================================
    if CONVERSATIONS.exists():
        logger.info(f"\n[3/3] Loading conversations: {CONVERSATIONS.name}")

        convos = json.loads(CONVERSATIONS.read_text())

        for category in ["genuine_conversations", "contacted_no_reply", "not_contacted"]:
            for entry in convos.get(category, []):
                company = entry.get("company", "")
                contact_email = entry.get("contact_email", "")

                # Find the email for this company
                email = contact_email
                if not email or "@" not in email:
                    email = company_to_email.get(company.lower()) if 'company_to_email' in dir() else None

                if not email:
                    for contact in crm.get_all_contacts():
                        if contact.company and contact.company.lower() == company.lower():
                            email = contact.email
                            break

                if not email:
                    continue

                # Import conversation threads
                for thread in entry.get("conversation_threads", []):
                    direction = "inbound" if thread.get("type") == "genuine_reply" else "outbound"
                    crm.add_conversation(
                        email,
                        direction=direction,
                        subject=thread.get("subject", ""),
                        preview=thread.get("preview", "")[:500],
                        date=thread.get("date", ""),
                        source="historical_import",
                    )
                    conversations_loaded += 1

        logger.info(f"  Loaded {conversations_loaded} conversation entries")
    else:
        logger.warning(f"  Conversations file not found: {CONVERSATIONS}")

    # =========================================================================
    # SUMMARY
    # =========================================================================
    stats = crm.get_pipeline_stats()

    logger.info("\n" + "=" * 50)
    logger.info("BOOTSTRAP COMPLETE")
    logger.info("=" * 50)
    logger.info(f"  Contacts: {contacts_loaded}")
    logger.info(f"  Leads: {leads_loaded}")
    logger.info(f"  Conversations: {conversations_loaded}")
    logger.info(f"\n  Pipeline: {json.dumps(stats, indent=4)}")
    logger.info(f"\n  Database: {crm.db_path}")
    logger.info(f"  Size: {crm.db_path.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    main()
