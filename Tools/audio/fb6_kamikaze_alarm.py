"""The kamikaze's alarm loop, from existing recordings only (no generation).
No take of the kamikaze's own voice saying "Alarme" exists: AssetGen/audio/panic_lines.py planned 4 ("alarme1-4", voice k1_kamikaze) but gen/panic_k1_kamikaze/ only holds
his two reference takes, and none of his 10 kept lines contains the word. The takes that do say it are the shouts "Alarme ! Alarme !" of the panic batch.
Chosen: pv_m4_colonel_shout_alarme_s1031 (a take never used in the game; the colonel's in-game line is s1030): the loudest, the highest (median f0 359 Hz), the longest words, whisper hears "Alarm ! Alarm !".
Run without -I (numpy, soundfile, scipy, librosa, faster_whisper in the user site):
  python -X utf8 fb6_kamikaze_alarm.py scan     transcribes and measures the candidates
  python -X utf8 fb6_kamikaze_alarm.py build    writes AssetGen/audio/final/feedback6/SFX_Kamikaze_Alarm_Loop.wav
Loop: the two words cut at their silences, the same level, pitched up 2 semitones with a little saturation (manic; not the colonel's line, not a guest). The user, 2026-11-05: "0.2 second cooldown between
each alarm": each shout is followed by exactly GAP s of digital silence, inside the file, so a looping playback keeps it to the sample. Nothing here has been heard: the checks are the transcription, the levels and the gaps."""
import glob, os, sys
import numpy as np, soundfile as sf
import librosa

ROOT = r'J:\Projets\Unreal_Projects\Guess Who\AssetGen\audio'
OUT = ROOT + r'\final\feedback6'
CANDS = sorted(glob.glob(ROOT + r'\gen\panic_*\pv_*_shout_alarme_*.flac'))
CHOSEN = ROOT + r'\gen\panic_m4_colonel\pv_m4_colonel_shout_alarme_s1031_0.flac'
SR = 44100
PITCH = 2.0      # semitones up
WORD_RMS_DB = -11.0
GAP = 0.2        # s of silence after each shout
FADE = 0.012     # s, at both ends of a shout (no click)


def load(f):
    x, sr = sf.read(f, always_2d=True)
    x = x.mean(axis=1)
    return librosa.resample(x, orig_sr=sr, target_sr=SR) if sr != SR else x


def db(v):
    return 20 * np.log10(v + 1e-9)


def env_db(x, win=0.02):
    n = int(SR * win)
    return db(np.sqrt(np.convolve(x ** 2, np.ones(n) / n, mode='same')))


def words(x, thr=-32.0, min_gap=0.05):
    """Spans over the threshold: the shouted words, in seconds."""
    e = env_db(x)
    a = e > (e.max() + thr)
    sp, on = [], None
    for i, v in enumerate(a):
        if v and on is None:
            on = i
        elif not v and on is not None:
            sp.append([on, i]); on = None
    if on is not None:
        sp.append([on, len(a)])
    m = []
    for s in sp:
        if m and s[0] - m[-1][1] < min_gap * SR:
            m[-1][1] = s[1]
        else:
            m.append(s)
    return [(p / SR, q / SR) for p, q in m if q - p > 0.08 * SR]


def scan():
    from faster_whisper import WhisperModel
    m = WhisperModel('small', device='cpu', compute_type='int8')
    for f in CANDS + [ROOT + r'\final\panic\VO_Panic_Shout_04_m.wav']:
        x = load(f)
        segs, _ = m.transcribe(f, language='fr', beam_size=5, vad_filter=False)
        f0, _, _ = librosa.pyin(x, fmin=70, fmax=600, sr=SR, frame_length=2048)
        print(os.path.basename(f), 'dur', round(len(x) / SR, 2), 'peak', round(db(np.abs(x).max()), 1), 'rms', round(db(np.sqrt(np.mean(x ** 2))), 1),
              'f0 med', round(float(np.nanmedian(f0))), 'words', [(round(p, 2), round(q, 2)) for p, q in words(x)], 'heard:', ' '.join(s.text.strip() for s in segs))


def build():
    os.makedirs(OUT, exist_ok=True)
    x = load(CHOSEN)
    w = words(x)
    print('words in the take', w)
    assert len(w) == 2
    parts = []
    nf = int(FADE * SR)
    ramp = np.sin(np.linspace(0, np.pi / 2, nf)) ** 2
    for p, q in w:
        c = x[max(0, int(p * SR) - 220):min(len(x), int(q * SR) + int(0.02 * SR))]
        c = librosa.effects.pitch_shift(c, sr=SR, n_steps=PITCH, res_type='soxr_hq')
        c = c / np.abs(c).max()
        c = np.tanh(c * 2.2) / np.tanh(2.2)
        c = c * 10 ** (WORD_RMS_DB / 20) / np.sqrt(np.mean(c ** 2))
        c[:nf] *= ramp
        c[-nf:] *= ramp[::-1]
        parts.append(c)
    gap = np.zeros(int(round(GAP * SR)))
    z = np.concatenate([parts[0], gap, parts[1], gap])
    z = z * min(1.0, 0.97 / np.abs(z).max())
    f = OUT + r'\SFX_Kamikaze_Alarm_Loop.wav'
    sf.write(f, z, SR, subtype='PCM_16')
    print('written', f, 'dur', round(len(z) / SR, 3), 'peak', round(db(np.abs(z).max()), 1), 'shout lengths', [round(len(c) / SR, 3) for c in parts], 'gap samples', len(gap), '=', len(gap) / SR, 's')
    nz = np.nonzero(np.abs(np.concatenate([z, z])) > 0)[0]
    d = np.diff(nz)
    print('silences in two loops (s)', [round(v / SR, 4) for v in d[d > SR * 0.05]])


if __name__ == '__main__':
    {'scan': scan, 'build': build}[sys.argv[1]]()
