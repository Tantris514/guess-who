"""Register references for every character voice (voice_id = char_id) that has no reference yet:
roster characters: neutral x2, panic, whisper, awkward, warm, gossip, startled; other characters: neutral x2, panic,
whisper, warm, gossip; the detective: neutral x2. Characters whose card equals an existing voice reuse it (ALIAS)."""
import json, os, sys
AUD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, AUD)
from panic_voices import VOICES, ALIAS, instruct, REF_TEXT
S = json.load(open(os.path.join(AUD, "script", "voice_script.json"), encoding="utf-8"))
ROSTER = ["char_colonel", "char_comte", "char_f_gown", "char_m_tailcoat", "char_minuit", "char_odette"]
SEED = {"neutral": (701, 702), "panic": (711,), "whisper": (721,), "awkward": (731,), "startled": (741,), "warm": (751,), "gossip": (761,)}
out = {"roster": [], "others": []}
for v in S["voices"]:
    vid = v["voice_id"]
    if vid in ALIAS:
        continue
    if vid in ROSTER:
        regs = ["neutral", "panic", "whisper", "awkward", "warm", "gossip", "startled"]
    elif v.get("role") == "detective":
        regs = ["neutral"]
    else:
        regs = ["neutral", "panic", "whisper", "warm", "gossip"]
    for reg in regs:
        for s in SEED[reg]:
            (out["roster"] if vid in ROSTER else out["others"]).append(
                {"key": f"pv_{vid}_ref{reg}", "group": "voice_" + vid, "mode": "design", "seed": s, "text": REF_TEXT[reg],
                 "instruct": instruct(vid, reg)})
for k, J in out.items():
    json.dump(J, open(os.path.join(AUD, "batches", f"char_refs_{k}.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(k, len(J))
