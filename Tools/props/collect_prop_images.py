"""Copy the chosen image of every 3D prop into one folder the user can browse or feed to a better image-to-3D model.

  python -I -X utf8 collect_prop_images.py

J:/Projets/Unreal_Projects/Guess Who/Props (images)/<Nom> (<name>)/ gets, for every approved prop and character_item
of AssetGen/manifest.json:
  <name>_image.png            the concept image the current 3D model was built from (files.concept)
  <name>_rendu_3d_actuel.png  a render of the current model (files.qa_front), to compare after a regeneration
LISEZMOI.md lists every prop with its description (the prompt), real size and rooms. Copies only (the pipeline keeps
its own files); re-run after each new prop. A folder left by a renamed prop moves to AssetGen/concepts/<name>/superseded_images/.
"""
import json
import os
import shutil

ROOT = r'J:\Projets\Unreal_Projects\Guess Who'
AG = os.path.join(ROOT, 'AssetGen')
OUT = os.path.join(ROOT, 'Props (images)')
KINDS = ('prop', 'character_item')

# French names for the props made before display_name existed (new manifest entries carry display_name)
FR = {
    'armchair_club': 'Fauteuil club', 'sofa_chesterfield': 'Canapé Chesterfield', 'chair_dining': 'Chaise de salle à manger',
    'table_dining': 'Table de banquet', 'table_side': "Guéridon", 'desk_partners': 'Bureau double',
    'bookcase': 'Bibliothèque', 'clock_grandfather': 'Horloge comtoise', 'piano_grand': 'Piano à queue',
    'gramophone': 'Gramophone', 'globe_floor': 'Globe terrestre', 'lamp_floor': 'Lampadaire', 'lamp_table': 'Lampe de table',
    'chandelier': 'Lustre', 'sconce_wall': 'Applique murale', 'fireplace': 'Cheminée', 'billiard_table': 'Table de billard',
    'bar_cart': 'Chariot à alcools', 'palm_potted': 'Palmier en pot', 'vase_flowers': 'Vase de fleurs',
    'bust_marble': 'Buste en marbre', 'armor_suit': 'Armure', 'telephone': 'Téléphone', 'typewriter': 'Machine à écrire',
    'radio_cathedral': 'Radio chapelle', 'chair_wingback': 'Fauteuil à oreilles', 'table_console': 'Console',
    'sideboard': 'Buffet', 'chair_wicker': 'Fauteuil en osier', 'candelabra': 'Candélabre', 'stag_head': 'Trophée de cerf',
    'ottoman': 'Pouf', 'champagne_table': 'Table à champagne', 'umbrella_stand': 'Porte-parapluies', 'harp': 'Harpe',
    'revolver': 'Revolver', 'hat_fedora': 'Chapeau fedora', 'hat_top': 'Haut-de-forme', 'hat_cloche': 'Chapeau cloche',
    'mask_venetian': 'Masque vénitien', 'mask_columbina': 'Masque Colombine', 'mask_deco_silver': 'Masque Art déco argent',
    'mask_domino_lace': 'Masque domino en dentelle',
}


def prompts():
    """name -> the description the concept image was generated from (props.json, else the concept's .txt)."""
    out = {}
    try:
        pj = json.load(open(os.path.join(AG, 'props.json'), encoding='utf-8'))
        for key in ('props', 'character_items'):
            for p in pj.get(key, []):
                if isinstance(p, dict) and p.get('name'):
                    out[p['name']] = p.get('item') or p.get('prompt') or ''
    except (OSError, ValueError):
        pass
    return out


def concept_prompt(img):
    txt = os.path.splitext(img)[0] + '.txt'
    try:
        return json.load(open(txt, encoding='utf-8')).get('prompt', '')
    except (OSError, ValueError):
        return ''


man = json.load(open(os.path.join(AG, 'manifest.json'), encoding='utf-8'))
desc = prompts()
os.makedirs(OUT, exist_ok=True)
rows, count = [], 0
for e in man['assets']:
    if e.get('kind') not in KINDS or e.get('status') != 'approved':
        continue
    name, files = e['name'], e.get('files', {})
    concept = files.get('concept')
    if not concept or not os.path.exists(concept):
        continue
    label = e.get('display_name') or FR.get(name) or name.replace('_', ' ').capitalize()
    dst = os.path.join(OUT, f'{label} ({name})')
    for old in os.listdir(OUT):
        if old.endswith(f' ({name})') and os.path.join(OUT, old) != dst:
            keep = os.path.join(AG, 'concepts', name, 'superseded_images')
            os.makedirs(keep, exist_ok=True)
            shutil.move(os.path.join(OUT, old), os.path.join(keep, old))
            print(f'  old folder "{old}" moved to {keep}')
    os.makedirs(dst, exist_ok=True)
    shutil.copy2(concept, os.path.join(dst, f'{name}_image.png'))
    count += 1
    render = files.get('qa_front')
    if render and os.path.exists(render):
        shutil.copy2(render, os.path.join(dst, f'{name}_rendu_3d_actuel.png'))
        count += 1
    size = e.get('size_cm')
    rows.append((e.get('kind'), label, name, desc.get(name) or concept_prompt(concept),
                 ' × '.join(str(round(v)) for v in size) if size else '', ', '.join(e.get('rooms') or [])))

rows.sort(key=lambda r: (r[0] != 'prop', r[1].lower()))
with open(os.path.join(OUT, 'LISEZMOI.md'), 'w', encoding='utf-8') as fh:
    fh.write('# Props du Bal Masqué — images\n\n'
             'Un dossier par objet 3D du jeu. `<nom>_image.png` est l\'image choisie à partir de laquelle le modèle 3D '
             'actuel a été généré : c\'est celle à donner à un meilleur générateur 3D. `<nom>_rendu_3d_actuel.png` montre '
             'le modèle actuel, pour comparer. Taille réelle en cm : largeur × profondeur × hauteur.\n\n'
             'Ce dossier est recréé par `Tools/props/collect_prop_images.py` (copies seulement ; les originaux restent '
             'dans `AssetGen/`).\n\n'
             '| Objet | Nom technique | Taille (cm) | Pièces | Description (prompt) |\n|---|---|---|---|---|\n')
    for kind, label, name, d, size, rooms in rows:
        fh.write(f'| {label}{" (accessoire)" if kind != "prop" else ""} | `{name}` | {size} | {rooms} | {d} |\n')
print(f'{len(rows)} props, {count} images -> {OUT}')
