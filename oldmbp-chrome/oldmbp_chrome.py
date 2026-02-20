#!/usr/bin/env python3
"""
oldmbp_chrome.py - Wrapper for Chrome on oldmbp.lnet via SSH tunnel

Manages SSH tunnel and Chrome DevTools Protocol connection to oldmbp.
Provides a simple interface to open URLs and interact with Chrome remotely.

Usage:
    python3 oldmbp_chrome.py --open "https://example.com"
    python3 oldmbp_chrome.py --status
    python3 oldmbp_chrome.py --list
    python3 oldmbp_chrome.py --close-tab <tab_id>
    python3 oldmbp_chrome.py --close-all
    python3 oldmbp_chrome.py --kill
    python3 oldmbp_chrome.py --start [--headless]
"""

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.request
import urllib.parse
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass


@dataclass
class ChromeTab:
    """Represents a Chrome tab/page"""
    id: str
    title: str
    url: str
    type: str
    web_socket_url: str


class OldmbpChrome:
    """Manager for Chrome on oldmbp via SSH tunnel"""
    
    DEFAULT_HOST = "localhost"
    DEFAULT_PORT = 9222
    REMOTE_USER = "garciamax"
    REMOTE_HOST = "oldmbp.lnet"
    CHROME_PATH = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    # Default to using Chrome's actual user profile for human-like browsing
    # Use "Default" for the main profile, or create a dedicated one like "Automation"
    DEFAULT_USER_DATA_DIR = os.path.expanduser("~/Library/Application Support/Google/Chrome/Default")
    
    def __init__(self, local_port: int = 9222, user_data_dir: str = None):
        self.local_port = local_port
        self.user_data_dir = user_data_dir or self.DEFAULT_USER_DATA_DIR
        self.base_url = f"http://{self.DEFAULT_HOST}:{local_port}"
        self._tunnel_proc = None
    
    def _ssh_exec(self, command: str, timeout: int = 30) -> tuple:
        """Execute command on oldmbp via SSH"""
        cmd = [
            "ssh",
            "-o", "ConnectTimeout=5",
            "-o", "StrictHostKeyChecking=no",
            f"{self.REMOTE_USER}@{self.REMOTE_HOST}",
            command
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return result.returncode, result.stdout, result.stderr
    
    def _test_remote_chrome(self) -> bool:
        """Test if Chrome is responding on oldmbp directly"""
        returncode, stdout, _ = self._ssh_exec(
            f"curl -s http://localhost:{self.DEFAULT_PORT}/json/version 2>/dev/null",
            timeout=5
        )
        if returncode == 0 and stdout and 'Browser' in stdout:
            return True
        return False
    
    def is_chrome_running(self) -> bool:
        """Check if Chrome is running on oldmbp with debugging port"""
        return self._test_remote_chrome()
    
    def kill_chrome(self) -> bool:
        """Kill Chrome browser on oldmbp gracefully to ensure cookies are saved"""
        print(f"Killing Chrome on {self.REMOTE_HOST}...")
        
        # First, try graceful quit via AppleScript (saves cookies properly)
        print("  Attempting graceful shutdown...")
        returncode, stdout, stderr = self._ssh_exec(
            "osascript -e 'tell app \"Google Chrome\" to quit' 2>/dev/null; echo 'done'",
            timeout=10
        )
        
        # Wait for Chrome to save cookies and quit
        time.sleep(3)
        
        # Check if it's still running
        if not self.is_chrome_running():
            print("✓ Chrome terminated gracefully")
            # Kill tunnel on local machine
            subprocess.run(
                ["pkill", "-f", f"ssh.*L {self.local_port}:localhost:{self.DEFAULT_PORT}"],
                capture_output=True
            )
            return True
        
        # Force kill Chrome processes if graceful didn't work
        print("  Graceful quit didn't work, force killing...")
        returncode, _, stderr = self._ssh_exec(
            f"pkill -f 'Google Chrome' 2>/dev/null; echo 'done'",
            timeout=10
        )
        
        # Wait a moment
        time.sleep(2)
        
        # Verify it's dead
        if not self.is_chrome_running():
            print("✓ Chrome processes terminated")
            # Also kill any existing tunnel on local machine
            subprocess.run(
                ["pkill", "-f", f"ssh.*L {self.local_port}:localhost:{self.DEFAULT_PORT}"],
                capture_output=True
            )
            return True
        else:
            print(f"⚠ Chrome may still be running (force kill with: ssh {self.REMOTE_USER}@{self.REMOTE_HOST} 'pkill -9 -f \"Google Chrome\"')")
            return False
    
    def start_chrome(self, headless: bool = False, disable_gpu: bool = False, no_sandbox: bool = False, url: str = "about:blank") -> bool:
        """Start Chrome on oldmbp with remote debugging
        
        Args:
            headless: Run in headless mode (no visible window)
            disable_gpu: Use software rendering (for problematic environments)
            no_sandbox: Disable sandbox (needed for some remote/debug scenarios)
            url: Initial URL to open
        """
        print(f"Starting Chrome on {self.REMOTE_HOST}...")
        
        # Check if already running
        if self.is_chrome_running():
            print("✓ Chrome is already running with debug port")
            return True
        
        # Kill any existing Chrome processes first
        print("Cleaning up existing Chrome processes...")
        self._ssh_exec("pkill -f 'Google Chrome' 2>/dev/null; sleep 1", timeout=10)
        
        # Prepare Chrome command
        # Only add flags that are needed for natural behavior
        headless_flag = "--headless" if headless else ""
        gpu_flag = "--disable-gpu" if disable_gpu else ""
        sandbox_flag = "--no-sandbox" if no_sandbox else ""
        
        # Disable fast startup to ensure cookies/sessions are properly saved to disk
        # Use restore-last-session to restore previous session (including logged-in state)
        fast_startup_flag = "--disable-fast-startup"
        restore_session_flag = "--restore-last-session"
        
        # For Mac, use 'open' command to launch Chrome more naturally
        # Don't pass URL - let Chrome restore last session automatically
        chrome_cmd = (
            f"mkdir -p '{self.user_data_dir}'; "
            f"open -a 'Google Chrome' --args "
            f"--remote-debugging-port={self.DEFAULT_PORT} "
            f"--user-data-dir='{self.user_data_dir}' "
            f"{fast_startup_flag} "
            f"{restore_session_flag} "
            f"{headless_flag} "
            f"{gpu_flag} "
            f"{sandbox_flag} &"
        )
        
        print(f"  Starting Chrome...")
        returncode, _, stderr = self._ssh_exec(chrome_cmd, timeout=10)
        
        if returncode != 0:
            print(f"✗ Failed to start Chrome: {stderr}")
            return False
        
        # Wait for Chrome to start
        print("  Waiting for Chrome to initialize...")
        for i in range(20):
            time.sleep(1)
            if self.is_chrome_running():
                mode = "headless" if headless else "headfull"
                print(f"✓ Chrome started in {mode} mode")
                return True
            if i == 10:
                print("  Still waiting... (this may take a moment on first start)")
        
        print("✗ Chrome start timeout - check /tmp/chrome.out on oldmbp for errors")
        print(f"  Try manually: ssh {self.REMOTE_USER}@{self.REMOTE_HOST}")
        return False
    
    def _kill_existing_tunnels(self):
        """Kill any existing SSH tunnels for this port"""
        subprocess.run(
            ["pkill", "-f", f"ssh.*L {self.local_port}:localhost:{self.DEFAULT_PORT}"],
            capture_output=True
        )
        time.sleep(1)
    
    def _test_tunnel(self) -> bool:
        """Test if the tunnel is working"""
        try:
            with urllib.request.urlopen(
                f"{self.base_url}/json/version", 
                timeout=3
            ) as response:
                return response.status == 200
        except:
            return False
    
    def ensure_tunnel(self) -> bool:
        """Ensure SSH tunnel is active, create if needed"""
        # First test if tunnel already works
        if self._test_tunnel():
            return True
        
        # Check if Chrome is running on remote first
        if not self.is_chrome_running():
            print(f"✗ Chrome is not running on {self.REMOTE_HOST}")
            print(f"  Start it with: python3 {sys.argv[0]} --start")
            return False
        
        print(f"Establishing SSH tunnel to {self.REMOTE_HOST}:{self.DEFAULT_PORT}...")
        
        # Kill any existing tunnel first
        self._kill_existing_tunnels()
        
        # Create new tunnel
        cmd = [
            "ssh",
            "-f",  # Fork to background
            "-N",  # Don't execute remote command
            "-o", "ExitOnForwardFailure=yes",
            "-o", "ConnectTimeout=10",
            "-L", f"{self.local_port}:localhost:{self.DEFAULT_PORT}",
            f"{self.REMOTE_USER}@{self.REMOTE_HOST}"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"✗ Failed to create tunnel: {result.stderr}")
            print(f"  Check SSH connection: ssh {self.REMOTE_USER}@{self.REMOTE_HOST}")
            return False
        
        # Wait for tunnel to be ready
        for i in range(15):
            time.sleep(0.5)
            if self._test_tunnel():
                print(f"✓ Tunnel established: localhost:{self.local_port} -> {self.REMOTE_HOST}:{self.DEFAULT_PORT}")
                return True
        
        print("✗ Tunnel creation timeout - tunnel process started but not responding")
        print(f"  Check: ps aux | grep 'ssh.*L {self.local_port}'")
        return False
    
    def get_version(self) -> Optional[Dict]:
        """Get Chrome version info"""
        try:
            with urllib.request.urlopen(
                f"{self.base_url}/json/version", 
                timeout=5
            ) as response:
                return json.loads(response.read().decode())
        except Exception as e:
            print(f"Error getting version: {e}")
            return None
    
    def list_tabs(self) -> List[ChromeTab]:
        """List all open tabs/pages"""
        try:
            with urllib.request.urlopen(
                f"{self.base_url}/json/list", 
                timeout=5
            ) as response:
                data = json.loads(response.read().decode())
                tabs = []
                for item in data:
                    tabs.append(ChromeTab(
                        id=item.get('id', ''),
                        title=item.get('title', 'Untitled'),
                        url=item.get('url', ''),
                        type=item.get('type', 'page'),
                        web_socket_url=item.get('webSocketDebuggerUrl', '')
                    ))
                return tabs
        except Exception as e:
            print(f"Error listing tabs: {e}")
            return []
    
    def open_url(self, url: str, activate: bool = True) -> Optional[ChromeTab]:
        """Open a new tab with the given URL"""
        try:
            encoded_url = urllib.parse.quote(url, safe='')
            req = urllib.request.Request(
                f"{self.base_url}/json/new?{encoded_url}",
                method='PUT'
            )
            
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode())
                
                tab = ChromeTab(
                    id=data.get('id', ''),
                    title=data.get('title', 'Loading...'),
                    url=data.get('url', url),
                    type=data.get('type', 'page'),
                    web_socket_url=data.get('webSocketDebuggerUrl', '')
                )
                
                if activate:
                    self.activate_tab(tab.id)
                
                return tab
        except Exception as e:
            print(f"Error opening URL: {e}")
            return None
    
    def activate_tab(self, tab_id: str) -> bool:
        """Activate/focus a tab"""
        try:
            req = urllib.request.Request(
                f"{self.base_url}/json/activate/{tab_id}",
                method='PUT'
            )
            urllib.request.urlopen(req, timeout=5)
            return True
        except:
            return False
    
    def close_tab(self, tab_id: str) -> bool:
        """Close a specific tab"""
        try:
            req = urllib.request.Request(
                f"{self.base_url}/json/close/{tab_id}",
                method='PUT'
            )
            urllib.request.urlopen(req, timeout=5)
            return True
        except Exception as e:
            print(f"Error closing tab: {e}")
            return False
    
    def close_all_tabs(self, keep_first: bool = True) -> int:
        """Close all tabs, optionally keeping the first one"""
        tabs = self.list_tabs()
        closed = 0
        
        start_idx = 1 if keep_first and tabs else 0
        
        for tab in tabs[start_idx:]:
            if self.close_tab(tab.id):
                closed += 1
        
        return closed
    
    def eval_js(self, js_code: str, tab_id: Optional[str] = None) -> Tuple[bool, str]:
        """
        Execute JavaScript in a tab.
        
        Args:
            js_code: JavaScript code to execute
            tab_id: Optional tab ID. If not provided, uses the first page tab.
        
        Returns:
            Tuple of (success, result_string)
        """
        # Get the target tab
        if tab_id:
            tabs = self.list_tabs()
            target_tab = next((t for t in tabs if t.id == tab_id), None)
            if not target_tab:
                return False, f"Tab not found: {tab_id}"
        else:
            tabs = self.list_tabs()
            target_tab = next((t for t in tabs if t.type == 'page'), None)
            if not target_tab:
                return False, "No page tabs found"
        
        if not target_tab.web_socket_url:
            return False, "No WebSocket URL available for tab"
        
        # Call the helper script
        script_dir = os.path.dirname(os.path.abspath(__file__))
        helper_script = os.path.join(script_dir, 'eval_js.py')
        
        # Replace localhost in ws_url with 127.0.0.1 to avoid issues
        ws_url = target_tab.web_socket_url.replace('localhost', '127.0.0.1')
        
        try:
            result = subprocess.run(
                ['python3', helper_script, str(self.local_port), ws_url, js_code],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                return False, result.stderr
            
            return True, result.stdout.strip()
        except subprocess.TimeoutExpired:
            return False, "JavaScript execution timed out"
        except Exception as e:
            return False, str(e)
    
    def print_status(self):
        """Print current status"""
        print("=" * 60)
        print("oldmbp Chrome Status")
        print("=" * 60)
        
        print(f"\nHost: {self.REMOTE_HOST}")
        print(f"Port: {self.DEFAULT_PORT}")
        print(f"Profile: {self.user_data_dir}")
        
        # Check Chrome on remote
        if self.is_chrome_running():
            print(f"✓ Chrome: RUNNING (on {self.REMOTE_HOST})")
        else:
            print(f"✗ Chrome: NOT RUNNING")
            script_path = sys.argv[0] if sys.argv[0].startswith('/') else f"./{sys.argv[0]}"
            print(f"  Start with: {script_path} --start")
        
        # Tunnel status
        if self._test_tunnel():
            print(f"✓ SSH Tunnel: ACTIVE")
            print(f"  localhost:{self.local_port} -> {self.REMOTE_HOST}:{self.DEFAULT_PORT}")
            
            # Chrome version (via tunnel)
            version = self.get_version()
            if version:
                print(f"  Version: {version.get('Browser', 'Unknown')}")
        else:
            print(f"✗ SSH Tunnel: NOT CONNECTED")
            if self.is_chrome_running():
                print(f"  The tunnel is not active but Chrome is running.")
                print(f"  Run with any command (except --status) to auto-establish tunnel.")
        
        # Tabs (only if tunnel is working)
        if self._test_tunnel():
            tabs = self.list_tabs()
            print(f"\n✓ Open tabs: {len(tabs)}")
            for i, tab in enumerate(tabs[:10], 1):
                title = tab.title[:40] if tab.title else "(no title)"
                print(f"  {i}. {title:<40} [{tab.type}]")
            
            if len(tabs) > 10:
                print(f"  ... and {len(tabs) - 10} more")
        
        print(f"\nDevTools: http://localhost:{self.local_port}/devtools/inspector.html")
        print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Control Chrome on oldmbp.lnet via SSH tunnel",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --start                    # Start Chrome (natural, using your profile)
  %(prog)s --start --headless         # Start Chrome in headless mode
  %(prog)s --start --no-sandbox       # Start with sandbox disabled (for remote debugging)
  %(prog)s --start --disable-gpu      # Start with GPU disabled (for problematic environments)
  %(prog)s --kill                     # Kill Chrome browser
  %(prog)s --status                   # Show connection status
  %(prog)s --open "https://google.com" # Open URL
  %(prog)s --list                     # List all tabs
  %(prog)s --close-all                # Close all tabs except first
  %(prog)s --js "document.title"      # Execute JS in active tab
  %(prog)s --js "document.title" --tab <id>  # Execute JS in specific tab
        """
    )
    
    # Browser control
    parser.add_argument(
        "--start",
        action="store_true",
        help="Start Chrome browser on oldmbp"
    )
    parser.add_argument(
        "--kill", "-k",
        action="store_true",
        help="Kill Chrome browser on oldmbp"
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Start Chrome in headless mode (with --start)"
    )
    parser.add_argument(
        "--disable-gpu",
        action="store_true",
        help="Disable GPU hardware acceleration (for problematic environments)"
    )
    parser.add_argument(
        "--no-sandbox",
        action="store_true",
        help="Disable sandbox (usually needed for root/remote debugging)"
    )
    
    # Tab/Page operations
    parser.add_argument(
        "--open", "-o",
        metavar="URL",
        help="Open a URL in Chrome"
    )
    parser.add_argument(
        "--list", "-l",
        action="store_true",
        help="List all open tabs"
    )
    parser.add_argument(
        "--status", "-s",
        action="store_true",
        help="Show connection status"
    )
    parser.add_argument(
        "--close-tab",
        metavar="ID",
        help="Close a specific tab by ID"
    )
    parser.add_argument(
        "--close-all",
        action="store_true",
        help="Close all tabs except the first"
    )
    parser.add_argument(
        "--js", "-j",
        metavar="CODE",
        help="Execute JavaScript code in the active tab"
    )
    parser.add_argument(
        "--tab",
        metavar="ID",
        help="Specify tab ID for --js option"
    )
    
    # Connection options
    parser.add_argument(
        "--port", "-p",
        type=int,
        default=9222,
        help="Local port for SSH tunnel (default: 9222)"
    )
    parser.add_argument(
        "--profile",
        metavar="PATH",
        default=None,
        help="Chrome user data directory (default: user's default Chrome profile)"
    )
    parser.add_argument(
        "--no-activate",
        action="store_true",
        help="Don't activate/focus the tab when opening"
    )
    
    args = parser.parse_args()
    
    # If no args, show help
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)
    
    chrome = OldmbpChrome(local_port=args.port, user_data_dir=args.profile)
    
    # Handle kill first (before tunnel)
    if args.kill:
        success = chrome.kill_chrome()
        sys.exit(0 if success else 1)
    
    # Handle start
    if args.start:
        success = chrome.start_chrome(
            headless=args.headless,
            disable_gpu=args.disable_gpu,
            no_sandbox=args.no_sandbox
        )
        if success:
            # Auto-establish tunnel after starting
            chrome.ensure_tunnel()
        sys.exit(0 if success else 1)
    
    # For other operations, ensure tunnel is active
    if not args.status:
        if not chrome.ensure_tunnel():
            script_path = sys.argv[0] if sys.argv[0].startswith('/') else f"./{sys.argv[0]}"
            print("\nTroubleshooting:")
            print(f"  1. Check SSH connection: ssh {chrome.REMOTE_USER}@{chrome.REMOTE_HOST}")
            print(f"  2. Check if Chrome is running: ssh {chrome.REMOTE_USER}@{chrome.REMOTE_HOST} 'curl -s http://localhost:9222/json/version'")
            print(f"  3. Start Chrome: {script_path} --start")
            sys.exit(1)
    
    # Handle status
    if args.status:
        chrome.print_status()
    
    # Handle open URL
    elif args.open:
        tab = chrome.open_url(args.open, activate=not args.no_activate)
        if tab:
            print(f"Opened: {tab.url}")
            print(f"Tab ID: {tab.id}")
            print(f"DevTools: http://localhost:{args.port}/devtools/inspector.html?ws=localhost:{args.port}/devtools/page/{tab.id}")
        else:
            print("Failed to open URL")
            sys.exit(1)
    
    # Handle list
    elif args.list:
        tabs = chrome.list_tabs()
        print(f"\n{len(tabs)} tab(s) open:")
        print("-" * 80)
        for tab in tabs:
            print(f"ID:   {tab.id}")
            print(f"Type: {tab.type}")
            print(f"Title: {tab.title}")
            print(f"URL:  {tab.url}")
            print("-" * 80)
    
    # Handle close-tab
    elif args.close_tab:
        if chrome.close_tab(args.close_tab):
            print(f"Closed tab: {args.close_tab}")
        else:
            print(f"Failed to close tab: {args.close_tab}")
            sys.exit(1)
    
    # Handle close-all
    elif args.close_all:
        closed = chrome.close_all_tabs()
        print(f"Closed {closed} tab(s)")
    
    # Handle --js (JavaScript execution)
    elif args.js:
        success, result = chrome.eval_js(args.js, tab_id=args.tab)
        if success:
            print(result)
        else:
            print(f"Error: {result}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
