#!/bin/bash
#
# IRA OPENCLAW STARTUP SCRIPT
# ===========================
# Starts all IRA components on OpenClaw framework
#
# Usage:
#   ./start_ira_openclaw.sh          # Start all components
#   ./start_ira_openclaw.sh gateway  # Start only gateway
#   ./start_ira_openclaw.sh email    # Start only email bridge
#   ./start_ira_openclaw.sh status   # Check status
#   ./start_ira_openclaw.sh stop     # Stop all components
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Paths
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"
LOG_DIR="$PROJECT_ROOT/logs"
VENV_DIR="$PROJECT_ROOT/.venv"

# Config
GATEWAY_PORT=18789
EMAIL_POLL_INTERVAL=60
AGENT_ID="users-rushabhdoshi-desktop-ira-openclaw-agents-ira"

# Ensure log directory exists
mkdir -p "$LOG_DIR"

# Load environment
if [ -f "$PROJECT_ROOT/.env" ]; then
    export $(grep -v '^#' "$PROJECT_ROOT/.env" | xargs)
fi

# Activate virtual environment if exists
activate_venv() {
    if [ -d "$VENV_DIR" ]; then
        source "$VENV_DIR/bin/activate"
        echo -e "${GREEN}✓${NC} Virtual environment activated"
    fi
}

# Check if gateway is running
is_gateway_running() {
    pgrep -f "openclaw.*gateway" > /dev/null 2>&1
}

# Check if email bridge is running
is_email_running() {
    pgrep -f "email_openclaw_bridge" > /dev/null 2>&1
}

# Start OpenClaw Gateway
start_gateway() {
    echo -e "${BLUE}Starting OpenClaw Gateway...${NC}"
    
    if is_gateway_running; then
        echo -e "${YELLOW}⚠ Gateway already running${NC}"
        return 0
    fi
    
    # Start gateway in background
    nohup openclaw gateway --port $GATEWAY_PORT > "$LOG_DIR/openclaw_gateway.log" 2>&1 &
    
    # Wait for gateway to start
    sleep 3
    
    if is_gateway_running; then
        echo -e "${GREEN}✓${NC} Gateway started on port $GATEWAY_PORT"
        echo -e "   Log: $LOG_DIR/openclaw_gateway.log"
    else
        echo -e "${RED}✗${NC} Failed to start gateway"
        echo -e "   Check: $LOG_DIR/openclaw_gateway.log"
        return 1
    fi
}

# Start Email Bridge
start_email() {
    echo -e "${BLUE}Starting Email Bridge...${NC}"
    
    if is_email_running; then
        echo -e "${YELLOW}⚠ Email bridge already running${NC}"
        return 0
    fi
    
    activate_venv
    
    # Start email bridge in background
    nohup python3 "$PROJECT_ROOT/scripts/email_openclaw_bridge.py" \
        --loop \
        --interval $EMAIL_POLL_INTERVAL \
        > "$LOG_DIR/email_bridge.log" 2>&1 &
    
    sleep 2
    
    if is_email_running; then
        echo -e "${GREEN}✓${NC} Email bridge started (polling every ${EMAIL_POLL_INTERVAL}s)"
        echo -e "   Log: $LOG_DIR/email_bridge.log"
    else
        echo -e "${RED}✗${NC} Failed to start email bridge"
        echo -e "   Check: $LOG_DIR/email_bridge.log"
        return 1
    fi
}

# Stop all components
stop_all() {
    echo -e "${BLUE}Stopping IRA components...${NC}"
    
    # Stop gateway
    if is_gateway_running; then
        openclaw gateway stop 2>/dev/null || pkill -f "openclaw.*gateway" 2>/dev/null || true
        echo -e "${GREEN}✓${NC} Gateway stopped"
    else
        echo -e "${YELLOW}⚠ Gateway not running${NC}"
    fi
    
    # Stop email bridge
    if is_email_running; then
        pkill -f "email_openclaw_bridge" 2>/dev/null || true
        echo -e "${GREEN}✓${NC} Email bridge stopped"
    else
        echo -e "${YELLOW}⚠ Email bridge not running${NC}"
    fi
    
    echo -e "${GREEN}All components stopped${NC}"
}

# Show status
show_status() {
    echo -e "${BLUE}═══════════════════════════════════════${NC}"
    echo -e "${BLUE}       IRA OpenClaw Status${NC}"
    echo -e "${BLUE}═══════════════════════════════════════${NC}"
    echo ""
    
    # Gateway status
    if is_gateway_running; then
        echo -e "  OpenClaw Gateway:  ${GREEN}● Running${NC} (port $GATEWAY_PORT)"
    else
        echo -e "  OpenClaw Gateway:  ${RED}○ Stopped${NC}"
    fi
    
    # Telegram status
    echo -e "  Telegram Channel:  ${GREEN}● Enabled${NC} (via gateway)"
    
    # Email status
    if is_email_running; then
        echo -e "  Email Bridge:      ${GREEN}● Running${NC} (poll: ${EMAIL_POLL_INTERVAL}s)"
    else
        echo -e "  Email Bridge:      ${RED}○ Stopped${NC}"
    fi
    
    echo ""
    echo -e "${BLUE}═══════════════════════════════════════${NC}"
    echo ""
    echo -e "  Agent ID: ${YELLOW}$AGENT_ID${NC}"
    echo ""
    echo -e "  Test CLI:"
    echo -e "    ${YELLOW}openclaw agent --agent $AGENT_ID --message \"What machines do you sell?\"${NC}"
    echo ""
    echo -e "  Logs:"
    echo -e "    Gateway: $LOG_DIR/openclaw_gateway.log"
    echo -e "    Email:   $LOG_DIR/email_bridge.log"
    echo ""
}

# Start all components
start_all() {
    echo ""
    echo -e "${BLUE}╔═══════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║     Starting IRA on OpenClaw          ║${NC}"
    echo -e "${BLUE}╚═══════════════════════════════════════╝${NC}"
    echo ""
    
    start_gateway
    echo ""
    
    # Wait for gateway to be fully ready
    sleep 2
    
    start_email
    echo ""
    
    echo -e "${GREEN}═══════════════════════════════════════${NC}"
    echo -e "${GREEN}       IRA is ready!${NC}"
    echo -e "${GREEN}═══════════════════════════════════════${NC}"
    echo ""
    echo -e "  ${YELLOW}Telegram:${NC} Message your bot"
    echo -e "  ${YELLOW}Email:${NC}    Send to ira@machinecraft.org"
    echo -e "  ${YELLOW}CLI:${NC}      openclaw agent --agent $AGENT_ID --message \"...\""
    echo ""
}

# Main
case "${1:-all}" in
    gateway)
        start_gateway
        ;;
    email)
        activate_venv
        start_email
        ;;
    stop)
        stop_all
        ;;
    status)
        show_status
        ;;
    all|start)
        start_all
        show_status
        ;;
    *)
        echo "Usage: $0 {all|gateway|email|status|stop}"
        echo ""
        echo "Commands:"
        echo "  all      Start all components (default)"
        echo "  gateway  Start only OpenClaw gateway"
        echo "  email    Start only email bridge"
        echo "  status   Show status of all components"
        echo "  stop     Stop all components"
        exit 1
        ;;
esac
