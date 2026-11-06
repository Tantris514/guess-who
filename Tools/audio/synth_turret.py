"""Synthesize the mezzanine machine gun's sounds (local, no model): three single shots and a dry "empty" click.

  V:\\ComfyUI\\ComfyUI\\ComfyUI\\.venv\\Scripts\\python.exe -I synth_turret.py

A 1930s tripod machine gun (Browning / Vickers type) fires ~9 rounds a second; the game plays one shot sample per round,
so each sample is short (0.5 s) with a fast, hard attack:
- crack: a broadband blast (noise through a fast decay), slightly band-passed so it bites without hiss;
- thump: the low body of the report (75-110 Hz sine with a pitch drop), what makes it feel heavy;
- action: the bolt cycling ~35 ms later (two short metallic clicks with a couple of inharmonic partials);
- tail: a dark room reflection (low-passed noise, ~0.35 s) so a burst blends in the hall instead of sounding dry.
The empty sound is the bolt slamming on an empty chamber: two dry clicks, no report.
Writes AssetGen/audio/final/synth/SFX_Turret_Shot_0[1-3].wav, SFX_Turret_Empty_01.wav and turret_report.json, which
Tools/gameplay/s31_reactions.py imports as categories 'turret_fire' / 'turret_empty' (bank sounds, ATT_GW_Far: loud and
positional, heard across the manor). The turret (s35_turret.py) plays them on every machine.
"""
import json
import os
import wave

import numpy as np

SR = 44100
OUT = r'J:\Projets\Unreal_Projects\Guess Who\AssetGen\audio\final\synth'


def onepole_lp(x, fc):
    a = np.exp(-2 * np.pi * fc / SR)
    y = np.zeros_like(x)
    acc = 0.0
    for i, v in enumerate(x):
        acc = (1 - a) * v + a * acc
        y[i] = acc
    return y


def bandish(x, lo, hi):
    """Cheap band-pass: low-pass at hi minus low-pass at lo."""
    return onepole_lp(x, hi) - onepole_lp(x, lo)


def click(n, t0, f_list, decay, amp, rng):
    out = np.zeros(n)
    i0 = int(t0 * SR)
    L = int(0.04 * SR)
    tt = np.arange(L) / SR
    s = 0.6 * rng.standard_normal(L) * np.exp(-tt * 900)
    for f, a in f_list:
        s += a * np.sin(2 * np.pi * f * tt + rng.uniform(0, 6.28)) * np.exp(-tt * decay)
    end = min(n, i0 + L)
    out[i0:end] += amp * s[:end - i0]
    return out


def shot(seed, pitch):
    rng = np.random.default_rng(seed)
    n = int(0.5 * SR)
    t = np.arange(n) / SR
    noise = rng.standard_normal(n)
    crack = bandish(noise, 350 * pitch, 7000) * (np.exp(-t * 60) + 0.25 * np.exp(-t * 14))
    crack[: int(0.0015 * SR)] *= np.linspace(0, 1, int(0.0015 * SR))
    f = 95 * pitch * (1 + 0.6 * np.exp(-t * 40))                       # thump with a fast pitch drop
    thump = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 22)
    tail = onepole_lp(rng.standard_normal(n), 900) * np.exp(-t * 9) * np.clip(t / 0.02, 0, 1)
    action = click(n, 0.033 + rng.uniform(-0.004, 0.004), [(2300 * pitch, 0.5), (3870 * pitch, 0.3)], 160, 0.28, rng)
    action += click(n, 0.071 + rng.uniform(-0.004, 0.004), [(1700 * pitch, 0.5), (4410 * pitch, 0.25)], 190, 0.2, rng)
    s = 1.0 * crack + 0.95 * thump + 0.55 * tail + action
    s /= np.max(np.abs(s))
    s = np.tanh(s * 2.2) / np.tanh(2.2)                                  # hard, loud report
    fade = np.ones(n)
    fade[-int(0.05 * SR):] = np.linspace(1, 0, int(0.05 * SR))
    return s * fade * 0.89


def empty(seed):
    rng = np.random.default_rng(seed)
    n = int(0.3 * SR)
    s = click(n, 0.004, [(2900, 0.6), (5200, 0.3), (1400, 0.2)], 140, 1.0, rng)
    s += click(n, 0.092, [(2100, 0.6), (3700, 0.35)], 170, 0.75, rng)
    s = onepole_lp(s, 9000)
    s /= np.max(np.abs(s))
    return s * 0.7


def write(name, data):
    path = os.path.join(OUT, name)
    with wave.open(path, 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(data, -1, 1) * 32767).astype('<i2').tobytes())
    return path


os.makedirs(OUT, exist_ok=True)
report = []
for k, (seed, pitch) in enumerate(((11, 1.0), (23, 0.93), (37, 1.07)), 1):
    name = f'SFX_Turret_Shot_0{k}.wav'
    d = shot(seed, pitch)
    write(name, d)
    report.append({'file': name, 'category': 'turret_fire', 'kind': 'oneshot', 'duration_s': round(len(d) / SR, 3),
                   'description': '1930s tripod machine gun, one round (crack + thump + bolt + room tail), synthesized',
                   'generator': 'numpy synthesis (local, Tools/audio/synth_turret.py)'})
d = empty(5)
write('SFX_Turret_Empty_01.wav', d)
report.append({'file': 'SFX_Turret_Empty_01.wav', 'category': 'turret_empty', 'kind': 'oneshot',
               'duration_s': round(len(d) / SR, 3),
               'description': 'machine gun bolt slamming on an empty chamber (two dry clicks), synthesized',
               'generator': 'numpy synthesis (local, Tools/audio/synth_turret.py)'})
with open(os.path.join(OUT, 'turret_report.json'), 'w', encoding='utf-8') as fh:
    json.dump(report, fh, indent=1)
print('wrote', len(report), 'sounds to', OUT)
