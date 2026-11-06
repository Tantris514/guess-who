import sys; sys.path.insert(0, '.')
from dance_core import *
from dances import ALL as DANCES
sk = Skeleton()
skip = {'ik_foot_l','ik_foot_r','ik_hand_l','ik_hand_r','ik_hand_gun'}
for d in DANCES:
    S = Solver(sk)
    n = int(round(d.length*30))
    fr = [S.solve(d.pose(k/30)) for k in range(n)]
    worst = []
    for k in range(n):
        a, b = fr[k][0], fr[(k+1) % n][0]
        for i in range(len(a)):
            if sk.names[i] in skip: continue
            ang = qangle(qmul(qconj(a[i]), b[i]))
            worst.append((round(ang,1), k, sk.names[i]))
    worst.sort(reverse=True)
    print(d.name, 'drops', S.stats['pelvis_drops'], round(S.stats['max_drop'],1), worst[:6])
