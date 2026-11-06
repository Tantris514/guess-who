"""Convert a UI-format ComfyUI workflow to API format with comfy-cli's own converter (same as `comfy run` / comfy-mcp).

  V:\\ComfyUI\\comfy-mcp-env\\Scripts\\python.exe -I ui2api.py UI.json API_OUT.json
Needs ComfyUI running (reads /object_info).
"""
import json
import sys
import urllib.request

from comfy_cli.workflow_to_api import convert_ui_to_api

ui, out = sys.argv[1], sys.argv[2]
with urllib.request.urlopen("http://127.0.0.1:8188/object_info", timeout=120) as r:
    object_info = json.loads(r.read().decode("utf-8"))
api = convert_ui_to_api(json.load(open(ui, encoding="utf-8")), object_info)
if not api:
    sys.exit("conversion produced no nodes")
json.dump(api, open(out, "w", encoding="utf-8"))
print(len(api), "nodes")
