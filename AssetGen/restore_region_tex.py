"""Restore the base-colour texels of one body region from another GLB of the same mesh (same UVs).

  V:/ComfyUI/ComfyUI/ComfyUI/.venv/Scripts/python.exe -I restore_region_tex.py FIXED.glb ORIGINAL.glb OUT.glb --where "EXPR"
despeckle_glb.py repaints each speckle's UV area + 1 px, which can bleed into a neighbouring UV chart (suit speckles
left blue slivers in the hair). The triangles selected by --where (same variables as despeckle_glb.py: fx, fy, fz
normalised positions, ax = |x| from the centre) are rasterised in UV space (dilated 2 px) and their texels are copied
back from ORIGINAL; everything else keeps FIXED's texels.
"""
import argparse
import io
import json
import struct

import numpy as np
from PIL import Image, ImageDraw

p = argparse.ArgumentParser()
p.add_argument("fixed")
p.add_argument("original")
p.add_argument("out")
p.add_argument("--where", required=True)
a = p.parse_args()


def load(path):
    b = open(path, "rb").read()
    jl = struct.unpack_from("<I", b, 12)[0]
    g = json.loads(b[20:20 + jl])
    bl = struct.unpack_from("<I", b, 20 + jl)[0]
    binb = bytearray(b[28 + jl:28 + jl + bl])
    return g, binb


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
    return np.frombuffer(bytes(binb[o:o + ac["count"] * n * np.dtype(dt).itemsize]), dt).reshape(-1, n) if n > 1 else \
        np.frombuffer(bytes(binb[o:o + ac["count"] * np.dtype(dt).itemsize]), dt)


g, binb = load(a.fixed)
g0, bin0 = load(a.original)
prim = g["meshes"][0]["primitives"][0]
pos = accessor(g, binb, prim["attributes"]["POSITION"]).astype(np.float64)
uv = accessor(g, binb, prim["attributes"]["TEXCOORD_0"]).astype(np.float64)
idx = accessor(g, binb, prim["indices"]).astype(np.int64).reshape(-1, 3)
cen = pos[idx].mean(axis=1)
lo, hi = pos.min(0), pos.max(0)
span = np.maximum(hi - lo, 1e-9)
env = {"np": np, "fx": (cen[:, 0] - lo[0]) / span[0], "fy": (cen[:, 1] - lo[1]) / span[1],
       "fz": (cen[:, 2] - lo[2]) / span[2], "ax": np.abs(cen[:, 0] - (lo[0] + hi[0]) / 2) / (span[0] / 2)}
sel = np.asarray(eval(a.where, {"__builtins__": {}}, env), bool)
ti = g["materials"][0]["pbrMetallicRoughness"]["baseColorTexture"]["index"]
img_i = g["textures"][ti]["source"]
bvi = g["images"][img_i]["bufferView"]
fixed = Image.open(io.BytesIO(bytes(view(g, binb, bvi))))
orig = Image.open(io.BytesIO(bytes(view(g0, bin0, g0["images"][img_i]["bufferView"]))))
mode = fixed.mode
W, H = fixed.size
mask = Image.new("L", (W, H), 0)
d = ImageDraw.Draw(mask)
for t in np.where(sel)[0]:
    d.polygon([(float(u * W), float(v * H)) for u, v in uv[idx[t]]], fill=255, outline=255)
m = np.asarray(mask) > 0
m = m | np.roll(m, 1, 0) | np.roll(m, -1, 0) | np.roll(m, 1, 1) | np.roll(m, -1, 1)
m = m | np.roll(m, 1, 0) | np.roll(m, -1, 0) | np.roll(m, 1, 1) | np.roll(m, -1, 1)
fa = np.asarray(fixed.convert(mode)).copy()
oa = np.asarray(orig.convert(mode))
changed = (fa != oa).any(-1) if fa.ndim == 3 else fa != oa
fa[m] = oa[m]
buf = io.BytesIO()
Image.fromarray(fa, mode).save(buf, "PNG")
data = buf.getvalue()
# rebuild the binary chunk with the new image appended (old image bytes left unreferenced)
pad = (-len(binb)) % 4
binb += b"\0" * pad
g["bufferViews"][bvi] = {"buffer": 0, "byteOffset": len(binb), "byteLength": len(data)}
binb += data
binb += b"\0" * ((-len(binb)) % 4)
g["buffers"][0]["byteLength"] = len(binb)
js = json.dumps(g, separators=(",", ":")).encode()
js += b" " * ((-len(js)) % 4)
out = struct.pack("<III", 0x46546C67, 2, 12 + 8 + len(js) + 8 + len(binb)) + struct.pack("<II", len(js), 0x4E4F534A) + js + \
    struct.pack("<II", len(binb), 0x004E4942) + bytes(binb)
open(a.out, "wb").write(out)
print(json.dumps({"region_tris": int(sel.sum()), "region_texels": int(m.sum()), "restored_changed_texels": int((changed & m).sum()),
                  "kept_changed_texels": int((changed & ~m).sum()), "out": a.out}))
