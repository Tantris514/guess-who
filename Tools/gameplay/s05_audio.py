import unreal, glob, os
src = UE_ARGS[0]
tasks = []
for f in glob.glob(os.path.join(src, '*.wav')):
    t = unreal.AssetImportTask()
    t.filename = f; t.destination_path = '/Game/GW/Audio'; t.automated = True; t.replace_existing = True; t.save = True
    tasks.append(t)
unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks(tasks)
for t in tasks:
    print(t.get_editor_property('imported_object_paths'))
