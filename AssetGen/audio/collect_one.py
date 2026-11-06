"""Collect one already-submitted TTS chunk by prompt_id (never resubmits).  python -I -X utf8 collect_one.py JOBS.json CHUNK_INDEX CHUNK_SIZE PROMPT_ID"""
import json, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import panic_run as R
jobs = json.load(open(sys.argv[1], encoding="utf-8-sig")); ci, size, pid = int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
chunks = []
for mode in ("design", "clone"):
    sel = [j for j in jobs if j["mode"] == mode]
    chunks += [sel[c:c + size] for c in range(0, len(sel), size)]
entry = R.wait(pid)
st = entry.get("status", {}).get("status_str")
print("status", st)
if st == "success":
    print("collected", R.collect_tts(R.outputs(entry), chunks[ci], pid), "of", len(chunks[ci]))
