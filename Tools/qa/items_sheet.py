"""Contact sheet of screenshots: items_sheet.py out.png first_number count [columns] [cell width]. Labels are the shot numbers."""
import sys
from PIL import Image, ImageDraw
out, first, n = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
cols = int(sys.argv[4]) if len(sys.argv) > 4 else 3
W = int(sys.argv[5]) if len(sys.argv) > 5 else 640
H = W * 9 // 16
D = r'J:\Projets\Unreal_Projects\Guess Who\GuessWho\Saved\Screenshots\WindowsEditor'
rows = (n + cols - 1) // cols
s = Image.new('RGB', (W * cols, H * rows), 'black')
d = ImageDraw.Draw(s)
for i in range(n):
    k = first + i
    im = Image.open(f'{D}\\ScreenShot{k:05d}.png').convert('RGB').resize((W, H))
    s.paste(im, ((i % cols) * W, (i // cols) * H))
    d.text(((i % cols) * W + 6, (i // cols) * H + 6), str(k), fill='yellow')
s.save(out)
