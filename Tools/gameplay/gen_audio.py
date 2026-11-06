"""Procedural sound effects for the game (no external assets). Usage: python gen_audio.py <outdir>"""
import sys, wave
import numpy as np
out = sys.argv[1]
SR = 44100
rng = np.random.default_rng(7)

def save(name, x):
    x = x / (np.max(np.abs(x)) + 1e-9) * 0.9
    pcm = (x * 32767).astype(np.int16)
    with wave.open(f'{out}/{name}.wav', 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())

def lowpass(x, a):
    y = np.zeros_like(x); acc = 0.0
    for i, v in enumerate(x):
        acc += a * (v - acc); y[i] = acc
    return y

# gunshot: crack + boom + room tail
n = int(SR * 1.2); t = np.arange(n) / SR
noise = rng.standard_normal(n)
crack = noise * np.exp(-t * 90)
boom = np.sin(2 * np.pi * (70 * t + 30 * np.exp(-t * 20))) * np.exp(-t * 14)
tail = lowpass(noise, 0.08) * np.exp(-t * 4.5) * 0.6
x = crack * 1.0 + boom * 1.4 + tail
x[: int(SR * 0.002)] *= np.linspace(0, 1, int(SR * 0.002))
save('S_GW_Gunshot', x)

# round start: soft gong / bell
n = int(SR * 3.5); t = np.arange(n) / SR
f0 = 196.0
partials = [(1.0, 1.0, 1.2), (2.01, 0.6, 1.8), (2.76, 0.45, 2.4), (4.07, 0.3, 3.2), (5.43, 0.2, 4.0), (0.5, 0.5, 0.9)]
x = sum(a * np.sin(2 * np.pi * f0 * r * t) * np.exp(-t * d) for r, a, d in partials)
x *= np.minimum(1, t / 0.01)
save('S_GW_Gong', x)

# win chime: arpeggio C E G C
n = int(SR * 2.4); t = np.arange(n) / SR; x = np.zeros(n)
for k, f in enumerate([523.25, 659.25, 783.99, 1046.5]):
    st = int(SR * 0.16 * k); tt = t[: n - st]
    x[st:] += (np.sin(2 * np.pi * f * tt) + 0.3 * np.sin(4 * np.pi * f * tt)) * np.exp(-tt * 2.5)
save('S_GW_Chime', x)

# lose / sombre: descending minor
n = int(SR * 2.4); t = np.arange(n) / SR; x = np.zeros(n)
for k, f in enumerate([440.0, 349.23, 293.66, 220.0]):
    st = int(SR * 0.22 * k); tt = t[: n - st]
    x[st:] += (np.sin(2 * np.pi * f * tt) + 0.4 * np.sin(2 * np.pi * 2 * f * tt)) * np.exp(-tt * 2.0)
save('S_GW_Sombre', x)

# body fall thud
n = int(SR * 0.7); t = np.arange(n) / SR
x = np.sin(2 * np.pi * (55 * t + 25 * np.exp(-t * 30))) * np.exp(-t * 9) + lowpass(rng.standard_normal(n), 0.05) * np.exp(-t * 12) * 0.8
save('S_GW_Thud', x)
print('ok')
