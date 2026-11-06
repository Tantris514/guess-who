"""Batch driver for a cast of generated characters (chars/cast3.json): images, 3D, clean-up, manifest.

  V:/ComfyUI/ComfyUI/ComfyUI/.venv/Scripts/python.exe -I -X utf8 creator_batch.py STAGE [NAME ...]   (no name = all)
Stages, each resumable (a character whose output exists is skipped unless --force):
  --cast=NAME  chars/NAME.json (default cast3); "unattended": true in it = no gate and no QA, runs without Claude
  auto     the whole cast in one process: the most advanced character's next job first (3D, back, front), one at a time
  front    Qwen edits of the mannequin template (char_edit.py), one seed per job until one passes the gate (4 seeds,
           the last two at denoise 0.9); sheet chars/<n>/front/sheet.png
  back     same for the back, with the chosen front as reference; sheet chars/<n>/back/sheet.png
  model    square views (char_views.py) + Pixal3D multi-view (char_3d.py), seed 42, 60k faces, 2k textures
  clean    raw copy, mask_flush (0.8 cm), despeckle_glb (below the head), restore the head texels, texel_despeckle on
           dark legs (+ restore above), the mask's detail painted back from the front image (project_front_tex.py),
           pose3d gate, head/hand close-ups (regions and scale follow tall headwear)
  approve  approve_char.py (manifest entry, kind "character", display name, voice note, roster, image + 3D gates)
Choices live in chars/cast3_sel.json {name: {"front": seed, "back": seed}}: `pick` fills the missing ones with the
best passing seed (coverage + arm coverage, small head offset); edit the file to override, then re-run `back` etc.
Every ComfyUI job is submitted only when the coordinator's GPU rule allows it (slot(): front in the :30-:52 character
slice, or a short FIFO filler on an empty queue), one at a time across processes (chars/.cast3_front.lock).
"""
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.request

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
import char_prompts as cp  # noqa: E402

PY = sys.executable
for _a in sys.argv:                # --cast NAME (children inherit it through GW_CAST)
    if _a.startswith('--cast='):
        os.environ['GW_CAST'] = _a.split('=', 1)[1]
CAST_NAME = os.environ.get('GW_CAST', 'cast3')
_cast = json.load(open(os.path.join(ROOT, 'chars', f'{CAST_NAME}.json'), encoding='utf-8'))
CAST = _cast['characters']
SEED_BASE = _cast.get('seed_base', 700)
UNATTENDED = _cast.get('unattended', False)      # no gate, no QA: first image of each view, 3D, manifest (not in the roster)
SEL_PATH = os.path.join(ROOT, 'chars', f'{CAST_NAME}_sel.json')
CH = os.path.join(ROOT, 'chars')
HEIGHT = {'manny': 180.5, 'quinn': 180.2}


def sel():
    return json.load(open(SEL_PATH, encoding='utf-8')) if os.path.exists(SEL_PATH) else {}


def save_sel(s):
    json.dump(s, open(SEL_PATH, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)


def wait_comfy():
    t0 = time.time()
    while True:
        try:
            urllib.request.urlopen('http://127.0.0.1:8188/system_stats', timeout=10).read()
            return
        except Exception:
            if time.time() - t0 > 6 * 3600:
                raise SystemExit('ComfyUI did not answer for 6 h')
            time.sleep(30)


FRONT_LOCK = os.path.join(CH, '.cast3_front.lock')
SEED_MIN, RELOAD_MIN, PIXAL_MIN, MARGIN = 4, 6, 6, 5   # minutes, from the shared queue's history (03:00)


def is_edit(prompt):
    return any(v.get('class_type') == 'FluxKontextMultiReferenceLatentMethod' for v in prompt.values())


def slot(kind):
    """Coordinator GPU rule v4 (2026-11-03 03:15): character jobs are submitted during :30-:52 of each hour with
    front=true, one at a time per producer, only if the estimate + 5 min ends before :52; outside the slice, one short
    job (<= 8 min) as FIFO when the queue is completely empty. Another producer's pending front job goes first (front
    jobs run last-in first-out, so mine would jump it). Returns 'front', 'fifo' or '' (wait); with a mode, this
    process holds the cross-process lock."""
    try:
        q = json.loads(urllib.request.urlopen('http://127.0.0.1:8188/queue', timeout=30).read())
        last = json.loads(urllib.request.urlopen('http://127.0.0.1:8188/history?max_items=1', timeout=30).read())
    except Exception:
        return ''
    running, pending = q['queue_running'], q['queue_pending']
    if any(it[0] < 0 for it in pending):
        return ''
    prev = running[-1][2] if running else next(iter(last.values()), {}).get('prompt', [0, 0, {}])[2]
    est = PIXAL_MIN if kind == 'pixal' else SEED_MIN + (0 if is_edit(prev) else RELOAD_MIN)
    t = time.localtime()
    m = t.tm_min + t.tm_sec / 60
    if not any(it[0] < 0 for it in running):      # GPU rule v5 (2026-11-03 13:20): no slices, no voices
        mode = 'front'
    elif not running and not pending and est <= 8:
        mode = 'fifo'
    else:
        return ''
    if os.path.exists(FRONT_LOCK) and time.time() - os.path.getmtime(FRONT_LOCK) > 3600:
        os.remove(FRONT_LOCK)                      # left behind by a killed process
    try:
        fd = os.open(FRONT_LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        return ''
    os.write(fd, str(os.getpid()).encode())
    os.close(fd)
    return mode


def run(args, log=None, kind=''):
    """kind 'edit' | 'pixal': a ComfyUI job, submitted only when slot() allows it (it waits up to 24 h once queued)."""
    env = dict(os.environ, GW_MIN_WAIT_S='86400')
    if kind:
        while not (mode := slot(kind)):
            time.sleep(30)
        if mode == 'front':
            env['GW_FRONT'] = '1'
        print(' ', args[1], args[2], mode, time.strftime('%H:%M'), flush=True)
    try:
        p = subprocess.run([PY, '-I', '-X', 'utf8'] + args, capture_output=True, text=True, encoding='utf-8',
                           errors='replace', cwd=ROOT, env=env, timeout=4 * 3600 if UNATTENDED else None)
        out = p.stdout + p.stderr
    except subprocess.TimeoutExpired:           # a job lost by a ComfyUI restart: the next seed goes on
        out = 'gave up after 4 h: ' + ' '.join(args[:3]) + chr(10)
    finally:
        if kind and os.path.exists(FRONT_LOCK):
            os.remove(FRONT_LOCK)
    if log:
        open(log, 'a', encoding='utf-8').write(out)
    return out


def edit_one(i, c, view, seed):
    """One Qwen edit (one seed: short jobs fit the slice), gated by char_edit; then the sheet and the pick."""
    n, body, d = c['name'], c['body'], os.path.join(CH, c['name'])
    args = ['char_edit.py', n, view, os.path.join(CH, 'templates', f'{body}_{view}.png')]
    if view == 'front':
        args += [c['front'] + ' ' + cp.POSE]
    else:
        approved_copy(n, 'front', sel()[n]['front'])
        args += [cp.BACK.format(desc=c['back']), '--ref', os.path.join(d, 'front_approved.png')]
    args += ['--seeds', str(seed)] + (['--denoise', f'{seed}:0.9'] if seed in seeds_for(i, view)[2:] else [])
    wait_comfy()
    run(args, os.path.join(d, f'{view}.log'), 'edit')
    sheet(n, view)
    pick([n])


def seeds_left(i, n, view):
    return [x for x in seeds_for(i, view) if f's{x}' not in gates(n, view)]


def seeds_for(i, view):
    base = SEED_BASE + 10 * i + (0 if view == 'front' else 5)
    return [base + k for k in range(1, 5)]


def gates(name, view):
    g = os.path.join(CH, name, view, 'gate.json')
    return json.load(open(g, encoding='utf-8')) if os.path.exists(g) else {}


def score(r):
    return r['coverage'] + r['arm_coverage'] - abs(r.get('head_top_offset_px', 0)) / 400.0


def sheet(name, view):
    from PIL import Image, ImageDraw
    d = os.path.join(CH, name, view)
    gs = gates(name, view)
    tags = sorted(k for k in gs if not k.endswith('_reg'))
    if not tags:
        return
    ims = [Image.open(os.path.join(d, f'gen_{t}.png')).convert('RGB') for t in tags]
    w, h = ims[0].size
    W, H = w // 2, h // 2
    out = Image.new('RGB', (W * len(ims), H + 40), (30, 30, 30))
    dr = ImageDraw.Draw(out)
    for i, (t, im) in enumerate(zip(tags, ims)):
        r = gs[t]
        out.paste(im.resize((W, H)), (i * W, 40))
        dr.text((i * W + 6, 4), f"{t} {'PASS' if r.get('pass') else 'fail'}", fill=(120, 255, 120) if r.get('pass') else (255, 120, 120))
        dr.text((i * W + 6, 20), f"cov {r['coverage']:.3f} arm {r['arm_coverage']:.3f} head {r.get('head_top_offset_px')}", fill=(230, 230, 230))
    out.save(os.path.join(d, 'sheet.png'))


def pick(names):
    s = sel()
    for c in CAST:
        n = c['name']
        if n not in names:
            continue
        s.setdefault(n, {})
        for view in ('front', 'back'):
            gs = gates(n, view)
            # slim sleeves fail the bulky template's arm gate (Rajan 0.886 on the image, 0.97 on the 3D): the pose gate on
            # the 3D has the last word
            ok = {t: r for t, r in gs.items() if (UNATTENDED or (r['coverage'] >= 0.95 and r['arm_coverage'] >= 0.85))
                  and not t.endswith('_reg')}
            if view not in s[n] and ok:
                s[n][view] = int(max(ok, key=lambda t: score(ok[t]))[1:])
    save_sel(s)
    print(json.dumps(s, ensure_ascii=False))


def headroom(name):
    """Height of the body as a fraction of the whole figure: a turban plume, top hat or tall hairdo (front gate head
    offset above the template, 0.1367 cm/px) makes the figure taller than the mannequin, so the clean-up regions (neck,
    legs) move down and the scale comes from the body fit, not from the total height."""
    over = -gates(name, 'front').get(f"s{sel()[name]['front']}", {}).get('head_top_offset_px', 0)
    body = HEIGHT[[c for c in CAST if c['name'] == name][0]['body']]
    return body / (body + over * 0.1367) if over > 40 else 1.0


def approved_copy(name, view, seed):
    d = os.path.join(CH, name)
    shutil.copyfile(os.path.join(d, view, f'gen_s{seed}.png'), os.path.join(d, f'{view}_approved.png'))
    shutil.copyfile(os.path.join(d, view, f'mask_s{seed}.png'), os.path.join(d, f'{view}_approved_mask.png'))


def next_job(wanted, tried):
    """The most advanced character first (3D, then back, then front), so whole characters come out early."""
    s = sel()
    todo = [(i, c) for i, c in enumerate(CAST) if c['name'] in wanted]
    for i, c in todo:
        n = c['name']
        glb = os.path.join(CH, n, '3d_pixal_s42', f'{n}.glb')
        if 'back' in s.get(n, {}) and not os.path.exists(glb) and ('model', n, 0) not in tried:
            return 'model', i, c, 0
    for view in ('back', 'front'):
        for i, c in todo:
            n = c['name']
            ready = 'front' in s.get(n, {}) if view == 'back' else True
            left = [x for x in seeds_left(i, n, view) if (view, n, x) not in tried]
            if ready and view not in s.get(n, {}) and left:
                return view, i, c, left[0]
    return None


def auto(wanted):
    """The whole cast in one process: next job (one seed, or the 3D), in a slot; then pick / clean on the CPU."""
    tried = set()
    while (job := next_job(wanted, tried)):
        view, i, c, seed = job
        tried.add((view, c['name'], seed))
        print(view, c['name'], seed or '', time.strftime('%H:%M'), flush=True)
        if view == 'model':
            for stage in ('model', 'clean') + (('approve',) if UNATTENDED else ()):
                subprocess.run([PY, '-I', '-X', 'utf8', os.path.abspath(__file__), stage, c['name']], cwd=ROOT)
            print('3d done', c['name'], time.strftime('%H:%M'), flush=True)
        else:
            try:
                edit_one(i, c, view, seed)
            except Exception as e:         # the night goes on with the next job
                print(c['name'], view, seed, 'failed:', str(e)[:300], flush=True)
    if UNATTENDED:
        subprocess.run([PY, '-I', '-X', 'utf8', os.path.join(ROOT, '..', 'Tools', 'chars', 'collect_images.py')], cwd=ROOT)
    s = sel()
    for c in CAST:
        if c['name'] in wanted and 'back' not in s.get(c['name'], {}):
            print(c['name'], 'no passing', 'back' if 'front' in s.get(c['name'], {}) else 'front', ': redo it', flush=True)


def main():
    stage = sys.argv[1]
    force = '--force' in sys.argv
    wanted = [a for a in sys.argv[2:] if not a.startswith('--')] or [c['name'] for c in CAST]
    if stage not in ('auto', 'pick'):
        os.makedirs(CH, exist_ok=True)
    if stage == 'pick':
        return pick(wanted)
    if stage == 'auto':
        return auto(wanted)
    s = sel()
    for i, c in enumerate(CAST):
        n, body = c['name'], c['body']
        if n not in wanted:
            continue
        d = os.path.join(CH, n)
        os.makedirs(d, exist_ok=True)
        log = os.path.join(d, f'{stage}.log')
        t0 = time.time()
        if stage in ('front', 'back'):          # seeds one at a time until one passes the gate
            if stage == 'back' and 'front' not in s.get(n, {}):
                print(n, 'no front chosen'); continue
            for seed in seeds_left(i, n, stage):
                if stage in sel().get(n, {}):
                    break
                edit_one(i, c, stage, seed)
        elif stage == 'model':
            glb = os.path.join(d, '3d_pixal_s42', f'{n}.glb')
            if os.path.exists(glb) and not force:
                continue
            if 'back' not in s.get(n, {}):
                print(n, 'no back chosen'); continue
            approved_copy(n, 'front', s[n]['front'])
            approved_copy(n, 'back', s[n]['back'])
            run(['char_views.py', os.path.join(d, 'views'), f"front={d}/front_approved.png,{d}/front_approved_mask.png",
                 f"back={d}/back_approved.png,{d}/back_approved_mask.png"], log)
            wait_comfy()
            run(['char_3d.py', n, 'pixal', os.path.join(d, 'views'), '--seed', '42', '--faces', '60000', '--tex', '2048'], log, 'pixal')
        elif stage == 'clean':
            dd = os.path.join(d, '3d_pixal_s42')
            glb, raw = os.path.join(dd, f'{n}.glb'), os.path.join(dd, f'{n}_raw.glb')
            if not os.path.exists(glb) or (os.path.exists(raw) and not force):
                continue
            if not os.path.exists(raw):
                shutil.copyfile(glb, raw)
            A, B, C, D = (os.path.join(dd, f'_tmp{k}.glb') for k in 'ABCD')
            k = headroom(n)
            h, neck, knee = str(round(HEIGHT[body] / k, 1)), round(0.83 * k, 3), round(0.5 * k, 3)
            if c['mask']:
                run(['mask_flush.py', raw, h, '--mask', c['mask'], '--out', A, '--max-cm', '0.8'], log)
            else:
                shutil.copyfile(raw, A)
            if not os.path.exists(A):        # mask_flush found no mask (Pixal shaded it away)
                shutil.copyfile(raw, A)
            run(['despeckle_glb.py', A, B, '--where', f'fy < {neck}'], log)
            run(['restore_region_tex.py', B, A, C, '--where', f'fy >= {neck}'], log)
            if c['dark_legs']:
                run(['texel_despeckle.py', C, D, '--where', f'fy < {knee}'], log)
                run(['restore_region_tex.py', D, C, glb, '--where', f'fy >= {knee}'], log)
            else:
                shutil.copyfile(C, glb)
            for f in (A, B, C, D):
                if os.path.exists(f):
                    os.remove(f)
            # the whole front of the head back from the image: Pixal shades a mask's or a face's fine detail away
            pre = os.path.join(dd, f'{n}_pre_proj.glb')
            shutil.copyfile(glb, pre)
            run(['project_front_tex.py', pre, os.path.join(d, 'front_approved.png'), os.path.join(d, 'front_approved_mask.png'),
                 glb, '--region', 'L >= 0', '--rows', '0:345', '--close', '0', '--grow', '0'], log)
            if UNATTENDED:
                print(f'clean {n} {time.time() - t0:.0f}s', flush=True)
                continue
            run(['char_pose3d.py', glb, os.path.join(CH, 'templates', f'{body}_front.png'), str(HEIGHT[body]),
                 os.path.join(dd, 'pose'), os.path.join(CH, 'templates', f'{body}_back.png')]
                + (['--fit-body'] if k < 1 else []), log)
            run(['char_closeup.py', glb, os.path.join(dd, 'qa_closeup_head_hands.png')], log)
        elif stage == 'approve':
            dd = os.path.join(d, '3d_pixal_s42')
            if not os.path.exists(os.path.join(dd, f'{n}_raw.glb')):
                print(n, 'not cleaned'); continue
            run(['approve_char.py', n, body, dd, 'pixal3d_multiview', '--front-tag', f"s{s[n]['front']}", '--back-tag',
                 f"s{s[n]['back']}", '--display-name', c['display'], '--notes',
                 f"Cast batch 3 (Character Creator, {time.strftime('%Y-%m-%d')}): " + c['front'][:400]]
                + (['--fit-body'] if headroom(n) < 1 else []), log)
            # personality + voice brief for the audio agent (VOIX_ARCHITECTURE.md principle 2), right after the upsert
            mp = os.path.join(ROOT, 'manifest.json')
            man = json.load(open(mp, encoding='utf-8'))
            for e in man['assets']:
                if e['name'] == n:
                    e['display_name'] = c['display']
                    e['voice_note'] = c['voice']
                    if not UNATTENDED:
                        e['outfits'] = 'roster'        # s29_gen_chars puts it in the party's roster
            json.dump(man, open(mp, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
        print(f'{stage} {n} {time.time() - t0:.0f}s', flush=True)


if __name__ == '__main__':
    main()
