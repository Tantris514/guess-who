"""Island exterior textures (PNG) -> island_src/tex/

  V:\\ComfyUI\\ComfyUI\\ComfyUI\\.venv\\Scripts\\python.exe -I gen_textures.py [T_GW_Name ...]

All tile seamlessly (periodic noise, wrapped stamping, wrap-mode filters).
Normal maps: tangent space, +Z blue, OpenGL convention (green = +Y = up in the image). UE expects DirectX
(green down): tick "Flip Green Channel" on import.
"""
import os
import sys

import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (TEX_DIR, fbm2, height_to_normal_rgb, perlin2, ridged2, roll_grad, smoothstep,  # noqa: E402
                    uv_grid, worley2)

N = 1024


def save(name, arr, mode):
    path = os.path.join(TEX_DIR, name + ".png")
    Image.fromarray(arr, mode).save(path, optimize=True)
    a = arr.astype(np.float64)
    print(f"{name}: {arr.shape[1]}x{arr.shape[0]} {mode}, mean {a.mean():.1f}, min {a.min():.0f}, max {a.max():.0f}")
    return {"size": [int(arr.shape[1]), int(arr.shape[0])], "mode": mode}


def to8(x):
    return np.clip(np.round(x * 255), 0, 255).astype(np.uint8)


def seam_error(a):
    """Mean jump across the wrap seams relative to the mean neighbour difference (1.0 = seamless)."""
    a = a.astype(np.float64)
    if a.ndim == 3:
        a = a.mean(-1)
    inner = (np.abs(np.diff(a, axis=1)).mean() + np.abs(np.diff(a, axis=0)).mean()) / 2
    seam = (np.abs(a[:, 0] - a[:, -1]).mean() + np.abs(a[0, :] - a[-1, :]).mean()) / 2
    return seam / max(inner, 1e-9)


# ------------------------------------------------------------------ sea

def sea_height(seed=1):
    U, V = uv_grid(N, N)
    rng = np.random.default_rng(seed)
    h = np.zeros((N, N))
    for _ in range(60):
        f = 3 * 2 ** rng.uniform(0, 4.4)                 # 3 .. ~63 cycles per tile
        th = rng.normal(0, 0.55)                         # wind-driven: around +U
        m, n = int(round(f * np.cos(th))), int(round(f * np.sin(th)))
        if m == 0 and n == 0:
            continue
        fr = np.hypot(m, n)
        amp = fr ** -1.25 * rng.uniform(0.6, 1.0)
        ph = 2 * np.pi * (m * U + n * V) + rng.uniform(0, 2 * np.pi)
        h += amp * ((1 - np.abs(np.sin(ph / 2))) ** 1.7 - 0.36)   # sharp crests, round troughs
    group = 0.65 + 0.35 * fbm2(U * 3, V * 3, 2, seed + 7, period=(3, 3))
    h *= group
    h += 0.012 * fbm2(U * 48, V * 24, 3, seed + 8, period=(48, 24))   # capillary chop
    return (h - h.mean()) / h.std()


def tex_sea_normal():
    h = sea_height()
    gx, gy = roll_grad(h)
    s = 0.9 / np.percentile(np.hypot(gx, gy), 95)
    rgb = height_to_normal_rgb(h, s)
    info = save("T_GW_SeaNormal", rgb, "RGB")
    info["seam_ratio"] = round(seam_error(rgb), 2)
    return info


def tex_sea_foam():
    h = sea_height()
    U, V = uv_grid(N, N)
    crest = smoothstep(np.percentile(h, 90), np.percentile(h, 99.3), h)
    # foam left behind the moving crest (waves travel toward +U): smear toward -U
    trail = np.zeros_like(crest)
    wsum = 0.0
    for k in range(0, 48, 2):
        w = np.exp(-k / 14.0)
        trail += w * np.roll(crest, -k, axis=1)
        wsum += w
    trail /= wsum
    patch = smoothstep(-0.05, 0.45, fbm2(U * 4, V * 4, 3, 11, period=(4, 4)))
    whitecap = np.clip(crest * 1.2 + trail * 1.6, 0, 1) * (0.35 + 0.65 * patch)
    # wind streaks: long thin bands along U
    streak = fbm2(U * 3, V * 40, 4, 12, period=(3, 40))
    streak = smoothstep(0.05, 0.5, streak) * smoothstep(-0.2, 0.4, fbm2(U * 2, V * 6, 2, 13, period=(2, 6)))
    fil = fbm2(U * 2, V * 110, 3, 16, period=(2, 110))
    fil = smoothstep(0.3, 0.6, fil) * smoothstep(-0.1, 0.5, fbm2(U * 3, V * 4, 2, 17, period=(3, 4)))
    foam = np.maximum.reduce([whitecap, 0.6 * streak, 0.75 * fil])
    # bubbly breakup
    f1, _ = worley2(N, N, 64, 64, 14)
    holes = smoothstep(0.15, 0.5, f1)
    detail = 0.6 + 0.4 * fbm2(U * 32, V * 32, 3, 15, period=(32, 32))
    foam = foam * detail * (1 - 0.45 * holes)
    foam = np.clip(foam / np.percentile(foam, 99.7), 0, 1) ** 1.1
    out = to8(foam)
    info = save("T_GW_SeaFoam", out, "L")
    info["seam_ratio"] = round(seam_error(out), 2)
    return info


# ------------------------------------------------------------------ clouds

def tex_clouds():
    U, V = uv_grid(N, N)
    q1 = fbm2(U * 3, V * 3, 2, 21, period=(3, 3))
    q2 = fbm2(U * 3 + 5.2, V * 3 + 1.3, 2, 22, period=(3, 3))
    # warp only the large shapes; fine detail unwarped (warping every octave smears it into streaks)
    c = fbm2(U * 3 + 0.6 * q1, V * 3 + 0.6 * q2, 3, 23, period=(3, 3))
    c = c + 0.22 * fbm2(U * 24, V * 24, 4, 24, period=(24, 24))
    c = (c - c.mean()) / c.std()
    cover = smoothstep(-0.95, 0.35, c)                                    # ~65 % dense storm cloud
    # puffy lobes inside the masses: billow noise (|perlin|: rounded bumps, sharp creases between them)
    bill, amp, norm = 0.0, 1.0, 0.0
    for o in range(5):
        fr = 6 * 2 ** o
        bill = bill + amp * np.abs(perlin2(U * fr, V * fr, 31 + o, (fr, fr)))
        norm += amp
        amp *= 0.55
    bill = (bill - bill.min()) / (bill.max() - bill.min())
    puff = 0.5 + 0.5 * smoothstep(0.1, 0.75, bill)
    core = smoothstep(0.3, 1.6, c)                                         # thickest cores stay bright
    dens = cover * np.maximum(puff, core)
    # thin wisps in the gaps
    wisp = fbm2(U * 8 + 0.4 * q1, V * 8 + 0.4 * q2, 4, 36, period=(8, 8))
    dens = dens + 0.18 * smoothstep(0.0, 0.6, wisp) * (1 - cover)
    out = to8(0.04 + 0.96 * np.clip(dens, 0, 1))
    info = save("T_GW_Clouds", out, "L")
    info["seam_ratio"] = round(seam_error(out), 2)
    return info


# ------------------------------------------------------------------ rain

def tex_rain_streaks():
    W, H = 512, 1024
    rng = np.random.default_rng(41)

    def layer(n, lmu, lsig, bmin, bpow):
        x = rng.uniform(0, W, n)
        y0 = rng.uniform(0, H, n)
        L = np.clip(rng.lognormal(np.log(lmu), lsig, n), 12, 480)
        b = rng.uniform(bmin, 1.0, n) ** bpow
        cnt = np.ceil(L / 0.5).astype(int)
        idx = np.repeat(np.arange(n), cnt)
        start = np.repeat(np.cumsum(cnt) - cnt, cnt)
        t = (np.arange(cnt.sum()) - start) / cnt[idx]
        val = b[idx] * np.sin(np.pi * t) ** 0.6 * (0.35 + 0.65 * t)       # brighter toward the falling head
        yy = (np.floor(y0[idx] + t * L[idx]).astype(int)) % H
        xf = x[idx]
        c0 = np.floor(xf).astype(int)
        fx = xf - c0
        acc = np.zeros((H, W))
        np.add.at(acc, (yy, c0 % W), val * (1 - fx))
        np.add.at(acc, (yy, (c0 + 1) % W), val * fx)
        return acc

    far = gaussian_filter(layer(1700, 70, 0.6, 0.1, 2.0), (1.5, 0.3), mode="wrap")
    near = gaussian_filter(layer(260, 180, 0.5, 0.35, 1.2), (2.5, 0.6), mode="wrap")
    acc = 0.45 * far / np.percentile(far[far > 1e-4], 99.5) + 1.0 * near / np.percentile(near[near > 1e-4], 99.5)
    out = to8(1 - np.exp(-1.6 * acc))
    info = save("T_GW_RainStreaks", out, "L")
    info["seam_ratio"] = round(seam_error(out), 2)
    return info


def tex_rain_glass():
    rng = np.random.default_rng(51)
    Hh = np.zeros((N, N))

    def patch(cx, cy, r):
        icx, icy = int(np.floor(cx)), int(np.floor(cy))
        o = np.arange(-r, r + 1)
        dx = (icx + o + 0.5)[None, :] - cx
        dy = (icy + o + 0.5)[:, None] - cy
        return np.ix_((icy + o) % N, (icx + o) % N), dx, dy

    def drop(cx, cy, R, sag=1.0, hs=0.35, op=np.maximum):
        r = int(np.ceil(R * 1.4)) + 2
        ix, dx, dy = patch(cx, cy, r)
        ry = np.where(dy > 0, R * sag * 1.12, R * sag * 0.95)        # heavier at the bottom
        q = (dx / R) ** 2 + (dy / ry) ** 2
        h = hs * R * np.clip(1 - q, 0, None) ** 0.8
        Hh[ix] = op(Hh[ix], h)

    # static drops of all sizes
    for n, lo, hi in ((4200, 1.0, 2.4), (1100, 2.4, 4.5), (260, 4.5, 8.0), (45, 8.0, 13.0)):
        R = rng.uniform(lo, hi, n)
        xs, ys = rng.uniform(0, N, n), rng.uniform(0, N, n)
        sag = 1 + 0.25 * (R / 13.0) * rng.uniform(0.5, 1.0, n)
        for x, y, r, s in zip(xs, ys, R, sag):
            drop(x, y, r, s)
    # short running rivulets: wipe a track, lay a thin beaded trail, finish with a heavy head drop
    for _ in range(28):
        x0, y0 = rng.uniform(0, N), rng.uniform(0, N)
        L = rng.uniform(50, 230)
        w = rng.uniform(1.4, 2.8)
        steps = int(L)
        wander = np.cumsum(rng.normal(0, 0.35, steps))
        wander = gaussian_filter(wander, 6)
        xs = x0 + wander
        ys = y0 + np.arange(steps)
        for k in range(0, steps, 2):                                   # wipe
            r = int(np.ceil(w + 4))
            ix, dx, dy = patch(xs[k], ys[k], r)
            m = (dx ** 2 + dy ** 2) < (w + 3.5) ** 2
            Hh[ix] = np.where(m, 0.0, Hh[ix])
        width = w * (0.75 + 0.25 * np.sin(np.arange(steps) / rng.uniform(4, 9)))
        fade = np.clip(np.arange(steps) / (0.35 * steps), 0, 1)          # thin / broken near the top
        for k in range(steps):
            if fade[k] < 1 and rng.random() > fade[k]:
                continue
            drop(xs[k], ys[k], width[k], 1.0, 0.22)
        drop(xs[-1], ys[-1] + w, w * 2.3 + 2.0, 1.3, 0.36)
    hn = height_to_normal_rgb(Hh, 1.9)
    info = save("T_GW_RainGlass", hn, "RGB")
    info["seam_ratio"] = round(seam_error(hn), 2)
    cov = gaussian_filter(smoothstep(0.0, 0.2, Hh), 0.6, mode="wrap")
    m8 = to8(cov)
    mi = save("T_GW_RainGlassMask", m8, "L")
    mi["coverage_fraction"] = round(float((cov > 0.5).mean()), 3)
    return info, mi


# ------------------------------------------------------------------ rock

def rock_fields(seed=61):
    U, V = uv_grid(N, N)
    rng = np.random.default_rng(seed)
    warp = 0.06 * fbm2(U * 3, V * 3, 3, seed, period=(3, 3)) + 0.015 * fbm2(U * 12, V * 12, 2, seed + 1, period=(12, 12))
    nl = 9
    thick = rng.uniform(0.45, 1.6, nl)
    cum = np.r_[0, np.cumsum(thick)] / thick.sum()
    vv = np.mod(V + warp + 0.5 * thick[0] / thick.sum(), 1.0)       # keep layer seams off the tile edge
    L = np.interp(vv, cum, np.arange(nl + 1))
    lid = np.floor(L).astype(int) % nl
    fr = L - np.floor(L)
    hard = rng.uniform(0.25, 1.0, nl)[lid]
    tint = rng.uniform(0, 1, nl)[lid]
    prof = smoothstep(0.0, 0.14, fr) * (1 - smoothstep(0.82, 1.0, fr))
    seam = 1 - smoothstep(0.0, 0.05, fr) * (1 - smoothstep(0.95, 1.0, fr))
    seam *= 0.45 + 0.55 * smoothstep(-0.3, 0.3, fbm2(U * 6, V * 3, 2, seed + 15, period=(6, 3)))
    # block joints: Worley edges looked up through a periodic domain warp so the fractures wander,
    # with width and continuity varying along each fracture
    wu = (U + 0.035 * fbm2(U * 6, V * 6, 3, seed + 9, period=(6, 6))
          + 0.012 * fbm2(U * 24, V * 24, 2, seed + 10, period=(24, 24)))
    wv = (V + 0.035 * fbm2(U * 6 + 3.3, V * 6 + 1.7, 3, seed + 11, period=(6, 6))
          + 0.012 * fbm2(U * 24 + 2.1, V * 24 + 4.2, 2, seed + 12, period=(24, 24)))
    f1, f2 = worley2(N, N, 6, 3, seed + 2, U=wu, V=wv)
    f1b, f2b = worley2(N, N, 13, 8, seed + 3, U=wu, V=wv)
    cw = 0.02 + 0.045 * smoothstep(-0.4, 0.6, fbm2(U * 7, V * 7, 2, seed + 13, period=(7, 7)))
    keep = smoothstep(-0.25, 0.15, fbm2(U * 5 + 7.7, V * 5, 2, seed + 14, period=(5, 5)))
    joint = (1 - smoothstep(0.0, 1.0, (f2 - f1) / cw)) * (0.3 + 0.7 * keep)
    joint2 = (1 - smoothstep(0.0, 0.03, f2b - f1b)) * smoothstep(0.0, 0.45, fbm2(U * 5, V * 5, 2, seed + 4, period=(5, 5)))
    fine_crack = smoothstep(0.88, 0.97, ridged2(wu * 16, wv * 16, 2, seed + 5, period=(16, 16)))
    big = fbm2(U * 3, V * 3, 4, seed + 16, period=(3, 3))
    mid = fbm2(U * 8, V * 8, 5, seed + 6, period=(8, 8))
    hi = fbm2(U * 48, V * 48, 3, seed + 7, period=(48, 48))
    block = 1 - f1b
    H = (0.5 * hard * prof + 0.25 * big + 0.25 * mid + 0.08 * hi + 0.08 * block
         - 0.45 * joint - 0.25 * joint2 - 0.18 * fine_crack - 0.2 * seam)
    crack = np.clip(np.maximum.reduce([joint, 0.8 * joint2, 0.7 * fine_crack, 0.8 * seam]), 0, 1)
    stain = smoothstep(-0.1, 0.5, fbm2(U * 20, V * 2, 3, seed + 8, period=(20, 2)))   # vertical water stains
    return U, V, H, crack, tint, stain, mid, hi


def tex_rock():
    U, V, H, crack, tint, stain, mid, hi = rock_fields()
    rng = np.random.default_rng(62)
    grey = np.array([66, 65, 63], float)
    brown = np.array([78, 66, 52], float)
    mix = np.clip(0.6 * tint + 0.4 * smoothstep(-0.4, 0.5, fbm2(U * 4, V * 4, 3, 63, period=(4, 4))), 0, 1)
    col = grey[None, None] * (1 - mix[..., None]) + brown[None, None] * mix[..., None]
    cav = np.clip(1 + 2.2 * (H - gaussian_filter(H, 7, mode="wrap")), 0.45, 1.2)
    col *= cav[..., None]
    col *= (1 - 0.7 * crack)[..., None]
    col *= (1 - 0.25 * stain)[..., None]
    col *= (0.9 + 0.12 * mid + 0.1 * hi)[..., None]
    speck = (rng.random((N, N)) > 0.985) * rng.uniform(0.05, 0.2, (N, N))
    col *= (1 + gaussian_filter(speck, 0.6, mode="wrap") * 2)[..., None]
    col *= 0.86                                                         # wet = darker
    base = np.clip(np.round(col), 0, 255).astype(np.uint8)
    info_c = save("T_GW_Rock_BaseColor", base, "RGB")
    info_c["seam_ratio"] = round(seam_error(base), 2)
    Hp = H * 14.0                                                       # pixels of relief
    gx, gy = roll_grad(Hp)
    s = 0.85 / np.percentile(np.hypot(gx, gy), 95)
    nrm = height_to_normal_rgb(Hp, s)
    info_n = save("T_GW_Rock_Normal", nrm, "RGB")
    info_n["seam_ratio"] = round(seam_error(nrm), 2)
    return info_c, info_n


# ------------------------------------------------------------------ grass

def tex_grass():
    U, V = uv_grid(N, N)
    rng = np.random.default_rng(71)
    low = fbm2(U * 4, V * 4, 4, 72, period=(4, 4))
    soil = np.array([28, 30, 19], float)
    thatch = np.array([44, 40, 27], float)
    k = smoothstep(-0.3, 0.3, low)[..., None]
    img = soil * (1 - k) + thatch * k
    dry = fbm2(U * 3, V * 3, 3, 73, period=(3, 3))
    green = np.array([68, 80, 45], float)
    olive = np.array([84, 84, 52], float)
    straw = np.array([104, 93, 63], float)
    flow = fbm2(U * 2, V * 2, 2, 75, period=(2, 2))
    nb = 34000
    order = rng.permutation(nb)
    x0 = rng.uniform(0, N, nb)[order]
    y0 = rng.uniform(0, N, nb)[order]
    ang = 0.5 * flow[y0.astype(int) % N, x0.astype(int) % N] + rng.normal(0, 0.12, nb)   # flattened along +U
    L = rng.uniform(18, 64, nb)
    wid = rng.choice([1, 1, 2], nb)
    bend = rng.normal(0, 4.0, nb)
    d = dry[y0.astype(int) % N, x0.astype(int) % N] + rng.normal(0, 0.22, nb)
    t1 = smoothstep(-0.35, 0.1, d)[:, None]
    t2 = smoothstep(0.1, 0.55, d)[:, None]
    col = green * (1 - t1) + olive * t1
    col = col * (1 - t2) + straw * t2
    col *= rng.uniform(0.7, 1.1, nb)[:, None]
    for c0 in range(0, nb, 4000):
        sl = slice(c0, c0 + 4000)
        cnt = np.ceil(L[sl] / 0.6).astype(int)
        idx = np.repeat(np.arange(len(cnt)), cnt)
        start = np.repeat(np.cumsum(cnt) - cnt, cnt)
        t = (np.arange(cnt.sum()) - start) / cnt[idx]
        a = ang[sl][idx]
        ll = L[sl][idx]
        bb = bend[sl][idx]
        px = x0[sl][idx] + t * ll * np.cos(a) - bb * t * t * np.sin(a)
        py = y0[sl][idx] + t * ll * np.sin(a) + bb * t * t * np.cos(a)
        shade = (0.5 + 0.5 * t)[:, None]
        c = col[sl][idx] * shade
        ix = np.floor(px).astype(int) % N
        iy = np.floor(py).astype(int) % N
        img[(iy + 1) % N, ix] = img[(iy + 1) % N, ix] * 0.55        # blade shadow
        img[iy, ix] = c
        two = wid[sl][idx] == 2
        img[(iy[two] + 1) % N, ix[two]] = c[two] * 0.85
    img = gaussian_filter(img, (0.55, 0.55, 0), mode="wrap")
    tone = 0.85 + 0.2 * smoothstep(-0.5, 0.5, fbm2(U * 2, V * 2, 3, 74, period=(2, 2)))
    img *= tone[..., None]
    out = np.clip(np.round(img), 0, 255).astype(np.uint8)
    info = save("T_GW_Grass_BaseColor", out, "RGB")
    info["seam_ratio"] = round(seam_error(out), 2)
    return info


# ------------------------------------------------------------------ main

BUILDERS = {
    "T_GW_SeaNormal": tex_sea_normal,
    "T_GW_SeaFoam": tex_sea_foam,
    "T_GW_Clouds": tex_clouds,
    "T_GW_RainStreaks": tex_rain_streaks,
    "T_GW_RainGlass": tex_rain_glass,
    "T_GW_Rock": tex_rock,
    "T_GW_Grass_BaseColor": tex_grass,
}


def build(names=None):
    out = {}
    for name, fn in BUILDERS.items():
        if names and name not in names:
            continue
        r = fn()
        if name == "T_GW_RainGlass":
            out["T_GW_RainGlass"], out["T_GW_RainGlassMask"] = r
        elif name == "T_GW_Rock":
            out["T_GW_Rock_BaseColor"], out["T_GW_Rock_Normal"] = r
        else:
            out[name] = r
        print("  ", name, {k: v for k, v in (r[0] if isinstance(r, tuple) else r).items() if k == "seam_ratio"})
    return out


if __name__ == "__main__":
    build(sys.argv[1:])
