#!/usr/bin/env python3
"""
Helper script to execute JavaScript in Chrome via DevTools Protocol.
This is called by oldmbp_chrome.py when --js is used.
"""

import sys
import json
import subprocess

def eval_js(port, ws_url, js_code):
    """Execute JavaScript using chrome-remote-interface"""
    node_code = f'''
const CDP = require('chrome-remote-interface');

async function main() {{
    const client = await CDP({{
        port: {port},
        target: '{ws_url}'
    }});
    
    const {{ Runtime }} = client;
    await Runtime.enable();
    
    const result = await Runtime.evaluate({{
        expression: `{js_code.replace('`', '\\`')}`,
        returnByValue: true
    }});
    
    console.log(JSON.stringify(result.result.value));
    
    await client.close();
}}

main().catch(e => {{
    console.error(JSON.stringify({{ error: e.message }}));
    process.exit(1);
}});
'''
    result = subprocess.run(
        ['node', '-e', node_code],
        capture_output=True,
        text=True,
        cwd='/tmp'
    )
    
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
        sys.exit(1)
    
    print(result.stdout)

if __name__ == '__main__':
    if len(sys.argv) < 4:
        print("Usage: eval_js.py <port> <ws_url> <js_code>", file=sys.stderr)
        sys.exit(1)
    
    port = sys.argv[1]
    ws_url = sys.argv[2]
    js_code = sys.argv[3]
    
    eval_js(port, ws_url, js_code)
