"""Audio QA + mastering helpers (numpy/scipy/soundfile/librosa from the ComfyUI venv).

Loudness = ITU-R BS.1770-4 (K-weighting, 400 ms blocks, -70 LUFS absolute + -10 LU relative gating), implemented here
(pyloudnorm is not installed). True peak is estimated with 4x polyphase oversampling.
"""
import math
import numpy as np
import soundfile as sf
from scipy import signal


def load(path):
    x, sr = sf.read(path, always_2d=True, dtype="float64")
    return x, sr


def save_wav(path, x, sr):
    x = np.clip(x, -1.0, 1.0)
    sf.write(path, x if x.shape[1] > 1 else x[:, 0], sr, subtype="PCM_16")


def db(v):
    return 20 * math.log10(max(float(v), 1e-12))


# ---------------------------------------------------------------- BS.1770 loudness
def _biquad_shelf(sr, G=3.999843853973347, Q=0.7071752369554196, fc=1681.974450955533):
    A = 10 ** (G / 40.0); w0 = 2 * math.pi * fc / sr; alpha = math.sin(w0) / (2 * Q); c = math.cos(w0)
    b0 = A * ((A + 1) + (A - 1) * c + 2 * math.sqrt(A) * alpha)
    b1 = -2 * A * ((A - 1) + (A + 1) * c)
    b2 = A * ((A + 1) + (A - 1) * c - 2 * math.sqrt(A) * alpha)
    a0 = (A + 1) - (A - 1) * c + 2 * math.sqrt(A) * alpha
    a1 = 2 * ((A - 1) - (A + 1) * c)
    a2 = (A + 1) - (A - 1) * c - 2 * math.sqrt(A) * alpha
    return np.array([b0, b1, b2]) / a0, np.array([1.0, a1 / a0, a2 / a0])


def _biquad_hp(sr, Q=0.5003270373238773, fc=38.13547087602444):
    w0 = 2 * math.pi * fc / sr; alpha = math.sin(w0) / (2 * Q); c = math.cos(w0)
    b = np.array([(1 + c) / 2, -(1 + c), (1 + c) / 2]); a = np.array([1 + alpha, -2 * c, 1 - alpha])
    return b / a[0], a / a[0]


def kweight(x, sr):
    b1, a1 = _biquad_shelf(sr); b2, a2 = _biquad_hp(sr)
    return signal.lfilter(b2, a2, signal.lfilter(b1, a1, x, axis=0), axis=0)


def block_loudness(x, sr, block=0.4, overlap=0.75):
    y = kweight(x, sr)
    n = int(block * sr); hop = max(1, int(n * (1 - overlap)))
    if len(y) < n:
        y = np.vstack([y, np.zeros((n - len(y), y.shape[1]))])
    zs = []
    for s in range(0, len(y) - n + 1, hop):
        zs.append(np.mean(y[s:s + n] ** 2, axis=0).sum())
    z = np.array(zs)
    return -0.691 + 10 * np.log10(np.maximum(z, 1e-12)), z


def lufs(x, sr):
    l, z = block_loudness(x, sr)
    keep = l > -70
    if not keep.any():
        return -70.0
    rel = -0.691 + 10 * math.log10(z[keep].mean()) - 10
    keep2 = keep & (l > rel)
    return -0.691 + 10 * math.log10(z[keep2].mean()) if keep2.any() else -70.0


def max_momentary(x, sr):
    l, _ = block_loudness(x, sr)
    return float(l.max())


def true_peak(x):
    up = signal.resample_poly(x, 4, 1, axis=0)
    return float(np.max(np.abs(up)))


# ---------------------------------------------------------------- metrics
def metrics(x, sr):
    mono = x.mean(axis=1)
    dur = len(x) / sr
    peak = float(np.max(np.abs(x)))
    rms = float(np.sqrt(np.mean(mono ** 2)))
    clip = int(np.sum(np.abs(x) >= 0.999))
    dc = [float(v) for v in x.mean(axis=0)]
    # 50 ms frame energies for silence analysis
    fl = int(0.05 * sr)
    nfr = max(1, len(mono) // fl)
    fe = np.array([np.sqrt(np.mean(mono[i * fl:(i + 1) * fl] ** 2) + 1e-20) for i in range(nfr)])
    fdb = 20 * np.log10(fe + 1e-12)
    silent = fdb < -60
    lead = int(np.argmax(~silent)) * 0.05 if (~silent).any() else dur
    trail = int(np.argmax(~silent[::-1])) * 0.05 if (~silent).any() else dur
    # longest silent run inside the active part
    act = np.where(~silent)[0]
    gap = 0.0
    if len(act) > 1:
        inner = silent[act[0]:act[-1] + 1]
        run = best = 0
        for s in inner:
            run = run + 1 if s else 0
            best = max(best, run)
        gap = best * 0.05
    # spectrum
    f, P = signal.welch(mono, sr, nperseg=4096)
    P = P + 1e-20
    centroid = float(np.sum(f * P) / np.sum(P))
    flatness = float(np.exp(np.mean(np.log(P[f > 50]))) / np.mean(P[f > 50]))
    hf = float(P[f > 12000].sum() / P.sum())
    lf = float(P[f < 120].sum() / P.sum())
    return {
        "sr": sr, "channels": x.shape[1], "duration": round(dur, 3), "peak_dbfs": round(db(peak), 2),
        "true_peak_dbtp": round(db(true_peak(x)), 2), "rms_dbfs": round(db(rms), 2), "lufs": round(lufs(x, sr), 2),
        "max_momentary_lufs": round(max_momentary(x, sr), 2), "clipped_samples": clip, "dc": [round(v, 5) for v in dc],
        "lead_silence_s": round(lead, 2), "trail_silence_s": round(trail, 2), "longest_inner_silence_s": round(gap, 2),
        "silent_fraction": round(float(silent.mean()), 3), "centroid_hz": round(centroid), "flatness": round(flatness, 4),
        "hf_ratio_12k": round(hf, 4), "lf_ratio_120": round(lf, 4),
    }


# ---------------------------------------------------------------- processing
def remove_dc(x):
    b, a = signal.butter(2, 20 / 22050 if False else 0.0009, btype="highpass")
    return signal.filtfilt(b, a, x, axis=0)


def highpass(x, sr, fc=25):
    b, a = signal.butter(2, fc / (sr / 2), btype="highpass")
    return signal.filtfilt(b, a, x, axis=0)


def trim_oneshot(x, sr, pre=0.004, floor_db=-55, tail_fade=0.08):
    mono = np.abs(x).max(axis=1)
    thr = 10 ** (floor_db / 20) * max(mono.max(), 1e-9)
    idx = np.where(mono > thr)[0]
    if len(idx) == 0:
        return x
    s = max(0, idx[0] - int(pre * sr)); e = min(len(x), idx[-1] + int(0.02 * sr))
    y = x[s:e].copy()
    fi = int(0.002 * sr); y[:fi] *= np.linspace(0, 1, fi)[:, None]
    fo = min(len(y) // 3, int(tail_fade * sr)); y[-fo:] *= np.linspace(1, 0, fo)[:, None] ** 2
    return y


def onset_peak_trim(x, sr, keep=0.6, pre=0.003):
    """For UI ticks: keep only the strongest transient (keep seconds after it)."""
    mono = np.abs(x).max(axis=1)
    pk = int(np.argmax(mono))
    # walk back to the onset (first sample above 10 % of the peak within 60 ms before)
    w = mono[max(0, pk - int(0.06 * sr)):pk + 1]
    on = pk - len(w) + 1 + int(np.argmax(w > 0.1 * mono[pk]))
    s = max(0, on - int(pre * sr)); e = min(len(x), s + int(keep * sr))
    y = x[s:e].copy()
    fi = int(0.0015 * sr); y[:fi] *= np.linspace(0, 1, fi)[:, None]
    fo = int(len(y) * 0.5); y[-fo:] *= np.linspace(1, 0, fo)[:, None] ** 2
    return y


def gain_to(x, sr, target_lufs=None, target_mom=None, tp_ceiling=-1.0):
    if target_lufs is not None:
        cur = lufs(x, sr)
        g = 10 ** ((target_lufs - cur) / 20)
    else:
        cur = max_momentary(x, sr)
        g = 10 ** ((target_mom - cur) / 20)
    y = x * g
    tp = true_peak(y)
    ceil = 10 ** (tp_ceiling / 20)
    limited = False
    if tp > ceil:
        y = soft_limit(y, sr, ceil)
        limited = True
    return y, round(db(g), 2), limited


def soft_limit(x, sr, ceil, release=0.08):
    """Simple look-ahead peak limiter (gain computer on the 4x-oversampled envelope)."""
    env = np.abs(signal.resample_poly(x, 4, 1, axis=0)).max(axis=1)[::4][:len(x)]
    need = np.minimum(1.0, ceil / np.maximum(env, 1e-9))
    la = int(0.005 * sr)
    need = np.minimum.accumulate(np.concatenate([need[la:], np.ones(la)])[::-1])[::-1] if False else need
    # look-ahead min filter + release smoothing
    from scipy.ndimage import minimum_filter1d
    g = minimum_filter1d(need, size=2 * la + 1)
    a = math.exp(-1.0 / (release * sr))
    out = np.empty_like(g); cur = 1.0
    for i, v in enumerate(g):
        cur = v if v < cur else a * cur + (1 - a) * v
        out[i] = cur
    y = x * out[:, None]
    tp = true_peak(y)
    if tp > ceil:
        y *= ceil / tp
    return y


def to_mono(x):
    return x.mean(axis=1, keepdims=True)


def resample(x, sr, to=48000):
    if sr == to:
        return x, sr
    g = math.gcd(sr, to)
    return signal.resample_poly(x, to // g, sr // g, axis=0), to


# ---------------------------------------------------------------- loops
def make_loop(x, sr, s, e, xfade):
    """Seamless loop of x[s:e]: the last xfade seconds are an equal-power crossfade into the audio that precedes s,
    so the wrap y[-1] -> y[0] continues exactly like x[s-1] -> x[s]."""
    L = int(xfade * sr)
    assert s >= L, "loop start must leave room for the crossfade"
    y = x[s:e].copy()
    t = np.linspace(0, 1, L)[:, None]
    fo, fi = np.cos(t * math.pi / 2), np.sin(t * math.pi / 2)
    y[-L:] = x[e - L:e] * fo + x[s - L:s] * fi
    return y


def seam_report(y, sr):
    """Compare the spectral flux across the wrap point with the flux distribution inside the loop."""
    n = 2048; hop = 512
    def spec(seg):
        f, t, Z = signal.stft(seg.mean(axis=1), sr, nperseg=n, noverlap=n - hop)
        return np.abs(Z)
    S = spec(y)
    flux = np.sqrt((np.diff(S, axis=1).clip(min=0) ** 2).sum(axis=0))
    wrap = np.vstack([y[-n * 4:], y[:n * 4]])
    W = spec(wrap)
    wf = np.sqrt((np.diff(W, axis=1).clip(min=0) ** 2).sum(axis=0))
    mid = len(wf) // 2
    seam = float(wf[mid - 3:mid + 3].max())
    jump = float(np.abs(y[0] - y[-1]).max())
    return {"seam_flux": round(seam, 4), "flux_p50": round(float(np.median(flux)), 4), "flux_p95": round(float(np.percentile(flux, 95)), 4),
            "seam_vs_p95": round(seam / max(float(np.percentile(flux, 95)), 1e-9), 3), "sample_jump": round(jump, 5)}


def find_music_loop(x, sr, min_len, max_len, xfade=0.75, skip_start=1.0, avoid_end=6.0):
    """Beat-aligned loop search: start/end on beats, keep whole bars (4 beats), maximise the similarity
    (chroma + MFCC, 3 s windows) between what follows the start and what follows the end."""
    import librosa
    mono = x.mean(axis=1).astype(np.float32)
    tempo, beats = librosa.beat.beat_track(y=mono, sr=sr, units="samples", trim=False)
    tempo = float(np.atleast_1d(tempo)[0])
    hop = 512
    chroma = librosa.feature.chroma_cqt(y=mono, sr=sr, hop_length=hop)
    mfcc = librosa.feature.mfcc(y=mono, sr=sr, hop_length=hop, n_mfcc=13)
    rmsf = librosa.feature.rms(y=mono, hop_length=hop)[0]
    feat = np.vstack([chroma / (np.linalg.norm(chroma, axis=0) + 1e-9), mfcc[1:] / 40.0])
    w = int(3.0 * sr / hop)
    dur = len(mono) / sr
    best = None
    med_rms = float(np.median(rmsf))
    for i, bs in enumerate(beats):
        if bs / sr < max(skip_start, xfade + 0.05):
            continue
        for j in range(i + 4, len(beats), 4):
            be = beats[j]
            L = (be - bs) / sr
            if L < min_len:
                continue
            if L > max_len or be / sr > dur - avoid_end:
                break
            fs, fe = bs // hop, be // hop
            if fe + w >= feat.shape[1]:
                break
            a, b = feat[:, fs:fs + w], feat[:, fe:fe + w]
            sim = float(np.sum(a * b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9))
            # energy continuity around the cut
            ea, eb = rmsf[max(0, fs - 8):fs + 8].mean(), rmsf[max(0, fe - 8):fe + 8].mean()
            econt = 1 - abs(ea - eb) / max(ea, eb, 1e-9)
            score = sim + 0.3 * econt + (0.15 if eb > 0.6 * med_rms else -0.5)
            if best is None or score > best[0]:
                best = (score, int(bs), int(be), sim, econt)
    if best is None:
        return None
    return {"tempo": round(tempo, 1), "start": best[1], "end": best[2], "score": round(best[0], 3), "sim": round(best[3], 3),
            "energy_cont": round(best[4], 3), "length_s": round((best[2] - best[1]) / sr, 2)}


def find_ambience_loop(x, sr, xfade=2.0, skip=1.0, tail=1.5):
    s = int(max(skip, xfade + 0.1) * sr)
    e = len(x) - int(tail * sr)
    return s, e


# ---------------------------------------------------------------- pictures
def spectrogram_png(path, x, sr, title):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    mono = x.mean(axis=1)
    fig, ax = plt.subplots(2, 1, figsize=(12, 5), gridspec_kw={"height_ratios": [1, 2]})
    t = np.arange(len(mono)) / sr
    step = max(1, len(mono) // 20000)
    ax[0].plot(t[::step], mono[::step], lw=0.4, color="#c9a227"); ax[0].set_xlim(0, t[-1]); ax[0].set_ylim(-1, 1)
    ax[0].set_title(title, fontsize=9)
    f, tt, Z = signal.stft(mono, sr, nperseg=2048, noverlap=1536)
    S = 20 * np.log10(np.abs(Z) + 1e-9)
    ax[1].pcolormesh(tt, f, S, shading="auto", vmin=S.max() - 90, vmax=S.max(), cmap="magma")
    ax[1].set_yscale("symlog", linthresh=200); ax[1].set_ylim(30, sr / 2); ax[1].set_xlim(0, t[-1])
    fig.tight_layout(); fig.savefig(path, dpi=70); plt.close(fig)
