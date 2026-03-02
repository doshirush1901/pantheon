#!/bin/bash
# Ira Telegram Gateway Runner - for launchd
cd /Users/rushabhdoshi/Desktop/Ira

# Load environment from .env
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Ensure Python can find modules
export PYTHONPATH="/Users/rushabhdoshi/Desktop/Ira:$PYTHONPATH"

# Run the gateway
exec /opt/homebrew/bin/python3 \
    /Users/rushabhdoshi/Desktop/Ira/_archive/pre_openclaw_legacy/telegram_gateway.py \
    --loop --interval 5
