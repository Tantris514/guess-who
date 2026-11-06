"""Print the input schema and description of selected comfy-mcp tools."""
import json
import os
import subprocess
import sys
import threading

EXE = r"V:\ComfyUI\comfy-mcp-env\Scripts\comfy-mcp.exe"
env = dict(os.environ, COMFY_BIN=r"V:\ComfyUI\comfy-mcp-env\Scripts\comfy.exe")
proc = subprocess.Popen([EXE], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                        env=env, text=True, encoding="utf-8", errors="replace", bufsize=1)
threading.Thread(target=lambda: [None for _ in proc.stderr], daemon=True).start()


def rpc(i, method, params=None):
    proc.stdin.write(json.dumps({"jsonrpc": "2.0", "id": i, "method": method, "params": params or {}}) + "\n")
    proc.stdin.flush()
    while True:
        r = json.loads(proc.stdout.readline())
        if r.get("id") == i:
            return r


rpc(1, "initialize", {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "s", "version": "0"}})
proc.stdin.write(json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n")
proc.stdin.flush()
tools = rpc(2, "tools/list")["result"]["tools"]
wanted = set(sys.argv[1:])
for t in tools:
    if t["name"] in wanted:
        print(f"\n##### {t['name']}\n{t.get('description', '')[:2500]}\nINPUT: {json.dumps(t.get('inputSchema', {}).get('properties', {}))[:2500]}")
proc.terminate()
