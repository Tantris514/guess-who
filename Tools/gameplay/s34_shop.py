"""Shop and economy: the barman behind the billiard-room bar sells items to the guests, who earn money by playing.

Barman: BP_GW_Barman (Shop folder), a Character with the UE mannequin (white shirt, black trousers, apron, bow tie);
no AI, spawned once by the server (ShopTick) behind the bar, on the floor (traced), facing the room; he turns his head
toward the nearest player. His skin is the class default `Skin` (SkeletalMesh): the assets pipeline sets it when the
generated barman exists (manifest "outfits": "barman"), and the apron / bow tie placeholders then hide.

Money: BP_GW_PlayerState.Money (replicated). Earned on the server: an instrument +25 $ (once / 30 s, OnInstrumentPlayed,
called by s33), NPC killed by a guest +100 $ (RewardNPCKill: also a loud positional scream, BP_GW_LoudCue + ATT_GW_Far),
door trap on a detective +50 $, detective shot by a guest +100 $, every 30 s of hunt alive +5 $. Kept across rounds.
Items (PlayerState counts, replicated): 1 Fusil 150 $ (1 bullet, left click: GuestFire -> GuestShoot; the revolver
shows in the hand, BP_GW_GuestGun), 2 Bombe fumigène 40 $ (G), 3 Lampe torche 20 $ (F, local BP_GW_HandLamp),
4 Gaz rétrécissant 60 $ (H, BP_GW_GasPuff + BP_GW_Shrink: x0.3 size, x1.7 speed, 20 s), 5 Piège de porte 80 $ (T in
a doorway, BP_GW_Trap on the lintel, BP_GW_SmallBlast on a detective: -25 PV), 6 Bombe 120 $ (B, BP_GW_Bomb: beeps,
explodes after 45 s, 9 m, BP_GW_BigBlast; a detective defuses it with E, BP_GW_DefuseFX), 7 Munitions de tourelle
80 $ (+60 TurretAmmo, used by s35), 8 Pistolet d'échange 200 $ (HasSwapGun / SwapReadyAt; the swap itself: pickups
agent). Purchases: "GWBuy <id>" (host direct, client ServerExec), checked on the server (guest, alive, near the bar).
Use: "GWUseItem <id> <yaw>". Defuse: "GWDefuse". Hooks bodies: ShopTick / RewardNPCKill (game mode), ShopClientTick /
TryShop / TryDefuse (player controller). GuestAttack (left click without bullets) is only declared here.
Dev (F2 -> Boutique, u15): GWDevMoney, GWDevGive, GWDevShopHere, GWDevBombNow, GWDevShopAim. -GWShopTest runs
ShopTestTick (a scripted sequence, one step every 2 s, "GW shoptest" lines).
Usage: ue_run.py s34_shop.py  (sounds: Tools/audio/synth_shop.py first; widget: Tools/ui/u17_shop_ui.py, then this
again if WBP_Shop did not exist; then u14_hud.py and u15_dev_menu.py)
"""
import sys, importlib, os, math, random, json
sys.path.insert(0, r'J:\Projets\Unreal_Projects\Guess Who\Tools\gameplay')
import gw_lib; importlib.reload(gw_lib)
from gw_lib import *

REP = unreal.BlueprintVariableReplication
V3 = unreal.Vector.static_struct()
MEL = unreal.MaterialEditingLibrary
MP = unreal.MaterialProperty
AT = unreal.AssetToolsHelpers.get_asset_tools()
SHOP = '/Game/GW/Blueprints/Shop'
# UE_ARGS: nothing = everything; else any of  mat (materials)  fx (effect actors)  vendors (barman, junkie, waiter)
# ps  gm  pc  or a Blueprint name. Only the chosen Blueprints are rewritten, compiled and saved (the shared editor is
# slow: a partial run keeps the locks short); existing materials are reused unless 'mat' is chosen.
PARTS = set(UE_ARGS)
_ALIAS = {'pc': 'BP_GW_PlayerController', 'gm': 'BP_GW_GameMode', 'ps': 'BP_GW_PlayerState'}
_FX = {'BP_GW_LoudCue', 'BP_GW_GuestGun', 'BP_GW_SmokeBomb', 'BP_GW_Firecracker', 'BP_GW_GasPuff', 'BP_GW_Shrink', 'BP_GW_Trap',
       'BP_GW_Bomb', 'BP_GW_BigBlast', 'BP_GW_SmallBlast', 'BP_GW_DefuseFX', 'BP_GW_HandLamp'}
_VENDORS = {'BP_GW_Barman', 'BP_GW_Junkie', 'BP_GW_Waiter'}


def want(part):
    return (not PARTS or part in PARTS or (part == 'fx' and bool(PARTS & _FX))
            or (part == 'vendors' and bool(PARTS & _VENDORS)))


def selected(bp):
    if not PARTS:
        return True
    n = bp.get_name()
    return (n in PARTS or any(_ALIAS.get(x) == n for x in PARTS) or ('fx' in PARTS and n in _FX)
            or ('vendors' in PARTS and n in _VENDORS))


_compile_bp, _save = compile_bp, save


def compile_bp(bp, quiet=False):
    return _compile_bp(bp, quiet) if selected(bp) else True


def save(*assets):
    """Save and verify (a -game test holding the .uasset makes a save fail silently)."""
    import time
    for a in assets:
        if isinstance(a, unreal.Blueprint) and not selected(a):
            continue
        ok = False
        for _ in range(4):
            ok = EAL.save_loaded_asset(a, only_if_is_dirty=False)
            if ok:
                break
            time.sleep(2.0)
        if not ok:
            print('!!! SAVE FAILED', a.get_path_name())


def reuse(path):
    """An existing asset to keep as is in a partial run."""
    return PARTS and 'mat' not in PARTS and EAL.does_asset_exist(path)
ISVALID = 'GW|Call|/Script/Engine.KismetSystemLibrary|IsValid'
GSC = '(Utilities|Casting|CastToBP_GW_GameState (Game|GetGameState))'
GMC = '(Utilities|Casting|CastToBP_GW_GameMode (Game|GetGameMode))'
PSC = '(Utilities|Casting|CastToBP_GW_PlayerState (GW|Get|/Script/Engine.Controller|PlayerState))'
MYCH = '(Utilities|Casting|CastToBP_GW_Character (Pawn|GetControlledPawn :self self))'
CHAR = '"/Game/GW/Blueprints/BP_GW_Character.BP_GW_Character_C"'
HUD = '/Game/GW/UI/WBP_HUD.WBP_HUD_C'
STIME = '(GameState|GetServerWorldTimeSeconds :self (Game|GetGameState))'
SYN = r'J:\Projets\Unreal_Projects\Guess Who\AssetGen\audio\final\synth'
GEN = '/Game/GW/Audio/Gen'
LAYOUT = r'J:\Projets\Unreal_Projects\Guess Who\Tools\manor_layout.json'
LOUD, GUN, SMOKE, GAS, SHRINK, TRAP, BOMB = (f'{SHOP}/{n}.{n}_C' for n in ('BP_GW_LoudCue', 'BP_GW_GuestGun', 'BP_GW_SmokeBomb', 'BP_GW_GasPuff', 'BP_GW_Shrink', 'BP_GW_Trap', 'BP_GW_Bomb'))
BIG, SMALL, DFX, BARMAN, LAMPC = (f'{SHOP}/{n}.{n}_C' for n in ('BP_GW_BigBlast', 'BP_GW_SmallBlast', 'BP_GW_DefuseFX', 'BP_GW_Barman', 'BP_GW_HandLamp'))
BAR = (4420.0, 1690.0)                 # between the counter (y 1558..1634) and the back bar (y 1738..1783)
BOMB_R, BOMB_T, TRAP_Z = 900.0, 45.0, 262.0
import shop_items; importlib.reload(shop_items)
ITEMS = shop_items.ITEMS                 # id, name, description, barman price, junkie price, key, hint
HINT = {i[0]: i[6] for i in ITEMS}
NITEMS = len(ITEMS)
JUNKIE, WAITER, CRACKER = (f'{SHOP}/{n}.{n}_C' for n in ('BP_GW_Junkie', 'BP_GW_Waiter', 'BP_GW_Firecracker'))
WAITER2 = f'{SHOP}/BP_GW_Waiter2.BP_GW_Waiter2_C'   # same class, other skin: Tools/chars/make_waiter2.py
DANCE = (2600.0, 3400.0, 2900.0, 3760.0)  # the ballroom dance floor (social agent): waiters don't stop there


def cp(name):
    return f'{SHOP}/{name}.{name}_C'


def ap(path):
    """Asset path -> quoted object path for a DSL pin."""
    return f'"{path}.{path.rsplit("/", 1)[1]}"'


def unbalanced(code):
    depth, quoted = 0, False
    for c in code:
        if c == '"':
            quoted = not quoted
        elif not quoted:
            depth += (c == '(') - (c == ')')
            if depth < 0:
                return depth
    return depth


def clean_graph(bp, graph_name):
    """Empty a graph before a rewrite (the transpiler keeps old nodes wired to the entry's parameter pins)."""
    g = get_graph(bp, graph_name)
    if g is None:
        return
    for node in list(BT.find_nodes(g)):
        if node.get_class().get_name() in ('K2Node_FunctionEntry', 'K2Node_FunctionResult'):
            for p in node.list_all_pins():
                for c in list(p.list_connected_pins()):
                    p.break_single_pin_link(c)
            continue
        BT.delete_node(node)


def wr(bp, name, code):
    if not selected(bp):
        return
    assert unbalanced(code) == 0, f'unbalanced DSL in {bp.get_name()}.{name}: {unbalanced(code)}'
    clean_graph(bp, name)
    write(bp, name, code, compile_after=False)


def local(bp, fn, name, typ=None, obj=None):
    g = get_graph(bp, fn)
    if name in BT.list_variables(bp, g):
        return
    if obj is not None:
        BT.add_object_variable(bp, name, obj, graph=g)
    else:
        BT.add_variable(bp, name, typ, graph=g)


def sel(var, mapping, default):
    e = default
    for k, v in reversed(list(mapping.items())):
        e = f'(select (== {var} {k}) {v} {e})'
    return e


def q(s):
    return '"' + s.replace('"', "'") + '"'


def mv(x, y, z):
    return f'(Math|Vector|MakeVector {float(x)} {float(y)} {float(z)})'


# ================================================================ sounds (Tools/audio/synth_shop.py)
def fresh_import(path, folder, name):
    """Same convention as s31_reactions.py: re-import only when the WAV changed (GWSrcStamp)."""
    dest = f'{folder}/{name}'
    stamp = f'{os.path.getsize(path)}|{int(os.path.getmtime(path))}'
    if EAL.does_asset_exist(dest) and EAL.get_metadata_tag(unreal.load_asset(dest), 'GWSrcStamp') == stamp:
        return unreal.load_asset(dest)
    t = unreal.AssetImportTask()
    t.filename = path; t.destination_path = folder; t.automated = True; t.replace_existing = True; t.save = False
    AT.import_asset_tasks([t])
    s = unreal.load_asset(dest)
    EAL.set_metadata_tag(s, 'GWSrcStamp', stamp)
    return s


SND = {}
for stem, cat in (('SFX_Shop_Buy', 'shop_buy'), ('SFX_Shop_Coins', 'shop_buy'), ('SFX_Smoke_Hiss', 'smoke_hiss'),
                  ('SFX_Gas_Hiss', 'gas_hiss'), ('SFX_Bomb_Beep', 'bomb_beep'), ('SFX_Defuse', 'defuse'),
                  ('SFX_Trap_Click', 'trap_click')):
    s = fresh_import(os.path.join(SYN, stem + '.wav'), f'{GEN}/{cat}', stem)
    s.set_editor_property('sound_class_object', unreal.load_asset('/Game/GW/Audio/Classes/SC_GW_SFX'))
    EAL.save_loaded_asset(s, False)
    SND[stem] = ap(f'{GEN}/{cat}/{stem}')
_ar = unreal.AssetRegistryHelpers.get_asset_registry()
_booms = sorted(str(d.package_name) for d in _ar.get_assets_by_path(f'{GEN}/explosion', recursive=True))
BOOM = ap(_booms[0]) if _booms else ap('/Game/GW/Audio/S_GW_Thud')
print('sounds', len(SND), 'boom', BOOM)


def attenuation(name, inner, falloff):
    p = f'{SHOP}/{name}'
    if reuse(p):
        return ap(p)
    a = unreal.load_asset(p) if EAL.does_asset_exist(p) else AT.create_asset(name, SHOP, unreal.SoundAttenuation, unreal.SoundAttenuationFactory())
    st = a.get_editor_property('attenuation')
    st.set_editor_property('attenuation_shape_extents', unreal.Vector(inner, 0, 0))
    st.set_editor_property('falloff_distance', falloff)
    a.set_editor_property('attenuation', st)
    EAL.save_loaded_asset(a, False)
    return ap(p)


ATT_NEAR = attenuation('ATT_GW_ShopNear', 300.0, 2200.0)     # hiss, defuse: a room and a bit
ATT_BEEP = attenuation('ATT_GW_BombBeep', 400.0, 3200.0)     # the bomb: found by ear from two rooms away
ATT_QUIET = attenuation('ATT_GW_ShopQuiet', 80.0, 700.0)     # trap set: discreet
ATT_FAR = ap('/Game/GW/Audio/ATT_GW_Far')                    # screams, explosions: the whole manor, louder near

# ================================================================ materials (Shop folder)
F1 = unreal.CustomMaterialOutputType.CMOT_FLOAT1
F3 = unreal.CustomMaterialOutputType.CMOT_FLOAT3


def fresh_mat(name):
    p = f'{SHOP}/{name}'
    if EAL.does_asset_exist(p):
        m = unreal.load_asset(p)
        MEL.delete_all_material_expressions(m)
        return m
    return AT.create_asset(name, SHOP, unreal.Material, unreal.MaterialFactoryNew())


def mexpr(m, cls, x, y, **props):
    e = MEL.create_material_expression(m, cls, x, y)
    for k, v in props.items():
        e.set_editor_property(k, v)
    return e


def mcustom(m, code, inputs, out, x=-400, y=0):
    e = mexpr(m, unreal.MaterialExpressionCustom, x, y, code=code, output_type=out, description='GW')
    ins = []
    for n in inputs:
        ci = unreal.CustomInput()
        ci.set_editor_property('input_name', n)
        ins.append(ci)
    e.set_editor_property('inputs', ins)
    return e


SOFT_INPUTS = ['N', 'V', 'P', 'T']
SMOKE_HLSL = '''float f = abs(dot(normalize(N), normalize(V)));
float e = pow(saturate(f), Soft);
float3 q = P * 0.011 + float3(0.0, 0.0, -T * 0.18);
float n = sin(q.x * 1.7 + sin(q.y * 1.3 + T * 0.21)) * sin(q.y * 1.9 + sin(q.z * 1.1 - T * 0.17)) * sin(q.z * 1.5 + sin(q.x * 0.9));
n = 0.72 + 0.28 * n;
return saturate(Op * e * n);'''
FIRE_HLSL = '''float f = abs(dot(normalize(N), normalize(V)));
float e = pow(saturate(f), Soft);
float3 q = P * 0.02 + float3(0.0, 0.0, -T * 1.4);
float n = 0.65 + 0.35 * sin(q.x * 2.1 + sin(q.y * 1.7 + T * 3.1)) * sin(q.y * 2.3 + sin(q.z * 1.9 - T * 2.3)) * sin(q.z * 1.6 + T * 1.7);
float3 hot = lerp(Color.rgb, float3(1.0, 0.92, 0.7), e * e);
return hot * Strength * e * n;'''


def soft_mat(name, hlsl, additive):
    if reuse(f'{SHOP}/{name}'):
        return unreal.load_asset(f'{SHOP}/{name}')
    m = fresh_mat(name)
    m.set_editor_property('blend_mode', unreal.BlendMode.BLEND_ADDITIVE if additive else unreal.BlendMode.BLEND_TRANSLUCENT)
    m.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_UNLIT if additive else unreal.MaterialShadingModel.MSM_DEFAULT_LIT)
    m.set_editor_property('two_sided', True)
    srcs = [mexpr(m, unreal.MaterialExpressionVertexNormalWS, -900, 0), mexpr(m, unreal.MaterialExpressionCameraVectorWS, -900, 100),
            mexpr(m, unreal.MaterialExpressionWorldPosition, -900, 200), mexpr(m, unreal.MaterialExpressionTime, -900, 300)]
    soft = mexpr(m, unreal.MaterialExpressionScalarParameter, -900, 400, parameter_name='Soft', default_value=1.4)
    col = mexpr(m, unreal.MaterialExpressionVectorParameter, -900, 500, parameter_name='Color', default_value=unreal.LinearColor(0.4, 0.4, 0.4, 1))
    if additive:
        stren = mexpr(m, unreal.MaterialExpressionScalarParameter, -900, 600, parameter_name='Strength', default_value=20.0)
        c = mcustom(m, hlsl, SOFT_INPUTS + ['Soft', 'Color', 'Strength'], F3)
        for s, pin in zip(srcs + [soft, col, stren], SOFT_INPUTS + ['Soft', 'Color', 'Strength']):
            MEL.connect_material_expressions(s, '', c, pin)
        MEL.connect_material_property(c, '', MP.MP_EMISSIVE_COLOR)
    else:
        op = mexpr(m, unreal.MaterialExpressionScalarParameter, -900, 600, parameter_name='Opacity', default_value=0.9)
        c = mcustom(m, hlsl, SOFT_INPUTS + ['Soft', 'Op'], F1)
        for s, pin in zip(srcs + [soft, op], SOFT_INPUTS + ['Soft', 'Op']):
            MEL.connect_material_expressions(s, '', c, pin)
        MEL.connect_material_property(c, '', MP.MP_OPACITY)
        MEL.connect_material_property(col, '', MP.MP_BASE_COLOR)
        em = mexpr(m, unreal.MaterialExpressionVectorParameter, -900, 700, parameter_name='Emissive', default_value=unreal.LinearColor(0, 0, 0, 1))
        MEL.connect_material_property(em, '', MP.MP_EMISSIVE_COLOR)
        MEL.connect_material_property(mexpr(m, unreal.MaterialExpressionConstant, -900, 800, r=1.0), '', MP.MP_ROUGHNESS)
    MEL.layout_material_expressions(m)
    MEL.recompile_material(m)
    EAL.save_loaded_asset(m, False)
    return m


def mic(name, parent, vec=None, scal=None):
    p = f'{SHOP}/{name}'
    if reuse(p):
        return unreal.load_asset(p)
    m = unreal.load_asset(p) if EAL.does_asset_exist(p) else AT.create_asset(name, SHOP, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    MEL.set_material_instance_parent(m, parent if isinstance(parent, unreal.MaterialInterface) else unreal.load_asset(parent))
    for k, v in (vec or {}).items():
        MEL.set_material_instance_vector_parameter_value(m, k, unreal.LinearColor(v[0], v[1], v[2], 1))
    for k, v in (scal or {}).items():
        MEL.set_material_instance_scalar_parameter_value(m, k, v)
    MEL.update_material_instance(m)
    EAL.save_loaded_asset(m, False)
    return m


M_SMOKE = soft_mat('M_GW_ShopSmoke', SMOKE_HLSL, False)
M_FIRE = soft_mat('M_GW_ShopFire', FIRE_HLSL, True)
METAL = '/Game/GW/Materials/Master/M_GW_Metal'
EMI = '/Game/GW/Materials/Master/M_GW_Emissive'
MI = {
    'smoke': mic('MI_GW_ShopSmoke', M_SMOKE, {'Color': (0.42, 0.42, 0.41)}, {'Opacity': 0.93, 'Soft': 1.25}),
    'gas': mic('MI_GW_GasCloud', M_SMOKE, {'Color': (0.16, 0.55, 0.1), 'Emissive': (0.015, 0.07, 0.01)}, {'Opacity': 0.72, 'Soft': 1.6}),
    'bsmoke': mic('MI_GW_BlastSmoke', M_SMOKE, {'Color': (0.05, 0.045, 0.04)}, {'Opacity': 0.85, 'Soft': 1.3}),
    'shock': mic('MI_GW_Shockwave', M_SMOKE, {'Color': (0.7, 0.66, 0.58)}, {'Opacity': 0.45, 'Soft': 0.7}),
    'scorch': mic('MI_GW_Scorch', M_SMOKE, {'Color': (0.01, 0.008, 0.006)}, {'Opacity': 0.9, 'Soft': 0.45}),
    'fire': mic('MI_GW_Fireball', M_FIRE, {'Color': (1.0, 0.36, 0.05)}, {'Strength': 25.0, 'Soft': 1.1}),
    'spark': mic('MI_GW_DefuseSpark', EMI, {'Color': (0.55, 0.78, 1.0)}, {'Strength': 45.0}),
    'led': mic('MI_GW_LedRed', EMI, {'Color': (1.0, 0.05, 0.03)}, {'Strength': 30.0}),
    'wisp': mic('MI_GW_GasWisp', EMI, {'Color': (0.3, 1.0, 0.22)}, {'Strength': 10.0}),
    'dark': mic('MI_GW_ShopDarkMetal', METAL, {'Color': (0.035, 0.035, 0.04)}, {'Metallic': 0.75, 'Roughness': 0.42}),
    'olive': mic('MI_GW_ShopOlive', METAL, {'Color': (0.11, 0.13, 0.05)}, {'Metallic': 0.3, 'Roughness': 0.5}),
    'red': mic('MI_GW_ShopRedPaper', METAL, {'Color': (0.5, 0.04, 0.03)}, {'Metallic': 0.0, 'Roughness': 0.85}),
    'blue': mic('MI_GW_ShopBlueWire', METAL, {'Color': (0.03, 0.08, 0.45)}, {'Metallic': 0.0, 'Roughness': 0.6}),
    'tape': mic('MI_GW_ShopTape', METAL, {'Color': (0.018, 0.016, 0.014)}, {'Metallic': 0.0, 'Roughness': 0.9}),
    'brass': mic('MI_GW_ShopBrass', METAL, {'Color': (0.75, 0.55, 0.25)}, {'Metallic': 1.0, 'Roughness': 0.3}),
    'white': mic('MI_GW_ShopWhite', METAL, {'Color': (0.85, 0.82, 0.74)}, {'Metallic': 0.0, 'Roughness': 0.6}),
    'glass': mic('MI_GW_ShopGreenGlass', METAL, {'Color': (0.05, 0.32, 0.08)}, {'Metallic': 0.25, 'Roughness': 0.18}),
    'apron': mic('MI_GW_BarmanApron', METAL, {'Color': (0.88, 0.86, 0.8)}, {'Metallic': 0.0, 'Roughness': 0.9}),
    'silk': mic('MI_GW_BarmanBowTie', METAL, {'Color': (0.01, 0.01, 0.012)}, {'Metallic': 0.0, 'Roughness': 0.35}),
    'tweed': mic('MI_GW_JunkieCap', METAL, {'Color': (0.17, 0.14, 0.1)}, {'Metallic': 0.0, 'Roughness': 0.95}),
    'silver': mic('MI_GW_WaiterTray', METAL, {'Color': (0.8, 0.8, 0.82)}, {'Metallic': 1.0, 'Roughness': 0.22}),
    'champ': mic('MI_GW_Champagne', METAL, {'Color': (0.95, 0.78, 0.38)}, {'Metallic': 0.3, 'Roughness': 0.1}),
    'fuse': mic('MI_GW_FuseSpark', EMI, {'Color': (1.0, 0.6, 0.15)}, {'Strength': 60.0}),
}
MIP = {k: ap(m.get_path_name().split('.')[0]) for k, m in MI.items()}
SPHERE, CUBE, CYL = '/Engine/BasicShapes/Sphere', '/Engine/BasicShapes/Cube', '/Engine/BasicShapes/Cylinder'

# ================================================================ classes
chc = load_bp('BP_GW_Character').generated_class()
chcdo = cdo(load_bp('BP_GW_Character'))
kp = load_bp('BP_GW_KeyPrompt')
psb = load_bp('BP_GW_PlayerState')


def actor_bp(name, life=0.0, replicated=True):
    bp = load_or_create_bp(name, unreal.Actor, folder=SHOP)
    compile_bp(bp, quiet=True)
    d = cdo(bp)
    d.set_editor_property('replicates', replicated)
    d.set_editor_property('always_relevant', replicated)
    if replicated:
        d.set_editor_property('replicate_movement', False)
    d.set_editor_property('initial_life_span', life)
    return bp


def mesh(bp, name, asset, mi, loc=(0, 0, 0), rot=(0, 0, 0), scale=(1, 1, 1), parent='DefaultSceneRoot', visible=True):
    c = ensure_component(bp, name, unreal.StaticMeshComponent, parent)
    c.set_editor_property('static_mesh', unreal.load_asset(asset))
    c.set_editor_property('override_materials', [MI[mi]])
    c.set_editor_property('relative_location', unreal.Vector(*loc))
    c.set_editor_property('relative_rotation', unreal.Rotator(roll=rot[0], pitch=rot[1], yaw=rot[2]))
    c.set_editor_property('relative_scale3d', unreal.Vector(*scale))
    c.set_editor_property('cast_shadow', False)
    c.set_editor_property('visible', visible)
    c.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
    return c


def light(bp, name, color, intensity, radius, loc=(0, 0, 0), parent='DefaultSceneRoot'):
    c = ensure_component(bp, name, unreal.PointLightComponent, parent)
    c.set_editor_property('light_color', unreal.Color(r=color[0], g=color[1], b=color[2], a=color[3]))
    c.set_editor_property('intensity', intensity)
    c.set_editor_property('attenuation_radius', radius)
    c.set_editor_property('relative_location', unreal.Vector(*loc))
    c.set_editor_property('cast_shadows', False)
    return c


def fxvars(bp, floats=('T0', 'Age', 'G', 'Fade'), bools=(), mids=()):
    for v in floats:
        ensure_var(bp, v, 'float', category='FX')
    for v in bools:
        ensure_var(bp, v, 'bool', category='FX')
    for v in mids:
        ensure_var(bp, v, obj_class=unreal.MaterialInstanceDynamic, category='FX')


def add_ease(bp):
    ensure_fn(bp, 'Ease', inputs=[('V', 'float')], outputs=[('R', 'float')], pure=True)
    compile_bp(bp, quiet=True)
    wr(bp, 'Ease', '(fn Ease (V) (bind c (- 1.0 (Math|Float|Max(Float) 0.0 (Math|Float|Min(Float) V 1.0)))) (return (- 1.0 (* (* c c) c))))')


def finish(bp):
    if not selected(bp):
        return
    ok = compile_bp(bp)
    probs = node_problems(bp)
    print(bp.get_name(), 'OK' if ok else 'FAILED', probs[:6])
    save(bp)


AGE = '(Variables|FX|SetAge (- (Utilities|Time|GetGameTimeinSeconds) (Variables|FX|GetT0)))\n  (bind age (Variables|FX|GetAge))'


def mid_setup(first, others, mi, var='MID'):
    out = f'(Variables|FX|Set{var} (Rendering|Material|CreateDynamicMaterialInstance :self (Variables|Default|Get{first}) :ElementIndex 0 :SourceMaterial {MIP[mi]}))'
    for o in others:
        out += f'\n  (Rendering|Material|SetMaterial :self (Variables|Default|Get{o}) :ElementIndex 0 :Material (Variables|FX|Get{var}))'
    return out


def set_scalar(var, param, val):
    return f'(GW|Call|/Script/Engine.MaterialInstanceDynamic|SetScalarParameterValue :self (Variables|FX|Get{var}) :ParameterName "{param}" :Value {val})'


def rel_loc(comp, v):
    return f'(Transformation|SetRelativeLocation :self (Variables|Default|Get{comp}) :NewLocation {v} :bSweep false :bTeleport true)'


def rel_scale(comp, v):
    return f'(Transformation|SetRelativeScale3D :self (Variables|Default|Get{comp}) :NewScale3D {v})'


def uni(s):
    return f'(Math|Vector|MakeVector {s} {s} {s})'


if want('fx'):
    # ---------------------------------------------------------------- loud positional cue (screams)
    loud = actor_bp('BP_GW_LoudCue', life=20.0)
    ensure_var(loud, 'Vol', 'float', rep=REP.REPLICATED, category='FX')
    ensure_var(loud, 'Idx', 'int', rep=REP.REP_NOTIFY, category='FX')
    ensure_fn(loud, 'OnRep_Idx')
    compile_bp(loud, quiet=True)
    cdo(loud).set_editor_property('Vol', 2.2)
    wr(loud, 'OnRep_Idx', f'''
    (fn OnRep_Idx ()
      (bind s {GSC}
        (:then
          (bind snds (GW|Get|BP_GW_GameState|BankSounds :self s))
          (if (and (>= (Variables|FX|GetIdx) 0) (< (Variables|FX|GetIdx) (Utilities|Array|Length snds)))
            (Audio|PlaySoundatLocation :Sound (Utilities|Array|Get(acopy) snds (Variables|FX|GetIdx)) :Location (Transformation|GetActorLocation) :VolumeMultiplier (Variables|FX|GetVol) :AttenuationSettings {ATT_FAR})))
        (:CastFailed)))
    ''')
    finish(loud)

    # ---------------------------------------------------------------- the armed guest's revolver
    gun = actor_bp('BP_GW_GuestGun')
    gm_ = ensure_component(gun, 'Gun', unreal.StaticMeshComponent, 'DefaultSceneRoot')
    gm_.set_editor_property('static_mesh', chcdo.get_editor_property('RevolverMesh'))
    if chcdo.get_editor_property('GunMat'):
        gm_.set_editor_property('override_materials', [chcdo.get_editor_property('GunMat')])
    gm_.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
    gm_.set_editor_property('cast_shadow', False)
    ensure_var(gun, 'Holder', obj_class=chc, rep=REP.REP_NOTIFY, category='FX')
    ensure_var(gun, 'FitIdx', 'int', category='FX')
    ensure_fn(gun, 'OnRep_Holder')
    compile_bp(gun, quiet=True)
    wr(gun, 'OnRep_Holder', f'''
    (fn OnRep_Holder ()
      (bind h (Variables|FX|GetHolder))
      (if (not ({ISVALID} :Object h))
        (return))
      ; the holder's own fit for the revolver (FitMeshes / FitBones / FitRels, s25-s26: hand_r on the mannequin skeleton,
      ; which has no weapon_r); hand_r + GunRel when the revolver is not in the fit table
      (Components|StaticMesh|SetStaticMesh :self (Variables|Default|GetGun) :NewMesh (GW|Get|BP_GW_Character|RevolverMesh :self h))
      (Variables|FX|SetFitIdx (Utilities|Array|FindItem (GW|Get|BP_GW_Character|FitMeshes :self h) (GW|Get|BP_GW_Character|RevolverMesh :self h)))
      (bind m (GW|Get|/Script/Engine.Character|Mesh :self h))
      (if (>= (Variables|FX|GetFitIdx) 0)
        (Transformation|AttachActorToComponent :self self :Parent m :SocketName (Utilities|Array|Get(acopy) (GW|Get|BP_GW_Character|FitBones :self h) (Variables|FX|GetFitIdx)) :LocationRule "SnapToTarget" :RotationRule "SnapToTarget" :ScaleRule "SnapToTarget" :bWeldSimulatedBodies false)
        (Transformation|SetRelativeTransform :self (Variables|Default|GetGun) :NewTransform (Utilities|Array|Get(acopy) (GW|Get|BP_GW_Character|FitRels :self h) (Variables|FX|GetFitIdx)) :bSweep false :bTeleport true)
        (else
          (Transformation|AttachActorToComponent :self self :Parent m :SocketName "hand_r" :LocationRule "SnapToTarget" :RotationRule "SnapToTarget" :ScaleRule "SnapToTarget" :bWeldSimulatedBodies false)
          (Transformation|SetRelativeTransform :self (Variables|Default|GetGun) :NewTransform (GW|Get|BP_GW_Character|GunRel :self h) :bSweep false :bTeleport true)))
      (Development|PrintString :InString (cat "GW: guest gun on " (Utilities|GetDisplayName :Object h) " fit " (Variables|FX|GetFitIdx) " at " (Transformation|GetActorLocation)) :bPrintToScreen false))
    ''')
    finish(gun)

    # ---------------------------------------------------------------- smoke grenade: flies, lands, a thick cloud for 18 s
    rs = random.Random(34)
    N_SMOKE = 16
    smoke = actor_bp('BP_GW_SmokeBomb', life=24.0)
    mesh(smoke, 'Can', CYL, 'olive', loc=(0, 0, 6), scale=(0.07, 0.07, 0.13))
    mesh(smoke, 'Cap', CYL, 'dark', loc=(0, 0, 52), scale=(0.8, 0.8, 0.18), parent='Can')
    SP = []
    for k in range(N_SMOKE):
        a, r = rs.uniform(0, 2 * math.pi), (0 if k == 0 else rs.uniform(40, 230))
        SP.append((r * math.cos(a), r * math.sin(a), rs.uniform(45, 175), rs.uniform(1.8, 3.0), rs.uniform(1.5, 5.0), rs.uniform(0, 6.28), k * 0.11))
        mesh(smoke, f'P{k}', SPHERE, 'smoke', scale=(0.01, 0.01, 0.01), visible=False)
    ensure_var(smoke, 'From', struct=V3, rep=REP.REPLICATED, category='FX')
    fxvars(smoke, bools=('Landed',), mids=('MID',))
    add_ease(smoke)
    compile_bp(smoke, quiet=True)
    puffs = '\n'.join(f'''  (Variables|FX|SetG (CallFunction|Ease :V (/ (- sa {d:.2f}) 2.4)))
      {rel_loc(f"P{k}", f"(Math|Vector|MakeVector (* {x:.1f} (+ 0.35 (* 0.65 (Variables|FX|GetG)))) (* {y:.1f} (+ 0.35 (* 0.65 (Variables|FX|GetG)))) (+ (* {z:.1f} (+ 0.4 (* 0.6 (Variables|FX|GetG)))) (* {rise:.2f} sa)))")}
      {rel_scale(f"P{k}", f"(* (Math|Vector|MakeVector 1.0 1.0 0.85) (* {s:.2f} (* (+ 0.02 (* 0.98 (Variables|FX|GetG))) (+ 1.0 (* 0.06 (Math|Trig|Sin(Radians) (+ (* sa 0.7) {ph:.2f})))))))")}'''
                      for k, (x, y, z, s, rise, ph, d) in enumerate(SP))
    show = '\n'.join(f'    (Rendering|SetVisibility :self (Variables|Default|GetP{k}) :bNewVisibility true :bPropagateToChildren false)' for k in range(N_SMOKE))
    wr(smoke, 'EventGraph', f'''
    (event EventBeginPlay
      (Variables|FX|SetT0 (Utilities|Time|GetGameTimeinSeconds))
      {mid_setup('P0', [f'P{k}' for k in range(1, N_SMOKE)], 'smoke')})

    (event EventTick (DeltaSeconds)
      {AGE}
      (bind here (Transformation|GetActorLocation))
      (if (< age 0.6)
        ; a float bind feeding vector math gets re-typed by the promotable operators: keep it in a variable
        (Variables|FX|SetG (/ age 0.6))
        (bind a (Variables|FX|GetG))
        (bind from (Variables|FX|GetFrom))
        (Transformation|SetWorldLocation :self (Variables|Default|GetCan) :NewLocation (+ (+ from (* (- here from) a)) (Math|Vector|MakeVector 0.0 0.0 (+ 6.0 (* 170.0 (* a (- 1.0 a)))))) :bSweep false :bTeleport true)
        (Transformation|SetWorldRotation :self (Variables|Default|GetCan) :NewRotation (Math|Rotator|MakeRotator :Roll (* age 420.0) :Pitch (* age 760.0) :Yaw 0.0) :bSweep false :bTeleport true)
        (return))
      (if (not (Variables|FX|GetLanded))
        (Variables|FX|SetLanded true)
        {rel_loc('Can', mv(0, 0, 4))}
        (Transformation|SetRelativeRotation :self (Variables|Default|GetCan) :NewRotation (Math|Rotator|MakeRotator :Roll 0.0 :Pitch 90.0 :Yaw 35.0) :bSweep false :bTeleport true)
        (Audio|PlaySoundatLocation :Sound {SND['SFX_Smoke_Hiss']} :Location here :VolumeMultiplier 1.1 :AttenuationSettings {ATT_NEAR})
    {show})
      (bind sa (- age 0.6))
      (Variables|FX|SetFade (* (Math|Float|Min(Float) (/ sa 0.5) 1.0) (Math|Float|Max(Float) 0.0 (Math|Float|Min(Float) 1.0 (/ (- 18.0 sa) 4.0)))))
      {set_scalar('MID', 'Opacity', '(* 0.93 (Variables|FX|GetFade))')}
    {puffs}
      (if (and (Networking|HasAuthority) (> sa 19.0))
        (Actor|DestroyActor :self self)))
    ''')
    finish(smoke)

    # ---------------------------------------------------------------- firecracker (junkie only): a fizzing fuse, then a fake gunfight
    BANGS = [4.0, 4.18, 4.31, 4.55, 4.7, 4.95, 5.08, 5.4]
    crk = actor_bp('BP_GW_Firecracker', life=9.0)
    mesh(crk, 'Stick', CYL, 'red', loc=(0, 0, 4), scale=(0.035, 0.035, 0.13))
    mesh(crk, 'Spark', SPHERE, 'fuse', loc=(0, 0, 55), scale=(0.6, 0.6, 0.25), parent='Stick')
    light(crk, 'FuseGlow', (255, 150, 50, 255), 0.0, 160.0, loc=(0, 0, 10))
    light(crk, 'Flash', (255, 220, 150, 255), 0.0, 1100.0, loc=(0, 0, 40))
    ensure_var(crk, 'From', struct=V3, rep=REP.REPLICATED, category='FX')
    ensure_var(crk, 'NextBang', 'int', category='FX')
    fxvars(crk, bools=('Landed', 'First'))
    compile_bp(crk, quiet=True)
    flashes = '\n'.join(f'  (Variables|FX|SetG (Math|Float|Max(Float) (Variables|FX|GetG) (select (>= age {b}) (Math|Float|Max(Float) 0.0 (- 1.0 (* (- age {b}) 9.0))) 0.0)))' for b in BANGS)
    wr(crk, 'EventGraph', f'''
    (event EventBeginPlay
      (Variables|FX|SetT0 (Utilities|Time|GetGameTimeinSeconds)))

    (event EventTick (DeltaSeconds)
      {AGE}
      (bind here (Transformation|GetActorLocation))
      (if (< age 0.5)
        ; a float bind feeding vector math gets re-typed by the promotable operators: keep it in a variable
        (Variables|FX|SetG (/ age 0.5))
        (bind a (Variables|FX|GetG))
        (bind from (Variables|FX|GetFrom))
        (Transformation|SetWorldLocation :self (Variables|Default|GetStick) :NewLocation (+ (+ from (* (- here from) a)) (Math|Vector|MakeVector 0.0 0.0 (+ 4.0 (* 150.0 (* a (- 1.0 a)))))) :bSweep false :bTeleport true)
        (Transformation|SetWorldRotation :self (Variables|Default|GetStick) :NewRotation (Math|Rotator|MakeRotator :Roll (* age 600.0) :Pitch (* age 900.0) :Yaw 0.0) :bSweep false :bTeleport true)
        (return))
      (if (not (Variables|FX|GetLanded))
        (Variables|FX|SetLanded true)
        {rel_loc('Stick', mv(0, 0, 2))}
        (Transformation|SetRelativeRotation :self (Variables|Default|GetStick) :NewRotation (Math|Rotator|MakeRotator :Roll 0.0 :Pitch 90.0 :Yaw 60.0) :bSweep false :bTeleport true)
        (Audio|PlaySoundatLocation :Sound {SND['SFX_Smoke_Hiss']} :Location here :VolumeMultiplier 0.3 :PitchMultiplier 1.6 :AttenuationSettings {ATT_QUIET}))
      ; the fuse fizzes until the first bang, then a flash with every bang
      (bind fuse (< age {BANGS[0]}))
      (Rendering|SetVisibility :self (Variables|Default|GetSpark) :bNewVisibility (and fuse (> (Math|Trig|Sin(Radians) (* age 47.0)) -0.3)) :bPropagateToChildren false)
      (Rendering|Components|Light|SetIntensity :self (Variables|Default|GetFuseGlow) :NewIntensity (select fuse (* 900.0 (+ 0.6 (* 0.4 (Math|Trig|Sin(Radians) (* age 31.0))))) 0.0))
      (Variables|FX|SetG 0.0)
    {flashes}
      (Rendering|Components|Light|SetIntensity :self (Variables|Default|GetFlash) :NewIntensity (* 60000.0 (Variables|FX|GetG)))
      ; the bangs themselves: game mode CrackerTick (server), from this actor's T0 and NextBang
      (if (and (Networking|HasAuthority) (> age 6.5))
        (Actor|DestroyActor :self self)))
    ''')
    finish(crk)

    # ---------------------------------------------------------------- shrinking gas: a green puff at the feet
    N_GAS = 9
    gas = actor_bp('BP_GW_GasPuff', life=7.0)
    mesh(gas, 'Bottle', CYL, 'glass', loc=(30, 14, 5), rot=(0, 90, 30), scale=(0.09, 0.09, 0.24))
    mesh(gas, 'Cap', CYL, 'brass', loc=(0, 0, 55), scale=(0.55, 0.55, 0.15), parent='Bottle')
    GP = []
    for k in range(N_GAS):
        a, r = rs.uniform(0, 2 * math.pi), (0 if k == 0 else rs.uniform(30, 120))
        GP.append((r * math.cos(a), r * math.sin(a), rs.uniform(20, 110), rs.uniform(0.9, 1.6), rs.uniform(6, 16), k * 0.05))
        mesh(gas, f'P{k}', SPHERE, 'gas', scale=(0.01, 0.01, 0.01))
    light(gas, 'Glow', (90, 255, 70, 255), 0.0, 420.0, loc=(0, 0, 60))
    ensure_var(gas, 'Small', 'bool', rep=REP.REPLICATED, category='FX')
    fxvars(gas, floats=('T0', 'Age', 'G', 'Fade', 'Sz'), bools=('Started',), mids=('MID',))
    add_ease(gas)
    compile_bp(gas, quiet=True)
    SM = '(Variables|FX|GetSz)'                 # a select feeding vector math would get re-typed: keep it in a float
    gpuffs = '\n'.join(f'''  (Variables|FX|SetG (CallFunction|Ease :V (/ (- age {d:.2f}) 0.9)))
      {rel_loc(f"P{k}", f"(* (Math|Vector|MakeVector (* {x:.1f} (+ 0.3 (* 0.7 (Variables|FX|GetG)))) (* {y:.1f} (+ 0.3 (* 0.7 (Variables|FX|GetG)))) (+ (* {z:.1f} (+ 0.5 (* 0.5 (Variables|FX|GetG)))) (* {rise:.1f} age))) {SM})")}
      {rel_scale(f"P{k}", uni(f"(* (* {s:.2f} {SM}) (+ 0.05 (* 0.95 (Variables|FX|GetG))))"))}'''
                       for k, (x, y, z, s, rise, d) in enumerate(GP))
    wr(gas, 'EventGraph', f'''
    (event EventBeginPlay
      (Variables|FX|SetT0 (Utilities|Time|GetGameTimeinSeconds))
      {mid_setup('P0', [f'P{k}' for k in range(1, N_GAS)], 'gas')})

    (event EventTick (DeltaSeconds)
      {AGE}
      (Variables|FX|SetSz (select (Variables|FX|GetSmall) 0.55 1.0))
      ; Small arrives with the spawn on clients but is set just after BeginPlay on the server: read it on the first tick
      (if (not (Variables|FX|GetStarted))
        (Variables|FX|SetStarted true)
        (Rendering|SetVisibility :self (Variables|Default|GetBottle) :bNewVisibility (not (Variables|FX|GetSmall)) :bPropagateToChildren true)
        (Audio|PlaySoundatLocation :Sound {SND['SFX_Gas_Hiss']} :Location (+ (Transformation|GetActorLocation) {mv(0, 0, 30)}) :VolumeMultiplier {SM} :AttenuationSettings {ATT_NEAR}))
      (Variables|FX|SetFade (Math|Float|Max(Float) 0.0 (Math|Float|Min(Float) 1.0 (/ (- 3.6 age) 2.2))))
      {set_scalar('MID', 'Opacity', '(* (* 0.75 (Variables|FX|GetFade)) (Math|Float|Min(Float) 1.0 (/ age 0.15)))')}
      (Rendering|Components|Light|SetIntensity :self (Variables|Default|GetGlow) :NewIntensity (* (* 5000.0 (Variables|FX|GetFade)) (+ 0.8 (* 0.2 (Math|Trig|Sin(Radians) (* age 13.0))))))
    {gpuffs}
      (if (and (Networking|HasAuthority) (> age 4.6))
        (Actor|DestroyActor :self self)))
    ''')
    finish(gas)

    # ---------------------------------------------------------------- shrink effect (follows its target on every machine)
    shrink = actor_bp('BP_GW_Shrink', life=0.0)
    light(shrink, 'Aura', (90, 255, 70, 255), 0.0, 260.0, loc=(0, 0, -40))
    for k in range(3):
        mesh(shrink, f'W{k}', SPHERE, 'wisp', scale=(0.07, 0.07, 0.07))
    ensure_var(shrink, 'Until', 'float', rep=REP.REPLICATED, category='FX')
    ensure_var(shrink, 'Target', obj_class=chc, rep=REP.REP_NOTIFY, category='FX')
    ensure_var(shrink, 'ToScale', 'float', rep=REP.REPLICATED, category='FX')      # GM.GasScale, set before Target (user, 2026-11-05: smaller than 0.55)
    fxvars(shrink, floats=('T0', 'Age', 'S', 'OrigWalk', 'OrigSprint'), bools=('Applied', 'Done'))
    ensure_fn(shrink, 'OnRep_Target')
    ensure_fn(shrink, 'Apply')
    add_ease(shrink)
    compile_bp(shrink, quiet=True)
    cdo(shrink).set_editor_property('ToScale', 0.3)
    wr(shrink, 'Apply', f'''
    (fn Apply ()
      (bind t (Variables|FX|GetTarget))
      (if (or (Variables|FX|GetApplied) (not ({ISVALID} :Object t)))
        (return))
      (Variables|FX|SetApplied true)
      (Variables|FX|SetT0 (Utilities|Time|GetGameTimeinSeconds))
      (Variables|FX|SetOrigWalk (GW|Get|BP_GW_Character|WalkSpeed :self t))
      (Variables|FX|SetOrigSprint (GW|Get|BP_GW_Character|SprintSpeed :self t))
      (GW|Set|BP_GW_Character|WalkSpeed :self t :WalkSpeed (* (Variables|FX|GetOrigWalk) 1.7))
      (GW|Set|BP_GW_Character|SprintSpeed :self t :SprintSpeed (* (Variables|FX|GetOrigSprint) 1.7))
      (GW|Call|BP_GW_Character|SetSprint :self t :On (GW|Get|BP_GW_Character|IsSprinting :self t))
      (Development|PrintString :InString (cat "GW: shrink on " (Utilities|GetDisplayName :Object t) " walk " (Variables|FX|GetOrigWalk) " -> " (GW|Get|BP_GW_Character|WalkSpeed :self t)) :bPrintToScreen false))
    ''')
    wr(shrink, 'OnRep_Target', '(fn OnRep_Target () (CallFunction|Apply))')
    wisps = '\n'.join(f'''  {rel_loc(f"W{k}", f"(Math|Vector|MakeVector (* 42.0 (Math|Trig|Cos(Radians) (+ (* age 3.5) {k * 2.094:.3f}))) (* 42.0 (Math|Trig|Sin(Radians) (+ (* age 3.5) {k * 2.094:.3f}))) (+ -50.0 (* 14.0 (Math|Trig|Sin(Radians) (+ (* age 2.3) {k:.1f})))))")}
      {rel_scale(f"W{k}", uni("(* 0.07 (Math|Float|Max(Float) (Math|Float|Max(Float) 0.0 (- 1.0 (/ age 4.0))) (select (and (> left 0.0) (< left 3.0)) 0.6 0.0)))"))}''' for k in range(3))
    wr(shrink, 'EventGraph', f'''
    (event EventTick (DeltaSeconds)
      (bind t (Variables|FX|GetTarget))
      (if (not ({ISVALID} :Object t))
        (if (Networking|HasAuthority)
          (Actor|DestroyActor :self self))
        (return))
      (Transformation|SetActorLocation :self self :NewLocation (Transformation|GetActorLocation :self t) :bSweep false :bTeleport true)
      (if (not (Variables|FX|GetApplied))
        (CallFunction|Apply)
        (return))
      (Variables|FX|SetAge (- (Utilities|Time|GetGameTimeinSeconds) (Variables|FX|GetT0)))
      (bind age (Variables|FX|GetAge))
      (bind left (- (Variables|FX|GetUntil) {STIME}))
      (if (GW|Get|BP_GW_Character|IsDead :self t)
        (Rendering|Components|Light|SetIntensity :self (Variables|Default|GetAura) :NewIntensity 0.0)
        (return))
      ; shrink in 0.6 s, grow back in 0.5 s once the 20 s are over
      (bind sz (Variables|FX|GetToScale))
      (Variables|FX|SetS (select (> left 0.0) (- 1.0 (* (- 1.0 sz) (CallFunction|Ease :V (/ age 0.6)))) (+ sz (* (- 1.0 sz) (CallFunction|Ease :V (/ (- 0.0 left) 0.5))))))
      (Transformation|SetActorScale3D :self t :NewScale3D (Math|Vector|MakeVector (Variables|FX|GetS) (Variables|FX|GetS) (Variables|FX|GetS)))
      ; green glow at the start, blinking during the last 3 s (time is running out)
      (Rendering|Components|Light|SetIntensity :self (Variables|Default|GetAura) :NewIntensity (+ (* 1800.0 (Math|Float|Max(Float) 0.0 (- 1.0 (/ age 3.0)))) (select (and (> left 0.0) (< left 3.0)) (* 1400.0 (Math|Float|Absolute(Float) (Math|Trig|Sin(Radians) (* age 9.0)))) 0.0)))
    {wisps}
      (if (and (<= left 0.0) (not (Variables|FX|GetDone)))
        (Variables|FX|SetDone true)
        (GW|Set|BP_GW_Character|WalkSpeed :self t :WalkSpeed (Variables|FX|GetOrigWalk))
        (GW|Set|BP_GW_Character|SprintSpeed :self t :SprintSpeed (Variables|FX|GetOrigSprint))
        (GW|Call|BP_GW_Character|SetSprint :self t :On (GW|Get|BP_GW_Character|IsSprinting :self t))
        (Development|PrintString :InString (cat "GW: shrink over on " (Utilities|GetDisplayName :Object t) " walk=" (GW|Get|BP_GW_Character|WalkSpeed :self t)) :bPrintToScreen false)
        (if (Networking|HasAuthority)
          ; lift a little so the growing capsule does not sink into the floor; a small puff
          (Transformation|SetActorLocation :self t :NewLocation (+ (Transformation|GetActorLocation :self t) (Math|Vector|MakeVector 0.0 0.0 (* (- 1.0 sz) 100.0))) :bSweep true :bTeleport true)
          (bind pf (Game|SpawnActorfromClass :Class "{GAS}" :SpawnTransform (Math|Transform|MakeTransform :Location (- (Transformation|GetActorLocation :self t) {mv(0, 0, 60)})) :CollisionHandlingOverride "AlwaysSpawn"))
          (GW|Set|{GAS}|Small :self pf :Small true)))
      (if (and (Networking|HasAuthority) (< left -0.7))
        (Transformation|SetActorScale3D :self t :NewScale3D {mv(1, 1, 1)})
        (Actor|DestroyActor :self self)))
    ''')
    finish(shrink)

    # ---------------------------------------------------------------- door trap: a small box under the lintel
    trap = actor_bp('BP_GW_Trap')
    mesh(trap, 'Body', CUBE, 'dark', scale=(0.3, 0.17, 0.1))
    mesh(trap, 'Plate', CUBE, 'brass', loc=(0, 0, 5.4), scale=(0.25, 0.19, 0.012))
    mesh(trap, 'Led', SPHERE, 'led', loc=(11.5, 8.0, 3), scale=(0.05, 0.05, 0.05))
    light(trap, 'LedLight', (255, 40, 20, 255), 900.0, 140.0, loc=(11.5, 8.0, -6))
    mesh(trap, 'Wire', CYL, 'tape', loc=(-5, 0, -9), scale=(0.005, 0.005, 0.18))
    ensure_var(trap, 'OwnerPS', obj_class=psb.generated_class(), category='FX')
    ensure_var(trap, 'AxisX', 'bool', category='FX')
    ensure_var(trap, 'HalfW', 'float', category='FX')
    ensure_var(trap, 'ArmAt', 'float', category='FX')
    ensure_var(trap, 'FloorMode', 'bool', rep=REP.REPLICATED, category='FX')
    fxvars(trap, floats=('T0', 'Age'))
    compile_bp(trap, quiet=True)
    wr(trap, 'EventGraph', f'''
    (event EventBeginPlay
      (Variables|FX|SetT0 (Utilities|Time|GetGameTimeinSeconds))
      (Audio|PlaySoundatLocation :Sound {SND['SFX_Trap_Click']} :Location (Transformation|GetActorLocation) :VolumeMultiplier 0.55 :AttenuationSettings {ATT_QUIET}))

    (event EventTick (DeltaSeconds)
      {AGE}
      (bind on (> (Math|Trig|Sin(Radians) (* age 5.0)) 0.2))
      (Rendering|SetVisibility :self (Variables|Default|GetLed) :bNewVisibility on :bPropagateToChildren false)
      (Rendering|SetVisibility :self (Variables|Default|GetLedLight) :bNewVisibility on :bPropagateToChildren false))
    ''')
    finish(trap)

    # ---------------------------------------------------------------- the bomb: dynamite, an alarm clock, a red LED
    bomb = actor_bp('BP_GW_Bomb')
    for k, (y, z) in enumerate(((-7, 3.5), (0, 3.5), (7, 3.5), (-3.5, 9.6), (3.5, 9.6))):
        mesh(bomb, f'Stick{k}', CYL, 'red', loc=(0, y, z), rot=(0, 90, 0), scale=(0.065, 0.065, 0.3))
    for k, x in enumerate((-9, 9)):
        mesh(bomb, f'Strap{k}', CUBE, 'tape', loc=(x, 0, 6.5), scale=(0.03, 0.23, 0.15))
    mesh(bomb, 'Clock', CYL, 'brass', loc=(0, 0, 19.5), rot=(0, 90, 0), scale=(0.13, 0.13, 0.05))
    mesh(bomb, 'Face', CYL, 'white', loc=(2.7, 0, 19.5), rot=(0, 90, 0), scale=(0.11, 0.11, 0.004))
    hp_ = ensure_component(bomb, 'HandPivot', unreal.SceneComponent, 'DefaultSceneRoot')
    hp_.set_editor_property('relative_location', unreal.Vector(3.1, 0, 19.5))
    mesh(bomb, 'Hand', CUBE, 'tape', loc=(0, 0, 2.2), scale=(0.003, 0.006, 0.045), parent='HandPivot')
    for k, y in enumerate((-3.6, 3.6)):
        mesh(bomb, f'Bell{k}', SPHERE, 'brass', loc=(0, y, 26.5), scale=(0.035, 0.035, 0.035))
    mesh(bomb, 'WireR', CYL, 'red', loc=(4, -2.5, 14), rot=(20, 0, 0), scale=(0.006, 0.006, 0.12))
    mesh(bomb, 'WireB', CYL, 'blue', loc=(4, 2.5, 14), rot=(-20, 0, 0), scale=(0.006, 0.006, 0.12))
    mesh(bomb, 'Led', SPHERE, 'led', loc=(6, 6.5, 10), scale=(0.022, 0.022, 0.022))
    light(bomb, 'Glow', (255, 30, 20, 255), 0.0, 240.0, loc=(10, 0, 22))
    ensure_var(bomb, 'ExplodeAt', 'float', rep=REP.REPLICATED, category='FX')
    ensure_var(bomb, 'OwnerPS', obj_class=psb.generated_class(), category='FX')
    ensure_var(bomb, 'Warned', 'bool', category='FX')          # server: the NPCs around already fled
    ensure_var(bomb, 'NextNear', 'float', category='FX')       # server: next "do you hear that beep?" line
    fxvars(bomb, floats=('NextBeep', 'Flash'))
    compile_bp(bomb, quiet=True)
    wr(bomb, 'EventGraph', f'''
    (event EventTick (DeltaSeconds)
      (bind at (Variables|FX|GetExplodeAt))
      (if (<= at 0.0)
        (return))
      (bind now {STIME})
      (bind left (- at now))
      ; a beep every second, faster and faster near the end; heard in 3D (ATT_GW_BombBeep), seen as a red flash
      (if (>= now (Variables|FX|GetNextBeep))
        (Variables|FX|SetNextBeep (+ now (select (> left 15.0) 1.0 (select (> left 6.0) 0.5 (select (> left 2.5) 0.25 0.12)))))
        (Audio|PlaySoundatLocation :Sound {SND['SFX_Bomb_Beep']} :Location (+ (Transformation|GetActorLocation) {mv(0, 0, 20)}) :VolumeMultiplier 1.0 :AttenuationSettings {ATT_BEEP})
        (Variables|FX|SetFlash 1.0))
      (Variables|FX|SetFlash (Math|Float|Max(Float) 0.0 (- (Variables|FX|GetFlash) (* DeltaSeconds 7.0))))
      (Rendering|Components|Light|SetIntensity :self (Variables|Default|GetGlow) :NewIntensity (* (Variables|FX|GetFlash) 2600.0))
      (Rendering|SetVisibility :self (Variables|Default|GetLed) :bNewVisibility (> (Variables|FX|GetFlash) 0.35) :bPropagateToChildren false)
      (Transformation|SetRelativeRotation :self (Variables|Default|GetHandPivot) :NewRotation (Math|Rotator|MakeRotator :Roll (* left 8.0) :Pitch 0.0 :Yaw 0.0) :bSweep false :bTeleport true))
    ''')
    finish(bomb)


    # ---------------------------------------------------------------- explosions (big: the bomb; small: the trap)
    def blast_bp(name, R, life, nf, ns, nd, ring, boom_vol, flash, click):
        bp = actor_bp(name, life=life)
        r = random.Random(name)
        F, S, D = [], [], []
        for k in range(nf):
            v = (r.uniform(-1, 1), r.uniform(-1, 1), r.uniform(0.1, 1))
            F.append((v, r.uniform(0.5, 0.9)))
            mesh(bp, f'F{k}', SPHERE, 'fire', scale=(0.01, 0.01, 0.01))
        for k in range(ns):
            v = (r.uniform(-1, 1), r.uniform(-1, 1), r.uniform(0.05, 0.6))
            S.append((v, r.uniform(0.5, 0.95), r.uniform(15, 60) * R / 900, r.uniform(0.2, 0.8)))
            mesh(bp, f'S{k}', SPHERE, 'bsmoke', scale=(0.01, 0.01, 0.01))
        for k in range(nd):
            a = r.uniform(0, 2 * math.pi)
            sp = r.uniform(0.5, 1.0) * (900 if R > 300 else 450)
            vz = r.uniform(250, 900) * (1 if R > 300 else 0.6)
            tl = (vz + math.sqrt(vz * vz + 2 * 490 * 10)) / 980.0
            D.append((sp * math.cos(a), sp * math.sin(a), vz, tl, r.uniform(200, 900), r.uniform(200, 900)))
            sz = r.uniform(0.03, 0.09) * (1 if R > 300 else 0.6)
            mesh(bp, f'D{k}', CUBE, 'dark', scale=(sz, sz * r.uniform(0.6, 1.4), sz * 0.6))
        if ring:
            mesh(bp, 'Ring', SPHERE, 'shock', loc=(0, 0, 20), scale=(0.01, 0.01, 0.01))
        mesh(bp, 'Scorch', SPHERE, 'scorch', loc=(0, 0, 1), scale=(0.01, 0.01, 0.004))
        light(bp, 'Flash', (255, 170, 90, 255), 0.0, R * 4.0, loc=(0, 0, 120))
        fxvars(bp, floats=('T0', 'Age', 'E1', 'E2'), mids=('FireMID', 'SmokeMID') + (('RingMID',) if ring else ()))
        add_ease(bp)
        compile_bp(bp, quiet=True)
        body = []
        for k, ((vx, vy, vz), sz) in enumerate(F):
            body.append(rel_loc(f'F{k}', f'(Math|Vector|MakeVector (* {vx * R * 0.3:.1f} (Variables|FX|GetE1)) (* {vy * R * 0.3:.1f} (Variables|FX|GetE1)) (+ {R * 0.1:.1f} (* {vz * R * 0.35:.1f} (Variables|FX|GetE1))))'))
            body.append(rel_scale(f'F{k}', uni(f'(select (> age 0.95) 0.001 (* {sz * R / 100:.2f} (+ 0.15 (* 0.85 (Variables|FX|GetE1)))))')))
        for k, ((vx, vy, vz), sz, rise, d) in enumerate(S):
            body.append(rel_loc(f'S{k}', f'(Math|Vector|MakeVector (* {vx * R * 0.55:.1f} (Variables|FX|GetE2)) (* {vy * R * 0.55:.1f} (Variables|FX|GetE2)) (+ (* {vz * R * 0.6:.1f} (Variables|FX|GetE2)) (* {rise:.1f} age)))'))
            body.append(rel_scale(f'S{k}', uni(f'(* (* {sz * R / 100:.2f} (+ 0.2 (* 0.8 (Variables|FX|GetE2)))) (+ 1.0 (* 0.07 age)))')))
        for k, (vx, vy, vz, tl, s1, s2) in enumerate(D):
            a = f'(Math|Float|Min(Float) age {tl:.3f})'
            body.append(f'(Transformation|SetRelativeLocationAndRotation :self (Variables|Default|GetD{k}) :NewLocation (Math|Vector|MakeVector (* {vx:.1f} {a}) (* {vy:.1f} {a}) (Math|Float|Max(Float) 3.0 (+ 10.0 (- (* {vz:.1f} {a}) (* 490.0 (* {a} {a})))))) :NewRotation (Math|Rotator|MakeRotator :Roll (* {s1:.1f} {a}) :Pitch (* {s2:.1f} {a}) :Yaw 0.0) :bSweep false :bTeleport true)')
        if ring:
            body.append(rel_scale('Ring', f'(Math|Vector|MakeVector (* {2 * R / 100:.2f} (CallFunction|Ease :V (/ age 0.5))) (* {2 * R / 100:.2f} (CallFunction|Ease :V (/ age 0.5))) 0.05)'))
            body.append(set_scalar('RingMID', 'Opacity', '(* 0.45 (Math|Float|Max(Float) 0.0 (- 1.0 (/ age 0.65))))'))
        body.append(rel_scale('Scorch', f'(Math|Vector|MakeVector (* {R * 1.1 / 100:.2f} (Math|Float|Min(Float) 1.0 (/ age 0.15))) (* {R * 1.1 / 100:.2f} (Math|Float|Min(Float) 1.0 (/ age 0.15))) 0.004)'))
        mids = mid_setup('F0', [f'F{k}' for k in range(1, nf)], 'fire', 'FireMID') + '\n  ' + mid_setup('S0', [f'S{k}' for k in range(1, ns)], 'bsmoke', 'SmokeMID')
        if ring:
            mids += '\n  ' + mid_setup('Ring', [], 'shock', 'RingMID')
        clicks = f'\n  (Audio|PlaySoundatLocation :Sound {SND["SFX_Trap_Click"]} :Location (Transformation|GetActorLocation) :VolumeMultiplier 0.9 :AttenuationSettings {ATT_NEAR})' if click else ''
        nl = '\n  '
        wr(bp, 'EventGraph', f'''
    (event EventBeginPlay
      (Variables|FX|SetT0 (Utilities|Time|GetGameTimeinSeconds))
      {mids}{clicks}
      (Audio|PlaySoundatLocation :Sound {BOOM} :Location (Transformation|GetActorLocation) :VolumeMultiplier {boom_vol} :AttenuationSettings {ATT_FAR}))

    (event EventTick (DeltaSeconds)
      {AGE}
      (Variables|FX|SetE1 (CallFunction|Ease :V (/ age 0.3)))
      (Variables|FX|SetE2 (CallFunction|Ease :V (/ age 1.6)))
      {set_scalar('FireMID', 'Strength', '(* 28.0 (Math|Float|Max(Float) 0.0 (- 1.0 (/ (Math|Float|Max(Float) 0.0 (- age 0.12)) 0.6))))')}
      {set_scalar('SmokeMID', 'Opacity', f'(* (* 0.85 (Math|Float|Min(Float) 1.0 (/ age 0.25))) (Math|Float|Max(Float) 0.0 (Math|Float|Min(Float) 1.0 (/ (- {life - 0.4:.1f} age) 3.0))))')}
      (bind fl (Math|Float|Max(Float) 0.0 (- 1.0 (/ age 0.45))))
      (Rendering|Components|Light|SetIntensity :self (Variables|Default|GetFlash) :NewIntensity (* {flash:.1f} (* fl fl)))
      {nl.join(body)})
    ''')
        finish(bp)
        return bp


    big = blast_bp('BP_GW_BigBlast', BOMB_R, 11.0, 6, 12, 14, True, 4.0, 220000.0, False)
    small = blast_bp('BP_GW_SmallBlast', 130.0, 4.0, 3, 4, 6, False, 1.2, 40000.0, True)

    # ---------------------------------------------------------------- defuse: sparks, a puff, the dying beep
    dfx = actor_bp('BP_GW_DefuseFX', life=3.0)
    DS = []
    for k in range(8):
        a = rs.uniform(0, 2 * math.pi)
        DS.append((math.cos(a) * rs.uniform(80, 220), math.sin(a) * rs.uniform(80, 220), rs.uniform(150, 420)))
        mesh(dfx, f'Sp{k}', SPHERE, 'spark', scale=(0.02, 0.02, 0.02))
    for k in range(3):
        mesh(dfx, f'Pf{k}', SPHERE, 'smoke', loc=(rs.uniform(-10, 10), rs.uniform(-10, 10), 15 + 8 * k), scale=(0.01, 0.01, 0.01))
    light(dfx, 'Zap', (150, 200, 255, 255), 0.0, 300.0, loc=(0, 0, 25))
    fxvars(dfx, mids=('MID',))
    compile_bp(dfx, quiet=True)
    sparks = '\n'.join(f'''  {rel_loc(f"Sp{k}", f"(Math|Vector|MakeVector (* {x:.1f} age) (* {y:.1f} age) (Math|Float|Max(Float) 2.0 (+ 15.0 (- (* {z:.1f} age) (* 490.0 (* age age))))))")}
      {rel_scale(f"Sp{k}", uni("(* 0.02 (Math|Float|Max(Float) 0.0 (- 1.0 (/ age 0.8))))"))}''' for k, (x, y, z) in enumerate(DS))
    pfs = '\n'.join(f'  {rel_scale(f"Pf{k}", uni(f"(* {0.35 + 0.1 * k:.2f} (Math|Float|Min(Float) 1.0 (/ age 0.6)))"))}' for k in range(3))
    wr(dfx, 'EventGraph', f'''
    (event EventBeginPlay
      (Variables|FX|SetT0 (Utilities|Time|GetGameTimeinSeconds))
      {mid_setup('Pf0', ['Pf1', 'Pf2'], 'smoke')}
      (Audio|PlaySoundatLocation :Sound {SND['SFX_Defuse']} :Location (Transformation|GetActorLocation) :VolumeMultiplier 1.0 :AttenuationSettings {ATT_NEAR}))

    (event EventTick (DeltaSeconds)
      {AGE}
      (Rendering|Components|Light|SetIntensity :self (Variables|Default|GetZap) :NewIntensity (* 9000.0 (Math|Float|Max(Float) 0.0 (- 1.0 (/ age 0.3)))))
      {set_scalar('MID', 'Opacity', '(* 0.6 (Math|Float|Max(Float) 0.0 (- 1.0 (/ age 2.5))))')}
    {sparks}
    {pfs})
    ''')
    finish(dfx)

    # ---------------------------------------------------------------- hand lamp (local, owner only: never replicated)
    lamp = actor_bp('BP_GW_HandLamp', replicated=False)
    beam = ensure_component(lamp, 'Beam', unreal.SpotLightComponent, 'DefaultSceneRoot')
    beam.set_editor_property('intensity', 9000.0)
    beam.set_editor_property('attenuation_radius', 2000.0)
    beam.set_editor_property('inner_cone_angle', 12.0)
    beam.set_editor_property('outer_cone_angle', 24.0)
    beam.set_editor_property('light_color', unreal.Color(r=255, g=228, b=190, a=255))
    beam.set_editor_property('cast_shadows', True)
    compile_bp(lamp, quiet=True)
    wr(lamp, 'EventGraph', f'''
    (event EventTick (DeltaSeconds)
      (bind cm (Game|GetPlayerCameraManager :PlayerIndex 0))
      (if ({ISVALID} :Object cm)
        (bind cr (Camera|GetCameraRotation :self cm))
        (Transformation|SetActorLocationAndRotation :self self :NewLocation (+ (Camera|GetCameraLocation :self cm) (* (Math|Vector|GetForwardVector cr) 30.0)) :NewRotation cr :bSweep false :bTeleport true)))
    ''')
    finish(lamp)
else:
    loud, gun, smoke, crk, gas, shrink, trap, bomb, big, small, dfx, lamp = (load_bp(n, SHOP) for n in ('BP_GW_LoudCue', 'BP_GW_GuestGun', 'BP_GW_SmokeBomb', 'BP_GW_Firecracker', 'BP_GW_GasPuff', 'BP_GW_Shrink', 'BP_GW_Trap', 'BP_GW_Bomb', 'BP_GW_BigBlast', 'BP_GW_SmallBlast', 'BP_GW_DefuseFX', 'BP_GW_HandLamp'))
    BANGS = [4.0, 4.18, 4.31, 4.55, 4.7, 4.95, 5.08, 5.4]

if want('vendors'):
    # ---------------------------------------------------------------- the vendors: barman (base class), junkie, waiters
    # One Character class for the three (BP_GW_Barman) with children BP_GW_Junkie / BP_GW_Waiter that only change class
    # defaults: VendorKind (0 / 1 / 2), Mobile (the waiters walk), Skin (the generated skin, set by the assets pipeline:
    # manifest "outfits": "barman" / "junkie" / "waiter"; the placeholder accessories hide once a skin is set),
    # ShirtMat / LegsMat (tinted mannequin). Accessories by kind: apron (barman), bow tie (barman, waiter), flat cap
    # (junkie), tray with three champagne glasses (waiter). Placeholders sit in mesh space (the mannequin faces +Y,
    # its right is -X), not on bones: the tray is held at the right side at elbow height.
    barman = load_or_create_bp('BP_GW_Barman', unreal.Character, folder=SHOP)
    compile_bp(barman, quiet=True)
    MANNY = '/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple'
    ABP = None
    for d in _ar.get_assets_by_path('/Game/Characters/Mannequins', recursive=True):
        if str(d.asset_name) == 'ABP_Unarmed':
            ABP = str(d.package_name)
    print('ABP', ABP)
    assert ABP, 'ABP_Unarmed not found under /Game/Characters/Mannequins'
    ensure_var(barman, 'Skin', obj_class=unreal.SkeletalMesh, category='Barman')
    ensure_var(barman, 'TrayMesh', obj_class=unreal.StaticMesh, category='Barman')
    ensure_var(barman, 'ShirtMat', obj_class=unreal.MaterialInterface, category='Barman')
    ensure_var(barman, 'LegsMat', obj_class=unreal.MaterialInterface, category='Barman')
    ensure_var(barman, 'VendorKind', 'int', category='Barman')
    for v in ('Mobile', 'Moving'):
        ensure_var(barman, v, 'bool', category='Barman')
    for v in ('BaseYaw', 'LookYaw', 'TargetYaw', 'BestD', 'MoveStart', 'NextMoveAt'):
        ensure_var(barman, v, 'float', category='Barman')
    ensure_fn(barman, 'PickLook')
    ensure_fn(barman, 'WaiterAnim')
    ensure_var(barman, 'WalkClip', 'bool', category='Barman')
    ensure_var(barman, 'ClipOn', 'bool', category='Barman')
    ACC = [  # name, shape, material, mesh-space location, scale, kinds that show it
        ('Apron', CUBE, 'apron', (0, 17.5, 80), (0.42, 0.015, 0.52), (0,)),
        ('BowTie', CUBE, 'silk', (0, 11.5, 147), (0.09, 0.02, 0.035), (0, 2)),
        ('Cap', SPHERE, 'tweed', (0, 1, 177), (0.23, 0.25, 0.09), (1,)),
        ('Brim', CUBE, 'tweed', (0, 12, 173.5), (0.17, 0.09, 0.012), (1,)),
        ('Tray', CYL, 'silver', (-28, 24, 112), (0.42, 0.42, 0.012), (2,)),
        ('Glass0', CYL, 'champ', (-34, 28, 119.5), (0.05, 0.05, 0.13), (2,)),
        ('Glass1', CYL, 'champ', (-22, 30, 119.5), (0.05, 0.05, 0.13), (2,)),
        ('Glass2', CYL, 'champ', (-28, 17, 119.5), (0.05, 0.05, 0.13), (2,)),
    ]
    for name, shape, mi_, loc, sc_, _ in ACC:
        c = ensure_component(barman, name, unreal.StaticMeshComponent, 'Mesh')
        c.set_editor_property('static_mesh', unreal.load_asset(shape))
        c.set_editor_property('override_materials', [MI[mi_]])
        c.set_editor_property('relative_location', unreal.Vector(*loc))
        c.set_editor_property('relative_scale3d', unreal.Vector(*sc_))
        c.set_editor_property('cast_shadow', False)
        c.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
    compile_bp(barman, quiet=True)
    # the inherited mesh template: mannequin, unarmed idle, feet on the capsule bottom, facing the actor's +X
    try:
        mt = unreal.SubobjectDataBlueprintFunctionLibrary.get_object(subobjects(barman)['Mesh'][1])
        mt.set_editor_property('skeletal_mesh_asset', unreal.load_asset(MANNY))
        mt.set_editor_property('animation_mode', unreal.AnimationMode.ANIMATION_BLUEPRINT)
        mt.set_editor_property('anim_class', unreal.load_asset(ABP).generated_class())
        mt.set_editor_property('relative_location', unreal.Vector(0, 0, -89))
        mt.set_editor_property('relative_rotation', unreal.Rotator(roll=0, pitch=0, yaw=-90))
    except Exception as e:
        print('barman mesh template not set:', e)
    _torso, _legs = chcdo.get_editor_property('TorsoMatM'), chcdo.get_editor_property('LegsMatM')
    acc_vis = '\n'.join(f'      (Rendering|SetVisibility :self (Variables|Default|Get{n}) :bNewVisibility {"(or " if len(ks) > 1 else ""}{" ".join(f"(== k {x})" for x in ks)}{")" if len(ks) > 1 else ""} :bPropagateToChildren false)' for n, _, _, _, _, ks in ACC)
    acc_hide = '\n'.join(f'    (Rendering|SetVisibility :self (Variables|Default|Get{n}) :bNewVisibility {"(== k 2)" if n.startswith(("Tray", "Glass")) else "false"} :bPropagateToChildren false)' for n, *_ in ACC)
    wr(barman, 'PickLook', f'''
    (fn PickLook ()
      ; looks at the nearest player in front of him (5 m), at most 70 degrees off his post, else straight ahead
      (Variables|Barman|SetTargetYaw (Variables|Barman|GetBaseYaw))
      (Variables|Barman|SetBestD 500.0)
      (bind me (Transformation|GetActorLocation))
      (bind fwd (Math|Vector|GetForwardVector (Math|Rotator|MakeRotator :Roll 0.0 :Pitch 0.0 :Yaw (Variables|Barman|GetBaseYaw))))
      (for c (Actor|GetAllActorsOfClass :ActorClass {CHAR})
        (if (Pawn|IsPlayerControlled :self c)
          (bind cl (Transformation|GetActorLocation :self c))
          (bind d (Math|Vector|Distance2D(Vector) cl me))
          (if (and (< d (Variables|Barman|GetBestD)) (> (Math|Vector|DotProduct fwd (Math|Vector|Normalize (- cl me))) 0.2))
            (Variables|Barman|SetBestD d)
            (bind dy (- (.yaw (Math|Rotator|FindLookatRotation :Start me :Target cl)) (Variables|Barman|GetBaseYaw)))
            (bind dw (- dy (* 360.0 (Math|Float|Round (/ dy 360.0)))))
            (Variables|Barman|SetTargetYaw (+ (Variables|Barman|GetBaseYaw) (Math|Float|Max(Float) -70.0 (Math|Float|Min(Float) 70.0 dw))))))))
    ''')
    # the user, 2026-11-05 ("the server is not animated"): on the host a waiter's acceleration is 0 (AI path following, a plain Character), so ABP_Unarmed's ShouldMove stays false and he glides in
    # his idle; a client gets a replicated acceleration and saw him walk. The waiters now play their own clips (Tools/anim/waiter_clips.py: forearm under the tray), chosen by speed on every machine
    _SKMC = 'GW|Call|/Script/Engine.SkeletalMeshComponent'
    wr(barman, 'WaiterAnim', f'''
    (fn WaiterAnim ()
      (bind sp (Math|Vector|VectorLength (Transformation|GetVelocity)))
      (bind walk (> sp 25.0))
      (bind m (Variables|Character|GetMesh))
      (if (or (not (Variables|Barman|GetClipOn)) (!= walk (Variables|Barman|GetWalkClip)))
        (Variables|Barman|SetClipOn true)
        (Variables|Barman|SetWalkClip walk)
        (if walk
          ({_SKMC}|PlayAnimation :self m :NewAnimToPlay "/Game/GW/Anims/Waiter/AS_GW_Waiter_Walk.AS_GW_Waiter_Walk" :bLooping true)
          (else
            ({_SKMC}|PlayAnimation :self m :NewAnimToPlay "/Game/GW/Anims/Waiter/AS_GW_Waiter_Idle.AS_GW_Waiter_Idle" :bLooping true))))
      (if walk
        ({_SKMC}|SetPlayRate :self m :Rate (Math|Float|Clamp(Float) :Value (/ sp 150.0) :Min 0.5 :Max 1.3))))
    ''')
    wr(barman, 'EventGraph', f'''
    (event EventBeginPlay
      (bind m (Variables|Character|GetMesh))
      (bind k (Variables|Barman|GetVendorKind))
      (if ({ISVALID} :Object (Variables|Barman|GetSkin))
        (Components|SkeletalMesh|SetSkeletalMeshAsset :self m :NewMesh (Variables|Barman|GetSkin))
    {acc_hide}
        (else
          (Components|SkeletalMesh|SetSkeletalMeshAsset :self m :NewMesh {ap(MANNY)})
    {acc_vis}
          (if ({ISVALID} :Object (Variables|Barman|GetShirtMat))
            (Rendering|Material|SetMaterial :self m :ElementIndex 1 :Material (Variables|Barman|GetShirtMat))
            (Rendering|Material|SetMaterial :self m :ElementIndex 0 :Material (Variables|Barman|GetLegsMat)))))
      (if ({ISVALID} :Object (Variables|Barman|GetTrayMesh))
        (Components|StaticMesh|SetStaticMesh :self (Variables|Default|GetTray) :NewMesh (Variables|Barman|GetTrayMesh))
        (Rendering|Material|SetMaterial :self (Variables|Default|GetTray) :ElementIndex 0 :Material (GW|Call|/Script/Engine.StaticMesh|GetMaterial :self (Variables|Barman|GetTrayMesh) :MaterialIndex 0)))
      (Components|SkeletalMesh|SetAnimInstanceClass :self m :NewClass "{ABP}.{ABP.rsplit('/', 1)[1]}_C")
      (Variables|Barman|SetBaseYaw (.yaw (Transformation|GetActorRotation)))
      (Variables|Barman|SetLookYaw (Variables|Barman|GetBaseYaw))
      (Variables|Barman|SetTargetYaw (Variables|Barman|GetBaseYaw))
      (if (Variables|Barman|GetMobile)
        (Class|CharacterMovementComponent|SetMaxWalkSpeed :self (Variables|Character|GetCharacterMovement) :MaxWalkSpeed 150.0)
        (Class|CharacterMovementComponent|SetOrientRotationtoMovement :self (Variables|Character|GetCharacterMovement) :bOrientRotationToMovement true)
        (Variables|Pawn|SetUseControllerRotationYaw false)
        (else
          (Utilities|Time|SetTimerbyFunctionName :Object self :FunctionName "PickLook" :Time 0.3 :bLooping true)))
      (Development|PrintString :InString (cat "GW: vendor " k " at " (Transformation|GetActorLocation) " mesh=" (Utilities|GetDisplayName :Object (Components|SkeletalMesh|GetSkeletalMeshAsset :self m)) " neck=" (Transformation|GetSocketLocation :self m :InSocketName "neck_01") " head=" (Transformation|GetSocketLocation :self m :InSocketName "head") " hand_r=" (Transformation|GetSocketLocation :self m :InSocketName "hand_r") " bowtie=" (Transformation|GetWorldLocation :self (Variables|Default|GetBowTie)) " cap=" (Transformation|GetWorldLocation :self (Variables|Default|GetCap)) " tray=" (Transformation|GetWorldLocation :self (Variables|Default|GetTray))) :bPrintToScreen false))

    (event EventTick (DeltaSeconds)
      (if (Variables|Barman|GetMobile)
        (CallFunction|WaiterAnim)
        (return))
      (Variables|Barman|SetLookYaw (+ (Variables|Barman|GetLookYaw) (* (- (Variables|Barman|GetTargetYaw) (Variables|Barman|GetLookYaw)) (Math|Float|Min(Float) 1.0 (* DeltaSeconds 2.5)))))
      (Transformation|SetActorRotation :self self :NewRotation (Math|Rotator|MakeRotator :Roll 0.0 :Pitch 0.0 :Yaw (Variables|Barman|GetLookYaw)) :bTeleportPhysics false))
    ''')
    finish(barman)


    def vendor_defaults(bp, kind, mobile, shirt, legs, tag):
        d = cdo(bp)
        d.set_editor_property('replicates', True)
        d.set_editor_property('always_relevant', True)
        d.set_editor_property('replicate_movement', mobile)
        d.set_editor_property('auto_possess_ai', unreal.AutoPossessAI.SPAWNED if mobile else unreal.AutoPossessAI.DISABLED)
        d.set_editor_property('VendorKind', kind)
        d.set_editor_property('Mobile', mobile)
        if _torso and _legs:
            d.set_editor_property('ShirtMat', mic(f'MI_GW_{tag}Shirt', _torso, {'Paint Tint': shirt}))
            d.set_editor_property('LegsMat', mic(f'MI_GW_{tag}Trousers', _legs, {'Paint Tint': legs}))


    vendor_defaults(barman, 0, False, (0.82, 0.8, 0.74), (0.02, 0.02, 0.022), 'Barman')
    compile_bp(barman, quiet=True)
    save(barman)
    junkie = load_or_create_bp('BP_GW_Junkie', barman.generated_class(), folder=SHOP)
    clean_graph(junkie, 'EventGraph')
    compile_bp(junkie, quiet=True)
    vendor_defaults(junkie, 1, False, (0.22, 0.2, 0.09), (0.11, 0.075, 0.05), 'Junkie')
    finish(junkie)
    waiter = load_or_create_bp('BP_GW_Waiter', barman.generated_class(), folder=SHOP)
    clean_graph(waiter, 'EventGraph')
    compile_bp(waiter, quiet=True)
    vendor_defaults(waiter, 2, True, (0.93, 0.93, 0.9), (0.02, 0.02, 0.022), 'Waiter')
    finish(waiter)
else:
    barman, junkie, waiter = (load_bp(n, SHOP) for n in ('BP_GW_Barman', 'BP_GW_Junkie', 'BP_GW_Waiter'))

if want('ps'):
    # ================================================================ player state: money and items (replicated)
    PSV = [('Money', 'int'), ('Ammo', 'int'), ('Smokes', 'int'), ('Gases', 'int'), ('Traps', 'int'), ('Bombs', 'int'), ('Crackers', 'int'),
           ('TurretAmmo', 'int'), ('HasLamp', 'bool'), ('HasSwapGun', 'bool'), ('SwapReadyAt', 'float'), ('ShopNote', 'string'),
           ('ShopNoteAt', 'float'), ('ShopBuys', 'int')]
    for v, t in PSV:
        ensure_var(psb, v, t, rep=REP.REPLICATED, category='Shop')
    for v, t in (('LastPianoPay', 'float'), ('NextGuestFire', 'float')):
        ensure_var(psb, v, t, category='Shop')
    ensure_var(psb, 'GunActor', obj_class=gun.generated_class(), category='Shop')
    compile_bp(psb, quiet=True)
    cdo(psb).set_editor_property('LastPianoPay', -1000.0)
    compile_bp(psb)
    save(psb)
else:
    pass

# ================================================================ door table (Tools/manor_layout.json, ground floor)
_lay = json.load(open(LAYOUT, encoding='utf-8'))
# the manor's doors + the cloakroom (detectives' waiting room) + the WC added by the level agent (west end of corridor_w,
# door x 345-365, y 2110-2230); the trap hangs 8 cm under the lintel
_doors = list(_lay['doors']) + [dict(_lay['cloakroom']['door'])] + [{'axis': 'x', 'at': 355, 'center': 2170, 'width': 120, 'height': 250}]
DOORS = []
for d in _doors:
    top = float(d.get('height', _lay.get('door_height', 270))) - 8.0
    if d['axis'] == 'x':
        DOORS.append((float(d['at']), float(d['center']), 1.0, d['width'] / 2.0, top))
    else:
        DOORS.append((float(d['center']), float(d['at']), 0.0, d['width'] / 2.0, top))
print('doors', len(DOORS))


def door_vars(bp):
    ensure_var(bp, 'DoorPts', struct=V3, array=True, category='Shop')
    ensure_var(bp, 'DoorHalfW', 'float', array=True, category='Shop')
    ensure_var(bp, 'DoorTop', 'float', array=True, category='Shop')


def door_defaults(bp):
    c = cdo(bp)
    c.set_editor_property('DoorPts', [unreal.Vector(x, y, z) for x, y, z, _, _ in DOORS])
    c.set_editor_property('DoorHalfW', [w for _, _, _, w, _ in DOORS])
    c.set_editor_property('DoorTop', [t for *_, t in DOORS])


FIND_DOOR = f'''
(fn FindDoor (Loc)
  ; the doorway the point stands in (across the wall < 1.1 m, within the opening): its lintel point, axis, half width
  (Variables|Default|SetBest -1)
  (Variables|Default|SetBestD 1000000.0)
  (bind pts (Variables|Shop|GetDoorPts))
  (bind hw (Variables|Shop|GetDoorHalfW))
  (for i (range (Utilities|Array|Length pts))
    (bind p (Utilities|Array|Get(acopy) pts i))
    (bind ax (> (.z p) 0.5))
    (bind across (Math|Float|Absolute(Float) (select ax (- (.x Loc) (.x p)) (- (.y Loc) (.y p)))))
    (bind along (Math|Float|Absolute(Float) (select ax (- (.y Loc) (.y p)) (- (.x Loc) (.x p)))))
    (if (and (and (< across 110.0) (< along (+ (Utilities|Array|Get(acopy) hw i) 30.0))) (< across (Variables|Default|GetBestD)))
      (Variables|Default|SetBestD across)
      (Variables|Default|SetBest i)))
  (bind b (Variables|Default|GetBest))
  (if (or (< b 0) (> (.z Loc) 420.0))
    (return {mv(0, 0, 0)} false 0.0 false))
  (bind q (Utilities|Array|Get(acopy) pts b))
  (return (Math|Vector|MakeVector (.x q) (.y q) (Utilities|Array|Get(acopy) (Variables|Shop|GetDoorTop) b)) (> (.z q) 0.5) (Utilities|Array|Get(acopy) hw b) true))
'''
DOOR_OUT = [('Top', V3), ('AxisX', 'bool'), ('HalfW', 'float'), ('Ok', 'bool')]

PSG = lambda v, ps='ps': f'(GW|Get|BP_GW_PlayerState|{v} :self {ps})'
PSS = lambda v, val, ps='ps': f'(GW|Set|BP_GW_PlayerState|{v} :self {ps} :{v} {val})'
PSADD = lambda v, n, ps='ps': PSS(v, f'(+ {PSG(v, ps)} {n})', ps)
PAY = lambda ps, amount, note: f'(CallFunction|ShopPay :PS {ps} :Amount {amount} :Note {note})'
NOTE = lambda ps, note: PAY(ps, 0, note)
NAMES = {i: q(n) for i, n, *_ in ITEMS}
PRICES = {i[0]: i[3] for i in ITEMS}
JPRICES = {i[0]: i[4] for i in ITEMS}
COUNT_OF = {1: 'Ammo', 2: 'Smokes', 4: 'Gases', 5: 'Traps', 6: 'Bombs', 9: 'Crackers'}

if want('gm'):
    # ================================================================ game mode (server)
    gm = load_bp('BP_GW_GameMode')
    PSCLS = psb.generated_class()
    for v, t in (('ShopPhase', 'int'), ('NextSurvive', 'float'), ('LoudN', 'int'), ('LoudAt', 'float'), ('LoudIdx', 'int'),
                 ('BlastKills', 'int'), ('WantGun', 'bool')):
        ensure_var(gm, v, t, category='Shop')
    ensure_var(gm, 'Barman', obj_class=unreal.Actor, category='Shop')
    ensure_var(gm, 'TraceIgnore', obj_class=unreal.Actor, array=True, category='Shop')
    ensure_var(gm, 'TmpV', struct=V3, category='Shop')
    ensure_var(gm, 'BlastOwner', obj_class=PSCLS, category='Shop')
    ensure_var(gm, 'GunPawn', obj_class=chc, category='Shop')
    ensure_var(gm, 'NoGun', obj_class=gun.generated_class(), category='Shop')
    ensure_var(gm, 'TmpShrink', obj_class=shrink.generated_class(), category='Shop')
    ensure_var(gm, 'GasScale', 'float', category='Shop')
    ensure_var(gm, 'NoShrink', obj_class=shrink.generated_class(), category='Shop')
    ensure_var(gm, 'Junkie', obj_class=unreal.Actor, category='Shop')
    ensure_var(gm, 'JunkieChecked', 'bool', category='Shop')
    ensure_var(gm, 'Waiters', obj_class=waiter.generated_class(), array=True, category='Shop')
    ensure_var(gm, 'WaiterOk', 'bool', category='Shop')
    ensure_var(gm, 'WaiterDest', struct=V3, category='Shop')
    ensure_var(gm, 'WaiterPick', obj_class=chc, category='Shop')
    door_vars(gm)
    P = unreal.Pawn
    GMF = {
        'ShopTick': [], 'RewardNPCKill': [('Killer', P), ('Victim', chc)], 'OnInstrumentPlayed': [('Who', P), ('I', 'int')],
        'ShopPay': [('PS', PSCLS), ('Amount', 'int'), ('Note', 'string')], 'LoudScream': [('Victim', chc)],
        'GuestShoot': [('Shooter', chc), ('Start', V3), ('Dir', V3)], 'GuestHit': [('Shooter', chc), ('Victim', chc), ('Dir', V3)],
        'ShopBuy': [('PS', PSCLS), ('Id', 'int'), ('Kind', 'int'), ('At', V3)], 'JunkieTick': [], 'UseItem': [('PS', PSCLS), ('Ch', chc), ('Id', 'int'), ('Yaw', 'float')],
        'ThrowSmoke': [('Ch', chc), ('Yaw', 'float')], 'UseGas': [('Ch', chc)], 'PlaceTrap': [('PS', PSCLS), ('Ch', chc)],
        'DropBomb': [('PS', PSCLS), ('Ch', chc)], 'TrapTick': [], 'TrapFire': [('T', trap.generated_class()), ('Victim', chc)],
        'BombTick': [], 'BombWarn': [('B', bomb.generated_class())], 'BombBlast': [('B', bomb.generated_class())], 'DefuseBomb': [('B', bomb.generated_class()), ('P', P)],
        'GunTick': [], 'GunFor': [('PS', PSCLS)], 'SurviveTick': [], 'ShopCleanup': [], 'SpawnBarman': [],
        'SpawnVendors': [], 'SpawnJunkie': [], 'WaiterTick': [], 'WaiterThink': [('W', waiter.generated_class())],
        'ThrowPoint': [('Ch', chc), ('Yaw', 'float')], 'ThrowCracker': [('Ch', chc), ('Yaw', 'float')],
        'CrackerTick': [], 'CrackerBang': [('Loc', V3), ('First', 'bool')],
    }
    for f, ins in GMF.items():
        ensure_fn(gm, f, inputs=ins)
    ensure_fn(gm, 'FindDoor', inputs=[('Loc', V3)], outputs=DOOR_OUT)
    ensure_fn(gm, 'ItemPrice', inputs=[('Id', 'int'), ('Kind', 'int')], outputs=[('Price', 'int')], pure=True)
    ensure_fn(gm, 'FarFromDoors', inputs=[('Loc', V3)], outputs=[('Ok', 'bool')])
    ensure_fn(gm, 'CharOfPS', inputs=[('PS', PSCLS)], outputs=[('Ch', chc)])
    ensure_fn(gm, 'IsSmokeBetween', inputs=[('A', V3), ('B', V3)], outputs=[('Blocked', 'bool')], pure=True)
    ensure_fn(gm, 'WaiterGo', inputs=[('W', waiter.generated_class()), ('Dest', V3)])
    ensure_fn(gm, 'WaiterLeave')
    ensure_var(gm, 'WaiterMode', 'int', category='Shop')
    ensure_var(gm, 'NextJunkieWarn', 'float', category='Shop')
    ensure_var(gm, 'WaiterFollow', obj_class=unreal.Pawn, category='Shop')
    ensure_fn(gm, 'ItemName', inputs=[('Id', 'int')], outputs=[('Name', 'string')], pure=True)
    compile_bp(gm, quiet=True)
    local(gm, 'FindDoor', 'Best', 'int')
    local(gm, 'FindDoor', 'BestD', 'float')
    door_defaults(gm)
    cdo(gm).set_editor_property('GasScale', 0.3)

    G = {}
    G['ItemPrice'] = f'(fn ItemPrice (Id Kind) (return (select (== Kind 1) {sel("Id", JPRICES, 0)} {sel("Id", PRICES, 0)})))'
    G['ItemName'] = f'(fn ItemName (Id) (return {sel("Id", NAMES, q("?"))}))'
    G['FindDoor'] = FIND_DOOR
    G['ShopPay'] = f'''
    (fn ShopPay (PS Amount Note)
      (if (not ({ISVALID} :Object PS))
        (return))
      (GW|Set|BP_GW_PlayerState|Money :self PS :Money (Math|Integer|Max(Integer) 0 (+ (GW|Get|BP_GW_PlayerState|Money :self PS) Amount)))
      (if (> (Utilities|String|Len Note) 0)
        (GW|Set|BP_GW_PlayerState|ShopNote :self PS :ShopNote Note)
        (GW|Set|BP_GW_PlayerState|ShopNoteAt :self PS :ShopNoteAt (CallFunction|Now)))
      (Development|PrintString :InString (cat "GW: shop " (PlayerState|GetPlayerName :self PS) " " Amount " $ -> " (GW|Get|BP_GW_PlayerState|Money :self PS) " $ : " Note) :bPrintToScreen false))
    '''
    G['OnInstrumentPlayed'] = f'''
    (fn OnInstrumentPlayed (Who I)
      ; any instrument (piano, harp, drums, bass; s33): +25 $ for a guest, once per 30 s per player
      (if (not ({ISVALID} :Object Who))
        (return))
      (bind ps (CallFunction|PSOf :P Who))
      (if (not ({ISVALID} :Object ps))
        (return))
      (if (!= {PSG('GWRole')} 1)
        (return))
      (if (< (CallFunction|Now) (+ {PSG('LastPianoPay')} 30.0))
        (Development|PrintString :InString (cat "GW: instrument " I " pay skipped (once per 30 s)") :bPrintToScreen false)
        (return))
      {PSS('LastPianoPay', '(CallFunction|Now)')}
      {PAY('ps', 25, q('+25 $ : quel vacarme !'))})
    '''
    G['LoudScream'] = f'''
    (fn LoudScream (Victim)
      ; the victim's own scream again, loud and in 3D over the whole manor (BP_GW_LoudCue, ATT_GW_Far); 5 per second at most
      (if (not ({ISVALID} :Object Victim))
        (return))
      (bind now (CallFunction|Now))
      (if (> (- now (Variables|Shop|GetLoudAt)) 1.0)
        (Variables|Shop|SetLoudAt now)
        (Variables|Shop|SetLoudN 0))
      (if (>= (Variables|Shop|GetLoudN) 5)
        (return))
      (Variables|Shop|SetLoudN (+ (Variables|Shop|GetLoudN) 1))
      (Variables|Shop|SetLoudIdx (% (GW|Get|BP_GW_Character|Cue :self Victim) 10000))
      (bind cats (Variables|GW|GetBankCat))
      (if (< (Variables|Shop|GetLoudIdx) (Utilities|Array|Length cats))
        (if (!= (Utilities|Array|Get(acopy) cats (Variables|Shop|GetLoudIdx)) 1)
          (Variables|Shop|SetLoudIdx (CallFunction|PickSound :Cat 1 :Fem (CallFunction|GenderOf :Ch Victim))))
        (else
          (Variables|Shop|SetLoudIdx (CallFunction|PickSound :Cat 1 :Fem (CallFunction|GenderOf :Ch Victim)))))
      (if (< (Variables|Shop|GetLoudIdx) 0)
        (return))
      (bind a (Game|SpawnActorfromClass :Class "{LOUD}" :SpawnTransform (Math|Transform|MakeTransform :Location (+ (Transformation|GetActorLocation :self Victim) {mv(0, 0, 60)})) :CollisionHandlingOverride "AlwaysSpawn"))
      (GW|Set|{LOUD}|Vol :self a :Vol 2.4)
      (GW|Set|{LOUD}|Idx :self a :Idx (Variables|Shop|GetLoudIdx))
      (Development|PrintString :InString (cat "GW: loud scream idx=" (Variables|Shop|GetLoudIdx) " at " (Transformation|GetActorLocation :self Victim)) :bPrintToScreen false))
    '''
    G['RewardNPCKill'] = f'''
    (fn RewardNPCKill (Killer Victim)
      (CallFunction|LoudScream :Victim Victim)
      (if (not ({ISVALID} :Object Killer))
        (return))
      (bind ps (CallFunction|PSOf :P Killer))
      (if (not ({ISVALID} :Object ps))
        (return))
      (if (== {PSG('GWRole')} 2)
        (return))
      {PAY('ps', 100, q('+100 $ : un invité de moins…'))})
    '''
    G['GuestShoot'] = f'''
    (fn GuestShoot (Shooter Start Dir)
      (if (not ({ISVALID} :Object Shooter))
        (return))
      (if (or (GW|Get|BP_GW_Character|IsDead :self Shooter) (GW|Get|BP_GW_Character|IsSeeker :self Shooter))
        (return))
      (bind ps (CallFunction|PSOf :P Shooter))
      (if (not ({ISVALID} :Object ps))
        (return))
      (if (<= {PSG('Ammo')} 0)
        (return))
      (if (not (CallFunction|CanShoot :Shooter Shooter))
        {NOTE('ps', '(select (== (GW|Get|BP_GW_GameState|Phase :self (CallFunction|GetGS)) 2) "Pas de tir au fusil pour l' + "'" + 'instant (tourelle ?)." "Le fusil ne sert que pendant la chasse.")')}
        (return))
      (if (< (CallFunction|Now) {PSG('NextGuestFire')})
        (return))
      {PSS('NextGuestFire', '(+ (CallFunction|Now) 0.8)')}
      {PSADD('Ammo', -1)}
      ; the trace ignores the shooter's own capsule
      (Utilities|Array|Clear (Variables|Shop|GetTraceIgnore))
      (Utilities|Array|Add :TargetArray (Variables|Shop|GetTraceIgnore) :NewItem Shooter)
      (bind traceEnd (+ Start (* Dir 8000.0)))
      (bind (hit ok) (Collision|LineTraceByProfile :Start Start :End traceEnd :ProfileName "BlockAll" :bTraceComplex false :ActorsToIgnore (Variables|Shop|GetTraceIgnore) :bIgnoreSelf true))
      (bind (bBlock bInit hTime hDist hLoc hImpact hNormal hImpNormal hPhys hActor) (Collision|BreakHitResult hit))
      ; shot FX on every machine + the manor's gunshot panic (ShotCounter, like ServerFire)
      (GW|Set|BP_GW_Character|ShotEnd :self Shooter :ShotEnd (select ok hImpact traceEnd))
      (GW|Set|BP_GW_Character|ShotTime :self Shooter :ShotTime (CallFunction|Now))
      (GW|Set|BP_GW_Character|ShotCounter :self Shooter :ShotCounter (+ (GW|Get|BP_GW_Character|ShotCounter :self Shooter) 1))
      (Development|PrintString :InString (cat "GW: guest shot by " (CallFunction|NameOf :P Shooter) " hit " (Utilities|GetDisplayName :Object hActor) " ammo left " {PSG('Ammo')}) :bPrintToScreen false)
      (if ok
        (bind v (Utilities|Casting|CastToBP_GW_Character hActor)
          (:then (CallFunction|GuestHit :Shooter Shooter :Victim v :Dir Dir))
          (:CastFailed))))
    '''
    G['GuestHit'] = f'''
    (fn GuestHit (Shooter Victim Dir)
  ; anyone may shoot a zombie, a zombified detective too (s40_events2.py)
  (if (== (GW|Get|BP_GW_Character|Kind :self Victim) 4)
    (if (not (GW|Get|BP_GW_Character|IsDead :self Victim))
      (Variables|GW|SetGunContext true)
      (CallFunction|ZombieDown :Victim Victim :Impulse (* Dir 700.0)))
    (return))
      (if (GW|Get|BP_GW_Character|IsDead :self Victim)
        (return))
      (bind kind (GW|Get|BP_GW_Character|Kind :self Victim))
      (bind sname (CallFunction|NameOf :P Shooter))
      (if (== kind 3)
        (CallFunction|Announce :Text "Les balles ricochent sur le robot !")
        (return))
      (if (== kind 2)
        (CallFunction|Announce :Text (cat sname " a fait sauter le kamikaze !"))
        (CallFunction|Explode :Loc (Transformation|GetActorLocation :self Victim) :Radius 650.0 :Cause "a été soufflé par le kamikaze")
        (return))
      (if (== kind 1)
        (CallFunction|DeathCry :Victim Victim)
        (GW|Call|BP_GW_Character|Die :self Victim :Impulse (* Dir 700.0))
        (CallFunction|Announce :Text (cat sname " a abattu un bandit !"))
        (return))
      (if (Pawn|IsPlayerControlled :self Victim)
        (bind vname (CallFunction|NameOf :P Victim))
        (if (GW|Get|BP_GW_Character|IsSeeker :self Victim)
          (CallFunction|Announce :Text (cat sname " a abattu le détective " vname " !"))
          {PAY('(CallFunction|PSOf :P Shooter)', 100, q('+100 $ : un détective de moins !'))}
          (else
            (CallFunction|Announce :Text (cat vname " a été abattu par un autre invité !"))))
        (CallFunction|DeathCry :Victim Victim)
        (CallFunction|KillPlayer :Victim Victim :Impulse (* Dir 700.0))
        (CallFunction|UpdateCounts)
        (CallFunction|CheckWin)
        (return))
      ; an NPC: dies (scream, neighbours shout, respawn later), +100 $ and the loud scream, the manor panics
      (CallFunction|HurtCharacter :Victim Victim :Amount 1000.0 :Impulse (* Dir 700.0) :Cause "")
      (CallFunction|RewardNPCKill :Killer Shooter :Victim Victim)
      (CallFunction|StartPanicCause :Loc (Transformation|GetActorLocation :self Victim) :Dur 15.0 :Cause 1))
    '''
    gives = '\n'.join(f'  (if (== Id {i})\n    {PSADD(COUNT_OF[i], 1, "PS")})' for i in (1, 2, 4, 5, 6, 9))
    G['ShopBuy'] = f'''
    (fn ShopBuy (PS Id Kind)
      ; Kind: who sells (0 barman, 1 junkie, 2 waiter); the junkie has his own prices and the only firecrackers
      (if (or (< Id 1) (> Id {NITEMS}))
        (return))
      (if (and (== Id 9) (!= Kind 1))
        {NOTE('PS', q('Des pétards ? Demandez au junkie, dans les toilettes…'))}
        (return))
      (bind price (CallFunction|ItemPrice :Id Id :Kind Kind))
      (bind name (CallFunction|ItemName :Id Id))
      (if (and (== Id 3) {PSG('HasLamp', 'PS')})
        {NOTE('PS', q('Vous avez déjà une lampe torche.'))}
        (return))
      (if (and (== Id 8) {PSG('HasSwapGun', 'PS')})
        {NOTE('PS', q("Vous avez déjà le pistolet d'échange."))}
        (return))
      (if (< {PSG('Money', 'PS')} price)
        {NOTE('PS', '(cat "Pas assez d' + "'" + 'argent pour : " name " (" price " $).")')}
        (if (> (Math|Vector|VectorLength At) 1.0)
          (CallFunction|StaffSay :Cat (select (== Kind 1) 63 (select (== Kind 2) 62 15)) :Ctx 5 :Loc At))
        (return))
      {PAY('PS', '(- 0 price)', '""')}
    {gives}
      (if (== Id 3)
        {PSS('HasLamp', 'true', 'PS')})
      (if (== Id 7)
        {PSADD('TurretAmmo', 60, 'PS')})
      (if (== Id 8)
        {PSS('HasSwapGun', 'true', 'PS')}
        {PSS('SwapReadyAt', '0.0', 'PS')})
      {PSADD('ShopBuys', 1, 'PS')}
      {NOTE('PS', '(cat "Acheté : " name " (" ' + sel('Id', {i: q(h) for i, h in HINT.items()}, '""') + ' ")")')}
      ; the vendor's line: a warning for the dangerous things (rifle, trap, bomb), else a sale line
      (if (> (Math|Vector|VectorLength At) 1.0)
        (CallFunction|StaffSay :Cat (select (== Kind 1) 63 (select (== Kind 2) 62 15)) :Ctx (select (or (== Id 1) (or (== Id 5) (== Id 6))) 6 4) :Loc At))
      (Development|PrintString :InString (cat "GW: sold " name " for " price " $ (vendor " Kind ")") :bPrintToScreen false))
    '''
    use_case = lambda i, var, none_msg, call: f'''  (if (== Id {i})
        (if (<= {PSG(var, 'PS')} 0)
          {NOTE('PS', q(none_msg))}
          (return))
        {call}
        (return))'''
    G['UseItem'] = f'''
    (fn UseItem (PS Ch Id Yaw)
    {use_case(2, 'Smokes', 'Pas de bombe fumigène : le barman en vend (salle de billard).', PSADD('Smokes', -1, 'PS') + chr(10) + '    (CallFunction|ThrowSmoke :Ch Ch :Yaw Yaw)')}
    {use_case(4, 'Gases', 'Pas de gaz rétrécissant : le barman en vend.', PSADD('Gases', -1, 'PS') + chr(10) + '    (CallFunction|UseGas :Ch Ch)')}
    {use_case(5, 'Traps', 'Pas de piège : le barman en vend.', '(CallFunction|PlaceTrap :PS PS :Ch Ch)')}
    {use_case(6, 'Bombs', 'Pas de bombe : le barman en vend.', PSADD('Bombs', -1, 'PS') + chr(10) + '    (CallFunction|DropBomb :PS PS :Ch Ch)')}
    {use_case(9, 'Crackers', 'Pas de pétard : le junkie en vend (toilettes).', PSADD('Crackers', -1, 'PS') + chr(10) + '    (CallFunction|ThrowCracker :Ch Ch :Yaw Yaw)')})
    '''
    G['ThrowPoint'] = f'''
    (fn ThrowPoint (Ch Yaw)
      ; where a thrown object lands (TmpV): 2.5 m ahead along the aim, stopped by a wall, then down to the floor
      (bind here (Transformation|GetActorLocation :self Ch))
      (bind dir (Math|Vector|GetForwardVector (Math|Rotator|MakeRotator :Roll 0.0 :Pitch 0.0 :Yaw Yaw)))
      (bind chest (+ here {mv(0, 0, 40)}))
      (Utilities|Array|Clear (Variables|Shop|GetTraceIgnore))
      (Utilities|Array|Add :TargetArray (Variables|Shop|GetTraceIgnore) :NewItem Ch)
      (bind (h1 ok1) (Collision|LineTraceByChannel :Start chest :End (+ chest (* dir 250.0)) :TraceChannel "Visibility" :bTraceComplex false :ActorsToIgnore (Variables|Shop|GetTraceIgnore) :bIgnoreSelf true))
      (bind (b1 i1 t1 d1 l1 imp1 n1 in1 p1 a1) (Collision|BreakHitResult h1))
      (Variables|Shop|SetTmpV (select ok1 (- imp1 (* dir 40.0)) (+ chest (* dir 250.0))))
      (bind mid (Variables|Shop|GetTmpV))
      (bind (h2 ok2) (Collision|LineTraceByChannel :Start mid :End (- mid {mv(0, 0, 400)}) :TraceChannel "Visibility" :bTraceComplex false :ActorsToIgnore (Variables|Shop|GetTraceIgnore) :bIgnoreSelf true))
      (bind (b2 i2 t2 d2 l2 imp2 n2 in2 p2 a2) (Collision|BreakHitResult h2))
      (Variables|Shop|SetTmpV (select ok2 imp2 (- mid {mv(0, 0, 136)}))))
    '''
    G['ThrowSmoke'] = f'''
    (fn ThrowSmoke (Ch Yaw)
      (CallFunction|ThrowPoint :Ch Ch :Yaw Yaw)
      (bind s (Game|SpawnActorfromClass :Class "{SMOKE}" :SpawnTransform (Math|Transform|MakeTransform :Location (Variables|Shop|GetTmpV)) :CollisionHandlingOverride "AlwaysSpawn"))
      (GW|Set|{SMOKE}|From :self s :From (+ (Transformation|GetActorLocation :self Ch) {mv(0, 0, 50)}))
      ; the guests around the cloud react (voice category 73 smoke_react)
      (Variables|GW|SetStamp (+ (Variables|GW|GetStamp) 1))
      (CallFunction|QueueSay :Ch (CallFunction|NearestNPC :Loc (Variables|Shop|GetTmpV) :MaxD 900.0) :Cat 73 :Delay 1.2)
      (CallFunction|QueueSay :Ch (CallFunction|NearestNPC :Loc (Variables|Shop|GetTmpV) :MaxD 900.0) :Cat 73 :Delay 3.0)
      (Development|PrintString :InString (cat "GW: smoke thrown by " (CallFunction|NameOf :P Ch) " lands at " (Transformation|GetActorLocation :self s)) :bPrintToScreen false))
    '''
    G['ThrowCracker'] = f'''
    (fn ThrowCracker (Ch Yaw)
      (CallFunction|ThrowPoint :Ch Ch :Yaw Yaw)
      (bind s (Game|SpawnActorfromClass :Class "{CRACKER}" :SpawnTransform (Math|Transform|MakeTransform :Location (Variables|Shop|GetTmpV)) :CollisionHandlingOverride "AlwaysSpawn"))
      (GW|Set|{CRACKER}|From :self s :From (+ (Transformation|GetActorLocation :self Ch) {mv(0, 0, 50)}))
      (Development|PrintString :InString (cat "GW: firecracker thrown by " (CallFunction|NameOf :P Ch) " lands at " (Transformation|GetActorLocation :self s)) :bPrintToScreen false))
    '''
    G['CrackerTick'] = f'''
    (fn CrackerTick ()
      ; each live firecracker: its next bang is due (from its own T0 on the server) -> a gunshot heard everywhere
      (for c (Actor|GetAllActorsOfClass :ActorClass "{CRACKER}")
        (bind nb (GW|Get|{CRACKER}|NextBang :self c))
        (if (< nb {len(BANGS)})
          (if (>= (- (Utilities|Time|GetGameTimeinSeconds) (GW|Get|{CRACKER}|T0 :self c)) {sel('nb', dict(enumerate(BANGS)), 99.0)})
            (CallFunction|CrackerBang :Loc (+ (Transformation|GetActorLocation :self c) {mv(0, 0, 20)}) :First (== nb 0))
            (GW|Set|{CRACKER}|NextBang :self c :NextBang (+ nb 1))))))
    '''
    G['CrackerBang'] = '''
    (fn CrackerBang (Loc First)
      ; a gunshot from the bank (heard everywhere, like a real shot); the first bang sends the manor running
      (CallFunction|WorldSound :Cat 29 :Loc Loc)
      (if First
        (CallFunction|StartPanicCause :Loc Loc :Dur 12.0 :Cause 1)
        (Development|PrintString :InString (cat "GW: firecracker goes off at " Loc) :bPrintToScreen false)))
    '''
    G['UseGas'] = f'''
    (fn UseGas (Ch)
      (bind here (Transformation|GetActorLocation :self Ch))
      (Game|SpawnActorfromClass :Class "{GAS}" :SpawnTransform (Math|Transform|MakeTransform :Location (- here {mv(0, 0, 92)})) :CollisionHandlingOverride "AlwaysSpawn")
      ; a second dose while small extends the 20 s
      (Variables|Shop|SetTmpShrink (Variables|Shop|GetNoShrink))
      (for s (Actor|GetAllActorsOfClass :ActorClass "{SHRINK}")
        (if (and (== (GW|Get|{SHRINK}|Target :self s) Ch) (> (GW|Get|{SHRINK}|Until :self s) (+ (CallFunction|Now) 0.2)))
          (Variables|Shop|SetTmpShrink s)))
      (bind old (Variables|Shop|GetTmpShrink))
      (if ({ISVALID} :Object old)
        (GW|Set|{SHRINK}|Until :self old :Until (+ (CallFunction|Now) 20.0))
        (else
          (bind sh (Game|SpawnActorfromClass :Class "{SHRINK}" :SpawnTransform (Math|Transform|MakeTransform :Location here) :CollisionHandlingOverride "AlwaysSpawn"))
          (GW|Set|{SHRINK}|Until :self sh :Until (+ (CallFunction|Now) 20.0))
          (GW|Set|{SHRINK}|ToScale :self sh :ToScale (Variables|Shop|GetGasScale))
          (GW|Set|{SHRINK}|Target :self sh :Target Ch)
          ; a guest who saw it can't believe his eyes (voice category 74 shrink_react)
          (Variables|GW|SetStamp (+ (Variables|GW|GetStamp) 1))
          (CallFunction|QueueSay :Ch (CallFunction|NearestNPC :Loc here :MaxD 800.0) :Cat 74 :Delay 1.6)))
      (Development|PrintString :InString (cat "GW: gas used by " (CallFunction|NameOf :P Ch)) :bPrintToScreen false))
    '''
    G['PlaceTrap'] = f'''
    (fn PlaceTrap (PS Ch)
      (bind (top ax hw ok) (CallFunction|FindDoor :Loc (Transformation|GetActorLocation :self Ch)))
      (if (not ok)
        {NOTE('PS', q("Placez-vous dans l'encadrement d'une porte pour poser le piège."))}
        (return))
      (for t (Actor|GetAllActorsOfClass :ActorClass "{TRAP}")
        (if (< (Math|Vector|Distance(Vector) (Transformation|GetActorLocation :self t) top) 60.0)
          {NOTE('PS', q('Il y a déjà un piège sur cette porte.'))}
          (return)))
      {PSADD('Traps', -1, 'PS')}
      (bind tr (Game|SpawnActorfromClass :Class "{TRAP}" :SpawnTransform (Math|Transform|MakeTransform :Location top :Rotation (Math|Rotator|MakeRotator :Roll 0.0 :Pitch 0.0 :Yaw (select ax 90.0 0.0))) :CollisionHandlingOverride "AlwaysSpawn"))
      (GW|Set|{TRAP}|OwnerPS :self tr :OwnerPS PS)
      (GW|Set|{TRAP}|AxisX :self tr :AxisX ax)
      (GW|Set|{TRAP}|HalfW :self tr :HalfW hw)
      (GW|Set|{TRAP}|ArmAt :self tr :ArmAt (+ (CallFunction|Now) 1.5))
      {NOTE('PS', q('Piège posé au-dessus de la porte : il attend le prochain détective.'))}
      (Development|PrintString :InString (cat "GW: trap set by " (PlayerState|GetPlayerName :self PS) " at " top) :bPrintToScreen false))
    '''
    G['DropBomb'] = f'''
    (fn DropBomb (PS Ch)
      (bind here (Transformation|GetActorLocation :self Ch))
      (Utilities|Array|Clear (Variables|Shop|GetTraceIgnore))
      (Utilities|Array|Add :TargetArray (Variables|Shop|GetTraceIgnore) :NewItem Ch)
      (bind (h ok) (Collision|LineTraceByChannel :Start here :End (- here {mv(0, 0, 300)}) :TraceChannel "Visibility" :bTraceComplex false :ActorsToIgnore (Variables|Shop|GetTraceIgnore) :bIgnoreSelf true))
      (bind (b1 i1 t1 d1 l1 imp n1 in1 p1 a1) (Collision|BreakHitResult h))
      (bind b (Game|SpawnActorfromClass :Class "{BOMB}" :SpawnTransform (Math|Transform|MakeTransform :Location (+ (select ok imp (- here {mv(0, 0, 96)})) {mv(0, 0, 1)}) :Rotation (Math|Rotator|MakeRotator :Roll 0.0 :Pitch 0.0 :Yaw (.yaw (Transformation|GetActorRotation :self Ch)))) :CollisionHandlingOverride "AlwaysSpawn"))
      (GW|Set|{BOMB}|OwnerPS :self b :OwnerPS PS)
      (GW|Set|{BOMB}|ExplodeAt :self b :ExplodeAt (+ (CallFunction|Now) {BOMB_T}))
      {NOTE('PS', q('Bombe posée : elle explose dans 45 s. Éloignez-vous !'))}
      (Development|PrintString :InString (cat "GW: bomb dropped by " (PlayerState|GetPlayerName :self PS) " at " (Transformation|GetActorLocation :self b)) :bPrintToScreen false))
    '''
    G['TrapTick'] = f'''
    (fn TrapTick ()
      (for t (Actor|GetAllActorsOfClass :ActorClass "{TRAP}")
        (if (>= (CallFunction|Now) (GW|Get|{TRAP}|ArmAt :self t))
          (bind tl (Transformation|GetActorLocation :self t))
          (bind ax (GW|Get|{TRAP}|AxisX :self t))
          (for c (Actor|GetAllActorsOfClass :ActorClass {CHAR})
            (if (and (GW|Get|BP_GW_Character|IsSeeker :self c) (not (GW|Get|BP_GW_Character|IsDead :self c)))
              (bind cl (Transformation|GetActorLocation :self c))
              (bind across (Math|Float|Absolute(Float) (select ax (- (.x cl) (.x tl)) (- (.y cl) (.y tl)))))
              (bind along (Math|Float|Absolute(Float) (select ax (- (.y cl) (.y tl)) (- (.x cl) (.x tl)))))
              ; wide across the wall: a sprinting detective moves ~1.2 m between two checks
              (if (and (and (< across 90.0) (< along (+ (GW|Get|{TRAP}|HalfW :self t) 15.0))) (< (.z cl) (.z tl)))
                (CallFunction|TrapFire :T t :Victim c)
                (break)))))))
    '''
    G['TrapFire'] = f'''
    (fn TrapFire (T Victim)
      (Variables|Shop|SetTmpV (Transformation|GetActorLocation :self T))
      (Variables|Shop|SetBlastOwner (GW|Get|{TRAP}|OwnerPS :self T))
      (Actor|DestroyActor :self T)
      (bind tl (Variables|Shop|GetTmpV))
      (Game|SpawnActorfromClass :Class "{SMALL}" :SpawnTransform (Math|Transform|MakeTransform :Location tl) :CollisionHandlingOverride "AlwaysSpawn")
      (Development|PrintString :InString (cat "GW: trap fired on " (CallFunction|NameOf :P Victim) " at " tl) :bPrintToScreen false)
      (CallFunction|Announce :Text (cat "Un piège explose au-dessus de " (CallFunction|NameOf :P Victim) " !"))
      {PAY('(Variables|Shop|GetBlastOwner)', 50, q('+50 $ : votre piège a explosé sur un détective !'))}
      (CallFunction|HurtCharacter :Victim Victim :Amount 25.0 :Impulse {mv(0, 0, 350)} :Cause "a été achevé par un piège")
      (CallFunction|StartPanicCause :Loc tl :Dur 8.0 :Cause 3))
    '''
    G['BombTick'] = f'''
    (fn BombTick ()
      (for b (Actor|GetAllActorsOfClass :ActorClass "{BOMB}")
        (bind at (GW|Get|{BOMB}|ExplodeAt :self b))
        ; every ~10 s the guest nearest a beeping bomb wonders about the beep (voice category 72 bomb_near)
        (if (and (> at 0.0) (>= (CallFunction|Now) (GW|Get|{BOMB}|NextNear :self b)))
          (GW|Set|{BOMB}|NextNear :self b :NextNear (+ (CallFunction|Now) (Math|Random|RandomFloatinRange 8.0 12.0)))
          (Variables|GW|SetStamp (+ (Variables|GW|GetStamp) 1))
          (CallFunction|Say :Ch (CallFunction|NearestNPC :Loc (Transformation|GetActorLocation :self b) :MaxD 600.0) :Cat 72))
        (if (and (and (> at 0.0) (< (- at (CallFunction|Now)) 12.0)) (not (GW|Get|{BOMB}|Warned :self b)))
          (CallFunction|BombWarn :B b))
        (if (and (> at 0.0) (>= (CallFunction|Now) at))
          (CallFunction|BombBlast :B b))))
    '''
    G['BombWarn'] = f'''
    (fn BombWarn (B)
      ; 12 s left, the beeping races: the guests within 7 m run away from it, one of them shouts
      (GW|Set|{BOMB}|Warned :self B :Warned true)
      (Variables|Shop|SetTmpV (Transformation|GetActorLocation :self B))
      (bind bl (Variables|Shop|GetTmpV))
      (Variables|Shop|SetBlastKills 0)
      (for c (Actor|GetAllActorsOfClass :ActorClass "/Game/GW/Blueprints/BP_GW_NPCController.BP_GW_NPCController_C")
        (bind p (Pawn|GetControlledPawn :self c))
        (if ({ISVALID} :Object p)
          (if (< (Math|Vector|Distance(Vector) (Transformation|GetActorLocation :self p) bl) 700.0)
            (GW|Set|BP_GW_NPCController|PanicUntil :self c :PanicUntil (+ (CallFunction|Now) 9.0))
            (GW|Set|BP_GW_NPCController|PanicFrom :self c :PanicFrom bl)
            (GW|Set|BP_GW_NPCController|IsMoving :self c :IsMoving false)
            (GW|Set|BP_GW_NPCController|NextMoveTime :self c :NextMoveTime (CallFunction|Now))
            (Variables|Shop|SetBlastKills (+ (Variables|Shop|GetBlastKills) 1)))))
      (Variables|GW|SetStamp (+ (Variables|GW|GetStamp) 1))
      (CallFunction|QueueSay :Ch (CallFunction|NearestNPC :Loc bl :MaxD 900.0) :Cat 2 :Delay 0.2)
      (Development|PrintString :InString (cat "GW: bomb about to blow, " (Variables|Shop|GetBlastKills) " guests flee it") :bPrintToScreen false))
    '''
    G['BombBlast'] = f'''
    (fn BombBlast (B)
      (Variables|Shop|SetTmpV (Transformation|GetActorLocation :self B))
      (Variables|Shop|SetBlastOwner (GW|Get|{BOMB}|OwnerPS :self B))
      (Actor|DestroyActor :self B)
      (bind loc (Variables|Shop|GetTmpV))
      (Game|SpawnActorfromClass :Class "{BIG}" :SpawnTransform (Math|Transform|MakeTransform :Location loc) :CollisionHandlingOverride "AlwaysSpawn")
      (Variables|Shop|SetBlastKills 0)
      (for c (Actor|GetAllActorsOfClass :ActorClass {CHAR})
        (bind cl (Transformation|GetActorLocation :self c))
        (if (and (< (Math|Vector|Distance(Vector) cl loc) {BOMB_R}) (not (GW|Get|BP_GW_Character|IsDead :self c)))
          (bind imp (* (Math|Vector|Normalize (+ (- cl loc) {mv(0, 0, 150)})) 1800.0))
          (bind kind (GW|Get|BP_GW_Character|Kind :self c))
          (if (or (== kind 1) (== kind 2))
            (GW|Call|BP_GW_Character|Die :self c :Impulse imp)
            (elif (Pawn|IsPlayerControlled :self c)
              (CallFunction|HurtCharacter :Victim c :Amount 500.0 :Impulse imp :Cause "a été pulvérisé par une bombe")
              (elif (== kind 0)
                (CallFunction|HurtCharacter :Victim c :Amount 1000.0 :Impulse imp :Cause "")
                (Variables|Shop|SetBlastKills (+ (Variables|Shop|GetBlastKills) 1))
                (CallFunction|LoudScream :Victim c))))))
      (bind kills (Variables|Shop|GetBlastKills))
      (CallFunction|StartPanicCause :Loc loc :Dur 18.0 :Cause 3)
      (CallFunction|Announce :Text (select (> kills 0) (cat "BOUM ! Une bombe a fait " kills (select (> kills 1) " victimes !" " victime !")) "BOUM ! Une bombe a explosé !"))
      (if (> kills 0)
        {PAY('(Variables|Shop|GetBlastOwner)', '(* kills 100)', '(cat "+" (* kills 100) " $ : votre bombe a fait " kills (select (> kills 1) " victimes" " victime"))')})
      (Development|PrintString :InString (cat "GW: bomb exploded at " loc " kills=" kills) :bPrintToScreen false)
      (CallFunction|UpdateCounts))
    '''
    G['DefuseBomb'] = f'''
    (fn DefuseBomb (B P)
      (if (not ({ISVALID} :Object B))
        (return))
      (Variables|Shop|SetTmpV (Transformation|GetActorLocation :self B))
      (Variables|Shop|SetBlastOwner (GW|Get|{BOMB}|OwnerPS :self B))
      (Actor|DestroyActor :self B)
      (Game|SpawnActorfromClass :Class "{DFX}" :SpawnTransform (Math|Transform|MakeTransform :Location (Variables|Shop|GetTmpV)) :CollisionHandlingOverride "AlwaysSpawn")
      (CallFunction|Announce :Text (cat (CallFunction|NameOf :P P) " a désamorcé une bombe !"))
      ; relief around (voice category 75 defuse_react)
      (Variables|GW|SetStamp (+ (Variables|GW|GetStamp) 1))
      (CallFunction|QueueSay :Ch (CallFunction|NearestNPC :Loc (Variables|Shop|GetTmpV) :MaxD 900.0) :Cat 75 :Delay 0.9)
      {NOTE('(Variables|Shop|GetBlastOwner)', q('Votre bombe a été désamorcée par un détective…'))}
      (Development|PrintString :InString (cat "GW: bomb defused by " (CallFunction|NameOf :P P) " at " (Variables|Shop|GetTmpV)) :bPrintToScreen false))
    '''
    G['GunFor'] = f'''
    (fn GunFor (PS)
      ; the revolver shows in the hand of a living guest who has bullets
      (bind g {PSG('GunActor', 'PS')})
      ; (a cast inside an if would end the flow there: the character comes from CharOfPS)
      (Variables|Shop|SetGunPawn (CallFunction|CharOfPS :PS PS))
      (bind ch (Variables|Shop|GetGunPawn))
      (Variables|Shop|SetWantGun false)
      (if ({ISVALID} :Object ch)
        (Variables|Shop|SetWantGun (and (and (> {PSG('Ammo', 'PS')} 0) (== {PSG('GWRole', 'PS')} 1)) (not (GW|Get|BP_GW_Character|IsDead :self ch)))))
      (if (Variables|Shop|GetWantGun)
        (if (not ({ISVALID} :Object g))
          (bind ng (Game|SpawnActorfromClass :Class "{GUN}" :SpawnTransform (Math|Transform|MakeTransform :Location (Transformation|GetActorLocation :self (Variables|Shop|GetGunPawn))) :CollisionHandlingOverride "AlwaysSpawn"))
          (GW|Set|{GUN}|Holder :self ng :Holder (Variables|Shop|GetGunPawn))
          {PSS('GunActor', 'ng', 'PS')}
          (return))
        (if (!= (GW|Get|{GUN}|Holder :self g) (Variables|Shop|GetGunPawn))
          (Actor|DestroyActor :self g)
          {PSS('GunActor', '(Variables|Shop|GetNoGun)', 'PS')})
        (return))
      (if ({ISVALID} :Object g)
        (Actor|DestroyActor :self g)
        {PSS('GunActor', '(Variables|Shop|GetNoGun)', 'PS')}))
    '''
    G['CharOfPS'] = f'''
    (fn CharOfPS (PS)
      (bind p (PlayerState|GetPawn :self PS))
      (if (not ({ISVALID} :Object p))
        (return (Variables|GW|GetNoChar)))
      (bind c (Utilities|Casting|CastToBP_GW_Character p)
        (:then (return c))
        (:CastFailed (return (Variables|GW|GetNoChar)))))
    '''
    G['GunTick'] = '''
    (fn GunTick ()
      (for ps (CallFunction|GetGWPlayers)
        (CallFunction|GunFor :PS ps)))
    '''
    G['SurviveTick'] = f'''
    (fn SurviveTick ()
      (if (!= (GW|Get|BP_GW_GameState|Phase :self (CallFunction|GetGS)) 2)
        (Variables|Shop|SetNextSurvive 0.0)
        (return))
      (if (<= (Variables|Shop|GetNextSurvive) 0.0)
        (Variables|Shop|SetNextSurvive (+ (CallFunction|Now) 30.0))
        (return))
      (if (< (CallFunction|Now) (Variables|Shop|GetNextSurvive))
        (return))
      (Variables|Shop|SetNextSurvive (+ (Variables|Shop|GetNextSurvive) 30.0))
      (for ps (CallFunction|GetGWPlayers)
        (if (and (== {PSG('GWRole')} 1) {PSG('IsAlive')})
          {PAY('ps', 5, q('+5 $ : toujours dans la foule'))})))
    '''
    cleanup = '\n'.join(f'''  (for a (Actor|GetAllActorsOfClass :ActorClass "{c}")
        (Actor|DestroyActor :self a))''' for c in (TRAP, BOMB, SMOKE, GAS, CRACKER))
    G['ShopCleanup'] = f'''
    (fn ShopCleanup ()
    {cleanup}
      (Development|PrintString :InString "GW: shop cleanup (traps, bombs, smoke)" :bPrintToScreen false))
    '''
    G['SpawnBarman'] = f'''
    (fn SpawnBarman ()
      ; behind the billiard-room bar, standing on the floor (traced), facing the room
      (bind top {mv(BAR[0], BAR[1], 240)})
      (bind (h ok) (Collision|LineTraceByChannel :Start top :End {mv(BAR[0], BAR[1], -200)} :TraceChannel "Visibility" :bTraceComplex false :bIgnoreSelf true))
      (bind (b1 i1 t1 d1 l1 imp n1 in1 p1 a1) (Collision|BreakHitResult h))
      (bind fz (select ok (.z imp) 0.0))
      (Variables|Shop|SetBarman (Game|SpawnActorfromClass :Class "{BARMAN}" :SpawnTransform (Math|Transform|MakeTransform :Location (Math|Vector|MakeVector {BAR[0]} {BAR[1]} (+ fz 90.0)) :Rotation (Math|Rotator|MakeRotator :Roll 0.0 :Pitch 0.0 :Yaw -90.0)) :CollisionHandlingOverride "AlwaysSpawn"))
      (Development|PrintString :InString (cat "GW: barman spawned, floor z=" fz " (hit " (Utilities|GetDisplayName :Object a1) ") at " (Transformation|GetActorLocation :self (Variables|Shop|GetBarman))) :bPrintToScreen false))
    '''
    G['SpawnJunkie'] = f'''
    (fn SpawnJunkie ()
      ; in the toilets, on the level's GW_Junkie marker (its position and facing); no marker, no junkie (logged once)
      (bind pts (Actor|GetAllActorswithTag :Tag "GW_Junkie"))
      (if (== (Utilities|Array|Length pts) 0)
        (Development|PrintString :InString "GW: no GW_Junkie marker in this map: the junkie is not spawned" :bPrintToScreen false)
        (return))
      (bind mk (Utilities|Array|Get(acopy) pts 0))
      (bind ml (Transformation|GetActorLocation :self mk))
      (bind (h ok) (Collision|LineTraceByChannel :Start (+ ml {mv(0, 0, 120)}) :End (- ml {mv(0, 0, 300)}) :TraceChannel "Visibility" :bTraceComplex false :bIgnoreSelf true))
      (bind (b1 i1 t1 d1 l1 imp n1 in1 p1 a1) (Collision|BreakHitResult h))
      (Variables|Shop|SetJunkie (Game|SpawnActorfromClass :Class "{JUNKIE}" :SpawnTransform (Math|Transform|MakeTransform :Location (Math|Vector|MakeVector (.x ml) (.y ml) (+ (select ok (.z imp) (.z ml)) 90.0)) :Rotation (Math|Rotator|MakeRotator :Roll 0.0 :Pitch 0.0 :Yaw (.yaw (Transformation|GetActorRotation :self mk)))) :CollisionHandlingOverride "AlwaysSpawn"))
      (Development|PrintString :InString (cat "GW: junkie spawned at " (Transformation|GetActorLocation :self (Variables|Shop|GetJunkie))) :bPrintToScreen false))
    '''
    G['SpawnVendors'] = f'''
    (fn SpawnVendors ()
      (if (not ({ISVALID} :Object (Variables|Shop|GetBarman)))
        (CallFunction|SpawnBarman))
      (if (not (Variables|Shop|GetJunkieChecked))
        (Variables|Shop|SetJunkieChecked true)
        (CallFunction|SpawnJunkie))
      ; two waiters wander among the guests (AI pawns, not BP_GW_Character: bullets and bombs ignore them)
      ; the second one is BP_GW_Waiter2 (other skin, Tools/chars/make_waiter2.py)
      (if (< (Utilities|Array|Length (Variables|Shop|GetWaiters)) 2)
        (bind t (CallFunction|RandomSpawnTransform))
        (if (== (Utilities|Array|Length (Variables|Shop|GetWaiters)) 1)
          (bind w2 (AI|SpawnAIFromClass :PawnClass "{WAITER2}" :Location (.location t) :Rotation (.rotation t) :bNoCollisionFail true))
          (bind wc2 (Utilities|Casting|CastToBP_GW_Waiter w2)
            (:then
              (Utilities|Array|Add :TargetArray (Variables|Shop|GetWaiters) :NewItem wc2)
              (GW|Set|{WAITER}|NextMoveAt :self wc2 :NextMoveAt (+ (CallFunction|Now) (Math|Random|RandomFloatinRange 1.0 4.0)))
              (Development|PrintString :InString (cat "GW: waiter2 spawned at " (Transformation|GetActorLocation :self wc2)) :bPrintToScreen false))
            (:CastFailed))
          (else
            (bind w (AI|SpawnAIFromClass :PawnClass "{WAITER}" :Location (.location t) :Rotation (.rotation t) :bNoCollisionFail true))
            (bind wc (Utilities|Casting|CastToBP_GW_Waiter w)
              (:then
                (Utilities|Array|Add :TargetArray (Variables|Shop|GetWaiters) :NewItem wc)
                (GW|Set|{WAITER}|NextMoveAt :self wc :NextMoveAt (+ (CallFunction|Now) (Math|Random|RandomFloatinRange 1.0 4.0)))
                (Development|PrintString :InString (cat "GW: waiter spawned at " (Transformation|GetActorLocation :self wc)) :bPrintToScreen false))
              (:CastFailed))))))
    '''
    G['FarFromDoors'] = f'''
    (fn FarFromDoors (Loc)
      ; not in a doorway (2.3 m from every door) and not on the dance floor
      (for p (Variables|Shop|GetDoorPts)
        (if (< (Math|Vector|Distance2D(Vector) p Loc) 230.0)
          (return false)))
      (return (not (and (and (> (.x Loc) {DANCE[0]}) (< (.x Loc) {DANCE[1]})) (and (> (.y Loc) {DANCE[2]}) (< (.y Loc) {DANCE[3]}))))))
    '''
    G['WaiterThink'] = f'''
    (fn WaiterThink (W)
      ; walk to a group of guests, pause 5-10 s next to them (a mobile shop for the players), then the next group
      ; dev menu: WaiterMode 1 frozen, 2 following the player who asked
      (if (== (Variables|Shop|GetWaiterMode) 1)
        (return))
      (if (and (== (Variables|Shop|GetWaiterMode) 2) ({ISVALID} :Object (Variables|Shop|GetWaiterFollow)))
        (if (> (Math|Vector|Distance2D(Vector) (Transformation|GetActorLocation :self W) (Transformation|GetActorLocation :self (Variables|Shop|GetWaiterFollow))) 260.0)
          (CallFunction|WaiterGo :W W :Dest (Transformation|GetActorLocation :self (Variables|Shop|GetWaiterFollow))))
        (return))
      (bind now (CallFunction|Now))
      (bind ms (GW|Get|{WAITER}|MoveStart :self W))
      (if (GW|Get|{WAITER}|Moving :self W)
        (if (or (> (- now ms) 25.0) (and (> (- now ms) 1.5) (< (Math|Vector|VectorLength (Transformation|GetVelocity :self W)) 8.0)))
          (GW|Set|{WAITER}|Moving :self W :Moving false)
          (GW|Set|{WAITER}|NextMoveAt :self W :NextMoveAt (+ now (Math|Random|RandomFloatinRange 5.0 10.0))))
        (return))
      (if (< now (GW|Get|{WAITER}|NextMoveAt :self W))
        (return))
      (bind all (Actor|GetAllActorsOfClass :ActorClass {CHAR}))
      (bind n (Utilities|Array|Length all))
      (Variables|Shop|SetWaiterOk false)
      (bind wl (Transformation|GetActorLocation :self W))
      (if (> n 0)
        (for k (range 8)
          (if (not (Variables|Shop|GetWaiterOk))
            (Variables|Shop|SetWaiterPick (Utilities|Array|Get(acopy) all (Math|Random|RandomIntegerinRange 0 (- n 1))))
            (bind c (Variables|Shop|GetWaiterPick))
            (bind cl (Transformation|GetActorLocation :self c))
            (bind side (Math|Vector|Normalize (Math|Vector|MakeVector (- (.x wl) (.x cl)) (- (.y wl) (.y cl)) 0.0)))
            (Variables|Shop|SetWaiterDest (+ cl (* side 130.0)))
            (if (and (and (not (Pawn|IsPlayerControlled :self c)) (not (GW|Get|BP_GW_Character|IsDead :self c))) (CallFunction|FarFromDoors :Loc (Variables|Shop|GetWaiterDest)))
              (Variables|Shop|SetWaiterOk true)))))
      (if (not (Variables|Shop|GetWaiterOk))
        (GW|Set|{WAITER}|NextMoveAt :self W :NextMoveAt (+ now 3.0))
        (return))
      (GW|Set|{WAITER}|Moving :self W :Moving true)
      (GW|Set|{WAITER}|MoveStart :self W :MoveStart now)
      (CallFunction|WaiterGo :W W :Dest (Variables|Shop|GetWaiterDest)))
    '''
    G['IsSmokeBetween'] = f'''
    (fn IsSmokeBetween (A B)
      ; true when the segment A-B crosses a live smoke cloud (BP_GW_SmokeBomb, server ages): robot sight, aim assist...
      (bind ab (- B A))
      (bind len2 (Math|Float|Max(Float) (Math|Vector|DotProduct ab ab) 1.0))
      (bind now (Utilities|Time|GetGameTimeinSeconds))
      (for s (Actor|GetAllActorsOfClass :ActorClass "{SMOKE}")
        (bind age (- now (GW|Get|{SMOKE}|T0 :self s)))
        (if (and (> age 1.0) (< age 19.5))
          (bind c (+ (Transformation|GetActorLocation :self s) {mv(0, 0, 110)}))
          (bind t (Math|Float|Max(Float) 0.0 (Math|Float|Min(Float) 1.0 (/ (Math|Vector|DotProduct (- c A) ab) len2))))
          (if (< (Math|Vector|Distance(Vector) (+ A (* ab t)) c) (* 290.0 (Math|Float|Min(Float) 1.0 (/ (- age 0.6) 2.5))))
            (return true))))
      (return false))
    '''
    G['WaiterGo'] = '''
    (fn WaiterGo (W Dest)
      (bind ai (Utilities|Casting|CastToAIController (Pawn|GetController :self W))
        (:then (AI|Navigation|MovetoLocation :self ai :Dest Dest :AcceptanceRadius 60.0 :bStopOnOverlap true :bUsePathfinding true :bProjectDestinationToNavigation true :bCanStrafe false :bAllowPartialPath true))
        (:CastFailed)))
    '''
    G['WaiterLeave'] = f'''
    (fn WaiterLeave ()
      (if (== (Utilities|Array|Length (Variables|Shop|GetWaiters)) 0)
        (return))
      (bind w (Utilities|Array|Get(acopy) (Variables|Shop|GetWaiters) 0))
      (bind wl (Transformation|GetActorLocation :self w))
      (Variables|Shop|SetWaiterOk false)
      (for k (range 8)
        (if (not (Variables|Shop|GetWaiterOk))
          (bind (pt ok) (AI|Navigation|GetRandomReachablePointinRadius :Origin wl :Radius 1500.0))
          (if (and ok (> (Math|Vector|Distance2D(Vector) pt wl) 800.0))
            (Variables|Shop|SetWaiterDest pt)
            (Variables|Shop|SetWaiterOk true))))
      (if (not (Variables|Shop|GetWaiterOk))
        (return))
      (GW|Set|{WAITER}|Moving :self w :Moving true)
      (GW|Set|{WAITER}|MoveStart :self w :MoveStart (CallFunction|Now))
      (CallFunction|WaiterGo :W w :Dest (Variables|Shop|GetWaiterDest))
      (Development|PrintString :InString (cat "GW: dev waiter leaves for " (Variables|Shop|GetWaiterDest)) :bPrintToScreen false))
    '''
    G['JunkieTick'] = f'''
    (fn JunkieTick ()
      (bind j (Variables|Shop|GetJunkie))
      (if (or (not ({ISVALID} :Object j)) (< (CallFunction|Now) (Variables|Shop|GetNextJunkieWarn)))
        (return))
      (bind jl (Transformation|GetActorLocation :self j))
      (for c (Actor|GetAllActorsOfClass :ActorClass {CHAR})
        (if (and (GW|Get|BP_GW_Character|IsSeeker :self c) (not (GW|Get|BP_GW_Character|IsDead :self c)))
          (if (< (Math|Vector|Distance(Vector) (Transformation|GetActorLocation :self c) jl) 400.0)
            (Variables|Shop|SetNextJunkieWarn (+ (CallFunction|Now) 20.0))
            (CallFunction|StaffSay :Cat 63 :Ctx 8 :Loc (+ jl {mv(0, 0, 70)}))
            (Development|PrintString :InString "GW: junkie sees a detective" :bPrintToScreen false)
            (return)))))
    '''
    G['WaiterTick'] = f'''
    (fn WaiterTick ()
      (for w (Variables|Shop|GetWaiters)
        (if ({ISVALID} :Object w)
          (CallFunction|WaiterThink :W w))))
    '''
    G['ShopTick'] = '''
    (fn ShopTick ()
      (CallFunction|SpawnVendors)
      (bind phase (GW|Get|BP_GW_GameState|Phase :self (CallFunction|GetGS)))
      (if (!= phase (Variables|Shop|GetShopPhase))
        (if (or (== phase 0) (== phase 1))
          (CallFunction|ShopCleanup))
        (Variables|Shop|SetShopPhase phase))
      (CallFunction|SurviveTick)
      (CallFunction|TrapTick)
      (CallFunction|BombTick)
      (CallFunction|GunTick)
      (CallFunction|CrackerTick)
      (CallFunction|JunkieTick)
      (CallFunction|WaiterTick))
    '''
    for name, code in G.items():
        if name in shop_items.S40_OWNS:      # body in s40_inventory.py (run it after this script)
            continue
        wr(gm, name, code)
        if not compile_bp(gm, quiet=True):
            print('GM compile failed after', name)
    finish(gm)
else:
    pass

if want('pc'):
    # ================================================================ player controller (client side + server commands)
    pc = load_bp('BP_GW_PlayerController')
    IMC = unreal.load_asset('/Game/GW/Input/IMC_GW')
    INP = '/Game/GW/Input'
    KEYS = {'IA_GW_Smoke': ('G', 'UseSmoke'), 'IA_GW_Gas': ('H', 'UseGas'), 'IA_GW_Trap': ('T', 'UseTrap'),
            'IA_GW_Lamp': ('F', 'ToggleLamp'), 'IA_GW_Bomb': ('B', 'UseBomb'), 'IA_GW_Cracker': ('X', 'UseCracker')}
    for ia_name, (key, _) in KEYS.items():
        pth = f'{INP}/{ia_name}'
        ia = unreal.load_asset(pth) if EAL.does_asset_exist(pth) else AT.create_asset(ia_name, INP, unreal.InputAction, unreal.InputAction_Factory())
        EAL.save_loaded_asset(ia, False)
        # (no key mapping any more: items are used through the 4-slot inventory, s40_inventory.py)
    EAL.save_loaded_asset(IMC, False)

    for v, t in (('LampOn', 'bool'), ('ShopPaused', 'bool'), ('ShopAnywhere', 'int'), ('ShopHere', 'bool'), ('ShopKind', 'int'),
                 ('VKind', 'int'), ('VBestD', 'float'), ('PromptOn', 'bool'), ('ShopTestStep', 'int'),
                 ('ShopTestAt', 'float'), ('ShopPick', 'int'), ('ShopPromptTxt', 'string')):
        ensure_var(pc, v, t, category='Shop')
    ensure_var(pc, 'ShopTmpIdx', 'int', array=True, category='Shop')
    ensure_var(pc, 'ShopW', obj_class=unreal.UserWidget, category='Shop')
    ensure_var(pc, 'NoWidget', obj_class=unreal.UserWidget, category='Shop')
    ensure_var(pc, 'ShopVendor', obj_class=unreal.Actor, category='Shop')
    ensure_var(pc, 'LampActor', obj_class=unreal.Actor, category='Shop')
    ensure_var(pc, 'ShopPrompt', obj_class=kp.generated_class(), category='Shop')
    ensure_var(pc, 'BombRef', obj_class=bomb.generated_class(), category='Shop')
    ensure_var(pc, 'AimT', obj_class=chc, category='Shop')
    ensure_var(pc, 'AimOk', 'bool', category='Shop')
    ensure_var(pc, 'AimSpot', struct=V3, category='Shop')
    for _v, _t in (('DefuseHold', 'bool'), ('DefuseT0', 'float'), ('DefuseProgress', 'float'), ('DefuseClicks', 'float'),
                   ('DefuseStartAt', 'float')):
        ensure_var(pc, _v, _t, category='Shop')       # DefuseStartAt: server side (when this detective began holding)
    ensure_var(pc, 'DefuseStartBomb', obj_class=bomb.generated_class(), category='Shop')
    ensure_var(pc, 'NextStaffLine', 'float', category='Shop')     # server: GWStaffLine anti-spam
    door_vars(pc)
    PCF = {
        'TryShop': ([], [('Handled', 'bool')]), 'TryDefuse': ([], [('Handled', 'bool')]), 'ShopClientTick': ([], []),
        'ShopServer': ([('Cmd', 'string')], []), 'Notice': ([('Msg', 'string')], []), 'NearVendor': ([('R', 'float')], [('Ok', 'bool'), ('Kind', 'int')]),
        'CanShop': ([], [('Ok', 'bool')]), 'ShopOpen': ([], [('Ok', 'bool')]), 'OpenShop': ([], []), 'CloseShop': ([], []),
        'OpenShopHere': ([('Kind', 'int')], []), 'VendorGreet': ([], []), 'UseCracker': ([], []), 'NearBomb': ([('R', 'float')], [('Ok', 'bool')]),
        'ShopBuy': ([('Id', 'int')], []), 'RequestUse': ([('Id', 'int')], []), 'UseSmoke': ([], []), 'UseGas': ([], []),
        'UseTrap': ([], []), 'UseBomb': ([], []), 'ToggleLamp': ([], []), 'LampTick': ([], []), 'PromptTick': ([], []),
        'PromptPick': ([], []), 'ShowShopPrompt': ([('Key', 'string'), ('Label', 'string'), ('At', V3)], []),
        'GuestFire': ([('Ch', chc), ('Start', V3), ('Dir', V3)], []), 'GuestAttack': ([('Ch', chc)], []),
        'ShopTestTick': ([], []), 'ShopDump': ([('St', 'int')], []), 'FindDoor': ([('Loc', V3)], DOOR_OUT),
        'DefuseRelease': ([], []), 'CancelDefuse': ([('Why', 'string')], []), 'DefuseTick': ([], []),
        'DefuseOk': ([], [('Ok', 'bool')]),
    }
    for f, (ins, outs) in PCF.items():
        ensure_fn(pc, f, inputs=ins, outputs=outs)
    EXEC = {'GWBuy': [('Id', 'int')], 'GWUseItem': [('Id', 'int'), ('Yaw', 'float')], 'GWDefuse': [],
            'GWDevMoney': [('Amount', 'int')], 'GWDevGive': [('Id', 'int')], 'GWDevBombNow': [], 'GWDevShopAim': [('Mode', 'int')],
            'GWDevShopHere': [('On', 'int')], 'GWDevWaiter': [], 'GWDefuseStart': [], 'GWDevGoBomb': [],
            'GWDevWaiters': [('Mode', 'int')], 'GWDevWaiterLeave': [], 'GWStaffLine': [('Ctx', 'int')]}
    for f, ins in EXEC.items():
        ensure_fn(pc, f, inputs=ins, exec_fn=True)
    compile_bp(pc, quiet=True)
    local(pc, 'FindDoor', 'Best', 'int')
    local(pc, 'FindDoor', 'BestD', 'float')
    local(pc, 'GWDevShopAim', 'BestD', 'float')
    door_defaults(pc)
    HAVE_SHOP_W = EAL.does_asset_exist('/Game/GW/UI/WBP_Shop')
    if not HAVE_SHOP_W:
        print('!!! WBP_Shop missing: run Tools/ui/u17_shop_ui.py, then this script again (OpenShop left empty)')
    GATE = '''  (if (not (CallFunction|DevOK))
        (Development|PrintString :InString "GW: dev shop command refused (server not started with -GWDev)" :bPrintToScreen false)
        (return))'''
    GMCALL = lambda fn, args: f'''(bind gm {GMC}
          (:then (GW|Call|BP_GW_GameMode|{fn} :self gm {args}))
          (:CastFailed))'''
    C = {}
    C['FindDoor'] = FIND_DOOR
    C['ShopServer'] = '''
    (fn ShopServer (Cmd)
      (if (Networking|HasAuthority)
        (Development|ExecuteConsoleCommand :Command Cmd :SpecificPlayer self)
        (else
          (Development|ExecuteConsoleCommand :Command (cat "ServerExec " Cmd) :SpecificPlayer self))))
    '''
    C['Notice'] = f'''
    (fn Notice (Msg)
      (bind hud (Variables|GW|GetHUDWidget))
      (if ({ISVALID} :Object hud)
        (GW|Set|{HUD}|LocalNotice :self hud :LocalNotice Msg)
        (GW|Set|{HUD}|LocalNoticeTime :self hud :LocalNoticeTime (Utilities|Time|GetRealTimeSeconds))))
    '''
    C['NearVendor'] = f'''
    (fn NearVendor (R)
      ; the nearest vendor within R (barman, junkie, waiters: all BP_GW_Barman); sets ShopVendor, returns its kind
      (Variables|Shop|SetVBestD R)
      (Variables|Shop|SetVKind -1)
      (bind p (Pawn|GetControlledPawn :self self))
      (if (not ({ISVALID} :Object p))
        (return false -1))
      (bind pl (Transformation|GetActorLocation :self p))
      (for v (Actor|GetAllActorsOfClass :ActorClass "{BARMAN}")
        (bind vl (Transformation|GetActorLocation :self v))
        (bind dz (- (.z pl) (.z vl)))
        (bind d (Math|Vector|Distance2D(Vector) pl vl))
        (if (and (< d (Variables|Shop|GetVBestD)) (< (* dz dz) 40000.0))
          (Variables|Shop|SetVBestD d)
          (Variables|Shop|SetVKind (GW|Get|{BARMAN}|VendorKind :self v))
          (Variables|Shop|SetShopVendor v)))
      (return (>= (Variables|Shop|GetVKind) 0) (Variables|Shop|GetVKind)))
    '''
    C['CanShop'] = f'''
    (fn CanShop ()
      ; guests only: not detectives, not ghosts, not the dead
      (bind ps {PSC}
        (:then
          (bind ch {MYCH}
            (:then (return (and (!= {PSG('GWRole')} 2) (not (GW|Get|BP_GW_Character|IsDead :self ch)))))
            (:CastFailed (return false))))
        (:CastFailed (return false))))
    '''
    C['ShopOpen'] = f'''
    (fn ShopOpen ()
      (bind w (Variables|Shop|GetShopW))
      (if ({ISVALID} :Object w)
        (return (Appearance|IsinViewport :self w)))
      (return false))
    '''
    C['OpenShop'] = ('''
    (fn OpenShop ()
      (if (CallFunction|ShopOpen)
        (return))
      (Variables|Shop|SetShopW (UserInterface|CreateWidget :Class "/Game/GW/UI/WBP_Shop.WBP_Shop_C" :OwningPlayer self))
      (UserInterface|Viewport|AddtoViewport :self (Variables|Shop|GetShopW) :ZOrder 40)
      (Input|SetInputModeGameAndUI :PlayerController self :bHideCursorDuringCapture false)
      (Variables|MouseInterface|SetShowMouseCursor true)
      (CallFunction|VendorGreet)
      (Development|PrintString :InString (cat "GW: shop opened, vendor kind " (Variables|Shop|GetShopKind)) :bPrintToScreen false))
    ''' if HAVE_SHOP_W else '(fn OpenShop () (Development|PrintString :InString "GW: WBP_Shop missing" :bPrintToScreen false))')
    C['CloseShop'] = f'''
    (fn CloseShop ()
      (bind w (Variables|Shop|GetShopW))
      (if ({ISVALID} :Object w)
        (Widget|RemovefromParent :self w))
      (Variables|Shop|SetShopW (Variables|Shop|GetNoWidget))
      (Variables|Shop|SetShopHere false)
      (Input|SetInputModeGameOnly :PlayerController self)
      (Variables|MouseInterface|SetShowMouseCursor false)
      (Audio|PlaySound2D :Sound "/Game/GW/Audio/S_UI_Back.S_UI_Back" :VolumeMultiplier 0.6)
      (Development|PrintString :InString "GW: shop closed" :bPrintToScreen false))
    '''
    C['OpenShopHere'] = '''
    (fn OpenShopHere (Kind)
      ; dev menu: the barman's (0) or the junkie's (1) shop anywhere; the server then accepts purchases away from a vendor
      (Variables|Shop|SetShopHere true)
      (Variables|Shop|SetShopKind Kind)
      (CallFunction|ShopServer :Cmd (cat "GWDevShopHere " (+ Kind 1)))
      (CallFunction|OpenShop))
    '''
    C['VendorGreet'] = f'''
    (fn VendorGreet ()
      ; one of the vendor's own lines (bank categories: barman 15, waiter 62, junkie 63), heard here only
      (if (not ({ISVALID} :Object (Variables|Shop|GetShopVendor)))
        (return))
      (Variables|Shop|SetShopPick (select (== (Variables|Shop|GetShopKind) 1) 63 (select (== (Variables|Shop|GetShopKind) 2) 62 15)))
      (bind s {GSC}
        (:then
          (Utilities|Array|Clear (Variables|Shop|GetShopTmpIdx))
          (bind cats (GW|Get|BP_GW_GameState|BankCat :self s))
          (bind ctxs (GW|Get|BP_GW_GameState|BankCtx :self s))
          (for i (range (Math|Integer|Min(Integer) (Utilities|Array|Length cats) (Utilities|Array|Length ctxs)))
            (if (and (== (Utilities|Array|Get(acopy) cats i) (Variables|Shop|GetShopPick)) (== (Utilities|Array|Get(acopy) ctxs i) 3))
              (Utilities|Array|Add :TargetArray (Variables|Shop|GetShopTmpIdx) :NewItem i)))
          (bind n (Utilities|Array|Length (Variables|Shop|GetShopTmpIdx)))
          (if (== n 0)
            (return))
          (Variables|Shop|SetShopPick (Utilities|Array|Get(acopy) (Variables|Shop|GetShopTmpIdx) (Math|Random|RandomIntegerinRange 0 (- n 1))))
          (bind snds (GW|Get|BP_GW_GameState|BankSounds :self s))
          (if (< (Variables|Shop|GetShopPick) (Utilities|Array|Length snds))
            (Audio|PlaySoundatLocation :Sound (Utilities|Array|Get(acopy) snds (Variables|Shop|GetShopPick)) :Location (+ (Transformation|GetActorLocation :self (Variables|Shop|GetShopVendor)) {mv(0, 0, 70)}) :VolumeMultiplier 1.0)))
        (:CastFailed)))
    '''
    C['TryShop'] = '''
    (fn TryShop ()
      (if (CallFunction|ShopOpen)
        (CallFunction|CloseShop)
        (return true))
      (if (not (CallFunction|CanShop))
        (return false))
      (bind (near kind) (CallFunction|NearVendor :R 300.0))
      (if (not near)
        (return false))
      (Variables|Shop|SetShopKind kind)
      (Variables|Shop|SetShopHere false)
      (CallFunction|OpenShop)
      (return true))
    '''
    C['NearBomb'] = f'''
    (fn NearBomb (R)
      (bind p (Pawn|GetControlledPawn :self self))
      (if (not ({ISVALID} :Object p))
        (return false))
      (bind here (Transformation|GetActorLocation :self p))
      (for b (Actor|GetAllActorsOfClass :ActorClass "{BOMB}")
        (bind bl (Transformation|GetActorLocation :self b))
        (bind dz (- (.z here) (.z bl)))
        (if (and (< (Math|Vector|Distance2D(Vector) bl here) R) (< (* dz dz) 40000.0))
          (Variables|Shop|SetBombRef b)
          (return true)))
      (return false))
    '''
    C['DefuseOk'] = f'''
    (fn DefuseOk ()
      ; a living detective
      (bind ps {PSC}
        (:then
          (if (!= {PSG('GWRole')} 2)
            (return false))
          (bind ch {MYCH}
            (:then (return (not (GW|Get|BP_GW_Character|IsDead :self ch))))
            (:CastFailed (return false))))
        (:CastFailed (return false))))
    '''
    C['TryDefuse'] = f'''
    (fn TryDefuse ()
      ; E near a bomb (1.5 m), detective: start holding; DefuseTick finishes after 2 s, releasing E cancels
      (if (not (CallFunction|DefuseOk))
        (return false))
      (if (not (CallFunction|NearBomb :R 150.0))
        (return false))
      (if (Variables|Shop|GetDefuseHold)
        (return true))
      (Variables|Shop|SetDefuseHold true)
      (Variables|Shop|SetDefuseT0 (Utilities|Time|GetRealTimeSeconds))
      (Variables|Shop|SetDefuseProgress 0.0)
      (Variables|Shop|SetDefuseClicks 0.0)
      (CallFunction|ShopServer :Cmd "GWDefuseStart")
      (Audio|PlaySound2D :Sound "/Game/GW/Audio/S_UI_Click.S_UI_Click" :VolumeMultiplier 0.7 :PitchMultiplier 0.8)
      (Development|PrintString :InString "GW: defuse hold started" :bPrintToScreen false)
      (return true))
    '''
    C['DefuseRelease'] = '''
    (fn DefuseRelease ()
      (if (Variables|Shop|GetDefuseHold)
        (CallFunction|CancelDefuse :Why "E relâché")))
    '''
    C['CancelDefuse'] = '''
    (fn CancelDefuse (Why)
      (Variables|Shop|SetDefuseHold false)
      (Variables|Shop|SetDefuseProgress 0.0)
      (CallFunction|Notice :Msg "Désamorçage interrompu !")
      (Audio|PlaySound2D :Sound "/Game/GW/Audio/S_UI_Back.S_UI_Back" :VolumeMultiplier 0.6)
      (Development|PrintString :InString (cat "GW: defuse cancelled (" Why ")") :bPrintToScreen false))
    '''
    C['DefuseTick'] = '''
    (fn DefuseTick ()
      (if (not (Variables|Shop|GetDefuseHold))
        (return))
      (if (or (not (CallFunction|DefuseOk)) (not (CallFunction|NearBomb :R 230.0)))
        (CallFunction|CancelDefuse :Why "trop loin")
        (return))
      (Variables|Shop|SetDefuseProgress (Math|Float|Min(Float) 1.0 (/ (- (Utilities|Time|GetRealTimeSeconds) (Variables|Shop|GetDefuseT0)) 2.0)))
      ; a click every quarter, higher and higher
      (if (>= (* (Variables|Shop|GetDefuseProgress) 4.0) (+ (Variables|Shop|GetDefuseClicks) 1.0))
        (Variables|Shop|SetDefuseClicks (+ (Variables|Shop|GetDefuseClicks) 1.0))
        (Audio|PlaySound2D :Sound "/Game/GW/Audio/S_UI_Click.S_UI_Click" :VolumeMultiplier 0.8 :PitchMultiplier (+ 0.9 (* (Variables|Shop|GetDefuseProgress) 0.6))))
      (if (>= (Variables|Shop|GetDefuseProgress) 1.0)
        (Variables|Shop|SetDefuseHold false)
        (CallFunction|ShopServer :Cmd "GWDefuse")
        (Development|PrintString :InString "GW: defuse hold complete" :bPrintToScreen false)))
    '''
    C['ShopBuy'] = '(fn ShopBuy (Id) (CallFunction|ShopServer :Cmd (cat "GWBuy " Id)))'
    none_msg = sel('Id', {2: q('fumigène'), 4: q('gaz rétrécissant'), 5: q('piège'), 9: q('pétard')}, q('bombe'))
    C['RequestUse'] = f'''
    (fn RequestUse (Id)
      (bind ps {PSC}
        (:then
          (if (== {PSG('GWRole')} 2)
            (return))
          (bind n {sel('Id', {2: PSG('Smokes'), 4: PSG('Gases'), 5: PSG('Traps'), 9: PSG('Crackers')}, PSG('Bombs'))})
          (if (<= n 0)
            (CallFunction|Notice :Msg (cat "Pas de " {none_msg} (select (== Id 9) " : le junkie en vend (toilettes)." " : le barman en vend (salle de billard).")))
            (return))
          (CallFunction|ShopServer :Cmd (cat "GWUseItem " Id " " (.yaw (Pawn|GetControlRotation :self self)))))
        (:CastFailed)))
    '''
    for f, i in (('UseSmoke', 2), ('UseGas', 4), ('UseTrap', 5), ('UseBomb', 6), ('UseCracker', 9)):
        C[f] = f'(fn {f} () (CallFunction|RequestUse :Id {i}))'
    C['ToggleLamp'] = f'''
    (fn ToggleLamp ()
      (bind ps {PSC}
        (:then
          (if (not {PSG('HasLamp')})
            (if (!= {PSG('GWRole')} 2)
              (CallFunction|Notice :Msg "Pas de lampe torche : le barman en vend une (20 $)."))
            (return))
          (Variables|Shop|SetLampOn (not (Variables|Shop|GetLampOn)))
          (Audio|PlaySound2D :Sound "/Game/GW/Audio/S_UI_Click.S_UI_Click" :VolumeMultiplier 0.5)
          (Development|PrintString :InString (cat "GW: lamp " (Variables|Shop|GetLampOn)) :bPrintToScreen false))
        (:CastFailed)))
    '''
    C['LampTick'] = f'''
    (fn LampTick ()
      ; the bought lamp (BP_GW_HandLamp, local) shines unless the blackout flashlight (s32) already does
      (bind want (and (and (Variables|Shop|GetLampOn) (not (Variables|GW|GetDarkOn))) (CallFunction|CanShop)))
      (if want
        (if (not ({ISVALID} :Object (Variables|Shop|GetLampActor)))
          (Variables|Shop|SetLampActor (Game|SpawnActorfromClass :Class "{LAMPC}" :SpawnTransform (Math|Transform|MakeTransform) :CollisionHandlingOverride "AlwaysSpawn")))
        (Rendering|SetActorHiddenInGame :self (Variables|Shop|GetLampActor) :bNewHidden false)
        (return))
      (if ({ISVALID} :Object (Variables|Shop|GetLampActor))
        (Rendering|SetActorHiddenInGame :self (Variables|Shop|GetLampActor) :bNewHidden true)))
    '''
    C['ShowShopPrompt'] = '''
    (fn ShowShopPrompt (Key Label At)
      (Variables|Shop|SetPromptOn true)
      (if (not (GW|Call|/Script/Engine.KismetSystemLibrary|IsValid :Object (Variables|Shop|GetShopPrompt)))
        (Variables|Shop|SetShopPrompt (Game|SpawnActorfromClass :Class "/Game/GW/Blueprints/BP_GW_KeyPrompt.BP_GW_KeyPrompt_C" :SpawnTransform (Math|Transform|MakeTransform :Location At) :CollisionHandlingOverride "AlwaysSpawn"))
        (Variables|Shop|SetShopPromptTxt ""))
      (bind kp (Variables|Shop|GetShopPrompt))
      (if (Utilities|String|NotEqualExactly(String) (Variables|Shop|GetShopPromptTxt) (cat Key Label))
        (Variables|Shop|SetShopPromptTxt (cat Key Label))
        (GW|Call|BP_GW_KeyPrompt|SetPrompt :self kp :Key Key :Label Label))
      (Transformation|SetActorLocation :self kp :NewLocation At :bSweep false :bTeleport true)
      (GW|Call|BP_GW_KeyPrompt|ShowPrompt :self kp :On true))
    '''
    C['PromptPick'] = f'''
    (fn PromptPick ()
      ; floating key prompts: the barman (guests), a bomb (detectives), a doorway with a trap in the pocket (guests)
      (bind p (Pawn|GetControlledPawn :self self))
      (bind ps {PSC}
        (:then
          (bind role {PSG('GWRole')})
          (if (not (CallFunction|CanShop))
            (if (and (== role 2) (CallFunction|NearBomb :R 260.0))
              (bind ch {MYCH}
                (:then
                  (if (not (GW|Get|BP_GW_Character|IsDead :self ch))
                    (CallFunction|ShowShopPrompt :Key "E" :Label (select (Variables|Shop|GetDefuseHold) (cat "Désamorçage… " (Math|Float|Truncate (* (Variables|Shop|GetDefuseProgress) 100.0)) " %") "Maintenir : désamorcer") :At (+ (Transformation|GetActorLocation :self (Variables|Shop|GetBombRef)) {mv(0, 0, 60)}))))
                (:CastFailed)))
            (return))
          (bind (near kind) (CallFunction|NearVendor :R 330.0))
          (if (and near (not (CallFunction|ShopOpen)))
            (CallFunction|ShowShopPrompt :Key "E" :Label (select (== kind 1) "Le junkie (marché noir)" (select (== kind 2) "Le serveur (boutique)" "Le barman (boutique)")) :At (+ (Transformation|GetActorLocation :self (Variables|Shop|GetShopVendor)) {mv(0, 0, 118)}))
            (return))
          (if (> {PSG('Traps')} 0)
            (bind (top ax hw ok) (CallFunction|FindDoor :Loc (Transformation|GetActorLocation :self p)))
            (if ok
              (CallFunction|ShowShopPrompt :Key "T" :Label "Poser le piège ici" :At (- top {mv(0, 0, 45)})))))
        (:CastFailed)))
    '''
    C['PromptTick'] = f'''
    (fn PromptTick ()
      (Variables|Shop|SetPromptOn false)
      (CallFunction|PromptPick)
      (if (and (not (Variables|Shop|GetPromptOn)) ({ISVALID} :Object (Variables|Shop|GetShopPrompt)))
        (GW|Call|BP_GW_KeyPrompt|ShowPrompt :self (Variables|Shop|GetShopPrompt) :On false)))
    '''
    C['ShopClientTick'] = f'''
    (fn ShopClientTick ()
      (if (not (Pawn|IsLocalPlayerController))
        (return))
      (if (Utilities|HasLaunchOption :OptionToCheck "GWShopTest")
        (CallFunction|ShopTestTick))
      (CallFunction|PromptTick)
      (CallFunction|LampTick)
      (CallFunction|DefuseTick)
      (if (not (CallFunction|ShopOpen))
        (return))
      ; the shop closes by itself when you walk away (or the waiter does), die, become a detective or open the pause menu
      (Variables|Shop|SetShopPaused false)
      (bind hud (Variables|GW|GetHUDWidget))
      (if ({ISVALID} :Object hud)
        (bind pw (GW|Get|{HUD}|PauseW :self hud))
        (if ({ISVALID} :Object pw)
          (Variables|Shop|SetShopPaused (Appearance|IsinViewport :self pw))))
      (if (or (Variables|Shop|GetShopPaused) (not (CallFunction|CanShop)))
        (Development|PrintString :InString "GW: shop auto-closed (pause, death or role)" :bPrintToScreen false)
        (CallFunction|CloseShop)
        (return))
      (if (Variables|Shop|GetShopHere)
        (return))
      (bind sv (Variables|Shop|GetShopVendor))
      (if (not ({ISVALID} :Object sv))
        (CallFunction|CloseShop)
        (return))
      (bind d (Math|Vector|Distance2D(Vector) (Transformation|GetActorLocation :self sv) (Transformation|GetActorLocation :self (Pawn|GetControlledPawn :self self))))
      (if (> d (select (== (Variables|Shop|GetShopKind) 2) 400.0 480.0))
        (if (== (Variables|Shop|GetShopKind) 2)
          (CallFunction|Notice :Msg "Le serveur est reparti… Vous avez trop hésité !")
          (CallFunction|ShopServer :Cmd "GWStaffLine 7"))
        (Development|PrintString :InString (cat "GW: shop auto-closed (vendor kind " (Variables|Shop|GetShopKind) " now " d " cm away)") :bPrintToScreen false)
        (CallFunction|CloseShop)))
    '''
    C['GuestFire'] = f'''
    (fn GuestFire (Ch Start Dir)
      ; server: left click of a non-detective (s13 GWFire). Bullets -> the rifle; none -> GuestAttack (melee / throw)
      (if (GW|Get|BP_GW_Character|IsDead :self Ch)
        (return))
      (bind ps {PSC}
        (:then
          (if (<= {PSG('Ammo')} 0)
            (CallFunction|GuestAttack :Ch Ch)
            (return))
          (bind gm {GMC}
            (:then (GW|Call|BP_GW_GameMode|GuestShoot :self gm :Shooter Ch :Start Start :Dir Dir))
            (:CastFailed)))
        (:CastFailed)))
    '''
    C['GWBuy'] = f'''
    (fn GWBuy (Id)
      (bind gm {GMC}
        (:then
          (bind ps {PSC}
            (:then
              (if (not (CallFunction|CanShop))
                (GW|Call|BP_GW_GameMode|ShopPay :self gm :PS ps :Amount 0 :Note "Le barman ne sert que les invités.")
                (return))
              (bind (near kind) (CallFunction|NearVendor :R 450.0))
              (if (and (not near) (<= (Variables|Shop|GetShopAnywhere) 0))
                (GW|Call|BP_GW_GameMode|ShopPay :self gm :PS ps :Amount 0 :Note "Approchez-vous du barman (salle de billard) ou d'un serveur.")
                (return))
              ; the vendor's head (his line is said there); zero away from any vendor (dev "shop here")
              (Variables|Shop|SetAimSpot {mv(0, 0, 0)})
              (if near
                (Variables|Shop|SetAimSpot (+ (Transformation|GetActorLocation :self (Variables|Shop|GetShopVendor)) {mv(0, 0, 70)})))
              (GW|Call|BP_GW_GameMode|ShopBuy :self gm :PS ps :Id Id :Kind (select near kind (- (Variables|Shop|GetShopAnywhere) 1)) :At (Variables|Shop|GetAimSpot)))
            (:CastFailed)))
        (:CastFailed)))
    '''
    C['GWUseItem'] = f'''
    (fn GWUseItem (Id Yaw)
      (bind gm {GMC}
        (:then
          (bind ps {PSC}
            (:then
              (bind ch {MYCH}
                (:then
                  (if (or (== {PSG('GWRole')} 2) (GW|Get|BP_GW_Character|IsDead :self ch))
                    (return))
                  (GW|Call|BP_GW_GameMode|UseItem :self gm :PS ps :Ch ch :Id Id :Yaw Yaw))
                (:CastFailed)))
            (:CastFailed)))
        (:CastFailed)))
    '''
    C['GWDefuse'] = f'''
    (fn GWDefuse ()
      (bind gm {GMC}
        (:then
          (bind ps {PSC}
            (:then
              (if (!= {PSG('GWRole')} 2)
                (return))
              (bind ch {MYCH}
                (:then
                  (if (GW|Get|BP_GW_Character|IsDead :self ch)
                    (return))
                  (if (not (CallFunction|NearBomb :R 250.0))
                    (Development|PrintString :InString "GW: defuse refused (no bomb within 2.5 m)" :bPrintToScreen false)
                    (return))
                  (if (or (!= (Variables|Shop|GetDefuseStartBomb) (Variables|Shop|GetBombRef)) (< (- {STIME} (Variables|Shop|GetDefuseStartAt)) 1.7))
                    (Development|PrintString :InString "GW: defuse refused (E not held 2 s on this bomb)" :bPrintToScreen false)
                    (return))
                  (GW|Call|BP_GW_GameMode|DefuseBomb :self gm :B (Variables|Shop|GetBombRef) :P ch))
                (:CastFailed)))
            (:CastFailed)))
        (:CastFailed)))
    '''
    C['GWDevMoney'] = f'''
    (fn GWDevMoney (Amount)
    {GATE}
      (bind gm {GMC}
        (:then
          (bind ps {PSC}
            (:then
              (if (== Amount 0)
                {PSS('Money', 0)}
                (GW|Call|BP_GW_GameMode|ShopPay :self gm :PS ps :Amount 0 :Note "Bourse remise à zéro (menu dev)")
                (return))
              (GW|Call|BP_GW_GameMode|ShopPay :self gm :PS ps :Amount Amount :Note (cat "+" Amount " $ (menu dev)")))
            (:CastFailed)))
        (:CastFailed)))
    '''
    devgive = '\n'.join(f'''      (if (or (== Id {i}) (== Id 0))
            {PSADD(COUNT_OF[i], f'(select (== Id 0) {n} 1)')})''' for i, n in ((1, 3), (2, 2), (4, 2), (5, 2), (6, 2), (9, 2)))
    C['GWDevGive'] = f'''
    (fn GWDevGive (Id)
    {GATE}
      (bind ps {PSC}
        (:then
    {devgive}
          (if (or (== Id 3) (== Id 0))
            {PSS('HasLamp', 'true')})
          (if (or (== Id 7) (== Id 0))
            {PSADD('TurretAmmo', 60)})
          (if (or (== Id 8) (== Id 0))
            {PSS('HasSwapGun', 'true')})
          (Development|PrintString :InString (cat "GW: dev give " Id) :bPrintToScreen false))
        (:CastFailed)))
    '''
    C['GWDevBombNow'] = f'''
    (fn GWDevBombNow ()
    {GATE}
      (for b (Actor|GetAllActorsOfClass :ActorClass "{BOMB}")
        (GW|Set|{BOMB}|ExplodeAt :self b :ExplodeAt {STIME}))
      (Development|PrintString :InString "GW: dev bombs now" :bPrintToScreen false))
    '''
    C['GWDevShopHere'] = f'''
    (fn GWDevShopHere (On)
    {GATE}
      (Variables|Shop|SetShopAnywhere On)
      (Development|PrintString :InString (cat "GW: dev shop anywhere " On) :bPrintToScreen false))
    '''
    C['GWStaffLine'] = f'''
    (fn GWStaffLine (Ctx)
      ; server: the nearest waiter's "I'll be back" (7) when he walked off with this guest's card open; 1 per 5 s
      (if (or (!= Ctx 7) (< {STIME} (Variables|Shop|GetNextStaffLine)))
        (return))
      (Variables|Shop|SetNextStaffLine (+ {STIME} 5.0))
      (bind (near kind) (CallFunction|NearVendor :R 1500.0))
      (if (and near (== kind 2))
        (bind gm {GMC}
          (:then (GW|Call|BP_GW_GameMode|StaffSay :self gm :Cat 62 :Ctx 7 :Loc (+ (Transformation|GetActorLocation :self (Variables|Shop|GetShopVendor)) {mv(0, 0, 70)})))
          (:CastFailed))))
    '''
    C['GWDefuseStart'] = f'''
    (fn GWDefuseStart ()
      ; server: a detective starts holding E at a bomb (GWDefuse checks the 2 s)
      (if (not (CallFunction|DefuseOk))
        (return))
      (if (not (CallFunction|NearBomb :R 250.0))
        (return))
      (Variables|Shop|SetDefuseStartBomb (Variables|Shop|GetBombRef))
      (Variables|Shop|SetDefuseStartAt {STIME})
      (Development|PrintString :InString "GW: defuse started on the server" :bPrintToScreen false))
    '''
    C['GWDevGoBomb'] = f'''
    (fn GWDevGoBomb ()
      ; next to the nearest bomb (tests and dev menu)
    {GATE}
      (bind p (Pawn|GetControlledPawn :self self))
      (bind all (Actor|GetAllActorsOfClass :ActorClass "{BOMB}"))
      (if (or (== (Utilities|Array|Length all) 0) (not ({ISVALID} :Object p)))
        (Development|PrintString :InString "GW: dev go bomb: none" :bPrintToScreen false)
        (return))
      (bind bl (Transformation|GetActorLocation :self (Utilities|Array|Get(acopy) all 0)))
      (Transformation|SetActorLocation :self p :NewLocation (+ bl {mv(110, 0, 96)}) :bSweep false :bTeleport true)
      (Pawn|SetControlRotation :self self :NewRotation (Math|Rotator|MakeRotator :Roll 0.0 :Pitch -30.0 :Yaw 180.0))
      (Development|PrintString :InString (cat "GW: dev went to the bomb at " bl) :bPrintToScreen false))
    '''
    C['GWDevWaiters'] = f'''
    (fn GWDevWaiters (Mode)
      ; 0 normal, 1 frozen, 2 follow me
    {GATE}
      (bind gm {GMC}
        (:then
          (GW|Set|BP_GW_GameMode|WaiterMode :self gm :WaiterMode Mode)
          (if (== Mode 1)
            (for w (GW|Get|BP_GW_GameMode|Waiters :self gm)
              (GW|Call|BP_GW_GameMode|WaiterGo :self gm :W w :Dest (Transformation|GetActorLocation :self w))))
          (GW|Set|BP_GW_GameMode|WaiterFollow :self gm :WaiterFollow (Pawn|GetControlledPawn :self self))
          (Development|PrintString :InString (cat "GW: dev waiters mode " Mode) :bPrintToScreen false))
        (:CastFailed)))
    '''
    C['GWDevWaiterLeave'] = f'''
    (fn GWDevWaiterLeave ()
      ; the first waiter walks 8-15 m away right now (tests the shop closing when he leaves)
    {GATE}
      (bind gm {GMC}
        (:then (GW|Call|BP_GW_GameMode|WaiterLeave :self gm))
        (:CastFailed)))
    '''
    C['GWDevWaiter'] = f'''
    (fn GWDevWaiter ()
      ; go 1.5 m in front of a waiter; he waits 6 s more, then walks off (the open shop then closes by itself)
    {GATE}
      (bind p (Pawn|GetControlledPawn :self self))
      (bind all (Actor|GetAllActorsOfClass :ActorClass "{WAITER}"))
      (if (or (== (Utilities|Array|Length all) 0) (not ({ISVALID} :Object p)))
        (Development|PrintString :InString "GW: dev waiter: none" :bPrintToScreen false)
        (return))
      (bind w (Utilities|Array|Get(acopy) all 0))
      (bind wc (Utilities|Casting|CastToBP_GW_Waiter w)
        (:then
          (bind ai (Utilities|Casting|CastToAIController (Pawn|GetController :self wc))
            (:then
              (AI|Navigation|StopMovement :self ai)
              (GW|Set|{WAITER}|Moving :self wc :Moving false)
              (GW|Set|{WAITER}|NextMoveAt :self wc :NextMoveAt (+ {STIME} 6.0))
              (Transformation|SetActorLocation :self p :NewLocation (+ (Transformation|GetActorLocation :self wc) {mv(150, 0, 10)}) :bSweep false :bTeleport true)
              (Development|PrintString :InString (cat "GW: dev went to waiter " (Utilities|GetDisplayName :Object wc) " at " (Transformation|GetActorLocation :self wc)) :bPrintToScreen false))
            (:CastFailed)))
        (:CastFailed)))
    '''
    C['GWDevShopAim'] = f'''
    (fn GWDevShopAim (Mode)
      ; 0: go 3.8 m from the nearest NPC and face it; 1: aim at it from the camera (the left click then hits it)
    {GATE}
      (bind ch {MYCH}
        (:then
          (if (== Mode 0)
            (Variables|Default|SetBestD 3000.0)
            (bind me (Transformation|GetActorLocation :self ch))
            (for a (Actor|GetAllActorsOfClass :ActorClass {CHAR})
              (if (and (and (not (Pawn|IsPlayerControlled :self a)) (not (GW|Get|BP_GW_Character|IsDead :self a))) (== (GW|Get|BP_GW_Character|Kind :self a) 0))
                (bind d (Math|Vector|Distance(Vector) (Transformation|GetActorLocation :self a) me))
                (if (< d (Variables|Default|GetBestD))
                  (Variables|Default|SetBestD d)
                  (Variables|Shop|SetAimT a))))
            (bind t (Variables|Shop|GetAimT))
            (if ({ISVALID} :Object t)
              (bind tl (Transformation|GetActorLocation :self t))
              (Variables|Shop|SetAimOk false)
              (Variables|Shop|SetAimSpot (+ tl {mv(380, 0, 0)}))
              (if (not (Variables|Shop|GetAimOk))
                (bind (h0 ok0) (Collision|LineTraceByChannel :Start (+ tl {mv(0, 0, 40)}) :End (+ tl {mv(380.0, 0.0, 40)}) :TraceChannel "Visibility" :bTraceComplex false :bIgnoreSelf true))
                (if (not ok0)
                  (Variables|Shop|SetAimSpot (+ tl {mv(380.0, 0.0, 0)}))
                  (Variables|Shop|SetAimOk true)))
              (if (not (Variables|Shop|GetAimOk))
                (bind (h1 ok1) (Collision|LineTraceByChannel :Start (+ tl {mv(0, 0, 40)}) :End (+ tl {mv(268.7, 268.7, 40)}) :TraceChannel "Visibility" :bTraceComplex false :bIgnoreSelf true))
                (if (not ok1)
                  (Variables|Shop|SetAimSpot (+ tl {mv(268.7, 268.7, 0)}))
                  (Variables|Shop|SetAimOk true)))
              (if (not (Variables|Shop|GetAimOk))
                (bind (h2 ok2) (Collision|LineTraceByChannel :Start (+ tl {mv(0, 0, 40)}) :End (+ tl {mv(0.0, 380.0, 40)}) :TraceChannel "Visibility" :bTraceComplex false :bIgnoreSelf true))
                (if (not ok2)
                  (Variables|Shop|SetAimSpot (+ tl {mv(0.0, 380.0, 0)}))
                  (Variables|Shop|SetAimOk true)))
              (if (not (Variables|Shop|GetAimOk))
                (bind (h3 ok3) (Collision|LineTraceByChannel :Start (+ tl {mv(0, 0, 40)}) :End (+ tl {mv(-268.7, 268.7, 40)}) :TraceChannel "Visibility" :bTraceComplex false :bIgnoreSelf true))
                (if (not ok3)
                  (Variables|Shop|SetAimSpot (+ tl {mv(-268.7, 268.7, 0)}))
                  (Variables|Shop|SetAimOk true)))
              (if (not (Variables|Shop|GetAimOk))
                (bind (h4 ok4) (Collision|LineTraceByChannel :Start (+ tl {mv(0, 0, 40)}) :End (+ tl {mv(-380.0, 0.0, 40)}) :TraceChannel "Visibility" :bTraceComplex false :bIgnoreSelf true))
                (if (not ok4)
                  (Variables|Shop|SetAimSpot (+ tl {mv(-380.0, 0.0, 0)}))
                  (Variables|Shop|SetAimOk true)))
              (if (not (Variables|Shop|GetAimOk))
                (bind (h5 ok5) (Collision|LineTraceByChannel :Start (+ tl {mv(0, 0, 40)}) :End (+ tl {mv(-268.7, -268.7, 40)}) :TraceChannel "Visibility" :bTraceComplex false :bIgnoreSelf true))
                (if (not ok5)
                  (Variables|Shop|SetAimSpot (+ tl {mv(-268.7, -268.7, 0)}))
                  (Variables|Shop|SetAimOk true)))
              (if (not (Variables|Shop|GetAimOk))
                (bind (h6 ok6) (Collision|LineTraceByChannel :Start (+ tl {mv(0, 0, 40)}) :End (+ tl {mv(-0.0, -380.0, 40)}) :TraceChannel "Visibility" :bTraceComplex false :bIgnoreSelf true))
                (if (not ok6)
                  (Variables|Shop|SetAimSpot (+ tl {mv(-0.0, -380.0, 0)}))
                  (Variables|Shop|SetAimOk true)))
              (if (not (Variables|Shop|GetAimOk))
                (bind (h7 ok7) (Collision|LineTraceByChannel :Start (+ tl {mv(0, 0, 40)}) :End (+ tl {mv(268.7, -268.7, 40)}) :TraceChannel "Visibility" :bTraceComplex false :bIgnoreSelf true))
                (if (not ok7)
                  (Variables|Shop|SetAimSpot (+ tl {mv(268.7, -268.7, 0)}))
                  (Variables|Shop|SetAimOk true)))
              (Transformation|SetActorLocation :self ch :NewLocation (Variables|Shop|GetAimSpot) :bSweep false :bTeleport true)
              (Pawn|SetControlRotation :self self :NewRotation (Math|Rotator|FindLookatRotation :Start (Transformation|GetActorLocation :self ch) :Target tl))
              (Development|PrintString :InString (cat "GW: dev aim near " (Utilities|GetDisplayName :Object t)) :bPrintToScreen false))
            (return))
          (bind t2 (Variables|Shop|GetAimT))
          (if ({ISVALID} :Object t2)
            (bind cam (Transformation|GetWorldLocation :self (GW|Get|BP_GW_Character|FollowCamera :self ch)))
            (Pawn|SetControlRotation :self self :NewRotation (Math|Rotator|FindLookatRotation :Start cam :Target (+ (Transformation|GetActorLocation :self t2) {mv(0, 0, 25)})))
            (Development|PrintString :InString (cat "GW: dev aim from camera at " (Utilities|GetDisplayName :Object t2) " dist " (Math|Vector|Distance(Vector) cam (Transformation|GetActorLocation :self t2))) :bPrintToScreen false)))
        (:CastFailed)))
    '''
    C['ShopDump'] = f'''
    (fn ShopDump (St)
      (bind p (Pawn|GetControlledPawn :self self))
      (bind ps {PSC}
        (:then
          (Development|PrintString :InString (cat "GW shoptest step " St " money=" {PSG('Money')} " ammo=" {PSG('Ammo')} " smokes=" {PSG('Smokes')} " lamp=" {PSG('HasLamp')} "/" (Variables|Shop|GetLampOn) " gas=" {PSG('Gases')} " traps=" {PSG('Traps')} " bombs=" {PSG('Bombs')} " turret=" {PSG('TurretAmmo')} " swap=" {PSG('HasSwapGun')} " buys=" {PSG('ShopBuys')} " role=" {PSG('GWRole')} " shop=" (CallFunction|ShopOpen) " vendor=" (Variables|Shop|GetShopKind) " near=" (CallFunction|NearVendor :R 330.0) " prompt=" (Variables|Shop|GetPromptOn) "/" (Variables|Shop|GetShopPromptTxt) " world: traps=" (Utilities|Array|Length (Actor|GetAllActorsOfClass :ActorClass "{TRAP}")) " bombs=" (Utilities|Array|Length (Actor|GetAllActorsOfClass :ActorClass "{BOMB}")) " smoke=" (Utilities|Array|Length (Actor|GetAllActorsOfClass :ActorClass "{SMOKE}")) " guns=" (Utilities|Array|Length (Actor|GetAllActorsOfClass :ActorClass "{GUN}")) " shrink=" (Utilities|Array|Length (Actor|GetAllActorsOfClass :ActorClass "{SHRINK}")) " crackers=" {PSG('Crackers')} " vendors=" (Utilities|Array|Length (Actor|GetAllActorsOfClass :ActorClass "{BARMAN}")) " npcs=" (Utilities|Array|Length (Actor|GetAllActorsOfClass :ActorClass {CHAR})) " note=" {PSG('ShopNote')}) :bPrintToScreen false)
          (bind ch {MYCH}
            (:then
              (Development|PrintString :InString (cat "GW shoptest char " (Utilities|GetDisplayName :Object ch) " at " (Transformation|GetActorLocation :self ch) " hp=" (GW|Get|BP_GW_Character|Health :self ch) " scale=" (.x (Transformation|GetActorScale3D :self ch)) " walk=" (GW|Get|BP_GW_Character|WalkSpeed :self ch) " max=" (Class|CharacterMovementComponent|GetMaxWalkSpeed :self (GW|Get|/Script/Engine.Character|CharacterMovement :self ch)) " seeker=" (GW|Get|BP_GW_Character|IsSeeker :self ch)) :bPrintToScreen false))
            (:CastFailed)))
        (:CastFailed)))
    '''
    SRV = lambda c: f'(CallFunction|ShopServer :Cmd "{c}")'
    TEST = [
        (2, SRV('GWDevQuickTest 1')), (3, SRV('GWDevPiano')), (4, SRV('GWDevMoney 5000') + '\n    ' + SRV('GWDevPiano')), (5, '(CallFunction|ShopBuy :Id 2)'),
        (6, SRV('GWDevTeleport 4420 1440 130')), (8, '(CallFunction|TryShop)'),
        (9, '(CallFunction|ShopBuy :Id 1)\n    (CallFunction|ShopBuy :Id 1)\n    (CallFunction|ShopBuy :Id 2)'),
        (10, '(CallFunction|ShopBuy :Id 3)\n    (CallFunction|ShopBuy :Id 4)\n    (CallFunction|ShopBuy :Id 5)'),
        (11, '(CallFunction|ShopBuy :Id 6)\n    (CallFunction|ShopBuy :Id 6)\n    (CallFunction|ShopBuy :Id 7)\n    (CallFunction|ShopBuy :Id 8)\n    (CallFunction|ShopBuy :Id 3)'),
        (12, '(CallFunction|TryShop)'), (13, '(CallFunction|ToggleLamp)'), (14, '(CallFunction|UseSmoke)'), (15, '(CallFunction|UseGas)'),
        (17, SRV('GWDevNPCFreeze 1') + '\n    ' + SRV('GWDevShopAim 0')), (18, SRV('GWDevShopAim 1')), (19, '(CallFunction|RequestFire)'),
        (21, SRV('GWDevNPCFreeze 0') + '\n    ' + SRV('GWDevTeleport 4060 600 130')), (22, '(CallFunction|UseTrap)'),
        (23, SRV('GWDevTeleport 2925 3565 130')), (24, '(CallFunction|UseBomb)'), (25, SRV('GWDevTeleport 1085 1685 130')),
        (26, '(CallFunction|UseBomb)'), (27, '(CallFunction|ToggleLamp)\n    ' + SRV('GWDevRole 2')), (29, '(CallFunction|ShopBuy :Id 2)'),
        (30, SRV('GWDevTeleport 4000 600 130')), (32, SRV('GWDevTeleport 1150 1685 130')), (33, '(CallFunction|TryDefuse)'),
        (50, SRV('GWDevRole 1') + '\n    ' + SRV('GWDevMoney 0')), (51, SRV('GWDevGive 0')), (52, '(CallFunction|UseBomb)'),
        (53, SRV('GWDevBombNow')), (54, SRV('GWDevRespawn') + '\n    ' + SRV('GWDevMoney 1000')), (55, SRV('GWDevWaiter')), (56, '(CallFunction|TryShop)'), (57, '(CallFunction|ShopBuy :Id 9)'),
        (58, '(CallFunction|UseCracker)'), (62, SRV('GWDevTeleport 260 2130 130')), (63, '(CallFunction|TryShop)'),
        (64, '(CallFunction|ShopBuy :Id 9)\n    (CallFunction|ShopBuy :Id 2)'), (65, '(CallFunction|TryShop)'),
        (66, '(CallFunction|OpenShopHere :Kind 0)'), (67, '(CallFunction|ShopBuy :Id 4)'), (68, '(CallFunction|TryShop)'),
        (69, SRV('GWDevTestEnd')), (72, '(Development|ExecuteConsoleCommand :Command "quit" :SpecificPlayer self)'),
    ]
    C['ShopTestTick'] = '''
    (fn ShopTestTick ()
      ; -GWShopTest: one step every 2 s (real time), the state dumped after each
      (if (< (Utilities|Time|GetRealTimeSeconds) (Variables|Shop|GetShopTestAt))
        (return))
      (Variables|Shop|SetShopTestAt (+ (Utilities|Time|GetRealTimeSeconds) 2.0))
      (Variables|Shop|SetShopTestStep (+ (Variables|Shop|GetShopTestStep) 1))
      (bind st (Variables|Shop|GetShopTestStep))
    ''' + '\n'.join(f'  (if (== st {s})\n    {code})' for s, code in TEST) + '''
      (CallFunction|ShopDump :St st))
    '''
    for name, code in C.items():
        if name in shop_items.S40_OWNS:
            continue
        wr(pc, name, code)
    compile_bp(pc, quiet=True)
    _g = get_graph(pc, 'EventGraph')
    for _n in BT.find_nodes(_g):
        if _n.get_class().get_name() == 'K2Node_EnhancedInputAction' and BT.get_node_infos([_n])[0].type_id.endswith('IA_Interact'):
            _cp = gw_lib._pin(_n, 'Completed', unreal.EdGraphPinDirection.EGPD_OUTPUT)
            _links = [c.get_owning_node().get_node_title().replace(' ', '') for c in _cp.list_connected_pins()]
            if not _links:
                wire_input(pc, 'IA_Interact', {'Completed': 'DefuseRelease'})
                print('IA_Interact Completed -> DefuseRelease')
            elif 'DefuseRelease' not in _links:
                print('!!! IA_Interact Completed already used by', _links, ': DefuseRelease NOT wired')
    for k, (ia_name, (_, fn)) in enumerate(KEYS.items()):
        wire_input(pc, ia_name, {'Started': fn}, pos=(0, 5200 + 200 * k))
    finish(pc)
print('done: s34_shop', sorted(PARTS) or 'all', 'WBP_Shop' if EAL.does_asset_exist('/Game/GW/UI/WBP_Shop') else '(no WBP_Shop yet)')
