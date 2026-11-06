"""Applies the flame colours of s32_events.py to the three flame instances without a full s32 run."""
import unreal, re
MEL = unreal.MaterialEditingLibrary
s = open(r'J:\Projets\Unreal_Projects\Guess Who\Tools\gameplay\s32_events.py', encoding='utf-8').read()
c, st = re.search(r"MI_FIRE = mi\('MI_GW_EventFire', FLAME, \(([^)]*)\), ([\d.]+)\)", s).groups()
col = unreal.LinearColor(*[float(x) for x in c.split(',')])
for n, k in (('MI_GW_EventFire', float(st)), ('MI_GW_BodyFlame', 7.0), ('MI_GW_WallFlame', 7.0)):
    m = unreal.load_asset('/Game/GW/Materials/' + n)
    MEL.set_material_instance_vector_parameter_value(m, 'Color', col)
    MEL.set_material_instance_scalar_parameter_value(m, 'Strength', k)
    MEL.update_material_instance(m)
    print(n, unreal.EditorAssetLibrary.save_loaded_asset(m, False))
