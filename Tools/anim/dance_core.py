"""Pose solver for procedural dances on the UE5 mannequin skeleton (SK_Mannequin). Pure Python: the same code runs
offline (Tools/anim/dance_qa.py) and inside the editor (Tools/anim/build_dances.py).

Space: component (mesh) space in centimetres, +X = the character's left, +Y = forward, +Z = up, floor at Z = 0.
Quaternions are (x, y, z, w), Hamilton product; qmul(a, b) rotates by b, then by a (UE FQuat a * b).
Skeleton data: sk_mannequin.json (bones, reference local transforms, MM_Idle sampled; from Tools/chars/deform_dump.py).

A dance is a function t -> Pose parameters (see Pose below). solve(pose) turns them into local bone rotations:
- pelvis: offset + rotation on top of the relaxed idle pelvis;
- spine / neck: bend, side bend, twist spread over the vertebrae, in the body frame (so they follow the hips);
- clavicles: shrug / forward roll; arms: two-bone IK to a hand target given relative to the shoulder in the chest
  frame, with an elbow direction; hands: the idle wrist, or an explicit finger / palm direction; twist bones share
  the forearm roll (no candy wrapper at the wrist);
- legs: feet placed on the floor (position, toe-out yaw, heel or toe raise around the ball or heel, lift), two-bone
  IK with the knee aimed along the foot; the pelvis is lowered automatically if a planted foot would be out of reach,
  so a planted foot never leaves the floor; toes stay flat when the heel rises.
"""
import json
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))
X, Y, Z = (1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)


# ---------------------------------------------------------------- vectors
def vadd(a, b): return (a[0] + b[0], a[1] + b[1], a[2] + b[2])
def vsub(a, b): return (a[0] - b[0], a[1] - b[1], a[2] - b[2])
def vmul(a, s): return (a[0] * s, a[1] * s, a[2] * s)
def dot(a, b): return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]
def cross(a, b): return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])
def length(a): return math.sqrt(dot(a, a))
def lerp(a, b, t): return tuple(x + (y - x) * t for x, y in zip(a, b))


def unit(a):
    n = length(a)
    return (a[0] / n, a[1] / n, a[2] / n) if n > 1e-9 else (0.0, 0.0, 0.0)


# ---------------------------------------------------------------- quaternions
def qmul(a, b):
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    return (aw * bx + ax * bw + ay * bz - az * by,
            aw * by - ax * bz + ay * bw + az * bx,
            aw * bz + ax * by - ay * bx + az * bw,
            aw * bw - ax * bx - ay * by - az * bz)


def qconj(q): return (-q[0], -q[1], -q[2], q[3])


def qnorm(q):
    n = math.sqrt(sum(c * c for c in q))
    return tuple(c / n for c in q)


def qrot(q, v):
    u = (q[0], q[1], q[2])
    t = vmul(cross(u, v), 2.0)
    return vadd(vadd(v, vmul(t, q[3])), cross(u, t))


def qaxis(axis, deg):
    a = unit(axis)
    h = math.radians(deg) * 0.5
    s = math.sin(h)
    return (a[0] * s, a[1] * s, a[2] * s, math.cos(h))


QI = (0.0, 0.0, 0.0, 1.0)


def qangle(q):
    """Rotation angle in degrees (0..180)."""
    return math.degrees(2.0 * math.acos(min(1.0, abs(q[3]))))


def qslerp(a, b, t):
    d = sum(x * y for x, y in zip(a, b))
    if d < 0:
        b, d = tuple(-c for c in b), -d
    if d > 0.9995:
        return qnorm(tuple(x + (y - x) * t for x, y in zip(a, b)))
    th = math.acos(d)
    s = math.sin(th)
    wa, wb = math.sin((1 - t) * th) / s, math.sin(t * th) / s
    return tuple(wa * x + wb * y for x, y in zip(a, b))


def qpow(q, t):
    """q^t (scales the rotation angle; t may exceed 1)."""
    q = q if q[3] >= 0 else tuple(-c for c in q)
    ang = 2.0 * math.acos(min(1.0, q[3]))
    s = math.sqrt(max(0.0, 1.0 - q[3] * q[3]))
    if s < 1e-7:
        return QI
    axis = (q[0] / s, q[1] / s, q[2] / s)
    return qaxis(axis, math.degrees(ang * t))


def q_from_matrix(m):
    """m[row][col], columns = images of X, Y, Z."""
    tr = m[0][0] + m[1][1] + m[2][2]
    if tr > 0:
        s = math.sqrt(tr + 1.0) * 2
        q = ((m[2][1] - m[1][2]) / s, (m[0][2] - m[2][0]) / s, (m[1][0] - m[0][1]) / s, 0.25 * s)
    elif m[0][0] > m[1][1] and m[0][0] > m[2][2]:
        s = math.sqrt(1.0 + m[0][0] - m[1][1] - m[2][2]) * 2
        q = (0.25 * s, (m[0][1] + m[1][0]) / s, (m[0][2] + m[2][0]) / s, (m[2][1] - m[1][2]) / s)
    elif m[1][1] > m[2][2]:
        s = math.sqrt(1.0 + m[1][1] - m[0][0] - m[2][2]) * 2
        q = ((m[0][1] + m[1][0]) / s, 0.25 * s, (m[1][2] + m[2][1]) / s, (m[0][2] - m[2][0]) / s)
    else:
        s = math.sqrt(1.0 + m[2][2] - m[0][0] - m[1][1]) * 2
        q = ((m[0][2] + m[2][0]) / s, (m[1][2] + m[2][1]) / s, 0.25 * s, (m[1][0] - m[0][1]) / s)
    return qnorm(q)


def frame(xdir, yhint):
    x = unit(xdir)
    y = unit(vsub(yhint, vmul(x, dot(yhint, x))))
    return x, y, cross(x, y)


def q_between_frames(new, base):
    """Rotation R with R * base_i = new_i (orthonormal frames given as 3 axis vectors)."""
    m = [[sum(new[i][r] * base[i][c] for i in range(3)) for c in range(3)] for r in range(3)]
    return q_from_matrix(m)


def rot_body(fwd=0.0, side=0.0, turn=0.0):
    """Body-frame rotation: fwd > 0 tips the top forward (+Y), side > 0 tips it to the left (+X),
    turn > 0 turns the front to the left. Applied fwd, then side, then turn."""
    return qmul(qaxis(Z, -turn), qmul(qaxis(Y, side), qaxis(X, -fwd)))


def swing_twist_x(q):
    """Twist angle (degrees) of q around its local X axis."""
    return math.degrees(2.0 * math.atan2(q[0], q[3]))


# ---------------------------------------------------------------- skeleton
class Skeleton:
    def __init__(self, path=None):
        d = json.load(open(path or os.path.join(HERE, 'sk_mannequin.json')))
        self.names = [b['name'] for b in d['bones']]
        self.idx = {n: i for i, n in enumerate(self.names)}
        self.parent = [b['parent'] for b in d['bones']]
        self.ref_t = [tuple(b['local'][1]) for b in d['bones']]
        self.ref_q = [qnorm(tuple(b['local'][0])) for b in d['bones']]
        self.ref_world = [(qnorm(tuple(b['ref_world'][0])), tuple(b['ref_world'][1])) for b in d['bones']]
        self.idle = [[qnorm(tuple(f[0])) for f in fr] for fr in d['idle']]
        self.idle_pelvis_t = [tuple(fr[self.idx['pelvis']][1]) for fr in d['idle']]
        self.children = {}
        for i, p in enumerate(self.parent):
            self.children.setdefault(p, []).append(i)

    def i(self, name):
        return self.idx[name]

    def fk(self, lq, lt):
        n = len(lq)
        Q, P = [None] * n, [None] * n
        for i in range(n):
            p = self.parent[i]
            if p < 0:
                Q[i], P[i] = lq[i], lt[i]
            else:
                Q[i] = qnorm(qmul(Q[p], lq[i]))
                P[i] = vadd(P[p], qrot(Q[p], lt[i]))
        return Q, P


SPINE = ('spine_01', 'spine_02', 'spine_03', 'spine_04', 'spine_05')
SPINE_W = (0.16, 0.2, 0.22, 0.22, 0.2)
NECK = ('neck_01', 'neck_02', 'head')
NECK_W = (0.4, 0.3, 0.3)
FINGERS = ('index', 'middle', 'ring', 'pinky')


def ease(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


class Track:
    """Periodic key track. mode 'ease': smoothstep between keys (no overshoot, zero speed at keys: planted feet);
    'cr': Catmull-Rom (smooth). Values are floats or tuples."""

    def __init__(self, period, keys, mode='cr'):
        self.T = float(period)
        self.keys = sorted((k % self.T, v) for k, v in keys)
        self.mode = mode

    def __call__(self, t):
        T, ks = self.T, self.keys
        t %= T
        n = len(ks)
        j = 0
        while j < n and ks[j][0] <= t:
            j += 1
        i1 = (j - 1) % n
        i2 = j % n
        t1, v1 = ks[i1]
        t2, v2 = ks[i2]
        span = (t2 - t1) % T or T
        u = ((t - t1) % T) / span
        tup = isinstance(v1, tuple)
        if self.mode == 'ease':
            e = ease(u)
            return tuple(a + (b - a) * e for a, b in zip(v1, v2)) if tup else v1 + (v2 - v1) * e
        t0, v0 = ks[(i1 - 1) % n]
        t3, v3 = ks[(i2 + 1) % n]
        d0 = (t1 - t0) % T or T
        d2 = (t3 - t2) % T or T

        def cr(p0, p1, p2, p3):
            m1 = (p2 - p0) / (d0 + span) * span
            m2 = (p3 - p1) / (span + d2) * span
            u2, u3 = u * u, u * u * u
            return (2 * u3 - 3 * u2 + 1) * p1 + (u3 - 2 * u2 + u) * m1 + (-2 * u3 + 3 * u2) * p2 + (u3 - u2) * m2

        return tuple(cr(a, b, c, d) for a, b, c, d in zip(v0, v1, v2, v3)) if tup else cr(v0, v1, v2, v3)


def wave(t, period, phase=0.0):
    return math.sin(2 * math.pi * (t / period + phase))


# ---------------------------------------------------------------- pose
def Pose(**kw):
    """Defaults for every pose parameter (degrees, cm). Arms and feet are given for the LEFT side in 'out' coordinates
    (out = away from the body centre, fwd, up); the right side mirrors them.
      pelvis (dx, dy, dz) offset from the idle pelvis; pelvis_rot (fwd, side, turn)
      spine (fwd, side, turn); neck (fwd, side, turn)
      clav_l / clav_r (up, fwd): shrug and forward roll of the shoulder
      hand_l / hand_r (out, fwd, up): wrist target relative to the shoulder joint, in the chest frame
      elbow_l / elbow_r (out, fwd, up): where the elbow points
      wrist_l / wrist_r (flex, twist): extra wrist bend (palm side) and forearm roll, degrees
      palm_l / palm_r: None (relaxed idle wrist) or ((out, fwd, up) finger direction, (out, fwd, up) palm normal, weight)
      curl_l / curl_r: finger curl 0 = straight (flat hand), 1 = relaxed idle, 2 = fist; thumb_l / thumb_r likewise
      point_l / point_r: index finger curl override (None = same as curl)
      foot_l / foot_r: dict(x=out, y=fwd, yaw=toe-out deg, heel=heel raise deg (pivot ball), toe=toe raise deg (pivot
        heel), lift=cm) ; knee_l / knee_r: extra outward aim of the knee, degrees
    """
    p = dict(pelvis=(0.0, 0.0, 0.0), pelvis_rot=(0.0, 0.0, 0.0), spine=(3.0, 0.0, 0.0), neck=(5.0, 0.0, 0.0),
             clav_l=(0.0, 0.0), clav_r=(0.0, 0.0),
             hand_l=None, hand_r=None, elbow_l=(0.6, -0.6, -0.5), elbow_r=(0.6, -0.6, -0.5),
             wrist_l=(0.0, 0.0), wrist_r=(0.0, 0.0), palm_l=None, palm_r=None,
             curl_l=1.0, curl_r=1.0, thumb_l=1.0, thumb_r=1.0, point_l=None, point_r=None,
             foot_l=dict(x=11.0, y=0.0), foot_r=dict(x=11.0, y=0.0), knee_l=0.0, knee_r=0.0)
    p.update(kw)
    return p


class Solver:
    MAX_LEG = 0.995          # planted legs never straighter than this share of their length (pelvis drops instead)
    MAX_ARM = 0.985

    def __init__(self, sk=None):
        self.sk = sk or Skeleton()
        sk = self.sk
        self.lt = list(sk.ref_t)
        # relaxed base pose: idle frame 0 rotations, neutral (centred, level) pelvis
        self.base_lq = list(sk.idle[0])
        ip = sk.i('pelvis')
        self.base_lq[ip] = self._neutral_pelvis()
        for nm in SPINE + NECK:                     # the idle spine leans sideways (weight on one leg): use the
            self.base_lq[sk.i(nm)] = sk.ref_q[sk.i(nm)]   # symmetric reference spine, posture comes from Pose()
        self.base_pelvis_t = (0.0, sk.ref_t[ip][1] - 1.0, sk.ref_t[ip][2] - 0.8)
        lt = list(self.lt)
        lt[ip] = self.base_pelvis_t
        self.BQ, self.BP = sk.fk(self.base_lq, lt)
        BQ, BP = self.BQ, self.BP
        # leg geometry
        self.leg = {}
        for s in ('l', 'r'):
            th, ca, fo, ba = (sk.i(f'{n}_{s}') for n in ('thigh', 'calf', 'foot', 'ball'))
            a, b = length(sk.ref_t[ca]), length(sk.ref_t[fo])
            rq_foot, rp_foot = sk.ref_world[fo]
            rp_ball = sk.ref_world[ba][1]
            fwd = unit((rp_ball[0] - rp_foot[0], rp_ball[1] - rp_foot[1], 0.0))
            yaw0 = math.degrees(math.atan2(abs(fwd[0]), fwd[1]))            # reference toe-out
            self.leg[s] = dict(th=th, ca=ca, fo=fo, ba=ba, a=a, b=b, ankle_h=rp_foot[2], foot_q=rq_foot,
                               ball_off=vsub(rp_ball, rp_foot), yaw0=yaw0, sign=1.0 if s == 'l' else -1.0)
        # base leg frames: the reference pose (template legs, knees forward)
        RW = sk.ref_world
        for s, L in self.leg.items():
            hip, knee, ank = RW[L['th']][1], RW[L['ca']][1], RW[L['fo']][1]
            L['F_th'] = frame(vsub(knee, hip), Y)
            L['F_ca'] = frame(vsub(ank, knee), Y)
            L['Q_th'], L['Q_ca'] = RW[L['th']][0], RW[L['ca']][0]
        # arms
        self.arm = {}
        for s in ('l', 'r'):
            cl, ua, la, ha = (sk.i(f'{n}_{s}') for n in ('clavicle', 'upperarm', 'lowerarm', 'hand'))
            S, E, W = BP[ua], BP[la], BP[ha]
            mid = vadd(S, vmul(unit(vsub(W, S)), dot(vsub(E, S), unit(vsub(W, S)))))
            pole = unit(vsub(E, mid))
            mc_i, mc_p = BP[sk.i(f'index_metacarpal_{s}')], BP[sk.i(f'pinky_metacarpal_{s}')]
            fing = unit(vsub(BP[sk.i(f'middle_01_{s}')], W))
            across = vsub(mc_i, mc_p)
            palm = unit(cross(fing, across)) if s == 'r' else unit(vmul(cross(fing, across), -1.0))
            self.arm[s] = dict(cl=cl, ua=ua, la=la, ha=ha, a=length(sk.ref_t[la]), b=length(sk.ref_t[ha]),
                               F_ua=frame(vsub(E, S), pole), F_la=frame(vsub(W, E), pole),
                               Q_ua=BQ[ua], Q_la=BQ[la], Q_ha=BQ[ha], F_ha=frame(fing, palm),
                               sign=1.0 if s == 'l' else -1.0,
                               tw1=sk.i(f'lowerarm_twist_01_{s}'), tw2=sk.i(f'lowerarm_twist_02_{s}'))
        self.stats = dict(pelvis_drops=0, frames=0, max_drop=0.0)

    def _neutral_pelvis(self):
        """Idle pelvis rotation with its sideways tilt and turn removed (keeps the forward tilt)."""
        sk = self.sk
        ip = sk.i('pelvis')
        ref = sk.ref_q[ip]
        idle = qnorm(sk.idle[0][ip])
        # forward axis of the pelvis frame = its local direction mapped; keep only the pitch difference
        d = qmul(idle, qconj(ref))
        up_ref = (0.0, 0.0, 1.0)
        up = qrot(d, up_ref)
        pitch = math.degrees(math.atan2(up[1], up[2]))                    # top toward +Y
        return qnorm(qmul(rot_body(fwd=pitch * 0.6), ref))

    # ------------------------------------------------------------ helpers
    @staticmethod
    def mirror(v, sign):
        return (v[0] * sign, v[1], v[2])

    def foot_target(self, s, f):
        """Ankle position + foot rotation (component space) for a foot placement dict."""
        L = self.leg[s]
        sg = L['sign']
        x, y = f.get('x', 11.0) * sg, f.get('y', 0.0)
        yaw = f.get('yaw', 0.0)
        qy = qaxis(Z, -yaw * sg)                                          # toe-out: left toe turns to +X
        if f.get('pivot') == 'ball':                                      # swivel on the ball of the foot
            bo = (L['ball_off'][0], L['ball_off'][1], 0.0)
            ball0 = vadd((x, y, 0.0), qrot(qaxis(Z, -f.get('rest_yaw', 0.0) * sg), bo))
            bxy = qrot(qy, bo)
            x, y = ball0[0] - bxy[0], ball0[1] - bxy[1]
        base = (x, y, L['ankle_h'] + f.get('lift', 0.0))
        fq = qmul(qy, L['foot_q'])
        fdir = unit(qrot(qy, unit((L['ball_off'][0], L['ball_off'][1], 0.0))))
        lat = unit(cross(Z, fdir))                                        # heel raise = + rotation about lat
        heel, toe = f.get('heel', 0.0), f.get('toe', 0.0)
        ankle = base
        ball_fix = QI
        if heel > 0.0:
            piv = vadd(base, qrot(qy, L['ball_off']))
            r = qaxis(lat, heel)
            ankle = vadd(piv, qrot(r, vsub(base, piv)))
            fq = qmul(r, fq)
            ball_fix = qaxis(lat, -heel)                                  # toes stay flat on the floor
        elif toe > 0.0:
            piv = vadd(base, vadd(vmul(fdir, -4.5), (0.0, 0.0, -L['ankle_h'] + 0.5)))
            r = qaxis(lat, -toe)
            ankle = vadd(piv, qrot(r, vsub(base, piv)))
            fq = qmul(r, fq)
        if f.get('point', 0.0):                                           # pointed foot in the air (kicks)
            r = qaxis(lat, f['point'])
            fq = qmul(r, fq)
            ball_fix = qmul(qaxis(lat, f['point'] * 0.3), ball_fix)
        return ankle, fq, fdir, ball_fix

    @staticmethod
    def two_bone(root, target, a, b, pole, maxr):
        d_vec = vsub(target, root)
        d = length(d_vec)
        d = min(max(d, abs(a - b) + 1e-3), (a + b) * maxr)
        u = unit(d_vec)
        cos_a = (a * a + d * d - b * b) / (2 * a * d)
        sin_a = math.sqrt(max(0.0, 1 - cos_a * cos_a))
        v = unit(vsub(pole, vmul(u, dot(pole, u))))
        mid = vadd(root, vadd(vmul(u, a * cos_a), vmul(v, a * sin_a)))
        end = vadd(root, vmul(u, d))
        return mid, end, v

    # ------------------------------------------------------------ solve
    def solve(self, P):
        sk = self.sk
        lq = list(self.base_lq)
        lt = list(self.lt)
        ip = sk.i('pelvis')
        Q = [None] * len(lq)
        # pelvis
        R_acc = rot_body(*P['pelvis_rot'])
        pel_t = vadd(self.base_pelvis_t, P['pelvis'])
        # feet first: lower the pelvis if a foot would be out of reach
        feet = {s: self.foot_target(s, P[f'foot_{s}']) for s in ('l', 'r')}
        drop = 0.0
        for _ in range(3):
            worst = 0.0
            for s, L in self.leg.items():
                hip = vadd(pel_t, qrot(R_acc, qrot(qconj(rot_body()), vsub(self.BP[L['th']], self.base_pelvis_t))))
                hip = vadd(vsub(hip, (0, 0, drop)), (0, 0, 0))
                reach = (L['a'] + L['b']) * self.MAX_LEG
                dv = vsub(feet[s][0], hip)
                if length(dv) > reach:
                    # extra drop so that |dv + (0,0,e)| = reach
                    h2 = dv[0] ** 2 + dv[1] ** 2
                    need = -dv[2] - math.sqrt(max(0.0, reach * reach - h2))
                    worst = max(worst, need + 0.05)
            if worst <= 0:
                break
            drop += worst
        self.stats['frames'] += 1
        if drop > 0:
            self.stats['pelvis_drops'] += 1
            self.stats['max_drop'] = max(self.stats['max_drop'], drop)
        pel_t = vsub(pel_t, (0, 0, drop))
        lt[ip] = pel_t
        Q[ip] = qmul(R_acc, self.BQ[ip])
        lq[ip] = Q[ip]
        # spine
        sf, ss, st = P['spine']
        for name, w in zip(SPINE, SPINE_W):
            i = sk.i(name)
            d_body = rot_body(sf * w, ss * w, st * w)
            d_world = qmul(qmul(R_acc, d_body), qconj(R_acc))
            inherited = qmul(Q[sk.parent[i]], self.base_lq[i])
            Q[i] = qnorm(qmul(d_world, inherited))
            lq[i] = qnorm(qmul(qconj(Q[sk.parent[i]]), Q[i]))
            R_acc = qmul(R_acc, d_body)
        R_chest = R_acc
        nf, ns, nt = P['neck']
        R_n = R_chest
        for name, w in zip(NECK, NECK_W):
            i = sk.i(name)
            d_body = rot_body(nf * w, ns * w, nt * w)
            d_world = qmul(qmul(R_n, d_body), qconj(R_n))
            inherited = qmul(Q[sk.parent[i]], self.base_lq[i])
            Q[i] = qnorm(qmul(d_world, inherited))
            lq[i] = qnorm(qmul(qconj(Q[sk.parent[i]]), Q[i]))
            R_n = qmul(R_n, d_body)
        # FK so far (for the shoulder and hip positions)
        Qf, Pf = sk.fk(lq, lt)
        # clavicles + arms
        for s, A in self.arm.items():
            sg = A['sign']
            up, fw = P[f'clav_{s}']
            i = A['cl']
            d_body = qmul(qaxis(Y, -up * sg), qaxis(Z, fw * sg))           # up: outer end up; fwd: toward +Y
            d_world = qmul(qmul(R_chest, d_body), qconj(R_chest))
            Qc = qnorm(qmul(d_world, qmul(Qf[sk.parent[i]], self.base_lq[i])))
            lq[i] = qnorm(qmul(qconj(Qf[sk.parent[i]]), Qc))
            S = vadd(Pf[i], qrot(Qc, lt[A['ua']]))
            hand = P[f'hand_{s}']
            if hand is None:
                # relaxed arm: the idle arm carried by the chest
                Dc = qmul(R_chest, QI)
                tgt = vadd(S, qrot(Dc, vsub(self.BP[A['ha']], self.BP[A['ua']])))
                pole = qrot(Dc, A['F_ua'][1])
            else:
                tgt = vadd(S, qrot(R_chest, self.mirror(hand, sg)))
                pole = qrot(R_chest, unit(self.mirror(P[f'elbow_{s}'], sg)))
            E, W, bend = self.two_bone(S, tgt, A['a'], A['b'], pole, self.MAX_ARM)
            # frames from the bend direction (stable even when the upper arm points along the pole)
            Qua = qmul(q_between_frames(frame(vsub(E, S), bend), A['F_ua']), A['Q_ua'])
            Qla = qmul(q_between_frames(frame(vsub(W, E), bend), A['F_la']), A['Q_la'])
            pole = bend
            lq[A['ua']] = qnorm(qmul(qconj(Qc), Qua))
            lq[A['la']] = qnorm(qmul(qconj(Qua), Qla))
            # hand
            Qha = qmul(Qla, self.base_lq[A['ha']])
            flex, roll = P[f'wrist_{s}']
            fa = unit(vsub(W, E))
            if roll:
                Qha = qmul(qaxis(fa, roll * sg), Qha)
            if flex:
                hinge = frame(fa, pole)[2]
                Qha = qmul(qaxis(hinge, flex * sg), Qha)
            pm = P[f'palm_{s}']
            if pm:
                fd, pn, w = pm
                Ft = frame(qrot(R_chest, unit(self.mirror(fd, sg))), qrot(R_chest, unit(self.mirror(pn, sg))))
                Qex = qmul(q_between_frames(Ft, A['F_ha']), A['Q_ha'])
                Qha = qslerp(Qha, Qex, w)
            lq[A['ha']] = qnorm(qmul(qconj(Qla), Qha))
            # forearm roll shared with the twist bones (local X is the bone axis)
            tw = swing_twist_x(qmul(qconj(self.base_lq[A['ha']]), lq[A['ha']]))
            if abs(tw) > 1.0:
                for bi, share in ((A['tw1'], 0.66), (A['tw2'], 0.33)):
                    lq[bi] = qnorm(qmul(self.base_lq[bi], qaxis(X, tw * share)))
            # fingers
            c, th, pt = P[f'curl_{s}'], P[f'thumb_{s}'], P[f'point_{s}']
            for fn in FINGERS:
                for k in ('metacarpal', '01', '02', '03'):
                    nm = f'{fn}_{k}_{s}'
                    bi = sk.i(nm)
                    cc = c if not (fn == 'index' and pt is not None) else pt
                    if k == 'metacarpal':
                        cc = min(cc, 1.0)
                    lq[bi] = self._curl(bi, cc)
            for k in ('01', '02', '03'):
                bi = sk.i(f'thumb_{k}_{s}')
                lq[bi] = self._curl(bi, th)
        # legs
        Qf, Pf = sk.fk(lq, lt)
        for s, L in self.leg.items():
            ankle, fq, fdir, ball_fix = feet[s]
            hip = Pf[L['th']]
            sg = L['sign']
            kd = qrot(qaxis(Z, -P[f'knee_{s}'] * sg), fdir)
            pole = unit(vadd(kd, (0.0, 0.0, 0.05)))
            K, A_, bend = self.two_bone(hip, ankle, L['a'], L['b'], pole, 0.9995)
            Qth = qmul(q_between_frames(frame(vsub(K, hip), bend), L['F_th']), L['Q_th'])
            Qca = qmul(q_between_frames(frame(vsub(A_, K), bend), L['F_ca']), L['Q_ca'])
            pi = sk.parent[L['th']]
            lq[L['th']] = qnorm(qmul(qconj(Qf[pi]), Qth))
            lq[L['ca']] = qnorm(qmul(qconj(Qth), Qca))
            lq[L['fo']] = qnorm(qmul(qconj(Qca), fq))
            ball_cs = qmul(ball_fix, qmul(fq, sk.ref_q[L['ba']]))
            lq[L['ba']] = qnorm(qmul(qconj(fq), ball_cs))
            # thigh / calf twist bones: keep the reference (the IK has no thigh roll beyond the knee aim)
            for nm in (f'thigh_twist_01_{s}', f'thigh_twist_02_{s}', f'calf_twist_01_{s}', f'calf_twist_02_{s}'):
                lq[sk.i(nm)] = sk.ref_q[sk.i(nm)]
        # ik bones follow the feet and hands (UE convention), so anything reading them sees the dance
        Qf, Pf = sk.fk(lq, lt)
        for s in ('l', 'r'):
            fo, ik = sk.i(f'foot_{s}'), sk.i(f'ik_foot_{s}')
            lq[ik], lt[ik] = Qf[fo], Pf[fo]
        hr, hl = sk.i('hand_r'), sk.i('hand_l')
        g = sk.i('ik_hand_gun')
        lq[g], lt[g] = Qf[hr], Pf[hr]
        inv = qconj(Qf[hr])
        lq[sk.i('ik_hand_l')] = qnorm(qmul(inv, Qf[hl]))
        lt[sk.i('ik_hand_l')] = qrot(inv, vsub(Pf[hl], Pf[hr]))
        lq[sk.i('ik_hand_r')], lt[sk.i('ik_hand_r')] = QI, (0.0, 0.0, 0.0)
        for nm in ('root', 'ik_foot_root', 'ik_hand_root', 'interaction', 'center_of_mass'):
            lq[sk.i(nm)], lt[sk.i(nm)] = QI, (0.0, 0.0, 0.0)
        return [qnorm(q) for q in lq], lt

    def _curl(self, bi, c):
        ref = self.sk.ref_q[bi]
        idle = self.base_lq[bi]
        d = qmul(qconj(ref), idle)
        return qnorm(qmul(ref, qpow(d, c)))


def bake(dance, solver=None, fps=30):
    """dance: object with .length (s) and .pose(t). Returns (frames, list of (local rotations, local translations))
    with frames + 1 keys, the last equal to the first (seamless loop)."""
    solver = solver or Solver()
    n = int(round(dance.length * fps))
    keys = [solver.solve(dance.pose(k / fps)) for k in range(n)]
    keys.append(keys[0])
    return n, keys
