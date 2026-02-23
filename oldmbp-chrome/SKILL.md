---
name: oldmbp-chrome
description: Manage Chrome remote debugging on oldmbp.lnet and use browser-tools with its IP address. Chrome runs on port 9222 via launchctl and is exposed via socat.
---

# Old MacBook Pro Chrome Remote Debugging

Chrome remote debugging instance running on `oldmbp.lnet` (192.168.2.4) with CDP exposed on port 9222.

## Chrome Instance Details

- **Host**: oldmbp.lnet (192.168.2.4)
- **Port**: 9222
- **Managed by**: launchctl (`com.user.chrome-remote`)
- **Profile**: ~/Desktop/chrome-profile
- **Access via**: socat forwarding

## Start Chrome

Chrome is managed via launchctl. To trigger a start:

```bash
ssh oldmbp.lnet 'touch /tmp/start-chrome'
```

This signals the launchctl service to start Chrome with these flags:
- `--remote-debugging-port=9222`
- `--user-data-dir="$HOME/Desktop/chrome-profile"`

## Stop Chrome

```bash
ssh oldmbp.lnet 'pkill -9 "Google Chrome"'
```

Or stop the launchctl service:
```bash
ssh oldmbp.lnet 'launchctl unload ~/Library/LaunchAgents/com.user.chrome-remote.plist'
```

## Check Status

```bash
# Check if Chrome is running
ssh oldmbp.lnet 'pgrep -f "Google Chrome" | head -1'

# Check CDP endpoint
curl -s http://192.168.2.4:9222/json/version
```

## Browser Tools for oldmbp.lnet

Modified versions of browser-tools that connect directly to oldmbp.lnet's Chrome instance (192.168.2.4:9222).

### Setup

```bash
cd ~/.pi/agent/skills/my-skills/oldmbp-chrome
npm install puppeteer-core @mozilla/readability jsdom turndown turndown-plugin-gfm
```

### Available Commands

All scripts connect to `http://192.168.2.4:9222` automatically.

#### Navigate
```bash
~/.pi/agent/skills/my-skills/oldmbp-chrome/oldmbp-nav.js https://example.com
~/.pi/agent/skills/my-skills/oldmbp-chrome/oldmbp-nav.js https://example.com --new
```

#### Execute JavaScript
```bash
~/.pi/agent/skills/my-skills/oldmbp-chrome/oldmbp-eval.js 'document.title'
~/.pi/agent/skills/my-skills/oldmbp-chrome/oldmbp-eval.js 'document.querySelectorAll("a").length'
```

#### Screenshot
```bash
~/.pi/agent/skills/my-skills/oldmbp-chrome/oldmbp-screenshot.js
# Returns: /tmp/screenshot-2024-... .png
```

#### Pick Elements
```bash
~/.pi/agent/skills/my-skills/oldmbp-chrome/oldmbp-pick.js "Click the submit button"
```

#### Cookies
```bash
~/.pi/agent/skills/my-skills/oldmbp-chrome/oldmbp-cookies.js
```

#### Extract Content
```bash
~/.pi/agent/skills/my-skills/oldmbp-chrome/oldmbp-content.js https://example.com
```

### Get the WebSocket URL

```bash
# Get the CDP WebSocket URL
~/.pi/agent/skills/my-skills/oldmbp-chrome/oldmbp-browser.sh ws
# Output: ws://192.168.2.4:9222/devtools/browser/...
```

## CDP Endpoints

| Endpoint | URL |
|----------|-----|
| Version | http://192.168.2.4:9222/json/version |
| List tabs | http://192.168.2.4:9222/json/list |
| New tab | http://192.168.2.4:9222/json/new |

## Quick Helper Script

A convenience script is included for common operations:

```bash
# Check status
~/.pi/agent/skills/my-skills/oldmbp-chrome/oldmbp-browser.sh status

# Get resolved IP
~/.pi/agent/skills/my-skills/oldmbp-chrome/oldmbp-browser.sh ip

# Start/stop Chrome
~/.pi/agent/skills/my-skills/oldmbp-chrome/oldmbp-browser.sh start
~/.pi/agent/skills/my-skills/oldmbp-chrome/oldmbp-browser.sh stop

# Get WebSocket URL for CDP connection
~/.pi/agent/skills/my-skills/oldmbp-chrome/oldmbp-browser.sh ws
```

## Troubleshooting

### "Host header is specified and is not an IP address or localhost"

Chrome rejects requests with non-localhost Host headers. Solutions:

```bash
# Use IP address
curl -s http://192.168.2.4:9222/json/version

# Or use empty Host header
curl -s -H "Host:" http://oldmbp.lnet:9222/json/version
```

### Chrome not responding

1. Check if Chrome process exists: `ssh oldmbp.lnet 'pgrep Chrome'`
2. Check launchctl service: `ssh oldmbp.lnet 'launchctl list | grep chrome'`
3. View logs: `ssh oldmbp.lnet 'cat /tmp/chrome-remote.log'`
4. Trigger restart: `ssh oldmbp.lnet 'pkill Chrome; sleep 2; touch /tmp/start-chrome'`

## Configuration Files

On oldmbp.lnet:
- LaunchAgent: `~/Library/LaunchAgents/com.user.chrome-remote.plist`
- Chrome profile: `~/Desktop/chrome-profile`
- Logs: `/tmp/chrome-remote.log`, `/tmp/chrome-remote.error`
