"""Voice production for VOIX_ARCHITECTURE.md (night of 2026-11-02): scripts -> clone jobs -> QA -> selection -> mastering ->
one report per batch (AssetGen/audio/final/<batch>/<batch>_report.json, read by Tools/gameplay/s31_reactions.py).

Scripts live in AssetGen/audio/scripts/<batch>.py and define ITEMS: dicts with
  cat ('dialogue'|'remark'|'greet'|'shout'|'calm'|'fire'|'blackout'|'attack_guest'|'kamikaze'|'robot_voice'|'piano_react'|
       'laugh'|'gasp'|'murmur'|...), text, voice (voice id) or gender ('m'/'f': auto-cast), reg (register reference to clone
  from: neutral / panic / whisper / awkward / startled / threat / manic / flat; 'design:<reg>' = direct VoiceDesign),
  optional dialogue_id + turn + speaker ('A'/'B'), cause (gun/fire/explosion/blackout/generic), whispered, gun, nonverbal.

  python -X utf8 vox.py jobs BATCH [--seeds 1] [--seed-base 0] [--only-missing]  -> batches/vox_BATCH[_rN].json
  python -X utf8 vox.py publish BATCH                                           -> QA, pick, master, report, missing list
  python -X utf8 vox.py check                                                   -> every script: duplicate texts, casting
Every sentence must be unique across ALL scripts and the earlier panic bank (checked by `check` and by `jobs`)."""
import argparse, difflib, glob, hashlib, importlib.util, json, os, re, shutil, sys, unicodedata
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from panic_voices import VOICES, ROLE, REF_TEXT, instruct  # noqa: E402

SCRIPTS = os.path.join(HERE, "scripts")
QA = os.path.join(HERE, "qa")
FINAL = os.path.join(HERE, "final")
COMFY_IN = r"V:\ComfyUI\input"
from panic_voices import ALIAS  # noqa: E402
# VOIX_ARCHITECTURE.md principle 2 (voice = character): every line is cast on a character voice. My own scripts (written
# before the character cast) are re-cast on the guest characters; their explicit generic voices become the character
# that uses that voice (voice map), or the line is dropped when no character has that voice.
OWN = {"dlg1", "dlg2", "dlg3", "rmk1", "shout1", "event1", "greet1", "nv1"}
STAFF_CHARS = {"char_barman", "char_junkie", "char_waiter", "char_bandit", "char_bandit2", "char_kamikaze", "char_robot", "char_detective"}
GUESTS = [v for v in VOICES if v.startswith("char_") and v not in STAFF_CHARS]
TO_CHAR = {g: c for c, g in ALIAS.items()}


def norm(s):
    s = unicodedata.normalize("NFKD", s.lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return " ".join(re.sub(r"[^a-z ]+", " ", s).split())


def voicemap():
    p = os.path.join(SCRIPTS, "_voicemap.json")
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {}


def load_script(batch):
    if SCRIPTS not in sys.path:
        sys.path.insert(0, SCRIPTS)
    p = os.path.join(SCRIPTS, batch + ".py")
    spec = importlib.util.spec_from_file_location("vox_" + batch, p)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    items = []
    vm = voicemap()
    for i, it in enumerate(m.ITEMS):
        it = dict(it)
        it.setdefault("reg", "neutral")
        if batch in OWN and it.get("voice"):
            if it["voice"] in TO_CHAR:
                it["voice"] = TO_CHAR[it["voice"]]
            elif not it["voice"].startswith("char_"):
                continue   # written for a generic voice that no character uses
        if it.get("voice") and it["voice"] not in VOICES:
            mapped = vm.get(it["voice"])
            it["char_id"] = it["voice"]
            it["voice"] = mapped if isinstance(mapped, str) and mapped in VOICES else None
            if not it["voice"] and not it.get("gender") and isinstance(mapped, dict):
                it["gender"] = mapped.get("gender")
        it["batch"] = batch
        it["key"] = f"vx_{batch}_{i:04d}"
        items.append(it)
    if batch in OWN:   # a dialogue that lost a speaker is dropped whole
        dl = {}
        for it in items:
            if "dialogue_id" in it:
                dl.setdefault(it["dialogue_id"], []).append(it)
        n_turns = {}
        for it in m.ITEMS:
            if "dialogue_id" in it:
                n_turns[it["dialogue_id"]] = n_turns.get(it["dialogue_id"], 0) + 1
        items = [it for it in items if "dialogue_id" not in it or len(dl[it["dialogue_id"]]) == n_turns[it["dialogue_id"]]]
    cast(items)
    return items


def _h(s):
    return int(hashlib.md5(s.encode()).hexdigest()[:8], 16)


MENTION = {"char_colonel": ("colonel",), "char_comte": ("comte", "vasilescu"), "char_hortense_gown": ("duchesse", "hortense"),
           "char_barnabe": ("majordome", "barnabe"), "char_rajan": ("prince", "rajan"), "char_tex": ("americain", "texas", "tex"),
           "char_vivienne_gown": ("actrice", "starlette", "vivienne"), "char_lou_gown": ("chanteuse", "lou"), "char_sonny": ("sonny",),
           "char_ophelie_gown": ("veuve", "ophelie"), "char_rosalie": ("rosalie", "femme de chambre"), "char_clara": ("journaliste", "clara"),
           "char_mei_gown": ("mei",), "char_lucien": ("chauffeur", "lucien"), "char_tony": ("tony", "gangster"), "char_morel": ("capitaine", "morel"),
           "char_ambroise": ("professeur", "ambroise"), "char_odette": ("odette",), "char_minuit": ("minuit",),
           "m5_americain": ("americain",), "m11_prince": ("prince", "tsar", "russe"), "m4_colonel": ("colonel",),
           "f2_comtesse": ("comtesse",), "f5_duchesse": ("duchesse",), "f12_marquise": ("marquise",), "f6_actrice": ("actrice",),
           "m7_docteur": ("docteur",), "m9_poete": ("poete",), "m1_baron": ("baron",), "f8_anglaise": ("anglaise", "anglais"),
           "f4_aviatrice": ("aviatrice",), "m10_marseillais": ("marseill",), "f11_mariee": ("mariee",), "f7_veuve": ("veuve",),
           "f9_etudiante": ("etudiante",), "m12_sportif": ("tennis",)}


def _mentions(text):
    t = norm(text)
    return {v for v, kws in MENTION.items() if any(k in t for k in kws)}


def cast(items):
    """Give every item a voice: explicit voice kept; dialogue speakers get one voice per (dialogue, speaker), two different
    voices per dialogue; usage balanced across the guest voices of the right gender (deterministic)."""
    use = {v: 0 for v in GUESTS}
    for it in items:
        if it.get("voice"):
            use[it["voice"]] = use.get(it["voice"], 0) + 1
    dlg_voice = {}
    dtext = {}
    for it in items:
        if "dialogue_id" in it:
            dtext[it["dialogue_id"]] = dtext.get(it["dialogue_id"], "") + " " + it["text"]
    for it in items:
        if it.get("voice"):
            if "dialogue_id" in it:
                dlg_voice[(it["dialogue_id"], it["speaker"])] = it["voice"]
            continue
        g = it.get("gender")
        if "dialogue_id" in it:
            k = (it["dialogue_id"], it["speaker"])
            if k not in dlg_voice:
                other = {v for (d, s), v in dlg_voice.items() if d == it["dialogue_id"]}
                avoid = _mentions(dtext[it["dialogue_id"]])
                pool = [v for v in GUESTS if (not g or VOICES[v][0] == g) and v not in other and v not in avoid]
                h = _h(f"{k}")
                pool.sort(key=lambda v: (use[v], (_h(v) ^ h) & 0xffff))
                dlg_voice[k] = pool[0]
            it["voice"] = dlg_voice[k]
        else:
            avoid = _mentions(it["text"])
            pool = [v for v in GUESTS if (not g or VOICES[v][0] == g) and v not in avoid]
            h = _h(it["text"])
            pool.sort(key=lambda v: (use[v], (_h(v) ^ h) & 0xffff))
            it["voice"] = pool[0]
        use[it["voice"]] = use.get(it["voice"], 0) + 1
    for it in items:
        it["gender"] = VOICES[it["voice"]][0]


def all_scripts():
    return sorted(os.path.splitext(os.path.basename(p))[0] for p in glob.glob(os.path.join(SCRIPTS, "*.py")) if not os.path.basename(p).startswith("_"))


def old_texts():
    """Texts already in the game from the panic bank (final/panic/panic_report.json)."""
    p = os.path.join(FINAL, "panic", "panic_report.json")
    return {norm(e["text"]): e["file"] for e in json.load(open(p, encoding="utf-8")) if e.get("text")} if os.path.exists(p) else {}


def check():
    seen = dict(old_texts())
    bad = 0
    stats = {}
    for b in all_scripts():
        for it in load_script(b):
            if it.get("nonverbal"):
                continue
            n = norm(it["text"])
            if n in seen:
                print(f"DUP {b} {it['key']}: «{it['text']}» already in {seen[n]}"); bad += 1
            seen[n] = it["key"]
            stats.setdefault(b, {}).setdefault(it["cat"], 0); stats[b][it["cat"]] += 1
    for b, s in stats.items():
        print(b, s)
    print("duplicates:", bad)
    return bad


def refs():
    return json.load(open(os.path.join(QA, "panic_refs.json"), encoding="utf-8"))


def ref_for(r, vid, reg):
    """Clone reference take for a voice/register, with fallbacks for voices that lack that register."""
    have = r.get(vid, {})
    chain = {"awkward": ["neutral"], "startled": ["panic", "neutral"], "whisper": ["awkward", "neutral"], "warm": ["neutral"],
             "gossip": ["whisper", "awkward", "neutral"], "threat": ["panic", "neutral"], "manic": ["panic", "neutral"]}
    for cand in [reg] + chain.get(reg, []) + ["neutral"]:
        if cand and cand in have:
            return cand, have[cand]
    return None, None


def jobs(batch, seeds=1, seed_base=0, only_missing=False, out=None, only_keys=None, claimed=None):
    items = load_script(batch)
    if only_keys is not None:
        items = [it for it in items if it["key"] in only_keys]
    if claimed is not None:   # texts already produced by an earlier batch: skip (the game de-duplicates by text anyway)
        keep = []
        for it in items:
            n = norm(it["text"])
            if it.get("nonverbal") or n not in claimed or claimed[n] == it["key"]:
                keep.append(it)
                if not it.get("nonverbal"):
                    claimed.setdefault(n, it["key"])
        items = keep
    r = refs()
    qa = json.load(open(os.path.join(QA, "panic_qa.json"), encoding="utf-8"))
    rej = json.load(open(os.path.join(QA, "panic_rejected.json"), encoding="utf-8")) if os.path.exists(os.path.join(QA, "panic_rejected.json")) else {}
    if only_missing:
        miss_p = os.path.join(QA, f"vox_{batch}_missing.json")
        miss = set(json.load(open(miss_p, encoding="utf-8"))) if os.path.exists(miss_p) else set()
        items = [it for it in items if it["key"] in miss]
    J, skipped = [], 0
    for i, it in enumerate(items):
        reg = it["reg"]
        base = 5000 + seed_base + (int(it["key"].rsplit("_", 1)[1]) * 7) % 4000
        if reg.startswith("design:"):
            dreg = reg.split(":", 1)[1]
            for k in range(seeds):
                J.append({"key": it["key"], "group": "vox_" + batch, "mode": "design", "seed": base + k, "text": it["text"],
                          "instruct": instruct(it["voice"], dreg), "meta": {"category": it["cat"], "register": dreg, "voice": it["voice"]}})
            continue
        used_reg, take = ref_for(r, it["voice"], reg)
        if not take:
            skipped += 1; continue
        ref = f"gw_panic_{it['voice']}_{used_reg}.flac"
        dst = os.path.join(COMFY_IN, ref)
        if not os.path.exists(dst) or os.path.getmtime(dst) < os.path.getmtime(qa[take]["file"]):
            shutil.copyfile(qa[take]["file"], dst)
        for k in range(seeds):
            J.append({"key": it["key"], "group": "vox_" + batch, "mode": "clone", "seed": base + k, "text": it["text"], "ref": ref,
                      "ref_text": qa[take].get("text") or REF_TEXT[used_reg], "meta": {"category": it["cat"], "register": used_reg, "voice": it["voice"], "ref_take": take}})
    out = out or os.path.join(HERE, "batches", f"vox_{batch}.json")
    json.dump(J, open(out, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(out, len(J), "jobs;", skipped, "items skipped (no reference yet)")
    return out, {j["key"] for j in J}


# ------------------------------------------------------------------ publish
def publish(batch):
    import panic_qa as Q
    from panic_select import asr_ok, register_ok, sim, asr_fix
    import panic_master as M
    import audiolib as A
    items = load_script(batch)
    files = sorted(glob.glob(os.path.join(HERE, "gen", "vox_" + batch, "*.flac")))
    Q.analyze(files)
    qa, emb = json.load(open(os.path.join(QA, "panic_qa.json"), encoding="utf-8")), None
    import numpy as np
    emb = dict(np.load(os.path.join(QA, "panic_emb.npz")))
    r = refs()
    rej_p = os.path.join(QA, "panic_rejected.json")
    rej = json.load(open(rej_p, encoding="utf-8")) if os.path.exists(rej_p) else {}
    out_dir = os.path.join(FINAL, batch); os.makedirs(out_dir, exist_ok=True)
    rep_p = os.path.join(out_dir, f"{batch}_report.json")
    report = {e["file"]: e for e in json.load(open(rep_p, encoding="utf-8"))} if os.path.exists(rep_p) else {}
    done_keys = {e.get("key") for e in report.values()}
    missing = []
    for it in items:
        if it["key"] in done_keys:
            continue
        takes = {k: v for k, v in qa.items() if k.startswith(it["key"] + "_s") and k not in rej}
        reg = it["reg"].split(":")[-1]
        if it.get("nonverbal"):
            ok = [k for k in takes if 0.3 <= takes[k].get("active_s", 0) <= 6.0]
        else:
            f0n = r.get(it["voice"], {}).get("f0_neutral", 0)
            chk = {"whisper": "awkward", "startled": "awkward", "threat": "panic", "manic": "panic", "flat": "awkward",
                   "neutral": "awkward"}.get(reg, reg)
            f0p = qa.get(r.get(it["voice"], {}).get("panic", ""), {}).get("f0_med", 0)
            # length limits scale with the text (slow speakers, long sentences, dramatic pauses "..." are fine)
            max_act = max(6.0, 0.11 * len(it["text"]) + 2.5)
            max_gap = 1.6 if ("..." in it["text"] or "…" in it["text"]) else 1.1
            def fits(r):
                return 0.3 <= r.get("active_s", 0) <= max_act and r.get("gap_s", 0) <= max_gap
            def reg_ok(r, c):
                return register_ok(dict(r, active_s=1.0, gap_s=0.0), c, f0n, f0_panic=f0p)[0]   # length checked by fits()
            ok = [k for k in takes if asr_ok(takes[k]) and fits(takes[k]) and reg_ok(takes[k], chk)]
            if not ok and chk == "panic":   # shouted lines: accept an understood take that is merely less raised
                ok = [k for k in takes if asr_ok(takes[k]) and fits(takes[k]) and reg_ok(takes[k], "awkward")]
        if not ok:
            missing.append(it["key"]); continue
        ref = r.get(it["voice"], {}).get(reg)
        best = max(ok, key=lambda k: (sim(emb, k, ref) if ref and k in emb else 0) + 0.3 * takes[k].get("word_match", 0)
                   + (0.002 * takes[k].get("f0_med", 0) if reg == "panic" else 0))
        tag = {"dialogue": "Dlg", "remark": "Rmk", "greet": "Greet"}.get(it["cat"], "".join(w.capitalize() for w in it["cat"].split("_")))
        idx = int(it["key"].rsplit("_", 1)[1])
        name = (f"VO_{tag}_{it['dialogue_id']}_{it['turn']}_{it['gender']}" if it["cat"] == "dialogue"
                else f"VO_{tag}_{batch}_{idx:03d}_{it['gender']}")
        sel = {"name": name, "source": takes[best]["file"], "category": "robot" if it["cat"] == "robot_voice" else it["cat"], "gender": it["gender"], "voice_id": it["voice"],
               "register": reg, "text": it["text"], "whispered": bool(it.get("whispered")), "nonverbal": bool(it.get("nonverbal")),
               "asr_ok": not it.get("nonverbal")}
        out = os.path.join(out_dir, name + ".wav")
        mixes = (0.15, 0.3, 0.5, 1.0) if sel["whispered"] else (None,)
        heard = None
        for mix in mixes:
            if mix is not None:
                sel["voice_mix"] = mix
            y, g, lim, _ = M.master_voice(sel)
            A.save_wav(out, y, M.SR)
            if it.get("nonverbal"):
                break
            heard = Q.asr(out)
            wm, cm = Q.word_match(it["text"], heard)
            hom = difflib.SequenceMatcher(None, Q.norm(it["text"]), asr_fix(heard).split()).ratio()
            asr_pass = wm >= 0.75 or cm >= 0.88 or hom >= 0.75
            if asr_pass or mix is None or mix == mixes[-1]:
                break
        if not it.get("nonverbal") and not asr_pass:
            rej[os.path.basename(takes[best]["file"])] = f"final ASR failed: heard '{heard}'"
            json.dump(rej, open(rej_p, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
            os.makedirs(os.path.join(out_dir, "_rejected"), exist_ok=True)
            os.replace(out, os.path.join(out_dir, "_rejected", name + ".wav"))
            missing.append(it["key"]); continue
        y2, _ = A.load(out)
        m = A.metrics(y2, M.SR)
        e = {"file": name + ".wav", "key": it["key"], "category": it["cat"], "voice_id": it["voice"], "gender": it["gender"],
             "voice_label": VOICES[it["voice"]][1], "text": it["text"], "duration_s": m["duration"],
             "cause": it.get("cause"), "dialogue_id": it.get("dialogue_id"), "turn": it.get("turn"), "speaker": it.get("speaker"),
             "whispered": bool(it.get("whispered")) and sel.get("voice_mix") != 1.0, "murmured": sel.get("voice_mix") == 1.0,
             "nonverbal": bool(it.get("nonverbal")), "gun": bool(it.get("gun")), "register": reg,
             "lufs": m["lufs"], "true_peak_dbtp": m["true_peak_dbtp"], "sample_rate": m["sr"],
             "asr_transcript": heard, "asr_match": True if not it.get("nonverbal") else None,
             "source_candidate": os.path.relpath(takes[best]["file"], HERE).replace("\\", "/"), "seed": takes[best].get("seed"),
             "generator": "Qwen3-TTS 1.7B " + ("VoiceDesign (direct)" if it["reg"].startswith("design:") else f"VoiceClone of the {reg} reference")}
        for k in ("context", "mood", "line_id", "char_id"):
            if k in it:
                e[k] = it[k]
        report[e["file"]] = e
        rows = sorted(report.values(), key=lambda x: x["file"])
        json.dump(rows, open(rep_p + ".tmp", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
        os.replace(rep_p + ".tmp", rep_p)
        print(f"{name:34s} {m['duration']:5.2f}s «{it['text'][:50]}» heard «{(heard or '')[:40]}»", flush=True)
    # dialogues are published whole: drop a dialogue whose turns are not all there yet (the game needs every turn)
    rows = sorted(report.values(), key=lambda x: x["file"])
    complete = []
    by_d = {}
    for it in items:
        if it["cat"] == "dialogue":
            by_d.setdefault(it["dialogue_id"], set()).add(it["key"])
    have = {e["key"] for e in rows}
    for e in rows:
        if e["category"] == "dialogue" and not by_d[e["dialogue_id"]] <= have:
            e = dict(e, incomplete=True)
        complete.append(e)
    final = [e for e in complete if not e.get("incomplete")]
    json.dump(final, open(rep_p, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    json.dump([e for e in complete if e.get("incomplete")], open(os.path.join(QA, f"vox_{batch}_pending.json"), "w", encoding="utf-8"),
              indent=1, ensure_ascii=False)
    json.dump(missing, open(os.path.join(QA, f"vox_{batch}_missing.json"), "w", encoding="utf-8"), indent=1)
    cats = {}
    for e in final:
        cats[e["category"]] = cats.get(e["category"], 0) + 1
    print(f"{batch}: {len(final)} in report {cats}; {len(missing)} missing; {sum(1 for e in complete if e.get('incomplete'))} dialogue lines waiting for their other turns")
    return final, missing


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd"); ap.add_argument("batch", nargs="?"); ap.add_argument("--seeds", type=int, default=1)
    ap.add_argument("--seed-base", type=int, default=0); ap.add_argument("--only-missing", action="store_true"); ap.add_argument("--out")
    a = ap.parse_args()
    if a.cmd == "check":
        sys.exit(1 if check() else 0)
    if a.cmd == "jobs":
        jobs(a.batch, a.seeds, a.seed_base, a.only_missing, a.out)
    if a.cmd == "publish":
        publish(a.batch)
