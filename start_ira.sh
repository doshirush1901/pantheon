#!/bin/bash
# =============================================================================
# Ira Startup Script
# =============================================================================
# Run this after PC restart to start all Ira services
#
# Usage:
#   ./start_ira.sh          # Start all services (new orchestrator)
#   ./start_ira.sh status   # Check service status
#   ./start_ira.sh stop     # Stop all services
#   ./start_ira.sh cli      # Interactive CLI mode
#   ./start_ira.sh legacy   # Use legacy telegram_gateway.py
# =============================================================================

set -e
cd "$(dirname "$0")"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}"
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║                    🤖 IRA STARTUP                         ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# -----------------------------------------------------------------------------
# Helper Functions
# -----------------------------------------------------------------------------

check_postgres() {
    pg_isready -q 2>/dev/null && return 0 || return 1
}

check_qdrant() {
    curl -s http://localhost:6333/health >/dev/null 2>&1 && return 0 || return 1
}

check_redis() {
    redis-cli ping >/dev/null 2>&1 && return 0 || return 1
}

check_telegram_gateway() {
    pgrep -f "telegram_gateway.py --loop" >/dev/null 2>&1 && return 0 || return 1
}

check_orchestrator() {
    pgrep -f "orchestrator.py" >/dev/null 2>&1 && return 0 || return 1
}

check_ira_agent() {
    # Check if either orchestrator or telegram gateway is running
    check_orchestrator || check_telegram_gateway
}

check_email_handler() {
    pgrep -f "email_conversation_loop.py" >/dev/null 2>&1 && return 0 || return 1
}

# Legacy alias
check_gmail_push() {
    check_email_handler
}

status_icon() {
    if $1; then
        echo -e "${GREEN}✓${NC}"
    else
        echo -e "${RED}✗${NC}"
    fi
}

# -----------------------------------------------------------------------------
# Status Command
# -----------------------------------------------------------------------------

if [ "$1" = "status" ]; then
    echo -e "\n${YELLOW}Service Status:${NC}\n"
    
    echo -e "  PostgreSQL:       $(status_icon check_postgres)"
    echo -e "  Qdrant:           $(status_icon check_qdrant)"
    echo -e "  Redis:            $(status_icon check_redis) (optional)"
    echo -e "  Orchestrator:     $(status_icon check_orchestrator)"
    echo -e "  Telegram Gateway: $(status_icon check_telegram_gateway)"
    echo -e "  Email Handler:    $(status_icon check_email_handler) (optional)"
    echo ""
    
    # Show agent status if running
    if check_ira_agent; then
        echo -e "${YELLOW}Agent Status:${NC}"
        python3 orchestrator.py --status 2>/dev/null | head -30
    fi
    exit 0
fi

# -----------------------------------------------------------------------------
# CLI Command
# -----------------------------------------------------------------------------

if [ "$1" = "cli" ]; then
    echo -e "${YELLOW}Starting Interactive CLI...${NC}\n"
    python3 orchestrator.py --cli
    exit 0
fi

# -----------------------------------------------------------------------------
# Stop Command
# -----------------------------------------------------------------------------

if [ "$1" = "stop" ]; then
    echo -e "${YELLOW}Stopping Ira services...${NC}\n"
    
    # Stop Orchestrator
    pkill -f "orchestrator.py" 2>/dev/null && echo "  Stopped Orchestrator" || echo "  Orchestrator not running"
    
    # Stop Telegram Gateway
    pkill -f "telegram_gateway.py --loop" 2>/dev/null && echo "  Stopped Telegram Gateway" || echo "  Telegram Gateway not running"
    
    # Stop Email Handler
    pkill -f "email_conversation_loop.py" 2>/dev/null && echo "  Stopped Email Handler" || echo "  Email Handler not running"
    
    # Stop Qdrant (if running in Docker)
    docker stop qdrant 2>/dev/null && echo "  Stopped Qdrant" || echo "  Qdrant container not running"
    
    echo -e "\n${GREEN}Done!${NC}"
    exit 0
fi

# -----------------------------------------------------------------------------
# Start Services
# -----------------------------------------------------------------------------

echo -e "${YELLOW}Starting services...${NC}\n"

# 1. PostgreSQL
echo -n "  [1/5] PostgreSQL: "
if check_postgres; then
    echo -e "${GREEN}Already running${NC}"
else
    # Try to start via brew
    if command -v brew &> /dev/null; then
        brew services start postgresql@14 2>/dev/null || brew services start postgresql 2>/dev/null || true
        sleep 2
    fi
    
    if check_postgres; then
        echo -e "${GREEN}Started${NC}"
    else
        echo -e "${RED}Not running - please start Postgres.app or run: brew services start postgresql${NC}"
    fi
fi

# 2. Qdrant
echo -n "  [2/5] Qdrant: "
if check_qdrant; then
    echo -e "${GREEN}Already running${NC}"
else
    # Start Qdrant in Docker
    docker run -d --name qdrant -p 6333:6333 -v ~/qdrant_data:/qdrant/storage qdrant/qdrant 2>/dev/null || \
    docker start qdrant 2>/dev/null || true
    
    sleep 3
    
    if check_qdrant; then
        echo -e "${GREEN}Started${NC}"
    else
        echo -e "${RED}Failed to start - run manually: docker run -p 6333:6333 qdrant/qdrant${NC}"
    fi
fi

# 3. Redis (Optional)
echo -n "  [3/5] Redis: "
if check_redis; then
    echo -e "${GREEN}Already running${NC}"
else
    # Try to start via brew
    if command -v brew &> /dev/null; then
        brew services start redis 2>/dev/null || true
        sleep 1
    fi
    
    if check_redis; then
        echo -e "${GREEN}Started${NC}"
    else
        echo -e "${YELLOW}Not available (optional - caching disabled)${NC}"
    fi
fi

# 4. Ira Agent (Main Interface)
echo -n "  [4/5] Ira Agent: "

if [ "$1" = "legacy" ]; then
    # Legacy mode: use telegram_gateway.py directly
    if check_telegram_gateway; then
        echo -e "${GREEN}Already running (legacy mode)${NC}"
    else
        nohup python3 _archive/pre_openclaw_legacy/telegram_gateway.py --loop > logs/telegram_gateway.log 2>&1 &
        sleep 2
        
        if check_telegram_gateway; then
            echo -e "${GREEN}Started (legacy mode)${NC}"
        else
            echo -e "${RED}Failed - check logs/telegram_gateway.log${NC}"
        fi
    fi
else
    # New mode: use unified orchestrator
    if check_orchestrator; then
        echo -e "${GREEN}Already running (orchestrator)${NC}"
    elif check_telegram_gateway; then
        echo -e "${GREEN}Already running (legacy mode)${NC}"
    else
        nohup python3 orchestrator.py --telegram > logs/orchestrator.log 2>&1 &
        sleep 3
        
        if check_orchestrator; then
            echo -e "${GREEN}Started (orchestrator)${NC}"
        else
            # Fallback to legacy
            echo -e "${YELLOW}Orchestrator failed, trying legacy...${NC}"
            nohup python3 _archive/pre_openclaw_legacy/telegram_gateway.py --loop > logs/telegram_gateway.log 2>&1 &
            sleep 2
            
            if check_telegram_gateway; then
                echo -e "${GREEN}Started (legacy fallback)${NC}"
            else
                echo -e "${RED}Failed - check logs/orchestrator.log${NC}"
            fi
        fi
    fi
fi

# 5. Email Handler (Optional - for email processing)
echo -n "  [5/5] Email Handler: "
if check_gmail_push; then
    echo -e "${GREEN}Already running${NC}"
else
    # Check if email handler exists (new location)
    EMAIL_HANDLER="scripts/email_openclaw_bridge.py"
    if [ -f "$EMAIL_HANDLER" ]; then
        nohup python3 "$EMAIL_HANDLER" --loop > logs/email_handler.log 2>&1 &
        sleep 2
        
        if check_gmail_push; then
            echo -e "${GREEN}Started${NC}"
        else
            echo -e "${YELLOW}Not started (check logs/email_handler.log)${NC}"
        fi
    else
        echo -e "${YELLOW}Not configured${NC}"
    fi
fi

# -----------------------------------------------------------------------------
# Summary
# -----------------------------------------------------------------------------

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo ""

# Final status check
ALL_OK=true

if ! check_postgres; then
    echo -e "${RED}⚠️  PostgreSQL not running - memories won't work${NC}"
    ALL_OK=false
fi

if ! check_qdrant; then
    echo -e "${RED}⚠️  Qdrant not running - knowledge search won't work${NC}"
    ALL_OK=false
fi

if ! check_ira_agent; then
    echo -e "${RED}⚠️  Ira Agent not running - can't chat with Ira${NC}"
    ALL_OK=false
fi

if $ALL_OK; then
    echo -e "${GREEN}✅ Ira is ready!${NC}"
    echo ""
    echo "   Test in Telegram:"
    echo "     /personality     - See personality traits"
    echo "     /boost charm     - Increase charm"
    echo "     /help            - All commands"
    echo ""
    echo "   CLI Mode:"
    echo "     ./start_ira.sh cli"
fi

echo ""
if check_orchestrator; then
    echo -e "   Logs: ${YELLOW}tail -f logs/orchestrator.log${NC}"
else
    echo -e "   Logs: ${YELLOW}tail -f logs/telegram_gateway.log${NC}"
fi
echo -e "   Stop: ${YELLOW}./start_ira.sh stop${NC}"
echo -e "   Status: ${YELLOW}./start_ira.sh status${NC}"
echo ""
