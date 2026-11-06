"""Head-top / neck / shoulder / feet rows of masks vs template:  proportions.py TEMPLATE.png MASK.png [MASK ...]"""
import sys

import numpy as np
from PIL import Image


def prof(m):
    ys = np.where(m.any(1))[0]
    top, bot = ys.min(), ys.max()
    c = m.shape[1] // 2
    w = np.array([m[y, c - 150:c + 150].sum() for y in range(m.shape[0])])
    neck = top + 40 + int(np.argmin(w[top + 40:top + 250]))
    sh = next((y for y in range(neck, neck + 200) if w[y] > 2.2 * w[neck]), -1)
    return int(top), int(neck), int(sh), int(bot)


t = prof(np.asarray(Image.open(sys.argv[1]).convert("RGB")).mean(-1) > 12)
print("template top/neck/shoulder/feet", t)
for p in sys.argv[2:]:
    g = prof(np.asarray(Image.open(p).convert("L")) > 127)
    print(p.split("/")[-1], g, "diff", [a - b for a, b in zip(g, t)])
