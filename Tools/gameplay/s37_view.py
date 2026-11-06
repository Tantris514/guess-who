"""The view (user decision, 2026-11-03): THIRD person by default, first person only while aiming a gun (right click) or after
the toggle key (C, s40_inventory.py -> SetViewMode). Aim down sights, recoil, head bob, the first-person gun and hands.
The text below still names first person "default" in places: the rig is the same, only WantFP's default changed.

How it works (one camera, the character's own FollowCamera, so the shot ray stays exact without touching GWFire):
- The CameraBoom is moved to the eyes: pivot (0, 0, EYE_Z) above the capsule centre, arm length 0, no socket offset.
  It is done on the owning client every frame (BP_GW_ViewDriver) and on the server for every player pawn
  (BP_GW_Character.ApplyView, from BP_GW_GameMode.ViewServerTick <- TurretTick, 0.25 s), so the server's FollowCamera
  -- where s13 GWFire starts the shot -- is the same eye point the player looks from.
- Third person is a blend of the same boom toward ApplyLook's over-the-shoulder values (s26): while dancing
  (BP_GW_Character.DanceId != 0, social agent), with the dev option "Vue : 3e personne" (local, synced to the server
  through ServerExec GWView so the server places the shot ray at the same camera), and back. The turret (s35) moves
  the camera to the gun's sight through BP_GW_PlayerController.TurretFrame.
- The own body (mesh + everything attached to it: costume pieces, the third-person gun, the burning flames BurnFlame0-2)
  is OwnerNoSee while the view is first person; CameraFadeTick (s23) also hides it when the camera is at the head.
- Body rotation (user, 2026-11-02): a player's body NEVER turns with the mouse, in first or third person: it faces its
  movement like the NPCs (OrientRotationToMovement, no controller yaw). While aiming down sights it faces the aim
  (BP_GW_Character.Aiming, replicated, ServerExec GWAim).
- BP_GW_ViewDriver: a local ticking actor (not replicated) spawned by ViewClientTick; every frame it blends the boom,
  sets the FOV (GWSettings FOV, +7 sprinting, 55 aiming down sights, the turret's 0.85x), head bob (walk / sprint),
  recoil (control-rotation kick on a predicted shot: left click, armed, hunt, revolver cooldown) and a short camera
  shake, ADS mouse sensitivity (x0.5), the first-person gun (only the owner sees it; the mesh of BP_GW_Character.GunMesh,
  so a bought guest gun shows too; poses from the FPGun* tables computed here from each mesh's shape) with sway, kick
  and its muzzle flash, small flames at the bottom of the view while burning, the flashlight brought to the eyes.
- Dev menu (u15, Affichage): "Vue" 1re personne / 3e personne -> BP_GW_PlayerController.SetViewMode (local).
Usage: ue_run.py s37_view.py  (after s32/s33; the turret body of TurretFrame comes from s35_turret.py)
"""
import sys, importlib, math
sys.path.insert(0, r'J:\Projets\Unreal_Projects\Guess Who\Tools\gameplay')
import gw_lib; importlib.reload(gw_lib)
from gw_lib import *

REP = unreal.BlueprintVariableReplication
V3 = unreal.Vector.static_struct()
TR = unreal.Transform.static_struct()
RT = unreal.Rotator.static_struct()
ISVALID = 'GW|Call|/Script/Engine.KismetSystemLibrary|IsValid'
GSC = '(Utilities|Casting|CastToBP_GW_GameState (Game|GetGameState))'
MYCH = '(Utilities|Casting|CastToBP_GW_Character (Pawn|GetControlledPawn :self self))'
SET = '/Game/GW/UI/BP_GW_Settings.BP_GW_Settings_C'
FOLDER = '/Game/GW/Blueprints/Turret'
DRV_CLS = f'{FOLDER}/BP_GW_ViewDriver.BP_GW_ViewDriver_C'
EYE_Z = 66.0            # camera height above the capsule centre (capsule half height 96 -> ~1.62 m eyes)
EYE_FWD = 10.0          # camera this far ahead of the head centre, along the view
TP_SEEK = ((0.0, 48.0, 66.0), 230.0, (0.0, 18.0, 8.0))      # s26 ApplyLook over-the-shoulder values (detective)
TP_GUEST = ((0.0, 0.0, 8.5), 330.0, (0.0, 40.0, 52.0))      # (guest)
ADS_FOV = 55.0
ADS_SENS = 0.5
FX = {}
GUN_HIP, GUN_ADS = (34.0, 13.0, -11.0), (30.0, 0.0, -4.2)      # the middle of the barrel in camera space
RIFLE_HIP, RIFLE_ADS, RIFLE_LEN = (64.0, 17.0, -17.0), (62.0, 0.0, -5.4), 100.0


def mv(v):
    return f'(Math|Vector|MakeVector {float(v[0])} {float(v[1])} {float(v[2])})'


ERRORS = []


def wr(bp, name, code):
    """Rewrite one of OUR graphs from scratch (stale nodes wired to the entry pins otherwise survive a rewrite)."""
    g = get_graph(bp, name)
    for node in list(BT.find_nodes(g)):
        if node.get_class().get_name() in ('K2Node_FunctionEntry', 'K2Node_FunctionResult'):
            for p in node.list_all_pins():
                for c in list(p.list_connected_pins()):
                    p.break_single_pin_link(c)
            continue
        BT.delete_node(node)
    try:
        write(bp, name, code, compile_after=False)
    except Exception as e:                            # keep going: every broken graph is reported in one run
        ERRORS.append(f'{bp.get_name()}.{name}: {str(e)[:300]}')


def lock(asset, on):
    import time
    with open(r'J:\Projets\Unreal_Projects\Guess Who\Tools\agent_logs\locks.md', 'a', encoding='utf-8') as fh:
        fh.write(f"{'LOCK' if on else 'UNLOCK'} {asset} camera-combat {time.strftime('%H:%M')}\n")


# ---------------------------------------------------------------- first-person gun poses (from each mesh's shape)
def gun_pose(mesh):
    """Hip and ADS transforms of a gun mesh attached to the camera (X forward, Y right, Z up), and its muzzle point.

    The longest bounding-box axis is the barrel; the muzzle is the thin end (smaller cross-section); the grip hangs on
    the side of the second axis that reaches furthest from the barrel line. Scaled so the gun is ~26 cm long."""
    try:
        sec = unreal.ProceduralMeshLibrary.get_section_from_static_mesh(mesh, 0, 0)
        pts = [(p.x, p.y, p.z) for p in sec[0]]
    except Exception as e:
        print('gun_pose: no vertices for', mesh.get_name(), e)
        pts = []
    if len(pts) < 8:
        b = mesh.get_bounding_box()
        pts = [(b.min.x, b.min.y, b.min.z), (b.max.x, b.max.y, b.max.z)]
    lo = [min(p[i] for p in pts) for i in range(3)]
    hi = [max(p[i] for p in pts) for i in range(3)]
    ext = [hi[i] - lo[i] for i in range(3)]
    ax = sorted(range(3), key=lambda i: -ext[i])
    a0, a1, a2 = ax                                  # barrel, grip, thickness axes
    mid0 = (lo[a0] + hi[a0]) / 2

    def spread(side):
        sel = [p for p in pts if (p[a0] - mid0) * side > ext[a0] * 0.2]
        if not sel:
            return 0.0
        return max(p[a1] for p in sel) - min(p[a1] for p in sel)
    fwd_sign = 1 if spread(1) <= spread(-1) else -1          # the muzzle end is the thinner one
    front = [p for p in pts if (p[a0] - mid0) * fwd_sign > ext[a0] * 0.3] or pts
    barrel_line = sum(p[a1] for p in front) / len(front)
    down_sign = 1 if (hi[a1] - barrel_line) > (barrel_line - lo[a1]) else -1   # the grip reaches further
    # mesh axes -> camera axes: barrel -> +X, grip -> -Z, the third axis -> Y (a proper rotation: right = up x fwd)
    fwd = [0.0, 0.0, 0.0]; fwd[a0] = float(fwd_sign)
    up = [0.0, 0.0, 0.0]; up[a1] = float(-down_sign)
    right = [up[1] * fwd[2] - up[2] * fwd[1], up[2] * fwd[0] - up[0] * fwd[2], up[0] * fwd[1] - up[1] * fwd[0]]

    def to_cam(v):                                    # mesh-local vector -> camera space (rows fwd, right, up)
        return [sum(r[i] * v[i] for i in range(3)) for r in (fwd, right, up)]
    cols = [to_cam([1, 0, 0]), to_cam([0, 1, 0]), to_cam([0, 0, 1])]     # images of the mesh axes
    rot = unreal.MathLibrary.make_rotation_from_axes(unreal.Vector(*cols[0]), unreal.Vector(*cols[1]), unreal.Vector(*cols[2]))
    is_rifle = 'rifle' in mesh.get_name().lower()
    scale = (RIFLE_LEN if is_rifle else 23.0) / max(ext[a0], 1.0)    # 23 cm: 26 filled too much of the view (gun2 shots)
    c_bl = [(lo[i] + hi[i]) / 2 for i in range(3)]
    c_bl[a1] = barrel_line                            # the gun's middle, on the barrel line
    rc = [x * scale for x in to_cam(c_bl)]
    hip_barrel = RIFLE_HIP if is_rifle else GUN_HIP
    ads_barrel = RIFLE_ADS if is_rifle else GUN_ADS
    sc = unreal.Vector(scale, scale, scale)
    hip = unreal.Transform(location=unreal.Vector(*[hip_barrel[i] - rc[i] for i in range(3)]), rotation=rot, scale=sc)
    ads = unreal.Transform(location=unreal.Vector(*[ads_barrel[i] - rc[i] for i in range(3)]), rotation=rot, scale=sc)
    muz = list(c_bl)
    muz[a0] = (hi[a0] if fwd_sign > 0 else lo[a0]) + fwd_sign * 2.0 / scale
    muz_v = unreal.Vector(*muz)
    print(f'gun_pose {mesh.get_name()}: ext={[round(e, 1) for e in ext]} barrel axis {a0} sign {fwd_sign}, grip axis {a1} '
          f'down {down_sign}, rot {rot}, scale {scale:.3f}')
    return hip, ads, muz_v


ch = load_bp('BP_GW_Character')
chc = ch.generated_class()
pcb = load_bp('BP_GW_PlayerController')
gm = load_bp('BP_GW_GameMode')
HAS_DANCE = 'DanceId' in [str(v) for v in BT.list_variables(ch)]
DANCE = '(!= (GW|Get|BP_GW_Character|DanceId :self C) 0)' if HAS_DANCE else '(== 0 1)'
DANCE_SELF = '(!= (Variables|GW|GetDanceId) 0)' if HAS_DANCE else '(== 0 1)'
print('DanceId present:', HAS_DANCE)

# ---------------------------------------------------------------- character
lock('/Game/GW/Blueprints/BP_GW_Character', True)
fg = ensure_component(ch, 'FPGun', unreal.StaticMeshComponent, 'FollowCamera')
fg.set_editor_property('only_owner_see', True)
fg.set_editor_property('cast_shadow', False)
fg.set_editor_property('visible', False)
fg.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
fg.set_editor_property('generate_overlap_events', False)
fg.set_editor_property('relative_location', unreal.Vector(34, 13, -11))
try:            # the revolver is a Nanite mesh: use its plain fallback here (owner-only visibility, no Nanite surprises)
    fg.set_editor_property('force_disable_nanite', True)
except Exception as e:
    print('FPGun: no force_disable_nanite', e)
blast = unreal.load_asset('/Game/GW/Materials/MI_GW_Blast')
ff = ensure_component(ch, 'FPFlash', unreal.StaticMeshComponent, 'FPGun')
ff.set_editor_property('static_mesh', unreal.load_asset('/Engine/BasicShapes/Sphere'))
ff.set_editor_property('override_materials', [blast])
ff.set_editor_property('only_owner_see', True)
ff.set_editor_property('cast_shadow', False)
ff.set_editor_property('visible', False)
ff.set_editor_property('absolute_scale', True)
ff.set_editor_property('relative_scale3d', unreal.Vector(0.09, 0.05, 0.05))
ff.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
flame_mi = unreal.load_asset('/Game/GW/Materials/MI_GW_BodyFlame')
# a flame plane facing the camera, its height (plane Y, as on BurnFlame0-2) going up the screen
flame_rot = unreal.MathLibrary.make_rotation_from_axes(unreal.Vector(0, -1, 0), unreal.Vector(0, 0, 1), unreal.Vector(-1, 0, 0))
for i, (y, z) in enumerate(((-30.0, -34.0), (31.0, -36.0))):
    fl = ensure_component(ch, f'FPFlame{i}', unreal.StaticMeshComponent, 'FollowCamera')
    fl.set_editor_property('static_mesh', unreal.load_asset('/Engine/BasicShapes/Plane'))
    fl.set_editor_property('override_materials', [flame_mi])
    fl.set_editor_property('only_owner_see', True)
    fl.set_editor_property('cast_shadow', False)
    fl.set_editor_property('visible', False)
    fl.set_editor_property('relative_location', unreal.Vector(48.0, y, z))
    fl.set_editor_property('relative_rotation', flame_rot)
    fl.set_editor_property('relative_scale3d', unreal.Vector(0.16, 0.32, 1.0))
    fl.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
_rifle = unreal.load_asset('/Game/GW/Blueprints/Shop/SM_GW_Rifle') if EAL.does_asset_exist('/Game/GW/Blueprints/Shop/SM_GW_Rifle') else None
ensure_var(ch, 'RifleMesh', obj_class=unreal.StaticMesh, category='View')
ensure_var(ch, 'HeldItem', 'int', rep=REP.REPLICATED, category='Inv')     # the selected inventory item (s40), 0 = empty hands
_glove = '/Game/GW/Materials/MI_GW_Leather_Glove'
if not EAL.does_asset_exist(_glove):
    _leather = unreal.AssetToolsHelpers.get_asset_tools().create_asset('MI_GW_Leather_Glove', '/Game/GW/Materials', unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    _leather.set_editor_property('parent', unreal.load_asset('/Game/GW/Materials/MI_GW_Leather_Oxblood').get_editor_property('parent'))
    unreal.MaterialEditingLibrary.set_material_instance_vector_parameter_value(_leather, 'Tint', unreal.LinearColor(0.035, 0.024, 0.018, 1))
    for _k, _v in (('TileSize', 60.0), ('RoughMin', 0.42), ('RoughMax', 0.42), ('Specular', 0.5), ('Metallic', 0.0), ('NormalStrength', 0.0), ('TileHeight', 0.0)):
        unreal.MaterialEditingLibrary.set_material_instance_scalar_parameter_value(_leather, _k, _v)
    unreal.MaterialEditingLibrary.update_material_instance(_leather)
    EAL.save_loaded_asset(_leather, False)
_leather = unreal.load_asset(_glove)
_cloth = unreal.load_asset('/Game/GW/Materials/MI_GW_Lacquer_Black')
for _n, _a, _m, _sc, _d in (('FPHand', 'Sphere', _leather, (0.085, 0.06, 0.095), None), ('FPHand2', 'Sphere', _leather, (0.095, 0.065, 0.06), None),
                            ('FPSleeve', 'Cylinder', _cloth, (0.075, 0.075, 0.38), (0.55, -0.3, 0.78)), ('FPSleeve2', 'Cylinder', _cloth, (0.075, 0.075, 0.38), (0.5, 0.45, 0.74))):
    _c = ensure_component(ch, _n, unreal.StaticMeshComponent, 'FollowCamera')
    _c.set_editor_property('static_mesh', unreal.load_asset('/Engine/BasicShapes/' + _a))
    _c.set_editor_property('override_materials', [_m])
    _c.set_editor_property('only_owner_see', True)
    _c.set_editor_property('cast_shadow', False)
    _c.set_editor_property('visible', False)
    _c.set_editor_property('relative_scale3d', unreal.Vector(*_sc))
    if _d:                                      # the sleeve runs from the hand down and back out of the frame
        _c.set_editor_property('relative_rotation', unreal.MathLibrary.make_rot_from_z(unreal.Vector(*_d)))
    _c.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
ensure_var(ch, 'ViewFP', 'bool', rep=REP.REPLICATED, category='View')
ensure_var(ch, 'Aiming', 'bool', rep=REP.REPLICATED, category='View')
ensure_var(ch, 'FPGunMeshes', obj_class=unreal.StaticMesh, array=True, category='View')
ensure_var(ch, 'FPGunHips', struct=TR, array=True, category='View')
ensure_var(ch, 'FPGunAdss', struct=TR, array=True, category='View')
ensure_var(ch, 'FPGunMuzzles', struct=V3, array=True, category='View')
ensure_var(ch, 'FPGunHipDef', struct=TR, category='View')
ensure_var(ch, 'FPGunAdsDef', struct=TR, category='View')
ensure_fn(ch, 'ApplyView')
ensure_fn(ch, 'SetBoomBlend', inputs=[('B', 'float')])
ensure_fn(ch, 'WantsFirstPerson', outputs=[('On', 'bool')], pure=True)
ensure_fn(ch, 'IsArmed', outputs=[('On', 'bool')], pure=True)
ensure_fn(ch, 'FPGunPose', inputs=[('M', unreal.StaticMesh)], outputs=[('Hip', TR), ('Ads', TR), ('Muzzle', V3)])
compile_bp(ch, quiet=True)
c = cdo(ch)
c.set_editor_property('ViewFP', False)
if _rifle:
    c.set_editor_property('RifleMesh', _rifle)
# gun table: the revolver + any gun the shop agent put in /Game/GW/Blueprints/Shop or /Game/GW/Characters/Items
guns = []
rev = c.get_editor_property('RevolverMesh')
if rev:
    guns.append(rev)
for folder in ('/Game/GW/Blueprints/Shop', '/Game/GW/Characters/Items', '/Game/GW/Meshes/Weapons'):
    if EAL.does_directory_exist(folder):
        for p in EAL.list_assets(folder, recursive=True):
            low = p.split('.')[-1].lower()                 # the asset name ('burgundy' contains 'gun')
            if any(k in low for k in ('rifle', 'fusil', 'pistol', 'revolver', 'shotgun')) or low.startswith('sm_gun') or low.endswith('_gun'):
                a = unreal.load_asset(p.split('.')[0])
                if isinstance(a, unreal.StaticMesh) and a not in guns:
                    guns.append(a)
hips, adss, muzs = [], [], []
for g_ in guns:
    h, a, m = gun_pose(g_)
    hips.append(h); adss.append(a); muzs.append(m)
c.set_editor_property('FPGunMeshes', guns)
c.set_editor_property('FPGunHips', hips)
c.set_editor_property('FPGunAdss', adss)
c.set_editor_property('FPGunMuzzles', muzs)
if hips:
    c.set_editor_property('FPGunHipDef', hips[0])
    c.set_editor_property('FPGunAdsDef', adss[0])
print('FP guns:', [g_.get_name() for g_ in guns])

lerp_loc = f'(+ (* {mv((0, 0, EYE_Z))} (- 1.0 k)) (* (select seeker {mv(TP_SEEK[0])} {mv(TP_GUEST[0])}) k))'
CH = {
    # boom between the eyes (B = 0) and ApplyLook's over-the-shoulder rig (B = 1)
    'SetBoomBlend': f'''
(fn SetBoomBlend (B)
  (bind seeker (Variables|GW|GetIsSeeker))
  (bind boom (Variables|Camera|GetCameraBoom))
  (bind k (Math|Float|Clamp(Float) :Value B :Min 0.0 :Max 1.0))
  (Transformation|SetRelativeLocation :self boom :NewLocation {lerp_loc})
  (Class|SpringArmComponent|SetTargetArmLength :self boom :TargetArmLength (* (select seeker {TP_SEEK[1]} {TP_GUEST[1]}) k))
  (Class|SpringArmComponent|SetSocketOffset :self boom :SocketOffset (* (select seeker {mv(TP_SEEK[2])} {mv(TP_GUEST[2])}) k)))
''',
    'WantsFirstPerson': f'''
(fn WantsFirstPerson ()
  (return (and (Variables|View|GetViewFP) (not {DANCE_SELF}))))
''',
    # armed = a gun is selected in the inventory (s40: 1 rifle, 8 swap gun, 13 the detective's revolver); 0 on the turret
    'IsArmed': f'''
(fn IsArmed ()
  (if (Variables|GW|GetIsDead)
    (return false))
  (bind h (Variables|Inv|GetHeldItem))
  (return (or (== h 1) (or (== h 8) (== h 13)))))
''',
    # players never turn with the mouse (they face their movement like the NPCs), except while aiming down sights;
    # the server also puts every remote player's boom where that player looks from (the shot ray starts there)
    'ApplyView': '''
(fn ApplyView ()
  (if (not (Pawn|IsPlayerControlled))
    (return))
  ; the user, 2026-11-05: aiming and first person keep the body on the aim, it must; otherwise the mouse only moves the camera
  (bind aim (or (and (Variables|View|GetAiming) (CallFunction|IsArmed)) (Variables|View|GetViewFP)))
  (Variables|Pawn|SetUseControllerRotationYaw aim)
  (Class|CharacterMovementComponent|SetOrientRotationtoMovement :self (Variables|Character|GetCharacterMovement) :bOrientRotationToMovement (not aim))
  (if (and (Networking|HasAuthority) (not (Pawn|IsLocallyControlled)))
    (CallFunction|SetBoomBlend :B (select (CallFunction|WantsFirstPerson) 0.0 1.0))))
''',
    'FPGunPose': '''
(fn FPGunPose (M)
  (bind i (Utilities|Array|FindItem (Variables|View|GetFPGunMeshes) M))
  (if (and (>= i 0) (< i (Utilities|Array|Length (Variables|View|GetFPGunMuzzles))))
    (return (Utilities|Array|Get(acopy) (Variables|View|GetFPGunHips) i) (Utilities|Array|Get(acopy) (Variables|View|GetFPGunAdss) i) (Utilities|Array|Get(acopy) (Variables|View|GetFPGunMuzzles) i)))
  (return (Variables|View|GetFPGunHipDef) (Variables|View|GetFPGunAdsDef) (Math|Vector|MakeVector 12.0 0.0 0.0)))
''',
}
for n, code in CH.items():
    wr(ch, n, code)
ok = compile_bp(ch)
print('BP_GW_Character', node_problems(ch))
save(ch)
lock('/Game/GW/Blueprints/BP_GW_Character', False)

# ---------------------------------------------------------------- the local view driver
drv = load_or_create_bp('BP_GW_ViewDriver', unreal.Actor, FOLDER)
compile_bp(drv, quiet=True)
# the controller's side first: the driver's graphs read WantFP and call TurretFrame
lock('/Game/GW/Blueprints/BP_GW_PlayerController', True)
ensure_var(pcb, 'WantFP', 'bool', category='GW')
ensure_var(pcb, 'ViewDrv', obj_class=drv.generated_class(), category='GW')
for v, t in (('VTestAds', 'bool'), ('VTestT0', 'float'), ('VTestStep', 'int')):     # -GWGunShot (ViewTestTick)
    ensure_var(pcb, v, t, category='GW')
ensure_var(pcb, 'VTestCam', obj_class=unreal.CameraActor, category='GW')
ensure_var(pcb, 'VTestNPC', obj_class=chc, category='GW')
ensure_fn(pcb, 'TurretFrame', inputs=[('Dt', 'float')], outputs=[('Mounted', 'bool'), ('CamLoc', V3)])
compile_bp(pcb, quiet=True)
dc = cdo(drv)
dc.set_editor_property('replicates', False)
for v, t in (('Blend', 'float'), ('MountB', 'float'), ('AdsB', 'float'), ('Fov', 'float'), ('BaseFov', 'float'), ('FovAt', 'float'),
             ('BobT', 'float'), ('BobAmp', 'float'), ('Kick', 'float'), ('Back', 'float'), ('KA', 'float'), ('KB', 'float'),
             ('Shake', 'float'), ('GunKick', 'float'), ('FlashT', 'float'), ('LastKick', 'float'), ('SentAt', 'float'),
             ('HideAt', 'float'), ('DriftT', 'float'), ('SwayYaw', 'float'), ('SwayPitch', 'float'), ('LogAt', 'float'),
             ('AdsOn', 'bool'), ('LastLMB', 'bool'), ('HasLast', 'bool'), ('HideOn', 'bool')):
    ensure_var(drv, v, t, category='View')
ensure_var(drv, 'Rot', struct=RT, category='View')
ensure_var(drv, 'LastRot', struct=RT, category='View')
ensure_var(drv, 'TCam', struct=V3, category='View')
ensure_var(drv, 'Hip', struct=TR, category='View')
ensure_var(drv, 'Ads', struct=TR, category='View')
ensure_var(drv, 'PC', obj_class=pcb.generated_class(), category='View')
ensure_var(drv, 'Ch', obj_class=chc, category='View')
ensure_var(drv, 'NoChar', obj_class=chc, category='View')
ensure_var(drv, 'GunM', obj_class=unreal.StaticMesh, category='View')
ensure_var(drv, 'NoMesh', obj_class=unreal.StaticMesh, category='View')
ensure_var(drv, 'SwapMesh', obj_class=unreal.StaticMesh, category='View')
ensure_fn(drv, 'Setup', inputs=[('NewPC', pcb.generated_class())])
ensure_fn(drv, 'Drive', inputs=[('Dt', 'float')])
ensure_fn(drv, 'DriveChar', inputs=[('C', chc), ('Dt', 'float')])
ensure_fn(drv, 'HideBody', inputs=[('C', chc), ('Hide', 'bool')])
ensure_fn(drv, 'PoseHands', inputs=[('C', chc), ('On', 'bool'), ('Rifle', 'bool'), ('Off', V3)])
ensure_fn(drv, 'PoseGun', inputs=[('C', chc), ('Dt', 'float'), ('BobY', 'float'), ('BobZ', 'float')])
ensure_fn(drv, 'ReadBaseFov')
ensure_fn(drv, 'ToServer', inputs=[('Cmd', 'string')])
ensure_fn(drv, 'HuntOn', outputs=[('On', 'bool')], pure=True)
compile_bp(drv, quiet=True)

# the turret hook the driver calls every frame (body: s35_turret.py)
ensure_fn(pcb, 'TurretFrame', inputs=[('Dt', 'float')], outputs=[('Mounted', 'bool'), ('CamLoc', V3)])

VG = lambda n: f'(Variables|View|Get{n})'
SIN = 'Math|Trig|Sin(Radians)'
FI = 'Math|Interpolation|FInterpTo'
D = {
    'Setup': '''
(fn Setup (NewPC)
  (Variables|View|SetPC NewPC)
  ; tick after the controller: its mouse input is in the control rotation when we read it
  (Actor|Tick|AddTickPrerequisiteActor :self self :PrerequisiteActor NewPC)
  (Development|PrintString :InString "GW view: driver ready" :bPrintToScreen false))
''',
    'Drive': f'''
(fn Drive (Dt)
  (bind pc (Variables|View|GetPC))
  (if (not ({ISVALID} :Object pc))
    (Actor|DestroyActor :self self)
    (return))
  (bind c (Utilities|Casting|CastToBP_GW_Character (Pawn|GetControlledPawn :self pc))
    (:then (CallFunction|DriveChar :C c :Dt Dt))
    (:CastFailed
      (Variables|View|SetHasLast false)
      (Variables|View|SetCh (Variables|View|GetNoChar)))))
''',
    'ToServer': '''
(fn ToServer (Cmd)
  (bind pc (Variables|View|GetPC))
  (if (Networking|HasAuthority :self pc)
    (Development|ExecuteConsoleCommand :Command Cmd :SpecificPlayer pc)
    (else
      (Development|ExecuteConsoleCommand :Command (cat "ServerExec " Cmd) :SpecificPlayer pc))))
''',
    'HuntOn': f'''
(fn HuntOn ()
  (bind s {GSC}
    (:then (return (== (GW|Get|BP_GW_GameState|Phase :self s) 2)))
    (:CastFailed (return false))))
''',
    'ReadBaseFov': f'''
(fn ReadBaseFov ()
  (Variables|View|SetBaseFov 90.0)
  (bind gi (Utilities|Casting|CastToBP_GW_GameInstance (Game|GetGameInstance))
    (:then
      (bind s (GW|Call|BP_GW_GameInstance|GWSettings :self gi))
      (if ({ISVALID} :Object s)
        (Variables|View|SetBaseFov (Math|Float|Clamp(Float) :Value (GW|Get|{SET}|FOV :self s) :Min 60.0 :Max 120.0))))
    (:CastFailed)))
''',
    'HideBody': f'''
(fn HideBody (C Hide)
  (bind m (GW|Get|/Script/Engine.Character|Mesh :self C))
  (Rendering|SetOwnerNoSee :self m :bNewOwnerNoSee Hide)
  (for k (Components|GetChildrenComponents :self m :bIncludeAllDescendants true)
    (bind p (Utilities|Casting|CastToPrimitiveComponent k)
      (:then (Rendering|SetOwnerNoSee :self p :bNewOwnerNoSee Hide))
      (:CastFailed))))
''',
    'PoseGun': f'''
(fn PoseGun (C Dt BobY BobZ)
  (bind fg (GW|Get|BP_GW_Character|FPGun :self C))
  ; the detective's GunMesh, else (a guest with the shop's rifle, BP_GW_GuestGun = the revolver mesh) RevolverMesh
  (bind gm3 (GW|Get|BP_GW_Character|GunMesh :self C))
  (bind rifle (== (GW|Get|BP_GW_Character|HeldItem :self C) 1))
  ; the swap gun (item 8) has its own model: SwapMesh, a default of this driver set by s41_item_models.py
  (bind want (select rifle (GW|Get|BP_GW_Character|RifleMesh :self C) (select (and (== (GW|Get|BP_GW_Character|HeldItem :self C) 8) ({ISVALID} :Object {VG('SwapMesh')})) {VG('SwapMesh')} (select ({ISVALID} :Object (Class|StaticMeshComponent|GetStaticMesh :self gm3)) (Class|StaticMeshComponent|GetStaticMesh :self gm3) (GW|Get|BP_GW_Character|RevolverMesh :self C)))))
  (if (!= want (Variables|View|GetGunM))
    (Variables|View|SetGunM want)
    (Components|StaticMesh|SetStaticMesh :self fg :NewMesh want)
    (bind (hip ads muz) (GW|Call|BP_GW_Character|FPGunPose :self C :M want))
    (Variables|View|SetHip hip)
    (Variables|View|SetAds ads)
    (Transformation|SetRelativeLocation :self (GW|Get|BP_GW_Character|FPFlash :self C) :NewLocation muz :bSweep false :bTeleport true)
    (Transformation|SetRelativeScale3D :self fg :NewScale3D (.scale hip)))
  (bind a {VG('AdsB')})
  (bind gk {VG('GunKick')})
  (bind hipT {VG('Hip')})
  (bind adsT {VG('Ads')})
  (bind off (Math|Vector|MakeVector (* gk -5.0) (* BobY -0.35) (- (* BobZ -0.3) (* gk 0.6))))
  (bind loc (+ (+ (* (.location hipT) (- 1.0 a)) (* (.location adsT) a)) off))
  (CallFunction|PoseHands :C C :On true :Rifle rifle :Off off)
  (bind kick (Math|Rotator|MakeRotator :Pitch (+ (* gk 8.0) {VG('SwayPitch')}) :Yaw {VG('SwayYaw')} :Roll (* {VG('SwayYaw')} 1.5)))
  (Transformation|SetRelativeLocationAndRotation :self fg :NewLocation loc :NewRotation (Math|Rotator|CombineRotators :A (.rotation hipT) :B kick) :bSweep false :bTeleport true))
''',
    # the first-person hands (placeholder gloves and sleeves): around the middle of the barrel of the current pose
    'PoseHands': f'''
(fn PoseHands (C On Rifle Off)
  (bind h1 (GW|Get|BP_GW_Character|FPHand :self C))
  (bind h2 (GW|Get|BP_GW_Character|FPHand2 :self C))
  (bind s1 (GW|Get|BP_GW_Character|FPSleeve :self C))
  (bind s2 (GW|Get|BP_GW_Character|FPSleeve2 :self C))
  (Rendering|SetVisibility :self h1 :bNewVisibility On :bPropagateToChildren false)
  (Rendering|SetVisibility :self s1 :bNewVisibility On :bPropagateToChildren false)
  (Rendering|SetVisibility :self h2 :bNewVisibility (and On Rifle) :bPropagateToChildren false)
  (Rendering|SetVisibility :self s2 :bNewVisibility (and On Rifle) :bPropagateToChildren false)
  (if (not On)
    (return))
  (bind a {VG('AdsB')})
  (bind bc (+ (+ (* (select Rifle {mv(RIFLE_HIP)} {mv(GUN_HIP)}) (- 1.0 a)) (* (select Rifle {mv(RIFLE_ADS)} {mv(GUN_ADS)}) a)) Off))
  ; the rifle's origin (its grip) is 24 cm behind the middle of the barrel at this scale; the forend lies 3 cm under the barrel
  (bind grip (+ bc (select Rifle {mv((-24.0, 0.0, -10.0))} {mv((-5.0, 0.0, -7.0))})))
  (bind fore (+ bc {mv((6.0, 0.0, -7.0))}))
  (Transformation|SetRelativeLocation :self h1 :NewLocation grip :bSweep false :bTeleport true)
  (Transformation|SetRelativeLocation :self s1 :NewLocation (+ grip {mv((-13.0, 7.0, -19.0))}) :bSweep false :bTeleport true)
  (Transformation|SetRelativeLocation :self h2 :NewLocation fore :bSweep false :bTeleport true)
  (Transformation|SetRelativeLocation :self s2 :NewLocation (+ fore {mv((-12.0, -11.0, -18.0))}) :bSweep false :bTeleport true))
''',
    'DriveChar': f'''
(fn DriveChar (C Dt)
  (bind pc (Variables|View|GetPC))
  (if (!= C (Variables|View|GetCh))
    (Variables|View|SetCh C)
    (Variables|View|SetBlend (select (GW|Get|BP_GW_PlayerController|WantFP :self pc) 0.0 1.0))
    (Variables|View|SetHideOn false)
    (Variables|View|SetHideAt -10.0)
    (Variables|View|SetHasLast false)
    (Variables|View|SetAdsB 0.0)
    (Variables|View|SetMountB 0.0)
    (Variables|View|SetFov 0.0)
    (Variables|View|SetFovAt -10.0)
    (Variables|View|SetAdsOn false)
    (Variables|View|SetGunM (Variables|View|GetNoMesh))
    (Development|PrintString :InString (cat "GW view: new pawn " (Utilities|GetDisplayName :Object C) " first person=" (GW|Get|BP_GW_PlayerController|WantFP :self pc)) :bPrintToScreen false))
  (bind now (Utilities|Time|GetGameTimeinSeconds))
  ; ---- the turret (s35): clamps the aim, turns the gun, sends aim and trigger; tells where its sight is
  (bind (mounted tcam) (GW|Call|BP_GW_PlayerController|TurretFrame :self pc :Dt Dt))
  (if mounted
    (Variables|View|SetTCam tcam))
  (Variables|View|SetMountB ({FI} :Current {VG('MountB')} :Target (select mounted 1.0 0.0) :DeltaTime Dt :InterpSpeed 7.0))
  ; ---- first or third person: dancing and the dev option blend to the over-the-shoulder rig
  (bind dead (GW|Get|BP_GW_Character|IsDead :self C))
  (bind dancing {DANCE})
  ; ---- aim down sights (right click, a gun selected in the inventory): that alone brings the first-person view
  (bind armed (GW|Call|BP_GW_Character|IsArmed :self C))
  (bind adsWant (and (and (or (Game|Player|IsInputKeyDown :self pc :Key "RightMouseButton") (GW|Get|BP_GW_PlayerController|VTestAds :self pc)) armed) (and (not mounted) (not dancing))))
  (bind wantFP (or (GW|Get|BP_GW_PlayerController|WantFP :self pc) adsWant))
  (Variables|View|SetBlend ({FI} :Current {VG('Blend')} :Target (select (or mounted (and wantFP (not dancing))) 0.0 1.0) :DeltaTime Dt :InterpSpeed (select adsWant 14.0 7.0)))
  (GW|Call|BP_GW_Character|SetBoomBlend :self C :B {VG('Blend')})
  ; the server must know (it starts the shot ray at this camera)
  (if (and (!= (GW|Get|BP_GW_Character|ViewFP :self C) wantFP) (> now (+ {VG('SentAt')} 0.12)))
    (Variables|View|SetSentAt now)
    (CallFunction|ToServer :Cmd (select wantFP "GWView 1" "GWView 0")))
  (if (!= adsWant {VG('AdsOn')})
    (Variables|View|SetAdsOn adsWant)
    (GW|Set|BP_GW_Character|Aiming :self C :Aiming adsWant)
    (CallFunction|ToServer :Cmd (select adsWant "GWAim 1" "GWAim 0")))
  (GW|Call|BP_GW_Character|ApplyView :self C)
  (Variables|View|SetAdsB ({FI} :Current {VG('AdsB')} :Target (select {VG('AdsOn')} 1.0 0.0) :DeltaTime Dt :InterpSpeed 11.0))
  ; ---- look: slower mouse while aiming, gun sway from the look speed
  (Variables|View|SetRot (Pawn|GetControlRotation :self pc))
  (if (and {VG('HasLast')} (> {VG('AdsB')} 0.02))
    (bind d (Math|Rotator|Delta(Rotator) :A {VG('Rot')} :B {VG('LastRot')}))
    (bind k (- 1.0 (* {VG('AdsB')} {1.0 - ADS_SENS})))
    (Variables|View|SetRot (Math|Rotator|MakeRotator :Pitch (+ (.pitch {VG('LastRot')}) (* (.pitch d) k)) :Yaw (+ (.yaw {VG('LastRot')}) (* (.yaw d) k)) :Roll 0.0)))
  ; the shop's old rifle is hard to aim: the sight drifts by itself (about +/- 1.5 degrees), a slow swing plus a tremble
  (if (and (== (GW|Get|BP_GW_Character|HeldItem :self C) 1) (> {VG('AdsB')} 0.5))
    (Variables|View|SetDriftT (+ {VG('DriftT')} Dt))
    (bind dT {VG('DriftT')})
    (bind dy (* Dt (+ (* ({SIN} (* dT 1.7)) 2.2) (* ({SIN} (* dT 4.3)) 1.3))))
    (bind dp (* Dt (+ (* ({SIN} (* dT 2.3)) 1.8) (* ({SIN} (* dT 5.9)) 1.0))))
    (Variables|View|SetRot (Math|Rotator|MakeRotator :Pitch (+ (.pitch {VG('Rot')}) dp) :Yaw (+ (.yaw {VG('Rot')}) dy) :Roll 0.0)))
  (bind dl (Math|Rotator|Delta(Rotator) :A {VG('Rot')} :B {VG('LastRot')}))
  (bind sw (select {VG('HasLast')} (/ 0.006 (Math|Float|Max(Float) Dt 0.001)) 0.0))
  (Variables|View|SetSwayYaw ({FI} :Current {VG('SwayYaw')} :Target (Math|Float|Clamp(Float) :Value (* (.yaw dl) (* sw -1.0)) :Min -3.5 :Max 3.5) :DeltaTime Dt :InterpSpeed 9.0))
  (Variables|View|SetSwayPitch ({FI} :Current {VG('SwayPitch')} :Target (Math|Float|Clamp(Float) :Value (* (.pitch dl) sw) :Min -3.0 :Max 3.0) :DeltaTime Dt :InterpSpeed 9.0))
  ; ---- recoil: a predicted shot (left click, armed, hunt, revolver cooldown) kicks the view up, 60 % comes back
  (bind lmb (Game|Player|IsInputKeyDown :self pc :Key "LeftMouseButton"))
  (if (and (and lmb (not {VG('LastLMB')})) (and armed (not mounted)))
    (if (and (CallFunction|HuntOn) (>= (- now {VG('LastKick')}) (GW|Get|BP_GW_Character|FireCooldown :self C)))
      (Variables|View|SetLastKick now)
      (Variables|View|SetKick (+ {VG('Kick')} 2.4))
      (Variables|View|SetShake 1.0)
      (Variables|View|SetGunKick 1.0)
      (Variables|View|SetFlashT 0.06)))
  (Variables|View|SetLastLMB lmb)
  (Variables|View|SetKA (* {VG('Kick')} (Math|Float|Min(Float) (* Dt 22.0) 1.0)))
  (Variables|View|SetKick (- {VG('Kick')} {VG('KA')}))
  (Variables|View|SetBack (+ {VG('Back')} (* {VG('KA')} 0.6)))
  (Variables|View|SetKB (* {VG('Back')} (Math|Float|Min(Float) (* Dt 5.0) 1.0)))
  (Variables|View|SetBack (- {VG('Back')} {VG('KB')}))
  (bind kp (- {VG('KA')} {VG('KB')}))
  (if (and (not mounted) (or (> {VG('AdsB')} 0.02) (> (Math|Float|Absolute(Float) kp) 0.0001)))
    (Variables|View|SetRot (Math|Rotator|MakeRotator :Pitch (Math|Float|Clamp(Float) :Value (+ (Math|Rotator|NormalizeAxis :Angle (.pitch {VG('Rot')})) kp) :Min -85.0 :Max 85.0) :Yaw (.yaw {VG('Rot')}) :Roll 0.0))
    (Pawn|SetControlRotation :self pc :NewRotation {VG('Rot')}))
  (Variables|View|SetLastRot {VG('Rot')})
  (Variables|View|SetHasLast true)
  (Variables|View|SetShake (Math|Float|Max(Float) 0.0 (- {VG('Shake')} (* Dt 5.0))))
  (Variables|View|SetGunKick (Math|Float|Max(Float) 0.0 (- {VG('GunKick')} (* Dt 6.0))))
  (Variables|View|SetFlashT (- {VG('FlashT')} Dt))
  ; ---- head bob (walk / sprint), less while aiming, none in third person
  (bind vel (Transformation|GetVelocity :self C))
  (bind spd (Math|Vector|VectorLength (Math|Vector|MakeVector (.x vel) (.y vel) 0.0)))
  (bind ground (< (Math|Float|Absolute(Float) (.z vel)) 15.0))
  (Variables|View|SetBobAmp ({FI} :Current {VG('BobAmp')} :Target (select (and ground (> spd 40.0)) (Math|Float|Min(Float) (/ spd 300.0) 1.3) 0.0) :DeltaTime Dt :InterpSpeed 6.0))
  (Variables|View|SetBobT (+ {VG('BobT')} (* Dt (+ 3.5 (* spd 0.011)))))
  (bind mb {VG('MountB')})
  (bind ba (* {VG('BobAmp')} (* (- 1.0 {VG('Blend')}) (* (- 1.0 (* {VG('AdsB')} 0.8)) (- 1.0 mb)))))
  (bind bobY (* ({SIN} {VG('BobT')}) (* 1.0 ba)))
  (bind bobZ (* ({SIN} (* {VG('BobT')} 2.0)) (* 1.3 ba)))
  ; ---- camera: eyes (+ bob) or the turret's sight, plus the shot shake
  (bind cam (GW|Get|BP_GW_Character|FollowCamera :self C))
  (bind boomLoc (Transformation|GetWorldLocation :self (GW|Get|BP_GW_Character|CameraBoom :self C)))
  (bind mrel (Math|Vector|UnrotateVector :A (- {VG('TCam')} boomLoc) :B {VG('Rot')}))
  (bind fprel (Math|Vector|MakeVector (* {EYE_FWD} (- 1.0 {VG('Blend')})) bobY bobZ))
  (Transformation|SetRelativeLocation :self cam :NewLocation (+ (* fprel (- 1.0 mb)) (* mrel mb)) :bSweep false :bTeleport true)
  (bind sk {VG('Shake')})
  (Transformation|SetRelativeRotation :self cam :NewRotation (Math|Rotator|MakeRotator :Roll (+ (* ({SIN} (* now 31.0)) (* sk 0.8)) (* ({SIN} {VG('BobT')}) (* 0.4 ba))) :Pitch (* ({SIN} (* now 43.0)) (* sk 0.5)) :Yaw (* ({SIN} (* now 37.0)) (* sk 0.4))) :bSweep false :bTeleport true)
  ; ---- field of view: the player's setting, +7 sprinting, {ADS_FOV:.0f} aiming down sights, x0.85 on the turret
  (if (> (- now {VG('FovAt')}) 0.5)
    (Variables|View|SetFovAt now)
    (CallFunction|ReadBaseFov))
  (bind base {VG('BaseFov')})
  (bind sprint (and (GW|Get|BP_GW_Character|IsSprinting :self C) (> spd 300.0)))
  (bind fpFov (+ base (select sprint (* 7.0 (- 1.0 {VG('Blend')})) 0.0)))
  (bind adsFov (Math|Float|Min(Float) {ADS_FOV} (- base 15.0)))
  (bind tgt (+ (* (+ (* fpFov (- 1.0 {VG('AdsB')})) (* adsFov {VG('AdsB')})) (- 1.0 mb)) (* (* base 0.85) mb)))
  (Variables|View|SetFov (select (< {VG('Fov')} 1.0) tgt ({FI} :Current {VG('Fov')} :Target tgt :DeltaTime Dt :InterpSpeed 9.0)))
  (Camera|SetFieldOfView :self cam :InFieldOfView {VG('Fov')})
  ; ---- the own body: hidden from its owner in first person (costume, hand gun, flames all hang on the mesh)
  (bind hide (< {VG('Blend')} 0.5))
  (if (or (!= hide {VG('HideOn')}) (> (- now {VG('HideAt')}) 1.0))
    (Variables|View|SetHideOn hide)
    (Variables|View|SetHideAt now)
    (CallFunction|HideBody :C C :Hide hide))
  ; ---- first-person gun, flash, flames, flashlight at the eyes
  (bind gunOn (and (and armed hide) (and (< mb 0.3) (not dead))))
  (Rendering|SetVisibility :self (GW|Get|BP_GW_Character|FPGun :self C) :bNewVisibility gunOn :bPropagateToChildren false)
  (if gunOn
    (CallFunction|PoseGun :C C :Dt Dt :BobY bobY :BobZ bobZ)
    (else
      (CallFunction|PoseHands :C C :On false :Rifle false :Off {mv((0, 0, 0))})))
  (Rendering|SetVisibility :self (GW|Get|BP_GW_Character|FPFlash :self C) :bNewVisibility (and gunOn (> {VG('FlashT')} 0.0)) :bPropagateToChildren false)
  (bind burn (and (GW|Get|BP_GW_Character|Burning :self C) (and hide (< mb 0.5))))
  (Rendering|SetVisibility :self (GW|Get|BP_GW_Character|FPFlame0 :self C) :bNewVisibility burn :bPropagateToChildren false)
  (Rendering|SetVisibility :self (GW|Get|BP_GW_Character|FPFlame1 :self C) :bNewVisibility burn :bPropagateToChildren false)
  (Transformation|SetRelativeLocation :self (GW|Get|BP_GW_Character|Flashlight :self C) :NewLocation (+ (* {mv((30, 0, -12))} (- 1.0 {VG('Blend')})) (* {mv((340, 0, -15))} {VG('Blend')})) :bSweep false :bTeleport true)
  (if (and (Utilities|HasLaunchOption :OptionToCheck "GWViewLog") (> (- now {VG('LogAt')}) 1.0))
    (Variables|View|SetLogAt now)
    (Development|PrintString :InString (cat "GW view: blend=" {VG('Blend')} " mount=" mb " ads=" {VG('AdsB')} " fov=" {VG('Fov')} " arm=" (GW|Get|/Script/Engine.SpringArmComponent|TargetArmLength :self (GW|Get|BP_GW_Character|CameraBoom :self C)) " armed=" armed " gun=" gunOn " orient=" (GW|Get|/Script/Engine.CharacterMovementComponent|bOrientRotationToMovement :self (GW|Get|/Script/Engine.Character|CharacterMovement :self C)) " yawctl=" (GW|Get|/Script/Engine.Pawn|bUseControllerRotationYaw :self C) " cam=" (Transformation|GetWorldLocation :self cam) " pawn=" (Transformation|GetActorLocation :self C)) :bPrintToScreen false)))
''',
    'EventGraph': '''
(event EventTick (DeltaSeconds)
  (CallFunction|Drive :Dt DeltaSeconds))
''',
}
for n, code in D.items():
    wr(drv, n, code)
    compile_bp(drv, quiet=True)
compile_bp(drv)
print('BP_GW_ViewDriver', node_problems(drv))
save(drv)

# ---------------------------------------------------------------- game mode: the server side of the view
if 'nogm' not in UE_ARGS:          # `ue_run.py s37_view.py nogm`: Character / driver / PC only (the GM body never changes)
    ensure_fn(gm, 'ViewServerTick')
    compile_bp(gm, quiet=True)
    wr(gm, 'ViewServerTick', f'''
(fn ViewServerTick ()
  (for c (Actor|GetAllActorsOfClass :ActorClass "/Game/GW/Blueprints/BP_GW_Character.BP_GW_Character_C")
    (if (Pawn|IsPlayerControlled :self c)
      (GW|Call|BP_GW_Character|ApplyView :self c))))
''')
    compile_bp(gm)
    print('BP_GW_GameMode', node_problems(gm))
    save(gm)

# ---------------------------------------------------------------- player controller
for f in ('ViewClientTick',):
    ensure_fn(pcb, f)
ensure_fn(pcb, 'SetViewMode', inputs=[('FP', 'bool')])
ensure_fn(pcb, 'ViewTestTick')
ensure_fn(pcb, 'VTestPlace', inputs=[('Mode', 'int')])
ensure_fn(pcb, 'GWView', inputs=[('On', 'int')], exec_fn=True)
ensure_fn(pcb, 'GWAim', inputs=[('On', 'int')], exec_fn=True)
compile_bp(pcb, quiet=True)
_g = get_graph(pcb, 'VTestPlace')
if 'BestD' not in BT.list_variables(pcb, _g):
    BT.add_variable(pcb, 'BestD', 'float', graph=_g)
if 'BestT' not in BT.list_variables(pcb, _g):
    BT.add_object_variable(pcb, 'BestT', chc, graph=_g)
cdo(pcb).set_editor_property('WantFP', False)
VSTEPS = '  (if (and (== (Variables|GW|GetVTestStep) 0) (> el 6))\n    (Variables|GW|SetVTestStep 1)\n    (CallFunction|DevServer :Cmd "GWDevQuickTest 2")\n    (Development|PrintString :InString (cat "GW viewshot step 1 t=" el) :bPrintToScreen false))\n  (if (and (== (Variables|GW|GetVTestStep) 1) (> el 8))\n    (Variables|GW|SetVTestStep 2)\n    (CallFunction|DevServer :Cmd "GWDevTeleport 2925 3000 130")\n    (Pawn|SetControlRotation :self self :NewRotation (Math|Rotator|MakeRotator :Pitch -6.0 :Yaw 90.0 :Roll 0.0))\n    (Development|PrintString :InString (cat "GW viewshot step 2 t=" el) :bPrintToScreen false))\n  (if (and (== (Variables|GW|GetVTestStep) 2) (> el 10))\n    (Variables|GW|SetVTestStep 3)\n    (Development|ExecuteConsoleCommand :Command "Shot showui" :SpecificPlayer self)\n    (Development|PrintString :InString (cat "GW viewshot step 3 t=" el) :bPrintToScreen false))\n  (if (and (== (Variables|GW|GetVTestStep) 3) (> el 10.5))\n    (Variables|GW|SetVTestStep 4)\n    (Variables|GW|SetVTestAds true)\n    (Development|PrintString :InString (cat "GW viewshot step 4 t=" el) :bPrintToScreen false))\n  (if (and (== (Variables|GW|GetVTestStep) 4) (> el 11.5))\n    (Variables|GW|SetVTestStep 5)\n    (Development|ExecuteConsoleCommand :Command "Shot showui" :SpecificPlayer self)\n    (Development|PrintString :InString (cat "GW viewshot step 5 t=" el) :bPrintToScreen false))\n  (if (and (== (Variables|GW|GetVTestStep) 5) (> el 12))\n    (Variables|GW|SetVTestStep 6)\n    (Variables|GW|SetVTestAds false)\n    (CallFunction|DevServer :Cmd "GWDevNPCOutfit 32")\n    (Development|PrintString :InString (cat "GW viewshot step 6 t=" el) :bPrintToScreen false))\n  (if (and (== (Variables|GW|GetVTestStep) 6) (> el 14))\n    (Variables|GW|SetVTestStep 7)\n    (CallFunction|VTestPlace :Mode -1)\n    (Development|PrintString :InString (cat "GW viewshot step 7 t=" el) :bPrintToScreen false))\n  (if (and (== (Variables|GW|GetVTestStep) 7) (> el 15))\n    (Variables|GW|SetVTestStep 8)\n    (CallFunction|VTestPlace :Mode 0)\n    (Development|ExecuteConsoleCommand :Command "Shot" :SpecificPlayer self)\n    (Development|PrintString :InString (cat "GW viewshot step 8 t=" el) :bPrintToScreen false))\n  (if (and (== (Variables|GW|GetVTestStep) 8) (> el 16))\n    (Variables|GW|SetVTestStep 9)\n    (CallFunction|VTestPlace :Mode 1)\n    (Development|ExecuteConsoleCommand :Command "Shot" :SpecificPlayer self)\n    (Development|PrintString :InString (cat "GW viewshot step 9 t=" el) :bPrintToScreen false))\n  (if (and (== (Variables|GW|GetVTestStep) 9) (> el 17))\n    (Variables|GW|SetVTestStep 10)\n    (CallFunction|VTestPlace :Mode 2)\n    (Development|ExecuteConsoleCommand :Command "Shot" :SpecificPlayer self)\n    (Development|PrintString :InString (cat "GW viewshot step 10 t=" el) :bPrintToScreen false))\n  (if (and (== (Variables|GW|GetVTestStep) 10) (> el 18))\n    (Variables|GW|SetVTestStep 11)\n    (CallFunction|VTestPlace :Mode 0)\n    (Development|ExecuteConsoleCommand :Command "Shot" :SpecificPlayer self)\n    (Development|PrintString :InString (cat "GW viewshot step 11 t=" el) :bPrintToScreen false))\n  (if (and (== (Variables|GW|GetVTestStep) 11) (> el 19))\n    (Variables|GW|SetVTestStep 12)\n    (CallFunction|VTestPlace :Mode 1)\n    (Development|ExecuteConsoleCommand :Command "Shot" :SpecificPlayer self)\n    (Development|PrintString :InString (cat "GW viewshot step 12 t=" el) :bPrintToScreen false))\n  (if (and (== (Variables|GW|GetVTestStep) 12) (> el 20))\n    (Variables|GW|SetVTestStep 13)\n    (CallFunction|VTestPlace :Mode 2)\n    (Development|ExecuteConsoleCommand :Command "Shot" :SpecificPlayer self)\n    (Development|PrintString :InString (cat "GW viewshot step 13 t=" el) :bPrintToScreen false))\n  (if (and (== (Variables|GW|GetVTestStep) 13) (> el 21))\n    (Variables|GW|SetVTestStep 14)\n    (Game|Player|SetViewTargetwithBlend :self self :NewViewTarget (Pawn|GetControlledPawn :self self) :BlendTime 0.0)\n    (CallFunction|SetViewMode :FP false)\n    (Development|PrintString :InString (cat "GW viewshot step 14 t=" el) :bPrintToScreen false))\n  (if (and (== (Variables|GW|GetVTestStep) 14) (> el 23.5))\n    (Variables|GW|SetVTestStep 15)\n    (Development|ExecuteConsoleCommand :Command "Shot showui" :SpecificPlayer self)\n    (Development|PrintString :InString (cat "GW viewshot step 15 t=" el) :bPrintToScreen false))\n  (if (and (== (Variables|GW|GetVTestStep) 15) (> el 24))\n    (Variables|GW|SetVTestStep 16)\n    (CallFunction|SetViewMode :FP true)\n    (Development|PrintString :InString (cat "GW viewshot step 16 t=" el) :bPrintToScreen false))\n  (if (and (== (Variables|GW|GetVTestStep) 16) (> el 26))\n    (Variables|GW|SetVTestStep 17)\n    (Development|PrintString :InString "GW viewshot done" :bPrintToScreen false)\n    (Development|PrintString :InString (cat "GW viewshot step 17 t=" el) :bPrintToScreen false))'


def vstep(n, at, body):
    return (f"\n  (if (and (== (Variables|GW|GetVTestStep) {n}) (> el {at}))\n    (Variables|GW|SetVTestStep {n + 1})\n{body}\n"
            f"    (Development|PrintString :InString (cat \"GW viewshot step {n + 1} t=\" el) :bPrintToScreen false))")


# then the machine gun: mount, a burst seen through the sight (HUD on), the same burst from the hall floor
SHOT_UI = '    (Development|ExecuteConsoleCommand :Command "Shot showui" :SpecificPlayer self)'
VSTEPS += ''.join(vstep(n, at, b) for n, at, b in [
    (17, 27, '    (CallFunction|DevServer :Cmd "GWDevTurretGo")'),
    (18, 28, '    (bind h18 (CallFunction|TryTurret))'),
    (19, 30, '    (Pawn|SetControlRotation :self self :NewRotation (Math|Rotator|MakeRotator :Pitch -18.0 :Yaw -80.0 :Roll 0.0))'),
    (20, 31, '    (Variables|GW|SetTTestFire true)'),
    (21, 31.6, SHOT_UI),
    (22, 32.2, '    (CallFunction|VTestPlace :Mode 3)\n    (Development|ExecuteConsoleCommand :Command "Shot" :SpecificPlayer self)'),
    (23, 33, '    (Variables|GW|SetTTestFire false)\n    (Game|Player|SetViewTargetwithBlend :self self :NewViewTarget (Pawn|GetControlledPawn :self self) :BlendTime 0.0)'),
    (24, 34, '    (bind h24 (CallFunction|TryTurret))'),
    (25, 36, '    (Development|PrintString :InString "GW viewshot turret done" :bPrintToScreen false)'),
    (26, 37, '    (CallFunction|DevServer :Cmd "GWDevRole 1")'),
    (27, 39.5, '    (CallFunction|DevServer :Cmd "GWDevGive 1")\n    (CallFunction|SetViewMode :FP false)'),
    (28, 42, '    (CallFunction|VTestPlace :Mode 4)\n    (Development|ExecuteConsoleCommand :Command "Shot" :SpecificPlayer self)'),
    (29, 43, '    (CallFunction|VTestPlace :Mode 5)\n    (Development|ExecuteConsoleCommand :Command "Shot" :SpecificPlayer self)'),
    (30, 44, '    (Game|Player|SetViewTargetwithBlend :self self :NewViewTarget (Pawn|GetControlledPawn :self self) :BlendTime 0.0)'),
    (31, 45, SHOT_UI),
    (32, 46, '    (CallFunction|SetViewMode :FP true)'),
    (33, 48, SHOT_UI),
    (34, 49, '    (Development|PrintString :InString "GW viewshot guest gun done" :bPrintToScreen false)')])
PCW = {
    # -GWGunShot (rendered QA): first-person hip and aim-down-sights shots as a detective, then a walking NPC in the
    # detective look filmed at the right hand (side, front, close), then the third-person option
    'ViewTestTick': '''
(fn ViewTestTick ()
  (bind now (Utilities|Time|GetRealTimeSeconds))
  (if (<= (Variables|GW|GetVTestT0) 0.0)
    (Variables|GW|SetVTestT0 now))
  (bind el (- now (Variables|GW|GetVTestT0)))
''' + VSTEPS + ')\n',
    'ViewClientTick': f'''
(fn ViewClientTick ()
  (if (not (Pawn|IsLocalPlayerController))
    (return))
  (if (Utilities|HasLaunchOption :OptionToCheck "GWGunShot")
    (CallFunction|ViewTestTick))
  (if (not ({ISVALID} :Object (Variables|GW|GetViewDrv)))
    (Variables|GW|SetViewDrv (Game|SpawnActorfromClass :Class "{DRV_CLS}" :SpawnTransform (Math|Transform|MakeTransform) :CollisionHandlingOverride "AlwaysSpawn"))
    (GW|Call|{DRV_CLS}|Setup :self (Variables|GW|GetViewDrv) :NewPC self)))
''',
    'VTestPlace': f"""
(fn VTestPlace (Mode)
  (if (== Mode -1)
    (bind me (Pawn|GetControlledPawn :self self))
    (Variables|Default|SetBestD 100000000.0)
    (for a (Actor|GetAllActorsOfClass :ActorClass "/Game/GW/Blueprints/BP_GW_Character.BP_GW_Character_C")
      ; the nearest guest NPC, a walking one preferred (-20 m): gun2 found no NPC above 60 cm/s at that instant
      (if (and (not (Pawn|IsPlayerControlled :self a)) (and (== (GW|Get|BP_GW_Character|Kind :self a) 0) (not (GW|Get|BP_GW_Character|IsDead :self a))))
        (bind d (- (Math|Vector|Distance(Vector) (Transformation|GetActorLocation :self a) (Transformation|GetActorLocation :self me)) (select (> (Math|Vector|VectorLength (Transformation|GetVelocity :self a)) 60.0) 2000.0 0.0)))
        (if (< d (Variables|Default|GetBestD))
          (Variables|Default|SetBestD d)
          (Variables|Default|SetBestT a))))
    (Variables|GW|SetVTestNPC (Variables|Default|GetBestT))
    (Variables|GW|SetVTestCam (Game|SpawnActorfromClass :Class "/Script/Engine.CameraActor" :SpawnTransform (Math|Transform|MakeTransform) :CollisionHandlingOverride "AlwaysSpawn"))
    (Game|Player|SetViewTargetwithBlend :self self :NewViewTarget (Variables|GW|GetVTestCam) :BlendTime 0.0)
    (return))
  ; mode 3: from the hall floor, looking up at the machine gun on the gallery
  (if (and (== Mode 3) ({ISVALID} :Object (Variables|GW|GetVTestCam)))
    (bind tl (Math|Vector|MakeVector 3000.0 1000.0 260.0))
    (Transformation|SetActorLocationAndRotation :self (Variables|GW|GetVTestCam) :NewLocation tl :NewRotation (Math|Rotator|FindLookatRotation :Start tl :Target (Math|Vector|MakeVector 3177.0 2005.0 640.0)) :bSweep false :bTeleport true)
    (Game|Player|SetViewTargetwithBlend :self self :NewViewTarget (Variables|GW|GetVTestCam) :BlendTime 0.0)
    (return))
  ; modes 4 / 5: the host's own pawn (the view driver's current character), framed like modes 0 / 1
  (if (>= Mode 4)
    (Variables|GW|SetVTestNPC (GW|Get|{DRV_CLS}|Ch :self (Variables|GW|GetViewDrv)))
    (Game|Player|SetViewTargetwithBlend :self self :NewViewTarget (Variables|GW|GetVTestCam) :BlendTime 0.0))
  (bind md (select (>= Mode 4) (- Mode 4) Mode))
  (bind n (Variables|GW|GetVTestNPC))
  (if (not ({ISVALID} :Object n))
    (return))
  (bind hand (Transformation|GetSocketLocation :self (GW|Get|/Script/Engine.Character|Mesh :self n) :InSocketName "hand_r"))
  (bind f (Transformation|GetActorForwardVector :self n))
  (bind r (Transformation|GetActorRightVector :self n))
  (bind off (select (== md 0) (* r 150.0) (select (== md 1) (+ (* f 170.0) (Math|Vector|MakeVector 0.0 0.0 30.0)) (+ (* f 60.0) (* r 75.0)))))
  (bind camLoc (+ hand off))
  (Transformation|SetActorLocationAndRotation :self (Variables|GW|GetVTestCam) :NewLocation camLoc :NewRotation (Math|Rotator|FindLookatRotation :Start camLoc :Target hand) :bSweep false :bTeleport true)
  (Development|PrintString :InString (cat "GW viewshot cam mode=" Mode " npc=" (Utilities|GetDisplayName :Object n) " hand=" hand) :bPrintToScreen false))
""",
    'SetViewMode': '''
(fn SetViewMode (FP)
  (Variables|GW|SetWantFP FP)
  (Development|PrintString :InString (cat "GW view: first person=" FP) :bPrintToScreen false))
''',
    'GWView': f'''
(fn GWView (On)
  (bind ch {MYCH}
    (:then
      (GW|Set|BP_GW_Character|ViewFP :self ch :ViewFP (!= On 0))
      ; the shot ray starts at this camera: move it now, not at the next ViewServerTick
      (GW|Call|BP_GW_Character|ApplyView :self ch)
      (Development|PrintString :InString (cat "GW view: server first person=" (!= On 0) " for " (PlayerState|GetPlayerName :self (GW|Get|/Script/Engine.Controller|PlayerState))) :bPrintToScreen false))
    (:CastFailed)))
''',
    'GWAim': f'''
(fn GWAim (On)
  (bind ch {MYCH}
    (:then
      (GW|Set|BP_GW_Character|Aiming :self ch :Aiming (and (!= On 0) (GW|Call|BP_GW_Character|IsArmed :self ch)))
      (GW|Call|BP_GW_Character|ApplyView :self ch)
      (Development|PrintString :InString (cat "GW view: aiming=" (GW|Get|BP_GW_Character|Aiming :self ch) " yawctl=" (GW|Get|/Script/Engine.Pawn|bUseControllerRotationYaw :self ch) " for " (PlayerState|GetPlayerName :self (GW|Get|/Script/Engine.Controller|PlayerState))) :bPrintToScreen false))
    (:CastFailed)))
''',
}
for n, code in PCW.items():
    wr(pcb, n, code)
# TurretFrame keeps s35's body; a default one until s35 has run
_tf = get_graph(pcb, 'TurretFrame')
if len(list(BT.find_nodes(_tf))) <= 2:
    wr(pcb, 'TurretFrame', '(fn TurretFrame (Dt) (return false (Math|Vector|MakeVector 0.0 0.0 0.0)))')
compile_bp(pcb)
print('BP_GW_PlayerController', node_problems(pcb))
save(pcb)
lock('/Game/GW/Blueprints/BP_GW_PlayerController', False)
print('DSL ERRORS:', len(ERRORS))
for e_ in ERRORS:
    print('  ', e_)
