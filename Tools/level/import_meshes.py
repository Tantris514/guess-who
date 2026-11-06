"""(in editor) Import Tools/level/meshes/*.obj into /Game/GW/Meshes/Arch and make Nanite shape copies.

  python -I -X utf8 Tools/ue_py.py Tools/level/import_meshes.py [only_name ...]
Re-runnable: existing assets are re-imported in place.
"""
import os
import unreal

eal = unreal.EditorAssetLibrary
sms = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "meshes")
DEST = "/Game/GW/Meshes/Arch"
SHAPES = "/Game/GW/Meshes/Shapes"
only = set(globals().get("UE_ARGS", []))
BOX_COLLISION = {"SM_GW_ColumnShaft", "SM_GW_BevelBox"}


def set_nanite(mesh, on=True):
    ns = mesh.get_editor_property("nanite_settings")
    if ns.get_editor_property("enabled") != on:
        ns.set_editor_property("enabled", on)
        mesh.set_editor_property("nanite_settings", ns)
        return True
    return False


def import_objs():
    tasks = []
    for fn in sorted(os.listdir(SRC)):
        if not fn.endswith(".obj"):
            continue
        name = fn[:-4]
        if only and name not in only:
            continue
        t = unreal.AssetImportTask()
        t.filename = os.path.join(SRC, fn)
        t.destination_path = DEST
        t.destination_name = name
        t.automated = True
        t.replace_existing = True
        t.save = False
        tasks.append(t)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks(tasks)
    done = 0
    for t in tasks:
        for p in t.imported_object_paths:
            a = unreal.load_asset(p)
            if isinstance(a, unreal.StaticMesh):
                name = a.get_name()
                sms.remove_collisions(a)
                if name in BOX_COLLISION:
                    sms.add_simple_collisions(a, unreal.ScriptCollisionShapeType.BOX)
                set_nanite(a, True)
                eal.save_loaded_asset(a)
                done += 1
            elif isinstance(a, (unreal.MaterialInterface, unreal.Texture)):
                # OBJ importer may create a default material; we don't want it
                eal.delete_loaded_asset(a)
    print(f"imported {done}/{len(tasks)} meshes into {DEST}")


def make_shapes():
    eal.make_directory(SHAPES)
    pairs = [("/Engine/BasicShapes/Cube", "SM_GW_Cube", True), ("/Engine/BasicShapes/Cylinder", "SM_GW_Cylinder", True),
             ("/Engine/BasicShapes/Plane", "SM_GW_Plane", True), ("/Engine/BasicShapes/Sphere", "SM_GW_Sphere", True),
             ("/Engine/BasicShapes/Cone", "SM_GW_Cone", True), ("/Engine/BasicShapes/Cube", "SM_GW_Cube_NoNanite", False),
             ("/Engine/BasicShapes/Plane", "SM_GW_Plane_NoNanite", False)]
    for src, name, nanite in pairs:
        dst = f"{SHAPES}/{name}"
        if not eal.does_asset_exist(dst):
            eal.duplicate_asset(src, dst)
        m = unreal.load_asset(dst)
        set_nanite(m, nanite)
        eal.save_loaded_asset(m)
    print("shapes ok")


make_shapes()
import_objs()
# leftovers from OBJ material creation
for p in eal.list_assets(DEST, recursive=True):
    a = unreal.load_asset(p)
    if not isinstance(a, unreal.StaticMesh):
        print("removing non-mesh", p)
        eal.delete_asset(p)
