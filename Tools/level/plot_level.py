"""Offline orthographic sketches of L_Manor from instances.json (no rendering needed).

  python plot_level.py plan  <out.png> [zmin zmax]
  python plot_level.py elev  <out.png> <axis x|y> <coord> <depth> [lo hi]   (view of the wall plane, looking from +depth)
Colours come from the material name. Run with the ComfyUI venv python (PIL).
"""
import hashlib
import json
import os
import sys

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
data = json.load(open(os.path.join(HERE, "instances.json"), encoding="utf-8"))
INST = [i for i in data["instances"] if i["v"]]

FIXED = {"Plaster": (225, 214, 190), "Walnut": (110, 70, 45), "Mahogany": (130, 50, 35), "Wood_Dark": (60, 40, 30),
         "Oak": (190, 150, 100), "DamaskRed": (130, 20, 25), "DamaskGreen": (20, 90, 60), "NavyGold": (25, 30, 80),
         "FloralCream": (220, 205, 170), "Marble_White": (240, 240, 240), "Marble_Black": (20, 20, 20),
         "Marble_Green": (40, 110, 80), "Gold": (230, 180, 60), "Brass": (210, 160, 70), "Velvet_Red": (150, 20, 30),
         "Velvet_Green": (20, 80, 40), "Velvet_Gold": (180, 130, 40), "Velvet_Navy": (20, 25, 70),
         "Ivory": (235, 228, 205), "Glass": (150, 220, 230), "Iron": (40, 40, 45), "Carpet": (140, 25, 35),
         "Window": (40, 60, 120), "Painting": (90, 70, 40), "Checker": (180, 180, 180), "Parquet": (170, 120, 70),
         "Crystal": (250, 250, 255), "Bulb": (255, 230, 120), "Fire": (255, 120, 30), "Lacquer": (15, 15, 15),
         "Book": (120, 60, 40), "Foliage": (30, 90, 40), "Grass": (20, 50, 20), "Stone": (120, 115, 105)}


def colour(m):
    for k, v in FIXED.items():
        if k in m:
            return v
    h = hashlib.md5(m.encode()).digest()
    return (h[0], h[1], h[2])


def plan(out, zmin=0.0, zmax=180.0, s=0.18, region=(-200, -200, 6400, 4800)):
    x0, y0, x1, y1 = region
    W, H = int((x1 - x0) * s), int((y1 - y0) * s)
    img = Image.new("RGB", (W, H), (0, 0, 0))
    d = ImageDraw.Draw(img)
    items = [i for i in INST if i["hi"][2] > zmin and i["lo"][2] < zmax
             and max(i["hi"][0] - i["lo"][0], i["hi"][1] - i["lo"][1]) < 2500]     # skip sky dome / garden ground
    items.sort(key=lambda i: i["hi"][2])
    for i in items:
        lo, hi = i["lo"], i["hi"]
        a = ((lo[0] - x0) * s, (y1 - hi[1]) * s)
        b = ((hi[0] - x0) * s, (y1 - lo[1]) * s)
        d.rectangle([a, b], fill=colour(i["mat"]))
    img.save(out)
    print("plan", out, len(items))


def elev(out, axis, coord, depth, lo_a=None, hi_a=None, s=0.35, zmax=1050):
    # view a wall from the room side: axis 'x' means wall plane x = coord, room at x in [coord, coord+depth]
    sel = []
    for i in INST:
        k = 0 if axis == "x" else 1
        a, b = sorted((coord, coord + depth))
        if i["hi"][k] < a or i["lo"][k] > b:
            continue
        sel.append(i)
    k2 = 1 if axis == "x" else 0
    los = [i["lo"][k2] for i in sel]
    his = [i["hi"][k2] for i in sel]
    lo_a = min(los) if lo_a is None else lo_a
    hi_a = max(his) if hi_a is None else hi_a
    W, H = int((hi_a - lo_a) * s) + 1, int(zmax * s) + 1
    img = Image.new("RGB", (W, H), (0, 0, 0))
    d = ImageDraw.Draw(img)
    k = 0 if axis == "x" else 1
    # draw far to near (near = farther from the wall plane along +depth direction)
    sign = 1 if depth > 0 else -1
    sel.sort(key=lambda i: sign * (i["lo"][k] + i["hi"][k]) / 2)
    flip = (axis == "x" and depth > 0) or (axis == "y" and depth < 0)
    for i in sel:
        a0, a1 = i["lo"][k2], i["hi"][k2]
        if flip:
            a0, a1 = hi_a - a1 + lo_a, hi_a - a0 + lo_a
        p = ((a0 - lo_a) * s, (zmax - i["hi"][2]) * s)
        q = ((a1 - lo_a) * s, (zmax - i["lo"][2]) * s)
        d.rectangle([p, q], fill=colour(i["mat"]))
    img.save(out)
    print("elev", out, len(sel))


if __name__ == "__main__":
    mode, out = sys.argv[1], sys.argv[2]
    if mode == "plan":
        zmin, zmax = (float(sys.argv[3]), float(sys.argv[4])) if len(sys.argv) > 4 else (0.0, 180.0)
        plan(out, zmin, zmax)
    else:
        axis, coord, depth = sys.argv[3], float(sys.argv[4]), float(sys.argv[5])
        lo = float(sys.argv[6]) if len(sys.argv) > 6 else None
        hi = float(sys.argv[7]) if len(sys.argv) > 7 else None
        elev(out, axis, coord, depth, lo, hi)
