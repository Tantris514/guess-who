"""Synthesize the shop / item sounds locally (numpy only, no model): cash register, smoke and gas hiss, bomb beep,
defuse, trap click, coins.

  V:\\ComfyUI\\ComfyUI\\ComfyUI\\.venv\\Scripts\\python.exe -I synth_shop.py

Writes AssetGen/audio/final/synth/SFX_*.wav + shop_report.json. Tools/gameplay/s34_shop.py imports them directly
(its actors reference the files), and Tools/gameplay/s31_reactions.py puts them in the sound bank under the categories
shop_buy, smoke_hiss, gas_hiss, bomb_beep, defuse, trap_click. Mono 44.1 kHz: every sound is played in 3D except the
buyer's own cash register / coins (UI feedback).
"""
import json
import os
import wave

import numpy as np

SR = 44100
OUT = r'J:\Projets\Unreal_Projects\Guess Who\AssetGen\audio\final\synth'
rng = np.random.default_rng(34)


def t_of(dur):
    return np.arange(int(dur * SR)) / SR


def band(x, lo, hi):
    """Band-pass by FFT mask with soft 15 % skirts."""
    n = len(x)
    f = np.fft.rfftfreq(n, 1 / SR)
    X = np.fft.rfft(x)
    m = np.clip((f - lo * 0.85) / (lo * 0.15 + 1e-9), 0, 1) * np.clip((hi * 1.15 - f) / (hi * 0.15 + 1e-9), 0, 1)
    return np.fft.irfft(X * m, n)


def lowpass1(x, fc):
    a = np.exp(-2 * np.pi * fc / SR)
    y = np.empty_like(x)
    acc = 0.0
    for i in range(len(x)):
        acc = (1 - a) * x[i] + a * acc
        y[i] = acc
    return y


def place(out, sig, at):
    i = int(at * SR)
    j = min(len(out), i + len(sig))
    out[i:j] += sig[:j - i]


def ring(f0, partials, dur, phase_rng=True):
    """Struck metal: list of (ratio, amp, decay)."""
    t = t_of(dur)
    s = np.zeros_like(t)
    for ratio, amp, decay in partials:
        s += amp * np.sin(2 * np.pi * f0 * ratio * t + (rng.uniform(0, 2 * np.pi) if phase_rng else 0)) * np.exp(-decay * t)
    return s


def burst(dur, lo, hi, decay, amp=1.0):
    t = t_of(dur)
    return amp * band(rng.standard_normal(len(t)), lo, hi) * np.exp(-decay * t)


def thump(f, dur, decay, amp=1.0, glide=0.0):
    t = t_of(dur)
    ph = 2 * np.pi * np.cumsum(f * (1 - glide * t / dur)) / SR
    return amp * np.sin(ph) * np.exp(-decay * t)


def fade(x, a=0.002, r=0.05):
    n = len(x)
    e = np.ones(n)
    na, nr = int(a * SR), int(r * SR)
    if na:
        e[:na] = np.linspace(0, 1, na)
    if nr:
        e[-nr:] *= np.linspace(1, 0, nr)
    return x * e


def norm(x, peak=0.8):
    x = x - np.mean(x)
    return x / (np.max(np.abs(x)) + 1e-9) * peak


def coins(n_pings, span, at0=0.0, dur=None):
    dur = dur or span + 0.5
    out = np.zeros(int(dur * SR))
    for k in range(n_pings):
        f0 = rng.uniform(3600, 6200)
        p = ring(f0, [(1.0, 1.0, 22), (1.47, 0.6, 30), (2.09, 0.35, 40)], 0.25)
        place(out, p * rng.uniform(0.35, 0.9), at0 + rng.uniform(0, span))
    return out


def cash_register():
    out = np.zeros(int(1.6 * SR))
    place(out, thump(85, 0.25, 26, 0.9), 0.0)                                   # the lever going down
    place(out, burst(0.12, 300, 2500, 32, 0.7), 0.0)
    for k in range(6):                                                           # mechanism rattle
        place(out, burst(0.012, 2500, 9000, 300, 0.45), 0.05 + k * 0.019)
    place(out, ring(2093, [(1.0, 1.0, 3.2), (2.76, 0.45, 5.0), (5.40, 0.25, 8.0), (8.93, 0.1, 12.0)], 1.35), 0.17)
    slide = band(rng.standard_normal(int(0.28 * SR)), 600, 3500) * np.hanning(int(0.28 * SR)) * 0.35   # drawer opens
    place(out, slide, 0.30)
    place(out, thump(60, 0.15, 30, 0.6), 0.56)                                   # drawer stop
    place(out, coins(7, 0.35, 0.0, 0.9), 0.58)
    return fade(norm(out, 0.82), r=0.12)


def coin_pickup():
    out = np.zeros(int(0.9 * SR))
    place(out, coins(5, 0.22, 0.0, 0.8), 0.0)
    place(out, ring(2637, [(1.0, 0.7, 7.0), (2.0, 0.25, 10.0)], 0.6), 0.04)     # bright little "ching"
    return fade(norm(out, 0.7), r=0.1)


def smoke_hiss():
    dur = 8.0
    out = np.zeros(int(dur * SR))
    place(out, ring(3200, [(1.0, 1.0, 40), (1.6, 0.6, 55), (2.4, 0.3, 70)], 0.2) * 0.5, 0.0)    # the pin
    place(out, ring(1800, [(1.0, 1.0, 25), (2.3, 0.4, 40)], 0.25) * 0.4, 0.12)                    # the spoon flies
    place(out, thump(70, 0.3, 18, 0.9), 0.38)                                                       # the pop
    place(out, burst(0.2, 200, 3000, 20, 0.8), 0.38)
    n = int((dur - 0.42) * SR)
    t = np.arange(n) / SR
    hi = band(rng.standard_normal(n), 1600, 9500)
    lo = band(rng.standard_normal(n), 300, 1600)
    env = np.minimum(t / 0.12, 1.0) * (0.35 + 0.65 * np.exp(-t / 2.8))
    sput = 1.0 + 0.22 * band(rng.standard_normal(n), 4, 14) / 0.05
    sput = np.clip(sput, 0.55, 1.45)
    mixk = 0.5 + 0.5 * np.sin(2 * np.pi * 0.23 * t)
    h = (hi * (0.75 + 0.25 * mixk) + lo * 0.45 * (1 - 0.5 * mixk)) * env * sput
    place(out, h * 0.9, 0.42)
    return fade(norm(out, 0.8), r=0.6)


def gas_hiss():
    dur = 3.6
    n = int(dur * SR)
    t = np.arange(n) / SR
    out = np.zeros(n)
    place(out, burst(0.02, 1500, 8000, 150, 0.8), 0.0)                          # valve click
    env = np.minimum(t / 0.04, 1.0) * np.exp(-t / 1.6)
    hiss = band(rng.standard_normal(n), 2800, 8000) * env
    vib = 3100 + 60 * np.sin(2 * np.pi * 6.0 * t) - 400 * t / dur
    whistle = 0.18 * np.sin(2 * np.pi * np.cumsum(vib) / SR) * env
    pulses = np.clip(band(rng.standard_normal(n), 5, 18) * 30, 0, 1)
    gurgle = band(rng.standard_normal(n), 150, 520) * pulses * 0.5 * np.exp(-t / 1.2)
    out += hiss + whistle + gurgle
    return fade(norm(out, 0.78), r=0.4)


def bomb_beep():
    dur = 0.16
    t = t_of(dur)
    f = 2350.0
    s = np.sin(2 * np.pi * f * t) + 0.28 * np.sin(2 * np.pi * 3 * f * t) + 0.12 * np.sin(2 * np.pi * 5 * f * t)
    env = np.clip(t / 0.003, 0, 1) * np.clip((0.115 - t) / 0.02, 0, 1)
    s = s * env
    s[:int(0.004 * SR)] += burst(0.004, 800, 6000, 400, 0.3)[:int(0.004 * SR)]
    return norm(s, 0.85)


def defuse():
    out = np.zeros(int(1.8 * SR))
    for k, at in enumerate((0.0, 0.035)):                                       # wire snip: two blades
        place(out, burst(0.05, 4000, 12000, 120, 0.9), at)
        place(out, ring(2700 + 400 * k, [(1.0, 1.0, 9), (1.63, 0.5, 12), (2.55, 0.3, 16)], 0.5) * 0.35, at)
    n = int(0.75 * SR)
    t = np.arange(n) / SR
    fdown = 2350 * np.exp(-t * 2.8) + 180
    whine = np.sin(2 * np.pi * np.cumsum(fdown) / SR) * np.exp(-t * 2.2) * 0.45
    whine *= np.where((t * 9) % 1.0 < 0.75, 1.0, 0.25)                           # sputtering, dying beeps
    place(out, whine, 0.12)
    place(out, burst(0.01, 1500, 7000, 300, 0.6), 1.05)                         # cover snaps shut
    place(out, thump(110, 0.2, 25, 0.5), 1.05)
    return fade(norm(out, 0.8), r=0.2)


def trap_click():
    out = np.zeros(int(0.6 * SR))
    place(out, burst(0.012, 2000, 9000, 260, 1.0), 0.0)                         # latch
    t = t_of(0.5)
    f = 430 - 50 * t / 0.5
    tw = (np.sin(2 * np.pi * np.cumsum(f) / SR) + 0.3 * np.sin(2 * np.pi * 3 * np.cumsum(f) / SR)) * np.exp(-8 * t) * 0.6
    place(out, tw, 0.004)                                                        # spring twang
    place(out, burst(0.01, 2500, 9000, 300, 0.7), 0.12)                         # second click (armed)
    return fade(norm(out, 0.8), r=0.08)


SOUNDS = [
    ('SFX_Shop_Buy', 'shop_buy', cash_register, 'Cash register: lever, bell ding, drawer, coins (shop purchase)'),
    ('SFX_Shop_Coins', 'shop_buy', coin_pickup, 'A few coins and a bright ching (money earned)'),
    ('SFX_Smoke_Hiss', 'smoke_hiss', smoke_hiss, 'Smoke grenade: pin, spoon, pop, then 7 s of sputtering hiss'),
    ('SFX_Gas_Hiss', 'gas_hiss', gas_hiss, 'Shrinking gas: valve click, sharp hiss with a whistle and gurgle'),
    ('SFX_Bomb_Beep', 'bomb_beep', bomb_beep, 'One bomb beep (2.35 kHz, 110 ms); the bomb repeats it faster and faster'),
    ('SFX_Defuse', 'defuse', defuse, 'Bomb defused: wire snip, dying beep whine, cover snapping shut'),
    ('SFX_Trap_Click', 'trap_click', trap_click, 'Door-frame trap: latch click and spring twang'),
]

os.makedirs(OUT, exist_ok=True)
report = []
for name, cat, fn, desc in SOUNDS:
    x = fn()
    path = os.path.join(OUT, name + '.wav')
    with wave.open(path, 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype('<i2').tobytes())
    report.append({'file': name + '.wav', 'category': cat, 'kind': 'oneshot', 'duration_s': round(len(x) / SR, 3),
                   'description': desc + ' (synthesized, Tools/audio/synth_shop.py)', 'generator': 'numpy synthesis (local)'})
    print(path, round(len(x) / SR, 2), 's')
with open(os.path.join(OUT, 'shop_report.json'), 'w', encoding='utf-8') as fh:
    json.dump(report, fh, indent=1)
print('report', len(report))
