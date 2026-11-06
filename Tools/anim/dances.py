"""The 1930s dances (choreography as functions of time). Each is a looping clip at 30 fps whose last key equals the
first; every one starts close to a standing pose so that switching from the idle does not jump much.

DANCES order = DanceId - 1 in the game (BP_GW_Character.DanceId): 1 Charleston, 2 Lindy Hop, 3 Valse lente,
4 Shimmy, 5 Truckin'. Pair dances (NPC couples facing each other): 1, 2, 3.
Coordinates for feet and hands are given for each side as (out, fwd, up): out = away from the body centre.
"""
import math
from dance_core import Pose, Track, wave, ease


def foot_path(T, plants, x0=None, y0=None, yaw0=None):
    """plants: list of (t_lift, t_land, x, y, yaw, arc_cm[, z_cm]): the foot leaves its previous spot at t_lift and
    reaches (x, y, yaw) at height z (0 = planted on the floor; > 0 = held in the air, e.g. a kick) at t_land, rising
    arc_cm above the straight path on the way. Returns f(t) -> dict(x, y, yaw, lift, air). No sliding when planted."""
    pts, zk = [], []
    prev = plants[-1]
    for pl in plants:
        tl, td, x, y, yaw, h = pl[:6]
        z = pl[6] if len(pl) > 6 else 0.0
        pz = prev[6] if len(prev) > 6 else 0.0
        pts.append((tl, (prev[2], prev[3], prev[4])))
        pts.append((td, (x, y, yaw)))
        mid = (tl + td) / 2 if td > tl else ((tl + td + T) / 2) % T
        zk += [(tl, pz), (mid, max(pz, z) + h), (td, z)]
        prev = pl
    pos = Track(T, pts, 'ease')
    lift = Track(T, zk, 'ease')

    def f(t):
        x, y, yaw = pos(t)
        z = max(0.0, lift(t))
        return dict(x=x, y=y, yaw=yaw, lift=z, air=z > 0.05)
    return f


class Charleston:
    """Basic Charleston: step forward on the left, kick the right forward, step back on the right, tap the left
    behind; the supporting foot swivels on its ball, a bounce on every count, arms swinging, open hands."""
    name, label, length = 'Charleston', 'Charleston', 2.0

    def __init__(self):
        T = self.length
        self.L = [(1.02, 1.46, 11.0, -15.0, 5.0, 6.0), (1.54, 1.98, 11.0, 15.0, 8.0, 5.0)]
        self.R = [(0.04, 0.44, 12.0, 30.0, 6.0, 3.0, 15.0),           # kick: held in the air at 15 cm
                  (0.56, 0.97, 11.0, 0.0, 8.0, 2.0)]
        self.fl, self.fr = foot_path(T, self.L), foot_path(T, self.R)
        self.pel = Track(T, [(0.0, (3.0, 8.0)), (0.5, (4.0, 9.0)), (1.0, (-3.0, 2.0)), (1.5, (-4.0, -1.0))], 'cr')
        self.tap = Track(T, [(1.0, 0.0), (1.42, 30.0), (1.54, 30.0), (1.7, 0.0)], 'ease')
        self.kick = Track(T, [(0.04, 0.0), (0.44, 34.0), (0.56, 30.0), (0.97, 0.0)], 'ease')

    def pose(self, t):
        T = self.length
        u = t % T
        fl, fr = self.fl(t), self.fr(t)
        # swivel of the supporting foot on its ball: left during counts 1-2, right during 3-4 (fades at the ends)
        if u < 1.0:
            fl.update(rest_yaw=fl['yaw'], pivot='ball', heel=8.0 * math.sin(math.pi * u))
            fl['yaw'] += 15.0 * math.sin(2 * math.pi * u)
        else:
            v = u - 1.0
            fr.update(rest_yaw=fr['yaw'], pivot='ball', heel=8.0 * math.sin(math.pi * v))
            fr['yaw'] += 15.0 * math.sin(2 * math.pi * v)
        tap = self.tap(t)
        if tap > 0:
            fl['heel'] = max(fl.get('heel', 0.0), tap)
            fl.pop('pivot', None)
        fr['point'] = self.kick(t)
        px, py = self.pel(t)
        bounce = 0.5 + 0.5 * math.cos(2 * math.pi * t / 0.5)          # 1 on the counts
        sing = wave(t, 1.0)                                            # arm swing
        fw, bk = (14.0, 30.0, -37.0), (17.0, -20.0, -42.0)
        mix = lambda a, b, k: tuple(x + (y - x) * k for x, y in zip(a, b))
        return Pose(
            pelvis=(px, py, -1.5 - 3.0 * bounce), pelvis_rot=(3.0, -2.0 * math.sin(2 * math.pi * t / T), 7.0 * math.sin(2 * math.pi * t / 1.0)),
            spine=(9.0 + 2.0 * bounce, 2.5 * math.sin(2 * math.pi * t / T), -9.0 * math.sin(2 * math.pi * t / 1.0)),
            neck=(-2.0 + 2.5 * bounce, -2.0 * math.sin(2 * math.pi * t / T), 4.0 * math.sin(2 * math.pi * t / 1.0)),
            clav_l=(2.0, 4.0 * sing), clav_r=(2.0, -4.0 * sing),
            hand_l=mix(bk, fw, 0.5 + 0.5 * sing), hand_r=mix(bk, fw, 0.5 - 0.5 * sing),
            elbow_l=(0.5, -0.8, -0.4), elbow_r=(0.5, -0.8, -0.4),
            wrist_l=(-10.0, 0.0), wrist_r=(-10.0, 0.0),
            curl_l=0.25, curl_r=0.25, thumb_l=0.4, thumb_r=0.4,
            foot_l=fl, foot_r=fr, knee_l=4.0, knee_r=4.0)


class Lindy:
    """East-coast swing basic, Lindy style: rock step back, two triple steps (left, right), a pulse on every count,
    leaning in, right hand forward as if holding the partner's, free arm swinging out on the rock step."""
    name, label, length = 'Lindy', 'Lindy hop', 2.8

    def __init__(self):
        T, c = self.length, self.length / 6.0
        self.c = c
        # (t_lift, t_land, out, fwd, yaw, lift)
        self.L = [(T - 0.22, 0.0, 11.0, -22.0, 10.0, 5.0),            # 1: rock back
                  (0.62, 2 * c, 16.0, 0.0, 6.0, 5.0),                  # 3: triple left
                  (2 * c + 0.06, 2.5 * c - 0.02, 14.0, 1.0, 6.0, 2.5),   # &
                  (2.5 * c + 0.06, 3 * c, 17.0, 0.0, 8.0, 2.5),          # 4
                  (3.5 * c + 0.04, 4.5 * c - 0.02, 4.0, 0.0, 6.0, 3.0)]  # & (closes under the right triple)
        self.R = [(1.5 * c + 0.06, 2.5 * c - 0.04, 4.0, 1.0, 6.0, 3.5),  # & of 3 (closes)
                  (3 * c + 0.12, 4 * c, 17.0, 0.0, 8.0, 5.0),          # 5: triple right
                  (4.5 * c + 0.04, 5 * c, 15.0, 1.0, 6.0, 2.5)]          # 6
        self.fl, self.fr = foot_path(T, self.L), foot_path(T, self.R)
        # weight: back on the rock step, back to the right, left during the left triple, right during the right one
        self.pel = Track(T, [(0.0, (1.0, -8.0)), (c, (-3.0, 0.0)), (2 * c, (4.0, 0.5)), (3 * c, (6.0, 0.5)),
                             (4 * c, (-4.0, 0.5)), (5 * c, (-6.0, 0.5)), (T - 0.2, (-3.0, -2.0))], 'cr')
        self.turn = Track(T, [(0.0, -10.0), (c, 0.0), (3 * c, 6.0), (5 * c, -6.0)], 'cr')
        self.rockheel = Track(T, [(T - 0.22, 0.0), (0.0, 12.0), (0.5 * c, 12.0), (0.62, 0.0)], 'ease')

    def pose(self, t):
        T, c = self.length, self.c
        fl, fr = self.fl(t), self.fr(t)
        fl['heel'] = self.rockheel(t)                                 # rock step on the ball of the foot
        px, py = self.pel(t)
        pulse = 0.5 + 0.5 * math.cos(2 * math.pi * t / c)
        rock = (0.5 + 0.5 * math.cos(2 * math.pi * t / T)) ** 6        # 1 on the rock step
        tr = self.turn(t)
        sw = wave(t, 2 * c)
        return Pose(
            pelvis=(px, py, -3.0 - 3.0 * pulse), pelvis_rot=(4.0, 2.0 * sw, tr * 0.6),
            spine=(11.0 + 2.0 * pulse - 4.0 * rock, -2.0 * sw, -tr * 0.4),
            neck=(-4.0 + 1.5 * pulse, 1.0 * sw, -tr * 0.3),
            clav_l=(1.0 + 1.5 * pulse, 2.0 * sw), clav_r=(1.0 + 1.5 * pulse, -2.0 * sw),
            hand_r=(6.0, 30.0 - 3.0 * pulse, -30.0 + 2.0 * pulse), elbow_r=(0.5, -0.6, -0.6),
            hand_l=(20.0 + 10.0 * rock, 4.0 - 14.0 * rock + 4.0 * sw, -36.0 + 8.0 * rock), elbow_l=(0.7, -0.6, -0.4),
            palm_r=((0.0, 1.0, -0.2), (-1.0, 0.0, -0.3), 0.7),
            curl_l=0.7, curl_r=1.3, thumb_r=1.2,
            foot_l=fl, foot_r=fr, knee_l=6.0, knee_r=6.0)


class Valse:
    """Slow waltz box step with rise and fall, in a mimed closed hold (left hand raised holding the partner's, right
    hand on the partner's back), head turned to the left; facing a partner ~1 m away the hands nearly meet."""
    name, label, length = 'Valse', 'Valse lente', 4.0

    def __init__(self):
        T, c = self.length, self.length / 6.0
        self.c = c
        d = 0.42
        # absolute (left +X) positions -> out coordinates: left foot out = x, right foot out = -x
        self.L = [(-d, 0.0, 9.0, 13.0, 4.0, 3.0),          # 1 forward
                  (2 * c - d, 2 * c, 3.0, 13.0, 4.0, 2.0),    # 3 close (beside the right)
                  (4 * c - d, 4 * c, 9.0, -13.0, 4.0, 3.0)]   # 5 side-back (home)
        self.R = [(c - d, c, 15.0, 13.0, 4.0, 3.0),         # 2 side-forward
                  (3 * c - d, 3 * c, 15.0, -13.0, 4.0, 3.0),  # 4 back
                  (5 * c - d, 5 * c, 9.0, -13.0, 4.0, 2.0)]   # 6 close
        self.fl, self.fr = foot_path(T, self.L), foot_path(T, self.R)
        # rise and fall: down on 1 / 4, rising through 2-3 / 5-6
        self.rise = Track(T, [(0.0, 0.0), (c, 0.6), (2 * c, 1.0), (2.75 * c, 0.15), (3 * c, 0.0),
                              (4 * c, 0.6), (5 * c, 1.0), (5.75 * c, 0.15)], 'cr')
        wl, wr = (9.0, 13.0), (-15.0, 13.0)
        self.pel = Track(T, [(0.0, (7.0, 11.0)), (c, (-9.0, 12.0)), (2 * c, (-3.0, 12.0)), (3 * c, (-10.0, -10.0)),
                             (4 * c, (6.0, -11.0)), (5 * c, (-3.0, -11.0))], 'cr')

    def pose(self, t):
        T, c = self.length, self.c
        fl, fr = self.fl(t), self.fr(t)
        r = min(1.0, max(0.0, self.rise(t)))
        fl['heel'] = 13.0 * r * max(0.0, 1.0 - fl['lift'] / 2.0)      # fades in as the foot lands
        fr['heel'] = 13.0 * r * max(0.0, 1.0 - fr['lift'] / 2.0)
        px, py = self.pel(t)
        sway = math.sin(2 * math.pi * t / (2 * c * 3))
        turn = 7.0 * math.sin(2 * math.pi * t / T)
        return Pose(
            pelvis=(px * 0.55, py * 0.55, -4.0 + 5.5 * r), pelvis_rot=(1.0, 2.0 * sway, turn * 0.5),
            spine=(-1.0, -3.5 * sway, turn * 0.5), neck=(-4.0, 3.0, 16.0 + turn * 0.3),
            clav_l=(3.0, 0.0), clav_r=(1.0, 2.0),
            hand_l=(32.0, 22.0, 12.0), elbow_l=(0.35, -0.25, -0.9),
            palm_l=((0.0, 0.25, 1.0), (0.15, 1.0, 0.0), 0.9),
            hand_r=(-6.0, 33.0, -17.0), elbow_r=(0.85, 0.1, -0.15),
            palm_r=((-1.0, 0.25, 0.0), (0.0, 1.0, 0.1), 0.85),
            curl_l=0.8, curl_r=0.35, thumb_r=0.6,
            foot_l=fl, foot_r=fr, knee_l=2.0, knee_r=2.0)


class Shimmy:
    """Shimmy: wide stance, knees bouncing, hips swaying, shoulders shaking fast, jazz hands up by the face."""
    name, label, length = 'Shimmy', 'Shimmy', 2.0

    def pose(self, t):
        T = self.length
        shake = math.sin(2 * math.pi * t * 4.0)                       # 8 shakes per loop
        slow = math.sin(2 * math.pi * t / T)
        hip = math.sin(2 * math.pi * t / 1.0)
        bounce = 0.5 + 0.5 * math.cos(2 * math.pi * t / 0.5)
        sink = 0.5 - 0.5 * math.cos(2 * math.pi * t / T)
        jazz = math.sin(2 * math.pi * t * 6.0)
        return Pose(
            pelvis=(4.0 * slow, 0.0, -4.0 - 2.0 * bounce - 3.0 * sink), pelvis_rot=(2.0, 5.0 * hip, 8.0 * slow),
            spine=(-3.0 + 2.0 * sink, -4.0 * hip, -6.0 * slow + 4.0 * shake), neck=(1.0, 4.0 * slow, 3.0 * slow - 2.0 * shake),
            clav_l=(5.0 + 2.0 * shake, 9.0 * shake), clav_r=(5.0 - 2.0 * shake, -9.0 * shake),
            hand_l=(22.0, 19.0, 4.0 + 3.0 * sink), elbow_l=(0.6, -0.2, -0.8),
            hand_r=(22.0, 19.0, 4.0 + 3.0 * sink), elbow_r=(0.6, -0.2, -0.8),
            palm_l=((0.35, 0.0, 1.0), (0.0, 1.0, 0.0), 1.0), palm_r=((0.35, 0.0, 1.0), (0.0, 1.0, 0.0), 1.0),
            wrist_l=(0.0, 14.0 * jazz), wrist_r=(0.0, -14.0 * jazz),
            curl_l=0.0, curl_r=0.0, thumb_l=0.2, thumb_r=0.2,
            foot_l=dict(x=17.0, y=0.0, yaw=16.0, heel=9.0 * max(0.0, hip)),
            foot_r=dict(x=17.0, y=0.0, yaw=16.0, heel=9.0 * max(0.0, -hip)),
            knee_l=8.0, knee_r=8.0)


class Truckin:
    """Truckin' (Cotton Club, 1935): shuffling steps in place with the heel swinging out, hips rolling, right index
    finger raised and wagging, left hand on the hip, leaning back, strutting."""
    name, label, length = 'Truckin', "Truckin'", 2.0

    def __init__(self):
        T = self.length
        self.L = [(1.74, 1.98, 11.0, 5.0, 26.0, 4.0), (0.76, 0.98, 11.0, -3.0, -4.0, 3.0)]
        self.R = [(0.24, 0.48, 11.0, 5.0, 26.0, 4.0), (1.26, 1.48, 11.0, -3.0, -4.0, 3.0)]
        self.fl, self.fr = foot_path(T, self.L), foot_path(T, self.R)

    def pose(self, t):
        T = self.length
        fl, fr = self.fl(t), self.fr(t)
        side = math.cos(2 * math.pi * t / 1.0)                        # +1: weight on the left (t = 0, 1)
        bounce = 0.5 + 0.5 * math.cos(2 * math.pi * t / 0.5)
        wag = math.sin(2 * math.pi * t / 0.5)
        return Pose(
            pelvis=(4.0 * side, 0.0, -3.0 - 2.5 * bounce), pelvis_rot=(-2.0, -6.0 * side, 10.0 * math.sin(2 * math.pi * t / 1.0)),
            spine=(-5.0, 4.0 * side, -8.0 * math.sin(2 * math.pi * t / 1.0)), neck=(-3.0 + 2.0 * bounce, -3.0 * side, 6.0 * math.sin(2 * math.pi * t / 1.0)),
            clav_l=(6.0, 5.0), clav_r=(9.0 + 2.0 * bounce, 3.0),
            hand_r=(8.0 + 6.0 * wag, 12.0, 41.0), elbow_r=(0.9, 0.1, -0.2),
            palm_r=((0.08 * wag, 0.0, 1.0), (0.0, 1.0, 0.0), 1.0), wrist_r=(0.0, 0.0),
            curl_r=1.9, point_r=0.0, thumb_r=1.6,
            hand_l=(3.0, 4.0, -44.0), elbow_l=(1.0, -0.35, 0.1),
            palm_l=((0.0, 1.0, -0.45), (-1.0, 0.0, 0.0), 0.85), curl_l=0.6,
            foot_l=fl, foot_r=fr, knee_l=10.0, knee_r=10.0)


DANCES = [Charleston(), Lindy(), Valse(), Shimmy(), Truckin()]
PAIR_DANCES = (1, 2, 3)


# ---------------------------------------------------------------- conversation loops (bar crowd, NPC chats): DanceId 6-8
REST = (9.5, 13.5, -50.5)                 # the relaxed hand (idle) relative to the shoulder, chest frame


def bump(t, a, b, c, d):
    """0 before a, eases up to 1 at b, holds, eases down to 0 at d."""
    if t <= a or t >= d:
        return 0.0
    if t < b:
        return ease((t - a) / (b - a))
    if t <= c:
        return 1.0
    return 1.0 - ease((t - c) / (d - c))


class Causerie:
    """Talking: weight on one leg, the right hand opens and beats the rhythm of the sentence in front of the chest,
    then drops back; small nods and head tilts toward the listener."""
    name, label, length = 'Causerie', 'Causerie', 6.0

    def __init__(self):
        T = self.length
        self.hand = Track(T, [(0.0, REST), (0.8, (8.0, 30.0, -27.0)), (1.4, (14.0, 34.0, -22.0)), (2.0, (6.0, 31.0, -28.0)),
                              (2.6, (16.0, 33.0, -20.0)), (3.4, (10.0, 27.0, -32.0)), (4.3, (12.0, 17.0, -46.0)),
                              (5.2, REST)], 'cr')
        self.g = Track(T, [(0.0, 0.0), (0.7, 1.0), (3.5, 1.0), (4.6, 0.0), (5.6, 0.0)], 'ease')

    def pose(self, t):
        T = self.length
        g = self.g(t)
        sl = math.sin(2 * math.pi * t / T)
        nod = 0.5 + 0.5 * math.cos(2 * math.pi * t / 1.5)
        return Pose(
            pelvis=(2.2 * sl, 0.0, -1.0), pelvis_rot=(1.0, 1.5 * sl, 4.0 * math.sin(2 * math.pi * t / T + 0.3)),
            spine=(4.0 + 1.5 * g, -1.5 * sl, 3.0 * g * math.sin(2 * math.pi * t / 3.0)),
            neck=(2.0 + 2.5 * nod * g, 2.0 * math.sin(2 * math.pi * t / T + 1.0), -3.0 * sl),
            hand_r=self.hand(t), elbow_r=(0.75, -0.45, -0.5),
            palm_r=((0.25, 1.0, 0.05), (0.0, 0.15, 1.0), 0.75 * g), wrist_r=(-8.0 * g, 0.0),
            curl_r=1.0 - 0.6 * g, thumb_r=1.0 - 0.5 * g,
            hand_l=(REST[0] + 1.0 * sl, REST[1] + 3.0 * g, REST[2] + 2.0 * g), curl_l=1.0,
            foot_l=dict(x=11.0, y=5.0, yaw=10.0), foot_r=dict(x=12.0, y=-4.0, yaw=16.0), knee_l=2.0, knee_r=3.0)


class Ecoute:
    """Listening, a 1930s gentleman: hands clasped behind the back, chest out, two small nods, weight shifting
    slowly, rocking once onto the heels."""
    name, label, length = 'Ecoute', 'Écoute', 8.0

    def __init__(self):
        T = self.length
        self.rock = Track(T, [(0.0, 0.0), (4.6, 0.0), (5.3, 1.0), (6.0, 0.0)], 'ease')

    def pose(self, t):
        T = self.length
        sl = math.sin(2 * math.pi * t / T)
        nod = bump(t % T, 1.8, 2.05, 2.15, 2.4) + 0.7 * bump(t % T, 2.45, 2.7, 2.8, 3.05)
        rk = self.rock(t)
        back = (-11.5, -17.0, -45.0)
        return Pose(
            pelvis=(2.5 * sl, -1.5 * rk, -0.8), pelvis_rot=(0.0, 1.2 * sl, 3.0 * math.sin(2 * math.pi * t / T + 0.5)),
            spine=(-1.5 - 1.0 * rk, -1.2 * sl, -2.0 * sl), neck=(1.0 + 7.0 * nod, 3.0 * math.sin(2 * math.pi * t / T + 2.0), 4.0 * math.sin(2 * math.pi * t / T)),
            clav_l=(0.0, -3.0), clav_r=(0.0, -3.0),
            hand_l=back, hand_r=back, elbow_l=(0.75, -0.45, -0.45), elbow_r=(0.75, -0.45, -0.45),
            palm_l=((-0.45, -0.15, -1.0), (0.1, -1.0, 0.2), 0.8), palm_r=((-0.45, -0.15, -1.0), (0.1, -1.0, 0.2), 0.8),
            curl_l=1.3, curl_r=1.1,
            foot_l=dict(x=12.0, y=1.0, yaw=14.0, toe=7.0 * rk), foot_r=dict(x=12.0, y=-1.0, yaw=14.0, toe=7.0 * rk))


class Rire:
    """Laughing: a quiet moment, then a burst of laughter (head thrown back, shoulders shaking, a hand on the
    stomach, leaning forward at the end), settling down again."""
    name, label, length = 'Rire', 'Rire', 7.0

    def pose(self, t):
        T = self.length
        u = t % T
        e = bump(u, 1.4, 1.9, 3.2, 4.2)                                # the laugh
        back = bump(u, 1.4, 2.0, 2.6, 3.2)                             # head thrown back first...
        fwd = bump(u, 2.7, 3.3, 3.6, 4.6)                              # ...then folding forward
        shake = math.sin(2 * math.pi * u * 5.0) * e
        sl = math.sin(2 * math.pi * t / T)
        hand = tuple(r + (h - r) * e for r, h in zip(REST, (-6.0, 25.0, -38.0)))
        return Pose(
            pelvis=(1.5 * sl, -1.0 * back + 1.0 * fwd, -1.0 - 1.5 * fwd), pelvis_rot=(0.0, 1.0 * sl, 3.0 * sl),
            spine=(3.0 - 7.0 * back + 11.0 * fwd, 0.0, 4.0 * e), neck=(1.0 - 15.0 * back + 6.0 * fwd, 4.0 * e, -3.0 * sl),
            clav_l=(3.0 * shake + 2.0 * e, 0.0), clav_r=(3.0 * shake + 2.0 * e, 0.0),
            hand_r=hand, elbow_r=(0.7, -0.5, -0.5), palm_r=((-1.0, 0.3, -0.1), (0.0, -1.0, 0.0), 0.7 * e),
            hand_l=(REST[0] + 6.0 * e, REST[1] + 10.0 * e, REST[2] + 6.0 * e),
            curl_l=1.0 - 0.4 * e, curl_r=1.0 - 0.3 * e,
            foot_l=dict(x=11.0, y=2.0, yaw=12.0), foot_r=dict(x=11.0, y=-2.0, yaw=14.0, heel=4.0 * fwd), knee_r=4.0)


class Slow:
    """Slow foxtrot sway for couples: weight rocking from foot to foot with small steps in place, the body swaying and
    turning gently, a soft mimed hold (lower than the waltz), the head leaning toward the partner's shoulder."""
    name, label, length = 'Slow', 'Slow', 4.0

    def __init__(self):
        T = self.length
        # heel lifts in turn (the unweighted foot), two sways per loop
        self.hl = Track(T, [(0.0, 0.0), (0.5, 10.0), (1.0, 0.0), (2.0, 0.0), (2.5, 10.0), (3.0, 0.0)], 'ease')
        self.hr = Track(T, [(1.0, 0.0), (1.5, 10.0), (2.0, 0.0), (3.0, 0.0), (3.5, 10.0), (4.0, 0.0)], 'ease')

    def pose(self, t):
        T = self.length
        sw = math.sin(2 * math.pi * t / 2.0)                          # +1: weight on the right (left heel up)
        turn = 9.0 * math.sin(2 * math.pi * t / T)
        bob = 0.5 - 0.5 * math.cos(2 * math.pi * t / 1.0)
        return Pose(
            pelvis=(-4.0 * sw, 0.0, -2.5 - 1.5 * bob), pelvis_rot=(1.0, 3.0 * sw, turn * 0.6),
            spine=(2.0, -3.0 * sw, turn * 0.4), neck=(-2.0, 7.0, 12.0 + turn * 0.3),
            clav_l=(2.0, 0.0), clav_r=(1.0, 2.0),
            hand_l=(30.0, 24.0, 3.0), elbow_l=(0.4, -0.3, -0.85),
            palm_l=((0.0, 0.3, 1.0), (0.15, 1.0, 0.0), 0.8),
            hand_r=(-4.0, 31.0, -21.0), elbow_r=(0.85, 0.05, -0.2),
            palm_r=((-1.0, 0.25, 0.0), (0.0, 1.0, 0.1), 0.8),
            curl_l=0.8, curl_r=0.4, thumb_r=0.6,
            foot_l=dict(x=11.0, y=2.0, yaw=8.0, heel=self.hl(t)), foot_r=dict(x=11.0, y=-2.0, yaw=8.0, heel=self.hr(t)),
            knee_l=2.0, knee_r=2.0)


GESTURES = [Causerie(), Ecoute(), Rire()]          # DanceId 6, 7, 8


class Assis:
    """Sitting on a chair, a sofa or a bench (s40_events2.py, DanceId 10): pelvis down and back onto the seat, feet flat
    in front, hands on the thighs, slow breathing and a small head turn now and then."""
    name, label, length = 'Assis', 'Assis', 8.0

    def pose(self, t):
        T = self.length
        b = math.sin(2 * math.pi * t / 4.0)
        h = math.sin(2 * math.pi * t / T)
        return Pose(
            pelvis=(0.0, -10.0, -44.0), pelvis_rot=(-6.0, 0.0, 0.0),
            spine=(7.0 + 0.5 * b, 0.0, 0.0), neck=(1.0 + 0.5 * b, 0.0, 6.0 * h),
            hand_r=(7.0, 31.0, -33.0 + 0.3 * b), elbow_r=(0.75, -0.45, -0.5), curl_r=0.6, thumb_r=0.6,
            hand_l=(7.0, 31.0, -33.0 + 0.3 * b), curl_l=0.6,
            foot_l=dict(x=13.0, y=34.0, yaw=6.0), foot_r=dict(x=13.0, y=34.0, yaw=6.0), knee_l=8.0, knee_r=8.0)


class Zombie:
    """The zombie's shamble (s40_events2.py ZombieAnim plays it directly, index 10 of DanceAnims): both arms held out in front,
    shuffling steps in place while the capsule moves, the head lolling and the back bent."""
    name, label, length = 'Zombie', 'Zombie', 1.6

    def __init__(self):
        T = self.length
        self.fl = foot_path(T, [(0.0, 0.4, 11.0, 7.0, 6.0, 3.0), (0.8, 1.2, 11.0, -5.0, 6.0, 2.0)])
        self.fr = foot_path(T, [(0.4, 0.8, 11.0, -5.0, 6.0, 2.0), (1.2, 1.6, 11.0, 7.0, 6.0, 3.0)])

    def pose(self, t):
        T = self.length
        s = math.sin(2 * math.pi * t / T)
        c = math.cos(2 * math.pi * t / T)
        return Pose(
            pelvis=(3.0 * s, 0.0, -3.0 - 0.8 * c), pelvis_rot=(5.0, 2.0 * s, 4.0 * s),
            spine=(14.0, -2.0 * s, -3.0 * s), neck=(10.0, 9.0 + 3.0 * s, 5.0 * c),
            clav_l=(3.0, 1.0 * s), clav_r=(3.0, -1.0 * s),
            hand_l=(15.0, 50.0 + 2.0 * s, -6.0 + 3.0 * c), elbow_l=(0.6, -0.2, -0.8),
            hand_r=(15.0, 50.0 - 2.0 * s, -3.0 - 3.0 * c), elbow_r=(0.6, -0.2, -0.8),
            palm_l=((0.0, 0.2, -1.0), (0.0, 1.0, 0.0), 0.8), palm_r=((0.0, 0.2, -1.0), (0.0, 1.0, 0.0), 0.8),
            curl_l=0.5, curl_r=0.6,
            foot_l=self.fl(t), foot_r=self.fr(t), knee_l=5.0, knee_r=5.0)


EXTRA = [Slow(), Assis(), Zombie()]                # DanceId 9 (couples only), 10 (seated), 11 (zombie)
ALL = DANCES + GESTURES + EXTRA
PAIR_DANCES = (1, 2, 3, 9)
