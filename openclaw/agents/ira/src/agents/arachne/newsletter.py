"""
Arachne — Newsletter Assembly
==============================

Assembles monthly newsletters from multiple content sources
(Atlas, Cadmus, Iris, machine_specs) and renders them as HTML
for distribution via Gmail.
"""

from __future__ import annotations

import json
import logging
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("ira.agents.arachne.newsletter")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent.parent.parent
ARACHNE_DIR = PROJECT_ROOT / "data" / "arachne"
TEMPLATE_PATH = ARACHNE_DIR / "newsletter_template.html"
ARCHIVE_DIR = ARACHNE_DIR / "newsletter_archive"
SUBSCRIBERS_PATH = ARACHNE_DIR / "subscribers.json"

MACHINE_SERIES_ROTATION = [
    ("PF1-C", "PF1-C Series — Pneumatic Vacuum Forming", "Reliable, cost-effective pneumatic forming for 1-8mm sheets."),
    ("PF1-X", "PF1-X Series — All-Servo with ZeroSag", "Precision servo-driven forming with patented ZeroSag technology."),
    ("AM", "AM Series — Multi-Station Thin Gauge", "High-speed multi-station forming for materials up to 1.5mm."),
    ("IMG", "IMG Series — In-Mold Graining", "Class-A textured surfaces for automotive interiors."),
    ("PF2", "PF2 Series — Large Format", "Large-format positive forming for bathtubs, shower trays, and spas."),
    ("ATF", "ATF Series — Automatic Thermoforming", "Fully automatic thermoforming for high-volume production."),
]


def _load_subscribers() -> Dict[str, Any]:
    ARACHNE_DIR.mkdir(parents=True, exist_ok=True)
    if SUBSCRIBERS_PATH.exists():
        try:
            return json.loads(SUBSCRIBERS_PATH.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return {"subscribers": [], "unsubscribed": []}


def _save_subscribers(data: Dict[str, Any]) -> None:
    ARACHNE_DIR.mkdir(parents=True, exist_ok=True)
    SUBSCRIBERS_PATH.write_text(json.dumps(data, indent=2))


def get_subscriber_list() -> List[Dict[str, Any]]:
    data = _load_subscribers()
    unsub = set(data.get("unsubscribed", []))
    return [
        s for s in data.get("subscribers", [])
        if s.get("subscribed", True) and s.get("email") not in unsub
    ]


def add_subscriber(
    email: str,
    name: str = "",
    company: str = "",
    source: str = "manual",
    tags: Optional[List[str]] = None,
) -> bool:
    """Add a subscriber. Returns True if new, False if already exists."""
    data = _load_subscribers()
    existing_emails = {s["email"].lower() for s in data.get("subscribers", [])}
    if email.lower() in existing_emails:
        return False
    data.setdefault("subscribers", []).append({
        "email": email,
        "name": name,
        "company": company,
        "source": source,
        "tags": tags or [],
        "subscribed": True,
        "added_date": date.today().isoformat(),
    })
    _save_subscribers(data)
    return True


def unsubscribe(email: str) -> bool:
    data = _load_subscribers()
    unsub = set(data.get("unsubscribed", []))
    if email.lower() in unsub:
        return False
    unsub.add(email.lower())
    data["unsubscribed"] = list(unsub)
    _save_subscribers(data)
    return True


def _load_template() -> str:
    if TEMPLATE_PATH.exists():
        return TEMPLATE_PATH.read_text()
    return _DEFAULT_TEMPLATE


async def _gather_section_new_orders() -> str:
    """Pull recent order milestones from Atlas."""
    try:
        from openclaw.agents.ira.src.skills.invocation import invoke_all_projects_overview
        result = await invoke_all_projects_overview({})
        if result and len(result) > 20:
            lines = result.strip().split("\n")[:15]
            return "\n".join(lines)
    except Exception as e:
        logger.warning("Newsletter: failed to gather orders: %s", e)
    return "No recent order updates available."


async def _gather_section_case_study() -> str:
    """Pull the latest published case study from Cadmus."""
    try:
        from openclaw.agents.ira.src.agents.cadmus import find_case_studies
        result = await find_case_studies(
            query="latest",
            format="paragraph",
            context={},
        )
        if result and len(result) > 20:
            return result[:2000]
    except Exception as e:
        logger.warning("Newsletter: failed to gather case study: %s", e)
    return "Stay tuned for upcoming customer success stories."


def _gather_section_product_spotlight() -> str:
    """Rotating machine series spotlight."""
    month_idx = date.today().month % len(MACHINE_SERIES_ROTATION)
    series_id, title, desc = MACHINE_SERIES_ROTATION[month_idx]

    try:
        specs_path = PROJECT_ROOT / "data" / "brain" / "machine_specs.json"
        if specs_path.exists():
            specs = json.loads(specs_path.read_text())
            models = [k for k in specs if k.startswith(series_id)]
            if models:
                desc += f" ({len(models)} models available)"
    except Exception:
        pass

    return f"<strong>{title}</strong><br>{desc}"


async def _gather_section_events() -> str:
    """Pull upcoming events from Google Calendar."""
    try:
        from openclaw.agents.ira.src.tools.google_tools import calendar_upcoming
        result = calendar_upcoming(30)
        if result and "no upcoming" not in result.lower():
            return result[:1000]
    except Exception as e:
        logger.warning("Newsletter: failed to gather events: %s", e)
    return "No upcoming events scheduled."


async def _gather_section_industry_insight() -> str:
    """Pull a recent industry insight via Iris."""
    try:
        from openclaw.agents.ira.src.tools.newsdata_client import search_news
        result = await search_news(
            query="thermoforming vacuum forming plastics manufacturing",
            category="business,technology",
            max_results=3,
        )
        if result and len(result) > 20:
            return result[:1500]
    except Exception as e:
        logger.warning("Newsletter: failed to gather industry news: %s", e)
    return "Industry insights coming soon."


async def assemble_newsletter(
    title: Optional[str] = None,
    sections: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Assemble a newsletter from multiple sources.

    Returns dict with 'subject', 'body_html', 'body_text', 'sections_gathered'.
    """
    if not title:
        title = f"Machinecraft Newsletter — {date.today().strftime('%B %Y')}"
    if not sections:
        sections = ["new_orders", "case_study", "product_spotlight", "event", "industry_insight"]

    section_content: Dict[str, str] = {}

    for section in sections:
        if section == "new_orders":
            section_content[section] = await _gather_section_new_orders()
        elif section == "case_study":
            section_content[section] = await _gather_section_case_study()
        elif section == "product_spotlight":
            section_content[section] = _gather_section_product_spotlight()
        elif section == "event":
            section_content[section] = await _gather_section_events()
        elif section == "industry_insight":
            section_content[section] = await _gather_section_industry_insight()

    body_html = _render_html(title, section_content)
    body_text = _render_plaintext(title, section_content)

    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    archive_name = f"newsletter_{date.today().isoformat()}.html"
    (ARCHIVE_DIR / archive_name).write_text(body_html)

    return {
        "subject": title,
        "body_html": body_html,
        "body_text": body_text,
        "sections_gathered": list(section_content.keys()),
        "archive_path": str(ARCHIVE_DIR / archive_name),
    }


_SECTION_TITLES = {
    "new_orders": "Recent Orders & Milestones",
    "case_study": "Customer Spotlight",
    "product_spotlight": "Product Spotlight",
    "event": "Upcoming Events",
    "industry_insight": "Industry Insights",
}


def _render_html(title: str, sections: Dict[str, str]) -> str:
    template = _load_template()

    sections_html = ""
    for key, content in sections.items():
        heading = _SECTION_TITLES.get(key, key.replace("_", " ").title())
        content_html = content.replace("\n", "<br>") if "<" not in content else content
        sections_html += f"""
        <tr>
          <td style="padding: 20px 30px;">
            <h2 style="color: #1a1a2e; font-size: 20px; margin: 0 0 12px 0; border-bottom: 2px solid #e94560; padding-bottom: 8px;">{heading}</h2>
            <div style="color: #333; font-size: 15px; line-height: 1.6;">{content_html}</div>
          </td>
        </tr>
        """

    html = template.replace("{{TITLE}}", title)
    html = html.replace("{{SECTIONS}}", sections_html)
    html = html.replace("{{MONTH_YEAR}}", date.today().strftime("%B %Y"))
    html = html.replace("{{YEAR}}", str(date.today().year))
    return html


def _render_plaintext(title: str, sections: Dict[str, str]) -> str:
    lines = [title, "=" * len(title), ""]
    for key, content in sections.items():
        heading = _SECTION_TITLES.get(key, key.replace("_", " ").title())
        lines.append(heading)
        lines.append("-" * len(heading))
        # Strip HTML tags for plaintext
        import re
        clean = re.sub(r"<[^>]+>", "", content)
        lines.append(clean)
        lines.append("")
    lines.append("---")
    lines.append("Machinecraft Technologies Pvt. Ltd.")
    lines.append("To unsubscribe, reply with 'unsubscribe'.")
    return "\n".join(lines)


async def send_newsletter(
    newsletter: Dict[str, Any],
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Send the assembled newsletter to all subscribers.

    Batches sends in groups of 50 (BCC) to respect Gmail limits.
    Returns stats dict.
    """
    import asyncio

    subscribers = get_subscriber_list()
    if not subscribers:
        return {"sent": 0, "error": "No subscribers"}

    emails = [s["email"] for s in subscribers if s.get("email")]
    if not emails:
        return {"sent": 0, "error": "No valid email addresses"}

    if dry_run:
        return {
            "sent": 0,
            "dry_run": True,
            "would_send_to": len(emails),
            "batches": (len(emails) + 49) // 50,
        }

    try:
        from openclaw.agents.ira.src.tools.google_tools import gmail_send
    except ImportError:
        return {"sent": 0, "error": "Gmail not available"}

    batch_size = 50
    sent_count = 0
    errors = []

    for i in range(0, len(emails), batch_size):
        batch = emails[i:i + batch_size]
        bcc = ",".join(batch)
        try:
            result = gmail_send(
                to="newsletter@machinecraft.org",
                subject=newsletter["subject"],
                body=newsletter["body_text"],
                body_html=newsletter["body_html"],
                cc=bcc,
            )
            if "sent" in result.lower() or "success" in result.lower():
                sent_count += len(batch)
            else:
                errors.append(f"Batch {i // batch_size + 1}: {result}")
        except Exception as e:
            errors.append(f"Batch {i // batch_size + 1}: {e}")

        if i + batch_size < len(emails):
            await asyncio.sleep(2)

    from .calendar_engine import log_distribution
    log_distribution(
        item_id=f"NL-{date.today().isoformat()}",
        channel="newsletter",
        details={"sent": sent_count, "total_subscribers": len(emails), "errors": errors},
    )

    return {"sent": sent_count, "total": len(emails), "errors": errors}


_DEFAULT_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{{TITLE}}</title>
</head>
<body style="margin: 0; padding: 0; background-color: #f4f4f8; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color: #f4f4f8;">
    <tr>
      <td align="center" style="padding: 30px 10px;">
        <table role="presentation" width="600" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.08);">
          <!-- Header -->
          <tr>
            <td style="background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); padding: 30px; text-align: center;">
              <h1 style="color: #ffffff; margin: 0; font-size: 26px; font-weight: 700;">Machinecraft</h1>
              <p style="color: #e94560; margin: 8px 0 0 0; font-size: 14px; letter-spacing: 1px;">THERMOFORMING INTELLIGENCE</p>
            </td>
          </tr>
          <!-- Title -->
          <tr>
            <td style="padding: 25px 30px 10px 30px;">
              <h1 style="color: #1a1a2e; font-size: 22px; margin: 0;">{{TITLE}}</h1>
              <p style="color: #888; font-size: 13px; margin: 6px 0 0 0;">{{MONTH_YEAR}}</p>
            </td>
          </tr>
          <!-- Sections -->
          {{SECTIONS}}
          <!-- Footer -->
          <tr>
            <td style="background-color: #1a1a2e; padding: 20px 30px; text-align: center;">
              <p style="color: #aaa; font-size: 12px; margin: 0;">Machinecraft Technologies Pvt. Ltd.</p>
              <p style="color: #666; font-size: 11px; margin: 8px 0 0 0;">To unsubscribe, reply with "unsubscribe".</p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""
