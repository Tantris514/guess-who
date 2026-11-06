"""c20_staff: staff lines drafted by the shop agent (aa673112fc6b59226), situation in "context" (open / sale / no_money /
danger_sold / walk_away / detective_near), plus its NPC reaction drafts given to the roster voices (texts that differ from
c19). Same item format as c01-c19; voice = char_id. Never edit lines already rendered: new lines go to a new batch."""

ITEMS = []
n = [0]


def add(cat, voice, gender, text, context=None, reg="neutral"):
    n[0] += 1
    it = {"cat": cat, "text": text, "voice": voice, "gender": gender, "reg": reg, "line_id": f"ST{n[0]:04d}",
          "whispered": False, "nonverbal": False, "gun": False}
    if context:
        it["context"] = context
    ITEMS.append(it)


STAFF = [
    ("barman", "char_barman", "m", {
        "open": ["Bonsoir ! Qu'est-ce que je vous sers ?", "Monsieur, madame... un petit remontant ?", "Le comptoir est à vous.",
                 "Pas un mot à personne, promis.", "Vous avez l'air d'avoir besoin de quelque chose de fort."],
        "sale": ["Excellent choix.", "Avec ceci ?", "Discrétion assurée.", "Ça ne quitte pas le comptoir.",
                 "Servi, et je n'ai rien vu.", "Revenez quand vous voulez."],
        "no_money": ["Ça, c'est hors de vos moyens, mon ami.", "La maison ne fait pas crédit."],
        "danger_sold": ["Faites attention avec ça...", "Ne le sortez pas devant les détectives."],
    }),
    ("waiter", "char_waiter", "m", {
        "open": ["Champagne ? ... Ou autre chose ?", "Monsieur désire ?", "Un petit extra avec votre coupe ?",
                 "Faites vite, on m'attend en salle."],
        "sale": ["Très bien, monsieur.", "Je n'ai rien vu, rien entendu.", "Bonne soirée... et prudence."],
        "walk_away": ["Je repasse dans un instant !", "Pardon, pardon... le service n'attend pas."],
    }),
    ("junkie", "char_junkie", "m", {
        "open": ["Psst... par ici.", "Ferme la porte, veux-tu ?", "Tu cherches quelque chose de... spécial ?",
                 "Pas de questions, pas de reçu."],
        "sale": ["Un pétard ? J'ai ça. Ça fait un boucan du tonnerre.", "Marché conclu. On ne s'est jamais vus.",
                 "Si on te demande, tu sortais des toilettes."],
        "no_money": ["Reviens quand t'auras les sous.", "Ici, c'est payé comptant."],
        "detective_near": ["Les détectives ? Connais pas."],
    }),
]
for cat, voice, g, by in STAFF:
    for ctx, texts in by.items():
        for t in texts:
            add(cat, voice, g, t, ctx)

# the shop agent's NPC reaction drafts, spread over the roster voices (P3 categories)
NPC = [
    ("bomb_near", "char_colonel", "m", "Vous entendez ce bip ?", "startled"),
    ("bomb_near", "char_odette", "f", "C'est quoi, ce tic-tac ?", "startled"),
    ("bomb_near", "char_comte", "m", "Il y a un réveil qui sonne quelque part...", "startled"),
    ("smoke_react", "char_f_gown", "f", "Je ne vois plus rien !", "startled"),
    ("smoke_react", "char_m_tailcoat", "m", "De la fumée ! Ouvrez les fenêtres !", "startled"),
    ("shrink_react", "char_minuit", "m", "Vous avez vu ? Il a... rapetissé !", "startled"),
    ("shrink_react", "char_odette", "f", "J'ai trop bu, moi.", "neutral"),
    ("defuse_react", "char_m_tailcoat", "m", "Ouf !", "neutral"),
    ("defuse_react", "char_f_gown", "f", "Bravo, inspecteur !", "warm"),
]
for cat, voice, g, t, reg in NPC:
    add(cat, voice, g, t, reg=reg)
