"""Derive the game-asset TRELLIS.2 workflow from the official template.

- Faster: fewer shape steps, 1024 upsample, 512 remesh, lighter AO/normal bakes.
- Adds QA renders of the final textured mesh (front, three-quarter back, side) saved as images,
  so every generated model can be reviewed before it goes into Unreal.

  python -I -X utf8 patch_trellis.py
"""
import copy
import json
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "workflows", "trellis2_template.json")
DST = os.path.join(ROOT, "workflows", "trellis2_game.json")

wf = json.load(open(SRC, encoding="utf-8"))
nodes = {n["id"]: n for n in wf["nodes"]}

nodes[18]["widgets_values"][2] = 12      # shape KSampler steps (20 -> 12)
nodes[94]["widgets_values"][0] = 1024    # Trellis2UpsampleStage target resolution (1536 -> 1024)
nodes[241]["widgets_values"][0] = 512    # RemeshMesh voxel resolution (768 -> 512)
nodes[233]["widgets_values"][1] = 32     # AO rays per texel (64 -> 32)
nodes[224]["widgets_values"][0] = 1024   # normal bake resolution (2048 -> 1024)
nodes[316]["widgets_values"] = [True]    # use TRELLIS.2 (not Pixal3D)

# Mute preview-only leaf nodes (temp GLBs, texture previews): saves time and disk, outputs unchanged.
for nid in (246, 323, 262):   # PreviewImage nodes with downstream links are pass-through here: keep them
    if nid in nodes:
        nodes[nid]["mode"] = 2

next_node = wf["last_node_id"]
next_link = wf["last_link_id"]


def add_node(node_type, inputs, outputs, widgets, pos, title=None):
    global next_node
    next_node += 1
    node = {"id": next_node, "type": node_type, "pos": pos, "size": [300, 120], "flags": {}, "order": 999,
            "mode": 0, "inputs": inputs, "outputs": outputs, "properties": {"Node name for S&R": node_type},
            "widgets_values": widgets}
    if title:
        node["title"] = title
    wf["nodes"].append(node)
    nodes[next_node] = node
    return next_node


def link(src_id, src_slot, dst_id, dst_slot, link_type):
    global next_link
    next_link += 1
    wf["links"].append([next_link, src_id, src_slot, dst_id, dst_slot, link_type])
    out = nodes[src_id]["outputs"][src_slot]
    out["links"] = (out.get("links") or []) + [next_link]
    nodes[dst_id]["inputs"][dst_slot]["link"] = next_link


FINAL_MESH = 260   # MeshSmoothNormals after ApplyTextureToMesh: the textured mesh that gets saved
# (name, yaw degrees about +Y, render mode). Unrotated = default camera on +Z looking at the object's +Z side.
# top34: turn 35 deg, then tilt the top 30 deg toward the camera (shows table tops, seats, felt).
views = [("front", None, "texture"), ("back34", 140.0, "texture"), ("side", -90.0, "texture"),
         ("front34_normal", 35.0, "normal"), ("top34", (35.0, 30.0), "texture")]
y = 2600
for name, yaw, mode in views:
    mesh_src = FINAL_MESH
    if yaw is not None:
        turns = [(0.0, yaw)] if not isinstance(yaw, tuple) else [(0.0, yaw[0]), (yaw[1], 0.0)]
        for ax, ay in turns:
            rot = add_node("RotateMesh",
                           [{"name": "mesh", "type": "MESH", "link": None}],
                           [{"name": "mesh", "type": "MESH", "links": []}],
                           ["euler_xyz", ax, ay, 0.0], [3600, y])
            link(mesh_src, 0, rot, 0, "MESH")
            mesh_src = rot
    render = add_node("RenderMesh",
                      [{"name": "mesh", "type": "MESH", "link": None}],
                      [{"name": "image", "type": "IMAGE", "links": []}, {"name": "mask", "type": "MASK", "links": []}],
                      [mode, 768, 768, "#8a8a8a"], [3950, y])
    link(mesh_src, 0, render, 0, "MESH")
    save = add_node("SaveImage",
                    [{"name": "images", "type": "IMAGE", "link": None}],
                    [],
                    [f"qa/render_{name}"], [4300, y], title=f"QA render {name}")
    link(render, 0, save, 0, "IMAGE")
    y += 400

wf["last_node_id"] = next_node
wf["last_link_id"] = next_link
json.dump(wf, open(DST, "w", encoding="utf-8"))
print("wrote", DST, "nodes:", len(wf["nodes"]))

# ---- Low-memory variant: pure 512 pipeline (no cascade upsample to 1024). For very dense shapes (hair) whose
# 1024 shape decode runs out of VRAM. Shape and texture are decoded from the first (512) shape pass.
DST512 = os.path.join(ROOT, "workflows", "trellis2_game_512.json")
wf512 = copy.deepcopy(wf)
links512 = {l[0]: l for l in wf512["links"]}
nodes512 = {n["id"]: n for n in wf512["nodes"]}


def relink(link_id, new_src, new_slot):
    l = links512[link_id]
    old_src, old_slot = l[1], l[2]
    outs = nodes512[old_src]["outputs"][old_slot]
    outs["links"] = [x for x in (outs.get("links") or []) if x != link_id]
    l[1], l[2] = new_src, new_slot
    nodes512[new_src]["outputs"][new_slot]["links"] = (nodes512[new_src]["outputs"][new_slot].get("links") or []) + [link_id]


relink(551, 18, 0)   # shape decode <- first shape KSampler (512) instead of the 1024 pass
relink(584, 18, 0)   # texture stage shape_latent <- same
relink(582, 91, 0)   # texture stage conditioning <- shape stage instead of the upsample stage
relink(583, 91, 1)
json.dump(wf512, open(DST512, "w", encoding="utf-8"))
print("wrote", DST512)
