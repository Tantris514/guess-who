"""Phase 1: variables, components and function signatures for every gameplay class (idempotent)."""
import sys, importlib
sys.path.insert(0, r'J:\Projets\Unreal_Projects\Guess Who\Tools\gameplay')
import gw_lib; importlib.reload(gw_lib)
from gw_lib import *

R, N = REP.REPLICATED, REP.REP_NOTIFY
V3 = unreal.Vector.static_struct()
LC = unreal.LinearColor.static_struct()
TR = unreal.Transform.static_struct()
V2 = unreal.Vector2D.static_struct()

ch = load_bp('BP_GW_Character')
gm = load_bp('BP_GW_GameMode')
gs = load_bp('BP_GW_GameState')
ps = load_bp('BP_GW_PlayerState')
pc = load_bp('BP_GW_PlayerController')
npc = load_bp('BP_GW_NPCController')
gh = load_bp('BP_GW_Ghost')
hud = unreal.load_asset('/Game/GW/UI/WBP_HUD')
menu = unreal.load_asset('/Game/GW/UI/WBP_MainMenu')
mgm = load_bp('BP_GW_MenuGameMode')
mpc = load_bp('BP_GW_MenuPlayerController')
CH = ch.generated_class()
PSC = ps.generated_class()
GSC = gs.generated_class()

# ---------------- PlayerState / GameState
for n, t in [('GWRole', 'int'), ('IsAlive', 'bool'), ('GWScore', 'int'), ('SeekCount', 'int'), ('Kills', 'int'), ('Mistakes', 'int')]:
    ensure_var(ps, n, t, R, category='GW')
for n, t in [('Phase', 'int'), ('PhaseEndTime', 'float'), ('HidersAlive', 'int'), ('SeekersAlive', 'int'), ('Winner', 'int'),
             ('RoundNumber', 'int'), ('Message', 'string'), ('LastEvent', 'string'), ('LastEventTime', 'float')]:
    ensure_var(gs, n, t, R, category='GW')
ensure_fn(gs, 'RemainingTime', outputs=[('Seconds', 'float')], pure=True)
for bp in (ps, gs):
    compile_bp(bp, quiet=True)

# ---------------- Character
for n, t, r in [('OutfitIndex', 'int', N), ('IsSeeker', 'bool', N), ('IsDead', 'bool', N), ('Health', 'float', R),
                ('ShotCounter', 'int', N), ('ShotTime', 'float', R), ('IsSprinting', 'bool', R), ('LastFireTime', 'float', None),
                ('WalkSpeed', 'float', None), ('SprintSpeed', 'float', None), ('FireCooldown', 'float', None)]:
    ensure_var(ch, n, t, r, category='GW')
ensure_var(ch, 'HitImpulse', struct=V3, rep=R, category='GW')
ensure_var(ch, 'ShotEnd', struct=V3, rep=R, category='GW')
ensure_var(ch, 'TorsoColors', struct=LC, array=True, category='GW')
ensure_var(ch, 'LegColors', struct=LC, array=True, category='GW')
ensure_var(ch, 'HatFlags', 'bool', array=True, category='GW')
ensure_var(ch, 'SeekerTorso', struct=LC, category='GW')
ensure_var(ch, 'SeekerLegs', struct=LC, category='GW')
for n in ['TopHatMesh', 'FedoraMesh', 'MaskStaticMesh', 'RevolverMesh']:
    ensure_var(ch, n, obj_class=unreal.StaticMesh, category='GW')
for n in ['BodyMale', 'BodyFemale']:
    ensure_var(ch, n, obj_class=unreal.SkeletalMesh, category='GW')
for n in ['HatMatGuest', 'HatMatSeeker', 'MaskMat', 'GunMat', 'TorsoMatM', 'LegsMatM', 'TorsoMatF', 'LegsMatF']:
    ensure_var(ch, n, obj_class=unreal.MaterialInterface, category='GW')
for n in ['HatRelTop', 'HatRelFedora', 'MaskRel', 'GunRel']:
    ensure_var(ch, n, struct=TR, category='GW')
for n in ['TorsoMID', 'LegsMID']:
    ensure_var(ch, n, obj_class=unreal.MaterialInstanceDynamic, category='GW')
for n in ['GunshotSound', 'ThudSound']:
    ensure_var(ch, n, obj_class=unreal.SoundBase, category='GW')
for n in ['HatMesh', 'MaskMesh', 'GunMesh']:
    ensure_component(ch, n, unreal.StaticMeshComponent, 'Mesh')
ensure_component(ch, 'MuzzleLight', unreal.PointLightComponent, 'GunMesh')
for n in ['ApplyLook', 'GoRagdoll', 'PlayShotFX', 'MuzzleOff', 'AttachAccessories']:
    ensure_fn(ch, n)
ensure_fn(ch, 'SetSprint', inputs=[('On', 'bool')])
ensure_fn(ch, 'SetFrozen', inputs=[('Frozen', 'bool')])
ensure_fn(ch, 'ServerFire', inputs=[('Start', V3), ('Dir', V3)])
ensure_fn(ch, 'Die', inputs=[('Impulse', V3)])
compile_bp(ch, quiet=True)

# ---------------- GameMode
for n, t in [('HideTime', 'float'), ('HuntTime', 'float'), ('EndTime', 'float'), ('LobbyCountdown', 'float'), ('NPCCount', 'int'),
             ('MinPlayers', 'int'), ('NPCRespawnDelay', 'float'), ('InnocentPenalty', 'float'), ('NumOutfits', 'int'),
             ('SeekerSpawnCursor', 'int'), ('HidersPresent', 'int'), ('SeekersPresent', 'int')]:
    ensure_var(gm, n, t, category='GW')
ensure_var(gm, 'NPCSpawnPoints', obj_class=unreal.Actor, array=True, category='GW')
ensure_var(gm, 'SeekerSpawnPoints', obj_class=unreal.Actor, array=True, category='GW')
ensure_var(gm, 'PendingNPCRespawns', 'float', array=True, category='GW')
ensure_fn(gm, 'GetGS', outputs=[('GS', GSC)], pure=True)
ensure_fn(gm, 'Now', outputs=[('T', 'float')], pure=True)
ensure_fn(gm, 'GetGWPlayers', outputs=[('Players', (PSC, 'array'))])
for n in ['RoundTick', 'StartRound', 'BeginHunt', 'ResetToLobby', 'ClearRoundActors', 'AssignRoles', 'SpawnNPC',
          'UpdateCounts', 'CheckWin', 'ProcessNPCRespawns', 'CachePoints', 'ApplyOptions', 'SpawnInitialNPCs']:
    ensure_fn(gm, n)
ensure_fn(gm, 'EndRound', inputs=[('W', 'int'), ('Msg', 'string')])
ensure_fn(gm, 'SpawnPlayerPawn', inputs=[('PC', unreal.PlayerController), ('Seeker', 'bool')], outputs=[('Pawn', CH)])
ensure_fn(gm, 'RandomSpawnTransform', outputs=[('T', TR)])
ensure_fn(gm, 'SeekerSpawnTransform', outputs=[('T', TR)])
ensure_fn(gm, 'MakeGhost', inputs=[('PC', unreal.Controller), ('Location', V3)])
ensure_fn(gm, 'CanShoot', inputs=[('Shooter', CH)], outputs=[('Ok', 'bool')])
ensure_fn(gm, 'OnCharacterShot', inputs=[('Shooter', CH), ('Victim', CH), ('Dir', V3)])
ensure_fn(gm, 'KillPlayer', inputs=[('Victim', CH), ('Impulse', V3)])
ensure_fn(gm, 'Announce', inputs=[('Text', 'string')])
ensure_fn(gm, 'UniqueName', inputs=[('PC', unreal.Controller), ('Wanted', 'string')], outputs=[('Name', 'string')])
ensure_fn(gm, 'NameTaken', inputs=[('PC', unreal.Controller), ('Name', 'string')], outputs=[('Taken', 'bool')], pure=True)
ensure_fn(gm, 'PSOf', inputs=[('P', unreal.Pawn)], outputs=[('PS', PSC)], pure=True)
ensure_fn(gm, 'NameOf', inputs=[('P', unreal.Pawn)], outputs=[('Name', 'string')], pure=True)
compile_bp(gm, quiet=True)

# ---------------- NPC controller
for n, t in [('NextMoveTime', 'float'), ('IsMoving', 'bool'), ('MoveStartTime', 'float')]:
    ensure_var(npc, n, t, category='GW')
ensure_var(npc, 'Points', obj_class=unreal.Actor, array=True, category='GW')
ensure_fn(npc, 'Think')
ensure_fn(npc, 'PickDestination', outputs=[('Dest', V3), ('Ok', 'bool')])
compile_bp(npc, quiet=True)

# ---------------- Ghost
ensure_fn(gh, 'GhostMove', inputs=[('Value', V2)])
ensure_fn(gh, 'GhostLook', inputs=[('Value', V2)])
compile_bp(gh, quiet=True)

# ---------------- HUD widget (owned by the UI agent since 23:00: only touched with the 'ui' argument)
if 'ui' in UE_ARGS:
    for n, t in [('LocalNotice', 'string'), ('LocalNoticeTime', 'float')]:
        ensure_var(hud, n, t, category='GW')
    ensure_fn(hud, 'Refresh', inputs=[('PC', unreal.PlayerController), ('ShowScores', 'bool')])
    ensure_fn(hud, 'FormatTime', inputs=[('Seconds', 'float')], outputs=[('Out', 'string')], pure=True)
    ensure_fn(hud, 'BuildScores', outputs=[('Out', 'string')])
    ensure_fn(hud, 'RefreshWith', inputs=[('GS', GSC), ('PS', PSC), ('PC', unreal.PlayerController), ('ShowScores', 'bool')])
    ensure_fn(hud, 'HealthOf', inputs=[('PC', unreal.PlayerController)], outputs=[('HP', 'float')], pure=True)
    ensure_fn(hud, 'DebugDump', outputs=[('Out', 'string')])
    ensure_fn(hud, 'ShowW', inputs=[('W', unreal.Widget), ('Show', 'bool')])
    compile_bp(hud, quiet=True)

# ---------------- PlayerController
ensure_var(pc, 'HUDWidget', obj_class=hud.generated_class(), category='GW')
for n, t in [('ShowScores', 'bool'), ('AutoTestCount', 'int'), ('LastPhase', 'int'), ('LastMenuPress', 'float'), ('CheatStep', 'int')]:
    ensure_var(pc, n, t, category='GW')
ensure_fn(pc, 'GWFire', inputs=[('Pitch', 'float'), ('Yaw', 'float')], exec_fn=True)
ensure_fn(pc, 'GWSprint', inputs=[('On', 'int')], exec_fn=True)
ensure_fn(pc, 'GWDebugShoot', inputs=[('Mode', 'int')], exec_fn=True)
ensure_fn(pc, 'GWStatus', exec_fn=True)
ensure_fn(pc, 'GWSetName', inputs=[('NewName', 'string')], exec_fn=True)
ensure_fn(pc, 'SendName')
ensure_fn(pc, 'MenuPressed')
ensure_fn(pc, 'CheatTestTick')
ensure_fn(pc, 'ApplySeekerDoor', inputs=[('Closed', 'bool')])
for n in ['RequestFire', 'RefreshHUD', 'AutoTestTick', 'SetupLocal', 'ScoresOn', 'ScoresOff', 'SprintOn', 'SprintOff']:
    ensure_fn(pc, n)
ensure_fn(pc, 'RequestSprint', inputs=[('On', 'bool')])
compile_bp(pc, quiet=True)

# ---------------- Menu (UI agent)
if 'ui' in UE_ARGS:
    ensure_fn(menu, 'OnHostClicked')
    ensure_fn(menu, 'OnJoinClicked')
    ensure_fn(menu, 'OnQuitClicked')
    ensure_fn(menu, 'StoreName')
    ensure_fn(menu, 'GetCleanName', outputs=[('Name', 'string')])
    compile_bp(menu, quiet=True)

for bp in (ch, gm, gs, ps, pc, npc, gh, mgm, mpc) + ((hud, menu) if 'ui' in UE_ARGS else ()):
    print(bp.get_name(), 'vars', len(BT.list_variables(bp)), 'graphs', len(graph_names(bp)))
    save(bp)
print('components', list(subobjects(ch).keys()))
