"""Build workflows/pixal3d_mv_game.json from the official 3d_pixal3d_multi_views template.

- Inputs: up to four pre-framed square views (front/left/back/right, same scale, black background) loaded by
  LoadImage nodes 900-903 (images gw_mv_front.png ... ); the turnaround-sheet crop + per-view BiRefNet crop chain
  is removed (it re-frames every view separately and would break the common scale).
- Lighter settings: upsample 1024, remesh 512, 60k-face decimation, 2048 textures, lighter AO.
- QA renders of the final textured mesh (front, back34, side, front34 normal, top34) like trellis2_game.json.
- Save3DAdvanced prefix 3d/gw_char.

  python -I -X utf8 patch_pixal_mv.py
"""
import json
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
wf = json.load(open(os.path.join(ROOT, "workflows", "pixal3d_mv_template.json"), encoding="utf-8"))
nodes = {n["id"]: n for n in wf["nodes"]}

DROP = {364, 338, 341, 342, 345, 192, 348, 349, 350, 351, 352, 353, 312, 340, 343, 344, 346}
dead_links = {l[0] for l in wf["links"] if l[1] in DROP or l[3] in DROP}
wf["links"] = [l for l in wf["links"] if l[0] not in dead_links]
wf["nodes"] = [n for n in wf["nodes"] if n["id"] not in DROP]
nodes = {n["id"]: n for n in wf["nodes"]}
for n in wf["nodes"]:
    for i in n.get("inputs", []):
        if i.get("link") in dead_links:
            i["link"] = None
    for o in n.get("outputs", []):
        if o.get("links"):
            o["links"] = [x for x in o["links"] if x not in dead_links]

nodes[94]["widgets_values"][0] = 1024        # upsample target
nodes[241]["widgets_values"][0] = 512        # remesh voxel resolution
nodes[186]["widgets_values"][0] = 60000      # decimation target faces
nodes[288]["widgets_values"][0] = 2048       # texture size
nodes[233]["widgets_values"][1] = 32         # AO rays
nodes[372]["widgets_values"][0] = "3d/gw_char"
for nid in (246, 323, 262):                  # preview-only leaves
    if nid in nodes:
        nodes[nid]["mode"] = 2

next_node = max(wf["last_node_id"], max(nodes)) + 1
next_link = max(wf["last_link_id"], max(l[0] for l in wf["links"])) + 1


def add_node(node_type, inputs, outputs, widgets, pos, nid=None, title=None):
    global next_node
    if nid is None:
        nid = next_node
        next_node += 1
    node = {"id": nid, "type": node_type, "pos": pos, "size": [300, 120], "flags": {}, "order": 999, "mode": 0,
            "inputs": inputs, "outputs": outputs, "properties": {"Node name for S&R": node_type}, "widgets_values": widgets}
    if title:
        node["title"] = title
    wf["nodes"].append(node)
    nodes[nid] = node
    return nid


def link(src, slot, dst, dslot, typ):
    global next_link
    lid = next_link
    next_link += 1
    wf["links"].append([lid, src, slot, dst, dslot, typ])
    nodes[src]["outputs"][slot]["links"] = (nodes[src]["outputs"][slot].get("links") or []) + [lid]
    nodes[dst]["inputs"][dslot]["link"] = lid


cond = nodes[324]
slot_of = {i["name"]: k for k, i in enumerate(cond["inputs"])}
for k, view in enumerate(("front", "left", "back", "right")):
    nid = 900 + k
    add_node("LoadImage", [], [{"name": "IMAGE", "type": "IMAGE", "links": []}, {"name": "MASK", "type": "MASK", "links": []}],
             [f"gw_mv_{view}.png", "image"], [-800, 200 * k], nid=nid, title=f"view {view}")
    link(nid, 0, 324, slot_of[view], "IMAGE")

FINAL_MESH = 260
views = [("front", None, "texture"), ("back34", 140.0, "texture"), ("side", -90.0, "texture"),
         ("front34_normal", 35.0, "normal"), ("top34", (35.0, 30.0), "texture")]
y = 2600
for name, yaw, mode in views:
    src = FINAL_MESH
    if yaw is not None:
        turns = [(0.0, yaw)] if not isinstance(yaw, tuple) else [(0.0, yaw[0]), (yaw[1], 0.0)]
        for ax, ay in turns:
            r = add_node("RotateMesh", [{"name": "mesh", "type": "MESH", "link": None}], [{"name": "mesh", "type": "MESH", "links": []}],
                         ["euler_xyz", ax, ay, 0.0], [3600, y])
            link(src, 0, r, 0, "MESH")
            src = r
    rn = add_node("RenderMesh", [{"name": "mesh", "type": "MESH", "link": None}],
                  [{"name": "image", "type": "IMAGE", "links": []}, {"name": "mask", "type": "MASK", "links": []}],
                  [mode, 768, 768, "#8a8a8a"], [3950, y])
    link(src, 0, rn, 0, "MESH")
    sv = add_node("SaveImage", [{"name": "images", "type": "IMAGE", "link": None}], [], [f"qa/render_{name}"], [4300, y],
                  title=f"QA render {name}")
    link(rn, 0, sv, 0, "IMAGE")
    y += 400

wf["last_node_id"] = next_node
wf["last_link_id"] = next_link
dst = os.path.join(ROOT, "workflows", "pixal3d_mv_game.json")
json.dump(wf, open(dst, "w", encoding="utf-8"))
print("wrote", dst, len(wf["nodes"]), "nodes; conditioning inputs", slot_of)
