"""Rig every generated character of cast3 and cast4 as it comes out of creator_batch.py, without Claude and without QA.

  V:/ComfyUI/ComfyUI/ComfyUI/.venv/Scripts/python.exe -I -X utf8 rig_all.py
Loops until all are rigged (resumable: chars/rigged.json; log in chars/rig_all.log). cast3 entries are approved first (cast4's
approve is part of its batch). One character at a time through ue_run.py in the shared editor, which is started if down.
"""
import json
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(ROOT)
CH = os.path.join(ROOT, 'chars')
DONE = os.path.join(CH, 'rigged.json')
LOG = os.path.join(CH, 'rig_all.log')
RECLEAN = ['char_ambroise', 'char_lucien', 'char_tony', 'char_tex', 'char_morel', 'char_hortense_gown', 'char_clara']
MAX_TRIES = 3


def log(msg):
    with open(LOG, 'a', encoding='utf-8') as f:
        f.write(time.strftime('%d %H:%M ') + msg + '\n')


def cast(name):
    return [c['name'] for c in json.load(open(os.path.join(CH, f'{name}.json'), encoding='utf-8'))['characters']]


def batch(*args):
    subprocess.run([sys.executable, '-I', '-X', 'utf8', os.path.join(ROOT, 'creator_batch.py')] + list(args), cwd=ROOT,
                   capture_output=True, env={k: v for k, v in os.environ.items() if k != 'GW_CAST'})


def approved():
    for _ in range(5):
        try:
            return {e['name'] for e in json.load(open(os.path.join(ROOT, 'manifest.json'), encoding='utf-8'))['assets']}
        except ValueError:          # being rewritten
            time.sleep(5)
    return set()


def rig(n):
    """True when rigged; the editor is often busy with other sessions, so this keeps trying for a long time."""
    script = os.path.join(PROJ, 'Tools', 'chars', 'rig_character.py')
    for k in range(600):
        subprocess.run(['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',   # no-op if one is up
                        os.path.join(PROJ, 'Tools', 'start_editor.ps1')], capture_output=True)
        p = subprocess.run([sys.executable, '-I', '-X', 'utf8', os.path.join(PROJ, 'Tools', 'ui', 'ue_run.py'), script, n],
                           capture_output=True, text=True, encoding='utf-8', errors='replace', cwd=PROJ)
        out = p.stdout + p.stderr
        if 'interactive editor not found' not in out:
            log(f'{n}: {out.strip()[-300:]}')
            return 'skeletal_mesh' in out
        time.sleep(30)
    log(f'{n}: editor never answered')
    return False


def main():
    done = json.load(open(DONE, encoding='utf-8')) if os.path.exists(DONE) else ['char_barnabe', 'char_rajan']
    c3, c4 = cast('cast3'), cast('cast4')
    for n in RECLEAN:                # cleaned before the whole-head projection existed
        if n not in done:
            batch('clean', n, '--force')
    tries = {}
    while True:
        man = approved()
        for n in c3:
            shot = os.path.join(CH, n, '3d_pixal_s42', 'qa_closeup_head_hands.png')
            if n not in man and os.path.exists(shot):
                batch('approve', n)
        man = approved()
        todo = [n for n in c3 + c4 if n in man and n not in done and tries.get(n, 0) < MAX_TRIES]
        for n in todo:
            tries[n] = tries.get(n, 0) + 1
            if rig(n):
                done.append(n)
                json.dump(done, open(DONE, 'w', encoding='utf-8'), indent=0)
        left = [n for n in c3 + c4 if n not in done and tries.get(n, 0) < MAX_TRIES]
        log(f'{len(done)} rigged, {len(left)} left')
        if not left:
            return
        if not todo:
            time.sleep(120)


if __name__ == '__main__':
    main()
