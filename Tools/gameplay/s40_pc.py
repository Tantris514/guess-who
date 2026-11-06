# s40_inventory.py, part "pc": exec'd by s40 (its names are in scope). Player controller: input, inventory, hold E, prompts, test.
if want('pc'):
    pc = load_bp('BP_GW_PlayerController')
    INP = '/Game/GW/Input'
    IMC = unreal.load_asset(f'{INP}/IMC_GW')
    # ---- keys: only these from now on (every per-item key is gone)
    KEYS = {'IA_GW_Slot1': ('One', 'InvPick1'), 'IA_GW_Slot2': ('Two', 'InvPick2'), 'IA_GW_Slot3': ('Three', 'InvPick3'), 'IA_GW_Slot4': ('Four', 'InvPick4'),
            'IA_GW_SlotNext': ('MouseScrollDown', 'InvNext'), 'IA_GW_SlotPrev': ('MouseScrollUp', 'InvPrev'), 'IA_GW_Drop': ('Q', 'InvDrop'), 'IA_GW_View': ('C', 'ViewToggle')}
    for ia_name, (key, _) in KEYS.items():
        pth = f'{INP}/{ia_name}'
        ia = unreal.load_asset(pth) if EAL.does_asset_exist(pth) else AT.create_asset(ia_name, INP, unreal.InputAction, unreal.InputAction_Factory())
        EAL.save_loaded_asset(ia, False)
        if not any(m.get_editor_property('action') == ia for m in IMC.get_editor_property('default_key_mappings').get_editor_property('mappings')):
            k = unreal.Key()
            k.set_editor_property('key_name', key)
            IMC.map_key(ia, k)
    ja = unreal.load_asset('/Game/Input/Actions/IA_Jump')
    if not any(m.get_editor_property('action') == ja for m in IMC.get_editor_property('default_key_mappings').get_editor_property('mappings')):
        k = unreal.Key()
        k.set_editor_property('key_name', 'SpaceBar')
        IMC.map_key(ja, k)
    for old in ('IA_GW_Smoke', 'IA_GW_Gas', 'IA_GW_Trap', 'IA_GW_Lamp', 'IA_GW_Bomb', 'IA_GW_Cracker', 'IA_Swap'):
        IMC.unmap_all_keys_from_action(unreal.load_asset(f'{INP}/{old}'))
    EAL.save_loaded_asset(IMC, False)

    for v, t in (('HK', 'int'), ('HL', 'string'), ('HD', 'float'), ('HoldOn', 'bool'), ('HoldT0', 'float'), ('HoldKind', 'int'), ('HoldSrvAt', 'float'),
                 ('HoldFrac', 'float'), ('InvT0', 'float'), ('InvStep', 'int'), ('NextBoostJump', 'float'), ('SeenCode', 'int'), ('SeenReads', 'int'),
                 ('DropBest', 'float'), ('GhostOn', 'bool')):
        ensure_var(pc, v, t, category='Inv')
    ensure_var(pc, 'HA', obj_class=unreal.Actor, category='Inv')
    ensure_var(pc, 'NoActor', obj_class=unreal.Actor, category='Inv')
    ensure_var(pc, 'HSpot', struct=V3, category='Inv')
    ensure_var(pc, 'InvWid', obj_class=unreal.load_asset('/Game/GW/UI/WBP_Inventory').generated_class(), category='Inv')
    ensure_var(pc, 'PostReads', 'int', rep=REP.REPLICATED, category='GW')
    DROPC = cp('BP_GW_ItemDrop')
    dropb, ghostb, kpb = load_bp('BP_GW_ItemDrop', SHOP), load_bp('BP_GW_TrapGhost', SHOP), load_bp('BP_GW_KeyPrompt')
    GHOST = cp('BP_GW_TrapGhost')
    KP = '"/Game/GW/Blueprints/BP_GW_KeyPrompt.BP_GW_KeyPrompt_C"'
    for v_, c_ in (('DropA', dropb), ('NoDrop', dropb), ('TrapGhost', ghostb), ('DropPrompt', kpb), ('GhostPrompt', kpb)):
        ensure_var(pc, v_, obj_class=c_.generated_class(), category='Inv')
    PCF = {'InvClientTick': ([], []), 'InvChTick': ([], []), 'InvPick': ([('I', 'int')], []), 'InvNext': ([], []), 'InvPrev': ([], []), 'InvDrop': ([], []), 'ViewToggle': ([], []),
           'RequestJump': ([], []), 'NearHold': ([('Ch', chc), ('Extra', 'float')], []), 'TryHold': ([], [('Handled', 'bool')]), 'HoldTick': ([], []),
           'HoldCancel': ([], []), 'HeldNow': ([], [('Id', 'int')]), 'GunsVisible': ([], []), 'InvTestTick': ([], []), 'InvTestStep': ([('St', 'int')], []),
           'DropNear': ([], [('A', dropb.generated_class())]), 'TryDrop': ([], [('Handled', 'bool')]), 'DropClientTick': ([], []), 'TrapGhostTick': ([], []), 'GhostShow': ([('On', 'bool')], []),
           'PostClose': ([], [('Handled', 'bool')]), 'PostFar': ([], [('Far', 'bool')])}
    for i in range(1, 5):
        PCF[f'InvPick{i}'] = ([], [])
    for f, (ins, outs) in PCF.items():
        ensure_fn(pc, f, inputs=ins, outputs=outs)
    # the seats, in the controller's defaults (a client has no game mode)
    for v_, t_ in (('SitBestD', 'float'), ('SitBestI', 'int'), ('SitPick', 'int'), ('SitOn', 'bool'), ('SitAt', 'float'), ('SitSent', 'float')):
        ensure_var(pc, v_, t_, category='Inv')
    ensure_var(pc, 'SitI', 'int', rep=REP.REPLICATED, category='Inv')
    ensure_var(pc, 'SitBack', struct=V3, category='Inv')
    ensure_var(pc, 'SitCh', obj_class=chc, category='Inv')
    ensure_var(pc, 'NoSitCh', obj_class=chc, category='Inv')
    ensure_var(pc, 'SeatLocs', struct=V3, array=True, category='Inv')
    ensure_var(pc, 'SeatYaws', 'float', array=True, category='Inv')
    ensure_fn(pc, 'SeatIdxNear', inputs=[('R', 'float')], outputs=[('I', 'int')])
    ensure_fn(pc, 'TrySit', outputs=[('Handled', 'bool')])
    ensure_fn(pc, 'SitStand')
    ensure_fn(pc, 'SitClientTick')
    ensure_fn(pc, 'GWSit', exec_fn=True)
    compile_bp(pc, quiet=True)
    _gd = cdo(gm)
    cdo(pc).set_editor_property('SitI', -1)
    cdo(pc).set_editor_property('SeatLocs', list(_gd.get_editor_property('SitLocs')))
    cdo(pc).set_editor_property('SeatYaws', list(_gd.get_editor_property('SitYaws')))
    print('seats for the players', len(_gd.get_editor_property('SitLocs')))
    EXEC = {'GWInvSel': [('I', 'int')], 'GWInvDrop': [], 'GWTakeDrop': [], 'GWHoldStart': [], 'GWHoldDone': [('Kind', 'int')], 'GWJumpBoost': [], 'GWBlade': [('Pitch', 'float'), ('Yaw', 'float')],
            'GWDevHurtSeeker': [], 'GWDevKillRival': [], 'GWDevInvState': [], 'GWDevChand': [], 'GWDevKamikaze': [], 'GWDevKillNear': [], 'GWDevTrapHere': [], 'GWDevGiveItem': [('Id', 'int')], 'GWDevInnocent': [], 'GWDevGoBox': [], 'GWDevGoProp': [], 'GWDevTrapTest': [('Mode', 'int')], 'GWDevRobotTurret': [], 'GWDevKnight': [], 'GWDevChandSee': []}
    for f, ins in EXEC.items():
        ensure_fn(pc, f, inputs=ins, exec_fn=True)
    compile_bp(pc, quiet=True)
    C = {}
    for i in range(1, 5):
        C[f'InvPick{i}'] = f'(fn InvPick{i} () (CallFunction|InvPick :I {i - 1}))'
    C['InvPick'] = '''
(fn InvPick (I)
  (Audio|PlaySound2D :Sound "/Game/GW/Audio/S_UI_Click.S_UI_Click" :VolumeMultiplier 0.35 :PitchMultiplier 1.2)
  (CallFunction|ShopServer :Cmd (cat "GWInvSel " I)))
'''
    for f, d in (('InvNext', 1), ('InvPrev', 3)):
        C[f] = f'''
(fn {f} ()
  (bind ps {PSC}
    (:then (CallFunction|InvPick :I (% (+ {Sp('InvSel')} {d}) 4)))
    (:CastFailed)))
'''
    C['InvDrop'] = '(fn InvDrop () (CallFunction|ShopServer :Cmd "GWInvDrop"))'
    C['ViewToggle'] = '''
(fn ViewToggle ()
  (Audio|PlaySound2D :Sound "/Game/GW/Audio/S_UI_Click.S_UI_Click" :VolumeMultiplier 0.3)
  (CallFunction|SetViewMode :FP (not (Variables|GW|GetWantFP))))
'''
    C['GWInvSel'] = f'''
(fn GWInvSel (I)
  (bind ps {PSC}
    (:then
      {SpS('InvSel', '(Math|Integer|Min(Integer) 3 (Math|Integer|Max(Integer) 0 I))')}
      (bind gm {GMC}
        (:then (GW|Call|BP_GW_GameMode|InvSync :self gm :PS ps))
        (:CastFailed)))
    (:CastFailed)))
'''
    C['GWInvDrop'] = f'''
(fn GWInvDrop ()
  (bind ps {PSC}
    (:then
      (bind id (GW|Call|BP_GW_PlayerState|SlotGet :self ps :I {Sp('InvSel')}))
      (if (or (<= id 0) (== id 13))
        (return))
      (bind gm {GMC}
        (:then
          (bind ch {MYCH}
            (:then (GW|Call|BP_GW_GameMode|DropItem :self gm :PS ps :Ch ch :Id id))
            (:CastFailed)))
        (:CastFailed)))
    (:CastFailed)))
'''
    # ---- dropped items: E takes the nearest one back, a key prompt shows it, every player sees it (BP_GW_ItemDrop is replicated)
    C['DropNear'] = f'''
(fn DropNear ()
  (Variables|Inv|SetDropA (Variables|Inv|GetNoDrop))
  (bind p (Pawn|GetControlledPawn :self self))
  (if (not ({ISVALID} :Object p))
    (return (Variables|Inv|GetDropA)))
  (Variables|Inv|SetDropBest 170.0)
  (bind here (Transformation|GetActorLocation :self p))
  (for d (Actor|GetAllActorsOfClass :ActorClass "{DROPC}")
    (bind dl (Transformation|GetActorLocation :self d))
    (bind dd (Math|Vector|Distance2D(Vector) dl here))
    (if (and (< dd (Variables|Inv|GetDropBest)) (< (Math|Float|Absolute(Float) (- (.z dl) (.z here))) 190.0))
      (Variables|Inv|SetDropBest dd)
      (Variables|Inv|SetDropA d)))
  (return (Variables|Inv|GetDropA)))
'''
    C['TryDrop'] = f'''
(fn TryDrop ()
  (bind ch {MYCH}
    (:then
      (if (GW|Get|BP_GW_Character|IsDead :self ch)
        (return false))
      (if (not ({ISVALID} :Object (CallFunction|DropNear)))
        (return false))
      (CallFunction|ShopServer :Cmd "GWTakeDrop")
      (return true))
    (:CastFailed (return false))))
'''
    C['GWTakeDrop'] = f'''
(fn GWTakeDrop ()
  (bind ps {PSC}
    (:then
      (bind ch {MYCH}
        (:then
          (if (GW|Get|BP_GW_Character|IsDead :self ch)
            (return))
          (bind d (CallFunction|DropNear))
          (if (not ({ISVALID} :Object d))
            (return))
          (bind gm {GMC}
            (:then (GW|Call|BP_GW_GameMode|TakeDrop :self gm :PS ps :Ch ch :D d))
            (:CastFailed)))
        (:CastFailed)))
    (:CastFailed)))
'''
    dnames = sel('(GW|Get|' + DROPC + '|ItemId :self (Variables|Inv|GetDropA))', {k: f'"{v}"' for k, v in NAMES.items()}, '"?"')
    C['DropClientTick'] = f'''
(fn DropClientTick ()
  (bind d (CallFunction|DropNear))
  (bind kp (Variables|Inv|GetDropPrompt))
  (if ({ISVALID} :Object d)
    (if (not ({ISVALID} :Object kp))
      (Variables|Inv|SetDropPrompt (Game|SpawnActorfromClass :Class {KP} :SpawnTransform (Math|Transform|MakeTransform :Location (Transformation|GetActorLocation :self d)) :CollisionHandlingOverride "AlwaysSpawn")))
    (GW|Call|BP_GW_KeyPrompt|SetPrompt :self (Variables|Inv|GetDropPrompt) :Key "E" :Label (cat "Ramasser : " {dnames}))
    (Transformation|SetActorLocation :self (Variables|Inv|GetDropPrompt) :NewLocation (+ (Transformation|GetActorLocation :self d) {mv(0, 0, 45)}) :bSweep false :bTeleport true)
    (GW|Call|BP_GW_KeyPrompt|ShowPrompt :self (Variables|Inv|GetDropPrompt) :On true)
    (return))
  (if ({ISVALID} :Object kp)
    (GW|Call|BP_GW_KeyPrompt|ShowPrompt :self kp :On false)))
'''
    # ---- the trap in hand, near a door: its ghost on the lintel and the key prompt. Local actors of this client only: nobody else sees them
    C['GhostShow'] = f'''
(fn GhostShow (On)
  (if (!= On (Variables|Inv|GetGhostOn))
    (Variables|Inv|SetGhostOn On)
    {LOG('(cat "GW ghost: " On)')})
  (if ({ISVALID} :Object (Variables|Inv|GetTrapGhost))
    (Rendering|SetActorHiddenInGame :self (Variables|Inv|GetTrapGhost) :bNewHidden (not On))))
  ; the key prompt is PromptTick's own (s34: "Poser le piège dans la porte")
'''
    C['TrapGhostTick'] = f'''
(fn TrapGhostTick ()
  (bind ch {MYCH}
    (:then
      (if (or (GW|Get|BP_GW_Character|IsDead :self ch) (!= (GW|Get|BP_GW_Character|HeldItem :self ch) 5))
        (CallFunction|GhostShow :On false)
        (return))
      (bind (top ax hw ok) (CallFunction|FindDoor :Loc (Transformation|GetActorLocation :self ch)))
      (if (not ok)
        (CallFunction|GhostShow :On false)
        (return))
      (for t (Actor|GetAllActorsOfClass :ActorClass "{TRAP}")
        (if (< (Math|Vector|Distance(Vector) (Transformation|GetActorLocation :self t) top) 60.0)
          (CallFunction|GhostShow :On false)
          (return)))
      (if (not ({ISVALID} :Object (Variables|Inv|GetTrapGhost)))
        (Variables|Inv|SetTrapGhost (Game|SpawnActorfromClass :Class "{GHOST}" :SpawnTransform (Math|Transform|MakeTransform :Location top) :CollisionHandlingOverride "AlwaysSpawn"))
        (Rendering|SetActorHiddenInGame :self (Variables|Inv|GetTrapGhost) :bNewHidden true))
      (bind g (Variables|Inv|GetTrapGhost))
      (Transformation|SetActorLocationAndRotation :self g :NewLocation top :NewRotation (Math|Rotator|MakeRotator :Yaw (select ax 90.0 0.0)) :bSweep false :bTeleport true)
      ; a line along the whole opening: the trigger of a trap on this door
      (Transformation|SetRelativeScale3D :self (GW|Get|{GHOST}|Span :self g) :NewScale3D (Math|Vector|MakeVector (/ hw 50.0) 0.09 0.09))
      (CallFunction|GhostShow :On true))
    (:CastFailed (CallFunction|GhostShow :On false))))
'''
    C['HeldNow'] = f'''
(fn HeldNow ()
  (bind ch {MYCH}
    (:then (return (GW|Get|BP_GW_Character|HeldItem :self ch)))
    (:CastFailed (return 0))))
'''
    # ---- left click: what the selected item does
    use_ids = '\n'.join(f'  (if (== id {i})\n    (CallFunction|RequestUse :Id {i})\n    (return))' for i in (2, 4, 5, 6, 9))
    C['RequestFire'] = f'''
(fn RequestFire ()
  (bind id (CallFunction|HeldNow))
  (bind rot (Pawn|GetControlRotation :self self))
  (if (or (== id 1) (== id 13))
    (if (Networking|HasAuthority)
      (CallFunction|GWFire :Pitch (.pitch rot) :Yaw (.yaw rot))
      (else
        (Development|ExecuteConsoleCommand :Command (cat "ServerExec GWFire " (.pitch rot) " " (.yaw rot)) :SpecificPlayer self)))
    (return))
  (if (or (== id 11) (== id 12))
    (bind ch {MYCH}
      (:then (CallFunction|GuestAttack :Ch ch))
      (:CastFailed)))
  (if (== id 8)
    (CallFunction|RequestSwap)
    (return))
  (if (== id 3)
    (CallFunction|ToggleLamp)
    (return))
  (if (== id 10)
    (CallFunction|ShopServer :Cmd (cat "GWBlade " (.pitch rot) " " (.yaw rot)))
    (return))
{use_ids})
'''
    C['GWFire'] = '''
(fn GWFire (Pitch Yaw)
  (bind ch (Utilities|Casting|CastToBP_GW_Character (Pawn|GetControlledPawn :self self))
    (:then
      (bind cam (Transformation|GetWorldLocation :self (GW|Get|BP_GW_Character|FollowCamera :self ch)))
      (bind srvDir (Math|Vector|GetForwardVector (Pawn|GetControlRotation :self self)))
      (bind cliDir (Math|Vector|GetForwardVector (Math|Rotator|MakeRotator :Pitch Pitch :Yaw Yaw)))
      (bind useCli (>= (Math|Vector|DotProduct srvDir cliDir) 0.985))
      (bind dir (select useCli cliDir srvDir))
      (if (not useCli)
        (Development|PrintString :InString "GW: fire aim too far from server view, using server rotation" :bPrintToScreen false))
      (bind t0 (Math|Float|Max(Float) (Math|Vector|DotProduct (- (Transformation|GetActorLocation :self ch) cam) dir) 0.0))
      (if (GW|Get|BP_GW_Character|IsSeeker :self ch)
        (if (!= (GW|Get|BP_GW_Character|HeldItem :self ch) 13)
          (return))
        (bind before (GW|Get|BP_GW_Character|ShotCounter :self ch))
        (GW|Call|BP_GW_Character|ServerFire :self ch :Start (+ cam (* dir t0)) :Dir dir)
        ; a detective's bullet brings a chandelier down too (no pay for him)
        (if (!= before (GW|Get|BP_GW_Character|ShotCounter :self ch))
          (bind gm (Utilities|Casting|CastToBP_GW_GameMode (Game|GetGameMode))
            (:then (GW|Call|BP_GW_GameMode|ChandShot :self gm :Shooter ch :Start (+ cam (* dir t0)) :Dir dir :End (GW|Get|BP_GW_Character|ShotEnd :self ch)))
            (:CastFailed)))
        (else
          (CallFunction|GuestFire :Ch ch :Start (+ cam (* dir t0)) :Dir dir))))
    (:CastFailed)))
'''
    C['GuestFire'] = f'''
(fn GuestFire (Ch Start Dir)
  (if (GW|Get|BP_GW_Character|IsDead :self Ch)
    (return))
  (bind gm {GMC}
    (:then (GW|Call|BP_GW_GameMode|GuestShoot :self gm :Shooter Ch :Start Start :Dir Dir))
    (:CastFailed)))
'''
    C['GWGuestAttack'] = f'''
(fn GWGuestAttack (Pitch Yaw)
  (bind ch {MYCH}
    (:then
      (bind ps {PSC}
        (:then
          (bind gm {GMC}
            (:then
              (bind now (GW|Call|BP_GW_GameMode|Now :self gm))
              (if (not (CallFunction|GuestOK :Ch ch :NeedHunt true))
                {LOG('"GW: attack refused (not a living guest in the hunt)"')}
                (return))
              (if (< now (Variables|GW|GetNextAttackAt))
                (return))
              (bind dir (CallFunction|AimDir :Pitch Pitch :Yaw Yaw))
              (bind held (GW|Get|BP_GW_Character|HeldItem :self ch))
              (if (and (== held 12) {Sp('HasSword')})
                (Variables|GW|SetNextAttackAt (+ now 0.7))
                (GW|Call|BP_GW_GameMode|Slash :self gm :Attacker ch :Dir dir)
                (return))
              (if (and (== held 11) (> {Sp('Balls')} 0))
                (Variables|GW|SetNextAttackAt (+ now 0.5))
                {SpA('Balls', -1)}
                (GW|Call|BP_GW_GameMode|ThrowBall :self gm :Thrower ch :Dir dir)
                (return))
              {LOG('(cat "GW: attack: holding " held)')})
            (:CastFailed)))
        (:CastFailed)))
    (:CastFailed)))
'''
    C['GWBlade'] = f'''
(fn GWBlade (Pitch Yaw)
  (bind ch {MYCH}
    (:then
      (bind ps {PSC}
        (:then
          (bind gm {GMC}
            (:then
              (if (or (!= (GW|Get|BP_GW_Character|HeldItem :self ch) 10) (not (CallFunction|GuestOK :Ch ch :NeedHunt true)))
                (return))
              (GW|Call|BP_GW_GameMode|BladeStrike :self gm :PS ps :Who ch :Dir (CallFunction|AimDir :Pitch Pitch :Yaw Yaw)))
            (:CastFailed)))
        (:CastFailed)))
    (:CastFailed)))
'''
    # ---- items, for everybody now
    C['CanShop'] = f'''
(fn CanShop ()
  ; guests and detectives alike (s40); not ghosts, not the dead, not outside a role
  (bind ps {PSC}
    (:then
      (bind ch {MYCH}
        (:then (return (and (> {Sp('GWRole')} 0) (not (GW|Get|BP_GW_Character|IsDead :self ch)))))
        (:CastFailed (return false))))
    (:CastFailed (return false))))
'''
    C['RequestUse'] = f'''
(fn RequestUse (Id)
  (bind ps {PSC}
    (:then
      (if (<= (GW|Call|BP_GW_PlayerState|CountOf :self ps :Id Id) 0)
        (return))
      (CallFunction|ShopServer :Cmd (cat "GWUseItem " Id " " (.yaw (Pawn|GetControlRotation :self self)))))
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
              (if (GW|Get|BP_GW_Character|IsDead :self ch)
                (return))
              (if (== Id 14)
                (GW|Call|BP_GW_GameMode|Mascarade :self gm :PS ps :Ch ch)
                (return))
              (GW|Call|BP_GW_GameMode|UseItem :self gm :PS ps :Ch ch :Id Id :Yaw Yaw))
            (:CastFailed)))
        (:CastFailed)))
    (:CastFailed)))
'''
    C['ToggleLamp'] = f'''
(fn ToggleLamp ()
  (bind ps {PSC}
    (:then
      (if (not {Sp('HasLamp')})
        (return))
      (Variables|Shop|SetLampOn (not (Variables|Shop|GetLampOn)))
      (Audio|PlaySound2D :Sound "/Game/GW/Audio/S_UI_Click.S_UI_Click" :VolumeMultiplier 0.5)
      {LOG('(cat "GW: lamp " (Variables|Shop|GetLampOn))')})
    (:CastFailed)))
'''
    C['LampTick'] = f'''
(fn LampTick ()
  ; the bought lamp (BP_GW_HandLamp, local) shines while selected, unless the blackout flashlight (s32) already does
  (bind want (and (and (and (Variables|Shop|GetLampOn) (not (Variables|GW|GetDarkOn))) (CallFunction|CanShop)) (== (CallFunction|HeldNow) 3)))
  (if want
    (if (not ({ISVALID} :Object (Variables|Shop|GetLampActor)))
      (Variables|Shop|SetLampActor (Game|SpawnActorfromClass :Class "{LAMPC}" :SpawnTransform (Math|Transform|MakeTransform) :CollisionHandlingOverride "AlwaysSpawn")))
    (Rendering|SetActorHiddenInGame :self (Variables|Shop|GetLampActor) :bNewHidden false)
    (return))
  (if ({ISVALID} :Object (Variables|Shop|GetLampActor))
    (Rendering|SetActorHiddenInGame :self (Variables|Shop|GetLampActor) :bNewHidden true)))
'''
    gives_dev = '\n'.join(f'''      (if (or (== Id {i}) (== Id 0))
        (GW|Call|BP_GW_GameMode|InvGive :self gm :PS ps :Id {i}))''' for i in (1, 2, 3, 4, 5, 6, 7, 8, 9, 10))
    C['GWDevGive'] = f'''
(fn GWDevGive (Id)
  (if (not (CallFunction|DevOK))
    {LOG('"GW: dev shop command refused (server not started with -GWDev)"')}
    (return))
  (bind ps {PSC}
    (:then
      (bind gm {GMC}
        (:then
{gives_dev}
          {LOG('(cat "GW: dev give " Id)')})
        (:CastFailed)))
    (:CastFailed)))
'''
    C['GWDevGiveItem'] = f'''
(fn GWDevGiveItem (Id)
  (if (not (CallFunction|DevOK))
    (return))
  (bind ps {PSC}
    (:then
      (bind gm {GMC}
        (:then (GW|Call|BP_GW_GameMode|InvGive :self gm :PS ps :Id Id))
        (:CastFailed)))
    (:CastFailed)))
'''
    # ---- E: bodies, props, box, kamikaze's bomb
    C['NearHold'] = f'''
(fn NearHold (Ch Extra)
  ; what E (held or not) reaches here: 1 a body, 2 a small prop, 3 the box (closed), 4 the box's prize, 5 the kamikaze's bomb
  (Variables|Inv|SetHK 0)
  (Variables|Inv|SetHA (Variables|Inv|GetNoActor))
  (Variables|Inv|SetHD (+ 170.0 Extra))
  (if (not (CallFunction|PlayerOK :Ch Ch))
    (return))
  (bind ps {PSC}
    (:then
      (bind s {GSC}
        (:then
          (bind phase (GW|Get|BP_GW_GameState|Phase :self s))
          (if (and (!= phase 1) (!= phase 2))
            (return))
          (bind here (Transformation|GetActorLocation :self Ch))
          (bind guest (== {Sp('GWRole')} 1))
          (for c (Actor|GetAllActorsOfClass :ActorClass {CHAR})
            (if (and (GW|Get|BP_GW_Character|IsDead :self c) (not (GW|Get|BP_GW_Character|Looted :self c)))
              (bind ml (Transformation|GetWorldLocation :self (GW|Get|/Script/Engine.Character|Mesh :self c)))
              (bind d (Math|Vector|Distance2D(Vector) ml here))
              (bind dz (- (.z ml) (.z here)))
              (if (and (< d (Variables|Inv|GetHD)) (< (* dz dz) 40000.0))
                (Variables|Inv|SetHD d)
                (Variables|Inv|SetHK 1)
                (Variables|Inv|SetHA c)
                (Variables|Inv|SetHSpot (+ ml {mv(0, 0, 40)}))
                (Variables|Inv|SetHL "Maintenir : fouiller le corps"))))
          (if guest
            (for p (Actor|GetAllActorsOfClass :ActorClass "{STEAL}")
              (if (not (GW|Get|{STEAL}|Stolen :self p))
                (bind pl (Transformation|GetActorLocation :self p))
                (bind d (Math|Vector|Distance2D(Vector) pl here))
                (bind dz (- (.z pl) (.z here)))
                (if (and (< d (Variables|Inv|GetHD)) (< (* dz dz) 32400.0))
                  (Variables|Inv|SetHD d)
                  (Variables|Inv|SetHK 2)
                  (Variables|Inv|SetHA p)
                  (Variables|Inv|SetHSpot (+ pl {mv(0, 0, 70)}))
                  (Variables|Inv|SetHL (cat "Maintenir : voler " (GW|Get|{STEAL}|Label :self p) " (+" (GW|Get|{STEAL}|Value :self p) " $)"))))))
          (for b (Actor|GetAllActorsOfClass :ActorClass "{BOX}")
            (bind bl (Transformation|GetActorLocation :self b))
            (bind st (GW|Get|{BOX}|State :self b))
            (bind d (Math|Vector|Distance2D(Vector) bl here))
            (bind dz (- (.z bl) (.z here)))
            (if (and (< d (+ 200.0 Extra)) (< (* dz dz) 40000.0))
              (if (== st 0)
                (Variables|Inv|SetHD d)
                (Variables|Inv|SetHK 3)
                (Variables|Inv|SetHA b)
                (Variables|Inv|SetHSpot (+ bl {mv(0, 0, 118)}))
                (Variables|Inv|SetHL "Boîte mystère ({BOX_PRICE} $)"))
              (if (and (== st 2) (== (GW|Get|{BOX}|Winner :self b) ps))
                (Variables|Inv|SetHD d)
                (Variables|Inv|SetHK 4)
                (Variables|Inv|SetHA b)
                (Variables|Inv|SetHSpot (+ bl {mv(0, 0, 118)}))
                (Variables|Inv|SetHL "Prendre l'objet de la boîte"))))
          (for q (Actor|GetAllActorsOfClass :ActorClass "{DROP}")
            (bind ql (Transformation|GetActorLocation :self q))
            (bind d (Math|Vector|Distance2D(Vector) ql here))
            (bind dz (- (.z ql) (.z here)))
            ; before his body, which lies right there
            (if (and (< d (+ 170.0 Extra)) (< (* dz dz) 40000.0))
              (Variables|Inv|SetHD d)
              (Variables|Inv|SetHK 5)
              (Variables|Inv|SetHA q)
              (Variables|Inv|SetHSpot (+ ql {mv(0, 0, 45)}))
              (Variables|Inv|SetHL "Récupérer la bombe du kamikaze"))))
        (:CastFailed)))
    (:CastFailed)))
'''
    C['TryHold'] = f'''
(fn TryHold ()
  (bind ch {MYCH}
    (:then
      (CallFunction|NearHold :Ch ch :Extra 0.0)
      (bind k (Variables|Inv|GetHK))
      (if (== k 0)
        (return false))
      (if (>= k 3)
        (CallFunction|ShopServer :Cmd (cat "GWHoldDone " k))
        (return true))
      (Variables|Inv|SetHoldOn true)
      (Variables|Inv|SetHoldKind k)
      (Variables|Inv|SetHoldT0 (Utilities|Time|GetRealTimeSeconds))
      (Variables|Inv|SetHoldFrac 0.0)
      (CallFunction|ShopServer :Cmd "GWHoldStart")
      {LOG('(cat "GW: hold E started, kind " k)')}
      (return true))
    (:CastFailed (return false))))
'''
    C['HoldCancel'] = '''
(fn HoldCancel ()
  (Variables|Inv|SetHoldOn false)
  (Variables|Inv|SetHoldFrac 0.0))
'''
    C['DefuseRelease'] = '''
(fn DefuseRelease ()
  (CallFunction|HoldCancel)
  (if (Variables|Shop|GetDefuseHold)
    (CallFunction|CancelDefuse :Why "E relâché")))
'''
    C['HoldTick'] = f'''
(fn HoldTick ()
  (if (not (Variables|Inv|GetHoldOn))
    (return))
  (if (!= (Variables|Inv|GetHK) (Variables|Inv|GetHoldKind))
    (CallFunction|HoldCancel)
    (return))
  (Variables|Inv|SetHoldFrac (Math|Float|Min(Float) 1.0 (/ (- (Utilities|Time|GetRealTimeSeconds) (Variables|Inv|GetHoldT0)) (select (== (Variables|Inv|GetHoldKind) 1) 1.2 1.5))))
  (if (>= (Variables|Inv|GetHoldFrac) 1.0)
    (CallFunction|ShopServer :Cmd (cat "GWHoldDone " (Variables|Inv|GetHoldKind)))
    (Audio|PlaySound2D :Sound {COINS} :VolumeMultiplier 0.7)
    (CallFunction|HoldCancel)))
'''
    C['GWHoldStart'] = '(fn GWHoldStart () (Variables|Inv|SetHoldSrvAt (GameState|GetServerWorldTimeSeconds :self (Game|GetGameState))))'
    C['GWHoldDone'] = f'''
(fn GWHoldDone (Kind)
  (bind ch {MYCH}
    (:then
      (bind ps {PSC}
        (:then
          (bind gm {GMC}
            (:then
              (CallFunction|NearHold :Ch ch :Extra 130.0)
              (if (!= (Variables|Inv|GetHK) Kind)
                {LOG('(cat "GW: hold refused: kind " Kind " but " (Variables|Inv|GetHK) " here")')}
                (return))
              (if (and (<= Kind 2) (< (- (GameState|GetServerWorldTimeSeconds :self (Game|GetGameState)) (Variables|Inv|GetHoldSrvAt)) 0.8))
                {LOG('"GW: hold refused: E not held long enough"')}
                (return))
              (bind a (Variables|Inv|GetHA))
              (if (== Kind 1)
                (bind body (Utilities|Casting|CastToBP_GW_Character a)
                  (:then (GW|Call|BP_GW_GameMode|LootBody :self gm :PS ps :Who ch :Body body))
                  (:CastFailed)))
              (if (== Kind 2)
                (bind st (Utilities|Casting|CastToBP_GW_Stealable a)
                  (:then (GW|Call|BP_GW_GameMode|StealProp :self gm :PS ps :S st))
                  (:CastFailed)))
              (if (== Kind 5)
                (if (GW|Call|BP_GW_PlayerState|HasRoom :self ps :Id 6)
                  (Actor|DestroyActor :self a)
                  (GW|Call|BP_GW_GameMode|InvGive :self gm :PS ps :Id 6)
                  {LOG('"GW: kamikaze bomb taken"')}
                  (else
                    (GW|Call|BP_GW_GameMode|ShopPay :self gm :PS ps :Amount 0 :Note "Inventaire plein : jetez un objet (Q).")))
                (return))
              (bind bx (Utilities|Casting|CastToBP_GW_MysteryBox a)
                (:then
                  (if (== Kind 3)
                    (GW|Call|BP_GW_GameMode|BoxOpen :self gm :PS ps :Who ch :B bx)
                    (else
                      (GW|Call|BP_GW_GameMode|BoxTake :self gm :PS ps :B bx))))
                (:CastFailed)))
            (:CastFailed)))
        (:CastFailed)))
    (:CastFailed)))
'''
    C['InteractOther_'] = ''
    del C['InteractOther_']
    # ---- sitting (the user, 2026-11-05: "I should be able to press e to sit"): E near a free seat (GM.SitLocs, copied into SeatLocs here: the clients have no game mode), the NPCs' pose (DanceId 10) and
    # slide-free placement; E again or moving stands up. SitI replicates to the owner, which holds the same place locally. Server: GWSit, a toggle
    C['SeatIdxNear'] = f'''
(fn SeatIdxNear (R)
  (Variables|Inv|SetSitBestD R)
  (Variables|Inv|SetSitBestI -1)
  (bind p (Pawn|GetControlledPawn :self self))
  (if (not ({ISVALID} :Object p))
    (return -1))
  (bind me (Transformation|GetActorLocation :self p))
  (bind locs (Variables|Inv|GetSeatLocs))
  (for i (range (Utilities|Array|Length locs))
    (bind q (Utilities|Array|Get(acopy) locs i))
    (if (< (Math|Float|Absolute(Float) (- (.z q) (.z me))) 170.0)
      (bind d (Math|Vector|Distance2D(Vector) q me))
      (if (< d (Variables|Inv|GetSitBestD))
        (Variables|Inv|SetSitBestD d)
        (Variables|Inv|SetSitBestI i))))
  (return (Variables|Inv|GetSitBestI)))
'''
    C['TrySit'] = f'''
(fn TrySit ()
  (if (>= (Variables|Inv|GetSitI) 0)
    (CallFunction|ShopServer :Cmd "GWSit")
    (return true))
  (bind ch {MYCH}
    (:then
      (if (or (GW|Get|BP_GW_Character|IsDead :self ch) (!= (GW|Get|BP_GW_Character|Kind :self ch) 0))
        (return false))
      (if (< (CallFunction|SeatIdxNear :R 170.0) 0)
        (return false))
      (CallFunction|ShopServer :Cmd "GWSit")
      (return true))
    (:CastFailed
      (return false))))
'''
    C['SitStand'] = f'''
(fn SitStand ()
  ; server. A new pawn (new round) or a swapped body: only the seat is given back
  (Variables|Inv|SetSitPick (Variables|Inv|GetSitI))
  (Variables|Inv|SetSitI -1)
  (bind c (Variables|Inv|GetSitCh))
  {LOG('(cat "GW: sit stand seat=" (Variables|Inv|GetSitPick))')}
  (if ({ISVALID} :Object c)
    (if (and (== (Pawn|GetControlledPawn :self self) c) (not (GW|Get|BP_GW_Character|IsDead :self c)))
      (if (== (GW|Get|BP_GW_Character|DanceId :self c) 10)
        (GW|Set|BP_GW_Character|DanceId :self c :DanceId 0))
      (Transformation|SetActorLocation :self c :NewLocation (Variables|Inv|GetSitBack) :bSweep false :bTeleport true)
      (Pawn|Components|CharacterMovement|SetMovementMode :self (GW|Get|/Script/Engine.Character|CharacterMovement :self c) :NewMovementMode "MOVE_Walking" :NewCustomMode 0)))
  (Variables|Inv|SetSitCh (Variables|Inv|GetNoSitCh))
  (bind gm {GMC}
    (:then (GW|Call|BP_GW_GameMode|SeatFree :self gm :I (Variables|Inv|GetSitPick)))
    (:CastFailed)))
'''
    C['GWSit'] = f'''
(fn GWSit ()
  (if (>= (Variables|Inv|GetSitI) 0)
    (CallFunction|SitStand)
    (return))
  (bind ch {MYCH}
    (:then
      (bind gm {GMC}
        (:then
          (if (or (GW|Get|BP_GW_Character|IsDead :self ch) (!= (GW|Get|BP_GW_Character|Kind :self ch) 0))
            (return))
          (bind here (Transformation|GetActorLocation :self ch))
          (Variables|Inv|SetSitPick (GW|Call|BP_GW_GameMode|SeatNear :self gm :Loc here :R 170.0))
          (bind i (Variables|Inv|GetSitPick))
          (if (< i 0)
            {LOG('"GW: sit refused, no free seat here"')}
            (bind pss {PSC}
              (:then (GW|Call|BP_GW_GameMode|ShopPay :self gm :PS pss :Amount 0 :Note "Ce siège est pris."))
              (:CastFailed))
            (else
              (Variables|Inv|SetSitBack here)
              (Variables|Inv|SetSitCh ch)
              (Variables|Inv|SetSitI i)
              (bind seat (GW|Call|BP_GW_GameMode|SeatLoc :self gm :I i))
              (Pawn|Components|CharacterMovement|DisableMovement :self (GW|Get|/Script/Engine.Character|CharacterMovement :self ch))
              (Transformation|SetActorLocationAndRotation :self ch :NewLocation (Math|Vector|MakeVector (.x seat) (.y seat) (.z here)) :NewRotation (Math|Rotator|MakeRotator :Roll 0.0 :Pitch 0.0 :Yaw (GW|Call|BP_GW_GameMode|SeatYaw :self gm :I i)) :bSweep false :bTeleport true)
              (GW|Set|BP_GW_Character|DanceByPlayer :self ch :DanceByPlayer true)
              (GW|Set|BP_GW_Character|DanceId :self ch :DanceId 10)
              {LOG('(cat "GW: sit seat=" i " at " seat " by " (Utilities|GetDisplayName :Object ch))')})))
        (:CastFailed)))
    (:CastFailed)))
'''
    C['SitClientTick'] = f'''
(fn SitClientTick ()
  (bind i (Variables|Inv|GetSitI))
  (bind ch {MYCH}
    (:then
      (bind cm (GW|Get|/Script/Engine.Character|CharacterMovement :self ch))
      (if (< i 0)
        (if (Variables|Inv|GetSitOn)
          (Variables|Inv|SetSitOn false)
          (if (not (Networking|HasAuthority))
            (Pawn|Components|CharacterMovement|SetMovementMode :self cm :NewMovementMode "MOVE_Walking" :NewCustomMode 0)))
        (return))
      (bind rt (Utilities|Time|GetRealTimeSeconds))
      (if (not (Variables|Inv|GetSitOn))
        (Variables|Inv|SetSitOn true)
        (Variables|Inv|SetSitAt rt)
        (if (not (Networking|HasAuthority))
          (bind q (Utilities|Array|Get(acopy) (Variables|Inv|GetSeatLocs) i))
          (Pawn|Components|CharacterMovement|DisableMovement :self cm)
          (Transformation|SetActorLocationAndRotation :self ch :NewLocation (Math|Vector|MakeVector (.x q) (.y q) (.z (Transformation|GetActorLocation :self ch))) :NewRotation (Math|Rotator|MakeRotator :Roll 0.0 :Pitch 0.0 :Yaw (Utilities|Array|Get(acopy) (Variables|Inv|GetSeatYaws) i)) :bSweep false :bTeleport true)))
      (bind age (- rt (Variables|Inv|GetSitAt)))
      (if (< age 0.4)
        (return))
      ; MoveKeys (s43) stamps MoveAt every frame a movement key is down
      (bind moving (< (- (Utilities|Time|GetGameTimeinSeconds) (GW|Get|BP_GW_Character|MoveAt :self ch)) 0.25))
      (if (or moving (or (GW|Get|BP_GW_Character|IsDead :self ch) (and (> age 1.5) (!= (GW|Get|BP_GW_Character|DanceId :self ch) 10))))
        (if (> rt (Variables|Inv|GetSitSent))
          (Variables|Inv|SetSitSent (+ rt 0.5))
          {LOG('(cat "GW: sit: asks to stand, moving=" moving)')}
          (CallFunction|ShopServer :Cmd "GWSit"))))
    (:CastFailed)))
'''
    C['InteractOther'] = '''
(fn InteractOther ()
  ; seated: E stands up, nothing else
  (if (>= (Variables|Inv|GetSitI) 0)
    (CallFunction|TrySit)
    (return))
  ; an open note closes first
  (if (CallFunction|PostClose)
    (return))
  (if (CallFunction|TryShop)
    (return))
  (if (CallFunction|TryTurret)
    (return))
  (if (CallFunction|TryPickup)
    (return))
  (if (CallFunction|TryBreaker)
    (return))
  (if (CallFunction|TryDefuse)
    (return))
  (if (CallFunction|TryDrop)
    (return))
  (if (CallFunction|TryHold)
    (return))
  (if (CallFunction|TrySit)
    (return))
  ; last: a guest NPC in front of me answers (s39_voice_director.py TryTalk -> GWTalk -> GM.TalkTo)
  (CallFunction|TryTalk))
'''
    # ---- jump
    C['RequestJump'] = f'''
(fn RequestJump ()
  (bind ch {MYCH}
    (:then
      (if (GW|Get|BP_GW_Character|IsDead :self ch)
        (return))
      (Character|Jump :self ch)
      ; a guest jumping out of a sprint gets a push: the way out of a corner. Not for the detective.
      (bind now (Utilities|Time|GetRealTimeSeconds))
      (if (and (and (GW|Get|BP_GW_Character|IsSprinting :self ch) (not (GW|Get|BP_GW_Character|IsSeeker :self ch))) (>= now (Variables|Inv|GetNextBoostJump)))
        (Variables|Inv|SetNextBoostJump (+ now 3.0))
        (CallFunction|ShopServer :Cmd "GWJumpBoost")))
    (:CastFailed)))
'''
    C['GWJumpBoost'] = f'''
(fn GWJumpBoost ()
  (bind ch {MYCH}
    (:then
      (if (or (GW|Get|BP_GW_Character|IsDead :self ch) (GW|Get|BP_GW_Character|IsSeeker :self ch))
        (return))
      (bind vel (Transformation|GetVelocity :self ch))
      (bind d (Math|Vector|Normalize (Math|Vector|MakeVector (.x vel) (.y vel) 0.0)))
      (Character|LaunchCharacter :self ch :LaunchVelocity (* d 520.0) :bXYOverride false :bZOverride false)
      {LOG('"GW: sprint jump boost"')}
      (bind gm {GMC}
        (:then (GW|Call|BP_GW_GameMode|GiveBoost :self gm :Ch ch :Mul 1.3 :Dur 2.0))
        (:CastFailed)))
    (:CastFailed)))
'''
    # ---- client tick
    C['GunsVisible'] = f'''
(fn GunsVisible ()
  ; the detective's revolver (GunMesh) shows only while selected, on every machine
  (bind s {GSC}
    (:then
      (for p (Class|GameStateBase|GetPlayerArray :self s)
        (bind pw (PlayerState|GetPawn :self p))
        (if ({ISVALID} :Object pw)
          (bind c (Utilities|Casting|CastToBP_GW_Character pw)
            (:then
              (if (GW|Get|BP_GW_Character|IsSeeker :self c)
                (Rendering|SetVisibility :self (GW|Get|BP_GW_Character|GunMesh :self c) :bNewVisibility (== (GW|Get|BP_GW_Character|HeldItem :self c) 13) :bPropagateToChildren false)))
            (:CastFailed)))))
    (:CastFailed)))
'''
    C['InvChTick'] = f'''
(fn InvChTick ()
  (Variables|Inv|SetHK 0)
  (bind ch {MYCH}
    (:then
      (GW|Call|BP_GW_Character|BoostApply :self ch)
      (if (not (GW|Get|BP_GW_Character|IsDead :self ch))
        (CallFunction|NearHold :Ch ch :Extra 0.0)))
    (:CastFailed)))
'''
    C['InvClientTick'] = f'''
(fn InvClientTick ()
  (if (Utilities|HasLaunchOption :OptionToCheck "GWInvTest")
    (CallFunction|InvTestTick))
  (CallFunction|GunsVisible)
  (CallFunction|DropClientTick)
  (CallFunction|SitClientTick)
  (CallFunction|TrapGhostTick)
  (CallFunction|InvChTick)
  (CallFunction|HoldTick)
  (bind w (Variables|Inv|GetInvWid))
  (if (not ({ISVALID} :Object w))
    (Variables|Inv|SetInvWid (UserInterface|CreateWidget :Class "{INVW}" :OwningPlayer self))
    (UserInterface|Viewport|AddtoViewport :self (Variables|Inv|GetInvWid) :ZOrder 6))
  (bind ps {PSC}
    (:then (GW|Call|{INVW}|Refresh :self (Variables|Inv|GetInvWid) :PS ps :Hold (Variables|Inv|GetHoldFrac)))
    (:CastFailed)))
'''
    bank_shop = '''(if (Utilities|HasLaunchOption :OptionToCheck "GWShopTest")
    (CallFunction|ShopTestTick))'''
    C['ShopClientTick'] = f'''
(fn ShopClientTick ()
  (if (not (Pawn|IsLocalPlayerController))
    (return))
  {bank_shop}
  (CallFunction|InvClientTick)
  (CallFunction|PromptTick)
  (CallFunction|LampTick)
  (CallFunction|DefuseTick)
  (if (not (CallFunction|ShopOpen))
    (return))
  ; the shop closes by itself when you walk away (or the waiter does), die or open the pause menu
  (Variables|Shop|SetShopPaused false)
  (bind hud (Variables|GW|GetHUDWidget))
  (if ({ISVALID} :Object hud)
    (bind pw (GW|Get|{HUD}|PauseW :self hud))
    (if ({ISVALID} :Object pw)
      (Variables|Shop|SetShopPaused (Appearance|IsinViewport :self pw))))
  (if (or (Variables|Shop|GetShopPaused) (not (CallFunction|CanShop)))
    {LOG('"GW: shop auto-closed (pause, death or role)"')}
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
    {LOG('(cat "GW: shop auto-closed (vendor kind " (Variables|Shop|GetShopKind) " now " d " cm away)")')}
    (CallFunction|CloseShop)))
'''
    C['PromptPick'] = f'''
(fn PromptPick ()
  ; floating key prompts: a bomb, a vendor, what E reaches (s40 NearHold), the doorway / floor for a selected trap
  (bind p (Pawn|GetControlledPawn :self self))
  (if (not ({ISVALID} :Object p))
    (return))
  (bind ps {PSC}
    (:then
      (if (not (CallFunction|CanShop))
        (return))
      (if (and (== {Sp('GWRole')} 1) (CallFunction|NearBomb :R 260.0))
        (CallFunction|ShowShopPrompt :Key "E" :Label (select (Variables|Shop|GetDefuseHold) (cat "Désamorçage… " (Math|Float|Truncate (* (Variables|Shop|GetDefuseProgress) 100.0)) " %") "Maintenir : désamorcer") :At (+ (Transformation|GetActorLocation :self (Variables|Shop|GetBombRef)) {mv(0, 0, 60)}))
        (return))
      (bind (near kind) (CallFunction|NearVendor :R 330.0))
      (if (and near (not (CallFunction|ShopOpen)))
        (CallFunction|ShowShopPrompt :Key "E" :Label (select (== kind 1) "Le junkie (marché noir)" (select (== kind 2) "Le serveur (boutique)" "Le barman (boutique)")) :At (+ (Transformation|GetActorLocation :self (Variables|Shop|GetShopVendor)) {mv(0, 0, 118)}))
        (return))
      (if (and (> (Variables|Inv|GetHK) 0) (not ({ISVALID} :Object (Variables|GW|GetPromptFor))))
        (CallFunction|ShowShopPrompt :Key "E" :Label (Variables|Inv|GetHL) :At (Variables|Inv|GetHSpot))
        (return))
      (if (>= (Variables|Inv|GetSitI) 0)
        (CallFunction|ShowShopPrompt :Key "E" :Label "Se lever" :At (+ (Transformation|GetActorLocation :self p) {mv(0, 0, 40)}))
        (return))
      (if (== (CallFunction|HeldNow) 5)
        (bind (top ax hw ok) (CallFunction|FindDoor :Loc (Transformation|GetActorLocation :self p)))
        (if ok
          (CallFunction|ShowShopPrompt :Key "Clic" :Label "Poser le piège dans la porte" :At (- top {mv(0, 0, 45)}))
          (return)))
      (bind seatI (CallFunction|SeatIdxNear :R 170.0))
      (if (>= seatI 0)
        (CallFunction|ShowShopPrompt :Key "E" :Label "S'asseoir" :At (+ (Utilities|Array|Get(acopy) (Variables|Inv|GetSeatLocs) seatI) {mv(0, 0, 70)}))))
    (:CastFailed)))
'''
    # ---- s38 bodies
    C['NearPickupFor'] = f'''
(fn NearPickupFor (Ch)
  (Variables|Default|SetBestD 1000.0)
  (Variables|Default|SetBestP (Variables|GW|GetNoPickup))
  (bind ps {PSC}
    (:then
      (bind s {GSC}
        (:then
          (bind phase (GW|Get|BP_GW_GameState|Phase :self s))
          (bind guest (CallFunction|GuestOK :Ch Ch :NeedHunt false))
          (bind alive (CallFunction|PlayerOK :Ch Ch))
          (bind here (Transformation|GetActorLocation :self Ch))
          (bind balls {Sp('Balls')})
          (bind sword {Sp('HasSword')})
          (bind roomB (GW|Call|BP_GW_PlayerState|HasRoom :self ps :Id 11))
          (bind roomS (GW|Call|BP_GW_PlayerState|HasRoom :self ps :Id 12))
          (for p (Actor|GetAllActorsOfClass :ActorClass "{PK}")
            (bind k (GW|Get|{PK}|Kind :self p))
            (bind tk (GW|Get|{PK}|Taken :self p))
            (bind pl (Transformation|GetActorLocation :self p))
            (bind d (Math|Vector|Distance2D(Vector) pl here))
            (bind dz (- (.z pl) (.z here)))
            (bind reach (select (== k 2) 170.0 (select (== k 4) 140.0 (select (== k 5) 160.0 170.0))))
            ; the post-it can always be read again, by anybody alive; each fire alarm works again after its 20 s
            (bind ok (select (== k 0) (and guest (and (not tk) (and roomB (< balls 2)))) (select (== k 1) (and guest (and (not tk) (and roomS (not sword)))) (select (== k 2) alive (select (== k 3) (and guest (not tk)) (select (== k 4) (and alive (and (not tk) (or (== phase 1) (== phase 2)))) alive))))))
            (if (and ok (and (< d reach) (and (< (* dz dz) 40000.0) (< d (Variables|Default|GetBestD)))))
              (Variables|Default|SetBestD d)
              (Variables|Default|SetBestP p)))
          (return (Variables|Default|GetBestP)))
        (:CastFailed (return (Variables|Default|GetBestP)))))
    (:CastFailed (return (Variables|Default|GetBestP)))))
'''
    C['PickupNotices'] = f'''
(fn PickupNotices ()
  (bind ps {PSC}
    (:then
      (bind now (GameState|GetServerWorldTimeSeconds :self (Game|GetGameState)))
      (bind gun {Sp('HasSwapGun')})
      (bind ready (and gun (>= now {Sp('SwapReadyAt')})))
      (if (!= ready (Variables|GW|GetSeenSwapReady))
        (if ready
          (CallFunction|PickupNotice :Msg "Pistolet d'échange prêt : sélectionnez-le, visez un invité, clic gauche."))
        (Variables|GW|SetSeenSwapReady ready))
      ; the note: a card on the screen every time it is read (PostReads counts the server's reads); it closes on E (InteractOther -> PostClose), when
      ; the player walks away or dies (PostFar), and by itself after 10 s (WBP_Inventory.Refresh)
      (bind w (Variables|Inv|GetInvWid))
      (if (!= (Variables|GW|GetPostReads) (Variables|Inv|GetSeenReads))
        (Variables|Inv|SetSeenReads (Variables|GW|GetPostReads))
        (if ({ISVALID} :Object w)
          (GW|Call|{INVW}|ShowPostIt :self w :Code (Variables|GW|GetKnownCode)))
        {LOG('(cat "GW: post-it shown, code " (Variables|GW|GetKnownCode) " read " (Variables|GW|GetPostReads))')})
      (if ({ISVALID} :Object w)
        (if (> (GW|Get|{INVW}|PostUntil :self w) (Utilities|Time|GetRealTimeSeconds))
          (if (CallFunction|PostFar)
            (GW|Call|{INVW}|HidePost :self w)
            {LOG('"GW: post-it closed (walked away)"')})))
      (bind p (Pawn|GetControlledPawn :self self))
      (if (!= p (Variables|GW|GetSeenPawn))
        (Variables|GW|SetSeenPawn p)
        {LOG('(cat "GW[" (select (Networking|HasAuthority) "host" "client") "] pawn now " (Utilities|GetDisplayName :Object p))')}))
    (:CastFailed)))
'''
    C['PostClose'] = f'''
(fn PostClose ()
  (bind w (Variables|Inv|GetInvWid))
  (if (not ({ISVALID} :Object w))
    (return false))
  (if (<= (GW|Get|{INVW}|PostUntil :self w) (Utilities|Time|GetRealTimeSeconds))
    (return false))
  (GW|Call|{INVW}|HidePost :self w)
  {LOG('"GW: post-it closed (E)"')}
  (return true))
'''
    C['PostFar'] = f'''
(fn PostFar ()
  (bind ch {MYCH}
    (:then
      (if (GW|Get|BP_GW_Character|IsDead :self ch)
        (return true))
      (for p (Actor|GetAllActorsOfClass :ActorClass "{PK}")
        (if (== (GW|Get|{PK}|Kind :self p) 2)
          (if (< (Math|Vector|Distance2D(Vector) (Transformation|GetActorLocation :self p) (Transformation|GetActorLocation :self ch)) 300.0)
            (return false))))
      (return true))
    (:CastFailed (return true))))
'''
    C['FPItemsTick'] = f'''
(fn FPItemsTick ()
  (Variables|GW|SetFPOn false)
  (bind fpi (Variables|GW|GetFPItems))
  (bind ch {MYCH}
    (:then
      (bind held (GW|Get|BP_GW_Character|HeldItem :self ch))
      (bind sw (== held 12))
      (bind ball (== held 11))
      (bind sb (== held 10))
      (Variables|GW|SetFPOn (and (GW|Get|BP_GW_Character|ViewFP :self ch) (or (or sw ball) sb)))
      (if (not (Variables|GW|GetFPOn))
        (if ({ISVALID} :Object fpi)
          (Rendering|SetActorHiddenInGame :self fpi :bNewHidden true))
        (return))
      (if (not ({ISVALID} :Object fpi))
        (Variables|GW|SetFPItems (Game|SpawnActorfromClass :Class "{FPC}" :SpawnTransform (Math|Transform|MakeTransform) :CollisionHandlingOverride "AlwaysSpawn")))
      (bind f (Variables|GW|GetFPItems))
      (bind cam (GW|Get|BP_GW_Character|FollowCamera :self ch))
      (if (!= (Variables|GW|GetFPAttach) ch)
        (Variables|GW|SetFPAttach ch)
        (Transformation|AttachActorToComponent :self f :Parent cam :SocketName "None" :LocationRule "SnapToTarget" :RotationRule "SnapToTarget" :ScaleRule "KeepWorld" :bWeldSimulatedBodies false))
      (Rendering|SetActorHiddenInGame :self f :bNewHidden false)
      (Rendering|SetVisibility :self (GW|Get|{FPC}|SwordRoot :self f) :bNewVisibility sw :bPropagateToChildren true)
      (Rendering|SetVisibility :self (GW|Get|{FPC}|Ball :self f) :bNewVisibility ball :bPropagateToChildren false)
      ; the hidden blade's model: first person only (s41_item_models.py adds the component)
      (Rendering|SetVisibility :self (GW|Get|{FPC}|SecretBlade :self f) :bNewVisibility sb :bPropagateToChildren false)
      (for h (Actor|GetAllActorsOfClass :ActorClass "{HS}")
        (if (== (GW|Get|{HS}|Holder :self h) ch)
          (if (!= (GW|Get|{HS}|SlashCount :self h) (GW|Get|{FPC}|SeenSlash :self f))
            (GW|Set|{FPC}|SeenSlash :self f :SeenSlash (GW|Get|{HS}|SlashCount :self h))
            (GW|Call|{FPC}|StartSwing :self f)))))
    (:CastFailed
      (if ({ISVALID} :Object fpi)
        (Rendering|SetActorHiddenInGame :self fpi :bNewHidden true)))))
'''
    # ---- test commands (-GWDev) + -GWInvTest
    GATE = '(if (not (CallFunction|DevOK))\n    (return))'
    C['GWDevKillRival'] = f'''
(fn GWDevKillRival ()
  {GATE}
  ; last one standing: the first other living player falls, for real (dev menu, harness plan "last")
  (bind ch {MYCH}
    (:then
      (bind gm {GMC}
        (:then
          (for c (Actor|GetAllActorsOfClass :ActorClass {CHAR})
            (if (and (and (!= c ch) (Pawn|IsPlayerControlled :self c)) (and (not (GW|Get|BP_GW_Character|IsDead :self c)) (== (GW|Get|BP_GW_Character|Kind :self c) 0)))
              (GW|Call|BP_GW_GameMode|HurtCharacter :self gm :Victim c :Amount 1000.0 :Impulse {mv(0, 0, 100)} :Cause "a été éliminé (menu développeur)")
              (break))))
        (:CastFailed)))
    (:CastFailed)))
'''
    C['GWDevHurtSeeker'] = f'''
(fn GWDevHurtSeeker ()
  {GATE}
  ; a trap on my own feet, for real (TrapFire)
  (bind ch {MYCH}
    (:then
      (bind gm {GMC}
        (:then
          (bind t (Game|SpawnActorfromClass :Class "{TRAP}" :SpawnTransform (Math|Transform|MakeTransform :Location (Transformation|GetActorLocation :self ch)) :CollisionHandlingOverride "AlwaysSpawn"))
          (GW|Call|BP_GW_GameMode|TrapFire :self gm :T t :Victim ch))
        (:CastFailed)))
    (:CastFailed)))
'''
    C['GWDevInvState'] = f'''
(fn GWDevInvState ()
  (bind ps {PSC}
    (:then
      (bind ch {MYCH}
        (:then {LOG('(cat "GW inv state: role " ' + Sp('GWRole') + ' " slots " ' + ' " " '.join(Sp(f'Slot{i}') for i in range(4)) + ' " sel " ' + Sp('InvSel') + ' " held " (GW|Get|BP_GW_Character|HeldItem :self ch) " money " ' + Sp('Money') + ' " hp " (GW|Get|BP_GW_Character|Health :self ch) " dead " (GW|Get|BP_GW_Character|IsDead :self ch) " viewfp " (GW|Get|BP_GW_Character|ViewFP :self ch) " jump " (GW|Get|/Script/Engine.Character|JumpMaxCount :self ch) " speed " (Class|CharacterMovementComponent|GetMaxWalkSpeed :self (GW|Get|/Script/Engine.Character|CharacterMovement :self ch)))')})
        (:CastFailed {LOG('"GW inv state: no character (ghost?)"')})))
    (:CastFailed)))
'''
    C['GWDevChand'] = f'''
(fn GWDevChand ()
  {GATE}
  ; me under the nearest... the hall chandelier, an NPC with me: shot straight up
  (bind ch {MYCH}
    (:then
      (bind gm {GMC}
        (:then
          (bind p (Utilities|Array|Get(acopy) (GW|Get|BP_GW_GameMode|ChandPts :self gm) 0))
          (bind st (Math|Vector|MakeVector (+ (.x p) 200.0) (.y p) 150.0))
          (bind dir (Math|Vector|Normalize (- p st)))
          (for c (Actor|GetAllActorsOfClass :ActorClass {CHAR})
            (if (and (and (not (Pawn|IsPlayerControlled :self c)) (not (GW|Get|BP_GW_Character|IsDead :self c))) (== (GW|Get|BP_GW_Character|Kind :self c) 0))
              (Transformation|SetActorLocation :self c :NewLocation (Math|Vector|MakeVector (.x p) (.y p) 110.0) :bSweep false :bTeleport true)
              (break)))
          (GW|Call|BP_GW_GameMode|ChandShot :self gm :Shooter ch :Start st :Dir dir :End (+ p (* dir 300.0))))
        (:CastFailed)))
    (:CastFailed)))
'''
    C['GWDevKamikaze'] = f'''
(fn GWDevKamikaze ()
  {GATE}
  ; a kamikaze next to me, shot by me; his bomb stays where he fell
  (bind ch {MYCH}
    (:then
      (bind gm {GMC}
        (:then
          (bind k (GW|Call|BP_GW_GameMode|SpawnSpecial :self gm :Kind 2 :Loc (+ (Transformation|GetActorLocation :self ch) {mv(120, 0, 0)})))
          (if ({ISVALID} :Object k)
            (GW|Call|BP_GW_GameMode|GuestHit :self gm :Shooter ch :Victim k :Dir {mv(1, 0, 0)})))
        (:CastFailed)))
    (:CastFailed)))
'''
    C['GWDevKillNear'] = f'''
(fn GWDevKillNear ()
  {GATE}
  ; an NPC dead beside me (bodies to search)
  (bind ch {MYCH}
    (:then
      (for c (Actor|GetAllActorsOfClass :ActorClass {CHAR})
        (if (and (and (not (Pawn|IsPlayerControlled :self c)) (not (GW|Get|BP_GW_Character|IsDead :self c))) (== (GW|Get|BP_GW_Character|Kind :self c) 0))
          (Transformation|SetActorLocation :self c :NewLocation (+ (Transformation|GetActorLocation :self ch) {mv(80, 0, 0)}) :bSweep false :bTeleport true)
          (GW|Call|BP_GW_Character|Die :self c :Impulse {mv(0, 0, -10)})
          (break))))
    (:CastFailed)))
'''
    C['GWDevTrapHere'] = f'''
(fn GWDevTrapHere ()
  {GATE}
  ; a floor trap under an NPC and one under a bandit next to me: only the bandit should set his off
  (bind ch {MYCH}
    (:then
      (bind gm {GMC}
        (:then
          (bind ps {PSC}
            (:then
              {SpA('Traps', 1)}
              (GW|Call|BP_GW_GameMode|PlaceTrap :self gm :PS ps :Ch ch))
            (:CastFailed)))
        (:CastFailed)))
    (:CastFailed)))
'''
    C['GWDevInnocent'] = f'''
(fn GWDevInnocent ()
  {GATE}
  ; as a detective: shoot one NPC for real (OnCharacterShot), the penalty included; dev test rounds have no penalty, so TestRound goes off
  (bind ch {MYCH}
    (:then
      (bind gm {GMC}
        (:then
          (GW|Set|BP_GW_GameState|TestRound :self (GW|Call|BP_GW_GameMode|GetGS :self gm) :TestRound false)
          (for c (Actor|GetAllActorsOfClass :ActorClass {CHAR})
            (if (and (and (not (Pawn|IsPlayerControlled :self c)) (not (GW|Get|BP_GW_Character|IsDead :self c))) (== (GW|Get|BP_GW_Character|Kind :self c) 0))
              (GW|Call|BP_GW_GameMode|OnCharacterShot :self gm :Shooter ch :Victim c :Dir {mv(1, 0, 0)})
              (break))))
        (:CastFailed)))
    (:CastFailed)))
'''
    SRV = lambda c: f'(CallFunction|DevServer :Cmd "{c}")'
    STEPS = [
        SRV('GWDevQuickTest 1'), SRV('GWDevAutoEvents 0'), SRV('GWDevRole 1'), 'WAIT', 'WAIT', SRV('GWDevMoney 3000'), SRV('GWDevInvState'),   # a guest, a test round (no passive income)
        SRV('GWDevShopHere 1'), '(CallFunction|ShopBuy :Id 1)', '(CallFunction|ShopBuy :Id 1)', SRV('GWDevInvState'), 'WAIT', '(Development|ExecuteConsoleCommand :Command "Shot showui" :SpecificPlayer self)',   # the rifle, 2 bullets: third person
        '(Variables|GW|SetVTestAds true)', 'WAIT', 'WAIT', '(Development|ExecuteConsoleCommand :Command "Shot showui" :SpecificPlayer self)', SRV('GWDevInvState'), SRV('GWDevGoNPC'), '(CallFunction|RequestFire)', 'WAIT', '(Variables|GW|SetVTestAds false)', 'WAIT',   # aims (first person, drift), fires
        SRV('GWDevInvState'), '(CallFunction|ShopBuy :Id 2)', SRV('GWDevInvState'), '(CallFunction|InvPick :I 1)', '(CallFunction|RequestFire)',   # smoke: selected, used
        SRV('GWDevInvState'), '(CallFunction|ShopBuy :Id 3)', '(CallFunction|RequestFire)', '(CallFunction|ShopBuy :Id 4)', '(CallFunction|ShopBuy :Id 10)',  # lamp on, gas, blade
        SRV('GWDevInvState'), '(CallFunction|ShopBuy :Id 6)', SRV('GWDevInvState'),   # 4 slots full (rifle lamp gas blade): the bomb is refused
        SRV('GWDevKillNear'), '(CallFunction|TryHold)', 'WAIT', 'WAIT', SRV('GWDevInvState'), '(CallFunction|DefuseRelease)',    # search a body (hold 1.2 s)
        '(CallFunction|InvPick :I 3)', SRV('GWDevGoNPC'), 'BLADE', 'WAIT', SRV('GWDevInvState'),   # the blade
        '(CallFunction|InvPick :I 2)', '(CallFunction|InvDrop)', SRV('GWDevInvState'), SRV('GWDevKamikaze'), '(CallFunction|TryHold)', SRV('GWDevInvState'),   # throw away, the kamikaze's bomb
        SRV('GWDevGoProp'), '(CallFunction|TryHold)', 'WAIT', 'WAIT', 'WAIT', SRV('GWDevInvState'), '(CallFunction|DefuseRelease)',   # steal a prop (hold 1.5 s)
        '(CallFunction|InvPick :I 2)', '(CallFunction|InvDrop)', SRV('GWDevMoney 500'), SRV('GWDevGoBox'), '(CallFunction|TryHold)', 'WAIT', 'WAIT', 'WAIT', 'WAIT', 'WAIT', 'WAIT', '(CallFunction|TryHold)', SRV('GWDevInvState'),   # the box
        SRV('GWDevKnight'), 'WAIT', '(Development|ExecuteConsoleCommand :Command "Shot showui" :SpecificPlayer self)', SRV('GWDevGoBox'), 'WAIT', '(Development|ExecuteConsoleCommand :Command "Shot showui" :SpecificPlayer self)',
        SRV('GWDevChandSee'), 'WAIT', SRV('GWDevChand'), '(Development|ExecuteConsoleCommand :Command "Shot showui" :SpecificPlayer self)', 'WAIT', '(Development|ExecuteConsoleCommand :Command "Shot showui" :SpecificPlayer self)', 'WAIT', SRV('GWDevInvState'), '(Development|ExecuteConsoleCommand :Command "Shot showui" :SpecificPlayer self)',   # a chandelier, seen from the side
        SRV('GWDevTrapTest 2'), 'WAIT', SRV('GWDevTrapTest 0'), 'WAIT', 'WAIT', 'WAIT', 'WAIT', 'WAIT', 'WAIT', SRV('GWDevTrapTest 1'), 'WAIT', 'WAIT',   # a trap: an NPC on it for 5 s (nothing), then a bandit
        SRV('GWDevRobotTurret'), 'WAIT', 'WAIT',   # the machine gun kills the robot
        SRV('GWSprint 1'), '(CallFunction|SprintOn)', 'WAIT', '(CallFunction|RequestJump)', 'WAIT', SRV('GWDevInvState'), '(CallFunction|SprintOff)', '(CallFunction|ViewToggle)', 'WAIT', SRV('GWDevInvState'), '(CallFunction|ViewToggle)',   # jump, view
        SRV('GWDevAlarmNear'), '(CallFunction|TryPickup)', SRV('GWDevInvState'), 'WAIT', '(CallFunction|TryPickup)', SRV('GWDevInvState'),   # alarm, again at once: refused
        SRV('GWDevPostIt'), '(CallFunction|TryPickup)', 'WAIT',  # the post-it
        SRV('GWDevRole 2'), 'WAIT', 'WAIT', SRV('GWDevInvState'), '(CallFunction|ShopBuy :Id 2)', SRV('GWDevInvState'), '(CallFunction|ShopBuy :Id 1)',   # detective: revolver slot, can shop, no rifle
        '(CallFunction|InvPick :I 0)', 'WAIT', '(Development|ExecuteConsoleCommand :Command "Shot showui" :SpecificPlayer self)', '(Variables|GW|SetVTestAds true)', 'WAIT', 'WAIT', '(Development|ExecuteConsoleCommand :Command "Shot showui" :SpecificPlayer self)', '(Variables|GW|SetVTestAds false)', 'WAIT', '(CallFunction|RequestFire)', SRV('GWDevInvState'),   # the revolver
        SRV('GWDevInnocent'), SRV('GWDevInnocent'), SRV('GWDevInnocent'), SRV('GWDevInnocent'), 'WAIT', SRV('GWDevInvState'),   # 4 innocents: the detective dies
        SRV('GWDevRespawn'), 'WAIT', 'WAIT', SRV('GWDevHeal'), SRV('GWDevHurtSeeker'), SRV('GWDevHurtSeeker'), SRV('GWDevInvState'), SRV('GWDevHurtSeeker'), SRV('GWDevHurtSeeker'), SRV('GWDevInvState'),    # 4 traps: he dies again
    ]
    steps_code = '\n'.join(f'  (if (== St {i})\n    {("(Development|PrintString :InString " + chr(34) + "GW invtest wait" + chr(34) + " :bPrintToScreen false)") if s == "WAIT" else ("(bind r" + str(i) + " " + s + ")" if s == "(CallFunction|TryHold)" or s == "(CallFunction|TryPickup)" else ("(CallFunction|ShopServer :Cmd (cat " + chr(34) + "GWBlade " + chr(34) + " 0.0 " + chr(34) + " " + chr(34) + " (.yaw (Pawn|GetControlRotation :self self))))" if s == "BLADE" else s))}\n    (return))' for i, s in enumerate(STEPS))
    C['InvTestStep'] = f'''
(fn InvTestStep (St)
{steps_code})
'''
    C['InvTestTick'] = f'''
(fn InvTestTick ()
  (bind now (Utilities|Time|GetRealTimeSeconds))
  (if (<= (Variables|Inv|GetInvT0) 0.0)
    (Variables|Inv|SetInvT0 (+ now 8.0)))
  (if (< now (Variables|Inv|GetInvT0))
    (return))
  (bind st (Variables|Inv|GetInvStep))
  (if (> st {len(STEPS) + 2})
    (return))
  (Variables|Inv|SetInvT0 (+ now 0.8))
  {LOG('(cat "GW invtest step " st)')}
  (if (== st {len(STEPS) + 2})
    {LOG('"GW invtest done"')})
  ; (st is a pure read of InvStep: it must be used before InvStep changes)
  (CallFunction|InvTestStep :St st)
  (Variables|Inv|SetInvStep (+ (Variables|Inv|GetInvStep) 1)))
'''
    ensure_fn(pc, 'GWDevGoNPC', exec_fn=True)
    ensure_fn(pc, 'GWDevAlarmNear', exec_fn=True)
    ensure_fn(pc, 'GWDevPostIt', exec_fn=True)
    compile_bp(pc, quiet=True)
    C['GWDevGoNPC'] = f'''
(fn GWDevGoNPC ()
  {GATE}
  ; the nearest living NPC comes right in front of me, frozen in place by the test
  (bind ch {MYCH}
    (:then
      (for c (Actor|GetAllActorsOfClass :ActorClass {CHAR})
        (if (and (and (not (Pawn|IsPlayerControlled :self c)) (not (GW|Get|BP_GW_Character|IsDead :self c))) (== (GW|Get|BP_GW_Character|Kind :self c) 0))
          (Transformation|SetActorLocation :self c :NewLocation (+ (Transformation|GetActorLocation :self ch) (* (Math|Vector|GetForwardVector (Pawn|GetControlRotation :self self)) 110.0)) :bSweep false :bTeleport true)
          (break))))
    (:CastFailed)))
'''
    GO = lambda cls, lbl: f'''
(fn {lbl} ()
  {GATE}
  (bind ch {MYCH}
    (:then
      (for a (Actor|GetAllActorsOfClass :ActorClass "{cls}")
        (Transformation|SetActorLocation :self ch :NewLocation (+ (Transformation|GetActorLocation :self a) {mv(0, 90, 96)}) :bSweep false :bTeleport true)
        (break)))
    (:CastFailed)))
'''
    C['GWDevKnight'] = f'''
(fn GWDevKnight ()
  {GATE}
  ; in front of the first armour, looking at its right hand and the sword (rendered QA)
  (bind ch {MYCH}
    (:then
      (Transformation|SetActorLocation :self ch :NewLocation {mv(2740, 2140, 130)} :bSweep false :bTeleport true)
      (Pawn|SetControlRotation :self self :NewRotation (Math|Rotator|MakeRotator :Pitch -8.0 :Yaw 90.0 :Roll 0.0)))
    (:CastFailed)))
'''
    C['GWDevChandSee'] = f'''
(fn GWDevChandSee ()
  {GATE}
  (bind ch {MYCH}
    (:then
      (bind gm {GMC}
        (:then
          ; 7 m from the hall chandelier, beside it, seeing it fall
          (bind p (Utilities|Array|Get(acopy) (GW|Get|BP_GW_GameMode|ChandPts :self gm) 0))
          (bind me (Math|Vector|MakeVector (- (.x p) 650.0) (+ (.y p) 160.0) 130.0))
          (Transformation|SetActorLocation :self ch :NewLocation me :bSweep true :bTeleport true)
          (Pawn|SetControlRotation :self self :NewRotation (Math|Rotator|FindLookatRotation :Start (+ me {mv(0, 0, 60)}) :Target (Math|Vector|MakeVector (.x p) (.y p) (* 0.55 (.z p))))))
        (:CastFailed)))
    (:CastFailed)))
'''
    C['GWDevGoBox'] = GO(BOX, 'GWDevGoBox')
    C['GWDevGoProp'] = GO(STEAL, 'GWDevGoProp')
    C['GWDevTrapTest'] = f'''
(fn GWDevTrapTest (Mode)
  {GATE}
  ; 2: a floor trap ahead of me. 0: a living NPC moved onto it (must not fire). 1: a bandit spawned on it (must fire)
  (if (== Mode 2)
    (CallFunction|GWDevTrapHere)
    (return))
  (for t (Actor|GetAllActorsOfClass :ActorClass "{TRAP}")
    (bind tl (Transformation|GetActorLocation :self t))
    (if (== Mode 1)
      (bind gm {GMC}
        (:then (GW|Call|BP_GW_GameMode|SpawnSpecial :self gm :Kind 1 :Loc (+ tl {mv(0, 0, 90)})))
        (:CastFailed))
      (else
        (for c (Actor|GetAllActorsOfClass :ActorClass {CHAR})
          (if (and (and (not (Pawn|IsPlayerControlled :self c)) (not (GW|Get|BP_GW_Character|IsDead :self c))) (== (GW|Get|BP_GW_Character|Kind :self c) 0))
            (Transformation|SetActorLocation :self c :NewLocation (+ tl {mv(0, 0, 90)}) :bSweep false :bTeleport true)
            (break)))))
    (break)))
'''
    C['GWDevRobotTurret'] = f'''
(fn GWDevRobotTurret ()
  {GATE}
  (bind ch {MYCH}
    (:then
      (bind gm {GMC}
        (:then
          (bind r (GW|Call|BP_GW_GameMode|SpawnSpecial :self gm :Kind 3 :Loc (+ (Transformation|GetActorLocation :self ch) {mv(300, 0, 0)})))
          (if ({ISVALID} :Object r)
            (for k (range 40)
              (GW|Call|BP_GW_GameMode|TurretHit :self gm :Gunner ch :Victim r :Dir {mv(1, 0, 0)}))))
        (:CastFailed)))
    (:CastFailed)))
'''
    for fname, kind, off in (('GWDevAlarmNear', 4, (0, 90, -50)), ('GWDevPostIt', 2, (60, 0, 90))):
        C[fname] = f'''
(fn {fname} ()
  {GATE}
  (bind ch {MYCH}
    (:then
      (for p (Actor|GetAllActorsOfClass :ActorClass "{PK}")
        (if (== (GW|Get|{PK}|Kind :self p) {kind})
          (Transformation|SetActorLocation :self ch :NewLocation (+ (Transformation|GetActorLocation :self p) {mv(*off)}) :bSweep false :bTeleport true)
          (break))))
    (:CastFailed)))
'''
    for n, code in C.items():
        wr(pc, n, code)
    compile_bp(pc, quiet=True)
    for k, (ia_name, (_, fn)) in enumerate(KEYS.items()):
        wire_input(pc, ia_name, {'Started': fn}, pos=(0, 7600 + 200 * k))
    wire_input(pc, 'IA_Jump', {'Started': 'RequestJump'}, pos=(0, 9400))
    finish(pc)
