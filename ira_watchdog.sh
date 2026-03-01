#!/bin/bash
# Ira Watchdog - ensures Ira stays running
# Add to crontab: */5 * * * * /Users/rushabhdoshi/Desktop/Ira/ira_watchdog.sh

PIDFILE="/Users/rushabhdoshi/Desktop/Ira/logs/telegram_gateway.pid"
LOGFILE="/Users/rushabhdoshi/Desktop/Ira/logs/watchdog.log"

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') $1" >> "$LOGFILE"
}

# Check if process is running
is_running() {
    if [ -f "$PIDFILE" ]; then
        pid=$(cat "$PIDFILE")
        if ps -p "$pid" > /dev/null 2>&1; then
            return 0
        fi
    fi
    # Fallback: PID file may not exist; check process by name
    pgrep -f "telegram_gateway.py --loop" >/dev/null 2>&1 && return 0
    pgrep -f "openclaw.*gateway" >/dev/null 2>&1 && return 0
    return 1
}

# Main
if is_running; then
    # Ira is running, all good
    exit 0
else
    log "Ira not running - restarting..."
    cd /Users/rushabhdoshi/Desktop/Ira
    ./start_ira.sh > /dev/null 2>&1
    sleep 5
    if is_running; then
        log "Ira restarted successfully"
    else
        log "ERROR: Failed to restart Ira"
    fi
fi
