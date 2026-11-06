"""Lighting + atmosphere for L_Manor (runs inside the Unreal Editor). Owner: lighting agent.

Called from Tools/build_manor.py:
  lights part -> build_lights(G)   (GW_Light actors + fixture emissive strengths + retune of the dress lamps)
  env part    -> build_env(G)      (GW_Env: garden, moon, sky, fog, haze, post-process)
  after dress -> tune_dress_lights(G)  (dress.py spawns the table/floor/bar lamps and the stage spots)
For look-dev without a full rebuild: Tools/lighting/lookdev.py.
All numbers live in look.py. Positions come from Tools/level/light_spots.json (written by the arch part), so the
lights follow the fixtures when the level agent moves them.
"""
import importlib
import json
import math
import os
import random
import sys

import unreal

ROOT = r"J:\Projets\Unreal_Projects\Guess Who"
for _p in (os.path.join(ROOT, "Tools", "level"), os.path.join(ROOT, "Tools", "lighting")):
    if _p not in sys.path:
        sys.path.insert(0, _p)
import lvl_common  # noqa: E402
import lvl_build  # noqa: E402
import look  # noqa: E402

importlib.reload(look)
from lvl_build import Batch, spawn, eas, mat  # noqa: E402

LAYOUT = lvl_common.load_layout()
ROOMS = {r["name"]: r for r in LAYOUT["rooms"]}
CLOAK = LAYOUT["cloakroom"]
GZ = LAYOUT["gallery"]["z"]
SPOTS_JSON = os.path.join(ROOT, "Tools", "level", "light_spots.json")
MOB = unreal.ComponentMobility.MOVABLE
STATS = {}


def log(*a):
    print(*a)


def room_of(x, y, z=100.0):
    x0, y0, x1, y1 = CLOAK["rect"]
    if x0 < x < x1 and y0 < y < y1 and z < CLOAK["height"]:
        return "cloakroom"
    for r in LAYOUT["rooms"]:
        x0, y0, x1, y1 = r["rect"]
        if x0 < x < x1 and y0 < y < y1:
            return r["name"]
    return "outside"


def moon_from():
    m = look.MOON
    az, el = math.radians(m["azimuth"]), math.radians(m["elevation"])
    return (math.cos(az) * math.cos(el), math.sin(az) * math.cos(el), math.sin(el))


# ------------------------------------------------------------------ generic light setup
def _setup(c, intensity, radius=None, temp=None, color=None, shadows=False, source_radius=None, soft=None,
           vol=0.0, indirect=1.0, specular=1.0, units=True, max_draw=0.0):
    c.set_mobility(MOB)
    if units:
        c.set_editor_property("intensity_units", unreal.LightUnits.CANDELAS)
    c.set_editor_property("intensity", float(intensity))
    if radius is not None:
        c.set_editor_property("attenuation_radius", float(radius))
    if color is not None:
        c.set_editor_property("use_temperature", False)
        c.set_editor_property("light_color", unreal.Color(r=color[0], g=color[1], b=color[2], a=255))
    elif temp is not None:
        c.set_editor_property("use_temperature", True)
        c.set_editor_property("temperature", float(temp))
        c.set_editor_property("light_color", unreal.Color(r=255, g=255, b=255, a=255))
    c.set_editor_property("cast_shadows", bool(shadows))
    c.set_editor_property("volumetric_scattering_intensity", float(vol))
    c.set_editor_property("indirect_lighting_intensity", float(indirect))
    c.set_editor_property("specular_scale", float(specular))
    try:
        c.set_editor_property("cast_volumetric_shadow", False)
    except Exception:
        pass
    if source_radius is not None:
        c.set_editor_property("source_radius", float(source_radius))
        c.set_editor_property("soft_source_radius", float(soft if soft is not None else source_radius))
    if max_draw:
        c.set_editor_property("max_draw_distance", float(max_draw))
        c.set_editor_property("max_distance_fade_range", float(max_draw) * 0.2)
    STATS["lights"] = STATS.get("lights", 0) + 1
    if shadows:
        STATS["shadowed"] = STATS.get("shadowed", 0) + 1


def point(loc, label, cd, radius, part="GW_Light", **kw):
    a = spawn(unreal.PointLight, loc, part=part, label=label)
    c = a.get_component_by_class(unreal.PointLightComponent)
    _setup(c, cd, radius, **kw)
    return a, c


def spot(loc, yaw, pitch, label, cd, radius, cone, part="GW_Light", **kw):
    a = spawn(unreal.SpotLight, loc, yaw=yaw, pitch=pitch, part=part, label=label)
    c = a.get_component_by_class(unreal.SpotLightComponent)
    _setup(c, cd, radius, **kw)
    c.set_editor_property("inner_cone_angle", float(cone[0]))
    c.set_editor_property("outer_cone_angle", float(cone[1]))
    return a, c


def rect(loc, yaw, pitch, label, cd, radius, w, h, part="GW_Light", barn=(70.0, 15.0), **kw):
    """Rect light emitting along its +X; width along local Y, height along local Z."""
    a = spawn(unreal.RectLight, loc, yaw=yaw, pitch=pitch, part=part, label=label)
    c = a.get_component_by_class(unreal.RectLightComponent)
    _setup(c, cd, radius, **kw)
    c.set_editor_property("source_width", float(w))
    c.set_editor_property("source_height", float(h))
    c.set_editor_property("barn_door_angle", float(barn[0]))
    c.set_editor_property("barn_door_length", float(barn[1]))
    return a, c


def indirect_for(room):
    return look.ROOM_INDIRECT.get(room, 1.0)


# ------------------------------------------------------------------ IES light profiles (written + imported here)
IES_DIR = os.path.join(ROOT, "Tools", "lighting", "ies")
IES_PKG = "/Game/GW/Lighting/IES"
_ies_cache = {}


def _ies_text(pairs):
    """LM-63-2002, type C, rotationally symmetric. pairs: (angle from nadir in deg, relative intensity)."""
    angs = list(range(0, 181, 5))
    pts = sorted(pairs)

    def val(a):
        for (a0, v0), (a1, v1) in zip(pts, pts[1:]):
            if a0 <= a <= a1:
                t = (a - a0) / max(1e-6, a1 - a0)
                t = t * t * (3 - 2 * t)
                return v0 + (v1 - v0) * t
        return pts[-1][1] if a > pts[-1][0] else pts[0][1]
    cd = [max(0.001, val(a)) * 1000.0 for a in angs]
    lines = ["IESNA:LM-63-2002", "[TEST] GW lighting", "[MANUFAC] Ashcombe Manor 1932", "TILT=NONE",
             f"1 1000 1 {len(angs)} 1 1 2 0 0 0", "1 1 0", " ".join(str(a) for a in angs), "0",
             " ".join(f"{c:.1f}" for c in cd)]
    return "\n".join(lines) + "\n"


def ies(name):
    """TextureLightProfile for look.IES[name]; re-imported only when the curve changed."""
    if name in _ies_cache:
        return _ies_cache[name]
    txt = _ies_text(look.IES[name])
    path = os.path.join(IES_DIR, name + ".ies")
    os.makedirs(IES_DIR, exist_ok=True)
    old = open(path, encoding="utf-8").read() if os.path.exists(path) else None
    asset_path = f"{IES_PKG}/{name}"
    if old != txt or not unreal.EditorAssetLibrary.does_asset_exist(asset_path):
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(txt)
        task = unreal.AssetImportTask()
        task.set_editor_property("filename", path)
        task.set_editor_property("destination_path", IES_PKG)
        task.set_editor_property("destination_name", name)
        task.set_editor_property("replace_existing", True)
        task.set_editor_property("automated", True)
        task.set_editor_property("save", True)
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        log("  imported IES", asset_path)
    prof = unreal.load_asset(asset_path)
    _ies_cache[name] = prof
    return prof


def set_ies(c, name):
    c.set_editor_property("ies_texture", ies(name))
    c.set_editor_property("use_ies_brightness", False)
    c.set_editor_property("ies_brightness_scale", 1.0)


# ------------------------------------------------------------------ fixture emissive / glass
def apply_fixture_materials():
    n = 0
    for name, vals in look.EMISSIVE.items():
        mi = unreal.load_asset("/Game/GW/Materials/" + name)
        if mi is None:
            log("  emissive: missing", name)
            continue
        for k, v in vals.items():
            if isinstance(v, tuple):
                unreal.MaterialEditingLibrary.set_material_instance_vector_parameter_value(
                    mi, k, unreal.LinearColor(v[0], v[1], v[2], 1.0))
            else:
                unreal.MaterialEditingLibrary.set_material_instance_scalar_parameter_value(mi, k, float(v))
        unreal.MaterialEditingLibrary.update_material_instance(mi)
        unreal.EditorAssetLibrary.save_loaded_asset(mi, False)
        n += 1
    log(f"  fixture materials tuned: {n}")


# ------------------------------------------------------------------ LIGHTS part
def build_lights(G=None, save_materials=True):
    STATS.clear()
    spots = json.load(open(SPOTS_JSON, encoding="utf-8"))
    chand_seen = {}
    for s in spots["spots"]:
        x, y, z = s["loc"]
        kind = s["kind"]
        room = room_of(x, y, z)
        if kind == "chandelier":
            _chandelier(s, room, chand_seen)
        elif kind == "sconce":
            cfg = look.SCONCE.get(room, look.SCONCE["default"])
            a, c = point((x, y, z), "L_Sconce", cfg["cd"], cfg["radius"], temp=cfg["temp"], source_radius=4, soft=8,
                         vol=0.25, indirect=indirect_for(room), specular=0.6, max_draw=4500)
            a.set_actor_rotation(unreal.Rotator(roll=0.0, pitch=-90.0, yaw=0.0), False)
            set_ies(c, "IES_GW_Sconce")
        elif kind == "lantern":
            c = look.LANTERN
            point((x, y, z), "L_Lantern", c["cd"], c["radius"], temp=c["temp"], source_radius=8, vol=c["vol"],
                  max_draw=5000)
    _billiard_lamp([s for s in spots["spots"] if s["kind"] == "billiard"])
    for fi in spots["fires"]:
        _fire(fi)
    pc = look.PICTURE
    for (loc, yaw) in spots["picture"]:
        room = room_of(loc[0], loc[1], loc[2])
        spot(tuple(loc), yaw + 180, -68, "L_PictureLight", pc["cd"], pc["radius"], pc["cone"], temp=pc["temp"],
             source_radius=pc["source_radius"], vol=0.0, indirect=0.6 * indirect_for(room), specular=0.3,
             max_draw=3500)
    mf = moon_from()
    wc = look.WINDOW
    for w in spots["windows"]:
        yaw = math.radians(w["yaw"])
        n_in = (math.cos(yaw), math.sin(yaw))
        moonlit = (-n_in[0] * mf[0] - n_in[1] * mf[1]) > 0.15
        lum = wc["lum_moon_side"] if moonlit else wc["lum_dark_side"]
        ww, hh = w["w"] * 0.9, w["h"] * 0.9
        rect(tuple(w["loc"]), w["yaw"], 0.0, "L_WindowMoon", lum * ww * hh / 10000.0, wc["radius"], ww, hh,
             temp=wc["temp"], vol=wc["vol"], specular=wc["specular"], indirect=1.0, max_draw=5000)
    for (label, loc, cd, radius, sh) in look.CANDLES:
        point(loc, label, cd, radius, temp=look.CANDLE_TEMP, shadows=sh, source_radius=3, soft=6, vol=0.3,
              indirect=indirect_for(room_of(*loc)), max_draw=3500)
    f = look.FOOTLIGHTS
    rect(f["loc"], 90, f["pitch"], "L_Footlights", f["cd"], f["radius"], f["w"], f["h"], temp=f["temp"], vol=0.4,
         barn=(80.0, 5.0), max_draw=5000)
    if save_materials:
        apply_fixture_materials()
    tune_dress_lights(G)
    log(f"  lights: {STATS.get('lights', 0)} spawned/tuned, shadowed {STATS.get('shadowed', 0)}")


def _chandelier(s, room, seen):
    """One point light at the candle ring, shaped by an IES curve (sideways onto walls and faces, a little down,
    very little up), shadowed for the key chandeliers."""
    x, y, z = s["loc"]
    r = s["radius"]
    key = room
    if room == "hall" and r < 50:
        key = "hall_small"
    cfg = look.CHANDELIER[key]
    idx = seen.get(key, 0)
    seen[key] = idx + 1
    pol = look.CHANDELIER_SHADOW_POLICY.get(key, "all")
    shadows = cfg["shadows"] and (pol == "all" or idx == 0)
    a, c = point((x, y, z), "L_Chandelier", cfg["cd"], cfg["radius"], temp=cfg["temp"], shadows=shadows,
                 source_radius=max(5.0, r * 0.4), soft=max(10.0, r * 0.6), vol=cfg["vol"],
                 indirect=indirect_for(room), specular=0.8)
    a.set_actor_rotation(unreal.Rotator(roll=0.0, pitch=-90.0, yaw=0.0), False)
    set_ies(c, cfg.get("ies", "IES_GW_Chandelier"))


def _billiard_lamp(lamps):
    if not lamps:
        return
    c = look.BILLIARD_LAMP
    xs = sorted(l["loc"][0] for l in lamps)
    mid = xs[len(xs) // 2]
    for l in lamps:
        x, y, z = l["loc"]
        sh = c["shadows"] == "all" or (c["shadows"] == "centre" and abs(x - mid) < 1)
        spot((x, y, z - 2), 0, -90, "L_BilliardLamp", c["cd"], c["radius"], c["cone"], temp=c["temp"], shadows=sh,
             source_radius=c["source_radius"], vol=c["vol"], indirect=indirect_for("billiard"), specular=0.8)


def _fire(fi):
    """Fire = shadowed spot thrown out of the firebox (a low, wide fan: little reaches the ceiling) + a small
    unshadowed glow on the surround and hearth. Both flicker (light function)."""
    cfg = dict(look.FIRE_COMMON)
    cfg.update(look.FIRE.get(fi["room"], {}))
    yaw = math.radians(fi["yaw"])
    ind = cfg["indirect"] * indirect_for(fi["room"])
    loc = (fi["x"] + math.cos(yaw) * cfg["forward"], fi["y"] + math.sin(yaw) * cfg["forward"], cfg["height"])
    a, c = spot(loc, fi["yaw"], cfg["pitch"], "L_Fire", cfg["cd"], cfg["radius"], cfg["cone"], temp=cfg["temp"],
                shadows=cfg["shadows"], source_radius=cfg["source_radius"], vol=cfg["vol"], indirect=ind, specular=0.5)
    c.set_editor_property("light_function_material", mat("Master/M_GW_LightFlicker"))
    g = cfg["glow"]
    loc2 = (fi["x"] + math.cos(yaw) * g["forward"], fi["y"] + math.sin(yaw) * g["forward"], g["height"])
    a2, c2 = point(loc2, "L_FireGlow", g["cd"], g["radius"], temp=cfg["temp"] - 100, source_radius=15, vol=0.2,
                   indirect=ind, specular=0.4)
    c2.set_editor_property("light_function_material", mat("Master/M_GW_LightFlicker"))


# ------------------------------------------------------------------ lights spawned by dress.py
def _bar_backlight(lamp):
    """Warm strip over the back-bar shelves (bottles and mirror glow), placed from the dress bar lamp (the back bar
    is on the billiard room's north wall, the lamp 40 cm in front of it)."""
    b = look.BAR_BACKLIGHT
    clear("GW_Light", ["L_BarBacklight"])
    rect((lamp.x, lamp.y + b["dy"], b["z"]), -90, b["pitch"], "L_BarBacklight", b["cd"], b["radius"], b["w"], b["h"],
         temp=b["temp"], vol=0.6, barn=(85.0, 5.0), max_draw=4000)


def bookcase_lights():
    """Brass picture lights over the built-in bookcases (library, study): a small fixture every ~1.5 m along each
    bookcase cornice and one rect light per run washing the books. Placed from the dress part's cornice instances,
    so they follow the bookcases."""
    cfg = look.BOOKCASE
    clear("GW_Light", ["L_Bookcase", "GW_BookcaseLights"])
    runs = []
    for a in eas.get_all_level_actors():
        if not a.actor_has_tag("GW_Dress"):
            continue
        for c in a.get_components_by_class(unreal.InstancedStaticMeshComponent):
            m = c.get_editor_property("static_mesh")
            mats = c.get_materials()
            if not m or m.get_name() != "SM_GW_Cornice" or not mats or not mats[0] or                     mats[0].get_name() != "MI_GW_Wood_Walnut":
                continue
            for i in range(c.get_instance_count()):
                t = c.get_instance_transform(i, True)
                l, yaw, sx = t.translation, t.rotation.rotator().yaw, t.scale3d.x
                if l.z > 150 and sx > 1.5 and room_of(l.x, l.y, 100) in cfg["rooms"]:
                    runs.append((l.x, l.y, l.z, yaw, sx * 100.0))
    if not runs:
        log("  bookcase lights: no bookcases found")
        return
    b = Batch("GW_Light")
    g = "BookcaseLights"
    for (x, y, z, yaw, length) in runs:
        ya = math.radians(yaw)
        d = (math.cos(ya), math.sin(ya))            # along the bookcase
        n = (-d[1], d[0])                           # into the room
        k = max(1, int(round(length / cfg["spacing"])))
        zf = z + cfg["dz"]
        for j in range(k):
            u = (j + 0.5) / k * length - length / 2
            px, py = x + d[0] * u + n[0] * cfg["out"], y + d[1] * u + n[1] * cfg["out"]
            # shade: horizontal brass tube along the bookcase, glowing slot underneath, arm back to the cornice
            b.add(g, "SM_GW_Cylinder", "MI_GW_Brass", (px, py, zf), yaw=yaw, pitch=-90,
                  scale=(0.055, 0.055, 0.44), coll=False, shadow=False)
            b.add(g, "SM_GW_Cube", "MI_GW_LampGlow", (px, py, zf - 2.6), yaw=yaw, scale=(0.4, 0.025, 0.012),
                  coll=False, shadow=False)
            b.add(g, "SM_GW_Cube", "MI_GW_Brass", (px - n[0] * cfg["out"] / 2, py - n[1] * cfg["out"] / 2, zf + 3),
                  yaw=yaw + 90, scale=(cfg["out"] / 100, 0.02, 0.02), coll=False, shadow=False)
        cx, cy = x + n[0] * cfg["out"], y + n[1] * cfg["out"]
        rect((cx, cy, zf - 4), math.degrees(math.atan2(-n[1], -n[0])), cfg["pitch"], "L_Bookcase",
             cfg["cd_per_m"] * length / 100.0, cfg["radius"], length - 30, 4, temp=cfg["temp"], vol=0.0,
             barn=(60.0, 12.0), specular=0.4, indirect=indirect_for(room_of(x, y, 100)), max_draw=4000)
    b.flush()
    log(f"  bookcase lights: {len(runs)} runs")


def tune_dress_lights(G=None):
    """dress.py lamps: the dress point light gets a lamp-shade IES (pool below, glow through the shade)."""
    n = 0
    clear("GW_Light", ["L_LampPool"])          # older rig versions
    for a in eas.get_all_level_actors():
        lab = a.get_actor_label()
        if lab.startswith("L_Lamp"):
            c = a.get_component_by_class(unreal.PointLightComponent)
            p = a.get_actor_location()
            room = room_of(p.x, p.y, p.z)
            kind = "bar" if p.z >= 200 else ("floor" if p.z >= 150 else "table")
            cfg = dict(look.LAMP[kind])
            k = look.LAMP_ROOM_SCALE.get(room, 1.0)
            for (kx, ky, over) in look.KEY_LAMPS:
                if abs(p.x - kx) < 40 and abs(p.y - ky) < 40:
                    cfg.update(over)
            _setup(c, cfg["cd"] * k, cfg["radius"], temp=cfg["temp"], shadows=cfg.get("shadows", False),
                   source_radius=6, soft=12, vol=0.3, indirect=indirect_for(room), specular=0.6, max_draw=4000)
            a.set_actor_rotation(unreal.Rotator(roll=0.0, pitch=-90.0, yaw=0.0), False)
            set_ies(c, "IES_GW_Shade")
            if kind == "bar":
                _bar_backlight(p)
            n += 1
        elif lab.startswith("L_StageSpot"):
            c = a.get_component_by_class(unreal.SpotLightComponent)
            s = look.STAGE_SPOT
            _setup(c, s["cd"], s["radius"], temp=s["temp"], shadows=s["shadows"], source_radius=6, soft=12,
                   vol=s["vol"], specular=0.8)
            c.set_editor_property("inner_cone_angle", float(s["cone"][0]))
            c.set_editor_property("outer_cone_angle", float(s["cone"][1]))
            n += 1
    bookcase_lights()
    log(f"  dress lights retuned: {n}")
    return n


# ------------------------------------------------------------------ ENV part
def build_env(G=None):
    # the level agent's storm island (always-loaded sublevel L_Manor_Island) replaces the old lawn/garden, which
    # would cover its sea; only the night-sky instance (normally set up at the end of _garden) is still needed
    if unreal.EditorAssetLibrary.does_asset_exist("/Game/GW/Maps/L_Manor_Island"):
        night_sky()
    else:
        _garden()
    _moon_and_sky()
    _haze()
    post_process()


def _garden():
    b = Batch("GW_Env")
    g = "Garden"
    b.box(g, "MI_GW_Grass", -4000, 12000, -4000, 14000, -90, -62)
    b.box(g, "MI_GW_Stone", 3000, 7600, 4415, 5600, -62, -6)
    b.box(g, "MI_GW_Stone", 6015, 7600, 1800, 4415, -62, -6)
    for (x0, x1, y0, y1) in ((2600, 7800, 5650, 5800), (7650, 7800, 1500, 5800)):
        b.box(g, "MI_GW_Foliage", x0, x1, y0, y1, -10, 140, coll=False)
    for (x, y) in ((4200, 5400), (5000, 5400), (5800, 5400), (7300, 4300), (7300, 3300), (7300, 2300)):
        b.add(g, "SM_GW_ColumnBase", "MI_GW_Stone", (x, y, -6), scale=(1.4, 1.4, 1.4), coll=False)
        b.add(g, "SM_GW_Ball", "MI_GW_Foliage", (x, y, 19), scale=(1.1, 1.1, 1.2), coll=False)
    gl = look.GARDEN_LAMP
    for (x, y) in ((4600, 5200), (7100, 3800), (7100, 2600)):
        b.add(g, "SM_GW_Cylinder", "MI_GW_Iron", (x, y, 140), scale=(0.08, 0.08, 2.9), coll=False)
        b.box(g, "MI_GW_LanternGlow", x - 12, x + 12, y - 12, y + 12, 285, 320, coll=False, shadow=False)
        b.add(g, "SM_GW_Cone", "MI_GW_Iron", (x, y, 330), scale=(0.34, 0.34, 0.2), coll=False)
        point((x, y, 300), "L_GardenLamp", gl["cd"], gl["radius"], part="GW_Env", temp=gl["temp"], source_radius=8,
              vol=gl["vol"], max_draw=8000)
    # a dark tree line (moonlit silhouettes in the mist) instead of a flat photo backdrop
    rng = random.Random(1932)
    trees = []
    for i in range(16):                                   # north, across the lawn
        trees.append((2500 + i * 420 + rng.uniform(-120, 120), 8200 + rng.uniform(-500, 600)))
    for i in range(12):                                   # east
        trees.append((10200 + rng.uniform(-500, 600), 400 + i * 520 + rng.uniform(-150, 150)))
    for i in range(6):                                    # a closer clump north-east, frames the view
        trees.append((8600 + rng.uniform(-400, 400), 6600 + i * 260 + rng.uniform(-100, 100)))
    for (x, y) in trees:
        hgt = rng.uniform(900, 1500)
        rad = rng.uniform(320, 520)
        b.add(g, "SM_GW_Cylinder", "MI_GW_Wood_Dark", (x, y, -62), scale=(0.35, 0.35, hgt * 0.5 / 100), coll=False)
        for k in range(3):
            rr = rad * rng.uniform(0.7, 1.05)
            b.add(g, "SM_GW_Sphere", "MI_GW_Foliage",
                  (x + rng.uniform(-rad, rad) * 0.4, y + rng.uniform(-rad, rad) * 0.4, hgt * (0.5 + 0.18 * k)),
                  scale=(rr / 50, rr / 50, rr * 1.15 / 50), coll=False)
    # the old photo backdrop, pushed far back and dimmed: only a faint skyline behind the trees
    b.add(g, "SM_GW_Plane", "MI_GW_Garden_Backdrop", (5000, 11500, 700), yaw=180, roll=90,
          scale=(120, 22, 1), coll=False, shadow=False)
    b.add(g, "SM_GW_Plane", "MI_GW_Garden_Backdrop", (14000, 2500, 700), yaw=90, roll=90,
          scale=(120, 22, 1), coll=False, shadow=False)
    b.flush()
    night_sky()


def night_sky():
    """Lighting's instance of the night-sky dome material (moon glow where the moonlight comes from), assigned to
    the dome the arch part builds (GW_Conservatory_Glass, SM_GW_Sphere + M_GW_NightSky)."""
    path = "/Game/GW/Lighting/MI_GW_NightSky"
    parent = unreal.load_asset("/Game/GW/Materials/Master/M_GW_NightSky")
    if parent is None:
        log("  night sky: no M_GW_NightSky yet")
        return
    mi = unreal.load_asset(path)
    if mi is None:
        mi = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
            "MI_GW_NightSky", "/Game/GW/Lighting", unreal.MaterialInstanceConstant,
            unreal.MaterialInstanceConstantFactoryNew())
    mel = unreal.MaterialEditingLibrary
    mel.set_material_instance_parent(mi, parent)
    mf = moon_from()
    vals = dict(look.NIGHT_SKY)
    vals["MoonDir"] = mf
    for k, v in vals.items():
        if isinstance(v, tuple):
            mel.set_material_instance_vector_parameter_value(mi, k, unreal.LinearColor(v[0], v[1], v[2], 1.0))
        else:
            mel.set_material_instance_scalar_parameter_value(mi, k, float(v))
    mel.update_material_instance(mi)
    unreal.EditorAssetLibrary.save_loaded_asset(mi, False)
    n = 0
    for a in eas.get_all_level_actors():
        for c in a.get_components_by_class(unreal.InstancedStaticMeshComponent):
            mats = c.get_materials()
            if mats and mats[0] and mats[0].get_name() in ("M_GW_NightSky", "MI_GW_NightSky"):
                c.set_material(0, mi)
                n += 1
    log(f"  night sky instance assigned to {n} dome(s)")


def _moon_and_sky():
    m = look.MOON
    az = m["azimuth"]
    moon = spawn(unreal.DirectionalLight, (6000, 4400, 2000), yaw=az + 180.0, pitch=-m["elevation"], part="GW_Env",
                 label="L_Moon")
    c = moon.get_component_by_class(unreal.DirectionalLightComponent)
    c.set_mobility(MOB)
    c.set_editor_property("intensity", float(m["lux"]))
    c.set_editor_property("use_temperature", True)
    c.set_editor_property("temperature", float(m["temp"]))
    c.set_editor_property("light_color", unreal.Color(r=255, g=255, b=255, a=255))
    c.set_editor_property("cast_shadows", True)
    c.set_editor_property("light_source_angle", float(m["source_angle"]))
    c.set_editor_property("volumetric_scattering_intensity", float(m["volumetric"]))
    c.set_editor_property("specular_scale", float(m["specular"]))
    try:
        c.set_editor_property("cast_volumetric_shadow", True)
    except Exception:
        pass
    sk = look.SKY
    sky = spawn(unreal.SkyLight, (3000, 2200, 1500), part="GW_Env", label="SkyLight_Night")
    sc = sky.get_component_by_class(unreal.SkyLightComponent)
    sc.set_mobility(MOB)
    sc.set_editor_property("intensity", float(sk["intensity"]))
    t = sk["tint"]
    sc.set_editor_property("light_color", unreal.Color(r=int(255 * t[0]), g=int(255 * t[1]), b=int(255 * t[2]), a=255))
    sc.set_editor_property("lower_hemisphere_is_black", True)
    sc.set_editor_property("real_time_capture", False)
    sc.set_editor_property("volumetric_scattering_intensity", float(sk["volumetric"]))
    fg = look.FOG
    fog = spawn(unreal.ExponentialHeightFog, (3000, 2200, fg["height"]), part="GW_Env", label="Fog_Night")
    fc = fog.get_component_by_class(unreal.ExponentialHeightFogComponent)
    props = dict(fog_density=fg["density"], fog_height_falloff=fg["falloff"], start_distance=fg["start"],
                 fog_max_opacity=fg["max_opacity"],
                 fog_inscattering_luminance=unreal.LinearColor(*fg["sky_luminance"], 1.0),
                 enable_volumetric_fog=fg["volumetric"], volumetric_fog_extinction_scale=fg["vol_extinction_scale"],
                 volumetric_fog_scattering_distribution=fg["vol_distribution"],
                 volumetric_fog_albedo=unreal.Color(r=int(255 * fg["vol_albedo"][0]), g=int(255 * fg["vol_albedo"][1]),
                                                    b=int(255 * fg["vol_albedo"][2]), a=255),
                 volumetric_fog_distance=fg["vol_distance"], volumetric_fog_start_distance=fg["vol_start"],
                 volumetric_fog_emissive=unreal.LinearColor(*fg["vol_emissive"], 1.0))
    for k, v in props.items():
        try:
            fc.set_editor_property(k, v)
        except Exception as e:
            log("   fog skip", k, e)


def _haze():
    """Local fog volumes (rendered into the volumetric fog): denser air where the moon shafts and the pool-lamp
    cones should read, so the global fog can stay thin (the conservatory and the garden stay clear)."""
    cls = getattr(unreal, "LocalFogVolume", None)
    if cls is None:
        log("   no LocalFogVolume class")
        return
    for (label, loc, scale, radial, height) in look.HAZE:
        a = spawn(cls, loc, part="GW_Env", label=label)
        a.set_actor_scale3d(unreal.Vector(*scale))
        c = a.get_component_by_class(unreal.LocalFogVolumeComponent)
        for k, v in (("radial_fog_extinction", radial), ("height_fog_extinction", height),
                     ("fog_phase_g", 0.5), ("fog_albedo", unreal.LinearColor(1, 1, 1, 1))):
            try:
                c.set_editor_property(k, v)
            except Exception as e:
                log("   haze skip", k, e)


def post_process():
    ppv = spawn(unreal.PostProcessVolume, (3000, 2200, 500), part="GW_Env", label="PP_Manor_Night")
    ppv.set_editor_property("unbound", True)
    ppv.set_editor_property("priority", 1.0)
    s = ppv.get_editor_property("settings")
    e, g, lu = look.EXPOSURE, look.GRADE, look.LUMEN
    V4 = lambda t, w=1.0: unreal.Vector4(t[0], t[1], t[2], w)  # noqa: E731
    sat = g["saturation"]
    vals = {
        "auto_exposure_method": unreal.AutoExposureMethod.AEM_HISTOGRAM,
        "auto_exposure_min_brightness": e["min_ev"],
        "auto_exposure_max_brightness": e["max_ev"],
        "auto_exposure_bias": e["bias"],
        "auto_exposure_speed_up": e["speed_up"],
        "auto_exposure_speed_down": e["speed_down"],
        "auto_exposure_low_percent": e["low_percent"],
        "auto_exposure_high_percent": e["high_percent"],
        "auto_exposure_apply_physical_camera_exposure": False,
        "temperature_type": unreal.TemperatureMethod.TEMP_WHITE_BALANCE,
        "white_temp": g["white_temp"],
        "white_tint": g["white_tint"],
        "color_saturation": V4((sat, sat, sat)),
        "color_saturation_highlights": V4((g["saturation_highlights"],) * 3),
        "color_contrast": V4((g["contrast"],) * 3),
        "color_gain_shadows": V4(g["gain_shadows"]),
        "color_offset_shadows": V4(g["offset_shadows"], 0.0),
        "color_gain_highlights": V4(g["gain_highlights"]),
        "color_gamma": V4(g["gamma"]),
        "color_gain": V4((1.0, 1.0, 1.0)),
        "film_slope": g["film_slope"],
        "film_toe": g["film_toe"],
        "film_shoulder": g["film_shoulder"],
        "film_black_clip": g["film_black_clip"],
        "film_white_clip": g["film_white_clip"],
        "bloom_intensity": g["bloom"],
        "bloom_threshold": g["bloom_threshold"],
        "vignette_intensity": g["vignette"],
        "film_grain_intensity": g["grain"],
        "scene_fringe_intensity": g["fringe"],
        "sharpen": g["sharpen"],
        "motion_blur_amount": 0.0,
        "local_exposure_highlight_contrast_scale": g["local_exposure_highlights"],
        "local_exposure_shadow_contrast_scale": g["local_exposure_shadows"],
        "lumen_final_gather_quality": lu["final_gather_quality"],
        "lumen_scene_lighting_quality": lu["scene_lighting_quality"],
        "lumen_scene_detail": lu["scene_detail"],
        "lumen_reflection_quality": lu["reflection_quality"],
        "lumen_max_trace_distance": lu["max_trace_distance"],
        "lumen_final_gather_lighting_update_speed": lu["final_gather_update_speed"],
        "lumen_scene_lighting_update_speed": lu["scene_lighting_update_speed"],
        "lumen_max_reflection_bounces": lu["max_reflection_bounces"],
        "lumen_skylight_leaking": lu["skylight_leaking"],
        "lumen_diffuse_color_boost": lu["diffuse_color_boost"],
    }
    skipped = []
    for k, v in vals.items():
        try:
            s.set_editor_property(k, v)
        except Exception as ex:
            skipped.append(f"{k}: {ex}")
            continue
        try:
            s.set_editor_property("override_" + k, True)
        except Exception as ex:
            skipped.append(f"override_{k}: {ex}")
    ppv.set_editor_property("settings", s)
    if skipped:
        log("   pp skipped:", skipped)
    room_volumes()


def room_volumes():
    """Bounded PostProcessVolumes per room: exposure compensation (the eye opening up in the walnut rooms) and
    small grade nudges, blended across the doorways (blend radius)."""
    n = 0
    for room, cfg in look.ROOM_GRADE.items():
        if room == "cloakroom":
            x0, y0, x1, y1 = CLOAK["rect"]
            z0, z1, prio = 0, CLOAK["height"], 3.0
        elif room == "gallery":
            x0, y0, x1, y1 = LAYOUT["gallery"]["rect"]
            z0, z1, prio = GZ, ROOMS["hall"]["height"], 3.0
        else:
            x0, y0, x1, y1 = ROOMS[room]["rect"]
            z0, z1, prio = 0, ROOMS[room]["height"], 2.0
        pad = 15.0
        v = spawn(unreal.PostProcessVolume, ((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2), part="GW_Env",
                  label="PP_Room_" + room)
        v.set_actor_scale3d(unreal.Vector((x1 - x0 - 2 * pad) / 200.0, (y1 - y0 - 2 * pad) / 200.0, (z1 - z0) / 200.0))
        v.set_editor_property("unbound", False)
        v.set_editor_property("priority", prio)
        v.set_editor_property("blend_radius", float(look.ROOM_BLEND_RADIUS))
        v.set_editor_property("blend_weight", 1.0)
        st = v.get_editor_property("settings")
        vals = {"auto_exposure_bias": cfg.get("ev", 0.0)}
        if "saturation" in cfg:
            sat = cfg["saturation"]
            vals["color_saturation"] = unreal.Vector4(sat[0], sat[1], sat[2], 1.0) if isinstance(sat, tuple) else                 unreal.Vector4(sat, sat, sat, 1.0)
        if "gain" in cfg:
            gg = cfg["gain"]
            vals["color_gain"] = unreal.Vector4(gg[0], gg[1], gg[2], 1.0)
        if "white_temp" in cfg:
            vals["white_temp"] = cfg["white_temp"]
        for k, val in vals.items():
            st.set_editor_property(k, val)
            st.set_editor_property("override_" + k, True)
        v.set_editor_property("settings", st)
        n += 1
    log(f"  room post volumes: {n}")


# ------------------------------------------------------------------ helpers for build_manor / lookdev
def clear(tag, label_prefixes=None):
    doomed = [a for a in eas.get_all_level_actors() if a.actor_has_tag("GW_Gen") and a.actor_has_tag(tag)
              and (label_prefixes is None or a.get_actor_label().startswith(tuple(label_prefixes)))]
    if doomed:
        eas.destroy_actors(doomed)
    return len(doomed)
