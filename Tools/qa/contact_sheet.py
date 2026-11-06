"""Tile screenshots 2x2 into contact sheets with labels (run with ComfyUI's Python, which has PIL).

  python -I contact_sheet.py SHOT_DIR OUT_PREFIX [--cell 800x450]
"""
import argparse
import glob
import os

from PIL import Image, ImageDraw


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("shot_dir")
    ap.add_argument("out_prefix")
    ap.add_argument("--cell", default="800x450")
    a = ap.parse_args()
    cw, ch = (int(v) for v in a.cell.split("x"))
    shots = sorted(glob.glob(os.path.join(a.shot_dir, "*.png")))
    for sheet, start in enumerate(range(0, len(shots), 4)):
        canvas = Image.new("RGB", (cw * 2, ch * 2), (20, 20, 20))
        draw = ImageDraw.Draw(canvas)
        for i, path in enumerate(shots[start:start + 4]):
            img = Image.open(path).convert("RGB").resize((cw, ch), Image.LANCZOS)
            x, y = (i % 2) * cw, (i // 2) * ch
            canvas.paste(img, (x, y))
            label = os.path.splitext(os.path.basename(path))[0]
            draw.rectangle([x, y, x + 8 * len(label) + 10, y + 18], fill=(0, 0, 0))
            draw.text((x + 5, y + 3), label, fill=(255, 255, 0))
        out = f"{a.out_prefix}_{sheet + 1}.png"
        canvas.save(out)
        print(out)


if __name__ == "__main__":
    main()
