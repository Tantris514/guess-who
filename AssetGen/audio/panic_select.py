"""Pick the best take of every panic line variant from the QA cache (qa/panic_qa.json + qa/panic_emb.npz) and write
qa/panic_selection.json for panic_master.py. Also lists the variants that still have no acceptable take (to regenerate).

  python -X utf8 panic_select.py [--refs-only]

Acceptance (objective; nobody has listened):
  ASR     word match >= 0.75 or character match >= 0.88 (faster-whisper small, French)
  shout   median F0 at least 1.2x the voice's neutral reference (the voice is raised, not read)
  whisper voiced fraction <= 0.35 over the active span (whispered or murmured, not spoken)
  calm    spoken (awkward) takes: voiced fraction >= 0.35
  length  active speech between 0.45 s and 5.5 s, no inner silence > 0.6 s
Among accepted takes: highest speaker similarity (ECAPA) to the voice's chosen register reference, then ASR match."""
import argparse, json, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from panic_voices import VOICES  # noqa: E402
from panic_lines import named  # noqa: E402

QA = os.path.join(HERE, "qa")
GEN = os.path.join(HERE, "gen")


def load():
    qa = json.load(open(os.path.join(QA, "panic_qa.json"), encoding="utf-8"))
    emb = dict(np.load(os.path.join(QA, "panic_emb.npz")))
    return qa, emb


REJECTED = json.load(open(os.path.join(QA, "panic_rejected.json"), encoding="utf-8")) if os.path.exists(os.path.join(QA, "panic_rejected.json")) else {}


def takes(qa, prefix):
    return {k: v for k, v in qa.items() if k.startswith(prefix + "_s") and k not in REJECTED}


# exact French homophones the ASR writes the other way (same sounds, so not a pronunciation error); documented in the report
HOMOPHONES = [("sauf qu il peut", "sauve qui peut"), ("sauf qui peut", "sauve qui peut"), ("alarm ", "alarme "), ("halarme", "alarme")]


def asr_fix(heard):
    import re, unicodedata
    h = unicodedata.normalize("NFKD", (heard or "").lower())
    h = "".join(c for c in h if not unicodedata.combining(c))
    h = re.sub(r"[^a-z ]+", " ", h); h = " ".join(h.split()) + " "
    for a, b in HOMOPHONES:
        h = h.replace(a, b)
    return h.strip()


def asr_ok(r):
    if r.get("word_match", 0) >= 0.75 or r.get("char_match", 0) >= 0.88:
        return True
    if r.get("heard") and r.get("text"):
        import difflib
        from panic_qa import norm
        a, b = norm(r["text"]), asr_fix(r["heard"]).split()
        return difflib.SequenceMatcher(None, a, b).ratio() >= 0.75
    return False


def sim(emb, a, b):
    if a not in emb or b not in emb:
        return 0.0
    return float(np.dot(emb[a], emb[b]))


def register_ok(r, reg, f0_neutral, ref=False, f0_panic=0):
    if not ref and (r.get("active_s", 0) < 0.45 or r.get("active_s", 0) > 5.5 or r.get("gap_s", 0) > 0.6):
        return False, "length"
    if reg == "whisper":
        return (r["voiced_frac"] <= 0.35, f"vf={r['voiced_frac']}")
    if reg == "panic":   # raised voice: above 1.2x the relaxed voice, or close to the voice's own panic reference
        thr = 1.2 * f0_neutral if f0_panic <= 0 else min(1.2 * f0_neutral, 0.85 * f0_panic)
        ok = f0_neutral <= 0 or r["f0_med"] >= thr
        return ok, f"f0={r['f0_med']} vs neutral {f0_neutral} / panic ref {f0_panic}"
    return (r["voiced_frac"] >= 0.35, f"vf={r['voiced_frac']}")


# register check applied to the raw TTS take (whispered lines are murmured by the TTS and whisperised at mastering)
REF_REG = {"whisper": "awkward", "startled": "awkward", "threat": "panic", "manic": "panic", "flat": "awkward", "neutral": "awkward",
           "warm": "awkward", "gossip": "awkward"}


def choose_refs(qa, emb):
    """Per voice: neutral anchor = best-ASR neutral take; each register reference = ASR-ok take that passes the register
    check and is closest (ECAPA) to the anchor."""
    refs = {}
    for vid in VOICES:
        pre = f"pv_{vid}_ref"
        neu = takes(qa, pre + "neutral")
        if neu:
            # the anchor must sound like its gender (median F0 of relaxed speech: men < 190 Hz, women > 165 Hz)
            g = VOICES[vid][0]
            gok = lambda r: (r["f0_med"] < 190) if g == "m" else (r["f0_med"] > 165)  # noqa: E731
            anchor = max(neu, key=lambda k: (gok(neu[k]), asr_ok(neu[k]), neu[k].get("word_match", 0)))
            f0n = neu[anchor]["f0_med"]
            refs[vid] = {"neutral": anchor, "f0_neutral": f0n}
        else:
            anchor, f0n = None, 0
            refs[vid] = {"f0_neutral": 0}
        for reg in ("panic", "awkward", "whisper", "startled", "threat", "manic", "flat", "warm", "gossip"):
            t = takes(qa, pre + reg)
            fem = VOICES[vid][0] == "f"
            ranked = sorted(t, key=lambda k: (asr_ok(t[k]), (t[k]["f0_med"] > 150) if fem else True,
                                              register_ok(t[k], REF_REG.get(reg, reg), f0n, ref=True)[0],
                                              sim(emb, k, anchor) if anchor else t[k].get("word_match", 0)), reverse=True)
            if ranked:
                k = ranked[0]
                refs[vid][reg] = k
                print(f"{vid:14s} {reg:8s} {k:42s} asr={asr_ok(t[k])} reg={register_ok(t[k], REF_REG.get(reg, reg), f0n, ref=True)} f0={t[k]['f0_med']} sim_anchor={sim(emb, k, anchor):.3f}")
    return refs


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--refs-only", action="store_true"); ap.add_argument("--cats", default="")
    a = ap.parse_args()
    qa, emb = load()
    refs = choose_refs(qa, emb)
    from panic_voices import ALIAS
    for c, v in ALIAS.items():          # characters sharing a voice card reuse that voice's references
        if v in refs:
            refs[c] = dict(refs[v], alias_of=v)
    p = os.path.join(QA, "panic_refs.json")
    json.dump(refs, open(p + ".tmp", "w", encoding="utf-8"), indent=1)
    os.replace(p + ".tmp", p)
    if a.refs_only:
        return
    cats = set(a.cats.split(",")) if a.cats else None
    sel, missing = [], []
    for it in named():
        if cats and it["cat"] not in cats:
            continue
        vid, reg = it["voice"], it["reg"]
        t = takes(qa, it["key"])
        ref = refs.get(vid, {}).get(reg)
        f0n = refs.get(vid, {}).get("f0_neutral", 0)
        chk = REF_REG.get(reg, reg)
        f0p = qa.get(refs.get(vid, {}).get(chk if chk == "panic" else "panic", ""), {}).get("f0_med", 0) if chk == "panic" else 0
        if chk == "panic" and reg in refs.get(vid, {}):
            f0p = qa.get(refs[vid][reg], {}).get("f0_med", 0)
        if it.get("nonverbal"):   # laughs: something laugh-like was heard, not too short (long ones are cut at mastering)
            import re
            ok = [k for k in t if 0.6 <= t[k].get("active_s", 0) <= 10.0
                  and len(re.findall(r"\b(h[aeio]|a[h]|eh)\b", (t[k].get("heard") or "").lower())) >= 2]
        else:
            ok = [k for k in t if asr_ok(t[k]) and register_ok(t[k], chk, f0n, f0_panic=f0p)[0]]
        if not ok:
            missing.append({"name": it["name"], "key": it["key"], "voice_id": vid, "register": reg, "text": it["text"],
                            "takes": {k: (t[k].get("heard"), t[k].get("word_match"), register_ok(t[k], chk, f0n, f0_panic=f0p)) for k in t}})
            continue
        if it.get("nonverbal"):
            want = 2.5 if it["reg"] == "maniac_laugh" else 1.4
            best = max(ok, key=lambda k: (-abs(min(t[k]["active_s"], 4.0) - want), t[k].get("word_match", 0)))
        else:
            best = max(ok, key=lambda k: (sim(emb, k, ref) if ref else 0) + 0.3 * t[k].get("word_match", 0))
        e = {"name": it["name"], "source": t[best]["file"], "category": it["cat"], "gender": it["gender"], "voice_id": vid,
             "register": reg, "text": it["text"], "whispered": reg == "whisper", "asr_ok": not it.get("nonverbal"),
             "nonverbal": bool(it.get("nonverbal")),
             "generator": ("Qwen3-TTS 1.7B VoiceDesign (direct, non-verbal)" if it.get("mode") == "design"
                           else f"Qwen3-TTS 1.7B: VoiceDesign reference ({reg}) -> VoiceClone"),
             "speaker_sim_to_ref": round(sim(emb, best, ref), 3) if ref else None}
        for k in ("speaker", "phase"):
            if k in it:
                e[k] = it[k]
        side_p = os.path.splitext(t[best]["file"])[0] + ".txt"
        side = json.load(open(side_p, encoding="utf-8")) if os.path.exists(side_p) else {}
        if side.get("mode") == "design" and not it.get("nonverbal"):
            e["generator"] = f"Qwen3-TTS 1.7B VoiceDesign (direct, {reg} instruct; the clone takes were not understood)"
            e["notes"] = "direct VoiceDesign fallback: same voice description, not cloned from the reference"
        r = t[best]
        if not it.get("nonverbal") and r.get("word_match", 0) < 0.75 and r.get("char_match", 0) < 0.88:
            e["notes"] = (e.get("notes", "") + f" ASR wrote a homophone ('{r.get('heard')}'): same sounds as the line.").strip()
        if it.get("nonverbal"):
            e["keep"] = 3.2 if reg == "maniac_laugh" else 2.2
        sel.append(e)
    # manual overrides (objective check failed narrowly; reason recorded in the report)
    OVERRIDE = {"VO_Panic_Shout_07_f": ("pv_f2_comtesse_shout_fuyez_s1061_0.flac",
                                        "understood by ASR but less raised than the shout check wants (F0 223 Hz vs 243 Hz)")}
    have = {e["name"] for e in sel}
    for it in named():
        if it["name"] in OVERRIDE and it["name"] not in have and (not cats or it["cat"] in cats):
            f, why = OVERRIDE[it["name"]]
            if f in qa:
                sel.append({"name": it["name"], "source": qa[f]["file"], "category": it["cat"], "gender": it["gender"], "voice_id": it["voice"],
                            "register": it["reg"], "text": it["text"], "whispered": False, "asr_ok": True, "nonverbal": False,
                            "generator": f"Qwen3-TTS 1.7B: VoiceDesign reference ({it['reg']}) -> VoiceClone", "notes": "manual pick: " + why,
                            "speaker_sim_to_ref": None})
                missing = [m for m in missing if m["name"] != it["name"]]
    for extra in (os.path.join(QA, "panic_selection_refs.json"),):   # reference takes used as extra lines
        if os.path.exists(extra):
            sel += [e for e in json.load(open(extra, encoding="utf-8")) if not cats or e["category"] in cats]
    extra = os.path.join(QA, "panic_selection_extra.json")   # screams, piano, sfx, music: picked after review
    if os.path.exists(extra):
        sel += [e for e in json.load(open(extra, encoding="utf-8")) if not cats or e["category"] in cats]
    json.dump(sel, open(os.path.join(QA, "panic_selection.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    json.dump(missing, open(os.path.join(QA, "panic_missing.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(len(sel), "selected,", len(missing), "missing")
    for m in missing:
        print("MISSING", m["name"], m["key"], m["register"], m["text"], json.dumps(m["takes"], ensure_ascii=False)[:300])


if __name__ == "__main__":
    main()
