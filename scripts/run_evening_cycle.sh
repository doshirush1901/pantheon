#!/bin/bash
# Evening cycle: exhale - clean, consolidate, prepare for dream
# Run via cron at 11:00 PM IST: 0 23 * * * /path/to/scripts/run_evening_cycle.sh
# Should run BEFORE dream mode (run_nightly_dream.sh)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

# Load environment
if [ -f .env ]; then
    set -a
    source .env
    set +a
fi

echo "[$(date)] Starting evening cycle..."

python3 -m openclaw.agents.ira.src.holistic.daily_rhythm --evening 2>&1 | tee -a logs/evening_cycle.log

echo "[$(date)] Evening cycle complete"
echo "[$(date)] Dream mode should run next (via run_nightly_dream.sh)"
