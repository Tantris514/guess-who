"""Storm ambience (WAV, 48 kHz, 16-bit PCM, mono, peak -3 dBFS) -> island_src/audio/

  V:\\ComfyUI\\ComfyUI\\ComfyUI\\.venv\\Scripts\\python.exe -I gen_audio.py [name ...]

Loops (rain / wind / sea) are synthesised circularly: noise beds are filtered in the frequency domain over
exactly one loop length (so they are periodic), slow envelopes are periodic band-limited noise, the moving
howl uses a phase track that closes on a whole number of cycles, and discrete events (drips, wave crashes)
are added modulo the loop length. The last sample therefore flows into the first exactly as any two
neighbouring samples do (no crossfade needed, no level dip at the loop point).
"""
import os
import sys
import wave

import numpy as np
from scipy.signal import butter, sosfilt, sosfiltfilt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import AUDIO_DIR, smoothstep  # noqa: E402

SR = 48000
PEAK_DB = -3.0


# ------------------------------------------------------------------ helpers

def write_wav(name, x, loop=False):
    x = np.asarray(x, dtype=np.float64)
    x = x - x.mean()
    y = x / np.abs(x).max() * 10 ** (PEAK_DB / 20)
    i16 = np.round(y * 32767).astype("<i2")
    path = os.path.join(AUDIO_DIR, name + ".wav")
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(i16.tobytes())
    yf = i16.astype(np.float64) / 32768
    info = {
        "duration_s": round(len(i16) / SR, 3), "sample_rate": SR, "channels": 1, "bits": 16,
        "peak_dbfs": round(20 * np.log10(np.abs(yf).max()), 2),
        "rms_dbfs": round(20 * np.log10(np.sqrt((yf ** 2).mean())), 2),
        "clipped_samples": int((np.abs(i16.astype(int)) >= 32767).sum()),
    }
    if loop:
        d = np.abs(np.diff(yf))
        info["loop_seam_step_percentile"] = round(float((d < abs(yf[0] - yf[-1])).mean() * 100), 1)
        s = SR
        info["loop_rms_first_vs_last_second_db"] = round(
            20 * np.log10(np.sqrt((yf[:s] ** 2).mean()) / np.sqrt((yf[-s:] ** 2).mean())), 2)
    print(name, info)
    return info


def spec_noise(n, rng, shape):
    """Periodic coloured noise of length n (unit std). shape(f) = amplitude response."""
    k = n // 2 + 1
    X = rng.normal(size=k) + 1j * rng.normal(size=k)
    f = np.fft.rfftfreq(n, 1 / SR)
    A = shape(np.maximum(f, 1e-3))
    A[0] = 0.0
    x = np.fft.irfft(X * A, n)
    return x / x.std()


def spec_filter(x, shape):
    """Circular (periodic) filtering of x with amplitude response shape(f)."""
    f = np.fft.rfftfreq(len(x), 1 / SR)
    A = shape(np.maximum(f, 1e-3))
    A[0] = 0.0
    return np.fft.irfft(np.fft.rfft(x) * A, len(x))


def band(lo=None, hi=None, order=2):
    def s(f):
        a = np.ones_like(f)
        if lo:
            a = a / np.sqrt(1 + (lo / f) ** (2 * order))
        if hi:
            a = a / np.sqrt(1 + (f / hi) ** (2 * order))
        return a
    return s


def pink(lo, hi, order=2, slope=0.5):
    b = band(lo, hi, order)
    return lambda f: b(f) / f ** slope


def slow_env(n, rng, fc, order=3):
    """Periodic smooth random envelope in [0, 1] with content below ~fc Hz."""
    e = spec_noise(n, rng, band(None, fc, order))
    return (e - e.min()) / (e.max() - e.min())


def add_wrapped(out, ev, start):
    idx = (int(start) + np.arange(len(ev))) % len(out)
    out[idx] += ev


def sos_band(lo, hi, order=4):
    if lo and hi:
        return butter(order, [lo, hi], btype="bandpass", fs=SR, output="sos")
    if lo:
        return butter(order, lo, btype="highpass", fs=SR, output="sos")
    return butter(order, hi, btype="lowpass", fs=SR, output="sos")


def filt(x, lo=None, hi=None, order=4):
    return sosfilt(sos_band(lo, hi, order), x)


# ------------------------------------------------------------------ thunder

def burst_env(t, t0, att, dec):
    """Smooth attack (att s) then exponential decay (dec s), zero before t0."""
    tt = t - t0
    e = np.where(tt > 0, (1 - np.exp(-np.maximum(tt, 0) / att)) * np.exp(-np.maximum(tt, 0) / dec), 0.0)
    return e


def thunder(name, seed, dur, crack, crack_level, onset, rumble_band, tau, n_bursts, burst_spread, swell=0.0):
    rng = np.random.default_rng(seed)
    n = int(dur * SR)
    t = np.arange(n) / SR
    out = np.zeros(n)
    t_crack = 0.06
    if crack:
        # main crack: a few ms of broadband noise, plus 1-2 secondary snaps and a tearing crackle
        c = np.zeros(n)
        for k, (dt, lvl, tau_c) in enumerate([(0.0, 1.0, 0.004), (rng.uniform(0.02, 0.05), 0.55, 0.006),
                                              (rng.uniform(0.07, 0.14), 0.35, 0.008)]):
            L = int(0.06 * SR)
            i0 = int((t_crack + dt) * SR)
            b = rng.normal(size=L) * np.exp(-np.arange(L) / (tau_c * SR))
            c[i0:i0 + L] += lvl * b
        c = filt(c, 150, None, 2)
        # crackle: dense then sparse impulses over ~0.6 s
        m = int(0.7 * SR)
        dens = np.exp(-np.arange(m) / (0.18 * SR))
        imp = (rng.random(m) < dens * 0.02) * rng.exponential(0.35, m) * np.sign(rng.normal(size=m))
        crk = filt(imp, 700, 7000, 2)
        i0 = int((t_crack + 0.01) * SR)
        c[i0:i0 + m] += crk * 0.8
        # low thump under the crack
        th = filt(rng.normal(size=n), None, 110, 4) * burst_env(t, t_crack, 0.004, 0.18)
        c += th / np.abs(th).max() * 0.5
        out += c / np.abs(c).max() * crack_level
    # rumble: brown noise, band-limited low, with irregular rolling bursts that decay
    br = np.cumsum(rng.normal(size=n))
    br = sosfiltfilt(sos_band(rumble_band[0], rumble_band[1], 3), br)
    br /= br.std()
    mid = sosfiltfilt(sos_band(rumble_band[1] * 0.9, rumble_band[1] * 3.5, 2), rng.normal(size=n))
    mid /= mid.std()
    env = np.zeros(n)
    envm = np.zeros(n)
    times = np.sort(onset + rng.exponential(burst_spread, n_bursts))
    times = times[times < dur - 1.5]
    for tk in times:
        a = rng.uniform(0.2, 1.0) ** 1.5 * np.exp(-(tk - onset) / tau)
        att, dec = rng.uniform(0.05, 0.3), rng.uniform(0.25, 0.9)
        env += a * burst_env(t, tk, att, dec)
        envm += a * burst_env(t, tk, att * 0.5, dec * 0.45)
    env += 0.12 * burst_env(t, onset, 0.25 + swell, tau * 1.2)                # faint continuous roll underneath
    if swell:
        env *= smoothstep(onset, onset + swell, t)
    rum = br * env + 0.28 * mid * envm
    rum /= np.abs(rum).max()
    out += rum * 0.7
    # end: fade the last 0.8 s, remove DC / subsonic
    out *= 1 - smoothstep(dur - 0.8, dur, t)
    out = sosfiltfilt(sos_band(18, None, 2), out)
    out[: int(0.002 * SR)] *= np.linspace(0, 1, int(0.002 * SR))
    return write_wav(name, out)


def build_thunders():
    r = {}
    # close strike: hard crack + crackle, quick heavy roll
    r["thunder_1"] = thunder("thunder_1", 901, 9.0, True, 1.0, 0.12, (24, 210), 2.6, 11, 1.4)
    # mid distance: softer crack, longer rolling with many bursts that come and go
    r["thunder_2"] = thunder("thunder_2", 902, 10.5, True, 0.55, 0.4, (22, 160), 3.6, 18, 2.6)
    # distant: no crack, slow swell, deep and muffled
    r["thunder_3"] = thunder("thunder_3", 903, 8.0, False, 0.0, 0.3, (18, 95), 2.8, 9, 2.0, swell=1.4)
    return r


# ------------------------------------------------------------------ rain

def build_rain(dur=20.0):
    rng = np.random.default_rng(1001)
    n = int(dur * SR)
    hiss = spec_noise(n, rng, pink(900, 9500, 2, 0.15))
    body = spec_noise(n, rng, pink(220, 2000, 2, 0.3))
    low = spec_noise(n, rng, band(50, 350, 2))
    env = 1 + 0.12 * (slow_env(n, rng, 0.25) - 0.5)
    # patter: dense far droplets + sparser close ticks. Impulse trains are smeared into 1.5-4 ms decaying
    # noise grains (circular convolution) so single impacts do not spike the peak
    def grains(rate, lo, hi, amp_lo, tau_ms):
        imp = np.zeros(n)
        k = int(rate * dur)
        np.add.at(imp, rng.integers(0, n, k), rng.uniform(amp_lo, 1.0, k))
        L = int(tau_ms * 6e-3 * SR)
        ker = np.zeros(n)
        ker[:L] = rng.normal(size=L) * np.exp(-np.arange(L) / (tau_ms * 1e-3 * SR))
        y = np.fft.irfft(np.fft.rfft(imp) * np.fft.rfft(ker), n)
        y = spec_filter(y, band(lo, hi, 2))
        return y / y.std()
    far = grains(1100, 1800, 8000, 0.2, 1.5)
    near = grains(80, 700, 5000, 0.4, 4.0)
    x = (hiss * 1.0 + body * 0.5 + low * 0.22) * env
    x += far * 0.45 + near * 0.35
    # gentle soft limiter on the bed (heavy rain is a dense, steady texture)
    lim = 3.2 * x.std()
    x = lim * np.tanh(x / lim)
    # a few drips (gutter / leaves): short gliding plinks, wrapped around the loop
    drip = np.zeros(n)
    for _ in range(10):
        L = int(0.3 * SR)
        tt = np.arange(L) / SR
        f0 = rng.uniform(1300, 3000)
        f = f0 * (1 - 0.22 * (1 - np.exp(-tt / 0.03)))
        ph = 2 * np.pi * np.cumsum(f) / SR
        e = (1 - np.exp(-tt / 0.0015)) * np.exp(-tt / rng.uniform(0.03, 0.06))
        ev = np.sin(ph) * e + 0.3 * rng.normal(size=L) * np.exp(-tt / 0.004)
        add_wrapped(drip, ev * rng.uniform(0.6, 1.0), rng.integers(0, n))
    x += drip * (2.6 * x.std())
    return write_wav("rain_loop", x, loop=True)


# ------------------------------------------------------------------ wind

def narrowband_carrier(n, rng, bw):
    """Periodic complex baseband noise (|f| < bw), unit rms."""
    f = np.fft.fftfreq(n, 1 / SR)
    m = np.abs(f) < bw * 2
    Z = np.zeros(n, dtype=np.complex128)
    Z[m] = (rng.normal(size=m.sum()) + 1j * rng.normal(size=m.sum())) * np.exp(-(f[m] / bw) ** 2)
    z = np.fft.ifft(Z)
    return z / np.sqrt((np.abs(z) ** 2).mean())


def closed_phase(fc):
    """Phase track for instantaneous frequency fc (Hz) that closes on a whole number of cycles."""
    n = len(fc)
    S = fc.sum() / SR
    fc = fc + (round(S) - S) * SR / n
    return 2 * np.pi * np.cumsum(fc) / SR


def build_wind(dur=30.0):
    rng = np.random.default_rng(2002)
    n = int(dur * SR)
    g = slow_env(n, rng, 0.22)
    g = 0.6 * g + 0.4 * slow_env(n, rng, 0.06)
    g = (g - g.min()) / (g.max() - g.min())
    gust = 0.08 + 0.92 * g ** 1.6
    low = spec_noise(n, rng, pink(55, 520, 2, 0.4))
    high = spec_noise(n, rng, band(380, 2600, 2))
    whistle = spec_noise(n, rng, band(1800, 5000, 3))
    x = low * (0.18 + 0.82 * gust) + 0.6 * high * gust ** 1.8 + 0.08 * whistle * gust ** 3
    # faint howl: two narrow resonances whose centre glides with the gusts
    slow2 = slow_env(n, rng, 0.05)
    f1 = 330 + 300 * g + 70 * (slow2 - 0.5)
    f2 = 1.47 * f1 + 40 * (slow_env(n, rng, 0.08) - 0.5)
    h1 = np.real(narrowband_carrier(n, rng, 9.0) * np.exp(1j * closed_phase(f1)))
    h2 = np.real(narrowband_carrier(n, rng, 12.0) * np.exp(1j * closed_phase(f2)))
    howl = (h1 + 0.5 * h2) * (0.08 + 0.92 * g ** 2)
    x = x / x.std()
    x += 0.3 * howl / howl.std()
    return write_wav("wind_loop", x, loop=True)


# ------------------------------------------------------------------ sea

def crash(rng, intensity):
    L = int(7.0 * SR)
    pre = 0.8                                            # swell before the impact
    t = np.arange(L) / SR - pre
    nz = lambda: rng.normal(size=L)
    swell = filt(nz(), 40, 300, 2) * smoothstep(-pre, 0.05, t) * np.exp(-np.maximum(t, 0) / 0.3)
    boom = filt(nz(), None, 260, 4) * burst_env(t, 0.0, 0.06, 0.9)
    bright = filt(nz(), 600, 7500, 2) * burst_env(t, 0.03, 0.12, 0.75)
    dark = filt(nz(), 150, 1600, 2) * burst_env(t, 0.05, 0.3, 2.2)
    back = filt(nz(), 2500, 9000, 2) * smoothstep(0.8, 1.7, t) * np.exp(-np.maximum(t - 1.7, 0) / 1.8)
    m = (rng.random(L) < 0.004 * smoothstep(0.6, 1.5, t) * np.exp(-np.maximum(t - 1.5, 0) / 2.0))
    fizz = filt(m * rng.exponential(1.0, L) * np.sign(rng.normal(size=L)), 3000, 9000, 2)
    ev = 0.25 * swell + 0.9 * boom + 0.8 * bright + 0.9 * dark + 0.18 * back + 0.25 * fizz
    ev *= 1 - smoothstep(6.3, 7.0, t + pre)
    return ev / np.abs(ev).max() * intensity, int(pre * SR)


def build_sea(dur=30.0):
    rng = np.random.default_rng(3003)
    n = int(dur * SR)
    surge = slow_env(n, rng, 0.12)
    rumble = spec_noise(n, rng, lambda f: band(22, 230, 2)(f) / f)
    wash = spec_noise(n, rng, pink(200, 3500, 2, 0.3))
    x = rumble * (0.6 + 0.4 * surge) + 0.18 * wash * (0.5 + 0.5 * surge)
    # wave crashes every 4..8 s, placed on the loop circle so the pattern repeats seamlessly
    k = 5
    while True:
        gaps = rng.uniform(4, 8, k)
        gaps = gaps / gaps.sum() * dur
        if gaps.min() >= 4 and gaps.max() <= 8:
            break
    starts = rng.uniform(0, dur) + np.r_[0, np.cumsum(gaps[:-1])]
    level = np.abs(x).max()
    for st in starts:
        ev, pre = crash(rng, rng.uniform(0.7, 1.0) * level * 2.6)
        add_wrapped(x, ev, int(st * SR) - pre)
    info = write_wav("sea_loop", x, loop=True)
    info["crash_times_s"] = [round(float(s % dur), 2) for s in sorted(starts % dur)]
    info["crash_gaps_s"] = [round(float(g), 2) for g in gaps]
    return info


BUILDERS = {"thunder": build_thunders, "rain_loop": build_rain, "wind_loop": build_wind, "sea_loop": build_sea}


def build(names=None):
    out = {}
    for name, fn in BUILDERS.items():
        if names and name not in names:
            continue
        r = fn()
        if name == "thunder":
            out.update(r)
        else:
            out[name] = r
    return out


if __name__ == "__main__":
    build(sys.argv[1:])
