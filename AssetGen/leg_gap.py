"""Where are the legs separate? Horizontal slices of a character GLB (height-scaled to HEIGHT_CM, feet at 0):
for each height, the mesh cross-section (edge crossings rasterised on a 1 cm grid) is split into connected parts,
and the parts within 25 cm of the centre line are counted (2 = two separate legs; 1 = fused or covered by a skirt/coat).

  python -I leg_gap.py GLB HEIGHT_CM [scale_override]
"""
import json
import os
import sys

import numpy as np
from scipy import ndimage

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import glb_mesh  # noqa: E402

g, v = glb_mesh.load(sys.argv[1])
prim, pos, idx, uv = glb_mesh.mesh(g, v)
lo, hi = pos.min(0), pos.max(0)
s = float(sys.argv[3]) if len(sys.argv) > 3 else float(sys.argv[2]) / (hi[1] - lo[1])
p = (pos - [(lo[0] + hi[0]) / 2, lo[1], (lo[2] + hi[2]) / 2]) * s
edges = np.concatenate([idx[:, [0, 1]], idx[:, [1, 2]], idx[:, [2, 0]]])
a, b = p[edges[:, 0]], p[edges[:, 1]]
rows = []
for h in range(4, 96, 2):
    m = (a[:, 1] - h) * (b[:, 1] - h) < 0
    t = (h - a[m, 1]) / (b[m, 1] - a[m, 1])
    pts = a[m] + (b[m] - a[m]) * t[:, None]
    near = np.abs(pts[:, 0]) < 25
    pts = pts[near]
    grid = np.zeros((60, 80), bool)
    gx = np.clip((pts[:, 0] + 30).astype(int), 0, 59)
    gz = np.clip((pts[:, 2] + 40).astype(int), 0, 79)
    grid[gx, gz] = True
    grid = ndimage.binary_dilation(grid, iterations=1)
    grid = ndimage.binary_fill_holes(grid)
    lab, n = ndimage.label(grid)
    sizes = ndimage.sum(grid, lab, range(1, n + 1)) if n else []
    parts = int(sum(1 for z in sizes if z >= 6))
    # gap between parts along x (cm)
    gap = None
    if parts >= 2:
        xs = np.where(grid.any(1))[0]
        holes = np.where(np.diff(xs) > 1)[0]
        gap = int(max(np.diff(xs)[holes]) - 1) if len(holes) else 0
    rows.append((h, parts, gap))
sep = [h for h, n, _ in rows if n >= 2]
print(json.dumps({"scale": round(s, 3), "separate_leg_heights_cm": [min(sep), max(sep)] if sep else None,
                  "slices": [f"{h}cm:{n}" + (f"(gap {gp})" if gp else "") for h, n, gp in rows]}))
