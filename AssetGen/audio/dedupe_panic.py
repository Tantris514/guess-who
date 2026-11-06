"""Clean the legacy panic bank for VOIX_ARCHITECTURE.md: one sentence = one file (a duplicate text, e.g. the reference takes
reused as lines 51+ or the same line in two voices, is moved to final/panic/_dups and dropped from the report), shout
causes (gun / generic) and gun flags set explicitly. Re-runnable.  python -X utf8 dedupe_panic.py"""
import json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from vox import norm  # noqa: E402

D = os.path.join(HERE, "final", "panic")
R = os.path.join(D, "panic_report.json")
GUN = re.compile(r"\b(tir\w*|arm[eé]s?|armée?s?|assassin|revolver|pistolet|fusil|balles?|malade|fou)\b", re.I)
PRIO = {"shout": 0, "attack_guest": 1, "calm": 2, "chatter": 3, "reply": 4, "blackout": 5, "fire": 6, "kamikaze": 7, "robot_voice": 8}
rows = json.load(open(R, encoding="utf-8"))
keep, seen, dropped = [], {}, []
for e in sorted(rows, key=lambda e: (PRIO.get(e["category"], 9), int(re.search(r"_(\d+)_[mf]\.wav$", e["file"]).group(1)) >= 51
                                     if re.search(r"_(\d+)_[mf]\.wav$", e["file"]) else 0, e["file"])):
    t = e.get("text") or ""
    if t and not e.get("nonverbal"):
        n = norm(t)
        if n in seen:
            dropped.append((e["file"], seen[n]))
            os.makedirs(os.path.join(D, "_dups"), exist_ok=True)
            if os.path.exists(os.path.join(D, e["file"])):
                os.replace(os.path.join(D, e["file"]), os.path.join(D, "_dups", e["file"]))
            continue
        seen[n] = e["file"]
    if e["category"] in ("shout", "attack_guest", "calm"):
        e["gun"] = bool(GUN.search(t))
    if e["category"] == "shout":
        e["cause"] = "gun" if e["gun"] else "generic"
    keep.append(e)
json.dump(sorted(keep, key=lambda e: (e["category"], e["file"])), open(R, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print(f"kept {len(keep)}, dropped {len(dropped)} duplicate texts")
for f, o in dropped:
    print("  dup", f, "of", o)
