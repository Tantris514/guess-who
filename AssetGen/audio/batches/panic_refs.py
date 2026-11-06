"""Register references for every guest voice (VoiceDesign, 2 seeds each; the best take per voice/register becomes the clone
reference) + TTS screams / gasps. The pilot already made neutral/panic/whisper refs and screams for m1_baron and f1_ingenue."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from panic_voices import VOICES, instruct, REF_TEXT
PILOT = ("m1_baron", "f1_ingenue")
J = []
for i, vid in enumerate(VOICES):
    grp = "panic_" + vid
    regs = ["awkward"] if vid in PILOT else ["neutral", "panic", "awkward", "whisper"]
    for reg in regs:
        for s in (701 + 10 * ["neutral", "panic", "whisper", "awkward"].index(reg) + k for k in (0, 1)):
            J.append({"key": f"pv_{vid}_ref{reg}", "group": grp, "mode": "design", "seed": s, "text": REF_TEXT[reg], "instruct": instruct(vid, reg)})
    if vid not in PILOT:
        for s in (771, 772):
            J.append({"key": f"pv_{vid}_scream", "group": grp, "mode": "design", "seed": s, "text": "Aaaaaaah !", "instruct": instruct(vid, "scream")})
    J.append({"key": f"pv_{vid}_gasp", "group": grp, "mode": "design", "seed": 781, "text": "Ah !", "instruct": instruct(vid, "gasp")})
json.dump(J, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "panic_refs.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print(len(J))
