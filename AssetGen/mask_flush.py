"""Measure (and optionally reduce) how far a face mask stands off the face on a character GLB.

  V:/ComfyUI/ComfyUI/ComfyUI/.venv/Scripts/python.exe -I mask_flush.py IN.glb HEIGHT_CM --mask "EXPR" [--skin "EXPR"]
        [--out OUT.glb --max-cm 0.6]
Head = top 14 % of the mesh, front half. Mask / skin triangles are chosen by colour expressions over H (deg), L, S of the
base colour at the triangle's UV centroid (e.g. --mask "L < 0.18"). The face surface under the mask is estimated by a
smooth thin-plate fit z(x, y) through the skin vertices around it; protrusion = mask vertex z - face z (cm, glTF +Z front).
With --out, mask vertices are pulled back so that no part stands more than --max-cm in front of the face (the mask keeps
its shape, compressed in depth only); vertices of other parts are untouched.
"""
import argparse
import colorsys
import json
import os
import sys

import numpy as np
from scipy.interpolate import RBFInterpolator

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import glb_mesh  # noqa: E402

p = argparse.ArgumentParser()
p.add_argument("src")
p.add_argument("height", type=float)
p.add_argument("--mask", required=True)
p.add_argument("--skin", default="(H < 40) & (L > 0.35) & (L < 0.85) & (S > 0.15)")
p.add_argument("--out", default="")
p.add_argument("--max-cm", type=float, default=0.6)
a = p.parse_args()

g, v = glb_mesh.load(a.src)
prim, pos, idx, uv = glb_mesh.mesh(g, v)
lo, hi = pos.min(0), pos.max(0)
s = a.height / (hi[1] - lo[1])
col = glb_mesh.tri_colors(glb_mesh.base_color(g, v), uv, idx)
hls = np.array([colorsys.rgb_to_hls(*c) for c in col])
env = {"np": np, "H": hls[:, 0] * 360, "L": hls[:, 1], "S": hls[:, 2]}
cen = pos[idx].mean(1)
fy = (cen[:, 1] - lo[1]) / (hi[1] - lo[1])
head_y0 = lo[1] + 0.86 * (hi[1] - lo[1])
hv = pos[:, 1] > head_y0
hz = pos[hv, 2]
zmid = (hz.min() + hz.max()) / 2
head = (fy > 0.86) & (cen[:, 2] > zmid)
mask_t = head & np.asarray(eval(a.mask, {"__builtins__": {}}, env), bool)
skin_t = head & np.asarray(eval(a.skin, {"__builtins__": {}}, env), bool)
mv = np.unique(idx[mask_t])
sv = np.unique(idx[skin_t])
if len(mv) < 10 or len(sv) < 30:
    raise SystemExit(f"too few mask ({len(mv)}) or skin ({len(sv)}) vertices: check the colour expressions")
# skin vertices near the mask (within the mask's x/y bounding box grown by 40 %)
mx0, my0 = pos[mv, 0].min(), pos[mv, 1].min()
mx1, my1 = pos[mv, 0].max(), pos[mv, 1].max()
gx, gy = 0.4 * (mx1 - mx0), 0.6 * (my1 - my0)
near = sv[(pos[sv, 0] > mx0 - gx) & (pos[sv, 0] < mx1 + gx) & (pos[sv, 1] > my0 - gy) & (pos[sv, 1] < my1 + gy)]
# keep only the front-most skin per small (x, y) cell (the face, not the inside of the head)
cell = np.round(pos[near, :2] / ((mx1 - mx0) / 40)).astype(int)
order = np.lexsort((-pos[near, 2], cell[:, 1], cell[:, 0]))
_, first = np.unique(cell[order], axis=0, return_index=True)
face_pts = near[order][first]
rbf = RBFInterpolator(pos[face_pts, :2], pos[face_pts, 2], kernel="thin_plate_spline", smoothing=1e-4)
face_z = rbf(pos[mv, :2])
prot = (pos[mv, 2] - face_z) * s
res = {"mask_tris": int(mask_t.sum()), "skin_ref_points": int(len(face_pts)),
       "protrusion_cm": {f"p{q}": round(float(np.percentile(prot, q)), 2) for q in (50, 90, 99)},
       "mask_size_cm": [round(float((mx1 - mx0) * s), 1), round(float((my1 - my0) * s), 1)]}
if a.out:
    newp = pos.copy()
    lim = a.max_cm / s
    d = pos[mv, 2] - face_z
    over = d > 0
    dmax = max(float(np.percentile(d[over], 99)), lim) if over.any() else lim
    # compress depth in front of the face so the 99th percentile lands at max-cm, keep everything behind as is
    newd = np.where(over, d * (lim / dmax), d)
    newp[mv, 2] = face_z + newd
    acc = g["accessors"][prim["attributes"]["POSITION"]]
    arr = glb_mesh.accessor(g, v, prim["attributes"]["POSITION"]).copy()
    arr[:] = newp.astype(np.float32)
    v[acc["bufferView"]] = np.ascontiguousarray(arr).tobytes()
    acc["byteOffset"] = 0
    acc["min"] = arr.min(0).astype(float).tolist()
    acc["max"] = arr.max(0).astype(float).tolist()
    glb_mesh.save(a.out, g, v)
    prot2 = newd * s
    res["after_protrusion_cm"] = {f"p{q}": round(float(np.percentile(prot2, q)), 2) for q in (50, 90, 99)}
    res["out"] = a.out
print(json.dumps(res))
