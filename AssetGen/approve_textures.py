"""Publish processed tileable textures / wallpapers (textures/final/*) in manifest.json.

  python -I -X utf8 approve_textures.py NAME [NAME...]
"""
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
FINAL = os.path.join(ROOT, "textures", "final")

# name: (kind, tile size in cm [w, h], metallic, rooms, use)
META = {
    "tex_wood_walnut":   ("texture_tileable", [60, 60], 0, ["library", "dining", "hall", "corridor_w", "corridor_e"], "walnut panelling / wainscot / library walls (grain runs vertically)"),
    "tex_wood_mahogany": ("texture_tileable", [60, 60], 0, ["ballroom", "billiard", "study"], "mahogany wainscot and panelling (grain runs vertically)"),
    "tex_wood_oak":      ("texture_tileable", [120, 120], 0, ["study"], "honey oak boards (horizontal planks); spare wood, e.g. doors, floors of service areas"),
    "tex_marble_white":  ("texture_tileable", [100, 100], 0, ["hall", "corridor_w", "corridor_e", "conservatory"], "white Carrara marble: checker floor tiles (with tex_marble_black), fireplace, columns"),
    "tex_marble_black":  ("texture_tileable", [100, 100], 0, ["hall", "corridor_w", "corridor_e", "conservatory"], "black Nero Marquina marble: checker floor tiles, plinths"),
    "tex_marble_green":  ("texture_tileable", [100, 100], 0, ["hall", "ballroom"], "verde antico marble: columns, fireplace inlays, plinths"),
    "tex_plaster_cream": ("texture_tileable", [200, 200], 0, ["hall"], "cream painted plaster: hall walls and every ceiling"),
    "tex_velvet_red":    ("texture_tileable", [50, 50], 0, ["ballroom", "dining"], "crimson crushed velvet: curtains, upholstery, stage skirt"),
    "tex_carpet_red":    ("texture_tileable", [80, 80], 0, ["billiard"], "burgundy wall-to-wall carpet with small gold motif"),
    "tex_gold_leaf":     ("texture_tileable", [40, 40], 1, ["ballroom", "hall"], "gilding: frames, ceiling coffer mouldings, trims (metallic)"),
    "tex_brass":         ("texture_tileable", [40, 40], 1, [], "antique brass: rails, fittings, trims (metallic)"),
    "tex_parquet_chevron": ("texture_tileable", [120, 120], 0, ["dining", "library", "ballroom", "study"], "point de Hongrie (chevron) oak parquet floor"),
    "wall_damask_green": ("wallpaper", [70, 70], 0, ["ballroom"], "Art Deco emerald and gold fan wallpaper"),
    "wall_damask_red":   ("wallpaper", [70, 70], 0, ["dining", "study"], "oxblood damask wallpaper"),
    "wall_floral_cream": ("wallpaper", [70, 70], 0, ["corridor_e"], "cream chinoiserie bird-and-branch wallpaper"),
    "wall_navy_gold":    ("wallpaper", [70, 70], 0, ["billiard", "corridor_w"], "navy Art Deco wallpaper with gold lines and diamonds"),
}


def main():
    entries = []
    for name in sys.argv[1:]:
        kind, tile, metallic, rooms, use = META[name]
        info = json.load(open(os.path.join(FINAL, f"{name}_info.json"), encoding="utf-8"))
        aspect = info.get("tile_aspect_w_over_h", 1.0)
        tile_cm = [tile[0], round(tile[1] / aspect)] if abs(aspect - 1.0) > 0.02 else tile
        notes = [use + ".",
                 "size_cm = real-world size covered by ONE repeat of the texture: [width, height, 0].",
                 "Normal map: DirectX/UE convention (green down), derived from luminance. Roughness map is greyscale (R=G=B).",
                 f"Metallic = {metallic}."]
        if abs(aspect - 1.0) > 0.02:
            notes.append(f"The square image holds a pattern repeat whose true aspect is {aspect} (w/h): use UV scale U:V = 1:{round(1/aspect, 3)} (already reflected in size_cm).")
        if info.get("qa_note"):
            notes.append(info["qa_note"])
        entries.append({
            "name": name, "kind": kind, "status": "approved",
            "files": {"basecolor": os.path.join(FINAL, f"{name}_basecolor.png"),
                      "normal": os.path.join(FINAL, f"{name}_normal.png"),
                      "roughness": os.path.join(FINAL, f"{name}_roughness.png"),
                      "preview_2x2": os.path.join(ROOT, "qa", f"tile_{name}.png"),
                      "source": os.path.join(ROOT, info["source"])},
            "size_cm": [tile_cm[0], tile_cm[1], 0],
            "rooms": rooms,
            "material": {"metallic": metallic, "roughness_base": info.get("roughness_base"), "resolution": 1024},
            "notes": " ".join(notes),
        })
    tmp = os.path.join(ROOT, "qa", "_entries_tex.json")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=1)
    subprocess.run([sys.executable, "-I", "-X", "utf8", os.path.join(ROOT, "manifest_tool.py"), "upsert", tmp], check=True)
    os.remove(tmp)


if __name__ == "__main__":
    main()
