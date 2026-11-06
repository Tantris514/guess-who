"""Describe Unreal MCP toolsets compactly: tool short name, required args, first line of description."""
import json
import sys
import urllib.request

URL = "http://127.0.0.1:8010/mcp"
session_id = None
msg_id = 0


def post(method, params=None, notify=False):
    global msg_id, session_id
    body = {"jsonrpc": "2.0", "method": method}
    if params is not None:
        body["params"] = params
    if not notify:
        msg_id += 1
        body["id"] = msg_id
    req = urllib.request.Request(URL, data=json.dumps(body).encode(), method="POST", headers={
        "Content-Type": "application/json", "Accept": "application/json, text/event-stream",
        **({"Mcp-Session-Id": session_id} if session_id else {})})
    with urllib.request.urlopen(req, timeout=120) as resp:
        session_id = resp.headers.get("Mcp-Session-Id") or session_id
        raw = resp.read().decode("utf-8", "replace")
    if notify or not raw.strip():
        return None
    if raw.lstrip().startswith("{"):
        return json.loads(raw)
    for line in reversed(raw.splitlines()):
        if line.startswith("data:"):
            data = json.loads(line[5:].strip())
            if data.get("id") == msg_id:
                return data


post("initialize", {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "d", "version": "0"}})
post("notifications/initialized", notify=True)

verbose = "-v" in sys.argv
for ts in [a for a in sys.argv[1:] if a != "-v"]:
    r = post("tools/call", {"name": "describe_toolset", "arguments": {"toolset_name": ts}})
    text = "".join(c.get("text", "") for c in r["result"]["content"])
    try:
        d = json.loads(text)
    except json.JSONDecodeError:
        print(f"## {ts}: {text[:300]}")
        continue
    print(f"\n## {ts} ({len(d['tools'])} tools)")
    for t in d["tools"]:
        short = t["name"].rsplit(".", 1)[-1]
        req = t.get("inputSchema", {}).get("required", [])
        props = list(t.get("inputSchema", {}).get("properties", {}).keys())
        desc = t.get("description", "").strip()
        first = desc.splitlines()[0] if desc else ""
        if verbose:
            print(f"- {short}({', '.join(props)}) req={req}\n    {desc[:900]}")
        else:
            print(f"- {short}({', '.join(props)}) :: {first[:150]}")
