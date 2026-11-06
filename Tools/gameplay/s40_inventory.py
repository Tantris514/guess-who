"""The 4-slot inventory and the economy of the 2026-11-03 test feedback. Run it AFTER s12/s13/s33/s34/s35/s37/s38: it writes the
graphs listed in shop_items.S40_OWNS, which those scripts now skip.

Inventory: BP_GW_PlayerState.Slot0-3 (item ids, replicated) + InvSel; counts stay where they were (Ammo, Smokes, Balls...).
GM.InvSync (ShopTick and after each change) drops emptied items, gives new ones a free slot and puts them in hand, and sets
BP_GW_Character.HeldItem (replicated; 0 when dead or on the turret): THE value everything reads (gun in hand, sword, aiming).
Ids: 1 rifle, 2 smoke, 3 lamp, 4 gas, 5 trap, 6 bomb, 8 swap gun, 9 firecracker, 10 hidden blade (7 turret ammo takes no slot),
11 balls, 12 sword, 13 the detective's revolver (always there for role 2). Keys: 1-4, mouse wheel, left click uses (RequestFire),
Q throws the selected item away, C toggles first / third person, Space jumps. WBP_Inventory = the slots at the bottom.
Hold E (TryHold, HoldTick, GWHoldStart / GWHoldDone): search a body (money, sometimes an item), steal a small prop; plain E: the
mystery box (BP_GW_MysteryBox: 100 $, spins, the player takes his item whenever he likes), the kamikaze's bomb (BP_GW_BombDrop).
Lustres: BP_GW_ChandFall, a shot within reach of a chandelier: its ISM instances fall on every machine, shards, kills below.
Parts: UE_ARGS among assets ps ch fx ui gm pc (none = all). Usage: ue_run.py s40_inventory.py [parts]
"""
import sys, importlib, os, math, wave, struct, random
sys.path.insert(0, r'J:\Projets\Unreal_Projects\Guess Who\Tools\gameplay')
sys.path.insert(0, r'J:\Projets\Unreal_Projects\Guess Who\Tools\ui')
import gw_lib; importlib.reload(gw_lib)
from gw_lib import *
import shop_items; importlib.reload(shop_items)

ARGS = set(globals().get('UE_ARGS', []))
want = lambda part: not ARGS or part in ARGS
ERR = []
REP = unreal.BlueprintVariableReplication
V3 = unreal.Vector.static_struct()
TR = unreal.Transform.static_struct()
AT = unreal.AssetToolsHelpers.get_asset_tools()
SHOP = '/Game/GW/Blueprints/Shop'
GENA = '/Game/GW/Audio/Gen/inv'
ROOT = r'J:\Projets\Unreal_Projects\Guess Who'
ISVALID = 'GW|Call|/Script/Engine.KismetSystemLibrary|IsValid'
GSC = '(Utilities|Casting|CastToBP_GW_GameState (Game|GetGameState))'
GMC = '(Utilities|Casting|CastToBP_GW_GameMode (Game|GetGameMode))'
PSC = '(Utilities|Casting|CastToBP_GW_PlayerState (GW|Get|/Script/Engine.Controller|PlayerState))'
MYCH = '(Utilities|Casting|CastToBP_GW_Character (Pawn|GetControlledPawn :self self))'
CHAR = '"/Game/GW/Blueprints/BP_GW_Character.BP_GW_Character_C"'
PKF = '/Game/GW/Blueprints/Pickups'
PK = f'{PKF}/BP_GW_Pickup.BP_GW_Pickup_C'
HS = f'{PKF}/BP_GW_HeldSword.BP_GW_HeldSword_C'
FPC = f'{PKF}/BP_GW_FPItems.BP_GW_FPItems_C'
TB = f'{PKF}/BP_GW_ThrownBall.BP_GW_ThrownBall_C'
cp = lambda n: f'{SHOP}/{n}.{n}_C'
GUN, TRAP, BOMB, SMOKE, GAS, CRACKER, SMALL = (cp(n) for n in ('BP_GW_GuestGun', 'BP_GW_Trap', 'BP_GW_Bomb', 'BP_GW_SmokeBomb', 'BP_GW_GasPuff', 'BP_GW_Firecracker', 'BP_GW_SmallBlast'))
STEAL, BOX, DROP, FALL = (cp(n) for n in ('BP_GW_Stealable', 'BP_GW_MysteryBox', 'BP_GW_BombDrop', 'BP_GW_ChandFall'))
LAMPC = cp('BP_GW_HandLamp')
BARMAN = cp('BP_GW_Barman')
HUD = '/Game/GW/UI/WBP_HUD.WBP_HUD_C'
INVW = '/Game/GW/UI/WBP_Inventory.WBP_Inventory_C'
Sp = lambda v, ps='ps': f'(GW|Get|BP_GW_PlayerState|{v} :self {ps})'
SpS = lambda v, val, ps='ps': f'(GW|Set|BP_GW_PlayerState|{v} :self {ps} :{v} {val})'
SpA = lambda v, n, ps='ps': SpS(v, f'(+ {Sp(v, ps)} {n})', ps)
LOG = lambda s: f'(Development|PrintString :InString {s} :bPrintToScreen false)'
ALLITEMS = [13, 1, 2, 3, 4, 5, 6, 8, 9, 10, 11, 12, 14]
NAMES = {1: 'Fusil', 2: 'Fumigène', 3: 'Lampe', 4: 'Gaz', 5: 'Piège', 6: 'Bombe', 7: 'Tourelle', 8: 'Échange', 9: 'Pétard', 10: 'Lame', 11: 'Boules', 12: 'Épée', 13: 'Revolver', 14: 'Mascarade'}
COUNTVAR = {1: 'Ammo', 2: 'Smokes', 4: 'Gases', 5: 'Traps', 6: 'Bombs', 9: 'Crackers', 11: 'Balls', 14: 'Masks'}
BOOLVAR = {3: 'HasLamp', 8: 'HasSwapGun', 10: 'HasBlade', 12: 'HasSword'}
BLADE_PAY, BOX_PRICE = 100, 100
# small props that can be stolen: mesh name part -> (label, value)
PROPS = [('gramophone', 'le gramophone', 120), ('lamp_table', 'la lampe', 40), ('telephone', 'le téléphone', 60), ('typewriter', 'la machine à écrire', 80),
         ('radio_cathedral', 'le poste de radio', 90), ('candelabra', 'le candélabre', 70), ('vase_flowers', 'le vase', 30), ('bust_marble', 'le buste', 100),
         ('globe_floor', 'le globe', 60)]


def sel(var, mapping, default):
    e = default
    for k, v in reversed(list(mapping.items())):
        e = f'(select (== {var} {k}) {v} {e})'
    return e


def mv(x, y, z):
    return f'(Math|Vector|MakeVector {float(x)} {float(y)} {float(z)})'


def wr(bp, name, code):
    try:
        write(bp, name, code, compile_after=False)
    except Exception as e:
        ERR.append(f'{bp.get_name()}.{name}: {str(e)[-400:]}')


def finish(bp):
    ok = compile_bp(bp)
    pr = node_problems(bp)
    print(bp.get_name(), 'compiled' if ok else 'FAILED', pr[:6])
    save(bp)


def actor(name, replicated=True, life=0.0):
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
    c.set_editor_property('static_mesh', unreal.load_asset('/Engine/BasicShapes/' + asset))
    c.set_editor_property('override_materials', [unreal.load_asset('/Game/GW/Materials/' + mi)])
    c.set_editor_property('relative_location', unreal.Vector(*loc))
    c.set_editor_property('relative_rotation', unreal.Rotator(roll=rot[0], pitch=rot[1], yaw=rot[2]))
    c.set_editor_property('relative_scale3d', unreal.Vector(*scale))
    c.set_editor_property('cast_shadow', False)
    c.set_editor_property('visible', visible)
    c.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
    return c


# ================================================================ assets: the rifle mesh, two synthesized sounds
def synth(name, fn, secs):
    path = os.path.join(ROOT, 'AssetGen', 'audio', 'final', 'synth', name + '.wav')
    if not os.path.exists(path):
        rnd = random.Random(40)
        with wave.open(path, 'wb') as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(44100)
            n = int(secs * 44100)
            w.writeframes(b''.join(struct.pack('<h', int(max(-1.0, min(1.0, fn(i / 44100.0, rnd))) * 30000)) for i in range(n)))
    dest = f'{GENA}/{name}'
    if not EAL.does_asset_exist(dest):
        t = unreal.AssetImportTask()
        t.filename = path; t.destination_path = GENA; t.automated = True; t.replace_existing = True; t.save = False
        AT.import_asset_tasks([t])
        s = unreal.load_asset(dest)
        s.set_editor_property('sound_class_object', unreal.load_asset('/Game/GW/Audio/Classes/SC_GW_SFX'))
        EAL.save_loaded_asset(s, False)
    return f'"{dest}.{name}"'


def crash(t, r):       # a chandelier on the floor: thud, then glass shards
    thud = math.exp(-t * 16) * math.sin(2 * math.pi * 70 * t) * 0.9
    glass = math.exp(-t * 3.2) * (r.random() * 2 - 1) * (0.35 + 0.3 * math.sin(2 * math.pi * 3100 * t)) * (0.55 + 0.45 * math.sin(t * 90))
    return thud + glass


def jingle(t, r):      # the mystery box: a music-box arpeggio going round, ~3.6 s
    notes = [523.25, 659.25, 783.99, 1046.5, 783.99, 659.25]
    k = int(t * 8)
    tn = t - k / 8.0
    f = notes[k % 6] * (1.0 + 0.02 * (k // 6))
    return 0.5 * math.exp(-tn * 9) * (math.sin(2 * math.pi * f * t) + 0.4 * math.sin(4 * math.pi * f * t))


CRASH = synth('SFX_Chandelier_Crash', crash, 2.2)
JINGLE = synth('SFX_MysteryBox_Spin', jingle, 4.0)
COINS = '"/Game/GW/Audio/Gen/shop_buy/SFX_Shop_Coins.SFX_Shop_Coins"'


def make_rifle():
    """SM_GW_Rifle, placeholder until a real model: origin at the grip, barrel along +X, 118 cm, walnut stock + iron barrel.
    Written as an OBJ and imported (merge_static_mesh_actors returns nothing under -nullrhi)."""
    dest = f'{SHOP}/SM_GW_Rifle'
    def _mats(m):
        for i, x in enumerate(m.static_materials):
            m.set_material(i, unreal.load_asset('/Game/GW/Materials/' + ('MI_GW_Wood_Walnut' if 'wood' in str(x.material_slot_name).lower() else 'MI_GW_Iron')))
    if EAL.does_asset_exist(dest):
        _m0 = unreal.load_asset(dest)
        _mats(_m0)
        EAL.save_loaded_asset(_m0, False)
        return _m0
    for junk in ('iron', 'wood'):
        if EAL.does_asset_exist(f'{SHOP}/{junk}'):
            EAL.delete_asset(f'{SHOP}/{junk}')
    verts, faces = [], {'iron': [], 'wood': []}

    def poly(ring0, ring1, g):
        n = len(ring0); b0 = len(verts) + 1
        verts.extend(ring0 + ring1)
        for i in range(n):
            j = (i + 1) % n
            faces[g].append((b0 + i, b0 + j, b0 + n + j, b0 + n + i))
        faces[g].append(tuple(b0 + n - 1 - i for i in range(n)))
        faces[g].append(tuple(b0 + n + i for i in range(n)))

    def box(x0, x1, y, z0, z1, g, z0b=None, z1b=None):       # along X, half width y; the far end can differ (a sloped butt)
        z0b = z0 if z0b is None else z0b
        z1b = z1 if z1b is None else z1b
        poly([(x0, -y, z0), (x0, y, z0), (x0, y, z1), (x0, -y, z1)], [(x1, -y, z0b), (x1, y, z0b), (x1, y, z1b), (x1, -y, z1b)], g)

    def tube(x0, x1, r, z, g):
        ring = lambda x: [(x, r * math.cos(i * math.pi / 4), z + r * math.sin(i * math.pi / 4)) for i in range(8)]
        poly(ring(x0), ring(x1), g)
    tube(-4, 90, 1.3, 5.0, 'iron')           # the long barrel
    tube(-6, 8, 2.1, 4.5, 'iron')            # the breech
    box(-1, 66, 1.9, 0.2, 3.8, 'wood')       # the forend
    box(-32, -1, 2.1, -8.0, 3.6, 'wood', -3.0, 3.8)   # the butt, sloping down to the shoulder
    box(-5, 3, 1.5, -9.0, 0.5, 'wood')       # the grip
    box(84, 86, 0.35, 6.2, 8.6, 'iron')      # front sight
    box(4, 6, 1.1, 7.0, 8.4, 'iron')         # rear sight
    folder = os.path.join(ROOT, 'AssetGen', 'rifle')
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, 'SM_GW_Rifle.obj')
    with open(path, 'w') as f:
        for v in verts:
            f.write('v %.3f %.3f %.3f\n' % v)
        f.write('vt 0 0\n')
        vn = 0
        for g, fl in faces.items():
            f.write(f'usemtl {g}\n')       # no "g" line: each group would become a mesh of its own
            for poly_ in fl:
                A, B, C_ = verts[poly_[0] - 1], verts[poly_[1] - 1], verts[poly_[2] - 1]
                u_, v_ = [B[i] - A[i] for i in range(3)], [C_[i] - A[i] for i in range(3)]
                n_ = (u_[1] * v_[2] - u_[2] * v_[1], u_[2] * v_[0] - u_[0] * v_[2], u_[0] * v_[1] - u_[1] * v_[0])
                f.write('vn %.3f %.3f %.3f\n' % n_)
                vn += 1
                for k in range(1, len(poly_) - 1):
                    f.write('f ' + ' '.join(f'{i}/1/{vn}' for i in (poly_[0], poly_[k], poly_[k + 1])) + '\n')
    t = unreal.AssetImportTask()
    t.filename = path; t.destination_path = SHOP; t.destination_name = 'SM_GW_Rifle'; t.automated = True; t.replace_existing = True; t.save = False
    AT.import_asset_tasks([t])
    print('rifle import paths', list(t.imported_object_paths))
    if not EAL.does_asset_exist(dest):
        print('!!! rifle import failed')
        return None
    m = unreal.load_asset(dest)
    if not isinstance(m, unreal.StaticMesh):
        print('!!! rifle import gave', m)
        return None
    _mats(m)
    b_ = m.get_bounding_box()
    print('rifle imported', b_.min, b_.max, [str(x.material_slot_name) for x in m.static_materials])
    EAL.save_loaded_asset(m, False)
    return m


if want('assets'):
    print('rifle', make_rifle())

# ================================================================ player state
psb = load_bp('BP_GW_PlayerState')
if want('ps'):
    for v in ('Slot0', 'Slot1', 'Slot2', 'Slot3', 'InvSel'):
        ensure_var(psb, v, 'int', rep=REP.REPLICATED, category='Inv')
    ensure_var(psb, 'HasBlade', 'bool', rep=REP.REPLICATED, category='Inv')
    ensure_var(psb, 'BladeReadyAt', 'float', rep=REP.REPLICATED, category='Inv')     # server time (GM.Now); GM.BladeStrike enforces it, the slot shows it
    ensure_var(psb, 'BladeCdLen', 'float', rep=REP.REPLICATED, category='Inv')
    ensure_fn(psb, 'SlotGet', inputs=[('I', 'int')], outputs=[('Id', 'int')], pure=True)
    ensure_fn(psb, 'SlotOf', inputs=[('Id', 'int')], outputs=[('I', 'int')], pure=True)
    ensure_fn(psb, 'CountOf', inputs=[('Id', 'int')], outputs=[('N', 'int')], pure=True)
    ensure_fn(psb, 'HasRoom', inputs=[('Id', 'int')], outputs=[('Ok', 'bool')], pure=True)
    ensure_fn(psb, 'SlotSet', inputs=[('I', 'int'), ('V', 'int')])
    compile_bp(psb, quiet=True)
    G_ = lambda v: f'(Variables|Inv|Get{v})'
    GG = lambda v: f'(GW|Get|BP_GW_PlayerState|{v})'
    wr(psb, 'SlotGet', f'(fn SlotGet (I) (return (select (== I 0) {G_("Slot0")} (select (== I 1) {G_("Slot1")} (select (== I 2) {G_("Slot2")} (select (== I 3) {G_("Slot3")} 0))))))')
    wr(psb, 'SlotOf', f'(fn SlotOf (Id) (return (select (== {G_("Slot0")} Id) 0 (select (== {G_("Slot1")} Id) 1 (select (== {G_("Slot2")} Id) 2 (select (== {G_("Slot3")} Id) 3 -1))))))')
    cm = {**{k: GG(v) for k, v in COUNTVAR.items()}, **{k: f'(select {G_(v) if v == "HasBlade" else GG(v)} 1 0)' for k, v in BOOLVAR.items()}, 13: f'(select (== {GG("GWRole")} 2) 1 0)'}
    wr(psb, 'CountOf', f'(fn CountOf (Id) (return {sel("Id", cm, "0")}))')
    wr(psb, 'HasRoom', '(fn HasRoom (Id) (return (or (>= (CallFunction|SlotOf :Id Id) 0) (>= (CallFunction|SlotOf :Id 0) 0))))')
    wr(psb, 'SlotSet', '(fn SlotSet (I V)\n' + '\n'.join(f'  (if (== I {i}) (Variables|Inv|SetSlot{i} V))' for i in range(4)) + ')')
    finish(psb)

# ================================================================ character
ch = load_bp('BP_GW_Character')
chc = ch.generated_class()
if want('ch'):
    ensure_var(ch, 'HeldItem', 'int', rep=REP.REPLICATED, category='Inv')
    ensure_var(ch, 'Looted', 'bool', rep=REP.REPLICATED, category='Inv')
    ensure_var(ch, 'BoostUntil', 'float', rep=REP.REPLICATED, category='Inv')
    ensure_var(ch, 'BoostMul', 'float', rep=REP.REPLICATED, category='Inv')
    ensure_var(ch, 'BoostOn', 'bool', category='Inv')
    ensure_fn(ch, 'BoostApply')
    compile_bp(ch, quiet=True)
    # players jump (RequestJump); NPCs never call Jump
    cdo(ch).set_editor_property('jump_max_count', 1)
    wr(ch, 'BoostApply', '''
(fn BoostApply ()
  ; a speed boost (fire alarm, sprint jump) on the server and on the owner: over, the normal walk / sprint speed returns
  (bind now (GameState|GetServerWorldTimeSeconds :self (Game|GetGameState)))
  (if (> (Variables|Inv|GetBoostUntil) now)
    (Variables|Inv|SetBoostOn true)
    (Class|CharacterMovementComponent|SetMaxWalkSpeed :self (Variables|Character|GetCharacterMovement) :MaxWalkSpeed (* (select (Variables|GW|GetIsSprinting) (Variables|GW|GetSprintSpeed) (Variables|GW|GetWalkSpeed)) (Variables|Inv|GetBoostMul)))
    (return))
  (if (Variables|Inv|GetBoostOn)
    (Variables|Inv|SetBoostOn false)
    (CallFunction|SetSprint :On (Variables|GW|GetIsSprinting))))
''')
    finish(ch)

# ================================================================ actors
if want('fx'):
    # ---- the rifle in the hand (other players and third person): s25's revolver grip, carried over to the rifle's axes
    gun = load_bp('BP_GW_GuestGun', SHOP)
    rifle = unreal.load_asset(f'{SHOP}/SM_GW_Rifle') if EAL.does_asset_exist(f'{SHOP}/SM_GW_Rifle') else None
    ensure_var(gun, 'RifleMesh', obj_class=unreal.StaticMesh, category='FX')
    ensure_var(gun, 'RifleRel', struct=TR, category='FX')
    ensure_var(gun, 'SwapMesh', obj_class=unreal.StaticMesh, category='FX')      # s41_item_models.py sets it, with SwapRel
    ensure_var(gun, 'SwapRel', struct=TR, category='FX')
    ensure_var(gun, 'Model', 'int', rep=REP.REPLICATED, category='FX')           # 1 the rifle, 8 the swap pistol (GM.GunFor)
    compile_bp(gun, quiet=True)
    if rifle:
        c0 = cdo(ch)
        cdo(gun).set_editor_property('RifleMesh', rifle)
        rev = c0.get_editor_property('RevolverMesh')
        fm = list(c0.get_editor_property('FitMeshes'))
        fit = c0.get_editor_property('FitRels')[fm.index(rev)] if rev in fm else c0.get_editor_property('GunRel')
        # s37's reading of the revolver's shape: barrel = longest axis (thin end forward), grip = second axis
        sec = unreal.ProceduralMeshLibrary.get_section_from_static_mesh(rev, 0, 0)
        pts = [(p.x, p.y, p.z) for p in sec[0]]
        lo = [min(p[i] for p in pts) for i in range(3)]
        hi = [max(p[i] for p in pts) for i in range(3)]
        ext = [hi[i] - lo[i] for i in range(3)]
        a0, a1, _ = sorted(range(3), key=lambda i: -ext[i])
        mid0 = (lo[a0] + hi[a0]) / 2

        def spread(side):
            se = [p for p in pts if (p[a0] - mid0) * side > ext[a0] * 0.2]
            return (max(p[a1] for p in se) - min(p[a1] for p in se)) if se else 0.0
        fs = 1 if spread(1) <= spread(-1) else -1
        front = [p for p in pts if (p[a0] - mid0) * fs > ext[a0] * 0.3] or pts
        bl = sum(p[a1] for p in front) / len(front)
        ds = 1 if (hi[a1] - bl) > (bl - lo[a1]) else -1
        fwd = [0.0, 0.0, 0.0]; fwd[a0] = float(fs)
        up = [0.0, 0.0, 0.0]; up[a1] = float(-ds)
        right = [up[1] * fwd[2] - up[2] * fwd[1], up[2] * fwd[0] - up[0] * fwd[2], up[0] * fwd[1] - up[1] * fwd[0]]
        grip = [0.0, 0.0, 0.0]
        grip[a0] = (lo[a0] if fs > 0 else hi[a0]) + fs * ext[a0] * 0.18
        grip[a1] = bl + ds * (hi[a1] - bl if ds > 0 else bl - lo[a1]) * 0.6
        grip[3 - a0 - a1] = (lo[3 - a0 - a1] + hi[3 - a0 - a1]) / 2
        rq = fit.rotation
        axes = [rq.rotate_vector(unreal.Vector(*v)) for v in (fwd, right, up)]
        rot = unreal.MathLibrary.make_rotation_from_axes(axes[0], axes[1], axes[2])
        loc = unreal.MathLibrary.transform_location(fit, unreal.Vector(*grip))
        cdo(gun).set_editor_property('RifleRel', unreal.Transform(location=loc, rotation=rot, scale=unreal.Vector(1, 1, 1)))
        print('rifle rel', loc, rot, 'revolver axes', a0, fs, a1, ds)
    wr(gun, 'OnRep_Holder', f'''
(fn OnRep_Holder ()
  (bind h (Variables|FX|GetHolder))
  (if (not ({ISVALID} :Object h))
    (return))
  (bind swp (== (Variables|FX|GetModel) 8))
  (Components|StaticMesh|SetStaticMesh :self (Variables|Default|GetGun) :NewMesh (select swp (Variables|FX|GetSwapMesh) (Variables|FX|GetRifleMesh)))
  (bind m (GW|Get|/Script/Engine.Character|Mesh :self h))
  (Variables|FX|SetFitIdx (Utilities|Array|FindItem (GW|Get|BP_GW_Character|FitMeshes :self h) (GW|Get|BP_GW_Character|RevolverMesh :self h)))
  (if (>= (Variables|FX|GetFitIdx) 0)
    (Transformation|AttachActorToComponent :self self :Parent m :SocketName (Utilities|Array|Get(acopy) (GW|Get|BP_GW_Character|FitBones :self h) (Variables|FX|GetFitIdx)) :LocationRule "SnapToTarget" :RotationRule "SnapToTarget" :ScaleRule "SnapToTarget" :bWeldSimulatedBodies false)
    (else
      (Transformation|AttachActorToComponent :self self :Parent m :SocketName "hand_r" :LocationRule "SnapToTarget" :RotationRule "SnapToTarget" :ScaleRule "SnapToTarget" :bWeldSimulatedBodies false)))
  (Transformation|SetRelativeTransform :self (Variables|Default|GetGun) :NewTransform (select swp (Variables|FX|GetSwapRel) (Variables|FX|GetRifleRel)) :bSweep false :bTeleport true)
  ; in first person the owner has his own gun (FPGun)
  (Rendering|SetOwnerNoSee :self (Variables|Default|GetGun) :bNewOwnerNoSee (GW|Get|BP_GW_Character|ViewFP :self h))
  {LOG('(cat "GW: gun model " (Variables|FX|GetModel) " in the hand of " (Utilities|GetDisplayName :Object h))')})
''')
    finish(gun)

    # ---- an item on the floor (Q, GM.DropItem): one mesh chosen by ItemId, the tables are filled by s41_item_models.py
    dropa = actor('BP_GW_ItemDrop')
    mesh(dropa, 'Model', 'Cube', 'MI_GW_Brass', scale=(0.1, 0.1, 0.1))
    aura = ensure_component(dropa, 'Aura', unreal.PointLightComponent, 'DefaultSceneRoot')
    aura.set_editor_property('light_color', unreal.Color(r=255, g=205, b=120, a=255))
    aura.set_editor_property('intensity', 260.0)
    aura.set_editor_property('attenuation_radius', 130.0)
    aura.set_editor_property('relative_location', unreal.Vector(0, 0, 35))
    aura.set_editor_property('cast_shadows', False)
    ensure_var(dropa, 'ItemId', 'int', rep=REP.REP_NOTIFY, category='FX')
    ensure_var(dropa, 'Count', 'int', rep=REP.REPLICATED, category='FX')
    ensure_var(dropa, 'Meshes', obj_class=unreal.StaticMesh, array=True, category='FX')
    ensure_var(dropa, 'Mats', obj_class=unreal.MaterialInterface, array=True, category='FX')
    ensure_var(dropa, 'Xfs', struct=TR, array=True, category='FX')
    ensure_fn(dropa, 'OnRep_ItemId')
    compile_bp(dropa, quiet=True)
    wr(dropa, 'OnRep_ItemId', f'''
(fn OnRep_ItemId ()
  (bind i (Variables|FX|GetItemId))
  (bind tb (Variables|FX|GetMeshes))
  (if (or (<= i 0) (>= i (Utilities|Array|Length tb)))
    (return))
  (Components|StaticMesh|SetStaticMesh :self (Variables|Default|GetModel) :NewMesh (Utilities|Array|Get(acopy) tb i))
  (if ({ISVALID} :Object (Utilities|Array|Get(acopy) (Variables|FX|GetMats) i))
    (Rendering|Material|SetMaterial :self (Variables|Default|GetModel) :ElementIndex 0 :Material (Utilities|Array|Get(acopy) (Variables|FX|GetMats) i)))
  (Transformation|SetRelativeTransform :self (Variables|Default|GetModel) :NewTransform (Utilities|Array|Get(acopy) (Variables|FX|GetXfs) i) :bSweep false :bTeleport true))
''')
    finish(dropa)

    # ---- the trap's ghost: local, never replicated (PC.TrapGhostTick); s41_item_models.py gives Body the trap's model and the translucent material
    ghosta = actor('BP_GW_TrapGhost', replicated=False)
    mesh(ghosta, 'Body', 'Cube', 'MI_GW_Brass', scale=(0.18, 0.1, 0.05))
    mesh(ghosta, 'Span', 'Cube', 'MI_GW_Brass', loc=(0, 0, -6), scale=(1, 0.05, 0.05))
    ensure_var(ghosta, 'Unused', 'bool', category='FX')
    finish(ghosta)

    # ---- a stealable prop: no mesh of its own, it hides the level's prop
    st = actor('BP_GW_Stealable')
    ensure_var(st, 'PropActor', obj_class=unreal.Actor, rep=REP.REPLICATED, category='FX')
    ensure_var(st, 'Stolen', 'bool', rep=REP.REP_NOTIFY, category='FX')
    ensure_var(st, 'Value', 'int', rep=REP.REPLICATED, category='FX')
    ensure_var(st, 'Label', 'string', rep=REP.REPLICATED, category='FX')
    ensure_fn(st, 'OnRep_Stolen')
    compile_bp(st, quiet=True)
    wr(st, 'OnRep_Stolen', f'''
(fn OnRep_Stolen ()
  (bind a (Variables|FX|GetPropActor))
  (if ({ISVALID} :Object a)
    (Rendering|SetActorHiddenInGame :self a :bNewHidden (Variables|FX|GetStolen))
    (Collision|SetActorEnableCollision :self a :bNewActorEnableCollision (not (Variables|FX|GetStolen)))))
''')
    finish(st)

    # ---- the kamikaze's bomb, on the floor where he fell
    dr = actor('BP_GW_BombDrop')
    for k, (y, z) in enumerate(((-7, 3.5), (0, 3.5), (7, 3.5))):
        mesh(dr, f'Stick{k}', 'Cylinder', 'MI_GW_Lacquer_Red' if EAL.does_asset_exist('/Game/GW/Materials/MI_GW_Lacquer_Red') else 'MI_GW_Leather_Oxblood', loc=(0, y, z), rot=(0, 90, 0), scale=(0.065, 0.065, 0.3))
    mesh(dr, 'Clock', 'Cylinder', 'MI_GW_Brass', loc=(0, 0, 13), rot=(0, 90, 0), scale=(0.13, 0.13, 0.05))
    finish(dr)

    # ---- the mystery box
    bx = actor('BP_GW_MysteryBox')
    mesh(bx, 'Chest', 'Cube', 'MI_GW_Lacquer_Black', loc=(0, 0, 22), scale=(0.8, 0.5, 0.44))
    mesh(bx, 'Band', 'Cube', 'MI_GW_Brass', loc=(0, 0, 22), scale=(0.1, 0.52, 0.45))
    lid = ensure_component(bx, 'LidPivot', unreal.SceneComponent, 'DefaultSceneRoot')
    lid.set_editor_property('relative_location', unreal.Vector(0, -25, 44))
    mesh(bx, 'Lid', 'Cube', 'MI_GW_Brass', loc=(0, 25, 3), scale=(0.84, 0.54, 0.06), parent='LidPivot')
    lt = ensure_component(bx, 'Glow', unreal.PointLightComponent, 'DefaultSceneRoot')
    lt.set_editor_property('light_color', unreal.Color(r=255, g=190, b=90, a=255))
    lt.set_editor_property('intensity', 1800.0)
    lt.set_editor_property('attenuation_radius', 380.0)
    lt.set_editor_property('relative_location', unreal.Vector(0, 0, 80))
    lt.set_editor_property('cast_shadows', False)
    tx = ensure_component(bx, 'Sign', unreal.TextRenderComponent, 'DefaultSceneRoot')
    tx.set_editor_property('relative_location', unreal.Vector(0, 0, 95))
    tx.set_editor_property('world_size', 16.0)
    tx.set_editor_property('horizontal_alignment', unreal.HorizTextAligment.EHTA_CENTER)
    tx.set_editor_property('text_render_color', unreal.Color(r=255, g=215, b=120, a=255))
    tx.set_editor_property('text', '?')
    ensure_var(bx, 'State', 'int', rep=REP.REP_NOTIFY, category='FX')
    ensure_var(bx, 'Result', 'int', rep=REP.REPLICATED, category='FX')
    ensure_var(bx, 'Winner', obj_class=psb.generated_class(), rep=REP.REPLICATED, category='FX')
    ensure_var(bx, 'SpinAt', 'float', rep=REP.REPLICATED, category='FX')
    ensure_var(bx, 'Age', 'float', category='FX')
    ensure_var(bx, 'LidK', 'float', category='FX')
    ensure_fn(bx, 'OnRep_State')
    compile_bp(bx, quiet=True)
    import gw_lib as _g
    _ts = [getattr(x, 'type_id', x) for x in _g.find_types(bx, 'TextRender', limit=200)]
    print('textrender', [t for t in _ts if 'SetText' in t or 'K2_' in t][:6])
    TXT = [t for t in _ts if t.endswith('SetText') and 'Casting' not in t][0]
    allnames = sel('(% (Math|Float|Truncate (* age 8.0)) 12)', {i: f'"{n}"' for i, n in enumerate(NAMES.values())}, '"?"')
    wr(bx, 'OnRep_State', f'''
(fn OnRep_State ()
  (if (== (Variables|FX|GetState) 1)
    (Audio|PlaySoundatLocation :Sound {JINGLE} :Location (Transformation|GetActorLocation) :VolumeMultiplier 0.9))
  (if (== (Variables|FX|GetState) 2)
    (Audio|PlaySoundatLocation :Sound {COINS} :Location (Transformation|GetActorLocation) :VolumeMultiplier 0.8)))
''')
    wr(bx, 'EventGraph', f'''
(event EventTick (DeltaSeconds)
  (Variables|FX|SetAge (+ (Variables|FX|GetAge) DeltaSeconds))
  (bind age (Variables|FX|GetAge))
  (bind st (Variables|FX|GetState))
  (Variables|FX|SetLidK (Math|Interpolation|FInterpTo :Current (Variables|FX|GetLidK) :Target (select (> st 0) 1.0 0.0) :DeltaTime DeltaSeconds :InterpSpeed 4.0))
  (Transformation|SetRelativeRotation :self (Variables|Default|GetLidPivot) :NewRotation (Math|Rotator|MakeRotator :Roll (* (Variables|FX|GetLidK) 70.0) :Pitch 0.0 :Yaw 0.0))
  (bind sign (Variables|Default|GetSign))
  (bind pl (Game|GetPlayerCameraManager :PlayerIndex 0))
  (if ({ISVALID} :Object pl)
    (Transformation|SetWorldRotation :self sign :NewRotation (Math|Rotator|FindLookatRotation :Start (Transformation|GetWorldLocation :self sign) :Target (Transformation|GetActorLocation :self pl))))
  (if (== st 1)
    ({TXT} :self sign :Value (Utilities|Text|ToText(String) {allnames})))
  (if (== st 2)
    ({TXT} :self sign :Value (Utilities|Text|ToText(String) {sel('(Variables|FX|GetResult)', {k: f'"{v}"' for k, v in NAMES.items()}, '"?"')})))
  (if (== st 0)
    ({TXT} :self sign :Value (Utilities|Text|ToText(String) "?"))))
''')
    finish(bx)

    # ---- a falling chandelier: moves the level's ISM instances on every machine, puts them back when destroyed (new round)
    fa = actor('BP_GW_ChandFall')
    for k in range(8):
        mesh(fa, f'Shard{k}', 'Cube', 'MI_GW_Brass' if k % 2 else 'MI_GW_Chrome', scale=(0.06, 0.05, 0.02), visible=False)
    ensure_var(fa, 'Spot', struct=V3, rep=REP.REPLICATED, category='FX')
    ensure_var(fa, 'Radius', 'float', rep=REP.REPLICATED, category='FX')
    ensure_var(fa, 'FloorZ', 'float', rep=REP.REPLICATED, category='FX')
    ensure_var(fa, 'Index', 'int', rep=REP.REPLICATED, category='FX')
    ensure_var(fa, 'ShooterPS', obj_class=psb.generated_class(), category='FX')
    ensure_var(fa, 'Killed', 'bool', category='FX')
    ensure_var(fa, 'Age', 'float', category='FX')
    ensure_var(fa, 'Ready', 'bool', category='FX')
    ensure_var(fa, 'Broke', 'bool', category='FX')
    ensure_var(fa, 'Comps', obj_class=unreal.InstancedStaticMeshComponent, array=True, category='FX')
    ensure_var(fa, 'Idx', 'int', array=True, category='FX')
    ensure_var(fa, 'Base', struct=TR, array=True, category='FX')
    ensure_var(fa, 'TheLight', obj_class=unreal.PointLightComponent, category='FX')
    ensure_fn(fa, 'Gather')
    ensure_fn(fa, 'Place', inputs=[('Drop', 'float'), ('Hide', 'bool')])
    ensure_fn(fa, 'Shards', inputs=[('K', 'float')])
    ensure_fn(fa, 'FallTime', outputs=[('T', 'float')], pure=True)
    compile_bp(fa, quiet=True)
    wr(fa, 'FallTime', '''
(fn FallTime ()
  (return (Math|Float|Sqrt (/ (* 2.0 (Math|Float|Max(Float) 1.0 (- (.z (Variables|FX|GetSpot)) (Variables|FX|GetFloorZ)))) 980.0))))
''')
    wr(fa, 'Gather', f'''
(fn Gather ()
  ; the instances of this chandelier in the merged GW_Chandeliers ISMs: same x / y as the spot, from just below it up to the ceiling
  (bind sp (Variables|FX|GetSpot))
  (bind rr (* (Variables|FX|GetRadius) (Variables|FX|GetRadius)))
  (for a (Actor|GetAllActorswithTag :Tag "GW_Arch")
    (bind cs (Actor|GetComponentsByClass :self a :ComponentClass "/Script/Engine.InstancedStaticMeshComponent"))
    (for c cs
      (bind ism (Utilities|Casting|CastToInstancedStaticMeshComponent c)
        (:then
          (bind mname (Utilities|GetDisplayName :Object (Class|StaticMeshComponent|GetStaticMesh :self ism)))
          (if (or (Utilities|String|Contains :SearchIn mname :Substring "Chandelier") (Utilities|String|Contains :SearchIn (Utilities|GetDisplayName :Object a) :Substring "Chandelier"))
            (for i (range (Components|InstancedStaticMesh|GetInstanceCount :self ism))
              (bind (t ok) (Components|InstancedStaticMesh|GetInstanceTransform :self ism :InstanceIndex i :bWorldSpace true))
              (bind l (.location t))
              (bind dx (- (.x l) (.x sp)))
              (bind dy (- (.y l) (.y sp)))
              (if (and (< (+ (* dx dx) (* dy dy)) rr) (> (.z l) (- (.z sp) 200.0)))
                (Utilities|Array|Add :TargetArray (Variables|FX|GetComps) :NewItem ism)
                (Utilities|Array|Add :TargetArray (Variables|FX|GetIdx) :NewItem i)
                (Utilities|Array|Add :TargetArray (Variables|FX|GetBase) :NewItem t)))))
        (:CastFailed))))
  ; the point light of this chandelier goes out
  (for la (Actor|GetAllActorswithTag :Tag "GW_Light")
    (bind ll (Transformation|GetActorLocation :self la))
    (if (< (Math|Vector|Distance2D(Vector) ll sp) 60.0)
      (Rendering|SetActorHiddenInGame :self la :bNewHidden true)))
  {LOG('(cat "GW: chandelier " (Variables|FX|GetIndex) " falls, " (Utilities|Array|Length (Variables|FX|GetIdx)) " instances, floor z=" (Variables|FX|GetFloorZ))')})
''')
    wr(fa, 'Place', '''
(fn Place (Drop Hide)
  (bind comps (Variables|FX|GetComps))
  (bind idx (Variables|FX|GetIdx))
  (bind base (Variables|FX|GetBase))
  (for i (range (Utilities|Array|Length idx))
    (bind t (Utilities|Array|Get(acopy) base i))
    (bind ism (Utilities|Array|Get(acopy) comps i))
    (if (GW|Call|/Script/Engine.KismetSystemLibrary|IsValid :Object ism)
      (Components|InstancedStaticMesh|UpdateInstanceTransform :self ism :InstanceIndex (Utilities|Array|Get(acopy) idx i) :NewInstanceTransform (Math|Transform|MakeTransform :Location (- (.location t) (Math|Vector|MakeVector 0.0 0.0 Drop)) :Rotation (.rotation t) :Scale (select Hide (Math|Vector|MakeVector 0.001 0.001 0.001) (.scale t))) :bWorldSpace true :bMarkRenderStateDirty true :bTeleport true))))
''')
    shard_code = '\n'.join(
        f'  (Transformation|SetWorldLocation :self (Variables|Default|GetShard{k}) :NewLocation (+ c0 (Math|Vector|MakeVector (* {math.cos(k * 0.785) * 240:.1f} K) (* {math.sin(k * 0.785) * 240:.1f} K) (Math|Float|Max(Float) 3.0 (* (- K (* K K)) {90 + k * 22:.1f})))) :bSweep false :bTeleport true)\n'
        f'  (Rendering|SetVisibility :self (Variables|Default|GetShard{k}) :bNewVisibility (< K 3.5) :bPropagateToChildren false)' for k in range(8))
    wr(fa, 'Shards', f'''
(fn Shards (K)
  (bind sp (Variables|FX|GetSpot))
  (bind c0 (Math|Vector|MakeVector (.x sp) (.y sp) (+ (Variables|FX|GetFloorZ) 3.0)))
{shard_code})
''')
    wr(fa, 'EventGraph', f'''
(event EventTick (DeltaSeconds)
  (if (not (Variables|FX|GetReady))
    (if (> (Math|Vector|VectorLength (Variables|FX|GetSpot)) 1.0)
      (Variables|FX|SetReady true)
      (CallFunction|Gather))
    (return))
  (Variables|FX|SetAge (+ (Variables|FX|GetAge) DeltaSeconds))
  (bind age (Variables|FX|GetAge))
  (bind ft (CallFunction|FallTime))
  (if (< age ft)
    (CallFunction|Place :Drop (* (* age age) 490.0) :Hide false)
    (return))
  (if (not (Variables|FX|GetBroke))
    (Variables|FX|SetBroke true)
    ; shattered: most of it is gone, the shards fly
    (CallFunction|Place :Drop (- (.z (Variables|FX|GetSpot)) (Variables|FX|GetFloorZ)) :Hide true)
    (Audio|PlaySoundatLocation :Sound {CRASH} :Location (Variables|FX|GetSpot) :VolumeMultiplier 1.4))
  (bind k (* (- age ft) 2.2))
  (if (< k 4.0)
    (CallFunction|Shards :K k)))

(event EventEndPlay (EndPlayReason)
  (CallFunction|Place :Drop 0.0 :Hide false)
  (bind sp (Variables|FX|GetSpot))
  (for la (Actor|GetAllActorswithTag :Tag "GW_Light")
    (if (< (Math|Vector|Distance2D(Vector) (Transformation|GetActorLocation :self la) sp) 60.0)
      (Rendering|SetActorHiddenInGame :self la :bNewHidden false))))
''')
    finish(fa)

# ================================================================ widget: the slots at the bottom of the screen, the hold bar, the post-it card
if want('ui'):
    import uilib; importlib.reload(uilib)
    from uilib import add, canvas, text, brush, clear_tree, get_or_create, compile_widget, GOLD, GOLD_HI, IVORY
    W = get_or_create('WBP_Inventory')
    clear_tree(W)
    add(W, unreal.CanvasPanel, 'Root')
    BOT = ((0.5, 1.0), (0.5, 1.0))
    # the user, 2026-11-05: between the HUD's two panels, same Art Deco frame, large icons; Cd / CdT: a dark curtain and the seconds left while an item recharges (blade, swap gun)
    SW, SH, GAP, BY = 108.0, 92.0, 8.0, -14.0
    from uilib import tex as _tex
    for i in range(4):
        x = (i - 1.5) * (SW + GAP)
        sel_ = add(W, unreal.Image, f'Sel{i}', 'Root', var=True)
        sel_.widget.set_editor_property('brush', brush(None, (8, 8), 'image', tint=(GOLD_HI[0], GOLD_HI[1], GOLD_HI[2], 1.0)))
        canvas(sel_, BOT, (0.5, 1.0), pos=(x, BY + 3), size=(SW + 6, SH + 6), z=1)
        bg = add(W, unreal.Image, f'Bg{i}', 'Root')
        bg.widget.set_editor_property('brush', brush(_tex('T_UI_PanelSmall'), (SH, SH), 'box', 0.18, tint=(1, 1, 1, 0.97)))
        canvas(bg, BOT, (0.5, 1.0), pos=(x, BY), size=(SW, SH), z=2)
        ic = add(W, unreal.Image, f'Ic{i}', 'Root', var=True)
        ic.widget.set_editor_property('brush', brush(None, (60, 60), 'image'))
        canvas(ic, BOT, (0.5, 1.0), pos=(x, BY - 21), size=(60, 60), z=3)
        cd = add(W, unreal.Image, f'Cd{i}', 'Root', var=True)
        cd.widget.set_editor_property('brush', brush(None, (8, 8), 'image', tint=(0.0, 0.0, 0.0, 0.74)))
        cd.widget.set_editor_property('render_transform_pivot', unreal.Vector2D(0.5, 1.0))
        canvas(cd, BOT, (0.5, 1.0), pos=(x, BY - 5), size=(SW - 10, SH - 10), z=5)
        k = add(W, unreal.TextBlock, f'Key{i}', 'Root')
        text(k, str(i + 1), 'Display', 'Regular', 15, GOLD_HI, shadow=True)
        canvas(k, BOT, (0.5, 1.0), pos=(x - SW / 2 + 13, BY - SH + 26), auto=True, z=6)
        n = add(W, unreal.TextBlock, f'Nm{i}', 'Root', var=True)
        text(n, '', 'Sans', 'SemiBold', 13, IVORY, just='center', shadow=True)
        canvas(n, BOT, (0.5, 1.0), pos=(x, BY - 5), auto=True, z=6)
        c = add(W, unreal.TextBlock, f'Ct{i}', 'Root', var=True)
        text(c, '', 'Display', 'Regular', 18, GOLD_HI, shadow=True)
        canvas(c, BOT, (0.5, 1.0), pos=(x + SW / 2 - 16, BY - SH + 28), auto=True, z=6)
        ct = add(W, unreal.TextBlock, f'CdT{i}', 'Root', var=True)
        text(ct, '', 'Display', 'Regular', 46, IVORY, just='center', outline=2)
        canvas(ct, BOT, (0.5, 1.0), pos=(x, BY - 18), auto=True, z=7)
    hb = add(W, unreal.Image, 'HoldBack', 'Root', var=True)
    hb.widget.set_editor_property('brush', brush(None, (8, 8), 'image', tint=(0.0, 0.0, 0.0, 0.6)))
    canvas(hb, BOT, (0.5, 1.0), pos=(0, BY - SH - 8), size=(240, 6), z=2)
    hf = add(W, unreal.Image, 'HoldFill', 'Root', var=True)
    hf.widget.set_editor_property('brush', brush(None, (8, 8), 'image', tint=GOLD_HI))
    canvas(hf, BOT, (0.5, 1.0), pos=(0, BY - SH - 8), size=(240, 6), z=3)
    # the note: the shop's Art Deco card, centred, large, hidden unless a read opened it (Refresh)
    from uilib import size_box, border_brush, box_slot, image, H, VA, IVORY_DIM
    MID = ((0.5, 0.5), (0.5, 0.5))
    pg = add(W, unreal.SizeBox, 'PostGroup', 'Root', var=True); size_box(pg, w=680)
    canvas(pg, MID, (0.5, 0.5), auto=True, z=10)
    pg.widget.set_editor_property('visibility', unreal.SlateVisibility.HIDDEN)
    pcard = add(W, unreal.Border, 'PostCard', 'PostGroup')
    border_brush(pcard, 'T_UI_PanelSmall', 0.18, tint=(1, 1, 1, 0.98), pad=(56, 34, 56, 30), size=(200, 200))
    pb = add(W, unreal.VerticalBox, 'PostBody', 'PostCard')
    pt0 = add(W, unreal.TextBlock, 'PostTitle', 'PostBody'); text(pt0, 'NOTE TROUVÉE', 'Display', 'Regular', 34, GOLD_HI, spacing=420, just='center')
    box_slot(pt0, (0, 0, 0, 0), H.H_ALIGN_CENTER)
    pdv = add(W, unreal.Image, 'PostDiv', 'PostBody'); image(pdv, 'T_UI_Divider', (240, 50), tint=(0.75, 0.58, 0.3, 1)); box_slot(pdv, (0, 2, 0, 6), H.H_ALIGN_CENTER)
    pl1 = add(W, unreal.TextBlock, 'PostLine', 'PostBody'); text(pl1, '« Le code du coffre, dans le bureau : »', 'Serif', 'Italic', 28, IVORY, just='center')
    box_slot(pl1, (0, 0, 0, 10), H.H_ALIGN_CENTER)
    pt = add(W, unreal.TextBlock, 'PostText', 'PostBody', var=True)
    text(pt, '0000', 'Display', 'Regular', 96, GOLD_HI, spacing=260, just='center')
    box_slot(pt, (0, 0, 0, 12), H.H_ALIGN_CENTER)
    pl2 = add(W, unreal.TextBlock, 'PostHint', 'PostBody'); text(pl2, 'E : refermer', 'Sans', 'Regular', 17, IVORY_DIM, just='center')
    box_slot(pl2, (0, 0, 0, 0), H.H_ALIGN_CENTER)
    compile_widget(W)
    ensure_var(W, 'Sig', 'string', category='Inv')
    ensure_var(W, 'PostUntil', 'float', category='Inv')
    ensure_fn(W, 'Refresh', inputs=[('PS', psb.generated_class()), ('Hold', 'float')])
    ensure_fn(W, 'ShowPostIt', inputs=[('Code', 'int')])
    ensure_fn(W, 'HidePost')
    ensure_var(W, 'Icons', obj_class=unreal.Texture2D, array=True, category='Inv')
    compile_bp(W, quiet=True)
    _ic = [None] * 14
    for _i in range(1, 14):
        _p = f'/Game/GW/UI/Items/T_UI_Item_{_i:02d}'
        if EAL.does_asset_exist(_p):
            _ic[_i] = unreal.load_asset(_p)
    cdo(W).set_editor_property('Icons', _ic)
    VI = lambda n: f'(Variables|WBP_Inventory|Get{n})'
    import re; SWAP_RELOAD_S = re.search(r"^BALL_BACK, SWORD_BACK, SWAP_RELOAD = .*, ([\d.]+)", open(r'J:\Projets\Unreal_Projects\Guess Who\Tools\gameplay\s38_pickups.py', encoding='utf-8').read(), re.M).group(1)
    nm = sel('id', {k: f'"{v}"' for k, v in NAMES.items()}, '""')
    rows = '\n'.join(f'''  (bind id (GW|Call|BP_GW_PlayerState|SlotGet :self PS :I {i}))
  (Widget|SetText(Text) :self {VI(f'Nm{i}')} :InText (Utilities|Text|ToText(String) {nm.replace('id', f'id')}))
  (bind n (GW|Call|BP_GW_PlayerState|CountOf :self PS :Id id))
  (Widget|SetText(Text) :self {VI(f'Ct{i}')} :InText (Utilities|Text|ToText(String) (select (> n 1) (cat "x" n) "")))
  (GW|Call|/Script/UMG.Image|SetBrushFromTexture :self {VI(f'Ic{i}')} :Texture (Utilities|Array|Get(acopy) (Variables|Inv|GetIcons) (Math|Integer|Max(Integer) 0 (Math|Integer|Min(Integer) 13 id))) :bMatchSize false)
  (bind rem (select (== id 10) (- (GW|Get|BP_GW_PlayerState|BladeReadyAt :self PS) srvNow) (select (== id 8) (- (GW|Get|BP_GW_PlayerState|SwapReadyAt :self PS) srvNow) 0.0)))
  (bind cdFrac (Math|Float|Clamp(Float) :Value (/ rem (select (== id 10) (Math|Float|Max(Float) (GW|Get|BP_GW_PlayerState|BladeCdLen :self PS) 0.1) {SWAP_RELOAD_S})) :Min 0.0 :Max 1.0))
  (Widget|SetRenderOpacity :self {VI(f'Ic{i}')} :InOpacity (select (> id 0) (select (> rem 0.0) 0.5 1.0) 0.0))
  (Widget|SetRenderOpacity :self {VI(f'Cd{i}')} :InOpacity (select (> rem 0.0) 1.0 0.0))
  (Widget|Transform|SetRenderScale :self {VI(f'Cd{i}')} :Scale (Math|Vector2D|MakeVector2D 1.0 (Math|Float|Max(Float) cdFrac 0.001)))
  (Widget|SetText(Text) :self {VI(f'CdT{i}')} :InText (Utilities|Text|ToText(String) (select (> rem 0.0) (cat "" (Math|Float|Truncate (+ rem 0.999))) "")))
  (Widget|SetRenderOpacity :self {VI(f'Sel{i}')} :InOpacity (select (== (GW|Get|BP_GW_PlayerState|InvSel :self PS) {i}) 1.0 0.0))'''.replace('(bind id ', f'(bind id{i} ').replace('(bind n ', f'(bind n{i} ').replace('(bind rem ', f'(bind rem{i} ').replace('(bind cdFrac ', f'(bind cdFrac{i} ').replace('(== id ', f'(== id{i} ').replace(':Id id)', f':Id id{i})').replace('13 id)', f'13 id{i})').replace('(> id 0)', f'(> id{i} 0)').replace('(> n 1)', f'(> n{i} 1)').replace('"x" n)', f'"x" n{i})').replace('(> rem 0.0)', f'(> rem{i} 0.0)').replace('(+ rem 0.999)', f'(+ rem{i} 0.999)').replace('(/ rem ', f'(/ rem{i} ').replace('cdFrac 0.001', f'cdFrac{i} 0.001') for i in range(4))
    wr(W, 'Refresh', f'''
(fn Refresh (PS Hold)
  (Widget|SetRenderOpacity :self {VI('HoldBack')} :InOpacity (select (> Hold 0.0) 1.0 0.0))
  (Widget|SetRenderOpacity :self {VI('HoldFill')} :InOpacity (select (> Hold 0.0) 1.0 0.0))
  (Widget|Transform|SetRenderScale :self {VI('HoldFill')} :Scale (Math|Vector2D|MakeVector2D (Math|Float|Clamp(Float) :Value Hold :Min 0.001 :Max 1.0) 1.0))
  (if (> (Variables|Inv|GetPostUntil) (Utilities|Time|GetRealTimeSeconds))
    (Widget|SetVisibility :self {VI('PostGroup')} :InVisibility "Visible")
    (else
      (Widget|SetVisibility :self {VI('PostGroup')} :InVisibility "Hidden")))
  (bind gs0 (Game|GetGameState))
  (if (not ({ISVALID} :Object gs0))
    (return))
  (bind srvNow (GameState|GetServerWorldTimeSeconds :self gs0))
{rows})
''')
    wr(W, 'ShowPostIt', f'''
(fn ShowPostIt (Code)
  (Variables|Inv|SetPostUntil (+ (Utilities|Time|GetRealTimeSeconds) 10.0))
  (Widget|SetText(Text) :self {VI('PostText')} :InText (Utilities|Text|ToText(String) (cat "" Code)))
  (Widget|SetVisibility :self {VI('PostGroup')} :InVisibility "Visible")
  (Audio|PlaySound2D :Sound "/Game/GW/Audio/S_UI_Card.S_UI_Card" :VolumeMultiplier 0.7))
''')
    wr(W, 'HidePost', f'''
(fn HidePost ()
  (Variables|Inv|SetPostUntil 0.0)
  (Widget|SetVisibility :self {VI('PostGroup')} :InVisibility "Hidden")
  (Audio|PlaySound2D :Sound "/Game/GW/Audio/S_UI_Click.S_UI_Click" :VolumeMultiplier 0.4))
''')
    compile_bp(W)
    print('WBP_Inventory', node_problems(W))
    compile_widget(W)

# ================================================================ game mode
gm = load_bp('BP_GW_GameMode')
if want('gm') or want('pc'):
    trapc, bxc, stc, drc, fac = (load_bp(n, SHOP).generated_class() for n in ('BP_GW_Trap', 'BP_GW_MysteryBox', 'BP_GW_Stealable', 'BP_GW_BombDrop', 'BP_GW_ChandFall'))
PSCLS = psb.generated_class()
exec(open(r'J:\Projets\Unreal_Projects\Guess Who\Tools\gameplay\s40_gm.py', encoding='utf-8').read())
exec(open(r'J:\Projets\Unreal_Projects\Guess Who\Tools\gameplay\s40_pc.py', encoding='utf-8').read())

print('DSL ERRORS', len(ERR))
for e in ERR:
    print('  ', e)
print('s40 done', sorted(ARGS) or 'all')
