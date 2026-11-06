"""Crops of screenshots: crop_sheet.py out.png cols cellw number:x0,y0,x1,y1 ... (coordinates in the 1600x900 shot)."""
import sys
from PIL import Image, ImageDraw
out, cols, W = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
items = sys.argv[4:]
D = r'J:\Projets\Unreal_Projects\Guess Who\GuessWho\Saved\Screenshots\WindowsEditor'
H = W * 9 // 16
rows = (len(items) + cols - 1) // cols
s = Image.new('RGB', (W * cols, H * rows), 'black')
d = ImageDraw.Draw(s)
for i, it in enumerate(items):
    k, box = it.split(':')
    im = Image.open(f'{D}\\ScreenShot{int(k):05d}.png').convert('RGB')
    x0, y0, x1, y1 = [int(v) * im.width // 1600 for v in box.split(',')]
    im = im.crop((x0, y0, x1, y1))
    im.thumbnail((W, H))
    s.paste(im, ((i % cols) * W, (i // cols) * H))
    d.text(((i % cols) * W + 6, (i // cols) * H + 6), k, fill='yellow')
s.save(out)
