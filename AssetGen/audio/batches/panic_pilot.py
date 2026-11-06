"""Pilot: 2 voices (m1_baron, f1_ingenue) x 2 lines. Compares (A) direct VoiceDesign with the emotion in the instruct,
(A-fr) the same with a French instruct, and the register references that (C) will be cloned in a second step."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from panic_voices import VOICES, instruct, REF_TEXT, FR, FR_REG
J = []
for vid in ("m1_baron", "f1_ingenue"):
    g = VOICES[vid][0]; grp = "panic_" + vid
    for reg, seeds in (("neutral", (701, 702)), ("panic", (711, 712)), ("whisper", (721, 722))):
        for s in seeds:
            J.append({"key": f"pv_{vid}_ref{reg}", "group": grp, "mode": "design", "seed": s, "text": REF_TEXT[reg], "instruct": instruct(vid, reg)})
    for s in (731, 732):
        J.append({"key": f"pv_{vid}_A_malade", "group": grp, "mode": "design", "seed": s, "text": "C'est un malade !", "instruct": instruct(vid, "panic")})
    for s in (741, 742):
        J.append({"key": f"pv_{vid}_A_rienvu", "group": grp, "mode": "design", "seed": s, "text": "Je n'ai rien vu, et vous ?", "instruct": instruct(vid, "whisper")})
    J.append({"key": f"pv_{vid}_Afr_malade", "group": grp, "mode": "design", "seed": 751, "text": "C'est un malade !", "instruct": FR[vid] + " " + FR_REG[(g, "panic")]})
    J.append({"key": f"pv_{vid}_Afr_rienvu", "group": grp, "mode": "design", "seed": 761, "text": "Je n'ai rien vu, et vous ?", "instruct": FR[vid] + " " + FR_REG[(g, "whisper")]})
    for s in (771, 772):
        J.append({"key": f"pv_{vid}_scream", "group": grp, "mode": "design", "seed": s, "text": "Aaaaaaah !", "instruct": instruct(vid, "scream")})
json.dump(J, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "panic_pilot.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print(len(J))
