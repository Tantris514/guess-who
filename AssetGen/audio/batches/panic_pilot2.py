"""Pilot 2: (C) clone the pilot lines from the register references; whisper instruct variants (the first whisper refs came out voiced)."""
import json, os, shutil, sys
AUD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, AUD)
from panic_voices import VOICES, REF_TEXT
J = []
REFS = {("m1_baron", "panic"): "pv_m1_baron_refpanic_s711_0", ("f1_ingenue", "panic"): "pv_f1_ingenue_refpanic_s712_0",
        ("m1_baron", "whisper"): "pv_m1_baron_refwhisper_s721_0", ("f1_ingenue", "whisper"): "pv_f1_ingenue_refwhisper_s722_0"}
for (vid, reg), take in REFS.items():
    ref = f"gw_panic_{vid}_{reg}_pilot.flac"
    shutil.copyfile(os.path.join(AUD, "gen", "panic_" + vid, take + ".flac"), os.path.join(r"V:\ComfyUI\input", ref))
    text = "C'est un malade !" if reg == "panic" else "Je n'ai rien vu, et vous ?"
    for s in (901, 902):
        J.append({"key": f"pv_{vid}_C_{'malade' if reg == 'panic' else 'rienvu'}", "group": "panic_" + vid, "mode": "clone", "seed": s,
                  "text": text, "ref": ref, "ref_text": REF_TEXT[reg]})
for vid in ("m1_baron", "f1_ingenue"):
    g, lab, card = VOICES[vid]
    he = "he" if g == "m" else "she"
    W = {"W1": f"{card} Now {he} is whispering: a hushed, breathy whisper with no voiced sound at all, only air, like telling a secret in a library.",
         "W2": f"{card} 用气声说悄悄话，非常小声，几乎没有声带振动。",
         "W3": "Whispering, very soft breathy voice, intimate and secretive, no vocal cord vibration. " + card}
    for w, ins in W.items():
        J.append({"key": f"pv_{vid}_{w}_rienvu", "group": "panic_" + vid, "mode": "design", "seed": 723, "text": "Je n'ai rien vu, et vous ?", "instruct": ins})
json.dump(J, open(os.path.join(AUD, "batches", "panic_pilot2.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print(len(J))
