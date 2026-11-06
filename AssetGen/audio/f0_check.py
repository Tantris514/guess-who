"""Median F0 of every intelligible voice candidate (to keep one consistent baritone across the lines)."""
import glob, json, os
import numpy as np, librosa, soundfile as sf
asr = json.load(open('qa/asr_report.json', encoding='utf-8'))
for f in sorted(glob.glob(os.path.join('gen', 'vo_*', '*.flac'))):
    b = os.path.basename(f)
    if asr.get(b, {}).get('word_match', 0) < 0.75:
        continue
    x, sr = sf.read(f)
    x = x.mean(axis=1) if x.ndim > 1 else x
    f0, v, _ = librosa.pyin(x.astype(np.float32), fmin=40, fmax=400, sr=sr)
    print(b, 'voiced', round(float(np.mean(v)), 2), 'f0', round(float(np.nanmedian(f0)), 1), 'match', asr[b]['word_match'])
