"""Replace large, solid pure-white patches of a GLB base colour (glass that TRELLIS baked as white) with a dark
glass tone. Small or ring-shaped white areas (dials, highlights) are kept.

  V:/ComfyUI/ComfyUI/ComfyUI/.venv/Scripts/python.exe -I fill_white_glb.py IN.glb OUT.glb [--min-area 3000] [--rgb 0.10,0.06,0.04]
"""
import argparse
import io

import numpy as np
from PIL import Image
from scipy import ndimage

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from recolor_glb import read_glb, write_glb  # noqa: E402

p = argparse.ArgumentParser()
p.add_argument("src")
p.add_argument("dst")
p.add_argument("--min-area", type=int, default=3000)
p.add_argument("--fill", type=float, default=0.6, help="min area / bounding-box area (solid patches only)")
p.add_argument("--rgb", default="0.10,0.06,0.04")
a = p.parse_args()
gltf, binary = read_glb(a.src)
views = [binary[v.get("byteOffset", 0):v.get("byteOffset", 0) + v["byteLength"]] for v in gltf["bufferViews"]]
tex = gltf["materials"][0]["pbrMetallicRoughness"]["baseColorTexture"]["index"]
bv = gltf["images"][gltf["textures"][tex]["source"]]["bufferView"]
im = Image.open(io.BytesIO(views[bv]))
mode = im.mode
arr = np.asarray(im.convert("RGBA")).astype(np.float64) / 255.0
white = arr[..., :3].min(-1) > 0.88
white = ndimage.binary_dilation(white, iterations=2)
lab, n = ndimage.label(white)
target = np.array([float(x) for x in a.rgb.split(",")])
changed = 0
for i, sl in enumerate(ndimage.find_objects(lab), start=1):
    comp = lab[sl] == i
    area = comp.sum()
    if area < a.min_area or area / comp.size < a.fill:
        continue
    h = comp.shape[0]
    shade = (0.8 + 0.4 * np.linspace(1, 0, h))[:, None, None]       # a little vertical gradient
    region = arr[sl]
    region[..., :3] = np.where(comp[..., None], target * shade, region[..., :3])
    changed += area
out = Image.fromarray((np.clip(arr, 0, 1) * 255 + 0.5).astype(np.uint8), "RGBA")
if mode != "RGBA":
    out = out.convert("RGB")
buf = io.BytesIO()
out.save(buf, "PNG")
views[bv] = buf.getvalue()
write_glb(a.dst, gltf, views)
print("filled", changed, "texels in", a.dst)
