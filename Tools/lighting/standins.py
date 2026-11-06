"""Readability check: spawn temporary mannequins (label TMP_Standin, never saved) on every GW_NPCSpawn marker,
facing the nearest review camera. Args: add | remove"""
import math
import unreal

eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
mode = (globals().get("UE_ARGS") or ["add"])[0]
old = [a for a in eas.get_all_level_actors() if a.get_actor_label().startswith("TMP_Standin")]
if old:
    eas.destroy_actors(old)
print("removed", len(old))
if mode == "add":
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    mesh = unreal.load_asset("/Game/Characters/Mannequins/Meshes/SKM_Quinn_Simple") or \
        unreal.load_asset("/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple")
    cams = [a for a in eas.get_all_level_actors() if a.actor_has_tag("GW_ReviewCam")]
    marks = [a for a in eas.get_all_level_actors() if a.actor_has_tag("GW_NPCSpawn")]
    n = 0
    for m in marks:
        p = m.get_actor_location()
        hit = unreal.SystemLibrary.line_trace_single(world, p, unreal.Vector(p.x, p.y, p.z - 400),
                                                     unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, False, [], 
                                                     unreal.DrawDebugTrace.NONE, True)
        z = p.z - 92
        if hit:
            t = hit.to_tuple()
            if t[0]:
                z = t[4].z if hasattr(t[4], "z") else z
        c = min(cams, key=lambda c: (c.get_actor_location() - p).length())
        cl = c.get_actor_location()
        yaw = math.degrees(math.atan2(cl.y - p.y, cl.x - p.x)) - 90.0   # mannequin faces +Y
        a = eas.spawn_actor_from_class(unreal.SkeletalMeshActor, unreal.Vector(p.x, p.y, z), unreal.Rotator(0, 0, yaw))
        a.set_actor_label(f"TMP_Standin_{n}")
        comp = a.get_component_by_class(unreal.SkeletalMeshComponent)
        comp.set_skinned_asset_and_update(mesh) if hasattr(comp, "set_skinned_asset_and_update") else \
            comp.set_editor_property("skeletal_mesh", mesh)
        n += 1
    print("standins", n, "mesh", mesh.get_name() if mesh else None)
