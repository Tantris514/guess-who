"""Contact sheet: sheet.py OUT.png TILE COLS img1 img2 ... (labels = file basenames or name=path)."""
import os
import sys

from PIL import Image, ImageDraw

out, tile, cols = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
items = []
for a in sys.argv[4:]:
    if "=" in a and not os.path.exists(a):
        label, path = a.split("=", 1)
    else:
        label, path = os.path.basename(a), a
    items.append((label, path))
rows = (len(items) + cols - 1) // cols
sheet = Image.new("RGB", (cols * tile, rows * (tile + 18)), (255, 255, 255))
d = ImageDraw.Draw(sheet)
for i, (label, path) in enumerate(items):
    im = Image.open(path).convert("RGB")
    im.thumbnail((tile, tile))
    x, y = (i % cols) * tile, (i // cols) * (tile + 18)
    sheet.paste(im, (x + (tile - im.width) // 2, y + 18))
    d.text((x + 3, y + 3), label[:40], fill=(0, 0, 0))
sheet.save(out)
print("sheet", out, sheet.size)
