"""Print a GLB's bounding box (POSITION accessor min/max), counts, and texture sizes.  glb_info.py FILE.glb ..."""
import json
import struct
import sys

for path in sys.argv[1:]:
    with open(path, "rb") as f:
        data = f.read()
    magic, ver, length = struct.unpack_from("<III", data, 0)
    clen, ctype = struct.unpack_from("<II", data, 12)
    gltf = json.loads(data[20:20 + clen])
    mins, maxs, verts, tris = [1e9] * 3, [-1e9] * 3, 0, 0
    for mesh in gltf.get("meshes", []):
        for prim in mesh["primitives"]:
            acc = gltf["accessors"][prim["attributes"]["POSITION"]]
            verts += acc["count"]
            mins = [min(a, b) for a, b in zip(mins, acc.get("min", mins))]
            maxs = [max(a, b) for a, b in zip(maxs, acc.get("max", maxs))]
            if "indices" in prim:
                tris += gltf["accessors"][prim["indices"]]["count"] // 3
    imgs = []
    for img in gltf.get("images", []):
        bv = gltf["bufferViews"][img["bufferView"]]
        off = 28 + clen + bv.get("byteOffset", 0)
        blob = data[off:off + bv["byteLength"]]
        if blob[:8] == b"\x89PNG\r\n\x1a\n":
            w, h = struct.unpack(">II", blob[16:24])
        else:
            w = h = "?"
        imgs.append(f"{img.get('mimeType', '?')} {w}x{h}")
    mats = [list(m.keys()) for m in gltf.get("materials", [])]
    ext = [round(b - a, 3) for a, b in zip(mins, maxs)]
    print(f"{path}: {length/1e6:.1f}MB verts={verts} tris={tris} min={[round(x,3) for x in mins]} max={[round(x,3) for x in maxs]} extent={ext} images={imgs} nodes={[n.get('rotation') or n.get('matrix') for n in gltf.get('nodes', [])]}")
