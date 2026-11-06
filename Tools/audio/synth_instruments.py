"""Synthesize the "cacophony" one-shots of the playable instruments (local, no model), 3 variants each.

  V:\\ComfyUI\\ComfyUI\\ComfyUI\\.venv\\Scripts\\python.exe -I synth_instruments.py

harp  : a clumsy two-handed glissando over clashing strings, then a dissonant chord left ringing (Karplus-Strong plucks)
drums : a frantic tom roll into a crash cymbal and a kick, all slightly out of time
bass  : low slapped strings, out of tune, with a buzzing open string
Writes AssetGen/audio/final/synth/SFX_<Instr>_Crash_0N.wav and adds them to synth_report.json (categories harp /
drums / bass, imported by Tools/gameplay/s31_reactions.py, played by s33_piano.py PlayInstrument).
"""
import json
import os
import wave

import numpy as np

SR = 44100
OUT = r'J:\Projets\Unreal_Projects\Guess Who\AssetGen\audio\final\synth'


def pluck(freq, dur, rng, bright=0.5, decay=0.996):
    """Karplus-Strong string: a noise burst in a delay line with a damped averaging filter."""
    n = int(dur * SR)
    period = max(2, int(SR / freq))
    buf = rng.uniform(-1, 1, period) * (0.5 + bright * 0.5)
    out = np.zeros(n)
    for i in range(n):
        j = i % period
        out[i] = buf[j]
        buf[j] = decay * 0.5 * (buf[j] + buf[(j + 1) % period])
    return out


def mix(a, b):
    """Sum of two signals of different lengths (the shorter one padded with silence)."""
    n = max(len(a), len(b))
    return np.pad(a, (0, n - len(a))) + np.pad(b, (0, n - len(b)))


def add(dst, src, at):
    a = int(at * SR)
    if a >= len(dst):
        return
    m = min(len(src), len(dst) - a)
    dst[a:a + m] += src[:m]


def noise_hit(dur, rng, decay, lp=0.0):
    n = int(dur * SR)
    x = rng.standard_normal(n) * np.exp(-decay * np.arange(n) / SR)
    if lp > 0:                                   # one-pole low-pass for toms / kick bodies
        y = np.zeros(n)
        for i in range(1, n):
            y[i] = y[i - 1] + lp * (x[i] - y[i - 1])
        x = y
    return x


def tone_hit(freq, dur, decay, sweep=0.0):
    t = np.arange(int(dur * SR)) / SR
    f = freq * (1 + sweep * np.exp(-t * 30))
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-decay * t)


def harp(seed):
    rng = np.random.default_rng(seed)
    out = np.zeros(int(4.2 * SR))
    base = rng.uniform(98, 130)
    strings = [base * 2 ** (k / 12 + rng.uniform(-0.18, 0.18)) for k in range(0, 40, 2)]   # detuned: it clashes
    t = 0.0
    for f in (strings if seed % 2 else strings[::-1]):                                   # glissando up or down
        add(out, pluck(f, 2.5, rng, bright=0.8, decay=0.9975) * 0.35, t)
        t += rng.uniform(0.018, 0.045)
    for f in rng.choice(strings, 6, replace=False):                                     # the slammed chord
        add(out, pluck(f * rng.uniform(0.98, 1.03), 3.2, rng, bright=1.0, decay=0.998) * 0.5, t + 0.15 + rng.uniform(0, 0.04))
    return out


def drums(seed):
    rng = np.random.default_rng(seed)
    out = np.zeros(int(3.6 * SR))
    t = 0.0
    for k in range(int(rng.integers(9, 15))):                                            # tom roll, rushing
        f = rng.choice([82, 98, 123, 147]) * rng.uniform(0.95, 1.05)
        add(out, mix(tone_hit(f, 0.5, 9, sweep=0.6) * 0.7, noise_hit(0.08, rng, 60, 0.3) * 0.25), t)
        t += rng.uniform(0.07, 0.13)
    add(out, mix(tone_hit(52, 0.9, 6, sweep=1.5) * 1.0, noise_hit(0.05, rng, 80, 0.1) * 0.4), t)  # kick
    crash = noise_hit(3.0, rng, 1.4)                                                       # crash cymbal: bright noise
    crash = np.diff(np.concatenate([[0], crash])) * 0.9
    add(out, crash, t + rng.uniform(0.0, 0.03))
    return out


def bass(seed):
    rng = np.random.default_rng(seed)
    out = np.zeros(int(3.4 * SR))
    t = 0.0
    for k in range(int(rng.integers(4, 7))):
        f = rng.choice([41.2, 46.2, 55.0, 61.7, 73.4]) * 2 ** rng.uniform(-0.12, 0.12)
        s = pluck(f, 2.2, rng, bright=1.0, decay=0.999)
        s += 0.3 * np.sign(s) * np.abs(s) ** 0.5 * np.exp(-np.arange(len(s)) / SR * 3)   # buzz
        add(out, s * 0.6, t)
        t += rng.uniform(0.12, 0.3)
    return out


def save(name, x):
    x = x / (np.max(np.abs(x)) + 1e-9)
    x = np.tanh(x * 1.4) / np.tanh(1.4) * 0.85
    fade = int(0.05 * SR)
    x[-fade:] *= np.linspace(1, 0, fade)
    path = os.path.join(OUT, name)
    with wave.open(path, 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((x * 32767).astype('<i2').tobytes())
    return round(len(x) / SR, 3)


os.makedirs(OUT, exist_ok=True)
rp = os.path.join(OUT, 'synth_report.json')
report = json.load(open(rp, encoding='utf-8')) if os.path.exists(rp) else []
report = [e for e in report if e.get('category') not in ('harp', 'drums', 'bass')]
for cat, fn, label in (('harp', harp, 'Harp'), ('drums', drums, 'Drums'), ('bass', bass, 'Bass')):
    for v in range(3):
        name = f'SFX_{label}_Crash_0{v + 1}.wav'
        d = save(name, fn(11 + v))
        report.append({'file': name, 'category': cat, 'kind': 'oneshot', 'duration_s': d,
                       'description': f'{label} cacophony, variant {v + 1} (synthesized, Tools/audio/synth_instruments.py)',
                       'generator': 'numpy synthesis (local)'})
        print(name, d, 's')
json.dump(report, open(rp, 'w', encoding='utf-8'), indent=1)
