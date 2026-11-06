"""Builds /Game/GW/Maps/Dev/L_GameplayTest and /Game/GW/Maps/L_MainMenu.

Run OUTSIDE the shared editor (it switches the edited level):
  UnrealEditor-Cmd.exe GuessWho.uproject -run=pythonscript -script=<this file> -nullrhi -unattended -nosplash
"""
import unreal

EAL = unreal.EditorAssetLibrary
les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
CUBE = unreal.load_asset('/Engine/BasicShapes/Cube')
GM = unreal.load_asset('/Game/GW/Blueprints/BP_GW_GameMode').generated_class()
MGM = unreal.load_asset('/Game/GW/Blueprints/BP_GW_MenuGameMode').generated_class()
log = []


def open_or_new(path):
    if EAL.does_asset_exist(path):
        assert les.load_level(path), 'load_level failed ' + path
        for a in eas.get_all_level_actors():
            if not isinstance(a, (unreal.WorldSettings, unreal.Brush)):
                eas.destroy_actor(a)
    else:
        assert les.new_level(path), 'new_level failed ' + path


def box(name, loc, scale, mat=None):
    a = eas.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(*loc))
    a.set_actor_label(name)
    smc = a.get_editor_property('static_mesh_component')
    smc.set_static_mesh(CUBE)
    a.set_actor_scale3d(unreal.Vector(*scale))
    if mat:
        smc.set_material(0, mat)
    return a


def point(cls, name, loc, tag=None, yaw=0.0):
    a = eas.spawn_actor_from_class(cls, unreal.Vector(*loc), unreal.Rotator(0, 0, yaw))
    a.set_actor_label(name)
    if tag:
        a.set_editor_property('tags', [unreal.Name(tag)])
    return a


def build_test():
    open_or_new('/Game/GW/Maps/Dev/L_GameplayTest')
    mat = unreal.load_asset('/Engine/BasicShapes/BasicShapeMaterial')
    box('Floor', (0, 0, -10), (44, 44, 0.2))
    H = 400
    for i, (loc, sc) in enumerate([((0, 2200, H / 2), (44, 0.3, H / 100)), ((0, -2200, H / 2), (44, 0.3, H / 100)),
                                    ((2200, 0, H / 2), (0.3, 44, H / 100)), ((-2200, 0, H / 2), (0.3, 44, H / 100))]):
        box(f'OuterWall{i}', loc, sc)
    # a few rooms / cover walls
    for i, (loc, sc) in enumerate([((-600, 0, 150), (0.3, 14, 3)), ((600, 700, 150), (12, 0.3, 3)), ((900, -900, 150), (0.3, 10, 3)),
                                    ((-1300, 1100, 150), (8, 0.3, 3)), ((-1200, -1300, 100), (3, 3, 2)), ((200, -300, 100), (2, 2, 2))]):
        box(f'Wall{i}', loc, sc)
    # seeker corner (open on one side)
    box('SeekerRoomA', (1850, 1250, 150), (7, 0.3, 3))
    box('SeekerRoomB', (1250, 1700, 150), (0.3, 9, 3))
    # lights (only matter when rendering)
    sun = eas.spawn_actor_from_class(unreal.DirectionalLight, unreal.Vector(0, 0, 1000), unreal.Rotator(0, -50, 30))
    sun.set_actor_label('Sun')
    sky = eas.spawn_actor_from_class(unreal.SkyLight, unreal.Vector(0, 0, 800))
    sky.set_actor_label('SkyLight')
    eas.spawn_actor_from_class(unreal.SkyAtmosphere, unreal.Vector(0, 0, 0))
    # navigation
    nav = eas.spawn_actor_from_class(unreal.NavMeshBoundsVolume, unreal.Vector(0, 0, 150))
    nav.set_actor_label('NavBounds')
    nav.set_actor_scale3d(unreal.Vector(23, 23, 3))
    log.append(f'nav bounds {nav.get_actor_bounds(False)}')
    # spawns
    for i, (x, y) in enumerate([(-300, -1800), (300, -1800), (-900, -1800), (900, -1800)]):
        point(unreal.PlayerStart, f'PlayerStart{i}', (x, y, 100), yaw=90)
    for i, (x, y) in enumerate([(1500, 1900), (1700, 1900), (1900, 1900), (1900, 1600)]):
        point(unreal.TargetPoint, f'SeekerSpawn{i}', (x, y, 10), 'GW_SeekerSpawn', yaw=-135)
    k = 0
    for x in (-1700, -1000, -300, 300, 1000):
        for y in (-1500, -700, 0, 900, 1600):
            if x > 900 and y > 800:
                continue
            point(unreal.TargetPoint, f'NPCSpawn{k}', (x + 40 * (k % 3), y, 10), 'GW_NPCSpawn')
            k += 1
    ws = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world().get_world_settings()
    ws.set_editor_property('default_game_mode', GM)
    les.save_current_level()
    log.append(f'test map saved, npc spawns={k}')


def build_menu():
    open_or_new('/Game/GW/Maps/L_MainMenu')
    cam = eas.spawn_actor_from_class(unreal.CameraActor, unreal.Vector(0, 0, 200))
    cam.set_actor_label('MenuCamera')
    ws = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world().get_world_settings()
    ws.set_editor_property('default_game_mode', MGM)
    les.save_current_level()
    log.append('menu map saved')


try:
    build_test()
    build_menu()
except Exception as e:
    log.append(f'ERROR {e!r}')
with open(r'J:\Projets\Unreal_Projects\Guess Who\Tools\gameplay\out_maps.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(log))
