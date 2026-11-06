"""Publish a generated full character in manifest.json (kind "character").

  V:/ComfyUI/ComfyUI/ComfyUI/.venv/Scripts/python.exe -I approve_char.py NAME BODY(manny|quinn) DIR3D WINNER_ENGINE \
      --front-tag s42_st2_reg --back-tag s54 [--notes "..."]
Renders (software) all-around views, head/hand close-ups and the 3D pose gate into DIR3D, then upserts the entry with
the image gates (from chars/NAME/<view>/gate.json) and the 3D gate.
"""
import argparse
import json
import os
import struct
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable
HEIGHT = {"manny": 180.5, "quinn": 180.2}

p = argparse.ArgumentParser()
p.add_argument("name")
p.add_argument("body", choices=["manny", "quinn"])
p.add_argument("dir3d")
p.add_argument("engine")
p.add_argument("--front-tag", required=True)
p.add_argument("--back-tag", required=True)
p.add_argument("--side-tag", default="", help="gate tag of the approved side (left) view, if one was used")
p.add_argument("--display-name", default="")
p.add_argument("--notes", default="")
p.add_argument("--fit-body", action="store_true", help="scale from the body fit (hat on top), not total height")
a = p.parse_args()

cdir = os.path.join(ROOT, "chars", a.name)
d3 = os.path.abspath(a.dir3d)
glb = os.path.join(d3, f"{a.name}.glb")
tf = os.path.join(ROOT, "chars", "templates", f"{a.body}_front.png")
tb = os.path.join(ROOT, "chars", "templates", f"{a.body}_back.png")
subprocess.run([PY, "-I", os.path.join(ROOT, "glb_mesh.py"), "render", glb, os.path.join(d3, "qa_allround.png"), "--size", "360"], check=True)
subprocess.run([PY, "-I", os.path.join(ROOT, "char_closeup.py"), glb, os.path.join(d3, "qa_closeup_head_hands.png")], check=True)
for f in os.listdir(d3):
    if f.endswith(".tmp.png"):
        os.remove(os.path.join(d3, f))
out = subprocess.run([PY, "-I", os.path.join(ROOT, "char_pose3d.py"), glb, tf, str(HEIGHT[a.body]), os.path.join(d3, "pose"), tb]
                     + (["--fit-body"] if a.fit_body else []),
                     check=True, capture_output=True, text=True).stdout
pose3d = json.loads(out.strip().splitlines()[-1])

data = open(glb, "rb").read()
clen = struct.unpack_from("<I", data, 12)[0]
gltf = json.loads(data[20:20 + clen])
mins, maxs, tris = [1e9] * 3, [-1e9] * 3, 0
for mesh in gltf["meshes"]:
    for prim in mesh["primitives"]:
        acc = gltf["accessors"][prim["attributes"]["POSITION"]]
        mins = [min(x, y) for x, y in zip(mins, acc["min"])]
        maxs = [max(x, y) for x, y in zip(maxs, acc["max"])]
        tris += gltf["accessors"][prim["indices"]]["count"] // 3
ext = [y - x for x, y in zip(mins, maxs)]
scale = pose3d["scale_glb_to_cm"] if a.fit_body else HEIGHT[a.body] / ext[1]
gf = json.load(open(os.path.join(cdir, "front", "gate.json"), encoding="utf-8"))
gb = json.load(open(os.path.join(cdir, "back", "gate.json"), encoding="utf-8"))
gs = json.load(open(os.path.join(cdir, "side", "gate.json"), encoding="utf-8")) if a.side_tag else {}
keep = ("coverage", "arm_coverage", "head_top_offset_px", "hand_offset_px", "registration", "raw", "denoise", "edit_input")
files = {"glb": glb,
         "front_image": os.path.join(cdir, "front_approved.png"), "front_mask": os.path.join(cdir, "front_approved_mask.png"),
         "back_image": os.path.join(cdir, "back_approved.png"), "back_mask": os.path.join(cdir, "back_approved_mask.png"),
         "qa_allround": os.path.join(d3, "qa_allround.png"), "qa_closeup_head_hands": os.path.join(d3, "qa_closeup_head_hands.png"),
         "pose_overlay_front": os.path.join(d3, "pose_front.png"), "pose_overlay_back": os.path.join(d3, "pose_back.png")}
if a.side_tag:
    files["side_image"] = os.path.join(cdir, "side_approved.png")
    files["side_mask"] = os.path.join(cdir, "side_approved_mask.png")
for f in sorted(os.listdir(d3)):
    if f.startswith("qa_") and f[:-4] not in files and f.endswith(".png"):
        files[f[:-4]] = os.path.join(d3, f)
views = os.path.join(cdir, "views")
if os.path.isdir(views):
    for f in sorted(os.listdir(views)):
        if f.endswith("_sq.png"):
            files[f"view_{f[:-7]}_square"] = os.path.join(views, f)
entry = {
    "name": a.name, "kind": "character", "body": a.body, "status": "approved",
    **({"display_name": a.display_name} if a.display_name else {}),
    "files": files,
    "size_cm": [round(ext[0] * scale, 1), round(ext[2] * scale, 1), round(ext[1] * scale, 1)],
    "rooms": [],
    "orientation": {"up": "+Y (glTF)", "front": "+Z (glTF)", "character_left": "+X (glTF)",
                    "pivot": "bounding-box centre (not the floor): feet at glTF y = %.4f" % mins[1],
                    "glb_extent_xyz": [round(x, 4) for x in ext], "uniform_scale_to_cm": round(scale, 3),
                    "scale_mode": pose3d.get("scale_mode"),
                    "pose": "UE mannequin reference A-pose (template chars/templates/%s_*.png)" % a.body},
    "mesh": {"triangles": tris, "textures_px": [2048], "material": "one PBR metallic-roughness material (baseColor, metallicRoughness, normal) embedded in the GLB",
             "generator": a.engine},
    "pose_gate": {"front_image": {k: gf[a.front_tag].get(k) for k in keep if k in gf[a.front_tag]},
                  "back_image": {k: gb[a.back_tag].get(k) for k in keep if k in gb[a.back_tag]},
                  **({"side_image_left": {k: gs[a.side_tag].get(k) for k in ("coverage", "head_top_offset_px", "extra_area_ratio", "denoise") if k in gs[a.side_tag]}} if a.side_tag else {}),
                  "mesh_silhouette_vs_template": pose3d,
                  "definitions": "coverage = |gen & tpl| / |tpl| (tpl = template luminance > 12, gen = BiRefNet mask); arm coverage = same on template "
                                 "pixels with |x - centre| > 22 cm; offsets in template px (0.1367 cm/px), head top negative = higher than the template's head."},
    "notes": a.notes,
}
tmp = os.path.join(ROOT, "qa", f"_entry_{a.name}.json")
json.dump(entry, open(tmp, "w", encoding="utf-8"), indent=1)
subprocess.run([PY, "-I", "-X", "utf8", os.path.join(ROOT, "manifest_tool.py"), "upsert", tmp], check=True)
os.remove(tmp)
print(json.dumps({"name": a.name, "tris": tris, "size_cm": entry["size_cm"], "scale": round(scale, 3), "pose3d": pose3d}))
