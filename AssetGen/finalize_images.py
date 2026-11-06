"""Copy selected paintings / rugs / window / keyart into paintings/final (rugs are cropped to the rug edge).

  V:/ComfyUI/ComfyUI/ComfyUI/.venv/Scripts/python.exe -I finalize_images.py NAME [NAME...]
Writes paintings/final/<name>.png and prints the final size.
"""
import json
import os
import sys

import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "paintings", "final")


def crop_to_object(img, thresh=40, inset=4):
    a = np.asarray(img.convert("RGB")).astype(np.int32)
    corners = np.concatenate([a[:8, :8].reshape(-1, 3), a[:8, -8:].reshape(-1, 3), a[-8:, :8].reshape(-1, 3), a[-8:, -8:].reshape(-1, 3)])
    bg = np.median(corners, axis=0)
    diff = np.abs(a - bg).sum(axis=-1) > thresh
    rows = np.where(diff.mean(axis=1) > 0.5)[0]   # rows/cols mostly covered by the rug
    cols = np.where(diff.mean(axis=0) > 0.5)[0]
    if len(rows) == 0 or len(cols) == 0:
        return img
    return img.crop((int(cols[0]) + inset, int(rows[0]) + inset, int(cols[-1]) + 1 - inset, int(rows[-1]) + 1 - inset))


def main():
    sel = json.load(open(os.path.join(ROOT, "selections.json"), encoding="utf-8"))
    os.makedirs(OUT, exist_ok=True)
    for name in sys.argv[1:]:
        img = Image.open(os.path.join(ROOT, sel[name])).convert("RGB")
        if name.startswith("rug_"):
            img = crop_to_object(img)
        dst = os.path.join(OUT, f"{name}.png")
        img.save(dst)
        print(name, img.size)


if __name__ == "__main__":
    main()
