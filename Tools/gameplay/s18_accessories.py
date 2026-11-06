"""Import placeholder accessories and fit them on BP_GW_Character (hat/mask on 'head', revolver on 'weapon_r')."""
import sys, importlib, os
sys.path.insert(0, r'J:\Projets\Unreal_Projects\Guess Who\Tools\gameplay')
import gw_lib; importlib.reload(gw_lib)
from gw_lib import *
D = '/Game/GW/Characters/Accessories'
src = r'J:\Projets\Unreal_Projects\Guess Who\Tools\gameplay\meshes'
tasks = []
for fn in sorted(os.listdir(src)):
    if fn.endswith('.obj'):
        t = unreal.AssetImportTask()
        t.filename = os.path.join(src, fn); t.destination_path = D; t.automated = True; t.replace_existing = True; t.save = True
        tasks.append(t)
unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks(tasks)
meshes = {}
for t in tasks:
    for p in t.get_editor_property('imported_object_paths'):
        a = unreal.load_asset(p)
        if isinstance(a, unreal.StaticMesh):
            meshes[a.get_name()] = a
            b = a.get_bounding_box()
            print(a.get_name(), 'min', [round(v,1) for v in (b.min.x, b.min.y, b.min.z)], 'max', [round(v,1) for v in (b.max.x, b.max.y, b.max.z)])
            # no collision needed on accessories
            unreal.EditorStaticMeshLibrary.remove_collisions(a) if hasattr(unreal.EditorStaticMeshLibrary, 'remove_collisions') else None
            EAL.save_loaded_asset(a, False)
print(sorted(meshes))
