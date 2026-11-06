"""Event lines: fire, blackout, attack (guests + bandits), kamikaze (himself + guests), robot (itself + guests), and the
lines after the fire / blackout."""
from _lib import lines

ITEMS = []
P, N, S, A = "panic", "neutral", "startled", "awkward"

lines(ITEMS, "fire", [
    (None, "Le feu est dans le petit salon !", P), (None, "Formez une chaîne avec les seaux !", P),
    (None, "Prenez les extincteurs du couloir !", P), (None, "Les tableaux ! Sauvez les tableaux !", P),
    (None, "Le feu remonte le long des boiseries !", P), (None, "Restez bas, sous la fumée !", P),
    (None, "Il pleut dehors, et ici tout brûle !", P), (None, "Quelqu'un a laissé une bougie sur les tentures !", P),
    (None, "Mouillez vos mouchoirs, vite !", P), (None, "Les flammes lèchent le plafond !", P),
    (None, "N'ouvrez pas cette porte, c'est chaud !", S), (None, "Je sens la chaleur à travers le mur.", S),
    (None, "Mais qui a mis le feu au bal ?", S), (None, "La fumée sort par le grand escalier.", S),
    (None, "On n'y voit plus à deux mètres.", S), (None, "Le buffet flambe comme une crêpe Suzette.", S),
    (None, "Les domestiques jettent de l'eau partout.", S), (None, "Il faut sauver le piano !", P),
    (None, "Ça crépite au-dessus de nos têtes.", S), (None, "Mon Dieu, la bibliothèque va y passer.", S),
    ("f", "J'ai les yeux qui piquent, je ne vois rien.", S), ("m", "Mon smoking sent le jambon fumé.", S),
])
lines(ITEMS, "fire_after", [
    (None, "Ça sent encore le roussi, non ?", A), (None, "Au moins, on n'a plus froid.", A),
    (None, "Le rôti sera bien cuit, ce soir.", A), (None, "Je crois que mes sourcils ont disparu.", A),
    (None, "Une soirée vraiment flamboyante.", A), (None, "Il faudra repeindre le salon. En noir.", A),
    (None, "Le feu est éteint. Mon enthousiasme aussi.", A), (None, "Notre hôte dira que c'était prévu.", A),
    (None, "J'ai encore de la suie jusque dans les oreilles.", A), (None, "Les pompiers de l'île, c'était nous.", A),
])
lines(ITEMS, "blackout", [
    (None, "Plus de lumière dans tout le manoir !", S), (None, "Quelqu'un a encore marché sur ma robe.", S),
    (None, "Ne bougez plus, j'entends des pas.", S), (None, "Qui a une allumette ? Une seule suffit !", S),
    (None, "J'ai serré une main. Ce n'était pas la bonne.", S), (None, "On dirait que la maison retient son souffle.", S),
    (None, "Restez près du mur, on suit le mur.", S), (None, "Oh pardon, je vous ai pris pour une colonne.", S),
    (None, "Il y a quelqu'un qui rit dans le noir.", S), (None, "C'est vous qui me tirez la manche ?", S),
    (None, "Les éclairs, au moins, ça éclaire.", S), (None, "Je ne retrouve plus la porte du salon.", S),
    (None, "Arrêtez de chuchoter, ça me donne la chair de poule.", S), (None, "Le majordome a sûrement une lampe.", S),
    (None, "Quelqu'un vient de passer tout près de moi.", S), (None, "Ma bague ! Quelqu'un m'a pris ma bague !", P),
    (None, "On ne voit même pas ses propres pieds.", S), (None, "Je compte jusqu'à dix et je hurle.", S),
    (None, "Ce n'est qu'une panne, n'est-ce pas ? N'est-ce pas ?", S), (None, "Tiens, le piano joue tout seul ?", S),
    ("f", "Monsieur, retirez votre main de ma taille.", S), ("m", "Madame, je crois que vous êtes assise sur moi.", S),
])
lines(ITEMS, "blackout_after", [
    (None, "Tiens, il manque quelqu'un, non ?", N), (None, "Qui m'a embrassé dans le noir ? Avouez !", N),
    (None, "Ouf. J'ai cru que la nuit ne finirait jamais.", N), (None, "Où est passé mon collier ?", N),
    (None, "Bon, on reprend la danse ?", N), (None, "On voit enfin les visages. Enfin, les masques.", N),
    (None, "Vous étiez là pendant tout ce temps ?", N), (None, "Quelqu'un a mangé les petits fours dans le noir.", N),
    (None, "Mes yeux ne s'y habituent plus.", N), (None, "Je ne poserai aucune question.", N),
])
lines(ITEMS, "attack_guest", [
    (None, "Des gangsters ! Dans un bal !", P), (None, "Donnez-leur ce qu'ils veulent !", P),
    (None, "Ils prennent l'argenterie !", P), (None, "Cachez vos bijoux, vite !", P),
    (None, "Derrière le piano, tout le monde !", P), (None, "Ils sont entrés par la terrasse !", P),
    (None, "Ne les regardez pas dans les yeux !", S), (None, "Ce sont de vrais bandits, ou un jeu ?", S),
    (None, "Mon Dieu, ils ont des mitraillettes !", P, {"gun": True}), (None, "Couchez-vous, ils tirent partout !", P, {"gun": True}),
    (None, "Ils ont pris la montre du baron !", S), (None, "Quelqu'un a prévenu la police ? Ah, le téléphone !", S),
    (None, "Ils sont arrivés en canot, par la tempête !", S), (None, "Faites le mort, c'est plus sûr.", S),
    (None, "Laissez-les partir, laissez-les partir !", P), (None, "Pas mon collier, c'est un souvenir !", P),
    (None, "Ils vont nous dévaliser jusqu'aux chaussettes.", S), (None, "Restez calme, ce ne sont que des voleurs.", S),
    (None, "Ils ont un drôle d'accent, ces brigands.", S), (None, "Prenez mon mari, mais laissez mes perles !", P),
    (None, "Il y en a un derrière la porte !", P),
])
lines(ITEMS, "attack_bandit", [
    ("m", "Les bijoux dans le sac, et que ça saute !", "threat", {"voice": "b1_brute"}),
    ("m", "Toi, le gros, ta montre !", "threat", {"voice": "b1_brute"}),
    ("m", "On ne bouge plus, on ne respire plus !", "threat", {"voice": "b1_brute"}),
    ("m", "Le premier qui crie, je le fais taire !", "threat", {"voice": "b1_brute"}),
    ("m", "Allez, allez, les perles aussi, la petite dame !", "threat", {"voice": "b2_voyou"}),
    ("m", "Joli manoir. Dommage pour vous.", "threat", {"voice": "b2_voyou"}),
    ("m", "Personne ne quitte l'île, compris ?", "threat", {"voice": "b2_voyou"}),
    ("m", "Les mains bien en vue, les rupins !", "threat", {"voice": "b2_voyou"}),
])
lines(ITEMS, "kamikaze", [
    ("m", "Écartez-vous ! J'ai tout ce qu'il faut sous ma veste !", "manic", {"voice": "k1_kamikaze"}),
    ("m", "Le grand soir, c'est ce soir !", "manic", {"voice": "k1_kamikaze"}),
    ("m", "Vous rirez moins dans une minute !", "manic", {"voice": "k1_kamikaze"}),
    ("m", "Personne ne m'invitait jamais ! Eh bien, me voilà !", "manic", {"voice": "k1_kamikaze"}),
    ("m", "Comptez avec moi ! Dix, neuf, huit !", "manic", {"voice": "k1_kamikaze"}),
    ("m", "Que la fête commence enfin !", "manic", {"voice": "k1_kamikaze"}),
    ("m", "Je vais faire trembler ce vieux manoir !", "manic", {"voice": "k1_kamikaze"}),
    ("m", "Courez, courez, ça ne servira à rien !", "manic", {"voice": "k1_kamikaze"}),
    ("m", "Vive l'anarchie, et vive le champagne !", "manic", {"voice": "k1_kamikaze"}),
    ("m", "Boum ! Ha ha ! Pas encore, pas encore !", "manic", {"voice": "k1_kamikaze"}),
])
lines(ITEMS, "kamikaze_guest", [
    (None, "Cet homme est couvert de dynamite !", P), (None, "Éloignez-vous de lui, vite !", P),
    (None, "Il va tous nous faire sauter !", P), (None, "Quelqu'un, assommez-le avec un vase !", P),
    (None, "Il court vers la salle de bal !", P), (None, "Ne le suivez surtout pas !", P),
    (None, "Mais qui a invité cet énergumène ?", S), (None, "Il a une mèche allumée dans la poche !", P),
    (None, "Fermez la porte derrière lui !", P), (None, "Il sent la poudre à dix mètres !", S),
])
lines(ITEMS, "robot_voice", [
    ("m", "Analyse du visage. Masque détecté.", "flat", {"voice": "r1_robot"}),
    ("m", "Invité non conforme. Correction en cours.", "flat", {"voice": "r1_robot"}),
    ("m", "Mouvement suspect dans le secteur.", "flat", {"voice": "r1_robot"}),
    ("m", "Je vous vois. Je vous entends. Je vous compte.", "flat", {"voice": "r1_robot"}),
    ("m", "Protocole de bal activé. Dansez.", "flat", {"voice": "r1_robot"}),
    ("m", "Erreur. Erreur. Sourire non reconnu.", "flat", {"voice": "r1_robot"}),
    ("m", "Toute résistance est inutile.", "flat", {"voice": "r1_robot"}),
    ("m", "Niveau d'énergie optimal. Chasse en cours.", "flat", {"voice": "r1_robot"}),
    ("m", "Ne courez pas. Cela ne change rien.", "flat", {"voice": "r1_robot"}),
    ("m", "Fin de la récréation.", "flat", {"voice": "r1_robot"}),
])
lines(ITEMS, "robot_guest", [
    (None, "Une machine qui marche toute seule !", P), (None, "Ses yeux sont rouges comme des braises !", S),
    (None, "C'est une attraction ou une menace ?", S), (None, "Il a fait un trou dans le mur avec son rayon !", P),
    (None, "Cachez-vous, il voit à travers les masques !", P), (None, "On dirait un scaphandrier en colère.", S),
    (None, "Qui a construit cette horreur ?", S), (None, "Il marche vers nous, il marche vers nous !", P),
    (None, "Le sol tremble à chacun de ses pas.", S), (None, "Ne restez pas devant lui !", P),
])
