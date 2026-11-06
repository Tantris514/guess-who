"""Dumps the local bone poses Unreal evaluates from the dance clips (after its compression), every frame, to
Tools/anim/qa/ue/<Dance>.json, for the offline QA: python -I dance_qa.py ue=Tools/anim/qa/ue [render].
Editor: python -I -X utf8 Tools/ui/ue_run.py Tools/anim/ue_eval.py
"""
import json
import os
import sys

import unreal

ANIM = r'J:\Projets\Unreal_Projects\Guess Who\Tools\anim'
if ANIM not in sys.path:
    sys.path.insert(0, ANIM)
import importlib  # noqa: E402
import dance_core  # noqa: E402
import dances  # noqa: E402
importlib.reload(dance_core)
importlib.reload(dances)

OUT = os.path.join(ANIM, 'qa', 'ue')
os.makedirs(OUT, exist_ok=True)
sk = dance_core.Skeleton()
for dance in dances.ALL:
    seq = unreal.load_asset(f'/Game/GW/Anims/Dance/AS_GW_Dance_{dance.name}')
    n = unreal.AnimationLibrary.get_num_frames(seq)
    frames = []
    worst = 0.0
    for f in range(n):
        poses = unreal.AnimationLibrary.get_bone_poses_for_frame(seq, sk.names, f, False)
        q = [(p.rotation.x, p.rotation.y, p.rotation.z, p.rotation.w) for p in poses]
        t = [(p.translation.x, p.translation.y, p.translation.z) for p in poses]
        frames.append({'q': q, 't': t})
    json.dump({'name': dance.name, 'frames': frames}, open(os.path.join(OUT, f'{dance.name}.json'), 'w'))
    # compare with the solver (rotation error per frame, worst bone)
    solver = dance_core.Solver(sk)
    for f in range(0, n, 5):
        lq, lt = solver.solve(dance.pose(f / 30.0))
        for i in range(len(sk.names)):
            worst = max(worst, dance_core.qangle(dance_core.qmul(dance_core.qconj(lq[i]), frames[f]['q'][i])))
    print(f'{dance.name}: {n} frames dumped; worst rotation difference vs the solver {worst:.2f} deg')
