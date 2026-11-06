"""The approved 3D models of the gameplay items replace the basic-shape placeholders. Gameplay graphs are untouched.

Re-runnable, and it must run AFTER s34 / s35 / s37 / s38 / s40_inventory / s40_events2 if one of them is re-run: those
scripts put the basic shapes back on their components (the components themselves stay, this script only changes their mesh and
transform). Args: `import` (GLBs only), `report` (print the geometry), names of parts to fit, nothing = everything.

Import: each GLB once (stamp = path + mtime, Tools/gameplay/s41_state.json) to /Game/GW/Characters/Items/<name>, then MI_GW_Item_<name>
of M_GW_Prop instead of the Interchange materials, so the game needs no Interchange plugin content at runtime (as Tools/level/dress.py).
Axes after import: UE (X, Y, Z) = glTF (x, z, y), 1 glTF unit = 100 cm, pivot = bounding-box centre. So front +Z (glTF) = +Y, muzzle
+X (glTF) = +X. Nanite stays off: FPGun is force_disable_nanite and a Nanite fallback looks coarse this close to the camera.
No collision is needed: every placeholder part had none, except the turret pedestal, which stays.
"""
import sys, importlib, json, os, re
sys.path.insert(0, r'J:\Projets\Unreal_Projects\Guess Who\Tools\gameplay')
import gw_lib; importlib.reload(gw_lib)
from gw_lib import *

ROOT = r'J:\Projets\Unreal_Projects\Guess Who'
STATE = os.path.join(ROOT, 'Tools', 'gameplay', 's41_state.json')
ITEMS_DIR = '/Game/GW/Characters/Items'
SHOP = '/Game/GW/Blueprints/Shop'
PICK = '/Game/GW/Blueprints/Pickups'
NAMES = 'sword_knight rifle_old smoke_grenade gas_canister door_trap time_bomb turret_mg swap_pistol hidden_blade mystery_box breaker_box serving_tray'.split()
ARGS = set(UE_ARGS)
tools = unreal.AssetToolsHelpers.get_asset_tools()
mel = unreal.MaterialEditingLibrary


def want(p):
    return not (ARGS - {'report'}) or p in ARGS


def classify(texs):
    bc = mr = nm = None
    for t in texs:
        low = t.get_name().lower()
        if 'normal' in low:
            nm = t
        elif 'metal' in low or 'rough' in low or 'orm' in low:
            mr = t
        elif bc is None or 'base' in low or 'color' in low or 'albedo' in low:
            bc = t
    return bc, mr, nm


def fix_textures(bc, mr, nm):
    TC = unreal.TextureCompressionSettings
    for tex, srgb, comp in ((bc, True, TC.TC_DEFAULT), (mr, False, TC.TC_DEFAULT), (nm, False, TC.TC_NORMALMAP)):
        if tex and (tex.get_editor_property('srgb') != srgb or tex.get_editor_property('compression_settings') != comp):
            tex.set_editor_property('srgb', srgb)
            tex.set_editor_property('compression_settings', comp)
            EAL.save_loaded_asset(tex, False)


def import_item(name, glb, state):
    stamp = f'{glb}|{int(os.path.getmtime(glb))}'
    dest = f'{ITEMS_DIR}/{name}'
    st = state.get(name)
    if st and st['stamp'] == stamp and EAL.does_asset_exist(st['mesh']):
        return unreal.load_asset(st['mesh'])
    t = unreal.AssetImportTask()
    t.filename = glb; t.destination_path = dest; t.automated = True; t.replace_existing = True; t.save = False
    tools.import_asset_tasks([t])
    mesh, texs, mats = None, [], []
    for p in EAL.list_assets(dest, recursive=True):
        o = unreal.load_asset(p)
        if isinstance(o, unreal.StaticMesh):
            mesh = o
        elif isinstance(o, unreal.Texture2D):
            texs.append(o)
        elif isinstance(o, unreal.MaterialInterface) and not o.get_name().startswith('MI_GW_Item'):
            mats.append(o)
    if mesh is None:
        raise RuntimeError(f'no static mesh imported for {name}')
    bc, mr, nm = classify(texs)
    print(' ', name, 'textures', [x.get_name() for x in texs], '->', bc and bc.get_name(), mr and mr.get_name(), nm and nm.get_name())
    fix_textures(bc, mr, nm)
    mi_path = f'{dest}/MI_GW_Item_{name}'
    mi = unreal.load_asset(mi_path) if EAL.does_asset_exist(mi_path) else tools.create_asset(
        f'MI_GW_Item_{name}', dest, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    mel.set_material_instance_parent(mi, unreal.load_asset('/Game/GW/Materials/Master/M_GW_Prop'))
    for pname, tex in (('BaseColor', bc), ('MetalRough', mr), ('Normal', nm)):
        if tex:
            mel.set_material_instance_texture_parameter_value(mi, pname, tex)
    if not mr:
        mel.set_material_instance_scalar_parameter_value(mi, 'MetallicScale', 0.0)
    mel.update_material_instance(mi)
    EAL.save_loaded_asset(mi, False)
    for i in range(len(mesh.static_materials)):
        mesh.set_material(i, mi)
    ns = mesh.get_editor_property('nanite_settings')
    ns.set_editor_property('enabled', False)
    mesh.set_editor_property('nanite_settings', ns)
    EAL.save_loaded_asset(mesh, False)
    for m in mats:
        EAL.delete_loaded_asset(m)
    for x in texs:
        EAL.save_loaded_asset(x, False)
    state[name] = dict(stamp=stamp, mesh=mesh.get_path_name().split('.')[0])
    print('  imported', name, mesh.get_path_name())
    return mesh


man = json.load(open(os.path.join(ROOT, 'AssetGen', 'manifest.json'), encoding='utf-8'))
ASSET = {a['name']: a for a in man['assets']}
try:
    state = json.load(open(STATE, encoding='utf-8'))
except (OSError, ValueError):
    state = {}
MESH = {}
for n in NAMES:
    a = ASSET[n]
    assert a.get('status') == 'approved', n
    MESH[n] = import_item(n, a['files']['glb'], state)
with open(STATE, 'w', encoding='utf-8') as fh:
    json.dump(state, fh, indent=1)


def verts(mesh):
    sec = unreal.ProceduralMeshLibrary.get_section_from_static_mesh(mesh, 0, 0)
    return [(p.x, p.y, p.z) for p in sec[0]]


def extents(mesh):
    b = mesh.get_bounding_box()
    return (b.min.x, b.min.y, b.min.z), (b.max.x, b.max.y, b.max.z)


if 'report' in ARGS or 'import' in ARGS:
    for n, m in MESH.items():
        lo, hi = extents(m)
        print(n, 'lo', [round(v, 1) for v in lo], 'hi', [round(v, 1) for v in hi], 'size_cm', ASSET[n]['size_cm'], 'mats', [str(x.material_interface.get_name()) if x.material_interface else None for x in m.static_materials])
        if 'report' in ARGS:
            pts = verts(m)
            ax = max(range(3), key=lambda i: hi[i] - lo[i])
            L = hi[ax] - lo[ax]
            for k in range(10):                    # slices along the longest axis: where is the guard, the grip, the barrel line
                s = [p for p in pts if lo[ax] + L * k / 10 <= p[ax] <= lo[ax] + L * (k + 1) / 10]
                if s:
                    print('   slice', k, 'n', len(s), ' '.join(f'{"XYZ"[i]} {min(p[i] for p in s):.1f}..{max(p[i] for p in s):.1f} c{sum(p[i] for p in s) / len(s):.1f}' for i in range(3) if i != ax))
    if not (ARGS - {'report', 'import'}):
        raise SystemExit

# ================================================================ fitting
def lock(asset, on):
    import time
    with open(os.path.join(ROOT, 'Tools', 'agent_logs', 'locks.md'), 'a', encoding='utf-8') as fh:
        fh.write(f"{'LOCK' if on else 'UNLOCK'} {asset} items {time.strftime('%H:%M')}\n")


def size_scale(n):
    """Uniform scale so the mesh's largest extent is the largest of size_cm."""
    lo, hi = extents(MESH[n])
    return max(ASSET[n]['size_cm']) / max(hi[i] - lo[i] for i in range(3))


def m2p(n, rot=(0, 0, 0), anchor=(0, 0, 0), target=(0, 0, 0), scale=None):
    """Model space -> placeholder space: uniform scale, rotation (roll, pitch, yaw), and the model's point `anchor` lands on `target`."""
    s = size_scale(n) if scale is None else scale
    r = unreal.Rotator(roll=rot[0], pitch=rot[1], yaw=rot[2])
    a = r.quaternion().rotate_vector(unreal.Vector(anchor[0] * s, anchor[1] * s, anchor[2] * s))
    return unreal.Transform(location=unreal.Vector(target[0] - a.x, target[1] - a.y, target[2] - a.z), rotation=r, scale=unreal.Vector(s, s, s))


def put(bp, comp, n, xf, shadow=None):
    c = unreal.SubobjectDataBlueprintFunctionLibrary.get_object(subobjects(bp)[comp][1])
    c.set_editor_property('static_mesh', MESH[n])
    c.set_editor_property('override_materials', [])
    c.set_editor_property('relative_location', xf.translation)
    c.set_editor_property('relative_rotation', xf.rotation.rotator())
    c.set_editor_property('relative_scale3d', xf.scale3d)
    c.set_editor_property('visible', True)
    if shadow is not None:
        c.set_editor_property('cast_shadow', shadow)
    c.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
    print(f'  {bp.get_name()}.{comp} = {n}: loc {[round(v, 2) for v in (xf.translation.x, xf.translation.y, xf.translation.z)]} scale {xf.scale3d.x:.4f}')
    return c


def hide(bp, *comps):
    objs = subobjects(bp)
    for name in comps:
        c = unreal.SubobjectDataBlueprintFunctionLibrary.get_object(objs[name][1])
        c.set_editor_property('static_mesh', None)
        c.set_editor_property('visible', False)


def rel(bp, comp, loc=None, scale=None):
    c = unreal.SubobjectDataBlueprintFunctionLibrary.get_object(subobjects(bp)[comp][1])
    if loc is not None:
        c.set_editor_property('relative_location', unreal.Vector(*loc))
    if scale is not None:
        c.set_editor_property('relative_scale3d', unreal.Vector(*scale))
    return c


def finish(bp):
    lock(bp.get_path_name().split('.')[0], True)
    ok = compile_bp(bp)
    save(bp)
    lock(bp.get_path_name().split('.')[0], False)
    if not ok:
        raise RuntimeError('compile failed: ' + bp.get_name())


# ---- the sword: tip towards -Z in the GLB. Placeholder: grip centre at the origin, blade +Z, guard across X. The grip's centre is at local z = 37.
if want('sword'):
    SW = m2p('sword_knight', rot=(180, 0, 0), anchor=(0, 0, 37), target=(0, 0, 0))
    for name, folder in (('BP_GW_Pickup', PICK), ('BP_GW_HeldSword', PICK), ('BP_GW_FPItems', PICK)):
        bp = load_bp(name, folder)
        put(bp, 'Blade', 'sword_knight', SW, shadow=False if name == 'BP_GW_FPItems' else True)
        hide(bp, 'Grip', 'Pommel', 'Guard', 'Tip')
        if name == 'BP_GW_FPItems':
            ensure_component(bp, 'SecretBlade', unreal.StaticMeshComponent, 'DefaultSceneRoot')
            # first person, low right, the tip (+Y in the GLB) forward and a little up
            c = put(bp, 'SecretBlade', 'hidden_blade', m2p('hidden_blade', rot=(12, 0, -90), target=(34, 14, -14), scale=size_scale('hidden_blade') * 0.8), shadow=False)
            c.set_editor_property('visible', False)
        finish(bp)

# ---- the rifle: origin at the grip, barrel +X, barrel line z = 5 (make_rifle); grip at local x = -19, barrel line at z = 5.2
RIFLE_M2P = m2p('rifle_old', anchor=(-19, -0.9, 5.2), target=(0, 0, 5))
if want('rifle'):
    gun = load_bp('BP_GW_GuestGun', SHOP)
    d = cdo(gun)
    cur = d.get_editor_property('RifleMesh')
    if cur != MESH['rifle_old'] or 'rifle_rel' not in state:
        t = d.get_editor_property('RifleRel')
        state['rifle_rel'] = [t.translation.x, t.translation.y, t.translation.z, t.rotation.x, t.rotation.y, t.rotation.z, t.rotation.w]
    b = state['rifle_rel']
    base = unreal.Transform(location=unreal.Vector(b[0], b[1], b[2]), rotation=unreal.Quat(b[3], b[4], b[5], b[6]).rotator(), scale=unreal.Vector(1, 1, 1))
    d.set_editor_property('RifleMesh', MESH['rifle_old'])
    d.set_editor_property('RifleRel', unreal.MathLibrary.compose_transforms(RIFLE_M2P, base))
    # the swap pistol, third person: same hand frame; its grip centre (x = -37.5) under the barrel line (z = 17)
    d.set_editor_property('SwapMesh', MESH['swap_pistol'])
    d.set_editor_property('SwapRel', unreal.MathLibrary.compose_transforms(m2p('swap_pistol', anchor=(-37.5, 0, 17), target=(0, 0, 5)), base))
    finish(gun)
    with open(STATE, 'w', encoding='utf-8') as fh:
        json.dump(state, fh, indent=1)

# ---- first person: the rifle takes the placeholder's pose (the hands of s37 stay on its grip and forend), the swap gun s37's own gun_pose
if want('view'):
    src = open(os.path.join(ROOT, 'Tools', 'gameplay', 's37_view.py'), encoding='utf-8').read()
    exec(re.search(r"^(GUN_HIP, GUN_ADS = .*?)$\n^(RIFLE_HIP, .*?)$", src, re.M | re.S).group(0))
    exec(re.search(r"^def gun_pose\(mesh\):.*?return hip, ads, muz_v$", src, re.M | re.S).group(0))
    ch = load_bp('BP_GW_Character')
    c = cdo(ch)
    guns = list(c.get_editor_property('FPGunMeshes'))
    hips = list(c.get_editor_property('FPGunHips'))
    adss = list(c.get_editor_property('FPGunAdss'))
    muzs = list(c.get_editor_property('FPGunMuzzles'))
    old = unreal.load_asset(f'{SHOP}/SM_GW_Rifle')
    i0 = guns.index(old)

    def entry(mesh, h, a, m):
        if mesh in guns:
            i = guns.index(mesh)
            hips[i], adss[i], muzs[i] = h, a, m
        else:
            guns.append(mesh); hips.append(h); adss.append(a); muzs.append(m)
    # the placeholder's muzzle, in the model's space
    p = unreal.MathLibrary.inverse_transform_location(RIFLE_M2P, muzs[i0])
    lo, hi = extents(MESH['rifle_old'])
    entry(MESH['rifle_old'], unreal.MathLibrary.compose_transforms(RIFLE_M2P, hips[i0]), unreal.MathLibrary.compose_transforms(RIFLE_M2P, adss[i0]),
          unreal.Vector(hi[0] + 2.0, p.y, 5.3))
    entry(MESH['swap_pistol'], *gun_pose(MESH['swap_pistol']))
    c.set_editor_property('FPGunMeshes', guns)
    c.set_editor_property('FPGunHips', hips)
    c.set_editor_property('FPGunAdss', adss)
    c.set_editor_property('FPGunMuzzles', muzs)
    c.set_editor_property('RifleMesh', MESH['rifle_old'])
    lock('/Game/GW/Blueprints/BP_GW_Character', True)
    save(ch)
    lock('/Game/GW/Blueprints/BP_GW_Character', False)
    print('  FP guns', [g.get_name() for g in guns])
    drv = load_bp('BP_GW_ViewDriver', '/Game/GW/Blueprints/Turret')
    ensure_var(drv, 'SwapMesh', obj_class=unreal.StaticMesh, category='View')
    compile_bp(drv, quiet=True)
    cdo(drv).set_editor_property('SwapMesh', MESH['swap_pistol'])
    ISVALID = 'GW|Call|/Script/Engine.KismetSystemLibrary|IsValid'
    VG = lambda n: f'(Variables|View|Get{n})'
    code = re.search(r"'PoseGun': f'''(.*?)''',", src, re.S).group(1)
    code = eval("f'''" + code + "'''")
    g = get_graph(drv, 'PoseGun')
    for node in list(BT.find_nodes(g)):
        if node.get_class().get_name() in ('K2Node_FunctionEntry', 'K2Node_FunctionResult'):
            for pin in node.list_all_pins():
                for other in list(pin.list_connected_pins()):
                    pin.break_single_pin_link(other)
            continue
        BT.delete_node(node)
    write(drv, 'PoseGun', code, compile_after=False)
    print('  driver', node_problems(drv))
    finish(drv)

# ---- thrown or placed by the shop's items. Pivot = centre of the model. Only the mesh of the part the graphs move changes.
if want('shop'):
    smoke = load_bp('BP_GW_SmokeBomb', SHOP)
    put(smoke, 'Can', 'smoke_grenade', m2p('smoke_grenade', target=(0, 0, 6)))
    hide(smoke, 'Cap')
    finish(smoke)

    gas = load_bp('BP_GW_GasPuff', SHOP)
    put(gas, 'Bottle', 'gas_canister', m2p('gas_canister', rot=(0, 90, 30), target=(30, 14, 5)))
    hide(gas, 'Cap')
    finish(gas)

    # the trap hangs under a lintel or sits 8 cm above the floor (PlaceTrap): the model's bottom ends up on the floor
    trap = load_bp('BP_GW_Trap', SHOP)
    put(trap, 'Body', 'door_trap', m2p('door_trap', target=(0, 0, -5.5)))
    hide(trap, 'Plate', 'Wire')
    rel(trap, 'Led', loc=(7.5, 3.5, -2.8), scale=(0.02, 0.02, 0.02))
    rel(trap, 'LedLight', loc=(7.5, 3.5, -6))
    finish(trap)

    # the bomb stands on the floor, its clock towards +X; the moving hand and the LED stay as simple parts on the model's clock
    BOMB_XF = m2p('time_bomb', rot=(0, 0, -90), target=(0, 0, 15))
    bomb = load_bp('BP_GW_Bomb', SHOP)
    put(bomb, 'Stick0', 'time_bomb', BOMB_XF)
    hide(bomb, 'Stick1', 'Stick2', 'Stick3', 'Stick4', 'Strap0', 'Strap1', 'Clock', 'Face', 'Bell0', 'Bell1', 'WireR', 'WireB')
    rel(bomb, 'HandPivot', loc=(5.9, -1.65, 16.8))
    rel(bomb, 'Led', loc=(4.6, -3.5, 7), scale=(0.022, 0.022, 0.022))
    finish(bomb)

    drop = load_bp('BP_GW_BombDrop', SHOP)
    put(drop, 'Stick0', 'time_bomb', BOMB_XF)
    hide(drop, 'Stick1', 'Stick2', 'Clock')
    finish(drop)

    # the chest: bottom on the floor, front +Y. One mesh, so the lid does not open: Lid is hidden (LidPivot still turns, harmlessly); the box
    # still answers with its sign, its glow and the jingle. (A thin plate on LidPivot was tried: Roll +70 sends it down into the chest.)
    bx = load_bp('BP_GW_MysteryBox', SHOP)
    put(bx, 'Chest', 'mystery_box', m2p('mystery_box', target=(0, 0, 28.2)))
    hide(bx, 'Band', 'Lid')
    finish(bx)

# ---- items on the floor (Q): every item id, lying on its long side, bottom on the floor
if want('drops'):
    from math import inf
    dr = load_bp('BP_GW_ItemDrop', SHOP)
    AT_B = '/Engine/BasicShapes/'

    def lay(mesh, s, rot):
        b = mesh.get_bounding_box()
        r = unreal.Rotator(roll=rot[0], pitch=rot[1], yaw=rot[2])
        q = r.quaternion()
        zs = [q.rotate_vector(unreal.Vector(x * s, y * s, z * s)).z for x in (b.min.x, b.max.x) for y in (b.min.y, b.max.y) for z in (b.min.z, b.max.z)]
        return unreal.Transform(location=unreal.Vector(0, 0, 1.0 - min(zs)), rotation=r, scale=unreal.Vector(s, s, s))

    TBL = {1: ('rifle_old', (0, 0, 0)), 2: ('smoke_grenade', (0, 90, 0)), 4: ('gas_canister', (0, 0, 0)), 5: ('door_trap', (0, 0, 0)), 6: ('time_bomb', (0, 0, 0)),
           8: ('swap_pistol', (90, 0, 0)), 10: ('hidden_blade', (0, 0, 0)), 12: ('sword_knight', (0, 90, 0))}
    meshes, mats, xfs = [None] * 14, [None] * 14, [unreal.Transform()] * 14
    for i_, (n_, rot_) in TBL.items():
        meshes[i_] = MESH[n_]
        xfs[i_] = lay(MESH[n_], size_scale(n_), rot_)
    # no approved model: the shapes of the thrown versions
    for i_, sh, mi_, s_, rot_ in ((3, 'Cylinder', 'MI_GW_Brass', (0.05, 0.05, 0.2), (90, 0, 0)), (9, 'Cylinder', 'MI_GW_Leather_Oxblood', (0.04, 0.04, 0.16), (90, 0, 0)), (11, 'Sphere', 'MI_GW_Leather_Oxblood', (0.06, 0.06, 0.06), (0, 0, 0))):
        meshes[i_] = unreal.load_asset(AT_B + sh)
        mats[i_] = unreal.load_asset('/Game/GW/Materials/' + mi_) if EAL.does_asset_exist('/Game/GW/Materials/' + mi_) else unreal.load_asset('/Game/GW/Materials/MI_GW_Brass')
        xfs[i_] = unreal.Transform(location=unreal.Vector(0, 0, 6), rotation=unreal.Rotator(roll=rot_[0], pitch=rot_[1], yaw=rot_[2]), scale=unreal.Vector(*s_))
    d = cdo(dr)
    d.set_editor_property('Meshes', meshes)
    d.set_editor_property('Mats', mats)
    d.set_editor_property('Xfs', xfs)
    finish(dr)
    # the ghost on the door: the trap's model where PlaceTrap would hang it, translucent green
    gh = load_bp('BP_GW_TrapGhost', SHOP)
    GHOSTMI = '/Game/GW/Materials/MI_GW_TrapGhost'
    gm_ = unreal.load_asset(GHOSTMI) if EAL.does_asset_exist(GHOSTMI) else tools.create_asset('MI_GW_TrapGhost', '/Game/GW/Materials', unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    mel.set_material_instance_parent(gm_, unreal.load_asset('/Game/GW/Materials/Master/M_GW_Beam'))
    mel.set_material_instance_vector_parameter_value(gm_, 'Color', unreal.LinearColor(0.1, 1.0, 0.25, 1))
    mel.set_material_instance_scalar_parameter_value(gm_, 'Strength', 12.0)
    mel.update_material_instance(gm_)
    EAL.save_loaded_asset(gm_, False)
    c_ = put(gh, 'Body', 'door_trap', m2p('door_trap', target=(0, 0, -5.5)), shadow=False)
    c_.set_editor_property('override_materials', [gm_])
    c2_ = unreal.SubobjectDataBlueprintFunctionLibrary.get_object(subobjects(gh)['Span'][1])
    c2_.set_editor_property('override_materials', [gm_])
    finish(gh)

# ---- the breaker: on a wall, the actor's +X comes out of the wall; a lever and the lamp stay as simple parts for OnRep_Thrown
if want('breaker'):
    br = load_bp('BP_GW_Breaker')
    put(br, 'Box', 'breaker_box', m2p('breaker_box', rot=(0, 0, -90), anchor=(0, -22.4, 0), target=(0, 0, 0)))
    rel(br, 'LeverRoot', loc=(25, -15, 8))
    rel(br, 'Lever', loc=(3, 0, 12))
    rel(br, 'Grip', loc=(3, 0, 25), scale=(0.04, 0.04, 0.04))
    rel(br, 'Lamp', loc=(26, 15, 28), scale=(0.03, 0.03, 0.03))
    finish(br)

# ---- the tray of the waiter: on the Tray component of BP_GW_Barman, a little higher so its floor meets the glasses' bottoms
if want('tray'):
    bm = load_bp('BP_GW_Barman', SHOP)
    put(bm, 'Tray', 'serving_tray', m2p('serving_tray', target=(-28, 24, 115)), shadow=False)
    finish(bm)
    w = load_bp('BP_GW_Waiter', SHOP)
    cdo(w).set_editor_property('TrayMesh', MESH['serving_tray'])
    finish(w)

# ---- the turret: one mesh, muzzle towards -X, the barrel rising 18 degrees towards the muzzle. It sits on Cradle (yaw and pitch), barrel
# level, the bore line through the pivot's axis as before (z = 1). The pedestal and tripod stay as the static base. The muzzle point,
# flash and light (read by the graphs through their components) move to the model's muzzle.
if want('turret'):
    tur = load_bp('BP_GW_Turret', '/Game/GW/Blueprints/Turret')
    TUR_PITCH = 18.0
    xf = m2p('turret_mg', rot=(0, TUR_PITCH, 180), anchor=(0, 0, 10), target=(0, 0, 1))
    put(tur, 'Receiver', 'turret_mg', xf)
    hide(tur, 'Yoke', 'Jacket', 'Ring0', 'Ring1', 'Ring2', 'Barrel', 'Hider', 'Grip0', 'Grip1', 'Trigger', 'AmmoBox', 'Belt', 'SightF', 'SightR')
    tip = unreal.MathLibrary.transform_location(xf, unreal.Vector(-50, 0, 26))
    print('  turret muzzle at', tip)
    rel(tur, 'MuzzlePoint', loc=(tip.x, 0, 1))
    rel(tur, 'MuzzleFlash', loc=(tip.x + 9, 0, 1))
    rel(tur, 'MuzzleLight', loc=(tip.x + 4, 0, 4))
    finish(tur)

# ---- one graph each, rendered from its owner's text (a full re-run of s40_events2 gm reloads the level, of s40_inventory pc rewrites the whole PC)
def rewrite(bp, name, code):
    g = get_graph(bp, name)
    for node in list(BT.find_nodes(g)):
        if node.get_class().get_name() in ('K2Node_FunctionEntry', 'K2Node_FunctionResult'):
            for pin in node.list_all_pins():
                for other in list(pin.list_connected_pins()):
                    pin.break_single_pin_link(other)
            continue
        BT.delete_node(node)
    write(bp, name, code, compile_after=False)
    print(' ', bp.get_name(), name, [p for p in node_problems(bp) if name in p])


if 'zombify' in ARGS:          # BP_GW_GameMode.Zombify from s40_events2.py
    src = open(os.path.join(ROOT, 'Tools', 'gameplay', 's40_events2.py'), encoding='utf-8').read()
    exec(re.search(r"^CHAR = .*?^ZOMBIE_MAX = \d+$", src, re.M | re.S).group(0))
    gm = load_bp('BP_GW_GameMode')
    rewrite(gm, 'Zombify', eval("f'''" + re.search(r"'Zombify': f'''(.*?)''',", src, re.S).group(1) + "'''"))
    src38 = open(os.path.join(ROOT, 'Tools', 'gameplay', 's38_pickups.py'), encoding='utf-8').read()
    SWAP_RELOAD = re.search(r"^BALL_BACK, SWORD_BACK, SWAP_RELOAD = .*, ([\d.]+)", src38, re.M).group(1)
    rewrite(gm, 'SwapStart', eval("f'''" + re.search(r"'SwapStart': f'''(.*?)''',", src38, re.S).group(1) + "'''"))
    finish(gm)

if 'die' in ARGS:              # BP_GW_Character.Die from s11_character.py
    src = open(os.path.join(ROOT, 'Tools', 'gameplay', 's11_character.py'), encoding='utf-8').read()
    ch = load_bp('BP_GW_Character')
    rewrite(ch, 'Die', re.search(r"W\['Die'\] = '''(.*?)'''", src, re.S).group(1))
    finish(ch)

if 'fpitems' in ARGS:          # BP_GW_PlayerController.FPItemsTick from s40_pc.py
    src = open(os.path.join(ROOT, 'Tools', 'gameplay', 's40_pc.py'), encoding='utf-8').read()
    ISVALID = 'GW|Call|/Script/Engine.KismetSystemLibrary|IsValid'
    MYCH = '(Utilities|Casting|CastToBP_GW_Character (Pawn|GetControlledPawn :self self))'
    FPC = f'{PICK}/BP_GW_FPItems.BP_GW_FPItems_C'
    HS = f'{PICK}/BP_GW_HeldSword.BP_GW_HeldSword_C'
    pc = load_bp('BP_GW_PlayerController')
    rewrite(pc, 'FPItemsTick', eval("f'''" + re.search(r"C\['FPItemsTick'\] = f'''(.*?)'''", src, re.S).group(1) + "'''"))
    finish(pc)

print('s41 done')
