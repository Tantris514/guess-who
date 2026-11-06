"""Island exterior meshes (OBJ, UE space cm, Z up) -> island_src/meshes/*.obj

  V:\\ComfyUI\\ComfyUI\\ComfyUI\\.venv\\Scripts\\python.exe -I gen_meshes.py [name ...]

Manor footprint x 0..6000, y 0..4400, floor z 0. Sea surface at z -2000. North = +X, east = +Y.
"""
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (box_uv_corners, face_normals, fbm2, fbm3, normalize, perlin2, perlin3, periodic1, ridged2,  # noqa: E402
                    smoothstep, vertex_normals, write_obj)

FOOT = (0.0, 6000.0, 0.0, 4400.0)
GRID_X = (-4500.0, 10500.0)
GRID_Y = (-4500.0, 8900.0)
STEP = 100.0
SEA_Z = -2000.0
PLATEAU_Z = -45.0


def soft_clip(x, lo, hi, k):
    """Smooth clamp of x into ~[lo - 0.7k, hi] without the flat runs of a hard clip."""
    y = lo + k * np.logaddexp(0.0, (x - lo) / k)
    return hi - k * np.logaddexp(0.0, (hi - y) / k)


def rect_dist(X, Y, x0, x1, y0, y1):
    dx = np.maximum(np.maximum(x0 - X, X - x1), 0.0)
    dy = np.maximum(np.maximum(y0 - Y, Y - y1), 0.0)
    return np.hypot(dx, dy)


# ================================================================== island

def island_height(X, Y):
    """Returns z and a dict of diagnostic fields."""
    d = rect_dist(X, Y, *FOOT)
    d100 = rect_dist(X, Y, FOOT[0] - 100, FOOT[1] + 100, FOOT[2] - 100, FOOT[3] + 100)
    th = np.arctan2(Y - 2200.0, X - 3000.0)
    # 1 toward north (+X) / east (+Y): the lawn beyond the conservatory; 0 toward south / west
    w = smoothstep(-0.35, 0.85, np.cos(th - np.pi / 4))
    # plateau edge distance from the footprint: smooth noise of the angle + 2D warp, soft-clamped so that the
    # actual edge stays 1250..2550 cm from the footprint
    E = (1600 + 650 * w + 330 * periodic1(th, 11, 2, 6) + 170 * periodic1(th, 12, 6, 14, 0.8)
         + 60 * periodic1(th, 15, 14, 30, 0.8)
         + 260 * fbm2(X / 1600, Y / 1600, 2, seed=22) + 110 * fbm2(X / 560, Y / 560, 2, seed=23))
    E = soft_clip(E, 1290, 2530, 50)
    # cliff horizontal width and rocky shore band width (angle + 2D noise -> jagged cliff foot)
    C = np.clip(700 + 200 * periodic1(th, 13, 2, 9) + 170 * fbm2(X / 800, Y / 800, 2, seed=24) - 110 * w, 400, 1000)
    S = np.clip(560 + 150 * periodic1(th, 14, 2, 9) + 160 * fbm2(X / 700, Y / 700, 2, seed=25) - 100 * w, 300, 800)
    t = d - E

    # plateau: -45 +- 15, never above -40 inside footprint + 100
    n = fbm2(X / 1700, Y / 1700, 3, seed=31)
    n = n / np.abs(n).max()
    und = 15 * n
    f = smoothstep(0, 500, d100)
    und = f * und + (1 - f) * np.minimum(und, 3.0)
    plat = PLATEAU_Z + und
    lip = -30 * smoothstep(-220, 0, t) ** 2
    top = plat - 30

    # cliffs: steep drop with ledges and crags (heightfield, so no overhangs)
    s = np.clip(t / C, 0, 1)
    g = 0.55 * (1 - (1 - s) ** 1.8) + 0.45 * s
    nl = 4.0
    q = g * nl + 0.9 * perlin2(X / 900, Y / 900, seed=41) * 4 * s * (1 - s)
    fl = np.floor(q)
    terr = (fl + smoothstep(0.45, 0.95, q - fl)) / nl
    g2 = np.clip(g + 0.85 * (terr - g), 0, 1)
    crag = 210 * fbm2(X / 420, Y / 420, 4, seed=51) + 260 * (ridged2(X / 190, Y / 190, 3, seed=52) - 0.55)
    env = 4 * s * (1 - s)
    zc = top + (SEA_Z - top) * g2 + crag * env
    zc = np.clip(zc, SEA_Z - 10, top + 5)

    # rocky shore band -2000 .. -2150
    s3 = np.clip((t - C) / S, 0, 1)
    rock = 70 * fbm2(X / 260, Y / 260, 3, seed=61) + 45 * (ridged2(X / 140, Y / 140, 2, seed=62) - 0.5)
    zs = SEA_Z - 150 * s3 ** 0.8 + rock * np.sin(np.pi * s3) ** 0.5
    zs = np.clip(zs, -2150, SEA_Z + 8)

    # sea bed falling to -2600
    t2 = t - C - S
    zd = -2150 - 450 * smoothstep(0, 550, t2) + 25 * fbm2(X / 500, Y / 500, 2, seed=71) * smoothstep(0, 250, t2)
    zd = np.minimum(zd, -2150)

    z = np.where(t < 0, plat + lip, np.where(t <= C, zc, np.where(t <= C + S, zs, zd)))
    b = np.minimum.reduce([X - GRID_X[0], GRID_X[1] - X, Y - GRID_Y[0], GRID_Y[1] - Y])
    z = np.minimum(z, -2600 + 4.5 * b)
    z = np.maximum(z, -2600)
    return z, dict(d=d, d100=d100, t=t, E=E, C=C, S=S, b=b)


def build_island():
    xs = np.arange(GRID_X[0], GRID_X[1] + 1, STEP)
    ys = np.arange(GRID_Y[0], GRID_Y[1] + 1, STEP)
    X, Y = np.meshgrid(xs, ys, indexing="ij")
    Z, diag = island_height(X, Y)
    nx, ny = X.shape
    V = np.stack([X, Y, Z], -1).reshape(-1, 3)
    idx = np.arange(nx * ny).reshape(nx, ny)
    a, b_, c, d = idx[:-1, :-1], idx[1:, :-1], idx[1:, 1:], idx[:-1, 1:]
    a, b_, c, d = a.ravel(), b_.ravel(), c.ravel(), d.ravel()
    # per cell pick the shorter 3D diagonal (crisper crags); both splits are CCW seen from +Z in UE space
    diag_ac = np.linalg.norm(V[a] - V[c], axis=1) <= np.linalg.norm(V[b_] - V[d], axis=1)
    F1 = np.where(diag_ac[:, None], np.stack([a, b_, c], 1), np.stack([a, b_, d], 1))
    F2 = np.where(diag_ac[:, None], np.stack([a, c, d], 1), np.stack([b_, c, d], 1))
    F = np.concatenate([F1, F2])
    UV = V[:, :2] / 400.0
    up = int((face_normals(V, F)[:, 2] > 0).sum())
    assert up == len(F), "heightfield face facing down"
    info = write_obj("SM_GW_Island", V, F, UV=UV)
    info["faces_facing_up"] = f"{up}/{len(F)}"

    # ---- checks
    inside = diag["d100"] == 0
    zin = Z[inside]
    edge = Z < PLATEAU_Z - 60      # vertices that have started to drop off the plateau
    dedge = diag["d"][edge]
    shore_end = diag["t"] - diag["C"] - diag["S"]
    room = diag["b"][(shore_end > -1) & (shore_end < 100)]
    plateau = Z[(diag["t"] < -250)]
    chk = {
        "z_min": round(float(Z.min()), 1), "z_max": round(float(Z.max()), 1),
        "footprint_plus_100_max_z": round(float(zin.max()), 2),
        "footprint_plus_100_vertices": int(inside.sum()),
        "footprint_plus_100_vertices_above_minus40": int((zin > -40).sum()),
        "plateau_z_range": [round(float(plateau.min()), 1), round(float(plateau.max()), 1)],
        "plateau_edge_distance_from_footprint_cm": [round(float(dedge.min())), None],
        "min_room_shore_end_to_grid_border_cm": round(float(room.min())) if room.size else None,
        "border_ring_z": [round(float(Z[[0, -1], :].min()), 1), round(float(np.r_[Z[[0, -1], :].ravel(), Z[:, [0, -1]].ravel()].max()), 1)],
    }
    # max plateau-edge distance: per angle, the distance where the drop starts
    th = np.degrees(np.arctan2(Y - 2200, X - 3000))
    bins = np.floor((th + 180) / 10).astype(int)
    first = []
    for k in range(36):
        m = (bins == k) & edge
        if m.any():
            first.append(diag["d"][m].min())
    chk["plateau_edge_distance_from_footprint_cm"][1] = round(float(max(first)))
    north = diag["d"][edge & (np.abs(th) < 25)].min()
    east = diag["d"][edge & (np.abs(th - 90) < 25)].min()
    south_ = diag["d"][edge & (np.abs(th + 90) < 25)].min()
    west = diag["d"][edge & (np.abs(np.abs(th) - 180) < 25)].min()
    chk["edge_distance_by_side_cm"] = {"north(+X)": round(float(north)), "east(+Y)": round(float(east)),
                                       "south(-Y)": round(float(south_)), "west(-X)": round(float(west))}
    print("island checks:", chk)
    assert chk["footprint_plus_100_vertices_above_minus40"] == 0
    info.update(chk)
    return info


# ================================================================== geodesic sphere

def geosphere(freq):
    """Class-I geodesic icosphere: 20 * freq^2 triangles, unit radius, faces CCW around the outward normal."""
    p = (1 + 5 ** 0.5) / 2
    iv = np.array([(-1, p, 0), (1, p, 0), (-1, -p, 0), (1, -p, 0), (0, -1, p), (0, 1, p), (0, -1, -p), (0, 1, -p),
                   (p, 0, -1), (p, 0, 1), (-p, 0, -1), (-p, 0, 1)], float)
    iv = normalize(iv)
    ifc = [(0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11), (1, 5, 9), (5, 11, 4), (11, 10, 2), (10, 7, 6),
           (7, 1, 8), (3, 9, 4), (3, 4, 2), (3, 2, 6), (3, 6, 8), (3, 8, 9), (4, 9, 5), (2, 4, 11), (6, 2, 10),
           (8, 6, 7), (9, 8, 1)]
    pts, faces = [], []
    for A, B, Cc in ifc:
        a, b, c = iv[A], iv[B], iv[Cc]
        if np.dot(np.cross(b - a, c - a), a + b + c) < 0:
            b, c = c, b
        base = len(pts)
        lid = {}
        for i in range(freq + 1):
            for j in range(freq + 1 - i):
                lid[(i, j)] = len(pts) - base
                pts.append(a + (b - a) * i / freq + (c - a) * j / freq)
        for i in range(freq):
            for j in range(freq - i):
                faces.append((base + lid[(i, j)], base + lid[(i + 1, j)], base + lid[(i, j + 1)]))
                if i + j + 1 < freq:
                    faces.append((base + lid[(i + 1, j)], base + lid[(i + 1, j + 1)], base + lid[(i, j + 1)]))
    P = normalize(np.array(pts))
    key = np.round(P, 6)
    U, inv = np.unique(key, axis=0, return_inverse=True)
    F = inv.ravel()[np.array(faces)]
    return normalize(U), F


def finish_blob(name, V, F, base_at_zero, closed=True, extra=None):
    """Recentre (pivot at base centre or bbox centre), smooth normals, box UVs, write."""
    lo, hi = V.min(0), V.max(0)
    c = (lo + hi) / 2
    if base_at_zero:
        V = V - np.array([c[0], c[1], lo[2]])
    else:
        V = V - c
    N = vertex_normals(V, F)
    info = write_obj(name, V, F, N=N, UVF=box_uv_corners(V, F, 100.0), closed=closed)
    if extra:
        info.update(extra)
    return info


def build_boulder(name, freq, radii, seed, target_w):
    P, F = geosphere(freq)
    rng = np.random.default_rng(seed)
    r = 1 + 0.20 * fbm3(P * 1.3 + seed, 4, seed) + 0.10 * (fbm3(P * 3.1 + 7, 3, seed + 1))
    r += 0.07 * (1 - np.abs(perlin3(P * 2.2 + 3, seed + 2))) ** 2 + 0.03 * perlin3(P * 7.0, seed + 4)
    Q = P * r[:, None] * np.array(radii)
    # fractured facets: clip against random planes (rock cleavage)
    for _ in range(9):
        n = normalize(rng.normal(size=3) * np.array([1, 1, 0.6]))
        off = np.dot(np.abs(n), radii) * rng.uniform(0.62, 0.8)
        e = Q @ n - off
        Q -= np.maximum(e, 0)[:, None] * n
    cut = -radii[2] * 0.55
    Q[:, 2] = np.maximum(Q[:, 2], cut + 4 * perlin2(Q[:, 0] / 40, Q[:, 1] / 40, seed + 3))
    Q[:, 2] = np.maximum(Q[:, 2], cut)
    w = Q[:, :2].max(0) - Q[:, :2].min(0)
    Q *= target_w / w.max()
    return finish_blob(name, Q, F, base_at_zero=True)


def build_crown(name, freq, seed):
    P, F = geosphere(freq)
    rng = np.random.default_rng(seed)
    r = 1 + 0.10 * fbm3(P * 2.0 + seed, 3, seed)
    # foliage clumps: gaussian puffs on the surface
    for _ in range(22):
        c = normalize(rng.normal(size=3) * np.array([1.0, 1.0, 0.8]))
        r += rng.uniform(0.18, 0.36) * np.exp(-np.sum((P - c) ** 2, 1) / rng.uniform(0.035, 0.09))
    r += 0.07 * (1 - np.abs(perlin3(P * 5.0, seed + 5)))
    Q = P * r[:, None]
    Q[:, 2] = np.where(Q[:, 2] < 0, Q[:, 2] * 0.75, Q[:, 2])         # flatter underside
    Q[:, 0] += 0.18 * np.maximum(Q[:, 2], 0) + 0.12 * Q[:, 0] * (Q[:, 0] > 0)   # streamed toward +X (wind)
    ext = Q.max(0) - Q.min(0)
    Q *= np.array([300.0, 220.0, 180.0]) / ext
    return finish_blob(name, Q, F, base_at_zero=False)


def build_bush(name, freq, seed):
    P, F = geosphere(freq)
    rng = np.random.default_rng(seed)
    r = 1 + 0.12 * fbm3(P * 2.2 + seed, 3, seed)
    for _ in range(16):
        c = normalize(rng.normal(size=3) * np.array([1.0, 1.0, 0.5]) + np.array([0, 0, 0.6]))
        r += rng.uniform(0.10, 0.22) * np.exp(-np.sum((P - c) ** 2, 1) / rng.uniform(0.04, 0.10))
    r += 0.05 * (1 - np.abs(perlin3(P * 5.0, seed + 5)))
    Q = P * r[:, None]
    Q[:, 2] = np.where(Q[:, 2] < 0, Q[:, 2] * 0.12, Q[:, 2])         # flat base lens
    zt = np.clip(Q[:, 2], 0, None)
    Q[:, 0] += 0.35 * zt ** 1.3                                        # top swept toward +X
    ext = Q.max(0) - Q.min(0)
    Q *= np.array([180.0, 140.0, 90.0]) / ext
    return finish_blob(name, Q, F, base_at_zero=True)


# ================================================================== sea

def build_sea():
    n = 160
    xs = np.linspace(-25000, 25000, n + 1)
    X, Y = np.meshgrid(xs, xs, indexing="ij")
    V = np.stack([X, Y, np.zeros_like(X)], -1).reshape(-1, 3)
    idx = np.arange((n + 1) ** 2).reshape(n + 1, n + 1)
    a, b, c, d = idx[:-1, :-1].ravel(), idx[1:, :-1].ravel(), idx[1:, 1:].ravel(), idx[:-1, 1:].ravel()
    F = np.concatenate([np.stack([a, b, c], 1), np.stack([a, c, d], 1)])
    N = np.tile([0.0, 0.0, 1.0], (len(V), 1))
    return write_obj("SM_GW_SeaGrid", V, F, N=N, UV=V[:, :2] / 1000.0)


# ================================================================== trees

def transport_frames(P):
    T = normalize(np.gradient(P, axis=0))
    ref = np.array([0.0, 1.0, 0.0]) if abs(T[0, 1]) < 0.9 else np.array([1.0, 0.0, 0.0])
    N1 = np.zeros_like(P)
    N1[0] = normalize(np.cross(ref, T[0]))
    for k in range(1, len(P)):
        v = N1[k - 1] - np.dot(N1[k - 1], T[k]) * T[k]
        N1[k] = normalize(v)
    N2 = np.cross(T, N1)
    return T, N1, N2


def tube(P, R, sides, seed, u_tiles=2.0, bark=0.06, cap_start=True, cap_end=True):
    """Closed tapered tube along spine P (K, 3) with radii R (K,). Returns V, F, UVF (CCW outward)."""
    K = len(P)
    T, N1, N2 = transport_frames(P)
    arc = np.r_[0, np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))]
    a = 2 * np.pi * np.arange(sides) / sides
    S, A = np.meshgrid(np.arange(sides), arc, indexing="xy")       # (K, sides)
    rn = 1 + bark * perlin2(S * 4.0 / sides, A / 35.0, seed, period=(4, None))
    rr = R[:, None] * rn
    ca, sa = np.cos(a)[None, :, None], np.sin(a)[None, :, None]
    ring = P[:, None, :] + rr[..., None] * (ca * N1[:, None, :] + sa * N2[:, None, :])
    V = ring.reshape(-1, 3)
    F, UVF = [], []
    k = np.arange(K - 1)[:, None]
    s = np.arange(sides)[None, :]
    i00 = (k * sides + s).ravel()
    i01 = (k * sides + (s + 1) % sides).ravel()
    i11 = ((k + 1) * sides + (s + 1) % sides).ravel()
    i10 = ((k + 1) * sides + s).ravel()
    u0 = np.broadcast_to(s / sides * u_tiles, (K - 1, sides)).ravel()
    u1 = np.broadcast_to((s + 1) / sides * u_tiles, (K - 1, sides)).ravel()
    v0 = np.broadcast_to(arc[:-1, None] / 100.0, (K - 1, sides)).ravel()
    v1 = np.broadcast_to(arc[1:, None] / 100.0, (K - 1, sides)).ravel()
    F.append(np.stack([i00, i01, i11], 1))
    UVF.append(np.stack([np.stack([u0, v0], 1), np.stack([u1, v0], 1), np.stack([u1, v1], 1)], 1))
    F.append(np.stack([i00, i11, i10], 1))
    UVF.append(np.stack([np.stack([u0, v0], 1), np.stack([u1, v1], 1), np.stack([u0, v1], 1)], 1))
    extra = []
    sl = np.arange(sides)
    cu, cv = 0.5 * u_tiles, 0.0
    if cap_end:
        tip = P[-1] + T[-1] * max(R[-1] * 1.5, 1.0)
        ti = len(V) + len(extra)
        extra.append(tip)
        last = (K - 1) * sides
        F.append(np.stack([last + sl, last + (sl + 1) % sides, np.full(sides, ti)], 1))
        ring_uv = np.stack([np.cos(a) * 0.1 + cu, np.sin(a) * 0.1 + arc[-1] / 100.0], 1)
        UVF.append(np.stack([ring_uv, np.roll(ring_uv, -1, 0), np.tile([cu, arc[-1] / 100.0 + 0.15], (sides, 1))], 1))
    if cap_start:
        bot = P[0] - T[0] * R[0] * 0.3
        bi = len(V) + len(extra)
        extra.append(bot)
        F.append(np.stack([(sl + 1) % sides, sl, np.full(sides, bi)], 1))
        ring_uv = np.stack([np.cos(a) * 0.3 + cu, np.sin(a) * 0.3 + cv], 1)
        UVF.append(np.stack([np.roll(ring_uv, -1, 0), ring_uv, np.tile([cu, cv], (sides, 1))], 1))
    if extra:
        V = np.vstack([V, np.array(extra)])
    return V, np.concatenate(F), np.concatenate(UVF)


def bent_spine(length, n, phi0, phi1, power, yaw_wobble, seed, start, wobble=0.06, kink=(0.0, 0.5)):
    """Integrate a spine whose lean from vertical grows from phi0 to phi1 (radians) toward +X."""
    rng = np.random.default_rng(seed)
    s = np.linspace(0, 1, n)
    phi = phi0 + (phi1 - phi0) * s ** power + wobble * np.sin(s * rng.uniform(5, 9) + rng.uniform(0, 6))
    phi = phi + kink[0] * smoothstep(kink[1] - 0.06, kink[1] + 0.06, s)          # dogleg
    yaw = yaw_wobble * np.sin(s * rng.uniform(3, 6) + rng.uniform(0, 6))
    d = np.stack([np.sin(phi) * np.cos(yaw), np.sin(phi) * np.sin(yaw), np.cos(phi)], 1)
    step = length / (n - 1)
    P = np.vstack([start, start + np.cumsum(d[:-1] * step, axis=0)])
    return P, s


def swept_branch(start, d0, length, n, sweep, droop, seed):
    """Branch spine: starts along d0, bends toward the wind (+X) and droops at the end."""
    rng = np.random.default_rng(seed)
    s = np.linspace(0, 1, n)
    W = normalize(np.array([1.0, 0.0, -droop]))
    k = (s ** 0.8 * sweep)[:, None]
    d = normalize(d0[None, :] * (1 - k) + W[None, :] * k)
    d += 0.08 * np.stack([np.zeros(n), np.sin(s * 7 + rng.uniform(0, 6)), np.sin(s * 5 + rng.uniform(0, 6))], 1)
    d = normalize(d)
    step = length / (n - 1)
    return np.vstack([start, start + np.cumsum(d[:-1] * step, axis=0)])


TREES = {
    # cypress-like: tall, leaning from the base, crown pushed downwind (branches only on the sides / lee side)
    "SM_GW_TreeBent_A": dict(height=900, r0=30, rtop=6, phi=(0.22, 1.15), power=1.4, wobble=0.07, kink=(0, 0.5),
                             seed=101,
                             branches=[(0.36, 75, 0.30, 290), (0.48, -85, 0.22, 330), (0.60, 50, 0.15, 340),
                                       (0.72, -45, 0.05, 300), (0.84, 15, -0.05, 250)]),
    # pine-like: shorter, crooked, flat-topped
    "SM_GW_TreeBent_B": dict(height=760, r0=27, rtop=7, phi=(0.12, 0.35), power=1.0, wobble=0.10, kink=(0.75, 0.55),
                             seed=202,
                             branches=[(0.50, 100, 0.15, 330), (0.62, -105, 0.12, 360), (0.74, 65, 0.05, 340),
                                       (0.86, -50, 0.0, 280)]),
}


def tree_parts(name):
    cfg = TREES[name]
    rng = np.random.default_rng(cfg["seed"])
    n = 50
    # build with unit-ish length, then scale so the top sits at the target height
    P, s = bent_spine(1000.0, n, cfg["phi"][0], cfg["phi"][1], cfg["power"], 0.25, cfg["seed"], np.zeros(3),
                      cfg["wobble"], cfg["kink"])
    P *= cfg["height"] / P[-1, 2]
    # buried root extension 40 cm straight down (pivot stays at the trunk base on the ground, z = 0)
    P = np.vstack([np.array([[P[0, 0], P[0, 1], -40.0]]), P])
    s = np.r_[-0.04, s]
    R = cfg["r0"] + (cfg["rtop"] - cfg["r0"]) * np.clip(s, 0, 1) ** 0.85
    R *= 1 + 0.45 * np.exp(-np.maximum(P[:, 2], 0) / 70.0)              # root flare
    parts = [tube(P, R, 14, cfg["seed"], u_tiles=2.0, bark=0.07, cap_start=True, cap_end=True)]
    tips = [P[-1] + normalize(P[-1] - P[-2]) * R[-1] * 1.5]
    T, _, _ = transport_frames(P)
    for bi, (sb, az, el, length) in enumerate(cfg["branches"]):
        k = int(np.argmin(np.abs(s - sb)))
        az_r = math.radians(az)
        side = np.array([math.cos(az_r), math.sin(az_r), el])
        d0 = normalize(side - np.dot(side, T[k]) * T[k] * 0.7 + T[k] * 0.35)
        start = P[k] - d0 * R[k] * 0.4
        bp = swept_branch(start, d0, length, 16, 0.6, 0.12, cfg["seed"] + bi)
        rb = np.linspace(R[k] * 0.62, 2.5, len(bp)) ** 1.0 * (1 + 0.15 * np.exp(-np.linspace(0, 6, len(bp))))
        parts.append(tube(bp, rb, 10, cfg["seed"] + 10 + bi, u_tiles=1.0, bark=0.05))
        tips.append(bp[-1] + normalize(bp[-1] - bp[-2]) * rb[-1] * 1.5)
        # two short twigs per branch, also swept downwind
        bT, _, _ = transport_frames(bp)
        for ti in range(2):
            kk = int(len(bp) * rng.uniform(0.45, 0.75))
            sgn = 1 if ti == 0 else -1
            side2 = np.array([0.4, sgn * 0.9, rng.uniform(-0.1, 0.5)])
            d1 = normalize(side2 + bT[kk] * 0.5)
            tw = swept_branch(bp[kk] - d1 * rb[kk] * 0.3, d1, rng.uniform(80, 130), 9, 0.7, 0.2,
                              cfg["seed"] + 50 + bi * 2 + ti)
            rt = np.linspace(rb[kk] * 0.55, 1.2, len(tw))
            parts.append(tube(tw, rt, 7, cfg["seed"] + 70 + bi * 2 + ti, u_tiles=1.0, bark=0.04))
    return parts, tips


def build_tree(name):
    parts, tips = tree_parts(name)
    Vs, Fs, UVs, off = [], [], [], 0
    for V, F, UVF in parts:
        Vs.append(V)
        Fs.append(F + off)
        UVs.append(UVF)
        off += len(V)
    V, F, UVF = np.vstack(Vs), np.concatenate(Fs), np.concatenate(UVs)
    N = vertex_normals(V, F)
    info = write_obj(name, V, F, N=N, UVF=UVF, closed=True)
    info["crown_anchors_ue"] = [[round(float(c), 1) for c in t] for t in tips]
    info["note"] = "trunk base at origin on the ground (z=0); the trunk continues 40 cm below ground (z=-40) to sit on uneven terrain"
    return info


# ================================================================== main

BUILDERS = {
    "SM_GW_Island": build_island,
    "SM_GW_Boulder_A": lambda: build_boulder("SM_GW_Boulder_A", 10, (110, 95, 75), 7, 210),
    "SM_GW_Boulder_B": lambda: build_boulder("SM_GW_Boulder_B", 11, (130, 85, 60), 8, 230),
    "SM_GW_Boulder_C": lambda: build_boulder("SM_GW_Boulder_C", 12, (95, 90, 105), 9, 190),
    "SM_GW_SeaGrid": build_sea,
    "SM_GW_TreeBent_A": lambda: build_tree("SM_GW_TreeBent_A"),
    "SM_GW_TreeBent_B": lambda: build_tree("SM_GW_TreeBent_B"),
    "SM_GW_Crown_A": lambda: build_crown("SM_GW_Crown_A", 9, 301),
    "SM_GW_Crown_B": lambda: build_crown("SM_GW_Crown_B", 8, 302),
    "SM_GW_Bush_A": lambda: build_bush("SM_GW_Bush_A", 9, 401),
    "SM_GW_Bush_B": lambda: build_bush("SM_GW_Bush_B", 8, 402),
}


def build(names=None):
    out = {}
    for name, fn in BUILDERS.items():
        if names and name not in names:
            continue
        out[name] = fn()
    return out


if __name__ == "__main__":
    build(sys.argv[1:])
