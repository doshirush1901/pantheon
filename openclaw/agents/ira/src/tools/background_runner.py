"""
Background Task Runner
======================

Launches long-running Ira tasks in a background thread.
When complete, delivers results proactively via Telegram.

This is the "Manus-like" async execution: user says "go do X",
Ira says "on it", works in the background, and messages back when done.
"""

import asyncio
import json
import logging
import os
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger("ira.background_runner")

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent.parent
TASKS_DIR = PROJECT_ROOT / "data" / "background_tasks"

_active_tasks: Dict[str, Dict[str, Any]] = {}


def launch_background_task(
    task_description: str,
    notify_channel: str = "telegram",
    context: Optional[Dict[str, Any]] = None,
) -> str:
    """Launch a background task. Returns task_id immediately."""
    TASKS_DIR.mkdir(parents=True, exist_ok=True)

    task_id = f"BG-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}"

    task_record = {
        "task_id": task_id,
        "description": task_description,
        "notify_channel": notify_channel,
        "status": "running",
        "started_at": datetime.now().isoformat(),
        "user_id": (context or {}).get("user_id", "unknown"),
        "channel": (context or {}).get("channel", "api"),
    }

    task_file = TASKS_DIR / f"{task_id}.json"
    task_file.write_text(json.dumps(task_record, indent=2))
    _active_tasks[task_id] = task_record

    ctx = dict(context or {})
    ctx.pop("_progress_callback", None)

    thread = threading.Thread(
        target=_run_task_in_thread,
        args=(task_id, task_description, notify_channel, ctx),
        daemon=True,
        name=f"bg-{task_id}",
    )
    thread.start()

    logger.info("Background task launched: %s — %s", task_id, task_description[:100])
    return task_id


def _run_task_in_thread(
    task_id: str,
    task_description: str,
    notify_channel: str,
    context: Dict[str, Any],
):
    """Execute the task in a new event loop and deliver results."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(
            _execute_task(task_id, task_description, context)
        )
        _deliver_result(task_id, task_description, result, notify_channel, context)
        _update_task_status(task_id, "completed", result)
    except Exception as e:
        logger.error("Background task %s failed: %s", task_id, e)
        error_msg = f"Background task failed: {e}"
        _deliver_result(task_id, task_description, error_msg, notify_channel, context)
        _update_task_status(task_id, "failed", str(e))
    finally:
        loop.close()


async def _execute_task(
    task_id: str,
    task_description: str,
    context: Dict[str, Any],
) -> str:
    """Run the task through Ira's full agentic pipeline."""
    from openclaw.agents.ira.src.core.tool_orchestrator import process_with_tools

    bg_context = {
        **context,
        "channel": "background",
        "is_internal": True,
        "_background_task_id": task_id,
    }

    enriched_prompt = (
        f"BACKGROUND TASK (task_id: {task_id}):\n\n"
        f"{task_description}\n\n"
        "This is a background task — be EXTREMELY thorough. Use 15-25 tool rounds. "
        "Research deeply, cross-reference, and produce a comprehensive result. "
        "If the task involves creating a deliverable, use create_report to generate "
        "a proper document. If it involves drafting emails, draft all of them. "
        "The user is not waiting — take your time and do excellent work."
    )

    result = await process_with_tools(
        message=enriched_prompt,
        channel="background",
        user_id=context.get("user_id", "unknown"),
        context=bg_context,
    )

    return result


def _deliver_result(
    task_id: str,
    task_description: str,
    result: str,
    notify_channel: str,
    context: Dict[str, Any],
):
    """Send the completed result to the user."""
    if notify_channel == "telegram":
        _send_telegram(task_id, task_description, result)
    elif notify_channel == "email":
        _send_email(task_id, task_description, result, context)
    else:
        logger.info("Background task %s completed (no delivery channel): %s", task_id, result[:200])


def _send_telegram(task_id: str, task_description: str, result: str):
    """Send result to Telegram."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.environ.get("RUSHABH_TELEGRAM_CHAT_ID") or os.environ.get("RUSHABH_TELEGRAM_ID", "")
    if not token or not chat_id:
        logger.warning("Cannot deliver background task %s — no Telegram credentials", task_id)
        return

    import requests

    header = f"Background task complete: {task_id}\nTask: {task_description[:200]}\n\n"
    full_msg = header + result

    # Telegram has a 4096 char limit; split if needed
    chunks = []
    while full_msg:
        if len(full_msg) <= 4000:
            chunks.append(full_msg)
            break
        split_at = full_msg[:4000].rfind("\n")
        if split_at < 500:
            split_at = 4000
        chunks.append(full_msg[:split_at])
        full_msg = full_msg[split_at:]

    for chunk in chunks:
        try:
            requests.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={"chat_id": chat_id, "text": chunk},
                timeout=15,
            )
        except Exception as e:
            logger.error("Telegram delivery failed for %s: %s", task_id, e)

    # Also send any report files that were generated
    task_file = TASKS_DIR / f"{task_id}.json"
    if task_file.exists():
        task_data = json.loads(task_file.read_text())
        for report in task_data.get("report_files", []):
            html_path = report.get("html_path", "")
            if html_path and Path(html_path).exists():
                try:
                    with open(html_path, "rb") as f:
                        requests.post(
                            f"https://api.telegram.org/bot{token}/sendDocument",
                            data={"chat_id": chat_id, "caption": f"Report: {report.get('title', task_id)}"},
                            files={"document": (Path(html_path).name, f)},
                            timeout=30,
                        )
                except Exception as e:
                    logger.error("Report file delivery failed: %s", e)


def _send_email(task_id: str, task_description: str, result: str, context: Dict[str, Any]):
    """Send result via email."""
    try:
        from openclaw.agents.ira.src.tools.google_tools import gmail_send
        to = context.get("user_email", "rushabh@machinecraft.org")
        gmail_send(
            to=to,
            subject=f"Ira Background Task Complete: {task_description[:80]}",
            body=f"Task ID: {task_id}\n\n{result}",
        )
    except Exception as e:
        logger.error("Email delivery failed for %s: %s", task_id, e)


def _update_task_status(task_id: str, status: str, result: Any):
    """Update the task record on disk."""
    task_file = TASKS_DIR / f"{task_id}.json"
    if task_file.exists():
        data = json.loads(task_file.read_text())
    else:
        data = {"task_id": task_id}

    data["status"] = status
    data["completed_at"] = datetime.now().isoformat()
    data["result_preview"] = str(result)[:500] if result else ""
    task_file.write_text(json.dumps(data, indent=2))
    _active_tasks.pop(task_id, None)
