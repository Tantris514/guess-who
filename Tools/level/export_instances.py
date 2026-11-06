"""(in editor) Dump every GW_Gen ISM instance (mesh, material, world AABB, transform) + actors to JSON.

Output: Tools/level/instances.json  (used by validate_offline.py and plot_level.py)
"""
import json
import os

import unreal

OUT = r"J:\Projets\Unreal_Projects\Guess Who\Tools\level\instances.json"
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
inst, actors = [], []
bounds_cache = {}
for a in eas.get_all_level_actors():
    tags = [str(t) for t in a.tags]
    loc = a.get_actor_location()
    actors.append(dict(cls=a.get_class().get_name(), label=a.get_actor_label(), tags=tags,
                       loc=[loc.x, loc.y, loc.z], rot=[a.get_actor_rotation().pitch, a.get_actor_rotation().yaw,
                                                       a.get_actor_rotation().roll]))
    if "GW_Gen" not in tags:
        continue
    for c in a.get_components_by_class(unreal.InstancedStaticMeshComponent):
        m = c.get_editor_property("static_mesh")
        if m is None:
            continue
        mn = m.get_name()
        if mn not in bounds_cache:
            bb = m.get_bounding_box()
            bounds_cache[mn] = (bb.min, bb.max)
        lo, hi = bounds_cache[mn]
        mats = c.get_materials()
        matn = mats[0].get_name() if mats and mats[0] else ""
        coll = str(c.get_collision_profile_name())
        vis = bool(c.is_visible())
        for i in range(c.get_instance_count()):
            t = c.get_instance_transform(i, True)
            pts = []
            for x in (lo.x, hi.x):
                for y in (lo.y, hi.y):
                    for z in (lo.z, hi.z):
                        p = t.transform_location(unreal.Vector(x, y, z))
                        pts.append((p.x, p.y, p.z))
            mn3 = [min(p[k] for p in pts) for k in range(3)]
            mx3 = [max(p[k] for p in pts) for k in range(3)]
            r = t.rotation.rotator()
            inst.append(dict(a=a.get_actor_label(), m=mn, mat=matn, c=coll, v=vis, lo=mn3, hi=mx3,
                             t=[t.translation.x, t.translation.y, t.translation.z],
                             r=[r.pitch, r.yaw, r.roll], s=[t.scale3d.x, t.scale3d.y, t.scale3d.z]))
with open(OUT, "w", encoding="utf-8") as fh:
    json.dump(dict(instances=inst, actors=actors), fh)
print(f"exported {len(inst)} instances, {len(actors)} actors")
