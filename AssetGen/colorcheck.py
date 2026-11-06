"""Median colour (RGB, hue, sat, light) of the object pixels: concept vs QA front render.
   colorcheck.py CONCEPT.png QA_FRONT.png"""
import colorsys
import sys

import numpy as np
from PIL import Image


def stats(p):
    a = np.asarray(Image.open(p).convert("RGB")).astype(float)
    bg = np.median(np.concatenate([a[:10, :10].reshape(-1, 3), a[:10, -10:].reshape(-1, 3)]), 0)
    px = a[np.abs(a - bg).sum(-1) > 54]
    med = np.median(px, 0)
    h, l, s = colorsys.rgb_to_hls(*(med / 255))
    return f"rgb={med.round().astype(int).tolist()} hue={round(h*360)} sat={s:.2f} light={l:.2f}"


print("concept", stats(sys.argv[1]))
print("model  ", stats(sys.argv[2]))
