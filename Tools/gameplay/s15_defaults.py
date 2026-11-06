"""Class defaults (CDOs) and component templates for the gameplay classes."""
import sys, importlib
sys.path.insert(0, r'J:\Projets\Unreal_Projects\Guess Who\Tools\gameplay')
import gw_lib; importlib.reload(gw_lib)
from gw_lib import *

LC = unreal.LinearColor
ch = load_bp('BP_GW_Character')
gm = load_bp('BP_GW_GameMode')
gh = load_bp('BP_GW_Ghost')
mgm = load_bp('BP_GW_MenuGameMode')
npc = load_bp('BP_GW_NPCController')

# 1930s evening-wear tints (jacket/gown = torso, trousers/skirt + head = legs)
# formal palette (fallback jacket / bodice colour when no costume piece is approved for the slot)
TORSO = [(0.012, 0.012, 0.014), (0.012, 0.018, 0.06), (0.04, 0.04, 0.045), (0.12, 0.012, 0.025),
         (0.02, 0.02, 0.05), (0.012, 0.05, 0.03), (0.06, 0.035, 0.02), (0.08, 0.02, 0.07),
         (0.012, 0.012, 0.014), (0.02, 0.025, 0.08), (0.05, 0.012, 0.02), (0.025, 0.025, 0.03)]
# trousers: black, charcoal, midnight navy, very dark brown
LEGS = [(0.012, 0.012, 0.014), (0.03, 0.03, 0.034), (0.012, 0.016, 0.05), (0.035, 0.022, 0.014), (0.012, 0.012, 0.014)]
HATS = [True, True, False, True, True, False, True, True, True, False, True, True]

c = cdo(ch)
c.set_editor_property('WalkSpeed', 165.0)
c.set_editor_property('SprintSpeed', 470.0)
c.set_editor_property('FireCooldown', 1.0)
c.set_editor_property('Health', 100.0)
c.set_editor_property('TorsoColors', [LC(*t, 1.0) for t in TORSO])
c.set_editor_property('LegColors', [LC(*t, 1.0) for t in LEGS])
c.set_editor_property('HatFlags', HATS)
c.set_editor_property('SeekerTorso', LC(0.40, 0.29, 0.15, 1.0))
c.set_editor_property('SeekerLegs', LC(0.06, 0.04, 0.025, 1.0))
c.set_editor_property('BodyMale', unreal.load_asset('/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple'))
c.set_editor_property('BodyFemale', unreal.load_asset('/Game/Characters/Mannequins/Meshes/SKM_Quinn_Simple'))
for k, p in [('TorsoMatM', 'MI_GW_Torso'), ('LegsMatM', 'MI_GW_HeadLegs'), ('TorsoMatF', 'MI_GW_Torso_F'), ('LegsMatF', 'MI_GW_HeadLegs_F')]:
    c.set_editor_property(k, unreal.load_asset('/Game/GW/Characters/Materials/' + p))
c.set_editor_property('GunshotSound', unreal.load_asset('/Game/GW/Audio/S_GW_Gunshot'))
c.set_editor_property('ThudSound', unreal.load_asset('/Game/GW/Audio/S_GW_Thud'))
c.set_editor_property('ai_controller_class', npc.generated_class())
c.set_editor_property('jump_max_count', 0)  # NPCs never jump, so players must not either (a jump would unmask a hider)
cm = c.get_editor_property('character_movement')
cm.set_editor_property('max_walk_speed', 165.0)

comps = subobjects(ch)
lib = unreal.SubobjectDataBlueprintFunctionLibrary
for name in ('HatMesh', 'MaskMesh', 'GunMesh'):
    t = lib.get_object(comps[name][1])
    t.set_collision_profile_name('NoCollision')
    t.set_editor_property('generate_overlap_events', False)
    t.set_editor_property('can_character_step_up_on', unreal.CanBeCharacterBase.ECB_NO)
light = lib.get_object(comps['MuzzleLight'][1])
light.set_editor_property('intensity', 0.0)
light.set_editor_property('attenuation_radius', 600.0)
light.set_editor_property('light_color', unreal.Color(r=255, g=196, b=120, a=255))
light.set_editor_property('cast_shadows', False)
light.set_editor_property('relative_location', unreal.Vector(0, 30, 6))
compile_bp(ch, quiet=True)
save(ch)

# GameMode
g = cdo(gm)
g.set_editor_property('game_state_class', cls('BP_GW_GameState'))
g.set_editor_property('player_state_class', cls('BP_GW_PlayerState'))
g.set_editor_property('player_controller_class', cls('BP_GW_PlayerController'))
g.set_editor_property('default_pawn_class', cls('BP_GW_Character'))
g.set_editor_property('spectator_class', cls('BP_GW_Ghost'))
g.set_editor_property('pauseable', False)
for k, v in [('HideTime', 20.0), ('HuntTime', 240.0), ('EndTime', 8.0), ('LobbyCountdown', 8.0), ('NPCCount', 120),
             ('MinPlayers', 2), ('NPCRespawnDelay', 20.0), ('InnocentPenalty', 25.0), ('NumOutfits', 32)]:
    g.set_editor_property(k, v)
compile_bp(gm, quiet=True)
save(gm)

# Ghost spectator pawn: replicated to its owner only, no collision, our own input handling
h = cdo(gh)
h.set_editor_property('replicates', True)
h.set_editor_property('replicate_movement', False)
h.set_editor_property('only_relevant_to_owner', True)
h.set_editor_property('add_default_movement_bindings', False)
col = h.get_editor_property('collision_component')
col.set_collision_profile_name('NoCollision')
compile_bp(gh, quiet=True)
save(gh)

# PlayerController: no cheat manager at all (ServerExec EnableCheats would otherwise force one in Development builds)
pcbp = load_bp('BP_GW_PlayerController')
p = cdo(pcbp)
p.set_editor_property('cheat_class', None)
compile_bp(pcbp, quiet=True)
save(pcbp)
print('pc cheat class', p.get_editor_property('cheat_class'))

# Menu game mode
m = cdo(mgm)
m.set_editor_property('default_pawn_class', None)
m.set_editor_property('player_controller_class', cls('BP_GW_MenuPlayerController'))
compile_bp(mgm, quiet=True)
save(mgm)

# read back
c = cdo(load_bp('BP_GW_Character'))
print('jump max', c.get_editor_property('jump_max_count'), 'char walk', c.get_editor_property('WalkSpeed'), 'colors', len(c.get_editor_property('TorsoColors')),
      'ai', c.get_editor_property('ai_controller_class').get_name(), 'cm speed', c.get_editor_property('character_movement').get_editor_property('max_walk_speed'))
g = cdo(load_bp('BP_GW_GameMode'))
print('gm', g.get_editor_property('game_state_class').get_name(), g.get_editor_property('player_controller_class').get_name(),
      g.get_editor_property('HuntTime'), g.get_editor_property('NumOutfits'))
h = cdo(load_bp('BP_GW_Ghost'))
print('ghost', h.get_editor_property('replicates'), h.get_editor_property('only_relevant_to_owner'),
      h.get_editor_property('collision_component').get_collision_profile_name())
