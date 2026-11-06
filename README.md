# Le Bal Masqué

Jeu multijoueur Unreal Engine 5.8. Manoir Ashcombe, 1932 : tous les joueurs sont déguisés en invités parmi des dizaines de PNJ. Chacun cherche les autres, et le dernier debout gagne.

Ce dépôt contient le code, les scripts et les documents. Il ne contient **pas** le contenu du jeu (`Content/`), le moteur ni les builds : il ne suffit donc pas pour compiler ou jouer.

- Règles et commandes : [GUIDE_JOUEUR.md](GUIDE_JOUEUR.md)
- Conception : [PLAN.md](PLAN.md)
- Travaux : [BACKLOG.md](BACKLOG.md)
- Scripts qui écrivent le jeu : [Tools/](Tools/), à lire à partir de [Tools/AGENTS.md](Tools/AGENTS.md)

## Configuration

`GuessWho/Config/DefaultEngine.ini` n'est pas publié, car il contient les identifiants Epic Online Services. Copiez `DefaultEngine.ini.example` sous ce nom et remplissez la section `[GWEOS]` avec les vôtres.
