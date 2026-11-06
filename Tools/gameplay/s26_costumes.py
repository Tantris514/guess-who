"""Costume system for BP_GW_Character: rigid pieces on bones + matte fabric/skin body material.

Slots (StaticMeshComponents, re-attached to the bone of their fit entry every ApplyLook):
  ShellMesh (coat / bodice / stole), SkirtMesh, HairMesh, MaskMesh, HatMesh, GunMesh.
Fit table (CDO arrays, filled by s25_costume_import.py / s22_items.py): FitMeshes[i] -> FitBones[i], FitRels[i] (bone space),
  FitColors[i] (dominant colour, used for the mannequin sleeves / trousers / under-dress under that piece).
Outfit pool (same for NPCs and disguised players, from the replicated OutfitIndex):
  OutfitIndex in [0, 2*NumPerBody): < NumPerBody = man (Manny), else woman (Quinn); k = OutfitIndex % NumPerBody.
  man:   shell = PoolShellM[k]   hair = PoolHairM[k/2]   mask = PoolMask[k + k/4]   top hat if k % 3 == 0
         (while no men's hair is approved: top hat for k % 3 != 2, the others bare-headed with a mask)
  woman: skirt = PoolSkirt[k]    top = PoolShellF[k] (same gown colour) or the stole when k/4 is odd   hair = PoolHairF[k/8]      mask = PoolMask[k + k/4]   cloche if k % 5 == 3
  detective: Manny, SeekerShell (if any), fedora, revolver, PoolHairM[0]
Empty pools -> the slot stays empty and the body tint palette (TorsoColors/LegColors) shows instead.
"""
import sys, importlib
sys.path.insert(0, r'J:\Projets\Unreal_Projects\Guess Who\Tools\gameplay')
import gw_lib; importlib.reload(gw_lib)
from gw_lib import *

ch = load_bp('BP_GW_Character')
SM = unreal.StaticMesh
LC = unreal.LinearColor.static_struct()
TR = unreal.Transform.static_struct()
ISVALID = 'GW|Call|/Script/Engine.KismetSystemLibrary|IsValid'
SETVEC = 'GW|Call|/Script/Engine.MaterialInstanceDynamic|SetVectorParameterValue'

for n in ('HairMesh', 'ShellMesh', 'SkirtMesh'):
    t = ensure_component(ch, n, unreal.StaticMeshComponent, 'Mesh')
    t.set_collision_profile_name('NoCollision')
    t.set_editor_property('generate_overlap_events', False)
    t.set_editor_property('can_character_step_up_on', unreal.CanBeCharacterBase.ECB_NO)
for n in ('PoolShellM', 'PoolShellF', 'PoolSkirt', 'PoolHairM', 'PoolHairF', 'PoolMask', 'FitMeshes'):
    ensure_var(ch, n, obj_class=SM, array=True, category='Costume')
for n in ('SeekerShell', 'ClocheMesh', 'StoleMesh'):
    ensure_var(ch, n, obj_class=SM, category='Costume')
ensure_var(ch, 'FitRels', struct=TR, array=True, category='Costume')
ensure_var(ch, 'FitColors', struct=LC, array=True, category='Costume')
ensure_var(ch, 'FitBones', 'name', array=True, category='Costume')
ensure_var(ch, 'SkinTones', struct=LC, array=True, category='Costume')
ensure_var(ch, 'NumPerBody', 'int', category='Costume')
ensure_var(ch, 'BodyMatM', obj_class=unreal.MaterialInterface, category='Costume')
ensure_var(ch, 'BodyMatF', obj_class=unreal.MaterialInterface, category='Costume')
ensure_var(ch, 'BodyMID', obj_class=unreal.MaterialInstanceDynamic, category='Costume')
ensure_fn(ch, 'Pick', inputs=[('Pool', (SM, 'array')), ('N', 'int')], outputs=[('M', SM)], pure=True)
ensure_fn(ch, 'FitColorOf', inputs=[('M', SM), ('Fallback', LC)], outputs=[('C', LC)], pure=True)
ensure_fn(ch, 'ApplySlot', inputs=[('Comp', unreal.StaticMeshComponent), ('M', SM)])
compile_bp(ch, quiet=True)

W = {}
W['Pick'] = '''
(fn Pick (Pool N)
  (bind n (Utilities|Array|Length Pool))
  (if (> n 0)
    (return (Utilities|Array|Get(acopy) Pool (% (Math|Integer|Max(Integer) N 0) n)))
    (else
      (return))))
'''
W['FitColorOf'] = '''
(fn FitColorOf (M Fallback)
  (bind i (Utilities|Array|FindItem (Variables|Costume|GetFitMeshes) M))
  (if (and (>= i 0) (< i (Utilities|Array|Length (Variables|Costume|GetFitColors))))
    (return (Utilities|Array|Get(acopy) (Variables|Costume|GetFitColors) i))
    (else
      (return Fallback))))
'''
W['ApplySlot'] = f'''
(fn ApplySlot (Comp M)
  (bind ok ({ISVALID} :Object M))
  (Components|StaticMesh|SetStaticMesh :self Comp :NewMesh M)
  (Rendering|SetVisibility :self Comp :bNewVisibility ok)
  (if ok
    ; reset any older override (placeholder material) to the piece's own material
    (Rendering|Material|SetMaterial :self Comp :ElementIndex 0 :Material (GW|Call|/Script/Engine.StaticMesh|GetMaterial :self M :MaterialIndex 0))
    (bind i (Utilities|Array|FindItem (Variables|Costume|GetFitMeshes) M))
    (if (>= i 0)
      (Transformation|AttachComponentToComponent :self Comp :Parent (Variables|Character|GetMesh) :SocketName (Utilities|Array|Get(acopy) (Variables|Costume|GetFitBones) i) :LocationRule "KeepRelative" :RotationRule "KeepRelative" :ScaleRule "KeepRelative")
      (Transformation|SetRelativeTransform :self Comp :NewTransform (Utilities|Array|Get(acopy) (Variables|Costume|GetFitRels) i)))))
'''


def pick(pool, n):
    return f'(CallFunction|Pick :Pool (Variables|Costume|Get{pool}) :N {n})'


W['ApplyLook'] = f'''
(fn ApplyLook ()
  (bind mesh (Variables|Character|GetMesh))
  (bind seeker (Variables|GW|GetIsSeeker))
  (bind npb (Math|Integer|Max(Integer) (Variables|Costume|GetNumPerBody) 1))
  (bind oi (Math|Integer|Max(Integer) (Variables|GW|GetOutfitIndex) 0))
  (bind female (and (not seeker) (>= oi npb)))
  (bind k (% oi npb))
  (Components|SkeletalMesh|SetSkeletalMeshAsset :self mesh :NewMesh (select female (Variables|GW|GetBodyFemale) (Variables|GW|GetBodyMale)))
  ; costume pieces
  (bind useStole (and (== (% (/ k 4) 2) 1) ({ISVALID} :Object (Variables|Costume|GetStoleMesh))))
  (bind shellM (select seeker (Variables|Costume|GetSeekerShell) (select female (select useStole (Variables|Costume|GetStoleMesh) {pick('PoolShellF', 'k')}) {pick('PoolShellM', 'k')})))
  (bind skirtM (select female {pick('PoolSkirt', 'k')} (GW|Call|/Script/Engine.KismetSystemLibrary|Conv_InterfaceToObject)))
  (CallFunction|ApplySlot :Comp (Variables|Default|GetShellMesh) :M shellM)
  (CallFunction|ApplySlot :Comp (Variables|Default|GetSkirtMesh) :M skirtM)
  ; the gowns are floor-length rigid shells: a walking stride pushed a knee or heel through every skirt
  ; (Tools/qa/motion QA). Nothing of the legs shows under a gown, so they are hidden instead.
  (if (and female ({ISVALID} :Object skirtM))
    (GW|Call|/Script/Engine.SkinnedMeshComponent|HideBoneByName :self mesh :BoneName "thigh_l" :PhysBodyOption "PBO_None")
    (GW|Call|/Script/Engine.SkinnedMeshComponent|HideBoneByName :self mesh :BoneName "thigh_r" :PhysBodyOption "PBO_None")
    (else
      (GW|Call|/Script/Engine.SkinnedMeshComponent|UnHideBoneByName :self mesh :BoneName "thigh_l")
      (GW|Call|/Script/Engine.SkinnedMeshComponent|UnHideBoneByName :self mesh :BoneName "thigh_r")))
  (CallFunction|ApplySlot :Comp (Variables|Default|GetHairMesh) :M (select female {pick('PoolHairF', '(/ k 8)')} {pick('PoolHairM', '(select seeker 0 (/ k 2))')}))
  (CallFunction|ApplySlot :Comp (Variables|Default|GetMaskMesh) :M (select seeker (GW|Call|/Script/Engine.KismetSystemLibrary|Conv_InterfaceToObject) {pick('PoolMask', '(+ k (/ k 4))')}))
  (CallFunction|ApplySlot :Comp (Variables|Default|GetHatMesh) :M (select seeker (Variables|GW|GetFedoraMesh) (select female (select (== (% k 5) 3) (Variables|Costume|GetClocheMesh) (GW|Call|/Script/Engine.KismetSystemLibrary|Conv_InterfaceToObject)) (select (or (== (% k 3) 0) (and (== (Utilities|Array|Length (Variables|Costume|GetPoolHairM)) 0) (== (% k 3) 1))) (Variables|GW|GetTopHatMesh) (GW|Call|/Script/Engine.KismetSystemLibrary|Conv_InterfaceToObject)))))
  (CallFunction|ApplySlot :Comp (Variables|Default|GetGunMesh) :M (select seeker (Variables|GW|GetRevolverMesh) (GW|Call|/Script/Engine.KismetSystemLibrary|Conv_InterfaceToObject)))
  ; body: matte fabric where clothes would be, skin on face/hands (and arms for women)
  (Variables|Costume|SetBodyMID (Rendering|Material|CreateDynamicMaterialInstance :self mesh :ElementIndex 0 :SourceMaterial (select female (Variables|Costume|GetBodyMatF) (Variables|Costume|GetBodyMatM))))
  (Rendering|Material|SetMaterial :self mesh :ElementIndex 1 :Material (Variables|Costume|GetBodyMID))
  (bind tc (Variables|GW|GetTorsoColors))
  (bind lcs (Variables|GW|GetLegColors))
  (bind sk (Variables|Costume|GetSkinTones))
  (bind palette (Utilities|Array|Get(acopy) tc (% k (Math|Integer|Max(Integer) (Utilities|Array|Length tc) 1))))
  (bind legpal (Utilities|Array|Get(acopy) lcs (% k (Math|Integer|Max(Integer) (Utilities|Array|Length lcs) 1))))
  ; men: sleeves + trousers take the coat colour; women: under a stole the torso is the gown top (skirt colour),
  ; under a bodice it is skin (neckline, bare back), so it never reads as a flat tinted patch above the cloth
  (bind skinC (Utilities|Array|Get(acopy) sk (% (+ (* k 5) 1) (Math|Integer|Max(Integer) (Utilities|Array|Length sk) 1))))
  (bind skirtC (CallFunction|FitColorOf :M skirtM :Fallback palette))
  (bind clothTop (select seeker (Variables|GW|GetSeekerTorso) (select female (select useStole skirtC skinC) (CallFunction|FitColorOf :M shellM :Fallback palette))))
  (bind clothLeg (select seeker (Variables|GW|GetSeekerLegs) (select female (Math|Color|LinearColor(Black)?) clothTop)))
  ({SETVEC} :self (Variables|Costume|GetBodyMID) :ParameterName "TorsoColor" :Value clothTop)
  ; women: legs in the skirt colour, so a stride poking through a rigid skirt reads as fabric; men: trouser palette
  ({SETVEC} :self (Variables|Costume|GetBodyMID) :ParameterName "LegColor" :Value (select seeker (Variables|GW|GetSeekerLegs) (select female skirtC legpal)))
  ({SETVEC} :self (Variables|Costume|GetBodyMID) :ParameterName "SkinColor" :Value skinC)
  ; opera gloves (material only) for one woman in three, ivory or black satin
  (GW|Call|/Script/Engine.MaterialInstanceDynamic|SetScalarParameterValue :self (Variables|Costume|GetBodyMID) :ParameterName "GloveOn" :Value (select (and female (== (% k 3) 1)) 1.0 0.0))
  ({SETVEC} :self (Variables|Costume|GetBodyMID) :ParameterName "GloveColor" :Value (select (== (% k 2) 0) (Utilities|Struct|MakeLinearColor 0.72 0.69 0.62 1.0) (Utilities|Struct|MakeLinearColor 0.015 0.015 0.017 1.0)))
  ; camera / control style
  ; nobody's body turns with the mouse (user, 2026-11-02: it gave the players away): everyone faces their movement
  ; like the NPCs; s37_view.py ApplyView (last line) turns a player toward the aim only while aiming down sights
  (Variables|Pawn|SetUseControllerRotationYaw false)
  (bind boom (Variables|Camera|GetCameraBoom))
  ; detective: boom pivot on the right shoulder so the body never covers the crosshair (third-person option)
  (Transformation|SetRelativeLocation :self boom :NewLocation (select seeker (Math|Vector|MakeVector 0.0 48.0 66.0) (Math|Vector|MakeVector 0.0 0.0 8.5)))
  (Class|SpringArmComponent|SetTargetArmLength :self boom :TargetArmLength (select seeker 230.0 330.0))
  (Class|SpringArmComponent|SetSocketOffset :self boom :SocketOffset (select seeker (Math|Vector|MakeVector 0.0 18.0 8.0) (Math|Vector|MakeVector 0.0 40.0 52.0)))
  (Class|CharacterMovementComponent|SetOrientRotationtoMovement :self (Variables|Character|GetCharacterMovement) :bOrientRotationToMovement true)
  ; first-person boom at the eyes on the server, aim-down-sights facing (s37_view.py)
  (CallFunction|ApplyView))
'''
# a None static mesh literal: select needs two object pins; an unconnected Conv_InterfaceToObject is awkward ->
# use a dedicated null variable instead
NULL = '(Variables|Costume|GetNoMesh)'
ensure_var(ch, 'NoMesh', obj_class=SM, category='Costume')
W['ApplyLook'] = W['ApplyLook'].replace('(GW|Call|/Script/Engine.KismetSystemLibrary|Conv_InterfaceToObject)', NULL)
W['ApplyLook'] = W['ApplyLook'].replace('''  (bind clothLeg (select seeker (Variables|GW|GetSeekerLegs) (select female (Math|Color|LinearColor(Black)?) clothTop)))
''', '')

# Generated characters (Tools/chars, s29_gen_chars.py): an outfit index or the detective mapped to a rigged generated
# character (GenChars[OutfitIndex] / GenDetective, on SK_Mannequin) replaces the mannequin + costume pieces entirely;
# the revolver still goes in hand_r. Outfits without one keep the costume path.
ensure_var(ch, 'GenChars', obj_class=unreal.SkeletalMesh, array=True, category='Costume')
ensure_var(ch, 'GenDetective', obj_class=unreal.SkeletalMesh, category='Costume')
ensure_fn(ch, 'PickGen', inputs=[('N', 'int')], outputs=[('M', unreal.SkeletalMesh)], pure=True)
W['PickGen'] = '''
(fn PickGen (N)
  (bind pool (Variables|Costume|GetGenChars))
  (if (and (>= N 0) (< N (Utilities|Array|Length pool)))
    (return (Utilities|Array|Get(acopy) pool N))
    (else
      (return))))
'''
_SET = '  (Components|SkeletalMesh|SetSkeletalMeshAsset'
_CAM = '  ; camera / control style'
_head, _rest = W['ApplyLook'].split(_SET, 1)
_costume, _tail = (_SET + _rest).split(_CAM, 1)
_slots = ''.join(f'    (CallFunction|ApplySlot :Comp (Variables|Default|Get{c}) :M {NULL})\n' for c in ('ShellMesh', 'SkirtMesh', 'HairMesh', 'MaskMesh', 'HatMesh'))
W['ApplyLook'] = (_head + f'''  (bind gen (select seeker (Variables|Costume|GetGenDetective) (CallFunction|PickGen :N oi)))
  (if ({ISVALID} :Object gen)
    (Components|SkeletalMesh|SetSkeletalMeshAsset :self mesh :NewMesh gen)
    ; clear the costume path's body material overrides (an unset Material pin = None = the asset's own material)
    (Rendering|Material|SetMaterial :self mesh :ElementIndex 0)
    (Rendering|Material|SetMaterial :self mesh :ElementIndex 1)
    (GW|Call|/Script/Engine.SkinnedMeshComponent|UnHideBoneByName :self mesh :BoneName "thigh_l")
    (GW|Call|/Script/Engine.SkinnedMeshComponent|UnHideBoneByName :self mesh :BoneName "thigh_r")
{_slots}    (CallFunction|ApplySlot :Comp (Variables|Default|GetGunMesh) :M (select seeker (Variables|GW|GetRevolverMesh) {NULL}))
    (else
''' + ''.join('    ' + l + '\n' if l.strip() else '\n' for l in _costume.rstrip('\n').split('\n')).rstrip('\n') + '))\n' + _CAM + _tail)
# dev menu (Tools/ui/u15_dev_menu.py): OutfitIndex 32 = the detective's look on a guest; camera and controls still
# follow the real role (IsSeeker)
_look, _camtail = W['ApplyLook'].split(_CAM, 1)
W['ApplyLook'] = (_look.replace('(bind seeker (Variables|GW|GetIsSeeker))', '(bind seeker (or (Variables|GW|GetIsSeeker) (== (Variables|GW|GetOutfitIndex) 32)))', 1)
                  + _CAM + '\n  (bind role (Variables|GW|GetIsSeeker))' + _camtail.replace('seeker', 'role'))
# event characters (bandit / kamikaze / robot, s32_events.py) keep their own look
W['ApplyLook'] = W['ApplyLook'].replace('(fn ApplyLook ()\n', '(fn ApplyLook ()\n  (if (and (!= (Variables|GW|GetKind) 0) (!= (Variables|GW|GetKind) 4))\n    (CallFunction|ApplySpecialLook)\n    (return))\n', 1)
compile_bp(ch, quiet=True)

only = set(UE_ARGS)
for name in ('Pick', 'PickGen', 'FitColorOf', 'ApplySlot', 'ApplyLook'):
    if only and name not in only:
        continue
    write(ch, name, W[name], compile_after=False)
    compile_bp(ch, quiet=True)
    print('wrote', name)
compile_bp(ch)
print(node_problems(ch))
save(ch)
