#!/bin/bash
# Heartbeat: record that Ira is alive
# Run via cron every 5 minutes: */5 * * * * /path/to/scripts/run_heartbeat.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

if [ -f .env ]; then
    set -a
    source .env
    set +a
fi

python3 -m openclaw.agents.ira.src.holistic.daily_rhythm --heartbeat 2>/dev/null
