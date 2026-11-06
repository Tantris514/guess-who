"""Call comfy-mcp tools over stdio.

Usage: comfy_mcp.py <calls.jsonl> [max_chars]
Each line: {"tool": "<name>", "args": {...}}
"""
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
msg_id = 0


def rpc(method, params=None, notify=False):
    global msg_id
    msg = {"jsonrpc": "2.0", "method": method}
    if params is not None:
        msg["params"] = params
    if not notify:
        msg_id += 1
        msg["id"] = msg_id
    proc.stdin.write(json.dumps(msg) + "\n")
    proc.stdin.flush()
    if notify:
        return None
    while True:
        line = proc.stdout.readline()
        if not line:
            raise RuntimeError("server closed stdout")
        resp = json.loads(line)
        if resp.get("id") == msg_id:
            return resp


rpc("initialize", {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "gw", "version": "0"}})
rpc("notifications/initialized", notify=True)

max_chars = int(sys.argv[2]) if len(sys.argv) > 2 else 6000
with open(sys.argv[1], encoding="utf-8-sig") as f:
    calls = [json.loads(l) for l in f if l.strip()]
for call in calls:
    resp = rpc("tools/call", {"name": call["tool"], "arguments": call.get("args", {})})
    result = resp.get("result") or resp.get("error")
    if isinstance(result, dict) and "content" in result:
        text = "\n".join(c.get("text", "") for c in result["content"])
        if result.get("isError"):
            text = "[isError] " + text
    else:
        text = json.dumps(result, indent=1)
    print(f"\n=== {call['tool']} {json.dumps(call.get('args', {}))[:150]}\n{text[:max_chars]}")
proc.stdin.close()
proc.terminate()
