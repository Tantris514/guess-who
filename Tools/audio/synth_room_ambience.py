"""Per-room ambience beds for L_Manor (local numpy synthesis, no model), all seamless loops.

  python -X utf8 Tools\\audio\\synth_room_ambience.py

Seamless by construction: noise beds are shaped in the frequency domain (an inverse FFT is periodic), every event is added
with wrap-around (np.add.at on indices modulo the loop length), and the beds derived from AMB_Crowd (already a seamless
41.35 s loop) are filtered / reverberated by circular (FFT) convolution, so the loop end flows into its start.

Writes AssetGen/audio/final/ambience/AMB_Room_*.wav (mono 44.1 kHz) + ambience_report.json. Placed by
Tools/audio/room_ambience.py (one box-attenuated actor per room, crossfading at the doors), kept well under voices/music:
beds at -27..-34 LUFS (voices are -14..-21 LUFS, AMB_Crowd -24)."""
import json
import os
import sys

import numpy as np
import soundfile as sf

SR = 44100
AUD = r'J:\Projets\Unreal_Projects\Guess Who\AssetGen\audio'
OUT = os.path.join(AUD, 'final', 'ambience')
sys.path.insert(0, AUD)
import audiolib as A  # noqa: E402  (BS.1770 loudness, metrics)

rng = np.random.default_rng(1930)


# ------------------------------------------------------------------ building blocks
def shaped_noise(n, lo, hi, tilt=0.0):
    """Periodic noise with a band-limited spectrum (tilt dB/octave above lo)."""
    f = np.fft.rfftfreq(n, 1 / SR)
    mag = ((f >= lo) & (f <= hi)).astype(float)
    edge = 0.25
    mag = np.clip(np.minimum((f - lo * (1 - edge)) / (lo * edge + 1e-9), (hi * (1 + edge) - f) / (hi * edge)), 0, 1)
    mag *= np.where(f > 0, (np.maximum(f, 1) / max(lo, 1)) ** (tilt / 6.02), 0)
    spec = mag * np.exp(2j * np.pi * rng.random(len(f)))
    x = np.fft.irfft(spec, n)
    return x / (np.std(x) + 1e-12)


def circ_filter(x, lo=None, hi=None):
    f = np.fft.rfftfreq(len(x), 1 / SR)
    g = np.ones_like(f)
    if lo:
        g *= 1 / np.sqrt(1 + (lo / np.maximum(f, 1)) ** 4)
    if hi:
        g *= 1 / np.sqrt(1 + (f / hi) ** 4)
    return np.fft.irfft(np.fft.rfft(x) * g, len(x))


def circ_reverb(x, rt60, wet, predelay=0.03, damp_hz=4000):
    n = len(x)
    L = int(rt60 * 1.3 * SR)
    t = np.arange(L) / SR
    ir = rng.standard_normal(L) * np.exp(-6.9 * t / rt60)
    ir[: int(predelay * SR)] = 0
    ir = circ_filter(np.pad(ir, (0, n - L)), hi=damp_hz)[:L] if L < n else ir
    h = np.zeros(n); h[:min(L, n)] = ir[:min(L, n)]
    w = np.fft.irfft(np.fft.rfft(x) * np.fft.rfft(h), n)
    w *= np.std(x) / (np.std(w) + 1e-12)
    return (1 - wet) * x + wet * w


def place(out, ev, at):
    idx = (np.arange(len(ev)) + int(at)) % len(out)
    np.add.at(out, idx, ev)


def resonator_hit(dur, partials, noise_ms=1.5, noise_amp=0.4):
    """Struck object: decaying sinusoidal partials (f, amp, decay /s) + a short noise transient."""
    tt = np.arange(int(dur * SR)) / SR
    s = np.zeros_like(tt)
    for f, a, d in partials:
        s += a * np.sin(2 * np.pi * f * tt + rng.uniform(0, 6.28)) * np.exp(-d * tt)
    nl = int(noise_ms / 1000 * SR)
    s[:nl] += noise_amp * rng.standard_normal(nl) * np.linspace(1, 0, nl)
    return s


def swish(dur, lo, hi):
    n = int(dur * SR)
    x = shaped_noise(n, lo, hi)
    env = np.sin(np.linspace(0, np.pi, n)) ** 2
    flutter = 1 + 0.5 * np.sin(2 * np.pi * rng.uniform(18, 35) * np.arange(n) / SR + rng.uniform(0, 6))
    return x * env * flutter


def load_mono(path):
    x, sr = sf.read(path, always_2d=True)
    assert sr == SR
    return x.mean(axis=1)


# ------------------------------------------------------------------ the sounds
def clock(n, period, pitch=1.0, level=0.5):
    out = np.zeros(n)
    k = 0
    for at in np.arange(0.31 * SR, n + 0.31 * SR - 1, period * SR):   # off the loop point; wrap-around keeps the count
        p = pitch * (1.0 if k % 2 == 0 else 0.88)    # tick / tock
        hit = resonator_hit(0.12, [(2300 * p, 0.6, 70), (3500 * p, 0.4, 90), (5200 * p, 0.25, 120), (420 * p, 0.5, 60)], 1.0, 0.5)
        place(out, level * hit * rng.uniform(0.9, 1.05), at)
        k += 1
    return out


def library(n):
    bed = 0.012 * shaped_noise(n, 40, 300, tilt=-3)                      # room tone
    out = bed + clock(n, 1.0, 1.0, 0.18)                                  # grandfather clock, 1 s
    t = rng.uniform(3, 8)
    while t < n / SR:                                                     # a page turned now and then
        place(out, 0.05 * swish(rng.uniform(0.35, 0.7), 900, 7000), t * SR)
        t += rng.uniform(6, 15)
    return out


def study(n):
    out = 0.012 * shaped_noise(n, 40, 300, tilt=-3)      # (the mantel clock is gone: the user's test of 2026-11-05, "annoying tic tac")
    t = rng.uniform(4, 9)
    while t < n / SR - 1:                                                 # typewriter bursts
        strokes = rng.integers(8, 26)
        for _ in range(strokes):
            key = resonator_hit(0.08, [(rng.uniform(2200, 3200), 0.5, 120), (rng.uniform(4000, 5500), 0.3, 160), (220, 0.6, 90)], 0.8, 0.9)
            place(out, 0.16 * key * rng.uniform(0.7, 1.0), t * SR)
            t += rng.uniform(0.09, 0.22) + (rng.uniform(0.2, 0.5) if rng.random() < 0.12 else 0)
        if rng.random() < 0.6:                                            # end of line: bell + carriage return
            place(out, 0.10 * resonator_hit(0.9, [(2210, 0.7, 5), (5480, 0.25, 9)], 0.5, 0.2), t * SR)
            place(out, 0.05 * swish(0.45, 300, 3000), (t + 0.15) * SR)
        t += rng.uniform(12, 22)
    return out


def billiard(n, crowd):
    talk = 0.35 * circ_filter(crowd, lo=120, hi=900)                      # low talk
    out = talk + 0.01 * shaped_noise(n, 40, 250, tilt=-3)
    t = rng.uniform(2, 5)
    while t < n / SR - 1:
        place(out, 0.10 * resonator_hit(0.06, [(1350, 0.6, 90), (2600, 0.3, 140)], 1.0, 0.4), t * SR)     # cue tip
        c = t + rng.uniform(0.15, 0.45)
        for _ in range(rng.integers(1, 4)):                               # ball-ball clacks
            place(out, 0.22 * resonator_hit(0.05, [(rng.uniform(3600, 4400), 0.7, 180), (rng.uniform(6500, 7600), 0.4, 240)], 0.5, 0.8), c * SR)
            c += rng.uniform(0.25, 0.9)
        if rng.random() < 0.4:                                            # cushion thump / pocket drop
            place(out, 0.12 * resonator_hit(0.15, [(140, 0.8, 30), (310, 0.4, 45)], 2.0, 0.3), c * SR)
        t += rng.uniform(5, 11)
    return out


def dining(n, crowd):
    out = 0.25 * circ_filter(crowd, lo=150, hi=1500) + 0.01 * shaped_noise(n, 40, 250, tilt=-3)
    t = 0.3
    while t < n / SR:
        if rng.random() < 0.7:                                            # cutlery on porcelain
            p = [(rng.uniform(2800, 4200), 0.5, 45), (rng.uniform(5200, 7800), 0.3, 70), (rng.uniform(1200, 1900), 0.4, 35)]
        else:                                                             # plate / cup set down
            p = [(rng.uniform(900, 1600), 0.6, 25), (rng.uniform(2500, 3300), 0.3, 40)]
        place(out, rng.uniform(0.04, 0.10) * resonator_hit(0.25, p, 0.8, 0.5), t * SR)
        t += rng.exponential(0.9) + 0.12
    return out


def conservatory(n):
    # fountain: falling-water noise with a darker tilt and a slow gurgle (periodic amplitude modulation from shaped noise)
    gurgle = 1 + 0.45 * shaped_noise(n, 2, 9)
    water = 0.02 * shaped_noise(n, 200, 4500, tilt=-4.5) * np.clip(gurgle, 0.2, 2.0)
    out = water
    for _ in range(int(n / SR * 28)):                                     # droplets / bubbles
        f0 = rng.uniform(500, 1400); d = rng.uniform(0.015, 0.04)
        tt = np.arange(int(d * SR)) / SR
        drop = np.sin(2 * np.pi * (f0 * tt + 0.5 * f0 * 3 * tt * tt / d)) * np.exp(-tt / (d / 3))
        place(out, rng.uniform(0.006, 0.03) * drop, rng.uniform(0, n))
    for f, rate, lvl in ((4400, 0.62, 0.022), (4750, 0.81, 0.015), (4150, 0.55, 0.011)):   # three crickets
        t = rng.uniform(0, rate)
        while t < n / SR:
            for s in range(3):                                            # one chirp = three syllables
                d = 0.018
                tt = np.arange(int(d * SR)) / SR
                syl = np.sin(2 * np.pi * f * tt) * np.sin(np.pi * tt / d) ** 2
                place(out, lvl * syl, (t + s * 0.033) * SR)
            t += rate * rng.uniform(0.95, 1.05)
    return out


def hall(crowd):
    return circ_reverb(circ_filter(crowd, lo=90, hi=6000), rt60=2.4, wet=0.65, predelay=0.04, damp_hz=3500)


def corridor(n, crowd):
    return 0.5 * circ_filter(crowd, lo=100, hi=450) + 0.02 * shaped_noise(n, 30, 220, tilt=-3)


# ------------------------------------------------------------------ build
def main():
    os.makedirs(OUT, exist_ok=True)
    crowd = load_mono(os.path.join(AUD, 'final', 'AMB_Crowd.wav'))
    nc = len(crowd)
    n40 = 40 * SR
    SPEC = [  # name, signal, target LUFS, description
        ('AMB_Room_Library', library(n40), -31.0, 'library: grandfather clock (1 s tick-tock), a page turned now and then, quiet room tone'),
        ('AMB_Room_Study', study(n40), -31.0, 'study: typewriter bursts with the carriage bell, room tone'),
        ('AMB_Room_Billiard', billiard(nc, crowd), -28.0, 'billiard room: cue strikes and ball clacks, low talk (crowd low-passed), room tone'),
        ('AMB_Room_Dining', dining(nc, crowd), -29.0, 'dining room: cutlery and porcelain, muffled conversation'),
        ('AMB_Room_Conservatory', conservatory(n40), -30.0, 'conservatory: fountain water and droplets, three crickets (rain on the glass is AMB_Rain)'),
        ('AMB_Room_Hall', hall(crowd), -27.0, 'entrance hall: the party crowd with a long stone-hall reverb (RT60 2.4 s)'),
        ('AMB_Room_Corridor', corridor(nc, crowd), -34.0, 'corridors: quiet room tone and the party murmur heard through walls (low-passed 450 Hz)'),
    ]
    report = []
    if len(sys.argv) > 1:                                  # names given: only those are rewritten (the report stays as it is)
        SPEC = [s for s in SPEC if s[0] in sys.argv[1:]]
    for name, x, tgt, desc in SPEC:
        x = x - x.mean()
        y, g, lim = A.gain_to(x[:, None], SR, target_lufs=tgt, tp_ceiling=-6.0)
        path = os.path.join(OUT, name + '.wav')
        A.save_wav(path, y, SR)
        y2, _ = A.load(path)
        m = A.metrics(y2, SR)
        jump = float(abs(y2[0, 0] - y2[-1, 0]))
        report.append({'file': name + '.wav', 'category': 'ambience', 'kind': 'loop', 'description': desc,
                       'duration_s': m['duration'], 'lufs': m['lufs'], 'true_peak_dbtp': m['true_peak_dbtp'],
                       'loop_seam_sample_jump': round(jump, 5), 'generator': 'numpy synthesis (Tools/audio/synth_room_ambience.py)'
                       + (' + AMB_Crowd (Stable Audio 3) circularly filtered' if name in ('AMB_Room_Billiard', 'AMB_Room_Dining', 'AMB_Room_Hall', 'AMB_Room_Corridor') else '')})
        A.spectrogram_png(os.path.join(AUD, 'qa', 'panic_png', 'amb_' + name + '.png'), y2, SR, name)
        print(f"{name:24s} {m['duration']:6.2f}s lufs={m['lufs']:6.1f} tp={m['true_peak_dbtp']:5.1f} seam_jump={jump:.4f}", flush=True)
    if len(sys.argv) <= 1:
        json.dump(report, open(os.path.join(OUT, 'ambience_report.json'), 'w', encoding='utf-8'), indent=1)


if __name__ == '__main__':
    main()
