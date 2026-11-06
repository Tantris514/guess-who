"""Master the selected candidates (panic / event voices, screams, piano, event SFX and music) into game-ready 44.1 kHz WAVs
in final/panic and write final/panic/panic_report.json (one entry per file).

  python -X utf8 panic_master.py [--cats a,b]     (reads qa/panic_selection.json, written by panic_select.py)

Loudness (BS.1770, true peak <= -1 dBTP; the majordome VO_* lines sit at -17 LUFS, the gunshot at -11.6 max momentary):
  voices, by register: panic/threat -14, manic -13, startled -16, neutral/awkward/laugh -18, maniac laugh -15, whisper -21,
                       robot -15 LUFS integrated;  screams -10 LUFS max momentary
  piano / sfx one-shots: max momentary target per item;  loops: integrated target, crossfaded seamless loop
  music: beat-aligned loop (same search as the MUS_* loops), -16 LUFS
Voices are mono and dry (UE spatialises them), 70-90 Hz high-pass, DC removed, trimmed (no leading/trailing silence), short
fades. Whispered lines: the murmured TTS take is whisperised (LPC + noise source, 15 % of the voice kept, panic_dsp.py).
Robot lines: LPC vocoder on a 58 Hz pulse train + metallic comb (panic_dsp.py)."""
import argparse, json, math, os, sys
import numpy as np
from scipy import signal
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import audiolib as A  # noqa: E402
import panic_dsp as D  # noqa: E402
from panic_voices import VOICES  # noqa: E402

OUT = os.path.join(HERE, "final", "panic"); os.makedirs(OUT, exist_ok=True)
QA = os.path.join(HERE, "qa")
REPORT = os.path.join(OUT, "panic_report.json")
SR = 44100
REG_LUFS = {"panic": -14.0, "threat": -14.0, "manic": -13.0, "startled": -16.0, "neutral": -18.0, "awkward": -18.0,
            "laugh": -18.0, "maniac_laugh": -15.0, "whisper": -21.0, "flat": -15.0}
VOICE_CATS = ("shout", "calm", "chatter", "reply", "piano_react", "attack", "fire", "blackout", "kamikaze", "robot")


def importer_category(it):
    """Category names read by Tools/gameplay/s31_reactions.py."""
    c = it["category"]
    if c == "attack":
        return "attack_bandit" if it.get("speaker") == "bandit" else "attack_guest"
    if c in ("fire", "blackout"):
        return c + "_after" if it.get("phase") == "after" else c
    if c == "robot":
        return "robot_voice"
    return c


def resample(x, sr):
    if sr == SR:
        return x
    g = math.gcd(sr, SR)
    return signal.resample_poly(x, SR // g, sr // g, axis=0)


def trim(x, sr, floor_db, pre=0.012, post=0.03, fade_in=0.004, fade_out=0.06):
    env = np.abs(x[:, 0])
    win = max(1, int(0.005 * sr))
    env = np.convolve(env, np.ones(win) / win, mode="same")
    thr = 10 ** (floor_db / 20) * env.max()
    idx = np.where(env > thr)[0]
    s = max(0, idx[0] - int(pre * sr)); e = min(len(x), idx[-1] + int(post * sr))
    y = x[s:e].copy()
    fi = int(fade_in * sr); y[:fi] *= np.linspace(0, 1, fi)[:, None]
    fo = min(len(y) // 4, int(fade_out * sr)); y[-fo:] *= np.linspace(1, 0, fo)[:, None] ** 2
    return y


def master_voice(it):
    x, sr = A.load(it["source"])
    x = A.to_mono(x); x = x - x.mean()
    if it.get("cut"):  # [start_s, end_s] window inside a long non-verbal take
        x = x[int(it["cut"][0] * sr): int(it["cut"][1] * sr)]
    reg = it.get("register")
    if reg == "whisper":
        x = D.whisperise(x[:, 0], sr, it.get("voice_mix", 0.15))[:, None]
    if it["category"] == "robot":
        x = D.robotise(x[:, 0], sr)[:, None]
    x = A.highpass(x, sr, 90 if it["category"] in ("scream", "shout") or reg in ("panic", "manic", "threat") else 70)
    x = resample(x, sr)
    y = trim(x, SR, -40 if reg in ("panic", "manic", "threat") or it["category"] == "scream" else -42)
    if it.get("keep") and len(y) > it["keep"] * SR:   # long non-verbal takes (laughs): keep the start, fade out
        y = y[: int(it["keep"] * SR)]
        fo = int(0.35 * SR); y[-fo:] *= np.linspace(1, 0, fo)[:, None] ** 2
    if it["category"] == "scream":
        y, g, lim = A.gain_to(y, SR, target_mom=-10.0 + it.get("gain_db", 0.0), tp_ceiling=-1.0)
    else:
        y, g, lim = A.gain_to(y, SR, target_lufs=REG_LUFS.get(reg, -18.0) + it.get("gain_db", 0.0), tp_ceiling=-1.0)
    return y - y.mean(), g, lim, {}


def master_fx(it):
    x, sr = A.load(it["source"])
    if it.get("mono", True):
        x = A.to_mono(x)
    x = x - x.mean(axis=0)
    x = A.highpass(x, sr, it.get("hp", 30))
    x = resample(x, sr)
    if it.get("cut"):
        x = x[int(it["cut"][0] * SR): int(it["cut"][1] * SR)]
    info = {}
    kind = it.get("kind", "oneshot")
    if kind == "music":
        lp = A.find_music_loop(x, SR, it.get("min_len", 30), it.get("max_len", 60), xfade=0.5, skip_start=2.0, avoid_end=4.0)
        y = A.make_loop(x, SR, lp["start"], lp["end"], 0.5)
        info = {"loop": lp, "seam": A.seam_report(y, SR)}
        y, g, lim = A.gain_to(y, SR, target_lufs=it.get("lufs", -16.0), tp_ceiling=-1.0)
    elif kind == "loop":
        s, e = A.find_ambience_loop(x, SR, xfade=2.0)
        y = A.make_loop(x, SR, s, e, 2.0)
        info = {"seam": A.seam_report(y, SR)}
        y, g, lim = A.gain_to(y, SR, target_lufs=it.get("lufs", -24.0), tp_ceiling=-3.0)
    else:
        y = trim(x, SR, it.get("floor_db", -55), pre=0.004, post=0.0, fade_in=0.001, fade_out=it.get("fade_out", 0.25))
        if it.get("keep") and len(y) > it["keep"] * SR:
            y = y[: int(it["keep"] * SR)]
            fo = int(min(0.6, it["keep"] / 3) * SR); y[-fo:] *= np.linspace(1, 0, fo)[:, None] ** 2
        if it.get("lufs") is not None:
            y, g, lim = A.gain_to(y, SR, target_lufs=it["lufs"], tp_ceiling=-1.0)
        else:
            y, g, lim = A.gain_to(y, SR, target_mom=it.get("mom", -10.0), tp_ceiling=-1.0)
    return y - y.mean(axis=0), g, lim, info


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--cats", default=""); ap.add_argument("--names", default="")
    a = ap.parse_args()
    cats = set(a.cats.split(",")) if a.cats else None
    names = set(a.names.split(",")) if a.names else None
    sel = json.load(open(os.path.join(QA, "panic_selection.json"), encoding="utf-8"))
    qa = json.load(open(os.path.join(QA, "panic_qa.json"), encoding="utf-8"))
    report = {e["file"]: e for e in json.load(open(REPORT, encoding="utf-8"))} if os.path.exists(REPORT) else {}
    for it in sel:
        if (cats and it["category"] not in cats and importer_category(it) not in cats) or (names and it["name"] not in names):
            continue
        voice = it["category"] in VOICE_CATS or it["category"] == "scream"
        out = os.path.join(OUT, it["name"] + ".wav")
        mixes = (0.15, 0.3, 0.5, 1.0) if it.get("whispered") else (None,)
        for mix in mixes:   # whispered lines: keep more of the murmur until the processed file is understood again
            if mix is not None:
                it["voice_mix"] = mix
            y, g, lim, info = (master_voice if voice else master_fx)(it)
            A.save_wav(out, y, SR)
            if mix is None or mix == mixes[-1]:
                break
            import panic_qa as Q
            from panic_select import asr_fix
            import difflib
            h = Q.asr(out); wm, cm = Q.word_match(it["text"], h)
            if wm >= 0.75 or cm >= 0.88 or difflib.SequenceMatcher(None, Q.norm(it["text"]), asr_fix(h).split()).ratio() >= 0.75:
                break
        y2, _ = A.load(out)
        m = A.metrics(y2, SR)
        q = qa.get(os.path.basename(it["source"]), {})
        e = {"file": os.path.basename(out), "category": importer_category(it)}
        if voice:
            v = VOICES.get(it.get("voice_id")) or (it.get("gender"), it.get("voice_label"), it.get("voice_description"))
            e.update({"gender": it.get("gender"), "voice_id": it.get("voice_id"), "voice_label": v[1], "voice_description": v[2],
                      "register": it.get("register"), "text": it.get("text"), "whispered": bool(it.get("whispered", False)),
                      "whisper_voice_mix": it.get("voice_mix") if it.get("whispered") else None,
                      "murmured": bool(it.get("whispered")) and it.get("voice_mix") == 1.0,
                      "nonverbal": bool(it.get("nonverbal", it["category"] == "scream"))})
            for k in ("speaker", "phase"):
                if k in it:
                    e[k] = it[k]
        else:
            e.update({"description": it.get("description"), "kind": it.get("kind", "oneshot")})
        e.update({"duration_s": m["duration"], "lufs": m["lufs"], "max_momentary_lufs": m["max_momentary_lufs"],
                  "true_peak_dbtp": m["true_peak_dbtp"], "sample_rate": m["sr"], "channels": m["channels"],
                  "lead_silence_s": m["lead_silence_s"], "trail_silence_s": m["trail_silence_s"], "gain_db": g, "limited": lim})
        if info:
            e.update(info)
        e.update({"generator": it.get("generator"), "source_candidate": os.path.relpath(it["source"], HERE).replace("\\", "/"),
                  "seed": q.get("seed"), "speaker_sim_to_ref": it.get("speaker_sim_to_ref"), "notes": it.get("notes", "")})
        if e.get("murmured"):
            e["whispered"] = False
            e["notes"] = (e.get("notes", "") + " Murmured, not whispered: the whisper processing made it unintelligible to ASR.").strip()
        if voice and not e.get("nonverbal"):
            # ASR of the mastered file itself (what the player hears, after trim / whisperising / robot processing)
            import difflib
            import panic_qa as Q
            from panic_select import asr_fix
            heard = Q.asr(out)
            wm, cm = Q.word_match(it["text"], heard)
            hom = difflib.SequenceMatcher(None, Q.norm(it["text"]), asr_fix(heard).split()).ratio()
            ok = wm >= 0.75 or cm >= 0.88 or hom >= 0.75
            e.update({"asr_transcript": heard, "asr_word_match": wm, "asr_char_match": cm, "asr_match": ok,
                      "asr_source_take_transcript": q.get("heard")})
            if ok and wm < 0.75 and cm < 0.88:
                e["notes"] = (e.get("notes", "") + " (ASR match via homophone: same sounds)").strip()
        if e.get("asr_match") is False:
            # not understood after mastering: keep it out of the game, blacklist the take so the next pass picks another one
            os.makedirs(os.path.join(OUT, "_rejected"), exist_ok=True)
            os.replace(out, os.path.join(OUT, "_rejected", e["file"]))
            bl_p = os.path.join(QA, "panic_rejected.json")
            bl = json.load(open(bl_p, encoding="utf-8")) if os.path.exists(bl_p) else {}
            bl[os.path.basename(it["source"])] = f"final ASR failed: heard '{e['asr_transcript']}'"
            json.dump(bl, open(bl_p, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
            report.pop(e["file"], None); write_report(report)
            print(f"REJECTED {e['file']} heard: {e['asr_transcript']}", flush=True)
            continue
        report[e["file"]] = e
        write_report(report)   # after every file: a crash (low RAM) never loses what is already mastered
        A.spectrogram_png(os.path.join(QA, "panic_png", "final_" + it["name"] + ".png"), y2, SR, it["name"])
        print(f"{e['file']:36s} dur={m['duration']:5.2f} lufs={m['lufs']:6.1f} mom={m['max_momentary_lufs']:6.1f} tp={m['true_peak_dbtp']:5.1f} "
              f"lead={m['lead_silence_s']:.2f} trail={m['trail_silence_s']:.2f} gain={g:+.1f} lim={lim}", flush=True)
    print(write_report(report), "files in report")


GUN_RE = None


def tag_entries(rows):
    """Legacy ids, cause / gun tags and dup_of (same sentence already in the bank) for the voice director (VOIX_ARCHITECTURE.md)."""
    import re
    import unicodedata
    global GUN_RE
    GUN_RE = GUN_RE or re.compile(r"(tir[eé]|tire|armes?|arm[eé]s?|fusil|pistolet|revolver|balle|assassin|il est fou|c.est un malade)")
    seen = {}
    for e in rows:
        if "text" not in e or e.get("nonverbal"):
            continue
        t = e.get("text") or ""
        e.setdefault("line_id", "LEG_" + os.path.splitext(e["file"])[0])
        e["legacy"] = True
        low = t.lower()
        e["gun"] = bool(GUN_RE.search(low))
        c = e["category"]
        if c == "shout":
            e["cause"] = "gun" if e["gun"] else "generic"
        elif c.startswith("fire"):
            e["cause"] = "fire"
        elif c.startswith("blackout"):
            e["cause"] = "blackout"
        elif c == "kamikaze":
            e["cause"] = "explosion"
        elif c.startswith("attack"):
            e["cause"] = "gun"
        key = " ".join(re.sub(r"[^a-z ]+", " ", "".join(ch for ch in unicodedata.normalize("NFKD", low) if not unicodedata.combining(ch))).split())
        if key in seen:
            e["dup_of"] = seen[key]
        else:
            e.pop("dup_of", None)
            seen[key] = e["file"]
    return rows


def write_report(report):
    order = {c: i for i, c in enumerate(["scream", "shout", "calm", "piano", "chatter", "reply", "piano_react", "attack_guest", "attack_bandit",
                                         "fire", "fire_after", "blackout", "blackout_after", "kamikaze", "robot_voice", "sfx", "music"])}
    rows = tag_entries(sorted(report.values(), key=lambda e: (order.get(e["category"], 99), e["file"])))
    # the engine never repeats a sentence: a second voice saying the same text is dropped from the bank (file kept aside)
    dups = [e for e in rows if e.get("dup_of")]
    if dups:
        os.makedirs(os.path.join(OUT, "_rejected", "dups"), exist_ok=True)
        for e in dups:
            src = os.path.join(OUT, e["file"])
            if os.path.exists(src):
                os.replace(src, os.path.join(OUT, "_rejected", "dups", e["file"]))
            report.pop(e["file"], None)
        rows = [e for e in rows if not e.get("dup_of")]
    tmp = REPORT + ".tmp"
    json.dump(rows, open(tmp, "w", encoding="utf-8"), indent=1, ensure_ascii=False, default=lambda o: o.item() if hasattr(o, "item") else str(o))
    os.replace(tmp, REPORT)
    return len(rows)


if __name__ == "__main__":
    main()
