"""
Google Cloud API Tools for Ira
==============================

Provides access to Google Sheets, Drive, Calendar, Contacts, Document AI, and DLP.
Used by the agentic pipeline (tool_orchestrator) via ira_skills_tools.py.

Auth:
  - Sheets, Drive, Calendar, Contacts: OAuth via token.json (shared with Gmail)
  - Document AI, DLP: Service account via service_account.json
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("ira.google_tools")

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent.parent
CREDENTIALS_FILE = PROJECT_ROOT / "credentials.json"
TOKEN_FILE = PROJECT_ROOT / "token.json"
TOKEN_RUSHABH_FILE = PROJECT_ROOT / "token_rushabh.json"

SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/contacts.readonly",
]


def _get_oauth_creds():
    """Get OAuth credentials, refreshing if needed.

    Loads the token without enforcing scopes so it works regardless of
    which scopes the token was originally granted (gmail-only, full suite, etc.).
    The full SCOPES list is only used when creating a brand-new token via the
    interactive OAuth flow.
    """
    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        from google_auth_oauthlib.flow import InstalledAppFlow

        creds = None
        if TOKEN_FILE.exists():
            creds = Credentials.from_authorized_user_file(str(TOKEN_FILE))

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
                TOKEN_FILE.write_text(creds.to_json())
            else:
                if not CREDENTIALS_FILE.exists():
                    logger.error("credentials.json not found")
                    return None
                flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE), SCOPES)
                creds = flow.run_local_server(port=0)
                TOKEN_FILE.write_text(creds.to_json())

        return creds
    except Exception as e:
        logger.error(f"OAuth auth failed: {e}")
        return None


def _get_service_account_creds():
    """Get service account credentials for Document AI and DLP."""
    sa_path = os.environ.get("GOOGLE_SERVICE_ACCOUNT_PATH", "service_account.json")
    sa_file = PROJECT_ROOT / sa_path if not Path(sa_path).is_absolute() else Path(sa_path)

    if not sa_file.exists():
        logger.debug("Service account file not found -- Document AI and DLP unavailable")
        return None

    try:
        from google.oauth2 import service_account
        return service_account.Credentials.from_service_account_file(str(sa_file))
    except Exception as e:
        logger.error(f"Service account auth failed: {e}")
        return None


# =============================================================================
# GOOGLE SHEETS
# =============================================================================

def sheets_read(spreadsheet_id: str, range_name: str = "Sheet1") -> str:
    """Read data from a Google Sheet.

    Args:
        spreadsheet_id: The spreadsheet ID (from the URL)
        range_name: Sheet and range, e.g. "Sheet1!A1:Z100"

    Returns:
        Formatted text of the sheet data, or error message.
    """
    creds = _get_oauth_creds()
    if not creds:
        return "(Google Sheets auth not available. Delete token.json and re-authenticate.)"

    try:
        from googleapiclient.discovery import build
        service = build("sheets", "v4", credentials=creds)
        result = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=range_name,
        ).execute()

        values = result.get("values", [])
        if not values:
            return f"(Sheet is empty: {spreadsheet_id} range {range_name})"

        headers = values[0] if values else []
        lines = []
        lines.append(" | ".join(headers))
        lines.append("-" * 40)
        for row in values[1:50]:
            padded = row + [""] * (len(headers) - len(row))
            lines.append(" | ".join(str(c) for c in padded))

        return f"Google Sheet data ({len(values)-1} rows):\n" + "\n".join(lines)
    except Exception as e:
        logger.error(f"Sheets read error: {e}")
        return f"(Sheets error: {e})"


# =============================================================================
# GOOGLE DRIVE
# =============================================================================

def drive_list(query: str = "", max_results: int = 10) -> str:
    """Search for files in Google Drive.

    Args:
        query: Search query (file name, content, type)
        max_results: Max files to return

    Returns:
        Formatted list of matching files.
    """
    creds = _get_oauth_creds()
    if not creds:
        return "(Google Drive auth not available.)"

    try:
        from googleapiclient.discovery import build
        service = build("drive", "v3", credentials=creds)

        safe_query = query.replace("\\", "\\\\").replace("'", "\\'") if query else ""
        q = f"name contains '{safe_query}'" if safe_query else ""
        results = service.files().list(
            q=q,
            pageSize=max_results,
            fields="files(id, name, mimeType, modifiedTime, size)",
            orderBy="modifiedTime desc",
        ).execute()

        files = results.get("files", [])
        if not files:
            return f"(No files found for '{query}')"

        lines = [f"Found {len(files)} files:"]
        for f in files:
            size = f.get("size", "?")
            modified = f.get("modifiedTime", "?")[:10]
            lines.append(f"  - {f['name']} (id:{f['id'][:12]}..., modified:{modified}, type:{f.get('mimeType', '?')})")

        return "\n".join(lines)
    except Exception as e:
        logger.error(f"Drive list error: {e}")
        return f"(Drive error: {e})"


def drive_read(file_id: str) -> str:
    """Read content of a Google Drive file (text, docs, sheets export).

    Args:
        file_id: The Drive file ID

    Returns:
        File content as text.
    """
    creds = _get_oauth_creds()
    if not creds:
        return "(Google Drive auth not available.)"

    try:
        from googleapiclient.discovery import build
        service = build("drive", "v3", credentials=creds)

        meta = service.files().get(fileId=file_id, fields="name,mimeType").execute()
        mime = meta.get("mimeType", "")

        if "spreadsheet" in mime:
            content = service.files().export(fileId=file_id, mimeType="text/csv").execute()
            return f"[{meta['name']}]\n{content.decode('utf-8', errors='ignore')[:5000]}"
        elif "document" in mime:
            content = service.files().export(fileId=file_id, mimeType="text/plain").execute()
            return f"[{meta['name']}]\n{content.decode('utf-8', errors='ignore')[:5000]}"
        elif "presentation" in mime:
            content = service.files().export(fileId=file_id, mimeType="text/plain").execute()
            return f"[{meta['name']}]\n{content.decode('utf-8', errors='ignore')[:5000]}"
        else:
            content = service.files().get_media(fileId=file_id).execute()
            if isinstance(content, bytes):
                return f"[{meta['name']}]\n{content.decode('utf-8', errors='ignore')[:5000]}"
            return f"[{meta['name']}] (binary file, cannot read as text)"
    except Exception as e:
        logger.error(f"Drive read error: {e}")
        return f"(Drive read error: {e})"


# =============================================================================
# GOOGLE CALENDAR
# =============================================================================

def calendar_upcoming(days: int = 7) -> str:
    """Get upcoming calendar events.

    Args:
        days: Number of days to look ahead

    Returns:
        Formatted list of upcoming events.
    """
    creds = _get_oauth_creds()
    if not creds:
        return "(Google Calendar auth not available.)"

    try:
        from googleapiclient.discovery import build
        from datetime import datetime, timedelta, timezone

        service = build("calendar", "v3", credentials=creds)
        now = datetime.now(timezone.utc).isoformat()
        end = (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()

        events_result = service.events().list(
            calendarId="primary",
            timeMin=now,
            timeMax=end,
            maxResults=20,
            singleEvents=True,
            orderBy="startTime",
        ).execute()

        events = events_result.get("items", [])
        if not events:
            return f"No events in the next {days} days."

        lines = [f"Upcoming events ({len(events)}):"]
        for event in events:
            start = event["start"].get("dateTime", event["start"].get("date", ""))
            summary = event.get("summary", "(no title)")
            attendees = [a.get("email", "") for a in event.get("attendees", [])]
            att_str = f" with {', '.join(attendees[:3])}" if attendees else ""
            lines.append(f"  - {start[:16]} {summary}{att_str}")

        return "\n".join(lines)
    except Exception as e:
        logger.error(f"Calendar error: {e}")
        return f"(Calendar error: {e})"


# =============================================================================
# GOOGLE CONTACTS (People API)
# =============================================================================

def contacts_search(query: str) -> str:
    """Search Google Contacts for a person or company.

    Args:
        query: Name, company, or email to search for

    Returns:
        Formatted contact information.
    """
    creds = _get_oauth_creds()
    if not creds:
        return "(Google Contacts auth not available.)"

    try:
        from googleapiclient.discovery import build
        service = build("people", "v1", credentials=creds)

        results = service.people().searchContacts(
            query=query,
            readMask="names,emailAddresses,phoneNumbers,organizations",
            pageSize=10,
        ).execute()

        contacts = results.get("results", [])
        if not contacts:
            return f"(No contacts found for '{query}')"

        lines = [f"Found {len(contacts)} contacts:"]
        for c in contacts:
            person = c.get("person", {})
            names = person.get("names", [{}])
            name = names[0].get("displayName", "Unknown") if names else "Unknown"
            emails = [e.get("value", "") for e in person.get("emailAddresses", [])]
            phones = [p.get("value", "") for p in person.get("phoneNumbers", [])]
            orgs = [o.get("name", "") for o in person.get("organizations", [])]

            parts = [name]
            if orgs:
                parts.append(f"({orgs[0]})")
            if emails:
                parts.append(f"email:{emails[0]}")
            if phones:
                parts.append(f"phone:{phones[0]}")
            lines.append(f"  - {' '.join(parts)}")

        return "\n".join(lines)
    except Exception as e:
        logger.error(f"Contacts search error: {e}")
        return f"(Contacts error: {e})"


# =============================================================================
# GMAIL (Read / Search / Thread)
# =============================================================================

def _get_gmail_creds(account: str = "rushabh"):
    """Get Gmail OAuth credentials for a specific account.

    Prefers token_rushabh.json for Rushabh's mailbox (where sales data lives).
    Falls back to the default token.json (Ira's mailbox).
    """
    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request

        token_map = {
            "rushabh": TOKEN_RUSHABH_FILE,
            "ira": TOKEN_FILE,
        }
        token_path = token_map.get(account, TOKEN_RUSHABH_FILE)

        if not token_path.exists():
            logger.warning(f"Token file {token_path.name} not found, falling back to token.json")
            token_path = TOKEN_FILE

        if not token_path.exists():
            logger.error("No Gmail token file found")
            return None

        creds = Credentials.from_authorized_user_file(str(token_path))

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
                token_path.write_text(creds.to_json())
            else:
                logger.error(f"Token {token_path.name} expired and cannot refresh. Re-run setup_gmail.py.")
                return None

        return creds
    except Exception as e:
        logger.error(f"Gmail auth failed ({account}): {e}")
        return None


def _get_gmail_service(account: str = "rushabh"):
    """Build a Gmail API service.

    Args:
        account: 'rushabh' for Rushabh's mailbox (default), 'ira' for Ira's.
    """
    creds = _get_gmail_creds(account)
    if not creds:
        return None
    try:
        from googleapiclient.discovery import build
        return build("gmail", "v1", credentials=creds)
    except Exception as e:
        logger.error(f"Gmail service build error: {e}")
        return None


def _extract_email_body(payload: Dict) -> str:
    """Extract plain-text body from a Gmail message payload."""
    import base64

    if "body" in payload and payload["body"].get("data"):
        return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="ignore")

    for part in payload.get("parts", []):
        if part["mimeType"] == "text/plain" and part["body"].get("data"):
            return base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="ignore")
        if "parts" in part:
            result = _extract_email_body(part)
            if result:
                return result
    return ""


def gmail_read_inbox(max_results: int = 10, unread_only: bool = True) -> str:
    """Fetch recent emails from Rushabh's Gmail inbox.

    Args:
        max_results: Number of emails to return (max 20).
        unread_only: If True, only return unread messages.

    Returns:
        Formatted summary of inbox messages.
    """
    service = _get_gmail_service()
    if not service:
        return "(Gmail not available. Check OAuth token.)"

    try:
        q = "is:unread" if unread_only else ""
        max_results = min(max_results, 20)

        results = service.users().messages().list(
            userId="me", q=q, maxResults=max_results,
        ).execute()

        messages = results.get("messages", [])
        if not messages:
            return "Inbox is clean — no unread emails." if unread_only else "No recent emails found."

        lines = [f"{'Unread' if unread_only else 'Recent'} emails ({len(messages)}):"]
        lines.append("")

        for msg_ref in messages:
            try:
                msg = service.users().messages().get(
                    userId="me", id=msg_ref["id"], format="metadata",
                    metadataHeaders=["From", "Subject", "Date"],
                ).execute()
                headers = {h["name"].lower(): h["value"] for h in msg.get("payload", {}).get("headers", [])}
                snippet = msg.get("snippet", "")[:120]
                labels = msg.get("labelIds", [])
                starred = " *" if "STARRED" in labels else ""

                lines.append(
                    f"  From: {headers.get('from', '?')}\n"
                    f"  Subject: {headers.get('subject', '(no subject)')}{starred}\n"
                    f"  Date: {headers.get('date', '?')}\n"
                    f"  Preview: {snippet}\n"
                    f"  [id:{msg_ref['id']}]\n"
                )
            except Exception as e:
                logger.debug(f"Skipping message {msg_ref['id']}: {e}")

        return "\n".join(lines)
    except Exception as e:
        logger.error(f"Gmail read inbox error: {e}")
        return f"(Gmail inbox error: {e})"


def gmail_search(query: str, max_results: int = 10) -> str:
    """Search Gmail using the same syntax as the Gmail search bar.

    Args:
        query: Gmail search query (e.g. "from:john subject:invoice", "has:attachment after:2026/01/01").
        max_results: Max messages to return (max 20).

    Returns:
        Formatted search results with sender, subject, date, and preview.
    """
    service = _get_gmail_service()
    if not service:
        return "(Gmail not available. Check OAuth token.)"

    try:
        max_results = min(max_results, 20)
        results = service.users().messages().list(
            userId="me", q=query, maxResults=max_results,
        ).execute()

        messages = results.get("messages", [])
        if not messages:
            return f"No emails found for: {query}"

        total_estimate = results.get("resultSizeEstimate", len(messages))
        lines = [f"Search results for '{query}' ({len(messages)} shown, ~{total_estimate} total):"]
        lines.append("")

        for msg_ref in messages:
            try:
                msg = service.users().messages().get(
                    userId="me", id=msg_ref["id"], format="metadata",
                    metadataHeaders=["From", "To", "Subject", "Date"],
                ).execute()
                headers = {h["name"].lower(): h["value"] for h in msg.get("payload", {}).get("headers", [])}
                snippet = msg.get("snippet", "")[:150]

                thread_id = msg.get("threadId", "")
                lines.append(
                    f"  From: {headers.get('from', '?')}\n"
                    f"  To: {headers.get('to', '?')}\n"
                    f"  Subject: {headers.get('subject', '(no subject)')}\n"
                    f"  Date: {headers.get('date', '?')}\n"
                    f"  Preview: {snippet}\n"
                    f"  [id:{msg_ref['id']}] [thread:{thread_id}]\n"
                )
            except Exception as e:
                logger.debug(f"Skipping message {msg_ref['id']}: {e}")

        return "\n".join(lines)
    except Exception as e:
        logger.error(f"Gmail search error: {e}")
        return f"(Gmail search error: {e})"


def gmail_get_attachments(message_id: str, download_dir: str = "") -> List[Dict[str, str]]:
    """Download attachments from a Gmail message.

    Args:
        message_id: The Gmail message ID.
        download_dir: Directory to save files. Defaults to data/delphi/attachments/.

    Returns:
        List of dicts with 'filename', 'path', 'mime_type', 'size_bytes'.
    """
    import base64

    service = _get_gmail_service()
    if not service:
        return []

    if not download_dir:
        download_dir = str(PROJECT_ROOT / "data" / "delphi" / "attachments")
    Path(download_dir).mkdir(parents=True, exist_ok=True)

    try:
        msg = service.users().messages().get(userId="me", id=message_id, format="full").execute()
        results = []

        def _walk_parts(parts, depth=0):
            for part in parts:
                filename = part.get("filename", "")
                body = part.get("body", {})
                attachment_id = body.get("attachmentId")
                mime_type = part.get("mimeType", "")

                if filename and attachment_id:
                    if filename.startswith("image") and mime_type.startswith("image/") and body.get("size", 0) < 50000:
                        continue
                    try:
                        att = service.users().messages().attachments().get(
                            userId="me", messageId=message_id, id=attachment_id,
                        ).execute()
                        data = base64.urlsafe_b64decode(att["data"])

                        safe_name = "".join(c if c.isalnum() or c in "._-" else "_" for c in filename)
                        save_path = Path(download_dir) / f"{message_id[:8]}_{safe_name}"
                        save_path.write_bytes(data)

                        results.append({
                            "filename": filename,
                            "path": str(save_path),
                            "mime_type": mime_type,
                            "size_bytes": len(data),
                        })
                        logger.info("Downloaded attachment: %s (%d bytes)", filename, len(data))
                    except Exception as e:
                        logger.warning("Failed to download attachment %s: %s", filename, e)

                if "parts" in part:
                    _walk_parts(part["parts"], depth + 1)

        payload = msg.get("payload", {})
        if "parts" in payload:
            _walk_parts(payload["parts"])

        return results
    except Exception as e:
        logger.error("Gmail attachment error: %s", e)
        return []


def gmail_read_message(message_id: str) -> str:
    """Read the full content of a specific email by its message ID.

    Args:
        message_id: The Gmail message ID (returned by read_inbox or search_email).

    Returns:
        Full email with headers and body text.
    """
    service = _get_gmail_service()
    if not service:
        return "(Gmail not available. Check OAuth token.)"

    try:
        msg = service.users().messages().get(
            userId="me", id=message_id, format="full",
        ).execute()

        headers = {h["name"].lower(): h["value"] for h in msg.get("payload", {}).get("headers", [])}
        body = _extract_email_body(msg.get("payload", {}))
        labels = msg.get("labelIds", [])

        parts = [
            f"From: {headers.get('from', '?')}",
            f"To: {headers.get('to', '?')}",
        ]
        if headers.get("cc"):
            parts.append(f"CC: {headers['cc']}")
        parts.extend([
            f"Subject: {headers.get('subject', '(no subject)')}",
            f"Date: {headers.get('date', '?')}",
            f"Labels: {', '.join(labels)}",
            "",
            body[:6000] if body else "(no text body)",
        ])

        return "\n".join(parts)
    except Exception as e:
        logger.error(f"Gmail read message error: {e}")
        return f"(Gmail read message error: {e})"


def gmail_get_thread(thread_id: str, max_messages: int = 10) -> str:
    """Fetch a full email conversation thread.

    Args:
        thread_id: The Gmail thread ID.
        max_messages: Max messages to include from the thread.

    Returns:
        Formatted conversation thread with all messages.
    """
    service = _get_gmail_service()
    if not service:
        return "(Gmail not available. Check OAuth token.)"

    try:
        thread = service.users().threads().get(
            userId="me", id=thread_id, format="full",
        ).execute()

        messages = thread.get("messages", [])
        if not messages:
            return f"(Thread {thread_id} is empty)"

        first_headers = {h["name"].lower(): h["value"] for h in messages[0].get("payload", {}).get("headers", [])}
        subject = first_headers.get("subject", "(no subject)")

        lines = [f"Thread: {subject} ({len(messages)} messages)"]
        lines.append("=" * 50)

        for msg in messages[-max_messages:]:
            headers = {h["name"].lower(): h["value"] for h in msg.get("payload", {}).get("headers", [])}
            body = _extract_email_body(msg.get("payload", {}))

            lines.append(f"\nFrom: {headers.get('from', '?')}")
            lines.append(f"Date: {headers.get('date', '?')}")
            lines.append(f"{'-' * 30}")
            lines.append(body[:3000] if body else "(no text body)")
            lines.append("")

        return "\n".join(lines)
    except Exception as e:
        logger.error(f"Gmail thread error: {e}")
        return f"(Gmail thread error: {e})"


_ALLOWED_EMAIL_DOMAINS: set = set()

def _load_allowed_email_domains() -> set:
    """Load allowed email domains from env. Fallback to Machinecraft domains."""
    global _ALLOWED_EMAIL_DOMAINS
    if _ALLOWED_EMAIL_DOMAINS:
        return _ALLOWED_EMAIL_DOMAINS
    raw = os.environ.get("ALLOWED_EMAIL_DOMAINS", "")
    if raw:
        _ALLOWED_EMAIL_DOMAINS = {d.strip().lower() for d in raw.split(",") if d.strip()}
    else:
        _ALLOWED_EMAIL_DOMAINS = {"machinecraft.org", "machinecraft.com", "machinecraft.in"}
    return _ALLOWED_EMAIL_DOMAINS

def _is_email_allowed(address: str) -> bool:
    """Check if an email address is allowed for sending.

    Allows all addresses when ALLOWED_EMAIL_DOMAINS is set to '*',
    otherwise restricts to the configured domain allowlist.
    Addresses that previously received email from us (found in Gmail)
    are also allowed.
    """
    if not address or "@" not in address:
        return False
    domains = _load_allowed_email_domains()
    if "*" in domains:
        return True
    domain = address.rsplit("@", 1)[-1].lower()
    if domain in domains:
        return True
    # Check if we've emailed this address before (established contact)
    try:
        svc = _get_gmail_service()
        if svc:
            results = svc.users().messages().list(
                userId="me", q=f"to:{address}", maxResults=1
            ).execute()
            if results.get("messages"):
                return True
    except Exception:
        pass
    return False


def gmail_send(to: str, subject: str, body: str, body_html: str = "", thread_id: str = "", cc: str = "", attachments: list = None, plain_text_only: bool = False) -> str:
    """Send an email via Gmail API. Supports HTML and file attachments.

    Args:
        to: Recipient email address.
        subject: Email subject.
        body: Email body (plain text fallback).
        body_html: Optional HTML body for rich formatting. If provided,
                   sends multipart (text/plain + text/html).
        thread_id: Optional thread ID to reply in.
        cc: Comma-separated CC recipients.
        attachments: Optional list of file paths to attach.
        plain_text_only: If True, skip auto-HTML conversion and send plain text.

    Returns:
        Success/failure message.
    """
    if not _is_email_allowed(to):
        logger.warning(f"[Security] Blocked email send to unrecognized address: {to}")
        return (
            f"(BLOCKED: '{to}' is not a recognized recipient. "
            "For security, emails can only be sent to known contacts or "
            "Machinecraft domains. Ask Rushabh to approve this recipient.)"
        )

    service = _get_gmail_service()
    if not service:
        return "(Gmail not available. Check OAuth token.)"

    try:
        import base64
        import mimetypes
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        from email.mime.base import MIMEBase
        from email import encoders

        if not body_html and not plain_text_only:
            try:
                from openclaw.agents.ira.src.brain.email_styling import plain_to_html
                body_html = plain_to_html(body)
            except Exception:
                pass

        has_attachments = attachments and len(attachments) > 0

        if has_attachments:
            message = MIMEMultipart("mixed")
            if body_html:
                alt_part = MIMEMultipart("alternative")
                alt_part.attach(MIMEText(body, "plain"))
                alt_part.attach(MIMEText(body_html, "html"))
                message.attach(alt_part)
            else:
                message.attach(MIMEText(body, "plain"))

            for file_path in attachments:
                fp = Path(file_path)
                if not fp.exists():
                    logger.warning(f"Attachment not found: {fp}")
                    continue
                content_type, _ = mimetypes.guess_type(str(fp))
                if content_type is None:
                    content_type = "application/octet-stream"
                main_type, sub_type = content_type.split("/", 1)
                with open(fp, "rb") as f:
                    att = MIMEBase(main_type, sub_type)
                    att.set_payload(f.read())
                encoders.encode_base64(att)
                att.add_header("Content-Disposition", "attachment", filename=fp.name)
                message.attach(att)
        elif body_html:
            message = MIMEMultipart("alternative")
            message.attach(MIMEText(body, "plain"))
            message.attach(MIMEText(body_html, "html"))
        else:
            message = MIMEText(body)

        message["to"] = to
        message["subject"] = subject
        if cc:
            message["cc"] = cc

        raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
        send_body: Dict[str, Any] = {"raw": raw}
        if thread_id:
            send_body["threadId"] = thread_id

        result = service.users().messages().send(userId="me", body=send_body).execute()
        att_count = len(attachments) if has_attachments else 0
        fmt = f"HTML + {att_count} attachments" if has_attachments else ("HTML" if body_html else "plain text")
        return f"Email sent to {to} ({fmt}, message id: {result.get('id', '?')})"
    except Exception as e:
        logger.error(f"Gmail send error: {e}")
        return f"(Gmail send error: {e})"


# =============================================================================
# GOOGLE DOCUMENT AI
# =============================================================================

def document_ai_parse(file_path: str) -> str:
    """Parse a PDF/image using Google Document AI for OCR and structure extraction.

    Args:
        file_path: Path to the file to parse

    Returns:
        Extracted text content.
    """
    sa_creds = _get_service_account_creds()
    if not sa_creds:
        return "(Document AI not available -- service account not configured.)"

    processor_id = os.environ.get("DOCUMENT_AI_PROCESSOR_ID", "")
    if not processor_id:
        return "(Document AI not available -- DOCUMENT_AI_PROCESSOR_ID not set.)"

    location = os.environ.get("DOCUMENT_AI_LOCATION", "us")

    try:
        from google.cloud import documentai_v1 as documentai

        client = documentai.DocumentProcessorServiceClient(credentials=sa_creds)

        file_path = Path(file_path)
        if not file_path.exists():
            return f"(File not found: {file_path})"

        with open(file_path, "rb") as f:
            content = f.read()

        mime_type = "application/pdf"
        if file_path.suffix.lower() in [".png", ".jpg", ".jpeg"]:
            mime_type = f"image/{file_path.suffix.lower().strip('.')}"

        raw_document = documentai.RawDocument(content=content, mime_type=mime_type)

        project_id = sa_creds.project_id
        name = client.processor_path(project_id, location, processor_id)

        request = documentai.ProcessRequest(name=name, raw_document=raw_document)
        result = client.process_document(request=request)

        text = result.document.text
        if not text:
            return "(Document AI returned no text.)"

        return f"[Document AI parsed: {file_path.name}]\n{text[:8000]}"
    except ImportError:
        return "(Document AI SDK not installed. Run: pip install google-cloud-documentai)"
    except Exception as e:
        logger.error(f"Document AI error: {e}")
        return f"(Document AI error: {e})"


# =============================================================================
# GOOGLE DLP (Data Loss Prevention)
# =============================================================================

def dlp_inspect(text: str) -> Tuple[bool, List[str]]:
    """Check text for sensitive data (PII, credentials, etc.) before sending.

    Args:
        text: The text to inspect

    Returns:
        (is_safe, findings) -- is_safe is False if sensitive data found.
    """
    sa_creds = _get_service_account_creds()
    if not sa_creds:
        return True, []

    try:
        from google.cloud import dlp_v2

        client = dlp_v2.DlpServiceClient(credentials=sa_creds)
        project_id = sa_creds.project_id

        item = dlp_v2.ContentItem(value=text[:10000])

        info_types = [
            dlp_v2.InfoType(name=t) for t in [
                "EMAIL_ADDRESS", "PHONE_NUMBER", "CREDIT_CARD_NUMBER",
                "IBAN_CODE", "PASSPORT", "INDIA_PAN_INDIVIDUAL",
                "INDIA_AADHAAR_INDIVIDUAL",
            ]
        ]

        inspect_config = dlp_v2.InspectConfig(
            info_types=info_types,
            min_likelihood=dlp_v2.Likelihood.LIKELY,
            include_quote=False,
        )

        request = dlp_v2.InspectContentRequest(
            parent=f"projects/{project_id}",
            inspect_config=inspect_config,
            item=item,
        )

        response = client.inspect_content(request=request)
        findings = response.result.findings

        if not findings:
            return True, []

        issues = []
        for finding in findings[:5]:
            issues.append(f"{finding.info_type.name} (likelihood: {finding.likelihood.name})")

        return False, issues
    except ImportError:
        return True, []
    except Exception as e:
        logger.debug(f"DLP inspect error: {e}")
        return True, []


# =============================================================================
# CONVENIENCE: Get available tools
# =============================================================================

def get_available_google_tools() -> Dict[str, bool]:
    """Check which Google tools are available."""
    available = {}

    creds = _get_oauth_creds()
    oauth_ok = creds is not None
    available["gmail"] = oauth_ok
    available["sheets"] = oauth_ok
    available["drive"] = oauth_ok
    available["calendar"] = oauth_ok
    available["contacts"] = oauth_ok

    sa_creds = _get_service_account_creds()
    available["document_ai"] = sa_creds is not None and bool(os.environ.get("DOCUMENT_AI_PROCESSOR_ID"))
    available["dlp"] = sa_creds is not None

    return available
