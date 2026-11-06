"""Seamless + normal + roughness for the selected tileable textures and wallpapers, plus 2x2 previews.

  V:/ComfyUI/ComfyUI/ComfyUI/.venv/Scripts/python.exe -I process_textures.py [names...]
Reads the chosen source image from selections.json; writes textures/final/<name>_basecolor|_normal|_roughness.png,
qa/tile_<name>.png (2x2 preview) and textures/final/<name>_info.json (seam stats, tile aspect).
"""
import json
import os
import sys

import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
import texture_tools as tt  # noqa: E402

# name: (flatten, periodic, normal strength, roughness base, roughness range)
PARAMS = {
    "tex_wood_walnut":    (0.5, False, 1.5, 0.35, 0.20),
    "tex_wood_oak":       (0.5, False, 1.5, 0.45, 0.20),
    "tex_wood_mahogany":  (0.5, False, 1.5, 0.35, 0.20),
    "tex_marble_white":   (0.6, False, 0.6, 0.12, 0.10),
    "tex_marble_black":   (0.6, False, 0.6, 0.10, 0.10),
    "tex_marble_green":   (0.6, False, 0.8, 0.15, 0.10),
    "tex_plaster_cream":  (0.8, False, 2.5, 0.85, 0.15),
    "tex_velvet_red":     (0.7, False, 2.0, 0.90, 0.20),
    "tex_carpet_red":     (0.8, True, 3.0, 0.95, 0.10),
    "tex_gold_leaf":      (0.6, False, 2.0, 0.30, 0.30),
    "tex_brass":          (1.0, False, 0.8, 0.30, 0.30),
    "tex_parquet_chevron": (0.6, True, 2.0, 0.35, 0.25),
    "wall_damask_green":  (1.0, True, 1.0, 0.70, 0.40),
    "wall_damask_red":    (1.0, True, 1.0, 0.70, 0.40),
    "wall_floral_cream":  (1.0, True, 1.0, 0.70, 0.40),
    "wall_navy_gold":     (1.0, True, 1.0, 0.70, 0.40),
}

# wider feather where grain lines drift (a hard cut across them shows as a jagged line)
FEATHER = {"tex_wood_walnut": 14, "tex_wood_oak": 14, "tex_wood_mahogany": 14, "tex_velvet_red": 8, "tex_gold_leaf": 8}

# tone band blur: patterns need a wide blur, or blurred motifs get cross-faded (ghosts)
SIGMA = {"wall_damask_green": 48.0, "wall_damask_red": 48.0, "wall_floral_cream": 48.0, "wall_navy_gold": 48.0,
         "tex_parquet_chevron": 40.0, "tex_brass": 40.0, "tex_carpet_red": 40.0}


def main():
    sel = json.load(open(os.path.join(ROOT, "selections.json"), encoding="utf-8"))
    names = sys.argv[1:] or [n for n in PARAMS if n in sel]
    out_dir = os.path.join(ROOT, "textures", "final")
    os.makedirs(out_dir, exist_ok=True)
    for name in names:
        flat, periodic, strength, rbase, rrange = PARAMS[name]
        src = os.path.join(ROOT, sel[name])
        img = tt.load(src)
        feather = FEATHER.get(name, 3)
        sigma = SIGMA.get(name, 12.0)
        pc = name.startswith("wall_") or name == "tex_brass"
        tile, info = tt.seamless(img, 1024, 200 if feather > 3 else 160, flat, periodic, feather, sigma, pc, 9.0 if pc else 6.0)
        info["flatten_per_channel"] = pc
        info["seam_feather_px"] = feather
        info["tone_band_sigma_px"] = sigma
        base = os.path.join(out_dir, name)
        tt.save(tile, base + "_basecolor.png")
        tt.save(tt.normal_map(tile, strength), base + "_normal.png")
        tt.save(tt.roughness_map(tile, rbase, rrange), base + "_roughness.png")
        tt.save(tt.preview(np.asarray(Image.fromarray((tile * 255).astype(np.uint8)).resize((512, 512), Image.LANCZOS)).astype(np.float32) / 255.0),
                os.path.join(ROOT, "qa", f"tile_{name}.png"))
        info.update(source=sel[name], normal_strength=strength, roughness_base=rbase)
        with open(base + "_info.json", "w", encoding="utf-8") as f:
            json.dump(info, f, indent=1)
        print(name, json.dumps(info))


if __name__ == "__main__":
    main()
