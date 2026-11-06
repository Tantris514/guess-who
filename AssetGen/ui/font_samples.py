"""Render a sample sheet of candidate local fonts (French text with accents) for visual choice."""
import os, sys
from PIL import Image, ImageDraw, ImageFont
R = r"V:\backup\J drive\Videos\ChromeMDP Python\WINpython\WPy64-31150\python-3.11.5.amd64\Lib\site-packages\panel\dist\bundled\reveal.js@4.5.0\dist\theme\fonts"
M = r"V:\ComfyUI\ComfyUI\ComfyUI\.venv\Lib\site-packages\matplotlib\mpl-data\fonts\ttf"
C = [
    ("League Gothic", os.path.join(R, "league-gothic", "league-gothic.ttf")),
    ("Source Sans Pro", os.path.join(R, "source-sans-pro", "source-sans-pro-regular.ttf")),
    ("Source Sans Pro SemiBold", os.path.join(R, "source-sans-pro", "source-sans-pro-semibold.ttf")),
    ("STIX General", os.path.join(M, "STIXGeneral.ttf")),
    ("STIX General Bold", os.path.join(M, "STIXGeneralBol.ttf")),
    ("STIX Italic", os.path.join(M, "STIXGeneralItalic.ttf")),
    ("DejaVu Serif", os.path.join(M, "DejaVuSerif.ttf")),
    ("DejaVu Sans Mono", os.path.join(M, "DejaVuSansMono.ttf")),
]
img = Image.new("RGB", (1800, 130 * len(C) + 40), (12, 10, 8))
d = ImageDraw.Draw(img)
y = 20
for name, path in C:
    f = ImageFont.truetype(path, 56)
    s = ImageFont.truetype(path, 26)
    d.text((20, y), "LE BAL MASQUÉ · DÉTECTIVE · INVITÉ", font=f, fill=(214, 170, 90))
    d.text((20, y + 66), f"{name}: Fondez-vous parmi les invités… Héberger, Rejoindre, Échap, « Que la chasse commence ! » 0123456789", font=s, fill=(236, 228, 210))
    y += 130
img.save(sys.argv[1])
print("ok")
