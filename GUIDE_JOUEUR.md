# Le Bal Masqué — Guide du joueur

Manoir Ashcombe, 1932. Des dizaines d'invités masqués déambulent dans le manoir. Parmi eux se cachent les joueurs,
tous déguisés en invités. Chacun chasse les autres : le dernier debout gagne.

## Lancer le jeu

- Ouvrir `GuessWho.exe` (dossier `Build\Windows`).
- Si Windows signale qu'il manque une bibliothèque Visual C++, installer
  `Engine\Extras\Redist\en-us\vc_redist.x64.exe` (même dossier), puis relancer.
- Configuration : Windows 10 ou 11 64 bits, carte graphique DirectX 12 recommandée (le mode DirectX 11 fonctionne,
  avec moins de détails).

## Jouer à plusieurs (2 à 10 joueurs)

**L'hôte** clique sur **Héberger une partie**. L'écran **La soirée** s'ouvre : nombre d'invités non-joueurs (120 par défaut, de 30 à 200), durée de la chasse, temps pour se cacher, nombre de manches (ou sans limite), événements automatiques et leur fréquence, joueurs pour commencer, attente au salon. Vos choix sont gardés pour la prochaine fois ; **Par défaut** les remet à zéro, **Commencer** ouvre le manoir. Au premier lancement, Windows demande d'autoriser le jeu sur le
réseau : accepter pour les réseaux privés.

Une fois dans le manoir, l'hôte voit en bas à droite un **code de 6 caractères**, déjà copié dans son presse-papiers. Il reste affiché 3 minutes ; **Tab** le rappelle.

**Les autres** cliquent sur **Rejoindre une partie** et tapent ce code. C'est tout : pas de compte à créer, pas de port à ouvrir, pas de VPN.

**Sans Internet, ou si le service d'Epic ne répond pas** : l'hôte voit « Pas de code » et la partie s'ouvre par adresse IP. Les autres tapent alors son adresse dans le même champ :

- **Même réseau (maison, LAN)** : l'IP locale de l'hôte, par exemple `192.168.1.20`
  (sur le PC de l'hôte : `ipconfig`, ligne « Adresse IPv4 »).
- **Par Internet** : un réseau privé virtuel entre amis (Tailscale, ZeroTier ou Radmin VPN), ou le **port 7777 en UDP** ouvert sur le routeur de l'hôte.

Quand le code fonctionne, la partie n'accepte que le code : l'adresse IP ne donne rien.

La partie commence dès qu'il y a au moins 2 joueurs.

## Déroulement d'une manche

1. **Cachette (20 s)** : tous les joueurs apparaissent au hasard parmi les PNJ, sans arme, et se dispersent. Personne ne peut encore blesser un joueur.
2. **La chasse (4 min)** : à vous de repérer les autres joueurs et de les éliminer. Un joueur éliminé devient un **fantôme** (il vole librement et regarde la suite).
3. **Fin de manche** : le **dernier joueur en vie** gagne. Si plusieurs survivent aux 4 minutes, ils se partagent la victoire.

**Points** (sur **Tab**) : +1 par rival éliminé de votre main, +3 pour un survivant à la fin. Éliminer un rival rapporte aussi **+100 $**.

**Dégâts entre joueurs** : fusil, lame secrète et mitrailleuse tuent d'un coup ; épée et boule de billard : −25 PV ; piège : −50 PV ; bombe et lustre tuent tout le monde dans la zone, le poseur ou le tireur compris.

**Conseils** : marchez, flânez, arrêtez-vous comme les PNJ. Courir est permis… mais louche. Abattre un PNJ rapporte de l'argent, mais révèle où vous êtes.

**Le piano** (salle de bal, sur la scène) : approchez-vous et appuyez sur **E** : un vacarme de piano résonne dans
tout le manoir, de quoi attirer les autres joueurs ailleurs… ou vers vous. Il faut attendre 12 s entre deux vacarmes.
Les PNJ en jouent aussi de temps en temps : un vacarme ne prouve pas qu'un joueur est là.

**Danser** : appuyez sur **V** pour danser une danse des années 30 tirée au hasard (charleston, lindy hop, valse
lente, shimmy, truckin'). **V** à nouveau, ou un pas, et vous arrêtez. Sur la piste de danse (salle de bal, devant
la scène), une touche « V Danser » s'affiche au-dessus de vous. Les invités (PNJ) viennent régulièrement y danser un
moment, seuls ou en couple face à face, puis repartent un par un : dansez parmi eux pour passer inaperçu. Pendant
qu'ils dansent, le gramophone de la salle de bal joue plus fort.

**Le bar** (salle de billard) : de temps en temps, une petite foule d'invités se rassemble devant le comptoir,
bavarde un moment, puis se disperse. Une panique, un événement ou le robot fait fuir les danseurs comme
les buveurs.

**Parler aux invités** (invités seulement) : face à un PNJ, à deux pas, appuyez sur **E** : il s'arrête, se tourne
vers vous et vous répond (un bonsoir, puis « encore vous ? », puis une remarque). Parfois son voisin s'en mêle.
Chaque personnage a sa propre voix et ne dit jamais deux fois la même phrase. Les PNJ discutent aussi entre eux,
seulement près des joueurs ; un invité traverse parfois la pièce pour aller parler à quelqu'un. Les voix ne
traversent pas les murs.

**Événements** (pendant la chasse, environ une fois par minute quand ils sont activés) : *À l'attaque* (des bandits
tirent au hasard), *Au feu* (ne marchez pas dans les flammes), *Panne de courant* (lampe torche, que vous seul voyez),
*Le Kamikaze* (fuyez la pièce où il court en criant), *Le Robot* (s'il vous voit, un fin rayon rouge s'allume : 1,5 s pour sortir de sa ligne avant le tir ; deux tirs tuent, les murs l'arrêtent. Il se tue : balles, épée, mitrailleuse, piège, explosion). Chaque événement a sa bannière, sa musique et les réactions des PNJ.

## L'argent et la boutique

**Gagner de l'argent.** Chaque gain s'affiche à l'écran en vert (« +50 $ ») ; le montant de votre bourse est toujours affiché en bas à droite. On la garde d'une manche à
l'autre ; un « +25 $ » doré monte à chaque gain, avec un bruit de pièces.
- Jouer d'un instrument (piano, harpe, batterie, contrebasse) : **+25 $**, au plus une fois toutes les 30 s.
- Abattre un PNJ (fusil, bombe, épée, bille…) : **+100 $**. Le PNJ pousse un grand cri qui s'entend dans tout le
  manoir et qu'on localise à l'oreille : tout le monde sait où ça s'est passé.
- Votre piège explose sur un rival : **+50 $**. Éliminer un rival : **+100 $**.
- Fouiller un corps (**maintenez E**, tout le monde peut) : de 10 à 60 $, et parfois un objet.
- Voler un petit objet du décor (gramophone, lampe de table, téléphone, machine à écrire, radio, candélabre, vase, buste,
  globe : **maintenez E**, invités) : de 30 à 120 $. L'objet disparaît jusqu'à la manche suivante.
- Faire tomber un lustre sur quelqu'un (invité) : **+100 $** par victime.
Il n'y a plus de revenu qui tombe tout seul : il faut agir pour gagner.

**Où acheter** (appuyez sur **E** près d'un vendeur ; un « E » flotte au-dessus de lui ; les fantômes ne peuvent rien acheter) :
- **le barman**, derrière le bar de la salle de billard ;
- **les deux serveurs** qui circulent avec leur plateau de coupes entre les invités. Ils ne vous attendent pas :
  si le serveur s'éloigne pendant que vous hésitez, la carte se ferme ;
- **le junkie**, dans les toilettes au bout du couloir ouest : un marché noir, d'autres prix, et lui seul vend des
  pétards.

La carte du vendeur affiche votre bourse et les articles ; ceux que vous ne pouvez pas payer sont grisés. Cliquez
pour acheter ; **E** ou « Fermer » pour refermer.

**L'inventaire : 4 objets.** Les cases sont en bas de l'écran. **1, 2, 3, 4** ou la **molette** choisissent l'objet,
**clic gauche** s'en sert, **Q** pose l'objet choisi par terre à vos pieds : n'importe qui peut le reprendre avec **E**. Un objet neuf arrive directement en main. Rien
d'autre ne se tient en main : avec le fusil ou l'épée rangés, personne ne les voit. Inventaire plein : le vendeur refuse.

| Article | Barman / serveur | Junkie | Effet du clic gauche |
|---|---|---|---|
| Vieux fusil (1 balle par achat) | 150 $ | 180 $ | long, se voit de loin. Sans viser, le tir part à côté ; **clic droit** pour viser, et le viseur bouge tout seul. Un rival touché tombe |
| Bombe fumigène | 40 $ | 30 $ | lancée à 2,5 m devant vous : un épais nuage gris pendant 18 s |
| Gaz rétrécissant | 60 $ | 45 $ | nuage vert à vos pieds : tout petit (x 0,3) et rapide (x 1,7) pendant 20 s ; ça clignote vert à la fin |
| Piège | 80 $ | 60 $ | dans l'encadrement d'une porte : sous le linteau ; ailleurs : par terre devant vous. Boîtier avec une lumière rouge qui clignote, armé après 3 s. Saute au passage de **n'importe quel joueur** (vous aussi !) ou d'un intrus (bandit, kamikaze, robot), jamais d'un simple invité. Un joueur perd 50 PV et il est projeté en l'air : écran rouge, « -50 » au milieu de l'écran, un coup sourd et un cri |
| Bombe | 120 $ | 90 $ | posée à vos pieds ; bip toutes les secondes, de plus en plus vite ; après 45 s, énorme explosion (9 m) qui tue PNJ et joueurs |
| Munitions de tourelle | 80 $ | 100 $ | pas de case : 60 balles pour la tourelle de la mezzanine |
| Pistolet d'échange | 200 $ | 240 $ | visez un invité : vous prenez son corps ; se recharge |
| Pétard (junkie seulement) | — | 30 $ | lancé devant vous ; 4 s plus tard, il crépite comme une fusillade : tout le manoir panique, un leurre parfait |
| Lame secrète | 180 $ | 150 $ | cachée dans la manche, personne ne la voit. Tout près d'un invité (PNJ) ou d'un rival : il s'effondre sans un cri et sans panique (+100 $). Se recharge 8 s après chaque coup, porté ou non : la case de l'objet s'assombrit et compte les secondes |

**La boîte mystère** : un coffre noir et doré, ailleurs à chaque manche. **E** + 100 $ : elle s'ouvre, les objets défilent,
elle s'arrête sur l'un d'eux. Il vous attend sans limite de temps : **E** pour le prendre, quand vous avez une case libre.

**Désamorcer une bombe** (tout le monde). On l'entend biper, de plus en plus vite ; approchez-vous à moins de 1,5 m et
**maintenez E pendant 2 secondes** (« E Maintenir : désamorcer » s'affiche au-dessus d'elle) : un anneau de perles se
remplit autour du viseur. Relâcher E ou s'éloigner annule. À 12 secondes de l'explosion, les invités autour la
fuient en criant. Les pièges se repèrent à leur lumière rouge. La fumée d'une bombe fumigène
cache aussi les invités au regard du robot.

## Objets, armes et curiosités du manoir

**Boules de billard** (salle de billard, sur la table) : près de la table, **E** pour prendre une boule (2 au plus,
invités seulement). **Clic gauche** (les boules sélectionnées) : vous la lancez vers le viseur. Un PNJ
touché meurt (+100 $), un rival perd 25 PV. Les boules reviennent sur la table 45 s plus tard.

**Épées des armures** (hall, les deux armures sous la galerie) : **E** pour voler l'épée (une à la fois). Tenue en main,
tout le monde peut la remarquer ! **Clic gauche** (l'épée sélectionnée, elle se voit alors dans votre main) : un coup d'épée devant vous (2 m). Un PNJ
touché meurt, un rival perd 25 PV. L'armure récupère son épée 60 s plus tard.

**Pistolet d'échange** (boutique, 200 $) : sélectionnez-le, visez un invité (PNJ) à moins de 25 m, clic gauche. Votre corps
actuel s'effondre comme un invité ordinaire, votre fantôme bleu vole jusqu'à la cible (tout le monde le voit !) et vous
prenez son corps. Il se recharge en 90 s ; l'écran vous dit quand il est prêt.

**Le coffre-fort du bureau** : à chaque manche, un post-it jaune avec le code traîne par terre quelque part dans le
manoir (jamais au vestiaire ni sur la scène). **E** dessus pour le lire (autant de fois qu'on veut) : un post-it s'affiche à l'écran, vous seul voyez le code. Ensuite **E** devant le
coffre : la porte s'ouvre et vous gagnez **500 $**. Une seule fois par manche, pour le premier qui l'ouvre (invités).

**Alarmes incendie** (boîtiers rouges aux murs : couloirs, hall, salle à manger) : **E** pour tirer l'alarme. La
cloche sonne 10 s et tous les PNJ courent. Un invité qui la tire **court bien plus vite pendant 12 s** : d'un boîtier à
l'autre, c'est le moyen de traverser le manoir. Chaque boîtier resservira après 20 s, autant de fois qu'on veut.

**Le lustre** : une balle de fusil dans un lustre le décroche. Il tombe, se brise au sol et tue tout le monde en
dessous. Chaque victime rapporte +100 $ à celui qui a tiré. Les lustres reviennent à la manche suivante.

**Le kamikaze** : abattu avant l'heure (balle, mitrailleuse, piège), il n'explose pas et sa bombe reste par terre :
**E** pour la récupérer.

**Toilettes** (au bout ouest du couloir) : **E** dans une cabine… très fort : tout le manoir l'entend, et on peut
deviner d'où ça vient. Une fois toutes les 5 s.

## La vue

On joue **à la troisième personne**. **C** bascule entre troisième et première personne. **À la troisième personne, la souris ne bouge que la caméra** : le corps se tourne vers là où l'on marche, exactement comme les PNJ. W A S D partent de la direction de la caméra au moment où l'on appuie ; tant que les mêmes touches restent enfoncées, regarder ailleurs n'infléchit la marche que doucement (120° par seconde). Pour changer franchement de direction, relâchez et appuyez de nouveau. À la première personne, le corps suit la visée.

**L'écran** : en bas à gauche votre état, le nombre de joueurs encore en vie, votre **vie** (grand chiffre et barre) ; en bas à droite le moment de la manche, le temps et votre **argent** ; entre les deux les 4 cases d'objets. Rien en haut de l'écran. La ligne d'aide des touches s'efface 20 s après le début de la chasse (Tab la rappelle).
- **Clic droit maintenu** (une arme à feu sélectionnée) : viser, à la première personne. Le champ de vision se resserre, la
  souris ralentit, l'arme monte au centre de l'écran, et le corps se tourne vers la visée (aussi louche que de tirer).
- Chaque tir donne un petit recul et une secousse ; à la première personne la vue balance un peu en marchant, davantage en
  courant. Le champ de vision de base est celui des Options.
- Pendant une danse (**V**), la caméra passe derrière le personnage.

## La mitrailleuse de la galerie

Une mitrailleuse des années 30 est montée sur la galerie du hall (en haut des escaliers), face à l'entrée : elle
couvre presque tout le hall, sauf le pied de la galerie, trop proche en contrebas.
- **E** à côté (un « E » flotte au-dessus) : la prendre (votre arme se range) ; **E** à nouveau : la lâcher. Un seul tireur.
- **Clic gauche maintenu** : tir automatique (9 balles par seconde). La souris oriente le canon, à 30° au plus de chaque
  côté ; seule cette arme tue le robot ; un viseur, les munitions ou la recharge s'affichent sous le centre de l'écran.
- Il faut des munitions de tourelle (60 balles, achetées au bar). Abattre un PNJ ou un rival rapporte de l'argent (+100 $). Personne ne sait qui tire.
- Chaque rafale s'entend dans tout le manoir et fait paniquer tous les invités pendant 10 s.

## Disjoncteurs, zombies, conversations

- **Disjoncteurs** : une boîte grise dans le couloir de service. **E** coupe le courant de tout le manoir, une fois par partie.
- **Zombies** : un invité se transforme, marche lentement et contamine au toucher. Touché, tu deviens zombie jusqu'à la fin de l'événement. N'importe quel joueur peut tirer sur un zombie.
- **Parler (E sur un invité)** : ton personnage parle avec sa propre voix, comme tous les invités. Voir deux personnes se saluer ne prouve donc rien.
- **Danser (V) dans la salle de bal** : les invités libres tout près viennent danser avec toi.

## Commandes

| Touche | Action |
|---|---|
| W A S D | se déplacer |
| E (près d'une chaise, d'un banc, d'un canapé libre) | s'asseoir ; E de nouveau ou bouger : se lever |
| Souris | regarder |
| Maj | courir |
| Espace | sauter (tout joueur) ; en courant, un invité fait un bond qui le lance en avant (toutes les 3 s) |
| 1 2 3 4 / molette | choisir un objet de l'inventaire |
| Clic gauche | se servir de l'objet choisi (tirer, lancer, poser, frapper…) ; la mitrailleuse, maintenu |
| Clic droit (maintenu) | viser avec une arme à feu, à la première personne : zoom, souris plus lente |
| Q | jeter l'objet choisi |
| C | première / troisième personne |
| E | jouer du piano ; acheter (barman, serveur, junkie) ; boîte mystère ; ramasser une boule, voler une épée, lire le post-it, ouvrir le coffre, tirer l'alarme, les toilettes, prendre / lâcher la mitrailleuse, récupérer la bombe du kamikaze ; **maintenu** : fouiller un corps, voler un objet du décor, désamorcer une bombe ; parler à l'invité en face de vous |
| V | danser / arrêter de danser (bouger arrête aussi) |
| Tab | tableau des scores |
| Échap | menu pause (Reprendre, Options, Comment jouer, Quitter) |

**Changer les touches.** Options > Changer les touches : cliquez sur une touche, puis appuyez sur la nouvelle (Échap annule). Si la touche sert déjà à une autre action, les deux s'échangent. « Par défaut » remet tout comme au départ. Les touches de déplacement (W A S D, flèches), la souris et Échap ne se changent pas.

Le menu **Options** règle les volumes (général, musique, effets, interface), la sensibilité de la souris, le champ
de vision, la qualité graphique (Faible à Épique), le mode d'affichage et la résolution. Tout est enregistré.

## Sécurité : à lire

Cette version est un build « Development ». Pour que le jeu fonctionne sans code C++, les actions des joueurs
passent par la console du serveur. Les commandes de triche sont bloquées, mais **un joueur connecté peut encore
forcer l'hôte à changer de carte** (ce qui coupe la partie pour tous). Il ne peut pas lire ni modifier vos fichiers.
**Jouez seulement avec des amis de confiance**, de préférence via un réseau privé (Tailscale, ZeroTier) plutôt
qu'en ouvrant un port sur Internet.

## Pour le développeur : ouvrir le projet dans Unreal

- **Menu développeur : F2 en partie.** Un menu compact à gauche, en pages, piloté au clavier pendant qu'on continue de
  jouer : Haut / Bas (ou pavé 8 / 2) pour choisir une ligne, Gauche / Droite (4 / 6) pour changer sa valeur, Entrée (5)
  pour valider ou ouvrir une page, Retour (0) pour revenir, Échap ou F2 pour fermer.
  - Joueur : personnage, devenir fantôme, réapparaître, rôle (invité / sans rôle), se téléporter dans une
    pièce, vitesse, se soigner, score, danser (V), aller à la mitrailleuse, 60 munitions de mitrailleuse.
  - Partie : mode solo (une manche à 1 joueur), fin de manche automatique (Non = la manche ne se termine pas toute
    seule), lancer une manche, passer à la chasse, terminer la manche (victoire / personne / annulée), éliminer un autre joueur, retour à la
    salle d'attente, chrono (+60 s, -30 s, finir la phase), vitesse du jeu, annonce de test.
  - PNJ : en ajouter, en retirer, les figer, abattre le plus proche, habiller tous les PNJ en un même personnage,
    les faire danser maintenant (piste de la salle de bal), réunir une foule au bar maintenant.
  - Affichage : vue à la 1re ou à la 3e personne (pour soi), FPS, temps de calcul, qualité graphique, masquer
    l'interface, tableau des scores, menu pause.
  - Son : jouer un son, jouer tous les sons à la suite (Gauche / Droite pour sauter), arrêter.
  - Boutique : argent (+100 $, +1000 $, remettre à 0), donner un objet (ou tout), ouvrir la boutique ou le marché
    noir sur place, aller au bar, aux toilettes (junkie) ou voir un serveur, serveurs figés / qui vous suivent /
    normaux, faire repartir un serveur (la carte se ferme), aller à la bombe la plus proche, faire exploser les
    bombes posées, se placer face au PNJ le plus proche (pour essayer le fusil).
  - Pour tester seul : Partie → Mode solo : Oui, Fin de manche automatique : Non, puis Lancer une manche.
  L'hôte peut toujours s'en servir ; un client seulement si l'hôte a lancé le jeu avec `-GWDev` (ajouter `-GWDev`
  après `GuessWho.exe` dans un raccourci), pour qu'en vraie partie personne ne s'en serve. Ajouter une ligne : la
  table `PAGES` dans `Tools\ui\u15_dev_menu.py`.
- **Personnages :** tous les invités et PNJ sont des personnages générés d'un seul tenant (la liste est dans
  `AssetGen\manifest.json`, `"outfits": "roster"`, et `Tools\gameplay\s29_gen_chars.py` la branche ; relancer ensuite
  `s28_motion_qa.py` pour le banc d'essai). Plus de costumes assemblés au hasard.
- Raccourci : `Open GuessWho (UE 5.8).lnk` dans `J:\Projets\Unreal_Projects\Guess Who`.
- Tout le contenu a été construit par scripts, rejouables : `Tools\` (niveau : `Tools\level\update_level.sh`,
  éclairage : `Tools\lighting\`, gameplay : `Tools\gameplay\`, interface et audio : `Tools\ui\`, génération ComfyUI :
  `AssetGen\`). Les journaux de chaque partie sont dans `Tools\agent_logs\`.
- Refaire l'exécutable : `powershell -File Tools\package.ps1` (résultat dans `Build\Windows`).
- Contrôles automatiques, dans `Tools\qa\` :
  - `pkg_menutest.ps1` : clique Héberger puis Rejoindre dans l'exécutable final.
  - `pkg_nettest.ps1` : parties hôte + client.
  - `shot_motion.ps1` + `motion_sheets.py` : chaque tenue filmée en marche puis en sprint, de profil et de face
    (`-Packaged` filme l'exécutable final).
  - `hair_fit.py`, `garment_fit.py` : mesurent si le mannequin traverse coiffures et vêtements.
  - `garment_wrap.py` : ajuste les corsages et les manteaux au corps. À relancer après tout réimport d'un vêtement.
- Menu développeur : `Tools\ui\u15_dev_menu.py` (test automatique : lancer avec `-GWDevTest`, et `-GWDevShot` pour des captures).
- Personnages générés d'un seul tenant (prototype : l'habit remplace Monsieur 1, la robe verte Dame 1), dans `Tools\chars\` :
  - `rig_character.py <nom>` : importe le modèle 3D et l'attache au squelette du mannequin pour les animations.
  - `deform_dump.py` + `deform_qa.py` : mesurent, sans carte graphique, l'étirement en marche et en course et
    l'enfoncement de l'ourlet dans le sol.
  - `Tools\gameplay\s29_gen_chars.py` : branche les personnages riggés sur leurs tenues (`clear` pour revenir à l'ancien système).
- Les scripts pilotent l'éditeur par l'exécution Python à distance (boucle locale seulement). Ce réglage de
  développement est rangé dans `Tools\dev_config\UserEngine.ini` pour qu'il ne parte jamais dans le jeu : le recopier
  dans `GuessWho\Config\` pour réutiliser les scripts, et le retirer avant de refaire l'exécutable.
