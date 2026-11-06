# s40_inventory.py, part "gm": exec'd by s40 (its names are in scope). Server side of the inventory and the economy.
import json as _json
if want('gm'):
    # ---- chandeliers: one spot per ChandelierBody instance, with the radius of its cluster (read from the level's ISMs)
    _spots, _rads = [], []
    _w = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
    _root = [a for a in _w if a.get_actor_label() == 'GW_Chandeliers']
    if _root:
        _cs = _root[0].get_components_by_class(unreal.InstancedStaticMeshComponent)
        for c_ in _cs:
            if c_.static_mesh and 'ChandelierBody' in c_.static_mesh.get_name():
                for i_ in range(c_.get_instance_count()):
                    _spots.append(c_.get_instance_transform(i_, True).translation)
        _rads = [40.0] * len(_spots)
        for c_ in _cs:
            for i_ in range(c_.get_instance_count()):
                l_ = c_.get_instance_transform(i_, True).translation
                for k_, s_ in enumerate(_spots):
                    d_ = math.hypot(l_.x - s_.x, l_.y - s_.y)
                    if d_ < 240.0 and d_ > _rads[k_]:
                        _rads[k_] = d_
        _rads = [r_ + 6.0 for r_ in _rads]
    print('chandeliers', len(_spots), [round(r_) for r_ in _rads])
    for v, t in (('InvRound', 'int'), ('NextInvFx', 'float'), ('LootN', 'int'), ('LootPick', 'int'), ('BoxPick', 'int'), ('FallKills', 'int')):
        ensure_var(gm, v, t, category='Inv')
    ensure_var(gm, 'InvCh', obj_class=chc, category='Inv')
    ensure_var(gm, 'TheBox', obj_class=bxc, category='Inv')
    ensure_var(gm, 'ChandPts', struct=V3, array=True, category='Inv')
    ensure_var(gm, 'ChandRs', 'float', array=True, category='Inv')
    ensure_var(gm, 'StealOn', 'bool', category='Inv')
    ensure_var(gm, 'TmpSpot', struct=V3, category='Inv')
    ensure_var(gm, 'BoxOK', 'bool', category='Inv')
    for v_, t_ in (('BladeCD', 'float'), ('TrapDmg', 'float')):       # the user, 2026-11-05: dev menu, Réglages
        ensure_var(gm, v_, t_, category='Inv')
    ensure_var(gm, 'TrapNPC', 'bool', category='Inv')
    ensure_var(gm, 'TrapRival', 'bool', category='Inv')
    ensure_var(gm, 'SeatBestD', 'float', category='Inv')
    ensure_var(gm, 'SeatBestI', 'int', category='Inv')
    ensure_fn(gm, 'SeatNear', inputs=[('Loc', V3), ('R', 'float')], outputs=[('I', 'int')])
    GMF = {
        'InvSync': [('PS', PSCLS)], 'InvTick': [], 'InvRoundCheck': [], 'InvAdd': [('PS', PSCLS), ('Id', 'int')], 'InvGive': [('PS', PSCLS), ('Id', 'int')],
        'InvClear': [('PS', PSCLS), ('Id', 'int')], 'InvHand': [('PS', PSCLS), ('Id', 'int')], 'LootBody': [('PS', PSCLS), ('Who', chc), ('Body', chc)],
        'StealProp': [('PS', PSCLS), ('S', stc)], 'StealInit': [], 'BoxOpen': [('PS', PSCLS), ('Who', chc), ('B', bxc)], 'BoxTake': [('PS', PSCLS), ('B', bxc)],
        'BoxPlace': [], 'KamikazeDown': [('Victim', chc), ('Dir', V3)], 'BladeStrike': [('PS', PSCLS), ('Who', chc), ('Dir', V3)],
        'ChandShot': [('Shooter', chc), ('Start', V3), ('Dir', V3), ('End', V3)], 'ChandFallStart': [('I', 'int'), ('Shooter', chc)], 'ChandTick': [], 'ChandBreak': [('F', fac)],
        'BoostTick': [], 'GiveBoost': [('Ch', chc), ('Mul', 'float'), ('Dur', 'float')],
        'DropItem': [('PS', PSCLS), ('Ch', chc), ('Id', 'int')], 'TakeDrop': [('PS', PSCLS), ('Ch', chc), ('D', load_bp('BP_GW_ItemDrop', SHOP).generated_class())],
    }
    for f, ins in GMF.items():
        ensure_fn(gm, f, inputs=ins)
    # signatures of the rewritten bodies already exist (s12/s34/s35/s38)
    compile_bp(gm, quiet=True)
    d_ = cdo(gm)
    d_.set_editor_property('ChandPts', _spots)
    d_.set_editor_property('ChandRs', _rads)
    d_.set_editor_property('BladeCD', 8.0)
    d_.set_editor_property('TrapDmg', 50.0)
    NOTE = lambda ps, s: f'(CallFunction|ShopPay :PS {ps} :Amount 0 :Note {s})'
    NOW = '(CallFunction|Now)'
    G = {}
    adds = '\n'.join(f'  (if (and (> (GW|Call|BP_GW_PlayerState|CountOf :self PS :Id {i}) 0) (< (GW|Call|BP_GW_PlayerState|SlotOf :self PS :Id {i}) 0))\n    (CallFunction|InvAdd :PS PS :Id {i}))' for i in ALLITEMS)
    G['ItemPrice'] = f'(fn ItemPrice (Id Kind) (return (select (== Kind 1) {sel("Id", {i[0]: i[4] for i in shop_items.ITEMS}, "0")} {sel("Id", {i[0]: i[3] for i in shop_items.ITEMS}, "0")})))'
    G['ItemName'] = '(fn ItemName (Id) (return ' + sel('Id', {**{i[0]: '"' + i[1] + '"' for i in shop_items.ITEMS}, 3: '"Lampe torche"', 11: '"Boule de billard"', 12: '"Épée"'}, '"?"') + '))'
    G['InvAdd'] = f'''
(fn InvAdd (PS Id)
  ; a new item takes the first free slot (none free: it waits there, only the shop and the dev menu can overflow) and goes in hand
  (bind free (GW|Call|BP_GW_PlayerState|SlotOf :self PS :Id 0))
  (if (< free 0)
    (return))
  ; (free is a pure read: it changes as soon as the slot is set, so the selection goes first)
  {SpS('InvSel', 'free', 'PS')}
  (GW|Call|BP_GW_PlayerState|SlotSet :self PS :I {Sp('InvSel', 'PS')} :V Id)
  {LOG('(cat "GW inv: " (PlayerState|GetPlayerName :self PS) " + item " Id " slot " ' + Sp('InvSel', 'PS') + ')')})
'''
    G['InvSync'] = f'''
(fn InvSync (PS)
  (for i (range 4)
    (bind id (GW|Call|BP_GW_PlayerState|SlotGet :self PS :I i))
    (if (> id 0)
      (if (<= (GW|Call|BP_GW_PlayerState|CountOf :self PS :Id id) 0)
        (GW|Call|BP_GW_PlayerState|SlotSet :self PS :I i :V 0))))
{adds}
  ; a guest turned detective leaves the murder weapons behind; his revolver always has a slot
  (if (== {Sp('GWRole', 'PS')} 2)
    {SpS('Ammo', '0', 'PS')}
    {SpS('Traps', '0', 'PS')}
    {SpS('Bombs', '0', 'PS')}
    {SpS('Balls', '0', 'PS')}
    {SpS('HasSwapGun', 'false', 'PS')}
    {SpS('HasBlade', 'false', 'PS')}
    {SpS('BladeReadyAt', '0.0', 'PS')}
    {SpS('HasSword', 'false', 'PS')}
    (if (< (GW|Call|BP_GW_PlayerState|SlotOf :self PS :Id 13) 0)
      (if (< (GW|Call|BP_GW_PlayerState|SlotOf :self PS :Id 0) 0)
        (GW|Call|BP_GW_PlayerState|SlotSet :self PS :I 0 :V 0))))
  (Variables|Inv|SetInvCh (CallFunction|CharOfPS :PS PS))
  (bind c (Variables|Inv|GetInvCh))
  (if (not ({ISVALID} :Object c))
    (return))
  (bind on (CallFunction|IsOnTurret :P c))
  (bind dead (GW|Get|BP_GW_Character|IsDead :self c))
  (bind h (select (or on dead) 0 (GW|Call|BP_GW_PlayerState|SlotGet :self PS :I {Sp('InvSel', 'PS')})))
  (if (!= (GW|Get|BP_GW_Character|HeldItem :self c) h)
    (GW|Set|BP_GW_Character|HeldItem :self c :HeldItem h)
    {LOG('(cat "GW inv: " (PlayerState|GetPlayerName :self PS) " holds " h " slots " ' + ' " " '.join(Sp(f'Slot{i}', 'PS') for i in range(4)) + ')')}))
'''
    gives = '\n'.join(f'  (if (== Id {i})\n    {SpA(v, 1 if i != 1 else 1, "PS")})' for i, v in COUNTVAR.items()) + '\n' + '\n'.join(f'  (if (== Id {i})\n    {SpS(v, "true", "PS")})' for i, v in BOOLVAR.items())
    G['InvGive'] = f'''
(fn InvGive (PS Id)
{gives}
  (if (== Id 7)
    {SpA('TurretAmmo', 60, 'PS')})
  (if (== Id 8)
    {SpS('SwapReadyAt', '0.0', 'PS')})
  (CallFunction|InvHand :PS PS :Id Id))
'''
    clears = '\n'.join(f'  (if (== Id {i})\n    {SpS(v, "0", "PS")})' for i, v in COUNTVAR.items()) + '\n' + '\n'.join(f'  (if (== Id {i})\n    {SpS(v, "false", "PS")})' for i, v in BOOLVAR.items())
    G['InvClear'] = f'''
(fn InvClear (PS Id)
{clears}
  (CallFunction|InvSync :PS PS))
'''
    G['InvHand'] = f'''
(fn InvHand (PS Id)
  (CallFunction|InvSync :PS PS)
  (bind s (GW|Call|BP_GW_PlayerState|SlotOf :self PS :Id Id))
  (if (>= s 0)
    {SpS('InvSel', 's', 'PS')}
    (CallFunction|InvSync :PS PS)))
'''
    # ---- ticks
    G['ShopTick'] = f'''
(fn ShopTick ()
  (CallFunction|SpawnVendors)
  (bind phase (GW|Get|BP_GW_GameState|Phase :self (CallFunction|GetGS)))
  (if (!= phase (Variables|Shop|GetShopPhase))
    (if (or (== phase 0) (== phase 1))
      (CallFunction|ShopCleanup))
    (Variables|Shop|SetShopPhase phase))
  (CallFunction|TrapTick)
  (CallFunction|BombTick)
  (CallFunction|InvTick)
  (CallFunction|GunTick)
  (CallFunction|CrackerTick)
  (CallFunction|JunkieTick)
  (CallFunction|WaiterTick))
'''
    G['SurviveTick'] = '(fn SurviveTick () (return))'     # user, 2026-11-03: no passive income
    G['InvTick'] = f'''
(fn InvTick ()
  (CallFunction|InvRoundCheck)
  (for ps (CallFunction|GetGWPlayers)
    (CallFunction|InvSync :PS ps))
  (CallFunction|BoostTick)
  (CallFunction|ChandTick)
  ; fire alarms come back (s38 PullAlarm: 20 s per station)
  (bind now {NOW})
  (for p (Actor|GetAllActorsOfClass :ActorClass "{PK}")
    (if (and (== (GW|Get|{PK}|Kind :self p) 4) (GW|Get|{PK}|Taken :self p))
      (if (>= now (GW|Get|{PK}|BackAt :self p))
        (GW|Set|{PK}|Taken :self p :Taken false))))
  ; the mystery box: spin over -> the prize waits for its winner, with no time limit (only his death or departure ends it)
  (bind b (Variables|Inv|GetTheBox))
  (if ({ISVALID} :Object b)
    (bind st (GW|Get|{BOX}|State :self b))
    (if (and (== st 1) (>= now (+ (GW|Get|{BOX}|SpinAt :self b) 3.8)))
      (GW|Set|{BOX}|State :self b :State 2)
      (Networking|ForceNetUpdate :self b)
      (Development|PrintString :InString (cat "GW: mystery box landed on " (GW|Get|{BOX}|Result :self b)) :bPrintToScreen false))
    (if (> st 0)
      (bind w (GW|Get|{BOX}|Winner :self b))
      (if ({ISVALID} :Object w)
        (if (not {Sp('IsAlive', 'w')})
          (GW|Set|{BOX}|State :self b :State 0))
        (else
          (GW|Set|{BOX}|State :self b :State 0))))))
'''
    G['InvRoundCheck'] = f'''
(fn InvRoundCheck ()
  (bind r (GW|Get|BP_GW_GameState|RoundNumber :self (CallFunction|GetGS)))
  (if (not (Variables|Inv|GetStealOn))
    (Variables|Inv|SetStealOn true)
    (CallFunction|StealInit))
  (if (== r (Variables|Inv|GetInvRound))
    (return))
  (Variables|Inv|SetInvRound r)
  ; a new round: lustres back up (their EndPlay restores the instances), props back, the box moves
  (for f (Actor|GetAllActorsOfClass :ActorClass "{FALL}")
    (Actor|DestroyActor :self f))
  (for d (Actor|GetAllActorsOfClass :ActorClass "{DROP}")
    (Actor|DestroyActor :self d))
  (for s (Actor|GetAllActorsOfClass :ActorClass "{STEAL}")
    (if (GW|Get|{STEAL}|Stolen :self s)
      (GW|Set|{STEAL}|Stolen :self s :Stolen false)
      (GW|Call|{STEAL}|OnRep_Stolen :self s)))
  (for ps (CallFunction|GetGWPlayers)
    {SpS('HasBlade', 'false')}
    {SpS('InvSel', '0')})
  (CallFunction|BoxPlace))
'''
    prop_if = lambda name_var: '\n'.join(
        f'''      (if (Utilities|String|Contains :SearchIn {name_var} :Substring "{n}")
        (bind s{i} (Game|SpawnActorfromClass :Class "{STEAL}" :SpawnTransform (Math|Transform|MakeTransform :Location (Transformation|GetActorLocation :self a)) :CollisionHandlingOverride "AlwaysSpawn"))
        (GW|Set|{STEAL}|PropActor :self s{i} :PropActor a)
        (GW|Set|{STEAL}|Value :self s{i} :Value {v})
        (GW|Set|{STEAL}|Label :self s{i} :Label "{lab}")
        (Variables|Inv|SetLootN (+ (Variables|Inv|GetLootN) 1)))''' for i, (n, lab, v) in enumerate(PROPS))
    G['StealInit'] = f'''
(fn StealInit ()
  (Variables|Inv|SetLootN 0)
  (for a (Actor|GetAllActorswithTag :Tag "GW_Manual")
    (bind sm (Utilities|Casting|CastToStaticMeshActor a)
      (:then
        (bind mn (Utilities|GetDisplayName :Object (Class|StaticMeshComponent|GetStaticMesh :self (Class|StaticMeshActor|GetStaticMeshComponent :self sm))))
{prop_if('mn')})
      (:CastFailed)))
  {LOG('(cat "GW: stealable props " (Variables|Inv|GetLootN))')})
'''
    # ---- Q: the item falls where the player stands (a step ahead if nothing is in the way), the whole stack; E takes it back
    DROPC = cp('BP_GW_ItemDrop')
    adds_d = '\n'.join(f'  (if (== id {i})\n    {SpS(v, "(+ " + Sp(v, "PS") + " n)", "PS")})' for i, v in COUNTVAR.items()) + '\n' + '\n'.join(f'  (if (== id {i})\n    {SpS(v, "true", "PS")})' for i, v in BOOLVAR.items())
    G['DropItem'] = f'''
(fn DropItem (PS Ch Id)
  (bind n (GW|Call|BP_GW_PlayerState|CountOf :self PS :Id Id))
  (bind here (Transformation|GetActorLocation :self Ch))
  (bind ahead (+ here (* (Transformation|GetActorForwardVector :self Ch) 70.0)))
  (bind (wh wok) (Collision|LineTraceByChannel :Start here :End ahead :TraceChannel "Visibility" :bTraceComplex false :bIgnoreSelf true))
  (Variables|Inv|SetTmpSpot (select wok here ahead))
  (bind (h ok) (Collision|LineTraceByChannel :Start (Variables|Inv|GetTmpSpot) :End (- (Variables|Inv|GetTmpSpot) {mv(0, 0, 400)}) :TraceChannel "Visibility" :bTraceComplex false :bIgnoreSelf true))
  (bind (b1 i1 t1 d1 l1 imp n1 in1 p1 a1) (Collision|BreakHitResult h))
  (bind dr (Game|SpawnActorfromClass :Class "{DROPC}" :SpawnTransform (Math|Transform|MakeTransform :Location (select ok imp (- here {mv(0, 0, 90)})) :Rotation (Math|Rotator|MakeRotator :Yaw (Math|Random|RandomFloatinRange 0.0 360.0))) :CollisionHandlingOverride "AlwaysSpawn"))
  (GW|Set|{DROPC}|Count :self dr :Count n)
  (GW|Set|{DROPC}|ItemId :self dr :ItemId Id)
  (Networking|ForceNetUpdate :self dr)
  (CallFunction|InvClear :PS PS :Id Id)
  (CallFunction|SyncSword :PS PS)
  (CallFunction|WorldSound :Cat 41 :Loc (Transformation|GetActorLocation :self dr))
  {LOG('(cat "GW drop: item " Id " x" n " by " (PlayerState|GetPlayerName :self PS) " at " (Transformation|GetActorLocation :self dr))')})
'''
    G['TakeDrop'] = f'''
(fn TakeDrop (PS Ch D)
  ; in variables: a bind would read D again after it is destroyed
  (Variables|Inv|SetLootPick (GW|Get|{DROPC}|ItemId :self D))
  (Variables|Inv|SetLootN (GW|Get|{DROPC}|Count :self D))
  (bind id (Variables|Inv|GetLootPick))
  (bind n (Variables|Inv|GetLootN))
  ; the murder weapons stay on the floor for a detective (InvSync would take them away at once)
  (if (and (== {Sp('GWRole', 'PS')} 2) (or (or (== id 1) (or (== id 5) (or (== id 6) (== id 8)))) (or (== id 10) (or (== id 11) (== id 12)))))
    {NOTE('PS', '"Pas pour un détective, voyons."')}
    (return))
  (if (not (GW|Call|BP_GW_PlayerState|HasRoom :self PS :Id id))
    {NOTE('PS', '"Inventaire plein : jetez un objet (Q)."')}
    (return))
{adds_d}
  (Actor|DestroyActor :self D)
  (CallFunction|InvHand :PS PS :Id id)
  (CallFunction|SyncSword :PS PS)
  (CallFunction|WorldSound :Cat 41 :Loc (Transformation|GetActorLocation :self Ch))
  {LOG('(cat "GW drop: item " id " x" n " taken by " (PlayerState|GetPlayerName :self PS))')})
'''
    # ---- loot
    pool_g = [2, 3, 4, 5, 6, 9, 11, 1]
    pool_d = [2, 3, 4, 9]
    G['LootBody'] = f'''
(fn LootBody (PS Who Body)
  (if (GW|Get|BP_GW_Character|Looted :self Body)
    (return))
  (GW|Set|BP_GW_Character|Looted :self Body :Looted true)
  (Variables|Inv|SetLootN (Math|Random|RandomIntegerinRange 10 60))
  (bind money (Variables|Inv|GetLootN))
  (Variables|Inv|SetLootPick -1)
  (if (Math|Random|RandomBoolwithWeight 0.25)
    (bind det (== {Sp('GWRole', 'PS')} 2))
    (bind k (Math|Random|RandomIntegerinRange 0 {len(pool_g) - 1}))
    (Variables|Inv|SetLootPick (select det {sel('(% k ' + str(len(pool_d)) + ')', dict(enumerate(pool_d)), '2')} {sel('k', dict(enumerate(pool_g)), '2')})))
  (bind pick (Variables|Inv|GetLootPick))
  (if (and (> pick 0) (GW|Call|BP_GW_PlayerState|HasRoom :self PS :Id pick))
    (CallFunction|InvGive :PS PS :Id pick)
    (CallFunction|ShopPay :PS PS :Amount money :Note (cat "Corps fouillé : +" money " $ et " (CallFunction|ItemName :Id pick)))
    (else
      (CallFunction|ShopPay :PS PS :Amount money :Note (cat "Corps fouillé : +" money " $"))))
  {LOG('(cat "GW: body looted by " (PlayerState|GetPlayerName :self PS) " money=" money " item=" pick)')})
'''
    G['StealProp'] = f'''
(fn StealProp (PS S)
  (if (GW|Get|{STEAL}|Stolen :self S)
    (return))
  (GW|Set|{STEAL}|Stolen :self S :Stolen true)
  (GW|Call|{STEAL}|OnRep_Stolen :self S)
  (bind v (GW|Get|{STEAL}|Value :self S))
  (CallFunction|ShopPay :PS PS :Amount v :Note (cat "Volé : " (GW|Get|{STEAL}|Label :self S) " (+" v " $)"))
  {LOG('(cat "GW: prop stolen by " (PlayerState|GetPlayerName :self PS) " value " v)')})
'''
    # ---- mystery box
    box_pool_g = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
    G['BoxPlace'] = f'''
(fn BoxPlace ()
  ; a random guest spot of the manor, on the floor, not in the cloakroom nor on the stage; another one every round
  (bind pts (Actor|GetAllActorswithTag :Tag "GW_NPCSpawn"))
  (if (== (Utilities|Array|Length pts) 0)
    (return))
  (Variables|Inv|SetBoxOK false)
  (for t (range 16)
    (if (not (Variables|Inv|GetBoxOK))
      (bind (np nok) (AI|Navigation|GetRandomReachablePointinRadius :Origin (Transformation|GetActorLocation :self (Utilities|Array|Get(acopy) pts (Math|Random|RandomIntegerinRange 0 (- (Utilities|Array|Length pts) 1)))) :Radius 250.0))
      (if nok
        (Variables|Inv|SetTmpSpot np)
        (bind sp (Variables|Inv|GetTmpSpot))
        (bind inC (and (and (>= (.x sp) 2580.0) (<= (.x sp) 3420.0)) (and (>= (.y sp) -100.0) (<= (.y sp) 560.0))))
        (bind inS (and (and (>= (.x sp) 2500.0) (<= (.x sp) 3500.0)) (and (>= (.y sp) 3820.0) (<= (.y sp) 4380.0))))
        (if (not (or inC inS))
          (bind (fh fok) (Collision|LineTraceByChannel :Start (+ sp {mv(0, 0, 100)}) :End (- sp {mv(0, 0, 200)}) :TraceChannel "Visibility" :bTraceComplex true :bIgnoreSelf true))
          (bind (fb fi ft fd fl fImpact fn2 fin fp fa) (Collision|BreakHitResult fh))
          (if fok
            (Variables|Inv|SetTmpSpot fImpact)
            (Variables|Inv|SetBoxOK true))))))
  (if (not (Variables|Inv|GetBoxOK))
    (return))
  (if (not ({ISVALID} :Object (Variables|Inv|GetTheBox)))
    (Variables|Inv|SetTheBox (Game|SpawnActorfromClass :Class "{BOX}" :SpawnTransform (Math|Transform|MakeTransform :Location (Variables|Inv|GetTmpSpot)) :CollisionHandlingOverride "AlwaysSpawn")))
  (bind b (Variables|Inv|GetTheBox))
  (GW|Set|{BOX}|State :self b :State 0)
  (Transformation|SetActorLocation :self b :NewLocation (Variables|Inv|GetTmpSpot) :bSweep false :bTeleport true)
  (Networking|SetReplicateMovement :self b :bInReplicateMovement true)
  {LOG('(cat "GW: mystery box at " (Variables|Inv|GetTmpSpot))')})
'''
    G['BoxOpen'] = f'''
(fn BoxOpen (PS Who B)
  (if (!= (GW|Get|{BOX}|State :self B) 0)
    (return))
  (if (< {Sp('Money', 'PS')} {BOX_PRICE})
    {NOTE('PS', '"Il faut ' + str(BOX_PRICE) + ' $ pour ouvrir la boîte."')}
    (return))
  (CallFunction|ShopPay :PS PS :Amount {-BOX_PRICE} :Note "")
  (bind det (== {Sp('GWRole', 'PS')} 2))
  (bind k (Math|Random|RandomIntegerinRange 0 {len(box_pool_g) - 1}))
  (Variables|Inv|SetBoxPick (select det {sel('(% k 5)', dict(enumerate([2, 3, 4, 7, 9])), '2')} {sel('k', dict(enumerate(box_pool_g)), '2')}))
  (GW|Set|{BOX}|Result :self B :Result (Variables|Inv|GetBoxPick))
  (GW|Set|{BOX}|Winner :self B :Winner PS)
  (GW|Set|{BOX}|SpinAt :self B :SpinAt {NOW})
  (GW|Set|{BOX}|State :self B :State 1)
  (GW|Call|{BOX}|OnRep_State :self B)
  {LOG('(cat "GW: mystery box opened by " (PlayerState|GetPlayerName :self PS) " result " (Variables|Inv|GetBoxPick))')})
'''
    G['BoxTake'] = f'''
(fn BoxTake (PS B)
  (if (or (!= (GW|Get|{BOX}|State :self B) 2) (!= (GW|Get|{BOX}|Winner :self B) PS))
    (return))
  (bind id (GW|Get|{BOX}|Result :self B))
  (if (not (or (== id 7) (GW|Call|BP_GW_PlayerState|HasRoom :self PS :Id id)))
    {NOTE('PS', '"Inventaire plein : jetez un objet (Q), la boîte vous attend."')}
    (return))
  (CallFunction|InvGive :PS PS :Id id)
  (GW|Set|{BOX}|State :self B :State 0)
  (CallFunction|ShopPay :PS PS :Amount 0 :Note (cat "Boîte mystère : " (CallFunction|ItemName :Id id)))
  {LOG('(cat "GW: mystery box item taken: " id " by " (PlayerState|GetPlayerName :self PS))')})
'''
    # ---- kamikaze, blade
    G['KamikazeDown'] = f'''
(fn KamikazeDown (Victim Dir)
  ; killed before his time: no explosion, his bomb stays on the floor for whoever comes first (TryHold, kind 5)
  (bind here (Transformation|GetActorLocation :self Victim))
  (bind (h ok) (Collision|LineTraceByChannel :Start here :End (- here {mv(0, 0, 300)}) :TraceChannel "Visibility" :bTraceComplex false :bIgnoreSelf true))
  (bind (b1 i1 t1 d1 l1 imp n1 in1 p1 a1) (Collision|BreakHitResult h))
  (CallFunction|DeathCry :Victim Victim)
  (GW|Call|BP_GW_Character|Die :self Victim :Impulse (* Dir 700.0))
  (Game|SpawnActorfromClass :Class "{DROP}" :SpawnTransform (Math|Transform|MakeTransform :Location (select ok imp (- here {mv(0, 0, 90)}))) :CollisionHandlingOverride "AlwaysSpawn")
  (CallFunction|Announce :Text "Le kamikaze est à terre : sa bombe traîne encore…")
  {LOG('"GW: kamikaze down, bomb dropped"')})
'''
    # a player sits (the user, 2026-11-05): the same seats as the NPCs; the nearest free one within R, reserved until he stands (GM.SeatFree)
    G['SeatNear'] = f'''
(fn SeatNear (Loc R)
  (Variables|Inv|SetSeatBestD R)
  (Variables|Inv|SetSeatBestI -1)
  (bind now {NOW})
  (bind locs (Variables|GW|GetSitLocs))
  (for i (range (Utilities|Array|Length locs))
    (bind p (Utilities|Array|Get(acopy) locs i))
    (if (< (Math|Float|Absolute(Float) (- (.z p) (.z Loc))) 170.0)
      (bind d (Math|Vector|Distance2D(Vector) p Loc))
      (if (and (< d (Variables|Inv|GetSeatBestD)) (<= (Utilities|Array|Get(acopy) (Variables|GW|GetSitBusy) i) now))
        (Variables|Inv|SetSeatBestD d)
        (Variables|Inv|SetSeatBestI i))))
  (if (>= (Variables|Inv|GetSeatBestI) 0)
    (Utilities|Array|SetArrayElem :TargetArray (Variables|GW|GetSitBusy) :Index (Variables|Inv|GetSeatBestI) :Item (+ now 100000.0) :bSizeToFit false))
  (return (Variables|Inv|GetSeatBestI)))
'''
    G['BladeStrike'] = f'''
(fn BladeStrike (PS Who Dir)
  ; the hidden blade: an NPC guest within 1.6 m in front, dead without a sound; he only looks like he fainted (no panic)
  ; the user, 2026-11-05: a cooldown (GM.BladeCD, dev menu Réglages), checked here on the server, started by every strike, shown on the slot (WBP_Inventory, replicated BladeReadyAt / BladeCdLen)
  (if (< {NOW} {Sp('BladeReadyAt', 'PS')})
    {NOTE('PS', '(cat "Lame : encore " (Math|Float|Truncate (+ (- ' + Sp('BladeReadyAt', 'PS') + ' ' + NOW + ') 0.999)) " s.")')}
    {LOG('(cat "GW: blade refused, " (- ' + Sp('BladeReadyAt', 'PS') + ' ' + NOW + ') " s left")')}
    (return))
  {SpS('BladeCdLen', '(Variables|Inv|GetBladeCD)', 'PS')}
  {SpS('BladeReadyAt', f'(+ {NOW} (Variables|Inv|GetBladeCD))', 'PS')}
  (Variables|Inv|SetInvCh (Variables|GW|GetNoChar))
  (Variables|Shop|SetTmpV {mv(0, 0, 0)})
  (bind here (Transformation|GetActorLocation :self Who))
  (bind f2 (Math|Vector|Normalize (Math|Vector|MakeVector (.x Dir) (.y Dir) 0.0)))
  (for c (Actor|GetAllActorsOfClass :ActorClass {CHAR})
    (if (and (and (!= c Who) (not (GW|Get|BP_GW_Character|IsDead :self c))) (and (== (GW|Get|BP_GW_Character|Kind :self c) 0) (or (not (Pawn|IsPlayerControlled :self c)) (== (GW|Get|BP_GW_GameState|Phase :self (CallFunction|GetGS)) 2))))
      (bind cl (Transformation|GetActorLocation :self c))
      (if (and (< (Math|Vector|Distance2D(Vector) cl here) 160.0) (> (Math|Vector|DotProduct f2 (Math|Vector|Normalize (Math|Vector|MakeVector (- (.x cl) (.x here)) (- (.y cl) (.y here)) 0.0))) 0.5))
        (Variables|Inv|SetInvCh c))))
  (bind v (Variables|Inv|GetInvCh))
  (if (not ({ISVALID} :Object v))
    {LOG('"GW: blade reaches nobody"')}
    (return))
  ; no DeathCry, no LoudScream, no StartPanic: the point of the thing. A rival player falls just as quietly.
  (if (Pawn|IsPlayerControlled :self v)
    {LOG('(cat "GW: blade killed player " (CallFunction|NameOf :P v) " silently")')}
    (CallFunction|KillPlayer :Victim v :Impulse {mv(0, 0, -50)})
    (CallFunction|RivalDown :PS PS)
    (CallFunction|UpdateCounts)
    (return))
  (GW|Call|BP_GW_Character|Die :self v :Impulse {mv(0, 0, -50)})
  (Utilities|Array|Add :TargetArray (Variables|GW|GetPendingNPCRespawns) :NewItem (+ {NOW} (Variables|GW|GetNPCRespawnDelay)))
  (CallFunction|ShopPay :PS PS :Amount {BLADE_PAY} :Note "")
  {LOG('(cat "GW: blade killed NPC " (Utilities|GetDisplayName :Object v) " silently")')})
'''
    # ---- chandeliers
    G['ChandShot'] = f'''
(fn ChandShot (Shooter Start Dir End)
  ; a bullet passing within reach of a chandelier's centre, before it hit anything: it comes down
  (bind pts (Variables|Inv|GetChandPts))
  (bind maxA (+ (Math|Vector|DotProduct (- End Start) Dir) 60.0))
  (for i (range (Utilities|Array|Length pts))
    (bind p (Utilities|Array|Get(acopy) pts i))
    (bind along (Math|Vector|DotProduct (- p Start) Dir))
    (if (and (> along 0.0) (< along maxA))
      (bind near (+ Start (* Dir along)))
      (if (< (Math|Vector|Distance(Vector) near p) (Math|Float|Max(Float) 45.0 (* (Utilities|Array|Get(acopy) (Variables|Inv|GetChandRs) i) 0.8)))
        (CallFunction|ChandFallStart :I i :Shooter Shooter)
        (return)))))
'''
    G['ChandFallStart'] = f'''
(fn ChandFallStart (I Shooter)
  (for f (Actor|GetAllActorsOfClass :ActorClass "{FALL}")
    (if (== (GW|Get|{FALL}|Index :self f) I)
      (return)))
  (bind p (Utilities|Array|Get(acopy) (Variables|Inv|GetChandPts) I))
  (bind (h ok) (Collision|LineTraceByChannel :Start (- p {mv(0, 0, 30)}) :End (- p {mv(0, 0, 1200)}) :TraceChannel "Visibility" :bTraceComplex false :bIgnoreSelf true))
  (bind (b1 i1 t1 d1 l1 imp n1 in1 p1 a1) (Collision|BreakHitResult h))
  (bind f (Game|SpawnActorfromClass :Class "{FALL}" :SpawnTransform (Math|Transform|MakeTransform :Location p) :CollisionHandlingOverride "AlwaysSpawn"))
  (GW|Set|{FALL}|Index :self f :Index I)
  (GW|Set|{FALL}|FloorZ :self f :FloorZ (select ok (.z imp) (- (.z p) 300.0)))
  (GW|Set|{FALL}|Radius :self f :Radius (Utilities|Array|Get(acopy) (Variables|Inv|GetChandRs) I))
  (GW|Set|{FALL}|ShooterPS :self f :ShooterPS (CallFunction|PSOf :P Shooter))
  (GW|Set|{FALL}|Spot :self f :Spot p)
  {LOG('(cat "GW: chandelier " I " shot down by " (CallFunction|NameOf :P Shooter))')})
'''
    G['ChandTick'] = f'''
(fn ChandTick ()
  (for f (Actor|GetAllActorsOfClass :ActorClass "{FALL}")
    (if (not (GW|Get|{FALL}|Killed :self f))
      (if (and (GW|Get|{FALL}|Ready :self f) (>= (GW|Get|{FALL}|Age :self f) (GW|Call|{FALL}|FallTime :self f)))
        (GW|Set|{FALL}|Killed :self f :Killed true)
        (CallFunction|ChandBreak :F f)))))
'''
    G['ChandBreak'] = f'''
(fn ChandBreak (F)
  ; whoever stands under it dies; every NPC and rival under it pays the guest who shot it
  (bind sp (GW|Get|{FALL}|Spot :self F))
  (bind fz (GW|Get|{FALL}|FloorZ :self F))
  (bind ps (GW|Get|{FALL}|ShooterPS :self F))
  (bind r (+ (GW|Get|{FALL}|Radius :self F) 90.0))
  (bind floorPt (Math|Vector|MakeVector (.x sp) (.y sp) fz))
  (Variables|Inv|SetFallKills 0)
  (for c (Actor|GetAllActorsOfClass :ActorClass {CHAR})
    (bind cl (Transformation|GetActorLocation :self c))
    (if (and (and (< (Math|Vector|Distance2D(Vector) cl floorPt) r) (< (- (.z cl) fz) 260.0)) (not (GW|Get|BP_GW_Character|IsDead :self c)))
      (bind kind (GW|Get|BP_GW_Character|Kind :self c))
      (bind imp {mv(0, 0, -600)})
      (if (== kind 2)
        (CallFunction|KamikazeDown :Victim c :Dir {mv(0, 0, -1)})
        (elif (== kind 3)
          (CallFunction|RobotHurt :Victim c :Amount 1000.0 :Dir {mv(0, 0, -1)})
          (elif (> kind 0)
            (GW|Call|BP_GW_Character|Die :self c :Impulse imp)
          (elif (Pawn|IsPlayerControlled :self c)
            ; a rival under it pays the guest who shot it, not himself
            (if (!= (CallFunction|PSOf :P c) ps)
              (Variables|Inv|SetFallKills (+ (Variables|Inv|GetFallKills) 1)))
            (CallFunction|HurtCharacter :Victim c :Amount 1000.0 :Impulse imp :Cause "a été écrasé par un lustre")
            (else
              (CallFunction|HurtCharacter :Victim c :Amount 1000.0 :Impulse imp :Cause "")
              (Variables|Inv|SetFallKills (+ (Variables|Inv|GetFallKills) 1))
              (CallFunction|LoudScream :Victim c))))))))
  (bind kills (Variables|Inv|GetFallKills))
  (CallFunction|StartPanicCause :Loc sp :Dur 15.0 :Cause 3)
  (CallFunction|Announce :Text (select (> kills 0) (cat "Un lustre s'écrase : " kills (select (> kills 1) " victimes !" " victime !")) "Un lustre s'écrase !"))
  (if (and ({ISVALID} :Object ps) (> kills 0))
    (if (!= {Sp('GWRole')} 2)
      (CallFunction|ShopPay :PS ps :Amount (* kills 100) :Note (cat "+" (* kills 100) " $ : le lustre a fait " kills (select (> kills 1) " victimes" " victime")))))
  (CallFunction|UpdateCounts)
  {LOG('(cat "GW: chandelier broke, kills=" kills)')})
'''
    # ---- speed boost
    G['GiveBoost'] = f'''
(fn GiveBoost (Ch Mul Dur)
  (GW|Set|BP_GW_Character|BoostMul :self Ch :BoostMul Mul)
  (GW|Set|BP_GW_Character|BoostUntil :self Ch :BoostUntil (+ (GameState|GetServerWorldTimeSeconds :self (Game|GetGameState)) Dur))
  (GW|Call|BP_GW_Character|BoostApply :self Ch))
'''
    G['BoostTick'] = f'''
(fn BoostTick ()
  (for ps (CallFunction|GetGWPlayers)
    (Variables|Inv|SetInvCh (CallFunction|CharOfPS :PS ps))
    (bind c (Variables|Inv|GetInvCh))
    (if ({ISVALID} :Object c)
      (GW|Call|BP_GW_Character|BoostApply :self c))))
'''
    # ---- rewritten bodies of the older scripts
    G['ShopCleanup'] = f'''
(fn ShopCleanup ()
''' + '\n'.join(f'  (for a (Actor|GetAllActorsOfClass :ActorClass "{c}")\n    (Actor|DestroyActor :self a))' for c in (TRAP, BOMB, SMOKE, GAS, CRACKER, DROPC)) + f'''
  {LOG('"GW: shop cleanup (traps, bombs, smoke)"')})
'''
    PRICES_J, HINTS = {i[0]: i[4] for i in shop_items.ITEMS}, {i[0]: '"' + i[6] + '"' for i in shop_items.ITEMS}
    G['ShopBuy'] = f'''
(fn ShopBuy (PS Id Kind At)
  ; Kind: who sells (0 barman, 1 junkie, 2 waiter); the junkie has his own prices and the only firecrackers
  ; the flashlight is not sold any more (no row in the shop: this is for a stale client)
  (if (or (or (or (< Id 1) (> Id {shop_items.MAX_ID})) (== Id 3)) (and (>= Id 11) (<= Id 13)))
    (return))
  (bind cat3 (select (== Kind 1) 63 (select (== Kind 2) 62 15)))
  (if (and (== Id 9) (!= Kind 1))
    {NOTE('PS', '"Des pétards ? Demandez au junkie, dans les toilettes…"')}
    (return))
  ; detectives shop too, but no murder weapons
  (if (and (== {Sp('GWRole', 'PS')} 2) (or (== Id 14) (or (== Id 1) (or (== Id 5) (or (== Id 6) (or (== Id 8) (== Id 10)))))))
    {NOTE('PS', '"Pas pour un détective, voyons."')}
    (return))
  (bind price (CallFunction|ItemPrice :Id Id :Kind Kind))
  (bind name (CallFunction|ItemName :Id Id))
  (if (and (== Id 8) {Sp('HasSwapGun', 'PS')})
    {NOTE('PS', '"Vous avez déjà le pistolet d' + "'" + 'échange."')}
    (return))
  (if (and (== Id 10) {Sp('HasBlade', 'PS')})
    {NOTE('PS', '"Vous avez déjà une lame secrète."')}
    (return))
  (bind room (or (or (== Id 7) (GW|Call|BP_GW_PlayerState|HasRoom :self PS :Id Id)) (Utilities|HasLaunchOption :OptionToCheck "GWShopTest")))
  (if (not room)
    {NOTE('PS', '"Inventaire plein (4 objets) : utilisez ou jetez-en un (Q)."')}
    (return))
  (if (< {Sp('Money', 'PS')} price)
    {NOTE('PS', '(cat "Pas assez d' + "'" + 'argent pour : " name " (" price " $).")')}
    (if (> (Math|Vector|VectorLength At) 1.0)
      (CallFunction|StaffSay :Cat cat3 :Ctx 5 :Loc At))
    (return))
  (CallFunction|ShopPay :PS PS :Amount (- 0 price) :Note "")
  (CallFunction|InvGive :PS PS :Id Id)
  {SpA('ShopBuys', 1, 'PS')}
  {NOTE('PS', '(cat "Acheté : " name " (" ' + sel('Id', HINTS, '""') + ' ")")')}
  (if (> (Math|Vector|VectorLength At) 1.0)
    (CallFunction|StaffSay :Cat cat3 :Ctx (select (or (== Id 1) (or (== Id 5) (or (== Id 6) (== Id 10)))) 6 4) :Loc At))
  {LOG('(cat "GW: sold " name " for " price " $ (vendor " Kind ")")')})
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
  (if (or (<= {Sp('Ammo')} 0) (!= (GW|Get|BP_GW_Character|HeldItem :self Shooter) 1))
    (return))
  (if (not (CallFunction|CanShoot :Shooter Shooter))
    {NOTE('ps', '"Le fusil ne sert que pendant la chasse."')}
    (return))
  (if (< {NOW} {Sp('NextGuestFire')})
    (return))
  {SpS('NextGuestFire', f'(+ {NOW} 0.8)')}
  {SpA('Ammo', -1)}
  ; the old rifle is hopeless from the hip: 4 degrees off, under a degree aimed (the drifting sight is the rest of the challenge)
  (bind aimed (GW|Get|BP_GW_Character|Aiming :self Shooter))
  (bind d2 (Math|Random|RandomUnitVectorinConeinDegrees :ConeDir Dir :ConeHalfAngleInDegrees (select aimed 0.6 4.0)))
  (Utilities|Array|Clear (Variables|Shop|GetTraceIgnore))
  (Utilities|Array|Add :TargetArray (Variables|Shop|GetTraceIgnore) :NewItem Shooter)
  (bind traceEnd (+ Start (* d2 8000.0)))
  (bind (hit ok) (Collision|LineTraceByProfile :Start Start :End traceEnd :ProfileName "BlockAll" :bTraceComplex false :ActorsToIgnore (Variables|Shop|GetTraceIgnore) :bIgnoreSelf true))
  (bind (bBlock bInit hTime hDist hLoc hImpact hNormal hImpNormal hPhys hActor) (Collision|BreakHitResult hit))
  (bind endP (select ok hImpact traceEnd))
  (GW|Set|BP_GW_Character|ShotEnd :self Shooter :ShotEnd endP)
  (GW|Set|BP_GW_Character|ShotTime :self Shooter :ShotTime {NOW})
  (GW|Set|BP_GW_Character|ShotCounter :self Shooter :ShotCounter (+ (GW|Get|BP_GW_Character|ShotCounter :self Shooter) 1))
  {LOG('(cat "GW: guest shot by " (CallFunction|NameOf :P Shooter) " hit " (Utilities|GetDisplayName :Object hActor) " ammo left " ' + Sp('Ammo') + ')')}
  (CallFunction|ChandShot :Shooter Shooter :Start Start :Dir d2 :End endP)
  (if ok
    (bind v (Utilities|Casting|CastToBP_GW_Character hActor)
      (:then (CallFunction|GuestHit :Shooter Shooter :Victim v :Dir d2))
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
    (CallFunction|RobotHurt :Victim Victim :Amount 100.0 :Dir Dir)
    (return))
  (if (== kind 2)
    (CallFunction|KamikazeDown :Victim Victim :Dir Dir)
    (return))
  (if (== kind 1)
    (CallFunction|DeathCry :Victim Victim)
    (GW|Call|BP_GW_Character|Die :self Victim :Impulse (* Dir 700.0))
    (CallFunction|Announce :Text (cat sname " a abattu un bandit !"))
    (return))
  (if (Pawn|IsPlayerControlled :self Victim)
    (bind vname (CallFunction|NameOf :P Victim))
    ; nobody is told who fired
    (CallFunction|Announce :Text (cat vname " a été abattu !"))
    (CallFunction|RivalDown :PS (CallFunction|PSOf :P Shooter))
    (CallFunction|StartPanicCause :Loc (Transformation|GetActorLocation :self Victim) :Dur 15.0 :Cause 1)
    (CallFunction|DeathCry :Victim Victim)
    (CallFunction|KillPlayer :Victim Victim :Impulse (* Dir 700.0))
    (CallFunction|UpdateCounts)
    (CallFunction|CheckWin)
    (return))
  (CallFunction|HurtCharacter :Victim Victim :Amount 1000.0 :Impulse (* Dir 700.0) :Cause "")
  (CallFunction|RewardNPCKill :Killer Shooter :Victim Victim)
  (CallFunction|StartPanicCause :Loc (Transformation|GetActorLocation :self Victim) :Dur 15.0 :Cause 1))
'''
    G['GunFor'] = f'''
(fn GunFor (PS)
  ; the long rifle or the swap pistol shows in the hand of a living guest who has it selected (Model: the item id; another id = another actor)
  (bind g {Sp('GunActor', 'PS')})
  (Variables|Shop|SetGunPawn (CallFunction|CharOfPS :PS PS))
  (bind ch (Variables|Shop|GetGunPawn))
  (Variables|Shop|SetWantGun false)
  (if ({ISVALID} :Object ch)
    (Variables|Shop|SetWantGun (and (or (== (GW|Get|BP_GW_Character|HeldItem :self ch) 1) (== (GW|Get|BP_GW_Character|HeldItem :self ch) 8)) (== {Sp('GWRole', 'PS')} 1))))
  (if (Variables|Shop|GetWantGun)
    (if (not ({ISVALID} :Object g))
      (bind ng (Game|SpawnActorfromClass :Class "{GUN}" :SpawnTransform (Math|Transform|MakeTransform :Location (Transformation|GetActorLocation :self (Variables|Shop|GetGunPawn))) :CollisionHandlingOverride "AlwaysSpawn"))
      (Actor|SetOwner :self ng :NewOwner (Variables|Shop|GetGunPawn))
      (GW|Set|{GUN}|Model :self ng :Model (GW|Get|BP_GW_Character|HeldItem :self (Variables|Shop|GetGunPawn)))
      (GW|Set|{GUN}|Holder :self ng :Holder (Variables|Shop|GetGunPawn))
      {SpS('GunActor', 'ng', 'PS')}
      (return))
    (if (or (!= (GW|Get|{GUN}|Holder :self g) (Variables|Shop|GetGunPawn)) (!= (GW|Get|{GUN}|Model :self g) (GW|Get|BP_GW_Character|HeldItem :self (Variables|Shop|GetGunPawn))))
      (Actor|DestroyActor :self g)
      {SpS('GunActor', '(Variables|Shop|GetNoGun)', 'PS')})
    (return))
  (if ({ISVALID} :Object g)
    (Actor|DestroyActor :self g)
    {SpS('GunActor', '(Variables|Shop|GetNoGun)', 'PS')}))
'''
    G['PlaceTrap'] = f'''
(fn PlaceTrap (PS Ch)
  ; in a doorway: on the lintel, the whole opening is the trigger; anywhere else: on the floor just ahead, a 1.1 m trigger
  (bind (top ax hw ok) (CallFunction|FindDoor :Loc (Transformation|GetActorLocation :self Ch)))
  (Variables|Shop|SetTmpV top)
  (if (not ok)
    (CallFunction|ThrowPoint :Ch Ch :Yaw (.yaw (Pawn|GetControlRotation :self (Pawn|GetController :self Ch)))))
  (bind spot (Variables|Shop|GetTmpV))
  (for t (Actor|GetAllActorsOfClass :ActorClass "{TRAP}")
    (if (< (Math|Vector|Distance(Vector) (Transformation|GetActorLocation :self t) spot) 60.0)
      {NOTE('PS', '"Il y a déjà un piège ici."')}
      (return)))
  {SpA('Traps', -1, 'PS')}
  (bind tr (Game|SpawnActorfromClass :Class "{TRAP}" :SpawnTransform (Math|Transform|MakeTransform :Location (+ spot (select ok {mv(0, 0, 0)} {mv(0, 0, 8)})) :Rotation (Math|Rotator|MakeRotator :Roll 0.0 :Pitch 0.0 :Yaw (select ax 90.0 0.0))) :CollisionHandlingOverride "AlwaysSpawn"))
  (GW|Set|{TRAP}|OwnerPS :self tr :OwnerPS PS)
  (GW|Set|{TRAP}|AxisX :self tr :AxisX ax)
  (GW|Set|{TRAP}|HalfW :self tr :HalfW hw)
  (GW|Set|{TRAP}|FloorMode :self tr :FloorMode (not ok))
  (GW|Set|{TRAP}|ArmAt :self tr :ArmAt (+ {NOW} 3.0))
  {NOTE('PS', '"Piège posé : il attend le prochain qui passe."')}
  {LOG('(cat "GW: trap set by " (PlayerState|GetPlayerName :self PS) " at " spot " floor=" (not ok))')})
'''
    G['TrapTick'] = f'''
(fn TrapTick ()
  ; every player and every event character sets it off (detective, guest player, bandit, kamikaze, robot); an NPC guest only with GM.TrapNPC (dev menu)
  ; this runs at 4 Hz: the door line is tested over the way walked since the last tick (a sprinter on gas crosses 1.8 m in 0.18 s and slipped through)
  (for t (Actor|GetAllActorsOfClass :ActorClass "{TRAP}")
    (if (>= {NOW} (GW|Get|{TRAP}|ArmAt :self t))
      (bind tl (Transformation|GetActorLocation :self t))
      (bind ax (GW|Get|{TRAP}|AxisX :self t))
      (bind fl (GW|Get|{TRAP}|FloorMode :self t))
      (for c (Actor|GetAllActorsOfClass :ActorClass {CHAR})
        (if (and (or (or (Pawn|IsPlayerControlled :self c) (!= (GW|Get|BP_GW_Character|Kind :self c) 0)) (Variables|Inv|GetTrapNPC)) (not (GW|Get|BP_GW_Character|IsDead :self c)))
          (bind cl (Transformation|GetActorLocation :self c))
          (bind vel (Transformation|GetVelocity :self c))
          (bind across0 (select ax (- (.x cl) (.x tl)) (- (.y cl) (.y tl))))
          (bind across1 (- across0 (* 0.26 (select ax (.x vel) (.y vel)))))
          (bind along (Math|Float|Absolute(Float) (select ax (- (.y cl) (.y tl)) (- (.x cl) (.x tl)))))
          (bind doorHit (and (and (and (< (Math|Float|Min(Float) across0 across1) 90.0) (> (Math|Float|Max(Float) across0 across1) -90.0)) (< along (+ (GW|Get|{TRAP}|HalfW :self t) 15.0))) (< (.z cl) (.z tl))))
          (bind floorHit (and (< (Math|Vector|Distance2D(Vector) cl tl) 110.0) (< (Math|Float|Absolute(Float) (- (.z cl) (.z tl))) 170.0)))
          (if (select fl floorHit doorHit)
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
  (bind kind (GW|Get|BP_GW_Character|Kind :self Victim))
  (bind vname (select (> kind 0) "un intrus" (CallFunction|NameOf :P Victim)))
  {LOG('(cat "GW: trap fired on " vname " at " tl)')}
  (CallFunction|Announce :Text (cat "Un piège explose sur " vname " !"))
  (if (== kind 2)
    (CallFunction|KamikazeDown :Victim Victim :Dir {mv(0, 0, 1)})
    (elif (== kind 3)
      (CallFunction|RobotHurt :Victim Victim :Amount 150.0 :Dir {mv(0, 0, 1)})
      (elif (> kind 0)
        (GW|Call|BP_GW_Character|Die :self Victim :Impulse {mv(0, 0, 350)})
      (else
        ; read now: the victim may be dead (and no longer controlled) after the damage
        (Variables|Inv|SetTrapRival (and (Pawn|IsPlayerControlled :self Victim) (!= (CallFunction|PSOf :P Victim) (Variables|Shop|GetBlastOwner))))
        (if (Variables|Inv|GetTrapRival)
          (CallFunction|ShopPay :PS (Variables|Shop|GetBlastOwner) :Amount 50 :Note "+50 $ : votre piège a explosé sur un rival !"))
        ; the user, 2026-11-05: "the trap doesn't do any damage". A player feels it: thrown up, a cry (and the HUD: red vignette, -X, thud); the owner is told; an NPC dies (GM.TrapNPC)
        (bind pl (Pawn|IsPlayerControlled :self Victim))
        (if pl
          (CallFunction|Say :Ch Victim :Cat 1)
          (GW|Call|/Script/Engine.Character|LaunchCharacter :self Victim :LaunchVelocity {mv(0, 0, 480)} :bXYOverride false :bZOverride true)
          (else
            (CallFunction|ShopPay :PS (Variables|Shop|GetBlastOwner) :Amount 100 :Note "+100 $ : votre piège a tué un invité.")))
        (CallFunction|HurtCharacter :Victim Victim :Amount (Variables|Inv|GetTrapDmg) :Impulse {mv(0, 0, 350)} :Cause "a été achevé par un piège")
        (if (and (Variables|Inv|GetTrapRival) (GW|Get|BP_GW_Character|IsDead :self Victim))
          (CallFunction|RivalDown :PS (Variables|Shop|GetBlastOwner)))))))
  {LOG('(cat "GW: trap victim health=" (GW|Get|BP_GW_Character|Health :self Victim) " dead=" (GW|Get|BP_GW_Character|IsDead :self Victim))')}
  (CallFunction|StartPanicCause :Loc tl :Dur 8.0 :Cause 3))
'''
    REWARD = '(CallFunction|RewardNPCKill :Killer Gunner :Victim Victim)'
    G['TurretHit'] = f'''
(fn TurretHit (Gunner Victim Dir)
  (if (GW|Get|BP_GW_Character|IsDead :self Victim)
    (return))
  (bind kind (GW|Get|BP_GW_Character|Kind :self Victim))
  (if (== kind 3)
    (CallFunction|RobotHurt :Victim Victim :Amount 25.0 :Dir Dir)
    (return))
  (if (== kind 4)
    {LOG('(cat "GW: turret killed zombie " (Utilities|GetDisplayName :Object Victim))')}
    (CallFunction|ZombieDown :Victim Victim :Impulse (* Dir 900.0))
    (return))
  (if (== kind 2)
    (CallFunction|KamikazeDown :Victim Victim :Dir Dir)
    (return))
  (if (== kind 1)
    (CallFunction|DeathCry :Victim Victim)
    (GW|Call|BP_GW_Character|Die :self Victim :Impulse (* Dir 900.0))
    (CallFunction|Announce :Text "Un bandit est tombé sous la mitrailleuse !")
    (return))
  (if (Pawn|IsPlayerControlled :self Victim)
    (if (== (GW|Get|BP_GW_GameState|Phase :self (CallFunction|GetGS)) 2)
      {LOG('(cat "GW: turret killed player " (CallFunction|NameOf :P Victim))')}
      (CallFunction|Announce :Text (cat (CallFunction|NameOf :P Victim) " a été abattu par la mitrailleuse !"))
      (CallFunction|RivalDown :PS (CallFunction|PSOf :P Gunner))
      (CallFunction|DeathCry :Victim Victim)
      (CallFunction|KillPlayer :Victim Victim :Impulse (* Dir 900.0))
      (CallFunction|UpdateCounts))
    (return))
  {LOG('(cat "GW: turret kill NPC " (Utilities|GetDisplayName :Object Victim) " by " (Utilities|GetDisplayName :Object Gunner))')}
  (CallFunction|DeathCry :Victim Victim)
  (GW|Call|BP_GW_Character|Die :self Victim :Impulse (* Dir 900.0))
  (Utilities|Array|Add :TargetArray (Variables|GW|GetPendingNPCRespawns) :NewItem (+ {NOW} (Variables|GW|GetNPCRespawnDelay)))
  {REWARD})
'''
    G['PullAlarm'] = f'''
(fn PullAlarm (P Who)
  ; user, 2026-11-03: repeatable, station to station; the guest who pulls it runs faster for a moment (20 s before this box works again)
  (if (GW|Get|{PK}|Taken :self P)
    (return))
  (GW|Set|{PK}|Taken :self P :Taken true)
  (GW|Set|{PK}|BackAt :self P :BackAt (+ {NOW} 20.0))
  (GW|Set|{PK}|RingUntil :self P :RingUntil (+ {NOW} 10.0))
  (CallFunction|StartPanicCause :Loc (Transformation|GetActorLocation :self P) :Dur 10.0 :Cause 2)
  (CallFunction|SayNearPlayers :Cat 67 :PerPlayer 1 :Delay 2.5 :Spread 1.5)
  (bind c (Utilities|Casting|CastToBP_GW_Character Who)
    (:then
      (if (not (GW|Get|BP_GW_Character|IsSeeker :self c))
        (CallFunction|GiveBoost :Ch c :Mul 1.45 :Dur 12.0))
      {LOG('(cat "GW: fire alarm pulled by " (CallFunction|NameOf :P Who))')})
    (:CastFailed)))
'''
    G['TakePickup'] = f'''
(fn TakePickup (P Who)
  (bind ps (CallFunction|PSOf :P Who))
  (if (or (not ({ISVALID} :Object ps)) (GW|Get|{PK}|Taken :self P))
    (return))
  (bind k (GW|Get|{PK}|Kind :self P))
  (GW|Set|{PK}|Taken :self P :Taken true)
  (GW|Set|{PK}|BackAt :self P :BackAt (+ {NOW} (select (== k 0) 45.0 60.0)))
  (Variables|GW|SetStamp (+ (Variables|GW|GetStamp) 1))
  (if (== k 0)
    {SpA('Balls', 1)}
    (CallFunction|WorldSound :Cat 41 :Loc (Transformation|GetActorLocation :self P))
    (CallFunction|QueueSay :Ch (CallFunction|NearestNPC :Loc (Transformation|GetActorLocation :self P) :MaxD 1200.0) :Cat 71 :Delay 0.9)
    (CallFunction|InvHand :PS ps :Id 11)
    {LOG('(cat "GW: pickup ball by " (CallFunction|NameOf :P Who) " balls=" ' + Sp('Balls') + ')')}
    (else
      {SpS('HasSword', 'true')}
      (CallFunction|WorldSound :Cat 42 :Loc (Transformation|GetActorLocation :self P))
      (CallFunction|QueueSay :Ch (CallFunction|NearestNPC :Loc (Transformation|GetActorLocation :self P) :MaxD 1200.0) :Cat 70 :Delay 0.8)
      (CallFunction|InvHand :PS ps :Id 12)
      {LOG('(cat "GW: pickup sword by " (CallFunction|NameOf :P Who))')}
      (CallFunction|SyncSword :PS ps))))
'''
    G['SyncSword'] = f'''
(fn SyncSword (PS)
  (bind cur (GW|Get|BP_GW_PlayerState|SwordActor :self PS))
  (bind c (Utilities|Casting|CastToBP_GW_Character (PlayerState|GetPawn :self PS))
    (:then
      ; in the hand only while selected in the inventory
      (bind want (and (GW|Get|BP_GW_PlayerState|HasSword :self PS) (== (GW|Get|BP_GW_Character|HeldItem :self c) 12)))
      (if (and want ({ISVALID} :Object cur))
        (if (== (GW|Get|{HS}|Holder :self cur) c)
          (return)))
      (if ({ISVALID} :Object cur)
        (Actor|DestroyActor :self cur))
      (if want
        (bind h (Game|SpawnActorfromClass :Class "{HS}" :SpawnTransform (Math|Transform|MakeTransform :Location (Transformation|GetActorLocation :self c)) :CollisionHandlingOverride "AlwaysSpawn"))
        (GW|Set|BP_GW_PlayerState|SwordActor :self PS :SwordActor h)
        (GW|Set|{HS}|Holder :self h :Holder c)
        {LOG('(cat "GW: sword in the hand of " (PlayerState|GetPlayerName :self PS))')}))
    (:CastFailed
      (if ({ISVALID} :Object cur)
        (Actor|DestroyActor :self cur)))))
'''
    # s12: kept in step with s12_gamemode.py's text except the kamikaze (no explosion when shot) and the robot
    gs_get = lambda v: f'(GW|Get|BP_GW_GameState|{v} :self gs)'
    ps_get = lambda v, o: f'(GW|Get|BP_GW_PlayerState|{v} :self {o})'
    ps_set = lambda v, val, o: f'(GW|Set|BP_GW_PlayerState|{v} :self {o} :{v} {val})'
    G['OnCharacterShot'] = f'''
(fn OnCharacterShot (Shooter Victim Dir)
  ; anyone may shoot a zombie, a zombified detective too (s40_events2.py)
  (if (== (GW|Get|BP_GW_Character|Kind :self Victim) 4)
    (if (not (GW|Get|BP_GW_Character|IsDead :self Victim))
      (Variables|GW|SetGunContext true)
      (CallFunction|ZombieDown :Victim Victim :Impulse (* Dir 700.0)))
    (return))
  (if (or (GW|Get|BP_GW_Character|IsDead :self Victim) (GW|Get|BP_GW_Character|IsSeeker :self Victim))
    (return))
  (Variables|GW|SetGunContext true)
  (bind gs (CallFunction|GetGS))
  (bind sps (CallFunction|PSOf :P Shooter))
  (bind sname (CallFunction|NameOf :P Shooter))
  (bind kind (GW|Get|BP_GW_Character|Kind :self Victim))
  (if (== kind 3)
    (CallFunction|RobotHurt :Victim Victim :Amount 100.0 :Dir Dir)
    (return))
  (if (== kind 2)
    (CallFunction|KamikazeDown :Victim Victim :Dir Dir)
    (return))
  (if (== kind 1)
    (CallFunction|DeathCry :Victim Victim)
    (GW|Call|BP_GW_Character|Die :self Victim :Impulse (* Dir 700.0))
    (CallFunction|Announce :Text (cat sname " a abattu un bandit !"))
    (return))
  (if (Pawn|IsPlayerControlled :self Victim)
    {LOG('(cat "GW: hider killed: " (CallFunction|NameOf :P Victim))')}
    (CallFunction|Announce :Text (cat sname " a démasqué " (CallFunction|NameOf :P Victim) " !"))
    (CallFunction|DeathCry :Victim Victim)
    (CallFunction|KillPlayer :Victim Victim :Impulse (* Dir 700.0))
    (if ({ISVALID} :Object sps)
      {ps_set('Kills', '(+ ' + ps_get('Kills', 'sps') + ' 1)', 'sps')}
      {ps_set('GWScore', '(+ ' + ps_get('GWScore', 'sps') + ' 3)', 'sps')})
    (else
      (CallFunction|DeathCry :Victim Victim)
      (GW|Call|BP_GW_Character|Die :self Victim :Impulse (* Dir 700.0))
      (CallFunction|StartPanic :Loc (Transformation|GetActorLocation :self Victim) :Dur 15.0)
      (Utilities|Array|Add :TargetArray (Variables|GW|GetPendingNPCRespawns) :NewItem (+ {NOW} (Variables|GW|GetNPCRespawnDelay)))
      (if {gs_get('TestRound')}
        (CallFunction|Announce :Text (cat sname " a abattu un innocent (manche de test : pas de pénalité)"))
        (return))
      (GW|Set|BP_GW_Character|Health :self Shooter :Health (- (GW|Get|BP_GW_Character|Health :self Shooter) (Variables|GW|GetInnocentPenalty)))
      {LOG('(cat "GW: innocent shot, seeker health=" (GW|Get|BP_GW_Character|Health :self Shooter))')}
      (if ({ISVALID} :Object sps)
        {ps_set('Mistakes', '(+ ' + ps_get('Mistakes', 'sps') + ' 1)', 'sps')}
        {ps_set('GWScore', '(- ' + ps_get('GWScore', 'sps') + ' 1)', 'sps')})
      (if (<= (GW|Get|BP_GW_Character|Health :self Shooter) 0.0)
        (CallFunction|Announce :Text (cat sname " a abattu trop d'innocents et est éliminé !"))
        {LOG('(cat "GW: detective died of innocents: " sname)')}
        (CallFunction|KillPlayer :Victim Shooter :Impulse (* Dir -300.0))
        (else
          (CallFunction|Announce :Text (cat sname " a abattu un innocent ! (-" (Math|Float|Round (Variables|GW|GetInnocentPenalty)) " PV)"))))))
  (CallFunction|UpdateCounts))
'''
    for n, code in G.items():
        wr(gm, n, code)
    finish(gm)
