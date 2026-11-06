"""Median hue/sat/light of a box in two images:  huecheck.py IMG_A x0,y0,x1,y1 IMG_B x0,y0,x1,y1"""
import colorsys
import sys

import numpy as np
from PIL import Image


def st(p, box):
    a = np.asarray(Image.open(p).convert("RGB").crop(tuple(int(v) for v in box.split(",")))).reshape(-1, 3).astype(float) / 255
    hls = np.array([colorsys.rgb_to_hls(*x) for x in a[::5]])
    h = np.degrees(np.angle(np.mean(np.exp(1j * np.radians(hls[:, 0] * 360)))))
    return f"hue={h % 360:.0f} light={np.median(hls[:, 1]):.2f} sat={np.median(hls[:, 2]):.2f}"


print("A", st(sys.argv[1], sys.argv[2]))
print("B", st(sys.argv[3], sys.argv[4]))
