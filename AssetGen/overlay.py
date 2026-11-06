"""overlay.py OUT.png TEMPLATE.png DIR seed [seed...]: generated image + mask overlay (grey both, red template only, blue gen only)."""
import sys

import numpy as np
from PIL import Image

out, tplp, d = sys.argv[1], sys.argv[2], sys.argv[3]
tpl = np.asarray(Image.open(tplp).convert("RGB")).mean(-1) > 12
tiles = []
for s in sys.argv[4:]:
    g = Image.open(f"{d}/gen_s{s}.png").convert("RGB")
    m = np.asarray(Image.open(f"{d}/mask_s{s}.png")) > 127
    ov = np.zeros(tpl.shape + (3,), np.uint8)
    ov[tpl & m] = (200, 200, 200)
    ov[tpl & ~m] = (255, 0, 0)
    ov[~tpl & m] = (0, 120, 255)
    tiles += [g.resize((400, 600)), Image.fromarray(ov).resize((400, 600))]
sheet = Image.new("RGB", (400 * len(tiles), 600), (255, 255, 255))
for i, t in enumerate(tiles):
    sheet.paste(t, (i * 400, 0))
sheet.save(out)
