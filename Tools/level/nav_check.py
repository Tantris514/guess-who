"""(in editor) Configure RecastNavMesh (dynamic runtime generation) and validate paths between rooms.

  level/run.sh level/nav_check.py [configure]
Prints nav build state, path results room->room and NPC spawn projection results; writes level/nav_report.json.
"""
import json
import math
import os
import sys

import unreal

sys.path.insert(0, r"J:\Projets\Unreal_Projects\Guess Who\Tools\level")
import dress  # noqa: E402

eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
nav = unreal.NavigationSystemV1.get_navigation_system(world)
args = globals().get("UE_ARGS", [])
if "configure" in args:
    navs = dress.configure_recast()
    if navs:
        unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
        print("saved")
print("building:", unreal.NavigationSystemV1.is_navigation_being_built(world))
recast = [a for a in eas.get_all_level_actors() if isinstance(a, unreal.RecastNavMesh)]
print("recast actors:", [(r.get_name(), str(r.get_editor_property("runtime_generation"))) for r in recast])

POINTS = {"hall": (3000, 700, 50), "hall_north": (3000, 2200, 50), "gallery": (3000, 2200, 550),
          "gallery_w_stairtop": (2150, 2100, 550), "dining": (1500, 400, 50), "corridor_w": (700, 2100, 50), "wc": (230, 2130, 50),
          "library": (1000, 2900, 50), "ballroom": (3000, 3300, 50), "stage": (3000, 4100, 110),
          "billiard": (4500, 400, 50), "corridor_e": (5700, 2100, 50), "study": (5000, 2800, 50),
          "conservatory": (4700, 4000, 50), "cloakroom": (3000, 250, 50)}
res = {}
ext = unreal.Vector(80, 80, 250)
proj = {}
for k, p in POINTS.items():
    pt = unreal.NavigationSystemV1.project_point_to_navigation(world, unreal.Vector(*p), None, None, ext)
    proj[k] = pt
    res[k] = {"projected": None if pt is None else [round(pt.x), round(pt.y), round(pt.z)]}
ok = 0
paths = {}
for k, p in proj.items():
    if k == "cloakroom" or p is None:
        continue
    src = proj["cloakroom"]
    if src is None:
        break
    path = unreal.NavigationSystemV1.find_path_to_location_synchronously(world, src, p)
    if path is None:
        paths[k] = "none"
        continue
    pts = path.get_editor_property("path_points")
    good = path.is_valid() and not path.is_partial()
    paths[k] = dict(valid=good, length=round(path.get_path_length()), points=len(pts))
    ok += good
print("projections:", {k: v["projected"] for k, v in res.items()})
print("paths from cloakroom:", json.dumps(paths))
print(f"reachable: {ok}/{len(paths)}")
# NPC spawns + player starts on navmesh
bad = []
n = 0
for a in eas.get_all_level_actors():
    tags = [str(t) for t in a.tags]
    if "GW_NPCSpawn" in tags or "GW_SeekerSpawn" in tags or "GW_Piano" in tags or any(t.startswith(("GW_Instrument", "GW_Toilet", "GW_Junkie")) for t in tags) or             isinstance(a, unreal.PlayerStart):
        n += 1
        l = a.get_actor_location()
        pt = unreal.NavigationSystemV1.project_point_to_navigation(world, l, None, None, unreal.Vector(30, 30, 150))
        if pt is None:
            bad.append(a.get_actor_label())
        else:
            p2 = unreal.NavigationSystemV1.find_path_to_location_synchronously(world, proj["hall"], pt)
            if p2 is None or not p2.is_valid() or p2.is_partial():
                bad.append(a.get_actor_label() + "(unreachable)")
print(f"markers checked {n}, off-navmesh/unreachable: {bad}")
json.dump(dict(paths=paths, projections=res, bad_markers=bad),
          open(r"J:\Projets\Unreal_Projects\Guess Who\Tools\level\nav_report.json", "w"), indent=1)
