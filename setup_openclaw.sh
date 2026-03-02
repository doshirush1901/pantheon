#!/bin/bash
# Setup script to configure OpenClaw to use the IRA project as its workspace.
# Run this ONCE after installing OpenClaw globally.

IRA_ROOT="$(cd "$(dirname "$0")" && pwd)"

echo "Configuring OpenClaw to use IRA workspace at: $IRA_ROOT"

# Ensure OpenClaw config directory exists
mkdir -p ~/.openclaw

# Create or update openclaw.json to point workspace to IRA root
if [ -f ~/.openclaw/openclaw.json ]; then
    echo "WARNING: ~/.openclaw/openclaw.json already exists."
    echo "Please manually add the following to your config:"
    echo ""
    echo '  "agent": { "workspace": "'$IRA_ROOT'" }'
    echo ""
else
    cat > ~/.openclaw/openclaw.json << EOF
{
  "agent": {
    "workspace": "$IRA_ROOT",
    "skipBootstrap": true
  }
}
EOF
    echo "Created ~/.openclaw/openclaw.json"
fi

echo ""
echo "Next steps:"
echo "  1. Install OpenClaw: npm install -g openclaw@latest"
echo "  2. Run onboarding:   openclaw onboard --install-daemon"
echo "  3. Start gateway:    openclaw gateway --port 18789 --verbose --log-level debug"
echo "  4. Test:             openclaw agent --message 'What machines do you sell?'"
echo ""
echo "For multi-agent pipeline visibility, use --log-level debug"
echo "This will show structured logs from ChiefOfStaff, Researcher, Writer, FactChecker, and Reflector agents."
