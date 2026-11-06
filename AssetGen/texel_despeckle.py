"""Texel-level clean-up of light specks on dark fabric in a GLB's base colour, inside one body region.

  V:/ComfyUI/ComfyUI/ComfyUI/.venv/Scripts/python.exe -I texel_despeckle.py IN.glb OUT.glb --where "fy < 0.5"
        [--bright 0.33] [--size 11] [--passes 3]
despeckle_glb.py samples one colour per triangle, so specks smaller than a triangle (the white cut-out halo baked
in rows along UV chart borders, seen as dotted lines down Monsieur Minuit's trousers) survive it. Here the
triangles selected by --where (fx, fy, fz normalised positions, ax = |x| from the centre, as in despeckle_glb.py)
are rasterised in UV space; inside that footprint every texel brighter than --bright is replaced by the mean
colour of the dark texels in a --size x --size window around it, repeated --passes times so wider blobs fill
from their edges. Only use it where no light colour belongs (legs of dark trousers, a dark coat).
"""
import argparse
import io
import json
import struct

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

p = argparse.ArgumentParser()
p.add_argument("src")
p.add_argument("dst")
p.add_argument("--where", required=True)
p.add_argument("--bright", type=float, default=0.33)
p.add_argument("--size", type=int, default=11)
p.add_argument("--passes", type=int, default=3)
a = p.parse_args()

b = open(a.src, "rb").read()
jl = struct.unpack_from("<I", b, 12)[0]
g = json.loads(b[20:20 + jl])
bl = struct.unpack_from("<I", b, 20 + jl)[0]
binb = bytearray(b[28 + jl:28 + jl + bl])


def accessor(i):
    ac = g["accessors"][i]
    bv = g["bufferViews"][ac["bufferView"]]
    o = bv.get("byteOffset", 0) + ac.get("byteOffset", 0)
    n = {"SCALAR": 1, "VEC2": 2, "VEC3": 3}[ac["type"]]
    dt = {5126: np.float32, 5125: np.uint32, 5123: np.uint16}[ac["componentType"]]
    arr = np.frombuffer(bytes(binb[o:o + ac["count"] * n * np.dtype(dt).itemsize]), dt)
    return arr.reshape(-1, n) if n > 1 else arr


prim = g["meshes"][0]["primitives"][0]
pos = accessor(prim["attributes"]["POSITION"]).astype(np.float64)
uv = accessor(prim["attributes"]["TEXCOORD_0"]).astype(np.float64)
idx = accessor(prim["indices"]).astype(np.int64).reshape(-1, 3)
cen = pos[idx].mean(axis=1)
lo, hi = pos.min(0), pos.max(0)
span = np.maximum(hi - lo, 1e-9)
env = {"np": np, "fx": (cen[:, 0] - lo[0]) / span[0], "fy": (cen[:, 1] - lo[1]) / span[1],
       "fz": (cen[:, 2] - lo[2]) / span[2], "ax": np.abs(cen[:, 0] - (lo[0] + hi[0]) / 2) / (span[0] / 2)}
sel = np.asarray(eval(a.where, {"__builtins__": {}}, env), bool)
ti = g["materials"][0]["pbrMetallicRoughness"]["baseColorTexture"]["index"]
bvi = g["images"][g["textures"][ti]["source"]]["bufferView"]
bv = g["bufferViews"][bvi]
im = Image.open(io.BytesIO(bytes(binb[bv.get("byteOffset", 0):bv.get("byteOffset", 0) + bv["byteLength"]])))
mode = im.mode
W, H = im.size
mask = Image.new("L", (W, H), 0)
d = ImageDraw.Draw(mask)
for t in np.where(sel)[0]:
    d.polygon([(float(u * W), float(v * H)) for u, v in uv[idx[t]]], fill=255, outline=255)
region = ndimage.binary_dilation(np.asarray(mask) > 0, iterations=1)
arr = np.asarray(im.convert("RGBA" if mode == "RGBA" else "RGB")).astype(np.float32) / 255.0
rgb = arr[..., :3]
fixed_total = 0
for _ in range(a.passes):
    lum = rgb.mean(-1)
    bad = region & (lum > a.bright)
    if not bad.any():
        break
    good = (~bad).astype(np.float32) * (lum <= a.bright)
    num = np.stack([ndimage.uniform_filter(rgb[..., c] * good, a.size) for c in range(3)], -1)
    den = ndimage.uniform_filter(good, a.size)[..., None]
    ok = bad & (den[..., 0] > 0.05)
    rgb[ok] = num[ok] / den[ok]
    fixed_total += int(ok.sum())
arr[..., :3] = rgb
out_img = Image.fromarray(np.clip(arr * 255 + 0.5, 0, 255).astype(np.uint8), "RGBA" if arr.shape[-1] == 4 else "RGB").convert(mode)
buf = io.BytesIO()
out_img.save(buf, "PNG")
data = buf.getvalue()
binb += b"\0" * ((-len(binb)) % 4)
g["bufferViews"][bvi] = {"buffer": 0, "byteOffset": len(binb), "byteLength": len(data)}
binb += data
binb += b"\0" * ((-len(binb)) % 4)
g["buffers"][0]["byteLength"] = len(binb)
js = json.dumps(g, separators=(",", ":")).encode()
js += b" " * ((-len(js)) % 4)
open(a.dst, "wb").write(struct.pack("<III", 0x46546C67, 2, 12 + 8 + len(js) + 8 + len(binb)) + struct.pack("<II", len(js), 0x4E4F534A) + js
                       + struct.pack("<II", len(binb), 0x004E4942) + bytes(binb))
print(json.dumps({"region_tris": int(sel.sum()), "region_texels": int(region.sum()), "texels_fixed": fixed_total,
                  "left_bright": int((region & (rgb.mean(-1) > a.bright)).sum()), "out": a.dst}))
