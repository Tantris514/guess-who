"""Remove bright speckles on dark fabric in a GLB's base colour (TRELLIS/Pixal3D bake artefacts), at triangle level.

  V:/ComfyUI/ComfyUI/ComfyUI/.venv/Scripts/python.exe -I despeckle_glb.py IN.glb OUT.glb [--dark 0.28] [--bright 0.45]
        [--frac 0.85] [--rings 2] [--where "EXPR"]
A triangle (colour sampled at its UV centroid) is a speckle when it is brighter than --bright while at least --frac of
the triangles within --rings rings around it (vertices welded by position, so UV seams do not cut the neighbourhood) are
darker than --dark. Its UV area (+1 px) is repainted with the median colour of those dark neighbours; its own texel
detail is kept at 30 % so the fabric grain does not go flat. Large bright areas (shirt fronts, stripes, buttons groups)
are not touched because their neighbourhood is not dark.
"""
import argparse
import io
import os
import sys

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage, sparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import glb_mesh  # noqa: E402

p = argparse.ArgumentParser()
p.add_argument("src")
p.add_argument("dst")
p.add_argument("--dark", type=float, default=0.28)
p.add_argument("--bright", type=float, default=0.45)
p.add_argument("--frac", type=float, default=0.85)
p.add_argument("--rings", type=int, default=2)
p.add_argument("--max-tris", type=int, default=80, help="bright clusters larger than this are real details")
p.add_argument("--where", default="")
p.add_argument("--dark-spots", action="store_true",
               help="inverse mode: remove small DARK clusters (lum < --dark) surrounded by light (lum > --bright), e.g. on hands")
a = p.parse_args()

g, v = glb_mesh.load(a.src)
prim, pos, idx, uv = glb_mesh.mesh(g, v)
tex = glb_mesh.base_color(g, v)
col = glb_mesh.tri_colors(tex, uv, idx)
lum = col.mean(1)
q = np.round(pos / max(np.ptp(pos), 1e-9) * 2e5).astype(np.int64)
_, weld = np.unique(q, axis=0, return_inverse=True)
weld = weld.ravel()
T = len(idx)
nv = weld.max() + 1
rows = np.repeat(np.arange(T), 3)
vt = sparse.csr_matrix((np.ones(3 * T, np.float32), (rows, weld[idx].ravel())), shape=(T, nv))
adj = (vt @ vt.T).astype(bool).astype(np.float32).tocsr()   # triangles sharing a welded vertex
bright = np.where(lum < a.dark)[0] if a.dark_spots else np.where(lum > a.bright)[0]
sub = adj[bright][:, bright]
ncomp, lab = sparse.csgraph.connected_components(sub, directed=False)
spk = np.zeros(T, bool)
targets = {}
for k in range(ncomp):
    comp = bright[lab == k]
    if len(comp) > a.max_tris:
        continue
    ring = np.unique(adj[comp].indices)
    for _ in range(a.rings - 1):
        ring = np.unique(adj[ring].indices)
    ring = np.setdiff1d(ring, comp)
    if len(ring) == 0:
        continue
    dk = ring[lum[ring] > a.bright] if a.dark_spots else ring[lum[ring] < a.dark]
    if len(dk) >= a.frac * len(ring):
        spk[comp] = True
        tgt = np.median(col[dk], axis=0)
        for t in comp:
            targets[t] = tgt
if a.where:
    cen = pos[idx].mean(axis=1)
    lo, hi = pos.min(0), pos.max(0)
    span = np.maximum(hi - lo, 1e-9)
    env = {"np": np, "fx": (cen[:, 0] - lo[0]) / span[0], "fy": (cen[:, 1] - lo[1]) / span[1], "fz": (cen[:, 2] - lo[2]) / span[2],
           "ax": np.abs(cen[:, 0] - (lo[0] + hi[0]) / 2) / (span[0] / 2)}
    spk &= np.asarray(eval(a.where, {"__builtins__": {}}, env), bool)
ti = g["materials"][0]["pbrMetallicRoughness"]["baseColorTexture"]["index"]
bv = g["images"][g["textures"][ti]["source"]]["bufferView"]
im = Image.open(io.BytesIO(v[bv]))
mode = im.mode
arr = np.asarray(im.convert("RGB")).astype(np.float32) / 255.0
h, w = arr.shape[:2]
# texel ownership: a speck triangle may only repaint texels that no other (non-speck) triangle drew last; Pixal3D
# atlases put charts edge to edge, so painting a triangle's polygon alone spilled onto neighbouring charts
# (dark marks on the aviatrix's jodhpurs, 2026-11-03)
own_im = Image.new("I", (w, h), -1)
own_dr = ImageDraw.Draw(own_im)
for t in range(len(idx)):
    own_dr.polygon([((uv[k, 0] % 1) * w, (uv[k, 1] % 1) * h) for k in idx[t]], fill=int(t))
own = np.asarray(own_im)
spk_own = np.zeros(own.shape, bool)
spk_own[own >= 0] = spk[own[own >= 0]]
for t in np.where(spk)[0]:
    target = targets[t]
    pts = [((uv[k, 0] % 1) * w, (uv[k, 1] % 1) * h) for k in idx[t]]
    xs, ys = [x for x, _ in pts], [y for _, y in pts]
    x0, y0 = max(int(min(xs)) - 2, 0), max(int(min(ys)) - 2, 0)
    x1, y1 = min(int(max(xs)) + 3, w), min(int(max(ys)) + 3, h)
    m = Image.new("L", (x1 - x0, y1 - y0), 0)
    ImageDraw.Draw(m).polygon([(x - x0, y - y0) for x, y in pts], fill=255)
    mk = (np.asarray(m) > 0) & spk_own[y0:y1, x0:x1]
    # no dilation: texels outside the triangle may belong to other UV charts (hair specks otherwise)
    reg = arr[y0:y1, x0:x1]
    detail = reg - reg.mean(axis=(0, 1), keepdims=True)
    reg[mk] = np.clip(target + 0.3 * detail[mk], 0, 1)
out = Image.fromarray((np.clip(arr, 0, 1) * 255 + 0.5).astype(np.uint8))
if mode == "RGBA":
    out = out.convert("RGBA")
buf = io.BytesIO()
out.save(buf, "PNG")
v[bv] = buf.getvalue()
glb_mesh.save(a.dst, g, v)
print(f"despeckled {int(spk.sum())} triangles of {T} -> {a.dst}")
