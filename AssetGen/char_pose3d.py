"""Pose check of a character GLB against the mannequin template: orthographic front (and back) silhouette of the mesh,
scaled so its height equals the mannequin's and its feet sit at z = 0, rasterised in the template's camera
(140 cm wide, centre 100 cm high, 0.1367 cm/px), then gated like the images (coverage, arm coverage, offsets).

  python -I char_pose3d.py GLB TEMPLATE_FRONT.png HEIGHT_CM OUT_PREFIX [TEMPLATE_BACK.png]
Writes OUT_PREFIX_front.png (overlay: grey both, red template only, blue mesh only) and prints JSON.
"""
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import char_edit  # noqa: E402
import glb_mesh  # noqa: E402

CM = 140.0 / 1024


def silhouette(pos, idx, back=False):
    x = pos[:, 0] if not back else -pos[:, 0]
    px = 512 + x / CM
    py = 768 - (pos[:, 1] - 100.0) / CM
    img = Image.new("L", (1024, 1536), 0)
    d = ImageDraw.Draw(img)
    for t in idx:
        d.polygon([(px[k], py[k]) for k in t], fill=255)
    return np.asarray(img) > 0


args = [x for x in sys.argv[1:] if not x.startswith("--")]
FIT_BODY = "--fit-body" in sys.argv          # scale fitted to the body below the neck (hats/hair excluded) instead of height
glb, tplf, height = args[0], args[1], float(args[2])
outp = args[3]
g, v = glb_mesh.load(glb)
prim, pos, idx, uv = glb_mesh.mesh(g, v)
lo, hi = pos.min(0), pos.max(0)
s = height / (hi[1] - lo[1])
# centre on the body below 60 % height (feathers, hats or a sash end must not shift the figure)
low_v = pos[:, 1] < lo[1] + 0.6 * (hi[1] - lo[1])
blo, bhi = pos[low_v].min(0), pos[low_v].max(0)
base = pos - [(blo[0] + bhi[0]) / 2, lo[1], (blo[2] + bhi[2]) / 2]
res = {"scale_glb_to_cm": round(float(s), 3), "scale_mode": "height"}
if FIT_BODY:
    tpl0 = char_edit.tpl_mask(tplf)
    body = np.zeros_like(tpl0)
    body[345:] = True                       # below the template's neck (row 330) -> shoulders, arms, legs
    sub = idx[:: max(1, len(idx) // 15000)]
    best = None
    for k in np.arange(0.74, 1.16, 0.005):         # up to +16 %: tall hair (kamikaze) on top of the body
        m = silhouette(base * (s * k), sub)
        iou = (m & tpl0 & body).sum() / ((m | tpl0) & body).sum()
        if best is None or iou > best[0]:
            best = (iou, k)
    s = s * best[1]
    res.update(scale_glb_to_cm=round(float(s), 3), scale_mode="fit_body (IoU below the neck)",
               height_cm_at_this_scale=round(float((hi[1] - lo[1]) * s), 1), body_iou=round(float(best[0]), 4))
p = base * s                                # cm, feet at 0, centred
views = [("front", tplf, False)]
if len(args) > 4:
    views.append(("back", args[4], True))
for name, tp, back in views:
    tpl = char_edit.tpl_mask(tp)
    m = silhouette(p, idx, back)
    g_ = char_edit.gate(tpl, m)
    res[name] = g_
    ov = np.zeros(tpl.shape + (3,), np.uint8)
    ov[tpl & m] = (200, 200, 200)
    ov[tpl & ~m] = (255, 0, 0)
    ov[~tpl & m] = (0, 120, 255)
    Image.fromarray(ov).save(f"{outp}_{name}.png")
# floor contact: what touches the floor (lowest 1.5 cm), in cm, glTF X (left/right) and Z (front/back)
low = p[:, 1] < 1.5
res["floor_contact_cm"] = {"x": [round(float(p[low, 0].min()), 1), round(float(p[low, 0].max()), 1)],
                           "z": [round(float(p[low, 2].min()), 1), round(float(p[low, 2].max()), 1)],
                           "gap_between_feet_at_floor": None}
xs = np.sort(p[low, 0])
if len(xs) > 10:
    gaps = np.diff(xs)
    k = int(np.argmax(gaps))
    res["floor_contact_cm"]["gap_between_feet_at_floor"] = round(float(gaps[k]), 1) if abs(xs[k]) < 15 else 0.0
# metallic / roughness statistics of the material (glTF: G = roughness, B = metallic)
try:
    import io
    mr = g["materials"][0]["pbrMetallicRoughness"].get("metallicRoughnessTexture")
    if mr:
        bv = g["images"][g["textures"][mr["index"]]["source"]]["bufferView"]
        a = np.asarray(Image.open(io.BytesIO(v[bv])).convert("RGB")).astype(np.float32) / 255
        res["material"] = {"metallic_median": round(float(np.median(a[..., 2])), 2), "roughness_median": round(float(np.median(a[..., 1])), 2)}
except Exception as e:  # noqa: BLE001
    res["material"] = str(e)
print(json.dumps(res))
