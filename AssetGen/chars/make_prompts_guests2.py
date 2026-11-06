"""Prompts for the six extra guests (coordinator, 2026-11-02 21:37)."""
import json
import os
import sys

ROOT = r"J:\Projets\Unreal_Projects\Guess Who\AssetGen"
sys.path.insert(0, ROOT)
import char_prompts as cp  # noqa: E402

os.chdir(ROOT)
P = json.load(open(r"chars\prompts_batch2.json", encoding="utf-8"))
KEEP = (" Keep everything else exactly as it is: the face, the hair, the clothes, the arms and hands, the pose, the scale and "
        "the position in the frame. Plain uniform light grey studio background.")
NEW = {
    "chanteuse": ("quinn", "La Chanteuse",
                  "Dress this mannequin as Josephine, a sultry 1930s jazz singer at a masquerade ball, keeping the mannequin's "
                  "exact silhouette. A glamorous woman with dark brown skin, short glossy black finger-waved hair with a large "
                  "white gardenia flower pinned over one ear, bold red lips, bare face. She wears a floor-length fitted scarlet "
                  "red sequined evening gown with thin straps, falling straight to the floor and hiding the feet, a thin gold "
                  "necklace and gold drop earrings, bare shoulders, long red satin gloves to the elbows, empty hands. ",
                  "the same floor-length fitted scarlet sequined gown with a low back falling to the floor, short glossy black "
                  "finger-waved hair from behind with the white gardenia over one ear, long red satin gloves, bare shoulders.",
                  "Add a thin scarlet red sequinned half-mask lying completely flat and flush against the skin around her eyes."),
    "douairiere": ("quinn", "La Douairiere",
                   "Dress this mannequin as the old Dowager Duchess, a formidable elderly aristocrat of about eighty at a 1930s "
                   "ball, keeping the mannequin's exact silhouette. A thin stern old woman with wrinkled skin, a hooked nose, "
                   "silver-white hair piled high in an Edwardian bun with a small diamond tiara, bare face. She wears an "
                   "old-fashioned floor-length gown of dove-grey and black silk with a high lace collar, long lace sleeves to "
                   "the wrists, a black velvet sash, several ropes of pearls, a cameo brooch, the gown falls to the floor and "
                   "hides the feet, and in her right hand she holds a small gold lorgnette (folding opera glasses on a handle) "
                   "pointing down beside her hip. ",
                   "the same floor-length dove-grey and black silk gown with long lace sleeves falling to the floor, the "
                   "silver-white Edwardian bun with the diamond tiara from behind, the black velvet sash bow at the back, the "
                   "small gold lorgnette in the right hand.",
                   "Add a thin silver lace half-mask lying completely flat and flush against the skin around her eyes."),
    "dandy": ("manny", "Le Dandy",
              "Dress this mannequin as Lucien, a vain young 1930s dandy at a masquerade ball, keeping the mannequin's exact "
              "silhouette. A handsome young man of about twenty-five with sleek platinum-blond hair slicked back, a thin pencil "
              "moustache, a smug smile, bare face, a straw boater hat with a black band tilted on his head. He wears a pale "
              "powder-blue three-piece suit with a double-breasted jacket ending at the hips, a pink carnation in the buttonhole, "
              "a lavender silk tie and pocket square, slim trousers with a crease and a clear gap between the legs, two-tone white "
              "and tan spectator shoes standing flat on the floor, bare hands with a gold signet ring. ",
              "the same pale powder-blue three-piece suit with the double-breasted jacket ending at the hips, the straw boater hat "
              "from behind, sleek platinum-blond hair at the nape, slim trousers, two-tone spectator shoes flat on the floor, "
              "bare hands.",
              "Add a thin gold half-mask lying completely flat and flush against the skin around his eyes."),
    "veuve": ("quinn", "La Veuve",
              "Dress this mannequin as the mysterious Veiled Widow at a 1930s masquerade ball, keeping the mannequin's exact "
              "silhouette. A pale elegant woman with dark red lips and black hair in a low chignon, bare face, wearing a small "
              "black pillbox hat. She wears a severe floor-length black crepe mourning gown with long fitted sleeves, a high "
              "neck with a jet-bead necklace, a narrow column skirt falling to the floor and hiding the feet, black lace "
              "gloves, empty hands, a single silver brooch. ",
              "the same severe floor-length black crepe gown with long fitted sleeves falling to the floor, the small black "
              "pillbox hat and black hair in a low chignon from behind, black lace gloves.",
              "Add a fine black lace veil hanging from the pillbox hat over her eyes and nose, the lace lying completely flat and "
              "flush against the face, the red lips visible below it."),
    "industriel": ("manny", "L'Industriel",
                   "Dress this mannequin as Monsieur Bertrand Lacombe, a portly wealthy 1930s steel industrialist at a "
                   "masquerade ball, keeping the mannequin's exact silhouette and arm position. A heavy-set bald man of about "
                   "sixty with a round belly, ruddy jowly cheeks, bushy grey mutton-chop sideburns, a self-satisfied frown, "
                   "bare face. He wears a charcoal grey chalk-stripe three-piece suit with a buttoned waistcoat over the belly, "
                   "a heavy gold watch chain across the waistcoat, a red silk tie, a jacket ending at the hips, trousers with a "
                   "clear gap between the legs, polished black shoes standing flat on the floor, bare hands with heavy gold "
                   "rings. ",
                   "the same charcoal grey chalk-stripe three-piece suit over the round belly, the jacket ending at the hips, "
                   "the bald head with grey hair at the sides from behind, trousers, polished black shoes flat on the floor, "
                   "bare hands.",
                   "Add a thin plain black half-mask lying completely flat and flush against the skin around his eyes."),
    "peintre": ("manny", "Le Peintre",
                "Dress this mannequin as Anatole, a bohemian 1930s painter from Montmartre at a masquerade ball, keeping the "
                "mannequin's exact silhouette. A lanky man of about thirty-five with long wavy chestnut hair to the shoulders, a "
                "scruffy short beard, a dreamy look, bare face, a floppy black velvet beret. He wears a loose rust-orange "
                "corduroy jacket ending at the hips over a paint-spattered white smock shirt, a long multicoloured knitted scarf "
                "around the neck hanging to the waist, baggy olive green trousers spattered with paint and a clear gap between "
                "the legs, worn brown boots standing flat on the floor, bare hands with paint stains. ",
                "the same loose rust-orange corduroy jacket ending at the hips, the multicoloured knitted scarf, long wavy "
                "chestnut hair to the shoulders under the floppy black velvet beret from behind, baggy paint-spattered olive "
                "trousers, worn brown boots flat on the floor, bare hands.",
                "Add a thin harlequin half-mask painted with small red, yellow and blue diamonds lying completely flat and flush "
                "against the skin around his eyes."),
}
for k, (body, disp, s1, back, mask) in NEW.items():
    P[k] = {"body": body, "display_name": disp, "s1": s1 + cp.POSE, "back": back, "mask_edit": mask + KEEP}
    open(rf"chars\prompt_{k}_s1.txt", "w", encoding="utf-8").write(P[k]["s1"])
    open(rf"chars\{k}_back.txt", "w", encoding="utf-8").write(back)
    open(rf"chars\{k}_mask.txt", "w", encoding="utf-8").write(P[k]["mask_edit"])
json.dump(P, open(r"chars\prompts_batch2.json", "w", encoding="utf-8"), indent=1)
print("ok", list(NEW))
