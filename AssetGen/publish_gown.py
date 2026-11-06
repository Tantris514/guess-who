"""Publish the skirt + bodice cut from gown_<colour> (after gown_split.py) as costume pieces.

  python -I -X utf8 publish_gown.py COLOUR "description" [COLOUR "description" ...]
The gown is taken as 150 cm from the shoulder straps to the floor; skirt and bodice sizes follow the waist cut.
"""
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
args = sys.argv[1:]
for c, desc in zip(args[::2], args[1::2]):
    res = json.load(open(os.path.join(ROOT, "models3d", f"skirt_{c}", "result.json"), encoding="utf-8"))
    fy = res["waist_fy"]
    meta = json.load(open(os.path.join(ROOT, "props_meta.json"), encoding="utf-8"))
    meta[f"skirt_{c}"]["ref"] = ["h", round(fy * 150)]
    meta[f"bodice_{c}"]["ref"] = ["h", round((1 - fy) * 150)]
    json.dump(meta, open(os.path.join(ROOT, "props_meta.json"), "w", encoding="utf-8"), indent=1)
    sel = json.load(open(os.path.join(ROOT, "selections.json"), encoding="utf-8"))
    concept = sel[f"gown_{c}"]
    common = (f" Cut from one TRELLIS gown (models3d/gown_{c}_trellis_s42/gown_{c}.glb, also usable whole) at the waist"
              f" ({round(fy * 150)} cm above the hem): skirt and bodice of the same colour meet exactly at the cut."
              " The cut edge is slightly jagged and open (hollow shell, double-sided material): hide it under the other piece"
              " or the character's waist. Rigid shell, no skinning. Front +Z, up +Y.")
    for part, text in (("skirt", f"Floor-length bias-cut evening skirt, {desc}. Attach to the pelvis bone; the waist opening is at the top (glTF y=max)."),
                       ("bodice", f"Sleeveless gown bodice with cap shoulders and open armholes, {desc}. Attach to the upper spine/chest; the waist edge is at the bottom (glTF y=min).")):
        subprocess.run([sys.executable, "-I", "-X", "utf8", os.path.join(ROOT, "approve_model.py"), f"{part}_{c}",
                        os.path.join("models3d", f"{part}_{c}"), "--front", "+Z", "--concept", concept,
                        "--notes", text + common], check=True)
