"""Paint a detail of the approved front image (a lace mask, a jewel) back onto a character GLB's base-colour texture.

  V:/ComfyUI/ComfyUI/ComfyUI/.venv/Scripts/python.exe -I project_front_tex.py IN.glb FRONT.png FRONT_MASK.png OUT.glb
        --region "EXPR" [--rows 0:330] [--close 7] [--grow 3] [--min-nz 0.35]
Pixal3D turns fine detail into shading: a gold filigree mask came out as dark eye blobs ("sunglasses"). The front
image and the mesh share the template camera (orthographic, front = glTF +Z), so the mesh is fitted onto the image's
silhouette (FRONT_MASK: scale from the bounding boxes, then a small IoU search on shift and scale), and every texel of
a front-facing triangle (normal z >= --min-nz) whose projection lands in the image region takes the image's colour,
blended in over normal z 0.35-0.65. The region: pixels where EXPR holds (H in degrees, L, S of the image), within rows
--rows of the image (e.g. above the neck, so gold embroidery on a jacket is left alone), closed by --close px (the
lace's holes show the eyes and skin behind it, which are taken from the image too) and grown by --grow px.
"""
import argparse
import io
import json
import struct

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

p = argparse.ArgumentParser()
p.add_argument("src")
p.add_argument("front")
p.add_argument("front_mask")
p.add_argument("out")
p.add_argument("--region", required=True)
p.add_argument("--rows", default="0:330")
p.add_argument("--close", type=int, default=7)
p.add_argument("--grow", type=int, default=3)
p.add_argument("--min-nz", type=float, default=0.35)
a = p.parse_args()


def load(path):
    b = open(path, "rb").read()
    jl = struct.unpack_from("<I", b, 12)[0]
    g = json.loads(b[20:20 + jl])
    bl = struct.unpack_from("<I", b, 20 + jl)[0]
    return g, bytearray(b[28 + jl:28 + jl + bl])


def view(g, binb, i):
    bv = g["bufferViews"][i]
    o = bv.get("byteOffset", 0)
    return binb[o:o + bv["byteLength"]]


def accessor(g, binb, i):
    ac = g["accessors"][i]
    bv = g["bufferViews"][ac["bufferView"]]
    o = bv.get("byteOffset", 0) + ac.get("byteOffset", 0)
    n = {"SCALAR": 1, "VEC2": 2, "VEC3": 3}[ac["type"]]
    dt = {5126: np.float32, 5125: np.uint32, 5123: np.uint16}[ac["componentType"]]
    arr = np.frombuffer(bytes(binb[o:o + ac["count"] * n * np.dtype(dt).itemsize]), dt)
    return arr.reshape(-1, n) if n > 1 else arr


def hls(rgb):
    """rgb float 0-1 (..., 3) -> H degrees, L, S (colorsys conventions)."""
    mx, mn = rgb.max(-1), rgb.min(-1)
    L = (mx + mn) / 2
    d = mx - mn
    S = np.where(d == 0, 0, d / np.maximum(np.where(L < 0.5, mx + mn, 2 - mx - mn), 1e-9))
    r, g_, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    dd = np.where(d == 0, 1, d)
    h = np.where(mx == r, (g_ - b) / dd % 6, np.where(mx == g_, (b - r) / dd + 2, (r - g_) / dd + 4))
    return np.where(d == 0, 0, h * 60), L, S


g, binb = load(a.src)
prim = g["meshes"][0]["primitives"][0]
pos = accessor(g, binb, prim["attributes"]["POSITION"]).astype(np.float64)
uv = accessor(g, binb, prim["attributes"]["TEXCOORD_0"]).astype(np.float64)
idx = accessor(g, binb, prim["indices"]).astype(np.int64).reshape(-1, 3)

img = np.asarray(Image.open(a.front).convert("RGB")).astype(np.float64) / 255
fig = np.asarray(Image.open(a.front_mask).convert("L").resize(img.shape[1::-1])) > 127
IH, IW = fig.shape

# fit: image px = cx + x * k, cy - y * k (glTF units); start from the bounding boxes, refine by IoU
ys, xs = np.where(fig)
k0 = (ys.max() - ys.min()) / (pos[:, 1].max() - pos[:, 1].min())
lo_v = pos[:, 1] < pos[:, 1].min() + 0.6 * (pos[:, 1].max() - pos[:, 1].min())
low = fig[int(ys.min() + 0.4 * (ys.max() - ys.min())):]
lx = np.where(low.any(0))[0]
cx0 = (lx.min() + lx.max()) / 2 - k0 * (pos[lo_v, 0].min() + pos[lo_v, 0].max()) / 2
cy0 = ys.max() + k0 * pos[:, 1].min()
sub = idx[:: max(1, len(idx) // 12000)]


def sil(k, cx, cy):
    im = Image.new("L", (IW, IH), 0)
    d = ImageDraw.Draw(im)
    px, py = cx + pos[:, 0] * k, cy - pos[:, 1] * k
    for t in sub:
        d.polygon([(px[j], py[j]) for j in t], fill=255)
    return np.asarray(im) > 0


def iou(k, cx, cy):
    m = sil(k, cx, cy)
    return (m & fig).sum() / (m | fig).sum()


best = (iou(k0, cx0, cy0), k0, cx0, cy0)
for step in (4, 2, 1):
    improved = True
    while improved:
        improved = False
        _, k, cx, cy = best
        for dk, dx, dy in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
            k1 = k * (1 + dk * step * 0.005)
            cand = (iou(k1, cx + dx * step, cy + dy * step), k1, cx + dx * step, cy + dy * step)
            if cand[0] > best[0] + 1e-4:
                best, improved = cand, True
fit_iou, k, cx, cy = best

# image region
Hd, L, S = hls(img)
region = np.asarray(eval(a.region, {"__builtins__": {}}, {"np": np, "H": Hd, "L": L, "S": S}), bool) & fig
r0, r1 = (int(x) for x in a.rows.split(":"))
region[:r0] = False
region[r1:] = False
rim = Image.fromarray((region * 255).astype(np.uint8))
if a.close:
    rim = rim.filter(ImageFilter.MaxFilter(a.close | 1)).filter(ImageFilter.MinFilter(a.close | 1))
if a.grow:
    rim = rim.filter(ImageFilter.MaxFilter(2 * a.grow + 1))
region = (np.asarray(rim) > 0) & fig

# texels of front-facing triangles whose projection lands in the region
nrm = np.cross(pos[idx[:, 1]] - pos[idx[:, 0]], pos[idx[:, 2]] - pos[idx[:, 0]])
nz = nrm[:, 2] / np.maximum(np.linalg.norm(nrm, axis=1), 1e-12)
cen = pos[idx].mean(1)
cpx, cpy = (cx + cen[:, 0] * k).round().astype(int), (cy - cen[:, 1] * k).round().astype(int)
inside = (cpx >= 0) & (cpx < IW) & (cpy >= 0) & (cpy < IH)
near = np.zeros(len(idx), bool)
rg = np.asarray(Image.fromarray((region * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(9))) > 0
near[inside] = rg[cpy[inside], cpx[inside]]
tris = np.where(near & (nz >= a.min_nz))[0]

ti = g["materials"][0]["pbrMetallicRoughness"]["baseColorTexture"]["index"]
bvi = g["images"][g["textures"][ti]["source"]]["bufferView"]
tex = Image.open(io.BytesIO(bytes(view(g, binb, bvi))))
mode = tex.mode
T = np.asarray(tex.convert("RGB")).astype(np.float64) / 255
TH, TW, _ = T.shape
painted = 0
for t in tris:
    tuv = uv[idx[t]] * [TW, TH]
    x0, y0 = np.floor(tuv.min(0)).astype(int)
    x1, y1 = np.ceil(tuv.max(0)).astype(int)
    gx, gy = np.meshgrid(np.arange(max(x0, 0), min(x1 + 1, TW)), np.arange(max(y0, 0), min(y1 + 1, TH)))
    q = np.stack([gx.ravel() + 0.5, gy.ravel() + 0.5], 1)
    A, B, C = tuv
    den = (B[1] - C[1]) * (A[0] - C[0]) + (C[0] - B[0]) * (A[1] - C[1])
    if abs(den) < 1e-12:
        continue
    w0 = ((B[1] - C[1]) * (q[:, 0] - C[0]) + (C[0] - B[0]) * (q[:, 1] - C[1])) / den
    w1 = ((C[1] - A[1]) * (q[:, 0] - C[0]) + (A[0] - C[0]) * (q[:, 1] - C[1])) / den
    w2 = 1 - w0 - w1
    ok = (w0 >= -0.02) & (w1 >= -0.02) & (w2 >= -0.02)
    if not ok.any():
        continue
    P = w0[ok, None] * pos[idx[t, 0]] + w1[ok, None] * pos[idx[t, 1]] + w2[ok, None] * pos[idx[t, 2]]
    ix, iy = (cx + P[:, 0] * k).astype(int), (cy - P[:, 1] * k).astype(int)
    vis = (ix >= 0) & (ix < IW) & (iy >= 0) & (iy < IH)
    ix, iy = ix[vis], iy[vis]
    inr = region[iy, ix]
    if not inr.any():
        continue
    tx, ty = gx.ravel()[ok][vis][inr], gy.ravel()[ok][vis][inr]
    wb = np.clip((nz[t] - 0.35) / 0.3, 0, 1)
    T[ty, tx] = (1 - wb) * T[ty, tx] + wb * img[iy[inr], ix[inr]]
    painted += len(tx)

data_img = Image.fromarray((T * 255).round().astype(np.uint8), "RGB").convert(mode)
buf = io.BytesIO()
data_img.save(buf, "PNG")
data = buf.getvalue()
binb += b"\0" * ((-len(binb)) % 4)
g["bufferViews"][bvi] = {"buffer": 0, "byteOffset": len(binb), "byteLength": len(data)}
binb += data
binb += b"\0" * ((-len(binb)) % 4)
g["buffers"][0]["byteLength"] = len(binb)
js = json.dumps(g, separators=(",", ":")).encode()
js += b" " * ((-len(js)) % 4)
out = struct.pack("<III", 0x46546C67, 2, 12 + 8 + len(js) + 8 + len(binb)) + struct.pack("<II", len(js), 0x4E4F534A) + js + \
    struct.pack("<II", len(binb), 0x004E4942) + bytes(binb)
open(a.out, "wb").write(out)
print(json.dumps({"fit_iou": round(float(fit_iou), 4), "px_per_unit": round(float(k), 2), "region_px": int(region.sum()),
                  "triangles": int(len(tris)), "texels_painted": int(painted), "out": a.out}))
