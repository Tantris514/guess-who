"""Remove hanging sleeves (and anything else) from a TRELLIS coat on a dress form, using the arm axes.

  V:/ComfyUI/ComfyUI/ComfyUI/.venv/Scripts/python.exe -I sleeve_cut.py IN.glb OUT.glb --band 0.42,0.74 --shoulder 0.86
        [--radius 1.25] [--drop EXPR ...]
For each side, the sleeve centre (x, z) is measured in horizontal slices inside --band (points beyond the torso:
|x| > 0.75 * slice half-width), a straight arm axis is fitted and extended up to --shoulder; triangles whose centroid
lies within radius * (measured sleeve radius) of that axis, between the cuff and the shoulder, are removed.
Extra --drop expressions (glb_mesh.cut syntax) are applied too, then the largest connected piece is kept.
"""
import argparse
import json
import os
import subprocess
import sys

import numpy as np

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
import glb_mesh  # noqa: E402

p = argparse.ArgumentParser()
p.add_argument("src")
p.add_argument("dst")
p.add_argument("--band", default="0.42,0.74")
p.add_argument("--shoulder", type=float, default=0.86)
p.add_argument("--radius", type=float, default=1.25)
p.add_argument("--drop", action="append", default=[])
a = p.parse_args()

g, v = glb_mesh.load(a.src)
prim, pos, idx, uv = glb_mesh.mesh(g, v)
lo, hi = pos.min(0), pos.max(0)
fy_v = (pos[:, 1] - lo[1]) / (hi[1] - lo[1])
b0, b1 = (float(x) for x in a.band.split(","))
axes = {}
for side in (-1, 1):
    rows = []
    for f in np.arange(b0, b1, 0.02):
        m = np.abs(fy_v - f) < 0.01
        if m.sum() < 30:
            continue
        x = pos[m, 0]
        half = np.abs(x).max()
        s = m.copy()
        s[m] = (np.sign(x) == side) & (np.abs(x) > 0.75 * half)
        if s.sum() < 10:
            continue
        sx, sz = pos[s, 0], pos[s, 2]
        r = max(np.ptp(sx), np.ptp(sz)) / 2
        rows.append((f, sx.mean(), sz.mean(), r))
    rows = np.array(rows)
    kx = np.polyfit(rows[:, 0], rows[:, 1], 1)
    kz = np.polyfit(rows[:, 0], rows[:, 2], 1)
    radius = float(np.median(rows[:, 3]))
    axes[side] = (kx, kz, radius)
    print("side", side, "x(fy)", kx.round(3), "z(fy)", kz.round(3), "sleeve radius", round(radius, 3), "slices", len(rows))

cen = pos[idx].mean(axis=1)
fy = (cen[:, 1] - lo[1]) / (hi[1] - lo[1])
expr = []
for side, (kx, kz, r) in axes.items():
    ax = np.polyval(kx, fy)
    az = np.polyval(kz, fy)
    d = np.hypot(cen[:, 0] - ax, cen[:, 2] - az)
    hit = (d < a.radius * r) & (fy > b0 - 0.06) & (fy < a.shoulder) & (np.sign(cen[:, 0]) == side)
    expr.append(hit)
sleeve = expr[0] | expr[1]
print("sleeve triangles", int(sleeve.sum()), "of", len(idx))
mask_path = a.dst + ".sleeve.npy"
np.save(mask_path, sleeve)
cmd = [sys.executable, "-I", os.path.join(ROOT, "glb_mesh.py"), "cut", a.src, a.dst, "--keep-largest", "1",
       "--drop", f"np.load(r'{mask_path}')"]
for e in a.drop:
    cmd += ["--drop", e]
subprocess.run(cmd, check=True)
os.remove(mask_path)
