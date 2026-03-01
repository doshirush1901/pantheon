#!/bin/bash
# Dream Progress Monitor - macOS compatible

LOG_FILE="$HOME/Desktop/Ira/logs/dream_$(date '+%Y-%m-%d').log"
TOTAL=318

while true; do
    if [ -f "$LOG_FILE" ]; then
        CURRENT=$(grep -o '\[[0-9]*/318\]' "$LOG_FILE" | tail -1 | sed 's/\[//;s/\/318\]//')
        CURRENT=${CURRENT:-0}
        PCT=$((CURRENT * 100 / TOTAL))
        FILLED=$((PCT / 2))
        EMPTY=$((50 - FILLED))
        BAR=$(printf "%${FILLED}s" | tr ' ' '#')
        BAR+=$(printf "%${EMPTY}s" | tr ' ' '-')
        LAST_FILE=$(grep '\[.*\/318\]' "$LOG_FILE" | tail -1 | sed 's/.*\] //')
        FACTS=$(grep 'Facts:' "$LOG_FILE" | tail -1 | sed 's/.*Facts: //' | cut -d',' -f1)

        clear
        echo ""
        echo "  ============== IRA DREAM PROGRESS =============="
        echo ""
        printf "  [%s] %3d%%\n" "$BAR" "$PCT"
        echo ""
        printf "  Documents: %3d / %3d\n" "$CURRENT" "$TOTAL"
        printf "  Latest facts extracted: %s\n" "${FACTS:-0}"
        echo ""
        echo "  Current: ${LAST_FILE:0:50}"
        echo ""
        echo "  ================================================"
        echo ""
        echo "  Press Ctrl+C to exit"
        
        if grep -q "DREAM CYCLE COMPLETE" "$LOG_FILE" 2>/dev/null; then
            echo ""
            echo "  Done!"
            exit 0
        fi
    else
        echo "Waiting for dream to start..."
    fi
    sleep 5
done
