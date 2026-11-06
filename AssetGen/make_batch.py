"""Build assetgen batch files from props.json.

  python -I -X utf8 make_batch.py concepts OUT.json [names...]     concept jobs (all props + character items, or the named ones)
  python -I -X utf8 make_batch.py models OUT.json name=image ...   3D jobs from approved concept images
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(ROOT, "props.json"), encoding="utf-8") as f:
    spec = json.load(f)

mode, out = sys.argv[1], sys.argv[2]
jobs = []
if mode == "concepts":
    wanted = set(sys.argv[3:])
    seed = 11
    for entry in spec["props"] + spec["character_items"]:
        if wanted and entry["name"] not in wanted:
            continue
        prompt = spec["_style"].replace("{item}", entry["item"])
        jobs.append({"kind": "concept", "name": entry["name"], "prompt": prompt, "seed": entry.get("seed", seed)})
elif mode == "models":
    for arg in sys.argv[3:]:
        name, image = arg.split("=", 1)
        jobs.append({"kind": "model", "name": name, "image": image, "engine": "trellis", "tex": 2048, "faces": 150000})
with open(out, "w", encoding="utf-8") as f:
    json.dump(jobs, f, indent=1)
print(f"{len(jobs)} jobs -> {out}")
