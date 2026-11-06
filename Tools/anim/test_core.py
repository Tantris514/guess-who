"""Self-test of dance_core (python -I -X utf8 test_core.py): FK against the dumped reference pose, sign conventions,
a neutral solve (feet on the floor, pelvis height)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dance_core import *

sk = Skeleton()
Q, P = sk.fk(sk.ref_q, sk.ref_t)
err_p = max(length(vsub(P[i], sk.ref_world[i][1])) for i in range(len(P)))
err_q = max(qangle(qmul(qconj(Q[i]), sk.ref_world[i][0])) for i in range(len(P)))
print(f'FK vs ref_world: max pos err {err_p:.4f} cm, max rot err {err_q:.4f} deg')
assert err_p < 0.05 and err_q < 0.1

# conventions
assert qrot(rot_body(fwd=90), Z)[1] > 0.99, 'fwd tips the top forward'
assert qrot(rot_body(side=90), Z)[0] > 0.99, 'side tips the top to the left'
assert qrot(rot_body(turn=90), Y)[0] > 0.99, 'turn turns the front to the left'
print('conventions OK; thigh_l x =', round(sk.ref_world[sk.i('thigh_l')][1][0], 1), '(left = +X)')

S = Solver(sk)
lq, lt = S.solve(Pose())
Q, P = sk.fk(lq, lt)
for nm in ('pelvis', 'head', 'hand_l', 'hand_r', 'foot_l', 'foot_r', 'ball_l', 'ball_r', 'calf_l', 'lowerarm_l'):
    print(f'{nm:12s}', tuple(round(c, 1) for c in P[sk.i(nm)]))
print('stats', S.stats)
# idle reference for comparison
Qi, Pi = sk.fk(sk.idle[0], [sk.idle_pelvis_t[0] if n == 'pelvis' else t for n, t in zip(sk.names, sk.ref_t)])
for nm in ('pelvis', 'head', 'hand_l', 'hand_r', 'foot_l', 'foot_r'):
    print(f'idle {nm:8s}', tuple(round(c, 1) for c in Pi[sk.i(nm)]))

# clavicle up raises the shoulder, clav fwd moves it forward
for kw, axis in ((dict(clav_l=(15, 0)), 2), (dict(clav_l=(0, 15)), 1)):
    lq2, lt2 = S.solve(Pose(**kw))
    Q2, P2 = sk.fk(lq2, lt2)
    d = P2[sk.i('upperarm_l')][axis] - P[sk.i('upperarm_l')][axis]
    print('clavicle', kw, 'moves shoulder by', round(d, 2), 'on axis', axis)
    assert d > 1.0
for kw, axis in ((dict(clav_r=(15, 0)), 2), (dict(clav_r=(0, 15)), 1)):
    lq2, lt2 = S.solve(Pose(**kw))
    Q2, P2 = sk.fk(lq2, lt2)
    d = P2[sk.i('upperarm_r')][axis] - P[sk.i('upperarm_r')][axis]
    print('clavicle', kw, 'moves shoulder by', round(d, 2), 'on axis', axis)
    assert d > 1.0
# hand target reached
lq2, lt2 = S.solve(Pose(hand_l=(20, 25, -30), hand_r=(20, 25, -30)))
Q2, P2 = sk.fk(lq2, lt2)
for s in 'lr':
    sh, wr = P2[sk.i(f'upperarm_{s}')], P2[sk.i(f'hand_{s}')]
    print('hand', s, 'rel to shoulder', tuple(round(c, 1) for c in vsub(wr, sh)))
# heel raise keeps the ball on the floor
lq2, lt2 = S.solve(Pose(foot_l=dict(x=11, y=0, heel=25)))
Q2, P2 = sk.fk(lq2, lt2)
print('heel 25: ankle_l', tuple(round(c, 1) for c in P2[sk.i('foot_l')]), 'ball_l', tuple(round(c, 1) for c in P2[sk.i('ball_l')]))
# symmetry of the base pose
lq, lt = S.solve(Pose())
Q, P = sk.fk(lq, lt)
for a, b in (('upperarm_l', 'upperarm_r'), ('lowerarm_l', 'lowerarm_r'), ('hand_l', 'hand_r'), ('calf_l', 'calf_r'), ('head', 'head'), ('neck_01', 'neck_01')):
    pa, pb = P[sk.i(a)], P[sk.i(b)]
    print(f'{a:11s} {tuple(round(c, 1) for c in pa)}  {b:11s} {tuple(round(c, 1) for c in pb)}')
print('neutral pelvis pitch', round(math.degrees(2 * math.acos(min(1, abs(qmul(lq[sk.i("pelvis")], qconj(sk.ref_q[sk.i("pelvis")]))[3])))), 1))
