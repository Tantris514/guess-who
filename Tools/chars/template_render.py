"""Reference-pose renders of the UE mannequins, the templates the generated characters are drawn over.

Editor (with rendering): ue_run.py template_render.py. In a scratch level /Game/GW/Dev/L_CharTemplate, Manny and Quinn
stand in their reference A-pose; an orthographic scene capture (show-only list, black background, three directional
lights, manual exposure) shoots front, back and side at 1024x1536. Pixel <-> cm mapping is written to
AssetGen/chars/templates/templates.json (ortho width, image centre in component space) so the generated images and
meshes can be checked against the mannequin silhouette.
"""
import json
import os
import unreal

OUT = r'J:\Projets\Unreal_Projects\Guess Who\AssetGen\chars\templates'
LEVEL = '/Game/GW/Dev/L_CharTemplate'
W, H, ORTHO_W, CZ = 1024, 1536, 140.0, 100.0          # 140 cm across -> 210 cm tall, centred 100 cm above the floor
BODIES = {'manny': '/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple',
          'quinn': '/Game/Characters/Mannequins/Meshes/SKM_Quinn_Simple'}
VIEWS = {'front': unreal.Vector(0, 600, CZ), 'back': unreal.Vector(0, -600, CZ), 'side': unreal.Vector(600, 0, CZ)}

les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
if unreal.EditorAssetLibrary.does_asset_exist(LEVEL):
    les.load_level(LEVEL)
else:
    les.new_level(LEVEL)
for a in eas.get_all_level_actors():
    if a.get_actor_label().startswith('GWT_'):
        eas.destroy_actor(a)
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()


def light(label, pitch, yaw, lux):
    l = eas.spawn_actor_from_class(unreal.DirectionalLight, unreal.Vector(0, 0, 400), unreal.Rotator(roll=0, pitch=pitch, yaw=yaw))
    l.set_actor_label(label)
    c = l.get_component_by_class(unreal.DirectionalLightComponent)
    c.set_editor_property('intensity', lux)
    c.set_editor_property('light_color', unreal.Color(r=255, g=244, b=232, a=255))
    return l


lights = [light('GWT_Key', -35, -125, 6.0), light('GWT_Fill', -15, -45, 2.5), light('GWT_Rim', -30, 80, 3.0)]
rt = unreal.RenderingLibrary.create_render_target2d(world, W, H, unreal.TextureRenderTargetFormat.RTF_RGBA8)
cap = eas.spawn_actor_from_class(unreal.SceneCapture2D, unreal.Vector(0, 600, CZ))
cap.set_actor_label('GWT_Capture')
cc = cap.capture_component2d
cc.set_editor_property('projection_type', unreal.CameraProjectionMode.ORTHOGRAPHIC)
cc.set_editor_property('ortho_width', ORTHO_W)
cc.set_editor_property('texture_target', rt)
cc.set_editor_property('capture_source', unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
cc.set_editor_property('capture_every_frame', False)
cc.set_editor_property('primitive_render_mode', unreal.SceneCapturePrimitiveRenderMode.PRM_USE_SHOW_ONLY_LIST)
pp = cc.get_editor_property('post_process_settings')
pp.set_editor_property('override_auto_exposure_method', True)
pp.set_editor_property('auto_exposure_method', unreal.AutoExposureMethod.AEM_MANUAL)
pp.set_editor_property('override_auto_exposure_apply_physical_camera_exposure', True)
pp.set_editor_property('auto_exposure_apply_physical_camera_exposure', False)
pp.set_editor_property('override_auto_exposure_bias', True)
pp.set_editor_property('auto_exposure_bias', 0.0)
cc.set_editor_property('post_process_settings', pp)
cc.set_editor_property('post_process_blend_weight', 1.0)

meta = {'width': W, 'height': H, 'ortho_width_cm': ORTHO_W, 'centre_z_cm': CZ, 'cm_per_px': ORTHO_W / W,
        'note': 'front camera on +Y looking -Y (mannequin faces +Y); image x grows toward the mannequin\'s left', 'files': []}
os.makedirs(OUT, exist_ok=True)
for name, path in BODIES.items():
    act = eas.spawn_actor_from_class(unreal.SkeletalMeshActor, unreal.Vector(0, 0, 0), unreal.Rotator(0, 0, 0))
    act.set_actor_label('GWT_' + name)
    act.skeletal_mesh_component.set_skinned_asset_and_update(unreal.load_asset(path))
    cc.clear_show_only_components()
    cc.show_only_actor_components(act, False)
    for view, pos in VIEWS.items():
        cap.set_actor_location_and_rotation(pos, unreal.MathLibrary.find_look_at_rotation(pos, unreal.Vector(0, 0, CZ)), False, True)
        cc.capture_scene()
        fn = f'{name}_{view}.png'
        unreal.RenderingLibrary.export_render_target(world, rt, OUT, fn)
        meta['files'].append(fn)
        print('wrote', os.path.join(OUT, fn))
    eas.destroy_actor(act)
json.dump(meta, open(os.path.join(OUT, 'templates.json'), 'w'), indent=1)
les.save_current_level()
