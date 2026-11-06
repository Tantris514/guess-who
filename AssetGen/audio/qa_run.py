"""QA every generated audio candidate: metrics (JSON) + waveform/spectrogram PNG. Usage: qa_run.py [name_prefix ...]"""
import glob, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import audiolib as A

HERE = os.path.dirname(os.path.abspath(__file__))
QA = os.path.join(HERE, "qa")
os.makedirs(QA, exist_ok=True)
pref = sys.argv[1:]
rows = []
for f in sorted(glob.glob(os.path.join(HERE, "gen", "*", "*.flac"))):
    base = os.path.splitext(os.path.basename(f))[0]
    if pref and not any(base.startswith(p) for p in pref):
        continue
    x, sr = A.load(f)
    m = A.metrics(x, sr)
    m["file"] = f
    A.spectrogram_png(os.path.join(QA, base + ".png"), x, sr, base)
    json.dump(m, open(os.path.join(QA, base + ".json"), "w"), indent=1)
    rows.append((base, m))
    print(f"{base:28s} dur={m['duration']:6.2f} pk={m['peak_dbfs']:6.1f} tp={m['true_peak_dbtp']:6.1f} lufs={m['lufs']:6.1f} "
          f"mom={m['max_momentary_lufs']:6.1f} clip={m['clipped_samples']:5d} dc={max(abs(d) for d in m['dc']):.4f} lead={m['lead_silence_s']:4.2f} "
          f"trail={m['trail_silence_s']:5.2f} gap={m['longest_inner_silence_s']:4.2f} sil={m['silent_fraction']:.2f} cen={m['centroid_hz']:5d} "
          f"flat={m['flatness']:.3f} hf={m['hf_ratio_12k']:.3f}", flush=True)
