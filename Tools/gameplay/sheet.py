import sys, glob, os
from PIL import Image, ImageDraw
d = sys.argv[1]; idx = [int(x) for x in sys.argv[2].split(',')]; out = sys.argv[3]; cols = int(sys.argv[4]) if len(sys.argv) > 4 else 3
ims = [Image.open(os.path.join(d, f'shot_{i}.png')).convert('RGB') for i in idx]
w, h = 640, 360
rows = (len(ims) + cols - 1) // cols
sheet = Image.new('RGB', (cols * w, rows * h), 'black')
for k, (i, im) in enumerate(zip(idx, ims)):
    im = im.resize((w, h))
    ImageDraw.Draw(im).text((8, h - 18), f'shot_{i}', fill='yellow')
    sheet.paste(im, ((k % cols) * w, (k // cols) * h))
sheet.save(out)
