"""NPC watcher for -game runs (py_harness plans npc*): what a player would call "appears / disappears / stays there".
Every frame, for every guest: mesh world location (what is SEEN: on a client it includes the network smoothing), actor list membership
(relevancy, spawn, destroy), bHidden, mesh visible flag, mesh asset, scale. At 2 Hz: stationary time per guest with the state of its brain.
With -Render: at 5 Hz, guests in clear view of the camera that the renderer does not draw (occlusion, culling, bounds).
Log lines start with 'GWH: NW'. Report: nw_report(world, pc)."""
import unreal
import time

CHAR = '/Game/GW/Blueprints/BP_GW_Character.BP_GW_Character_C'
SPRINT = 470.0
ROOMS = [('dining', 0, 0, 2000, 1800), ('corridor_w', 0, 1800, 2000, 2400), ('library', 0, 2400, 2000, 4400), ('hall', 2000, 0, 4000, 2400), ('ballroom', 2000, 2400, 4000, 4400), ('billiard', 4000, 0, 6000, 1800), ('corridor_e', 4000, 1800, 6000, 2400), ('study', 4000, 2400, 6000, 3200), ('conservatory', 4000, 3200, 6000, 4400)]


def log(*a):
    unreal.log('GWH: NW ' + ' '.join(str(x) for x in a))


class G:
    __slots__ = ('pair_t', 'ch', 'mesh', 'name', 'p', 'kind', 'hid', 'vis', 'asset', 'scale', 'dead', 'born',
                 'still_p', 'still_t', 'area_p', 'area_t', 'stuck_t', 'dance', 'unr')


class Watch:
    def __init__(self, render=False):
        self.render = render
        self.g = {}
        self.t = 0.0
        self.t2 = 0.0
        self.t5 = 0.0
        self.counts = {}
        self.segs = []            # (stationary seconds, state)
        self.areas = []
        self.stuck = []
        self.pairs = []
        self.frames = 0
        self.dt_max = 0.0
        self.t0 = None
        self.room_samples = {}
        self.room_n = 0
        self.gap = {}
        self.cost = 0.0
        self.grace_until = 0.0
        self.state_time = {}
        self.events = 0
        self.h = unreal.register_slate_post_tick_callback(self.tick)
        log('watch started render', render)

    def stop(self):
        unreal.unregister_slate_post_tick_callback(self.h)

    def bump(self, k, n=1):
        self.counts[k] = self.counts.get(k, 0) + n

    def ev(self, kind, *a):
        self.bump(kind)
        self.events += 1
        if self.events < 400:
            log(kind, 't=%.1f' % self.t, *a)

    def world(self):
        for gi in unreal.ObjectIterator(unreal.GameInstance):
            if not gi.get_name().startswith('Default__'):
                return gi.get_world()

    def state(self, ch):
        try:
            c = ch.get_controller()
            if c is None:
                return 'client', ch.get_editor_property('DanceId')
            if ch.is_player_controlled():
                return 'player', 0
            if 'NPCController' not in c.get_class().get_name():
                return c.get_class().get_name()[6:16], 0
            m = c.get_editor_property('SocialMode')
            s = ['free', 'dance', 'bar', 'leave', 'seat', 'follow'][m] if 0 <= m <= 5 else 'm%d' % m
            try:
                lm = c.get_editor_property('LifeMode')
                if lm and m == 0:
                    s = 'life%d' % lm
            except Exception:
                pass
            if m == 4 and c.get_editor_property('SeatState') == 2:
                s = 'sitting'
            if c.get_editor_property('IsMoving'):
                s += '+mv'
            return s, ch.get_editor_property('DanceId')
        except Exception as e:
            return 'err', 0

    def tick(self, dt):
        t0 = time.perf_counter()
        try:
            self.step(dt)
        except Exception as e:
            self.bump('watcher_error')
            if self.counts['watcher_error'] < 5:
                log('watcher error', e)
        self.cost += time.perf_counter() - t0

    def step(self, dt):
        w = self.world()
        if w is None:
            return
        self.t += dt
        self.frames += 1
        self.dt_max = max(self.dt_max, dt)
        allc = unreal.GameplayStatics.get_all_actors_of_class(w, unreal.load_class(None, CHAR))
        seen = set()
        for ch in allc:
            n = ch.get_name()
            seen.add(n)
            g = self.g.get(n)
            if g is None:
                g = G()
                g.ch = ch
                g.mesh = ch.get_editor_property('mesh')
                g.name = n
                g.p = g.mesh.get_world_location()
                g.kind = ch.get_editor_property('Kind')
                g.vis = g.mesh.is_visible()
                g.hid = g.mesh.get_editor_property('hidden_in_game')
                a = g.mesh.get_skinned_asset()
                g.asset = a.get_name() if a else None
                g.scale = ch.get_actor_scale3d().x
                g.dead = ch.get_editor_property('IsDead')
                g.born = self.t
                g.still_p, g.still_t, g.area_p, g.area_t = g.p, self.t, g.p, self.t
                g.stuck_t = None
                g.pair_t = None
                g.unr = None
                self.g[n] = g
                if self.t > self.grace_until:
                    self.ev('APPEAR', n, 'at', self.fmt(g.p), 'kind', g.kind, self.near(g.p, w), g.asset)
                continue
            p = g.mesh.get_world_location()
            d = (p - g.p).length()
            lim = max(SPRINT * 1.25 * max(dt, 0.008) + 6.0, 40.0)      # below 40 cm: a stair step or the 20 Hz movement of a far guest, not a pop
            if d > lim and not g.dead and not ch.get_editor_property('IsDead'):
                st = self.state(ch)
                hd = ((p.x - g.p.x) ** 2 + (p.y - g.p.y) ** 2) ** 0.5
                self.ev('STEP' if hd <= lim else 'JUMP', n, 'd=%.0f' % d, 'dz=%.0f' % (p.z - g.p.z), 'dt=%.3f' % dt, 'state', st[0], 'dance', st[1], 'from', self.fmt(g.p), 'to', self.fmt(p), self.near(p, w))
            g.p = p
            v = g.mesh.is_visible()
            if v != g.vis:
                self.ev('MESHVIS', n, v, self.near(p, w))
                g.vis = v
            hg = g.mesh.get_editor_property('hidden_in_game')
            if hg != g.hid:
                self.ev('HIDE' if hg else 'UNHIDE', n, self.near(p, w))
                g.hid = hg
            sc = ch.get_actor_scale3d().x
            if abs(sc - g.scale) > 0.01:
                self.ev('SCALE', n, sc)
                g.scale = sc
            dd = ch.get_editor_property('IsDead')
            if dd and not g.dead:
                self.ev('DIED', n, self.near(p, w))
            g.dead = dd
            if p.z < -300 or p.z > 900:
                self.ev('OUTZ', n, self.fmt(p))
            if self.frames % 30 == 0:
                a = g.mesh.get_skinned_asset()
                an = a.get_name() if a else None
                if an != g.asset:
                    self.ev('ASSET', n, g.asset, '->', an, self.near(p, w))
                    g.asset = an
        for n in list(self.g):
            if n not in seen:
                g = self.g.pop(n)
                if self.t > self.grace_until:
                    self.ev('GONE', n, 'dead' if g.dead else 'alive', 'at', self.fmt(g.p), 'age %.0f' % (self.t - g.born), self.near(g.p, w))
        if self.t - self.t2 >= 0.5:
            self.t2 = self.t
            self.slow(w)
        if self.render and self.t - self.t5 >= 0.2:
            self.t5 = self.t
            self.rendered(w)

    def fmt(self, p):
        return '%d,%d,%d' % (p.x, p.y, p.z)

    def camera(self, w):
        pc = unreal.GameplayStatics.get_player_controller(w, 0)
        if pc is None:
            return None, None
        cm = pc.get_editor_property('player_camera_manager')
        return (cm.get_camera_location(), cm.get_camera_rotation()) if cm else (None, None)

    def near(self, p, w):
        cl, cr = self.camera(w)
        if cl is None:
            return ''
        d = (p - cl).length()
        f = unreal.MathLibrary.get_forward_vector(cr)
        to = (p - cl)
        dot = f.dot(to.normal()) if d > 1 else 1
        return 'cam=%dm%s' % (d / 100, ' INVIEW' if dot > 0.6 else '')

    def slow(self, w):
        for n, g in self.g.items():
            if g.dead or g.kind != 0 or g.ch.is_player_controlled():
                continue
            p = g.p
            if (p - g.still_p).length() > 25:
                if self.t - g.still_t >= 2.0:
                    self.segs.append((self.t - g.still_t, g.dance_state if False else self.last_state(g), n))
                g.still_p, g.still_t = p, self.t
            if (p - g.area_p).length() > 300:
                if self.t - g.area_t >= 2.0:
                    self.areas.append(self.t - g.area_t)
                g.area_p, g.area_t = p, self.t
            st, _ = self.state(g.ch)
            g.dance = st
            self.state_time[st] = self.state_time.get(st, 0) + 1
            for r in ROOMS:
                if r[1] <= p.x < r[3] and r[2] <= p.y < r[4]:
                    self.room_samples[r[0]] = self.room_samples.get(r[0], 0) + 1
                    break
            else:
                self.room_samples['outside'] = self.room_samples.get('outside', 0) + 1
            # NPC against NPC: wants to move, hardly moves, someone within reach
            vel = g.ch.get_velocity().length()
            blocked = False
            if st.endswith('+mv') and vel < 15:
                for m, o in self.g.items():
                    if m != n and not o.dead and (o.p - p).length() < 110:
                        blocked = True
                        break
            if blocked and not st.startswith('life7'):      # waiting in line is what a queue does
                if g.pair_t is None:
                    g.pair_t = self.t
            else:
                if g.pair_t is not None and self.t - g.pair_t >= 1.5 and not st.startswith('life7'):
                    self.pairs.append(self.t - g.pair_t)
                g.pair_t = None
            if st.endswith('+mv') and vel < 3:
                if g.stuck_t is None:
                    g.stuck_t = self.t
            else:
                if g.stuck_t is not None and self.t - g.stuck_t >= 1.0:
                    self.stuck.append(self.t - g.stuck_t)
                g.stuck_t = None
        self.room_n += 1

    def last_state(self, g):
        try:
            return g.dance
        except AttributeError:
            return '?'

    def rendered(self, w):
        cl, cr = self.camera(w)
        if cl is None:
            return
        f = unreal.MathLibrary.get_forward_vector(cr)
        for n, g in self.g.items():
            if g.dead:
                continue
            to = g.p + unreal.Vector(0, 0, 90) - cl
            d = to.length()
            inview = d < 2500 and d > 150 and f.dot(to.normal()) > 0.75
            rec = g.mesh.was_recently_rendered(0.15)
            if inview and not rec:
                hit = unreal.SystemLibrary.line_trace_single(w, cl, g.p + unreal.Vector(0, 0, 90), unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, False, [], unreal.DrawDebugTrace.NONE, True)
                blocked = hit is not None
                if blocked:
                    ha = hit.to_tuple()[9] if False else None
                g.unr = None if blocked else (g.unr or self.t)
                if not blocked and self.t - g.unr >= 0.4:
                    self.ev('NOTDRAWN', n, 'for %.1f' % (self.t - g.unr), 'd=%d' % d)
            else:
                if g.unr is not None and rec and self.t - g.unr >= 0.2:
                    self.bump('POPIN')
                g.unr = None


W = {}


def nw_start(render=False):
    def f(world, pc):
        W['w'] = Watch(render)
        W['w'].grace_until = W['w'].t + 2.0
    return f


def pct(v, q):
    v = sorted(v)
    return v[min(len(v) - 1, int(len(v) * q))] if v else 0


def nw_report(world, pc):
    w = W.get('w')
    if not w:
        return log('no watch')
    n = len([g for g in w.g.values() if not g.dead])
    log('REPORT t=%.0f frames %d fps %.1f worst dt %.2f guests alive %d' % (w.t, w.frames, w.frames / max(w.t, 1), w.dt_max, n), 'watcher ms/frame %.2f' % (1000 * w.cost / max(w.frames, 1)))
    log('events', sorted(w.counts.items()))
    segs = [s[0] for s in w.segs] + [w.t - g.still_t for g in w.g.values() if not g.dead and g.kind == 0 and w.t - g.still_t >= 2]
    area = w.areas + [w.t - g.area_t for g in w.g.values() if not g.dead and g.kind == 0 and w.t - g.area_t >= 2]
    log('still(<25cm) segments', len(segs), 'median %.0f p90 %.0f p99 %.0f max %.0f' % (pct(segs, .5), pct(segs, .9), pct(segs, .99), max(segs) if segs else 0))
    log('same area(<3m) segments', len(area), 'median %.0f p90 %.0f p99 %.0f max %.0f' % (pct(area, .5), pct(area, .9), pct(area, .99), max(area) if area else 0))
    by = {}
    for d, st, _ in w.segs:
        by.setdefault(st, []).append(d)
    log('still by end state', sorted((k, len(v), round(max(v))) for k, v in by.items()))
    stuck_now = [w.t - g.stuck_t for g in w.g.values() if g.stuck_t is not None]
    log('moving-but-not-moving', len(w.stuck), 'sum %.0f max %.0f; now' % (sum(w.stuck), max(w.stuck) if w.stuck else 0), len(stuck_now), 'max %.0f' % (max(stuck_now) if stuck_now else 0))
    pr = w.pairs + [w.t - g.pair_t for g in w.g.values() if g.pair_t is not None and w.t - g.pair_t >= 1.5]
    log('NPC-against-NPC stuck >=1.5s: episodes', len(pr), 'per min %.1f' % (60 * len(pr) / max(w.t, 1)), '>=3s', len([x for x in pr if x >= 3]), '>=6s', len([x for x in pr if x >= 6]), 'sum %.0f max %.0f' % (sum(pr), max(pr) if pr else 0))
    tot = max(sum(w.state_time.values()), 1)
    log('state share %', sorted(((k, round(100 * v / tot, 1)) for k, v in w.state_time.items()), key=lambda x: -x[1])[:14])
    log('room average', sorted(((k, round(v / max(w.room_n, 1), 1)) for k, v in w.room_samples.items()), key=lambda x: -x[1]))
    top = sorted(w.segs, key=lambda s: -s[0])[:6]
    log('longest ended still', [(round(a), b, c[-8:]) for a, b, c in top])
    cur = sorted(((w.t - g.still_t, n[-8:], w.fmt(g.p), g.dance if hasattr(g, 'dance') else '') for n, g in w.g.items() if not g.dead and g.kind == 0), key=lambda x: -x[0])[:6]
    log('longest still now', [(round(a), b, c, d) for a, b, c, d in cur])
    log('census', sorted(unreal_census(w).items(), key=lambda x: -x[1])[:80])


def unreal_census(w):
    c = {}
    for g in w.g.values():
        if g.kind == 0 and not g.dead:
            c[g.asset] = c.get(g.asset, 0) + 1
    return c
