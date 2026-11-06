"""Arm centreline/width comparison between the template mask and a generated mask (rows where both have arm pixels).
   arm_axis.py TEMPLATE.png MASK.png"""
import sys

import numpy as np
from PIL import Image

ARM = int(round(22.0 / (140.0 / 1024)))


def arm_rows(m, side):
    h, w = m.shape
    c = w // 2
    out = {}
    for y in range(int(0.25 * h), int(0.62 * h)):
        row = m[y]
        xs = np.where(row[:c - ARM])[0] if side == "L" else np.where(row[c + ARM:])[0] + c + ARM
        if len(xs) > 2:
            out[y] = (xs.mean(), xs.max() - xs.min() + 1)
    return out


tpl = np.asarray(Image.open(sys.argv[1]).convert("RGB")).mean(-1) > 12
gen = np.asarray(Image.open(sys.argv[2]).convert("L")) > 127
for side in ("L", "R"):
    t, g = arm_rows(tpl, side), arm_rows(gen, side)
    ys = sorted(set(t) & set(g))
    if not ys:
        print(side, "no overlap")
        continue
    dx = np.array([g[y][0] - t[y][0] for y in ys])
    wt = np.array([t[y][1] for y in ys])
    wg = np.array([g[y][1] for y in ys])
    print(f"{side}: rows {len(ys)}  centreline offset mean {dx.mean():+.1f}px (|dx| median {np.median(np.abs(dx)):.1f}, max {np.abs(dx).max():.1f})"
          f"  width tpl {np.median(wt):.0f}px gen {np.median(wg):.0f}px  ({np.median(wg)/np.median(wt):.2f})")
