"""Dialogues d101-d160 (a few absurd ones, a few with the characters of the cast)."""
from _lib import dialogue

ITEMS = []
D = lambda did, ga, gb, turns, voices=None: dialogue(ITEMS, did, ga, gb, turns, voices)  # noqa: E731
W = "whisper"

D("d101", "m", "f", [("A", "Ma chère, ce bal vous rajeunit."),
                     ("B", "C'est le masque. Il cache vingt ans."),
                     ("A", "Alors gardez-le jusqu'à Noël.")])
D("d102", "f", "m", [("A", "Vous êtes américain ? Vous avez un accent délicieux."),
                     ("B", "Merci ! Et vous, vous avez un château ?"),
                     ("A", "Un petit. Il fuit."),
                     ("B", "Je l'achète !")], voices={"B": "m5_americain"})
D("d103", "m", "m", [("A", "Prince, est-il vrai que vous avez fui Saint-Pétersbourg en traîneau ?"),
                     ("B", "En traîneau, en train, en bateau. Et un peu à pied."),
                     ("A", "Quelle épopée !"),
                     ("B", "Le plus dur, ce fut le bac de ce soir.")], voices={"B": "m11_prince"})
D("d104", "f", "f", [("A", "Lady, vous buvez du thé à minuit ?"),
                     ("B", "Le thé est une affaire sérieuse, ma chère. L'heure, beaucoup moins.")], voices={"B": "f8_anglaise"})
D("d105", "m", "f", [("A", "Docteur, ce n'est pas vous qui m'avez soigné à Vichy ?"),
                     ("B", "Je suis une femme, monsieur."),
                     ("A", "Ah. Alors ce n'était pas vous.")])
D("d106", "f", "m", [("A", "On vous a déjà dit que vous ressembliez à Valentino ?"),
                     ("B", "Tous les soirs. Surtout ma mère."),
                     ("A", "Votre mère a du goût.")])
D("d107", "m", "m", [("A", "Mon cher, d'où vient votre accent ?"),
                     ("B", "De Marseille, peuchère ! On ne le perd jamais."),
                     ("A", "On ne cherche même pas à le perdre, j'ai l'impression.")], voices={"B": "m10_marseillais"})
D("d108", "f", "f", [("A", "J'ai tourné dans trois films, ma chérie."),
                     ("B", "Je ne les ai pas vus."),
                     ("A", "Personne. C'est ce qui les rend précieux.")], voices={"A": "f6_actrice"})
D("d109", "m", "f", [("A", "Madame la duchesse, permettez-moi de vous présenter mes hommages."),
                     ("B", "Permis. Soyez bref, je vieillis."),
                     ("A", "Mes hommages."),
                     ("B", "Parfait. Vous irez loin.")], voices={"B": "f5_duchesse"})
D("d110", "f", "m", [("A", "Vous êtes champion de tennis, n'est-ce pas ?"),
                     ("B", "Champion de France, mademoiselle ! Trois années de suite !"),
                     ("A", "Alors attrapez-moi ce petit four au vol.")], voices={"B": "m12_sportif"})
D("d111", "m", "f", [("A", "Je vous trouve bien silencieuse, ce soir."),
                     ("B", "Je viens de me marier. J'observe."),
                     ("A", "Et qu'observez-vous ?"),
                     ("B", "Que mon mari danse beaucoup.")], voices={"B": "f11_mariee"})
D("d112", "f", "m", [("A", "Vous écrivez des vers, paraît-il ?"),
                     ("B", "J'écris surtout des dettes. En alexandrins."),
                     ("A", "Au moins, elles riment.")])
D("d113", "m", "m", [("A", "Vous avez placé votre argent où, cette année ?"),
                     ("B", "Sous mon matelas. Et un peu dans le caviar de ce soir."),
                     ("A", "Placement à court terme.")])
D("d114", "f", "f", [("A", "Vous savez ce qu'on raconte sur la veuve ?"),
                     ("B", "Qu'elle a enterré trois maris ?"),
                     ("A", "Quatre. Et elle cherche le cinquième ici même."),
                     ("B", "Alors je surveille le mien.", W)])
D("d115", "m", "f", [("A", "J'ai écrasé un escargot sur le perron."),
                     ("B", "Il voulait sans doute quitter l'île, lui aussi.")])
D("d116", "f", "m", [("A", "Vous croyez que les poissons ont peur de l'orage ?"),
                     ("B", "Je crois qu'ils s'en moquent. Ils sont déjà mouillés.")])
D("d117", "m", "m", [("A", "Si je vous dis girafe, vous me répondez quoi ?"),
                     ("B", "Je vous réponds que vous avez trop bu."),
                     ("A", "Mauvaise réponse. C'était le mot de passe."),
                     ("B", "Le mot de passe de quoi ?"),])
D("d118", "f", "f", [("A", "J'ai vu un perroquet dans la bibliothèque."),
                     ("B", "Il parlait ?"),
                     ("A", "Il citait Racine. Mal.")])
D("d119", "m", "f", [("A", "Avez-vous déjà mangé une huître qui vous regardait ?"),
                     ("B", "Toutes les huîtres me regardent. C'est pour ça que je n'en mange pas.")])
D("d120", "f", "m", [("A", "Vous avez l'heure ?"),
                     ("B", "Non. Toutes les pendules sont arrêtées, et ma montre aussi."),
                     ("A", "Alors il est quelle heure, selon vous ?"),
                     ("B", "L'heure de reprendre un verre.")])
D("d121", "m", "m", [("A", "Le colonel a sorti sa médaille pour le dîner."),
                     ("B", "Laquelle ? Il en a vingt."),
                     ("A", "Celle du concours agricole.")])
D("d122", "f", "f", [("A", "Pourquoi les domestiques portent-ils des masques, eux aussi ?"),
                     ("B", "Pour qu'on ne sache pas lequel a cassé le vase."),
                     ("A", "Quel vase ?"),
                     ("B", "Celui qui sera cassé tout à l'heure.")])
D("d123", "m", "f", [("A", "On dit que vous avez traversé la Manche en avion."),
                     ("B", "Deux fois. La seconde, sans le faire exprès."),
                     ("A", "Comment peut-on traverser la Manche sans le faire exprès ?"),
                     ("B", "Avec une boussole d'occasion.")], voices={"B": "f4_aviatrice"})
D("d124", "f", "m", [("A", "Je vous préviens, je mords quand je m'ennuie."),
                     ("B", "Alors racontez-moi votre enfance, je vous écoute.")])
D("d125", "m", "m", [("A", "Le baron a encore perdu son dentier dans la soupe."),
                     ("B", "Ça devient une tradition."),
                     ("A", "Le chef a mis la soupe à la carte : velouté à la surprise.")])
D("d126", "f", "f", [("A", "Ma chère, vous avez vu ? L'orchestre joue un tango."),
                     ("B", "Un tango ? Ici ? Sur une île bretonne ?"),
                     ("A", "Le contrebassiste est argentin. Enfin, il le dit.")])
D("d127", "m", "f", [("A", "Si ce bal était un roman, qui serait l'assassin ?"),
                     ("B", "Celui qui pose la question, en général."),
                     ("A", "Je retire ma question.")])
D("d128", "f", "m", [("A", "Vous aimez la mer ?"),
                     ("B", "Je l'aime de loin, sur une carte postale, bien sèche.")])
D("d129", "m", "m", [("A", "Qu'est-ce que vous faites dans la vie ?"),
                     ("B", "Je vais à des bals."),
                     ("A", "Et ça paie ?"),
                     ("B", "Ça dépend avec qui on danse.")])
D("d130", "f", "f", [("A", "Il paraît que la cuisinière lit l'avenir dans le marc de café."),
                     ("B", "Et alors, que dit-il ?"),
                     ("A", "Qu'il faut changer de café.")])
D("d131", "m", "f", [("A", "Pardon, ce fauteuil est libre ?"),
                     ("B", "Il l'est. Moi, non."),
                     ("A", "Je reste debout, alors.")])
D("d132", "f", "m", [("A", "Vous avez entendu ? Quelqu'un a joué trois notes sur le piano."),
                     ("B", "Le fantôme du manoir. Il ne connaît que celles-là."),
                     ("A", "Un fantôme mélomane. Comme c'est rassurant.")])
D("d133", "m", "m", [("A", "Vous fumez ?"),
                     ("B", "Seulement les cigares des autres."),
                     ("A", "Alors j'ai bien fait de cacher les miens.")])
D("d134", "f", "f", [("A", "Ma robe est bleue, et la sienne aussi. C'est un scandale."),
                     ("B", "La vôtre est plus jolie."),
                     ("A", "Vous dites ça pour me consoler."),
                     ("B", "Je dis ça parce qu'elle est assise sur la sienne.")])
D("d135", "m", "f", [("A", "Mon chien aurait adoré ce bal."),
                     ("B", "Il aurait mangé le buffet."),
                     ("A", "Justement. Il aurait adoré.")])
D("d136", "f", "m", [("A", "Comment s'appelle cette danse ?"),
                     ("B", "Le fox-trot. On avance, on recule, on marche sur les pieds."),
                     ("A", "Comme en politique.")])
D("d137", "m", "m", [("A", "Le cognac a disparu du salon."),
                     ("B", "Le colonel a été vu avec une carafe sous le bras."),
                     ("A", "Affaire classée.")])
D("d138", "f", "f", [("A", "Vous savez coudre ?"),
                     ("B", "Pourquoi cette question ?"),
                     ("A", "Mon corsage vient de céder. Ne regardez pas.")])
D("d139", "m", "f", [("A", "Mademoiselle, vous avez laissé tomber ceci."),
                     ("B", "Ce n'est pas à moi."),
                     ("A", "Je sais. Mais c'était une excuse pour vous parler.")])
D("d140", "f", "m", [("A", "J'ai l'impression que nous sommes tous observés."),
                     ("B", "Par qui ?"),
                     ("A", "Par quelqu'un qui joue avec nous, comme avec des figurines.", W),
                     ("B", "Vous avez trop bu de ce porto.", W)])
D("d141", "m", "m", [("A", "Vous êtes le notaire du comte, n'est-ce pas ?"),
                     ("B", "Je suis son tailleur. Mais je garde aussi ses secrets.")])
D("d142", "f", "f", [("A", "L'Américaine a offert un éléphant à son mari."),
                     ("B", "Un vrai ?"),
                     ("A", "En porcelaine, mais grandeur nature."),
                     ("B", "Où le met-on ?"),
                     ])
D("d143", "m", "f", [("A", "Vous savez ce que je préfère dans les bals ?"),
                     ("B", "La musique ?"),
                     ("A", "Le moment où l'on rentre se coucher."),
                     ("B", "Ce soir, vous allez attendre longtemps.")])
D("d144", "f", "m", [("A", "Pourquoi êtes-vous déguisé en hibou ?"),
                     ("B", "Je ne suis pas déguisé. C'est mon vrai visage."),
                     ("A", "Mon Dieu. Pardon.")])
D("d145", "m", "m", [("A", "Le bac de demain est annulé, lui aussi."),
                     ("B", "Alors nous serons encore là pour le déjeuner."),
                     ("A", "Et le dîner. Et peut-être pour Pâques.")])
D("d146", "f", "f", [("A", "Vous prenez du sucre dans votre champagne ?"),
                     ("B", "Uniquement quand il est triste."),
                     ("A", "Le champagne, ou vous ?")])
D("d147", "m", "f", [("A", "J'ai cru voir notre hôte sur le toit."),
                     ("B", "Sur le toit, par ce temps ?"),
                     ("A", "Il parlait au paratonnerre."),
                     ("B", "Il a toujours eu des amis étranges.")])
D("d148", "f", "m", [("A", "Ce serveur m'a fait un clin d'œil."),
                     ("B", "C'est un tic. Il en fait à tout le monde."),
                     ("A", "Même à vous ?"),
                     ("B", "Surtout à moi. Je lui dois de l'argent.")])
D("d149", "m", "m", [("A", "Une partie d'échecs, demain matin ?"),
                     ("B", "Si la tour n'est pas emportée par la tempête."),
                     ("A", "Je parlais de la tour de l'échiquier.")])
D("d150", "f", "f", [("A", "Je n'arrive pas à savoir si cette dame est la reine de Saba ou ma couturière."),
                     ("B", "Demandez-lui le prix d'une robe."),
                     ("A", "Si elle répond, c'est ma couturière.")])
D("d151", "m", "f", [("A", "On dit qu'à minuit, le dernier invité arrivé doit chanter."),
                     ("B", "Qui est arrivé le dernier ?"),
                     ("A", "Vous, ma chère."),
                     ("B", "Alors je pars en premier.")])
D("d152", "f", "m", [("A", "Votre moustache est fausse ?"),
                     ("B", "Elle est vraie. C'est moi qui suis faux.")])
D("d153", "m", "m", [("A", "Avez-vous vu le chat noir dans l'escalier ?"),
                     ("B", "Il a traversé devant moi trois fois."),
                     ("A", "Ça fait combien de malheurs ?"),
                     ("B", "Ça dépend s'il revenait ou s'il repartait.")])
D("d154", "f", "f", [("A", "Ce petit jeune homme rougit dès qu'on le regarde."),
                     ("B", "Regardons-le, alors. C'est amusant.")])
D("d155", "m", "f", [("A", "Quelle est votre couleur préférée ?"),
                     ("B", "La couleur des yeux de quelqu'un qui écoute."),
                     ("A", "Je... vous écoute."),
                     ("B", "Gris, donc. Pas mal.")])
D("d156", "f", "m", [("A", "Vous croyez qu'on trouvera un trésor dans la cave ?"),
                     ("B", "On y trouvera surtout du vin. C'est un trésor."),
                     ("A", "Alors allons fouiller.")])
D("d157", "m", "m", [("A", "J'ai entendu la mer gronder sous le plancher."),
                     ("B", "Ce sont les canalisations. Ou mon estomac."),
                     ("A", "Je préfère que ce soit la mer.")])
D("d158", "f", "f", [("A", "Vous croyez qu'il est trop tard pour rentrer à Paris ?"),
                     ("B", "Il est trop tard depuis le bac de cinq heures."),
                     ("A", "Alors autant danser.")])
D("d159", "m", "f", [("A", "Si on vous demande, nous ne nous sommes jamais parlé.", W),
                     ("B", "Parlé de quoi ?", W),
                     ("A", "Parfait. Vous comprenez vite.", W)])
D("d160", "f", "m", [("A", "C'est la dernière valse, paraît-il."),
                     ("B", "Ils disent ça toutes les demi-heures."),
                     ("A", "Alors c'est la dernière de cette demi-heure.")])
