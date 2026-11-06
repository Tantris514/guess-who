# Le Bal Masqué — Manoir Ashcombe, 1932

Plan de production du jeu « Guess Who » (cache-cache parmi des PNJ, à la manière du mode Garry's Mod), fait dans Unreal Engine 5.8 avec les MCP ComfyUI et Unreal.

## Le jeu

- **Concept** : un bal masqué dans un grand manoir des années 1930. Une trentaine d'invités PNJ déambulent. Parmi eux se cachent des joueurs.
- **Invités (cacheurs)** : ils ont exactement la même apparence que les PNJ (mêmes tenues et masques, couleurs tirées au hasard dans la même liste). Ils doivent marcher, s'arrêter et flâner comme les PNJ pour ne pas se faire repérer. Courir est possible, mais louche.
- **Détectives (chercheurs)** : ils ont un look distinct (imperméable) et un revolver. Ils sont aveuglés 20 s au début de la manche, le temps que les invités se dispersent.
  - Tirer sur un joueur caché l'élimine.
  - Tirer sur un PNJ innocent coûte 25 PV au détective (4 erreurs = éliminé).
- **Manche** : 4 minutes.
  - Les détectives gagnent s'ils éliminent tous les invités-joueurs.
  - Les invités gagnent s'il en reste un en vie à la fin du chrono.
  - Les rôles tournent à chaque manche et un score est tenu.
- **Multijoueur** : un joueur héberge (serveur intégré à sa partie) et les autres rejoignent par adresse IP (LAN ou Internet avec redirection de port 7777/UDP). Jusqu'à 8 joueurs.

## La carte : manoir 1930

Pièces prévues, sur un étage avec mezzanine :

- **Grand hall** : double hauteur, grand escalier, galerie en balcon, damier de marbre.
- **Salle de bal** : parquet, lustres, estrade avec piano et gramophone.
- **Bibliothèque** : rayonnages, globe, fauteuils club, cheminée.
- **Salle à manger** : longue table, chandeliers, portraits.
- **Salle de billard / fumoir** : billard, chesterfields, bar.
- **Bureau** : secrétaire, machine à écrire, téléphone, coffre.
- **Jardin d'hiver** : palmiers, mobilier en rotin.
- **Corridors** : galeries de portraits.

Direction artistique :

- **Matériaux** : boiseries en noyer et acajou, papiers peints Art déco, parquet en point de Hongrie, plafonds à caissons, laiton, tapis persans.
- **Tableaux** : des dizaines de tableaux à l'huile.
- **Ambiance** : éclairage chaud de lustres (Lumen), nuit de pluie aux fenêtres.

## Pipeline des assets (MCP ComfyUI, 100 % local)

1. **Concept** : image du meuble ou de l'objet, isolé sur fond neutre (Z-Image Turbo, Krea 2, Qwen-Image), puis **revue visuelle** (rejet et régénération si ce n'est pas joli ou pas d'époque).
2. **3D** : détourage (BiRefNet), puis TRELLIS 2 qui produit un modèle 3D texturé (GLB). Ensuite, nettoyage (décimation, texture PBR) et rendu sous plusieurs angles, suivi d'une **revue visuelle du modèle**.
3. **Import** : import dans Unreal, mise à l'échelle et collisions, puis capture de vignette dans Unreal pour une **revue finale**, et placement.
4. **Matériaux** : textures raccordables (bois, papiers peints, parquet, marbre, tapis) générées, rendues sans couture, avec cartes normales et rugosité dérivées, puis matériaux Unreal.
5. **Tableaux** : portraits et paysages générés, puis toiles encadrées dans le manoir.

## Architecture technique

- **Projet 100 % Blueprint** : il n'y a pas de compilateur C++ sur la machine, et un projet Blueprint se package avec les exécutables précompilés du moteur.
- **Écriture des Blueprints** : via le MCP Unreal (DSL de graphes Blueprint, outils d'acteurs, de matériaux et de scène) et des scripts Python dans l'éditeur.
- **Réseau** :
  - variables répliquées avec RepNotify pour l'état de la manche, les rôles et la vie ;
  - commandes client → serveur (tirer, etc.) via `ServerExec` vers des fonctions Exec côté serveur. Ça fonctionne en build Development, qui est le build livré.
- **Classes** : GameMode, GameState, PlayerState, PlayerController, Personnage joueur, PNJ + contrôleur IA, widgets (menu principal, HUD, fin de manche).
- **IA des PNJ** : déplacement vers des points aléatoires du NavMesh (généré à l'exécution), pauses, regards.
- **Personnages** : mannequins UE5 animés (marche, mort, pistolet), habillés en tenue de soirée 1930 avec masque et chapeau générés par ComfyUI.

## Étapes

1. Boucle de jeu jouable en gris : réseau, rôles, PNJ, tir, manches, HUD.
2. Génération et revue des assets (matériaux, tableaux, meubles et objets 3D).
3. Construction et habillage du manoir, éclairage.
4. Tests multijoueur (plusieurs instances), corrections, polish.
5. Build Windows jouable et guide du joueur.
