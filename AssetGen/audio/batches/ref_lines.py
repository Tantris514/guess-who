"""Extra voice lines taken from the register reference takes themselves (each one is a VoiceDesign take of that voice, already
ASR-checked): they need no ComfyUI and give every category something while the clone batch is pending.
Names are numbered from 51 per category so they never collide with the planned lines. -> qa/panic_selection_refs.json"""
import json, os, sys
AUD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, AUD)
from panic_voices import VOICES, REF_TEXT
qa = json.load(open(os.path.join(AUD, "qa", "panic_qa.json"), encoding="utf-8"))
refs = json.load(open(os.path.join(AUD, "qa", "panic_refs.json"), encoding="utf-8"))
E, n = [], {}


def add(cat, vid, take, text, reg, **kw):
    n[cat] = n.get(cat, 50) + 1
    g = VOICES[vid][0]
    cname = "".join(w.capitalize() for w in cat.split("_"))
    E.append(dict(name=f"VO_Panic_{cname}_{n[cat]:02d}_{g}", source=qa[take]["file"], category=cat, gender=g, voice_id=vid, register=reg,
                  text=text, whispered=reg == "whisper", asr_ok=True, nonverbal=False, ref_line=True,
                  generator=f"Qwen3-TTS 1.7B VoiceDesign ({reg} register reference take of this voice)",
                  notes="reference take used as a line (no clone needed)", **kw))


# one reference take per distinct sentence (the engine never repeats a text; same text in several voices is wasted)
add("shout", "m4_colonel", refs["m4_colonel"]["panic"], REF_TEXT["panic"], "panic")
add("calm", "f4_aviatrice", refs["f4_aviatrice"]["awkward"], REF_TEXT["awkward"], "awkward")
add("calm", "m3_bonvivant", refs["m3_bonvivant"]["whisper"], REF_TEXT["whisper"], "whisper")
add("chatter", "f2_comtesse", refs["f2_comtesse"]["neutral"], REF_TEXT["neutral"], "neutral")
add("blackout", "f3_bourgeoise", refs["f3_bourgeoise"]["startled"], REF_TEXT["startled"], "startled", phase="during")
add("attack", "b1_brute", refs["b1_brute"]["threat"], REF_TEXT["threat"], "threat", speaker="bandit")
add("kamikaze", "k1_kamikaze", "pv_k1_kamikaze_refmanic_s762_0.flac", "Ah ! Vous allez tous voir !", "manic", cut=[0.0, 3.0])
add("kamikaze", "k1_kamikaze", "pv_k1_kamikaze_refmanic_s761_0.flac", "Plus personne ne m'arrêtera maintenant ! Plus personne !", "manic",
    cut=[3.5, 7.9])
add("robot", "r1_robot", "pv_r1_robot_refflat_s792_0.flac", REF_TEXT["flat"], "flat")
for e in E:
    if e.get("cut"):
        e["notes"] += f"; cut {e['cut'][0]}-{e['cut'][1]} s from a longer take (word timestamps from faster-whisper)"
json.dump(E, open(os.path.join(AUD, "qa", "panic_selection_refs.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print(len(E))
