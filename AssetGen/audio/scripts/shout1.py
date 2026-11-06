"""Panic shouts by cause (gun / fire / explosion / blackout / generic) and calm-down lines (half whispered)."""
from _lib import lines

ITEMS = []
P, W, N = "panic", "whisper", "neutral"


def shouts(cause, specs):
    for s in specs:
        g, text = s[0], s[1]
        lines(ITEMS, "shout", [(g, text, P, {"cause": cause, "gun": cause == "gun"})])


shouts("gun", [
    (None, "Il a tiré ! Il a tiré !"), (None, "Un coup de feu ! Couchez-vous !"), (None, "Il est armé, reculez !"),
    (None, "Quelqu'un a sorti un revolver !"), (None, "On tire dans la salle de bal !"), (None, "Il vient de tuer quelqu'un !"),
    (None, "Lâchez cette arme !"), (None, "Il a abattu ce pauvre homme !"), (None, "Le tireur est là, juste là !"),
    (None, "Ne restez pas dans sa ligne de mire !"), (None, "Il va tirer encore !"), (None, "Derrière les colonnes, vite !"),
    (None, "Un détective qui tire sur les invités !"), (None, "Il a tiré sans sommation !"), (None, "Arrêtez-le, il est fou à lier !"),
    (None, "Mon Dieu, il y a du sang partout !"), (None, "C'est un assassin ! Un assassin !"), (None, "Il a encore son arme à la main !"),
    (None, "Quelqu'un, désarmez-le !"), (None, "Il a tiré à bout portant !"), (None, "Sortez par les cuisines, il tire !"),
    (None, "Ce n'est pas un jeu, il a une vraie arme !"), (None, "Il a tiré sur un invité !"), (None, "Écartez-vous, il recharge !"),
    (None, "Le coup est parti tout seul ? Mon œil !"), (None, "Pas de geste brusque, il est armé !"),
    (None, "Appelez la gendarmerie, il y a un tireur !"), (None, "Il a descendu quelqu'un devant le buffet !"),
    (None, "Baissez la tête ! Baissez la tête !"), (None, "Il pointe son arme sur nous !"), (None, "J'ai entendu deux détonations !"),
    ("m", "Ne tirez pas, je suis désarmé !"), ("f", "Ne tirez pas, je suis une invitée !"),
])
shouts("fire", [
    (None, "Le feu ! Le feu a pris !"), (None, "Les rideaux brûlent !"), (None, "Il y a de la fumée partout !"),
    (None, "Sortez, la pièce est en flammes !"), (None, "Apportez de l'eau ! Des seaux !"), (None, "Ça brûle, ça brûle !"),
    (None, "Le feu gagne le couloir !"), (None, "Mon Dieu, les flammes montent !"), (None, "Ouvrez les fenêtres ! Non, fermez-les !"),
    (None, "Je ne vois plus rien, la fumée !"), (None, "Le tapis a pris feu !"), (None, "Éteignez ça, vite !"),
    (None, "Ne restez pas près du feu !"), (None, "La cheminée a craché des braises !"), (None, "Le lustre est en flammes !"),
    (None, "Mettez-vous un mouchoir sur la bouche !"), (None, "Tout le monde dehors, sous la pluie !"),
    (None, "Ça sent le roussi, courez !"), (None, "Le bois craque, ça va s'effondrer !"), (None, "Qui a renversé les bougies ?"),
    (None, "Au secours, le feu me coupe le chemin !"), (None, "Les tentures, elles flambent !"), (None, "On étouffe, ici !"),
    ("f", "Ma robe ! Ma robe a pris feu !"), ("m", "Ma moustache ! J'ai brûlé ma moustache !"), (None, "Par ici, la sortie, par ici !"),
])
shouts("explosion", [
    (None, "Une explosion ! Une explosion !"), (None, "Tout a sauté !"), (None, "Le mur s'est effondré !"),
    (None, "Mes oreilles ! Je n'entends plus rien !"), (None, "C'était une bombe ?"), (None, "Il y a des débris partout !"),
    (None, "Le plafond va tomber !"), (None, "Courez, ça peut sauter encore !"), (None, "Il y a des blessés là-bas !"),
    (None, "Les vitres ont volé en éclats !"), (None, "Qu'est-ce qui a explosé ?"), (None, "La poussière, je ne vois rien !"),
    (None, "Tout le manoir a tremblé !"), (None, "Il a fait tout sauter, le fou !"), (None, "Écartez-vous des fenêtres !"),
    (None, "J'ai cru que la foudre était tombée sur nous !"), (None, "Quelqu'un est sous les décombres !"),
    (None, "Ça venait de la pièce d'à côté !"), (None, "Le souffle m'a jeté par terre !"), (None, "Mon Dieu, il ne reste plus rien !"),
    (None, "Ne bougez pas, le sol est fragile !"),
])
shouts("blackout", [
    (None, "Le noir complet !"), (None, "Qui a coupé le courant ?"), (None, "Je ne vois plus mes mains !"),
    (None, "Ne me bousculez pas !"), (None, "Où est la sortie ?"), (None, "Quelqu'un m'a attrapé le bras !"),
    (None, "Allumez une bougie, n'importe qui !"), (None, "Restez où vous êtes !"), (None, "J'ai trébuché sur quelque chose !"),
    (None, "Il y a quelqu'un juste derrière moi !"), (None, "Qui respire comme ça ?"), (None, "Lâchez-moi, je ne vous connais pas !"),
    (None, "Tout est noir, on ne voit rien !"), (None, "Les fusibles ! Allez voir les fusibles !"), (None, "Quelqu'un a des bougies ?"),
    (None, "Arrêtez de me marcher dessus !"), (None, "C'est encore l'orage, j'en suis sûr !"), (None, "Ne paniquez pas, surtout !"),
    (None, "Qui a éteint ? Rallumez !"), (None, "J'ai perdu mon cavalier dans le noir !"), (None, "Une main froide m'a touché la nuque !"),
])
shouts("generic", [
    (None, "Mon Dieu, mon Dieu !"), (None, "Courez ! Courez !"), (None, "Tout le monde dehors !"), (None, "Qu'est-ce qui se passe ?"),
    (None, "Laissez-moi passer !"), (None, "Ne poussez pas !"), (None, "Il faut prévenir quelqu'un !"), (None, "Où sont nos hôtes ?"),
    (None, "Je veux rentrer chez moi !"), (None, "C'est un cauchemar !"), (None, "À l'aide ! À l'aide !"), (None, "Vite, par la terrasse !"),
    (None, "Ne restons pas là !"), (None, "Écartez-vous, bon sang !"), (None, "Qu'on fasse venir un médecin !"),
    (None, "Fermez les portes !"), (None, "Ce bal est maudit !"), (None, "On va tous y passer !"), (None, "Suivez-moi, je connais la maison !"),
    (None, "Par ici ! Non, par là !"), (None, "Prenez les enfants ! Ah, il n'y a pas d'enfants."), (None, "Gardez votre calme, bon sang !"),
    (None, "Je savais que cette soirée finirait mal !"), (None, "Majordome ! Majordome !"), (None, "Personne ne bouge ! Ou plutôt si, tout le monde court !"),
    (None, "Mes perles ! Où sont mes perles ?"), (None, "On se croirait au Titanic !"), (None, "Ne me laissez pas seul ici !"),
    (None, "Mais faites quelque chose !"), (None, "C'est la fin du monde !"), ("f", "Mon mari ! Où est mon mari ?"),
    ("m", "Ma femme ! Quelqu'un a vu ma femme ?"),
])

# calm-down after a panic: awkward, darkly funny; about half whispered
lines(ITEMS, "calm", [
    (None, "Bon. On reprend où on en était ?", N), (None, "Quelqu'un a encore faim ?", N),
    (None, "Ce n'était peut-être pas si grave.", N), (None, "Je propose qu'on n'en parle plus jamais.", N),
    (None, "Il avait l'air de quelqu'un qui cherchait les ennuis.", N), (None, "Au moins, il y a plus de place pour danser.", N),
    (None, "Le champagne est toujours frais, c'est déjà ça.", N), (None, "Remettez la musique, je vous prie.", N),
    (None, "Je ne l'aimais pas beaucoup, de toute façon.", N), (None, "On dira que c'était un malaise.", N),
    (None, "Ce sont des choses qui arrivent. Surtout ici.", N), (None, "Enfin, il ne souffre plus.", N),
    (None, "Il faudra bien prévenir sa famille. Demain.", N), (None, "Notre hôte va être furieux pour le tapis.", N),
    (None, "C'est la deuxième fois cette année. Non, la troisième.", N), (None, "Respirez, ma chère, respirez.", N),
    (None, "Bon, eh bien, la soirée continue.", N), (None, "Quelqu'un pourrait couvrir ça avec une nappe ?", N),
    (None, "Je n'ai jamais vu un bal aussi animé.", N), (None, "Mon cœur bat encore la chamade.", N),
    (None, "Personne n'a rien vu. C'est bien compris ?", W), (None, "Il me doit encore une danse, celui-là.", W),
    (None, "Je savais bien qu'il cachait quelque chose.", W), (None, "Ne regardez pas par là, ça vaut mieux.", W),
    (None, "On fera comme si de rien n'était, d'accord ?", W), (None, "Vous croyez que c'était lui, le coupable ?", W),
    (None, "J'ai toujours dit que ce masque portait malheur.", W), (None, "Pauvre diable. Enfin, presque pauvre.", W),
    (None, "Moi, je n'étais même pas dans la pièce.", W), (None, "Il avait volé mon fiacre en mille neuf cent douze.", W),
    (None, "Si on me demande, j'étais au buffet.", W), (None, "Ce détective tire d'abord et réfléchit ensuite.", W, {"gun": True}),
    (None, "Le pire, c'est qu'il était presque aimable.", W), (None, "On devrait peut-être fermer les rideaux.", W),
    (None, "Vous avez vu sa tête ? Non, ne regardez pas.", W), (None, "Je ne dirai rien. Je n'ai rien vu. Rien de rien.", W),
    (None, "Il paraît que ça arrive dans les meilleurs bals.", W), (None, "Je crois que je vais reprendre un cognac.", W),
    (None, "Chut. Faisons comme si nous parlions de la pluie.", W), (None, "Encore un qui ne dansera plus.", W),
    (None, "Bon débarras, si vous voulez mon avis.", W), ("f", "Je suis toute retournée.", N), ("m", "Je suis tout retourné.", N),
])
