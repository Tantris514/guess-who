"""c21_aviatrice: L'Aviatrice (char_aviatrice, added to the cast 2026-11-03 07:38): greetings, follow-ups, shouts by cause,
calm, remarks, event lines, the c19 reaction categories, and a few dialogues with the other characters; plus Barnabé's
(char_barnabe) lines in the c19 reaction categories. Written by the audio agent, same item format as c01-c20.
L'Aviatrice: a bold, modern 1930s pilot, record-breaking, direct, amused, adventurous, unpretentious.
Barnabé: the impassive butler, formal ("Madame", "Monsieur le Comte"), dry humour, never raises his voice."""

ITEMS = []
n = [0]
AV, BA = "char_aviatrice", "char_barnabe"
GEN = {AV: "f", BA: "m", "char_colonel": "m", "char_comte": "m", "char_f_gown": "f", "char_m_tailcoat": "m",
       "char_minuit": "m", "char_odette": "f"}
CTX = {"dance_end": "dance", "bar_toast": "bar"}


def add(cat, voice, text, reg="neutral", **kw):
    n[0] += 1
    it = {"cat": cat, "text": text, "voice": voice, "gender": GEN[voice], "reg": reg, "line_id": f"AV{n[0]:04d}",
          "whispered": reg == "whisper", "nonverbal": False, "gun": False}
    if cat in CTX:
        it["context"] = CTX[cat]
    it.update(kw)
    ITEMS.append(it)


def dlg(did, turns):
    for t, (voice, text, *reg) in enumerate(turns, 1):
        n[0] += 1
        ITEMS.append({"cat": "dialogue", "text": text, "voice": voice, "gender": GEN[voice], "reg": reg[0] if reg else "neutral",
                      "line_id": f"AV{n[0]:04d}", "whispered": False, "nonverbal": False, "gun": False, "dialogue_id": did,
                      "turn": t, "speaker": "A" if voice == turns[0][0] else "B"})


# ---------------------------------------------------------------- the aviatrix: P3 gameplay reactions first
for cat, reg, texts in [
    ("bomb_near", "startled", ["Ce bip, c'est un compte à rebours. Je connais ce bruit-là.", "Tout le monde dehors, ça va sauter !"]),
    ("smoke_react", "startled", ["De la fumée ! On se croirait dans un nuage d'orage.", "Baissez-vous, l'air est meilleur près du sol !"]),
    ("defuse_react", "warm", ["Joli pilotage ! Atterrissage en douceur.", "Ouf. Je préfère encore une panne de moteur."]),
]:
    for t in texts:
        add(cat, AV, t, reg)
add("gasp", AV, "Keuh, keuh ! Keuh !", reg="design:cough", nonverbal=True, context="smoke")
# greetings, follow-ups
for t in ["Bonsoir ! Vous avez l'air de quelqu'un qui aime le risque.", "Tiens, un nouveau visage ! Vous volez, vous aussi ?",
          "Enchantée. On m'appelle l'Aviatrice, ici. C'est plus court.", "Salut ! Pardon, bonsoir. J'ai encore la tête dans les nuages.",
          "Vous cherchez quelqu'un ? Moi, je cherche la sortie de secours.", "Bonsoir. Votre masque est très réussi, on dirait un faucon."]:
    add("greet", AV, t, "warm")
for t in ["Encore vous ? Vous me suivez comme un ailier.", "On se recroise souvent, ce soir. C'est un signe.",
          "Ah, vous revoilà ! Toujours en vol ?"]:
    add("greet_again", AV, t, "warm")
# shouts by cause
for cause, texts in [
    ("gun", ["Il a tiré ! À couvert, vite !", "Une arme ! Tout le monde à plat ventre !"]),
    ("fire", ["Le feu ! Sortez par la terrasse !", "Les rideaux flambent ! De l'eau, vite !"]),
    ("explosion", ["Ça a explosé ! Il y a des blessés ?", "Le souffle m'a plaquée au mur !"]),
    ("blackout", ["Plus de lumière ! Restez calmes, j'ai l'habitude du vol de nuit !", "Je ne vois rien ! Suivez ma voix !"]),
    ("generic", ["Dégagez le passage, vite !", "Par ici ! Je connais une sortie !", "Mon Dieu, mais qu'est-ce qui se passe ?"]),
]:
    for t in texts:
        add("shout", AV, t, "panic", cause=cause, gun=cause == "gun")
# calm (half whispered)
for t, reg in [("Bon. On a connu pire au-dessus de l'Atlantique.", "neutral"), ("Respirez. L'orage est passé.", "warm"),
               ("Personne n'a rien vu, d'accord ? Rien du tout.", "whisper"), ("Je ne serais pas venue, si j'avais su.", "whisper"),
               ("Il faudrait peut-être prévenir quelqu'un, non ?", "whisper"), ("On reprend la soirée, alors ?", "neutral")]:
    add("calm", AV, t, reg)
# remarks
for t in ["Avec ce vent, aucun avion ne pourrait se poser sur l'île.", "J'ai traversé la Manche avec moins de turbulences que ce bal.",
          "Ce lustre me rappelle le tableau de bord de mon biplan.", "Demain, si le ciel se lève, je repars. Avec ou sans bateau.",
          "On m'a demandé si je pilotais vraiment moi-même. Évidemment !", "La tempête tourne au nord-ouest. Elle va durer.",
          "Je préfère mille fois un cockpit à un corset.", "Un jour, les femmes piloteront des paquebots du ciel. Vous verrez."]:
    add("remark", AV, t)
# event lines
for cat, reg, texts in [
    ("fire", "panic", ["Formez une chaîne avec les seaux, comme au terrain d'aviation !"]),
    ("fire_after", "neutral", ["Ça sent l'huile brûlée. Comme après un mauvais atterrissage."]),
    ("blackout", "startled", ["Sans instruments, on vole à l'oreille. Écoutez !"]),
    ("blackout_after", "neutral", ["La lumière revient. Tout le monde a encore ses deux ailes ?"]),
    ("attack_guest", "panic", ["Des bandits ! Ne faites pas les héros, ils sont nerveux !"]),
    ("kamikaze_guest", "panic", ["Il est couvert d'explosifs ! Éloignez-vous de lui !"]),
    ("robot_guest", "startled", ["Une machine qui marche ! Il faudra que je voie son moteur."]),
    ("piano_react", "neutral", ["Quel vacarme ! On dirait un moteur qui cale."]),
]:
    for t in texts:
        add(cat, AV, t, reg)
# the other c19 reaction categories
for cat, reg, texts in [
    ("ghost_react", "startled", ["Un fantôme ! Il vole mieux que certains pilotes."]),
    ("sword_react", "startled", ["Posez cette épée, mousquetaire, vous allez vous blesser !"]),
    ("ball_react", "neutral", ["Belle trajectoire ! Mais on jouait, là."]),
    ("safe_react", "gossip", ["Le coffre est ouvert ! Il y a de quoi s'acheter un avion."]),
    ("alarm_react", "startled", ["Une alarme ! Évacuation, comme à l'exercice !"]),
    ("shrink_react", "startled", ["Il a rapetissé ! Il tiendrait dans mon cockpit."]),
    ("dance_end", "warm", ["Bravo ! On remet ça ?"]),
    ("bar_toast", "warm", ["Aux hélices, et au champagne !"]),
]:
    for t in texts:
        add(cat, AV, t, reg)

# ---------------------------------------------------------------- Barnabé in the c19 reaction categories (P3 first)
for cat, reg, texts in [
    ("bomb_near", "neutral", ["Ce bip ne fait pas partie du service, Madame. Je vous conseille de vous éloigner.",
                              "Un objet qui fait bip. Je vais devoir en informer Monsieur le Comte."]),
    ("smoke_react", "neutral", ["De la fumée. Je vais ouvrir les fenêtres, avec votre permission.",
                                "Restez près de moi, Madame. Je connais le chemin les yeux fermés."]),
    ("defuse_react", "neutral", ["Parfait. Je ferai nettoyer le tapis.", "Bien. La soirée peut reprendre son cours."]),
    ("ghost_react", "neutral", ["Encore lui. Il ne paie jamais sa chambre.", "Un esprit. Je mettrai un couvert de plus."]),
    ("sword_react", "neutral", ["Monsieur, cette épée appartient à l'armure. Veuillez la reposer.",
                                "Je vous prierai de ne pas embrocher les invités."]),
    ("ball_react", "neutral", ["Les boules de billard restent sur la table, Monsieur.", "Je ramasserai. Comme toujours."]),
    ("safe_react", "neutral", ["Le coffre de Monsieur. Je n'ai rien vu, naturellement.", "Fermez-le en partant, je vous prie."]),
    ("alarm_react", "neutral", ["Une alarme. Je suppose que personne n'a jugé bon de me prévenir.",
                                "Mesdames, messieurs, dirigez-vous calmement vers la sortie."]),
    ("shrink_react", "neutral", ["Monsieur a rapetissé. Je vais ajuster le service.", "Voilà qui complique le choix du fauteuil."]),
    ("dance_end", "warm", ["Bravo. Très réussi.", "Les musiciens apprécieront."]),
    ("bar_toast", "warm", ["À votre santé, Madame, Monsieur.", "Santé. Je ne bois jamais pendant le service. Presque jamais."]),
]:
    for t in texts:
        add(cat, BA, t, reg)
add("gasp", BA, "Hum, hum. Keuh.", reg="design:cough", nonverbal=True, context="smoke")

# ---------------------------------------------------------------- dialogues with the other characters
dlg("AV001", [(AV, "Colonel, vous avez déjà volé ?"), ("char_colonel", "Jamais ! Un cavalier garde les pieds sur terre."),
              (AV, "Vous ne savez pas ce que vous manquez."), ("char_colonel", "Je sais très bien : le mal de mer, en plus haut.")])
dlg("AV002", [("char_comte", "Une femme pilote... Vous n'avez jamais peur, mademoiselle ?"),
              (AV, "Si, des gens qui posent cette question."), ("char_comte", "Touché. Je retire la question.")])
dlg("AV003", [("char_f_gown", "Ma chère, votre robe sent l'essence."), (AV, "C'est mon parfum. Il s'appelle Kérosène."),
              ("char_f_gown", "Il faudra me donner l'adresse.")])
dlg("AV004", [(AV, "Victor, vous me devez toujours un tour d'avion."), ("char_m_tailcoat", "Je vous le dois, comme je dois tout à tout le monde."),
              (AV, "Alors je vous emmène, et je vous lâche au-dessus de vos créanciers.")])
dlg("AV005", [("char_odette", "Toi, tu voles pour de vrai ? T'as pas le vertige ?"), (AV, "Le vertige, c'est pour ceux qui regardent en bas."),
              ("char_odette", "Moi, je regarde surtout le bar.")])
dlg("AV006", [("char_minuit", "Vous observez les fenêtres depuis tout à l'heure."), (AV, "J'observe le ciel. Il se lève au nord."),
              ("char_minuit", "Alors demain, quelqu'un pourra partir."), (AV, "Ou s'enfuir. Tout dépend de qui.")])
dlg("AV007", [(BA, "Madame désire-t-elle quelque chose ?"), (AV, "Un bulletin météo, Barnabé, et un cognac."),
              (BA, "Le cognac, je peux. La météo, je laisse cela à Dieu.")])
dlg("AV008", [(AV, "Barnabé, vous êtes ici depuis combien de temps ?"), (BA, "Depuis avant la tempête, Madame. Et depuis avant Monsieur le Comte."),
              (AV, "Alors vous savez tout."), (BA, "Je sais surtout me taire, Madame.")])
