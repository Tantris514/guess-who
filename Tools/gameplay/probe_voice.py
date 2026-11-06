"""Read-only probe for s39_voice_director.py: node types, collision responses to the Camera channel, attenuation state."""
import sys, importlib
sys.path.insert(0, r'J:\Projets\Unreal_Projects\Guess Who\Tools\gameplay')
import gw_lib; importlib.reload(gw_lib)
from gw_lib import *

gm = load_bp('BP_GW_GameMode')
for f in ('Resize', 'SetArrayElem', 'FadeOut', 'GetCameraLocation', 'GetPlayerCameraManager', 'LineTraceByChannel',
          'IsValidIndex', 'LastIndex', 'RandomBoolwithWeight', 'GetForwardVector', 'FInterp', 'HasLaunchOption',
          'GetTimeSeconds', 'SetControlRotation', 'Conv_IntToFloat', 'Float|Max', 'Integer|Max', 'Truncate'):
    try:
        r = find_types(gm, f, limit=12)
        print('##', f, '->', [str(x) for x in r][:12])
    except Exception as e:
        print('##', f, 'ERR', e)
for tid in ('Collision|LineTraceByChannel', 'Utilities|Array|Resize'):
    try:
        print(tid, pins(gm, tid))
    except Exception as e:
        print(tid, 'ERR', e)

# collision: who blocks the Camera channel
chd = unreal.get_default_object(load_bp('BP_GW_Character').generated_class())
for c in chd.get_components_by_class(unreal.PrimitiveComponent):
    try:
        print('char comp', c.get_name(), c.get_collision_profile_name(),
              'camera:', c.get_collision_response_to_channel(unreal.CollisionChannel.ECC_CAMERA),
              'visibility:', c.get_collision_response_to_channel(unreal.CollisionChannel.ECC_VISIBILITY),
              'enabled:', c.get_collision_enabled())
    except Exception as e:
        print('char comp', c.get_name(), 'ERR', e)
w = unreal.EditorLevelLibrary.get_editor_world()
print('world', w.get_name() if w else None)
acts = unreal.EditorLevelLibrary.get_all_level_actors()
n = 0
seen = {}
for a in acts:
    if isinstance(a, unreal.StaticMeshActor):
        nm = a.get_actor_label()
        if 'wall' in nm.lower() or 'mur' in nm.lower():
            c = a.static_mesh_component
            key = (c.get_collision_profile_name(), str(c.get_collision_response_to_channel(unreal.CollisionChannel.ECC_CAMERA)), str(c.get_collision_enabled()))
            seen.setdefault(key, []).append(nm)
for k, v in seen.items():
    print('walls', k, len(v), v[:4])
for name in ('ATT_GW_Voice', 'ATT_GW_Far'):
    a = unreal.load_asset(f'/Game/GW/Audio/{name}')
    s = a.get_editor_property('attenuation')
    print(name, 'occl', s.get_editor_property('enable_occlusion'), s.get_editor_property('occlusion_trace_channel'),
          s.get_editor_property('occlusion_volume_attenuation'), 'inner', s.get_editor_property('attenuation_shape_extents'),
          'falloff', s.get_editor_property('falloff_distance'))
