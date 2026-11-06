"""Contact sheet: sheet.py OUT.png W file1 file2 ... (thumbnails W px wide, labelled)."""
import os, sys
from PIL import Image, ImageDraw
out, W = sys.argv[1], int(sys.argv[2])
files = sys.argv[3:]
ims = []
for f in files:
    im = Image.open(f).convert("RGBA")
    h = int(im.height * W / im.width)
    bg = Image.new("RGBA", im.size, (40, 90, 40, 255))  # green shows transparency
    bg.alpha_composite(im)
    ims.append((os.path.basename(f), bg.convert("RGB").resize((W, h), Image.LANCZOS)))
cols = max(1, min(len(ims), 1600 // W))
rows = (len(ims) + cols - 1) // cols
rh = max(i.height for _, i in ims) + 18
sheet = Image.new("RGB", (cols * (W + 6), rows * rh), (20, 20, 20))
d = ImageDraw.Draw(sheet)
for k, (n, im) in enumerate(ims):
    x, y = (k % cols) * (W + 6), (k // cols) * rh
    sheet.paste(im, (x, y + 16))
    d.text((x + 2, y + 2), n[:48], fill=(230, 230, 230))
sheet.save(out)
print(sheet.size)
