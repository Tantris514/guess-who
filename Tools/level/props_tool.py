"""Props of L_Manor after freeze_dress.py: the level itself is the source of truth, edited by script OR by hand.

Nothing to declare after a manual edit: every command reads the level as it is now.
  python -I -X utf8 Tools\\ui\\ue_run.py Tools\\level\\props_tool.py export
      -> Tools/level/props_layout.json: every prop (label, mesh, room folder, x y z, yaw, scale) to read or plan with
  ... props_tool.py move <label> <x> <y> <z> [yaw]          (z "floor" = keep the current height)
  ... props_tool.py delete <label>
  ... props_tool.py add <prop_name> <x> <y> <z> <yaw> [room] [scale]   (mesh from /Game/GW/Meshes/Props/<prop_name>/)
  ... props_tool.py batch <file.json>   [{"op": "move"|"delete"|"add", ...same fields...}, ...] in one save
Every change is saved; new props go in Outliner folder Decor_Manuel/<room>, tag GW_Manual.
"""
import json
import os
import unreal

ARGS = list(globals().get('UE_ARGS', []))
ROOT = r'J:\Projets\Unreal_Projects\Guess Who'
OUT = os.path.join(ROOT, 'Tools', 'level', 'props_layout.json')
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
EAL = unreal.EditorAssetLibrary


def props():
    return {a.get_actor_label(): a for a in eas.get_all_level_actors()
            if 'GW_Manual' in [str(t) for t in a.tags] and isinstance(a, unreal.StaticMeshActor)}


def export():
    rows = []
    for label, a in sorted(props().items()):
        loc, rot, sc = a.get_actor_location(), a.get_actor_rotation(), a.get_actor_scale3d()
        mesh = a.static_mesh_component.static_mesh
        rows.append(dict(label=label, mesh=mesh.get_name() if mesh else None, room=str(a.get_folder_path()).split('/')[-1],
                         x=round(loc.x, 1), y=round(loc.y, 1), z=round(loc.z, 1), yaw=round(rot.yaw, 1),
                         scale=[round(sc.x, 3), round(sc.y, 3), round(sc.z, 3)]))
    json.dump(rows, open(OUT, 'w', encoding='utf-8'), indent=0, ensure_ascii=False)
    print(f'props_tool: {len(rows)} props -> {OUT}')


def mesh_of(name):
    folder = f'/Game/GW/Meshes/Props/{name}'
    for p in EAL.list_assets(folder, recursive=True):
        o = unreal.load_asset(p)
        if isinstance(o, unreal.StaticMesh):
            return o
    raise RuntimeError(f'no static mesh under {folder}')


def apply(op):
    kind = op['op']
    cur = props()
    if kind == 'move':
        a = cur[op['label']]
        loc = a.get_actor_location()
        z = loc.z if str(op.get('z', 'floor')) == 'floor' else float(op['z'])
        a.set_actor_location(unreal.Vector(float(op['x']), float(op['y']), z), False, True)
        if op.get('yaw') is not None:
            r = a.get_actor_rotation()
            a.set_actor_rotation(unreal.Rotator(roll=r.roll, pitch=r.pitch, yaw=float(op['yaw'])), True)
    elif kind == 'delete':
        eas.destroy_actor(cur[op['label']])
    elif kind == 'add':
        m = mesh_of(op['prop'])
        a = eas.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(float(op['x']), float(op['y']), float(op['z'])),
                                       unreal.Rotator(roll=0, pitch=0, yaw=float(op.get('yaw', 0))))
        smc = a.static_mesh_component
        smc.set_mobility(unreal.ComponentMobility.MOVABLE)
        smc.set_static_mesh(m)
        smc.set_mobility(unreal.ComponentMobility.STATIC)
        s = float(op.get('scale', 1))
        a.set_actor_scale3d(unreal.Vector(s, s, s))
        a.set_actor_label(f"{m.get_name()}_add{len(cur)}")
        a.set_folder_path(f"Decor_Manuel/{op.get('room', 'Ajouts')}")
        a.tags = [unreal.Name('GW_Manual')]
    else:
        raise RuntimeError(f'unknown op {kind}')
    print('props_tool:', kind, op.get('label') or op.get('prop'))


cmd = ARGS[0] if ARGS else 'export'
if cmd == 'export':
    export()
else:
    if cmd == 'batch':
        ops = json.load(open(ARGS[1], encoding='utf-8'))
    elif cmd == 'move':
        ops = [dict(op='move', label=ARGS[1], x=ARGS[2], y=ARGS[3], z=ARGS[4], yaw=ARGS[5] if len(ARGS) > 5 else None)]
    elif cmd == 'delete':
        ops = [dict(op='delete', label=ARGS[1])]
    elif cmd == 'add':
        ops = [dict(op='add', prop=ARGS[1], x=ARGS[2], y=ARGS[3], z=ARGS[4], yaw=ARGS[5],
                    room=ARGS[6] if len(ARGS) > 6 else 'Ajouts', scale=ARGS[7] if len(ARGS) > 7 else 1)]
    else:
        raise RuntimeError(f'unknown command {cmd}')
    for op in ops:
        apply(op)
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    export()
