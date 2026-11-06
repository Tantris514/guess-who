"""Rigid registration (translation + small uniform scale) of a generated character image to its template, then re-gate.

The edit model sometimes shifts or rescales the whole frame by a few pixels (both arms move the same way). The 3D
generators re-frame the cut-out anyway, so a global similarity transform does not change the pose; correcting it
before the gate measures pose drift only. The transform is fitted on the upper body (rows above 62% of the height:
head, shoulders, arms, hands), where the costume should match the template silhouette.

  python -I char_register.py TEMPLATE.png DIR TAG [TAG ...]       (reads DIR/gen_s<TAG>.png + mask_s<TAG>.png)
Writes DIR/gen_s<TAG>_reg.png, mask_s<TAG>_reg.png and adds "s<TAG>_reg" (with the transform) to DIR/gate.json.
"""
import json
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import char_edit  # noqa: E402


def warp(img, s, dx, dy, resample, fill=None):
    """scale about the template centre column / figure centre, then translate."""
    w, h = img.size
    cx, cy = w / 2, 840.0
    # inverse map for Image.transform: src = (dst - c - d) / s + c
    a = 1 / s
    return img.transform((w, h), Image.AFFINE, (a, 0, cx - (cx + dx) * a, 0, a, cy - (cy + dy) * a), resample=resample,
                         fillcolor=fill)


FIXED_SCALE = "--no-scale" in sys.argv
WIDE = "--wide" in sys.argv                 # side views: allow +-60 px shifts
sys.argv = [x for x in sys.argv if x not in ("--no-scale", "--wide")]
tplp, d = sys.argv[1], sys.argv[2]
tpl = char_edit.tpl_mask(tplp)
H, W = tpl.shape
up = np.zeros_like(tpl)
t_top = int(np.where(tpl.any(1))[0].min())
up[t_top + 25: int(0.62 * H)] = True        # below the crown: feathers, hats and hair volume are not fitted
G = json.load(open(os.path.join(d, "gate.json"), encoding="utf-8"))
for tag in sys.argv[3:]:
    m_img = Image.open(os.path.join(d, f"mask_s{tag}.png")).convert("L")
    best = None
    for s in np.arange(0.96, 1.041, 0.01) if not FIXED_SCALE else [1.0]:
        for dy in range(-30, 31, 2):
            for dx in (range(-60, 61, 3) if WIDE else range(-30, 31, 2)):
                m = np.asarray(warp(m_img, s, dx, dy, Image.NEAREST)) > 127
                inter = (m & tpl & up).sum()
                union = ((m | tpl) & up).sum()
                iou = inter / union
                if best is None or iou > best[0]:
                    best = (iou, float(s), dx, dy)
    # refine translation at 1 px
    iou0, s, dx0, dy0 = best
    for dy in range(dy0 - 2, dy0 + 3):
        for dx in range(dx0 - 2, dx0 + 3):
            m = np.asarray(warp(m_img, s, dx, dy, Image.NEAREST)) > 127
            iou = (m & tpl & up).sum() / ((m | tpl) & up).sum()
            if iou > best[0]:
                best = (iou, s, dx, dy)
    iou, s, dx, dy = best
    m = warp(m_img, s, dx, dy, Image.BILINEAR)
    m.save(os.path.join(d, f"mask_s{tag}_reg.png"))
    img = Image.open(os.path.join(d, f"gen_s{tag}.png")).convert("RGB")
    corners = np.asarray(img)[[5, 5, -6, -6], [5, -6, 5, -6]]
    bg = tuple(int(v) for v in np.median(corners, axis=0))
    warp(img, s, dx, dy, Image.BICUBIC, bg).save(os.path.join(d, f"gen_s{tag}_reg.png"))
    g = char_edit.gate(tpl, np.asarray(m) > 127)
    g["pass"] = bool(g["coverage"] >= 0.95 and g["arm_coverage"] >= 0.92)
    g["registration"] = {"scale": round(s, 3), "dx_px": dx, "dy_px": dy, "upper_body_iou": round(float(iou), 4)}
    g["raw"] = {k: G.get(f"s{tag}", {}).get(k) for k in ("coverage", "arm_coverage", "head_top_offset_px", "hand_offset_px")}
    G[f"s{tag}_reg"] = g
    print(json.dumps({"tag": tag, **g}))
json.dump(G, open(os.path.join(d, "gate.json"), "w", encoding="utf-8"), indent=1)
