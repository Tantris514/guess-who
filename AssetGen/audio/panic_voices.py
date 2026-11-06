"""Guest voices and lines for the panic reaction (an innocent guest is shot): voice cards for Qwen3-TTS VoiceDesign, the
style register appended to each card, and the line list. Shared by panic_jobs.py, panic_master.py and the report."""

VOICES = {
    # id: (gender, short label, card)
    "m1_baron": ("m", "posh elderly aristocrat",
                 "A posh elderly French aristocrat in his seventies, a deep, slightly nasal and gravelly bass voice, haughty upper-class "
                 "Parisian diction, slow and drawling, an old baron at a 1930s masked ball."),
    "m2_nerveux": ("m", "nervous young man",
                   "A nervous young Frenchman of about twenty-five, clearly a grown man's voice in the low tenor range, a bit reedy, "
                   "fast and jittery delivery with small hesitations, timid and anxious, the son of a rich family at a 1930s ball."),
    "m3_bonvivant": ("m", "jovial middle-aged bon vivant",
                     "A stout, jovial French businessman in his fifties, a warm, round, booming baritone voice roughened by cigars, "
                     "hearty and loud, a bon vivant at a 1930s party."),
    "m4_colonel": ("m", "gruff old colonel",
                   "A gruff retired French army colonel in his sixties, a harsh, gravelly, barking low voice, clipped military "
                   "diction, short-tempered."),
    "f1_ingenue": ("f", "bright young debutante",
                   "A bright, bubbly young Frenchwoman of about twenty, a high, clear, sparkling soprano voice, quick and lively, "
                   "a debutante at a 1930s ball."),
    "f2_comtesse": ("f", "husky elderly countess",
                    "An elderly French countess in her late sixties, a low, husky, smoky voice roughened by decades of cigarettes "
                    "and champagne, slow, theatrical and drawling, aristocratic."),
    "f3_bourgeoise": ("f", "prim middle-aged society lady",
                      "A refined French society lady in her forties, a crisp, slightly pinched mezzo-soprano voice, precise and "
                      "prim upper-class diction, a little snobbish."),
    "f4_aviatrice": ("f", "confident young aviatrix",
                     "A confident, sporty Frenchwoman of about thirty, an aviator, a warm, slightly low alto voice, energetic, "
                     "direct and sardonic."),
    # ---- 16 more guests (night of 2026-11-02: 24+ distinct voices, a few nouveaux riches and foreign accents)
    "m5_americain": ("m", "American industrialist (accent)",
                     "A wealthy American industrialist in his fifties speaking French fluently but with a strong American accent, "
                     "a loud, booming, friendly baritone, nouveau riche and very pleased with himself."),
    "m6_dandy": ("m", "languid young dandy",
                 "An elegant young dandy of about twenty-eight, a smooth, silky light baritone, languid, ironic and flirtatious, "
                 "drawling upper-class Parisian diction."),
    "m7_docteur": ("m", "kindly old provincial doctor",
                   "A kindly elderly provincial doctor in his late sixties, a warm, slightly cracked voice with a gentle southern "
                   "French lilt, talkative and benevolent."),
    "m8_banquier": ("m", "cold precise banker",
                    "A cold, precise banker in his forties, a dry, clipped, slightly nasal tenor voice, condescending and exact."),
    "m9_poete": ("m", "dreamy young poet",
                 "A young bohemian poet of about twenty-two, a soft, dreamy, breathy male tenor voice, theatrical and melancholy."),
    "m10_marseillais": ("m", "boastful nouveau riche from Marseille",
                        "A loud nouveau-riche businessman in his forties from Marseille, a strong southern French accent (accent du "
                        "Midi), jovial and boastful, a rough warm baritone."),
    "m11_prince": ("m", "Russian émigré prince (accent)",
                   "A Russian émigré prince in his sixties speaking French with a noticeable Russian accent, a deep, slow, "
                   "melancholic bass voice, very formal and courteous."),
    "m12_sportif": ("m", "cheerful young sportsman",
                    "A cheerful young aristocrat and tennis champion of about twenty-four, a bright, energetic male tenor voice, "
                    "says everything with boyish enthusiasm."),
    "f5_duchesse": ("f", "imperious old duchess",
                    "An imperious duchess in her mid-seventies, a thin, sharp, high and slightly tremulous voice, very haughty, "
                    "precise old-fashioned diction."),
    "f6_actrice": ("f", "sultry film actress",
                   "A glamorous film actress of about thirty-five, a low, sultry, velvety female voice, theatrical and amused, "
                   "slow and seductive."),
    "f7_veuve": ("f", "merry rich widow",
                 "A merry rich widow in her fifties, a warm, round, laughing mezzo-soprano voice, gossipy and generous."),
    "f8_anglaise": ("f", "English lady (accent)",
                    "An English lady in her forties speaking French with a light English accent, polite, clipped, with a dry "
                    "sense of humour."),
    "f9_etudiante": ("f", "witty young student",
                     "A clever young woman student of about twenty-two, a quick, crisp, slightly mocking soprano voice, modern "
                     "and witty."),
    "f10_parvenue": ("f", "loud nouveau-riche wife",
                     "A nouveau-riche manufacturer's wife in her forties, a loud, shrill, enthusiastic voice, a little vulgar, "
                     "trying too hard to sound posh."),
    "f11_mariee": ("f", "shy young bride",
                   "A shy young bride of about twenty-five, a soft, sweet, hesitant light soprano voice, timid and very polite."),
    "f12_marquise": ("f", "sardonic marquise",
                     "A sardonic marquise in her fifties, a deep, smoky, ironic female alto voice, slow and cutting."),
    # ---- staff
    "s1_barman": ("m", "barman",
                  "A friendly barman in his forties, a warm, relaxed, slightly hoarse baritone, working-class Parisian accent, "
                  "discreet and witty."),
    "s2_junkie": ("m", "twitchy junkie",
                  "A twitchy, wasted man of about thirty, a raspy, slurred, mumbling voice with nervous laughter, slightly "
                  "paranoid."),
    "s3_serveur": ("m", "young waiter",
                   "A polite young waiter of about twenty, a clear, deferential male tenor voice, quick and formal."),
    "s4_serveuse": ("f", "young waitress",
                    "A polite young waitress of about twenty-five, a clear, bright, deferential voice, quick and formal."),
    # event voices
    "b1_brute": ("m", "rough gangster (bandit)",
                 "A rough, menacing French gangster in his forties, a deep, hoarse, gravelly voice from the Paris underworld, "
                 "working-class Parisian accent, brutal and threatening."),
    "b2_voyou": ("m", "sneering young hoodlum (bandit)",
                 "A wiry, nasty young French hoodlum in his twenties, a raspy, nasal, sneering voice, fast, cocky and aggressive, "
                 "Parisian street accent."),
    "k1_kamikaze": ("m", "crazed fanatic (kamikaze)",
                    "A crazed, wild-eyed Frenchman in his thirties, an unhinged, shrill, manic tenor voice, fanatical and exalted."),
    "r1_robot": ("m", "deep robot automaton (processed)",
                 "A very deep, slow, completely monotone male voice with no emotion at all, perfectly flat pitch, mechanical rhythm, "
                 "every syllable evenly spaced and clearly articulated, like a 1930s science-fiction automaton."),
}


AGE = {"m1_baron": 72, "m2_nerveux": 25, "m3_bonvivant": 52, "m4_colonel": 64, "f1_ingenue": 20, "f2_comtesse": 68,
       "f3_bourgeoise": 45, "f4_aviatrice": 30, "m5_americain": 55, "m6_dandy": 28, "m7_docteur": 68, "m8_banquier": 45,
       "m9_poete": 22, "m10_marseillais": 45, "m11_prince": 63, "m12_sportif": 24, "f5_duchesse": 75, "f6_actrice": 35,
       "f7_veuve": 55, "f8_anglaise": 42, "f9_etudiante": 22, "f10_parvenue": 44, "f11_mariee": 25, "f12_marquise": 55,
       "s1_barman": 42, "s2_junkie": 30, "s3_serveur": 20, "s4_serveuse": 25, "b1_brute": 45, "b2_voyou": 24,
       "k1_kamikaze": 35, "r1_robot": None}
ROLE = {**{v: "guest" for v in AGE}, "s1_barman": "staff", "s2_junkie": "staff", "s3_serveur": "staff", "s4_serveuse": "staff",
        "b1_brute": "bandit", "b2_voyou": "bandit", "k1_kamikaze": "kamikaze", "r1_robot": "robot"}


# ---- character voices (VOIX_ARCHITECTURE.md principle 2: voice_id = char_id), cards written by the content director in
# AssetGen/audio/script/voice_script.json; merged at import so new characters are picked up automatically.
# Characters whose card is identical to one of the voices above reuse its references (ALIAS).
ALIAS = {}
try:
    import json as _json, os as _os
    _S = _json.load(open(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "script", "voice_script.json"), encoding="utf-8"))
    for _v in _S.get("voices", []):
        _vid = _v["voice_id"]
        _same = next((k for k, (g, lab, card) in list(VOICES.items()) if card.strip() == _v["card"].strip()), None)
        if _same:
            ALIAS[_vid] = _same
        VOICES[_vid] = (_v["gender"], _v.get("display", _vid), _v["card"])
        AGE[_vid] = _v.get("age")
        ROLE[_vid] = {"guest": "character", "detective": "character"}.get(_v.get("role"), _v.get("role", "character"))
    # the content director's voice map wins: {char_id: voice_id} reuses that voice, {char_id: {...}} = a design of its own
    _VM = _json.load(open(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "scripts", "_voicemap.json"), encoding="utf-8"))
    for _c, _m in _VM.items():
        if isinstance(_m, str):
            ALIAS[_c] = _m
        elif isinstance(_m, dict):
            ALIAS.pop(_c, None)
            VOICES[_c] = (_m.get("gender", VOICES.get(_c, ("m",))[0]), _m.get("display", _c), _m.get("description", VOICES.get(_c, (0, 0, ""))[2]))
            AGE[_c] = _m.get("age", AGE.get(_c))
            ROLE.setdefault(_c, "character")
except Exception as _e:  # the registry still works without the content script
    print("voice_script.json not merged:", _e)

# characters added to the cast after the content director finished (s29, 2026-11-03 07:38), designed by the audio agent
EXTRA_CHARS = {
    "char_aviatrice": ("f", "L'Aviatrice", 30,
                       "A bold, modern French aviatrix of about thirty in 1932, a clear, confident, slightly husky mezzo-soprano voice, "
                       "quick and direct, adventurous and amused, an easy sporty laugh, unpretentious, a record-breaking pilot."),
}
for _c, (_g, _disp, _age, _card) in EXTRA_CHARS.items():
    if _c not in VOICES:
        VOICES[_c] = (_g, _disp, _card)
        AGE[_c] = _age
        ROLE[_c] = "character"


def _p(g, he, she):
    return he if g == "m" else she


def register(vid, reg):
    g = VOICES[vid][0]
    he, his, him = _p(g, "he", "she"), _p(g, "his", "her"), _p(g, "him", "her")
    return {
        "neutral": f"{he.capitalize()} is chatting politely at the party, relaxed, natural conversational tone.",
        "panic": (f"Right now {he} is terrified and panicking: shouting at the top of {his} lungs, frantic and breathless, "
                  f"{his} voice cracking with fear, very loud and urgent."),
        "awkward": (f"Now {he} speaks in a low, awkward, embarrassed tone, trying to act casual right after something terrible "
                    f"happened, with a nervous little laugh, natural and conversational."),
        "whisper": (f"Now {he} whispers very softly and conspiratorially, a breathy unvoiced whisper close to the listener's ear, "
                    f"quiet but with clear articulation."),
        "scream": f"{he.capitalize()} lets out a sudden, loud, piercing scream of pure terror, no words, just a raw scream.",
        "gasp": f"{he.capitalize()} gasps loudly in shock and fright, a sharp sudden cry, no words.",
        "startled": (f"The lights just went out: {he} is startled and confused in the dark, speaking loudly and anxiously, "
                     f"a little indignant, natural."),
        "warm": f"{he.capitalize()} speaks warmly and kindly, with a smile in {his} voice, friendly and charming, natural.",
        "gossip": (f"{he.capitalize()} speaks in a low, confidential, gossiping tone, leaning in to share a juicy secret, amused "
                   f"and a little wicked, quiet but clearly voiced."),
        "laugh": f"{he.capitalize()} laughs lightly and politely at a joke, a short, amused, natural little laugh.",
        "bigLaugh": f"{he.capitalize()} bursts out laughing heartily at a very funny story, a warm, genuine, rolling laugh.",
        "chuckle": f"{he.capitalize()} chuckles quietly to {him}self, a short, knowing, amused laugh with closed lips.",
        "murmur": f"{he.capitalize()} murmurs thoughtfully to {him}self, a short pensive 'hmm', quiet, no real words.",
        "sigh": f"{he.capitalize()} lets out a long, weary, theatrical sigh.",
        "cough": f"{he.capitalize()} coughs hard in thick smoke, two or three rough coughs, no words.",
        "threat": (f"{he.capitalize()} is robbing a ballroom full of rich guests: barking orders, loud, aggressive and menacing, "
                   f"shouting to be obeyed."),
        "maniac_laugh": f"{he.capitalize()} bursts into a loud, cruel, maniacal villain's laugh.",
        "manic": (f"{he.capitalize()} is completely out of his mind, screaming at the top of his lungs in fanatical exaltation, "
                  f"voice cracking, laughing and shouting at the same time, about to blow everything up."),
        "flat": "He speaks slowly in a perfectly flat, emotionless monotone, like a machine.",
    }[reg]


def instruct(vid, reg):
    return VOICES[vid][2] + " " + register(vid, reg)


# French instructions (the majordome lines used a French instruct); pilot comparison only.
FR = {
    "m1_baron": "Un vieil aristocrate français de soixante-dix ans, voix de basse grave, un peu nasale et rocailleuse, diction hautaine.",
    "f1_ingenue": "Une jeune Française pétillante d'une vingtaine d'années, voix de soprano aiguë, claire et vive.",
}
FR_REG = {
    ("m", "panic"): "Terrifié, en pleine panique, il hurle à pleins poumons, essoufflé, la voix qui se brise de peur, très fort.",
    ("f", "panic"): "Terrifiée, en pleine panique, elle hurle à pleins poumons, essoufflée, la voix qui se brise de peur, très fort.",
    ("m", "whisper"): "Il chuchote tout bas, sur le ton de la confidence, un murmure soufflé à l'oreille, articulation claire.",
    ("f", "whisper"): "Elle chuchote tout bas, sur le ton de la confidence, un murmure soufflé à l'oreille, articulation claire.",
}

# reference sentences, one per register (VoiceDesign once per voice and register, then every line is cloned from it)
REF_TEXT = {
    # neutral reference sentence for NEW voice designs (2026-11-03 05:45; the earlier designs used "Je dois dire que cette
    # soirée est absolument charmante, vous ne trouvez pas ?" and are cloned with their own text, read from the take's sidecar)
    "neutral": "Il pleut depuis ce matin, et le dernier bateau est reparti sans nous. Enfin, la maison est grande.",
    "panic": "Mon Dieu ! Il a tiré sur quelqu'un ! Aidez-moi, vite, je vous en supplie !",
    "awkward": "Bon, eh bien... ce sont des choses qui arrivent, n'est-ce pas ? Ha ha... enfin, bref.",
    "whisper": "Ne dites rien à personne, d'accord ? On fait comme si de rien n'était.",
    "startled": "Hé ! Qui est là ? Je ne vois plus rien du tout, qu'est-ce qui se passe ?",
    "threat": "Toi, là-bas, recule ! Les mains en l'air, et que personne ne fasse le malin !",
    "manic": "Vous allez tous voir ! Ha ha ! Plus personne ne m'arrêtera maintenant, plus personne !",
    "flat": "Analyse en cours. Toutes les unités sont en position. Fin de la transmission.",
    "warm": "Quel bonheur de vous voir ici ! Venez, je vous présente à tout le monde.",
    "gossip": "Vous savez ce qu'on raconte ? Elle est arrivée avec un autre homme que son mari.",
}
