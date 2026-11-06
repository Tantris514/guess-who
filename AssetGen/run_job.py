"""Run one prepared workflow through comfy-mcp and fetch its outputs.

  python -I -X utf8 run_job.py WORKFLOW.json OUT_DIR [timeout_s]
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from assetgen import ComfyMCP, run_and_fetch  # noqa: E402

mcp = ComfyMCP()
try:
    pid, secs, files, mapping = run_and_fetch(mcp, sys.argv[1], sys.argv[2], float(sys.argv[3]) if len(sys.argv) > 3 else 1800)
    print(json.dumps({"prompt_id": pid, "seconds": secs, "files": {f: mapping.get(f, "") for f in files}}))
finally:
    mcp.close()
