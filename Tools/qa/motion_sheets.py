"""One sheet per outfit from a shot_motion.ps1 run: 6 side frames over 6 front frames, cropped on the walker.

  python -I motion_sheets.py MOTION_DIR [--crop 420] [--cell 210x360]
"""
import argparse
import glob
import os
import re

from PIL import Image, ImageDraw


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("motion_dir")
    ap.add_argument("--crop", type=int, default=420, help="width of the centre crop in source pixels")
    ap.add_argument("--cell", default="210x360")
    a = ap.parse_args()
    cw, chh = (int(v) for v in a.cell.split("x"))
    frames = {}
    for p in glob.glob(os.path.join(a.motion_dir, "k*_*_f*.png")):
        m = re.match(r"k(\d+)_(side|front)_f(\d+)\.png", os.path.basename(p))
        if m:
            frames.setdefault(int(m.group(1)), {}).setdefault(m.group(2), []).append((int(m.group(3)), p))
    out_dir = os.path.join(a.motion_dir, "sheets")
    os.makedirs(out_dir, exist_ok=True)
    for k in sorted(frames):
        sheet = Image.new("RGB", (cw * 6, chh * 2), (20, 20, 20))
        d = ImageDraw.Draw(sheet)
        for row, view in enumerate(("side", "front")):
            for col, (f, p) in enumerate(sorted(frames[k].get(view, []))[:6]):
                im = Image.open(p).convert("RGB")
                w, h = im.size
                x0 = (w - a.crop) // 2
                sheet.paste(im.crop((x0, 0, x0 + a.crop, h)).resize((cw, chh)), (col * cw, row * chh))
                d.text((col * cw + 4, row * chh + 3), f"k{k} {view} f{f}", fill=(255, 255, 0))
        sheet.save(os.path.join(out_dir, f"k{k:02d}.png"))
    print(f"{len(frames)} sheets in {out_dir}")


if __name__ == "__main__":
    main()
