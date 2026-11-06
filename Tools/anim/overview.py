"""One image with a characteristic frame of every clip (three-quarter view, skinned Manny): Tools/anim/qa/overview.png.
Run with the ComfyUI venv python -I."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import matplotlib  # noqa: E402
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.collections import PolyCollection  # noqa: E402
from dance_core import Skeleton, Solver  # noqa: E402
from dances import ALL  # noqa: E402
from dance_qa import load_mesh, globals_from, skin, draw  # noqa: E402

PICK = {'Charleston': 0.45, 'Lindy': 0.0, 'Valse': 1.3, 'Shimmy': 0.3, 'Truckin': 0.0, 'Causerie': 1.4,
        'Ecoute': 1.0, 'Rire': 2.3, 'Slow': 0.5}
sk = Skeleton()
mesh = load_mesh('manny')
fig, axs = plt.subplots(1, len(ALL), figsize=(2.6 * len(ALL), 4.6), facecolor='#1c1c1c')
for ax, d in zip(axs, ALL):
    lq, lt = Solver(sk).solve(d.pose(PICK.get(d.name, 0.0)))
    p = skin(mesh, globals_from(mesh, dict(zip(sk.names, lq)), dict(zip(sk.names, lt))))
    draw(ax, p, mesh['tris'], '3/4', d.label, plt, PolyCollection)
fig.suptitle('Le Bal Masqué: dances 1-5 (V), conversation loops 6-8, couples slow 9', color='w')
fn = os.path.join(HERE, 'qa', 'overview.png')
fig.savefig(fn, dpi=70, facecolor=fig.get_facecolor())
print(fn)
