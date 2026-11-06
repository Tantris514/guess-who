"""Tiny CLI over comfy-mcp (reuses assetgen.ComfyMCP). Usage: mcpcall.py TOOL '{"json":"args"}' [maxchars]"""
import json, os, sys
sys.path.insert(0, r"J:\Projets\Unreal_Projects\Guess Who\AssetGen")
from comfyclient import ComfyMCP
m = ComfyMCP()
try:
    r = m.call(sys.argv[1], **json.loads(sys.argv[2] if len(sys.argv) > 2 else "{}"))
    s = r if isinstance(r, str) else json.dumps(r, indent=1, ensure_ascii=False)
    mx = int(sys.argv[3]) if len(sys.argv) > 3 else 6000
    print(s[:mx])
finally:
    m.close()
