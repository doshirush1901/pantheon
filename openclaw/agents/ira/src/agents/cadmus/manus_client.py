"""
Manus API Client — Cadmus Only
===============================

Thin wrapper around the Manus task API for generating visuals and
presentation slides. EXPENSIVE — gated to Cadmus agent only.

Usage:
    result = await manus_generate(
        prompt="Create a professional LinkedIn carousel image...",
        agent_profile="manus-1.6",
    )
    # result.text — text output
    # result.files — list of {url, filename, mime_type}
    # result.credits_used — cost tracking
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger("ira.agents.cadmus.manus")

MANUS_API_BASE = "https://api.manus.ai"
MANUS_TASK_ENDPOINT = f"{MANUS_API_BASE}/v1/tasks"

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent.parent.parent
MANUS_DOWNLOADS_DIR = PROJECT_ROOT / "data" / "cadmus" / "manus_outputs"

# Cost tracking
COST_LOG_PATH = PROJECT_ROOT / "data" / "cadmus" / "manus_cost_log.jsonl"


@dataclass
class ManusResult:
    task_id: str = ""
    status: str = ""
    text: str = ""
    files: List[Dict[str, str]] = field(default_factory=list)
    credits_used: int = 0
    task_url: str = ""
    error: str = ""


def _get_api_key() -> str:
    key = os.environ.get("MANUS_API_KEY", "")
    if not key:
        logger.warning("MANUS_API_KEY not set in environment")
    return key


def _headers() -> Dict[str, str]:
    return {
        "accept": "application/json",
        "content-type": "application/json",
        "API_KEY": _get_api_key(),
    }


def _log_cost(task_id: str, credits: int, prompt_preview: str):
    """Append to cost log for tracking spend."""
    import json
    COST_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "task_id": task_id,
        "credits": credits,
        "prompt": prompt_preview[:200],
    }
    with open(COST_LOG_PATH, "a") as f:
        f.write(json.dumps(entry) + "\n")


def _create_task(
    prompt: str,
    agent_profile: str = "manus-1.6",
    attachments: Optional[List[Dict]] = None,
) -> Dict[str, Any]:
    """Create a Manus task. Returns {task_id, task_url, ...}."""
    payload: Dict[str, Any] = {
        "prompt": prompt,
        "agentProfile": agent_profile,
        "hideInTaskList": False,
    }
    if attachments:
        payload["attachments"] = attachments

    resp = requests.post(MANUS_TASK_ENDPOINT, json=payload, headers=_headers(), timeout=30)
    resp.raise_for_status()
    return resp.json()


def _get_task(task_id: str) -> Dict[str, Any]:
    """Poll task status. Returns full task object."""
    resp = requests.get(
        f"{MANUS_TASK_ENDPOINT}/{task_id}",
        headers=_headers(),
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def _download_file(url: str, filename: str) -> str:
    """Download a file from Manus output to local storage."""
    MANUS_DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = "".join(c if c.isalnum() or c in "._-" else "_" for c in filename)
    local_path = MANUS_DOWNLOADS_DIR / safe_name

    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    local_path.write_bytes(resp.content)
    logger.info("Downloaded Manus output: %s (%d bytes)", safe_name, len(resp.content))
    return str(local_path)


async def manus_generate(
    prompt: str,
    agent_profile: str = "manus-1.6",
    attachments: Optional[List[Dict]] = None,
    max_wait_seconds: int = 300,
    poll_interval: int = 10,
) -> ManusResult:
    """Create a Manus task, wait for completion, return results.

    Args:
        prompt: The task instruction for Manus.
        agent_profile: "manus-1.6" (default), "manus-1.6-lite" (cheaper), or "manus-1.6-max" (best).
        attachments: Optional file attachments [{filename, url}] or [{filename, fileData}].
        max_wait_seconds: Max time to wait for task completion.
        poll_interval: Seconds between status polls.

    Returns:
        ManusResult with text, files, credits_used, etc.
    """
    if not _get_api_key():
        return ManusResult(error="MANUS_API_KEY not configured")

    result = ManusResult()

    try:
        # Create task
        create_resp = _create_task(prompt, agent_profile, attachments)
        result.task_id = create_resp.get("task_id", "")
        result.task_url = create_resp.get("task_url", "")
        logger.info("Manus task created: %s", result.task_id)

        if not result.task_id:
            result.error = f"No task_id in response: {create_resp}"
            return result

        # Poll for completion
        start = time.time()
        while time.time() - start < max_wait_seconds:
            await asyncio.sleep(poll_interval)

            task_data = _get_task(result.task_id)
            status = task_data.get("status", "unknown")
            result.status = status

            if status == "completed":
                result.credits_used = task_data.get("credit_usage", 0)

                # Extract text and files from output
                for msg in task_data.get("output", []):
                    if msg.get("role") != "assistant":
                        continue
                    for content in msg.get("content", []):
                        if content.get("type") == "output_text":
                            result.text += content.get("text", "") + "\n"
                        elif content.get("type") == "output_file":
                            file_info = {
                                "url": content.get("fileUrl", ""),
                                "filename": content.get("fileName", ""),
                                "mime_type": content.get("mimeType", ""),
                            }
                            if file_info["url"]:
                                try:
                                    local = _download_file(file_info["url"], file_info["filename"])
                                    file_info["local_path"] = local
                                except Exception as e:
                                    logger.warning("Failed to download %s: %s", file_info["filename"], e)
                            result.files.append(file_info)

                _log_cost(result.task_id, result.credits_used, prompt)
                logger.info(
                    "Manus task completed: %s (credits: %d, files: %d)",
                    result.task_id, result.credits_used, len(result.files),
                )
                return result

            elif status == "failed":
                result.error = task_data.get("error", "Task failed")
                _log_cost(result.task_id, task_data.get("credit_usage", 0), prompt)
                return result

        result.error = f"Timeout after {max_wait_seconds}s (status: {result.status})"
        return result

    except requests.HTTPError as e:
        result.error = f"Manus API error: {e.response.status_code} {e.response.text[:200]}"
        logger.error("Manus HTTP error: %s", result.error)
        return result
    except Exception as e:
        result.error = f"Manus error: {e}"
        logger.error("Manus error: %s", e)
        return result


def get_manus_spend_today() -> Dict[str, Any]:
    """Get today's Manus API spend from the cost log."""
    import json
    today = time.strftime("%Y-%m-%d")
    total_credits = 0
    task_count = 0

    if COST_LOG_PATH.exists():
        for line in COST_LOG_PATH.read_text().splitlines():
            try:
                entry = json.loads(line)
                if entry.get("timestamp", "").startswith(today):
                    total_credits += entry.get("credits", 0)
                    task_count += 1
            except Exception:
                continue

    return {"date": today, "credits": total_credits, "tasks": task_count}
