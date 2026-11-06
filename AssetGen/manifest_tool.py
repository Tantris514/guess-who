"""Add or update approved assets in AssetGen/manifest.json (atomic write: temp file + os.replace).

  python -I -X utf8 manifest_tool.py upsert ENTRY.json      (one entry object or a list of them; matched by name)
  python -I -X utf8 manifest_tool.py remove NAME
  python -I -X utf8 manifest_tool.py summary
"""
import json
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.abspath(__file__))
MANIFEST = os.path.join(ROOT, "manifest.json")


def load():
    if os.path.exists(MANIFEST):
        with open(MANIFEST, encoding="utf-8") as f:
            return json.load(f)
    return {"assets": []}


def save(data):
    data["assets"].sort(key=lambda a: (a.get("kind", ""), a["name"]))
    fd, tmp = tempfile.mkstemp(prefix="manifest_", suffix=".tmp", dir=ROOT)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1, ensure_ascii=False)
    with open(tmp, encoding="utf-8") as f:
        json.load(f)  # never publish an invalid file
    os.replace(tmp, MANIFEST)


def main():
    mode = sys.argv[1]
    data = load()
    if mode == "upsert":
        with open(sys.argv[2], encoding="utf-8-sig") as f:
            entries = json.load(f)
        if isinstance(entries, dict):
            entries = [entries]
        by_name = {a["name"]: i for i, a in enumerate(data["assets"])}
        for e in entries:
            for key, path in e.get("files", {}).items():
                if not os.path.exists(path):
                    raise SystemExit(f"{e['name']}: missing file {key}={path}")
            e.setdefault("status", "approved")
            if e["name"] in by_name:
                data["assets"][by_name[e["name"]]] = e
            else:
                data["assets"].append(e)
        save(data)
        print(f"upserted {len(entries)}; manifest has {len(data['assets'])} assets")
    elif mode == "remove":
        data["assets"] = [a for a in data["assets"] if a["name"] != sys.argv[2]]
        save(data)
        print("removed", sys.argv[2])
    else:
        counts = {}
        for a in data["assets"]:
            counts[a["kind"]] = counts.get(a["kind"], 0) + 1
        print(len(data["assets"]), counts)


if __name__ == "__main__":
    main()
