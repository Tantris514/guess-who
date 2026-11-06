"""Write AssetGen/audio/voices.json (every voice with a reference take) and script/legacy_texts.json (sentences already
rendered in the legacy batch, so the voice director does not script them again)."""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from panic_voices import VOICES  # noqa: E402

AGES = {"m1_baron": 72, "m2_nerveux": 25, "m3_bonvivant": 52, "m4_colonel": 64, "f1_ingenue": 20, "f2_comtesse": 68, "f3_bourgeoise": 45,
        "f4_aviatrice": 30, "b1_brute": 45, "b2_voyou": 24, "k1_kamikaze": 35, "r1_robot": None}
ROLE = lambda v: "guest" if v[0] in "mf" and v[1].isdigit() else {"b": "bandit", "k": "kamikaze", "r": "robot", "s": "staff"}.get(v[0], "guest")  # noqa: E731
refs = json.load(open(os.path.join(HERE, "qa", "panic_refs.json"), encoding="utf-8"))
qa = json.load(open(os.path.join(HERE, "qa", "panic_qa.json"), encoding="utf-8"))
script_p = os.path.join(HERE, "script", "voice_script.json")
script = json.load(open(script_p, encoding="utf-8")) if os.path.exists(script_p) else {"voices": []}
cards = {v["voice_id"]: v for v in script.get("voices", [])}
out = []
for vid, (g, label, desc) in VOICES.items():
    r = refs.get(vid, {})
    regs = {k: os.path.relpath(qa[t]["file"], HERE).replace("\\", "/") for k, t in r.items() if isinstance(t, str) and t in qa}
    if not regs:
        continue
    c = cards.get(vid, {})
    out.append({"voice_id": vid, "gender": g, "age": c.get("age", AGES.get(vid)), "role": c.get("role", ROLE(vid)), "label": c.get("label", label),
                "description": desc, "accent": c.get("accent"), "ref_file": regs.get("neutral") or next(iter(regs.values())), "register_refs": regs})
for g, desc in (("f", "generic adult / older woman (Stable Audio 3 text-to-audio, non-verbal only)"),
                ("m", "generic adult / older man (Stable Audio 3 text-to-audio, non-verbal only)")):
    out.append({"voice_id": f"sa3_{g}", "gender": g, "age": None, "role": "generic", "label": "generic non-verbal", "description": desc,
                "ref_file": None, "register_refs": {}})
json.dump({"voices": out}, open(os.path.join(HERE, "voices.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
rep = json.load(open(os.path.join(HERE, "final", "panic", "panic_report.json"), encoding="utf-8"))
from panic_lines import named  # noqa: E402
texts = sorted({e["text"] for e in rep if e.get("text")} | {it["text"] for it in named() if not it.get("nonverbal")})
json.dump({"note": "sentences rendered (or rendering) in the legacy batch final/panic; do not script these again", "texts": texts},
          open(os.path.join(HERE, "script", "legacy_texts.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print(len(out), "voices;", len(texts), "legacy texts")
