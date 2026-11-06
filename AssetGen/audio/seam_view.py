"""Render the wrap point of a loop (last 3 s + first 3 s) so the seam can be inspected: seam_view.py NAME..."""
import os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import audiolib as A
for n in sys.argv[1:]:
    y, sr = A.load(os.path.join("final", n + ".wav"))
    k = 3 * sr
    w = np.vstack([y[-k:], y[:k]])
    A.spectrogram_png(os.path.join("qa", "seam_" + n + ".png"), w, sr, n + " wrap at t=3.0 s")
