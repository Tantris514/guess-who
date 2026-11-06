"""Master the brass-free replacements (Stable Audio 3, batches/music_soft.json) into seamless loops:
  MUS_Party.wav       <- mus_party_soft (reveal / party phase; replaces the big band with muted trumpets)
  MUS_Gramophone.wav  <- mus_gramophone_soft (ballroom gramophone, mono lo-fi)
  MUS_Hunt_Soft.wav   <- mus_hunt_soft (an alternative for the hunt, not swapped in automatically)
The old files are kept in final/_old/. Picks the candidate with the best loop (similarity, seam), same loop search and
loudness as master_audio.py (-16 LUFS, -1 dBTP).  python -X utf8 music_soft_apply.py"""
import glob, json, os, shutil, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import audiolib as A  # noqa: E402

OUT = os.path.join(HERE, "final")
SPEC = [("MUS_Party", "mus_party_soft", False, (30, 44)), ("MUS_Gramophone", "mus_gramophone_soft", True, (30, 48)),
        ("MUS_Hunt_Soft", "mus_hunt_soft", False, (40, 70))]
rep = []
for name, d, mono, (lo, hi) in SPEC:
    best = None
    for f in sorted(glob.glob(os.path.join(HERE, "gen", d, "*.flac"))):
        x, sr = A.load(f)
        lp = A.find_music_loop(x, sr, lo, hi, xfade=0.5, skip_start=2.0, avoid_end=4.0)
        if not lp:
            continue
        y = A.make_loop(x, sr, lp["start"], lp["end"], 0.5)
        seam = A.seam_report(y, sr)["seam_vs_p95"]
        score = lp["sim"] - 0.2 * seam
        if best is None or score > best[0]:
            best = (score, f, y, sr, lp, seam)
    if not best:
        print("no candidate for", name); continue
    _, f, y, sr, lp, seam = best
    if mono:
        y = A.to_mono(y)
    y, g, lim = A.gain_to(y, sr, target_lufs=-16.0, tp_ceiling=-1.0)
    dst = os.path.join(OUT, name + ".wav")
    if os.path.exists(dst) and not name.endswith("_Soft"):
        os.makedirs(os.path.join(OUT, "_old"), exist_ok=True)
        if not os.path.exists(os.path.join(OUT, "_old", name + ".wav")):
            shutil.copyfile(dst, os.path.join(OUT, "_old", name + ".wav"))
    A.save_wav(dst, y, sr)
    m = A.metrics(*A.load(dst))
    rep.append({"file": name + ".wav", "source": os.path.relpath(f, HERE), "loop_s": lp["length_s"], "tempo": lp["tempo"],
                "sim": lp["sim"], "seam_vs_p95": seam, "lufs": m["lufs"], "true_peak_dbtp": m["true_peak_dbtp"]})
    print(rep[-1])
json.dump(rep, open(os.path.join(HERE, "qa", "music_soft_report.json"), "w", encoding="utf-8"), indent=1)
