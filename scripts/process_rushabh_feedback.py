#!/usr/bin/env python3
"""Process Rushabh feedback from chat log for dream stage."""
import json
from pathlib import Path

def main():
    root = Path(__file__).parent.parent
    log_path = root / "data" / "chat_log" / "rushabh_ira_chat.jsonl"
    feedback_items = []
    if log_path.exists():
        with open(log_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    if entry.get("is_feedback") and entry.get("role") == "user":
                        feedback_items.append(entry)
                except json.JSONDecodeError:
                    pass
    print(f"Feedback entries from Rushabh: {len(feedback_items)}")
    backlog_path = root / "data" / "chat_log" / "feedback_backlog.jsonl"
    backlog_path.parent.mkdir(parents=True, exist_ok=True)
    with open(backlog_path, "w") as f:
        for item in feedback_items:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
    print(f"Backlog written to {backlog_path}")

if __name__ == "__main__":
    main()
