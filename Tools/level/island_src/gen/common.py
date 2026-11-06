"""Shared helpers for the island exterior asset generators (numpy only).

Noise (tileable Perlin 2D, Perlin 3D, fBm, Worley) and an indexed OBJ writer that follows the
convention of Tools/level/gen_arch_meshes.py: meshes are authored in UE space (cm, Z up), written as
"v x -y z" / "vn nx -ny nz", and every face is wound so that its geometric normal computed in OBJ space
(y negated) points outward.
"""
import os

import numpy as np

GEN = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(GEN)
MESH_DIR = os.path.join(ROOT, "meshes")
TEX_DIR = os.path.join(ROOT, "tex")
AUDIO_DIR = os.path.join(ROOT, "audio")
for _d in (MESH_DIR, TEX_DIR, AUDIO_DIR):
    os.makedirs(_d, exist_ok=True)


# ------------------------------------------------------------------ small math

def smoothstep(e0, e1, x):
    t = np.clip((np.asarray(x, dtype=np.float64) - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def normalize(v, axis=-1):
    n = np.linalg.norm(v, axis=axis, keepdims=True)
    return v / np.where(n < 1e-12, 1.0, n)


# ------------------------------------------------------------------ noise

_TABLES = {}


def _tables(seed):
    t = _TABLES.get(seed)
    if t is None:
        rng = np.random.default_rng(seed)
        perm = rng.permutation(256).astype(np.int64)
        ang = rng.uniform(0.0, 2.0 * np.pi, 256)
        g2 = np.stack([np.cos(ang), np.sin(ang)], -1)
        g3 = normalize(rng.normal(size=(256, 3)))
        t = _TABLES[seed] = (perm, g2, g3)
    return t


def _fade(t):
    return t * t * t * (t * (t * 6.0 - 15.0) + 10.0)


def perlin2(x, y, seed=0, period=None):
    """Gradient noise, roughly in [-1, 1]. period=(px, py) (integers) makes it tile on that lattice."""
    perm, g2, _ = _tables(seed)
    x = np.asarray(x, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    xi = np.floor(x).astype(np.int64)
    yi = np.floor(y).astype(np.int64)
    fx, fy = x - xi, y - yi
    x0, x1, y0, y1 = xi, xi + 1, yi, yi + 1
    if period is not None:
        px, py = period
        if px:
            x0, x1 = x0 % px, x1 % px
        if py:
            y0, y1 = y0 % py, y1 % py

    def grad(ix, iy, dx, dy):
        h = perm[(perm[ix & 255] + iy) & 255]
        g = g2[h]
        return g[..., 0] * dx + g[..., 1] * dy

    n00 = grad(x0, y0, fx, fy)
    n10 = grad(x1, y0, fx - 1, fy)
    n01 = grad(x0, y1, fx, fy - 1)
    n11 = grad(x1, y1, fx - 1, fy - 1)
    u, v = _fade(fx), _fade(fy)
    nx0 = n00 + u * (n10 - n00)
    nx1 = n01 + u * (n11 - n01)
    return 1.41 * (nx0 + v * (nx1 - nx0))


def fbm2(x, y, octaves=4, seed=0, period=None, lac=2.0, gain=0.5):
    """Normalised fBm (sum of octaves / sum of amplitudes). With period, lac must be an integer."""
    tot = np.zeros(np.broadcast(np.asarray(x), np.asarray(y)).shape)
    amp, fr, norm = 1.0, 1.0, 0.0
    for o in range(octaves):
        per = None
        if period is not None:
            per = (int(round(period[0] * fr)) if period[0] else None, int(round(period[1] * fr)) if period[1] else None)
        tot += amp * perlin2(x * fr, y * fr, seed * 101 + o, per)
        norm += amp
        amp *= gain
        fr *= lac
    return tot / norm


def ridged2(x, y, octaves=3, seed=0, period=None):
    """Ridged multifractal-ish noise in [0, 1] (sharp crests)."""
    tot = np.zeros(np.broadcast(np.asarray(x), np.asarray(y)).shape)
    amp, fr, norm = 1.0, 1.0, 0.0
    for o in range(octaves):
        per = None
        if period is not None:
            per = (int(period[0] * fr) if period[0] else None, int(period[1] * fr) if period[1] else None)
        n = 1.0 - np.abs(perlin2(x * fr, y * fr, seed * 131 + o, per))
        tot += amp * n * n
        norm += amp
        amp *= 0.5
        fr *= 2.0
    return tot / norm


def perlin3(p, seed=0):
    """3D gradient noise for points p (..., 3), roughly in [-1, 1]."""
    perm, _, g3 = _tables(seed)
    p = np.asarray(p, dtype=np.float64)
    pi = np.floor(p).astype(np.int64)
    f = p - pi
    u = _fade(f)
    res = 0.0
    out = None
    for dx in (0, 1):
        for dy in (0, 1):
            for dz in (0, 1):
                ix, iy, iz = pi[..., 0] + dx, pi[..., 1] + dy, pi[..., 2] + dz
                h = perm[(perm[(perm[ix & 255] + iy) & 255] + iz) & 255]
                g = g3[h]
                d = (g[..., 0] * (f[..., 0] - dx) + g[..., 1] * (f[..., 1] - dy) + g[..., 2] * (f[..., 2] - dz))
                w = ((u[..., 0] if dx else 1 - u[..., 0]) * (u[..., 1] if dy else 1 - u[..., 1]) *
                     (u[..., 2] if dz else 1 - u[..., 2]))
                out = d * w if out is None else out + d * w
    res = out
    return 1.5 * res


def fbm3(p, octaves=4, seed=0, gain=0.5):
    tot, amp, fr, norm = 0.0, 1.0, 1.0, 0.0
    for o in range(octaves):
        tot = tot + amp * perlin3(p * fr, seed * 101 + o)
        norm += amp
        amp *= gain
        fr *= 2.0
    return tot / norm


def periodic1(theta, seed, kmin=2, kmax=10, slope=1.2):
    """Smooth 2*pi-periodic 1D noise of an angle, normalised to [-1, 1]."""
    rng = np.random.default_rng(seed)
    ks = np.arange(kmin, kmax + 1)
    amps = ks ** -slope * rng.uniform(0.6, 1.0, len(ks))
    ph = rng.uniform(0, 2 * np.pi, len(ks))
    ref = np.linspace(0, 2 * np.pi, 4096)
    f = lambda t: sum(a * np.cos(k * t + q) for k, a, q in zip(ks, amps, ph))
    return f(np.asarray(theta, dtype=np.float64)) / np.abs(f(ref)).max()


def uv_grid(h, w):
    """Pixel-centre coordinates in [0, 1): returns (U, V) arrays of shape (h, w); V grows downward (rows)."""
    v = (np.arange(h) + 0.5) / h
    u = (np.arange(w) + 0.5) / w
    return np.meshgrid(u, v)


def worley2(h, w, cx, cy, seed, jitter=1.0, U=None, V=None):
    """Tileable Worley noise on a cx * cy cell lattice. Returns (F1, F2) in cell units.
    U, V: optional (periodically) warped lookup coordinates in tile units."""
    rng = np.random.default_rng(seed)
    pts = (1.0 - jitter) / 2 + rng.random((cy, cx, 2)) * jitter
    if U is None:
        U, V = uv_grid(h, w)
    U, V = U * cx, V * cy
    ci, cj = np.floor(V).astype(np.int64), np.floor(U).astype(np.int64)
    f1 = np.full((h, w), np.inf)
    f2 = np.full((h, w), np.inf)
    for di in (-1, 0, 1):
        for dj in (-1, 0, 1):
            ni, nj = ci + di, cj + dj
            p = pts[ni % cy, nj % cx]
            d = np.hypot(nj + p[..., 1] - U, ni + p[..., 0] - V)
            f2 = np.minimum(f2, np.maximum(f1, d))
            f1 = np.minimum(f1, d)
    return f1, f2


def roll_grad(H):
    """Periodic central differences: (dH/dcol, dH/drow)."""
    gx = (np.roll(H, -1, 1) - np.roll(H, 1, 1)) * 0.5
    gy = (np.roll(H, -1, 0) - np.roll(H, 1, 0)) * 0.5
    return gx, gy


def height_to_normal_rgb(H, strength):
    """Tangent-space normal map, OpenGL convention (+Y = up in the image, i.e. toward row 0), +Z blue."""
    gx, gr = roll_grad(H)
    nx = -gx * strength
    ny = gr * strength          # dH/dv_up = -dH/drow, n_y = -dH/dv_up
    nz = np.ones_like(H)
    n = normalize(np.stack([nx, ny, nz], -1))
    return np.clip(np.round((n * 0.5 + 0.5) * 255), 0, 255).astype(np.uint8)


# ------------------------------------------------------------------ meshes

def face_normals(V, F):
    return np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]])


def vertex_normals(V, F):
    """Area-weighted smooth normals (F wound counter-clockwise around the outward normal, UE-space formula)."""
    fn = face_normals(V, F)
    N = np.zeros_like(V)
    for k in range(3):
        np.add.at(N, F[:, k], fn)
    bad = np.linalg.norm(N, axis=1) < 1e-12
    N[bad] = (0.0, 0.0, 1.0)
    return normalize(N)


def signed_volume(V, F):
    return float(np.einsum("ij,ij->i", V[F[:, 0]], np.cross(V[F[:, 1]], V[F[:, 2]])).sum() / 6.0)


def box_uv_corners(V, F, scale=100.0):
    """Per-corner box projection on the dominant face-normal axis (same rule as gen_arch_meshes.Mesh._uv)."""
    fn = face_normals(V, F)
    ax = np.argmax(np.abs(fn), axis=1)
    pairs = np.array([(1, 2), (0, 2), (0, 1)])[ax]
    P = V[F]                                            # (m, 3, 3)
    a = np.take_along_axis(P, pairs[:, None, 0:1].repeat(3, 1), 2)[..., 0]
    b = np.take_along_axis(P, pairs[:, None, 1:2].repeat(3, 1), 2)[..., 0]
    return np.stack([a, b], -1) / scale


def write_obj(name, V, F, N=None, UV=None, UVF=None, out_dir=MESH_DIR, closed=False):
    """Write an OBJ in the project's convention.

    V  (n, 3) UE-space vertices (cm, Z up)
    F  (m, 3) faces wound so that cross(v1 - v0, v2 - v0) computed in UE space points OUTWARD
    N  (n, 3) UE-space vertex normals (computed smooth if None)
    UV (n, 2) per-vertex UVs, or UVF (m, 3, 2) per-corner UVs
    Mirroring y flips handedness, so the faces are written as (v0, v2, v1): their geometric normal in OBJ
    space (y negated) then points outward, exactly as gen_arch_meshes.Mesh.tri() arranges it.
    """
    V = np.asarray(V, dtype=np.float64)
    F = np.asarray(F, dtype=np.int64)
    if N is None:
        N = vertex_normals(V, F)
    # drop degenerate faces
    area = np.linalg.norm(face_normals(V, F), axis=1)
    keep = area > 1e-9
    F = F[keep]
    if UVF is not None:
        UVF = np.asarray(UVF)[keep]
    Fo = F[:, [0, 2, 1]]
    if UVF is not None:
        UVFo = UVF[:, [0, 2, 1]]
        flat = np.round(UVFo.reshape(-1, 2), 5)
        vt, inv = np.unique(flat, axis=0, return_inverse=True)
        Ti = inv.reshape(-1, 3)
    else:
        vt = np.asarray(UV, dtype=np.float64)
        Ti = Fo
    # verification in OBJ space, exactly as the importer will see it
    M = np.array([1.0, -1.0, 1.0])
    Vo, No = V * M, N * M
    gn = np.cross(Vo[Fo[:, 1]] - Vo[Fo[:, 0]], Vo[Fo[:, 2]] - Vo[Fo[:, 0]])
    avg = No[Fo].sum(1)
    disagree = int((np.einsum("ij,ij->i", gn, avg) < 0).sum())
    vol = signed_volume(Vo, Fo)
    path = os.path.join(out_dir, name + ".obj")
    with open(path, "w", encoding="ascii", newline="\n") as fh:
        fh.write(f"o {name}\n")
        np.savetxt(fh, Vo, fmt="v %.4f %.4f %.4f")
        np.savetxt(fh, vt, fmt="vt %.5f %.5f")
        np.savetxt(fh, No, fmt="vn %.4f %.4f %.4f")
        idx = np.stack([Fo + 1, Ti + 1, Fo + 1], -1).reshape(-1, 9)
        np.savetxt(fh, idx, fmt="f %d/%d/%d %d/%d/%d %d/%d/%d")
    info = {
        "tris": int(len(F)), "verts": int(len(V)),
        "bbox_min": [round(float(c), 1) for c in V.min(0)],
        "bbox_max": [round(float(c), 1) for c in V.max(0)],
        "normal_face_disagree": disagree,
    }
    msg = f"{name}: {info['tris']} tris, {info['verts']} verts, bbox {info['bbox_min']} .. {info['bbox_max']}"
    msg += f", faces vs normals disagree {disagree}"
    if closed:
        msg += f", OBJ-space signed volume {vol / 1e6:.3f} m3 ({'outward' if vol > 0 else 'INWARD!'})"
        info["obj_signed_volume_m3"] = round(vol / 1e6, 4)
    print(msg)
    return info
