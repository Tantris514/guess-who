"""Procedural placeholder textures for L_Manor (used until AssetGen textures are approved).

Run with the ComfyUI venv (numpy + PIL):
  V:\\ComfyUI\\ComfyUI\\ComfyUI\\.venv\\Scripts\\python.exe -I Tools/level/gen_placeholder_textures.py
Writes PNGs to Tools/level/tex/. All tileable textures are periodic (FFT-filtered noise).
"""
import os
import numpy as np
from PIL import Image

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tex")
os.makedirs(OUT, exist_ok=True)
rng = np.random.default_rng(1932)


def pnoise(n, sx, sy=None):
    """Periodic gaussian-filtered noise in [0,1]; sx/sy = blur sigma in pixels."""
    sy = sx if sy is None else sy
    w = rng.standard_normal((n, n))
    fy = np.fft.fftfreq(n)[:, None]
    fx = np.fft.rfftfreq(n)[None, :]
    filt = np.exp(-2 * (np.pi ** 2) * ((fx * sx) ** 2 + (fy * sy) ** 2))
    r = np.fft.irfft2(np.fft.rfft2(w) * filt, s=(n, n))
    r -= r.min()
    return r / max(r.max(), 1e-9)


def save(name, arr, mode="RGB"):
    a = np.clip(arr * 255.0 + 0.5, 0, 255).astype(np.uint8)
    Image.fromarray(a, mode if a.ndim == 3 else "L").save(os.path.join(OUT, name + ".png"))
    print("wrote", name, a.shape)


def lerp(a, b, t):
    return a + (b - a) * t[..., None]


def col(*rgb):
    return np.array(rgb, dtype=np.float64) / 255.0


N = 512
yy, xx = np.mgrid[0:N, 0:N] / N

# --- defaults
save("T_GW_Default_Normal", np.ones((8, 8, 3)) * np.array([0.5, 0.5, 1.0]))
save("T_GW_Default_Rough", np.full((8, 8), 0.5))

# --- wood (vertical grain), light-mid brown so tints can push walnut / mahogany / oak
warp = pnoise(N, 30, 120)
fine = pnoise(N, 1.2, 30)
rings = 0.5 + 0.5 * np.sin(2 * np.pi * (xx * 14 + warp * 1.2))
g = np.clip(0.55 * rings + 0.35 * fine + 0.25 * pnoise(N, 60), 0, 1)
wood = lerp(col(120, 74, 40), col(196, 140, 88), g)
save("T_GW_PH_Wood", wood)
save("T_GW_PH_Wood_R", 0.45 + 0.25 * (1 - g))

# --- marble light (white + grey veins) and dark (black + white veins)
turb = pnoise(N, 60) * 1.6 + pnoise(N, 10) * 0.35
v = np.abs(np.sin(2 * np.pi * (xx * 2 + yy * 1 + turb)))
veins = 1 - np.power(v, 0.12)
v2 = np.abs(np.sin(2 * np.pi * (xx * -1 + yy * 3 + turb * 0.7 + 0.3)))
veins2 = 1 - np.power(v2, 0.08)
cloud = pnoise(N, 50)
m_light = np.clip(0.93 - 0.06 * cloud - 0.35 * veins - 0.2 * veins2, 0, 1)
save("T_GW_PH_MarbleLight", lerp(col(150, 150, 155), col(245, 243, 238), m_light))
m_dark = np.clip(0.06 + 0.05 * cloud + 0.75 * veins + 0.35 * veins2, 0, 1)
save("T_GW_PH_MarbleDark", lerp(col(14, 14, 16), col(225, 225, 225), m_dark))

# --- plaster
p = 0.9 + 0.06 * (pnoise(N, 25) - 0.5) + 0.03 * (pnoise(N, 2) - 0.5)
save("T_GW_PH_Plaster", lerp(col(0, 0, 0), col(255, 255, 255), p))

# --- velvet / fabric (greyscale, tint it)
f = 0.7 + 0.15 * (pnoise(N, 12) - 0.5) + 0.1 * (pnoise(N, 1.0) - 0.5)
save("T_GW_PH_Fabric", np.repeat(f[..., None], 3, axis=2))


def motif_cell(u, v):
    """Symmetric damask-like motif in a unit cell, u,v in [-0.5,0.5]."""
    au = np.abs(u)
    r = np.sqrt(au ** 2 + v ** 2) + 1e-6
    th = np.arctan2(v, au)
    petal = r < (0.22 + 0.10 * np.cos(5 * th) + 0.05 * np.cos(9 * th))
    stem = (au < 0.012) & (np.abs(v) < 0.42)
    leaf = (np.abs(np.sqrt((au - 0.17) ** 2 + (v + 0.25) ** 2) - 0.12) < 0.018)
    leaf2 = (np.abs(np.sqrt((au - 0.17) ** 2 + (v - 0.25) ** 2) - 0.12) < 0.018)
    ring = np.abs(r - 0.33) < 0.012
    return (petal | stem | leaf | leaf2 | ring).astype(np.float64)


def half_drop(fn, reps=4):
    u = xx * reps
    v = yy * reps
    m1 = fn(np.mod(u, 1) - 0.5, np.mod(v, 1) - 0.5)
    m2 = fn(np.mod(u + 0.5, 1) - 0.5, np.mod(v + 0.5, 1) - 0.5) * 0.0
    return np.clip(m1 + m2, 0, 1)


def soften(m, s=1.0):
    k = pnoise  # noqa - reuse fft blur
    n = m.shape[0]
    fy = np.fft.fftfreq(n)[:, None]
    fx = np.fft.rfftfreq(n)[None, :]
    filt = np.exp(-2 * (np.pi ** 2) * ((fx * s) ** 2 + (fy * s) ** 2))
    return np.clip(np.fft.irfft2(np.fft.rfft2(m) * filt, s=(n, n)), 0, 1)


dm = soften(half_drop(motif_cell, 3), 1.2)
grain = 0.04 * (pnoise(N, 3) - 0.5)
save("T_GW_PH_DamaskRed", lerp(col(92, 14, 18), col(58, 6, 10), dm) + grain[..., None])


def fan_cell(u, v):
    r = np.sqrt(u ** 2 + (v + 0.5) ** 2)
    th = np.arctan2(u, v + 0.5)
    arcs = (np.abs(np.mod(r * 9, 1) - 0.5) < 0.07) & (r < 0.95)
    rays = (np.abs(np.mod(th * 8 / np.pi, 1) - 0.5) < 0.06) & (r < 0.95) & (r > 0.12)
    edge = np.abs(r - 0.97) < 0.02
    return (arcs | rays | edge).astype(np.float64)


fan = soften(half_drop(lambda u, v: fan_cell(u, v), 4), 0.8)
save("T_GW_PH_DecoGreen", lerp(col(10, 52, 38), col(196, 158, 82), fan) + grain[..., None])

lines = (np.abs(np.mod(xx * 8, 1) - 0.5) > 0.47).astype(float)
du = np.abs(np.mod(xx * 8 + 0.5, 1) - 0.5)
dv = np.abs(np.mod(yy * 8, 1) - 0.5)
diam = ((du + dv) < 0.09).astype(float)
ng = soften(np.clip(lines + diam, 0, 1), 0.6)
save("T_GW_PH_NavyGold", lerp(col(14, 20, 44), col(190, 150, 80), ng) + grain[..., None])

blobs = pnoise(N, 10)
flor = (blobs > 0.62).astype(float)
bird = soften(half_drop(motif_cell, 2), 2.0) * 0.6
cream = lerp(col(232, 220, 196), col(120, 150, 118), soften(flor, 1.5) * 0.8)
cream = lerp(cream, col(190, 120, 115), bird)
save("T_GW_PH_FloralCream", cream + grain[..., None])

# --- carpet: burgundy with small gold fleurs
fl = soften(half_drop(lambda u, v: (np.sqrt(u ** 2 + v ** 2) < (0.12 + 0.05 * np.cos(4 * np.arctan2(v, u)))).astype(float), 8), 1.0)
carpet = lerp(col(88, 16, 22), col(176, 132, 64), fl * 0.85) + 0.05 * (pnoise(N, 1.0) - 0.5)[..., None]
save("T_GW_PH_Carpet", carpet)

# --- rug (persian-like), 1024 x 683
H, W = 683, 1024
ry, rx = np.mgrid[0:H, 0:W]
u = (rx + 0.5) / W
v = (ry + 0.5) / H
bd = np.minimum(np.minimum(u, 1 - u) * W / H, np.minimum(v, 1 - v))
rug = np.zeros((H, W, 3)) + col(130, 22, 26)
rug[bd < 0.13] = col(24, 30, 64)
rug[(bd > 0.105) & (bd < 0.12)] = col(205, 180, 130)
rug[bd < 0.025] = col(205, 180, 130)
cu, cv = (u - 0.5) * W / H, v - 0.5
rr = np.sqrt(cu ** 2 + cv ** 2)
th = np.arctan2(cv, cu)
med = rr < (0.18 + 0.05 * np.cos(8 * th))
rug[med] = col(214, 196, 158)
rug[rr < 0.08] = col(24, 30, 64)
pat = (np.sin(rx / 9.0) * np.sin(ry / 9.0) > 0.6) & (bd > 0.14) & ~med
rug[pat] = rug[pat] * 0.55 + col(205, 160, 90) * 0.45
img = rug + 0.06 * (rng.random((H, W))[..., None] - 0.5)
save("T_GW_PH_Rug", img)

# --- night garden window view (portrait 512 x 853)
H, W = 853, 512
wy, wx = np.mgrid[0:H, 0:W]
t = wy / H
sky = lerp(col(10, 18, 40), col(22, 34, 52), t)
hedge = (t > 0.55 + 0.03 * np.sin(wx / 30.0)).astype(float)
sky = lerp(sky, col(8, 20, 14), hedge * 0.92)
lanterns = np.zeros((H, W))
for cx, cy in ((120, 520), (400, 505), (260, 470)):
    lanterns += np.exp(-((wx - cx) ** 2 + (wy - cy) ** 2) / (2 * 9.0 ** 2))
sky = sky + lanterns[..., None] * col(255, 190, 110) * 1.5
rain = (rng.random((H, W)) > 0.996).astype(float)
streak = np.zeros_like(rain)
for k in range(12):
    streak += np.roll(rain, k, axis=0) * (1 - k / 12)
sky = sky + np.clip(streak, 0, 1)[..., None] * 0.12
save("T_GW_PH_WindowNight", sky)

# --- painting placeholders (dark old-master look), 4 variants 512 x 640
for i in range(4):
    H, W = 640, 512
    py, px = np.mgrid[0:H, 0:W]
    base = lerp(col(40, 28, 18), col(70, 52, 30), np.tile(pnoise(512, 60), (2, 1))[:H, :W])
    cx, cy = W * (0.5 + 0.1 * (i - 1.5) * 0.5), H * (0.38 + 0.03 * i)
    face = np.exp(-(((px - cx) / 70.0) ** 2 + ((py - cy) / 90.0) ** 2))
    body = np.exp(-(((px - cx) / 170.0) ** 2 + ((py - H * 0.95) / 220.0) ** 2))
    tones = [col(205, 170, 130), col(180, 150, 110), col(150, 170, 160), col(200, 160, 140)]
    cloth = [col(20, 30, 60), col(70, 15, 20), col(25, 45, 30), col(15, 15, 15)]
    img = lerp(base, tones[i], face * 0.85)
    img = lerp(img, cloth[i], body * 0.8)
    img = img * (0.75 + 0.25 * np.exp(-(((px - W / 2) / W) ** 2 + ((py - H / 2) / H) ** 2) * 3))[..., None]
    save(f"T_GW_PH_Painting{i}", img)
