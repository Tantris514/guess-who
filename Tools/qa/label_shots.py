"""Label motion-QA screenshots by time when the log has no 'Tracing Screenshot' lines (packaged builds).

  python -I label_shots.py MOTION_DIR

Files unlabelled_ScreenShotNNNNN.png (written in request order, some requests dropped when two land in one frame) are
aligned to the "GW mq shot k=.. v=.. f=.." log lines by a monotonic alignment (dynamic programming) that skips
labels and minimises |file time - log time - offset|, the offset (clock + write latency) searched on a grid.
"""
import datetime
import os
import re
import sys

import numpy as np

d = sys.argv[1]
labels, lt = [], []
for line in open(os.path.join(d, 'server.log'), encoding='utf-8', errors='ignore'):
    m = re.search(r'\[(\d{4})\.(\d\d)\.(\d\d)-(\d\d)\.(\d\d)\.(\d\d):(\d{3})\].*GW mq shot k=(\d+) v=(\w+) f=(\d+)', line)
    if m:
        g = list(map(int, m.groups()[:7]))
        lt.append(datetime.datetime(*g[:6], g[6] * 1000).timestamp())
        labels.append('k%02d_%s_f%02d' % (int(m.group(8)), m.group(9), int(m.group(10))))
files = sorted((f for f in os.listdir(d) if re.match(r'unlabelled_ScreenShot\d+\.png$', f)), key=lambda f: int(re.findall(r'\d+', f)[0]))
if not files:
    sys.exit(0)
F = np.array([os.path.getmtime(os.path.join(d, f)) for f in files])
L = np.array(lt)
n, m = len(F), len(L)
coarse = np.median(F) - np.median(L)


def align(off):
    """cost[i][j]: files[:i+1] aligned, file i on label j (labels strictly increasing)."""
    INF = 1e18
    c = np.abs(F[:, None] - L[None, :] - off)
    cost = np.full((n, m), INF)
    back = np.zeros((n, m), dtype=np.int64)
    cost[0] = c[0]
    for i in range(1, n):
        prev = np.minimum.accumulate(cost[i - 1])               # best over labels < j
        arg = np.zeros(m, dtype=np.int64)
        best = 0
        for j in range(m):                                       # argmin running index
            if cost[i - 1][j] <= cost[i - 1][best]:
                best = j
            arg[j] = best
        cost[i, 1:] = prev[:-1] + c[i, 1:]
        back[i, 1:] = arg[:-1]
    j = int(np.argmin(cost[-1]))
    total = cost[-1, j]
    path = [j]
    for i in range(n - 1, 0, -1):
        j = int(back[i, j])
        path.append(j)
    return total, path[::-1]


best = None
for off in coarse + np.arange(-0.6, 0.61, 0.03):
    t, p = align(off)
    if best is None or t < best[0]:
        best = (t, p, off)
total, path, off = best
for f, j in zip(files, path):
    os.replace(os.path.join(d, f), os.path.join(d, labels[j] + '.png'))
missing = sorted(set(labels) - {labels[j] for j in path})
print(f'labelled {len(files)} files by time (offset {off - coarse:+.2f} s, mean error {total / n * 1000:.0f} ms); missing {missing}')
