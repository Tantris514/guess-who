"""Image stats for QA shots (ComfyUI python: PIL + numpy).  imgstats.py dirA [dirB ...]
Per camera: mean sRGB luma, median, % near-black (<12), % clipped (>250), warmth (mean R-B), saturation."""
import glob, os, sys
import numpy as np
from PIL import Image

dirs = sys.argv[1:]
rows = {}
for d in dirs:
    for p in sorted(glob.glob(os.path.join(d, "*.png"))):
        a = np.asarray(Image.open(p).convert("RGB"), dtype=np.float32)
        y = 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]
        mx, mn = a.max(-1), a.min(-1)
        sat = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1), 0)
        rows.setdefault(os.path.basename(p)[:-4], []).append(
            f"{y.mean():5.1f} {np.median(y):5.1f} {100 * (y < 12).mean():4.0f}% {100 * (y > 250).mean():4.1f}% "
            f"{(a[..., 0] - a[..., 2]).mean():5.1f} {sat.mean():.2f}")
print(f"{'cam':22s} " + " | ".join(f"{os.path.basename(d):^34s}" for d in dirs))
print(f"{'':22s} " + " | ".join(f"{'mean   med  blk  clip   R-B  sat':34s}" for _ in dirs))
for k, v in rows.items():
    print(f"{k:22s} " + " | ".join(v))
