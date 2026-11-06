"""Synthesize a 1930s electric fire-alarm bell (local, no model): a striker hits a bell ~19 times a second.

  V:\\ComfyUI\\ComfyUI\\ComfyUI\\.venv\\Scripts\\python.exe -I synth_fire_bell.py

Each strike excites the bell's inharmonic partials (ratios of a struck bell), which decay over ~0.4 s and overlap into
a continuous ring; a slow tremble of the strike force keeps it alive. The loop length is a whole number of strikes so
it loops seamlessly. Writes AssetGen/audio/final/synth/SFX_Fire_Bell_Loop.wav + synth_report.json, which
Tools/gameplay/s31_reactions.py imports as category 'fire_alarm' (played in 2D on every client during "Au feu !").
"""
import json
import os
import wave

import numpy as np

SR = 44100
OUT = r'J:\Projets\Unreal_Projects\Guess Who\AssetGen\audio\final\synth'
RATE = 19.0                      # strikes per second
STRIKES = 95                     # 5 s loop
F0 = 742.0
PARTIALS = [(1.0, 1.0, 5.5), (2.32, 0.55, 7.0), (3.67, 0.32, 9.5), (5.12, 0.22, 12.0), (6.8, 0.12, 15.0), (8.9, 0.07, 19.0)]

n = int(round(STRIKES / RATE * SR))
t = np.arange(n) / SR
out = np.zeros(n)
rng = np.random.default_rng(7)
period = n / STRIKES
for k in range(STRIKES):
    start = k * period
    force = 0.82 + 0.12 * np.sin(2 * np.pi * k / STRIKES * 3) + rng.uniform(-0.05, 0.05)
    # each strike rings into the next ones: add it with wrap-around so the loop stays seamless
    idx = (np.arange(int(0.6 * SR)) + int(start)) % n
    tt = np.arange(int(0.6 * SR)) / SR
    s = np.zeros_like(tt)
    for ratio, amp, decay in PARTIALS:
        s += amp * np.sin(2 * np.pi * F0 * ratio * tt + rng.uniform(0, 2 * np.pi)) * np.exp(-decay * tt)
    s += 0.25 * rng.standard_normal(len(tt)) * np.exp(-400 * tt)       # the hammer click
    np.add.at(out, idx, force * s)
out /= np.max(np.abs(out))
out = np.tanh(out * 1.6) / np.tanh(1.6) * 0.7                       # a little bite, peak about -3 dBFS
os.makedirs(OUT, exist_ok=True)
path = os.path.join(OUT, 'SFX_Fire_Bell_Loop.wav')
with wave.open(path, 'wb') as w:
    w.setnchannels(1)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes((out * 32767).astype('<i2').tobytes())
report = [{'file': 'SFX_Fire_Bell_Loop.wav', 'category': 'fire_alarm', 'kind': 'loop', 'duration_s': round(n / SR, 3),
           'description': '1930s electric fire-alarm bell, ~19 strikes/s, seamless loop (synthesized, Tools/audio/synth_fire_bell.py)',
           'generator': 'numpy synthesis (local)'}]
with open(os.path.join(OUT, 'synth_report.json'), 'w', encoding='utf-8') as fh:
    json.dump(report, fh, indent=1)
print(path, round(n / SR, 2), 's')
