"""Dialogues d051-d100."""
from _lib import dialogue

ITEMS = []
D = lambda did, ga, gb, turns, voices=None: dialogue(ITEMS, did, ga, gb, turns, voices)  # noqa: E731
W = "whisper"

D("d051", "f", "m", [("A", "Vous savez qui a invité le monsieur au masque de corbeau ?"),
                     ("B", "Personne. Il est arrivé avec la tempête."),
                     ("A", "Vous plaisantez ?"),
                     ("B", "À moitié seulement.")])
D("d052", "m", "f", [("A", "Ce collier est un cadeau de votre mari ?"),
                     ("B", "D'un mari. Je ne sais plus lequel.")])
D("d053", "m", "m", [("A", "J'ai misé sur le cheval de la marquise, à Longchamp."),
                     ("B", "Et alors ?"),
                     ("A", "Il court encore, je crois.")])
D("d054", "f", "f", [("A", "Regardez, la duchesse a mis sa tiare."),
                     ("B", "Pour un bal masqué ? Elle veut qu'on la reconnaisse de Paris."),
                     ("A", "Avec ce poids sur la tête, elle ne pourra pas danser."),
                     ("B", "Elle n'a pas dansé depuis l'Exposition universelle.")])
D("d055", "m", "f", [("A", "Le chef a fait un gâteau en forme de manoir."),
                     ("B", "Avec la tempête en sucre filé ?"),
                     ("A", "Et le majordome en pâte d'amande.")])
D("d056", "f", "m", [("A", "Vous êtes poète, n'est-ce pas ? Dites-moi quelque chose de beau."),
                     ("B", "Le buffet ferme dans dix minutes."),
                     ("A", "C'est en effet bouleversant.")], voices={"B": "m9_poete"})
D("d057", "m", "m", [("A", "Les journaux disent que l'île est hantée."),
                     ("B", "Les journaux disent aussi que je suis riche."),
                     ("A", "Alors l'île est sûrement hantée.")])
D("d058", "f", "f", [("A", "Pourquoi le petit salon est-il fermé ?"),
                     ("B", "Notre hôtesse y range ses secrets."),
                     ("A", "Il doit être très encombré.")])
D("d059", "m", "f", [("A", "Vous tremblez, mademoiselle ?"),
                     ("B", "C'est le tonnerre. Et votre eau de Cologne."),
                     ("A", "Je vais changer de flacon."),
                     ("B", "Changez plutôt de tempête.")])
D("d060", "f", "m", [("A", "Mon mari est parti chercher des cigares il y a une heure."),
                     ("B", "Le fumoir est au bout du couloir."),
                     ("A", "Je sais. Le bar aussi.")])
D("d061", "m", "m", [("A", "Avez-vous lu le dernier roman de l'Anglaise ?"),
                     ("B", "Celui où le majordome est coupable ?"),
                     ("A", "Dans tous ses romans, le majordome est coupable."),
                     ("B", "Alors je garde un œil sur le nôtre.")])
D("d062", "f", "f", [("A", "J'ai prêté mon rouge à lèvres à une inconnue."),
                     ("B", "Imprudente !"),
                     ("A", "Maintenant, elle a la même bouche que moi. C'est troublant.")])
D("d063", "m", "f", [("A", "Ce sont les vraies perles de votre grand-mère ?"),
                     ("B", "Ma grand-mère n'a jamais rien eu de vrai. Même pas les dents.")])
D("d064", "f", "m", [("A", "Vous croyez que notre hôte va faire un discours ?"),
                     ("B", "Il en fait un chaque année, à minuit pile."),
                     ("A", "Les pendules sont arrêtées."),
                     ("B", "Alors nous sommes sauvés.")])
D("d065", "m", "m", [("A", "L'orchestre vient de Paris ?"),
                     ("B", "De Paris, oui. Le contrebassiste vient de Pontoise."),
                     ("A", "Ça s'entend.")])
D("d066", "f", "f", [("A", "Elle a quel âge, à votre avis ?"),
                     ("B", "Celui de son masque. Il est très ancien."),
                     ("A", "Vous êtes méchante."),
                     ("B", "Je suis lucide, ce n'est pas pareil.")])
D("d067", "m", "f", [("A", "Si la tempête se calme, on fera une promenade sur la jetée ?"),
                     ("B", "Si la tempête se calme, je rentre chez moi à la nage.")])
D("d068", "f", "m", [("A", "Vous avez une tache de sauce sur votre plastron."),
                     ("B", "C'est voulu. C'est ma décoration."),
                     ("A", "Vous êtes décoré de la Légion du rôti.")])
D("d069", "m", "m", [("A", "Ils ont servi la bisque dans des coquillages."),
                     ("B", "J'ai mangé le coquillage."),
                     ("A", "Vous avez bien fait. C'était le meilleur.")])
D("d070", "f", "f", [("A", "J'ai vu notre hôtesse pleurer dans l'escalier."),
                     ("B", "De joie ?"),
                     ("A", "Je ne crois pas. Elle tenait une lettre."),
                     ("B", "Une lettre, un soir de bal... Ça finit toujours mal.", W)])
D("d071", "m", "f", [("A", "Accepteriez-vous cette danse ?"),
                     ("B", "Avec plaisir. Mais je mène."),
                     ("A", "Je n'en attendais pas moins.")])
D("d072", "f", "m", [("A", "Vous jouez du piano ?"),
                     ("B", "Uniquement quand tout le monde est parti."),
                     ("A", "Par modestie ?"),
                     ("B", "Par charité.")])
D("d073", "m", "m", [("A", "On m'a volé mon tabac."),
                     ("B", "Quelqu'un fume votre pipe en ce moment même."),
                     ("A", "Où ça ?"),
                     ("B", "Dans le jardin d'hiver. Il a l'air ravi.")])
D("d074", "f", "f", [("A", "Ce bal est d'un ennui..."),
                     ("B", "Attendez la panne de courant. Il y en a toujours une."),
                     ("A", "Vous l'organisez ?")])
D("d075", "m", "f", [("A", "Mon horoscope m'avait annoncé une rencontre."),
                     ("B", "Et elle a eu lieu ?"),
                     ("A", "Je l'ai rencontrée. C'est la porte vitrée.")])
D("d076", "f", "m", [("A", "Pourquoi portez-vous deux masques ?"),
                     ("B", "Le premier est pour les invités. Le second pour ma belle-mère.")])
D("d077", "m", "m", [("A", "Le baron a encore raconté l'histoire du sanglier."),
                     ("B", "Le sanglier grossit à chaque fois."),
                     ("A", "Ce soir, il pesait une tonne.")])
D("d078", "f", "f", [("A", "Vous trouvez qu'on reconnaît les gens à leur démarche ?"),
                     ("B", "Le colonel, oui. Il marche comme un char d'assaut."),
                     ("A", "Et moi ?"),
                     ("B", "Vous, comme une gazelle. Pressée.")])
D("d079", "m", "f", [("A", "Vous sentez cette odeur de brûlé ?"),
                     ("B", "C'est le chef. Il flambe tout ce qu'il touche."),
                     ("A", "J'espère qu'il ne touchera pas les rideaux.")])
D("d080", "f", "m", [("A", "Vous êtes venu par le bac de six heures ?"),
                     ("B", "Par celui de cinq. On a failli chavirer."),
                     ("A", "Alors vous avez vu le passager qui n'est jamais descendu ?"),
                     ("B", "Ne commencez pas. J'ai déjà du mal à dormir.")])
D("d081", "m", "m", [("A", "Vous croyez que les serveurs sont de vrais serveurs ?"),
                     ("B", "Celui-là porte des chaussures à deux cents francs."),
                     ("A", "Un serveur très bien payé, ou un faux serveur.")])
D("d082", "f", "f", [("A", "Le jeune homme au violon me fait les yeux doux."),
                     ("B", "Il fait les yeux doux à la partition."),
                     ("A", "Vous croyez ?"),
                     ("B", "Il louche, ma chère.")])
D("d083", "m", "f", [("A", "J'ai entendu dire que vous écriviez vos mémoires."),
                     ("B", "Je les écris ce soir. Vous serez dedans."),
                     ("A", "En bien, j'espère ?"),
                     ("B", "En note de bas de page.")])
D("d084", "f", "m", [("A", "Je n'ai jamais vu une mer aussi grise."),
                     ("B", "Elle a pris la couleur des invités."),
                     ("A", "Vous êtes d'une humeur charmante.")])
D("d085", "m", "m", [("A", "Ce sont des truffes, dans les œufs brouillés ?"),
                     ("B", "Ce sont des truffes partout, mon cher. Même dans le pain."),
                     ("A", "Notre hôte n'est donc pas ruiné.")])
D("d086", "f", "f", [("A", "Elle a dansé trois fois avec le même cavalier."),
                     ("B", "Trois fois ? C'est presque des fiançailles."),
                     ("A", "Quatre, et c'est un mariage.")])
D("d087", "m", "f", [("A", "Vous avez peur des orages ?"),
                     ("B", "Non. J'ai peur des gens qui en parlent toute la soirée.")])
D("d088", "f", "m", [("A", "Le petit escalier derrière la cuisine, il mène où ?"),
                     ("B", "Au grenier. Ou à la cave. Ça dépend du jour."),
                     ("A", "Ça ne veut rien dire."),
                     ("B", "Je sais. Mais c'est ce qu'a dit le cuisinier.")])
D("d089", "m", "m", [("A", "J'ai serré la main du ministre."),
                     ("B", "Il est ici ?"),
                     ("A", "Je crois que oui. Ou c'était son sosie."),
                     ("B", "Avec un masque, ça revient au même.")])
D("d090", "f", "f", [("A", "Je vais me remaquiller. Gardez-moi ma coupe."),
                     ("B", "Je ne promets rien.")])
D("d091", "m", "f", [("A", "Je suis navré, je ne me souviens plus de votre nom."),
                     ("B", "Parfait. Ce soir, je n'en ai pas.")])
D("d092", "f", "m", [("A", "Vous êtes bien pâle, monsieur."),
                     ("B", "J'ai croisé quelqu'un que je croyais mort."),
                     ("A", "Qui donc ?"),
                     ("B", "Mon créancier.")])
D("d093", "m", "m", [("A", "Ces bougies sont neuves, et déjà à moitié consumées."),
                     ("B", "Le temps passe vite quand on s'ennuie."),
                     ("A", "D'habitude, c'est le contraire.")])
D("d094", "f", "f", [("A", "Qu'est-ce qu'elle a, la petite mariée ?"),
                     ("B", "Son mari danse avec l'actrice."),
                     ("A", "Déjà ? Ils sont mariés depuis samedi.")])
D("d095", "m", "f", [("A", "Si nous sommes encore là demain, je propose une partie de croquet."),
                     ("B", "Sous la pluie ?"),
                     ("A", "C'est plus sportif.")])
D("d096", "f", "m", [("A", "Le monsieur à la cape rouge a disparu dans le mur."),
                     ("B", "Il y a une porte dérobée derrière la tapisserie."),
                     ("A", "Comment le savez-vous ?"),
                     ("B", "Je l'utilise depuis le début de la soirée.")])
D("d097", "m", "m", [("A", "On dit que la tempête emportera le ponton."),
                     ("B", "Tant mieux. Ma belle-mère arrive demain."),
                     ("A", "Vous êtes un monstre."),
                     ("B", "Un monstre reposé.")])
D("d098", "f", "f", [("A", "Ce rouge vous va à ravir."),
                     ("B", "C'était du blanc avant le dîner."),
                     ("A", "Le vin de Bourgogne ?"),
                     ("B", "Le voisin de Bourgogne.")])
D("d099", "m", "f", [("A", "Vous connaissez la règle du bal ? On ne se démasque qu'à l'aube."),
                     ("B", "Et si l'aube ne vient pas ?"),
                     ("A", "Alors on reste mystérieux pour toujours.")])
D("d100", "f", "m", [("A", "J'ai trouvé une clé dans le pot de fleurs."),
                     ("B", "Remettez-la vite où vous l'avez prise."),
                     ("A", "Pourquoi ?"),
                     ("B", "Parce que c'est la mienne.", W)])
