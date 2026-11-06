"""Offline QA of the dances, no GPU (numpy + matplotlib: run with the ComfyUI venv python, -I).

  python -I dance_qa.py [render] [chars=char_f_gown,char_comte] [ue=<dir>]

Bakes every dance with the same solver build_dances.py uses (or, with ue=<dir>, reads the poses Unreal itself
evaluated from the imported AnimSequences: Tools/anim/ue_eval.py writes <dir>/<Dance>.json), skins the mannequin mesh
(AssetGen/chars/deform/manny.json) and reports per dance:
  - floor: lowest skinned vertex over the loop (anything under the floor), sole height of each foot when planted;
  - limbs through the body: clearance between capsules around the bones (hands/forearms vs torso, head, thighs;
    knees and calves against each other; negative = overlap, cm);
  - joint ranges: knee and elbow bend, wrist twist, pelvis height range, pelvis auto-drops (should be 0);
  - loop seam: largest bone rotation step across the wrap compared with the largest step inside the loop.
With 'render' it draws contact sheets (front, side, three-quarter) to Tools/anim/qa/<Dance>.png, and with chars=
the same for generated characters (their deform dumps).
"""
import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from dance_core import Skeleton, Solver, qmul, qconj, qangle  # noqa: E402
from dances import ALL as DANCES  # noqa: E402

DEFORM = r'J:\Projets\Unreal_Projects\Guess Who\AssetGen\chars\deform'
OUT = os.path.join(HERE, 'qa')
FPS = 30


def quat_mat(q):
    x, y, z, w = q
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])


def mat(q, t):
    m = np.eye(4)
    m[:3, :3] = quat_mat(q)
    m[:3, 3] = t
    return m


def load_mesh(name):
    d = json.load(open(os.path.join(DEFORM, f'{name}.json')))
    v = np.array(d['verts'])
    tris = np.array(d['tris'], dtype=np.int64)
    W = np.zeros((len(v), len(d['bones'])))
    for i, ws in enumerate(d['weights']):
        for b, w in ws:
            W[i, b] += w
    names = [b['name'] for b in d['bones']]
    gref = np.array([mat(b['ref_world'][0], b['ref_world'][1]) for b in d['bones']])
    top = np.argsort(-W, axis=1)[:, :4]                     # sparse skinning: the 4 strongest bones per vertex
    tw = np.take_along_axis(W, top, axis=1)
    tw /= tw.sum(1, keepdims=True) + 1e-12
    return dict(name=name, v=v, tris=tris, W=W, names=names, Gref_inv=np.linalg.inv(gref), top=top, tw=tw,
                parent=[b['parent'] for b in d['bones']], ref_t=[b['local'][1] for b in d['bones']])


def globals_from(mesh, lq_by_name, lt_by_name):
    """Component-space 4x4 per mesh bone; rotations from the dance, translations from the mesh's own skeleton
    (pelvis translation from the dance), as the mannequin skeleton's retargeting does."""
    G = []
    for i, nm in enumerate(mesh['names']):
        q = lq_by_name.get(nm, (0, 0, 0, 1))
        t = lt_by_name[nm] if nm == 'pelvis' else mesh['ref_t'][i]
        loc = mat(q, t)
        G.append(loc if mesh['parent'][i] < 0 else G[mesh['parent'][i]] @ loc)
    return np.array(G)


def skin(mesh, G):
    S = G @ mesh['Gref_inv']
    v = mesh['v']
    out = np.zeros_like(v)
    for k in range(mesh['top'].shape[1]):
        Sk = S[mesh['top'][:, k]]                          # (N, 4, 4)
        out += mesh['tw'][:, k, None] * (np.einsum('nij,nj->ni', Sk[:, :3, :3], v) + Sk[:, :3, 3])
    return out


def seg_dist(p1, q1, p2, q2):
    """Closest distance between segments p1q1 and p2q2."""
    d1, d2, r = q1 - p1, q2 - p2, p1 - p2
    a, e, f = d1 @ d1, d2 @ d2, d2 @ r
    c, b = d1 @ r, d1 @ d2
    den = a * e - b * b
    s = np.clip((b * f - c * e) / den, 0, 1) if den > 1e-9 else 0.0
    t = (b * s + f) / e
    if t < 0:
        t, s = 0.0, np.clip(-c / a, 0, 1)
    elif t > 1:
        t, s = 1.0, np.clip((b - c) / a, 0, 1)
    return float(np.linalg.norm((p1 + d1 * s) - (p2 + d2 * t)))


def capsules(P, ix):
    g = lambda n: np.array(P[ix[n]])
    caps = {
        'pelvis': (g('pelvis') + [0, 0, -4], g('spine_02'), 14.0),
        'chest': (g('spine_03'), g('spine_05') + [0, 0, 4], 14.5),
        'head': (g('head') + [0, 1, 5], g('head') + [0, 3, 13], 10.5),
    }
    for s in 'lr':
        caps[f'uarm_{s}'] = (g(f'upperarm_{s}'), g(f'lowerarm_{s}'), 5.0)
        caps[f'farm_{s}'] = (g(f'lowerarm_{s}') + 0.25 * (g(f'hand_{s}') - g(f'lowerarm_{s}')), g(f'hand_{s}'), 4.0)
        caps[f'hand_{s}'] = (g(f'hand_{s}'), g(f'middle_02_{s}'), 4.0)
        caps[f'thigh_{s}'] = (g(f'thigh_{s}') + 0.35 * (g(f'calf_{s}') - g(f'thigh_{s}')), g(f'calf_{s}'), 7.0)
        caps[f'calf_{s}'] = (g(f'calf_{s}'), g(f'foot_{s}'), 5.5)
    return caps


PAIRS = [(f'{a}_{s}', b) for s in 'lr' for a in ('hand', 'farm') for b in ('pelvis', 'chest', 'head')] + \
        [(f'{a}_{s}', f'thigh_{o}') for s in 'lr' for o in 'lr' for a in ('hand', 'farm')] + \
        [('calf_l', 'calf_r'), ('thigh_l', 'thigh_r'), ('hand_l', 'hand_r'), ('farm_l', 'farm_r'),
         ('uarm_l', 'pelvis'), ('uarm_r', 'pelvis')]


def angle(a, b, c):
    u, v = np.array(a) - np.array(b), np.array(c) - np.array(b)
    return math.degrees(math.acos(np.clip(u @ v / (np.linalg.norm(u) * np.linalg.norm(v)), -1, 1)))


def bake_frames(dance, solver):
    n = int(round(dance.length * FPS))
    return [solver.solve(dance.pose(k / FPS)) for k in range(n)]


def check(dance, frames, sk, mesh, solver_stats=None, keep=None):
    ix = sk.idx
    rep = {}
    feet_ix = {s: np.where((mesh['W'][:, mesh['names'].index(f'foot_{s}')] + mesh['W'][:, mesh['names'].index(f'ball_{s}')]) > 0.5)[0] for s in 'lr'}
    lowest, soles, clear = 1e9, {'l': [], 'r': []}, {}
    knee, elbow, pel = [], [], []
    posed = []
    for lq, lt in frames:
        Q, P = sk.fk(lq, lt)
        G = globals_from(mesh, dict(zip(sk.names, lq)), dict(zip(sk.names, lt)))
        p = skin(mesh, G)
        posed.append(p if keep is None or len(posed) in keep else None)
        lowest = min(lowest, float(p[:, 2].min()))
        for s in 'lr':
            soles[s].append(float(p[feet_ix[s], 2].min()))
            knee.append(180 - angle(P[ix[f'thigh_{s}']], P[ix[f'calf_{s}']], P[ix[f'foot_{s}']]))
            elbow.append(180 - angle(P[ix[f'upperarm_{s}']], P[ix[f'lowerarm_{s}']], P[ix[f'hand_{s}']]))
        pel.append(P[ix['pelvis']][2])
        caps = capsules(P, ix)
        for a, b in PAIRS:
            (p1, q1, r1), (p2, q2, r2) = caps[a], caps[b]
            cl = seg_dist(p1, q1, p2, q2) - r1 - r2
            clear[(a, b)] = min(clear.get((a, b), 1e9), cl)
    # seam: rotation step per bone between consecutive frames, inside vs across the wrap
    inside, seam = 0.0, 0.0
    main = [ix[n] for n in ('pelvis', 'spine_03', 'head', 'upperarm_l', 'lowerarm_l', 'hand_l', 'upperarm_r',
                            'lowerarm_r', 'hand_r', 'thigh_l', 'calf_l', 'foot_l', 'thigh_r', 'calf_r', 'foot_r')]
    for k in range(len(frames)):
        a, b = frames[k][0], frames[(k + 1) % len(frames)][0]
        step = max(qangle(qmul(qconj(a[i]), b[i])) for i in main)
        if k == len(frames) - 1:
            seam = step
        else:
            inside = max(inside, step)
    rep['lowest vertex z'] = round(lowest, 1)
    for s in 'lr':
        sl = np.array(soles[s])
        rep[f'sole {s} min/median'] = (round(float(sl.min()), 1), round(float(np.median(sl)), 1))
    rep['knee bend range'] = (round(min(knee)), round(max(knee)))
    rep['elbow bend range'] = (round(min(elbow)), round(max(elbow)))
    rep['pelvis z range'] = (round(min(pel), 1), round(max(pel), 1))
    worst = sorted(clear.items(), key=lambda kv: kv[1])[:5]
    rep['tightest clearances cm'] = [(f'{a}/{b}', round(c, 1)) for (a, b), c in worst]
    rep['seam step / max step deg'] = (round(seam, 1), round(inside, 1))
    if solver_stats:
        rep['pelvis auto-drops'] = (solver_stats['pelvis_drops'], round(solver_stats['max_drop'], 1))
    return rep, posed


def draw(ax, p, tris, view, title, plt, PolyCollection):
    if view == 'front':      # camera in front (+Y) looking back: the character's left on the image right
        x, y, depth = p[:, 0], p[:, 2], p[:, 1]
    elif view == 'side':     # camera on the character's right (-X)
        x, y, depth = p[:, 1], p[:, 2], -p[:, 0]
    else:                    # three-quarter front-right
        c, s = math.cos(math.radians(40)), math.sin(math.radians(40))
        x, y, depth = p[:, 0] * c + p[:, 1] * s, p[:, 2], p[:, 1] * c - p[:, 0] * s
    tp = np.stack([x, y], 1)[tris]
    dz = depth[tris].mean(1)
    order = np.argsort(dz)
    v3 = p[tris]
    n = np.cross(v3[:, 1] - v3[:, 0], v3[:, 2] - v3[:, 0])
    n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-9
    light = np.clip(np.abs(n @ (np.array([-0.3, 0.8, 0.5]) / np.linalg.norm([-0.3, 0.8, 0.5]))), 0.2, 1.0)
    col = np.array([0.85, 0.78, 0.68])[None, :] * light[:, None]
    ax.add_collection(PolyCollection(tp[order], facecolors=col[order], edgecolors='none'))
    ax.plot([-60, 60], [0, 0], color='#6a8', lw=1)
    ax.set_xlim(-65, 65)
    ax.set_ylim(-5, 195)
    ax.set_aspect('equal')
    ax.axis('off')
    ax.set_title(title, color='w', fontsize=8)


def render(dance, posed, mesh, tag=''):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.collections import PolyCollection
    os.makedirs(OUT, exist_ok=True)
    picks = np.linspace(0, len(posed), 7)[:-1].astype(int)
    views = ('front', 'side', '3/4')
    fig, axs = plt.subplots(len(views), len(picks), figsize=(3.0 * len(picks), 4.6 * len(views)), facecolor='#1c1c1c')
    for c, k in enumerate(picks):
        for r, view in enumerate(views):
            draw(axs[r, c], posed[k], mesh['tris'], view, f'{view} t={k / FPS:.2f}s', plt, PolyCollection)
    fig.suptitle(f'{dance.label} ({dance.length:.1f} s loop) - {mesh["name"]}', color='w')
    fn = os.path.join(OUT, f'{dance.name}{tag}.png')
    fig.savefig(fn, dpi=62, facecolor=fig.get_facecolor())
    plt.close(fig)
    return fn


def gif(dance, posed, mesh, tag=''):
    """Animated three-quarter view of the loop (every other frame, 15 fps) to Tools/anim/qa/<Dance><tag>.gif."""
    import io
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.collections import PolyCollection
    from PIL import Image
    frames = []
    for k in range(0, len(posed), 2):
        fig, axs = plt.subplots(1, 2, figsize=(5.2, 4.2), facecolor='#1c1c1c')
        draw(axs[0], posed[k], mesh['tris'], '3/4', f'{dance.label} {k / FPS:.2f}s', plt, PolyCollection)
        draw(axs[1], posed[k], mesh['tris'], 'side', 'side', plt, PolyCollection)
        buf = io.BytesIO()
        fig.savefig(buf, dpi=70, facecolor=fig.get_facecolor(), format='png')
        plt.close(fig)
        buf.seek(0)
        frames.append(Image.open(buf).convert('P', palette=Image.ADAPTIVE))
    fn = os.path.join(OUT, f'{dance.name}{tag}.gif')
    frames[0].save(fn, save_all=True, append_images=frames[1:], duration=int(2000 / FPS), loop=0)
    return fn


def main(args):
    sk = Skeleton()
    mesh = load_mesh('manny')
    chars = next((a.split('=', 1)[1].split(',') for a in args if a.startswith('chars=')), [])
    ue = next((a.split('=', 1)[1] for a in args if a.startswith('ue=')), None)
    summary = {}
    only = next((a.split('=', 1)[1].split(',') for a in args if a.startswith('only=')), None)
    for dance in DANCES:
        if only and dance.name not in only:
            continue
        if ue:
            d = json.load(open(os.path.join(ue, f'{dance.name}.json')))
            frames = [([tuple(q) for q in f['q']], [tuple(t) for t in f['t']]) for f in d['frames']]
            stats = None
        else:
            solver = Solver(sk)
            frames = bake_frames(dance, solver)
            stats = solver.stats
        keep = None if 'gif' in args else (set(np.linspace(0, len(frames), 7)[:-1].astype(int)) if 'render' in args else set())
        rep, posed = check(dance, frames, sk, mesh, stats, keep)
        summary[dance.name] = rep
        print(f'== {dance.label} ({len(frames)} frames){" [as evaluated by Unreal]" if ue else ""}')
        for k, v in rep.items():
            print(f'   {k}: {v}')
        if 'gif' in args:
            print('   gif', gif(dance, posed, mesh))
        if 'render' in args:
            print('   sheet', render(dance, posed, mesh, '_ue' if ue else ''))
            for ch in chars:
                cm = load_mesh(ch)
                cposed = [skin(cm, globals_from(cm, dict(zip(sk.names, lq)), dict(zip(sk.names, lt)))) for lq, lt in frames]
                print('   sheet', render(dance, cposed, cm, f'_{ch}'))
    json.dump(summary, open(os.path.join(HERE, 'qa', 'summary.json' if not ue else 'summary_ue.json'), 'w'), indent=1, default=str)


if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    main(sys.argv[1:])
