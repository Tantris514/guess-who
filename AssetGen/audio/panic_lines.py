"""Every guest / event voice line: category, text, voice, register. Output names are numbered per category in this order:
VO_Panic_<Category>_<NN>_<m|f>.wav.
Registers (one VoiceDesign reference per voice and register, every line cloned from it):
  panic (shouted), awkward (low, embarrassed), whisper (murmured, then whisperised), neutral (chatty small talk),
  startled (blackout: surprised, anxious, indignant), threat (bandit orders), manic (kamikaze), flat (robot base voice).
Non-verbal items (laughs) are generated directly with VoiceDesign (mode "design")."""

M1, M2, M3, M4 = "m1_baron", "m2_nerveux", "m3_bonvivant", "m4_colonel"
F1, F2, F3, F4 = "f1_ingenue", "f2_comtesse", "f3_bourgeoise", "f4_aviatrice"
B1, B2, K1, R1 = "b1_brute", "b2_voyou", "k1_kamikaze", "r1_robot"

ITEMS = []


def add(cat, slug, text, variants, **kw):
    for v in variants:
        vid, reg = v if isinstance(v, tuple) else (v, kw.get("reg"))
        ITEMS.append(dict(cat=cat, slug=slug, text=text, voice=vid, reg=reg, **{k: x for k, x in kw.items() if k != "reg"}))


# ------------------------------------------------------------------ panic: shouts (raised panicked voice)
for slug, text, vs in [
    ("malade", "C'est un malade !", [M3, F1, M1]),
    ("alarme", "Alarme ! Alarme !", [M4, F4, M2]),
    ("fuyez", "Fuyez !", [F2, M4, F3]),
    ("secours", "Au secours !", [F3, M2, F1]),
    ("tire", "Il a tiré sur quelqu'un !", [M2, F4, M3]),
    ("fou", "Mon Dieu, il est fou !", [F2, M1]),
    ("sauve", "Sauve qui peut !", [M3, F1]),
    ("police", "Appelez la police !", [F4, M1, F3]),
    ("assassin", "À l'assassin !", [M4, F2]),
]:
    add("shout", slug, text, vs, reg="panic")

# ------------------------------------------------------------------ panic: calm-down (awkward / whispered)
W, A = "whisper", "awkward"
for slug, text, vs in [
    ("aupire", "Au pire...", [(M3, W), (F4, A)]),
    ("pasgrave", "C'est pas grave.", [(F1, A), (M2, W), (F2, A)]),
    ("connaissais", "En vrai, je le connaissais pas.", [(M2, W), (F4, W), (M3, A)]),
    ("jamais", "Agissons comme si ça ne s'était jamais produit.", [(M1, A), (F3, W)]),
    ("champagne", "Quelqu'un reprend du champagne ?", [(F2, A), (M3, A)]),
    ("masque", "Il avait un drôle de masque, de toute façon.", [(F3, W), (M4, A)]),
    ("gacher", "On ne va pas gâcher la soirée pour si peu.", [(M1, A), (F2, A)]),
    ("enetions", "Bon... où en étions-nous ?", [(F4, A), (M4, A)]),
    ("rienvu", "Je n'ai rien vu, et vous ?", [(F1, W), (M1, W), (F3, W)]),
    ("argent", "Il me devait de l'argent, en plus.", [(M4, W), (F2, W)]),
    ("pauvre", "Pauvre homme... enfin.", [(F3, A), (M2, W)]),
    ("dansait", "Remarquez, il dansait très mal.", [(F1, W), (M3, W)]),
    ("familles", "Ça arrive dans les meilleures familles.", [(M1, A), (F4, W)]),
    ("musique", "Maestro, la musique, je vous prie !", [(F2, A), (M4, A)]),
]:
    add("calm", slug, text, vs)

# ------------------------------------------------------------------ chatter: ambient small talk (neutral register)
N = "neutral"
for slug, text, vs in [
    ("charmante", "Quelle charmante soirée !", [F2, M3]),
    ("deco", "J'adore la décoration.", [F1, M2]),
    ("lumiere", "Quelle belle lumière, vous ne trouvez pas ?", [F3, M1]),
    ("simulation", "On dirait presque qu'on est dans une simulation.", [M2, F4]),
    ("coupe", "Ce champagne est divin. C'est ma troisième coupe... ou ma cinquième.", [F2]),
    ("petitsfours", "Vous avez goûté les petits fours ? Ils sont d'un sec !", [M3]),
    ("ravir", "Votre masque vous va à ravir. Enfin, je crois que c'est vous.", [F3]),
    ("reconnais", "Je ne reconnais personne avec ces masques. C'est délicieux.", [F1]),
    ("fortune", "Notre hôte a encore dépensé une fortune, à ce qu'on dit.", [M1]),
    ("hote", "Où est passé notre hôte, d'ailleurs ? Je ne l'ai jamais vu.", [F4]),
    ("derniere", "Vous connaissez la dernière ? La comtesse a encore changé de mari.", [F3]),
    ("guerre", "Il paraît que le colonel n'a jamais fait la guerre.", [M2]),
    ("orchestre", "L'orchestre joue divinement ce soir.", [M1]),
    ("morceau", "Encore ce morceau ? Ils ne connaissent qu'une seule chanson.", [M4]),
    ("tempsdechien", "Quel temps de chien, dehors ! Heureusement qu'on est au chaud.", [M3]),
    ("pluie", "Il pleut depuis des heures. Personne ne peut repartir, c'est fâcheux.", [F2]),
    ("dejavu", "J'ai l'étrange impression d'avoir déjà vécu cette soirée.", [F4]),
    ("enrond", "Vous aussi, vous tournez en rond dans ce salon ?", [M4]),
    ("observe", "Parfois, j'ai l'impression que quelqu'un nous observe... d'en haut.", [F1]),
    ("sortir", "Je n'arrive pas à sortir de cette pièce. Curieux, non ?", [M2]),
    ("detective", "Ce détective me regarde bizarrement depuis tout à l'heure.", [F3]),
    ("innocent", "Si on me demande, je suis un parfait innocent.", [M3]),
    ("majordome", "Le majordome a l'air de tout savoir. Ça m'inquiète.", [F2]),
    ("dansons", "Dansons ! Enfin... si mes pieds suivent.", [F1]),
    ("cavalier", "J'ai encore perdu mon cavalier.", [F4]),
    ("tante", "Ma tante dit que les bals masqués sont mal famés. Elle est ici.", [M1]),
    ("naturel", "On m'a dit de rester naturel. Est-ce que j'ai l'air naturel ?", [M2]),
    ("lustre", "Ce lustre a l'air de tenir par miracle.", [M4]),
    ("caviar", "Le caviar est fini ? Quelle tragédie.", [F2]),
    ("buffet", "Je suis venu pour le buffet, je l'avoue.", [M3]),
    ("nimportequi", "Avec ce masque, je pourrais être n'importe qui. Même vous.", [F3]),
    ("collier", "Ma chère, ce collier ! Il est vrai ?", [F1]),
    ("montre", "On m'a volé ma montre ! Ah, non... la voilà.", [M1]),
    ("passage", "Il paraît qu'il y a un passage secret derrière la bibliothèque.", [F4]),
    ("medecin", "Mon médecin m'a interdit le champagne. Je ne lui dirai rien.", [M4]),
    ("costume", "Tout le monde porte le même costume, ou c'est moi ?", [M2]),
    ("visage", "Hmm... ce visage me dit quelque chose.", [F3]),
    ("charleston", "Vous dansez le charleston ? Moi non plus.", [F1]),
    ("enigme", "Ce soir, je suis une énigme. Demain, une migraine.", [F2]),
    ("pareil", "Vous ne trouvez pas qu'on bouge tous un peu... pareil ?", [M3]),
    ("faitescomme", "Si vous voyez un détective, faites comme si de rien n'était.", [M4]),
    ("mari", "Vous n'auriez pas vu mon mari ? Grand, masqué, en smoking.", [F4]),
    ("jardinier", "Je parie que c'est le jardinier. C'est toujours le jardinier.", [M1]),
    ("bonsoir", "Bonsoir ! Enfin... qui que vous soyez, bonsoir !", [F3]),
]:
    add("chatter", slug, text, vs, reg=N)

# ------------------------------------------------------------------ chatter replies (short answers)
for slug, text, vs in [
    ("nestcepas", "N'est-ce pas ?", [F1, M1]),
    ("absolument", "Absolument.", [M3, F2]),
    ("trouvez", "Vous trouvez ?", [F3, M2]),
    ("siledites", "Hmm, si vous le dites.", [M4, F4]),
    ("toutafait", "Tout à fait.", [F2, M1]),
    ("vraiment", "Oh, vraiment ?", [F1, M3]),
    ("horreur", "Quelle horreur !", [F3]),
    ("amusant", "Comme c'est amusant.", [M1, F4]),
    ("lefaitesdire", "Je ne vous le fais pas dire.", [M4]),
    ("aca", "Ah, ça...", [M2]),
    ("bienvrai", "C'est bien vrai.", [F2]),
    ("maisoui", "Mais oui, mais oui.", [M3]),
    ("impayable", "Vous êtes impayable !", [F4]),
    ("passible", "Pas possible !", [F1, M4]),
    ("evidemment", "Évidemment.", [F3]),
]:
    add("reply", slug, text, vs, reg=N)
for vid, text in [(F1, "Hi hi hi !"), (M3, "Ha ha ha !"), (F2, "Ha ha ha..."), (M1, "Ho ho ho !")]:
    ITEMS.append(dict(cat="reply", slug="rire", text=text, voice=vid, reg="laugh", mode="design", nonverbal=True))

# ------------------------------------------------------------------ piano_react: someone bangs a cacophony on the grand piano
S, N_, AW = "startled", "neutral", "awkward"
for slug, text, v in [
    ("vacarme", "Mon Dieu, quel vacarme !", (F2, S)),
    ("marche", "Quelqu'un a marché sur le piano ?", (M3, N_)),
    ("jazz", "C'est du jazz moderne, paraît-il.", (F3, N_)),
    ("chopin", "Chopin se retourne dans sa tombe.", (M1, N_)),
    ("salle", "Ça venait de la salle de bal !", (F4, S)),
    ("encore", "Encore ! ... Non, en fait, non.", (M4, N_)),
    ("escalier", "On a fait tomber le piano dans l'escalier ?", (M2, S)),
    ("fa", "Je crois que c'était un fa. Ou tous les fa.", (F1, N_)),
    ("mari", "Mon mari joue exactement comme ça.", (F2, N_)),
    ("champagne", "Voilà ce qui arrive quand on sert trop de champagne.", (M3, AW)),
    ("applaudissons", "Applaudissons... ou pas.", (F3, AW)),
    ("recital", "Un récital surprise ? Comme c'est audacieux.", (M1, N_)),
    ("oreilles", "Mes pauvres oreilles !", (F1, S)),
    ("accorder", "Quelqu'un devrait accorder ce pianiste.", (M4, N_)),
    ("avantgarde", "Ah, l'avant-garde...", (F4, N_)),
    ("colonel", "Je parie que c'est encore le colonel.", (M2, N_)),
]:
    add("piano_react", slug, text, [v])

# ------------------------------------------------------------------ attack: bandits storm the ball
for slug, text, vs in [
    ("bandits", "Des bandits !", [F3, M2, F1]),
    ("aterre", "À terre !", [M4, F4, M3]),
    ("armes", "Ils sont armés !", [F2, M1, F4]),
]:
    add("attack", slug, text, vs, reg="panic", speaker="guest")
for slug, text in [("hautlesmains", "Haut les mains !"), ("bougepas", "Personne ne bouge !"), ("holdup", "C'est un hold-up !")]:
    add("attack", slug, text, [B1, B2], reg="threat", speaker="bandit")
for vid, text in [(B1, "Ha ha ha ha ha !"), (B2, "Hé hé hé hé ha ha ha !")]:
    for k in range(2):
        ITEMS.append(dict(cat="attack", slug=f"rire{k + 1}", text=text, voice=vid, reg="maniac_laugh", mode="design", nonverbal=True,
                          speaker="bandit"))

# ------------------------------------------------------------------ fire
for slug, text, vs in [
    ("aufeu", "Au feu !", [M4, F1, M3]),
    ("brule", "Ça brûle !", [F2, M2]),
    ("eau", "De l'eau, vite !", [M1, F4]),
    ("cheveux", "Mes cheveux !", [F3, F2]),
]:
    add("fire", slug, text, vs, reg="panic", phase="during")
for slug, text, vs in [
    ("chaud", "Il fait un peu chaud, non ?", [M3, F4]),
    ("cheminee", "Rien de tel qu'un bon feu de cheminée.", [M1, F2]),
]:
    add("fire", slug, text, vs, reg="awkward", phase="after")

# ------------------------------------------------------------------ blackout
for slug, text, vs in [
    ("eteint", "Qui a éteint la lumière ?", [M4, F3, M2]),
    ("pied", "Aïe, mon pied !", [F1, M3]),
    ("allumettes", "Quelqu'un a des allumettes ?", [M1, F4]),
    ("touchez", "C'est vous qui me touchez ?", [F2, M2]),
]:
    add("blackout", slug, text, vs, reg="startled", phase="during")
add("blackout", "lumiere", "Ah ! La lumière !", [F1, M3], reg="neutral", phase="after")
add("blackout", "rienfait", "Je n'ai rien fait, je le jure.", [M2, F3], reg="awkward", phase="after")

# ------------------------------------------------------------------ kamikaze (one crazed voice, several takes)
for k in range(4):
    ITEMS.append(dict(cat="kamikaze", slug=f"alarme{k + 1}", text="Alarme ! Alarme ! Alarme !", voice=K1, reg="manic"))
for k in range(2):
    ITEMS.append(dict(cat="kamikaze", slug=f"sauter{k + 1}", text="Tout va sauter !", voice=K1, reg="manic"))
    ITEMS.append(dict(cat="kamikaze", slug=f"adieu{k + 1}", text="Adieu, mes amis !", voice=K1, reg="manic"))

# ------------------------------------------------------------------ robot (flat base voice, then metallic processing)
for slug, text in [("cible", "Cible détectée."), ("elimination", "Élimination."), ("cacher", "Vous ne pouvez pas vous cacher.")]:
    ITEMS.append(dict(cat="robot", slug=slug, text=text, voice=R1, reg="flat"))

CATS = ["shout", "calm", "chatter", "reply", "piano_react", "attack", "fire", "blackout", "kamikaze", "robot"]


def named():
    """ITEMS with their output name (numbered per category, in list order)."""
    from panic_voices import VOICES
    n, out = {}, []
    for it in ITEMS:
        c = it["cat"]
        n[c] = n.get(c, 0) + 1
        g = VOICES[it["voice"]][0]
        cname = "".join(w.capitalize() for w in c.split("_"))
        out.append(dict(it, name=f"VO_Panic_{cname}_{n[c]:02d}_{g}", gender=g,
                        key=f"pv_{it['voice']}_{c}_{it['slug']}" + ("" if c not in ("kamikaze",) else "")))
    return out
