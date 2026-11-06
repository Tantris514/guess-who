"""Prepare same-scale square views for 3D generation from orthographic character images (front/back/side).

  python -I char_views.py OUT_DIR front=IMG,MASK [back=IMG,MASK] [left=IMG,MASK] [right=IMG,MASK]
Each view is cut out with its BiRefNet mask onto black and cropped with ONE common square window (the template's
figure height x 1.1, taller when hair or a hat rises above the template's head, centred on the frame's centre column and the figure's vertical middle), so every view keeps the
same scale and position, as Pixal3D's multi-view rig expects. Writes OUT_DIR/<view>_sq.png (1024x1024, RGBA).
"""
import json
import os
import sys

import numpy as np
from PIL import Image

H_PX = 1536
W_PX = 1024
TOP, BOTTOM = 175, 1500           # template figure extent (rows), feet at ~1496, head top ~179
out = sys.argv[1]
os.makedirs(out, exist_ok=True)
# tall hair / hats above the template's head: widen the common window so nothing is clipped (all views, same scale)
for arg in sys.argv[2:]:
    _m = np.asarray(Image.open(arg.split("=", 1)[1].split(",")[1]).convert("L").resize((W_PX, H_PX))) > 127
    _rows = np.where(_m.any(1))[0]
    if len(_rows) and _rows[0] - 20 < TOP:
        TOP = int(_rows[0]) - 20
side = int(round((BOTTOM - TOP) * 1.1))
cy = (TOP + BOTTOM) // 2
x0, y0 = W_PX // 2 - side // 2, cy - side // 2
info = {"square_px": side, "crop_xy": [x0, y0], "scale_cm_per_px": 140.0 / 1024 * side / 1024}
for arg in sys.argv[2:]:
    view, paths = arg.split("=", 1)
    img_p, mask_p = paths.split(",")
    img = np.asarray(Image.open(img_p).convert("RGB").resize((W_PX, H_PX), Image.LANCZOS))
    m = np.asarray(Image.open(mask_p).convert("L").resize((W_PX, H_PX), Image.BILINEAR))
    rgba = np.dstack([img, m]).astype(np.uint8)
    rgba[m < 128, :3] = 0
    canvas = np.zeros((side, side, 4), np.uint8)
    sx0, sy0 = max(x0, 0), max(y0, 0)
    sx1, sy1 = min(x0 + side, W_PX), min(y0 + side, H_PX)
    canvas[sy0 - y0:sy1 - y0, sx0 - x0:sx1 - x0] = rgba[sy0:sy1, sx0:sx1]
    Image.fromarray(canvas, "RGBA").resize((1024, 1024), Image.LANCZOS).save(os.path.join(out, f"{view}_sq.png"))
    info[view] = [img_p, mask_p]
json.dump(info, open(os.path.join(out, "views.json"), "w"), indent=1)
print(json.dumps(info))
