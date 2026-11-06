"""Voice processing for the panic/event lines (numpy/scipy/librosa):
  whisperise(x, sr, voice_mix)  LPC analysis/resynthesis with a noise source (a real whisper is the vocal tract excited by
                                turbulent noise), plus a small amount of the original murmur for naturalness.
  robotise(x, sr)               LPC vocoder on a fixed-pitch pulse train (monotone, deep), noise on unvoiced frames, then a
                                metallic comb resonance and a little ring modulation: the 1930s 'automaton' voice."""
import numpy as np
from scipy import signal
import librosa


def _frames_lpc(x, sr, exc, order, n=512, hop=128, pre=0.97):
    """Overlap-add LPC cross-synthesis: spectral envelope of x per frame, excitation `exc` (same length), gain matched."""
    xp = signal.lfilter([1, -pre], [1], x)
    win = np.hanning(n)
    y = np.zeros(len(x) + n)
    norm = np.zeros(len(x) + n)
    for s in range(0, len(x) - n, hop):
        fr = xp[s:s + n] * win
        if np.sqrt(np.mean(fr ** 2)) < 1e-6:
            continue
        a = librosa.lpc(fr.astype(np.float64) + 1e-9 * np.random.randn(n), order=order)
        res = signal.lfilter(a, [1], fr)
        g = np.sqrt(np.mean(res ** 2))
        e = exc[s:s + n] * win
        e = e / (np.sqrt(np.mean(e ** 2)) + 1e-12) * g
        out = signal.lfilter([1], a, e)
        if not np.all(np.isfinite(out)) or np.max(np.abs(out)) > 50 * (np.max(np.abs(fr)) + 1e-9):
            continue
        y[s:s + n] += out * win
        norm[s:s + n] += win ** 2
    y = y[:len(x)] / np.maximum(norm[:len(x)], 1e-3)
    return signal.lfilter([1], [1, -pre], y)


def whisperise(x, sr, voice_mix=0.15, seed=0):
    x = np.asarray(x, dtype=np.float64)
    rng = np.random.default_rng(seed)
    noise = rng.standard_normal(len(x))
    w = _frames_lpc(x, sr, noise, order=int(sr / 1000) + 4)
    # whispers have no voicing bar: thin the lows, keep the air
    w = signal.sosfiltfilt(signal.butter(2, 260 / (sr / 2), btype="highpass", output="sos"), w)
    w = w / (np.sqrt(np.mean(w ** 2)) + 1e-12) * np.sqrt(np.mean(x ** 2))
    v = signal.sosfiltfilt(signal.butter(2, 180 / (sr / 2), btype="highpass", output="sos"), x)
    return (1 - voice_mix) * w + voice_mix * v


def robotise(x, sr, f0=58.0, comb_ms=4.2, comb_fb=0.55, ring_hz=34.0, ring_mix=0.25, seed=0):
    x = np.asarray(x, dtype=np.float64)
    rng = np.random.default_rng(seed)
    t = np.arange(len(x)) / sr
    # band-limited buzz: sum of harmonics of f0 (sawtooth-like), plus a little noise
    buzz = np.zeros(len(x))
    k = 1
    while k * f0 < 0.45 * sr and k <= 120:
        buzz += np.sin(2 * np.pi * k * f0 * t) / k ** 0.6
        k += 1
    noise = rng.standard_normal(len(x))
    # voiced / unvoiced per sample from pyin (fricatives keep a noise source so the words stay intelligible)
    _, vflag, _ = librosa.pyin(x.astype(np.float32), fmin=50, fmax=500, sr=sr, frame_length=1024, hop_length=256)
    vs = np.repeat(vflag.astype(float), 256)[:len(x)]
    vs = np.pad(vs, (0, max(0, len(x) - len(vs))), constant_values=0)
    vs = np.convolve(vs, np.ones(240) / 240, mode="same")
    exc = vs * buzz / (np.std(buzz) + 1e-9) + (1 - vs) * noise * 0.8
    y = _frames_lpc(x, sr, exc, order=int(sr / 1000) + 6)
    # metallic resonance (feedback comb) and ring modulation
    d = int(comb_ms / 1000 * sr)
    y = signal.lfilter([1], np.concatenate([[1], np.zeros(d - 1), [-comb_fb]]), y)
    y = (1 - ring_mix) * y + ring_mix * y * np.sin(2 * np.pi * ring_hz * t)
    y = signal.sosfiltfilt(signal.butter(2, [70 / (sr / 2), 7000 / (sr / 2)], btype="band", output="sos"), y)
    return y / (np.max(np.abs(y)) + 1e-9) * 0.9
