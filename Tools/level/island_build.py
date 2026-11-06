"""(in editor) Storm-island exterior in its own always-loaded sublevel /Game/GW/Maps/L_Manor_Island.

  level/run.sh level/island_build.py [mesh] [audio] [level]      (no args = all three)

mesh  : island_src/meshes/*.obj -> /Game/GW/Meshes/Island (no collision; Nanite for the island + boulders; sea grid,
        trees, crowns and shrubs stay non-Nanite for their world-position-offset waves / wind sway)
audio : island_src/audio/*.wav -> /Game/GW/Environment/Audio (+ ATT_GW_Exterior: low-passed beyond 6 m)
level : (re)builds every GW_Island actor inside L_Manor_Island from island_src/layout.json (island_layout.py):
        island + plinth, sea, boulders, wind-bent trees and shrubs, garden lamps (flickering), rain curtains outside
        the windows, wind/sea/rain ambience, the storm actor (BP_GW_Storm, lightning + thunder); then removes the
        lighting agent's old garden (GW_Garden + L_GardenLamp) from L_Manor and saves both levels.
Materials/textures: island_materials.py (run it first).
"""
import json
import os
import sys

import unreal

TL = r"J:\Projets\Unreal_Projects\Guess Who\Tools\level"
if TL not in sys.path:
    sys.path.insert(0, TL)
import importlib  # noqa: E402

import lvl_build  # noqa: E402

importlib.reload(lvl_build)
from lvl_build import Batch, point_light, spawn, eas  # noqa: E402

eal = unreal.EditorAssetLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
SRC = os.path.join(TL, "island_src")
MESHD = "/Game/GW/Meshes/Island"
AUDD = "/Game/GW/Environment/Audio"
ENV = "/Game/GW/Environment"
SUB = "/Game/GW/Maps/L_Manor_Island"
PART = "GW_Island"
ARGS = [a.lower() for a in globals().get("UE_ARGS", [])] or ["mesh", "audio", "level"]
NANITE = {"SM_GW_Island", "SM_GW_Boulder_A", "SM_GW_Boulder_B", "SM_GW_Boulder_C"}


def M(name):
    return f"{MESHD}/{name}"


def import_meshes():
    tasks = []
    for fn in sorted(os.listdir(os.path.join(SRC, "meshes"))):
        if not fn.endswith(".obj"):
            continue
        t = unreal.AssetImportTask()
        t.filename = os.path.join(SRC, "meshes", fn)
        t.destination_path = MESHD
        t.destination_name = fn[:-4]
        t.automated = True
        t.replace_existing = True
        t.save = False
        tasks.append(t)
    tools.import_asset_tasks(tasks)
    sms = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    n = 0
    for t in tasks:
        for p in t.imported_object_paths:
            a = unreal.load_asset(p)
            if isinstance(a, unreal.StaticMesh):
                sms.remove_collisions(a)
                ns = a.get_editor_property("nanite_settings")
                ns.set_editor_property("enabled", a.get_name() in NANITE)
                a.set_editor_property("nanite_settings", ns)
                eal.save_loaded_asset(a)
                n += 1
            elif isinstance(a, (unreal.MaterialInterface, unreal.Texture)):
                eal.delete_loaded_asset(a)
    for p in eal.list_assets(MESHD, recursive=True):
        a = unreal.load_asset(p)
        if not isinstance(a, unreal.StaticMesh):
            eal.delete_asset(p)
    print(f"  island meshes: {n}/{len(tasks)}")


SOUNDS = {"thunder_1": ("SC_GW_SFX", False), "thunder_2": ("SC_GW_SFX", False), "thunder_3": ("SC_GW_SFX", False),
          "rain_loop": ("SC_GW_Ambience", True), "wind_loop": ("SC_GW_Ambience", True),
          "sea_loop": ("SC_GW_Ambience", True)}


def import_audio():
    eal.make_directory(AUDD)
    tasks = []
    for name in SOUNDS:
        t = unreal.AssetImportTask()
        t.filename = os.path.join(SRC, "audio", name + ".wav")
        t.destination_path = AUDD
        t.destination_name = "SW_GW_" + "".join(w.capitalize() for w in name.split("_"))
        t.automated = True
        t.replace_existing = True
        t.save = False
        tasks.append(t)
    tools.import_asset_tasks(tasks)
    for (name, (cls, loop)), t in zip(SOUNDS.items(), tasks):
        sw = unreal.load_asset(f"{AUDD}/{t.destination_name}")
        if sw is None:
            print("  !! sound not imported", name)
            continue
        sw.set_editor_property("looping", loop)
        sc = unreal.load_asset(f"/Game/GW/Audio/Classes/{cls}")
        if sc:
            sw.set_editor_property("sound_class_object", sc)
        eal.save_loaded_asset(sw)
    # exterior attenuation: audible around the house, muffled (low-passed) beyond 6 m, silent past 30 m
    path = f"{ENV}/ATT_GW_Exterior"
    att = unreal.load_asset(path) if eal.does_asset_exist(path) else tools.create_asset(
        "ATT_GW_Exterior", ENV, unreal.SoundAttenuation, unreal.SoundAttenuationFactory())
    s = att.get_editor_property("attenuation")
    for k, v in (("attenuate", True), ("spatialize", True), ("attenuation_shape", unreal.AttenuationShape.SPHERE),
                 ("attenuation_shape_extents", unreal.Vector(400, 0, 0)), ("falloff_distance", 2600.0),
                 ("attenuate_with_lpf", True), ("lpf_radius_min", 600.0), ("lpf_radius_max", 2400.0),
                 ("lpf_frequency_at_min", 18000.0), ("lpf_frequency_at_max", 900.0)):
        try:
            s.set_editor_property(k, v)
        except Exception as e:
            print("   attenuation skip", k, e)
    att.set_editor_property("attenuation", s)
    eal.save_loaded_asset(att)
    print(f"  island audio: {len(tasks)} waves + ATT_GW_Exterior")


# ------------------------------------------------------------------ level
def les():
    return unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)


def world():
    return unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()


def ensure_sublevel():
    w = world()
    if unreal.GameplayStatics.get_streaming_level(w, "L_Manor_Island") is None:
        if eal.does_asset_exist(SUB):
            unreal.EditorLevelUtils.add_level_to_world(w, SUB, unreal.LevelStreamingAlwaysLoaded)
        else:
            unreal.EditorLevelUtils.create_new_streaming_level(unreal.LevelStreamingAlwaysLoaded, SUB, False)
        print("  sublevel added:", SUB)
    if not les().set_current_level_by_name("L_Manor_Island"):
        raise RuntimeError("could not make L_Manor_Island current")


def current_is_sublevel():
    lvl = les().get_current_level()
    return lvl is not None and "L_Manor_Island" in lvl.get_path_name()


def restore_persistent():
    for name in ("L_Manor", "PersistentLevel"):
        if les().set_current_level_by_name(name) and not current_is_sublevel():
            return True
    return not current_is_sublevel()


def clear_island():
    doomed = [a for a in eas.get_all_level_actors() if a.actor_has_tag(PART)]
    if doomed:
        eas.destroy_actors(doomed)
    print(f"  cleared {len(doomed)} {PART} actors")


def ambient(loc, wave, vol, label):
    a = eas.spawn_actor_from_class(unreal.AmbientSound, unreal.Vector(*loc))
    a.set_editor_property("tags", [unreal.Name("GW_Gen"), unreal.Name(PART)])
    a.set_actor_label(label)
    a.set_folder_path("GW/Island")
    ac = a.get_component_by_class(unreal.AudioComponent)
    ac.set_editor_property("sound", unreal.load_asset(f"{AUDD}/{wave}"))
    ac.set_editor_property("volume_multiplier", vol)
    ac.set_editor_property("auto_activate", True)
    ac.set_editor_property("override_attenuation", False)
    ac.set_editor_property("attenuation_settings", unreal.load_asset(f"{ENV}/ATT_GW_Exterior"))
    return a


def build_level():
    lay = json.load(open(os.path.join(SRC, "layout.json"), encoding="utf-8"))
    ensure_sublevel()
    try:
        clear_island()
        b = Batch(PART)
        b.add("Island_Ground", M("SM_GW_Island"), "/Game/GW/Environment/MI_GW_Island", (0, 0, 0), coll=False)
        sea = lay["sea"]
        b.add("Island_Sea", M("SM_GW_SeaGrid"), "/Game/GW/Environment/MI_GW_Sea", tuple(sea["loc"]),
              scale=tuple(sea["scale"]), coll=False, shadow=False)
        for (x0, y0, x1, y1, z0, z1) in lay["plinth"]:
            b.box("Island_Plinth", "MI_GW_Stone", x0, x1, y0, y1, z0, z1, coll=False)
        for (x0, x1, y0, y1, z0, z1) in lay.get("steps", []):          # front steps down to the gravel
            b.box("Island_Plinth", "MI_GW_Stone", x0, x1, y0, y1, z0, z1, coll=False)
        for (x, y, z) in lay.get("balustrade", []):                     # terrace balustrade (posts + rail)
            b.box("Island_Balustrade", "MI_GW_Stone", x - 16, x + 16, y - 16, y + 16, z - 10, z + 82, coll=False)
            b.add("Island_Balustrade", "SM_GW_Finial", "MI_GW_Stone", (x, y, z + 82), scale=(2.0, 2.0, 1.2),
                  coll=False)
        bal = lay.get("balustrade", [])
        for p0, p1 in zip(bal, bal[1:]):
            if abs(p1[0] - p0[0]) < 300:                                # consecutive posts: rail between them
                zt = max(p0[2], p1[2]) + 70
                b.box("Island_Balustrade", "MI_GW_Stone", p0[0] + 16, p1[0] - 16, p0[1] - 9, p0[1] + 9, zt, zt + 12,
                      coll=False)
                for k in range(1, 4):                                   # balusters
                    bx = p0[0] + (p1[0] - p0[0]) * k / 4
                    b.add("Island_Balustrade", "SM_GW_Baluster", "MI_GW_Stone", (bx, p0[1], zt - 62),
                          scale=(1.6, 1.6, 0.775), coll=False)
        lh = lay.get("lighthouse")
        if lh:                                   # distant lighthouse on a rock, blinking through the storm
            x, y, z = lh
            for k, (sx, sz) in enumerate(((14.0, 6.0), (9.0, 7.5), (6.0, 4.0))):
                b.add("Island_Lighthouse", M("SM_GW_Boulder_B"), "/Game/GW/Environment/MI_GW_Island",
                      (x + k * 180, y - k * 120, z - 300), yaw=k * 70, scale=(sx, sx * 0.9, sz), coll=False)
            b.add("Island_Lighthouse", "SM_GW_Cylinder", "MI_GW_Plaster_Cream", (x, y, z + 1700),
                  scale=(4.2, 4.2, 18.0), coll=False)
            b.add("Island_Lighthouse", "SM_GW_Cylinder", "MI_GW_Iron", (x, y, z + 2620), scale=(5.0, 5.0, 0.4), coll=False)
            b.add("Island_Lighthouse", "SM_GW_Sphere", "/Game/GW/Environment/MI_GW_Beacon", (x, y, z + 2790),
                  scale=(3.4, 3.4, 3.4), coll=False, shadow=False)
            b.add("Island_Lighthouse", "SM_GW_Cone", "MI_GW_Iron", (x, y, z + 3060), scale=(5.2, 5.2, 2.0), coll=False)
        for bo in lay["boulders"]:
            b.add("Island_Rocks", M(bo["mesh"]), "/Game/GW/Environment/MI_GW_Island", tuple(bo["loc"]), yaw=bo["yaw"],
                  scale=tuple(bo["scale"]), coll=False)
        for t in lay["trees"]:
            s = t["scale"]
            b.add("Island_Trees", M(t["mesh"]), "/Game/GW/Environment/MI_GW_Bark", tuple(t["loc"]), yaw=t["yaw"],
                  scale=(s, s, s), coll=False)
            for c in t["crowns"]:
                cs = c["scale"]
                b.add("Island_Trees", M(c["mesh"]), "/Game/GW/Environment/MI_GW_Crown", tuple(c["loc"]), yaw=c["yaw"],
                      scale=(cs, cs * 0.9, cs * 0.8), coll=False)
        for bu in lay["bushes"]:
            s = bu["scale"]
            b.add("Island_Shrubs", M(bu["mesh"]), "/Game/GW/Environment/MI_GW_Bush", tuple(bu["loc"]), yaw=bu["yaw"],
                  scale=(s, s, s * 0.9), coll=False)
        for (x, y, z) in lay["lamps"]:
            b.add("Island_Lamps", "SM_GW_Cylinder", "MI_GW_Iron", (x, y, z + 145), scale=(0.09, 0.09, 2.9), coll=False)
            b.add("Island_Lamps", "SM_GW_ColumnBase", "MI_GW_Stone", (x, y, z - 5), scale=(0.5, 0.5, 0.5), coll=False)
            b.box("Island_Lamps", "MI_GW_LanternGlow", x - 13, x + 13, y - 13, y + 13, z + 288, z + 326, coll=False,
                  shadow=False)
            b.add("Island_Lamps", "SM_GW_Cone", "MI_GW_Iron", (x, y, z + 336), scale=(0.36, 0.36, 0.22), coll=False)
            point_light((x, y, z + 308), 70, 650, temp=2100, shadows=False, source_radius=8, label="L_IslandLamp",
                        light_fn="Master/M_GW_LightFlicker", part=PART)
        for r in lay["rain"]:
            w, h = r["size"]
            yaw = 0.0 if r["axis"] == "y" else 90.0
            b.add("Island_Rain", "SM_GW_Plane_NoNanite", "/Game/GW/Environment/MI_GW_RainCurtain", tuple(r["loc"]),
                  yaw=yaw, roll=90, scale=(w / 100, h / 100, 1), coll=False, shadow=False)
        b.flush()
        for i, loc in enumerate(lay["wind"]):
            ambient(loc, "SW_GW_WindLoop", 0.22, f"AMB_Island_Wind_{i}")
        for i, loc in enumerate(lay["sea_sounds"]):
            ambient(loc, "SW_GW_SeaLoop", 0.3, f"AMB_Island_Sea_{i}")
        for i, loc in enumerate(lay["rain_sounds"]):
            ambient(loc, "SW_GW_RainLoop", 0.16, f"AMB_Island_Rain_{i}")
        storm = unreal.load_asset(f"{ENV}/BP_GW_Storm")
        if storm:
            a = eas.spawn_actor_from_class(storm.generated_class(), unreal.Vector(3000, 2200, 2500),
                                           unreal.Rotator(roll=0.0, pitch=-32.0, yaw=35.0))
            a.set_editor_property("tags", [unreal.Name("GW_Gen"), unreal.Name(PART)])
            a.set_actor_label("BP_GW_Storm")
            a.set_folder_path("GW/Island")
        else:
            print("  (no BP_GW_Storm yet: lightning not placed)")
        if not les().save_current_level():
            print("  !! sublevel save failed")
        else:
            print("  saved", SUB)
    finally:
        restore_persistent()
    # the lighting agent's lawn/garden (GW_Env) would cover the sea: the island replaces it (rig.build_env skips
    # _garden() once L_Manor_Island exists)
    gone = [a for a in eas.get_all_level_actors() if a.actor_has_tag("GW_Env") and
            (a.get_actor_label() == "GW_Garden" or a.get_actor_label().startswith("L_GardenLamp"))]
    if gone:
        eas.destroy_actors(gone)
    print(f"  removed {len(gone)} old garden actors; current level persistent: {not current_is_sublevel()}")
    les().save_current_level()
    print("  saved /Game/GW/Maps/L_Manor")


if "mesh" in ARGS:
    import_meshes()
if "audio" in ARGS:
    import_audio()
if "level" in ARGS:
    build_level()
