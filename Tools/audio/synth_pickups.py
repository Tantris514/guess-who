"""Synthesize the pickups & interactables sounds (local, no model): billiard-ball clack, sword swish, sword hit,
body-swap whoosh, toilet farts, safe opening.

  V:\\ComfyUI\\ComfyUI\\ComfyUI\\.venv\\Scripts\\python.exe -I synth_pickups.py

Writes AssetGen/audio/final/synth/SFX_*.wav + pickups_report.json (its own report: synth_report.json belongs to the
other synth scripts). Tools/gameplay/s31_reactions.py imports them with the categories of its CAT table:
ball_clack 41, sword_swish 42, sword_hit 43, swap_whoosh 44, fart 48, safe_open 49 (s38_pickups.py plays them).
"""
import json
import os
import wave

import numpy as np
from scipy.signal import butter, sosfilt

SR = 44100
OUT = r'J:\Projets\Unreal_Projects\Guess Who\AssetGen\audio\final\synth'
rng = np.random.default_rng(38)


def t_of(sec):
    return np.arange(int(sec * SR)) / SR


def band(x, lo, hi, order=2):
    return sosfilt(butter(order, [lo, hi], btype='band', fs=SR, output='sos'), x)


def lowpass(x, f, order=2):
    return sosfilt(butter(order, f, btype='low', fs=SR, output='sos'), x)


def sweep_band(noise, centers, q=2.5, block=256):
    """Time-varying band-pass: filter block by block with the centre frequency of that block (overlap-added)."""
    out = np.zeros_like(noise)
    win = np.hanning(block * 2)
    n = len(noise)
    for s in range(0, n - block, block):
        seg = noise[max(0, s - block):s + block]
        c = centers[min(s, n - 1)]
        lo, hi = max(40.0, c / (1 + 1 / q)), min(SR / 2 - 100, c * (1 + 1 / q))
        y = band(seg, lo, hi)
        y = y[-block * 2:] if len(y) >= block * 2 else np.pad(y, (block * 2 - len(y), 0))
        a = s - block
        if a < 0:
            y, w, a = y[-a:], win[-a:], 0
        else:
            w = win
        e = min(n, a + len(y))
        out[a:e] += (y * w)[:e - a]
    return out


def finish(x, peak=0.8, fade_ms=4):
    x = x - np.mean(x)
    f = int(SR * fade_ms / 1000)
    x[-f:] *= np.linspace(1, 0, f)
    return x / (np.max(np.abs(x)) + 1e-9) * peak


def clack(seed):
    """Two ivory/phenolic balls: a hard click with a few high inharmonic partials, ~60 ms, plus a faint table tock."""
    r = np.random.default_rng(seed)
    t = t_of(0.22)
    f0 = r.uniform(2300, 2900)
    s = np.zeros_like(t)
    for ratio, amp, dec in ((1.0, 1.0, 70), (1.58, 0.6, 95), (2.27, 0.42, 120), (3.11, 0.25, 160), (4.4, 0.15, 210)):
        s += amp * np.sin(2 * np.pi * f0 * ratio * t + r.uniform(0, 6.28)) * np.exp(-dec * t)
    click = band(r.standard_normal(len(t)), 3000, 12000) * np.exp(-900 * t) * 1.4
    tock = np.sin(2 * np.pi * r.uniform(380, 460) * t) * np.exp(-55 * t) * 0.35
    s = s + click + tock
    if r.random() < 0.6:                                      # a quieter second contact (rebound), 25-45 ms later
        d = int(r.uniform(0.025, 0.045) * SR)
        s[d:] += 0.35 * s[:-d]
    return finish(s, 0.85)


def swish(seed, dur=0.38):
    """A blade cutting the air: band-passed noise whose centre rises then falls, bell-shaped loudness."""
    r = np.random.default_rng(seed)
    t = t_of(dur)
    u = t / dur
    centers = 500 + 2600 * np.sin(np.pi * np.clip(u * 1.08, 0, 1)) ** 1.5
    x = sweep_band(r.standard_normal(len(t)), centers, q=2.2)
    env = np.sin(np.pi * u) ** 2.2 * (1 + 0.15 * np.sin(2 * np.pi * 34 * t))
    whistle = np.sin(2 * np.pi * np.cumsum(centers * 0.9) / SR) * env * 0.06
    return finish(x * env + whistle, 0.75, 10)


def hit(seed):
    """The blade lands: a dull body thud, a cloth/flesh slap and a short steel ring."""
    r = np.random.default_rng(seed)
    t = t_of(0.6)
    f = 105 * np.exp(-6 * t) + 55
    thud = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-14 * t)
    slap = band(r.standard_normal(len(t)), 300, 2500) * np.exp(-60 * t) * 0.9
    ring = np.zeros_like(t)
    f0 = r.uniform(2100, 2500)
    for ratio, amp, dec in ((1.0, 0.22, 9), (2.76, 0.12, 13), (5.4, 0.06, 18)):
        ring += amp * np.sin(2 * np.pi * f0 * ratio * t + r.uniform(0, 6.28)) * np.exp(-dec * t)
    s = thud * 1.0 + slap + ring
    return finish(np.tanh(s * 1.3), 0.85, 20)


def whoosh(seed, dur=1.3):
    """The ghost flies over: a long airy whoosh (noise sweeping up then down), a wavering theremin-like gliss and a
    soft tail, so it reads as eerie rather than as wind."""
    r = np.random.default_rng(seed)
    t = t_of(dur)
    u = t / dur
    centers = 300 + 2200 * np.sin(np.pi * u) ** 1.2
    air = sweep_band(r.standard_normal(len(t)), centers, q=1.6)
    env = np.clip(u / 0.15, 0, 1) * np.clip((1 - u) / 0.45, 0, 1) ** 1.4
    f = 520 + 380 * np.sin(np.pi * u * 0.9) + 14 * np.sin(2 * np.pi * 5.5 * t)
    voice = (np.sin(2 * np.pi * np.cumsum(f) / SR) + 0.3 * np.sin(2 * np.pi * np.cumsum(f * 1.5) / SR)) * env * 0.22
    s = air * env + voice
    # a cheap room: a few decaying echoes
    out = s.copy()
    for d, g in ((0.043, 0.35), (0.071, 0.27), (0.113, 0.2), (0.17, 0.12)):
        k = int(d * SR)
        out[k:] += g * s[:-k]
    return finish(lowpass(out, 7000), 0.8, 30)


def fart(seed, dur, f0, f1, wet=0.3, squeak=0.0):
    """A comic fart: an irregular pulse train (flapping lips) through a low resonance, gliding f0 -> f1, fluttering
    loudness, some breath noise and a sputter at the end."""
    r = np.random.default_rng(seed)
    n = int(dur * SR)
    t = np.arange(n) / SR
    u = t / dur
    f = f0 + (f1 - f0) * u + 18 * np.sin(2 * np.pi * r.uniform(3, 7) * t) + squeak * 260 * np.clip(u - 0.6, 0, 1)
    out = np.zeros(n)
    pos = 0.0
    pulse_t = np.arange(int(0.03 * SR)) / SR
    form = r.uniform(280, 420)
    pulse = np.sin(2 * np.pi * form * pulse_t) * np.exp(-90 * pulse_t) + 0.5 * np.sin(2 * np.pi * form * 2.3 * pulse_t) * np.exp(-140 * pulse_t)
    while pos < n - len(pulse):
        i = int(pos)
        k = min(i, n - 1)
        amp = (0.6 + 0.4 * r.random()) * (1.0 if r.random() > wet * 0.25 else 0.25)
        out[i:i + len(pulse)] += amp * pulse
        pos += SR / max(30.0, f[k] * r.uniform(0.85, 1.18))
    env = np.clip(u / 0.04, 0, 1) * np.clip((1 - u) / 0.12, 0, 1) * (0.75 + 0.25 * np.sin(2 * np.pi * r.uniform(5, 11) * t) ** 2)
    breath = band(r.standard_normal(n), 200, 1800) * 0.25 * (wet + 0.2)
    x = out * env + breath * env
    if wet > 0.2:                                              # the sputter: a few late, separated blats
        for _ in range(int(2 + wet * 6)):
            a = int(r.uniform(0.75, 0.97) * n)
            ln = int(r.uniform(0.02, 0.05) * SR)
            if a + ln < n:
                x[a:a + ln] += np.tanh(3 * band(r.standard_normal(ln), 120, 900)) * 0.6 * np.hanning(ln)
    return finish(np.tanh(lowpass(x, 2600) * 2.0), 0.9, 15)


def safe_open(seed):
    """A heavy safe: the bolts slide back (clunk + metal clank), then the thick door creaks open on its hinges."""
    r = np.random.default_rng(seed)
    t = t_of(1.6)
    x = np.zeros_like(t)
    for k, d in enumerate((0.0, 0.11, 0.19)):                   # three bolts
        i = int(d * SR)
        tt = t[:len(t) - i]
        clank = sum(a * np.sin(2 * np.pi * fr * tt + r.uniform(0, 6.28)) * np.exp(-dc * tt)
                    for fr, a, dc in ((r.uniform(780, 860), 0.5, 22), (r.uniform(1300, 1420), 0.35, 30), (2210, 0.2, 40)))
        thud = np.sin(2 * np.pi * (70 + 40 * np.exp(-20 * tt)) * tt) * np.exp(-18 * tt)
        x[i:] += (thud * 0.9 + clank) * (1.0 - 0.2 * k)
    # hinge creak: stick-slip squeaks with a slowly rising pitch
    c0 = int(0.45 * SR)
    ct = t[c0:] - t[c0]
    fc = 520 + 260 * ct / ct[-1]
    creak = np.sin(2 * np.pi * np.cumsum(fc) / SR) * (0.5 + 0.5 * np.sign(np.sin(2 * np.pi * 38 * ct)))
    creak = band(creak, 300, 3000) * np.clip(ct / 0.1, 0, 1) * np.exp(-1.2 * ct) * 0.5
    x[c0:] += creak
    return finish(np.tanh(x * 1.2), 0.85, 30)


SOUNDS = [
    ('SFX_Ball_Clack_01', 'ball_clack', clack(1), 'Billiard balls clacking, hard click (synthesized)'),
    ('SFX_Ball_Clack_02', 'ball_clack', clack(2), 'Billiard balls clacking, variant 2 (synthesized)'),
    ('SFX_Ball_Clack_03', 'ball_clack', clack(3), 'Billiard balls clacking, variant 3 (synthesized)'),
    ('SFX_Sword_Swish_01', 'sword_swish', swish(11), 'Sword blade swish through the air (synthesized)'),
    ('SFX_Sword_Swish_02', 'sword_swish', swish(12, 0.32), 'Sword blade swish, shorter (synthesized)'),
    ('SFX_Sword_Hit_01', 'sword_hit', hit(21), 'Sword striking a body: thud, slap, short steel ring (synthesized)'),
    ('SFX_Sword_Hit_02', 'sword_hit', hit(22), 'Sword striking a body, variant 2 (synthesized)'),
    ('SFX_Swap_Whoosh_01', 'swap_whoosh', whoosh(31), 'Ghostly whoosh of the body-swap spirit flying over (synthesized)'),
    ('SFX_Fart_01', 'fart', fart(41, 0.9, 95, 70, wet=0.2), 'Comic fart, long and low (synthesized)'),
    ('SFX_Fart_02', 'fart', fart(42, 0.45, 140, 110, wet=0.1), 'Comic fart, short (synthesized)'),
    ('SFX_Fart_03', 'fart', fart(43, 1.4, 80, 60, wet=0.8), 'Comic fart, wet with a sputter (synthesized)'),
    ('SFX_Fart_04', 'fart', fart(44, 1.1, 110, 150, wet=0.15, squeak=1.0), 'Comic fart ending in a squeak (synthesized)'),
    ('SFX_Safe_Open_01', 'safe_open', safe_open(51), 'Heavy safe: bolts clunk back, door creaks open (synthesized)'),
]
os.makedirs(OUT, exist_ok=True)
report = []
for name, cat, x, desc in SOUNDS:
    path = os.path.join(OUT, name + '.wav')
    with wave.open(path, 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype('<i2').tobytes())
    report.append({'file': name + '.wav', 'category': cat, 'kind': 'oneshot', 'duration_s': round(len(x) / SR, 3),
                   'description': desc + ', Tools/audio/synth_pickups.py', 'generator': 'numpy synthesis (local)'})
    print(path, round(len(x) / SR, 2), 's')
with open(os.path.join(OUT, 'pickups_report.json'), 'w', encoding='utf-8') as fh:
    json.dump(report, fh, indent=1)
print('report', len(report))
