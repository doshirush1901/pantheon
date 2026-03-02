#!/bin/bash
# Mailbox ingestion daemon — runs independently of terminal sessions.
# Resumes from last checkpoint. Logs to data/logs/mailbox_ingestion.log.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

LOG_DIR="$PROJECT_ROOT/data/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/mailbox_ingestion.log"

cd "$PROJECT_ROOT"

# Use the project's Python (venv if available, else system)
if [ -f "$PROJECT_ROOT/.venv/bin/python3" ]; then
    PYTHON="$PROJECT_ROOT/.venv/bin/python3"
else
    PYTHON="$(which python3)"
fi

echo "$(date '+%Y-%m-%d %H:%M:%S') Starting mailbox ingestion (resume mode)..." >> "$LOG_FILE"

$PYTHON scripts/ingest_mailbox.py --contacts --limit 50 --resume >> "$LOG_FILE" 2>&1

echo "$(date '+%Y-%m-%d %H:%M:%S') Mailbox ingestion finished with exit code $?" >> "$LOG_FILE"
