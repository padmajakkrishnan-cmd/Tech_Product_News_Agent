#!/bin/bash
# setup_macos_schedule.sh
# Sets up a macOS launchd job to run the Daily AI News Agent every day.

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLIST_NAME="com.dailyainews.agent"
PLIST_PATH="$HOME/Library/LaunchAgents/${PLIST_NAME}.plist"

# Detect Python path
PYTHON_PATH=$(which python3)
if [ -z "$PYTHON_PATH" ]; then
    echo "Error: python3 not found. Please install Python 3 first."
    exit 1
fi

# Read SEND_TIME from .env (default 08:00)
if [ -f "$SCRIPT_DIR/.env" ]; then
    SEND_TIME=$(grep -E "^SEND_TIME=" "$SCRIPT_DIR/.env" | cut -d= -f2 | tr -d ' ')
fi
SEND_TIME="${SEND_TIME:-08:00}"
HOUR=$(echo "$SEND_TIME" | cut -d: -f1 | sed 's/^0//')
MINUTE=$(echo "$SEND_TIME" | cut -d: -f2 | sed 's/^0//')

echo "Setting up daily schedule at ${HOUR}:${MINUTE}..."

# Create the plist
mkdir -p "$HOME/Library/LaunchAgents"
cat > "$PLIST_PATH" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>${PLIST_NAME}</string>
    <key>ProgramArguments</key>
    <array>
        <string>${PYTHON_PATH}</string>
        <string>${SCRIPT_DIR}/main.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>${SCRIPT_DIR}</string>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>${HOUR}</integer>
        <key>Minute</key>
        <integer>${MINUTE}</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>${SCRIPT_DIR}/logs/agent.log</string>
    <key>StandardErrorPath</key>
    <string>${SCRIPT_DIR}/logs/agent.log</string>
    <key>RunAtLoad</key>
    <false/>
</dict>
</plist>
EOF

# Create logs directory
mkdir -p "$SCRIPT_DIR/logs"

# Unload if already loaded, then load
launchctl unload "$PLIST_PATH" 2>/dev/null || true
launchctl load "$PLIST_PATH"

echo ""
echo "✓ Daily AI News Agent scheduled!"
echo "  Time: Every day at ${SEND_TIME}"
echo "  Logs: ${SCRIPT_DIR}/logs/agent.log"
echo ""
echo "Useful commands:"
echo "  Check status:  launchctl list | grep ${PLIST_NAME}"
echo "  Run now:       launchctl start ${PLIST_NAME}"
echo "  Stop schedule: launchctl unload ${PLIST_PATH}"
echo "  View logs:     tail -f ${SCRIPT_DIR}/logs/agent.log"
