#!/bin/bash
# Morning cycle: inhale - gather, assess, prepare
# Run via cron at 7:00 AM IST: 0 7 * * * /path/to/scripts/run_morning_cycle.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

# Load environment
if [ -f .env ]; then
    set -a
    source .env
    set +a
fi

echo "[$(date)] Starting morning cycle..."

python3 -m openclaw.agents.ira.src.holistic.daily_rhythm --morning 2>&1 | tee -a logs/morning_cycle.log

echo "[$(date)] Morning cycle complete"
