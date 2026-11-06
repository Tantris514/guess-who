"""One row per model: concept | front | back34 | side | front34_normal.  Writes qa/<out>.png

  V:/ComfyUI/ComfyUI/ComfyUI/.venv/Scripts/python.exe -I qa_models.py OUT name=model_dir [name=model_dir ...]
"""
import json
import os
import sys

from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.abspath(__file__))
T = 300
out = sys.argv[1]
rows = [a.split("=", 1) for a in sys.argv[2:]]
sheet = Image.new("RGB", (6 * T, len(rows) * (T + 16)), (255, 255, 255))
d = ImageDraw.Draw(sheet)
for r, (name, mdir) in enumerate(rows):
    mdir = os.path.join(ROOT, mdir)
    res = {}
    if os.path.exists(os.path.join(mdir, "result.json")):
        res = json.load(open(os.path.join(mdir, "result.json"), encoding="utf-8"))
    concept = res.get("image", "")
    if concept and not os.path.isabs(concept):
        concept = os.path.join(ROOT, concept)
    paths = [concept] + [os.path.join(mdir, f"qa_{v}.png") for v in ("front", "back34", "side", "front34_normal", "top34")]
    y = r * (T + 16)
    d.text((3, y + 2), f"{name}  {res.get('seconds', '?')} s  seed {res.get('seed', '?')}", fill=(0, 0, 0))
    for c, p in enumerate(paths):
        if p and os.path.exists(p):
            im = Image.open(p).convert("RGB")
            im.thumbnail((T, T))
            sheet.paste(im, (c * T + (T - im.width) // 2, y + 16))
sheet.save(os.path.join(ROOT, "qa", out + ".png"))
print("wrote", out, sheet.size)
