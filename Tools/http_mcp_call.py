"""Streamable-HTTP MCP helper: initialize, then run each argv JSON step as {"method":..., "params":...} and print results."""
import json
import sys
import urllib.request

url = sys.argv[1]
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
    req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST", headers={
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        **({"Mcp-Session-Id": session_id} if session_id else {}),
    })
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
    raise RuntimeError(f"no response in: {raw[:500]}")


post("initialize", {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "probe", "version": "0"}})
post("notifications/initialized", notify=True)

with open(sys.argv[2], encoding="utf-8") as f:
    steps = [line for line in f.read().splitlines() if line.strip()]

for step in steps:
    spec = json.loads(step)
    resp = post(spec["method"], spec.get("params"))
    result = resp.get("result") or resp.get("error")
    if isinstance(result, dict) and "content" in result:
        out = " ".join(c.get("text", "") for c in result["content"])
        if result.get("isError"):
            out = "[isError] " + out
    else:
        out = json.dumps(result, indent=1)
    print(f"\n=== {spec['method']} {json.dumps(spec.get('params', {}))[:120]}\n{out[:int(spec.get('max', 3000))]}")
