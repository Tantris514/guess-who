"""Small GLB mesh toolkit for TRELLIS outputs (one mesh, one primitive, float attributes, uint32 indices).

  cut:     glb_mesh.py cut IN.glb OUT.glb --drop "EXPR" [--drop "EXPR" ...] [--keep-largest N]
           Removes triangles whose centroid matches any EXPR (numpy expression over per-triangle arrays):
             x y z      centroid (glTF units, Y up)        fx fy fz  same as 0..1 fractions of the bounding box
             ax         |x - centre| / half-width (0 centre .. 1 side)
             L S H      lightness, saturation (0..1) and hue (deg) of the base colour at the centroid UV
           e.g. --drop "fy > 0.55"  (keep below 55% height)   --drop "(L > 0.75) & (S < 0.18)"  (white dress form)
           --keep-largest N keeps only the N biggest connected pieces (removes floating junk after a cut).
           Unused vertices are compacted away; textures/material are kept.
  render:  glb_mesh.py render IN.glb OUT.png [--size 360]
           Software QA render (orthographic, textured + lambert, front / back34 / side / top34 / under), any GLB.
"""
import argparse
import colorsys
import io
import json
import struct

import numpy as np
from PIL import Image, ImageDraw

DT = {5126: np.float32, 5125: np.uint32, 5123: np.uint16, 5121: np.uint8}
NC = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}


def load(path):
    data = open(path, "rb").read()
    clen = struct.unpack_from("<I", data, 12)[0]
    gltf = json.loads(data[20:20 + clen])
    blen = struct.unpack_from("<I", data, 20 + clen)[0]
    binary = data[28 + clen:28 + clen + blen]
    views = [binary[v.get("byteOffset", 0):v.get("byteOffset", 0) + v["byteLength"]] for v in gltf["bufferViews"]]
    return gltf, views


def accessor(gltf, views, i):
    acc = gltf["accessors"][i]
    raw = views[acc["bufferView"]]
    arr = np.frombuffer(raw, dtype=DT[acc["componentType"]], offset=acc.get("byteOffset", 0),
                        count=acc["count"] * NC[acc["type"]])
    return arr.reshape(acc["count"], NC[acc["type"]]) if NC[acc["type"]] > 1 else arr


def save(path, gltf, views):
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
    with open(path, "wb") as f:
        f.write(struct.pack("<III", 0x46546C67, 2, 12 + 8 + len(js) + 8 + len(out)))
        f.write(struct.pack("<II", len(js), 0x4E4F534A) + js)
        f.write(struct.pack("<II", len(out), 0x004E4942) + bytes(out))


def base_color(gltf, views):
    tex = gltf["materials"][0]["pbrMetallicRoughness"]["baseColorTexture"]["index"]
    bv = gltf["images"][gltf["textures"][tex]["source"]]["bufferView"]
    return np.asarray(Image.open(io.BytesIO(views[bv])).convert("RGB")).astype(np.float32) / 255.0


def mesh(gltf, views):
    prim = gltf["meshes"][0]["primitives"][0]
    pos = accessor(gltf, views, prim["attributes"]["POSITION"]).astype(np.float64)
    idx = accessor(gltf, views, prim["indices"]).astype(np.int64).reshape(-1, 3)
    uv = accessor(gltf, views, prim["attributes"]["TEXCOORD_0"]).astype(np.float64)
    return prim, pos, idx, uv


def tri_colors(tex, uv, idx):
    c = uv[idx].mean(axis=1)
    h, w = tex.shape[:2]
    px = np.clip((c[:, 0] % 1.0) * (w - 1), 0, w - 1).astype(int)
    py = np.clip((c[:, 1] % 1.0) * (h - 1), 0, h - 1).astype(int)
    return tex[py, px]


def components(idx, pos):
    """Connected component id per triangle. Vertices are welded by position first (UV seams split vertices)."""
    q = np.round(pos / max(np.ptp(pos), 1e-9) * 2e5).astype(np.int64)
    _, weld = np.unique(q, axis=0, return_inverse=True)
    weld = weld.ravel()
    tri = weld[idx]
    n = weld.max() + 1
    parent = np.arange(n)

    def find(a):
        root = a
        while parent[root] != root:
            root = parent[root]
        while parent[a] != root:
            parent[a], a = root, parent[a]
        return root
    for a, b, c in tri:
        ra, rb, rc = find(a), find(b), find(c)
        parent[rb] = ra
        parent[rc] = ra
    roots = np.array([find(v) for v in range(n)])
    return roots[tri[:, 0]]


def cut(a):
    gltf, views = load(a.src)
    prim, pos, idx, uv = mesh(gltf, views)
    tex = base_color(gltf, views)
    cen = pos[idx].mean(axis=1)
    lo, hi = pos.min(0), pos.max(0)
    span = np.maximum(hi - lo, 1e-9)
    col = tri_colors(tex, uv, idx)
    hls = np.array([colorsys.rgb_to_hls(*c) for c in col])
    env = {"np": np, "x": cen[:, 0], "y": cen[:, 1], "z": cen[:, 2],
           "fx": (cen[:, 0] - lo[0]) / span[0], "fy": (cen[:, 1] - lo[1]) / span[1], "fz": (cen[:, 2] - lo[2]) / span[2],
           "ax": np.abs(cen[:, 0] - (lo[0] + hi[0]) / 2) / (span[0] / 2),
           "H": hls[:, 0] * 360, "L": hls[:, 1], "S": hls[:, 2]}
    drop = np.zeros(len(idx), bool)
    for expr in a.drop:
        drop |= np.asarray(eval(expr, {"__builtins__": {}}, env), bool)
    keep = idx[~drop]
    if a.keep_largest:
        comp = components(keep, pos)
        ids, counts = np.unique(comp, return_counts=True)
        best = ids[np.argsort(-counts)[:a.keep_largest]]
        keep = keep[np.isin(comp, best)]
    used = np.unique(keep)
    remap = -np.ones(len(pos), np.int64)
    remap[used] = np.arange(len(used))
    new_idx = remap[keep].astype(np.uint32)
    for name, ai in prim["attributes"].items():
        arr = accessor(gltf, views, ai)[used]
        acc = gltf["accessors"][ai]
        views[acc["bufferView"]] = np.ascontiguousarray(arr).tobytes()
        acc["count"] = int(len(used))
        acc["byteOffset"] = 0
        if name == "POSITION":
            acc["min"] = arr.min(0).astype(float).tolist()
            acc["max"] = arr.max(0).astype(float).tolist()
    ia = gltf["accessors"][prim["indices"]]
    views[ia["bufferView"]] = new_idx.tobytes()
    ia["count"] = int(new_idx.size)
    ia["componentType"] = 5125
    ia["byteOffset"] = 0
    save(a.dst, gltf, views)
    print(f"kept {len(keep)}/{len(idx)} triangles, {len(used)} vertices -> {a.dst}")


def paint(a):
    """Repaint, in the base colour texture, the UV area of triangles matching --where (same variables as cut, plus
    nx ny nz = face normal) with --rgb, keeping a little of the original luminance variation (--keep)."""
    gltf, views = load(a.src)
    prim, pos, idx, uv = mesh(gltf, views)
    tri = pos[idx]
    n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)
    cen = tri.mean(axis=1)
    lo, hi = pos.min(0), pos.max(0)
    span = np.maximum(hi - lo, 1e-9)
    env = {"np": np, "nx": n[:, 0], "ny": n[:, 1], "nz": n[:, 2],
           "fx": (cen[:, 0] - lo[0]) / span[0], "fy": (cen[:, 1] - lo[1]) / span[1], "fz": (cen[:, 2] - lo[2]) / span[2],
           "ax": np.abs(cen[:, 0] - (lo[0] + hi[0]) / 2) / (span[0] / 2),
           "az": np.abs(cen[:, 2] - (lo[2] + hi[2]) / 2) / (span[2] / 2),
           "ar": np.hypot((cen[:, 0] - (lo[0] + hi[0]) / 2) / (span[0] / 2), (cen[:, 2] - (lo[2] + hi[2]) / 2) / (span[2] / 2))}
    sel = np.asarray(eval(a.where, {"__builtins__": {}}, env), bool)
    tex_i = gltf["materials"][0]["pbrMetallicRoughness"]["baseColorTexture"]["index"]
    bv = gltf["images"][gltf["textures"][tex_i]["source"]]["bufferView"]
    im = Image.open(io.BytesIO(views[bv]))
    mode = im.mode
    arr = np.asarray(im.convert("RGB")).astype(np.float32) / 255.0
    h, w = arr.shape[:2]
    mask = Image.new("L", (w, h), 0)
    dr = ImageDraw.Draw(mask)
    for t in idx[sel]:
        pts = [((uv[k, 0] % 1.0) * w, (uv[k, 1] % 1.0) * h) for k in t]
        dr.polygon(pts, fill=255)
    from PIL import ImageFilter
    other = Image.new("L", (w, h), 0)
    do = ImageDraw.Draw(other)
    for t in idx[~sel]:
        pts = [((uv[k, 0] % 1.0) * w, (uv[k, 1] % 1.0) * h) for k in t]
        do.polygon(pts, fill=255)
    taken_raw = np.asarray(other) > 0
    # texels inside a selected triangle are painted unless they lie well inside another triangle (eroded mask)
    other_inner = np.asarray(other.filter(ImageFilter.MinFilter(3))) > 0
    core = (np.asarray(mask) > 0) & ~other_inner
    grown = np.asarray(mask.filter(ImageFilter.MaxFilter(3))) > 0       # 1-px gutter around the painted charts...
    taken = np.asarray(other.filter(ImageFilter.MaxFilter(3))) > 0       # ...unless close to other triangles' texels
    m = (core | (grown & ~taken)).astype(np.float32)[..., None]
    lum = arr.mean(-1, keepdims=True)
    target = np.array([float(x) for x in a.rgb.split(",")], np.float32)
    var = (lum - lum[m[..., 0] > 0.5].mean()) * a.keep if (m > 0.5).any() else 0
    new = np.clip(target + var, 0, 1)
    arr = arr * (1 - m) + new * m
    out = Image.fromarray((arr * 255 + 0.5).astype(np.uint8), "RGB")
    if mode == "RGBA":
        out = out.convert("RGBA")
    buf = io.BytesIO()
    out.save(buf, "PNG")
    views[bv] = buf.getvalue()
    save(a.dst, gltf, views)
    print(f"painted {int(sel.sum())} triangles ({(m > 0.5).mean() * 100:.1f}% of texels) -> {a.dst}")


def rot(yaw, pitch):
    cy, sy = np.cos(np.radians(yaw)), np.sin(np.radians(yaw))
    cp, sp = np.cos(np.radians(pitch)), np.sin(np.radians(pitch))
    ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    rx = np.array([[1, 0, 0], [0, cp, -sp], [0, sp, cp]])
    return rx @ ry


def render(a):
    gltf, views = load(a.src)
    prim, pos, idx, uv = mesh(gltf, views)
    tex = base_color(gltf, views)
    col = tri_colors(tex, uv, idx)
    pos = pos - (pos.min(0) + pos.max(0)) / 2
    radius = np.abs(pos).max() * 1.1
    S = a.size
    shots = [("front", 0, 0), ("back34", 140, 0), ("side", -90, 0), ("top34", 35, 30), ("under", 0, -60)]
    sheet = Image.new("RGB", (S * len(shots), S + 16), (255, 255, 255))
    d0 = ImageDraw.Draw(sheet)
    for k, (name, yaw, pitch) in enumerate(shots):
        p = pos @ rot(yaw, pitch).T
        tri = p[idx]
        n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
        n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)
        shade = 0.35 + 0.65 * np.abs(n @ np.array([0.3, 0.5, 0.81]))
        rgb = np.clip(col * shade[:, None] * 255, 0, 255).astype(int)
        order = np.argsort(tri[:, :, 2].mean(axis=1))
        img = Image.new("RGB", (S, S), (138, 138, 138))
        dr = ImageDraw.Draw(img)
        xy = (tri[:, :, :2] / radius * 0.5 + 0.5) * S
        xy[:, :, 1] = S - xy[:, :, 1]
        for t in order:
            c = tuple(rgb[t])
            dr.polygon([tuple(v) for v in xy[t]], fill=c, outline=c)
        sheet.paste(img, (k * S, 16))
        d0.text((k * S + 3, 2), name, fill=(0, 0, 0))
    sheet.save(a.dst)
    print("rendered", a.dst, len(idx), "tris")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("mode", choices=["cut", "render", "paint"])
    p.add_argument("src")
    p.add_argument("dst")
    p.add_argument("--drop", action="append", default=[])
    p.add_argument("--keep-largest", type=int, default=0)
    p.add_argument("--size", type=int, default=360)
    p.add_argument("--where", default="")
    p.add_argument("--rgb", default="0.1,0.35,0.15")
    p.add_argument("--keep", type=float, default=0.25)
    a = p.parse_args()
    {"cut": cut, "render": render, "paint": paint}[a.mode](a)


if __name__ == "__main__":
    main()
