"""Publish an approved TRELLIS model in manifest.json.

  python -I -X utf8 approve_model.py NAME MODEL_DIR --front +Z [--notes "..."] [--concept PATH]

--front: the glTF axis the object's front faces (seen in the QA renders: the unrotated 'front' render looks from +Z).
size_cm = GLB bounding box scaled uniformly so the reference dimension in props_meta.json matches reality.
"""
import argparse
import json
import os
import struct
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))


def glb_bounds(path):
    with open(path, "rb") as f:
        data = f.read()
    clen = struct.unpack_from("<I", data, 12)[0]
    gltf = json.loads(data[20:20 + clen])
    mins, maxs, tris = [1e9] * 3, [-1e9] * 3, 0
    for mesh in gltf["meshes"]:
        for prim in mesh["primitives"]:
            acc = gltf["accessors"][prim["attributes"]["POSITION"]]
            mins = [min(a, b) for a, b in zip(mins, acc["min"])]
            maxs = [max(a, b) for a, b in zip(maxs, acc["max"])]
            if "indices" in prim:
                tris += gltf["accessors"][prim["indices"]]["count"] // 3
    tex = []
    for img in gltf.get("images", []):
        bv = gltf["bufferViews"][img["bufferView"]]
        blob = data[28 + clen + bv.get("byteOffset", 0):][:24]
        tex.append(struct.unpack(">II", blob[16:24])[0] if blob[:4] == b"\x89PNG" else 0)
    return mins, maxs, tris, tex


def main():
    p = argparse.ArgumentParser()
    p.add_argument("name")
    p.add_argument("model_dir")
    p.add_argument("--front", default="+Z", choices=["+Z", "-Z", "+X", "-X"])
    p.add_argument("--notes", default="")
    p.add_argument("--concept", default="")
    p.add_argument("--size", default="", help="w,d,h in cm: real proportions differ from the model -> per-axis scale")
    a = p.parse_args()
    meta = json.load(open(os.path.join(ROOT, "props_meta.json"), encoding="utf-8"))[a.name]
    mdir = os.path.abspath(os.path.join(ROOT, a.model_dir))
    glb = os.path.join(mdir, f"{a.name}.glb")
    mins, maxs, tris, tex = glb_bounds(glb)
    ext = [b - c for b, c in zip(maxs, mins)]                  # glTF metres-ish units, X, Y(up), Z
    if a.front in ("+Z", "-Z"):
        w, d = ext[0], ext[2]
    else:
        w, d = ext[2], ext[0]
    h = ext[1]
    axis, cm = meta["ref"]
    scale = cm / {"w": w, "d": d, "h": h}[axis]
    size = [round(w * scale), round(d * scale), round(h * scale)]
    per_axis = None
    if a.size:
        size = [int(v) for v in a.size.split(",")]
        per_axis = [round(size[0] / w, 2), round(size[1] / d, 2), round(size[2] / h, 2)]
    files = {"glb": glb}
    for fn in sorted(os.listdir(mdir)):
        if fn.startswith("qa_") and fn.endswith(".png"):
            files[fn[:-4]] = os.path.join(mdir, fn)
    sel = json.load(open(os.path.join(ROOT, "selections.json"), encoding="utf-8"))
    concept = a.concept or sel.get(a.name, "")
    if concept:
        files["concept"] = os.path.abspath(os.path.join(ROOT, concept))
    result = json.load(open(os.path.join(mdir, "result.json"), encoding="utf-8")) if os.path.exists(os.path.join(mdir, "result.json")) else {}
    entry = {
        "name": a.name,
        **({"display_name": meta["display_name"]} if meta.get("display_name") else {}),
        "kind": meta.get("kind", "prop"),
        "status": "approved",
        "files": files,
        "size_cm": size,
        "rooms": meta["rooms"],
        **({"slot": meta["slot"]} if meta.get("slot") else {}),
        "orientation": {
            "up": "+Y (glTF)",
            "front": f"{a.front} (glTF)",
            "pivot": "bounding-box centre (not the floor): bottom is at glTF y = %.3f" % mins[1],
            "glb_extent_xyz": [round(x, 3) for x in ext],
            "uniform_scale_to_cm": round(scale, 2),
        },
        "mesh": {"triangles": tris, "textures_px": tex, "material": "PBR metallic-roughness (baseColor, metallicRoughness, normal) embedded in the GLB"},
        "notes": a.notes,
    }
    if per_axis:
        entry["orientation"].pop("uniform_scale_to_cm")
        entry["orientation"]["per_axis_scale_to_cm_wdh"] = per_axis
        entry["notes"] += (" The generated proportions are off (too squat/deep), so size_cm is the REAL size: scale non-uniformly"
                           " per axis to fit it (width, depth, height scale factors from the GLB = %s)." % per_axis)
    if result.get("seconds"):
        entry["gen_seconds"] = result["seconds"]
    tmp = os.path.join(ROOT, "qa", f"_entry_{a.name}.json")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(entry, f, indent=1)
    subprocess.run([sys.executable, "-I", "-X", "utf8", os.path.join(ROOT, "manifest_tool.py"), "upsert", tmp], check=True)
    os.remove(tmp)
    print(a.name, "size_cm", size, "tris", tris, "tex", tex)


if __name__ == "__main__":
    main()
