#!/bin/bash
# oldmbp-browser.sh - Run browser-tools against oldmbp.lnet Chrome instance

set -e

OLDMBP_HOST="oldmbp.lnet"
OLDMBP_IP=$(dig +short $OLDMBP_HOST | head -1)

if [ -z "$OLDMBP_IP" ]; then
    echo "Error: Could not resolve $OLDMBP_HOST"
    exit 1
fi

echo "Using Chrome at $OLDMBP_HOST ($OLDMBP_IP:9222)"

# Base directory for browser-tools
BROWSER_TOOLS_DIR="$HOME/.pi/agent/skills/pi-skills/browser-tools"

# Function to get browser WebSocket URL
get_ws_url() {
    curl -s "http://$OLDMBP_IP:9222/json/version" | grep -o '"webSocketDebuggerUrl": "[^"]*"' | cut -d'"' -f4
}

case "${1:-}" in
    start)
        echo "Starting Chrome on oldmbp.lnet..."
        ssh $OLDMBP_HOST 'touch /tmp/start-chrome'
        sleep 3
        echo "Chrome should be running. Testing..."
        curl -s "http://$OLDMBP_IP:9222/json/version" | jq -r '.Browser' 2>/dev/null || echo "Chrome not responding yet"
        ;;
    stop)
        echo "Stopping Chrome on oldmbp.lnet..."
        ssh $OLDMBP_HOST 'pkill -9 "Google Chrome" 2>/dev/null || true'
        echo "Chrome stopped"
        ;;
    status)
        echo "Checking Chrome status..."
        if curl -s "http://$OLDMBP_IP:9222/json/version" > /dev/null 2>&1; then
            echo "✅ Chrome is running"
            VERSION=$(curl -s "http://$OLDMBP_IP:9222/json/version")
            BROWSER=$(echo "$VERSION" | jq -r '.Browser')
            PROTOCOL=$(echo "$VERSION" | jq -r '.["Protocol-Version"]')
            echo "Browser: $BROWSER, Protocol: $PROTOCOL"
            echo "WebSocket: $(get_ws_url)"
        else
            echo "❌ Chrome not responding"
            echo "Launchctl status:"
            ssh $OLDMBP_HOST 'launchctl list | grep chrome' 2>/dev/null || echo "  Service not loaded"
        fi
        ;;
    ws|websocket)
        echo "WebSocket URL: $(get_ws_url)"
        ;;
    ip)
        echo "$OLDMBP_IP"
        ;;
    *)
        cat << 'EOF'
Usage: oldmbp-browser.sh <command> [args]

Commands:
  start              Start Chrome on oldmbp.lnet
  stop               Stop Chrome on oldmbp.lnet
  status             Check Chrome status and CDP endpoint
  ws                 Show WebSocket URL for CDP connection
  ip                 Show resolved IP address

EOF
        ;;
esac
