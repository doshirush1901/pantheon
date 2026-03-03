"""
Report Builder — Rich Artifact Generation
==========================================

Lets Athena / Hephaestus create downloadable reports (HTML or Markdown)
that can be attached to Telegram messages or emails.

Output directory: data/exports/reports/
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger("ira.report_builder")

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent.parent
REPORTS_DIR = PROJECT_ROOT / "data" / "exports" / "reports"

_FONT_STACK = "Montserrat, 'Helvetica Neue', Helvetica, Arial, sans-serif"
_COLOR_ACCENT = "#2b4b96"
_COLOR_BODY = "#212121"


def build_report(
    title: str,
    body_markdown: str,
    report_type: str = "research",
    metadata: Optional[dict] = None,
) -> dict:
    """Build an HTML report from markdown-ish content and save to disk.

    Returns dict with ``report_id``, ``html_path``, ``md_path``, ``title``.
    """
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    ts = datetime.now()
    report_id = f"RPT-{ts.strftime('%Y%m%d%H%M%S')}-{report_type[:4].upper()}"
    safe_title = "".join(c if c.isalnum() or c in " -_" else "" for c in title)[:60].strip().replace(" ", "_")
    base_name = f"{report_id}_{safe_title}"

    md_path = REPORTS_DIR / f"{base_name}.md"
    html_path = REPORTS_DIR / f"{base_name}.html"

    md_content = f"# {title}\n\n"
    md_content += f"*Report ID: {report_id} | Generated: {ts.strftime('%Y-%m-%d %H:%M')}*\n\n"
    md_content += body_markdown
    if metadata:
        md_content += f"\n\n---\n*Metadata: {json.dumps(metadata, default=str)}*\n"

    md_path.write_text(md_content, encoding="utf-8")

    html_body = _markdown_to_html(body_markdown)
    html_content = _wrap_html(title, report_id, ts, html_body)
    html_path.write_text(html_content, encoding="utf-8")

    logger.info("Report generated: %s (%s)", report_id, html_path)

    return {
        "report_id": report_id,
        "title": title,
        "html_path": str(html_path),
        "md_path": str(md_path),
        "report_type": report_type,
        "generated_at": ts.isoformat(),
    }


def _markdown_to_html(md: str) -> str:
    """Lightweight markdown-to-HTML for reports (no external deps)."""
    import re

    lines = md.split("\n")
    html_parts: list = []
    i = 0

    while i < len(lines):
        line = lines[i]

        if not line.strip():
            i += 1
            continue

        if line.startswith("### "):
            html_parts.append(f'<h3 style="color:{_COLOR_ACCENT};margin:24px 0 8px 0;">{_inline(line[4:])}</h3>')
            i += 1
            continue
        if line.startswith("## "):
            html_parts.append(f'<h2 style="color:{_COLOR_ACCENT};margin:28px 0 12px 0;">{_inline(line[3:])}</h2>')
            i += 1
            continue
        if line.startswith("# "):
            html_parts.append(f'<h1 style="color:{_COLOR_ACCENT};margin:32px 0 16px 0;">{_inline(line[2:])}</h1>')
            i += 1
            continue

        if re.match(r"^\s*[-*]\s+", line):
            items = []
            while i < len(lines) and re.match(r"^\s*[-*]\s+", lines[i]):
                items.append(_inline(re.sub(r"^\s*[-*]\s+", "", lines[i])))
                i += 1
            html_parts.append("<ul>" + "".join(f"<li>{it}</li>" for it in items) + "</ul>")
            continue

        if re.match(r"^\s*\d+[.)]\s+", line):
            items = []
            while i < len(lines) and re.match(r"^\s*\d+[.)]\s+", lines[i]):
                items.append(_inline(re.sub(r"^\s*\d+[.)]\s+", "", lines[i])))
                i += 1
            html_parts.append("<ol>" + "".join(f"<li>{it}</li>" for it in items) + "</ol>")
            continue

        if line.startswith("|") and i + 1 < len(lines) and lines[i + 1].startswith("|"):
            table_lines = []
            while i < len(lines) and lines[i].startswith("|"):
                table_lines.append(lines[i])
                i += 1
            html_parts.append(_table_to_html(table_lines))
            continue

        if line.startswith("---") or line.startswith("***"):
            html_parts.append("<hr>")
            i += 1
            continue

        para = []
        while i < len(lines) and lines[i].strip() and not lines[i].startswith("#") and not re.match(r"^\s*[-*]\s+", lines[i]) and not lines[i].startswith("|"):
            para.append(lines[i])
            i += 1
        html_parts.append(f'<p style="margin:0 0 12px 0;line-height:1.6;">{_inline(" ".join(para))}</p>')

    return "\n".join(html_parts)


def _inline(text: str) -> str:
    import re
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<!\*)\*([^*]+?)\*(?!\*)", r"<em>\1</em>", text)
    text = re.sub(r"`([^`]+)`", r'<code style="background:#f0f0f0;padding:2px 4px;border-radius:3px;">\1</code>', text)
    return text


def _table_to_html(lines: list) -> str:
    rows = []
    for line in lines:
        cells = [c.strip() for c in line.strip("|").split("|")]
        rows.append(cells)
    if len(rows) < 2:
        return ""
    separator_idx = None
    for idx, row in enumerate(rows):
        if all(set(c.strip()) <= {"-", ":"} for c in row):
            separator_idx = idx
            break

    html = '<table style="border-collapse:collapse;width:100%;margin:12px 0;">'
    header = rows[0] if separator_idx and separator_idx > 0 else None
    if header:
        html += "<thead><tr>"
        for cell in header:
            html += f'<th style="border:1px solid #ddd;padding:8px;background:{_COLOR_ACCENT};color:#fff;text-align:left;">{_inline(cell)}</th>'
        html += "</tr></thead>"

    start = (separator_idx + 1) if separator_idx is not None else (1 if header else 0)
    html += "<tbody>"
    for row in rows[start:]:
        html += "<tr>"
        for cell in row:
            html += f'<td style="border:1px solid #ddd;padding:8px;">{_inline(cell)}</td>'
        html += "</tr>"
    html += "</tbody></table>"
    return html


def _wrap_html(title: str, report_id: str, ts: datetime, body: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} — Machinecraft</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;500;600;700&display=swap');
body {{ font-family: {_FONT_STACK}; color: {_COLOR_BODY}; max-width: 800px; margin: 40px auto; padding: 0 20px; line-height: 1.6; }}
h1, h2, h3 {{ color: {_COLOR_ACCENT}; }}
table {{ border-collapse: collapse; width: 100%; }}
th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
th {{ background: {_COLOR_ACCENT}; color: #fff; }}
hr {{ border: none; border-top: 2px solid #eee; margin: 24px 0; }}
code {{ background: #f0f0f0; padding: 2px 6px; border-radius: 3px; font-size: 0.9em; }}
ul, ol {{ padding-left: 24px; }}
li {{ margin-bottom: 4px; }}
.header {{ border-bottom: 3px solid {_COLOR_ACCENT}; padding-bottom: 16px; margin-bottom: 24px; }}
.footer {{ border-top: 1px solid #ddd; padding-top: 16px; margin-top: 32px; font-size: 0.85em; color: #888; }}
</style>
</head>
<body>
<div class="header">
<h1>{title}</h1>
<p style="color:#888;font-size:0.9em;">Report ID: {report_id} | Generated: {ts.strftime('%Y-%m-%d %H:%M')} | Machinecraft Technologies</p>
</div>
{body}
<div class="footer">
<p>Generated by Ira — Intelligent Revenue Assistant | Machinecraft Technologies</p>
<p>ira@machinecraft.org | machinecraft.org</p>
</div>
</body>
</html>"""
