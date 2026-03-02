#!/bin/bash
# Install Ira's launchd schedules (macOS)
#
# Dream mode: 2:00 AM nightly
# Vital signs: 7:30 AM daily (sends Telegram report)
#
# Usage:
#   bash scripts/install_schedules.sh          # Install
#   bash scripts/install_schedules.sh remove   # Uninstall

IRA_DIR="/Users/rushabhdoshi/Desktop/Ira"
LAUNCH_DIR="$HOME/Library/LaunchAgents"

DREAM_PLIST="com.machinecraft.ira-dream.plist"
VITALS_PLIST="com.machinecraft.ira-vitals.plist"
SCHEDULER_PLIST="com.machinecraft.ira-scheduler.plist"

mkdir -p "$LAUNCH_DIR"
mkdir -p "$IRA_DIR/logs"

if [ "$1" = "remove" ]; then
    echo "Removing Ira schedules..."
    launchctl unload "$LAUNCH_DIR/$DREAM_PLIST" 2>/dev/null
    launchctl unload "$LAUNCH_DIR/$VITALS_PLIST" 2>/dev/null
    launchctl unload "$LAUNCH_DIR/$SCHEDULER_PLIST" 2>/dev/null
    rm -f "$LAUNCH_DIR/$DREAM_PLIST"
    rm -f "$LAUNCH_DIR/$VITALS_PLIST"
    rm -f "$LAUNCH_DIR/$SCHEDULER_PLIST"
    echo "Done. Schedules removed."
    exit 0
fi

echo "Installing Ira schedules..."

cp "$IRA_DIR/scripts/$DREAM_PLIST" "$LAUNCH_DIR/$DREAM_PLIST"
cp "$IRA_DIR/scripts/$VITALS_PLIST" "$LAUNCH_DIR/$VITALS_PLIST"
cp "$IRA_DIR/scripts/$SCHEDULER_PLIST" "$LAUNCH_DIR/$SCHEDULER_PLIST"

launchctl unload "$LAUNCH_DIR/$DREAM_PLIST" 2>/dev/null
launchctl load "$LAUNCH_DIR/$DREAM_PLIST"
echo "  ✅ Dream mode: 2:00 AM nightly"

launchctl unload "$LAUNCH_DIR/$VITALS_PLIST" 2>/dev/null
launchctl load "$LAUNCH_DIR/$VITALS_PLIST"
echo "  ✅ Vital signs: 7:30 AM daily (Telegram)"

launchctl unload "$LAUNCH_DIR/$SCHEDULER_PLIST" 2>/dev/null
launchctl load "$LAUNCH_DIR/$SCHEDULER_PLIST"
echo "  ✅ Sales scheduler: 9:00 AM daily (outreach + drip + follow-up)"

echo ""
echo "Verify with:"
echo "  launchctl list | grep machinecraft"
echo ""
echo "To remove:"
echo "  bash scripts/install_schedules.sh remove"
