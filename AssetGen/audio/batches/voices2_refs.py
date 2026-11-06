"""Register references for the 16 new guests (neutral x2, panic x2, whisper x1) and the 4 staff voices (neutral x2)."""
import json, os, sys
AUD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, AUD)
from panic_voices import VOICES, ROLE, instruct, REF_TEXT
OLD = {"m1_baron", "m2_nerveux", "m3_bonvivant", "m4_colonel", "f1_ingenue", "f2_comtesse", "f3_bourgeoise", "f4_aviatrice"}
J = []
for vid in VOICES:
    if vid in OLD or ROLE[vid] not in ("guest", "staff"):
        continue
    regs = [("neutral", (701, 702)), ("panic", (711, 712)), ("whisper", (721,))] if ROLE[vid] == "guest" else [("neutral", (701, 702))]
    for reg, seeds in regs:
        for s in seeds:
            J.append({"key": f"pv_{vid}_ref{reg}", "group": "panic_" + vid, "mode": "design", "seed": s, "text": REF_TEXT[reg],
                      "instruct": instruct(vid, reg)})
json.dump(J, open(os.path.join(AUD, "batches", "voices2_refs.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print(len(J))
