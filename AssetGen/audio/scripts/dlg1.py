"""Dialogues d001-d050: gossip, hosts, masks, food, band, storm on the island, small mysteries."""
from _lib import dialogue

ITEMS = []
D = lambda did, ga, gb, turns: dialogue(ITEMS, did, ga, gb, turns)  # noqa: E731

D("d001", "f", "m", [("A", "Vous avez vu ? Le bac ne repartira pas avant demain matin."),
                     ("B", "Avec cette tempête ? Nous voilà prisonniers de nos hôtes."),
                     ("A", "Prisonniers du champagne, plutôt. Il y a pire.")])
D("d002", "m", "f", [("A", "Qui se cache sous ce masque de renard, à votre avis ?"),
                     ("B", "Quelqu'un qui n'a aucune envie d'être reconnu, évidemment.")])
D("d003", "f", "f", [("A", "La comtesse a encore changé de coiffure."),
                     ("B", "Pour la quatrième fois cette année."),
                     ("A", "On dit que c'est pour plaire au chef d'orchestre."),
                     ("B", "Alors elle perd son temps : il n'aime que sa clarinette.")])
D("d004", "m", "m", [("A", "Ces huîtres viennent de l'île, paraît-il."),
                     ("B", "Alors elles ont vu plus de tempêtes que nous.")])
D("d005", "f", "m", [("A", "Vous dansez, ce soir ?"),
                     ("B", "Seulement si l'orchestre joue assez lentement pour mes genoux."),
                     ("A", "Je vais leur demander une valse pour vieillards."),
                     ("B", "Vous êtes trop bonne. Et trop cruelle.")])
D("d006", "m", "f", [("A", "Avez-vous entendu ces pas au grenier, tout à l'heure ?"),
                     ("B", "Le vent, sans doute."),
                     ("A", "Le vent ne porte pas de talons.")])
D("d007", "f", "m", [("A", "Notre hôte m'a juré que ce manoir n'avait aucun fantôme."),
                     ("B", "C'est exactement ce que dirait un fantôme.")])
D("d008", "m", "m", [("A", "Vous connaissez l'Américain, là-bas ?"),
                     ("B", "Il a acheté trois usines et un titre de baron."),
                     ("A", "Le titre a dû coûter plus cher que les usines.")])
D("d009", "f", "f", [("A", "Votre robe est divine. C'est de Paris ?"),
                     ("B", "De Paris, oui. Enfin, de la boutique en face de Paris."),
                     ("A", "On n'y voit que du feu.")])
D("d010", "m", "f", [("A", "Les éclairs font trembler les vitres du salon."),
                     ("B", "Tant mieux, ça couvre le pianiste.")])
D("d011", "f", "m", [("A", "On m'a placée à côté du colonel au dîner."),
                     ("B", "Mes condoléances. Il vous a raconté sa campagne d'Afrique ?"),
                     ("A", "Trois fois. Avec les bruitages."),
                     ("B", "Alors il vous apprécie.")])
D("d012", "m", "f", [("A", "Pourquoi tout le monde porte-t-il un masque, au juste ?"),
                     ("B", "Pour que les maris ne reconnaissent pas leurs épouses."),
                     ("A", "Ou l'inverse.")])
D("d013", "f", "f", [("A", "Le majordome boite depuis ce matin."),
                     ("B", "Il dit qu'il a glissé dans la cave."),
                     ("A", "Que faisait-il dans la cave à six heures ?"),
                     ("B", "Voilà une excellente question.")])
D("d014", "m", "m", [("A", "Ce cigare vient de La Havane."),
                     ("B", "Il sent plutôt le grenier de ma grand-mère.")])
D("d015", "f", "m", [("A", "Vous croyez que la comtesse est vraiment comtesse ?"),
                     ("B", "Ce soir, tout le monde est ce qu'il prétend être."),
                     ("A", "Alors je suis une princesse."),
                     ("B", "Votre Altesse, permettez-moi de vous resservir.")])
D("d016", "m", "f", [("A", "J'ai perdu mon bouton de manchette dans le potage."),
                     ("B", "Ne le dites à personne. Quelqu'un va le trouver au dessert.")])
D("d017", "f", "f", [("A", "Le prince russe m'a baisé la main pendant une minute entière."),
                     ("B", "Il cherchait peut-être votre bague."),
                     ("A", "Mon Dieu. Elle est toujours là ?")])
D("d018", "m", "m", [("A", "Si cette pluie continue, l'île va finir par couler."),
                     ("B", "Au moins, nous coulerons avec un bon bordeaux.")])
D("d019", "f", "m", [("A", "Qui a choisi cette musique ?"),
                     ("B", "Notre hôtesse. Elle dit que c'est moderne."),
                     ("A", "Moderne, c'est un mot poli pour bruyant.")])
D("d020", "m", "f", [("A", "Mademoiselle, nous sommes-nous déjà rencontrés à Deauville ?"),
                     ("B", "Je n'ai jamais mis les pieds à Deauville."),
                     ("A", "Alors c'était à Biarritz."),
                     ("B", "Ni à Biarritz. Essayez encore, c'est amusant.")])
D("d021", "f", "f", [("A", "Il paraît qu'un tableau a disparu de la galerie."),
                     ("B", "Lequel ?"),
                     ("A", "Le portrait de l'arrière-grand-oncle. Celui qui louchait."),
                     ("B", "Le voleur a du goût, finalement.")])
D("d022", "m", "m", [("A", "Vous jouez au billard après le dîner ?"),
                     ("B", "Seulement contre des gens qui ont bu plus que moi."),
                     ("A", "Alors vous ne trouverez personne.")])
D("d023", "f", "m", [("A", "Ce masque me tient horriblement chaud."),
                     ("B", "Enlevez-le."),
                     ("A", "Jamais. Mon couturier en mourrait.")])
D("d024", "m", "f", [("A", "Le téléphone ne fonctionne plus depuis une heure."),
                     ("B", "La ligne a dû tomber avec l'orage."),
                     ("A", "Ou quelqu'un l'a coupée."),
                     ("B", "Vous lisez trop de romans policiers.")])
D("d025", "f", "f", [("A", "Ma fille veut épouser un aviateur."),
                     ("B", "C'est romantique."),
                     ("A", "C'est surtout très haut.")])
D("d026", "m", "m", [("A", "Notre hôte a fait fortune dans quoi, déjà ?"),
                     ("B", "Le caoutchouc, je crois. Ou les chapeaux."),
                     ("A", "Les deux, peut-être. Des chapeaux en caoutchouc."),
                     ("B", "Voilà qui expliquerait le salon.")])
D("d027", "f", "m", [("A", "Le homard avait l'air vexé dans son assiette."),
                     ("B", "On l'aurait été à moins.")])
D("d028", "m", "f", [("A", "Vous savez pourquoi le grand escalier grince à minuit ?"),
                     ("B", "Parce que le majordome monte se coucher."),
                     ("A", "Il dort au rez-de-chaussée.")])
D("d029", "f", "f", [("A", "J'adore ces bals : on peut dévisager tout le monde."),
                     ("B", "Et personne ne vous le reproche, puisqu'on ne vous reconnaît pas."),
                     ("A", "C'est la démocratie, en somme.")])
D("d030", "m", "f", [("A", "Ce champagne a un goût de pluie."),
                     ("B", "C'est l'humidité de l'île. Tout a un goût de pluie, ici."),
                     ("A", "Même vous ?"),
                     ("B", "Surtout moi. Je suis bretonne.")])
D("d031", "f", "m", [("A", "Le pianiste a des mains magnifiques."),
                     ("B", "Dommage qu'il ne s'en serve pas pour jouer juste.")])
D("d032", "m", "m", [("A", "On dit que l'Américain veut racheter le manoir."),
                     ("B", "Avec les invités dedans ?"),
                     ("A", "Il a dit : tout compris.")])
D("d033", "f", "f", [("A", "Vous avez remarqué ? Toutes les horloges sont arrêtées."),
                     ("B", "Notre hôtesse déteste qu'on regarde l'heure."),
                     ("A", "C'est charmant, ou très inquiétant.")])
D("d034", "m", "f", [("A", "Puis-je vous offrir une coupe ?"),
                     ("B", "Vous m'en avez déjà offert trois."),
                     ("A", "Je ne m'en souvenais plus."),
                     ("B", "Moi non plus, c'est bon signe.")])
D("d035", "f", "m", [("A", "Ce monsieur en noir nous regarde depuis tout à l'heure."),
                     ("B", "Il regarde surtout le buffet."),
                     ("A", "Ah. Je préfère ça.")])
D("d036", "m", "m", [("A", "Le bateau de ravitaillement n'est pas arrivé."),
                     ("B", "Nous allons manquer de quoi ?"),
                     ("A", "De glaçons, d'abord. Ensuite, de patience.")])
D("d037", "f", "f", [("A", "Comment trouvez-vous ma voisine de table ?"),
                     ("B", "Charmante. Elle a un rire de mouette."),
                     ("A", "C'est ma sœur."),
                     ("B", "Une mouette très distinguée.")])
D("d038", "m", "f", [("A", "Vous croyez aux sciences occultes ?"),
                     ("B", "Seulement après minuit et avant le café.")])
D("d039", "f", "m", [("A", "La salle de bal est plus petite que l'an dernier."),
                     ("B", "Non, c'est nous qui avons grossi."),
                     ("A", "Parlez pour vous.")])
D("d040", "m", "m", [("A", "Vous avez gagné aux cartes, hier soir ?"),
                     ("B", "J'ai perdu ma montre et gagné un cheval."),
                     ("A", "Où est le cheval ?"),
                     ("B", "Sur le continent. Comme ma montre, d'ailleurs.")])
D("d041", "f", "m", [("A", "Ne me dites pas que vous êtes le docteur."),
                     ("B", "Je ne vous le dirai pas, alors."),
                     ("A", "J'ai mal au genou depuis mardi.")])
D("d042", "m", "f", [("A", "La mer est si forte que les mouettes marchent."),
                     ("B", "Elles ont bien raison. Je ferais pareil.")])
D("d043", "f", "f", [("A", "Elle porte des perles à un bal masqué. Quelle idée."),
                     ("B", "Pour qu'on la reconnaisse, justement."),
                     ("A", "Alors à quoi bon le masque ?")])
D("d044", "m", "m", [("A", "Je ne retrouve plus ma femme."),
                     ("B", "Quel masque porte-t-elle ?"),
                     ("A", "Je n'en ai aucune idée. C'est elle qui m'a habillé."),
                     ("B", "Alors attendez qu'elle vous retrouve.")])
D("d045", "f", "m", [("A", "Ce bal est le plus beau de la saison."),
                     ("B", "C'est aussi le seul où on ne peut pas partir.")])
D("d046", "m", "f", [("A", "J'ai vu une lumière dans la tour, alors que personne n'y monte."),
                     ("B", "C'est peut-être le gardien du phare."),
                     ("A", "Il n'y a pas de phare sur cette île."),
                     ("B", "Alors je ne veux pas savoir.")])
D("d047", "f", "f", [("A", "Vous avez goûté le soufflé ?"),
                     ("B", "Il est retombé avant que j'arrive."),
                     ("A", "Comme l'enthousiasme du colonel.")])
D("d048", "m", "m", [("A", "Le prince prétend avoir dansé avec le tsar."),
                     ("B", "Le tsar ne dansait pas."),
                     ("A", "C'est pour ça qu'il s'en souvient si bien.")])
D("d049", "f", "m", [("A", "Si l'orage coupe le courant, je hurle."),
                     ("B", "Prévenez-moi, que je me bouche les oreilles."),
                     ("A", "Vous me tiendrez la main ?"),
                     ("B", "Seulement si je la trouve dans le noir.")])
D("d050", "m", "f", [("A", "Pardonnez-moi, j'ai marché sur votre traîne."),
                     ("B", "Ce n'est rien, elle a connu pire."),
                     ("A", "Vraiment ?"),
                     ("B", "Le colonel. Deux fois.")])
