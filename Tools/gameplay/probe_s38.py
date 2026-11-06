"""Read-only probe for s38_pickups.py: node type ids, pin names, assets, felt height. Prints only."""
import sys, importlib
sys.path.insert(0, r'J:\Projets\Unreal_Projects\Guess Who\Tools\gameplay')
import gw_lib; importlib.reload(gw_lib)
from gw_lib import *

pc = load_bp('BP_GW_PlayerController')
for q in ['EventHit', 'SetViewTargetwithBlend', 'PlayAnimMontage', 'StopAnimMontage', 'AttachActorToComponent',
          'SphereTraceByProfile', 'SphereTraceByChannel', 'GetPlayerController', 'GetViewTarget', 'SetRelativeRotation',
          'CombineRotators', 'MakeArray', 'Possess', 'StopMovementImmediately', 'GetPlayerCameraManager',
          'GetRightVector', 'MakeRotFromZX', 'GetComponentVelocity', 'SetActorRotation', 'FInterpEaseInOut', 'Ease',
          'ClientSetRotation', 'SetActorRelativeTransform', 'SetLifeSpan', 'MakeRotFromX', 'sin(degrees)', 'SetActorLocationAndRotation', 'SetActorHiddenInGame', 'StopMovement']:
    try:
        r = find_types(pc, q, limit=8)
        print('##', q, '->', r)
    except Exception as e:
        print('##', q, 'ERR', e)
for t in ['Animation|PlayAnimMontage']:
    try:
        print(t, pins(pc, t))
    except Exception as e:
        print(t, 'ERR', e)
ch = load_bp('BP_GW_Character')
c = cdo(ch)
m = c.get_editor_property('mesh')
print('anim class', m.get_editor_property('anim_class'), 'mode', m.get_editor_property('animation_mode'))
print('mesh', m.get_editor_property('skeletal_mesh_asset') if hasattr(m, 'get_editor_property') else None)
print('GunRel', c.get_editor_property('GunRel'))
ps = load_bp('BP_GW_PlayerState')
print('PS vars', [str(v) for v in BT.list_variables(ps)])
print('PC fns', [g for g in graph_names(pc) if any(k in g for k in ('Try', 'Guest', 'Client', 'Interact', 'Shop'))])
imc = unreal.load_asset('/Game/GW/Input/IMC_GW')
print('IMC_GW', [(m.get_editor_property('action').get_name(), str(m.get_editor_property('key').get_editor_property('key_name'))) for m in imc.get_editor_property('default_key_mappings').get_editor_property('mappings')])
for p in ['/Game/GW/Materials/MI_GW_Chrome', '/Game/GW/Materials/MI_GW_Brass', '/Game/GW/Materials/MI_GW_Iron',
          '/Game/GW/Materials/MI_GW_Leather_Brown', '/Game/GW/Materials/MI_GW_Porcelain', '/Game/GW/Materials/MI_GW_Velvet_Red']:
    print(p, EAL.does_asset_exist(p))
ar = unreal.AssetRegistryHelpers.get_asset_registry()
mats = [str(d.asset_name) for d in ar.get_assets_by_path('/Game/GW/Materials', recursive=False)]
print('materials', [n for n in mats if any(k in n for k in ('Chrome', 'Brass', 'Iron', 'Steel', 'Leather', 'Porcelain', 'Velvet', 'Lacquer', 'Gold', 'Felt', 'Book', 'Emissive', 'Ghost'))])
print('masters', [str(d.asset_name) for d in ar.get_assets_by_path('/Game/GW/Materials/Master', recursive=False)])
# felt height and armour in the editor world
w = unreal.EditorLevelLibrary.get_editor_world()
for (x, y) in [(5000, 900), (4945, 880), (5070, 905), (4930, 930)]:
    for cx in (False, True):
        h = unreal.SystemLibrary.line_trace_single(w, unreal.Vector(x, y, 250), unreal.Vector(x, y, -50), unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, cx, [], unreal.DrawDebugTrace.NONE, True)
        if h:
            t = h.to_tuple()
            print('trace', x, y, 'complex' if cx else 'simple', 'z', round(t[4].z, 2), t[9].get_name() if t[9] else None)
for (x, y) in [(2620, 2300), (3380, 2300), (2620, 2353)]:
    h = unreal.SystemLibrary.line_trace_single(w, unreal.Vector(x, y, 250), unreal.Vector(x, y, -50), unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, True, [], unreal.DrawDebugTrace.NONE, True)
    if h:
        t = h.to_tuple()
        print('armour trace', x, y, 'z', round(t[4].z, 2), t[9].get_name() if t[9] else None)
acts = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
for a in acts:
    n = a.get_actor_label()
    if 'armor' in n.lower() or 'billiard_table' in n.lower():
        o, e = a.get_actor_bounds(False)
        print('actor', n, 'loc', a.get_actor_location(), 'rot', a.get_actor_rotation(), 'bounds', o, e, 'tags', [str(t) for t in a.tags])
