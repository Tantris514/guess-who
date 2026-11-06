"""Item 14, la Mascarade (the user, 2026-11-05): every living guest, players included, gets a new random look.
Server: GM.Mascarade, called by PC.GWUseItem (s40_pc.py). The look replicates through OutfitIndex; BP_GW_MascaradeCue plays the sting on every machine.
Order after a change:
  python ue_run.py s45_mascarade.py / s40_inventory.py ps ui gm pc / ui\\u15_dev_menu.py pc, data / ui\\u17_shop_ui.py
Icon: Tools/props/item_icons.py 14, then s42_feedback5.py icons.
"""
import sys, importlib
sys.path.insert(0, r'J:\Projets\Unreal_Projects\Guess Who\Tools\gameplay')
import gw_lib; importlib.reload(gw_lib)
from gw_lib import *
import voice_bank as VB

SHOP = '/Game/GW/Blueprints/Shop'
REP = unreal.BlueprintVariableReplication
CHAR = '/Game/GW/Blueprints/BP_GW_Character.BP_GW_Character_C'
CUE = f'{SHOP}/BP_GW_MascaradeCue.BP_GW_MascaradeCue_C'
GASP = VB.CAT['gasp']

# the count, replicated like the other consumables
psb = load_bp('BP_GW_PlayerState')
ensure_var(psb, 'Masks', 'int', rep=REP.REPLICATED, category='Shop')
print('ps', compile_bp(psb, quiet=True), save(psb))

# the sting: a replicated actor whose non-spatial audio starts by itself on every machine
cue = load_or_create_bp('BP_GW_MascaradeCue', unreal.Actor, folder=SHOP)
compile_bp(cue, quiet=True)
d = cdo(cue)
d.set_editor_property('replicates', True)
d.set_editor_property('always_relevant', True)
d.set_editor_property('replicate_movement', False)
d.set_editor_property('initial_life_span', 8.0)
au = ensure_component(cue, 'Sting', unreal.AudioComponent, 'DefaultSceneRoot')
au.set_editor_property('sound', unreal.load_asset('/Game/GW/Audio/STG_Reveal'))
au.set_editor_property('auto_activate', True)
print('cue', compile_bp(cue, quiet=True), save(cue))

gm = load_bp('BP_GW_GameMode')
chc = load_bp('BP_GW_Character').generated_class()
psc = psb.generated_class()
ensure_fn(gm, 'Mascarade', inputs=[('PS', psc), ('Ch', chc)])
local_note = lambda s: f'(CallFunction|ShopPay :PS PS :Amount 0 :Note {s})'
write(gm, 'Mascarade', f'''
(fn Mascarade (PS Ch)
  (if (<= (GW|Get|BP_GW_PlayerState|Masks :self PS) 0)
    {local_note('"Pas de masque : le barman en vend."')}
    (return))
  (GW|Set|BP_GW_PlayerState|Masks :self PS :Masks (- (GW|Get|BP_GW_PlayerState|Masks :self PS) 1))
  (for c (Actor|GetAllActorsOfClass :ActorClass "{CHAR}")
    (bind g (Utilities|Casting|CastToBP_GW_Character c)
      (:then
        (if (and (and (== (GW|Get|BP_GW_Character|Kind :self g) 0) (not (GW|Get|BP_GW_Character|IsDead :self g))) (not (GW|Get|BP_GW_Character|IsSeeker :self g)))
          (GW|Set|BP_GW_Character|OutfitIndex :self g :OutfitIndex (CallFunction|NextOutfit))))
      (:CastFailed)))
  (Game|SpawnActorfromClass :Class "{CUE}" :SpawnTransform (Math|Transform|MakeTransform) :CollisionHandlingOverride "AlwaysSpawn")
  (CallFunction|SayNearPlayers :Cat {GASP} :PerPlayer 3 :Delay 0.4 :Spread 1.2)
  {local_note('"Mascarade ! Tous les invités changent de visage."')}
  (Development|PrintString :InString "GW: mascarade" :bPrintToScreen false))
''')
print('gm', compile_bp(gm), save(gm))
print('problems', node_problems(gm))
