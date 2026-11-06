"""Per-character voice assets (VOIX_ARCHITECTURE.md principle 2: one character = one voice, voice_id = char_id):
  AssetGen/voices/<char_id>/voice.json   voice_id, display name, gender, age, card, personality, reference takes per register
  AssetGen/voices/<char_id>/ref.wav      the neutral reference (44.1 kHz mono, -18 LUFS): what this character sounds like
  AssetGen/voices/<char_id>/lines/       a copy of every published line of this character + index.json
  AssetGen/manifest.json                 the character entry gets "voice": <voice.json path>
  Voix (personnages)/<display> (<char_id>).wav   listening copy of ref.wav for the user
Re-runnable, incremental.  python -X utf8 voice_assets.py"""
import glob, json, os, re, shutil, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.dirname(os.path.dirname(HERE))           # J:\Projets\Unreal_Projects\Guess Who
VOICES_DIR = os.path.join(os.path.dirname(HERE), "voices")
LISTEN = os.path.join(ROOT, "Voix (personnages)")
MANIFEST = os.path.join(os.path.dirname(HERE), "manifest.json")


def safe(s):
    return re.sub(r'[<>:"/\\|?*]', "-", s).strip()


def main():
    import audiolib as A
    import panic_master as M
    S = json.load(open(os.path.join(HERE, "script", "voice_script.json"), encoding="utf-8"))
    refs = json.load(open(os.path.join(HERE, "qa", "panic_refs.json"), encoding="utf-8"))
    qa = json.load(open(os.path.join(HERE, "qa", "panic_qa.json"), encoding="utf-8"))
    reports = {}
    for rp in glob.glob(os.path.join(HERE, "final", "*", "*_report.json")):
        for e in json.load(open(rp, encoding="utf-8")):
            if str(e.get("voice_id", "")).startswith("char_"):
                reports.setdefault(e["voice_id"], []).append((os.path.dirname(rp), e))
    os.makedirs(LISTEN, exist_ok=True)
    done = []
    from panic_voices import EXTRA_CHARS   # characters added after the content script (e.g. char_aviatrice)
    voices = list(S["voices"]) + [{"voice_id": c, "gender": g, "display": d, "age": age, "role": "guest", "card": card}
                                  for c, (g, d, age, card) in EXTRA_CHARS.items() if c not in {v["voice_id"] for v in S["voices"]}]
    for v in voices:
        cid = v["voice_id"]
        r = refs.get(cid)
        reg = next((k for k in ("neutral", "threat", "manic", "flat", "panic") if r and isinstance(r.get(k), str) and r[k] in qa), None)
        if not reg:
            continue
        d = os.path.join(VOICES_DIR, cid); os.makedirs(os.path.join(d, "lines"), exist_ok=True)
        ref_src = qa[r[reg]]["file"]
        ref_wav = os.path.join(d, "ref.wav")
        if not os.path.exists(ref_wav) or os.path.getmtime(ref_wav) < os.path.getmtime(ref_src):
            y, g, lim, _ = M.master_voice({"source": ref_src, "category": "robot" if reg == "flat" else "remark", "register": reg})
            A.save_wav(ref_wav, y, M.SR)
            shutil.copyfile(ref_wav, os.path.join(LISTEN, f"{safe(v.get('display', cid))} ({cid}).wav"))
        meta = {"voice_id": cid, "display": v.get("display"), "gender": v["gender"], "age": v.get("age"), "role": v.get("role"),
                "card": v["card"], "personality": v.get("personality"), "ref_wav": ref_wav,
                "references": {k: qa[t]["file"] for k, t in r.items() if isinstance(t, str) and t in qa},
                "alias_of": r.get("alias_of"), "generator": "Qwen3-TTS 1.7B VoiceDesign (card) -> VoiceClone for every line"}
        index = []
        for folder, e in sorted(reports.get(cid, []), key=lambda x: x[1]["file"]):
            src = os.path.join(folder, e["file"])
            dst = os.path.join(d, "lines", e["file"])
            if os.path.exists(src) and (not os.path.exists(dst) or os.path.getmtime(dst) < os.path.getmtime(src)):
                shutil.copyfile(src, dst)
            index.append({k: e.get(k) for k in ("file", "category", "text", "line_id", "dialogue_id", "turn", "speaker", "cause",
                                                 "whispered", "nonverbal", "gun", "duration_s")})
        meta["lines"] = len(index)
        json.dump(meta, open(os.path.join(d, "voice.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
        json.dump(index, open(os.path.join(d, "lines", "index.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
        done.append((cid, len(index)))
    # manifest "voice" field (atomic read-modify-write; only the character entries that have a voice asset)
    if done and os.path.exists(MANIFEST):
        m = json.load(open(MANIFEST, encoding="utf-8"))
        changed = False
        for a in m.get("assets", []):
            if a.get("kind") == "character" and a.get("name") in dict(done):
                p = os.path.join(VOICES_DIR, a["name"], "voice.json")
                if a.get("voice") != p:
                    a["voice"] = p; changed = True
        if changed:
            json.dump(m, open(MANIFEST + ".tmp", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
            os.replace(MANIFEST + ".tmp", MANIFEST)
    print("voice assets:", done)
    return done


if __name__ == "__main__":
    main()
