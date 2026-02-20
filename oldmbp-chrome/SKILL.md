---
name: oldmbp-chrome
description: Access and control Chrome browser running on oldmbp.lnet via SSH tunnel and Chrome DevTools Protocol. Provides remote browser automation, tab management, and web scraping capabilities.
---

# oldmbp-chrome Skill

Access and control Chrome browser running on oldmbp.lnet via SSH tunnel and Chrome DevTools Protocol.

## Overview

This skill provides access to a Chrome browser instance running on `oldmbp.lnet` (a remote Mac). Chrome is started with remote debugging enabled on port 9222, and an SSH tunnel proxies this port to localhost.

## Location

**Skill directory:** `~/.pi/agent/skills/oldmbp-chrome/`

**Main script:** `~/.pi/agent/skills/oldmbp-chrome/oldmbp_chrome.py`

## Features

- Start/stop Chrome browser on oldmbp remotely
- Automatic SSH tunnel management
- Open URLs in new tabs
- List and manage tabs
- Execute JavaScript in tabs
- Access Chrome DevTools for debugging

## Quick Start

```bash
# Navigate to skill directory
cd ~/.pi/agent/skills/oldmbp-chrome/

# Start Chrome on oldmbp (headfull mode - visible window)
# Uses your default Chrome profile for human-like browsing
# No --no-sandbox or --disable-gpu by default for natural behavior
./oldmbp_chrome.py --start

# Or use a specific profile (e.g., for automation)
./oldmbp_chrome.py --start --profile "~/Library/Application Support/Google/Chrome/Automation"

# Or start in headless mode
./oldmbp_chrome.py --start --headless

# If you need compatibility flags (for problematic environments)
./oldmbp_chrome.py --start --no-sandbox       # for remote/root scenarios
./oldmbp_chrome.py --start --disable-gpu      # for software rendering issues

# Check status
./oldmbp_chrome.py --status

# Open a URL
./oldmbp_chrome.py --open "https://www.rail.co.il"

# Execute JavaScript
./oldmbp_chrome.py --js "document.title"

# When done, kill Chrome
./oldmbp_chrome.py --kill
```

## Commands

### Browser Control
```bash
./oldmbp_chrome.py --start              # Start Chrome (natural behavior, uses your profile)
./oldmbp_chrome.py --start --headless   # Start Chrome (headless)
./oldmbp_chrome.py --start --no-sandbox # Start with sandbox disabled (for remote debugging)
./oldmbp_chrome.py --start --disable-gpu # Start with GPU disabled (for problematic envs)
./oldmbp_chrome.py --kill               # Kill Chrome browser
```

### Tab Operations
```bash
./oldmbp_chrome.py --status             # Show connection status
./oldmbp_chrome.py --list               # List all tabs
./oldmbp_chrome.py --open "https://..." # Open URL in new tab
./oldmbp_chrome.py --close-tab <id>     # Close specific tab
./oldmbp_chrome.py --close-all          # Close all tabs except first
```

### JavaScript Execution
```bash
./oldmbp_chrome.py --js "document.title"                    # Get page title
./oldmbp_chrome.py -j "document.querySelector('h1').innerText" # Get h1 text
./oldmbp_chrome.py --js "..." --tab <id>                     # Run in specific tab
```

### Advanced Options
```bash
./oldmbp_chrome.py -p 9223 --start      # Use different local port
./oldmbp_chrome.py --profile "~/Library/Application Support/Google/Chrome/MyProfile" --start  # Use specific Chrome profile
./oldmbp_chrome.py --open "..." --no-activate  # Don't focus tab
```

## Direct Chrome DevTools Protocol Usage

### Endpoints

Base URL: `http://localhost:9222`

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/json/version` | GET | Chrome version info |
| `/json/list` | GET | List all tabs/pages |
| `/json/new?<url>` | PUT | Open new tab |
| `/json/activate/<id>` | PUT | Focus a tab |
| `/json/close/<id>` | PUT | Close a tab |

### Examples

```bash
# Get Chrome version
curl -s http://localhost:9222/json/version

# List tabs
curl -s http://localhost:9222/json/list

# Open new tab
curl -X PUT "http://localhost:9222/json/new?https://rail.co.il"

# Open DevTools
open "http://localhost:9222/devtools/inspector.html"
```

## Python API

```python
# Add skill directory to path or import directly
import sys
sys.path.insert(0, '~/.pi/agent/skills/oldmbp-chrome')

from oldmbp_chrome import OldmbpChrome

chrome = OldmbpChrome()

# Check if Chrome is running on oldmbp
if chrome.is_chrome_running():
    print("Chrome is running")

# Start Chrome (optionally in headless mode)
chrome.start_chrome(headless=False)

# Ensure tunnel is active
if chrome.ensure_tunnel():
    # Open URL
    tab = chrome.open_url("https://rail.co.il")
    print(f"Opened tab: {tab.id}")
    
    # List all tabs
    for tab in chrome.list_tabs():
        print(f"{tab.title}: {tab.url}")
    
    # Execute JavaScript
    success, result = chrome.eval_js("document.title")
    if success:
        print(f"Page title: {result}")
    
    # Execute in specific tab
    success, result = chrome.eval_js("document.title", tab_id="abc123")
    
    # Close a tab
    chrome.close_tab(tab.id)

# When done, kill Chrome
chrome.kill_chrome()
```

## Use Cases

### Israel Railways Schedule Lookup

```bash
# Start Chrome
./oldmbp_chrome.py --start

# Open rail.co.il planner with specific route
./oldmbp_chrome.py --open "https://www.rail.co.il/en/pages/trainsearch.aspx?fromStation=3700&toStation=5400&scheduleType=1"

# Check status
./oldmbp_chrome.py --status
```

### Execute JavaScript / Scrape Data

```bash
# Open a website
./oldmbp_chrome.py --open "https://example.com"

# Get page title
./oldmbp_chrome.py --js "document.title"

# Get all links
./oldmbp_chrome.py --js "Array.from(document.querySelectorAll('a')).map(a => a.href)"

# Open Reddit and get post titles
./oldmbp_chrome.py --open "https://www.reddit.com"

# Scroll to load more content, then get posts
./oldmbp_chrome.py --js "window.scrollBy(0, 2000)"
./oldmbp_chrome.py --js "Array.from(document.querySelectorAll('shreddit-post')).slice(0,10).map(p => p.getAttribute('post-title'))"

# Run in a specific tab
./oldmbp_chrome.py --list  # Get tab ID
./oldmbp_chrome.py --js "document.title" --tab <tab_id>
```

### Automated Web Scraping

```python
import sys
sys.path.insert(0, '~/.pi/agent/skills/custom/oldmbp-chrome')
from oldmbp_chrome import OldmbpChrome

chrome = OldmbpChrome()

# Ensure Chrome is running
if not chrome.is_chrome_running():
    chrome.start_chrome(headless=True)  # Headless for scraping

chrome.ensure_tunnel()

# Open target page
chrome.open_url("https://example.com")

# Extract data via CDP WebSocket or DevTools
# (Use the webSocketDebuggerUrl from tab info)
```

## Troubleshooting

### Connection Refused

1. Check if Chrome is running and SSH tunnel is active:
   ```bash
   ./oldmbp_chrome.py --status
   ```

2. Manually restart tunnel:
   ```bash
   pkill -f "ssh.*L 9222"
   ssh -f -N -L 9222:localhost:9222 garciamax@oldmbp.lnet
   ```

### Chrome Won't Start

1. Check if Chrome is already running:
   ```bash
   ./oldmbp_chrome.py --status
   ```

2. Kill and restart:
   ```bash
   ./oldmbp_chrome.py --kill
   ./oldmbp_chrome.py --start
   ```

3. Start manually on oldmbp:
   ```bash
   ssh garciamax@oldmbp.lnet
   /Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
     --remote-debugging-port=9222 \
     --user-data-dir="$HOME/Library/Application Support/Google/Chrome/Default" &
   ```

### Chrome Process Hanging

If Chrome becomes unresponsive:

```bash
# Force kill on oldmbp
ssh garciamax@oldmbp.lnet 'pkill -9 -f "Google Chrome"'

# Then restart
./oldmbp_chrome.py --start
```

## Security Notes

- The SSH tunnel uses local port forwarding only (localhost:9222)
- Chrome runs with normal sandbox by default (more secure)
- Use `--no-sandbox` only when needed for remote debugging
- Use `--disable-gpu` only for problematic environments
- Chrome uses your actual user profile by default (cookies, history, etc.)
- Only use on trusted networks
- Anyone with access to localhost:9222 can control the browser
- Consider using a dedicated profile for automation if you manually use Chrome on oldmbp

## Configuration

Default settings in `oldmbp_chrome.py`:
- Remote host: `oldmbp.lnet`
- Remote user: `garciamax`
- Debug port: `9222`
- Chrome path: `/Applications/Google Chrome.app/Contents/MacOS/Google Chrome`
- Local tunnel port: `9222`
- Chrome user data dir: `~/Library/Application Support/Google/Chrome/Default` (your actual Chrome profile!)

**Note:** By default, Chrome uses your actual browser profile, giving you:
- Logged-in sessions (cookies preserved)
- Browser history
- Saved passwords and autofill
- Extensions
- Bookmarks
- All custom settings

This makes automated browsing feel exactly like you were using Chrome manually.

## Related Files

- `~/.pi/agent/skills/oldmbp-chrome/oldmbp_chrome.py` - Main wrapper script
- `~/.pi/agent/skills/oldmbp-chrome/eval_js.py` - Helper for JavaScript execution
- `~/.pi/agent/skills/oldmbp-chrome/SKILL.md` - This documentation
