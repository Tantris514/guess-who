"""Job lists for every voice line in panic_lines.ITEMS.
  python -X utf8 batches/vo_jobs.py refs2                  -> batches/vo_refs2.json (startled/threat/manic/flat refs + laughs)
  python -X utf8 batches/vo_jobs.py lines [--cats a,b] [--seeds 2] [--only key,...] [--out f.json] [--seed-base N]
     clone jobs from qa/panic_refs.json (copies the refs to V:/ComfyUI/input), design jobs for non-verbal items."""
import argparse, json, os, shutil, sys
AUD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, AUD)
from panic_voices import VOICES, REF_TEXT, instruct
from panic_lines import named
ap = argparse.ArgumentParser(); ap.add_argument("phase"); ap.add_argument("--cats", default=""); ap.add_argument("--seeds", type=int, default=2)
ap.add_argument("--only", default=""); ap.add_argument("--out", default=""); ap.add_argument("--seed-base", type=int, default=1000)
ap.add_argument("--seeds-map", default="shout:2,attack:2,kamikaze:2")   # category:seeds overrides (others use --seeds)
ap.add_argument("--skip-voices", default=""); ap.add_argument("--skip-done", action="store_true")
a = ap.parse_args()
J = []
ITEMS = named()
if a.phase == "refs2":
    seeds = {"startled": (741, 742), "threat": (751, 752), "manic": (761, 762), "flat": (791, 792), "neutral": (701, 702)}
    for vid in VOICES:
        regs = {it["reg"] for it in ITEMS if it["voice"] == vid and it.get("mode") != "design"}
        for reg in sorted(regs - {"panic", "awkward", "whisper"} - ({"neutral"} if not vid[0] in "bkr" else set())):
            for s in seeds[reg]:
                J.append({"key": f"pv_{vid}_ref{reg}", "group": "panic_" + vid, "mode": "design", "seed": s, "text": REF_TEXT[reg],
                          "instruct": instruct(vid, reg)})
    for i, it in enumerate(ITEMS):
        if it.get("mode") == "design":
            for k in range(2):
                J.append({"key": it["key"], "group": "panic_" + it["voice"], "mode": "design", "seed": a.seed_base + 10 * i + k,
                          "text": it["text"], "instruct": instruct(it["voice"], it["reg"]), "meta": {"category": it["cat"], "register": it["reg"]}})
    out = a.out or "vo_refs2.json"
else:
    refs = json.load(open(os.path.join(AUD, "qa", "panic_refs.json"), encoding="utf-8"))
    qa = json.load(open(os.path.join(AUD, "qa", "panic_qa.json"), encoding="utf-8"))
    cats = set(a.cats.split(",")) if a.cats else None
    only = set(a.only.split(",")) if a.only else None
    smap = {kv.split(":")[0]: int(kv.split(":")[1]) for kv in a.seeds_map.split(",") if kv}
    skipv = set(a.skip_voices.split(",")) if a.skip_voices else set()
    for i, it in enumerate(ITEMS):
        if it.get("mode") == "design" or (cats and it["cat"] not in cats) or (only and it["key"] not in only):
            continue
        if it["voice"] in skipv or it["reg"] not in refs.get(it["voice"], {}):
            print("skip (no ref yet)", it["key"]); continue
        if a.skip_done and any(k.startswith(it["key"] + "_s") for k in qa):
            continue
        reg = it["reg"]
        reftake = refs[it["voice"]][reg]
        ref = f"gw_panic_{it['voice']}_{reg}.flac"
        dst = os.path.join(r"V:\ComfyUI\input", ref)
        shutil.copyfile(qa[reftake]["file"], dst)
        for k in range(smap.get(it["cat"], a.seeds)):
            J.append({"key": it["key"], "group": "panic_" + it["voice"], "mode": "clone", "seed": a.seed_base + 10 * i + k, "text": it["text"],
                      "ref": ref, "ref_text": REF_TEXT[reg], "meta": {"category": it["cat"], "register": reg, "ref_take": reftake}})
    out = a.out or "vo_lines.json"
json.dump(J, open(os.path.join(AUD, "batches", out), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print(out, len(J))
