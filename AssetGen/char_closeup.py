"""Close-ups of head and hands of a character GLB (software render, front and back34), for QA.
   char_closeup.py GLB OUT.png"""
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import glb_mesh  # noqa: E402


class A:
    pass


a = A()
a.src, a.dst, a.size = sys.argv[1], sys.argv[2] + ".tmp.png", 1100
glb_mesh.render(a)
im = Image.open(a.dst); im.load()
os.remove(a.dst)
S = 1100
tiles = []
for k in (0, 1):                     # front, back34 panels
    p = im.crop((k * S, 16, (k + 1) * S, 16 + S))
    # body spans the full panel height (radius-normalised): head ~ top 8-20 %, hands ~ 48-62 %
    tiles.append(p.crop((int(0.36 * S), int(0.03 * S), int(0.64 * S), int(0.22 * S))).resize((440, 300)))
    tiles.append(p.crop((int(0.14 * S), int(0.40 * S), int(0.36 * S), int(0.58 * S))).resize((300, 245)))
    tiles.append(p.crop((int(0.64 * S), int(0.40 * S), int(0.86 * S), int(0.58 * S))).resize((300, 245)))
# side panel (index 2): head in profile, to judge mask thickness
side = im.crop((2 * S, 16, 3 * S, 16 + S)).crop((int(0.34 * S), int(0.02 * S), int(0.66 * S), int(0.22 * S))).resize((440, 275))
sheet = Image.new("RGB", (1040, 880), (255, 255, 255))
x = [0, 440, 740]
for k in (0, 1):
    for j in range(3):
        sheet.paste(tiles[k * 3 + j], (x[j], k * 300))
sheet.paste(side, (0, 600))
sheet.save(sys.argv[2])
print("wrote", sys.argv[2])
