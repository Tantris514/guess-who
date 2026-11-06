"""Offline skinning check of a rigged character (python deform_qa.py <name> [baseline]).

Reads AssetGen/chars/deform/<name>.json (Tools/chars/deform_dump.py), skins the mesh with numpy (linear blend skinning,
animation rotations on the mesh's own bone lengths, as the mannequin skeleton's retargeting does) over the idle, walk
and jog cycles, and measures how far each triangle's edges stretch or shrink compared to the reference pose:
  stretch = max over frames and edges of |log(posed length / reference length)|, reported as a ratio.
Per body region it prints the share of triangles beyond 1.25x and 1.5x, and how far what rests on the floor in the
reference pose sinks under it (95th percentile: a hem going under shows as spikes); with a baseline (the bare mannequin, same
animations) the numbers can be read against what the Epic skinning itself does. It also draws side and front views
of the posed mesh, coloured by stretch, to AssetGen/chars/deform/<name>_<anim>.png.
"""
import json
import os
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
import numpy as np

DIR = r'J:\Projets\Unreal_Projects\Guess Who\AssetGen\chars\deform'
KEEP_TRANSLATION = {'root', 'pelvis'}


def quat_mat(q):
    x, y, z, w = q
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])


def mat(t):
    m = np.eye(4)
    m[:3, :3] = quat_mat(t[0]) * np.array(t[2])[None, :]
    m[:3, 3] = t[1]
    return m


def load(name):
    d = json.load(open(os.path.join(DIR, f'{name}.json')))
    v = np.array(d['verts'])
    tris = np.array(d['tris'], dtype=np.int64)
    nb = len(d['bones'])
    W = np.zeros((len(v), nb))
    for i, ws in enumerate(d['weights']):
        for b, w in ws:
            W[i, b] += w
    return d, v, tris, W


def globals_for(d, frame):
    out = []
    for i, b in enumerate(d['bones']):
        if frame is None:
            loc = mat(b['local'])
        else:
            a = frame[i]
            t = [a[0], a[1] if b['name'] in KEEP_TRANSLATION and b['name'] != 'root' else b['local'][1], b['local'][2]]
            loc = mat(t)
        out.append(loc if b['parent'] < 0 else out[b['parent']] @ loc)
    return np.array(out)


def skin(v, W, G, Gref_inv):
    S = G @ Gref_inv                                   # (B,4,4)
    vh = np.c_[v, np.ones(len(v))]
    per_bone = np.einsum('bij,nj->bni', S, vh)[:, :, :3]   # (B,N,3)
    return np.einsum('nb,bni->ni', W, per_bone)


def edges_len(p, tris):
    a, b, c = p[tris[:, 0]], p[tris[:, 1]], p[tris[:, 2]]
    return np.stack([np.linalg.norm(b - a, axis=1), np.linalg.norm(c - b, axis=1), np.linalg.norm(a - c, axis=1)], 1)


def regions(d, v, tris):
    G = globals_for(d, None)
    z = {b['name']: G[i][2, 3] for i, b in enumerate(d['bones'])}
    c = v[tris].mean(1)
    crotch = min(z['thigh_l'], z['thigh_r']) - 6.0
    reg = np.full(len(tris), 'torso', dtype=object)
    reg[np.abs(c[:, 0]) > 22.0] = 'arms'
    reg[c[:, 2] > z['neck_01']] = 'head'
    reg[c[:, 2] < crotch] = 'below crotch'
    return reg


def draw(p, tris, val, ax, view):
    i, j, depth = (1, 2, 0) if view == 'side' else (0, 2, 1)
    sign = -1 if view == 'side' else 1
    tp = p[tris]
    order = np.argsort(sign * tp[:, :, depth].mean(1))
    if view == 'front':
        order = order[::-1]
    poly = tp[order][:, :, [i, j]]
    if view == 'front':
        poly[:, :, 0] *= -1                                  # camera on +Y: the mannequin's left on the image right
    n = np.cross(tp[:, 1] - tp[:, 0], tp[:, 2] - tp[:, 0])
    n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-9
    light = np.clip(np.abs(n @ (np.array([0.4, 0.8, 0.45]) / np.linalg.norm([0.4, 0.8, 0.45]))), 0.25, 1.0)
    col = plt.cm.turbo(np.clip((val - 1.0) / 0.6, 0, 1))[:, :3] * light[:, None]
    ax.add_collection(PolyCollection(poly, facecolors=col[order], edgecolors='none'))
    ax.set_xlim(poly[:, :, 0].min() - 5, poly[:, :, 0].max() + 5)
    ax.set_ylim(-2, 190)
    ax.set_aspect('equal')
    ax.axis('off')


def run(name, render=True):
    d, v, tris, W = load(name)
    Gref_inv = np.linalg.inv(np.array([mat(b['ref_world']) for b in d['bones']]))
    check = np.abs(globals_for(d, None) - np.linalg.inv(Gref_inv)).max()
    L0 = edges_len(v, tris) + 1e-6
    reg = regions(d, v, tris)
    floor = v[:, 2] < 4.0                              # what touches the floor in the reference pose (hem, shoes)
    res = {}
    for key, an in d['anims'].items():
        worst = np.zeros(len(tris))
        posed = []
        sink = 0.0
        for f in an['frames']:
            p = skin(v, W, globals_for(d, f), Gref_inv)
            r = np.abs(np.log(edges_len(p, tris) / L0)).max(1)
            worst = np.maximum(worst, r)
            posed.append((p, np.exp(r)))
            sink = max(sink, float(np.percentile(v[floor, 2] - p[floor, 2], 95)) if floor.any() else 0.0)
        ratio = np.exp(worst)
        res[key] = {g: (round(float((ratio[reg == g] > 1.25).mean() * 100), 2), round(float((ratio[reg == g] > 1.5).mean() * 100), 2))
                    for g in ('head', 'torso', 'arms', 'below crotch')}
        res[key]['floor sink cm'] = round(sink, 1)
        if render:
            picks = np.linspace(0, len(posed) - 1, 4).astype(int)
            fig, axs = plt.subplots(2, 4, figsize=(16, 13), facecolor='#202020')
            for col, k in enumerate(picks):
                for row, view in enumerate(('side', 'front')):
                    draw(posed[k][0], tris, posed[k][1], axs[row, col], view)
                    axs[row, col].set_title(f'{key} f{k} {view}', color='w')
            fig.suptitle(f'{name} - {key}: colour = edge stretch this frame (blue 1.0x, red >= 1.6x)', color='w')
            fig.savefig(os.path.join(DIR, f'{name}_{key}.png'), dpi=60, facecolor=fig.get_facecolor())
            plt.close(fig)
    return check, res


if __name__ == '__main__':
    for nm in sys.argv[1:]:
        chk, out = run(nm, render=not nm.startswith(('quinn', 'manny')))
        print(f'{nm}: ref-pose check {chk:.3f}; % triangles stretched >1.25x / >1.5x at worst over the cycle')
        for k, regs in out.items():
            print('  ', k, regs)
