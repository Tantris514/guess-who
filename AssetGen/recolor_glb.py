"""Hue-selective recolour of a GLB's base colour texture (TRELLIS sometimes drifts the hue of a material).

  V:/ComfyUI/ComfyUI/ComfyUI/.venv/Scripts/python.exe -I recolor_glb.py IN.glb OUT.glb --hue 12 --to 1 [--width 25]
        [--light 1.15] [--sat 1.0]
Pixels whose hue is within --width degrees of --hue (and that are saturated enough) are rotated to hue --to,
with lightness x --light and saturation x --sat; the weight fades smoothly to 0 at the edge of the hue window,
so other materials (wood, brass) stay as they are. Only the baseColor image of material 0 is changed.
"""
import argparse
import io
import json
import struct

import numpy as np
from PIL import Image


def read_glb(path):
    data = open(path, "rb").read()
    clen = struct.unpack_from("<I", data, 12)[0]
    gltf = json.loads(data[20:20 + clen])
    blen = struct.unpack_from("<I", data, 20 + clen)[0]
    binary = data[28 + clen:28 + clen + blen]
    return gltf, binary


def write_glb(path, gltf, views):
    """views: list of bytes, one per bufferView (in order); rebuilds the single buffer."""
    out = bytearray()
    for i, blob in enumerate(views):
        while len(out) % 4:
            out += b"\0"
        gltf["bufferViews"][i]["byteOffset"] = len(out)
        gltf["bufferViews"][i]["byteLength"] = len(blob)
        out += blob
    while len(out) % 4:
        out += b"\0"
    gltf["buffers"][0]["byteLength"] = len(out)
    js = json.dumps(gltf, separators=(",", ":")).encode("utf-8")
    while len(js) % 4:
        js += b" "
    total = 12 + 8 + len(js) + 8 + len(out)
    with open(path, "wb") as f:
        f.write(struct.pack("<III", 0x46546C67, 2, total))
        f.write(struct.pack("<II", len(js), 0x4E4F534A))
        f.write(js)
        f.write(struct.pack("<II", len(out), 0x004E4942))
        f.write(out)


def rgb_to_hls(a):
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    mx, mn = a.max(-1), a.min(-1)
    l = (mx + mn) / 2
    d = mx - mn
    s = np.where(d == 0, 0, d / np.maximum(1e-6, 1 - np.abs(2 * l - 1)))
    h = np.zeros_like(l)
    m = d > 0
    rc = np.where(m, (mx - r) / np.maximum(d, 1e-6), 0)
    gc = np.where(m, (mx - g) / np.maximum(d, 1e-6), 0)
    bc = np.where(m, (mx - b) / np.maximum(d, 1e-6), 0)
    h = np.where(r == mx, bc - gc, np.where(g == mx, 2 + rc - bc, 4 + gc - rc))
    h = (h / 6.0) % 1.0
    return h * 360, l, np.clip(s, 0, 1)


def hls_to_rgb(h, l, s):
    c = (1 - np.abs(2 * l - 1)) * s
    hp = (h % 360) / 60
    x = c * (1 - np.abs(hp % 2 - 1))
    z = np.zeros_like(h)
    conds = [(hp < 1), (hp < 2), (hp < 3), (hp < 4), (hp < 5), (hp <= 6)]
    choices = [np.stack([c, x, z], -1), np.stack([x, c, z], -1), np.stack([z, c, x], -1),
               np.stack([z, x, c], -1), np.stack([x, z, c], -1), np.stack([c, z, x], -1)]
    rgb = np.select([cnd[..., None] for cnd in conds], choices)
    return rgb + (l - c / 2)[..., None]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("src")
    p.add_argument("dst")
    p.add_argument("--hue", type=float, required=True)
    p.add_argument("--to", type=float, required=True)
    p.add_argument("--width", type=float, default=25)
    p.add_argument("--light", type=float, default=1.0)
    p.add_argument("--sat", type=float, default=1.0)
    p.add_argument("--minsat", type=float, default=0.12, help="texels less saturated than this are left alone")
    p.add_argument("--even", type=float, default=0.0, help="0..1: pull lightness of affected texels toward their median (removes blotches)")
    a = p.parse_args()
    gltf, binary = read_glb(a.src)
    views = [binary[v.get("byteOffset", 0):v.get("byteOffset", 0) + v["byteLength"]] for v in gltf["bufferViews"]]
    tex_index = gltf["materials"][0]["pbrMetallicRoughness"]["baseColorTexture"]["index"]
    img_index = gltf["textures"][tex_index]["source"]
    bv = gltf["images"][img_index]["bufferView"]
    im = Image.open(io.BytesIO(views[bv]))
    mode = im.mode
    arr = np.asarray(im.convert("RGBA")).astype(np.float64) / 255.0
    rgb = arr[..., :3]
    h, l, s = rgb_to_hls(rgb)
    dh = np.abs(((h - a.hue) + 180) % 360 - 180)
    w = np.clip(1 - dh / a.width, 0, 1) ** 0.5 * np.clip((s - a.minsat) / 0.10, 0, 1)
    h2 = h + (((a.to - a.hue) + 180) % 360 - 180) * w
    l2 = l * (1 + (a.light - 1) * w)
    if a.even > 0:
        sel = w > 0.5
        med = float(np.median(l2[sel])) if sel.any() else 0.5
        l2 = l2 + (med - l2) * a.even * w
    s2 = np.clip(s * (1 + (a.sat - 1) * w), 0, 1)
    out = np.clip(hls_to_rgb(h2, np.clip(l2, 0, 1), s2), 0, 1)
    arr[..., :3] = out
    res = Image.fromarray((arr * 255 + 0.5).astype(np.uint8), "RGBA")
    if mode != "RGBA":
        res = res.convert("RGB")
    buf = io.BytesIO()
    res.save(buf, "PNG")
    views[bv] = buf.getvalue()
    write_glb(a.dst, gltf, views)
    print("recoloured", a.dst, "affected %.1f%% of texels" % (100 * (w > 0.05).mean()))


if __name__ == "__main__":
    main()
