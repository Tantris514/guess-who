"""Dressing, gameplay markers, review cameras and navigation for L_Manor (imported by build_manor.py).

Props: every approved `prop` of AssetGen/manifest.json is imported once (Interchange glTF) into
/Game/GW/Meshes/Props/<name>/, its material is replaced by an MI of M_GW_Prop (no Interchange plugin content
needed at runtime), Nanite + box collision are enabled, and it is scaled to size_cm and oriented using the
manifest orientation (front +Z glTF -> +Y UE). Each furniture slot uses the prop when it exists, otherwise a
procedural placeholder (boxes / lathe shapes) so the rooms are playable before the props arrive.
Props that are still being generated get reserved slots (slot(..., fit=(w, d, h)) / R(...) in build_dress): nothing is
placed until they are approved, but their footprints go to dress_state.json "reserved" and are kept free by the
markers, audit_furniture.py, lanes_check.py and validate_walls.py; once approved they are shrunk to fit if needed.
"""
import json
import math
import os
import random

import unreal

import lvl_common
from lvl_build import Batch, spawn, point_light, spot_light, target_point, eas, tag_actor

ROOT = lvl_common.ROOT
PROPS_DIR = "/Game/GW/Meshes/Props"
STATE_PATH = os.path.join(ROOT, "Tools", "level", "props_state.json")
eal = unreal.EditorAssetLibrary
FOOT = []          # (x0, y0, x1, y1, label, top, base) collision footprints (markers / wall decor / audits)
LAST = {"center": (0.0, 0.0)}   # centre of the last placed slot (for things put on top of it)
CANDLES = []       # candelabra flame positions (written to light_spots.json for the lighting agent)
LAMPS = []         # (x, y, z, cd, radius)
PLACED = {"props": {}, "fallback": {}, "rooms": {}, "waiting": {}}   # waiting: slots with no prop and no fallback
# footprints kept free for props that are not generated yet (slot(..., fit=(w, d, h))): world AABB
# (x0, y0, x1, y1, name, top, base, placed). Markers, audits and the lanes check treat the unplaced ones as furniture.
RESERVED = []
PIANO = []         # GW_Piano interaction point: [x, y, z, yaw] (stage floor ~90 cm in front of the keys)
INSTRUMENTS = []   # [tag, x, y, z, yaw]: GW_Instrument_* interaction points, 90 cm from the musician's side
# small things that must stand on furniture (table, console, sideboard, desk, bar, piano lid, dedicated stand), never
# on the floor: audit_furniture.py checks every one of them has a supporting top under its centre
TABLETOP = ("lamp_table", "gramophone", "radio_cathedral", "typewriter", "telephone", "candelabra", "vase_flowers")


def play_point(tag, x, y, z, face, half_depth, musician_side="front"):
    """Interaction point 90 cm out from the instrument's footprint on the musician's side, facing the instrument."""
    sgn = 1.0 if musician_side == "front" else -1.0
    d = sgn * (half_depth + 90.0)
    px = x + math.cos(math.radians(face)) * d
    py = y + math.sin(math.radians(face)) * d
    INSTRUMENTS.append([tag, round(px, 1), round(py, 1), z, round((face + (180.0 if sgn > 0 else 0.0)) % 360.0, 1)])


def reserve(name, x, y, face, w, d, h, z=0.0, placed=False):
    """Record the footprint (w across the front, d front-to-back, h) centred on (x, y), front facing `face`."""
    r = math.radians(face - 90.0)
    c, s = math.cos(r), math.sin(r)
    pts = [(x + lx * c - ly * s, y + lx * s + ly * c) for lx in (-w / 2, w / 2) for ly in (-d / 2, d / 2)]
    RESERVED.append((round(min(p[0] for p in pts), 1), round(min(p[1] for p in pts), 1),
                     round(max(p[0] for p in pts), 1), round(max(p[1] for p in pts), 1), name, z + h, z, bool(placed)))


# ------------------------------------------------------------------ prop import
def _front_angle(orient):
    f = (orient or {}).get("front", "+Z")
    f = f.strip().split()[0].upper()
    return {"+Z": 90.0, "-Z": -90.0, "+X": 0.0, "-X": 180.0}.get(f, 90.0)


def classify_textures(texs):
    bc = next((x for x in texs if x.get_editor_property("srgb")), None)
    nm = next((x for x in texs if x.get_editor_property("compression_settings") ==
               unreal.TextureCompressionSettings.TC_NORMALMAP), None)
    mr = next((x for x in texs if x is not bc and x is not nm), None)
    return bc, mr, nm


def fix_prop_textures(dest):
    """Force texture settings that match M_GW_Prop's samplers (Color / LinearColor / Normal)."""
    texs = [o for o in (unreal.load_asset(p) for p in eal.list_assets(dest, recursive=True))
            if isinstance(o, unreal.Texture2D)]
    bc, mr, nm = classify_textures(texs)
    TC = unreal.TextureCompressionSettings
    for tex, srgb, comp in ((bc, True, TC.TC_DEFAULT), (mr, False, TC.TC_DEFAULT), (nm, False, TC.TC_NORMALMAP)):
        if tex and (tex.get_editor_property("srgb") != srgb or tex.get_editor_property("compression_settings") != comp):
            tex.set_editor_property("srgb", srgb)
            tex.set_editor_property("compression_settings", comp)
            eal.save_loaded_asset(tex)


def import_props():
    man = lvl_common.load_manifest()
    try:
        state = json.load(open(STATE_PATH, encoding="utf-8"))
    except (OSError, ValueError):
        state = {}
    tools = unreal.AssetToolsHelpers.get_asset_tools()
    mel = unreal.MaterialEditingLibrary
    sms = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    master = unreal.load_asset("/Game/GW/Materials/Master/M_GW_Prop")
    for key, a in man.items():
        if a.get("kind") != "prop":
            continue
        glb = lvl_common.file_of(a, "glb")
        if not glb:
            continue
        stamp = f"{glb}|{int(os.path.getmtime(glb))}"
        st = state.get(key)
        if st and st.get("stamp") == stamp and eal.does_asset_exist(st["mesh"]):
            st["size_cm"] = a.get("size_cm")
            st["front"] = _front_angle(a.get("orientation"))
            fix_prop_textures(f"{PROPS_DIR}/{key}")
            continue
        dest = f"{PROPS_DIR}/{key}"
        t = unreal.AssetImportTask()
        t.filename = glb
        t.destination_path = dest
        t.automated = True
        t.replace_existing = True
        t.save = False
        tools.import_asset_tasks([t])
        mesh, texs, mis = None, [], []
        for p in eal.list_assets(dest, recursive=True):
            o = unreal.load_asset(p)
            if isinstance(o, unreal.StaticMesh):
                mesh = o
            elif isinstance(o, unreal.Texture2D):
                texs.append(o)
            elif isinstance(o, unreal.MaterialInterface) and not o.get_name().startswith("MI_GW_Prop"):
                mis.append(o)
        if mesh is None:
            print("  !! no mesh imported for", key)
            continue
        bc, mr, nm = classify_textures(texs)
        fix_prop_textures(dest)
        mi_path = f"{dest}/MI_GW_Prop_{key}"
        mi = unreal.load_asset(mi_path) if eal.does_asset_exist(mi_path) else tools.create_asset(
            f"MI_GW_Prop_{key}", dest, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
        mel.set_material_instance_parent(mi, master)
        for pname, tex in (("BaseColor", bc), ("MetalRough", mr), ("Normal", nm)):
            if tex:
                mel.set_material_instance_texture_parameter_value(mi, pname, tex)
        if not mr:
            mel.set_material_instance_scalar_parameter_value(mi, "MetallicScale", 0.0)
        mel.update_material_instance(mi)
        eal.save_loaded_asset(mi)
        for i in range(len(mesh.static_materials)):
            mesh.set_material(i, mi)
        ns = mesh.get_editor_property("nanite_settings")
        ns.set_editor_property("enabled", True)
        mesh.set_editor_property("nanite_settings", ns)
        sms.remove_collisions(mesh)
        sms.add_simple_collisions(mesh, unreal.ScriptCollisionShapeType.BOX)
        eal.save_loaded_asset(mesh)
        for m in mis:
            eal.delete_loaded_asset(m)
        for x in texs:
            eal.save_loaded_asset(x)
        bb = mesh.get_bounding_box()
        state[key] = dict(stamp=stamp, mesh=mesh.get_path_name().split(".")[0], lo=[bb.min.x, bb.min.y, bb.min.z],
                          hi=[bb.max.x, bb.max.y, bb.max.z], size_cm=a.get("size_cm"),
                          front=_front_angle(a.get("orientation")), rooms=a.get("rooms", []))
        print("  imported prop", key)
    with open(STATE_PATH, "w", encoding="utf-8") as fh:
        json.dump(state, fh, indent=1)
    return state


# ------------------------------------------------------------------ local frame for placing furniture
class LF:
    """Local frame: origin (x, y), front facing `face` degrees (0 = +X, 90 = +Y). Local +Y = front."""

    def __init__(self, b, g, x, y, face, z=0.0):
        self.b, self.g, self.x, self.y, self.z = b, g, x, y, z
        self.yaw = face - 90.0
        r = math.radians(self.yaw)
        self.c, self.s = math.cos(r), math.sin(r)

    def p(self, lx, ly, z=0.0):
        return (self.x + lx * self.c - ly * self.s, self.y + lx * self.s + ly * self.c, self.z + z)

    def box(self, matn, lx0, lx1, ly0, ly1, z0, z1, coll=False, shadow=True, mesh="SM_GW_Cube"):
        self.b.add(self.g, mesh, matn, self.p((lx0 + lx1) / 2, (ly0 + ly1) / 2, (z0 + z1) / 2), yaw=self.yaw,
                   scale=((lx1 - lx0) / 100, (ly1 - ly0) / 100, (z1 - z0) / 100), coll=coll, shadow=shadow)

    def bevel(self, matn, lx0, lx1, ly0, ly1, z0, z1, coll=False, shadow=True):
        self.box(matn, lx0, lx1, ly0, ly1, z0, z1, coll, shadow, mesh="SM_GW_BevelBox")

    def piece(self, meshn, matn, lx, ly, z, sx=1.0, sy=1.0, sz=1.0, yaw_add=0.0, pitch=0.0, roll=0.0, coll=False,
              shadow=True):
        self.b.add(self.g, meshn, matn, self.p(lx, ly, z), yaw=self.yaw + yaw_add, pitch=pitch, roll=roll,
                   scale=(sx, sy, sz), coll=coll, shadow=shadow)

    def cyl(self, matn, lx, ly, z0, z1, d, coll=False, shadow=True):
        self.piece("SM_GW_Cylinder", matn, lx, ly, (z0 + z1) / 2, d / 100, d / 100, (z1 - z0) / 100, coll=coll,
                   shadow=shadow)

    def block(self, lx0, lx1, ly0, ly1, z0, z1, label="furniture"):
        self.b.add(self.g, "SM_GW_Cube", "MI_GW_Plaster_Cream",
                   self.p((lx0 + lx1) / 2, (ly0 + ly1) / 2, (z0 + z1) / 2), yaw=self.yaw,
                   scale=((lx1 - lx0) / 100, (ly1 - ly0) / 100, (z1 - z0) / 100), coll=True, shadow=False,
                   visible=False)
        self.foot(lx0, lx1, ly0, ly1, label, self.z + z1)

    def foot(self, lx0, lx1, ly0, ly1, label, top=120.0):
        """Register a footprint (world AABB) with its top height (used by markers, wall decor and audits)."""
        pts = [self.p(a, c) for a in (lx0, lx1) for c in (ly0, ly1)]
        FOOT.append((min(p[0] for p in pts), min(p[1] for p in pts), max(p[0] for p in pts),
                     max(p[1] for p in pts), label, top, self.z))


# ------------------------------------------------------------------ procedural placeholders
def f_chair(lf, seat="MI_GW_Velvet_Red", wood="MI_GW_Wood_Walnut"):
    for lx in (-19, 19):
        for ly in (-19, 19):
            lf.box(wood, lx - 2, lx + 2, ly - 2, ly + 2, 0, 46)
    lf.bevel(seat, -23, 23, -23, 23, 44, 52)
    lf.box(wood, -22, 22, -24, -19, 46, 108)
    lf.box(seat, -17, 17, -19, -17.5, 60, 100)
    lf.piece("SM_GW_Ball", "MI_GW_Brass", -19, -21.5, 108, 0.05, 0.05, 0.05)
    lf.piece("SM_GW_Ball", "MI_GW_Brass", 19, -21.5, 108, 0.05, 0.05, 0.05)
    lf.block(-24, 24, -25, 24, 0, 105, "chair")


def f_armchair(lf, leather="MI_GW_Leather_Oxblood", w=86):
    h = w / 2
    for lx in (-h + 8, h - 8):
        for ly in (-32, 32):
            lf.piece("SM_GW_Ball", "MI_GW_Wood_Dark", lx, ly, 0, 0.08, 0.08, 0.09)
    lf.bevel(leather, -h, h, -40, 40, 8, 44)
    lf.bevel(leather, -h + 14, h - 14, -26, 38, 42, 54)
    for sgn in (-1, 1):
        lf.bevel(leather, sgn * h - 14 if sgn > 0 else -h, h if sgn > 0 else -h + 14, -40, 40, 40, 70)
        lf.piece("SM_GW_Cylinder", leather, sgn * (h - 7), 0, 70, 0.15, 0.15, 0.8, pitch=90, yaw_add=90)
    lf.bevel(leather, -h, h, -40, -22, 40, 96)
    lf.piece("SM_GW_Cylinder", leather, 0, -31, 96, 0.19, 0.19, w / 100, pitch=90)
    lf.block(-h, h, -41, 40, 0, 95, "armchair")


def f_sofa(lf, w=210, leather="MI_GW_Leather_Oxblood"):
    h = w / 2
    for lx in (-h + 10, 0, h - 10):
        for ly in (-34, 34):
            lf.piece("SM_GW_Ball", "MI_GW_Wood_Dark", lx, ly, 0, 0.08, 0.08, 0.09)
    lf.bevel(leather, -h, h, -42, 42, 8, 42)
    n = 3 if w > 180 else 2
    cw = (w - 30) / n
    for i in range(n):
        x0 = -h + 15 + i * cw
        lf.bevel(leather, x0 + 1, x0 + cw - 1, -24, 40, 40, 53)
    for sgn in (-1, 1):
        lf.bevel(leather, h - 15 if sgn > 0 else -h, h if sgn > 0 else -h + 15, -42, 42, 40, 72)
        lf.piece("SM_GW_Cylinder", leather, sgn * (h - 7.5), 0, 72, 0.17, 0.17, 0.84, pitch=90, yaw_add=90)
    lf.bevel(leather, -h, h, -42, -24, 40, 88)
    lf.piece("SM_GW_Cylinder", leather, 0, -33, 88, 0.2, 0.2, w / 100, pitch=90)
    lf.block(-h, h, -43, 42, 0, 90, "sofa")


def f_side_table(lf, d=60, top="MI_GW_Marble_White", wood="MI_GW_Wood_Walnut", h=62, lamp=False):
    lf.cyl(wood, 0, 0, 0, 4, d * 0.6)
    lf.piece("SM_GW_ColumnShaft", wood, 0, 0, 4, 0.22, 0.22, (h - 8) / 100)
    lf.cyl(top, 0, 0, h - 4, h, d)
    lf.block(-d / 2, d / 2, -d / 2, d / 2, 0, h, "side_table")
    if lamp:
        f_table_lamp(lf, 0, 0, h)


def f_table_lamp(lf, lx, ly, z):
    lf.cyl("MI_GW_Brass", lx, ly, z, z + 3, 16)
    lf.cyl("MI_GW_Brass", lx, ly, z + 3, z + 34, 3)
    lf.piece("SM_GW_Tulip", "MI_GW_LampGlow", lx, ly, z + 52, 2.2, 2.2, 1.6, roll=180, shadow=False)
    LAMPS.append(lf.p(lx, ly, z + 42) + (55.0, 380.0))


def f_floor_lamp(lf):
    lf.cyl("MI_GW_Brass", 0, 0, 0, 3, 32)
    lf.cyl("MI_GW_Brass", 0, 0, 3, 150, 3.5)
    lf.piece("SM_GW_Tulip", "MI_GW_LampGlow", 0, 0, 175, 3.2, 3.2, 2.0, roll=180, shadow=False)
    lf.block(-16, 16, -16, 16, 0, 160, "floor_lamp")
    LAMPS.append(lf.p(0, 0, 160) + (80.0, 480.0))


def f_round_table(lf, d=150, h=78, top="MI_GW_Marble_Black", wood="MI_GW_Wood_Mahogany"):
    lf.piece("SM_GW_ColumnBase", wood, 0, 0, 0, 1.4, 1.4, 0.8)
    lf.piece("SM_GW_ColumnShaft", wood, 0, 0, 14, 0.7, 0.7, (h - 22) / 100)
    lf.piece("SM_GW_ColumnCapital", "MI_GW_GoldLeaf", 0, 0, h - 14, 1.2, 1.2, 0.5)
    lf.cyl(top, 0, 0, h - 5, h, d)
    lf.cyl("MI_GW_GoldLeaf", 0, 0, h - 6, h - 5, d + 2)
    lf.block(-d / 2, d / 2, -d / 2, d / 2, 0, h, "round_table")


def f_vase(lf, lx, ly, z, s=1.0):
    lf.piece("SM_GW_Finial", "MI_GW_Porcelain", lx, ly, z, 2.2 * s, 2.2 * s, 2.2 * s)
    for k in range(7):
        a = 2 * math.pi * k / 7
        lf.piece("SM_GW_Ball", "MI_GW_Foliage" if k % 2 else "MI_GW_Velvet_Red", lx + math.cos(a) * 12 * s,
                 ly + math.sin(a) * 12 * s, z + (50 + 6 * (k % 3)) * s, 0.16 * s, 0.16 * s, 0.14 * s, shadow=False)
    lf.piece("SM_GW_Ball", "MI_GW_Porcelain", lx, ly, z + 58 * s, 0.18 * s, 0.18 * s, 0.16 * s)


def f_long_table(lf, L=640, W=130, h=77, wood="MI_GW_Wood_Mahogany"):
    lf.bevel(wood, -L / 2, L / 2, -W / 2, W / 2, h - 5, h)
    lf.box(wood, -L / 2 + 10, L / 2 - 10, -W / 2 + 8, W / 2 - 8, h - 14, h - 5)
    for lx in (-L / 2 + 90, L / 2 - 90):
        lf.piece("SM_GW_ColumnBase", wood, lx, 0, 0, 1.0, 1.6, 0.8)
        lf.piece("SM_GW_ColumnShaft", wood, lx, 0, 14, 0.5, 0.5, (h - 28) / 100)
    lf.box(wood, -L / 2 + 90, L / 2 - 90, -4, 4, 18, 26)
    lf.block(-L / 2, L / 2, -W / 2, W / 2, 0, h, "long_table")


def f_candelabra(lf, lx, ly, z, s=1.0, metal="MI_GW_Silver"):
    lf.piece("SM_GW_Finial", metal, lx, ly, z, 0.9 * s, 0.9 * s, 1.0 * s)
    lf.cyl(metal, lx, ly, z + 20 * s, z + 40 * s, 2.0 * s)
    for k in range(5):
        if k == 4:
            ax, ay = lx, ly
        else:
            a = 2 * math.pi * k / 4
            ax, ay = lx + math.cos(a) * 13 * s, ly + math.sin(a) * 13 * s
            lf.box(metal, min(lx, ax) - 0.6, max(lx, ax) + 0.6, min(ly, ay) - 0.6, max(ly, ay) + 0.6,
                   z + 38 * s, z + 39.5 * s, shadow=False)
        lf.piece("SM_GW_CandleCup", metal, ax, ay, z + 39 * s, 0.8 * s, 0.8 * s, 0.6 * s, shadow=False)
        lf.cyl("MI_GW_Porcelain", ax, ay, z + 45 * s, z + 60 * s, 2.2 * s, shadow=False)
        lf.piece("SM_GW_Flame", "MI_GW_Bulb", ax, ay, z + 60 * s, 0.9 * s, 0.9 * s, 1.0 * s, shadow=False)


def f_sideboard(lf, w=190, wood="MI_GW_Wood_Walnut", top="MI_GW_Marble_Black"):
    for lx in (-w / 2 + 6, w / 2 - 6):
        for ly in (-20, 20):
            lf.box(wood, lx - 3, lx + 3, ly - 3, ly + 3, 0, 14)
    lf.bevel(wood, -w / 2, w / 2, -24, 24, 12, 88)
    for k in range(3):
        lx = -w / 2 + w * (k + 0.5) / 3
        lf.piece("SM_GW_RaisedPanel", wood, lx, 24, 22, (w / 3 - 14) / 100, 1.0, 0.56)
        lf.piece("SM_GW_Ball", "MI_GW_Brass", lx, 26.5, 72, 0.04, 0.04, 0.04)
    lf.bevel(top, -w / 2 - 3, w / 2 + 3, -27, 27, 88, 92)
    lf.block(-w / 2 - 3, w / 2 + 3, -27, 27, 0, 92, "sideboard")
    return 92


def f_console(lf, w=140, top="MI_GW_Marble_White", body="MI_GW_Lacquer_Black"):
    for lx in (-w / 2 + 8, w / 2 - 8):
        lf.box("MI_GW_GoldLeaf", lx - 2.5, lx + 2.5, 8, 14, 0, 80)
        lf.box("MI_GW_GoldLeaf", lx - 2.5, lx + 2.5, -18, -12, 0, 80)
    lf.box(body, -w / 2 + 4, w / 2 - 4, -17, 16, 70, 82)
    lf.bevel(top, -w / 2, w / 2, -20, 20, 82, 86)
    lf.box("MI_GW_GoldLeaf", -w / 2 + 10, w / 2 - 10, -18, 14, 18, 21)
    lf.block(-w / 2, w / 2, -20, 20, 0, 86, "console")
    return 86


def f_pedestal(lf, h=110, mat_="MI_GW_Marble_White", top_item="urn"):
    lf.bevel(mat_, -24, 24, -24, 24, 0, 10)
    lf.piece("SM_GW_ColumnBase", mat_, 0, 0, 10, 0.6, 0.6, 0.6)
    lf.piece("SM_GW_ColumnShaft", mat_, 0, 0, 21, 0.62, 0.62, (h - 42) / 100)
    lf.piece("SM_GW_ColumnCapital", mat_, 0, 0, h - 21, 0.62, 0.62, 0.6)
    lf.bevel(mat_, -24, 24, -24, 24, h - 10, h)
    if top_item == "urn":
        lf.piece("SM_GW_Finial", "MI_GW_GoldLeaf", 0, 0, h, 2.4, 2.4, 2.8)
    lf.block(-24, 24, -24, 24, 0, h + 40, "pedestal")


def f_planter(lf, s=1.0):
    lf.piece("SM_GW_Finial", "MI_GW_Porcelain", 0, 0, 0, 4.6 * s, 4.6 * s, 3.2 * s)
    lf.cyl("MI_GW_Wood_Dark", 0, 0, 70 * s, 120 * s, 6 * s)
    lf.piece("SM_GW_Ball", "MI_GW_Foliage", 0, 0, 95 * s, 0.85 * s, 0.85 * s, 0.95 * s)
    lf.piece("SM_GW_Ball", "MI_GW_Foliage", 0, 0, 165 * s, 0.55 * s, 0.55 * s, 0.6 * s)
    lf.block(-33 * s, 33 * s, -33 * s, 33 * s, 0, 200 * s, "planter")


def f_clock(lf):
    lf.bevel("MI_GW_Wood_Mahogany", -27, 27, -16, 16, 0, 18)
    lf.box("MI_GW_Wood_Mahogany", -22, 22, -13, 13, 18, 170)
    lf.box("MI_GW_Glass", -12, 12, 13, 14, 40, 150, mesh="SM_GW_Cube_NoNanite", shadow=False)
    lf.cyl("MI_GW_Brass", 0, 11, 60, 61, 14)
    lf.box("MI_GW_Brass", -0.6, 0.6, 11, 12, 61, 140)
    lf.bevel("MI_GW_Wood_Mahogany", -27, 27, -17, 17, 170, 222)
    lf.piece("SM_GW_Cylinder", "MI_GW_Porcelain", 0, 17.5, 196, 0.36, 0.36, 0.01, roll=90)
    lf.piece("SM_GW_Torus", "MI_GW_Brass", 0, 17.8, 196, 0.38, 0.38, 0.5, roll=90)
    lf.piece("SM_GW_Cornice", "MI_GW_Wood_Mahogany", 0, 17, 222, 0.6, 0.2, 0.3)
    for lx in (-22, 0, 22):
        lf.piece("SM_GW_Finial", "MI_GW_Brass", lx, 0, 228, 0.5, 0.5, 0.6)
    lf.block(-27, 27, -17, 18, 0, 230, "clock")


def f_desk(lf, w=180, d=90):
    wood, leather = "MI_GW_Wood_Walnut", "MI_GW_Felt_Green"
    for sgn in (-1, 1):
        lf.bevel(wood, sgn * w / 2 - (52 if sgn > 0 else 0), sgn * w / 2 + (0 if sgn > 0 else 52), -d / 2 + 2,
                 d / 2 - 2, 0, 72)
        for z in (12, 36, 56):
            lf.piece("SM_GW_Ball", "MI_GW_Brass", sgn * (w / 2 - 26), d / 2 - 1, z, 0.04, 0.04, 0.04)
    lf.box(wood, -w / 2 + 52, w / 2 - 52, -d / 2 + 4, -d / 2 + 6, 40, 70)
    lf.bevel(wood, -w / 2 - 2, w / 2 + 2, -d / 2 - 2, d / 2 + 2, 72, 77)
    lf.box(leather, -w / 2 + 16, w / 2 - 16, -d / 2 + 12, d / 2 - 12, 77, 77.4, shadow=False)
    lf.block(-w / 2 - 2, w / 2 + 2, -d / 2 - 2, d / 2 + 2, 0, 77, "desk")
    return 77.4


def f_billiard(lf):
    wood, felt = "MI_GW_Wood_Mahogany", "MI_GW_Felt_Green"
    for lx in (-120, 0, 120):
        for ly in (-60, 60):
            lf.piece("SM_GW_ColumnBase", wood, lx, ly, 0, 0.32, 0.32, 0.5)
            lf.piece("SM_GW_ColumnShaft", wood, lx, ly, 9, 0.34, 0.34, 0.54)
    lf.bevel(wood, -142, 142, -77, 77, 62, 80)
    lf.box(felt, -127, 127, -64, 64, 80, 82)
    for (a0, a1, b0, b1) in ((-142, 142, 64, 77), (-142, 142, -77, -64), (-142, -127, -77, 77), (127, 142, -77, 77)):
        lf.bevel(wood, a0, a1, b0, b1, 80, 86)
    for (a0, a1, b0, b1) in ((-127, 127, 60, 64), (-127, 127, -64, -60), (-127, -123, -64, 64), (123, 127, -64, 64)):
        lf.box(felt, a0, a1, b0, b1, 82, 85)
    for lx in (-128, 0, 128):
        for ly in (-65, 65):
            lf.cyl("MI_GW_Lacquer_Black", lx, ly, 81, 86.2, 11, shadow=False)
    cols = ["MI_GW_Porcelain", "MI_GW_Velvet_Red", "MI_GW_Book_Black", "MI_GW_Velvet_Gold", "MI_GW_Book_Navy"]
    rng = random.Random(11)
    for k, c in enumerate(cols * 2):
        lf.piece("SM_GW_Ball", c, rng.uniform(-100, 100), rng.uniform(-45, 45), 82, 0.057, 0.057, 0.057)
    lf.piece("SM_GW_Cylinder", "MI_GW_Wood_Oak", 20, 40, 87, 0.025, 0.025, 1.45, pitch=90, yaw_add=12)
    lf.block(-142, 142, -77, 77, 0, 86, "billiard_table")


def f_bar(lf, w=560, wall_v=-60):
    """Bar counter; local +Y faces the room, the back bar is on the wall behind (ly = wall_v)."""
    wood = "MI_GW_Wood_Mahogany"
    lf.bevel(wood, -w / 2, w / 2, -30, 30, 0, 104)
    for k in range(int(w / 70)):
        lx = -w / 2 + 35 + k * 70
        lf.piece("SM_GW_RaisedPanel", wood, lx, 30, 14, 0.56, 1.0, 0.76)
    lf.bevel("MI_GW_Marble_Black", -w / 2 - 5, w / 2 + 5, -34, 36, 104, 109)
    lf.piece("SM_GW_Cylinder", "MI_GW_Brass", 0, 40, 18, 0.05, 0.05, w / 100, pitch=90)
    lf.block(-w / 2 - 5, w / 2 + 5, -34, 42, 0, 109, "bar")
    # back bar on the wall
    lf.box(wood, -w / 2, w / 2, wall_v, wall_v + 45, 0, 92, coll=True)
    lf.foot(-w / 2, w / 2, wall_v, wall_v + 45, "backbar", 215)
    lf.box("MI_GW_Mirror", -w / 2 + 20, w / 2 - 20, wall_v + 0.5, wall_v + 2, 100, 212, shadow=False)
    rng = random.Random(5)
    for z in (100, 138, 176):
        lf.box(wood, -w / 2 + 10, w / 2 - 10, wall_v, wall_v + 24, z - 3, z)
        lx = -w / 2 + 25
        while lx < w / 2 - 25:
            m = rng.choice(["MI_GW_Bottle_Green", "MI_GW_Bottle_Amber", "MI_GW_Bottle_Green", "MI_GW_Crystal"])
            h = rng.uniform(20, 28)
            lf.cyl(m, lx, wall_v + 12, z, z + h, 7.5, shadow=False)
            lf.cyl(m, lx, wall_v + 12, z + h, z + h + 8, 2.6, shadow=False)
            lx += rng.uniform(10, 16)
    LAMPS.append(lf.p(0, wall_v + 40, 215) + (90.0, 500.0))
    for k in range(5):
        lx = -w / 2 + 60 + k * (w - 120) / 4
        lf.cyl("MI_GW_Brass", lx, 75, 0, 3, 40)
        lf.cyl("MI_GW_Brass", lx, 75, 3, 72, 5)
        lf.cyl("MI_GW_Leather_Oxblood", lx, 75, 72, 80, 40)
        lf.block(lx - 21, lx + 21, 54, 96, 0, 80, "stool")


def f_piano(lf):
    blk = "MI_GW_Lacquer_Black"
    for (lx, ly) in ((-60, 40), (60, 40), (0, -95)):
        lf.piece("SM_GW_ColumnShaft", blk, lx, ly, 0, 0.18, 0.18, 0.62)
    lf.bevel(blk, -75, 75, -40, 60, 62, 95)
    lf.bevel(blk, -55, 45, -120, -40, 62, 95)
    lf.bevel(blk, -30, 15, -160, -120, 62, 95)
    lf.box("MI_GW_Porcelain", -60, 60, 60, 74, 74, 77)
    for k in range(36):
        if k % 7 in (0, 3):
            continue
        lf.box(blk, -58 + k * 3.3, -56.6 + k * 3.3, 66, 74, 77, 78.2, shadow=False)
    lf.piece("SM_GW_Cube", blk, -10, -50, 125, 1.35, 1.75, 0.02, pitch=0, roll=-38)
    lf.box(blk, -2, 2, -50, -46, 95, 125, shadow=False)
    lf.bevel(blk, -40, 40, 90, 125, 0, 50)
    lf.block(-75, 75, -160, 60, 0, 110, "piano")
    lf.foot(-40, 40, 90, 125, "piano_bench", 50)


def f_gramophone(lf):
    lf.cyl("MI_GW_Wood_Dark", 0, 0, 0, 76, 34)
    lf.bevel("MI_GW_Wood_Walnut", -24, 24, -24, 24, 76, 96)
    lf.cyl("MI_GW_Book_Black", 0, 0, 96, 97, 30)
    lf.cyl("MI_GW_Brass", -14, -14, 96, 112, 3)
    lf.piece("SM_GW_Tulip", "MI_GW_Brass", -12, -6, 108, 4.5, 4.5, 4.0, pitch=0, roll=-55)
    lf.block(-24, 24, -24, 24, 0, 120, "gramophone")


def f_bench(lf, w=140, seat="MI_GW_Velvet_Red"):
    for lx in (-w / 2 + 8, w / 2 - 8):
        for ly in (-14, 14):
            lf.box("MI_GW_Wood_Dark", lx - 2.5, lx + 2.5, ly - 2.5, ly + 2.5, 0, 42)
    lf.bevel(seat, -w / 2, w / 2, -20, 20, 40, 50)
    lf.block(-w / 2, w / 2, -20, 20, 0, 50, "bench")


def f_safe(lf):
    lf.bevel("MI_GW_Iron", -40, 40, -35, 35, 0, 110)
    lf.cyl("MI_GW_Brass", 0, 0, 0, 0, 1)
    lf.piece("SM_GW_Cylinder", "MI_GW_Brass", 10, 35.5, 70, 0.12, 0.12, 0.02, roll=90)
    lf.piece("SM_GW_Cylinder", "MI_GW_Brass", -15, 35.5, 70, 0.04, 0.04, 0.08, roll=90)
    lf.box("MI_GW_GoldLeaf", -34, 34, 35, 35.3, 100, 103, shadow=False)
    lf.block(-40, 40, -35, 36, 0, 110, "safe")


def f_wicker(lf):
    w = "MI_GW_Porcelain"
    lf.cyl(w, 0, 0, 0, 40, 70)
    lf.cyl("MI_GW_Velvet_Green", 0, 4, 40, 48, 60)
    lf.piece("SM_GW_Torus", w, 0, 0, 70, 0.62, 0.62, 3.0)
    lf.box(w, -30, 30, -34, -26, 40, 95)
    lf.block(-36, 36, -36, 36, 0, 95, "wicker_chair")


def f_fountain(b, g, x, y):
    lf = LF(b, g, x, y, 90)
    lf.piece("SM_GW_ColumnBase", "MI_GW_Marble_White", 0, 0, 0, 3.6, 3.6, 2.4)
    lf.cyl("MI_GW_Lacquer_Black", 0, 0, 30, 38, 205, shadow=False)
    lf.piece("SM_GW_ColumnShaft", "MI_GW_Marble_White", 0, 0, 38, 0.5, 0.5, 0.75)
    lf.piece("SM_GW_Tulip", "MI_GW_Marble_White", 0, 0, 110, 6.0, 6.0, 2.2)
    lf.cyl("MI_GW_Lacquer_Black", 0, 0, 138, 140, 80, shadow=False)
    lf.piece("SM_GW_Finial", "MI_GW_Marble_White", 0, 0, 140, 1.6, 1.6, 2.0)
    lf.block(-112, 112, -112, 112, 0, 60, "fountain")


def f_armor(lf):
    lf.bevel("MI_GW_Wood_Dark", -30, 30, -25, 25, 0, 10)
    st = "MI_GW_Chrome"
    for lx in (-11, 11):
        lf.cyl(st, lx, 0, 10, 95, 14)
    lf.bevel(st, -24, 24, -14, 14, 95, 150)
    lf.piece("SM_GW_Ball", st, 0, 0, 148, 0.34, 0.3, 0.3)
    for lx in (-30, 30):
        lf.cyl(st, lx, 0, 85, 145, 10)
    lf.piece("SM_GW_Ball", st, 0, 0, 158, 0.28, 0.3, 0.36)
    lf.piece("SM_GW_Cylinder", "MI_GW_Iron", 38, 8, 110, 0.03, 0.03, 2.1)
    lf.block(-30, 30, -25, 25, 0, 190, "armor")


FALLBACK = {"armchair_club": f_armchair, "sofa_chesterfield": f_sofa, "chair_dining": f_chair,
            "table_side": f_side_table, "lamp_floor": f_floor_lamp, "clock_grandfather": f_clock,
            "desk_partners": f_desk, "billiard_table": f_billiard, "piano_grand": f_piano, "gramophone": f_gramophone,
            "chair_wingback": lambda lf: f_armchair(lf, "MI_GW_Velvet_Green", 80), "sideboard": f_sideboard,
            "table_console": f_console, "palm_potted": f_planter, "bust_marble": f_pedestal, "armor_suit": f_armor,
            "chair_wicker": f_wicker, "bench": f_bench,
            "ottoman": lambda lf: (lf.cyl("MI_GW_Velvet_Red", 0, 0, 6, 44, 70),
                                                             lf.block(-35, 35, -35, 35, 0, 44, "ottoman")),
            "globe_floor": lambda lf: (lf.piece("SM_GW_Finial", "MI_GW_Wood_Walnut", 0, 0, 0, 3, 3, 2.6),
                                       lf.piece("SM_GW_Ball", "MI_GW_Book_Tan", 0, 0, 62, 0.5, 0.5, 0.5),
                                       lf.piece("SM_GW_Torus", "MI_GW_Brass", 0, 0, 87, 0.56, 0.56, 1.0, roll=70),
                                       lf.block(-30, 30, -30, 30, 0, 115, "globe"))}


def slot(b, g, props, name, x, y, face, z=0.0, scale=1.0, back=False, fit=None, **kw):
    """Place prop `name` (from the manifest) or its procedural fallback. Returns top height (approx).

    back=True: (x, y) is the point the prop's back should touch (wall-mounted props).
    fit=(w, d, h): reserve that footprint now (even if the prop does not exist yet: it then places nothing) and,
    once the prop exists, shrink it uniformly if needed so it stays inside the reservation (centred on it, or
    back on the wall point when back=True)."""
    st = props.get(name)
    if fit:
        fw, fd, fh = fit
        rx, ry = x, y
        if back:
            rx += math.cos(math.radians(face)) * fd / 2
            ry += math.sin(math.radians(face)) * fd / 2
        reserve(name, rx, ry, face, fw, fd, fh, z, placed=bool(st) or name in FALLBACK)
    if st:
        lo, hi = st["lo"], st["hi"]
        size = st.get("size_cm")
        fr = round(st.get("front", 90.0) / 90.0) * 90 % 360
        ext = [hi[k] - lo[k] for k in range(3)]
        w_ax, d_ax = (1, 0) if fr in (0, 180) else (0, 1)
        if size:
            # scale every axis to the manifest size (w across the front, d along it, h): TRELLIS proportions are off
            sc = [1.0, 1.0, 1.0]
            sc[w_ax] = size[0] / max(ext[w_ax], 1e-3)
            sc[d_ax] = size[1] / max(ext[d_ax], 1e-3)
            sc[2] = size[2] / max(ext[2], 1e-3)
        else:
            sc = [1.0, 1.0, 1.0]
        sc = [v * scale for v in sc]
        if fit:
            k = min(1.0, fw / max(ext[w_ax] * sc[w_ax], 1e-3), fd / max(ext[d_ax] * sc[d_ax], 1e-3),
                    fh / max(ext[2] * sc[2], 1e-3))
            sc = [v * k for v in sc]
            # put the scaled bounding-box centre on the reservation (back props: back face on the wall point)
            dep = ext[d_ax] * sc[d_ax]
            tx = x + (math.cos(math.radians(face)) * dep / 2 if back else 0.0)
            ty = y + (math.sin(math.radians(face)) * dep / 2 if back else 0.0)
            ry_ = math.radians(face - st.get("front", 90.0))
            mx, my = (lo[0] + hi[0]) / 2 * sc[0], (lo[1] + hi[1]) / 2 * sc[1]
            x = tx - (mx * math.cos(ry_) - my * math.sin(ry_))
            y = ty - (mx * math.sin(ry_) + my * math.cos(ry_))
            back = False
        if back:
            back_ext = {0: -lo[0] * sc[0], 90: -lo[1] * sc[1], 180: hi[0] * sc[0], 270: hi[1] * sc[1]}[fr]
            x += math.cos(math.radians(face)) * back_ext
            y += math.sin(math.radians(face)) * back_ext
        yaw = face - st.get("front", 90.0)
        b.add(g, st["mesh"], None, (x, y, z - lo[2] * sc[2]), yaw=yaw, scale=tuple(sc), coll=True)
        r = math.radians(yaw)
        pts = [(x + px * sc[0] * math.cos(r) - py * sc[1] * math.sin(r),
                y + px * sc[0] * math.sin(r) + py * sc[1] * math.cos(r)) for px in (lo[0], hi[0]) for py in (lo[1], hi[1])]
        top = z + ext[2] * sc[2]
        FOOT.append((min(p[0] for p in pts), min(p[1] for p in pts), max(p[0] for p in pts),
                     max(p[1] for p in pts), name, top, z))
        LAST["center"] = (x, y)
        PLACED["props"][name] = PLACED["props"].get(name, 0) + 1
        room = g[6:] if g.startswith("Dress_") else g
        PLACED["rooms"][room] = PLACED["rooms"].get(room, 0) + 1
        if name == "lamp_floor":
            LAMPS.append((x, y, z + ext[2] * sc[2] * 0.85, 80.0, 480.0))
        if name == "lamp_table":
            LAMPS.append((x, y, z + ext[2] * sc[2] * 0.8, 55.0, 380.0))
        if name == "candelabra":
            CANDLES.append((round(x), round(y), round(top - 4)))
        return top
    fb = FALLBACK.get(name)
    cnt = PLACED["fallback"] if fb else PLACED["waiting"]
    cnt[name] = cnt.get(name, 0) + 1
    if back:
        fb_half = kw.pop("fb_half", 22.0)
        x += math.cos(math.radians(face)) * fb_half
        y += math.sin(math.radians(face)) * fb_half
    else:
        kw.pop("fb_half", None)
    LAST["center"] = (x, y)
    if fb:
        lf = LF(b, g, x, y, face, z)
        r = fb(lf, **kw) if kw else fb(lf)
        return z + (r if isinstance(r, (int, float)) else 80)
    return z


def tabletop(b, g, props, name, x, y, face, z, scale=1.0):
    """Small prop on a surface; placeholder only for lamps/candelabras/vases."""
    if props.get(name):
        c = LAST["center"]
        r = slot(b, g, props, name, x, y, face, z, scale=scale)
        LAST["center"] = c
        return r
    lf = LF(b, g, x, y, face, z)
    if name == "lamp_table":
        f_table_lamp(lf, 0, 0, 0)
    elif name in ("candelabra",):
        f_candelabra(lf, 0, 0, 0)
        CANDLES.append((round(x), round(y), round(z + 60)))
    elif name == "vase_flowers":
        f_vase(lf, 0, 0, 0)
    PLACED["fallback"][name] = PLACED["fallback"].get(name, 0) + 1
    return z


def rug(b, g, x, y, w, yaw, mi):
    """Rug image plane; `w` = long side (along local X), depth from the image aspect."""
    try:
        asp = json.load(open(os.path.join(ROOT, "Tools", "level", "materials_state.json"),
                             encoding="utf-8")).get("aspect", {}).get(mi, 1.5)
    except (OSError, ValueError):
        asp = 1.5
    d = w / max(asp, 0.2)
    b.add(g, "SM_GW_Plane", mi, (x, y, 0.6), yaw=yaw, scale=(w / 100, d / 100, 1), coll=False, shadow=False)
    b.add(g, "SM_GW_Cube", "MI_GW_Wood_Dark", (x, y, 0.25), yaw=yaw, scale=((w + 4) / 100, (d + 4) / 100, 0.004),
          coll=False, shadow=False)


def runner(b, g, x0, x1, y, w=170):
    try:
        st = json.load(open(os.path.join(ROOT, "Tools", "level", "materials_state.json"), encoding="utf-8"))
    except (OSError, ValueError):
        st = {}
    if "MI_GW_Rug_Runner" in st.get("generated", {}):
        aspect = st.get("runner_aspect", 1.5)
        if aspect >= 1:      # image long along U -> U along the corridor
            b.add(g, "SM_GW_Plane", "MI_GW_Rug_Runner", ((x0 + x1) / 2, y, 0.6),
                  scale=((x1 - x0) / 100, w / 100, 1), coll=False, shadow=False)
        else:                # portrait image: V along the corridor
            b.add(g, "SM_GW_Plane", "MI_GW_Rug_Runner", ((x0 + x1) / 2, y, 0.6), yaw=90,
                  scale=(w / 100, (x1 - x0) / 100, 1), coll=False, shadow=False)
        b.box(g, "MI_GW_Wood_Dark", x0 - 1, x1 + 1, y - w / 2 - 1, y + w / 2 + 1, 0, 0.25, coll=False, shadow=False)
        return
    b.box(g, "MI_GW_Carpet_Red", x0, x1, y - w / 2, y + w / 2, 0, 0.8, coll=False, shadow=False)
    for s in (-1, 1):
        b.box(g, "MI_GW_Velvet_Gold", x0, x1, y + s * (w / 2 - 9) - 2, y + s * (w / 2 - 9) + 2, 0, 0.9, coll=False,
              shadow=False)


# ------------------------------------------------------------------ bookcases (built along wall faces)
def bookcases(b, g, f, spans, height=300, seed=3):
    rng = random.Random(seed)
    wood = "MI_GW_Wood_Walnut"
    books = ["MI_GW_Book_Oxblood", "MI_GW_Book_Green", "MI_GW_Book_Navy", "MI_GW_Book_Brown", "MI_GW_Book_Tan",
             "MI_GW_Book_Black"]
    V0, V1 = 2.0, 42.0
    nshelf = int((height - 40) / 37)
    for (a, c) in spans:
        a, c = a + 2.5, c - 2.5
        if c - a < 60:
            continue
        f.box(b, g, wood, a, c, V0, V1, 0, 10, coll=False)
        f.box(b, g, wood, a, c, V0, V0 + 2, 10, height, coll=False)
        f.blocker(b, g, a, c, 0, V1, 0, height)
        f.run(b, g, "SM_GW_Cornice", wood, a - 2, c + 2, V0, height - 18, sy=1.35, sz=0.6)
        f.box(b, g, wood, a, c, V0, V1, height - 20, height - 16, coll=False)
        nb = max(1, int(round((c - a) / 95)))
        bw = (c - a) / nb
        for k in range(nb + 1):
            u = a + k * bw
            f.box(b, g, wood, u - 2, u + 2, V0, V1, 10, height - 16, coll=False)
        for k in range(nb):
            u0, u1 = a + k * bw + 2, a + (k + 1) * bw - 2
            for sidx in range(nshelf + 1):
                z = 10 + sidx * 37
                f.box(b, g, wood, u0, u1, V0, V1 - 1, z, z + 2.5, coll=False)
                if sidx == nshelf:
                    break
                u = u0 + rng.uniform(0, 3)
                while u < u1 - 3:
                    t = rng.uniform(2.6, 6.0)
                    if u + t > u1:
                        break
                    h = rng.uniform(21, 32)
                    dpt = rng.uniform(17, 24)
                    if rng.random() < 0.05:            # a gap / leaning book
                        u += rng.uniform(4, 9)
                        continue
                    f.box(b, g, rng.choice(books), u, u + t, V0 + 3, V0 + 3 + dpt, z + 2.5, z + 2.5 + h, coll=False,
                          shadow=False)
                    u += t + rng.uniform(0, 0.4)
        f.obstacles.append((a, c, height, "bookcase"))
        p0, p1 = f.P(a, V0, 0), f.P(c, V1, 0)
        FOOT.append((min(p0[0], p1[0]), min(p0[1], p1[1]), max(p0[0], p1[0]), max(p0[1], p1[1]), "bookcase",
                     height, 0.0))


def wall_spans(f, door_m=28, win_m=78, breast=True):
    blocks = []
    for o in f.openings:
        m = door_m if o["kind"] == "door" else win_m
        blocks.append((o["u0"] - m, o["u1"] + m))
    for (a, c, zm, k) in f.obstacles:
        if k == "breast" and breast:
            blocks.append((a, c))
    blocks.sort()
    spans, cur = [], 0.0
    for a, c in blocks:
        if a > cur:
            spans.append((cur, min(a, f.length)))
        cur = max(cur, c)
    if cur < f.length:
        spans.append((cur, f.length))
    return [(a, c) for a, c in spans if c - a > 50]


def room_faces(G, room):
    r = G["ROOMS"][room]
    faces = G["make_faces"](room, r["rect"], r["height"])
    for f in faces:
        G["add_openings"](f)
    for (rm, side, coord, _sh) in G["FIREPLACES"]:
        if rm != room:
            continue
        f = next(ff for ff in faces if ff.side == side)
        u = f.u_of(*G["line_point"](f.line, coord))
        f.obstacles.append((u - 140, u + 140, 10000, "breast"))
    return {f.side: f for f in faces}


# ------------------------------------------------------------------ the dressing
def build_dress(G):
    FOOT.clear()
    LAMPS.clear()
    CANDLES.clear()
    RESERVED.clear()
    PIANO.clear()
    INSTRUMENTS.clear()
    for v in PLACED.values():
        v.clear()
    props = import_props()
    b = Batch("GW_Dress")
    S = lambda *a, **k: slot(b, a[0], props, *a[1:], **k)  # noqa: E731
    TT = lambda *a: tabletop(b, a[0], props, *a[1:])  # noqa: E731

    def ring(g, name, cx, cy, r, angles, **kw):
        """Seats on a circle around (cx, cy), each facing the centre."""
        for a in angles:
            S(g, name, cx + r * math.cos(math.radians(a)), cy + r * math.sin(math.radians(a)), a + 180.0, **kw)

    def card_group(g, x, y, yaw=0.0):
        """Card table (85 cm, being generated) + 4 chairs once it exists; the whole group's floor is reserved now."""
        have = bool(props.get("card_table"))
        reserve("card_table+chairs", x, y, yaw + 90.0, 225, 225, 110, placed=have)
        S(g, "card_table", x, y, yaw + 90.0, fit=(90, 90, 80))
        if have:
            ring(g, "chair_dining", x, y, 80, [yaw + 90 * k for k in range(4)])

    # sizes kept free for the props being generated (w across the front, d, h), real reference axis first
    FIT = dict(bench=(150, 50, 60), coat_rack=(72, 65, 195), trunk_steamer=(95, 60, 75), curio_cabinet=(100, 50, 185),
               screen_folding=(170, 50, 180), statue_dancer=(75, 75, 165), fern_stand=(85, 85, 135),
               birdcage=(70, 70, 175), chaise_longue=(190, 80, 90), champagne_bucket=(45, 45, 90),
               fire_screen=(100, 40, 90), microphone_stand=(45, 45, 180), vase_floor=(50, 50, 105),
               dress_form=(60, 55, 170), drum_kit=(160, 120, 120), writing_bureau=(100, 60, 115),
               film_projector=(75, 100, 145), double_bass=(75, 55, 190))

    def R(g, name, x, y, face, **kw):
        """Slot for a prop that is still being generated (places nothing until it is approved)."""
        S(g, name, x, y, face, fit=kw.pop("fit", FIT.get(name)), **kw)

    # ---------------- library: built-in bookcases, fireside chesterfields, reading desk, globe
    g = "Dress_library"
    lib = room_faces(G, "library")
    for side, f in lib.items():
        spans = wall_spans(f)
        if side in ("E", "W"):              # N/S bookcases own the corners
            spans = [(max(a, 46.0), min(c, f.length - 46.0)) for a, c in spans]
        bookcases(b, g, f, spans, height=300, seed=ord(side))
    rug(b, g, 520, 3400, 450, 90, "MI_GW_Rug_Persian")
    S(g, "sofa_chesterfield", 520, 3170, 90)
    S(g, "sofa_chesterfield", 520, 3630, -90)
    S(g, "armchair_club", 820, 3400, 180)
    S(g, "ottoman", 520, 3400, 0)
    S(g, "table_side", 330, 3105, 90, lamp=True)
    S(g, "lamp_floor", 330, 3700, 0)
    S(g, "desk_partners", 1250, 3950, -90)
    S(g, "chair_wingback", 1250, 3820, 90)
    TT(g, "lamp_table", 1180, 3970, 0, 77.4)
    S(g, "globe_floor", 1700, 3700, 200)
    S(g, "chair_wingback", 1500, 2760, 90)
    S(g, "table_side", 1680, 2620, 0, lamp=True)
    S(g, "chair_wingback", 400, 2750, 45)
    # second reading group (east half): chesterfield + club chairs around a side table, the wingback closes it
    S(g, "sofa_chesterfield", 1500, 3180, -90)
    S(g, "armchair_club", 1220, 2960, 0)
    S(g, "armchair_club", 1780, 2960, 180)
    S(g, "table_side", 1500, 2975, 0)
    TT(g, "vase_flowers", 1500, 2975, 0, 65, 0.6)
    S(g, "lamp_floor", 1700, 3230, 0)
    TT(g, "lamp_table", 330, 3105, 0, 65)             # prop side tables carry no lamp of their own
    TT(g, "lamp_table", 1680, 2620, 0, 65)
    S(g, "table_side", 790, 3730, 0)                  # gramophone (moved off the stage) on its own small table
    TT(g, "gramophone", 790, 3730, -60, 65)
    for yy in (3200, 3600):                           # busts flanking the ballroom door
        S(g, "bust_marble", 1855, yy, 180)
    # reading nook under the north windows: two club chairs and a lamp table
    S(g, "armchair_club", 640, 4150, 0)
    S(g, "armchair_club", 860, 4150, 180)
    S(g, "table_side", 750, 4150, 0)
    TT(g, "lamp_table", 750, 4150, 0, 65)
    # slots for the props being generated
    R(g, "fire_screen", 142, 3400, 0)
    card_group(g, 1650, 4100)
    R(g, "writing_bureau", 600, 2460, 90, back=True)  # back against the south bookcase
    R(g, "film_projector", 380, 4120, -45)
    R(g, "chaise_longue", 1850, 3950, 180)

    # ---------------- dining: long table, 16 chairs, sideboards, candelabras
    g = "Dress_dining"
    rug(b, g, 1050, 900, 950, 0, "MI_GW_Rug_Persian")
    if props.get("table_dining"):                       # two 280 cm tables end to end = one banquet table
        S(g, "table_dining", 910, 900, 90)
        S(g, "table_dining", 1190, 900, 90)
    else:
        PLACED["fallback"]["table_dining"] = 1
        f_long_table(LF(b, g, 1050, 900, 90))
    tw = 115 if props.get("table_dining") else 130         # table depth
    n_side = 6 if props.get("table_dining") else 7
    half = (n_side - 1) * 45
    for k in range(n_side):
        x = 1050 - half + k * 90
        S(g, "chair_dining", x, 900 - tw / 2 - 34, 90)
        S(g, "chair_dining", x, 900 + tw / 2 + 34, -90)
    end = 280 + 52 if props.get("table_dining") else 352
    S(g, "chair_dining", 1050 - end, 900, 0)
    S(g, "chair_dining", 1050 + end, 900, 180)
    for x in (850, 1250):
        TT(g, "candelabra", x, 900, 0, 77)
    TT(g, "vase_flowers", 1050, 900, 0, 77)
    for x in (480, 1520):
        top = S(g, "sideboard", x, 1781, -90, back=True, fb_half=27)
        cx, cy = LAST["center"]
        TT(g, "candelabra", x - 50, cy, 0, top)
        TT(g, "lamp_table", x + 60, cy, 0, top)
    top = S(g, "sideboard", 1981, 1350, 180, back=True, fb_half=27)
    sx = LAST["center"][0]
    TT(g, "vase_flowers", sx, 1350, 0, top, 0.7)
    for yy in (1290, 1410):
        TT(g, "candelabra", sx, yy, 0, top)
    S(g, "clock_grandfather", 1981, 1690, 180, back=True, fb_half=17)
    S(g, "palm_potted", 128, 128, 90)                  # fronds are ~150 cm across: keep them off the walls
    S(g, "palm_potted", 1872, 128, 90)
    S(g, "bar_cart", 1900, 1010, 180)
    # fireside pair + reading lamp, spare chairs along the west wall, consoles on the south piers
    S(g, "armchair_club", 300, 700, 132)
    S(g, "armchair_club", 300, 1100, -132)
    S(g, "lamp_floor", 230, 1300, 0)
    for yy in (560, 640, 1170, 1250):
        S(g, "chair_dining", 19, yy, 0, back=True, fb_half=27)
    for xx in (750, 1250):                             # wall piers between the south windows
        top = S(g, "table_console", xx, 21, 90, back=True, fb_half=21)
        cx, cy = LAST["center"]
        TT(g, "lamp_table", xx - 38, cy, 0, top)
        TT(g, "vase_flowers", xx + 34, cy, 0, top, 0.7)
    R(g, "fire_screen", 142, 900, 0)
    for (xx, yy) in ((60, 1740), (850, 1745), (1150, 1745)):     # NW corner + flanking the corridor door
        R(g, "vase_floor", xx, yy, -90)
    R(g, "curio_cabinet", 1560, 1400, 180)             # free-standing vitrine (walls carry paintings + sconces)
    R(g, "champagne_bucket", 1460, 780, 0)

    # ---------------- corridors: runners, consoles with lamps, busts, benches
    for room, y0, y1, x0, x1, wx in (("corridor_w", 1815, 2385, 15, 1985, 15), ("corridor_e", 1815, 2385, 4015, 5985,
                                                                                 5985)):
        g = "Dress_" + room
        cy = (y0 + y1) / 2
        runner(b, g, (WC_X1 + 15) if wx == x0 else (x0 + 5), x1 - (60 if wx == x1 else 5), cy, 170)   # W.C. x < 365
        mid = (x0 + x1) / 2
        for xx in (x0 + 420, x1 - 420):
            if abs(xx - mid) < 200:
                continue
            for (yy, face) in ((y1 - 6, -90), (y0 + 6, 90)):       # back 6 cm off the wall: clear of the dado
                top = S(g, "table_console", xx, yy, face, back=True, fb_half=21)
                cx, cy = LAST["center"]
                TT(g, "lamp_table", xx - 38, cy, 0, top)
                TT(g, "vase_flowers", xx + 34, cy, 0, top, 0.7)
                for dx in (-100, 100):                         # hall chairs flanking each console
                    if wx == x0 and xx + dx < WC_X1 + 40:      # (the W.C. partition takes that spot)
                        continue
                    S(g, "chair_dining", xx + dx, yy, face, back=True, fb_half=27)
        endx = x0 + 70 if wx == x0 else x1 - 70
        S(g, "bust_marble", endx, y0 + 60, 0 if wx == x0 else 180)
        S(g, "bust_marble", endx, y1 - 60, 0 if wx == x0 else 180)
        for xx in (mid - 300, mid + 300):
            S(g, "bench", xx, y1 - 35, -90, fit=FIT["bench"])
        # busts centred under the two south-wall paintings next to the doors (inside the paintings' clearance, so
        # the wall decor layout does not move)
        for xx in (mid - 272.5, mid + 272.5):
            S(g, "bust_marble", xx, y0 + 4, 90, back=True, fb_half=26)
        for xx in (mid - 150, mid + 150):                      # floor vases flanking the two doors
            for yy in (y0 + 30, y1 - 30):
                R(g, "vase_floor", xx, yy, 90 if yy < (y0 + y1) / 2 else -90)
        hx = x1 - 150 if wx == x0 else x0 + 150                # ferns at the hall end (clear of the door approach)
        for yy in (y0 + 50, y1 - 50):
            R(g, "fern_stand", hx, yy, 90)

    # ---------------- hall: round table + flowers, consoles, clock, armors, palms, busts at the stair feet
    g = "Dress_hall"
    rug(b, g, 3000, 1150, 560, 0, "MI_GW_Rug_ArtDeco")
    f_round_table(LF(b, g, 3000, 1150, 90))
    TT(g, "vase_flowers", 3000, 1150, 0, 78)
    # "Ils étaient dix": ten little porcelain soldiers in a ring around the flowers on the hall's round table
    for k in range(10):
        a = math.radians(18 + 36 * k)
        fx, fy, fz = 3000 + math.cos(a) * 56, 1150 + math.sin(a) * 56, 78.2
        yaw = math.degrees(a) + 180.0
        b.add(g, "SM_GW_Cylinder", "MI_GW_Book_Black", (fx, fy, fz + 0.4), scale=(0.045, 0.045, 0.008), coll=False,
              shadow=False)
        b.add(g, "SM_GW_Cylinder", "MI_GW_Velvet_Red", (fx, fy, fz + 4.2), yaw=yaw, scale=(0.032, 0.026, 0.07),
              coll=False)
        b.add(g, "SM_GW_Cylinder", "MI_GW_Book_Navy", (fx, fy, fz + 1.8), scale=(0.03, 0.024, 0.03), coll=False,
              shadow=False)
        b.add(g, "SM_GW_Ball", "MI_GW_Porcelain", (fx, fy, fz + 8.2), scale=(0.022, 0.022, 0.024), coll=False,
              shadow=False)
        b.add(g, "SM_GW_Cylinder", "MI_GW_Book_Black", (fx, fy, fz + 10.6), scale=(0.024, 0.024, 0.034), coll=False,
              shadow=False)
    # consoles sit in the wall bays between the side doors' casings and the first pilaster (audit_furniture.py)
    for (xx, yy, face) in ((2021, 817, 0), (3979, 896, 180)):
        top = S(g, "table_console", xx, yy, face, back=True, fb_half=21, w=120)
        cx, cy = LAST["center"]
        TT(g, "lamp_table", cx, yy - 34, 0, top)
        TT(g, "vase_flowers", cx, yy + 34, 0, top, 0.7)
    S(g, "clock_grandfather", 2470, 2381, -90, back=True, fb_half=17)    # between the under-gallery pilasters
    S(g, "armor_suit", 2620, 2381, -90, back=True, fb_half=26)
    S(g, "armor_suit", 3380, 2381, -90, back=True, fb_half=26)
    S(g, "palm_potted", 2150, 150, 90)                 # clear of the corner pilasters
    S(g, "palm_potted", 3850, 150, 90)
    S(g, "bust_marble", 2380, 960, -90)
    S(g, "bust_marble", 3620, 960, -90)
    S(g, "umbrella_stand", 2560, 540, 90)
    S(g, "armchair_club", 3620, 2160, -135)
    for (xx, face) in ((2530, 0), (3470, 180)):     # settees in the south half of the hall, facing the centre
        S(g, "sofa_chesterfield", xx, 680, face)
        S(g, "table_side", xx, 840, 0, lamp=True)
    S(g, "armchair_club", 2380, 2160, -45)
    # two compact seating groups north of the round table (sofa facing two club chairs across a lamp table);
    # 2 m lanes stay open along both stair flights, on the axis and under the gallery
    for sx in (-1, 1):
        gx = 3000 + sx * 380
        S(g, "sofa_chesterfield", gx, 1520, 90)
        S(g, "table_side", gx, 1650, 0)
        TT(g, "vase_flowers", gx, 1650, 0, 65, 0.6)
        for dx in (-70, 70):
            S(g, "armchair_club", gx + dx, 1780, -90)
        S(g, "lamp_floor", 3000 + sx * 220, 1640, 0)
    # slots for the props being generated: dancer statue facing the entrance, flanked by ferns,
    # cloakroom-side furniture (the cloakroom's outer walls carry no wall decor)
    R(g, "statue_dancer", 3000, 850, -90)
    for xx in (2850, 3150):
        R(g, "fern_stand", xx, 850, 90)
    for xx in (2750, 3250):
        R(g, "curio_cabinet", xx, 502, 90, back=True)
    for xx in (2560, 3440):
        R(g, "coat_rack", xx, 380, 90)
    R(g, "trunk_steamer", 2598, 190, 180, back=True)
    R(g, "bench", 3402, 190, 0, back=True)
    for xx in (2735, 3265):                 # flanking the ballroom door, low enough for the hall's lower decor zone
        R(g, "vase_floor", xx, 2335, -90, fit=(50, 50, 96))
    # gallery: benches, pedestals with urns, a pair of club chairs (low enough to keep the upper wall decor)
    for xx in (2600, 3400):
        S("Dress_gallery", "bench", xx, 2350, -90, z=500, fit=(165, 50, 60), w=160)
    for xx in (2350, 3650):
        S("Dress_gallery", "bust_marble", xx, 2340, -90, z=500)
    S("Dress_gallery", "armchair_club", 2880, 2320, -45, z=500)
    S("Dress_gallery", "armchair_club", 3120, 2320, -135, z=500)
    S("Dress_gallery", "table_side", 3000, 2345, 0, z=500)

    # ---------------- ballroom: stage, piano, gramophone, gilded chairs, champagne tables, palms
    g = "Dress_ballroom"
    stage(b, g)
    S(g, "piano_grand", 2850, 4130, -70, z=60)
    # GW_Piano interaction point: on the stage floor ~90 cm in front of the keyboard (the piano's front = keys)
    pst = props.get("piano_grand")
    key_d = (pst["size_cm"][1] / 2.0) if pst and pst.get("size_cm") else 74.0
    PIANO[:] = [round(2850 + math.cos(math.radians(-70)) * (key_d + 90), 1),
                round(4130 + math.sin(math.radians(-70)) * (key_d + 90), 1), 60.0, 110.0]
    # harp stage left of the piano; the band (being generated) stage right: double bass and drums with the musicians'
    # side (behind them) kept reachable through the gap between them; the singer's microphone front right.
    # Interaction points (GW_Instrument_*) sit 90 cm out from the musician's side, on the stage floor.
    S(g, "harp", 2600, 4250, -90, z=60)
    hst = props.get("harp")
    play_point("GW_Instrument_Harp", 2600, 4250, 60.0, -90, (hst["size_cm"][1] / 2.0) if hst and hst.get("size_cm")
               else 22.5, "front")
    R(g, "double_bass", 3060, 4200, -90, z=60)
    if props.get("double_bass"):           # gameplay activates an instrument as soon as its marker exists
        play_point("GW_Instrument_Bass", 3060, 4200, 60.0, -90, FIT["double_bass"][1] / 2.0, "back")
    R(g, "drum_kit", 3360, 4150, -90, z=60)
    if props.get("drum_kit"):
        play_point("GW_Instrument_Drums", 3360, 4150, 60.0, -90, FIT["drum_kit"][1] / 2.0, "back")
    R(g, "microphone_stand", 3440, 3960, -90, z=60)
    for xx in (2410, 3590):                              # folding screens in the back corners beside the stage
        R(g, "screen_folding", xx, 4300, -90)
    R(g, "dress_form", 2440, 4190, -90)
    for xx in (2440, 3560):                              # busts flanking the stage front
        S(g, "bust_marble", xx, 3850, -90)
    # gilded chairs along the south wall (between the pilasters), a chaise in the south-east bay
    for xx in (2160, 2240, 2320, 2530, 2610, 2690, 3340, 3420, 3500):
        S(g, "chair_dining", xx, 2419, 90, back=True, fb_half=27)
    R(g, "chaise_longue", 3755, 2419, 90, back=True)
    R(g, "statue_dancer", 3700, 3175, 180)
    for xx in (2280, 3720):
        S(g, "palm_potted", xx, 4180, 90)
    rng = random.Random(4)
    for (xx, ys, face) in ((2062, list(range(2520, 3240, 80)) + list(range(3580, 4060, 80)), 0),
                           (3938, list(range(2520, 3620, 80)) + list(range(3990, 4100, 80)), 180)):
        for yy in ys:
            S(g, "chair_dining", xx, yy, face) if props.get("chair_dining") else \
                f_chair(LF(b, g, xx, yy, face), "MI_GW_Velvet_Red", "MI_GW_GoldLeaf")
    for (xx, yy) in ((2400, 2750), (3600, 2750), (2400, 3600), (3600, 3600)):
        S(g, "champagne_table", xx, yy, 90 * round(rng.uniform(0, 360) / 90)) if props.get("champagne_table") else \
            f_side_table(LF(b, g, xx, yy, 90), d=70, top="MI_GW_Porcelain", wood="MI_GW_GoldLeaf", h=75)
        if not props.get("champagne_table"):
            f_candelabra(LF(b, g, xx, yy, 90, 75), 0, 0, 0, s=0.7)
        # two chairs on the wall side of each champagne table (the dance floor side stays open)
        base = 180.0 if xx < 3000 else 0.0
        ring(g, "chair_dining", xx, yy, 102, [-60, -120] if (xx > 3000 and yy > 3000) else [base - 30, base + 30])
        if yy < 3000:
            R(g, "champagne_bucket", xx, yy - 88, 90)

    # ---------------- billiard: table, bar, fireside chesterfield, cue rack
    g = "Dress_billiard"
    S(g, "billiard_table", 5000, 900, 90)
    f_bar(LF(b, g, 4420, 1600, -90), w=560, wall_v=-183)
    S(g, "sofa_chesterfield", 5560, 900, 0)
    S(g, "armchair_club", 5720, 560, 60)
    S(g, "armchair_club", 5720, 1240, -60)
    S(g, "table_side", 5560, 650, 0, lamp=True)
    rug(b, g, 5700, 900, 420, 90, "MI_GW_Rug_Persian")
    S(g, "lamp_floor", 4080, 300, 0)

    S(g, "palm_potted", 5870, 1670, 90)
    if props.get("stag_head"):                 # over the mantel (billiard fireplace on the east wall, y = 900)
        S(g, "stag_head", 5985 - 52.5, 900, 180, z=200, back=True)
    # cue rack on the west wall
    lf = LF(b, g, 4017, 1200, 0)
    lf.box("MI_GW_Wood_Mahogany", -60, 60, 0, 6, 70, 74)
    lf.box("MI_GW_Wood_Mahogany", -60, 60, 0, 6, 170, 176)
    for k in range(7):
        lf.piece("SM_GW_Cylinder", "MI_GW_Wood_Oak", -45 + k * 15, 4, 125, 0.025, 0.025, 1.45)
    lf.foot(-62, 62, 0, 8, "cue_rack", 200)
    # spectators: chairs + lamp table on the west wall, club chairs on the south piers, fireside extras
    for yy in (860, 1020):
        S(g, "chair_dining", 4019, yy, 0, back=True, fb_half=27)
    S(g, "table_side", 4052, 940, 0)
    TT(g, "lamp_table", 4052, 920, 0, 65)
    TT(g, "radio_cathedral", 4058, 955, 0, 65)        # the radio stands on the lamp table, not on the floor
    for xx in (4750, 5250):
        S(g, "armchair_club", xx, 19, 90, back=True, fb_half=40)
    S(g, "ottoman", 5720, 900, 0)
    TT(g, "lamp_table", 5560, 650, 0, 65)
    S(g, "table_side", 5560, 1150, 0)
    TT(g, "lamp_table", 5560, 1150, 0, 65)
    S(g, "bar_cart", 4790, 1560, -90)
    TT(g, "vase_flowers", 4250, 1596, 0, 109, 0.6)       # on the bar counter
    card_group(g, 5450, 300)

    # ---------------- study: partners desk, typewriter, telephone, safe, fireside armchairs, bookcases
    g = "Dress_study"
    st = room_faces(G, "study")
    bookcases(b, g, st["N"], wall_spans(st["N"]), height=230, seed=17)
    rug(b, g, 5520, 2800, 420, 90, "MI_GW_Rug_ArtDeco")
    top = S(g, "desk_partners", 5520, 2800, 180)
    S(g, "chair_wingback", 5650, 2800, 180)
    if props.get("typewriter"):
        S(g, "typewriter", 5500, 2800, 180, z=top)
    if props.get("telephone"):
        S(g, "telephone", 5505, 2850, 200, z=top)
    TT(g, "lamp_table", 5505, 2738, 0, top)              # within 40 cm of look.KEY_LAMPS (5480, 2700)
    # safe prop: its door face sits exactly on s38_pickups.SAFE_FRONT (5900.25, 2499.75), yaw 135 (pickups overlay)
    S(g, "safe", 5923.2, 2476.8, 135, fit=(85, 75, 110)) if props.get("safe") else f_safe(LF(b, g, 5925, 2475, 135))
    S(g, "armchair_club", 4380, 2580, 150)
    S(g, "armchair_club", 4380, 3020, -150)
    S(g, "table_side", 4300, 2800, 0, lamp=True)
    S(g, "globe_floor", 5900, 3100, 200)
    # fireside chesterfield closing the armchair group, visitors' chairs at the desk, reading lamps
    S(g, "sofa_chesterfield", 4600, 2800, 180)
    TT(g, "lamp_table", 4300, 2800, 0, 65)
    S(g, "lamp_floor", 4720, 2620, 0)
    for yy in (2740, 2860):
        S(g, "chair_dining", 5405, yy, 0)
    R(g, "writing_bureau", 5250, 2419, 90, back=True)
    R(g, "film_projector", 5250, 3050, 0)
    R(g, "screen_folding", 4700, 3080, -90)             # the north wall is bookcases: no wall decor to keep

    # ---------------- conservatory: fountain, palms, wicker chairs
    g = "Dress_conservatory"
    f_fountain(b, g, 5250, 3850)
    for (xx, yy) in ((5895, 4290), (4125, 4290), (5895, 3305), (4600, 4290), (5895, 3800)):
        S(g, "palm_potted", xx, yy, 90)
    for (xx, yy, face) in ((4500, 3450, 60), (4700, 3600, 200), (5750, 4150, -120), (5550, 4280, -60)):
        S(g, "chair_wicker", xx, yy, face)
    S(g, "table_side", 4600, 3500, 0)
    S(g, "table_side", 5700, 4250, 0)
    for (xx, yy) in ((4600, 3500), (5700, 4250)):
        TT(g, "vase_flowers", xx, yy, 0, 65, 0.6)
    for (xx, yy) in ((4850, 4290), (5200, 4290), (5895, 3552), (4125, 3330)):
        S(g, "palm_potted", xx, yy, 90)
    # a third wicker group (south-east) and a pair facing the fountain
    S(g, "table_side", 5550, 3380, 0)
    TT(g, "vase_flowers", 5550, 3380, 0, 65, 0.6)
    ring(g, "chair_wicker", 5550, 3380, 100, [180, 0])
    S(g, "chair_wicker", 5150, 4080, -60)
    S(g, "chair_wicker", 5350, 4080, -120)
    for (xx, yy) in ((4380, 4300), (5300, 3300), (4130, 3560)):
        R(g, "fern_stand", xx, yy, 90)
    R(g, "birdcage", 5350, 4200, -90)
    R(g, "chaise_longue", 4500, 4100, -90)
    R(g, "screen_folding", 4250, 4100, -45)

    # ---------------- cloakroom: bench + umbrella stand (+ slots for the coat racks, trunk and dress form)
    g = "Dress_cloakroom"
    S(g, "bench", 3345, 260, 180, fit=FIT["bench"])
    S(g, "umbrella_stand", 2665, 70, 45)
    for xx in (2840, 3160):
        R(g, "coat_rack", xx, 290, -90)
    R(g, "dress_form", 3000, 150, 90)
    R(g, "trunk_steamer", 2622, 160, 0, back=True)

    # window seats: a bench under the south windows of the dining room, billiard room and hall, and under the
    # library's north windows (50 cm high: below every wall decor band; clear of the curtain blockers)
    if props.get("bench"):
        for (g, xs, yb, face) in (("Dress_dining", (500, 1000, 1500), 44, 90), ("Dress_billiard", (4500, 5000, 5500), 44, 90),
                                  ("Dress_hall", (2300, 3700), 44, 90), ("Dress_library", (400, 1000, 1600), 4356, -90)):
            for xx in xs:
                S(g, "bench", xx, yb, face, back=True, fit=FIT["bench"])
    build_wc(b)
    b.flush()
    # lamp lights
    for (x, y, z, cd, rad) in LAMPS:
        point_light((x, y, z), cd, rad, temp=2500, shadows=False, source_radius=6, label="L_Lamp", part="GW_Dress")
    # stage lights
    for xx in (2700, 3300):
        spot_light((xx, 3500, 690), 90 if xx < 3000 else 90, -45, 700, 1500, 15, 32, temp=3000, shadows=False,
                   label="L_StageSpot").set_editor_property("tags", [unreal.Name("GW_Gen"), unreal.Name("GW_Dress")])
    # candelabra flames for the lighting agent (keeps light_spots.json in sync with the dressing)
    spots_p = os.path.join(ROOT, "Tools", "level", "light_spots.json")
    try:
        spots = json.load(open(spots_p, encoding="utf-8"))
        spots["candles"] = CANDLES
        with open(spots_p, "w", encoding="utf-8") as fh:
            json.dump(spots, fh, indent=0)
    except (OSError, ValueError):
        pass
    with open(os.path.join(ROOT, "Tools", "level", "dress_state.json"), "w", encoding="utf-8") as fh:
        json.dump(dict(foot=FOOT, placed=PLACED, lamps=len(LAMPS), reserved=RESERVED, piano=PIANO,
                       instruments=INSTRUMENTS, wc=WC, wc_points=WC_POINTS, extra_doors=WC_DOORS), fh, indent=0)
    waiting = sorted({r[4] for r in RESERVED if not r[7]})
    print(f"  dress: props placed {sum(PLACED['props'].values())} ({sorted(PLACED['props'])}), "
          f"placeholders {sum(PLACED['fallback'].values())}, empty slots {sum(PLACED['waiting'].values())}, "
          f"lamps {len(LAMPS)}; "
          f"per room {dict(sorted(PLACED['rooms'].items()))}; reserved slots {len(RESERVED)} "
          f"({sum(1 for r in RESERVED if not r[7])} waiting for {len(waiting)} props: {waiting})")


# ------------------------------------------------------------------ W.C. (west end of the west corridor)
WC = []            # W.C. pieces (x0, y0, x1, y1, label, top, base): kept out of FOOT so the corridor's wall decor
                   # does not move; markers, audits, lanes and validate_walls read them from dress_state "wc"
WC_POINTS = []     # [tag, x, y, z, yaw]: GW_Toilet (in front of each bowl) + GW_Junkie
WC_DOORS = []      # extra doorways for lanes_check: dict(axis, at, center, width)
WC_X0, WC_X1 = 345.0, 365.0          # partition (between the corridor's sconce at x 300 and painting at x 407-478)
WC_DOOR = (2110.0, 2230.0, 230.0)    # door opening y0, y1, height
WC_DIVIDERS = (112.0, 225.0)         # stall dividers (the corridor's south-west bust stays west of the first one)
WC_STALLS = (168.5, 286.0)           # stall centres (stalls ~110-118 wide between the dividers and the partition)
WC_BASINS = (170.0, 270.0)


def _wc(lo, hi, label):
    WC.append((lo[0], lo[1], hi[0], hi[1], label, hi[2], lo[2]))


def build_wc(b, g="Dress_wc"):
    """W.C. carved from the dead-end west end of the west corridor: plastered partition with a doorway (open door
    leaf), two stalls (dividers, low-cistern toilets with wooden seats, paper holders), two pedestal basins with
    gilt mirrors, white tiled dado on the W.C. side. The corridor's own paintings, sconces, window and busts stay
    where they are (the partition sits in the gap between the sconce at x 300 and the painting at x 407-478)."""
    WC.clear()
    WC_POINTS.clear()
    WC_DOORS.clear()
    X0, X1 = WC_X0, WC_X1
    Y0, Y1 = 1817.0, 2383.0
    D0, D1, DZ = WC_DOOR
    TOP = 428.0                                   # crown moulding runs along both walls above this
    core, paper, dado, tile, trim = ("MI_GW_Plaster_Cream", "MI_GW_Wall_NavyGold", "MI_GW_Wood_Walnut",
                                     "MI_GW_Marble_White", "MI_GW_Wood_Dark")
    segs = ((Y0, D0, 0.0, TOP), (D1, Y1, 0.0, TOP), (D0, D1, DZ, TOP))
    for (a, c, z0, z1) in segs:
        b.box(g, core, X0 + 2, X1 - 2, a, c, z0, z1)
        _wc((X0, a, z0), (X1, c, z1), "wc_wall")
        # corridor face (east): walnut dado + navy/gold paper; W.C. face (west): white tiles + plaster
        b.box(g, dado, X1 - 2, X1, a, c, z0, max(z0, 100.0), coll=False)
        b.box(g, paper, X1 - 2, X1, a, c, max(z0, 100.0), z1, coll=False)
        b.box(g, tile, X0, X0 + 2, a, c, z0, max(z0, 150.0), coll=False)
        b.box(g, core, X0, X0 + 2, a, c, max(z0, 150.0), z1, coll=False)
    b.box(g, core, X0, X1, 1840, 2360, TOP, 450, coll=False)            # up to the ceiling between the crowns
    # baseboards / chair rail on the corridor face, tile cap on the W.C. face
    for (a, c) in ((Y0 + 3, D0 - 10), (D1 + 10, Y1 - 3)):
        b.box(g, trim, X1, X1 + 3, a, c, 0, 22, coll=False)
        b.box(g, trim, X1, X1 + 4, a, c, 96, 102, coll=False)
        b.box(g, trim, X0 - 2, X0, a, c, 148, 152, coll=False)
    # door casing (both faces), door leaf standing open inside the W.C. (no collision), brass plaque over the door
    for (v0, v1) in ((X1, X1 + 3), (X0 - 3, X0)):
        b.box(g, trim, v0, v1, D0 - 10, D0, 0, DZ + 10, coll=False)
        b.box(g, trim, v0, v1, D1, D1 + 10, 0, DZ + 10, coll=False)
        b.box(g, trim, v0, v1, D0 - 10, D1 + 10, DZ, DZ + 10, coll=False)
    # door leaf swung right back against the W.C. face of the partition (north of the doorway)
    b.box(g, "MI_GW_Wood_Walnut", X0 - 4, X0 - 0.5, D1 + 12, D1 + 128, 2, DZ - 4, coll=False)
    b.add(g, "SM_GW_Ball", "MI_GW_Brass", (X0 - 7, D1 + 116, 105), scale=(0.05, 0.05, 0.05), coll=False)
    b.box(g, "MI_GW_Brass", X1 + 3, X1 + 4, (D0 + D1) / 2 - 18, (D0 + D1) / 2 + 18, DZ + 18, DZ + 34, coll=False)
    WC_DOORS.append(dict(axis="x", at=(X0 + X1) / 2, center=(D0 + D1) / 2, width=D1 - D0))
    # two stalls along the south wall (dividers raised off the floor on brass feet, header rail across the fronts)
    SY0, SY1 = 1822.0, 1995.0
    for dx in WC_DIVIDERS:
        b.box(g, "MI_GW_Wood_Mahogany", dx - 1.5, dx + 1.5, SY0, SY1, 15, 205)
        for yy in (SY0 + 6, SY1 - 6):
            b.box(g, "MI_GW_Brass", dx - 2.5, dx + 2.5, yy - 2.5, yy + 2.5, 0, 15, coll=False)
        _wc((dx - 1.5, SY0, 0.0), (dx + 1.5, SY1, 205.0), "wc_divider")
    b.box(g, "MI_GW_Wood_Mahogany", WC_DIVIDERS[0] - 1.5, X0, SY1 - 2, SY1 + 2, 201, 207, coll=False)
    por = "MI_GW_Porcelain"
    for cx, dvx in zip(WC_STALLS, WC_DIVIDERS):
        b.box(g, por, cx - 20, cx + 20, 1820, 1838, 45, 80)                 # low cistern
        b.box(g, por, cx - 21, cx + 21, 1819, 1840, 80, 83, coll=False)
        b.box(g, "MI_GW_Brass", cx + 12, cx + 16, 1838, 1846, 74, 76, coll=False)     # flush lever
        b.add(g, "SM_GW_Cylinder", por, (cx, 1866, 15), scale=(0.24, 0.3, 0.3), coll=False)      # pedestal
        b.add(g, "SM_GW_Tulip", por, (cx, 1868, 30), scale=(2.0, 2.6, 0.6), coll=False)          # bowl
        b.add(g, "SM_GW_Torus", "MI_GW_Wood_Dark", (cx, 1868, 42), scale=(0.36, 0.46, 1.0), coll=False)  # seat
        b.box(g, "MI_GW_Wood_Dark", cx - 18, cx + 18, 1838, 1841, 43, 88, coll=False)          # seat lid (up)
        b.blocker(g, cx - 21, cx + 21, 1819, 1895, 0, 45)
        _wc((cx - 21, 1819, 0.0), (cx + 21, 1895, 88.0), "wc_toilet")
        hx = dvx + 1.5                                                       # paper holder on the west divider
        b.box(g, "MI_GW_Brass", hx, hx + 2, 1905, 1925, 72, 74, coll=False)
        b.add(g, "SM_GW_Cylinder", por, (hx + 6, 1915, 66), scale=(0.11, 0.11, 0.1), pitch=90, coll=False)
        WC_POINTS.append(["GW_Toilet", cx, 1945.0, 0.0, -90.0])
    # pedestal basins with gilt mirrors on the north wall
    for cx in WC_BASINS:
        b.add(g, "SM_GW_Cylinder", por, (cx, 2368, 35), scale=(0.18, 0.18, 0.7), coll=False)
        b.box(g, por, cx - 28, cx + 28, 2342, 2383, 72, 86)
        b.box(g, "MI_GW_Plaster_Cream", cx - 22, cx + 22, 2348, 2377, 86, 86.4, coll=False, shadow=False)
        for tx in (-9, 9):
            b.add(g, "SM_GW_Cylinder", "MI_GW_Brass", (cx + tx, 2376, 92), scale=(0.03, 0.03, 0.12), coll=False)
        b.add(g, "SM_GW_Cylinder", "MI_GW_Brass", (cx, 2370, 97), scale=(0.025, 0.025, 0.14), pitch=90, coll=False)
        b.blocker(g, cx - 28, cx + 28, 2342, 2383, 0, 88)
        _wc((cx - 28, 2342, 0.0), (cx + 28, 2383, 88.0), "wc_basin")
        b.box(g, "MI_GW_GoldLeaf", cx - 29, cx + 29, 2380, 2383, 112, 192, coll=False)
        b.box(g, "MI_GW_Mirror", cx - 25, cx + 25, 2379.4, 2380, 116, 188, coll=False, shadow=False)
    WC_POINTS.append(["GW_Junkie", 110.0, 2130.0, 0.0, 0.0])


def stage(b, g):
    x0, x1, y0, y1, h = 2500, 3500, 3880, 4380, 60     # y1 stops short of the dado panels
    b.box(g, "MI_GW_Wood_Mahogany", x0, x1, y0, y1, 0, h - 3)
    b.box(g, "MI_GW_Parquet", x0, x1, y0, y1, h - 3, h)
    b.box(g, "MI_GW_Brass", x0 - 1, x1 + 1, y0 - 2, y0, h - 4, h, coll=False)
    for k in range(10):
        b.add(g, "SM_GW_RaisedPanel", "MI_GW_Wood_Mahogany", (x0 + 50 + k * 100, y0, 8), yaw=180,
              scale=(0.8, 1.0, 0.42), coll=False)
    # steps (20 cm risers)
    sx0, sx1 = 2840, 3160
    b.box(g, "MI_GW_Wood_Mahogany", sx0, sx1, y0 - 60, y0 - 30, 0, 20)
    b.box(g, "MI_GW_Wood_Mahogany", sx0, sx1, y0 - 30, y0, 0, 40)
    b.box(g, "MI_GW_Carpet_Red", sx0 + 20, sx1 - 20, y0 - 61, y0 - 30, 20, 20.8, coll=False)
    b.box(g, "MI_GW_Carpet_Red", sx0 + 20, sx1 - 20, y0 - 31, y0, 40, 40.8, coll=False)
    # velvet backdrop + valance
    for k in range(10):
        b.add(g, "SM_GW_Curtain", "MI_GW_Velvet_Red", (x0 + 50 + k * 100, y1 - 2, 680), yaw=180,
              scale=(1.0, 1.0, (680 - h) / 100), coll=False)
    b.box(g, "MI_GW_Velvet_Gold", x0 - 40, x1 + 40, y1 - 30, y1, 600, 676, coll=False)
    b.box(g, "MI_GW_Gold", x0 - 41, x1 + 41, y1 - 31, y1, 596, 601, coll=False, shadow=False)
    # footlights
    for k in range(12):
        xx = x0 + 60 + k * (x1 - x0 - 120) / 11
        b.add(g, "SM_GW_Tulip", "MI_GW_Brass", (xx, y0 + 12, h), scale=(0.9, 0.9, 0.5), coll=False)
        b.add(g, "SM_GW_Flame", "MI_GW_Bulb", (xx, y0 + 12, h + 2), scale=(1.4, 1.4, 1.0), coll=False, shadow=False)
    FOOT.append((x0, y0 - 60, x1, y1, "stage", h, 0.0))


# ------------------------------------------------------------------ gameplay markers
def _free(x, y, margin=55):
    for fp in FOOT:
        x0, y0, x1, y1 = fp[:4]
        if x0 - margin < x < x1 + margin and y0 - margin < y < y1 + margin:
            return False
    return True


def build_markers(G):
    ds = {}
    try:
        ds = json.load(open(os.path.join(ROOT, "Tools", "level", "dress_state.json"), encoding="utf-8"))
        FOOT[:] = [tuple(f) for f in ds["foot"]]
        # floor kept for props that are not generated yet counts as furniture (markers must stay valid when they land)
        FOOT.extend(tuple(r[:7]) for r in ds.get("reserved", []) if not r[7])
        FOOT.extend(tuple(w) for w in ds.get("wc", []))
    except (OSError, ValueError):
        pass
    T = G["T"]
    # piano interaction point (gameplay: "press E to play the piano"), on the stage floor in front of the keys
    if ds.get("piano"):
        px, py, pz, pyaw = ds["piano"]
        target_point((px, py, pz), "GW_Piano", yaw=pyaw, label="GW_Piano")
    for (tag, ix, iy, iz, iyaw) in ds.get("instruments", []):           # GW_Instrument_Harp / _Bass / _Drums
        target_point((ix, iy, iz), tag, yaw=iyaw, label=tag)
    nt = 0
    for (tag, ix, iy, iz, iyaw) in ds.get("wc_points", []):             # GW_Toilet (x2) / GW_Junkie
        nt += tag == "GW_Toilet"
        target_point((ix, iy, iz), tag, yaw=iyaw, label=f"{tag}_{nt}" if tag == "GW_Toilet" else tag)
    # seekers: closed entrance vestibule / cloakroom south of the hall (door faces the hall, north)
    seek = [(2760, 200), (2920, 200), (3080, 200), (3240, 200), (2760, 380), (3240, 380)]
    for i, (x, y) in enumerate(seek):
        target_point((x, y, 100), "GW_SeekerSpawn", yaw=90, label=f"SeekerSpawn_{i}")
    # optional door leaf for the cloakroom doorway (hidden, no collision): gameplay may show it + enable collision
    # during the seekers' blind phase (actor tag GW_SeekerDoor)
    door = spawn(unreal.StaticMeshActor, (3000, 490, 125), part="GW_Markers", label="SeekerDoor",
                 extra_tags=("GW_SeekerDoor",))
    smc = door.get_component_by_class(unreal.StaticMeshComponent)
    smc.set_mobility(unreal.ComponentMobility.MOVABLE)
    smc.set_static_mesh(unreal.load_asset("/Game/GW/Meshes/Shapes/SM_GW_Cube"))
    smc.set_material(0, unreal.load_asset("/Game/GW/Materials/MI_GW_Wood_Walnut"))
    door.set_actor_scale3d(unreal.Vector(2.0, 0.06, 2.5))
    door.set_actor_hidden_in_game(True)
    door.set_actor_enable_collision(False)
    smc.set_editor_property("can_ever_affect_navigation", False)
    # player starts spread over the house
    starts = [(2650, 1150, 0), (3350, 1150, 180), (3000, 2000, -90), (2450, 1250, 0), (3000, 3000, 90),
              (2600, 3300, 0), (1000, 3000, 90), (1000, 500, 90), (4600, 1300, 0), (5000, 3000, 0),
              (4600, 3800, 0), (1000, 2100, 0), (5000, 2100, 180)]
    for i, (x, y, yaw) in enumerate(starts):
        k = 0
        while not _free(x, y, 70) and k < 40:          # nudge away from furniture
            x += 37 * math.cos(k * 2.4)
            y += 37 * math.sin(k * 2.4)
            k += 1
        spawn(unreal.PlayerStart, (x, y, 100), yaw=yaw, part="GW_Markers", label=f"PlayerStart_{i}")
    # NPC spawns: farthest-point sampling of free floor in each room
    quota = {"hall": 7, "ballroom": 7, "library": 5, "dining": 5, "billiard": 4, "study": 3, "conservatory": 4,
             "corridor_w": 3, "corridor_e": 3}
    n_total = 0
    rng = random.Random(1932)
    for room, q in quota.items():
        x0, y0, x1, y1 = G["ROOMS"][room]["rect"]
        cand = []
        for x in range(int(x0 + T + 70), int(x1 - T - 69), 40):
            for y in range(int(y0 + T + 70), int(y1 - T - 69), 40):
                if not _free(x, y):
                    continue
                if room == "corridor_w" and x < WC_X1 + 60:
                    continue                                   # W.C.
                if room == "hall" and ((2000 <= x <= 2330 or 3670 <= x <= 4000) and 950 <= y <= 1990):
                    continue                                   # stairs
                if room == "hall" and 2580 <= x <= 3420 and y <= 560:
                    continue                                   # cloakroom
                if room == "hall" and any(abs(x - cx) < 70 and abs(y - 1950) < 70 for cx in (2600, 3400)):
                    continue
                cand.append((x, y))
        if not cand:
            print("  !! no NPC spawn candidates in", room)
            continue
        pts = [rng.choice(cand)]
        while len(pts) < q:
            best = max(cand, key=lambda c: min((c[0] - p[0]) ** 2 + (c[1] - p[1]) ** 2 for p in pts))
            pts.append(best)
        for i, (x, y) in enumerate(pts):
            target_point((x, y, 100), "GW_NPCSpawn", yaw=rng.uniform(0, 360), label=f"NPCSpawn_{room}_{i}")
            n_total += 1
    for i, x in enumerate((2450, 3550)):
        target_point((x, 2170, 600), "GW_NPCSpawn", yaw=-90, label=f"NPCSpawn_gallery_{i}")
        n_total += 1
    print(f"  markers: {len(seek)} seeker spawns (cloakroom), {len(starts)} player starts, {n_total} NPC spawns, "
          f"GW_Piano {ds.get('piano')}, instruments {ds.get('instruments')}, W.C. {ds.get('wc_points')}")


# ------------------------------------------------------------------ review cameras
def _cam(name, loc, target, fov=75.0):
    dx, dy, dz = target[0] - loc[0], target[1] - loc[1], target[2] - loc[2]
    yaw = math.degrees(math.atan2(dy, dx))
    pitch = math.degrees(math.atan2(dz, math.hypot(dx, dy)))
    a = spawn(unreal.CameraActor, loc, yaw=yaw, pitch=pitch, part="GW_Cams", label=name, extra_tags=("GW_ReviewCam",))
    cc = a.get_component_by_class(unreal.CameraComponent)
    cc.set_editor_property("field_of_view", fov)
    cc.set_editor_property("constrain_aspect_ratio", False)
    return a


def build_cams(G):
    cams = [
        ("Cam_Hall_FromCloak", (3000, 640, 170), (3000, 2300, 420)),
        ("Cam_Hall_FromGallery", (3300, 2300, 670), (2700, 600, 250)),
        ("Cam_Hall_Stairs", (3880, 650, 175), (2250, 1800, 320)),
        ("Cam_Ballroom_Stage", (3000, 2600, 170), (3000, 4300, 220)),
        ("Cam_Ballroom_Diag", (3880, 2520, 260), (2300, 4200, 200)),
        ("Cam_Library_Fire", (1500, 2650, 170), (100, 3500, 150)),
        ("Cam_Library_Shelves", (1900, 4300, 190), (300, 2600, 120)),
        ("Cam_Dining_Table", (1650, 380, 240), (300, 1500, 90)),
        ("Cam_Dining_Fire", (1600, 1500, 170), (40, 900, 160)),
        ("Cam_Billiard", (4150, 200, 210), (5600, 1300, 90)),
        ("Cam_Billiard_Bar", (5400, 600, 170), (4300, 1750, 140)),
        ("Cam_CorridorW", (1950, 2250, 170), (0, 2050, 170)),
        ("Cam_CorridorE", (4050, 1950, 170), (6000, 2150, 170)),
        ("Cam_Study", (4150, 3100, 170), (5900, 2600, 120)),
        ("Cam_Conservatory", (4140, 4120, 230), (5800, 3350, 200)),
        ("Cam_Conservatory_Up", (5000, 3500, 150), (5600, 4400, 700)),
        ("Cam_Cloakroom", (3000, 470, 170), (3000, 0, 150)),
    ]
    for (n, loc, tgt) in cams:
        _cam(n, loc, tgt)
    print(f"  review cams: {len(cams)}")


# ------------------------------------------------------------------ navigation
def build_nav(G):
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    vol = spawn(unreal.NavMeshBoundsVolume, (3000, 2200, 480), part="GW_Nav", label="NavBounds_Manor")
    bb = vol.get_actor_bounds(False)
    ext = bb[1]
    if ext.x < 1:
        print("  !! nav bounds volume has no brush")
    sx, sy, sz = 6600 / (2 * ext.x), 4900 / (2 * ext.y), 1200 / (2 * ext.z)
    vol.set_actor_scale3d(unreal.Vector(sx, sy, sz))
    bb = vol.get_actor_bounds(False)
    print("  nav bounds centre", bb[0], "extent", bb[1])
    # the headless editor world never ticks, so the RecastNavMesh is not auto-created: spawn it, configure it
    # (DynamicModifiersOnly runtime generation) and build synchronously with the editor's BuildPaths command
    rn = [a for a in eas.get_all_level_actors() if isinstance(a, unreal.RecastNavMesh)]
    for a in rn:
        eas.destroy_actor(a)
    nm = eas.spawn_actor_from_class(unreal.RecastNavMesh, unreal.Vector(0, 0, 0))
    tag_actor(nm, "GW_Nav", "RecastNavMesh-Default")
    configure_recast()
    unreal.SystemLibrary.execute_console_command(world, "BuildPaths")
    p = unreal.NavigationSystemV1.project_point_to_navigation(world, unreal.Vector(3000, 700, 50), None, None,
                                                              unreal.Vector(80, 80, 250))
    print("  navmesh built; hall probe ->", None if p is None else (round(p.x), round(p.y), round(p.z)))


def configure_recast():
    navs = [a for a in eas.get_all_level_actors() if isinstance(a, unreal.RecastNavMesh)]
    for n in navs:
        # only nav modifiers update at runtime: full Dynamic rebuilt every tile at load (906 ms hitch, startup.csv)
        n.set_editor_property("runtime_generation", unreal.RuntimeGenerationType.DYNAMIC_MODIFIERS_ONLY)
        for k, v in (("agent_radius", 40.0), ("agent_height", 190.0), ("agent_max_step_height", 40.0),
                     ("agent_max_slope", 46.0)):
            try:
                n.set_editor_property(k, v)
            except Exception as e:
                print("   recast skip", k, e)
        print("  RecastNavMesh", n.get_name(), "runtime_generation =", n.get_editor_property("runtime_generation"))
    return navs
