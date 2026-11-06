"""Scripted steps inside an editor -game run, no Blueprint test code to compile.
Run: -ExecCmds="py J:\\...\\Tools\\qa\\py_harness.py"  with -GWHarness=<plan name>; plans are in PLANS below. Steps are (delay seconds, action):
a string is a console command on the host's PlayerController (exec functions included), a callable gets (world, pc).
Log lines start with 'GWH:'. Ends the process at the end of the plan."""
import unreal

NPCC = '/Game/GW/Blueprints/BP_GW_NPCController.BP_GW_NPCController_C'
CHAR = '/Game/GW/Blueprints/BP_GW_Character.BP_GW_Character_C'


def log(*a):
    unreal.log('GWH: ' + ' '.join(str(x) for x in a))


def count(tag):
    def f(world, pc):
        ctl = unreal.GameplayStatics.get_all_actors_of_class(world, unreal.load_class(None, NPCC))
        orphans = [c for c in ctl if c.get_controlled_pawn() is None]
        chars = unreal.GameplayStatics.get_all_actors_of_class(world, unreal.load_class(None, CHAR))
        dead = [c for c in chars if c.get_editor_property('IsDead')]
        zc = unreal.GameplayStatics.get_all_actors_of_class(world, unreal.load_class(None, '/Game/GW/Blueprints/BP_GW_ZombieController.BP_GW_ZombieController_C'))
        log(tag, 'zombie controllers', len(zc), 'no pawn', len([c for c in zc if c.get_controlled_pawn() is None]))
        log(tag, 'chars', len(chars), 'dead', len(dead), 'npc controllers', len(ctl), 'orphans', len(orphans), 'of', sorted({c.get_name() for c in orphans})[:4])
    return f


def view(pitch, yaw):
    def f(world, pc):
        pc.set_control_rotation(unreal.Rotator(roll=0, pitch=pitch, yaw=yaw))
    return f


def fp(world, pc):
    pc.call_method('SetViewMode', args=(True,))


def pick(i):
    def f(world, pc):
        pc.call_method('InvPick', args=(i,))
    return f


def actor_view(cls, offset=(150, 0, 60), pitch=None, tz=20):
    """Teleports the host in front of the first actor of a class, at `offset` in the actor's frame, looking at it."""
    def f(world, pc):
        all_ = unreal.GameplayStatics.get_all_actors_of_class(world, unreal.load_class(None, cls))
        if not all_:
            log('no actor of', cls)
            return
        a = all_[0]
        tgt = a.get_actor_location()
        p = unreal.MathLibrary.transform_location(a.get_actor_transform(), unreal.Vector(*offset))
        ch = pc.get_controlled_pawn()
        ch.set_actor_location(unreal.Vector(p.x, p.y, p.z), False, True)
        look = unreal.MathLibrary.find_look_at_rotation(unreal.Vector(p.x, p.y, p.z + 66), tgt + unreal.Vector(0, 0, tz))
        pc.set_control_rotation(look if pitch is None else unreal.Rotator(roll=0, pitch=pitch, yaw=look.yaw))
        log('at', a.get_name(), 'loc', tgt)
    return f


SHOT = 'Shot showui'
SHOP = '/Game/GW/Blueprints/Shop'
TURRET = '/Game/GW/Blueprints/Turret/BP_GW_Turret.BP_GW_Turret_C'


def label(t):
    def f(world, pc):
        log('SHOT', t)
    return f


def ads(on):
    def f(world, pc):
        pc.set_editor_property('VTestAds', on)
    return f


def tp_view(fp_on):
    def f(world, pc):
        pc.call_method('SetViewMode', args=(fp_on,))
    return f


def box_state(v):
    def f(world, pc):
        for b in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.load_class(None, SHOP + '/BP_GW_MysteryBox.BP_GW_MysteryBox_C')):
            b.set_editor_property('State', v)
    return f


def breaker(on):
    def f(world, pc):
        for b in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.load_class(None, '/Game/GW/Blueprints/BP_GW_Breaker.BP_GW_Breaker_C')):
            b.set_editor_property('Thrown', on)
            b.call_method('OnRep_Thrown')
    return f


def gm_use(fn):
    def f(world, pc):
        gm = unreal.GameplayStatics.get_game_mode(world)
        ch = pc.get_controlled_pawn()
        ps = pc.get_editor_property('player_state')
        args = {'ThrowSmoke': (ch, 0.0), 'UseGas': (ch,), 'DropBomb': (ps, ch), 'PlaceTrap': (ps, ch)}[fn]
        gm.call_method(fn, args=args)
    return f


def follow_shop(name, offset):
    return actor_view(f'{SHOP}/{name}.{name}_C', offset)


def turret_yaw(y):
    def f(world, pc):
        for t in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.load_class(None, TURRET)):
            t.set_editor_property('AimYaw', y)
            t.set_editor_property('VisYaw', y)
    return f


BOX = SHOP + '/BP_GW_MysteryBox.BP_GW_MysteryBox_C'
BREAKER = '/Game/GW/Blueprints/BP_GW_Breaker.BP_GW_Breaker_C'


def try_hold(world, pc):
    log('TryHold', pc.call_method('TryHold'))


def try_turret(world, pc):
    log('TryTurret', pc.call_method('TryTurret'))


def call(fn):
    def f(world, pc):
        try:
            log(fn, pc.call_method(fn))
        except Exception as e:
            log(fn, 'failed', e)
    return f


def fire(world, pc):
    pc.call_method('RequestFire')


def yaw_add(d):
    def f(world, pc):
        r = pc.get_control_rotation()
        pc.set_control_rotation(unreal.Rotator(roll=0, pitch=r.pitch, yaw=r.yaw + d))
    return f


def dump(cls):
    def f(world, pc):
        for a in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.load_class(None, cls))[:1]:
            log('dump', a.get_name(), 'loc', a.get_actor_location(), 'rot', a.get_actor_rotation())
            for c in a.get_components_by_class(unreal.SceneComponent):
                if c.get_name() in ('Receiver', 'MuzzlePoint', 'Swivel', 'Cradle', 'CamPoint'):
                    log('  ', c.get_name(), 'world', c.get_world_location(), 'rot', c.get_world_rotation())
    return f


START = {}


def snap(world, pc):
    START['names'] = {c.get_name() for c in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.load_class(None, NPCC))}
    log('snap', len(START['names']))


def compare(world, pc):
    ctl = unreal.GameplayStatics.get_all_actors_of_class(world, unreal.load_class(None, NPCC))
    orphans = [c for c in ctl if c.get_controlled_pawn() is None]
    now = {c.get_name() for c in ctl}
    log('new since snap', len(now - START['names']), 'gone', len(START['names'] - now), 'orphans in snap', len([c for c in orphans if c.get_name() in START['names']]))
    if orphans:
        c = orphans[0]
        c.k2_destroy_actor()
        log('destroyed one orphan by python, being destroyed', c.is_actor_being_destroyed())


def zexp(world, pc):
    gm = unreal.GameplayStatics.get_game_mode(world)
    chars = unreal.GameplayStatics.get_all_actors_of_class(world, unreal.load_class(None, CHAR))
    npcs = [c for c in chars if c.get_controller() and 'NPCController' in c.get_controller().get_name()]
    ch = npcs[0]
    old = ch.get_controller()
    log('before', ch.get_name(), old.get_name(), 'role', old.get_local_role())
    gm.call_method('Zombify', args=(ch,))
    log('after zombify: pawn controller', ch.get_controller().get_name(), 'old valid', unreal.SystemLibrary.is_valid(old), 'being destroyed', old.is_actor_being_destroyed(), 'old pawn', old.get_controlled_pawn())
    START['old'] = old


def zexp2(world, pc):
    old = START['old']
    log('later: old valid', unreal.SystemLibrary.is_valid(old), 'being destroyed', old.is_actor_being_destroyed(), 'name', old.get_name())
    if unreal.SystemLibrary.is_valid(old):
        r = old.call_method('K2_DestroyActor')
        log('python destroy ret', r, 'being destroyed', old.is_actor_being_destroyed())


def zexp3(world, pc):
    chars = unreal.GameplayStatics.get_all_actors_of_class(world, unreal.load_class(None, CHAR))
    npcs = [c for c in chars if c.get_controller() and 'NPCController' in c.get_controller().get_name()]
    a, b, c_, d = [n.get_controller() for n in npcs[:4]]
    START['a'] = (a, b, c_, d)
    a.call_method('K2_DestroyActor')
    log('A possessed, destroy: being destroyed', a.is_actor_being_destroyed(), 'valid', unreal.SystemLibrary.is_valid(a))
    b.call_method('UnPossess')
    b.call_method('K2_DestroyActor')
    log('B unpossess+destroy: being destroyed', b.is_actor_being_destroyed(), 'valid', unreal.SystemLibrary.is_valid(b))
    c_.call_method('UnPossess')
    c_.set_life_span(0.2)
    log('C unpossess+lifespan', c_.get_life_span())
    d.call_method('K2_DestroyActor')
    log('D', d.get_class().get_name(), d.get_world().get_name())


def zexp4(world, pc):
    a, b, c_, d = START['a']
    log('later valid: A', unreal.SystemLibrary.is_valid(a), 'B', unreal.SystemLibrary.is_valid(b), 'C', unreal.SystemLibrary.is_valid(c_), 'D', unreal.SystemLibrary.is_valid(d))


def mesh_view(mesh_sub, offset=(190, 0, 10), tz=20):
    """Host in front of the first BP_GW_Character wearing a skeletal mesh whose name contains mesh_sub."""
    def f(world, pc):
        for c in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.load_class(None, CHAR)):
            m = c.get_editor_property('mesh').get_skinned_asset()
            if m and mesh_sub in m.get_name():
                p = unreal.MathLibrary.transform_location(c.get_actor_transform(), unreal.Vector(*offset))
                pc.get_controlled_pawn().set_actor_location(p, False, False)
                pc.set_control_rotation(unreal.MathLibrary.find_look_at_rotation(p + unreal.Vector(0, 0, 66), c.get_actor_location() + unreal.Vector(0, 0, tz)))
                log('at', c.get_name(), m.get_name())
                return
        log('no character wearing', mesh_sub)
    return f


def cast_census(world, pc):
    names = {}
    for c in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.load_class(None, CHAR)):
        m = c.get_editor_property('mesh').get_skinned_asset()
        k = m.get_name() if m else 'None'
        names[k] = names.get(k, 0) + 1
    log('census', sorted(names.items()))


# ---------------------------------------------------------------- the user's feedback of 2026-11-05
ITEMDROP = SHOP + '/BP_GW_ItemDrop.BP_GW_ItemDrop_C'
GHOST = SHOP + '/BP_GW_TrapGhost.BP_GW_TrapGhost_C'
BEAM = '/Game/GW/Blueprints/BP_GW_Beam.BP_GW_Beam_C'
GUEST = SHOP + '/BP_GW_GuestGun.BP_GW_GuestGun_C'
SHRINKC = SHOP + '/BP_GW_Shrink.BP_GW_Shrink_C'


def actors(world, cls):
    return unreal.GameplayStatics.get_all_actors_of_class(world, unreal.load_class(None, cls))


def fb_gm(world, pc):
    gm = unreal.GameplayStatics.get_game_mode(world)
    log('defaults: EventEvery', gm.get_editor_property('EventEvery'), 'AutoEvents', gm.get_editor_property('AutoEvents'), 'ZombieLife', gm.get_editor_property('ZombieLife'), 'ZombieBite', gm.get_editor_property('ZombieBite'), 'RobotHP', gm.get_editor_property('RobotHP'), 'RobotDmg', gm.get_editor_property('RobotDmg'), 'GasScale', gm.get_editor_property('GasScale'))


def zstat(world, pc):
    chars = actors(world, CHAR)
    z = [c for c in chars if c.get_editor_property('Kind') == 4]
    gs = unreal.GameplayStatics.get_game_state(world)
    log('zombies alive', len([c for c in z if not c.get_editor_property('IsDead')]), 'dead', len([c for c in z if c.get_editor_property('IsDead')]), 'event', gs.get_editor_property('EventId'), 't', round(unreal.GameplayStatics.get_time_seconds(world), 1))


def bring_guests(n, r=200.0):
    """A few living guests around the first zombie: contamination needs someone to bite."""
    def f(world, pc):
        chars = actors(world, CHAR)
        z = [c for c in chars if c.get_editor_property('Kind') == 4 and not c.get_editor_property('IsDead') and not c.is_player_controlled()]
        if not z:
            log('no zombie to bring guests to')
            return
        l = z[0].get_actor_location()
        g = [c for c in chars if c.get_editor_property('Kind') == 0 and not c.get_editor_property('IsDead') and not c.is_player_controlled()][:n]
        for i, c in enumerate(g):
            c.set_actor_location(unreal.Vector(l.x + 40 + 10 * i, l.y + 20 - 10 * i, l.z), False, True)
        log('brought', len(g), 'guests onto', z[0].get_name())
    return f


def robot_of(world):
    r = [c for c in actors(world, CHAR) if c.get_editor_property('Kind') == 3 and not c.get_editor_property('IsDead')]
    return r[0] if r else None


def rstat(world, pc):
    r = robot_of(world)
    me = pc.get_controlled_pawn()
    beams = actors(world, BEAM)
    log('robot', None if r is None else round(r.get_editor_property('Health')), 'my hp', me and round(me.get_editor_property('Health')), 'dead', me and me.get_editor_property('IsDead'),
        'beams', [(round(b.get_editor_property('Width'), 2), [round(v) for v in (b.get_editor_property('BeamEnd').x, b.get_editor_property('BeamEnd').y)]) for b in beams], 'on', unreal.GameplayStatics.get_game_state(world).get_editor_property('RobotOn'))


def beam_rays(world, pc):
    """From the middle of the hall, in four directions: where the laser's line ends."""
    gm = unreal.GameplayStatics.get_game_mode(world)
    me = pc.get_controlled_pawn()
    f = unreal.Vector(2845, 1485, 200)
    for d in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0)):
        e = gm.call_method('RobotBeamEnd', args=(f, unreal.Vector(*d), me))
        log('laser ray', d, 'ends at', round((e - f).length()), 'cm', e)


def robot_stand(world, pc):
    """Puts the robot in the ballroom, the player 6 m ahead in the line of sight (same room)."""
    r = robot_of(world)
    me = pc.get_controlled_pawn()
    if not r:
        return log('no robot')
    r.set_actor_location(unreal.Vector(2500, 3000, 170), False, True)
    r.set_actor_rotation(unreal.Rotator(roll=0, pitch=0, yaw=0), True)
    me.set_actor_location(unreal.Vector(3100, 3000, 100), False, True)
    log('robot at', r.get_actor_location(), 'me at', me.get_actor_location())


def robot_wall(world, pc):
    """The player behind a wall straight ahead of the robot: hall (y 1485) towards the ballroom beyond the north wall. It must not see him."""
    r = robot_of(world)
    me = pc.get_controlled_pawn()
    if not r:
        return log('no robot')
    r.set_actor_location(unreal.Vector(2400, 2100, 170), False, True)
    r.set_actor_rotation(unreal.Rotator(roll=0, pitch=0, yaw=90), True)
    me.set_actor_location(unreal.Vector(2400, 3000, 100), False, True)
    gm = unreal.GameplayStatics.get_game_mode(world)
    e = gm.call_method('RobotBeamEnd', args=(unreal.Vector(2400, 2100, 280), unreal.Vector(0, 1, -0.2).normal(), r))
    log('wall test: robot', r.get_actor_location(), 'player', me.get_actor_location(), 'line ends', e)


def dodge(world, pc):
    me = pc.get_controlled_pawn()
    l = me.get_actor_location()
    me.set_actor_location(unreal.Vector(l.x, l.y + 300, l.z), False, True)
    log('dodged to', me.get_actor_location())


RC = {'spot': 0}


def rc(do_dodge):
    """One step of a duel: until the charging beam shows, the player keeps standing 5 m ahead of the robot; on the beam's third tick he steps aside if do_dodge."""
    def f(world, pc):
        beams = [b for b in actors(world, BEAM) if b.get_editor_property('Width') < 2.0]
        me = pc.get_controlled_pawn()
        if me is None or me.get_editor_property('IsDead'):
            log('duel: I am dead'); rstat(world, pc)
            return
        if beams:
            RC['spot'] += 1
            log('duel: charging, tick', RC['spot'], 'width', round(beams[0].get_editor_property('Width'), 2), 'end', beams[0].get_editor_property('BeamEnd'), 'hp', me.get_editor_property('Health'))
            if do_dodge and RC['spot'] == 3:
                dodge(world, pc)
        else:
            if RC['spot']:
                log('duel: no charge any more, hp', me.get_editor_property('Health'), 'shot beams', len(actors(world, BEAM)))
            RC['spot'] = 0
            r = robot_of(world)
            if r and not do_dodge:           # in the middle of the hall, towards the ballroom: 5 m ahead is never behind a wall
                r.set_actor_location(unreal.Vector(2845, 1485, r.get_actor_location().z), False, True)
                r.set_actor_rotation(unreal.Rotator(roll=0, pitch=0, yaw=90), True)
            unreal.SystemLibrary.execute_console_command(world, 'GWDevRobotFace', pc)
    return f


def near_wall(world, pc):
    """The robot 50 cm from the hall's west wall (x = 2290), facing it, the player right behind that wall: it must not see him."""
    r = robot_of(world)
    me = pc.get_controlled_pawn()
    if not r:
        return log('no robot')
    r.get_controller().stop_movement()
    r.set_actor_location(unreal.Vector(2340, 1485, r.get_actor_location().z), False, True)
    r.set_actor_rotation(unreal.Rotator(roll=0, pitch=0, yaw=180), True)
    me.set_actor_location(unreal.Vector(1950, 1485, r.get_actor_location().z), False, True)
    log('near wall: beams', len(actors(world, BEAM)), 'hp', me.get_editor_property('Health'))


def gmcall(fn, *a):
    def f(world, pc):
        gm = unreal.GameplayStatics.get_game_mode(world)
        r = robot_of(world)
        if not r:
            return log('no robot for', fn)
        me = pc.get_controlled_pawn()
        gm.call_method(fn, args=tuple((me if x == 'ME' else r if x == 'R' else unreal.Vector(1, 0, 0) if x == 'D' else x) for x in a))
    return f


def inv(world, pc):
    ps = pc.get_editor_property('player_state')
    if ps is None:
        return log('no ps')
    ch = pc.get_controlled_pawn()
    log('inv slots', [ps.get_editor_property(f'Slot{i}') for i in range(4)], 'sel', ps.get_editor_property('InvSel'), 'held', ch and ch.get_editor_property('HeldItem'), 'money', ps.get_editor_property('Money'), 'lamp', ps.get_editor_property('HasLamp'))


def drops(world, pc):
    ds = actors(world, ITEMDROP)
    out = []
    for d in ds:
        m = [c for c in d.get_components_by_class(unreal.StaticMeshComponent)][0]
        out.append((d.get_editor_property('ItemId'), d.get_editor_property('Count'), m.static_mesh.get_name() if m.static_mesh else None, [round(v) for v in (d.get_actor_location().x, d.get_actor_location().y, d.get_actor_location().z)]))
    log('drops', out)


def gun_stat(world, pc):
    out = []
    for g in actors(world, GUEST):
        m = [c for c in g.get_components_by_class(unreal.StaticMeshComponent)][0]
        h = g.get_editor_property('Holder')
        out.append((g.get_editor_property('Model'), m.static_mesh.get_name() if m.static_mesh else None, h and h.get_name(), m.get_attach_socket_name() if False else g.get_attach_parent_socket_name() if hasattr(g, 'get_attach_parent_socket_name') else ''))
    ch = pc.get_controlled_pawn()
    fp = ch and ch.get_editor_property('FPGun')
    log('guns', out, 'FPGun visible', fp and fp.is_visible(), 'mesh', fp and fp.static_mesh and fp.static_mesh.get_name(), 'viewfp', ch and ch.get_editor_property('ViewFP'))


def ghost_stat(world, pc):
    g = actors(world, GHOST)
    log('ghosts', [(x.get_editor_property('hidden') if False else x.is_temporarily_hidden_in_editor() if False else x.get_actor_enable_collision() if False else None, [round(v) for v in (x.get_actor_location().x, x.get_actor_location().y, x.get_actor_location().z)]) for x in g], 'ghost var', pc.get_editor_property('GhostOn'))


def at_door(world, pc):
    p = pc.get_editor_property('DoorPts')[0]
    log('door 0', p)
    unreal.SystemLibrary.execute_console_command(world, f'GWDevTeleport {p.x} {p.y} 130', pc)


def scale_stat(world, pc):
    ch = pc.get_controlled_pawn()
    log('my scale', ch.get_actor_scale3d().x, 'z', round(ch.get_actor_location().z), 'walk', ch.get_editor_property('WalkSpeed'), 'shrinks', [s.get_editor_property('ToScale') for s in actors(world, SHRINKC)])


def post_stat(world, pc):
    w = pc.get_editor_property('InvWid')
    now = unreal.GameplayStatics.get_real_time_seconds(world)
    log('post-it reads', pc.get_editor_property('PostReads'), 'code', pc.get_editor_property('KnownCode'), 'open', w and round(w.get_editor_property('PostUntil') - now, 1), 'group visible', w and str(w.get_editor_property('PostGroup').get_visibility()))


def pcall(fn, *a):
    def f(world, pc):
        log(fn, a, '->', pc.call_method(fn, args=a) if a else pc.call_method(fn))
    return f


def srvcmd(c):
    """A dev command through the client's ServerExec path."""
    def f(world, pc):
        log('srv', c, 'role', pc.get_local_role() if hasattr(pc, 'get_local_role') else '?', pc.get_name())
        unreal.SystemLibrary.execute_console_command(world, 'ServerExec ' + c, pc)
    return f


def view_ch(world, pc):
    pass


FB_ZOMB = [(10, 'GWDevQuickTest 1'), (1, 'GWDevAutoEvents 0'), (0.5, fb_gm), (1, 'GWDevTeleport 500 500 130'), (0.5, 'GWDevEvent 6'), (0.5, zstat), (2.5, bring_guests(4))] + [(1.0, zstat)] * 5 + [(0.1, bring_guests(3))] + [(1.0, zstat)] * 24 + [(1, count('after zombies'))]
FB_ROBOT = [(10, 'GWDevQuickTest 1'), (1, 'GWDevAutoEvents 0'), (1, 'GWDevRole 1'), (2, pcall('DevEnsureAlive')), (0.5, beam_rays), (0.5, 'GWDevEvent 5'), (2, rstat)] + [(0.1, near_wall), (0.15, near_wall), (0.15, near_wall)] * 8 + [(0.2, rstat)] + [
    (0.25, rc(True))] * 40 + [(0.1, rstat), (0.3, 'GWDevHeal'), (0.1, rstat)] + [(0.25, rc(False))] * 40 + [(0.3, rstat), (0.5, pcall('DevEnsureAlive')), (0.5, 'GWDevHeal'), (0.5, rstat), (1, rstat),
    (0.3, gmcall('WeaponHit', 'ME', 'R', 'D', 1)), (0.2, rstat), (0.3, gmcall('TurretHit', 'ME', 'R', 'D')), (0.2, rstat), (0.3, gmcall('OnCharacterShot', 'ME', 'R', 'D')), (0.2, rstat), (0.3, gmcall('GuestHit', 'ME', 'R', 'D')), (0.2, rstat), (0.3, 'GWDevRobotHit'), (2, rstat), (1, count('after robot'))]
FB_ITEMS = [(10, 'GWDevQuickTest 1'), (1, 'GWDevAutoEvents 0'), (1, 'GWDevRole 1'), (1, 'GWDevMoney 1000'), (0.5, inv),
    (0.5, pcall('ShopBuy', 3)), (0.5, inv)] + sum([[(0.3, f'GWDevGiveItem {i}'), (0.3, inv), (0.3, 'GWInvDrop'), (0.3, drops), (0.1, inv)] for i in (1, 2, 3, 4, 5, 6, 8, 9, 10, 11, 12)], []) + [
    (0.5, inv)] + [(0.4, pcall('TryDrop')), (0.4, inv), (0.1, drops)] * 4 + [(0.3, 'GWInvDrop'), (0.3, inv)] * 2 + [(0.5, drops),
    (0.5, 'GWDevGiveItem 8'), (1, gun_stat), (0.5, fp), (1.5, gun_stat), (0.5, tp_view(False)), (1, 'GWDevGiveItem 1'), (1, gun_stat), (0.3, 'GWInvDrop'), (0.3, 'GWInvDrop'), (1, gun_stat),
    (0.5, 'GWDevGiveItem 5'), (0.5, ghost_stat), (0.5, at_door), (1, ghost_stat), (0.3, pick(1)), (0.5, inv), (0.5, ghost_stat), (0.3, pick(0)), (0.5, inv), (0.5, ghost_stat), (0.5, 'GWDevTeleport 2925 3565 130'), (1, ghost_stat),
    (0.5, 'GWDevGiveItem 4'), (0.5, inv), (0.3, gm_use('UseGas')), (1.5, scale_stat), (1, scale_stat),
    (0.5, 'GWDevPostIt'), (0.5, post_stat), (0.3, pcall('TryPickup')), (0.5, post_stat), (0.5, pcall('PostClose')), (0.3, post_stat), (0.3, pcall('TryPickup')), (0.5, post_stat), (0.5, pcall('PostClose')), (0.3, pcall('TryPickup')), (0.5, post_stat), (10.5, post_stat), (0.3, pcall('TryPickup')), (0.5, post_stat), (0.5, 'GWDevTeleport 2925 3565 130'), (1, post_stat)]
RC2 = {}


def qt_two(world, pc):
    n = len(unreal.GameplayStatics.get_game_state(world).get_editor_property('player_array'))
    if n >= 2 and not RC2:
        RC2['go'] = 1
        log('two players: quick test')
        for c in ('GWDevAutoEvents 0', 'GWDevQuickTest 1'):
            unreal.SystemLibrary.execute_console_command(world, c, pc)


def cpc(fn, *a):
    """The client's controller on the server, running the server side of its commands (the python console path from a client does not reach the server)."""
    def f(world, pc):
        c = [x for x in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.PlayerController) if x != pc]
        if not c:
            return log('no client controller')
        log('client pc', fn, a)
        c[0].call_method(fn, args=a) if a else c[0].call_method(fn)
    return f


def stat_all(world, pc):
    inv(world, pc); drops(world, pc); gun_stat(world, pc); ghost_stat(world, pc); post_stat(world, pc)


FB_NET_HOST = [(2, qt_two)] * 12 + [(1, cpc('GWDevRole', 1)), (2, cpc('GWDevGiveItem', 8)), (3, stat_all), (0.5, cpc('GWInvDrop')), (3, stat_all), (0.5, cpc('GWTakeDrop')), (3, stat_all), (0.5, cpc('GWInvDrop')), (2, cpc('GWDevGiveItem', 5)), (2, stat_all), (1, cpc('GWDevTeleport', 1000.0, 1800.0, 130.0)), (3, stat_all), (1, cpc('GWDevTeleport', 2925.0, 3565.0, 130.0)), (3, stat_all), (1, cpc('GWDevPostIt')), (1, cpc('GWPickup')), (3, stat_all), (6, stat_all), (0.5, cpc('GWPickup')), (3, stat_all)]
FB_NET_CLIENT = [(40, inv)] + [(2, stat_all)] * 28
FB_SHOTS = [(10, 'GWDevQuickTest 1'), (1, 'GWDevAutoEvents 0'), (1, 'GWDevRole 1'), (1, 'GWDevHeal'),
    (0.5, 'GWDevGiveItem 8'), (1, tp_view(False)), (0.5, view(-10, 90)), (2, label('swap third person')), (0.2, SHOT), (1, tp_view(True)), (2, label('swap first person')), (0.2, SHOT), (1, tp_view(False)),
    (0.5, 'GWDevGiveItem 1'), (0.5, 'GWDevGiveItem 4'), (0.5, 'GWDevGiveItem 5'), (1, label('slots with icons')), (0.2, SHOT),
    (0.5, at_door), (0.5, view(-30, 0)), (2, ghost_stat), (0.2, label('ghost at door')), (0.2, SHOT), (0.5, view(-45, 90)), (1, label('ghost at door 2')), (0.2, SHOT),
    (0.5, 'GWDevTeleport 2925 3565 130'), (0.5, 'GWInvDrop'), (0.5, view(-50, 0)), (1, label('dropped item')), (0.2, SHOT),
    (0.5, 'GWDevPostIt'), (1, pcall('TryPickup')), (1.5, label('note open')), (0.2, SHOT), (0.5, pcall('PostClose')), (1, label('note closed')), (0.2, SHOT),
    (0.5, 'GWDevHeal'), (0.5, 'GWDevEvent 5'), (2, robot_stand), (0.1, view(0, 180)), (1, label('robot charge beam')), (0.1, SHOT), (0.6, label('robot charge beam 2')), (0.1, SHOT), (0.8, label('robot shot')), (0.1, SHOT),
    (0.5, 'GWDevShopHere 0'), (2, label('shop icons')), (0.2, SHOT), (0.5, 'GWDevShopHere 0')]

def front_view(world, pc):
    """Third person, the camera in front of my character: he faces it."""
    ch = pc.get_controlled_pawn()
    pc.set_control_rotation(unreal.Rotator(roll=0, pitch=-5, yaw=90))
    ch.set_actor_rotation(unreal.Rotator(roll=0, pitch=0, yaw=270), True)


def look_door(world, pc):
    p = pc.get_editor_property('DoorPts')[0]
    unreal.SystemLibrary.execute_console_command(world, f'GWDevTeleport {p.x} {p.y - 90} 130', pc)
    pc.set_control_rotation(unreal.Rotator(roll=0, pitch=38, yaw=90))


def beam_shot(world, pc):
    """During a duel: a shot of the charging beam, once per width stage, and of the fired one."""
    beams = actors(world, BEAM)
    if beams:
        w = beams[0].get_editor_property('Width')
        key = 'shot' if w >= 2.0 else ('a' if w < 0.8 else 'b')
        if key not in RC2:
            RC2[key] = 1
            log('SHOT beam', key, 'width', round(w, 2))
            unreal.SystemLibrary.execute_console_command(world, 'Shot showui', pc)


def duel_view(world, pc):
    me = pc.get_controlled_pawn()
    r = robot_of(world)
    if me and r:
        pc.set_control_rotation(unreal.Rotator(roll=0, pitch=-3, yaw=unreal.MathLibrary.find_look_at_rotation(me.get_actor_location(), r.get_actor_location()).yaw - 25))


FB_SHOTS2 = [(10, 'GWDevQuickTest 1'), (1, 'GWDevAutoEvents 0'), (1, 'GWDevRole 1'), (1, 'GWDevHeal'), (0.5, 'GWDevTeleport 2925 3100 130'),
    (0.5, 'GWDevGiveItem 8'), (1, tp_view(False)), (0.5, front_view), (2, label('swap third person front')), (0.2, SHOT), (0.3, front_view), (0.5, 'GWDevGiveItem 4'), (0.5, 'GWDevGiveItem 1'), (1, label('slots')), (0.2, SHOT),
    (0.5, 'GWInvDrop'), (0.5, 'GWDevGiveItem 5'), (1, fp), (0.5, look_door), (1.5, label('ghost FP')), (0.2, SHOT), (0.5, view(10, 90)), (0.8, label('ghost FP 2')), (0.2, SHOT),
    (0.5, 'GWDevTeleport 2925 3100 130'), (0.3, view(-75, 0)), (0.5, 'GWInvDrop'), (1, label('dropped trap FP')), (0.2, SHOT), (0.5, tp_view(False)),
    (0.3, pcall('OpenShopHere', 0)), (2, label('shop')), (0.2, SHOT), (0.3, pcall('CloseShop')),
    (0.5, 'GWDevHeal'), (0.5, 'GWDevEvent 5'), (2, duel_view)] + [(0.25, rc(False)), (0.01, duel_view), (0.01, beam_shot)] * 60 + [(1, rstat)]

def rcfast(world, pc):
    r = robot_of(world)
    beams = [b for b in actors(world, BEAM)]
    if r and not beams:
        r.get_controller().stop_movement()
        r.set_actor_location(unreal.Vector(2845, 1000, r.get_actor_location().z), False, True)
        r.set_actor_rotation(unreal.Rotator(roll=0, pitch=0, yaw=90), True)
        me = pc.get_controlled_pawn()
        me.set_actor_location(unreal.Vector(2845, 1650, r.get_actor_location().z), False, True)
        pc.set_control_rotation(unreal.Rotator(roll=0, pitch=-12, yaw=-140))
    beam_shot(world, pc)


FB_BEAM = [(10, 'GWDevQuickTest 1'), (1, 'GWDevAutoEvents 0'), (1, 'GWDevRole 1'), (1, 'GWDevHeal'), (1, tp_view(False)), (0.5, 'GWDevEvent 5')] + [(0.05, rcfast)] * 500 + [(0.5, rstat)]

# ---------------------------------------------------------------- the user's feedback of 2026-11-05 (2): trap, waiters' animation, kamikaze, blade
TRAPC = SHOP + '/BP_GW_Trap.BP_GW_Trap_C'
SMALLB = SHOP + '/BP_GW_SmallBlast.BP_GW_SmallBlast_C'
F6 = {}


def trap_stat(world, pc):
    log('traps', [(round(t.get_actor_location().x), round(t.get_actor_location().y), round(t.get_actor_location().z), 'ax', t.get_editor_property('AxisX'), 'hw', round(t.get_editor_property('HalfW')), 'floor', t.get_editor_property('FloorMode')) for t in actors(world, TRAPC)], 'blasts', len(actors(world, SMALLB)))


def hp(c):
    return None if c is None else (round(c.get_editor_property('Health')), c.get_editor_property('IsDead'))


def me_stat(world, pc):
    log('me hp/dead', hp(pc.get_controlled_pawn()), 'money', pc.get_editor_property('player_state') and pc.get_editor_property('player_state').get_editor_property('Money'))


def door_trap(world, pc):
    """The host stands in door 0 and sets a trap there (server path of the T key / click)."""
    p = pc.get_editor_property('DoorPts')[0]
    ch = pc.get_controlled_pawn()
    ch.set_actor_location(unreal.Vector(p.x, p.y, ch.get_actor_location().z if False else 130), False, True)
    log('door', p, 'me', ch.get_actor_location())


def sweep_target(who):
    def f(world, pc):
        chars = actors(world, CHAR)
        if who == 'host':
            c = pc.get_controlled_pawn()
        elif who == 'client':
            c = [x for x in chars if x.is_player_controlled() and x != pc.get_controlled_pawn()]
            c = c[0] if c else None
        else:
            t = actors(world, TRAPC)
            tl = t[0].get_actor_location() if t else pc.get_controlled_pawn().get_actor_location()
            g = [x for x in chars if x.get_editor_property('Kind') == 0 and not x.is_player_controlled() and not x.get_editor_property('IsDead')]
            g.sort(key=lambda x: (x.get_actor_location() - tl).length())
            c = g[0] if g else None
        F6['c'] = c
        F6['k'] = 0
        F6['done'] = False
        t = actors(world, TRAPC)
        F6['t'] = t[0] if t else None
        log('sweep', who, c and c.get_name(), 'hp', hp(c), 'trap', F6['t'] and F6['t'].get_actor_location())
    return f


def sweep_step(speed):
    """The chosen pawn crosses the trap's door line at `speed` cm/s (the time between two steps is the harness's real frame time)."""
    def f(world, pc):
        c, t = F6.get('c'), F6.get('t')
        if c is None or not unreal.SystemLibrary.is_valid(c):
            return
        if t is None or not unreal.SystemLibrary.is_valid(t):
            if not F6['done']:
                F6['done'] = True
                log('trap gone (fired) with pawn hp', hp(c), 'blasts', len(actors(world, SMALLB)))
            return
        ax = t.get_editor_property('AxisX')
        tl = t.get_actor_location()
        F6['k'] = F6.get('k', 0) + 1
        d = -260.0 + F6['k'] * speed * 0.05
        z = c.get_actor_location().z
        c.set_actor_location(unreal.Vector(tl.x + d, tl.y, z) if ax else unreal.Vector(tl.x, tl.y + d, z), False, True)
    return f


def anim_watch(world, pc):
    """Who animates: a foot and a hand relative to the capsule, between two reads, with the ABP's own variables."""
    vendors = []
    for n in ('BP_GW_Barman', 'BP_GW_Junkie', 'BP_GW_Waiter', 'BP_GW_Waiter2'):
        vendors += actors(world, f'{SHOP}/{n}.{n}_C')
    chars = actors(world, CHAR)
    npcs = [c for c in chars if not c.is_player_controlled()][:2]
    others = [c for c in chars if c.is_player_controlled() and c != pc.get_controlled_pawn()]
    for c in vendors + npcs + others:
        m = c.get_editor_property('mesh')
        m.set_editor_property('visibility_based_anim_tick_option', unreal.VisibilityBasedAnimTickOption.ALWAYS_TICK_POSE_AND_REFRESH_BONES)
        loc = c.get_actor_location()
        rel = lambda s: unreal.MathLibrary.inverse_transform_location(c.get_actor_transform(), m.get_socket_location(s))
        fo, ha = rel('foot_r'), rel('hand_r')
        prev = F6.setdefault('anim', {}).get(c.get_name())
        F6['anim'][c.get_name()] = (fo, ha)
        dfoot = round((fo - prev[0]).length(), 1) if prev else None
        dhand = round((ha - prev[1]).length(), 1) if prev else None
        ai = m.get_anim_instance()
        vs = {}
        for v in ('GroundSpeed', 'ShouldMove', 'IsFalling'):
            try:
                x = ai.get_editor_property(v)
                vs[v] = round(x, 1) if isinstance(x, float) else x
            except Exception:
                pass
        cm = c.get_editor_property('character_movement')
        acc = cm.get_current_acceleration().length() if hasattr(cm, 'get_current_acceleration') else None
        log('ANIM', c.get_name(), 'role', str(c.get_local_role()).split('.')[-1].split(':')[0] if hasattr(c, 'get_local_role') else '', 'speed', round(c.get_velocity().length()), 'acc', acc and round(acc), 'skin', m.get_skinned_asset().get_name() if m.get_skinned_asset() else None, 'abp', ai.get_class().get_name() if ai else None, vs, 'dfoot', dfoot, 'dhand', dhand, 'hand', [round(v) for v in (ha.x, ha.y, ha.z)])


ALARM = '/Game/GW/Blueprints/BP_GW_KamiAlarm.BP_GW_KamiAlarm_C'


def kami_stat(world, pc):
    k = [c for c in actors(world, CHAR) if c.get_editor_property('Kind') == 2]
    al = actors(world, ALARM)
    out = []
    for a_ in al:
        cry = [x for x in a_.get_components_by_class(unreal.AudioComponent)][0]
        c = a_.get_editor_property('Ch')
        out.append(('started', a_.get_editor_property('Started'), 'snd', cry.sound.get_name() if cry.sound else None, 'att', cry.attenuation_settings.get_name() if cry.attenuation_settings else None,
                    'gap to him', round((a_.get_actor_location() - c.get_actor_location()).length()) if c else None))
    log('KAMI t', round(unreal.GameplayStatics.get_time_seconds(world), 1), 'kamikazes', [(x.get_name(), x.get_editor_property('IsDead'), round(x.get_velocity().length())) for x in k], 'alarms', out, 'ev', unreal.GameplayStatics.get_game_state(world).get_editor_property('EventId'), 'drops', len(actors(world, SHOP + '/BP_GW_BombDrop.BP_GW_BombDrop_C')))


def npc_ahead(world, pc, ch=None):
    """The nearest living guest, frozen, 100 cm in front of the pawn: the blade's target."""
    ch = ch or pc.get_controlled_pawn()
    l = ch.get_actor_location()
    g = [x for x in actors(world, CHAR) if x.get_editor_property('Kind') == 0 and not x.is_player_controlled() and not x.get_editor_property('IsDead')]
    g.sort(key=lambda x: (x.get_actor_location() - l).length())
    fw = unreal.Vector(1, 0, 0)
    g[0].set_actor_location(unreal.Vector(l.x + 100, l.y, l.z), False, True)
    F6['blade'] = g[0]
    return g[0]


def blade_try(world, pc):
    npc_ahead(world, pc)
    pc.set_control_rotation(unreal.Rotator(roll=0, pitch=0, yaw=0))
    ps = pc.get_editor_property('player_state')
    now = unreal.GameplayStatics.get_game_state(world).get_server_world_time_seconds()
    pc.call_method('GWBlade', args=(0.0, 0.0))
    log('BLADE t', round(now, 1), 'target dead', F6['blade'].get_editor_property('IsDead'), 'readyAt-now', round(ps.get_editor_property('BladeReadyAt') - now, 1), 'len', ps.get_editor_property('BladeCdLen'), 'money', ps.get_editor_property('Money'))


def cblade_try(world, pc):
    c = [x for x in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.PlayerController) if x != pc]
    if not c:
        return log('no client controller')
    c = c[0]
    t = npc_ahead(world, pc, c.get_controlled_pawn())
    c.set_control_rotation(unreal.Rotator(roll=0, pitch=0, yaw=0))
    ps = c.get_editor_property('player_state')
    now = unreal.GameplayStatics.get_game_state(world).get_server_world_time_seconds()
    c.call_method('GWBlade', args=(0.0, 0.0))
    log('CBLADE t', round(now, 1), 'target dead', t.get_editor_property('IsDead'), 'readyAt-now', round(ps.get_editor_property('BladeReadyAt') - now, 1))


def slots_stat(world, pc):
    w = pc.get_editor_property('InvWid')
    ps = pc.get_editor_property('player_state')
    if not w or not ps:
        return log('no inv widget / ps')
    gs_ = unreal.GameplayStatics.get_game_state(world)
    now = gs_.get_server_world_time_seconds()
    log('SLOTS', [ps.get_editor_property(f'Slot{i}') for i in range(4)], 'readyAt-now', round(ps.get_editor_property('BladeReadyAt') - now, 1), 'CdT', [str(w.get_editor_property(f'CdT{i}').get_text()) for i in range(4)], 'cd opacity', [round(w.get_editor_property(f'Cd{i}').get_render_opacity(), 1) for i in range(4)], 'cd scale', [round(w.get_editor_property(f'Cd{i}').get_editor_property('render_transform').scale.y, 2) for i in range(4)])


def run_setup(world, pc):
    ch = pc.get_controlled_pawn()
    ch.get_editor_property('character_movement').set_editor_property('max_walk_speed', 1000.0)
    t = actors(world, TRAPC)
    if not t:
        return log('no trap')
    tl = t[0].get_actor_location()
    ch.set_actor_location(unreal.Vector(tl.x, tl.y - 260, 110), False, True)
    F6['t'] = t[0]
    F6['c'] = ch
    F6['done'] = False
    log('run from', ch.get_actor_location(), 'to trap', tl, 'hp', hp(ch))


def run_step(world, pc):
    """Really running through the door along +Y, at 1000 cm/s (a player on gas is about that fast)."""
    c, t = F6.get('c'), F6.get('t')
    if t is None or not unreal.SystemLibrary.is_valid(t):
        if not F6.get('done'):
            F6['done'] = True
            log('trap fired, speed', round(c.get_velocity().length()), 'y', round(c.get_actor_location().y), 'hp', hp(c))
        return
    c.add_movement_input(unreal.Vector(0, 1, 0), 1.0, True)
    F6['maxv'] = max(F6.get('maxv', 0), c.get_velocity().length())


def run_end(world, pc):
    c = F6.get('c')
    log('run ended: y', round(c.get_actor_location().y), 'max speed', round(F6.get('maxv', 0)), 'trap left', len(actors(world, TRAPC)), 'hp', hp(c))
    c.get_editor_property('character_movement').set_editor_property('max_walk_speed', 165.0)


def hud_dump(world, pc):
    h = None
    for w in unreal.ObjectIterator(unreal.UserWidget):
        if w.get_class().get_name() == 'WBP_HUD_C' and w.get_world() == world:
            h = w
    if h:
        log('HUD', 'life', str(h.get_editor_property('TxtHealth').get_text()), 'money', str(h.get_editor_property('TxtMoney').get_text()), 'role', str(h.get_editor_property('TxtRole').get_text()), 'counts', str(h.get_editor_property('TxtHiders').get_text()), 'hint vis', str(h.get_editor_property('HintPlate').get_visibility()).split('.')[-1])


FB6_SWEEP = lambda who, speed, n=40: [(0.5, sweep_target(who))] + [(0.05, sweep_step(speed))] * n + [(1.0, trap_stat), (0.1, me_stat)]
def look_stat(tag):
    def f(world, pc):
        ch = pc.get_controlled_pawn()
        if ch is None:
            return log('LOOK', tag, 'no pawn')
        cm = ch.get_editor_property('character_movement')
        m = ch.get_editor_property('mesh')
        m.set_editor_property('visibility_based_anim_tick_option', unreal.VisibilityBasedAnimTickOption.ALWAYS_TICK_POSE_AND_REFRESH_BONES)
        head = unreal.MathLibrary.inverse_transform_location(ch.get_actor_transform(), m.get_socket_location('head'))
        log('LOOK', tag, 'ctrl yaw', round(pc.get_control_rotation().yaw), 'body yaw', round(ch.get_actor_rotation().yaw), 'useCtlYaw', ch.get_editor_property('use_controller_rotation_yaw'), 'orient', cm.get_editor_property('orient_rotation_to_movement'), 'desired', cm.get_editor_property('use_controller_desired_rotation'),
            'ViewFP', ch.get_editor_property('ViewFP'), 'Aiming', ch.get_editor_property('Aiming'), 'WantFP', pc.get_editor_property('WantFP'), 'seeker', ch.get_editor_property('IsSeeker'), 'held', ch.get_editor_property('HeldItem'), 'head', [round(v) for v in (head.x, head.y, head.z)], 'abp', m.get_anim_instance().get_class().get_name() if m.get_anim_instance() else None)
    return f


LOOK_STEPS = lambda tag: [(0.5, look_stat(tag + ' before')), (0.1, yaw_add(90)), (0.2, look_stat(tag + ' +90 0.2s')), (1.0, look_stat(tag + ' +90 1.2s')), (0.1, yaw_add(120)), (0.5, look_stat(tag + ' +210')), (1.0, look_stat(tag + ' +210 1.5s'))]
FB6_LOOK = [(10, 'GWDevQuickTest 1'), (1, 'GWDevAutoEvents 0'), (1, 'GWDevRole 1'), (1, pcall('DevEnsureAlive')), (1, look_stat('guest'))] + LOOK_STEPS('guest') + [(0.5, 'GWDevGiveItem 1'), (0.5, inv)] + LOOK_STEPS('guest rifle') + [(0.5, 'GWInvDrop'), (0.5, 'GWDevRole 2'), (2, pcall('DevEnsureAlive')), (1, inv)] + LOOK_STEPS('detective revolver') + [(0.5, ads(True)), (1, look_stat('detective ads')), (0.1, yaw_add(90)), (0.5, look_stat('detective ads +90')), (0.5, ads(False)), (1, look_stat('after ads'))] + LOOK_STEPS('detective after ads')


def cpawn(world, pc):
    c = [x for x in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.PlayerController) if x != pc]
    return c[0] if c else None


def cseat_tp(k):
    def f(world, pc):
        c = cpawn(world, pc)
        if not c:
            return log('no client')
        q = c.get_editor_property('SeatLocs')[k]
        c.get_controlled_pawn().set_actor_location(unreal.Vector(q.x + 90, q.y, q.z + 95), False, True)
        log('client near seat', k, q)
    return f


def csit_stat(world, pc):
    c = cpawn(world, pc)
    p = c.get_controlled_pawn()
    log('SERVER SIDE client SitI', c.get_editor_property('SitI'), 'dance', p.get_editor_property('DanceId'), 'loc', p.get_actor_location())


def sit_stat(tag):
    def f(world, pc):
        ch = pc.get_controlled_pawn()
        if ch is None:
            return log('SIT', tag, 'no pawn')
        cm = ch.get_editor_property('character_movement')
        m = ch.get_editor_property('mesh')
        ai = m.get_anim_instance()
        l = ch.get_actor_location()
        i = pc.get_editor_property('SitI')
        seats = pc.get_editor_property('SeatLocs')
        log('SIT', tag, 'SitI', i, 'dance', ch.get_editor_property('DanceId'), 'mode', str(cm.get_editor_property('movement_mode')).split('.')[-1].split(':')[0], 'loc', [round(v) for v in (l.x, l.y, l.z)], 'yaw', round(ch.get_actor_rotation().yaw), 'seat', [round(v) for v in (seats[i].x, seats[i].y, seats[i].z)] if 0 <= i < len(seats) else None, 'seats', len(seats), 'abp', ai.get_class().get_name() if ai else None, 'view blend', ch.get_editor_property('ViewFP'))
    return f


def at_seat(k):
    def f(world, pc):
        seats = pc.get_editor_property('SeatLocs')
        q = seats[k % len(seats)]
        ch = pc.get_controlled_pawn()
        ch.set_actor_location(unreal.Vector(q.x + 90, q.y, q.z + 95), False, True)
        log('at seat', k, q, 'me', ch.get_actor_location())
    return f


def move_key(ch):
    """What IA_Move does each frame the key is down: W."""
    ch.call_method('MoveKeys', args=(0.0, 1.0))


def press_e(world, pc):
    log('E -> InteractOther')
    pc.call_method('InteractOther')


def nudge(world, pc):
    move_key(pc.get_controlled_pawn())


def walk_input(world, pc):
    move_key(pc.get_controlled_pawn())


def walk_stat(world, pc):
    ch = pc.get_controlled_pawn()
    v = ch.get_velocity()
    log('WALK ctrl yaw', round(pc.get_control_rotation().yaw), 'heading', round(ch.get_editor_property('MoveYaw')), 'body yaw', round(ch.get_actor_rotation().yaw), 'vel yaw', round(unreal.MathLibrary.make_rot_from_x(v).yaw) if v.length() > 5 else None, 'speed', round(v.length()))


CS = {'moved': 0}


def client_sit_step(world, pc):
    """On the client: once seated for 4 s (the host sat it down), W for 0.5 s must stand it up through its own ServerExec; afterwards a look test: the camera turns, the body must not."""
    ch = pc.get_controlled_pawn()
    if ch is None:
        return log('SIT client no pawn')
    sit_stat('client')(world, pc)
    i = pc.get_editor_property('SitI')
    if i >= 0:
        CS['moved'] += 1
        if CS['moved'] == 4:
            log('client presses W')
            for k_ in range(30):
                pass
            move_key(ch)
            CS['hold'] = 8
    if CS.get('hold', 0) > 0:
        CS['hold'] -= 1
        move_key(ch)
    if i < 0 and CS['moved'] >= 4 and not CS.get('looked'):
        CS['looked'] = 1
        look_stat('client before')(world, pc)
        yaw_add(120)(world, pc)
        CS['look'] = 2
    elif CS.get('look'):
        CS['look'] -= 1
        look_stat('client +120')(world, pc)


WALK = lambda n: [(0.1, walk_input), (0.1, walk_input), (0.0, walk_stat)] * n
FB6_SIT = [(10, 'GWDevQuickTest 1'), (1, 'GWDevAutoEvents 0'), (1, 'GWDevRole 1'), (1, pcall('DevEnsureAlive')), (0.5, sit_stat('start'))] + [(0.3, at_seat(0)), (0.8, sit_stat('near')), (0.1, press_e), (0.6, sit_stat('E: seated')), (1.0, sit_stat('later')), (0.1, press_e), (0.6, sit_stat('E: stood'))] + sum([[(0.3, at_seat(k)), (0.5, 'GWSit'), (0.4, sit_stat('seat ' + str(k))), (0.1, 'GWSit')] for k in range(3, 181, 8)], []) + [
    (0.3, at_seat(5)), (0.6, press_e), (1.0, sit_stat('seated')), (0.0, nudge), (0.0, nudge), (0.0, nudge), (0.1, nudge), (0.1, nudge), (0.8, sit_stat('moved: stood'))] + [
    (0.5, 'GWDevTeleport 2925 3100 130'), (0.5, walk_stat)] + WALK(4) + [(0.0, yaw_add(90)), (0.0, walk_stat)] + WALK(10) + [(0.0, yaw_add(-90))] + WALK(10)
FB6_SIT_HOST = [(2, qt_two)] * 12 + [(1, 'GWDevRole 1'), (1, cpc('GWDevRole', 1)), (1, cpc('DevEnsureAlive')), (0.5, 'GWDevNPCFreeze 1')] + sum([[(1, cseat_tp(k)), (2, cpc('GWSit')), (2, csit_stat), (8, csit_stat), (1, csit_stat)] for k in (3, 44)], []) + [(1, csit_stat), (1, cseat_tp(90)), (2, cpc('GWSit')), (2, csit_stat), (2, cpc('GWSit')), (2, csit_stat), (1, cseat_tp(120)), (1, cpc('GWSit')), (20, csit_stat), (5, csit_stat)]
FB6_SIT_CLIENT = [(25, sit_stat('client'))] + [(1.0, client_sit_step)] * 100


def setup_widget(world):
    for w in unreal.ObjectIterator(unreal.UserWidget):
        if w.get_class().get_name() == 'WBP_GameSetup_C' and w.is_in_viewport():
            return w
    return None


def setup_open(world, pc):
    menu = [w for w in unreal.ObjectIterator(unreal.UserWidget) if w.get_class().get_name() == 'WBP_MainMenu_C' and w.get_world() == world][0]
    F6['menu'] = menu
    menu.call_method('OnHostAsk')
    log('setup open', setup_widget(world) is not None)


def setup_stat(tag):
    def f(world, pc):
        w = setup_widget(world)
        if not w:
            return log('SETUP', tag, 'no widget')
        log('SETUP', tag, [str(w.get_editor_property(f'Val{i}').get_text()) for i in range(9)], 'vals', list(w.get_editor_property('Vals')))
    return f


def setup_call(fn):
    def f(world, pc):
        setup_widget(world).call_method(fn)
    return f


def setup_gm(tag):
    def f(world, pc):
        gm = unreal.GameplayStatics.get_game_mode(world)
        gs_ = unreal.GameplayStatics.get_game_state(world)
        log('SETUP GM', tag, 'NPCCount', gm.get_editor_property('NPCCount'), 'Hunt', gm.get_editor_property('HuntTime'), 'Hide', gm.get_editor_property('HideTime'), 'MaxRounds', gm.get_editor_property('MaxRounds'), 'Seekers', gm.get_editor_property('SeekersWanted'), 'Auto', gm.get_editor_property('AutoEvents'), 'Every', gm.get_editor_property('EventEvery'), 'Min', gm.get_editor_property('MinPlayers'), 'Lobby', gm.get_editor_property('LobbyCountdown'), 'chars', len(actors(world, CHAR)), 'phase', gs_.get_editor_property('Phase'), 'round', gs_.get_editor_property('RoundNumber'))
    return f


def end_round(world, pc):
    unreal.GameplayStatics.get_game_mode(world).call_method('EndRound', args=(2, 'test'))


FB6_SETUP = [(10, setup_open), (1, setup_stat('first open')), (0.5, setup_call('N0')), (0.1, setup_call('N0')), (0.1, setup_call('P1')), (0.1, setup_call('N3')), (0.1, setup_call('N4')), (0.1, setup_call('P5')), (0.1, setup_call('P5')), (0.1, setup_call('N6')), (0.3, setup_stat('changed')), (0.5, setup_call('OnStart')),
    (30, setup_gm('after travel')), (1, 'GWDevQuickTest 1'), (2, setup_gm('quick test')), (0.5, 'GWDevMoney 1250'), (0.3, 'GWDevGiveItem 5'), (0.3, 'GWDevGiveItem 10'), (0.5, end_round), (4, setup_gm('round over')), (10, setup_gm('after end time'))]


FB6_KAMI = [(10, 'GWDevQuickTest 1'), (1, 'GWDevAutoEvents 0'), (1, 'GWDevRole 1'), (1, pcall('DevEnsureAlive')), (0.5, 'GWDevEvent 4')] + [(1.0, kami_stat)] * 32 + [(0.5, 'GWDevHeal'), (1, pcall('DevEnsureAlive')), (0.5, 'GWDevKamikaze'), (0.1, kami_stat), (0.4, kami_stat), (1, kami_stat)]
FB6_BLADE = [(10, 'GWDevQuickTest 1'), (1, 'GWDevAutoEvents 0'), (1, 'GWDevRole 1'), (1, pcall('DevEnsureAlive')), (0.5, 'GWDevNPCFreeze 1'), (0.5, 'GWDevGiveItem 10'), (0.5, inv), (0.5, blade_try), (0.3, slots_stat), (0.2, blade_try), (2, slots_stat), (3, blade_try), (3, slots_stat), (0.2, slots_stat), (0.2, blade_try), (0.3, slots_stat), (0.5, 'GWDevBladeCD 4'), (8, blade_try), (0.5, slots_stat), (2, blade_try), (2, blade_try), (0.2, 'GWDevBladeCD 8'), (0.1, inv)]
FB6_RUN = [(10, 'GWDevQuickTest 1'), (1, 'GWDevAutoEvents 0'), (1, 'GWDevRole 1'), (1, pcall('DevEnsureAlive')), (0.5, 'GWDevNPCFreeze 1'), (0.3, hud_dump),
    (0.5, door_trap), (0.5, 'GWDevGiveItem 5'), (0.5, gm_use('PlaceTrap')), (0.5, trap_stat), (0.5, 'GWDevTeleport 2925 3100 130'), (4, run_setup)] + [(0.0, run_step)] * 90 + [(0.1, run_end), (1, me_stat), (0.2, hud_dump),
    (0.5, 'GWDevTrapNPC 1'), (0.5, door_trap), (0.5, 'GWDevGiveItem 5'), (0.5, gm_use('PlaceTrap')), (0.5, trap_stat), (0.5, 'GWDevTeleport 2925 3100 130'), (4, trap_stat)] + FB6_SWEEP('npc', 300) + [(0.5, 'GWDevTrapNPC 0'), (0.5, me_stat)]
FB6_NET2_HOST = [(2, qt_two)] * 12 + [(1, 'GWDevRole 1'), (1, cpc('GWDevRole', 1)), (1, pcall('DevEnsureAlive')), (0.5, cpc('DevEnsureAlive')), (0.5, 'GWDevNPCFreeze 1'), (0.5, cpc('GWDevGiveItem', 10)), (1, cblade_try), (1, cblade_try), (5, 'GWDevEvent 4')] + [(1.0, kami_stat)] * 8
FB6_NET2_CLIENT = [(15, slots_stat)] + [(1.0, slots_stat), (0.0, kami_stat)] * 60 + [(0.5, hud_dump)]


def walker(n):
    """Shot at a waiter from the side while he walks, whichever is moving."""
    def f(world, pc):
        w = actors(world, f'{SHOP}/{n}.{n}_C')
        if not w:
            return log('no', n)
        w = w[0]
        p = unreal.MathLibrary.transform_location(w.get_actor_transform(), unreal.Vector(140, -190, 0))
        ch = pc.get_controlled_pawn()
        ch.set_actor_location(p, False, False)
        pc.set_control_rotation(unreal.MathLibrary.find_look_at_rotation(p + unreal.Vector(0, 0, 66), w.get_actor_location() + unreal.Vector(0, 0, 25)))
        log('at waiter', n, 'speed', round(w.get_velocity().length()), 'anim', w.get_editor_property('mesh').get_anim_instance().get_class().get_name())
    return f


def wait_moving(n, want=True):
    return walker(n)


FB6_SHOTS = [(10, 'GWDevQuickTest 1'), (1, 'GWDevAutoEvents 0'), (1, 'GWDevRole 1'), (1, pcall('DevEnsureAlive')), (0.5, 'GWDevMoney 1250'), (0.5, tp_view(False)), (0.5, 'GWDevTeleport 2925 3100 130'), (0.3, view(-8, 0)),
    (1.5, label('empty slots, start of the hunt, hint')), (0.2, SHOT), (0.5, 'GWDevGiveItem 1'), (0.3, 'GWDevGiveItem 5'), (0.3, 'GWDevGiveItem 8'), (0.3, 'GWDevGiveItem 10'), (1, label('four items')), (0.2, SHOT),
    (0.5, 'GWDevNPCFreeze 1'), (1, blade_try), (0.8, label('blade cooldown')), (0.2, SHOT), (0.5, 'GWDevNPCFreeze 0'),
    (0.5, door_trap), (0.5, gm_use('PlaceTrap')), (0.3, 'GWDevTeleport 2925 3100 130'), (4, run_setup), (0.0, view(-5, 90))] + [(0.0, run_step)] * 60 + [(0.1, label('trap just fired')), (0.0, SHOT), (0.25, label('trap +0.3 s')), (0.0, SHOT), (0.5, label('trap +0.8 s')), (0.0, SHOT), (2, run_end), (0.5, 'GWDevHeal'),
    (1, 'GWDevMoney 100'), (0.3, label('money gained')), (0.1, SHOT), (0.5, 'GWDevEvent 4'), (1.0, label('kamikaze event')), (0.1, SHOT), (0.5, 'GWDevEventStop'),
    (1.0, walker('BP_GW_Waiter')), (1.0, label('waiter')), (0.1, SHOT), (0.3, walker('BP_GW_Waiter')), (0.8, label('waiter 2')), (0.1, SHOT), (0.3, walker('BP_GW_Waiter2')), (1.0, label('waiter2')), (0.1, SHOT), (4, walker('BP_GW_Waiter')), (1, label('waiter 3')), (0.1, SHOT), (4, walker('BP_GW_Waiter2')), (1, label('waiter2 2')), (0.1, SHOT),
    (0.5, 'GWDevTeleport 2925 3100 130'), (0.5, 'GWDevRole 2'), (2, label('detective')), (0.2, SHOT), (1, label('end'))]


FB6_ANIM = [(10, 'GWDevQuickTest 1'), (1, 'GWDevAutoEvents 0'), (20, anim_watch)] + [(1.0, anim_watch)] * 45
FB6_ANIM_HOST = [(2, qt_two)] * 12 + [(10, anim_watch)] + [(1.0, anim_watch)] * 45
FB6_ANIM_CLIENT = [(45, anim_watch)] + [(1.0, anim_watch)] * 60
FB6_TRAP = [(10, 'GWDevQuickTest 1'), (1, 'GWDevAutoEvents 0'), (1, 'GWDevRole 1'), (1, pcall('DevEnsureAlive')), (0.5, 'GWDevNPCFreeze 1'), (0.5, me_stat),
    (0.5, door_trap), (0.5, 'GWDevGiveItem 5'), (0.5, gm_use('PlaceTrap')), (0.5, trap_stat), (0.5, 'GWDevTeleport 2925 3100 130'), (4, trap_stat)] + FB6_SWEEP('npc', 300) + FB6_SWEEP('host', 300) + [
    (2, me_stat),
    (0.5, door_trap), (0.5, 'GWDevGiveItem 5'), (0.5, gm_use('PlaceTrap')), (0.5, trap_stat), (0.5, 'GWDevTeleport 2925 3100 130'), (4, trap_stat)] + FB6_SWEEP('host', 1000) + [(2, me_stat)]
FB6_NET_HOST = [(2, qt_two)] * 12 + [(1, 'GWDevRole 1'), (1, cpc('GWDevRole', 1)), (1, pcall('DevEnsureAlive')), (0.5, cpc('DevEnsureAlive')), (0.5, 'GWDevNPCFreeze 1'),
    (0.5, door_trap), (0.5, 'GWDevGiveItem 5'), (0.5, gm_use('PlaceTrap')), (0.5, trap_stat), (0.5, 'GWDevTeleport 2925 3100 130'), (4, trap_stat)] + FB6_SWEEP('client', 300) + [(3, trap_stat)]
FB6_NET_CLIENT = [(20, me_stat)] + [(1.0, me_stat)] * 70

# ---------------------------------------------------------------- NPC life (Tools/qa/npc_watch.py): pops, dwell, cast census; npc_net.ps1 for host + client
def _nw():
    import sys
    if r'J:\Projets\Unreal_Projects\Guess Who\Tools\qa' not in sys.path:
        sys.path.insert(0, r'J:\Projets\Unreal_Projects\Guess Who\Tools\qa')
    import npc_watch
    return npc_watch


def nw_start(render=False):
    def f(world, pc):
        _nw().nw_start(render)(world, pc)
    return f


def nw_report(world, pc):
    _nw().nw_report(world, pc)


def slow_pan(world, pc):
    r = pc.get_control_rotation()
    pc.set_control_rotation(unreal.Rotator(roll=0, pitch=-4, yaw=r.yaw + 11))


def _npcsolo(n, reports, every=30, render=False):
    return [(10, 'GWDevQuickTest 1'), (1, 'GWDevAutoEvents 0'), (2, f'GWDevNPCCount {n}'), (3, count('after count')), (1, nw_start(render))] + [(every, nw_report)] * reports


def rvo_off(world, pc):
    k = 0
    for c in actors(world, CHAR):
        if not c.is_player_controlled():
            c.get_editor_property('character_movement').set_avoidance_enabled(False)
            k += 1
    log('avoidance off on', k)


def npc_state(world, pc):
    log('STATE', unreal.GameplayStatics.get_game_mode(world).call_method('LifeState'))


NPC_PLANS = {f'npcsolo{n}': _npcsolo(n, 10) for n in (30, 60, 100, 120, 150, 200)}
NPC_PLANS.update({f'npcshort{n}': _npcsolo(n, 2) for n in (30, 60, 100, 120, 150, 200)})
NPC_PLANS['npcnorvo120'] = [(10, 'GWDevQuickTest 1'), (1, 'GWDevAutoEvents 0'), (2, 'GWDevNPCCount 120'), (6, rvo_off), (1, nw_start())] + [(45, nw_report)] * 4
def _npc_spot(tag, x, y, pitch, yaw):
    # a few frames of the same place, 1.5 s apart: what moves, what breaks a line
    return [(0.5, f'GWDevTeleport {x} {y} 130'), (0.3, view(pitch, yaw))] + sum([[(1.2, label(f'{tag} {i}')), (0.2, SHOT)] for i in range(4)], [])


NPC_PLANS['npcshots'] = [(10, 'GWDevQuickTest 1'), (1, 'GWDevAutoEvents 0'), (2, 'GWDevNPCCount 120'), (45, npc_state)] + _npc_spot('bar queue', 4420, 300, -12, 90) + _npc_spot('dance floor', 3000, 2560, -14, 90) + _npc_spot('dining cart', 1500, 1300, -10, 45) + _npc_spot('hall', 2950, 400, -10, 90) + _npc_spot('library', 1000, 2700, -10, 90) + [(0.3, npc_state)]
NPC_PLANS['npcnofix120'] = [(10, 'GWDevQuickTest 1'), (1, 'GWDevAutoEvents 0'), (2, 'GWDevNPCCount 120'), (1, 'GWDevNPCBlock 0'), (3, nw_start())] + [(45, nw_report)] * 6
NPC_PLANS['npcq120'] = [(10, 'GWDevQuickTest 1'), (1, 'GWDevAutoEvents 0'), (2, 'GWDevNPCCount 120'), (3, nw_start())] + ([(10, npc_state)] * 3 + [(0.1, nw_report)]) * 9
NPC_PLANS['npchost100'] = [(2, qt_two)] * 15 + [(1, 'GWDevAutoEvents 0'), (2, 'GWDevNPCCount 120'), (3, nw_start())] + [(40, nw_report)] * 6
NPC_PLANS['npcclient'] = [(40, nw_start())] + [(40, nw_report)] * 6
NPC_PLANS['npcrender100'] = [(10, 'GWDevQuickTest 1'), (1, 'GWDevAutoEvents 0'), (2, 'GWDevNPCCount 120'), (2, 'GWDevTeleport 3000 3000 130'), (3, nw_start(True))] + ([(3, slow_pan)] * 9 + [(1, nw_report)]) * 6


PLANS = {
    **NPC_PLANS,
    'fb6sit': FB6_SIT, 'fb6sith': FB6_SIT_HOST, 'fb6sitc': FB6_SIT_CLIENT,
    'fb6setup': FB6_SETUP,
    'fb6look': FB6_LOOK,
    'fb6kami': FB6_KAMI, 'fb6blade': FB6_BLADE, 'fb6run': FB6_RUN, 'fb6net2h': FB6_NET2_HOST, 'fb6net2c': FB6_NET2_CLIENT, 'fb6shots': FB6_SHOTS,
    'fb6anim': FB6_ANIM, 'fb6animh': FB6_ANIM_HOST, 'fb6animc': FB6_ANIM_CLIENT,
    'fb6trap': FB6_TRAP, 'fb6nethost': FB6_NET_HOST, 'fb6netclient': FB6_NET_CLIENT,
    'fb5beam': FB_BEAM,
    'fb5shots2': FB_SHOTS2,
    'fb5hit': [(10, 'GWDevQuickTest 1'), (1, 'GWDevAutoEvents 0'), (1, 'GWDevRole 1'), (2, pcall('DevEnsureAlive')), (0.5, 'GWDevEvent 5'), (2, rstat)] + [(0.25, rc(False))] * 90 + [(0.3, rstat)],
    'fb5zomb': FB_ZOMB, 'fb5robot': FB_ROBOT, 'fb5items': FB_ITEMS, 'fb5nethost': FB_NET_HOST, 'fb5netclient': FB_NET_CLIENT, 'fb5shots': FB_SHOTS,
    'staff': [
        (10, 'GWDevQuickTest 1'), (1, 'GWDevAutoEvents 0'), (1, 'GWDevRole 1'), (2, 'GWDevWaiters 1'), (1, fp), (3, cast_census),
        (1, follow_shop('BP_GW_Barman', (190, 0, 10))), (1.5, label('barman front')), (0.2, SHOT),
        (1, follow_shop('BP_GW_Junkie', (190, 0, 10))), (1.5, label('junkie front')), (0.2, SHOT),
        (1, follow_shop('BP_GW_Junkie', (0, 190, 10))), (1.5, label('junkie side')), (0.2, SHOT),
        (1, follow_shop('BP_GW_Waiter', (190, 0, 10))), (1.5, label('waiter front')), (0.2, SHOT),
        (1, follow_shop('BP_GW_Waiter', (0, -190, 10))), (1.5, label('waiter side tray')), (0.2, SHOT),
        (1, follow_shop('BP_GW_Waiter', (-190, 0, 10))), (1.5, label('waiter back')), (0.2, SHOT),
        (1, follow_shop('BP_GW_Waiter2', (190, 0, 10))), (1.5, label('waiter2 front')), (0.2, SHOT),
        (1, mesh_view('char_minuit')), (1.5, label('minuit')), (0.2, SHOT),
        (1, mesh_view('char_irene')), (1.5, label('irene')), (0.2, SHOT),
        (2, mesh_view('char_irene', (0, 220, 10))), (1.5, label('irene side')), (0.2, SHOT),
        (1, 'GWDevEvent 5'), (6, cast_census), (0.5, mesh_view('char_robot', (300, 0, 40), 60)), (1.5, label('robot event')), (0.2, SHOT),
    ],
    'zomb4': [(10, 'GWDevQuickTest 1'), (1, 'GWDevAutoEvents 0'), (4, zexp3), (2, zexp4), (1, count('end'))],
    'zomb3': [(10, 'GWDevQuickTest 1'), (1, 'GWDevAutoEvents 0'), (4, 'GWDevEvent 6'), (1, zexp), (3, zexp2), (2, count('end'))],
    'zomb2': [
        (10, 'GWDevQuickTest 1'), (1, 'GWDevAutoEvents 0'), (4, snap),
        (1, 'GWDevEvent 6'), (1, 'GWDevEventGo'), (25, count('zombies+25s')), (0.5, compare), (3, count('after')),
    ],
    'zomb': [
        (10, 'GWDevQuickTest 1'), (1, 'GWDevAutoEvents 0'), (4, count('start')),
        (1, 'GWDevEvent 6'), (1, 'GWDevEventGo'), (25, count('zombies+25s')), (15, count('zombies+40s')),
        (1, 'GWDevEventStop'), (3, count('stopped')), (25, count('stopped+25s')),
        (1, 'GWDevEvent 6'), (1, 'GWDevEventGo'), (25, count('zombies2+25s')), (1, 'GWDevEventStop'), (25, count('stopped2+25s')),
        (1, 'GWDevNPCCount 40'), (3, count('npc40')), (1, 'GWDevNPCCount 60'), (3, count('npc60')),
        (1, 'GWDevNPCKill'), (1, 'GWDevNPCKill'), (1, 'GWDevNPCKill'), (3, count('3 kills')),
    ],
    'items3': [
        (10, 'GWDevQuickTest 1'), (1, 'GWDevAutoEvents 0'), (1, 'GWDevRole 1'), (1, fp),
        (1, actor_view(BREAKER, (110, 35, -20))), (1, label('breaker open')), (0.2, SHOT), (0.5, call('GWBreakerTest')), (1.5, actor_view(BREAKER, (110, 35, -20))), (1, label('breaker thrown')), (0.2, SHOT),
        (1, 'GWDevGoBox'), (1, actor_view(BOX, (10, 150, 96), tz=30)), (1, label('box')), (0.2, SHOT),
    ],
    'items2': [
        (10, 'GWDevQuickTest 1'), (1, 'GWDevAutoEvents 0'), (1, 'GWDevRole 1'), (3, 'GWDevMoney 5000'), (1, fp), (1, view(-4, 0)),
        (1, 'GWDevGoBox'), (0.5, try_hold), (2.2, actor_view(BOX, (10, 150, 96), tz=30)), (0.6, label('box spinning, lid')), (0.1, SHOT), (6, 'GWDevMoney 5000'),
        (1, 'GWDevTeleport 2925 3200 130'), (0.5, gm_use('PlaceTrap')), (1, actor_view(SHOP + '/BP_GW_Trap.BP_GW_Trap_C', (30, 12, 40), tz=0)), (1, label('trap close')), (0.2, SHOT),
        (2, actor_view(BREAKER, (130, 20, -10))), (0.5, call('GWBreakerTest')), (1, 'GWDevEventStop'), (1.5, label('breaker thrown')), (0.2, SHOT),
        (1, 'GWDevTurretGo'), (1, try_turret), (2, dump(TURRET)), (0.5, yaw_add(25)), (1.5, dump(TURRET)), (0.1, call('TurretTest')),
    ],
    'items': [
        (10, 'GWDevQuickTest 1'), (1, 'GWDevAutoEvents 0'), (1, 'GWDevRole 1'), (3, 'GWDevMoney 5000'), (1, 'GWDevWaiters 1'), (1, fp), (1, view(-4, 0)),
        # the box, its lid while it spins
        (1, 'GWDevGoBox'), (1, actor_view(BOX, (130, 110, 40))), (1, label('box closed')), (0.2, SHOT),
        (1, 'GWDevGoBox'), (0.5, try_hold), (2.5, label('box spinning, lid')), (0.2, actor_view(BOX, (130, 110, 40))), (0.3, SHOT), (5, try_hold),
        # placed and thrown, in the big hall away from the box
        (1, 'GWDevTeleport 2925 3565 130'), (1, gm_use('DropBomb')), (1, actor_view(SHOP + '/BP_GW_Bomb.BP_GW_Bomb_C', (80, 25, 96))), (1, label('bomb')), (0.2, SHOT),
        (1, dump(SHOP + '/BP_GW_Bomb.BP_GW_Bomb_C')),
        (0.5, 'GWDevTeleport 2925 3200 130'), (0.5, gm_use('PlaceTrap')), (1, actor_view(SHOP + '/BP_GW_Trap.BP_GW_Trap_C', (50, 25, 88))), (1, label('trap')), (0.2, SHOT),
        (0.5, 'GWDevKamikaze'), (1, actor_view(SHOP + '/BP_GW_BombDrop.BP_GW_BombDrop_C', (80, 25, 96))), (1, label('bomb drop (kamikaze)')), (0.2, SHOT),
        (1, dump(SHOP + '/BP_GW_BombDrop.BP_GW_BombDrop_C')),
        (0.5, 'GWDevTeleport 2000 3565 130'), (0.5, gm_use('UseGas')), (0.3, follow_shop('BP_GW_GasPuff', (110, 60, 96))), (0.2, label('gas')), (0.1, SHOT),
        (6, 'GWDevTeleport 3400 3565 130'), (0.5, gm_use('ThrowSmoke')), (0.75, follow_shop('BP_GW_SmokeBomb', (60, 30, 96))), (0.1, label('smoke can landed')), (0.1, SHOT),
        # the breaker: open, thrown (the blackout's close command)
        (2, actor_view(BREAKER, (130, 20, -10))), (1, label('breaker')), (0.2, SHOT),
        (0.2, 'GWDevEvent 3'), (0.3, 'GWDevEventGo'), (2, actor_view(BREAKER, (130, 20, -10))), (0.5, 'GWBreakerTest'), (1, 'GWDevEventStop'), (1.5, label('breaker thrown')), (0.2, SHOT),
        # the waiter
        (0.5, 'GWDevWaiters 1'), (1, actor_view(SHOP + '/BP_GW_Waiter.BP_GW_Waiter_C', (95, 75, 0), tz=25)), (1, label('waiter tray')), (0.2, SHOT),
        # the turret: from the side and behind, then on it: straight, turned, firing
        (1, actor_view(TURRET, (-40, 190, 96), tz=150)), (1, label('turret side')), (0.2, SHOT),
        (1, actor_view(TURRET, (-170, 70, 96), tz=150)), (1, label('turret behind')), (0.2, SHOT),
        (1, 'GWDevTurretGo'), (1, try_turret), (2, label('turret mounted')), (0.2, SHOT),
        (0.5, yaw_add(25)), (1.5, label('turret mounted yaw +25')), (0.2, SHOT), (0.5, fire), (0.15, label('turret firing')), (0.05, SHOT),
        (2, try_turret), (2, 'GWDevGoBox'),
        # in the hands, first person
        (1, 'GWDevKnight'), (2, label('knight sword')), (0.2, SHOT),
        (1, 'GWDevGiveItem 1'), (1, pick(0)), (2, label('rifle FP hip')), (0.2, SHOT),
        (1, tp_view(False)), (1, view(-10, 90)), (2, label('rifle third person')), (0.2, SHOT), (1, tp_view(True)),
        (1, 'GWDevGiveItem 8'), (1, pick(1)), (2, label('swap FP')), (0.2, SHOT),
        (1, 'GWDevGiveItem 10'), (1, pick(2)), (2, label('blade FP')), (0.2, SHOT),
        (1, 'GWDevGiveSword'), (1, pick(3)), (2, label('sword FP')), (0.2, SHOT), (1, tp_view(False)), (2, label('sword third person')), (0.2, SHOT), (1, tp_view(True)),
    ],
}


LOOKS = {}


def looks(tag):
    """Mascarade: who changed look since the last call, by kind."""
    def f(world, pc):
        now = {c.get_name(): (c.get_editor_property('OutfitIndex'), c.get_editor_property('Kind'), c.get_editor_property('IsSeeker'), c.is_player_controlled()) for c in actors(world, CHAR)}
        ch = [k for k, v in now.items() if k in LOOKS and LOOKS[k][0] != v[0]]
        log(tag, 'chars', len(now), 'changed', len(ch), 'seekers changed', len([k for k in ch if now[k][2]]), 'seekers', len([v for v in now.values() if v[2]]),
            'players', [(v[0], 'seeker' if v[2] else 'guest', 'changed' if k in ch else 'same') for k, v in now.items() if v[3]], 'distinct looks', len({v[0] for v in now.values()}))
        LOOKS.clear()
        LOOKS.update(now)
    return f


PLANS['mask'] = [(12, 'GWDevQuickTest 1'), (1, 'GWDevAutoEvents 0'), (1, 'GWDevNPCCount 30'), (8, 'GWDevGiveItem 14'), (2, 'GWDevInvState'), (1, looks('before')),
                 (0.5, 'GWUseItem 14 0'), (2, looks('after use')), (0.5, 'GWDevInvState'), (0.5, 'GWUseItem 14 0'), (2, looks('used without any left'))]

def last_add(world, pc):
    """A second player in this process (splitscreen slot): two players without a second game."""
    unreal.GameplayStatics.create_player(world, 1, True)
    log('players', len(unreal.GameplayStatics.get_game_state(world).get_editor_property('player_array')))


def last_state(tag):
    def f(world, pc):
        gs = unreal.GameplayStatics.get_game_state(world)
        cs = actors(world, CHAR)
        log(tag, 'phase', gs.get_editor_property('Phase'), 'winner', gs.get_editor_property('Winner'), 'alive', gs.get_editor_property('HidersAlive'), 'msg', str(gs.get_editor_property('Message')),
            'players', [(p.get_player_name(), p.get_editor_property('GWRole'), p.get_editor_property('IsAlive'), p.get_editor_property('Kills'), p.get_editor_property('Money'), p.get_editor_property('GWScore')) for p in gs.get_editor_property('player_array')],
            'health', [c.get_editor_property('Health') for c in cs if c.is_player_controlled()], 'wearing the detective', len([c for c in cs if c.get_editor_property('OutfitIndex') == 32]), 'of', len(cs))
    return f


def last_sword(world, pc):
    """Host's sword on the other player, through the real damage function."""
    a, v = [c for c in actors(world, CHAR) if c.is_player_controlled()][:2]
    if a != pc.get_controlled_pawn():
        a, v = v, a
    unreal.GameplayStatics.get_game_mode(world).call_method('WeaponHit', (a, v, unreal.Vector(1, 0, 0), 1))


PLANS['last'] = [(12, last_add), (2, 'GWDevAutoEvents 0'), (1, 'GWDevNPCCount 30'), (1, 'GWDevStartRound'), (3, last_state('dispersal')), (0.5, last_sword), (0.5, last_state('sword in the dispersal')),
                 (1, 'GWDevHunt'), (1, last_sword), (0.5, last_state('sword in the hunt')), (0.5, 'GWDevKillRival'), (1, last_state('rival down')), (2, last_state('end card'))]

BUMP = {}


def bump_dir(world, pawn):
    """The freest of 8 directions from the player."""
    import math
    l = pawn.get_actor_location()
    best, best_d = (1.0, 0.0), -1.0
    for i in range(8):
        a = i * math.pi / 4
        d = (math.cos(a), math.sin(a))
        end = unreal.Vector(l.x + d[0] * 1500, l.y + d[1] * 1500, l.z)
        hit = unreal.SystemLibrary.line_trace_single(world, l, end, unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, False, [pawn], unreal.DrawDebugTrace.NONE, True)
        h = hit.to_tuple() if hit else None
        dist = h[3] * 1500 if h and h[0] else 1500.0   # blocking hit, time
        if dist > best_d:
            best, best_d = d, dist
    log('freest direction', best, 'free', int(best_d))
    return best


def bump_place(dead):
    """A living guest (or its corpse) 300 cm in front of the player."""
    def f(world, pc):
        p = pc.get_controlled_pawn()
        d = bump_dir(world, p)
        BUMP['d'] = d
        l = p.get_actor_location()
        BUMP['start'] = l
        g = [c for c in actors(world, CHAR) if c.get_editor_property('Kind') == 0 and not c.get_editor_property('IsDead') and not c.is_player_controlled()]
        if not g:
            log('no guest')
            return
        t = g[0]
        BUMP['t'] = t
        t.set_actor_location(unreal.Vector(l.x + d[0] * 300, l.y + d[1] * 300, l.z), False, True)
        if dead:
            p.set_actor_location(unreal.Vector(l.x + d[0] * 230, l.y + d[1] * 230, l.z), False, True)
            unreal.SystemLibrary.execute_console_command(world, 'GWDevKillNear', pc)
    return f


def bump_back(world, pc):
    p = pc.get_controlled_pawn()
    if 'start' in BUMP:
        p.set_actor_location(BUMP['start'], False, True)
    t = BUMP.get('t')
    log('target dead', t.get_editor_property('IsDead') if t else None)


def bump_run(tag, secs=2.2, jump=False):
    """Hold forward for secs, sampling the movement: what the player does when running into the target."""
    def f(world, pc):
        p = pc.get_controlled_pawn()
        cm = p.character_movement
        d = BUMP['d']
        z0 = p.get_actor_location().z
        s = {'t': 0.0, 'air': 0.0, 'zmax': 0.0, 'n': 0, 'speed': [], 'jumped': False, 'first_air': None}

        def tick(dt):
            s['t'] += dt
            if s['t'] > secs:
                unreal.unregister_slate_post_tick_callback(s['h'])
                log(tag, 'air_time %.2f first_air %s zrise %.0f speeds %s moved %.0f target_moved %s' % (s['air'], s['first_air'], s['zmax'], s['speed'][::8],
                    (p.get_actor_location() - BUMP['start']).length(), int((BUMP['t'].get_actor_location() - BUMP['start']).length()) if BUMP.get('t') else None))
                return
            p.add_movement_input(unreal.Vector(d[0], d[1], 0), 1.0, False)
            if jump and not s['jumped'] and s['t'] > 0.5:
                s['jumped'] = True
                p.jump()
            if cm.is_falling():
                s['air'] += dt
                if s['first_air'] is None:
                    s['first_air'] = round(s['t'], 2)
            s['zmax'] = max(s['zmax'], p.get_actor_location().z - z0)
            v = p.get_velocity()
            s['speed'].append(int((v.x ** 2 + v.y ** 2) ** 0.5))

        s['h'] = unreal.register_slate_post_tick_callback(tick)
    return f


PLANS['bump'] = [(12, 'GWDevQuickTest 1'), (1, 'GWDevAutoEvents 0'), (1, 'GWDevNPCCount 30'), (8, 'GWSprint 1')]
for _i in range(2):
    PLANS['bump'] += [(1, bump_place(False)), (0.1, bump_run('living %d' % _i)), (2.6, bump_back)]
PLANS['bump'] += [(1, bump_place(True)), (3, bump_back), (0.3, bump_run('corpse')), (2.6, bump_back)]
PLANS['bump'] += [(1, 'GWSprint 0'), (1, bump_run('jump walking', jump=True)), (2.6, bump_back), (0.5, 'GWSprint 1'), (0.5, bump_run('jump sprinting', jump=True)), (2.6, bump_back)]


class Runner:
    def __init__(self):
        cmd = unreal.SystemLibrary.get_command_line()
        name = [x for x in cmd.split() if x.lower().startswith('-gwharness=')]
        self.plan = list(PLANS[name[0].split('=', 1)[1]]) if name else []
        log('plan', len(self.plan), 'steps')
        self.t = 0.0
        self.i = 0
        self.wait = self.plan[0][0] if self.plan else 0
        self.h = unreal.register_slate_post_tick_callback(self.tick)

    def tick(self, dt):
        self.t += dt
        if self.t < self.wait:
            return
        if self.i >= len(self.plan):
            log('done')
            unreal.unregister_slate_post_tick_callback(self.h)
            unreal.SystemLibrary.quit_game(world(), None, unreal.QuitPreference.QUIT, False)
            return
        act = self.plan[self.i][1]
        self.i += 1
        self.t = 0.0
        self.wait = self.plan[self.i][0] if self.i < len(self.plan) else 4.0
        try:
            w = world()
            pc = unreal.GameplayStatics.get_player_controller(w, 0)
            if callable(act):
                act(w, pc)
            else:
                log('cmd', act)
                unreal.SystemLibrary.execute_console_command(w, act, pc)
        except Exception as e:
            log('step failed', act, e)


def world():
    for gi in unreal.ObjectIterator(unreal.GameInstance):
        if not gi.get_name().startswith('Default__'):
            return gi.get_world()
    return None


RUNNER = Runner()
