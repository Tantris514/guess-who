"""c19_reactions: roster characters reacting to the gameplay objects (voice_bank.CAT: bomb_near, smoke_react, defuse_react
first (P3, gameplay-relevant), then ghost_react, sword_react, ball_react, safe_react, alarm_react, shrink_react, dance_end
(context dance), bar_toast (context bar)), plus a cough per character (nonverbal gasp) and the staff lines (barman /
waiter / junkie). Written by the audio agent (content agent #1 finished); same item format as c01-c18; voice = char_id.
Never edit lines already rendered: new lines go to a new batch."""

ITEMS = []
G = {"char_colonel": "m", "char_comte": "m", "char_f_gown": "f", "char_m_tailcoat": "m", "char_minuit": "m", "char_odette": "f"}
REG = {"bomb_near": "startled", "smoke_react": "startled", "defuse_react": "neutral", "ghost_react": "startled",
       "sword_react": "startled", "ball_react": "neutral", "safe_react": "gossip", "alarm_react": "startled",
       "shrink_react": "startled", "dance_end": "warm", "bar_toast": "warm"}
CTX = {"dance_end": "dance", "bar_toast": "bar"}
n = [0]


def add(cat, voice, text, reg=None, **kw):
    n[0] += 1
    it = {"cat": cat, "text": text, "voice": voice, "gender": G.get(voice, kw.pop("gender", "m")), "reg": reg or REG.get(cat, "neutral"),
          "line_id": f"RX{n[0]:04d}", "whispered": False, "nonverbal": False, "gun": False}
    if cat in CTX:
        it["context"] = CTX[cat]
    it.update(kw)
    ITEMS.append(it)


L = {
    "bomb_near": {
        "char_colonel": ["Ce bip... Je connais ce bruit. Tout le monde à terre !", "Une minuterie ! Comme dans les tranchées, en pire."],
        "char_comte": ["Vous entendez ce petit bip ? Il n'annonce rien de bon.", "Un mécanisme d'horlogerie dans un salon ? Charmant."],
        "char_f_gown": ["C'est quoi, ce bip ? Ma montre ne fait pas ça.", "Quelqu'un a laissé un réveil sous le canapé ?"],
        "char_m_tailcoat": ["Ce bip-bip me rappelle un créancier pressé.", "Je n'aime pas ce petit bruit régulier. Pas du tout."],
        "char_minuit": ["Une bombe. Ne bougez plus.", "Le bip accélère. Reculez."],
        "char_odette": ["Eh, c'est quoi c'bip ? Ça me file les jetons !", "Ça fait bip-bip sous la table, t'entends ?"],
    },
    "smoke_react": {
        "char_colonel": ["De la fumée ! Couvrez-vous le nez, nom d'un chien !", "On se croirait sous les gaz, en seize !"],
        "char_comte": ["Ce brouillard... presque comme chez moi, dans les Carpates.", "De la fumée ? Quelle entrée théâtrale."],
        "char_f_gown": ["Mes yeux ! Qui a allumé ce brouillard ?", "Je ne vois plus mon verre, c'est un drame."],
        "char_m_tailcoat": ["De la fumée ! Idéal pour filer sans payer.", "On n'y voit plus rien. Profitons-en pour disparaître."],
        "char_minuit": ["Un fumigène. Quelqu'un prépare un coup.", "Restez près du mur. On ne voit rien."],
        "char_odette": ["Oh là là, la purée de pois ! J'y vois que dalle !", "Qui c'est qui fume la pipe à ce point-là ?"],
    },
    "defuse_react": {
        "char_colonel": ["Désamorcée ! Bon travail, soldat.", "Ouf. J'ai connu des obus plus aimables."],
        "char_comte": ["Ouf. La mort attendra encore un peu.", "Bravo. Vous avez des mains de chirurgien."],
        "char_f_gown": ["Ouf ! J'ai cru que ma coiffure allait sauter.", "Mon héros ! Enfin, mon héros du moment."],
        "char_m_tailcoat": ["Ouf. Je n'aurais pas parié là-dessus.", "Bien joué. Je vous dois un verre. Un de plus."],
        "char_minuit": ["Désamorcée. Pour cette fois.", "Bien. Restez vigilants."],
        "char_odette": ["Ouf ! J'ai le palpitant qui fait la java !", "Chapeau, mon chou ! T'as des doigts d'or."],
    },
}
for cat in ("bomb_near", "smoke_react", "defuse_react"):
    for v, texts in L[cat].items():
        for t in texts:
            add(cat, v, t)
for v in G:   # a cough in the smoke (non-verbal, may repeat)
    add("gasp", v, "Keuh, keuh ! Keuh keuh !", reg="design:cough", nonverbal=True, context="smoke")

L2 = {
    "ghost_react": {
        "char_colonel": ["Un fantôme bleu ! Ça, on ne l'avait pas à Verdun.", "Halte-là ! Qui vive ?"],
        "char_comte": ["Un spectre ! Un cousin, peut-être ?", "Les fantômes de cette maison manquent de discrétion."],
        "char_f_gown": ["Un fantôme ! Il était tout bleu !", "J'ai vu passer quelque chose à travers le mur !"],
        "char_m_tailcoat": ["Un fantôme ? Pourvu qu'il ne me réclame pas d'argent.", "Il m'a traversé ! Brrr."],
        "char_minuit": ["Une ombre bleue. Elle cherche un corps.", "Ce n'est pas un fantôme. C'est quelqu'un."],
        "char_odette": ["Un revenant ! J'ai la chair de poule !", "Hé, le fantôme, tu paies ta tournée ?"],
    },
    "sword_react": {
        "char_colonel": ["Reposez ce sabre ! On ne joue pas avec une lame !", "Une épée ! En garde, jeune impertinent !"],
        "char_comte": ["Rangez cette épée, voyons. Le sang tache les tapis.", "Une lame d'apparat. Elle coupe quand même."],
        "char_f_gown": ["Posez ça, voyons, vous allez éborgner quelqu'un !", "Quel chevalier ! Mais rendez-la à l'armure."],
        "char_m_tailcoat": ["Doucement avec cette épée, mon vieux !", "Un duel ? Pas ce soir, j'ai trop dîné."],
        "char_minuit": ["Lâchez cette épée.", "Une lame. Mauvaise idée."],
        "char_odette": ["Eh, range ton coupe-chou, tu vas blesser quelqu'un !", "D'Artagnan, va ! Repose ça."],
    },
    "ball_react": {
        "char_colonel": ["Hé ! On jouait, nom de nom !", "Rendez-moi cette boule, c'était mon coup !"],
        "char_comte": ["Ma partie ! J'allais gagner, pour une fois.", "On ne lance pas les boules de billard, mon ami."],
        "char_f_gown": ["Hé, on jouait ! Rendez-la !", "Une boule de billard en plein vol ! Quelle soirée !"],
        "char_m_tailcoat": ["Hé ! J'avais misé sur cette partie !", "Elle m'a frôlé l'oreille, cette boule !"],
        "char_minuit": ["Rendez la boule.", "La partie est finie, on dirait."],
        "char_odette": ["Oh ! Faut pas piquer les boules, c'est pas du jeu !", "Aïe ! Qui c'est qui lance les billes ?"],
    },
    "safe_react": {
        "char_colonel": ["Le coffre est ouvert ! Où est la sentinelle ?", "Qui a forcé le coffre ? Avouez !"],
        "char_comte": ["Le coffre s'ouvre... Que de secrets en perspective.", "Le coffre de notre hôte, grand ouvert. Quelle imprudence."],
        "char_f_gown": ["Le coffre est ouvert ! Il y a des bijoux ?", "Oh, regardez-moi tous ces billets !"],
        "char_m_tailcoat": ["Le coffre ouvert... Je n'y suis pour rien, je le jure.", "Tous ces billets... Mes créanciers en pleureraient."],
        "char_minuit": ["Le coffre est ouvert. Qui avait le code ?", "Quelqu'un a trouvé le code."],
        "char_odette": ["Oh, le coffre ! Y a de quoi s'acheter tout Montmartre !", "Pas touche, hein ? Enfin... juste un peu."],
    },
    "alarm_react": {
        "char_colonel": ["Qui a déclenché l'alarme ? Rassemblement !", "Une alarme ! Tout le monde dehors, au pas !"],
        "char_comte": ["Cette sonnerie m'écorche les oreilles.", "Une alarme incendie ? Je ne sens aucune fumée."],
        "char_f_gown": ["Qui a déclenché cette sonnerie ?", "Une alarme ! Mais où est le feu ?"],
        "char_m_tailcoat": ["L'alarme ! Encore une excuse pour quitter la table.", "Cette cloche me donne la migraine."],
        "char_minuit": ["Fausse alerte. Quelqu'un veut une diversion.", "L'alarme. Observez qui court."],
        "char_odette": ["Ça sonne ! C'est le feu ou c'est la fête ?", "Qui c'est qui a fait sonner la cloche ?"],
    },
    "shrink_react": {
        "char_colonel": ["Il a... rapetissé ! Sacrebleu !", "Un soldat de plomb vivant ! Qu'on m'apporte un cognac."],
        "char_comte": ["Il a rapetissé. Une sorcellerie de mon pays, sans doute.", "Fascinant. Il tiendrait dans une boîte à cigares."],
        "char_f_gown": ["Il a rapetissé ! Il est adorable !", "Mon Dieu, on dirait une poupée de salon !"],
        "char_m_tailcoat": ["Il a rétréci au lavage, celui-là ?", "J'ai trop bu, ou il est tout petit ?"],
        "char_minuit": ["Il a rétréci. Un gaz.", "Petit, mais toujours dangereux."],
        "char_odette": ["Il a rapetissé ! On dirait un nain de jardin !", "Oh, le mignon ! Tu tiens dans ma poche !"],
    },
    "dance_end": {
        "char_colonel": ["Bravo ! Enfin une danse au pas.", "Repos ! Belle manœuvre, mesdames et messieurs."],
        "char_comte": ["Bravo. Une valse digne de mon château.", "Charmant. Mes pieds n'en reviennent pas."],
        "char_f_gown": ["Bravo ! Encore une, encore une !", "Ah, je danserais jusqu'à l'aube !"],
        "char_m_tailcoat": ["Encore ! L'orchestre est en forme ce soir.", "Bravo ! J'en ai presque oublié mes dettes."],
        "char_minuit": ["Bien dansé.", "Fin de la danse. Restez attentifs."],
        "char_odette": ["Bravo les amoureux ! Encore, encore !", "Ah, ça c'est du swing, mon vieux !"],
    },
    "bar_toast": {
        "char_colonel": ["À la cavalerie ! Santé !", "À la France, et à nos chevaux ! Santé !"],
        "char_comte": ["À votre santé. Et à la mienne, éternelle.", "Noroc ! C'est ainsi qu'on trinque chez moi."],
        "char_f_gown": ["Santé ! À nous, les plus beaux du bal !", "À l'amour, et au champagne !"],
        "char_m_tailcoat": ["À la chance ! Elle me doit bien ça.", "Santé ! Et que personne ne me présente l'addition."],
        "char_minuit": ["Santé. Gardez l'œil ouvert.", "À la nuit."],
        "char_odette": ["Tchin-tchin, les amis !", "À la vôtre ! Et vive Montmartre !"],
    },
}
for cat, by in L2.items():
    for v, texts in by.items():
        for t in texts:
            add(cat, v, t)
