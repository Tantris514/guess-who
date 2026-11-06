"""Procedural SFX for the social life (numpy; run with the ComfyUI venv python -I): polite ballroom applause when a
dance ends, glass clinks (a toast) at the bar. Writes Tools/anim/sfx/SFX_Social_Applause_0N.wav and
SFX_Social_Clink_0N.wav (44.1 kHz, 16-bit mono) + a contact image of the waveforms for a quick check.
Imported by Tools/anim/import_sfx.py into /Game/GW/Audio/Social.
"""
import os
import wave

import numpy as np

SR = 44100
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sfx')


def bandpass(x, lo, hi):
    f = np.fft.rfft(x)
    fr = np.fft.rfftfreq(len(x), 1 / SR)
    w = np.clip((fr - lo * 0.7) / (lo * 0.3 + 1e-9), 0, 1) * np.clip((hi * 1.3 - fr) / (hi * 0.3 + 1e-9), 0, 1)
    return np.fft.irfft(f * w, len(x))


def room(x, rt=0.45, wet=0.22, seed=0):
    """Small ballroom reverb: convolution with decaying, slightly low-passed noise."""
    rng = np.random.default_rng(seed)
    n = int(SR * rt * 1.6)
    ir = rng.standard_normal(n) * np.exp(-6.9 * np.arange(n) / (SR * rt))
    ir = bandpass(ir, 150, 5000)
    ir /= np.abs(ir).max()
    y = np.convolve(x, ir)[:len(x) + n]
    out = np.zeros_like(y)
    out[:len(x)] = x
    return out * (1 - wet) + y / (np.abs(y).max() + 1e-9) * np.abs(x).max() * wet


def applause(seed, dur=4.2, people=11):
    rng = np.random.default_rng(seed)
    n = int(SR * dur)
    x = np.zeros(n)
    for p in range(people):
        rate = rng.uniform(3.2, 4.6)                      # claps per second
        start = rng.uniform(0.0, 0.6)
        stop = dur - rng.uniform(0.6, 1.6)
        hand = rng.uniform(900, 2300)                     # each person's hands sound different
        gain = rng.uniform(0.4, 1.0) * (0.55 if rng.random() < 0.3 else 1.0)     # some far away
        t = start
        while t < stop:
            i = int(t * SR)
            L = int(SR * rng.uniform(0.006, 0.012))
            burst = rng.standard_normal(L) * np.exp(-np.arange(L) / (L * 0.25))
            burst = bandpass(np.pad(burst, (0, 512)), hand * 0.6, hand * 2.2)[:L + 512]
            env = min(1.0, (t - start) / 0.5, (stop - t) / 0.8)   # swell in, die out
            seg = burst * gain * max(env, 0.15) * rng.uniform(0.7, 1.0)
            x[i:i + len(seg)] += seg[:max(0, min(len(seg), n - i))]
            t += 1.0 / rate * rng.uniform(0.85, 1.15)
    x = room(x, rt=0.6, wet=0.3, seed=seed)
    fade = np.ones(len(x))
    k = int(SR * 0.4)
    fade[-k:] = np.linspace(1, 0, k)
    return x * fade


def clink(seed, glasses=2):
    rng = np.random.default_rng(seed)
    n = int(SR * 1.6)
    x = np.zeros(n)
    t0 = 0.02
    for g in range(glasses):
        f0 = rng.uniform(2300, 3300)
        i = int((t0 + g * rng.uniform(0.05, 0.11)) * SR)
        tt = np.arange(n - i) / SR
        tone = np.zeros(n - i)
        for ratio, amp, dec in ((1.0, 1.0, 2.6), (2.32, 0.5, 4.5), (4.25, 0.28, 7.0), (1.51, 0.18, 3.5)):
            tone += amp * np.sin(2 * np.pi * f0 * ratio * tt + rng.uniform(0, 6.28)) * np.exp(-dec * tt * rng.uniform(0.85, 1.2))
        click = rng.standard_normal(n - i) * np.exp(-tt * 900) * 0.6           # the glass touch
        x[i:] += (tone * 0.5 + bandpass(click, 2000, 9000)) * rng.uniform(0.6, 1.0)
    return room(x, rt=0.35, wet=0.18, seed=seed)


def save(name, x, peak=0.6):
    x = x / (np.abs(x).max() + 1e-9) * peak
    loud = np.nonzero(np.abs(x) > 0.004)[0]                 # trim the near-silent tail, then a 60 ms fade
    end = min(len(x), (loud[-1] if len(loud) else len(x)) + int(0.12 * SR))
    x = x[:end].copy()
    k = int(0.06 * SR)
    x[-k:] *= np.linspace(1.0, 0.0, k)
    os.makedirs(OUT, exist_ok=True)
    p = os.path.join(OUT, name + '.wav')
    with wave.open(p, 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype('<i2').tobytes())
    return p, x


if __name__ == '__main__':
    made = []
    for k in range(3):
        made.append(save(f'SFX_Social_Applause_0{k + 1}', applause(100 + k), 0.55))
        made.append(save(f'SFX_Social_Clink_0{k + 1}', clink(200 + k, glasses=2 + (k == 2)), 0.5))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axs = plt.subplots(len(made), 1, figsize=(10, 1.4 * len(made)))
    for ax, (p, x) in zip(axs, made):
        ax.plot(np.arange(len(x)) / SR, x, lw=0.4)
        ax.set_title(os.path.basename(p), fontsize=8)
        ax.set_ylim(-0.7, 0.7)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, 'waveforms.png'), dpi=60)
    for p, x in made:
        print(os.path.basename(p), f'{len(x) / SR:.2f} s', 'peak', round(float(np.abs(x).max()), 2),
              'rms', round(float(np.sqrt((x ** 2).mean())), 3))
