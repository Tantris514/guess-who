"""Publish finished 2D images (paintings, rugs, window view, key art) from paintings/final in manifest.json.

  python -I -X utf8 approve_images.py NAME [NAME...]
"""
import json
import os
import struct
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
FINAL = os.path.join(ROOT, "paintings", "final")

PORTRAIT_ROOMS = ["dining", "hall", "corridor_w", "corridor_e"]
LANDSCAPE_ROOMS = ["corridor_w", "corridor_e", "library", "billiard", "study", "ballroom"]
# name: (kind, real width cm (long side for paintings), rooms, description)
META = {
    "rug_persian": ("rug", 300, ["library", "study", "hall", "dining"], "Persian rug, red field, navy border, ivory medallion"),
    "rug_artdeco": ("rug", 300, ["ballroom", "billiard", "hall"], "Art Deco rug, black/gold/cream geometric"),
    "rug_runner": ("rug", 300, ["corridor_w", "corridor_e"], "long Persian hallway runner"),
    "window_night": ("window", 160, ["hall", "ballroom", "dining", "library", "billiard", "study", "conservatory"],
                     "rainy moonlit formal garden seen through the windows (backdrop plane / emissive material behind window glass)"),
    "keyart": ("keyart", 0, [], "main menu key art: masquerade ball in the manor hall (no text; leave room for the title)"),
    "keyart_alt": ("keyart", 0, [], "alternative key art (same scene, different composition)"),
    "paint_lord": ("painting", 100, PORTRAIT_ROOMS, "portrait: aristocratic lord in white tie"),
    "paint_lady": ("painting", 100, PORTRAIT_ROOMS, "portrait: lady in silver evening gown with pearls"),
    "paint_colonel": ("painting", 100, PORTRAIT_ROOMS, "portrait: old colonel in red dress uniform"),
    "paint_dowager": ("painting", 100, PORTRAIT_ROOMS, "portrait: dowager duchess in black silk"),
    "paint_heir": ("painting", 100, PORTRAIT_ROOMS, "portrait: young heir in tweed, autumn landscape"),
    "paint_hunt": ("painting", 140, LANDSCAPE_ROOMS, "fox hunt landscape"),
    "paint_sea": ("painting", 140, LANDSCAPE_ROOMS, "sailing ship in a storm"),
    "paint_country": ("painting", 140, LANDSCAPE_ROOMS, "English countryside at golden hour"),
    "paint_horse": ("painting", 120, LANDSCAPE_ROOMS, "racehorse held by a groom"),
    "paint_stilllife": ("painting", 90, ["dining", "corridor_w", "corridor_e"], "Dutch-style still life with flowers and pheasant"),
    "paint_venice": ("painting", 120, LANDSCAPE_ROOMS, "Grand Canal, Venice"),
    "paint_manor": ("painting", 140, LANDSCAPE_ROOMS + ["hall"], "Georgian manor house (the family seat)"),
    "paint_artdeco": ("painting", 100, ["ballroom", "corridor_e", "study"], "Art Deco woman with a greyhound"),
    "paint_mountains": ("painting", 140, LANDSCAPE_ROOMS, "Scottish highlands with a stag"),
}


def png_size(path):
    with open(path, "rb") as f:
        head = f.read(24)
    return struct.unpack(">II", head[16:24])


def main():
    sel = json.load(open(os.path.join(ROOT, "selections.json"), encoding="utf-8"))
    entries = []
    for name in sys.argv[1:]:
        kind, cm, rooms, desc = META[name]
        img = os.path.join(FINAL, f"{name}.png")
        w, h = png_size(img)
        notes = [desc + "."]
        if kind == "rug":
            size = [cm, round(cm * h / w), 1]
            notes.append("size_cm = [length, width, thickness]; image is cropped to the rug edge, lay it flat on the floor.")
        elif kind == "painting":
            long_side = cm
            size = [round(long_side * w / max(w, h)), 4, round(long_side * h / max(w, h))]
            notes.append("size_cm = canvas [width, depth, height] without frame; image aspect is preserved.")
        elif kind == "window":
            size = [cm, 0, round(cm * h / w)]
            notes.append("size_cm = suggested backdrop plane [width, 0, height] behind a window; use unlit/emissive at low intensity.")
        else:
            size = [0, 0, 0]
            notes.append("2D UI image, %dx%d; size_cm not applicable." % (w, h))
        entry = {"name": name, "kind": kind, "status": "approved",
                 "files": {"image": img, "source": os.path.join(ROOT, sel.get(name, ""))},
                 "size_cm": size, "rooms": rooms, "pixels": [w, h], "notes": " ".join(notes)}
        entries.append(entry)
    tmp = os.path.join(ROOT, "qa", "_entries_img.json")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=1)
    subprocess.run([sys.executable, "-I", "-X", "utf8", os.path.join(ROOT, "manifest_tool.py"), "upsert", tmp], check=True)
    os.remove(tmp)


if __name__ == "__main__":
    main()
