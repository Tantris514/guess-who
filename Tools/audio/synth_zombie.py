"""SFX_Zombie_Groan.wav: a low, wet, rasping groan, synthesized here (no generation). Pure stdlib.
python -I -X utf8 Tools/audio/synth_zombie.py  -> Tools/audio/out_zombie/SFX_Zombie_Groan.wav (s40_events2.py imports it)."""
import math, os, random, struct, wave

SR = 44100
T = 2.6
rnd = random.Random(7)
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out_zombie')
os.makedirs(out, exist_ok=True)
n = int(SR * T)
buf = []
phase = 0.0
lp = [0.0, 0.0, 0.0]        # three "formant" resonators on a buzzing glottis
y = [[0.0, 0.0] for _ in lp]
FORM = ((340.0, 0.9), (720.0, 0.5), (1450.0, 0.22))
for i in range(n):
    t = i / SR
    env = min(1.0, t / 0.35) * min(1.0, (T - t) / 0.9) ** 1.4
    f0 = 62.0 + 18.0 * math.sin(2 * math.pi * 0.7 * t) - 14.0 * t / T + rnd.uniform(-6, 6)
    phase += f0 / SR
    if phase >= 1.0:
        phase -= 1.0
    glottis = (phase * 2.0 - 1.0) * (0.5 + 0.5 * math.sin(2 * math.pi * 7.5 * t) ** 2) + rnd.uniform(-0.5, 0.5) * 0.45
    s = 0.0
    wob = 1.0 + 0.12 * math.sin(2 * math.pi * 0.45 * t)
    for k, (f, g) in enumerate(FORM):
        w = 2 * math.pi * f * wob / SR
        r = 0.975
        v = glottis * (1 - r) * 3.0 + 2 * r * math.cos(w) * y[k][0] - r * r * y[k][1]
        y[k][1], y[k][0] = y[k][0], v
        s += v * g
    buf.append(math.tanh(s * 2.2) * env)
peak = max(abs(x) for x in buf) or 1.0
with wave.open(os.path.join(out, 'SFX_Zombie_Groan.wav'), 'wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes(b''.join(struct.pack('<h', int(x / peak * 0.85 * 32767)) for x in buf))
print('ok', len(buf) / SR, 's')
