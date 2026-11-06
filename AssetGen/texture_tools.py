"""Texture post-processing for the GuessWho materials (run with ComfyUI's Python: numpy, PIL, scipy).

  python -I texture_tools.py seamless IN.png OUT.png [--size 1024] [--overlap 160] [--flatten 0.7] [--periodic]
      Makes a texture tile without visible seams, without ghosting:
        1. optional low-frequency flattening (removes lighting gradients / vignetting),
        2. --periodic (wallpapers, patterned carpet): detects the pattern repeat (autocorrelation) and crops a
           whole number of repeats, so the tile edges fall on matching pattern,
        3. wrap seams are closed with a minimum-error boundary cut (image-quilting style) inside an overlap band,
           with a narrow feather: the image is never cross-faded with a shifted copy of itself.
  python -I texture_tools.py preview IN.png OUT.png       2x2 tiled preview (to check seams)
  python -I texture_tools.py normal IN.png OUT.png [--strength 2.0]
      Tangent-space normal map from luminance (DirectX/UE green convention).
  python -I texture_tools.py roughness IN.png OUT.png [--base 0.55] [--range 0.3]
      Roughness map: brighter = slightly smoother, darker grain = rougher.
"""
import argparse
import json

import numpy as np
from PIL import Image
from scipy import ndimage


def load(path, size=None):
    img = Image.open(path).convert("RGB")
    if size:
        img = img.resize((size, size), Image.LANCZOS)
    return np.asarray(img).astype(np.float32) / 255.0


def save(arr, path):
    Image.fromarray(np.clip(arr * 255.0 + 0.5, 0, 255).astype(np.uint8)).save(path)


def luminance(img):
    return img[..., 0] * 0.2126 + img[..., 1] * 0.7152 + img[..., 2] * 0.0722


def flatten(img, strength, per_channel=False, sigma_div=6.0):
    """Divide out the very-low-frequency field (lighting gradient), keep detail.
    per_channel also evens out colour/saturation drift (good for flat-coloured wallpapers)."""
    if strength <= 0:
        return img
    sigma = max(img.shape[:2]) / sigma_div
    if per_channel:
        out = np.empty_like(img)
        for c in range(img.shape[2]):
            ch = img[..., c]
            low = ndimage.gaussian_filter(ch, sigma, mode="reflect")
            out[..., c] = ch * (ch.mean() / np.maximum(low, 1e-3)) ** strength
        return np.clip(out, 0.0, 1.0)
    lum = luminance(img)
    low = ndimage.gaussian_filter(lum, sigma, mode="reflect")
    gain = (lum.mean() / np.maximum(low, 1e-3)) ** strength
    return np.clip(img * gain[..., None], 0.0, 1.0)


def find_period(signal_2d, axis, min_p, max_p):
    """Strongest repeat length along one axis, from the mean autocorrelation of the rows/columns."""
    x = signal_2d - signal_2d.mean()
    if axis == 0:
        x = x.T
    n = x.shape[1]
    f = np.fft.rfft(x, n=2 * n, axis=1)
    ac = np.fft.irfft(f * np.conj(f), axis=1)[:, :n].mean(axis=0)
    ac = ac / max(ac[0], 1e-9)
    max_p = min(max_p, n // 2)              # at least two repeats inside the image
    best, score = None, -1.0
    for p in range(min_p, min(max_p, n - 1)):
        if ac[p] >= ac[p - 1] and ac[p] >= ac[p + 1] and ac[p] > score:
            best, score = p, float(ac[p])
    # prefer the smallest repeat that is almost as strong (avoid picking 2x the true period)
    if best:
        for p in range(min_p, best):
            if ac[p] >= ac[p - 1] and ac[p] >= ac[p + 1] and ac[p] > 0.85 * score:
                best, score = p, float(ac[p])
                break
    return best, score


def lag_peaks(lum, axis, lo, hi, top=6):
    """Local maxima (shift, score) in [lo, hi] of the unbiased autocorrelation along `axis`."""
    x = lum - lum.mean()
    if axis == 0:
        x = x.T
    n = x.shape[1]
    f = np.fft.rfft(x, n=2 * n, axis=1)
    ac = np.fft.irfft(f * np.conj(f), axis=1)[:, :n].sum(axis=0) / (x.shape[0] * np.arange(n, 0, -1))
    ac = ac / max(ac[0], 1e-9)
    peaks = [(p, float(ac[p])) for p in range(max(lo, 1), min(hi, n - 2) + 1) if ac[p] >= ac[p - 1] and ac[p] >= ac[p + 1]]
    peaks.sort(key=lambda t: -t[1])
    return peaks[:top] or [(hi, float(ac[hi]))]


def cut_path(cost):
    """Minimum-cost top-to-bottom path through cost[h, w] (one column per row, |step| <= 1)."""
    h, w = cost.shape
    acc = cost.copy()
    back = np.zeros((h, w), dtype=np.int64)
    for y in range(1, h):
        prev = acc[y - 1]
        left = np.concatenate([[np.inf], prev[:-1]])
        right = np.concatenate([prev[1:], [np.inf]])
        stack = np.stack([left, prev, right])
        idx = np.argmin(stack, axis=0)
        back[y] = idx - 1
        acc[y] += stack[idx, np.arange(w)]
    path = np.zeros(h, dtype=np.int64)
    path[-1] = int(np.argmin(acc[-1]))
    for y in range(h - 1, 0, -1):
        path[y - 1] = np.clip(path[y] + back[y, path[y]], 0, w - 1)
    return path


def wrap_cut(crop, period, overlap, feather=3, sigma=12.0):
    """Make crop[:, :period] tile horizontally. crop has period+overlap columns.

    Two bands: the detail band (crop minus a blur) is joined with a minimum-error cut (no ghosting); the
    low-frequency band (tone, lighting) is cross-faded over the whole overlap, so there is no brightness step.
    """
    low = np.stack([ndimage.gaussian_filter(crop[..., c], sigma, mode="nearest") for c in range(crop.shape[2])], -1)
    high = crop - low
    a_h, b_h = high[:, :overlap], high[:, period:period + overlap]   # after column period-1 comes crop[:, period:]
    a_l, b_l = low[:, :overlap], low[:, period:period + overlap]     # so left of the cut use b, right of it use a
    cost = ((a_h - b_h) ** 2).sum(axis=-1)
    cost = ndimage.uniform_filter(cost, size=3)
    path = cut_path(cost)
    xs = np.arange(overlap)[None, :]
    wa = np.clip((xs - path[:, None] + feather) / (2.0 * feather), 0.0, 1.0)[..., None]
    t = (np.arange(overlap) + 0.5) / overlap
    wl = (t * t * (3 - 2 * t))[None, :, None]                          # smoothstep fade for the tone band
    out = crop[:, :period].copy()
    out[:, :overlap] = (b_h * (1.0 - wa) + a_h * wa) + (b_l * (1.0 - wl) + a_l * wl)
    return np.clip(out, 0.0, 1.0), float(cost[np.arange(len(path)), path].mean())


def seamless(img, size, overlap, flat, periodic, feather=3, sigma=12.0, per_channel=False, flat_div=6.0):
    img = flatten(img, flat, per_channel, flat_div)
    h, w = img.shape[:2]
    info = {"flatten": flat}
    if periodic:
        # Generated patterns drift a little, so whole multiples of the base repeat do not line up. Instead pick,
        # in each axis, the large shift at which the image best matches itself (unbiased autocorrelation):
        # a tile of exactly that size has matching pattern at its edges.
        lum = luminance(img)
        px = lag_peaks(lum, 1, int(0.55 * (w - overlap)), w - overlap)
        py = lag_peaks(lum, 0, int(0.55 * (h - overlap)), h - overlap)
        (tw, sx), (th, sy) = max(((a, b) for a in px for b in py),
                                 key=lambda ab: ab[0][1] + ab[1][1] - 1.0 * abs(np.log(ab[0][0] / ab[1][0])))
        info.update(lag_score_x=round(sx, 3), lag_score_y=round(sy, 3))
    else:
        tw, th = w - overlap, h - overlap
    x0, y0 = (w - tw - overlap) // 2, (h - th - overlap) // 2
    crop = img[y0:y0 + th + overlap, x0:x0 + tw + overlap]
    t1, ex = wrap_cut(crop, tw, overlap, feather, sigma)                                  # horizontal wrap
    t2, ey = wrap_cut(t1.transpose(1, 0, 2), th, overlap, feather, sigma)                 # vertical wrap
    tile = t2.transpose(1, 0, 2)
    info.update(tile_px=[tw, th], tile_aspect_w_over_h=round(tw / th, 3), seam_err_x=round(ex, 5), seam_err_y=round(ey, 5))
    out = Image.fromarray(np.clip(tile * 255 + 0.5, 0, 255).astype(np.uint8))
    out = out.resize((size, size), Image.LANCZOS)
    return np.asarray(out).astype(np.float32) / 255.0, info


def preview(img):
    return np.concatenate([np.concatenate([img, img], axis=1)] * 2, axis=0)


def normal_map(img, strength):
    lum = ndimage.gaussian_filter(luminance(img), 0.7, mode="wrap")
    dx = (np.roll(lum, -1, axis=1) - np.roll(lum, 1, axis=1)) * strength
    dy = (np.roll(lum, -1, axis=0) - np.roll(lum, 1, axis=0)) * strength
    n = np.stack([-dx, dy, np.ones_like(lum)], axis=-1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    return n * 0.5 + 0.5


def roughness_map(img, base, spread):
    lum = luminance(img)
    lum = (lum - lum.mean()) / max(lum.std(), 1e-4)
    r = np.clip(base - lum * spread * 0.33, 0.05, 1.0)
    return np.repeat(r[..., None], 3, axis=-1)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("mode", choices=["seamless", "normal", "roughness", "preview"])
    p.add_argument("src")
    p.add_argument("dst")
    p.add_argument("--size", type=int, default=1024)
    p.add_argument("--overlap", type=int, default=160)
    p.add_argument("--flatten", type=float, default=0.7)
    p.add_argument("--periodic", action="store_true")
    p.add_argument("--strength", type=float, default=2.0)
    p.add_argument("--base", type=float, default=0.55)
    p.add_argument("--range", type=float, default=0.3)
    a = p.parse_args()
    img = load(a.src)
    if a.mode == "seamless":
        out, info = seamless(img, a.size, a.overlap, a.flatten, a.periodic)
        save(out, a.dst)
        print("wrote", a.dst, json.dumps(info))
    elif a.mode == "preview":
        save(preview(img), a.dst)
        print("wrote", a.dst)
    elif a.mode == "normal":
        save(normal_map(img, a.strength), a.dst)
        print("wrote", a.dst)
    else:
        save(roughness_map(img, a.base, a.range), a.dst)
        print("wrote", a.dst)


if __name__ == "__main__":
    main()
