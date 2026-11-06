"""Copy every chosen character image into one folder the user can browse or reuse with other generators.

  python -I collect_images.py

J:/Projets/Unreal_Projects/Guess Who/Personnages (images)/<Nom>/ gets the approved views of each AssetGen/chars/char_*
(face, dos, profil, face sans masque = the image the 3D was built from); _gabarits/ gets the mannequin pose templates
the images must match. Copies only (the pipeline keeps its own files); re-run after each new character.
A folder left by a renamed character moves to AssetGen/chars/<id>/superseded_images/.
"""
import json
import os
import shutil

ROOT = r'J:\Projets\Unreal_Projects\Guess Who'
CHARS = os.path.join(ROOT, 'AssetGen', 'chars')
OUT = os.path.join(ROOT, 'Personnages (images)')
VIEWS = {'front_approved.png': 'face', 'back_approved.png': 'dos', 'side_approved.png': 'profil',
         'front_unmasked_3d_source.png': 'face_sans_masque'}

names = {}
man = json.load(open(os.path.join(ROOT, 'AssetGen', 'manifest.json'), encoding='utf-8'))
for e in man['assets']:
    if e.get('kind') == 'character':
        names[e['name']] = e.get('display_name') or e['name']
os.makedirs(OUT, exist_ok=True)
count = 0
for d in sorted(os.listdir(CHARS)):
    src = os.path.join(CHARS, d)
    if not d.startswith('char_') or not os.path.isdir(src):
        continue
    found = [(f, v) for f, v in VIEWS.items() if os.path.exists(os.path.join(src, f))]
    if not found:
        continue
    label = names.get(d, d.replace('char_', '').capitalize())
    dst = os.path.join(OUT, f'{label} ({d})')
    # a renamed character leaves its old folder behind: move it out of the browse folder (kept, not deleted)
    for old in os.listdir(OUT):
        if old.endswith(f' ({d})') and os.path.join(OUT, old) != dst:
            keep = os.path.join(src, 'superseded_images')
            os.makedirs(keep, exist_ok=True)
            shutil.move(os.path.join(OUT, old), os.path.join(keep, old))
            print(f'  old folder "{old}" moved to {keep}')
    os.makedirs(dst, exist_ok=True)
    for f, v in found:
        shutil.copy2(os.path.join(src, f), os.path.join(dst, f'{d}_{v}.png'))
        count += 1
    print(f'{label}: {", ".join(v for _, v in found)}')
tpl = os.path.join(CHARS, 'templates')
if os.path.isdir(tpl):
    dst = os.path.join(OUT, '_gabarits')
    os.makedirs(dst, exist_ok=True)
    for f in os.listdir(tpl):
        if f.endswith('.png') or f.endswith('.json'):
            shutil.copy2(os.path.join(tpl, f), os.path.join(dst, f))
print(f'{count} images -> {OUT}')
