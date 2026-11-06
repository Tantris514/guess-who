# Le Bal Masqué — suivi des demandes

Toutes les demandes faites pendant le développement, avec leur état. Tenu à jour par Claude à chaque étape ; ajoute
tes idées n'importe où (section « À faire » ou « Idées »), elles seront reprises.

États : ✅ fait et testé · 🔄 en cours · ⏳ à faire · 💡 idée / à décider

## Règles permanentes (s'appliquent à tout, sans qu'il faille le redemander)

- Chaque événement, mode ou action notable s'accompagne automatiquement de : répliques de PNJ (variées, naturelles,
  un peu d'humour), bruitages, musique ou ambiance sonore adaptée, et réaction des PNJ (cris, fuite, commentaires).
- Les répliques ne doivent jamais tourner en boucle sur 3 phrases : beaucoup de variantes, plusieurs voix
  (hommes, femmes, âges), certaines chuchotées.
- Les joueurs doivent entendre les répliques importantes : ce sont les PNJ proches de chaque joueur qui parlent.
- Les événements durent environ 30 s par défaut (réglable).
- Une build est refaite en arrière-plan à chaque étape stable (`Build\Windows`, heure dans `BUILD_INFO.txt`).
- Tout est testable depuis le menu développeur (F2) ; chaque nouvelle fonction y gagne une ligne.
- Les images de personnages choisies sont copiées dans `Personnages (images)\` (script `Tools\chars\collect_images.py`).
- Personnages : 100 % générés (ComfyUI), plus de costumes assemblés au hasard.

## Fait

- ✅ Jeu de base « Le Bal Masqué » (manoir 1930, invités / détectives, réseau, menus, son, éclairage) — 2026-11-01/02
- ✅ Correction du bouton Héberger (ne marchait pas dans la première build)
- ✅ Coiffures et vêtements recalés (ancien système, désormais remplacé)
- ✅ Personnages générés d'un seul tenant, riggés sur le squelette du mannequin (marche, course, ragdoll)
  - ✅ Sandra (robe verte), Victor (habit, nom provisoire), le détective (trench), le Comte, Odette
  - ✅ Monsieur Minuit (session Character Creator) : super-héros discret en tenue de gala (smoking croisé bleu nuit,
    gilet cramoisi, croissant de lune doré, loup bleu nuit, gants de cuir) — riggé, dans la galerie (n° 5)
  - ✅ Barnabé, le majordome (lot de 15, 2026-11-03) : vieux majordome à moustache, gilet noir, pantalon rayé,
    gants blancs — riggé, dans la distribution depuis 07:38 (build de 07:10)
  - ✅ Plus de costumes aléatoires : tous les invités et PNJ sont tirés de cette galerie
- ✅ Menu développeur F2 (style trainer GTA, pages, clavier) : Joueur / Partie / PNJ / Affichage / Son
  - ✅ Personnage, fantôme, réapparaître, rôle, téléportation, vitesse, soins, score
  - ✅ Mode solo, fin automatique oui/non, lancer / terminer une manche, chasse, salle d'attente, chrono, vitesse du jeu
  - ✅ PNJ : ajouter, retirer, figer, abattre le plus proche, habiller tous pareil
  - ✅ Affichage : FPS, stat unit, qualité, masquer l'interface, scores, menu pause
  - ✅ Son : jouer un son, jouer tous les sons, arrêter
- ✅ Fantôme : même personnage, bleu translucide, vue à la troisième personne, ne peut pas sortir du manoir
  (visible seulement par son propriétaire, pour qu'un mort ne puisse pas montrer les cachettes aux détectives)
- ✅ Manche de test (menu dev → Partie) : on choisit son rôle (invité / détective), manche normale mais illimitée,
  aucune condition de fin ; « Terminer la manche de test » pour en sortir. HUD : « MANCHE DE TEST ».
- ✅ Déplacements des PNJ plus variés : petits pas dans la pièce, changements de pièce (parfois avec détour),
  discussions (un PNJ en rejoint un autre et se tourne vers lui), pauses de durées très variables, petits pas pour se
  retourner ; même vitesse de marche que les joueurs pour qu'on puisse toujours se fondre dans la foule.
- ✅ Système de réactions : banque de sons partagée, répliques jouées en 3D sur les PNJ (voix d'homme ou de femme selon
  le personnage), choix des PNJ proches de chaque joueur pour que tout le monde entende, pas de répétition immédiate.
- ✅ Panique (innocent abattu) : cris près du corps, phrases d'alarme près des joueurs, tous les PNJ courent 15 s en
  s'éloignant, puis répliques de retour au calme. Les voix arrivent de l'agent audio (sinon silencieux).
- ✅ Bavardages : toutes les 3,5 à 8 s, un PNJ près d'un joueur dit une petite phrase, parfois un voisin répond.
  Phrases en génération (40+).
- ✅ Système d'événements (menu dev → Événements : déclencher, arrêter, automatique oui/non, fréquence, durée) avec
  bannière en grand, son d'alerte et réactions des PNJ :
  - ✅ À l'attaque : 3-4 bandits entrent, courent et tirent au hasard (mal visé) ~12 s ; 50 dégâts par balle aux
    joueurs, un PNJ touché meurt. (Bandit riggé et branché le 2026-11-03 à 04:59 ; 2e tenue « bandit2 » en génération.)
  - ✅ Au feu : des feux dans plusieurs pièces ~25 s ; qui marche dedans brûle (joueurs : perte de PV ; PNJ : mort).
  - ✅ Panne de courant : toutes les lumières s'éteignent ~45 s, chaque joueur a sa lampe torche (visible de lui seul
    pour ne pas se trahir), puis la lumière revient.
  - ✅ Kamikaze : court de pièce en pièce en criant « Alarme ! », explose 15-25 s plus tard dans la pièce où il est
    (6,5 m, tue tout le monde). (Modèle en génération.)
  - ✅ Le Robot : grand, lent, pas bruyants, yeux rouges ; repère les joueurs devant lui en ligne de vue, dit
    « Cible détectée » et tire au laser 1,1 s plus tard s'il les voit encore ; reste jusqu'à la fin de la manche.
    (Modèle en génération.)
- ✅ Piano : près du piano de la salle de bal, **E** → vacarme entendu dans tout le manoir (12 s entre deux), message
  « E : jouer du piano » quand on est assez près ; des PNJ vont aussi en jouer de temps en temps (un vacarme ne prouve
  pas qu'un joueur est là) ; réactions des invités. Menu dev → Son : « Piano : vacarme maintenant », « Piano : un PNJ
  va en jouer ». (`Tools\gameplay\s33_piano.py`)
- ✅ Bruitages générés branchés : piano, explosions, feu (crépitement en boucle + souffle à l'allumage), laser, servo
  et pas du robot, coupure de courant, alarme d'événement.
- ✅ Musique d'événement : chaque événement a sa musique (attaque, feu, panne, robot ; le kamikaze reprend celle de
  l'attaque), puis la musique de la chasse revient sans rejouer le jingle de départ.
- ✅ Menu dev → Événements → « Aller voir l'événement » : téléporte près du feu / des bandits / du kamikaze / du robot.
- ✅ Personnages des événements : dès que les modèles du bandit (2 tenues), du kamikaze et du robot sont riggés avec
  `"outfits": "bandit" | "bandit2" | "kamikaze" | "robot"`, `s29_gen_chars.py` les branche (mannequin en attendant).
- ✅ Rigging : `rig_character.py --reimport` gardait les anciennes textures ; corrigé (l'ancien import est retiré).
- ✅ Carte plus meublée : 165 → 277 → 309 objets (nouveaux props validés placés : bancs, malles, porte-manteaux, vitrines, paravents, coffre-fort ; banquettes sous les fenêtres ; les dix petits soldats de porcelaine sur la table du hall) (salons, chaises, bustes, palmiers, vases, lampes 17 → 31), passages et
  piste de danse dégagés ; 67 emplacements réservés aux 20 nouveaux props (ils apparaissent dès qu'ils sont validés :
  relancer `bash Tools/level/update_level.sh`). Toutes les vérifications à 0, 13/13 pièces accessibles.
- ✅ Écran « Le bal se prépare… » : barre de progression + pourcentage (ne recule jamais, 100 % au fondu).
- ✅ Événement « Au feu » : les flammes étaient invisibles (matériau de braises de cheminée) → vraies flammes
  animées (`M_GW_Flame`).
- ✅ Test rendu automatique des événements (`Tools\qa\devmenu_render.ps1`) : piano, PNJ pianistes, musique de chaque
  événement, vue rapprochée de chaque événement ; 0 erreur.
- ✅ Builds automatiques : `Tools\build_when_idle.ps1` attend que le jeu soit fermé, puis empaquette.
- ✅ Builds en arrière-plan (config de dev retirée et remise automatiquement)
- ✅ Dossier des images de personnages : `Personnages (images)\` (+ gabarits de pose) ; doublon du Colonel retiré
  (l'ancien dossier est rangé dans `AssetGen\chars\char_colonel\superseded_images\`, le script ne recrée plus de doublon)
- ✅ Dossier des images de props : `Props (images)\` — pour chaque objet 3D, l'image d'origine du modèle + un rendu
  du modèle actuel, et `LISEZMOI.md` (description, taille réelle, pièces) pour les redonner un jour à une meilleure IA 3D
- ✅ Navmesh : la reconstruction du niveau gardait le mode « Dynamic » (saccade de 0,9 s au chargement) → corrigé

### Virage du 2026-11-06 : dernier debout (plus de détectives)
- ✅ Tous les joueurs sont invités ; le dernier en vie gagne ; 20 s de dispersion sans dégâts entre joueurs ; au temps écoulé, les survivants se partagent la victoire ; personne en vie = « Personne n'a survécu »
- ✅ Dégâts entre joueurs : fusil, lame et mitrailleuse tuent ; épée et boule −25 PV ; piège −50 PV ; bombe et lustre tuent ; +100 $ et +1 point par rival éliminé (+50 $ par piège qui le touche), +3 points au survivant
- ✅ Bombe désamorçable par tous ; plus de pénalité pour un PNJ abattu ; le révolver du détective sort du jeu
- ✅ Le modèle du détective devient un invité tiré au sort (PNJ, joueurs, Mascarade)
- ✅ Interface : HUD, carte de début, journal de fin, scores, Comment jouer, écran La soirée, menu de dev (+ Éliminer un autre joueur), boutique, guide
- 🔲 À décider : voix enregistrées qui parlent encore des détectives (1 réplique du junkie, 1 du serveur, 1 de Clara, génération de voix arrêtée) ; illustration de Comment jouer qui montre un détective ; zone qui rétrécit ; butin d'un joueur mort
- Code : `Tools\gameplay\s46_last_standing.py` ; `IsSeeker` et `GWRole 2` restent dans les anciens scripts mais ne sont plus jamais posés

## En cours

- ✅ Build final du 2026-11-03 10:00 dans `Build\Windows` : 2421 paquets, 0 erreur de cuisson, test de démarrage
  réussi (serveur + client propres, 2 manches, voix entendues). Banque de 901 sons, 72 dialogues, 15 voix de
  personnages. Pas encore dedans : le robot et les yeux corrigés du kamikaze (rig + s29 au prochain tour).
  Builds ratés de 02:32 et 04:41 gardés dans `Build\Windows_failed_*` (1,4 Go chacun, à supprimer si inutiles).

- ✅ 2026-11-03 07:38 : 8 invités en jeu (l'Aviatrice et Barnabé le majordome ajoutés) ; événements : le Bandit, le
  Bandit au foulard (2e tenue) et le Kamikaze riggés et branchés. Voix de l'Aviatrice et de Barnabé en création.
- ✅ 2026-11-05 11:07 : personnel en jeu (rendu vérifié en éditeur -game, pas encore dans un build) : Barman, Junkie, Serveur (plateau), 2e serveur « Le Vieux Serveur » (`BP_GW_Waiter2`, SpawnVendors en fait apparaître un de chaque) ; Madame Irène ajoutée seule à la distribution (10 invités, `Tools/chars/add_to_roster.py`), masque aux bords un peu dentelés, sans voix. Robot et Monsieur Minuit vérifiés en jeu. Reste : un s29 complet ajoutera les 13 autres invités riggés en attente ; voix d'Irène et du Vieux Serveur à faire.
  Session « Character Creator » : lots terminés (2026-11-06), 115 personnages générés et riggés sans vérification
  visuelle, à la demande de l'utilisateur (il reviendra s'il voit un problème). Lots : `chars/cast3.json` (15) et
  `chars/cast4.json` (100, recette `chars/make_cast4.py`). Relancer : `creator_batch.py auto --cast=cast4` puis
  `rig_all.py` (dans `AssetGen`, reprennent où ils en sont).
- ✅ 2026-11-06 09:26 : tous dans le jeu (build OK, pas lancé ni testé en partie) : 123 invités + le détective à l'index 32
  (`NumOutfits` 124). Les 101 invités sans voix partagent les 22 voix d'invités existantes, même genre, aucune voix
  générée (`Tools/chars/assign_shared_voices.py`, champ « voice » du manifeste, repris par s29 dans `GenIds`). Reste :
  vérifier en partie le temps de chargement et la mémoire, tous les personnages étant chargés par le Blueprint.
- ✅ 2026-11-06 : invités tous différents tant qu'ils sont 124 ou moins, corps inclus (`NextOutfit` de `s44_npc_life.py`, qui
  cherche une apparence que personne ne porte ; `s45_mascarade.py` libère les apparences avant de redistribuer). Vérifié :
  121 invités, 121 apparences, avant et après Mascarade (`py_harness.ps1 -Plan unique`). Le menu dev peut encore créer des doublons.
- ✅ Directeur des voix (moteur, `s39_voice_director.py` + `voice_bank.py`) : compilé (2026-11-03 05:59) ; test sans
  écran partie B (mort par balle, panne, bandits) propre : 0 avertissement, 0 répétition, 0 cri hors sujet, chaque
  réplique dans la voix de son personnage (`Tools\qa\voice_test.ps1` + `voice_log_check.py`). 06:59 : la banque ne
  contient plus que de vraies voix (573 sons, 11 voix de personnages, 59 dialogues complets, salutations, cris selon
  la cause, calme, barman, kamikaze, robot, bandits) ; les invités qui traversent la pièce pour parler arrivent
  vraiment (seuil d'arrivée corrigé). 07:09–07:18 : parties A (conversations, E sur un PNJ) et C sur la vraie
  banque, 0 avertissement : 77 répliques en 7,5 min, 11 vraies conversations (36 répliques), 6 discussions avec E,
  0 phrase répétée, 0 cri hors sujet (feu → cris de feu, explosion → cris d'explosion). À venir (créneau 08:30) :
  pas de voix déjà occupée pour E, dialogue coupé quand aucun joueur n'est à moins de 16 m, au plus 2 cris de mort
  par zone et par seconde. Chaque phrase n'est dite qu'une fois ; une voix = un personnage (tous les PNJ habillés en
  Colonel parlent avec la voix du Colonel, jamais deux à la fois) ; vraies conversations écrites pour la paire de
  personnages (un invité traverse la pièce pour aller parler à quelqu'un) ; seulement près des joueurs et en vue ;
  priorités cri > alarme > événement > calme > conversation > réaction ; cris selon la cause (le feu ne dit jamais
  « il a tiré ») ; E sur un PNJ = il se tourne et répond (bonjour, puis « encore vous ? », puis une remarque) ; le
  kamikaze parle rarement ; voix étouffées par les murs mais plus par les gens ; menu F2 → Son : panique par cause,
  « conversation ici », bilan des voix.
- ✅ Génération des voix arrêtée à la demande de l'utilisateur ; ce qui existe est dans le jeu (1159 répliques). Plan d'origine (agent audio) : une voix par personnage (29 voix « char_* » : la voix de chaque
  personnage est conçue une fois, puis toutes ses répliques sont clonées dessus ; `AssetGen\voices\<char_id>\`, copie
  d'écoute dans `Voix (personnages)\`), puis les lots de répliques c01 à c18 (2647 répliques écrites pour chaque personnage : 345 dialogues
  pour 210 paires de personnages, dont 8 par paire pour les 6 personnages déjà en jeu et des dialogues de piste de danse
  et de bar ; 30 remarques par personnage ; salutations, cris par cause, calme, événements, réactions, rires), puis les compléments de l'agent audio (160 dialogues,
  124 remarques, cris par cause, calme, événements, salutations). Chaque réplique est vérifiée (reconnaissance vocale),
  aucune phrase n'apparaît deux fois. Un rapport par lot (`AssetGen\audio\final\<lot>\<lot>_report.json`) : le
  directeur des voix les importe au fur et à mesure. File ComfyUI partagée : au plus 2 travaux audio à la fois.
- ✅ Ambiance sonore par pièce (agent audio, carte sauvegardée 22:10) : bibliothèque (horloge, pages), bureau (pendule,
  machine à écrire), billard (billes, conversation basse, bar), salle à manger (couverts, verres), jardin d'hiver
  (fontaine, grillons, pluie sur la verrière), hall (foule qui résonne), couloirs (murmure lointain), salle de bal (foule,
  verres, gramophone) ; fondus aux portes, sous les voix. Script `Tools\audio\room_ambience.py` (relançable).
- ✅ Musique « trompette » adoucie : la musique de fête (big band avec trompettes bouchées) et le gramophone joués moins
  fort (0,5 / 0,45). 💡 Remplacements sans cuivres (cordes, piano, clarinette) : pas générés.

- ✅ 2026-11-05 : 20 nouveaux props générés, placés dans le manoir et dans la build (même flux : image → modèle 3D → contrôle → dossier `Props (images)`) :
  banquette, coffre-fort, portemanteau, malle de voyage, vitrine, paravent, statue de danseuse, fougère sur sellette,
  cage à oiseaux, table de jeu, méridienne, seau à champagne, pare-feu, micro de scène, grand vase chinois,
  mannequin de couture, batterie jazz, secrétaire, projecteur de cinéma, contrebasse.

- ✅ Lot « retours de test » (compilé le 2026-11-02 à 23:25, 0 erreur ; à vérifier en jeu) :
  - événement « Au feu » : alarme incendie (cloche synthétisée), vraies flammes, feux sur les murs ;
  - personnage qui brûle : flammes sur lui, cri, bras qui battent l'air ; un PNJ en feu court puis meurt ;
  - tuer quelqu'un le fait crier, et les PNJ voisins réagissent ; pendant un événement, les PNJ parlent de
    l'événement (panne, feu, attaque) ;
  - manche de test : tirer sur un innocent n'enlève pas de vie au détective ;
  - le détective ne peut pas tuer le robot (les balles ricochent) ; tirer sur le kamikaze le fait exploser ;
    abattre un bandit ne coûte rien ;
  - ✅ robot : voit loin (60 m) mais étroit (cône rouge visible), tire 0,6 s après avoir repéré un joueur (il ne voyait
    jamais personne : sa ligne de vue partait de son propre corps, et les personnages ne bloquent pas le canal
    Visibility ; testé le 2026-11-03 06:2x : repéré 1, tir 1, son 26 joué, 0 erreur) ;
  - les PNJ s'approchent du piano mais n'en jouent jamais ;
  - menu dev → Partie réorganisé : « TESTER : lancer en Invité / Détective » (manche sans fin, chasse directe) ;
  - saccades du kamikaze : les corps disparaissent 20 s après la mort, le flash de l'explosion est allégé.

## Chantiers en cours (agents en parallèle, 2026-11-02 nuit)

| Chantier | Contenu | Qui |
|---|---|---|
| Voix (architecture) | aucune phrase répétée (chaque réplique dite une seule fois), vraies conversations entre PNJ, une voix fixe par personne, priorités (cris > alarme > événement > calme > conversation > réactions), seulement près des joueurs, voix étouffées par les murs, répliques selon la cause (le feu ne dit jamais « il a tiré »), E sur un PNJ = petit dialogue, sous-titres. Spécification : `VOIX_ARCHITECTURE.md` | agent « voix » + agent audio (des centaines de répliques et 150+ dialogues générés dans ComfyUI) |
| ✅ Argent et boutiques | barman (bar du billard), junkie (toilettes), 2 serveurs ambulants avec plateau (la boutique se ferme s'ils s'éloignent) ; gains (instruments, tuer un PNJ +100 $ avec cri fort et localisable, piège, survie) ; objets : fusil, fumigène, lampe, gaz rétrécissant, piège de porte, bombe à bip désamorçable, munitions de tourelle, pistolet d'échange | agent boutique |
| Caméra et combat | première personne « cool » (arme en main, recul, balancement, visée au clic droit), le corps ne tourne plus avec la souris, arme mieux tenue, tourelle sur la mezzanine (munitions pour l'invité, long rechargement pour le détective) | agent caméra |
| Vie sociale | danses des années 30 (touche V pour tous), PNJ qui viennent danser dans la salle de bal, foule qui se rassemble au bar puis repart | agent social |
| Objets à ramasser | ✅ boules de billard (arme de jet), ✅ épées des armures (attaque, visible en main, aussi à la 1re personne), ✅ pistolet d'échange de corps (fantôme bleu qui vole vers le nouveau corps, se recharge en 90 s), ✅ post-it avec le code du coffre-fort (au sol, change à chaque manche) → ✅ coffre du bureau (500 $, la porte s'ouvre), ✅ alarmes incendie (une fois par partie : tout le monde court 10 s), ✅ toilettes (E = pet sonore, les PNJ réagissent) ; testé en réseau (hôte + client) et en image ; ✅ vrais modèles 3D de l'épée et du pistolet | agent objets |
| Niveau | ✅ lampes, gramophones et radios sur des meubles (plus au sol ; l'audit le refuse désormais), ✅ repères des instruments (harpe ; batterie et contrebasse dès que leurs props sont validés), ✅ toilettes (W.C. au bout du couloir ouest : 2 cabinets, lavabos, `GW_Toilet` ×2, `GW_Junkie`), ✅ vraies fenêtres (vitres avec gouttes de pluie, on voit dehors), ✅ île dans la tempête dehors inspirée d'« Ils étaient dix » (sous-niveau `L_Manor_Island` : falaises, mer animée, arbres pliés par le vent, lanternes qui vacillent, terrasse avec balustrade, phare lointain qui clignote, pluie, nuages, éclairs synchronisés qui éclairent les pièces et zèbrent le ciel), ✅ tonnerre déclenché à chaque éclair (vérifié dans le journal du jeu), 🔄 vent et mer placés (ambiances extérieures étouffées) mais pas encore écoutés | agent niveau |
| Ambiances | ✅ une ambiance sonore par pièce, ✅ musique de trompette adoucie, 💡 musiques sans cuivres : pas générées | agent audio |
| Modèles 3D | 20 nouveaux props + objets du jeu (épée, fusil, bombes, piège, tourelle, pistolet d'échange…), personnages des événements, barman, junkie, serveurs (+ plateau à part) | agents props et personnages (ComfyUI relancé) |

Fait par le coordinateur ce soir :
- le piano devient des instruments : piano, harpe, puis batterie et contrebasse quand leurs props existeront ; un « E »
  flotte devant l'instrument, sans délai ;
- les événements se déclenchent seuls en partie : le 1er 45 s après le début de la chasse, puis environ une fois par minute ;
- un coup de feu = panique de 10 s dans tout le manoir ;
- un feu bien plus impressionnant : 5 flammes, lumière vacillante, étincelles, fumée, et il se propage ;
- le robot voit loin et étroit, avec un cône rouge visible, chasse le dernier joueur aperçu et lui tire dessus (testé) ;
- le kamikaze crie moins souvent.

## À faire — grandes nouveautés demandées (2026-11-02 soir)

- ✅ **Argent et boutiques** (agent boutique, `Tools\gameplay\s34_shop.py`, `Tools\ui\u17_shop_ui.py`, testé sans
  carte graphique le 2026-11-03 : 0 « Accessed None », 0 erreur ni avertissement de script) :
  - ✅ le **barman** (mannequin en chemise blanche, tablier, nœud papillon ; il tourne la tête vers le client) derrière
    le bar du billard ; le **junkie** dans les toilettes (casquette, autres prix, seul à vendre des **pétards**) ;
    **2 serveurs** avec plateau et coupes qui vont d'un groupe d'invités à l'autre (jamais dans une porte ni sur la
    piste de danse) : la carte se ferme toute seule si le serveur s'éloigne (« Vous avez trop hésité ! ») ;
  - ✅ E près d'un vendeur (un « E » flotte au-dessus de lui) : carte avec la bourse, une ligne par article (grisée si
    trop cher), le mot du serveur sur l'achat ; caisse enregistreuse à l'achat, bruit de pièces et « +N $ » à chaque gain ;
  - ✅ gains : instrument +25 $ (une fois / 30 s), PNJ abattu +100 $ avec un **grand cri en 3D** qui s'entend dans tout
    le manoir, piège sur un détective +50 $, détective abattu +100 $, survie +5 $ / 30 s ;
  - ✅ fusil (balle à 150 $, revolver dans la main, viseur), fumigène (nuage épais 18 s), lampe (vue par soi seul),
    gaz (petit x0,55 et rapide x1,7 pendant 20 s, clignote vert à la fin), piège de porte (boîtier sous le linteau,
    explose sur un détective : -25 PV), bombe (bip 3D de plus en plus rapide, 45 s, 9 m, désamorçable avec E),
    munitions de tourelle (+60), pistolet d'échange (l'achat ; l'échange lui-même : agent objets), pétard (leurre :
    fausse fusillade 4 s après, tout le manoir panique) ;
  - ✅ menu dev → Boutique : argent, donner un objet, boutique / marché noir sur place, aller au bar / aux toilettes /
    voir un serveur, bombes maintenant ; test automatique `-GWShopTest` ;
  - 💡 réglable : la bombe paie 100 $ par PNJ tué (une bombe dans la salle de bal rapporte vite 300-600 $) ;
  - ✅ modèles 3D du fusil, du fumigène, du gaz, du piège, de la bombe et du plateau (`Tools\gameplay\s41_item_models.py`) ; ✅ barman, junkie et 2 serveurs : peaux branchées (2026-11-05) ;
    répliques du barman, du junkie et des serveurs (catégories 15 / 63 / 62) : silencieux tant qu'elles n'existent pas (voix arrêtées à la demande).
- ✅ **Foule au bar** : toutes les 90-160 s pendant une manche, 6 à 10 PNJ se rassemblent devant le comptoir de la
  salle de billard (contre le bar ou en petits cercles), bavardent 20-40 s (gestes : parler, écouter les mains dans
  le dos, rire), trinquent (bruit de verres, « Santé ! »), bougent un peu, puis repartent un par un. Une panique,
  un événement ou le robot qui s'approche les fait fuir.
- ✅ **Danse** : **V** pour danser (charleston, lindy hop, valse lente, shimmy, truckin' : 5 danses des années 30
  créées par script) ; V à nouveau ou un pas pour arrêter. Toutes les 60-120 s pendant une manche, 4 à 8 PNJ
  viennent danser 15-40 s sur la piste devant la scène (couples face à face qui dansent en rythme, avec en plus
  un slow pour eux ; solos), puis repartent un par un ;
  le gramophone joue plus fort pendant ce temps, applaudissements (« Bravo ! ») à la fin. Menu dev : Joueur →
  Danser (V) ; PNJ → danser maintenant, foule
  au bar maintenant.
- ✅ **Tourelle** (testée sans affichage, 0 erreur) : une mitrailleuse des années 30 sur la galerie du hall, face à
  l'entrée (modèle 3D sur son pied en formes simples, s41). E pour la prendre / la lâcher, un tireur à la
  fois ; clic gauche maintenu = tir automatique (9 coups/s, traçantes, flamme, son fort qu'on localise) ; la vue
  passe au viseur, dans un arc devant soi. Invité : munitions achetées au bar (60), +100 $ par PNJ ou détective
  abattu, jamais de tir ami. Détective : 3 s de tir puis 25 s de recharge, un innocent coûte des PV. Chaque rafale
  fait paniquer le manoir 10 s. Menu dev : aller à la tourelle, 60 munitions. Vue en image (viseur, traçantes) : OK.
- ✅ **Vue à la première personne** (testée sans affichage, 0 erreur) : caméra aux yeux pour tous les joueurs, son
  propre corps invisible (pour soi seulement), arme en main visible quand on en tient une, petit recul et secousse au
  tir, balancement en marchant / courant, champ de vision des Options (+ un peu à la course) ; **clic droit = viser**
  (zoom, souris plus lente, arme au centre) ; le corps ne tourne plus jamais avec la souris (comme les PNJ), sauf en
  visant ; 3ᵉ personne pendant la danse et en option dans le menu dev (Affichage → Vue). Vue en image : OK ; le
  revolver en main (3ᵉ personne) est tenu canon vers l'avant et le bas au lieu de pendre vers le sol.
- ✅ **Piano** : plus de bandeau d'interface ; un « E » flottant juste devant le piano, intuitif ; pas de délai
  entre deux vacarmes (voir « Fait par le coordinateur »).
- ✅ 2026-11-05 (modèles des objets dans `s41_item_models.py`) : créer toutes les textures, props, particules et animations nécessaires (fusil, bombe, fumigène, gaz, piège,
  tourelle, barman…) — « do more than less ». Agent props au travail dans ComfyUI ; formes simples en attendant.

- ✅ **Objets et armes des invités** (`Tools\gameplay\s38_pickups.py`) : 6 boules de billard sur la table (E : prendre,
  2 max ; clic gauche : lancer ; PNJ tué +100 $ / détective −25 PV ; retour 45 s), les épées des 2 armures du hall
  (E : voler, visible en main ; clic gauche : coup d'épée 2 m ; retour 60 s), pistolet d'échange (R : on prend le
  corps du PNJ visé, l'ancien corps meurt, fantôme bleu visible de tous, recharge 90 s), sons synthétisés
  (`Tools\audio\synth_pickups.py`), menu dev page Joueur.
- ✅ **Coffre-fort, alarme incendie, toilettes** (même script) : post-it du code à un endroit aléatoire à chaque
  manche (E : lire, code visible pour soi seul), coffre du bureau (E avec le code : 500 $, porte qui s'ouvre, une fois
  par manche), 4 alarmes murales (E : cloche 10 s + panique 10 s, une fois par partie), toilettes (E : pet très sonore,
  5 s entre deux).

## À faire

- ✅ Chute de FPS au chargement du jeu : mesuré le 2026-11-05 (profil CSV dès le démarrage, éditeur -game non cuit, 1280x720 selon le journal, 60 PNJ) : un seul à-coup de 1,86 s à 2,2 s, caché par le rideau « Le bal se prépare… » ; 65 i/s dès la 3e seconde, 61-73 i/s ensuite, aucune image au-delà de 50 ms après 3 s. À remesurer dans le jeu empaqueté.
- ✅ Monsieur Minuit (build du 2026-11-05 11:42) : riggé, branché, en jeu dans l'éditeur (SK_char_minuit, oi=6 dans le journal) ; sera dans la prochaine build du coordinateur (la dernière date du 2026-11-03 10:02).

- 🔄 Props, chantier continu : imaginer, dessiner et générer d'autres props (la carte en veut toujours plus) ; à chaque
  nouveau prop, enregistrer son image dans `Props (images)\` (`python -I -X utf8 Tools\props\collect_prop_images.py`).
- 💡 Un jour : redonner toutes les images de `Props (images)\` et `Personnages (images)\` à un meilleur générateur 3D.

- ✅ ComfyUI bloqué depuis ~19 h 40 : relancé, l'agent props y travaille.

## Idées / décisions à prendre

- ✅ Danses : vues en jeu à l'écran le 2026-11-05 (`social_test.ps1 -Shots`) : groupe sur la piste, foule au bar ; de loin, pas de gros plan.
- 💡 Une vraie musique de danse (swing des années 30) quand les PNJ dansent, au lieu du gramophone plus fort ; à
  générer quand ComfyUI sera relancé (catégorie `dance_music` déjà prévue dans s31).
- 💡 Plugin « Multiplayer FPS » (vster) installé : à ne pas brancher tel quel (jeu à la 3ᵉ personne, tir déjà fait
  et testé, et un plugin avec du code C++ risque d'empêcher l'empaquetage sans compilateur). On peut en reprendre
  les effets (flash de tir, impacts, secousses de caméra, sons) — à confirmer.
- 💡 Odette : la grande plume du bandeau manque (le générateur 3D l'a perdue) ; possible en petite pièce rigide.
- 💡 « Victor » est un nom provisoire pour l'homme en habit.
- 💡 Masques peints (Comte, Odette) un peu marbrés de près.

## Où trouver les choses

- Jeu empaqueté : `Build\Windows\GuessWho.exe` (heure dans `BUILD_INFO.txt`), guide : `GUIDE_JOUEUR.md`
- Images des personnages : `Personnages (images)\` ; modèles et rendus : `AssetGen\chars\char_<nom>\`
- Images des props : `Props (images)\` ; descriptions : `AssetGen\props.json` ; placement : `Tools\level\dress.py`
- Scripts : `Tools\` (menu dev : `Tools\ui\u15_dev_menu.py`, galerie : `Tools\gameplay\s29_gen_chars.py`,
  fantôme : `Tools\gameplay\s30_ghost.py`, rigging : `Tools\chars\rig_character.py`)
- ✅ Optimisation : la compilation de WBP_DevMenu : menu piloté par des tableaux (`u15_dev_menu.py data`, voir Interface).
- ✅ QA (qa_suite 2026-11-05 06:47, `Tools\qa\reports\qa_20261105-0647.md`) : PASS, 0 Accessed None, 0 erreur, 0 avertissement, 42 contrôles OK (le robot de test cherche une ligne de vue, le joueur se place devant lui). Seul contrôle optionnel absent : « rideau », qui ne se journalise pas sans rendu.

## Décoration : comment on la modifie maintenant (2026-11-03)
- La décoration est figée (`Tools\level\freeze_dress.py`, drapeau `Tools\level\dress_frozen.flag`) : les 309 props sont
  des objets normaux dans `L_Manor` (dossier Outliner `Decor_Manuel/<pièce>`, tag GW_Manual). Le niveau est la
  référence ; rien ne les régénère.
- Les sessions Claude les modifient par script avec `Tools\level\props_tool.py` (export → props_layout.json, move,
  delete, add, batch) : toujours faire `export` d'abord pour lire l'état réel (y compris les retouches manuelles).
- L'utilisateur peut aussi les déplacer à la main dans l'éditeur (fermer l'éditeur caché d'abord) ; rien à déclarer.
- Nouveaux props approuvés : les placer avec `props_tool.py add <nom> x y z yaw <pièce>`.

## Retours de test du 2026-11-03 (à faire, rien n'est commencé)

### Interface
- ✅ AUCUN sous-titre : fonction Subtitle, SubText et BankText retirés des Blueprints et des scripts (s31, s39).
- ✅ AUCUN texte d'interface en haut de l'écran : bandeau de rôle, ligne d'instructions et fil d'annonces retirés ; le panneau (rôle, chrono, comptes, santé, objets) passe en bas à gauche ; les messages personnels en bas au centre.
- ✅ Grande interface de l'argent retirée ; un « +X $ » vert apparaît, grossit, monte et s'efface à chaque gain (montant visible seulement dans la boutique).
- ✅ Les événements s'annoncent en texte rouge stylé au centre de l'écran (4,5 s).
- ✅ Menu dev : cases [x] / [ ] qui montrent la vraie valeur (jouer seul, fin de manche auto, figer les PNJ, événements automatiques, interface, scores) ; « Événements automatiques » cochée par défaut. Le menu est maintenant piloté par des tableaux (compilation beaucoup plus courte, `u15_dev_menu.py data` pour une simple ligne).
- ✅ Options > Changer les touches : liste des commandes, touches modifiables et enregistrées dans les réglages, échange en cas de doublon, retour par défaut. Vérifié dans l'éditeur (`-game`) ; à reconfirmer dans le jeu empaqueté. Limite : déplacement (WASD, flèches), souris et Échap restent fixes.
- ✅ Le « E » du piano ne reste plus visible : la boucle qui le cache ne s'arrêtait plus une fois loin du piano. Sécurité sur toutes les invites flottantes : elles se cachent seules à plus de 9 m ou si elles ne sont plus rafraîchies.

### Caméra et armes
- ✅ Vue à la 3e personne par défaut ; la 1re personne s'active quand on vise avec une arme. Une touche permet aussi de basculer (décidé). C bascule ; clic droit = 1re personne avec une arme à feu (s37). Vu à l'image le 2026-11-05 : fusil et revolver dans la main à la 3e personne, mains à la 1re personne (gants de cuir sombre, avant : grosses boules rouges qui bouchaient la vue). Les gants restent des formes simples (💡 de vraies mains : à modéliser).
- ✅ Inventaire de 4 objets, plus de touches séparées par arme. Le détective a aussi un inventaire et peut acheter. Touches 1-4, molette, clic gauche, Q jette ; cases en bas (WBP_Inventory, s40_inventory.py). Testé sans rendu.
- ✅ Le fusil de la boutique : vieux fusil long à une balle, difficile à viser (le viseur bouge). Modèle 3D rifle_old (s41 ; SM_GW_Rifle ne sert plus) ; le viseur dérive, tir à la hanche à 4°. Vu à l'image avec le modèle : hanche, visée, troisième personne.
- ✅ On ne peut pas tenir une arme et utiliser la tourelle : l'arme se range.
- ✅ Tourelle : rotation très limitée, environ 30° de chaque côté. La mitrailleuse peut tuer le robot. 30° ; le robot meurt sous la mitrailleuse seulement.
- ✅ Lame secrète à acheter (façon Assassin's Creed) : tue un PNJ très discrètement, difficile à remarquer. Id 10, 180 $, aucun cri ni panique, +100 $.
- ✅ Boîte mystère (façon CoD) : payante, fait défiler tous les objets ; le joueur a tout son temps pour prendre l'objet. 100 $, change de place à chaque manche, aucune limite pour prendre l'objet.

### Économie
- ✅ Retirer le revenu passif (les 5 $ réguliers).
- ✅ Chaque corps peut être fouillé : argent, parfois un objet de la boutique. E maintenu 1,2 s : 10-60 $, 25 % d'avoir un objet.
- ✅ Petits props volables (gramophone, lampe, petits objets) : rester appuyé sur E donne de l'argent. 73 objets (9 sortes), E maintenu 1,5 s, 30-120 $.
- ✅ Tuer le kamikaze permet de récupérer sa bombe. Abattu, il n'explose plus ; la bombe reste par terre (E).
- ✅ Tirer sur un lustre le fait tomber et se briser ; il tue ceux qui sont dessous, et les morts rapportent de l'argent à l'invité qui l'a fait tomber. +100 $ par victime. Vu à l'image : lustre du hall qui tombe, disparu au plafond, +200 $ pour 2 victimes.

### Déplacement
- ✅ Tous les joueurs peuvent sauter (pas les PNJ). Sauter en sprintant donne une accélération pour fuir, sauf pour le détective. Espace ; bond en courant toutes les 3 s, pas pour le détective.
- ✅ Les alarmes peuvent être déclenchées à répétition : c'est un moyen de courir plus vite pour l'invité (remplace « une fois par partie »). 20 s par boîtier ; l'invité qui tire court x1,45 pendant 12 s.

### Événements
- ✅ Nouvel événement « attaque zombie » (Id 6, automatique et menu dev) : un PNJ se transforme (cri, 2 s sur place), marche lentement, contamine au toucher ; tout joueur peut tuer un zombie ; un joueur touché devient zombie et redevient lui-même à la fin de l'événement. Peau zombie pour tous via le paramètre ZombieAmount de M_GW_GenChar. Testé sans erreur et vu au rendu. Bras tendus et pas traînants ajoutés (clip AS_GW_Dance_Zombie, vu sur plusieurs personnages) ; la mitrailleuse tue les zombies (testé par la fonction serveur).
- ✅ Panne de courant : boîte de disjoncteurs (E) dans le couloir de service, une fois par partie (réarmable au menu dev) ; la panne naturelle reste. Testé par la fonction serveur ; la touche E réelle reste à essayer en jeu.
- ✅ Au feu : 15 lumières rouges clignotantes, 10 foyers de départ et jusqu'à 32. Vu de près le 2026-11-05 et corrigé : les flammes étaient blanches (matériau additif surexposé), elles sont maintenant vraiment orange (M_GW_Flame translucide) ; alarmes 4,7 fois plus fortes (elles ne se voyaient pas dans une pièce claire) ; les foyers de départ sont choisis sur le navmesh depuis un point intérieur (l'un d'eux brûlait sur la terrasse ; pas recompté depuis). Les flammes restent des plans animés un peu plats.
- ✅ Robot : cône net de 30 m (la portée réelle), ligne centrale et 4 arêtes lumineuses, coupé au premier mur. Vu au rendu.
- ✅ Kamikaze : 10 répliques variées, une toutes les 7-10 s ; les PNJ qui le voient fuient (12 m pour le zombie : 7 m). La boucle « ALARME » n'a pas été reproduite (voir Tools/agent_logs/events.md) : à réécouter en jeu.
- ✅ Bandits : à la fin ils marchent vers l'entrée principale et disparaissent à 1,5 m du point de sortie.

### PNJ et foule
- ✅ Nombre de PNJ réglable au menu dev. Mesuré : 150 PNJ (× 5) donne 35 i/s, donc défaut à 60 (72 i/s). Chiffres dans Tools/agent_logs/events.md.
- ✅ Les PNJ s'assoient sur 173 places (chaises, fauteuils, canapés, bancs) : 70 % 12-40 s, 30 % 60-150 s. Vu au rendu sur un canapé.
- ✅ Salle de bal : un invité qui danse attire jusqu'à 3 PNJ libres à moins de 4,5 m, même danse, face à lui. Testé sans rendu.
- ✅ Le personnage du joueur crie et réagit comme les autres invités, avec sa propre voix (vu dans le journal du serveur).
- ✅ Dialogues : E fait parler le personnage du joueur avec sa propre voix ; le PNJ répond 8 fois sur 10 ; des paires de PNJ font le même échange d'elles-mêmes, en silence loin des joueurs. Un personnage sans répliques enregistrées reste muet.

### Musique
- ✅ Musique tendue seulement pendant une attaque (bandits, kamikaze, zombies) et 25 s après un coup de feu ; plus rien pour le chrono. Pendant la chasse, la musique de fête continue, moins fort. États vérifiés dans le journal, pas écoutés.

### Objets et décor
- ✅ Les chevaliers tiennent vraiment l'épée. Poignée dans le gantelet droit, pointe au sol. Vu à l'image.
- ✅ Lire le post-it ne fonctionne pas : à corriger. Carte à l'écran, relisible, accessible à tout joueur vivant.
- ✅ Piège : un peu plus visible, plus facile à poser, se déclenche à chaque passage d'un joueur ou d'un personnage d'événement, pas d'un PNJ ordinaire. Plus gros, lumière rouge ; porte ou sol ; joueurs et intrus seulement.
- ✅ Vérifier qu'en partie normale le détective peut vraiment mourir (piège, trop d'innocents tués). Vérifié : 4 pièges ou 4 innocents hors manche de test le tuent.

### Finitions (2026-11-05, agent finisher, tout vu à l'écran sauf mention)
- ✅ Couleurs de lumière (rouge et bleu inversés) corrigées dans les Blueprints : lampe, fantôme d'échange, gaz, bombe, explosions, pétard, piège, flash du tir.
- ✅ WBP_Shop compile sans erreur (le 10e article manquait au script) ; carte refaite : 10 articles tiennent à l'écran, colonnes alignées, plus de colonne « Clic ».
- ✅ Viseur seulement avec le fusil, le revolver, le pistolet d'échange ou les boules en main. TxtItems caché (vu).
- ✅ Options > Commandes en français, « Objet 1-4 » dans l'ordre. Comment jouer et la ligne d'aide montrent les touches actuelles et les nouvelles commandes. Le sélecteur de touche lui-même affiche le nom anglais du moteur (Left Shift…).
- ✅ Foule du bar : les PNJ partent un par un (1,1 s entre chacun) ; sur le dernier test, 1 abandon pour 3 arrivées au bar : amélioration à confirmer sur une plus longue partie.
- ✅ Menu dev : « Nombre de PNJ » marche (40 puis 60 testés) et détruit aussi le contrôleur du PNJ retiré ; « Aller voir l'événement » n'envoie plus dehors.
- ✅ Message orange « Multiple directional lights » : l'éclair passe après la lune. À confirmer pendant un orage.

### Retours de test du 2026-11-05 (build de 08:58)
Logique testée sans son (-nosound) ; images vues : carte, cases, boutique, fantôme, objets au sol, pistolet, faisceau (ScreenShot01182-01206). Rien n'a été écouté : tout ce qui concerne le son reste ⏳.
- ✅ 1. Zombies : la contagion ralentit (une morsure toutes les 8 s au plus, 6 zombies à la fois) et chaque zombie tombe 15 s après sa transformation (mesuré : 15,2 s) ; l'événement se termine quand le dernier tombe. ⏳ Le nouveau gémissement (soupirs existants passés dans le grave) n'a pas été écouté. Un joueur mordu meurt aussi au bout de 15 s (règle à confirmer).
- ✅ 2. Post-it : grande carte Art déco au centre (vue), relisible à volonté (lu 4 fois en test), se ferme avec E, en s'éloignant ou après 10 s (testé, aussi côté client).
- ✅ 3. Pendant les zombies, les PNJ n'ont plus les répliques du robot (la catégorie manquait dans la table). Il n'existe pas de répliques de zombies : cris et appels à l'aide génériques, en attendant des voix.
- ⏳ 4. Bureau : la pendule retirée de l'ambiance AMB_Room_Study. Pas écouté. La bibliothèque a encore sa comtoise (non demandé).
- ✅ 5. Q pose vraiment l'objet au sol à vos pieds, tous les objets, visible par les autres (testé côté client) ; E le reprend. La touche Q et la touche E sur un client réel n'ont pas été testées, seulement le côté serveur.
- ✅ 6. Un événement automatique toutes les 3 minutes par défaut ; le menu dev a « 3 min ». Le premier arrive toujours 45 s après le début de la chasse.
- ✅ 7. La lampe torche n'est plus en vente (elle reste dans la boîte mystère, sur les corps et au menu dev).
- ✅ 8. Le laser s'arrête au premier mur ou objet, trait et dégâts ; le robot ne voit plus à travers un mur tout proche ; son cône aussi part de l'œil.
- ⏳ 9. Le « TIN TIN TIN » : c'est MUS_Event_Attack (un coup de cuivres toutes les 0,78 s, identifié à la mesure, pas à l'oreille), retiré des événements ; les pas du robot, métalliques, sont aussi assourdis. À écouter.
- ✅ 10. 1,5 s d'avertissement : le cône se referme, un rayon fin clignote et grossit (vu), suit la cible 0,5 s puis garde sa ligne ; un pas de côté évite le tir (testé). Un tir enlève 55 PV : deux tirs tuent (testé). ⏳ Sifflement de charge pas écouté.
- ⏳ 11. Un tir : un seul coup, une seule fois tant que la fusillade dure (extrait de la même piste). Logique en place, pas écoutée.
- ✅ 12. Le robot se tue : 300 PV, balle -100, épée -50, boule -20, mitrailleuse -25, piège -150, explosion : mort. Il tombe, explose, ses yeux s'éteignent. ⏳ Vu seulement dans les journaux.
- ✅ 13. Pistolet d'échange en main, en 3e personne pour tous (vu, et testé côté client) et en 1re personne (vu). Une icône par objet (Props (images)\icons, `Tools\props\item_icons.py`), dans les cases et la boutique (vues).
- ✅ 14. Le gaz réduit à x0,3 au lieu de x0,55 (réglable au menu dev). ⏳ Caméra et collisions à cette taille pas vues.
- ✅ 15. Piège en main près d'une porte : piège fantôme vert et ligne sur tout le linteau (vus) et l'invite « Clic : Poser le piège dans la porte », seulement chez soi (testé côté client : apparaît, disparaît avec un autre objet ou en s'éloignant, rien chez l'hôte).
- Menu dev : nouvelle page « Réglages » (zombies, robot, gaz, jeter, donner).

### Retours de test du 2026-11-05 (3)
- ✅ Objet « Mascarade » (id 14, 150 $ au bar, 120 $ au junkie, refusé aux détectives) : tous les invités vivants, joueurs compris, changent d'apparence au hasard. `Tools/gameplay/s45_mascarade.py`, menu F2 Boutique > Donner. Testé : 31 personnages changent, objet consommé, 0 erreur. Pas vu ni entendu : icône, rangée en plus dans la boutique, le « Reveal » et les souffles coupés (pas de nouvelle réplique, génération de voix arrêtée). Exclusion du détective pas mise à l'épreuve (0 détective dans le test), coût d'image à 120 PNJ pas mesuré.
- ⏳ Saut « bogué » : pas reproduit (hôte : 128 cm, 1,02 s en l'air, plan `py_harness -Plan bump`). Il manque la description de ce qui se voit. À noter : au sprint, la vitesse chute brièvement de 350 à 285 environ, même sans obstacle, cause inconnue.
- ⏳ Chute en courant dans un corps ou un joueur : pas reproduit côté hôte (0 s en l'air contre un PNJ et sur un corps, aucun ragdoll au contact dans le code). Pas essayé côté invité, où la correction réseau peut soulever le personnage. Il manque : hôte ou invité, vivant ou mort.

### Jeu en ligne avec code de partie (EOS), 2026-11-05
- ✅ Héberger donne un code de 6 caractères, Rejoindre l'accepte dans le même champ que l'IP. Sans compte Epic, sans port ouvert. Module `GuessWho/Source/GuessWho/GWOnline.cpp`, identifiants dans `Config/DefaultEngine.ini` (section GWEOS).
- ✅ Testé sur l'exécutable final (`Tools/qa/eos_test.ps1`) : deux instances sur un PC, relais d'Epic forcé (`EOS_NCT_RelayedConnection`), 2 manches, 0 erreur. Mode IP toujours bon (`pkg_nettest`).
- ⏳ À vérifier : vrais boutons du menu, affichage du code à l'écran, partie entre deux réseaux différents (avec un ami ou par partage de connexion), repli IP sans Internet, renouvellement du jeton après 1 h.
- ⏳ Proton sur Fedora pas essayé. Build Linux natif non commencé : il manque le support Linux du moteur et l'outil de compilation croisée.

### Retours de test du 2026-11-05 (2)
- ✅ Kamikaze : plus aucune réplique ni tic-tac, seulement l'alarme, en 3D (de plus en plus fort quand il approche), du début à sa chute (testé hôte et client). ⏳ Pas écouté. Il n'existe aucune prise de SA voix disant « Alarme » : c'est une prise inutilisée de la voix du colonel, montée de 2 demi-tons. Il faudrait 2 à 4 prises « ALARME ! » de char_kamikaze.
- ✅ Alarme : exactement 0,2 s de silence entre deux cris (mesuré dans le fichier : 0,2001 s, aussi à la jonction de la boucle). ⏳ Pas écouté.
- ✅ Piège : il faisait bien des dégâts (-25) ; un invité joueur n'avait pas de vie affichée et rien ne le signalait. Maintenant -50 (réglable), projeté en l'air, cri, écran rouge, « -50 », coup sourd. Testé hôte et client. Un PNJ ordinaire ne le déclenche toujours pas (demande précédente) ; Réglages > « Aussi les invités » : testé, il meurt, +100 $. ⏳ Effets non écoutés.
- ✅ Interface : vie en bas à gauche, argent en bas à droite (grands chiffres), cases d'objets avec icônes entre les deux, même cadre Art déco. Rien en haut. La ligne d'aide s'efface 20 s après le début de la chasse (Tab la rappelle). Vu en 1920x1080 (salon, cases vides). ⏳ Pas vu : 1280x720, cases pleines, écran rouge et « -50 » (ils ne tournent pas sans rendu).
- ✅ Lame secrète : recharge de 8 s à chaque coup, réglable (Réglages), vérifiée par le serveur, rideau sombre et secondes sur la case. Testé hôte et client.
- ✅ Serveurs (position de la main mesurée, ⏳ pose pas vue à l'image) : sur l'hôte ils glissaient sans marcher (accélération nulle), le client les voyait marcher. Ils ont maintenant leur marche et leur attente, avant-bras sous le plateau, sur toutes les machines (testé). Barman, junkie, PNJ et autres joueurs s'animaient déjà.
- ✅ S'asseoir : E près d'un siège libre (les mêmes 181 que les PNJ, même pose), E ou bouger pour se lever, invite à l'écran, siège pris refusé. Testé hôte et client (W se lève côté client). ⏳ Pose assise du joueur pas vue à l'image ; vraie touche E côté client non pressée par une personne.
- ✅ Souris : à l'arrêt le corps ne tournait déjà pas (mesuré). C'est en marchant que la caméra dirigeait le corps : tant que les mêmes touches restent enfoncées, la marche ne suit plus la caméra qu'à 120°/s (Réglages) ; un changement de touche repart de la caméra. Visée et 1re personne : le corps suit la visée. ⏳ Sensation à juger en jouant.
- ⏳ Écran « La soirée » à l'hébergement : invités 30 à 200 (120), chasse, cachette, manches, détectives, événements et fréquence, joueurs pour commencer, attente au salon ; gardé d'une partie à l'autre. Testé : ouverture depuis le vrai menu, valeurs, flèches. Pas testé : le voyage jusqu'au jeu avec ces valeurs (il passe par le Tick du menu, qui ne tourne pas sans rendu), la fin de partie après N manches, l'écran à l'image. Dernière manche : le journal de fin dit encore « Manche suivante ».

### Points à trancher
- Vue : DÉCIDÉ par l'utilisateur : 3e personne par défaut, 1re personne en visant, et une touche pour basculer.
- PNJ × 5 : passer d'environ 40 à environ 200 PNJ risque de coûter cher en images par seconde. Mesurer d'abord, avec le nombre réglable dans le menu dev.
- Voix : la génération est arrêtée à la demande de l'utilisateur. Vérifier que les 8 répliques du kamikaze ont bien été enregistrées, sinon en rendre seulement celles-là.

### Retours de test du 2026-11-05 (2) : PNJ (agent feedback6_npc, chiffres dans Tools/agent_logs/feedback6_npc.md)
- ✅ PNJ qui apparaissent / disparaissent : trois causes trouvées à la mesure et corrigées : la caméra cachait tout invité qui passait entre elle et le joueur (seulement si la caméra est dans l'invité maintenant) ; s'asseoir et se lever téléportait jusqu'à 1,7 m (glissement de moins d'une seconde maintenant) ; un corps partait après 20 s même sous les yeux du joueur, un remplaçant apparaissait n'importe où (hors de vue maintenant). Testé sans rendu : 0 saut sur l'hôte à 120 PNJ. ⏳ Pas revérifié côté client après correction, pas vu au rendu.
- ✅ PNJ qui restent plantés : un invité qui se levait d'un siège ne pouvait plus jamais bouger (mode de déplacement mal écrit). Corrigé.
- ⏳ Mouvement plus humain : personnalité par PNJ, humeurs, tableaux, fenêtres, scène, cheminées, murs, duos qui marchent ensemble, cercles de conversation, regards, rotation douce. Mesuré dans les journaux, jamais vu en mouvement à l'écran.
- ✅ Distribution : 54 invités au lieu de 23, tenues tirées sans doublon avant d'avoir épuisé la distribution. L'inspecteur Dupuis est laissé de côté (ressemble au détective). ⏳ Les nouveaux n'ont pas de voix (31+), restent muets.
- ⏳ Temps assis au hasard, de 5 s à plus de 3 min, par siège. Plus de danseurs (12 à 20 + ceux qui rejoignent, le piano lance la danse). Vraies files au bar (3 files, 25 places, 17 à 24 PNJ en file mesurés). Pas vus à l'écran.
- ⏳ PNJ bloqués entre eux : le moins prioritaire s'écarte à droite, puis les deux s'ignorent 1,5 s, puis glissement en dernier recours. Moins de blocages mesurés, il en reste : voir le rapport.
- ⏳ 120 PNJ par défaut (BP_GW_GameMode.NPCCount, ?NPCs=). Menu dev PNJ : 30 à 200, anti-blocage, état. Mesuré : 56 i/s (image p95 : 44 i/s) dans l'éditeur non cuit, hors manche, ComfyUI occupé. Pas mesuré dans le jeu empaqueté.
