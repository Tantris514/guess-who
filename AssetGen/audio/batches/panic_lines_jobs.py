"""Clone every panic line from the voice's chosen register reference (qa/panic_refs.json, from panic_select.py --refs-only).
Copies the references to V:/ComfyUI/input/gw_panic_<voice>_<register>.flac.
  python -X utf8 batches/panic_lines_jobs.py [--seeds 901,902] [--only prefix1,prefix2] [--out name.json]"""
import argparse, json, os, shutil, sys
AUD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, AUD)
from panic_voices import REF_TEXT
from panic_lines import SHOUT, CALM
ap = argparse.ArgumentParser(); ap.add_argument("--seeds", default="901,902"); ap.add_argument("--only", default="")
ap.add_argument("--out", default="panic_lines.json"); ap.add_argument("--temperature", type=float, default=0.8)
a = ap.parse_args()
refs = json.load(open(os.path.join(AUD, "qa", "panic_refs.json"), encoding="utf-8"))
qa = json.load(open(os.path.join(AUD, "qa", "panic_qa.json"), encoding="utf-8"))
only = set(a.only.split(",")) if a.only else None
J = []
for cat, lines in (("shout", SHOUT), ("calm", CALM)):
    for slug, text, variants in lines:
        for v in variants:
            vid, reg = (v, "panic") if cat == "shout" else v
            key = f"pv_{vid}_L_{slug}"
            if only and key not in only:
                continue
            src = qa[refs[vid][reg]]["file"]
            ref = f"gw_panic_{vid}_{reg}.flac"
            shutil.copyfile(src, os.path.join(r"V:\ComfyUI\input", ref))
            for s in a.seeds.split(","):
                J.append({"key": key, "group": "panic_" + vid, "mode": "clone", "seed": int(s), "text": text, "ref": ref,
                          "ref_text": REF_TEXT[reg], "temperature": a.temperature,
                          "meta": {"category": cat, "register": reg, "ref_take": refs[vid][reg]}})
json.dump(J, open(os.path.join(AUD, "batches", a.out), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print(len(J))
