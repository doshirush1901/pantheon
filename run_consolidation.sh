#!/bin/bash
#
# IRA Memory Consolidation - Wrapper Script
# ==========================================
#
# This script runs memory consolidation with proper environment setup.
#
# Usage:
#   ./run_consolidation.sh                    # Normal run
#   ./run_consolidation.sh --require-approval # Queue patterns for review
#   ./run_consolidation.sh --dry-run          # Preview without storing
#   ./run_consolidation.sh --export-excel     # Export knowledge to Excel
#
# For cron scheduling, add to crontab:
#   crontab -e
#   # Run at 3 AM daily:
#   0 3 * * * /Users/rushabhdoshi/Desktop/Ira/run_consolidation.sh >> /Users/rushabhdoshi/Desktop/Ira/logs/consolidation_cron.log 2>&1
#
# For launchd (macOS):
#   cp com.ira.memory-consolidation.plist ~/Library/LaunchAgents/
#   launchctl load ~/Library/LaunchAgents/com.ira.memory-consolidation.plist
#

set -e

# Configuration
IRA_DIR="/Users/rushabhdoshi/Desktop/Ira"
PYTHON="/usr/bin/python3"
CONSOLIDATOR="$IRA_DIR/openclaw/agents/ira/src/memory/memory_consolidator.py"
LOG_DIR="$IRA_DIR/logs"

# Ensure log directory exists
mkdir -p "$LOG_DIR"

# Change to IRA directory
cd "$IRA_DIR"

# Load environment variables from .env if it exists
if [ -f "$IRA_DIR/.env" ]; then
    export $(grep -v '^#' "$IRA_DIR/.env" | xargs)
fi

# Set PYTHONPATH
export PYTHONPATH="$IRA_DIR:$PYTHONPATH"

# Log start
echo ""
echo "========================================"
echo "IRA Memory Consolidation"
echo "Started: $(date)"
echo "========================================"

# Run consolidation with passed arguments (or defaults)
if [ $# -eq 0 ]; then
    # Default: run with require-approval for safety
    $PYTHON "$CONSOLIDATOR" --days 7 --require-approval
else
    # Pass through any arguments
    $PYTHON "$CONSOLIDATOR" "$@"
fi

# Log completion
echo ""
echo "Completed: $(date)"
echo "========================================"
