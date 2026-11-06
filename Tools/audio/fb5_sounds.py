"""Sounds of the 2026-11-05 test feedback, made from existing assets with ffmpeg + numpy (no generation, no GPU). Re-runnable.
Writes AssetGen/audio/final/feedback5/ :
  SFX_Zombie_Moan_01..03  existing male gasps (c19_reactions), pitched down, low-passed, a short room echo: replaces the synthesized groan
  SFX_Shot_Hit            ONE stab cut from MUS_Event_Attack (the track behind the "TIN TIN TIN"): played once when shooting starts
  SFX_Robot_Step_01..04   the metallic robot steps with their ring low-passed away: a heavy thud
  SFX_Charge_Laser        synthesized: a rising whine of 1.5 s, the warning before the robot fires
Nothing here has been listened to by a human; the printed numbers are all that was checked.
Run: python -X utf8 Tools\\audio\\fb5_sounds.py   then ue_run.py Tools\\gameplay\\s42_feedback5.py audio"""
import array
import os
import subprocess
import wave

import numpy as np

ROOT = r'J:\Projets\Unreal_Projects\Guess Who\AssetGen\audio\final'
OUT = os.path.join(ROOT, 'feedback5')
os.makedirs(OUT, exist_ok=True)
SR = 44100


def ff(src, dst, chain, extra=()):
    subprocess.run(['ffmpeg', '-y', '-v', 'error', *extra, '-i', src, '-af', chain, '-ac', '1', '-ar', str(SR), dst], check=True)


def load(p):
    r = subprocess.run(['ffmpeg', '-v', 'error', '-i', p, '-ac', '1', '-ar', str(SR), '-f', 's16le', '-'], capture_output=True, check=True)
    return np.frombuffer(r.stdout[:len(r.stdout) // 2 * 2], dtype=np.int16).astype(float) / 32768


def save(p, x):
    with wave.open(p, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(x, -1, 1) * 32000).astype(np.int16).tobytes())


def report(p):
    a = load(p)
    rms = np.sqrt((a ** 2).mean() + 1e-12)
    S = np.abs(np.fft.rfft(a * np.hanning(len(a))))
    f = np.fft.rfftfreq(len(a), 1 / SR)
    print(f'{os.path.basename(p):26s} {len(a) / SR:5.2f} s  peak {np.abs(a).max():.2f}  rms {20 * np.log10(rms):6.1f} dB  centroid {(S * f).sum() / (S.sum() + 1e-9):6.0f} Hz')


# ---- zombie moans: three male gasps, 0.58-0.66 of their pitch
GASPS = [('c19_reactions', 'VO_Gasp_c19_reactions_036_m.wav', 0.60), ('c19_reactions', 'VO_Gasp_c19_reactions_039_m.wav', 0.66), ('c19_reactions', 'VO_Gasp_c19_reactions_040_m.wav', 0.58)]
for i, (d, f, pitch) in enumerate(GASPS, 1):
    p = os.path.join(OUT, f'SFX_Zombie_Moan_{i:02d}.wav')
    chain = (f'asetrate={int(SR * pitch)},aresample={SR},highpass=f=70,lowpass=f=1500,'
             'aecho=0.7:0.6:55|110:0.3|0.15,atrim=0:2.6,afade=t=out:st=2.1:d=0.5,loudnorm=I=-21:TP=-4:LRA=9')
    ff(os.path.join(ROOT, d, f), p, chain)
    report(p)

# ---- one stab of the attack track: the strongest onset of its first 20 s, 0.75 s, faded out
mus = load(os.path.join(ROOT, 'panic', 'MUS_Event_Attack.wav'))
hop = 441
env = np.array([np.abs(mus[i:i + hop]).mean() for i in range(0, min(len(mus), 20 * SR) - hop, hop)])
rise = env[3:] - env[:-3]
at = (int(np.argmax(rise)) + 1) * hop
stab = mus[at:at + int(0.75 * SR)].copy()
stab *= np.minimum(1.0, np.linspace(6.0, 0.0, len(stab)))
stab[:220] *= np.linspace(0, 1, 220)
stab *= 0.7 / np.abs(stab).max()
p = os.path.join(OUT, 'SFX_Shot_Hit.wav')
save(p, stab)
print('stab cut at', round(at / SR, 2), 's')
report(p)

# ---- the robot's steps: only the body of the impact stays
for i in range(1, 5):
    p = os.path.join(OUT, f'SFX_Robot_Step_{i:02d}.wav')
    ff(os.path.join(ROOT, 'panic', f'SFX_Robot_Step_{i:02d}.wav'), p, 'lowpass=f=420,lowpass=f=420,volume=4dB,alimiter=limit=0.8')
    report(p)

# ---- the laser's charge: a rising whine with a growing tremolo, ends just as the shot comes
t = np.arange(int(1.5 * SR)) / SR
f0 = 180 + 900 * (t / 1.5) ** 2
ph = 2 * np.pi * np.cumsum(f0) / SR
x = (np.sin(ph) + 0.35 * np.sin(2 * ph) + 0.15 * np.sin(3.01 * ph)) * (0.25 + 0.75 * (t / 1.5) ** 1.5)
x *= 0.8 + 0.2 * np.sin(2 * np.pi * (6 + 14 * t / 1.5) * t)
x[:400] *= np.linspace(0, 1, 400)
x[-300:] *= np.linspace(1, 0, 300)
p = os.path.join(OUT, 'SFX_Charge_Laser.wav')
save(p, x * 0.45)
report(p)
