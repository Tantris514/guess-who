"""Dev menu (F2): a compact trainer-style menu with sub-pages, one line per entry, driven from the keyboard while you
keep playing. Up / Down (or numpad 8 / 2) pick a line, Left / Right (4 / 6) change its value, Enter (5) applies or opens
a page, Backspace (0) goes back (closes on the first page), Esc or F2 close. WASD and the mouse still move you: while
the menu is open its own mapping context (priority 10) takes the arrows and Enter away from movement.

Everything is the PAGES table below; adding a test is one line there (+ a GWDev* Exec function on
BP_GW_PlayerController when the server must act), then re-run this script. Entry kinds:
  page(label, key)                 opens another page
  srv(label, cmd)                  server command ("GWDev..."): host runs it, a client sends "ServerExec cmd"
  pick(label, how, cmd, options)   Left / Right choose an option, Enter sends cmd.format(arg); how = srv | both
                                   (here and on the server: movement speed) | local (console command here) | ui
                                   (cmd is Blueprint DSL run in the widget)
  check(label, cmd, flag)          [x] / [ ] showing the REAL server value (bit of BP_GW_GameState.DevFlags, set by GWDevSync);
                                   Enter or Left / Right send cmd.format(0 or 1)
  checkui(label, read, off, on)    the same for local state: read = DSL bool, off / on = DSL run in the widget
  local(label, cmd)                console command on this machine (stat fps...)
  ui(label, code)                  Blueprint DSL run in the widget
  cast / castnpc / sound / sounds  the generated cast (+ detective look) for you / for every NPC; the game's sounds
The widget is data-driven since 2026-11-04 (it took 10-20 min to compile with one set of widgets and nodes per entry): a pool of
ROW_POOL rows filled from arrays in the class defaults. UE_ARGS: 'data' = PAGES labels / commands only (no compile, seconds; not for a
new ui() / checkui() code or a new page count above ROW_POOL), 'widget' = the widget only, 'pc' = player controller + game mode only,
nothing = everything. A new server command needs 'pc' (EXEC + PCG) and its entry 'data'.
Server commands are refused for a client unless the server was started with -GWDev (the host's own are always
accepted), so a real party cannot use them. -GWDevTest runs every server command and the page navigation on a timer
and logs the state ("GW devtest ..."); -GWDevShot adds screenshots with the UI.
"""
import sys
sys.path.insert(0, r'J:\Projets\Unreal_Projects\Guess Who\Tools\ui')
import importlib, uilib
importlib.reload(uilib)
from uilib import *
import gw_lib

ISVALID = 'GW|Call|/Script/Engine.KismetSystemLibrary|IsValid'
CHAR = '"/Game/GW/Blueprints/BP_GW_Character.BP_GW_Character_C"'
DM = '/Game/GW/UI/WBP_DevMenu.WBP_DevMenu_C'
HUD = '/Game/GW/UI/WBP_HUD.WBP_HUD_C'
IMC_DEV = '/Game/GW/Input/IMC_GW_DevMenu.IMC_GW_DevMenu'
INP = '/Game/GW/Input'
AT = unreal.AssetToolsHelpers.get_asset_tools()
INK = (0.03, 0.022, 0.015, 1)
ROW_POOL = 24                                      # rows on the longest page (assert below)
PARTS = set(UE_ARGS) & {'data', 'widget', 'pc'}
DO_W = not PARTS or 'widget' in PARTS
DO_PC = not PARTS or 'pc' in PARTS
# bits of BP_GW_GameState.DevFlags (GWDevSync, server)
F_SOLO, F_AUTOEND, F_FROZEN, F_AUTOEV, F_NPCBLOCK = 1, 2, 4, 8, 16
ALL_MAX_S = 12.0                                   # "play all": long music tracks are cut after this
PCCAST = '(Utilities|Casting|CastToBP_GW_PlayerController (Widget|GetOwningPlayer))'


def page(label, key): return dict(kind='page', label=label, key=key)
def srv(label, cmd): return dict(kind='srv', label=label, cmd=cmd)
def pick(label, how, cmd, opts): return dict(kind='pick', label=label, how=how, cmd=cmd, opts=opts)
def check(label, cmd, flag): return dict(kind='check', label=label, cmd=cmd, flag=flag)
def checkui(label, read, off, on): return dict(kind='checkui', label=label, read=read, off=off, on=on)
def local(label, cmd): return dict(kind='local', label=label, cmd=cmd)
def ui(label, code): return dict(kind='ui', label=label, code=code)
def special(kind, label): return dict(kind=kind, label=label)


# spawn points of each room in L_Manor (GW_NPCSpawn markers), raised to stand on the floor
ROOMS = [('Hall d’entrée', (2845, 1485, 130)), ('Salle de bal', (2925, 3565, 130)), ('Bibliothèque', (1085, 3405, 130)),
         ('Salle à manger', (1085, 1685, 130)), ('Billard', (4765, 1685, 130)), ('Bureau', (5085, 2485, 130)),
         ('Jardin d’hiver', (4605, 3285, 130)), ('Galerie (étage)', (2450, 2170, 630)), ('Vestiaire', (3000, 380, 130))]
HUD_VIS = f'''(bind pc {PCCAST}
      (:then
        (bind hud (GW|Get|BP_GW_PlayerController|HUDWidget :self pc))
        (if ({ISVALID} :Object hud)
          (Widget|SetVisibility :self hud :InVisibility "{{}}")))
      (:CastFailed))'''
SCORES = f'''(bind pc {PCCAST}
      (:then (GW|Set|BP_GW_PlayerController|ShowScores :self pc :ShowScores {{}}))
      (:CastFailed))'''
PAUSE = f'''(CallFunction|CloseDev)
    (bind pc {PCCAST}
      (:then (GW|Call|BP_GW_PlayerController|UIMenuPressed :self pc))
      (:CastFailed))'''
# first / third person, local (s37_view.py BP_GW_PlayerController.SetViewMode)
VIEWMODE = f'''(bind pc {PCCAST}
      (:then (GW|Call|BP_GW_PlayerController|SetViewMode :self pc :FP {{}}))
      (:CastFailed))'''
SHOP_HERE = '''(CallFunction|CloseDev)
    (bind pc {PCCAST}
      (:then (GW|Call|BP_GW_PlayerController|OpenShopHere :self pc :Kind {}))
      (:CastFailed))'''.replace('{PCCAST}', PCCAST)
PAGES = [
    ('root', 'Menu', [page('Joueur', 'player'), page('Partie', 'game'), page('PNJ', 'npc'), page('Affichage', 'view'),
                      page('Événements', 'events'), page('Son', 'sound'), page('Boutique', 'shop'), special('close', 'Fermer')]),
    ('player', 'Joueur', [
        special('cast', 'Personnage'),
        srv('Devenir fantôme', 'GWDevGhost'),
        srv('Réapparaître', 'GWDevRespawn'),
        pick('Rôle', 'srv', 'GWDevRole {}', [('Invité', 1), ('Sans rôle', 0)]),
        pick('Se téléporter', 'srv', 'GWDevTeleport {}', [(n, f'{x} {y} {z}') for n, (x, y, z) in ROOMS]),
        pick('Vitesse', 'both', 'GWDevSpeed {}', [('x2', 200), ('x4', 400), ('x0,5', 50), ('x1', 100)]),
        srv('Soigner (100 PV)', 'GWDevHeal'),
        pick('Score', 'srv', 'GWDevScore {}', [('+5', 5), ('+1', 1), ('-1', -1), ('-5', -5)]),
        # s38_pickups.py (Exec bodies there): weapons and interactables
        srv('Donner une boule de billard', 'GWDevGiveBall'),
        srv('Donner une épée', 'GWDevGiveSword'),
        srv("Donner le pistolet d'échange (rechargé)", 'GWDevGiveSwap'),
        srv('Apprendre le code du coffre', 'GWDevLearnCode'),
        pick('Aller à', 'srv', 'GWDevGoTo {}', [('Post-it du code', 2), ('Coffre-fort', 3), ('Alarme incendie', 4), ('Toilettes', 5), ('Boules de billard', 0), ('Épées', 1)]),
        srv("Réarmer l'alarme incendie", 'GWDevAlarmReset'),
        srv('Aller à la tourelle', 'GWDevTurretGo'),                       # s35_turret.py
        srv('Donner 60 munitions de tourelle', 'GWDevTurretAmmo'),
        srv('Danser (V)', 'GWDance'),                          # s36_social.py (toggle)
    ]),
    ('game', 'Partie', [
        # 1) test environment in one line: a round that never ends (no timer, no win, no "not enough players", no
        #    health lost for innocents), straight into the hunt, with the role picked here (GWDevQuickTest)
        srv('TESTER : lancer', 'GWDevQuickTest 1'),
        srv('TESTER : arrêter', 'GWDevTestEnd'),
        # 2) a normal round, as the players get it
        srv('Manche normale : lancer', 'GWDevStartRound'),
        srv('Manche normale : passer à la chasse', 'GWDevHunt'),
        pick('Manche normale : terminer', 'srv', 'GWDevEndRound {}', [('Victoire', 2), ('Personne', 4), ('Annulée', 3)]),
        srv('Éliminer un autre joueur', 'GWDevKillRival'),
        srv('Retour à la salle d’attente', 'GWDevLobby'),
        # 3) settings
        check('Réglage : jouer seul', 'GWDevSolo {}', F_SOLO),
        check('Réglage : fin de manche auto', 'GWDevAutoEnd {}', F_AUTOEND),
        pick('Réglage : chrono', 'srv', 'GWDevClock {}', [('+60 s', 60), ('-30 s', -30), ('Finir la phase', 0)]),
        pick('Réglage : vitesse du jeu', 'srv', 'GWDevTimeScale {}', [('x0,5', 50), ('x0,25', 25), ('x2', 200), ('x4', 400), ('x1', 100)]),
        srv('Annonce de test', 'GWDevAnnounce'),
    ]),
    ('npc', 'PNJ', [
        pick('Ajouter des PNJ', 'srv', 'GWDevNPCAdd {}', [('5', 5), ('1', 1), ('20', 20)]),
        pick('Retirer des PNJ', 'srv', 'GWDevNPCRemove {}', [('5', 5), ('1', 1), ('Tous', 999)]),
        pick('Nombre de PNJ', 'srv', 'GWDevNPCCount {}', [('30', 30), ('60', 60), ('80', 80), ('100', 100), ('120', 120), ('150', 150), ('180', 180), ('200', 200)]),
        check('Figer les PNJ', 'GWDevNPCFreeze {}', F_FROZEN),
        srv('Abattre le PNJ le plus proche', 'GWDevNPCKill'),
        special('castnpc', 'Habiller tous les PNJ'),
        srv('PNJ : danser maintenant', 'GWDevDanceNow'),         # s36_social.py
        srv('PNJ : foule au bar maintenant', 'GWDevBarNow'),
        check('PNJ : anti-blocage entre PNJ', 'GWDevNPCBlock {}', F_NPCBLOCK),       # s44_npc_life.py
        srv('PNJ : état (marchent, cercles, duos, assis, en file)', 'GWDevNPCState'),     # s44_npc_life.py
    ]),
    ('events', 'Événements', [                       # s32_events.py
        pick('Déclencher', 'srv', 'GWDevEvent {}', [("À l'attaque", 1), ('Au feu', 2), ('Panne de courant', 3), ('Kamikaze', 4), ('Robot', 5), ('Zombies', 6)]),
        srv('Disjoncteurs : réarmer (une fois par partie)', 'GWDevBreakerReset'),
        srv("Aller voir l'événement", 'GWDevEventGo'),
        srv('Robot : en face de moi (test)', 'GWDevRobotTest'),
        srv("Arrêter l'événement", 'GWDevEventStop'),
        check('Événements automatiques', 'GWDevAutoEvents {}', F_AUTOEV),
        pick('Fréquence', 'srv', 'GWDevEventEvery {}', [('3 min', 180), ('1 min', 60), ('30 s', 30), ('2 min', 120)]),
        pick('Durée', 'srv', 'GWDevEventDur {}', [('Par défaut', 0), ('15 s', 15), ('30 s', 30), ('60 s', 60)]),
    ]),
    ('tune', 'Réglages', [                          # the user's test of 2026-11-05 (s40_events2.py, s32_events.py, s34_shop.py, s40_gm.py)
        pick('Zombies : vie', 'srv', 'GWDevZombieLife {}', [('15 s', 15), ('8 s', 8), ('30 s', 30)]),
        pick('Zombies : une morsure par', 'srv', 'GWDevZombieBite {}', [('8 s', 8), ('4 s', 4), ('15 s', 15)]),
        pick('Robot : vie', 'srv', 'GWDevRobotHP {}', [('300', 300), ('100', 100), ('600', 600)]),
        pick('Robot : dégâts du laser', 'srv', 'GWDevRobotDmg {}', [('55', 55), ('25', 25), ('100', 100)]),
        srv('Robot : le toucher (-100)', 'GWDevRobotHit'),
        pick('Gaz : taille', 'srv', 'GWDevGasScale {}', [('x0,3', 0.3), ('x0,2', 0.2), ('x0,4', 0.4), ('x0,55', 0.55)]),
        pick('Lame secrète : recharge', 'srv', 'GWDevBladeCD {}', [('8 s', 8), ('4 s', 4), ('15 s', 15), ('30 s', 30), ('Aucune', 0)]),
        pick('Marche : la souris infléchit le cap', 'srv', 'GWDevMoveTurn {}', [('120 °/s', 120), ('60 °/s', 60), ('240 °/s', 240), ('Sans limite', 0)]),
        srv("S'asseoir / se lever (E)", 'GWSit'),
        pick('Piège : dégâts', 'srv', 'GWDevTrapDmg {}', [('50', 50), ('25', 25), ('75', 75), ('100', 100)]),
        pick('Piège : qui le déclenche', 'srv', 'GWDevTrapNPC {}', [('Joueurs et intrus', 0), ('Aussi les invités', 1)]),
        srv("Jeter l'objet sélectionné (Q)", 'GWInvDrop'),
        srv('Donner un piège', 'GWDevGiveItem 5'),
        srv("Donner le pistolet d'échange", 'GWDevGiveItem 8'),
        srv('Aller au post-it', 'GWDevPostIt'),
    ]),
    ('view', 'Affichage', [
        pick('Vue', 'ui', VIEWMODE, [('1re personne', 'true'), ('3e personne', 'false')]),
        local('Afficher les FPS', 'stat fps'),
        local('Temps de calcul (stat unit)', 'stat unit'),
        pick('Qualité graphique', 'local', 'scalability {}', [('Faible', 0), ('Moyenne', 1), ('Élevée', 2), ('Épique', 3)]),
        checkui('Interface du jeu', '(CallFunction|HudOn)', HUD_VIS.format('Hidden'), HUD_VIS.format('Visible')),
        checkui('Tableau des scores', '(CallFunction|ScoresOn)', SCORES.format('false'), SCORES.format('true')),
        ui('Ouvrir le menu pause', PAUSE),
    ]),
    ('shop', 'Boutique', [                          # Tools/gameplay/s34_shop.py (money, items, vendors)
        pick('Argent', 'srv', 'GWDevMoney {}', [('+100 $', 100), ('+1000 $', 1000), ('Remettre à 0', 0)]),
        pick('Donner', 'srv', 'GWDevGive {}', [('Tout', 0), ('Fusil (1 balle)', 1), ('Bombe fumigène', 2), ('Lampe torche', 3),
                                              ('Gaz rétrécissant', 4), ('Piège', 5), ('Bombe', 6), ('Munitions tourelle', 7),
                                              ("Pistolet d'échange", 8), ('Pétard', 9), ('Lame secrète', 10), ('Mascarade', 14)]),
        srv('Inventaire : état (journal)', 'GWDevInvState'),
        srv('Aller à la boîte mystère', 'GWDevGoBox'),
        srv('Aller à un objet à voler', 'GWDevGoProp'),
        srv('Un corps à côté de moi (à fouiller)', 'GWDevKillNear'),
        srv('Kamikaze abattu à côté de moi (sa bombe)', 'GWDevKamikaze'),
        srv('Faire tomber le lustre du hall', 'GWDevChand'),
        srv('Piège qui saute sur moi', 'GWDevHurtSeeker'),
        srv('Robot tué par la mitrailleuse', 'GWDevRobotTurret'),
        srv('Aller à une alarme incendie', 'GWDevAlarmNear'),
        srv('Aller au post-it', 'GWDevPostIt'),
        ui('Ouvrir la boutique ici', SHOP_HERE.format(0)),
        ui('Ouvrir le marché noir ici', SHOP_HERE.format(1)),
        srv('Aller au bar (barman)', 'GWDevTeleport 4420 1440 130'),
        srv('Aller aux toilettes (junkie)', 'GWDevTeleport 260 2130 130'),
        srv('Aller voir un serveur', 'GWDevWaiter'),
        pick('Serveurs', 'srv', 'GWDevWaiters {}', [('Figer', 1), ('Me suivre', 2), ('Normal', 0)]),
        srv('Serveur : repartir (la boutique se ferme)', 'GWDevWaiterLeave'),
        srv('Aller à la bombe la plus proche', 'GWDevGoBomb'),
        srv('Bombes : exploser maintenant', 'GWDevBombNow'),
        srv('Fusil : se placer face au PNJ le plus proche', 'GWDevShopAim 0'),
    ]),
    ('sound', 'Son', [
        special('sound', 'Jouer un son'),
        special('sounds', 'Jouer tous les sons'),
        ui('Arrêter le son', '(Variables|Dev|SetAllOn false)\n    (CallFunction|StopSnd)\n    (CallFunction|Refresh)'),
        srv('Piano : vacarme maintenant', 'GWDevPiano'),
        srv('Piano : y aller', 'GWDevPianoGo'),
        srv('Piano : un PNJ s’en approche', 'GWDevNPCPiano'),
        # voice director (s39_voice_director.py): a panic of a given cause here, a conversation here, the bank's state
        pick('Voix : panique', 'srv', 'GWDevVoicePanic {}', [('Coup de feu', 1), ('Feu', 2), ('Explosion', 3), ('Panne', 4), ('Sans cause', 0)]),
        srv('Voix : conversation ici', 'GWDevVoiceChat'),
        srv('Voix : bilan', 'GWDevVoiceState'),
    ]),
]
assert max(len(e) for _, _, e in PAGES) <= ROW_POOL, 'raise ROW_POOL'
KEYS = [k for k, _, _ in PAGES]
ROWS = []                                          # (page index, line in page, entry): g = index in ROWS
for p, (_, _, entries) in enumerate(PAGES):
    for i, e in enumerate(entries):
        ROWS.append((p, i, e))
ROOT_N = len(PAGES[0][2])


# ---------------------------------------------------------------- input: F2 everywhere, navigation only while open
def action(name):
    pth = f'{INP}/{name}'
    a = unreal.load_asset(pth) if EAL.does_asset_exist(pth) else AT.create_asset(name, INP, unreal.InputAction, unreal.InputAction_Factory())
    EAL.save_loaded_asset(a, False)
    return a


def key(name):
    k = unreal.Key()
    k.set_editor_property('key_name', name)
    return k


ia_menu = action('IA_DevMenu')
for imc_path in ('/Game/GW/Input/IMC_GW', '/Game/GW/UI/Input/IMC_GW_Pause'):
    imc = unreal.load_asset(imc_path)
    if not any(m.get_editor_property('action') == ia_menu for m in imc.get_editor_property('default_key_mappings').get_editor_property('mappings')):
        imc.map_key(ia_menu, key('F2'))
        EAL.save_loaded_asset(imc, False)
NAV = {'IA_DevUp': ('Up', 'NumPadEight', 'DevUp'), 'IA_DevDown': ('Down', 'NumPadTwo', 'DevDown'),
       'IA_DevLeft': ('Left', 'NumPadFour', 'DevLeft'), 'IA_DevRight': ('Right', 'NumPadSix', 'DevRight'),
       'IA_DevAccept': ('Enter', 'NumPadFive', 'DevAccept'), 'IA_DevBack': ('BackSpace', 'NumPadZero', 'DevBack')}
imc_dev = unreal.load_asset(IMC_DEV.split('.')[0]) if EAL.does_asset_exist(IMC_DEV.split('.')[0]) else \
    AT.create_asset('IMC_GW_DevMenu', INP, unreal.InputMappingContext, unreal.InputMappingContext_Factory())
imc_dev.unmap_all()
for ia_name, (k1, k2, _) in NAV.items():
    a = action(ia_name)
    imc_dev.map_key(a, key(k1))
    imc_dev.map_key(a, key(k2))
EAL.save_loaded_asset(imc_dev, False)

# ---------------------------------------------------------------- signatures (widget, PC and game mode call each other)
pc = unreal.load_asset('/Game/GW/Blueprints/BP_GW_PlayerController')
gm = unreal.load_asset('/Game/GW/Blueprints/BP_GW_GameMode')
chc = unreal.load_asset('/Game/GW/Blueprints/BP_GW_Character').generated_class()
for v, t in (('DevOutfit', 'int'), ('DevTestStep', 'int'), ('DevTestOpen', 'bool'), ('DevTestPage', 'int'),
             ('DevBaseWalk', 'float'), ('DevBaseSprint', 'float'), ('DevCount', 'int')):
    ensure_var(pc, v, t, category='GW')
for f in ['DevFlagsPush', 'ToggleDevMenu', 'CloseDevMenu', 'DevTestTick', 'DevTestChars', 'UIMenuPressed'] + [v[2] for v in NAV.values()]:
    ensure_fn(pc, f)
ensure_fn(pc, 'DevPick', inputs=[('N', 'int')])
ensure_fn(pc, 'DevSetInput', inputs=[('On', 'bool')])
ensure_fn(pc, 'DevTestLog', inputs=[('St', 'int')])
ensure_fn(pc, 'DevServer', inputs=[('Cmd', 'string')])
ensure_fn(pc, 'DevBoth', inputs=[('Cmd', 'string')])
ensure_fn(pc, 'DevLog', inputs=[('Msg', 'string')])
ensure_fn(pc, 'DevOK', outputs=[('Ok', 'bool')], pure=True)
ensure_fn(pc, 'DevSpawnSelf', inputs=[('Seeker', 'bool')])
ensure_fn(pc, 'DevUnfreeze', inputs=[('Ch', chc)])
ensure_fn(pc, 'DevKillSelf', inputs=[('Ch', chc)])
ensure_fn(pc, 'DevUIQA', inputs=[('St', 'int')])     # -GWUIQA: interface screenshots and floating prompt checks
ensure_fn(pc, 'DevPromptLog', inputs=[('St', 'int')])
ensure_var(pc, 'DevQAW', obj_class=unreal.UserWidget, category='GW')
ensure_var(pc, 'DevRobotSpot', struct=unreal.Vector.static_struct(), category='GW')
ensure_var(pc, 'DevRobotTry', struct=unreal.Vector.static_struct(), category='GW')
ensure_fn(pc, 'DevEnsureAlive')                     # GWDevRobotTest: a ghost tester respawns first
EXEC = {'GWDevVoicePanic': [('C', 'int')], 'GWDevVoiceChat': [], 'GWDevVoiceState': [],   # s39 voice director
        'GWDevOutfit': [('Index', 'int')], 'GWDevGhost': [], 'GWDevRespawn': [], 'GWDevRole': [('R', 'int')],
        'GWDevSpeed': [('Pct', 'float')], 'GWDevHeal': [], 'GWDevTeleport': [('X', 'float'), ('Y', 'float'), ('Z', 'float')],
        'GWDevScore': [('D', 'int')], 'GWDevSolo': [('On', 'int')], 'GWDevAutoEnd': [('On', 'int')], 'GWDevStartRound': [],
        'GWDevHunt': [], 'GWDevEndRound': [('W', 'int')], 'GWDevLobby': [], 'GWDevClock': [('D', 'int')],
        'GWDevTimeScale': [('Pct', 'float')], 'GWDevNPCAdd': [('N', 'int')], 'GWDevNPCRemove': [('N', 'int')],
        'GWDevNPCFreeze': [('On', 'int')], 'GWDevNPCState': [], 'GWDevNPCBlock': [('On', 'int')], 'GWDevNPCKill': [], 'GWDevNPCOutfit': [('I', 'int')], 'GWDevAnnounce': [],
        'GWDevTestRound': [('R', 'int')], 'GWDevTestEnd': [],
        'GWDevEvent': [('Id', 'int')], 'GWDevEventStop': [], 'GWDevAutoEvents': [('On', 'int')],
        'GWDevEventEvery': [('S', 'float')], 'GWDevEventDur': [('S', 'float')],
        'GWDevZombieLife': [('S', 'float')], 'GWDevZombieBite': [('S', 'float')], 'GWDevRobotHP': [('V', 'float')], 'GWDevRobotDmg': [('V', 'float')], 'GWDevMoveTurn': [('V', 'float')], 'GWDevBladeCD': [('V', 'float')], 'GWDevTrapDmg': [('V', 'float')], 'GWDevTrapNPC': [('V', 'int')], 'GWDevRobotHit': [], 'GWDevGasScale': [('V', 'float')],
        'GWDevPiano': [], 'GWDevNPCPiano': [], 'GWDevTurretGo': [], 'GWDevTurretAmmo': [], 'GWDevTurretTarget': [], 'GWDevDanceNow': [], 'GWDevBarNow': [], 'GWDevEventGo': [], 'GWDevQuickTest': [('R', 'int')],
        'GWDevRobotTest': [], 'GWDevRobotFace': [], 'GWDevSync': [], 'GWDevKeyTest': [('Mode', 'int')], 'GWDevPianoGo': []}
# shop (bodies in Tools/gameplay/s34_shop.py)
EXEC.update({'GWDevMoney': [('Amount', 'int')], 'GWDevGive': [('Id', 'int')], 'GWDevShopHere': [('On', 'int')], 'GWDevBombNow': [],
             'GWDevWaiter': [], 'GWDevShopAim': [('Mode', 'int')], 'GWDevGoBomb': [], 'GWDevWaiters': [('Mode', 'int')],
             'GWDevWaiterLeave': []})
ensure_fn(pc, 'OpenShopHere', inputs=[('Kind', 'int')])          # body: s34_shop.py
ensure_fn(pc, 'DevTestFlags', inputs=[('On', 'bool')])
gs_bp = unreal.load_asset('/Game/GW/Blueprints/BP_GW_GameState')
if DO_PC:
    ensure_var(gs_bp, 'TestRound', 'bool', rep=unreal.BlueprintVariableReplication.REPLICATED, category='GW')
    ensure_var(gs_bp, 'DevFlags', 'int', rep=unreal.BlueprintVariableReplication.REPLICATED, category='GW')
    compile_bp(gs_bp, quiet=True)
    save(gs_bp)
for f, ins in EXEC.items():
    ensure_fn(pc, f, inputs=ins, exec_fn=True)
if DO_PC:
    compile_bp(pc, quiet=True)
    unreal.get_default_object(pc.generated_class()).set_editor_property('DevOutfit', -1)
ensure_var(gm, 'DevNoWin', 'bool', category='GW')
ensure_var(gm, 'DevFrozen', 'bool', category='GW')
ensure_fn(gm, 'ApplyDevOutfit', inputs=[('PC', unreal.PlayerController), ('Ch', chc)])
ensure_fn(gm, 'DevKillNearestNPC', inputs=[('Loc', unreal.Vector.static_struct())])
if DO_PC:
    compile_bp(gm, quiet=True)
_g = gw_lib.get_graph(gm, 'DevKillNearestNPC')
if 'BestD' not in BT.list_variables(gm, _g):
    BT.add_variable(gm, 'BestD', 'float', graph=_g)
if 'BestT' not in BT.list_variables(gm, _g):
    BT.add_object_variable(gm, 'BestT', chc, graph=_g)

# ---------------------------------------------------------------- widget tree (drops earlier versions' graphs)
W = get_or_create('WBP_DevMenu')
UI_CODES = []                                      # (id, DSL): ui entries, ui picks and checkui, run by UiCode
RK = dict(page=0, srv=1, pick_srv=2, pick_both=3, pick_local=4, pick_ui=5, local=6, ui=7, close=8, cast=9, castnpc=10, sound=11,
          sounds=12, check=13, checkui=14)
D = dict(RowKind=[], RowLabel=[], RowCmd=[], RowArg=[], OptFirst=[], OptN=[], OptText=[], OptArg=[], PageFirst=[], PageCount=[],
         PageTitle=[], BackSel=[])
CHECK_READS = []                                   # (g, DSL bool)
_root_sel = {e['key']: i for i, e in enumerate(PAGES[0][2]) if e['kind'] == 'page'}
_g = 0
for q, (pk, title, entries) in enumerate(PAGES):
    D['PageFirst'].append(_g)
    D['PageCount'].append(len(entries))
    D['PageTitle'].append('' if q == 0 else title.upper())
    D['BackSel'].append(_root_sel.get(pk, -1))
    for e in entries:
        k = e['kind']
        rk, cmd, arg, of, on = k, '', 0, len(D['OptText']), 0
        if k == 'page':
            arg = KEYS.index(e['key'])
        elif k in ('srv', 'local'):
            cmd = e['cmd']
        elif k == 'ui':
            arg = len(UI_CODES)
            UI_CODES.append(e['code'])
        elif k == 'pick':
            rk = 'pick_' + e['how']
            on = len(e['opts'])
            if e['how'] == 'ui':
                arg = len(UI_CODES)
            else:
                cmd = e['cmd']
            for disp, a_ in e['opts']:
                D['OptText'].append(disp)
                D['OptArg'].append(str(a_))
                if e['how'] == 'ui':
                    UI_CODES.append(e['cmd'].format(a_))
        elif k == 'check':
            cmd = e['cmd']
            CHECK_READS.append((_g, f'(CallFunction|Flag :B {e["flag"]})'))
        elif k == 'checkui':
            arg = len(UI_CODES)
            UI_CODES += [e['off'], e['on']]
            CHECK_READS.append((_g, e['read']))
        D['RowKind'].append(RK[rk])
        D['RowLabel'].append(e['label'])
        D['RowCmd'].append(cmd)
        D['RowArg'].append(arg)
        D['OptFirst'].append(of)
        D['OptN'].append(on)
        _g += 1
NROWS = _g
print('rows', NROWS, 'ui codes', len(UI_CODES))


def push_data():
    c = unreal.get_default_object(W.generated_class())
    for n, v in D.items():
        c.set_editor_property(n, v)
    c.set_editor_property('Vals', [0] * NROWS)


OV = lambda n: f'(Variables|WBP_DevMenu|Get{n})'
AG = lambda arr, i: f'(Utilities|Array|Get(acopy) (Variables|Dev|Get{arr}) {i})'
LEN = '(Utilities|Array|Length (Variables|Dev|GetNames))'
SNDS = '(Variables|Dev|GetSounds)'
NS = f'(Utilities|Array|Length {SNDS})'
CLICK = '(Audio|PlaySound2D :Sound "/Game/GW/Audio/S_UI_Click.S_UI_Click" :VolumeMultiplier 0.6)'
HOVER = '(Audio|PlaySound2D :Sound "/Game/GW/Audio/S_UI_Hover.S_UI_Hover" :VolumeMultiplier 0.5)'


def unbalanced(code):
    """Generated DSL sanity check: parenthesis depth outside string literals (returns the final depth, 0 = balanced)."""
    depth, quoted = 0, False
    for ch in code:
        if ch == '"':
            quoted = not quoted
        elif not quoted:
            depth += (ch == '(') - (ch == ')')
            if depth < 0:
                return depth
    return depth


def write_all(bp, graphs):
    bad = {n: unbalanced(c) for n, c in graphs.items() if unbalanced(c)}
    assert not bad, f'unbalanced generated DSL: {bad}'
    for n, c in graphs.items():
        write(bp, n, c, compile_after=False)


def say(msg):
    """Status line (also logged, for -GWDevTest). A literal is used as is; an expression is bound once."""
    head, ref = ('', msg) if msg.startswith('"') else (f'(bind said {msg})\n    ', 'said')
    return (f'{head}(Widget|SetText(Text) :self {OV("Status")} :InText (Utilities|Text|ToText(String) {ref}))\n'
            f'    (Development|PrintString :InString (cat "GW devmenu: " {ref}) :bPrintToScreen false)')


def to_pc(fn, cmd):
    return f"""(bind pc {PCCAST}
      (:then (GW|Call|BP_GW_PlayerController|{fn} :self pc :Cmd {cmd}))
      (:CastFailed))"""


if 'data' in PARTS:
    push_data()
    save(W)
if DO_W:
    W_FUNCS = ['SetupDev', 'SyncChar', 'CloseDev', 'Refresh', 'Accept', 'Move', 'Change', 'Back', 'OpenPage', 'DevTick',
               'PlaySnd', 'StopSnd', 'SoundTick', 'UiCode', 'CheckVal', 'Flag', 'HudOn', 'ScoresOn', 'RowValue', 'AddRow']
    for g in gw_lib.graph_names(W):
        if g not in W_FUNCS + ['EventGraph']:
            BT.remove_function_graph(W, g)
    for v in ('Btns', 'BtnHov', 'Closing', 'T'):
        if v in [str(x) for x in BT.list_variables(W)]:
            BT.remove_variable(W, v)
    uilib.clean_graph(W, 'EventGraph')
    clear_tree(W)
    add(W, unreal.CanvasPanel, 'Root')
    ps = add(W, unreal.SizeBox, 'PanelSize', 'Root', var=True); size_box(ps, w=480)
    canvas(ps, ((0, 0), (0, 0)), (0, 0), pos=(30, 24), auto=True, z=5)
    pn = add(W, unreal.Border, 'Panel', 'PanelSize')
    pn.widget.set_editor_property('background', brush(None, (8, 8), 'image', tint=(0.012, 0.010, 0.008, 0.88)))
    pn.widget.set_editor_property('padding', unreal.Margin(0, 0, 0, 10))
    add(W, unreal.VerticalBox, 'Body', 'Panel')
    hd = add(W, unreal.Border, 'Head', 'Body'); box_slot(hd, (0, 0, 0, 6), H.H_ALIGN_FILL)
    hd.widget.set_editor_property('background', brush(None, (8, 8), 'image', tint=(0.62, 0.42, 0.13, 1)))
    hd.widget.set_editor_property('padding', unreal.Margin(16, 8, 16, 6))
    hh = add(W, unreal.HorizontalBox, 'HeadH', 'Head')
    ht = add(W, unreal.TextBlock, 'HeadText', 'HeadH'); text(ht, 'MENU DÉVELOPPEUR', 'Display', 'Regular', 24, INK, spacing=300, shadow=False)
    box_slot(ht, (0, 0, 0, 0), H.H_ALIGN_LEFT, VA.V_ALIGN_CENTER, fill=1.0)
    cr = add(W, unreal.TextBlock, 'Crumb', 'HeadH', var=True); text(cr, '', 'Sans', 'SemiBold', 17, INK, shadow=False, just='right')
    box_slot(cr, (0, 0, 0, 0), H.H_ALIGN_RIGHT, VA.V_ALIGN_CENTER)
    for r in range(ROW_POOL):
        sb = add(W, unreal.SizeBox, f'R{r}', 'Body', var=True); size_box(sb, h=36); box_slot(sb, (0, 0, 0, 0), H.H_ALIGN_FILL)
        ov = add(W, unreal.Overlay, f'R{r}O', f'R{r}')
        hi = add(W, unreal.Image, f'Hi{r}', f'R{r}O', var=True)
        hi.widget.set_editor_property('brush', brush(None, (8, 8), 'image', tint=(0.92, 0.73, 0.32, 0.26))); overlay_slot(hi)
        vis(hi, V.COLLAPSED)
        hb = add(W, unreal.HorizontalBox, f'R{r}H', f'R{r}O'); overlay_slot(hb, pad=(16, 0, 16, 0))
        lb = add(W, unreal.TextBlock, f'Label{r}', f'R{r}H', var=True); text(lb, '', 'Sans', 'Regular', 18, IVORY)
        box_slot(lb, (0, 0, 8, 0), H.H_ALIGN_LEFT, VA.V_ALIGN_CENTER, fill=1.0)
        vt = add(W, unreal.TextBlock, f'Value{r}', f'R{r}H', var=True); text(vt, '', 'Sans', 'SemiBold', 18, GOLD_HI, just='right')
        box_slot(vt, (0, 0, 0, 0), H.H_ALIGN_RIGHT, VA.V_ALIGN_CENTER)
        vis(sb, V.COLLAPSED)
    st = add(W, unreal.TextBlock, 'Status', 'Body', var=True)
    text(st, '', 'Sans', 'Regular', 16, IVORY, wrap=440); box_slot(st, (16, 8, 16, 0), H.H_ALIGN_LEFT)
    nt = add(W, unreal.TextBlock, 'Note', 'Body', var=True)
    text(nt, '', 'Sans', 'Regular', 15, (0.95, 0.55, 0.45, 1), wrap=440); box_slot(nt, (16, 4, 16, 0), H.H_ALIGN_LEFT)
    ft = add(W, unreal.TextBlock, 'Keys', 'Body')
    text(ft, 'Haut / Bas : choisir · Gauche / Droite : changer\nEntrée : valider · Retour : page précédente · F2 : fermer', 'Sans', 'Regular', 13, IVORY_DIM)
    box_slot(ft, (16, 8, 16, 0), H.H_ALIGN_LEFT)
    compile_widget(W)

    # ------------------------------------------------------------ widget graph
    for v, t in (('Page', 'int'), ('PageN', 'int'), ('Sel', 'int'), ('Cur', 'int'), ('CurK', 'int'), ('CharIdx', 'int'), ('NpcIdx', 'int'), ('SndIdx', 'int'),
                 ('AllIdx', 'int'), ('Shut', 'bool'), ('AllOn', 'bool'), ('Busy', 'bool'), ('Age', 'float'), ('AllT', 'float'), ('RefreshT', 'float'), ('SyncT', 'float')):
        ensure_var(W, v, t, category='Dev')
    ensure_var(W, 'Names', 'string', array=True, category='Dev')
    ensure_var(W, 'Vals', 'int', array=True, category='Dev')
    for n in ('RowKind', 'RowArg', 'OptFirst', 'OptN', 'PageFirst', 'PageCount', 'BackSel'):
        ensure_var(W, n, 'int', array=True, category='Dev')
    for n in ('RowLabel', 'RowCmd', 'OptText', 'OptArg', 'PageTitle'):
        ensure_var(W, n, 'string', array=True, category='Dev')
    ensure_var(W, 'RowBox', obj_class=unreal.Widget, array=True, category='Dev')
    ensure_var(W, 'RowHi', obj_class=unreal.Widget, array=True, category='Dev')
    ensure_var(W, 'RowLbl', obj_class=unreal.TextBlock, array=True, category='Dev')
    ensure_var(W, 'RowVal', obj_class=unreal.TextBlock, array=True, category='Dev')
    ensure_var(W, 'Sounds', obj_class=unreal.SoundBase, array=True, category='Dev')
    ensure_var(W, 'Comp', obj_class=unreal.AudioComponent, category='Dev')
    for f in ('SetupDev', 'SyncChar', 'CloseDev', 'Refresh', 'Accept', 'Back', 'StopSnd'):
        ensure_fn(W, f)
    for f in ('Move', 'Change'):
        ensure_fn(W, f, inputs=[('D', 'int')])
    ensure_fn(W, 'OpenPage', inputs=[('P', 'int'), ('N', 'int'), ('S', 'int')])
    for f in ('DevTick', 'SoundTick'):
        ensure_fn(W, f, inputs=[('Dt', 'float')])
    ensure_fn(W, 'PlaySnd', inputs=[('I', 'int')])
    ensure_fn(W, 'UiCode', inputs=[('Id', 'int')])
    ensure_fn(W, 'RowValue', inputs=[('K', 'int'), ('G', 'int')])
    ensure_fn(W, 'CheckVal', inputs=[('G', 'int')], outputs=[('On', 'bool')], pure=True)
    ensure_fn(W, 'Flag', inputs=[('B', 'int')], outputs=[('On', 'bool')], pure=True)
    ensure_fn(W, 'HudOn', outputs=[('On', 'bool')], pure=True)
    ensure_fn(W, 'ScoresOn', outputs=[('On', 'bool')], pure=True)
    compile_bp(W, quiet=True)
    _ar = unreal.AssetRegistryHelpers.get_asset_registry()
    SOUNDS = sorted((a for a in (unreal.load_asset(str(d.package_name)) for d in _ar.get_assets_by_path('/Game/GW/Audio', recursive=True))
                     if isinstance(a, unreal.SoundBase)), key=lambda a: a.get_name())
    unreal.get_default_object(W.generated_class()).set_editor_property('Sounds', SOUNDS)
    push_data()
    print('sounds', len(SOUNDS), 'rows', NROWS)
    CUR = '(Variables|Dev|GetCur)'
    LABEL = AG('RowLabel', CUR)
    CMDARG = f'(Utilities|String|Replace :SourceString {AG("RowCmd", CUR)} :From "{{}}" :To {AG("OptArg", "(+ " + AG("OptFirst", CUR) + " " + AG("Vals", CUR) + ")")})'
    PICKSAY = say(f'(cat {LABEL} " : " {AG("OptText", "(+ " + AG("OptFirst", CUR) + " " + AG("Vals", CUR) + ")")})')
    CHECKSAY = say(f'(cat {LABEL} (select (CallFunction|CheckVal :G {CUR}) " : désactivé" " : activé"))')
    G = {
        'SetupDev': '\n(fn SetupDev ()\n' + '\n'.join(
            f'  (Utilities|Array|Add :TargetArray (Variables|Dev|GetRowBox) :NewItem {OV(f"R{r}")})\n'
            f'  (Utilities|Array|Add :TargetArray (Variables|Dev|GetRowHi) :NewItem {OV(f"Hi{r}")})\n'
            f'  (Utilities|Array|Add :TargetArray (Variables|Dev|GetRowLbl) :NewItem {OV(f"Label{r}")})\n'
            f'  (Utilities|Array|Add :TargetArray (Variables|Dev|GetRowVal) :NewItem {OV(f"Value{r}")})' for r in range(ROW_POOL)) + f"""
  (Variables|Dev|SetShut false)
  (Variables|Dev|SetAge 0.0)
  (Variables|Dev|SetCharIdx 0)
  (Variables|Dev|SetNpcIdx 0)
  (Variables|Dev|SetSyncT 1.0)
  (bind all (Actor|GetAllActorsOfClass :ActorClass {CHAR}))
  (if (> (Utilities|Array|Length all) 0)
    (Variables|Dev|SetNames (GW|Get|BP_GW_Character|GenNames :self (Utilities|Array|Get(acopy) all 0))))
  (Audio|PlaySound2D :Sound "/Game/GW/Audio/S_UI_Card.S_UI_Card" :VolumeMultiplier 0.6)
  (CallFunction|OpenPage :P 0 :N {AG('PageCount', 0)} :S 0)
  (CallFunction|SyncChar))
""",
        # start on what we wear now (a seeker, or the detective look, sits after the cast)
        'SyncChar': f"""
(fn SyncChar ()
  (bind ch (Utilities|Casting|CastToBP_GW_Character (Player|GetOwningPlayerPawn))
    (:then
      (bind oi (GW|Get|BP_GW_Character|OutfitIndex :self ch))
      (Variables|Dev|SetCharIdx (select (or (GW|Get|BP_GW_Character|IsSeeker :self ch) (>= oi {LEN})) {LEN} (Math|Integer|Max(Integer) oi 0)))
      (CallFunction|Refresh))
    (:CastFailed)))
""",
        'OpenPage': """
(fn OpenPage (P N S)
  (Variables|Dev|SetPage P)
  (Variables|Dev|SetPageN N)
  (Variables|Dev|SetSel S)
  (CallFunction|Refresh))
""",
        # bit B of the replicated DevFlags (the server's real values, GWDevSync)
        'Flag': """
(fn Flag (B)
  (bind s (Utilities|Casting|CastToBP_GW_GameState (Game|GetGameState))
    (:then (return (== (% (/ (GW|Get|BP_GW_GameState|DevFlags :self s) B) 2) 1)))
    (:CastFailed (return false))))
""",
        'HudOn': f"""
(fn HudOn ()
  (bind pc {PCCAST}
    (:then
      (bind hud (GW|Get|BP_GW_PlayerController|HUDWidget :self pc))
      (if ({ISVALID} :Object hud)
        (return (Widget|IsVisible :self hud)))
      (return false))
    (:CastFailed (return false))))
""",
        'ScoresOn': f"""
(fn ScoresOn ()
  (bind pc {PCCAST}
    (:then (return (GW|Get|BP_GW_PlayerController|ShowScores :self pc)))
    (:CastFailed (return false))))
""",
        'CheckVal': '(fn CheckVal (G)\n' + '\n'.join(f'  (if (== G {g})\n    (return {r}))' for g, r in CHECK_READS) + '\n  (return false))\n',
        'RowValue': f"""
(fn RowValue (K G)
  (bind kd {AG('RowKind', 'G')})
  (bind vb {AG('RowVal', 'K')})
  (Widget|SetText(Text) :self vb :InText (Utilities|Text|ToText(String) ""))
  (if (== kd {RK['page']})
    (Widget|SetText(Text) :self vb :InText (Utilities|Text|ToText(String) "›")))
  (if (and (>= kd {RK['pick_srv']}) (<= kd {RK['pick_ui']}))
    (Widget|SetText(Text) :self vb :InText (Utilities|Text|ToText(String) (cat "<  " {AG('OptText', '(+ ' + AG('OptFirst', 'G') + ' ' + AG('Vals', 'G') + ')')} "  >"))))
  (if (or (== kd {RK['check']}) (== kd {RK['checkui']}))
    (Widget|SetText(Text) :self vb :InText (Utilities|Text|ToText(String) (select (CallFunction|CheckVal :G G) "[x]" "[ ]"))))
  (if (== kd {RK['cast']})
    (Widget|SetText(Text) :self vb :InText (Utilities|Text|ToText(String) (select (< (Variables|Dev|GetCharIdx) {LEN}) (cat "<  " (Utilities|Array|Get(acopy) (Variables|Dev|GetNames) (Math|Integer|Min(Integer) (Variables|Dev|GetCharIdx) (Math|Integer|Max(Integer) (- {LEN} 1) 0))) "  >") "<  Le détective  >"))))
  (if (and (== kd {RK['castnpc']}) (> {LEN} 0))
    (Widget|SetText(Text) :self vb :InText (Utilities|Text|ToText(String) (select (< (Variables|Dev|GetNpcIdx) {LEN}) (cat "<  " (Utilities|Array|Get(acopy) (Variables|Dev|GetNames) (Math|Integer|Min(Integer) (Variables|Dev|GetNpcIdx) (- {LEN} 1))) "  >") "<  Au hasard  >"))))
  (if (and (== kd {RK['sound']}) (> {NS} 0))
    (Widget|SetText(Text) :self vb :InText (Utilities|Text|ToText(String) (cat "<  " (Utilities|GetDisplayName :Object (Utilities|Array|Get(acopy) {SNDS} (Variables|Dev|GetSndIdx))) "  >"))))
  (if (== kd {RK['sounds']})
    (Widget|SetText(Text) :self vb :InText (Utilities|Text|ToText(String) (select (Variables|Dev|GetAllOn) (cat "<  " (+ (Variables|Dev|GetAllIdx) 1) " / " {NS} "  >") (cat {NS} " sons"))))))
""",
        'Refresh': f"""
(fn Refresh ()
  (bind pg (Variables|Dev|GetPage))
  (bind first {AG('PageFirst', 'pg')})
  (bind cnt {AG('PageCount', 'pg')})
  (Widget|SetText(Text) :self {OV('Crumb')} :InText (Utilities|Text|ToText(String) {AG('PageTitle', 'pg')}))
  (for r (range {ROW_POOL})
    (if (< r cnt)
      (Widget|SetVisibility :self {AG('RowBox', 'r')} :InVisibility "SelfHitTestInvisible")
      (if (== r (Variables|Dev|GetSel))
        (Widget|SetVisibility :self {AG('RowHi', 'r')} :InVisibility "HitTestInvisible")
        (else
          (Widget|SetVisibility :self {AG('RowHi', 'r')} :InVisibility "Collapsed")))
      (Widget|SetText(Text) :self {AG('RowLbl', 'r')} :InText (Utilities|Text|ToText(String) {AG('RowLabel', '(+ first r)')}))
      (CallFunction|RowValue :K r :G (+ first r))
      (else
        (Widget|SetVisibility :self {AG('RowBox', 'r')} :InVisibility "Collapsed")))))
""",
        'Move': f"""
(fn Move (D)
  (Variables|Dev|SetSel (% (+ (+ (Variables|Dev|GetSel) D) (Variables|Dev|GetPageN)) (Math|Integer|Max(Integer) (Variables|Dev|GetPageN) 1)))
  {HOVER}
  (CallFunction|Refresh))
""",
        'UiCode': '(fn UiCode (Id)\n' + '\n'.join(f'  (if (== Id {i})\n    {c})' for i, c in enumerate(UI_CODES)) + ')\n',
        # Accept / Change act on the line chosen when they start (Cur, CurK): an action may open a page and change Page / Sel
        'Accept': f"""
(fn Accept ()
  (Variables|Dev|SetCur (+ {AG('PageFirst', '(Variables|Dev|GetPage)')} (Variables|Dev|GetSel)))
  (Variables|Dev|SetCurK {AG('RowKind', CUR)})
  (bind k (Variables|Dev|GetCurK))
  (if (!= k {RK['close']})
    {CLICK})
  (if (== k {RK['page']})
    (CallFunction|OpenPage :P {AG('RowArg', CUR)} :N {AG('PageCount', AG('RowArg', CUR))} :S 0))
  (if (== k {RK['close']})
    (CallFunction|CloseDev))
  (if (== k {RK['srv']})
    {say(f'(cat {LABEL} " : envoyé")')}
    {to_pc('DevServer', AG('RowCmd', CUR))})
  (if (== k {RK['local']})
    (Development|ExecuteConsoleCommand :Command {AG('RowCmd', CUR)} :SpecificPlayer (Widget|GetOwningPlayer))
    {say(LABEL)})
  (if (== k {RK['ui']})
    (CallFunction|UiCode :Id {AG('RowArg', CUR)}))
  (if (== k {RK['pick_srv']})
    {PICKSAY}
    {to_pc('DevServer', CMDARG)})
  (if (== k {RK['pick_both']})
    {PICKSAY}
    {to_pc('DevBoth', CMDARG)})
  (if (== k {RK['pick_local']})
    {PICKSAY}
    (Development|ExecuteConsoleCommand :Command {CMDARG} :SpecificPlayer (Widget|GetOwningPlayer)))
  (if (== k {RK['pick_ui']})
    {PICKSAY}
    (CallFunction|UiCode :Id (+ {AG('RowArg', CUR)} {AG('Vals', CUR)})))
  (if (== k {RK['check']})
    {CHECKSAY}
    {to_pc('DevServer', f'(Utilities|String|Replace :SourceString {AG("RowCmd", CUR)} :From "{{}}" :To (select (CallFunction|CheckVal :G {CUR}) "0" "1"))')})
  (if (== k {RK['checkui']})
    {CHECKSAY}
    (CallFunction|UiCode :Id (+ {AG('RowArg', CUR)} (select (CallFunction|CheckVal :G {CUR}) 0 1))))
  (if (== k {RK['cast']})
    (bind ci (Variables|Dev|GetCharIdx))
    (if (< ci {LEN})
      {say('(cat "Personnage : " (Utilities|Array|Get(acopy) (Variables|Dev|GetNames) ci))')}
      (else
        {say('"Personnage : le détective"')}))
    (bind pc {PCCAST}
      (:then (GW|Call|BP_GW_PlayerController|DevPick :self pc :N (select (< ci {LEN}) ci 32)))
      (:CastFailed)))
  (if (== k {RK['castnpc']})
    (bind ni (Variables|Dev|GetNpcIdx))
    {say('"PNJ habillés"')}
    {to_pc('DevServer', f'(cat "GWDevNPCOutfit " (select (< ni {LEN}) ni -1))')})
  (if (== k {RK['sound']})
    (CallFunction|PlaySnd :I (Variables|Dev|GetSndIdx)))
  (if (== k {RK['sounds']})
    (if (Variables|Dev|GetAllOn)
      (Variables|Dev|SetAllOn false)
      (CallFunction|StopSnd)
      {say('"Lecture de tous les sons arrêtée."')}
      (else
        (Variables|Dev|SetAllOn true)
        (Variables|Dev|SetAllIdx 0)
        (CallFunction|PlaySnd :I 0)))
    (CallFunction|Refresh))
  ; the [x] of a local check changes at once; a server one when the replicated flags arrive (DevTick refreshes)
  (if (!= k {RK['close']})
    (CallFunction|Refresh)))
""",
        'Change': f"""
(fn Change (D)
  (Variables|Dev|SetCur (+ {AG('PageFirst', '(Variables|Dev|GetPage)')} (Variables|Dev|GetSel)))
  (bind k {AG('RowKind', CUR)})
  (if (and (>= k {RK['pick_srv']}) (<= k {RK['pick_ui']}))
    (bind n {AG('OptN', CUR)})
    (Utilities|Array|SetArrayElem :TargetArray (Variables|Dev|GetVals) :Index {CUR} :Item (% (+ (+ {AG('Vals', CUR)} D) n) n))
    {HOVER})
  (if (or (== k {RK['check']}) (== k {RK['checkui']}))
    (CallFunction|Accept)
    (return))
  (if (== k {RK['cast']})
    (Variables|Dev|SetCharIdx (% (+ (+ (Variables|Dev|GetCharIdx) D) (+ {LEN} 1)) (+ {LEN} 1)))
    {HOVER})
  (if (== k {RK['castnpc']})
    (Variables|Dev|SetNpcIdx (% (+ (+ (Variables|Dev|GetNpcIdx) D) (+ {LEN} 1)) (+ {LEN} 1)))
    {HOVER})
  (if (and (== k {RK['sound']}) (> {NS} 0))
    (Variables|Dev|SetSndIdx (% (+ (+ (Variables|Dev|GetSndIdx) D) {NS}) {NS})))
  ; while "play all" runs, Left / Right skip back / ahead
  (if (and (== k {RK['sounds']}) (Variables|Dev|GetAllOn))
    (bind nx (Math|Integer|Clamp(Integer) :Value (+ (Variables|Dev|GetAllIdx) D) :Min 0 :Max (- {NS} 1)))
    (Variables|Dev|SetAllIdx nx)
    (CallFunction|PlaySnd :I nx))
  (CallFunction|Refresh))
""",
        'Back': f"""
(fn Back ()
  (bind bs {AG('BackSel', '(Variables|Dev|GetPage)')})
  (if (>= bs 0)
    (CallFunction|OpenPage :P 0 :N {AG('PageCount', 0)} :S bs)
    (return))
  (CallFunction|CloseDev))
""",
        'PlaySnd': f"""
(fn PlaySnd (I)
  (CallFunction|StopSnd)
  (Variables|Dev|SetAllT 0.0)
  (if (and (>= I 0) (< I {NS}))
    (bind s (Utilities|Array|Get(acopy) {SNDS} I))
    (Variables|Dev|SetComp (Audio|SpawnSound2D :Sound s :VolumeMultiplier 1.0 :PitchMultiplier 1.0 :bAutoDestroy true))
    {say('(cat "Son : " (Utilities|GetDisplayName :Object s))')}))
""",
        'StopSnd': f"""
(fn StopSnd ()
  (bind c (Variables|Dev|GetComp))
  (if ({ISVALID} :Object c)
    (Audio|Components|Audio|Stop :self c)))
""",
        'SoundTick': f"""
(fn SoundTick (Dt)
  (if (not (Variables|Dev|GetAllOn))
    (return))
  (Variables|Dev|SetAllT (+ (Variables|Dev|GetAllT) Dt))
  (Variables|Dev|SetBusy false)
  (bind c (Variables|Dev|GetComp))
  (if ({ISVALID} :Object c)
    (Variables|Dev|SetBusy (Audio|Components|Audio|IsPlaying :self c)))
  (if (or (and (not (Variables|Dev|GetBusy)) (> (Variables|Dev|GetAllT) 0.4)) (> (Variables|Dev|GetAllT) {ALL_MAX_S}))
    (bind nx (+ (Variables|Dev|GetAllIdx) 1))
    (if (>= nx {NS})
      (Variables|Dev|SetAllOn false)
      (CallFunction|StopSnd)
      {say(f'(cat "Tous les sons ont été joués (" {NS} ").")')}
      (else
        (Variables|Dev|SetAllIdx nx)
        (CallFunction|PlaySnd :I nx)))
    (CallFunction|Refresh)))
""",
        'CloseDev': f"""
(fn CloseDev ()
  (if (Variables|Dev|GetShut)
    (return))
  (Variables|Dev|SetShut true)
  (Variables|Dev|SetAllOn false)
  (CallFunction|StopSnd)
  (Audio|PlaySound2D :Sound "/Game/GW/Audio/S_UI_Back.S_UI_Back" :VolumeMultiplier 0.6)
  (Widget|RemovefromParent :self self)
  (bind pc {PCCAST}
    (:then (GW|Call|BP_GW_PlayerController|DevSetInput :self pc :On false))
    (:CastFailed)))
""",
        # keeps the [x] / [ ] true while the menu is open: lines 4 times a second, the server's flags asked for once a second
        'DevTick': f"""
(fn DevTick (Dt)
  (Variables|Dev|SetAge (+ (Variables|Dev|GetAge) Dt))
  (Widget|SetRenderOpacity :self {OV('PanelSize')} :InOpacity (Math|Float|Min(Float) (/ (Variables|Dev|GetAge) 0.15) 1.0))
  (CallFunction|SoundTick :Dt Dt)
  (Variables|Dev|SetRefreshT (+ (Variables|Dev|GetRefreshT) Dt))
  (if (> (Variables|Dev|GetRefreshT) 0.25)
    (Variables|Dev|SetRefreshT 0.0)
    (CallFunction|Refresh))
  (Variables|Dev|SetSyncT (+ (Variables|Dev|GetSyncT) Dt))
  (if (> (Variables|Dev|GetSyncT) 1.0)
    (Variables|Dev|SetSyncT 0.0)
    {to_pc('DevServer', '"GWDevSync"')})
  (Widget|SetText(Text) :self {OV('Note')} :InText (Utilities|Text|ToText(String) (select (Networking|HasAuthority :self (Widget|GetOwningPlayer)) "" "Client : le serveur n’accepte ces commandes que si l’hôte a lancé le jeu avec -GWDev."))))
""",
        'EventGraph': """
(event UserInterface|EventConstruct
  (CallFunction|SetupDev))

(event UserInterface|EventTick (MyGeometry InDeltaTime)
  (CallFunction|DevTick :Dt InDeltaTime))
""",
    }
    write_all(W, G)
    compile_bp(W)
    print('WBP_DevMenu', node_problems(W))
    compile_widget(W)

# ---------------------------------------------------------------- player controller: menu plumbing
ensure_var(pc, 'DevMenuW', obj_class=W.generated_class(), category='GW')
compile_bp(pc, quiet=True)
OPEN = f'''(bind w (Variables|GW|GetDevMenuW))
  (if ({ISVALID} :Object w)
    (if (Appearance|IsinViewport :self w)'''
GMC = '(Utilities|Casting|CastToBP_GW_GameMode (Game|GetGameMode))'
GSC = '(Utilities|Casting|CastToBP_GW_GameState (Game|GetGameState))'
PSC = '(Utilities|Casting|CastToBP_GW_PlayerState (GW|Get|/Script/Engine.Controller|PlayerState))'
MYCH = '(Utilities|Casting|CastToBP_GW_Character (Pawn|GetControlledPawn :self self))'


def gate(name):
    return f'''  (if (not (CallFunction|DevOK))
    (Development|PrintString :InString (cat "GW: dev {name} refused for " (PlayerState|GetPlayerName :self (GW|Get|/Script/Engine.Controller|PlayerState)) " (server not started with -GWDev)") :bPrintToScreen false)
    (return))'''


def on_gm(body):
    return f'''  (bind gm {GMC}
    (:then
{body})
    (:CastFailed))'''


UISHOT = '(Development|ExecuteConsoleCommand :Command "Shot showui" :SpecificPlayer self)'
PCG = {
    'ToggleDevMenu': f'''
(fn ToggleDevMenu ()
  {OPEN}
      (CallFunction|CloseDevMenu)
      (return)))
  ; the pause menu holds the UI input mode: close it first (HUD.TogglePause closes it when it is up)
  (bind hud (Variables|GW|GetHUDWidget))
  (if ({ISVALID} :Object hud)
    (bind pw (GW|Get|{HUD}|PauseW :self hud))
    (if ({ISVALID} :Object pw)
      (if (Appearance|IsinViewport :self pw)
        (GW|Call|{HUD}|TogglePause :self hud))))
  (bind nw (UserInterface|CreateWidget :Class "{DM}" :OwningPlayer self))
  (Variables|GW|SetDevMenuW nw)
  (UserInterface|Viewport|AddtoViewport :self nw :ZOrder 55)
  (CallFunction|DevSetInput :On true))
''',
    'DevSetInput': f'''
(fn DevSetInput (On)
  (bind sub (LocalPlayerSubsystems|GetEnhancedInputLocalPlayerSubsystem))
  (if On
    (Input|AddMappingContext :self sub :MappingContext "{IMC_DEV}" :Priority 10)
    (else
      (Input|RemoveMappingContext :self sub :MappingContext "{IMC_DEV}"))))
''',
    'CloseDevMenu': f'''
(fn CloseDevMenu ()
  (bind w (Variables|GW|GetDevMenuW))
  (if ({ISVALID} :Object w)
    (GW|Call|{DM}|CloseDev :self w)))
''',
    # Esc: closes the dev menu when it is open, else the pause menu as before (u05_gi_pc.py writes the same body)
    'UIMenuPressed': f'''
(fn UIMenuPressed ()
  (bind dw (Variables|GW|GetDevMenuW))
  (if ({ISVALID} :Object dw)
    (if (Appearance|IsinViewport :self dw)
      (CallFunction|CloseDevMenu)
      (return)))
  (bind hud (Variables|GW|GetHUDWidget))
  (if ({ISVALID} :Object hud)
    (GW|Call|{HUD}|TogglePause :self hud)
    (else
      (CallFunction|MenuPressed))))
''',
    'DevServer': '''
(fn DevServer (Cmd)
  (if (Networking|HasAuthority)
    (Development|ExecuteConsoleCommand :Command Cmd :SpecificPlayer self)
    (else
      (Development|ExecuteConsoleCommand :Command (cat "ServerExec " Cmd) :SpecificPlayer self))))
''',
    # movement values are predicted by the owning client: set them here too
    'DevBoth': '''
(fn DevBoth (Cmd)
  (Development|ExecuteConsoleCommand :Command Cmd :SpecificPlayer self)
  (if (not (Networking|HasAuthority))
    (Development|ExecuteConsoleCommand :Command (cat "ServerExec " Cmd) :SpecificPlayer self)))
''',
    'DevPick': '''
(fn DevPick (N)
  (CallFunction|DevServer :Cmd (cat "GWDevOutfit " N)))
''',
    'DevOK': '''
(fn DevOK ()
  (return (or (Pawn|IsLocalPlayerController) (Utilities|HasLaunchOption :OptionToCheck "GWDev"))))
''',
    'DevLog': '''
(fn DevLog (Msg)
  (Development|PrintString :InString (cat "GW: dev " (PlayerState|GetPlayerName :self (GW|Get|/Script/Engine.Controller|PlayerState)) " " Msg) :bPrintToScreen false))
''',
    'DevSpawnSelf': on_gm('''      (bind ch (GW|Call|BP_GW_GameMode|SpawnPlayerPawn :self gm :PC self :Seeker Seeker))
      (GW|Call|BP_GW_GameMode|UpdateCounts :self gm)
      (CallFunction|DevUnfreeze :Ch ch)
      (CallFunction|DevLog :Msg (cat "respawned seeker=" Seeker))''').replace('  (bind gm', '(fn DevSpawnSelf (Seeker)\n  (bind gm', 1) + ')\n',
    'DevUnfreeze': f'''
(fn DevUnfreeze (Ch)
  (bind s {GSC}
    (:then
      (if (!= (GW|Get|BP_GW_GameState|Phase :self s) 1)
        (GW|Call|BP_GW_Character|SetFrozen :self Ch :Frozen false)))
    (:CastFailed)))
''',
    'DevKillSelf': '(fn DevKillSelf (Ch)\n' + on_gm('''      (GW|Call|BP_GW_GameMode|KillPlayer :self gm :Victim Ch :Impulse (Math|Vector|MakeVector 0.0 0.0 0.0))
      (GW|Call|BP_GW_GameMode|UpdateCounts :self gm)
      (CallFunction|DevLog :Msg "became a ghost")''') + ')\n',
    'GWDevOutfit': f'''
(fn GWDevOutfit (Index)
{gate('outfit')}
  (bind pick (Math|Integer|Clamp(Integer) :Value Index :Min 0 :Max 200))
  (Variables|GW|SetDevOutfit pick)
  (bind ch {MYCH}
    (:then
      (GW|Set|BP_GW_Character|OutfitIndex :self ch :OutfitIndex pick)
      (CallFunction|DevLog :Msg (cat "outfit -> OutfitIndex=" pick)))
    (:CastFailed
      (CallFunction|DevLog :Msg (cat "outfit stored " pick " (no character now)")))))
''',
    'GWDevGhost': f'''
(fn GWDevGhost ()
{gate('ghost')}
  (bind ch {MYCH}
    (:then
      (if (GW|Get|BP_GW_Character|IsDead :self ch)
        (return))
      (CallFunction|DevKillSelf :Ch ch))
    (:CastFailed
      (CallFunction|DevLog :Msg "ghost: already a ghost"))))
''',
    'GWDevRespawn': f'''
(fn GWDevRespawn ()
{gate('respawn')}
  (bind ps {PSC}
    (:then
      (GW|Set|BP_GW_PlayerState|IsAlive :self ps :IsAlive true)
      (CallFunction|DevSpawnSelf :Seeker (== (GW|Get|BP_GW_PlayerState|GWRole :self ps) 2)))
    (:CastFailed)))
''',
    'GWDevRole': f'''
(fn GWDevRole (R)
{gate('role')}
  (bind ps {PSC}
    (:then
      (GW|Set|BP_GW_PlayerState|GWRole :self ps :GWRole R)
      (GW|Set|BP_GW_PlayerState|IsAlive :self ps :IsAlive true)
      (CallFunction|DevSpawnSelf :Seeker (== R 2)))
    (:CastFailed)))
''',
    'GWDevSpeed': f'''
(fn GWDevSpeed (Pct)
{gate('speed')}
  (bind ch {MYCH}
    (:then
      (if (<= (Variables|GW|GetDevBaseWalk) 0.0)
        (Variables|GW|SetDevBaseWalk (GW|Get|BP_GW_Character|WalkSpeed :self ch))
        (Variables|GW|SetDevBaseSprint (GW|Get|BP_GW_Character|SprintSpeed :self ch)))
      (GW|Set|BP_GW_Character|WalkSpeed :self ch :WalkSpeed (* (Variables|GW|GetDevBaseWalk) (/ Pct 100.0)))
      (GW|Set|BP_GW_Character|SprintSpeed :self ch :SprintSpeed (* (Variables|GW|GetDevBaseSprint) (/ Pct 100.0)))
      (GW|Call|BP_GW_Character|SetSprint :self ch :On (GW|Get|BP_GW_Character|IsSprinting :self ch))
      (CallFunction|DevLog :Msg (cat "speed " Pct "%")))
    (:CastFailed)))
''',
    'GWDevHeal': f'''
(fn GWDevHeal ()
{gate('heal')}
  (bind ch {MYCH}
    (:then
      (GW|Set|BP_GW_Character|Health :self ch :Health 100.0)
      (CallFunction|DevLog :Msg "healed"))
    (:CastFailed)))
''',
    'GWDevTeleport': f'''
(fn GWDevTeleport (X Y Z)
{gate('teleport')}
  (bind p (Pawn|GetControlledPawn :self self))
  (if ({ISVALID} :Object p)
    (Transformation|SetActorLocation :self p :NewLocation (Math|Vector|MakeVector X Y Z) :bSweep false :bTeleport true)
    (CallFunction|DevLog :Msg (cat "teleport " X " " Y " " Z))))
''',
    'GWDevScore': f'''
(fn GWDevScore (D)
{gate('score')}
  (bind ps {PSC}
    (:then
      (GW|Set|BP_GW_PlayerState|GWScore :self ps :GWScore (+ (GW|Get|BP_GW_PlayerState|GWScore :self ps) D))
      (CallFunction|DevLog :Msg (cat "score " (GW|Get|BP_GW_PlayerState|GWScore :self ps))))
    (:CastFailed)))
''',
    # the server's real values, for the [x] / [ ] of the menu (replicated to everyone, harmless: no gate)
    'DevFlagsPush': '(fn DevFlagsPush ()\n' + on_gm(f'''      (bind s {GSC}
        (:then
          (GW|Set|BP_GW_GameState|DevFlags :self s :DevFlags (+ (+ (select (<= (GW|Get|BP_GW_GameMode|MinPlayers :self gm) 1) {F_SOLO} 0) (select (GW|Get|BP_GW_GameMode|DevNoWin :self gm) 0 {F_AUTOEND})) (+ (select (GW|Get|BP_GW_GameMode|DevFrozen :self gm) {F_FROZEN} 0) (+ (select (GW|Get|BP_GW_GameMode|AutoEvents :self gm) {F_AUTOEV} 0) (select (GW|Get|BP_GW_GameMode|LifeBlockOn :self gm) {F_NPCBLOCK} 0))))))
        (:CastFailed))''') + ')\n',
    'GWDevPianoGo': f'''
(fn GWDevPianoGo ()
{gate('pianogo')}
  (bind p (Pawn|GetControlledPawn :self self))
  (if (not ({ISVALID} :Object p))
    (return))
  (bind s {GSC}
    (:then (Transformation|SetActorLocation :self p :NewLocation (+ (GW|Call|BP_GW_GameState|PianoSpot :self s) (Math|Vector|MakeVector 150.0 0.0 100.0)) :bSweep false :bTeleport true))
    (:CastFailed)))
''',
    'DevPromptLog': '''
(fn DevPromptLog (St)
  (Variables|GW|SetDevCount 0)
  (bind all (Actor|GetAllActorsOfClass :ActorClass "/Game/GW/Blueprints/BP_GW_KeyPrompt.BP_GW_KeyPrompt_C"))
  (for a all
    (if (GW|Call|/Script/Engine.SceneComponent|IsVisible :self (GW|Get|BP_GW_KeyPrompt|Prompt :self a))
      (Variables|GW|SetDevCount (+ (Variables|GW|GetDevCount) 1))))
  (Development|PrintString :InString (cat "GW promptqa step " St " shown=" (Variables|GW|GetDevCount) " of " (Utilities|Array|Length all)) :bPrintToScreen false))
''',
    'DevUIQA': '(fn DevUIQA (St)\n' + '\n'.join(f'  (if (== St {n})\n    {c})' for n, c in [
        (3, '(CallFunction|DevServer :Cmd "GWDevQuickTest 1")'), (5, '(CallFunction|ToggleDevMenu)'), (6, '(CallFunction|DevDown)'), (7, '(CallFunction|DevAccept)'),
        (8, UISHOT), (9, '(CallFunction|DevBack)'), (10, '(CallFunction|DevDown)\n    (CallFunction|DevDown)\n    (CallFunction|DevDown)'), (11, '(CallFunction|DevAccept)'),
        (12, UISHOT), (13, '(CallFunction|DevDown)\n    (CallFunction|DevDown)\n    (CallFunction|DevDown)\n    (CallFunction|DevDown)'), (14, '(CallFunction|DevAccept)'), (15, UISHOT),
        (16, '(CallFunction|DevAccept)'), (17, '(CallFunction|CloseDevMenu)'),
        (18, '(CallFunction|DevServer :Cmd "GWDevMoney 500")\n    (Utilities|Time|SetTimerbyFunctionName :Object self :FunctionName "DevEventShotNow" :Time 0.45 :bLooping false)'),
        (20, '(CallFunction|DevServer :Cmd "GWDevEvent 1")\n    (Utilities|Time|SetTimerbyFunctionName :Object self :FunctionName "DevEventShotNow" :Time 1.0 :bLooping false)'),
        (23, '(CallFunction|DevServer :Cmd "GWDevEventStop")'), (25, UISHOT),
        (26, '(Variables|GW|SetDevQAW (UserInterface|CreateWidget :Class "/Game/GW/UI/WBP_Options.WBP_Options_C" :OwningPlayer self))\n    (UserInterface|Viewport|AddtoViewport :self (Variables|GW|GetDevQAW) :ZOrder 60)'),
        (27, UISHOT), (28, '(bind ow (Utilities|Casting|CastToWBP_Options (Variables|GW|GetDevQAW))\n      (:then (GW|Call|/Game/GW/UI/WBP_Options.WBP_Options_C|OnKeys :self ow))\n      (:CastFailed))'), (29, UISHOT), (30, '(Widget|RemovefromParent :self (Variables|GW|GetDevQAW))'),
        (31, '(CallFunction|DevServer :Cmd "GWDevPianoGo")'), (33, '(CallFunction|DevPromptLog :St St)'), (34, UISHOT), (35, '(CallFunction|DevServer :Cmd "GWDevGhost")'),
        (37, '(CallFunction|DevPromptLog :St St)'), (38, '(CallFunction|DevServer :Cmd "GWDevRespawn")'), (39, '(CallFunction|DevServer :Cmd "GWDevPianoGo")'), (41, '(CallFunction|DevPromptLog :St St)'),
        (42, '(CallFunction|DevServer :Cmd "GWDevTeleport 5085 2485 130")'), (44, '(CallFunction|DevPromptLog :St St)'), (45, UISHOT),
        (46, '(CallFunction|OpenShopHere :Kind 0)'), (48, UISHOT), (50, '(CallFunction|CloseShop)'),
        (51, '(Variables|GW|SetDevQAW (UserInterface|CreateWidget :Class "/Game/GW/UI/WBP_HowTo.WBP_HowTo_C" :OwningPlayer self))\n    (UserInterface|Viewport|AddtoViewport :self (Variables|GW|GetDevQAW) :ZOrder 50)'),
        (53, UISHOT),
        (55, '(Game|QuitGame :SpecificPlayer self :QuitPreference "Quit" :bIgnorePlatformRestrictions false)')]) + ')\n',
    'GWDevSync': '(fn GWDevSync ()\n  (CallFunction|DevFlagsPush))\n',
    # options test: 0 = rebind the first action to the second one's key (they swap), 1 = log the keys, 2 = back to the defaults
    'GWDevKeyTest': '''
(fn GWDevKeyTest (Mode)
  (bind gi (Utilities|Casting|CastToBP_GW_GameInstance (Game|GetGameInstance))
    (:then
      (if (== Mode 0)
        (GW|Call|BP_GW_GameInstance|GWSetBind :self gi :I 0 :K (Utilities|Array|Get(acopy) (GW|Get|BP_GW_GameInstance|KeyDefs :self gi) 1)))
      (if (== Mode 2)
        (GW|Call|BP_GW_GameInstance|GWResetBinds :self gi))
      (bind sub (LocalPlayerSubsystems|GetEnhancedInputLocalPlayerSubsystem))
      (bind a0 (Utilities|Array|Get(acopy) (GW|Get|BP_GW_GameInstance|KeyActs :self gi) 0))
      (bind a1 (Utilities|Array|Get(acopy) (GW|Get|BP_GW_GameInstance|KeyActs :self gi) 1))
      (bind q0 (Input|MappingQueries|QueryKeysMappedtoAction :self sub :Action a0))
      (bind q1 (Input|MappingQueries|QueryKeysMappedtoAction :self sub :Action a1))
      (Development|PrintString :InString (cat "GW keytest mode=" Mode " " (Utilities|GetObjectName :Object a0) " shows " (GW|Call|BP_GW_GameInstance|GWKeyName :self gi :I 0) " mapped=" (Utilities|Array|Length q0) ":" (select (> (Utilities|Array|Length q0) 0) (Utilities|String|ToString(Text) (Input|Key|GetKeyDisplayName :Key (Utilities|Array|Get(acopy) q0 0))) "-") " | " (Utilities|GetObjectName :Object a1) " shows " (GW|Call|BP_GW_GameInstance|GWKeyName :self gi :I 1) " mapped=" (Utilities|Array|Length q1) ":" (select (> (Utilities|Array|Length q1) 0) (Utilities|String|ToString(Text) (Input|Key|GetKeyDisplayName :Key (Utilities|Array|Get(acopy) q1 0))) "-") " | prompt E -> " (GW|Call|BP_GW_GameInstance|GWKeyLabel :self gi :Key "E")) :bPrintToScreen false))
    (:CastFailed)))
''',
    'GWDevSolo': f'''
(fn GWDevSolo (On)
{gate('solo')}
''' + on_gm('''      (GW|Set|BP_GW_GameMode|MinPlayers :self gm :MinPlayers (select (!= On 0) 1 2))
      (CallFunction|DevFlagsPush)
      (CallFunction|DevLog :Msg (cat "MinPlayers=" (GW|Get|BP_GW_GameMode|MinPlayers :self gm)))''') + ')\n',
    'GWDevAutoEnd': f'''
(fn GWDevAutoEnd (On)
{gate('autoend')}
''' + on_gm('''      (GW|Set|BP_GW_GameMode|DevNoWin :self gm :DevNoWin (== On 0))
      (CallFunction|DevFlagsPush)
      (CallFunction|DevLog :Msg (cat "auto end=" On))''') + ')\n',
    # test round flags: solo, no win check (game mode) and TestRound (game state: no timeout, no "not enough
    # players", HUD shows TEST) -- s12_gamemode.py RoundTick / u14_hud.py RefreshWith read it
    'DevTestFlags': '(fn DevTestFlags (On)\n' + on_gm(f'''      (GW|Set|BP_GW_GameMode|MinPlayers :self gm :MinPlayers (select On 1 2))
      (GW|Set|BP_GW_GameMode|DevNoWin :self gm :DevNoWin On)
      (bind s {GSC}
        (:then
          (GW|Set|BP_GW_GameState|TestRound :self s :TestRound On)
          (CallFunction|DevFlagsPush))
        (:CastFailed))''') + ')\n',
    'GWDevTestRound': f'''
(fn GWDevTestRound (R)
{gate('testround')}
  (CallFunction|DevTestFlags :On true)
''' + on_gm('''      (GW|Call|BP_GW_GameMode|StartRound :self gm)
      (CallFunction|GWDevRole :R R)
      (CallFunction|DevLog :Msg (cat "test round started as role " R))''') + ')\n',
    'GWDevQuickTest': f'''
(fn GWDevQuickTest (R)
{gate('quicktest')}
  (CallFunction|DevTestFlags :On true)
''' + on_gm('''      (GW|Call|BP_GW_GameMode|StartRound :self gm)
      (CallFunction|GWDevRole :R R)
      (GW|Call|BP_GW_GameMode|BeginHunt :self gm)
      (CallFunction|DevLog :Msg (cat "quick test as role " R))''') + ')\n',
    'GWDevTestEnd': f'''
(fn GWDevTestEnd ()
{gate('testend')}
  (CallFunction|DevTestFlags :On false)
''' + on_gm('''      (GW|Call|BP_GW_GameMode|ResetToLobby :self gm)
      (CallFunction|DevLog :Msg "test round ended")''') + ')\n',
    'GWDevEvent': f'''
(fn GWDevEvent (Id)
{gate('event')}
''' + on_gm('''      (GW|Call|BP_GW_GameMode|StartEvent :self gm :Id Id)
      (CallFunction|DevLog :Msg (cat "event " Id))''') + ')\n',
    'GWDevPiano': f'''
(fn GWDevPiano ()
{gate('piano')}
''' + on_gm('''      (bind s (Utilities|Casting|CastToBP_GW_GameState (Game|GetGameState))
        (:then
          (GW|Set|BP_GW_GameState|PianoNext :self s :PianoNext 0.0)
          (GW|Call|BP_GW_GameMode|PlayPiano :self gm :Who (Pawn|GetControlledPawn :self self))
          (CallFunction|DevLog :Msg "piano"))
        (:CastFailed))''') + ')\n',
    'DevEnsureAlive': f'''
(fn DevEnsureAlive ()
  (bind me0 {MYCH}
    (:then
      (if (GW|Get|BP_GW_Character|IsDead :self me0)
        (CallFunction|GWDevRespawn)))
    (:CastFailed
      (CallFunction|GWDevRespawn))))
''',
    'GWDevRobotTest': f'''
(fn GWDevRobotTest ()
{gate('robottest')}
  (CallFunction|DevEnsureAlive)
''' + on_gm('''      (bind p (Pawn|GetControlledPawn :self self))
      (if (GW|Call|/Script/Engine.KismetSystemLibrary|IsValid :Object p)
        (bind pl (Transformation|GetActorLocation :self p))
        ; 12 directions around the player: the first spot with a clear line of sight (straight ahead is often a wall), else right in front of him
        (Variables|GW|SetDevRobotSpot (+ pl (* (Transformation|GetActorForwardVector :self p) 300.0)))
        (for k (range 12)
          (bind (rp rok) (AI|Navigation|GetRandomReachablePointinRadius :Origin (+ pl (Math|Vector|MakeVector (* 800.0 (Math|Trig|Cos(Radians) (* k 0.5236))) (* 800.0 (Math|Trig|Sin(Radians) (* k 0.5236))) 0.0)) :Radius 150.0))
          (Variables|GW|SetDevRobotTry rp)
          (if rok
            (bind (rh rblock) (Collision|LineTraceByChannel :Start (+ pl (Math|Vector|MakeVector 0.0 0.0 60.0)) :End (+ (Variables|GW|GetDevRobotTry) (Math|Vector|MakeVector 0.0 0.0 150.0)) :TraceChannel "Visibility" :bTraceComplex false :bIgnoreSelf true))
            (if (not rblock)
              (Variables|GW|SetDevRobotSpot (Variables|GW|GetDevRobotTry))
              (break))))
        (bind r (GW|Call|BP_GW_GameMode|SpawnSpecial :self gm :Kind 3 :Loc (+ (Variables|GW|GetDevRobotSpot) (Math|Vector|MakeVector 0.0 0.0 100.0))))
        (Transformation|SetActorRotation :self r :NewRotation (Math|Rotator|MakeRotator :Yaw (.yaw (Math|Rotator|FindLookatRotation :Start (Transformation|GetActorLocation :self r) :Target pl))) :bTeleportPhysics false)
        (CallFunction|DevLog :Msg "robot test: spawned facing the player"))''') + ')\n',
    # test: the player 5 m straight ahead of the robot (it walks where it wants; its cone is only 15 degrees wide)
    'GWDevRobotFace': f'''
(fn GWDevRobotFace ()
{gate('robotface')}
  (bind p (Pawn|GetControlledPawn :self self))
  (if (not ({ISVALID} :Object p))
    (return))
  (for c (Actor|GetAllActorsOfClass :ActorClass "/Game/GW/Blueprints/BP_GW_Character.BP_GW_Character_C")
    (if (and (== (GW|Get|BP_GW_Character|Kind :self c) 3) (not (GW|Get|BP_GW_Character|IsDead :self c)))
      (Transformation|SetActorLocation :self p :NewLocation (+ (Transformation|GetActorLocation :self c) (* (Transformation|GetActorForwardVector :self c) 500.0)) :bSweep false :bTeleport true)
      (CallFunction|DevLog :Msg "robot test: player in front of the robot")
      (break))))
''',
    'GWDevEventGo': f'''
(fn GWDevEventGo ()
{gate('eventgo')}
''' + on_gm('''      (bind (fl fok) (GW|Call|BP_GW_GameMode|EventFocus :self gm))
      (bind p (Pawn|GetControlledPawn :self self))
      (if (and fok (GW|Call|/Script/Engine.KismetSystemLibrary|IsValid :Object p))
        (bind (np nok) (AI|Navigation|GetRandomReachablePointinRadius :Origin fl :Radius 420.0))
        (Transformation|SetActorLocation :self p :NewLocation (+ (select nok np (+ fl (Math|Vector|MakeVector 380.0 0.0 0.0))) (Math|Vector|MakeVector 0.0 0.0 100.0)) :bSweep false :bTeleport true)
        (Pawn|SetControlRotation :self self :NewRotation (Math|Rotator|FindLookatRotation :Start (Transformation|GetActorLocation :self p) :Target fl))
        (CallFunction|DevLog :Msg (cat "went to the event at " fl)))''') + ')\n',
    'GWDevNPCPiano': f'''
(fn GWDevNPCPiano ()
{gate('npcpiano')}
''' + on_gm('''      (GW|Call|BP_GW_GameMode|SendNPCToPiano :self gm)
      (CallFunction|DevLog :Msg "npc piano")''') + ')\n',
    # s36_social.py: an NPC dance group / bar crowd right now (ends the current one first)
    'GWDevDanceNow': f'''
(fn GWDevDanceNow ()
{gate('dancenow')}
''' + on_gm('''      (GW|Call|BP_GW_GameMode|SocialStartDance :self gm :Force true)
      (CallFunction|DevLog :Msg "npc dance group")''') + ')\n',
    'GWDevBarNow': f'''
(fn GWDevBarNow ()
{gate('barnow')}
''' + on_gm('''      (GW|Call|BP_GW_GameMode|SocialStartBar :self gm :Force true)
      (CallFunction|DevLog :Msg "npc bar crowd")''') + ')\n',
    'GWDevVoicePanic': f'''
(fn GWDevVoicePanic (C)
{gate('voicepanic')}
  (bind p (Pawn|GetControlledPawn :self self))
  (if (not ({ISVALID} :Object p))
    (return))
  (bind loc (Transformation|GetActorLocation :self p))
''' + on_gm('''      (GW|Call|BP_GW_GameMode|StartPanicCause :self gm :Loc (+ loc (Math|Vector|MakeVector 300.0 0.0 0.0)) :Dur 10.0 :Cause C)
      (CallFunction|DevLog :Msg (cat "voice panic, cause " C))''') + ')\n',
    'GWDevVoiceChat': f'''
(fn GWDevVoiceChat ()
{gate('voicechat')}
  (bind p (Pawn|GetControlledPawn :self self))
  (if (not ({ISVALID} :Object p))
    (return))
  (bind loc (Transformation|GetActorLocation :self p))
''' + on_gm('''      (GW|Call|BP_GW_GameMode|DevVoiceChat :self gm :Loc loc)
      (CallFunction|DevLog :Msg "voice chat here")''') + ')\n',
    'GWDevVoiceState': f'''
(fn GWDevVoiceState ()
{gate('voicestate')}
''' + on_gm('''      (GW|Call|BP_GW_GameMode|DevVoiceState :self gm)
      (CallFunction|DevLog :Msg "voice state")''') + ')\n',
    'GWDevEventStop': f'''
(fn GWDevEventStop ()
{gate('eventstop')}
''' + on_gm('''      (GW|Call|BP_GW_GameMode|EndEvent :self gm)
      (CallFunction|DevLog :Msg "event stopped")''') + ')\n',
    'GWDevAutoEvents': f'''
(fn GWDevAutoEvents (On)
{gate('autoevents')}
''' + on_gm('''      (GW|Set|BP_GW_GameMode|AutoEvents :self gm :AutoEvents (!= On 0))
      (CallFunction|DevFlagsPush)
      (GW|Set|BP_GW_GameMode|NextEventAt :self gm :NextEventAt (+ (GW|Call|BP_GW_GameMode|Now :self gm) 15.0))
      (CallFunction|DevLog :Msg (cat "auto events " On))''') + ')\n',
    'GWDevEventEvery': f'''
(fn GWDevEventEvery (S)
{gate('eventevery')}
''' + on_gm('''      (GW|Set|BP_GW_GameMode|EventEvery :self gm :EventEvery S)
      (CallFunction|DevLog :Msg (cat "event every " S))''') + ')\n',
    **{n_: f'''
(fn {n_} ({a_})
{gate(n_.lower())}
''' + on_gm(f'''      (GW|Set|BP_GW_GameMode|{v_} :self gm :{v_} {a_})
      (CallFunction|DevLog :Msg (cat "{n_} " {a_}))''') + ')\n' for n_, v_, a_ in (('GWDevZombieLife', 'ZombieLife', 'S'), ('GWDevZombieBite', 'ZombieBite', 'S'), ('GWDevRobotHP', 'RobotHP', 'V'), ('GWDevRobotDmg', 'RobotDmg', 'V'), ('GWDevGasScale', 'GasScale', 'V'), ('GWDevBladeCD', 'BladeCD', 'V'), ('GWDevTrapDmg', 'TrapDmg', 'V'))},
    'GWDevMoveTurn': f'''
(fn GWDevMoveTurn (V)
{gate('gwdevmoveturn')}
  (bind st (Utilities|Casting|CastToBP_GW_GameState (Game|GetGameState))
    (:then
      (GW|Set|BP_GW_GameState|MoveTurn :self st :MoveTurn V)
      (CallFunction|DevLog :Msg (cat "GWDevMoveTurn " V)))
    (:CastFailed)))
''',
    'GWDevTrapNPC': f'''
(fn GWDevTrapNPC (V)
{gate('gwdevtrapnpc')}
''' + on_gm(f'''      (GW|Set|BP_GW_GameMode|TrapNPC :self gm :TrapNPC (!= V 0))
      (CallFunction|DevLog :Msg (cat "GWDevTrapNPC " V))''') + ')\n',
    'GWDevRobotHit': f'''
(fn GWDevRobotHit ()
{gate('robothit')}
''' + on_gm('''      (for c (Actor|GetAllActorsOfClass :ActorClass "/Game/GW/Blueprints/BP_GW_Character.BP_GW_Character_C")
        (if (== (GW|Get|BP_GW_Character|Kind :self c) 3)
          (GW|Call|BP_GW_GameMode|RobotHurt :self gm :Victim c :Amount 100.0 :Dir (Math|Vector|MakeVector 1.0 0.0 0.0))))''') + ')\n',
    'GWDevEventDur': f'''
(fn GWDevEventDur (S)
{gate('eventdur')}
''' + on_gm('''      (GW|Set|BP_GW_GameMode|EventDurSet :self gm :EventDurSet S)
      (CallFunction|DevLog :Msg (cat "event duration " S))''') + ')\n',
    'GWDevStartRound': f'''
(fn GWDevStartRound ()
{gate('start')}
''' + on_gm('''      (GW|Call|BP_GW_GameMode|StartRound :self gm)
      (CallFunction|DevLog :Msg "round started")''') + ')\n',
    'GWDevHunt': f'''
(fn GWDevHunt ()
{gate('hunt')}
''' + on_gm(f'''      (bind s {GSC}
        (:then
          (if (== (GW|Get|BP_GW_GameState|Phase :self s) 1)
            (GW|Call|BP_GW_GameMode|BeginHunt :self gm)
            (CallFunction|DevLog :Msg "hunt started")))
        (:CastFailed))''') + ')\n',
    'GWDevEndRound': f'''
(fn GWDevEndRound (W)
{gate('end')}
''' + on_gm('''      (GW|Call|BP_GW_GameMode|EndRound :self gm :W W :Msg (select (== W 2) "Fin forcée : les survivants gagnent." (select (== W 4) "Fin forcée : personne n'a survécu." "Manche annulée (menu développeur).")))
      (CallFunction|DevLog :Msg (cat "round ended W=" W))''') + ')\n',
    'GWDevLobby': f'''
(fn GWDevLobby ()
{gate('lobby')}
''' + on_gm('''      (GW|Call|BP_GW_GameMode|ResetToLobby :self gm)
      (CallFunction|DevLog :Msg "back to lobby")''') + ')\n',
    'GWDevClock': f'''
(fn GWDevClock (D)
{gate('clock')}
''' + on_gm(f'''      (bind now (GW|Call|BP_GW_GameMode|Now :self gm))
      (bind s {GSC}
        (:then
          (bind pe (GW|Get|BP_GW_GameState|PhaseEndTime :self s))
          (if (== D 0)
            (GW|Set|BP_GW_GameState|PhaseEndTime :self s :PhaseEndTime (+ now 0.05))
            (else
              (if (> pe 0.0)
                (GW|Set|BP_GW_GameState|PhaseEndTime :self s :PhaseEndTime (+ pe D)))))
          (CallFunction|DevLog :Msg (cat "clock D=" D " end=" (GW|Get|BP_GW_GameState|PhaseEndTime :self s) " now=" now)))
        (:CastFailed))''') + ')\n',
    'GWDevTimeScale': f'''
(fn GWDevTimeScale (Pct)
{gate('timescale')}
  (Utilities|Time|SetGlobalTimeDilation :TimeDilation (/ Pct 100.0))
  (CallFunction|DevLog :Msg (cat "time dilation " (Utilities|Time|GetGlobalTimeDilation))))
''',
    'GWDevNPCAdd': f'''
(fn GWDevNPCAdd (N)
{gate('npcadd')}
''' + on_gm('''      (for i (range N)
        (GW|Call|BP_GW_GameMode|SpawnNPC :self gm))
      (CallFunction|DevLog :Msg (cat "npc +" N))''') + ')\n',
    'GWDevNPCRemove': f'''
(fn GWDevNPCRemove (N)
{gate('npcremove')}
  (Variables|GW|SetDevCount 0)
  (for c (Actor|GetAllActorsOfClass :ActorClass {CHAR})
    (if (and (not (Pawn|IsPlayerControlled :self c)) (< (Variables|GW|GetDevCount) N))
      (Variables|GW|SetDevCount (+ (Variables|GW|GetDevCount) 1))
      (Actor|DestroyActor :self c)))
  (CallFunction|DevLog :Msg (cat "npc -" (Variables|GW|GetDevCount))))
''',
    'GWDevNPCFreeze': f'''
(fn GWDevNPCFreeze (On)
{gate('npcfreeze')}
  (for c (Actor|GetAllActorsOfClass :ActorClass {CHAR})
    (if (not (Pawn|IsPlayerControlled :self c))
      (GW|Call|BP_GW_Character|SetFrozen :self c :Frozen (!= On 0))))
  (CallFunction|DevLog :Msg (cat "npc frozen=" On))
  (bind gm {GMC}
    (:then
      (GW|Set|BP_GW_GameMode|DevFrozen :self gm :DevFrozen (!= On 0))
      (CallFunction|DevFlagsPush))
    (:CastFailed)))
''',
    'GWDevNPCBlock': f'''
(fn GWDevNPCBlock (On)
{gate('npcblock')}
  (bind gm {GMC}
    (:then
      (GW|Set|BP_GW_GameMode|LifeBlockOn :self gm :LifeBlockOn (!= On 0))
      (CallFunction|DevFlagsPush))
    (:CastFailed)))
''',
    'GWDevNPCState': f'''
(fn GWDevNPCState ()
{gate('npcstate')}
  (bind gm {GMC}
    (:then
      (bind st (GW|Call|BP_GW_GameMode|LifeState :self gm))
      (CallFunction|DevLog :Msg st)
      (CallFunction|Notice :Msg st))
    (:CastFailed)))
''',
    'GWDevNPCKill': f'''
(fn GWDevNPCKill ()
{gate('npckill')}
  (bind p (Pawn|GetControlledPawn :self self))
  (if (not ({ISVALID} :Object p))
    (return))
  (bind loc (Transformation|GetActorLocation :self p))
''' + on_gm('''      (GW|Call|BP_GW_GameMode|DevKillNearestNPC :self gm :Loc loc)''') + ')\n',
    'GWDevNPCOutfit': f'''
(fn GWDevNPCOutfit (I)
{gate('npcoutfit')}
''' + on_gm(f'''      (bind n (Math|Integer|Max(Integer) (GW|Get|BP_GW_GameMode|NumOutfits :self gm) 1))
      (for c (Actor|GetAllActorsOfClass :ActorClass {CHAR})
        (if (not (Pawn|IsPlayerControlled :self c))
          (GW|Set|BP_GW_Character|OutfitIndex :self c :OutfitIndex (select (< I 0) (Math|Random|RandomIntegerinRange 0 (- n 1)) I))))
      (CallFunction|DevLog :Msg (cat "npc outfit " I))''') + ')\n',
    'GWDevAnnounce': f'''
(fn GWDevAnnounce ()
{gate('announce')}
''' + on_gm('''      (GW|Call|BP_GW_GameMode|Announce :self gm :Text "Annonce de test du menu développeur.")''') + ')\n',
    # -GWDevTest: page navigation, then every server command, then a dump of the characters
    'DevTestTick': '(fn DevTestTick ()\n  (Variables|GW|SetDevTestStep (+ (Variables|GW|GetDevTestStep) 1))\n  (bind st (Variables|GW|GetDevTestStep))\n  (if (Utilities|HasLaunchOption :OptionToCheck "GWUIQA")\n    (CallFunction|DevUIQA :St st)\n    (return))\n' + '\n'.join(
        f'  (if (== st {s}) {call})' for s, call in [
            (3, '(CallFunction|ToggleDevMenu)'), (4, '(CallFunction|DevDown)'), (5, '(CallFunction|DevAccept)'),
            (6, '(CallFunction|DevServer :Cmd "GWDevKeyTest 0")'), (7, '(CallFunction|DevBack)'),
            (8, '(CallFunction|DevServer :Cmd "GWDevSolo 1")'), (9, '(CallFunction|DevServer :Cmd "GWDevAutoEnd 0")'),
            (10, '(CallFunction|DevServer :Cmd "GWDevStartRound")'), (12, '(CallFunction|DevServer :Cmd "GWDevRole 1")'),
            (13, '(CallFunction|DevServer :Cmd "GWDevHunt")'), (14, '(CallFunction|DevServer :Cmd "GWDevGhost")'),
            (15, '(CallFunction|DevServer :Cmd "GWDevTeleport 7000 2000 130")'),
            (18, '(CallFunction|DevServer :Cmd "GWDevRespawn")'), (19, '(CallFunction|DevServer :Cmd "GWDevTeleport 1085 3405 130")'),
            (20, '(CallFunction|DevBoth :Cmd "GWDevSpeed 200")'), (21, '(CallFunction|DevServer :Cmd "GWDevHeal")'),
            (22, '(CallFunction|DevServer :Cmd "GWDevScore 5")'), (23, '(CallFunction|DevServer :Cmd "GWDevNPCAdd 5")'),
            (11, '(CallFunction|DevServer :Cmd "GWDevKeyTest 1")'), (16, '(CallFunction|DevServer :Cmd "GWDevKeyTest 2")'), (17, '(CallFunction|DevServer :Cmd "GWDevKeyTest 1")'),
            (24, '(CallFunction|DevServer :Cmd "GWDevNPCRemove 5")'), (25, '(CallFunction|DevServer :Cmd "GWDevNPCFreeze 1")'),
            (26, '(CallFunction|DevServer :Cmd "GWDevNPCKill")'), (27, '(CallFunction|DevServer :Cmd "GWDevNPCOutfit 0")'),
            (28, '(CallFunction|DevServer :Cmd "GWDevNPCFreeze 0")'), (29, '(CallFunction|DevServer :Cmd "GWDevClock 60")'),
            (30, '(CallFunction|DevServer :Cmd "GWDevTimeScale 50")'), (32, '(CallFunction|DevServer :Cmd "GWDevTimeScale 100")'),
            (33, '(CallFunction|DevServer :Cmd "GWDevAnnounce")'), (34, '(CallFunction|DevServer :Cmd "GWDevRole 2")'),
            (35, '(CallFunction|DevServer :Cmd "GWDevEndRound 1")'), (37, '(CallFunction|DevServer :Cmd "GWDevLobby")'),
            (39, '(CallFunction|DevTestChars)'),
            # test round: starts as detective, forced hunt, clock run out -> must stay in the hunt; then ends
            (41, '(CallFunction|DevServer :Cmd "GWDevTestRound 2")'), (43, '(CallFunction|DevServer :Cmd "GWDevHunt")'),
            (44, '(CallFunction|DevServer :Cmd "GWDevClock 0")'), (47, '(CallFunction|DevServer :Cmd "GWDevTestEnd")'),
            (48, '(CallFunction|DevServer :Cmd "GWDevAutoEvents 0")'), (49, '(CallFunction|DevServer :Cmd "GWDevAutoEvents 1")'),
            # s36_social.py: an NPC dance group and the bar crowd, then the player dances (V) and stops (V)
            (42, '(CallFunction|DevServer :Cmd "GWDevDanceNow")'), (42, '(CallFunction|DevServer :Cmd "GWDevBarNow")'),
            (45, '(CallFunction|RequestDance)'), (46, '(CallFunction|RequestDance)'),
            # events during a test round as a guest: blackout, fire, attack, kamikaze, robot
            (50, '(CallFunction|DevServer :Cmd "GWDevTestRound 1")'), (52, '(CallFunction|DevServer :Cmd "GWDevHunt")'),
            (53, '(CallFunction|DevServer :Cmd "GWDevPiano")'), (54, '(CallFunction|DevServer :Cmd "GWDevEvent 3")'), (58, '(CallFunction|DevServer :Cmd "GWDevEvent 2")'),
            (64, '(CallFunction|DevServer :Cmd "GWDevEvent 1")'), (72, '(CallFunction|DevServer :Cmd "GWDevEvent 4")'),
            (88, '(CallFunction|DevServer :Cmd "GWDevEvent 5")'), (89, '(CallFunction|DevServer :Cmd "GWDevNPCPiano")'), (91, '(CallFunction|DevServer :Cmd "GWDevRobotTest")'), (92, '(CallFunction|DevServer :Cmd "GWDevRobotFace")'), (94, '(CallFunction|DevServer :Cmd "GWDevRobotFace")'), (96, '(CallFunction|DevServer :Cmd "GWDevRobotFace")'), (98, '(CallFunction|DevServer :Cmd "GWDevRobotFace")'), (100, '(CallFunction|DevServer :Cmd "GWDevTestEnd")'),
            (102, '(CallFunction|DevBack)'),
            # pickups & interactables (bodies in Tools/gameplay/s38_pickups.py; checked by Tools/qa/qa_check.py):
            # ball picked up + thrown at an NPC, sword stolen + slash, body swap, safe, fire alarm, toilet
            (104, '(CallFunction|DevServer :Cmd "GWDevQuickTest 1")'), (106, '(CallFunction|DevServer :Cmd "GWDevGoTo 0")'),
            (107, '(CallFunction|TryPickup)'), (108, '(CallFunction|DevServer :Cmd "GWDevAimAt 0 300")'),
            (109, '(CallFunction|DevServer :Cmd "GWDevBallAt")'), (111, '(CallFunction|DevServer :Cmd "GWDevGoTo 1")'),
            (112, '(CallFunction|TryPickup)'), (113, '(CallFunction|DevServer :Cmd "GWDevAimAt 0 140")'),
            (114, '(CallFunction|DevAimLocal :Mode 0 :Dist 140.0)'), (115, '(CallFunction|PTAttack)'),
            (117, '(CallFunction|DevServer :Cmd "GWDevGiveSwap")'), (118, '(CallFunction|DevServer :Cmd "GWDevAimAt 0 220")'),
            (119, '(CallFunction|DevAimLocal :Mode 0 :Dist 220.0)'), (120, '(CallFunction|RequestSwap)'),
            (123, '(CallFunction|DevServer :Cmd "GWDevLearnCode")'), (124, '(CallFunction|DevServer :Cmd "GWDevGoTo 3")'),
            (125, '(CallFunction|TryPickup)'), (126, '(CallFunction|DevServer :Cmd "GWDevGoTo 4")'), (127, '(CallFunction|TryPickup)'),
            (128, '(CallFunction|DevServer :Cmd "GWDevGoTo 5")'), (129, '(CallFunction|TryPickup)'),
            (131, '(CallFunction|DevServer :Cmd "GWDevTestEnd")'),
            # shop (Tools/gameplay/s34_shop.py; checked by Tools/qa/qa_check.py): barman purchases, a rifle kill (+100 $),
            # a bomb defused by holding E 2 s, a waiter who walks away (the shop closes), a junkie sale
            (133, '(CallFunction|DevServer :Cmd "GWDevQuickTest 1")'), (135, '(CallFunction|DevServer :Cmd "GWDevMoney 3000")'),
            (136, '(CallFunction|DevServer :Cmd "GWDevTeleport 4420 1440 130")'), (137, '(CallFunction|TryShop)'),
            (138, '(CallFunction|ShopBuy :Id 1)'), (138, '(CallFunction|ShopBuy :Id 6)'), (139, '(CallFunction|TryShop)'),
            (140, '(CallFunction|DevServer :Cmd "GWDevNPCFreeze 1")'), (140, '(CallFunction|DevServer :Cmd "GWDevShopAim 0")'),
            (141, '(CallFunction|DevServer :Cmd "GWDevShopAim 1")'), (142, '(CallFunction|RequestFire)'),
            (143, '(CallFunction|DevServer :Cmd "GWDevNPCFreeze 0")'), (143, '(CallFunction|UseBomb)'),
            (144, '(CallFunction|DevServer :Cmd "GWDevRole 2")'), (145, '(CallFunction|DevServer :Cmd "GWDevGoBomb")'),
            (146, '(CallFunction|TryDefuse)'), (149, '(CallFunction|DevServer :Cmd "GWDevRole 1")'),
            (150, '(CallFunction|DevServer :Cmd "GWDevWaiter")'), (151, '(CallFunction|TryShop)'),
            (152, '(CallFunction|DevServer :Cmd "GWDevWaiterLeave")'), (162, '(CallFunction|DevServer :Cmd "GWDevTeleport 260 2130 130")'),
            (163, '(CallFunction|TryShop)'), (164, '(CallFunction|ShopBuy :Id 9)'), (165, '(CallFunction|TryShop)'),
            (166, '(CallFunction|DevServer :Cmd "GWDevTestEnd")')]) + '''
  ; -GWDevShot: screenshots with the UI (the Partie page, then the ghost after it was teleported outside)
  (if (and (Utilities|HasLaunchOption :OptionToCheck "GWDevShot") (or (== st 14) (== st 16)))
    (Development|ExecuteConsoleCommand :Command "Shot showui" :SpecificPlayer self))
  (if (and (>= st 3) (<= st 102))
    (CallFunction|DevTestLog :St st)))
''',
    'DevTestChars': f'''
(fn DevTestChars ()
  (for c (Actor|GetAllActorsOfClass :ActorClass {CHAR})
    (Development|PrintString :InString (cat "GW devtest char " (Utilities|GetDisplayName :Object c) " oi=" (GW|Get|BP_GW_Character|OutfitIndex :self c) " seeker=" (GW|Get|BP_GW_Character|IsSeeker :self c) " dead=" (GW|Get|BP_GW_Character|IsDead :self c) " mesh=" (Utilities|GetDisplayName :Object (Components|SkeletalMesh|GetSkeletalMeshAsset :self (GW|Get|/Script/Engine.Character|Mesh :self c)))) :bPrintToScreen false)))
''',
    'DevTestLog': f'''
(fn DevTestLog (St)
  (Variables|GW|SetDevTestOpen false)
  (Variables|GW|SetDevTestPage -1)
  (bind w (Variables|GW|GetDevMenuW))
  (if ({ISVALID} :Object w)
    (Variables|GW|SetDevTestOpen (Appearance|IsinViewport :self w))
    (Variables|GW|SetDevTestPage (GW|Get|{DM}|Page :self w)))
  (bind p (Pawn|GetControlledPawn :self self))
  (bind s {GSC}
    (:then
      (bind ps {PSC}
        (:then
          (Development|PrintString :InString (cat "GW devtest step " St " open=" (Variables|GW|GetDevTestOpen) " page=" (Variables|GW|GetDevTestPage) " phase=" (GW|Get|BP_GW_GameState|Phase :self s) " role=" (GW|Get|BP_GW_PlayerState|GWRole :self ps) " alive=" (GW|Get|BP_GW_PlayerState|IsAlive :self ps) " score=" (GW|Get|BP_GW_PlayerState|GWScore :self ps) " pawn=" (Utilities|GetDisplayName :Object p) " chars=" (Utilities|Array|Length (Actor|GetAllActorsOfClass :ActorClass {CHAR})) " dilation=" (Utilities|Time|GetGlobalTimeDilation) " flags=" (GW|Get|BP_GW_GameState|DevFlags :self s) " hud=[" (select ({ISVALID} :Object (Variables|GW|GetHUDWidget)) (GW|Call|{HUD}|DebugDump :self (Variables|GW|GetHUDWidget)) "") "] msg=" (GW|Get|BP_GW_GameState|LastEvent :self s)) :bPrintToScreen false))
        (:CastFailed)))
    (:CastFailed)))
''',
}
for fn, call in {'DevUp': 'Move :D -1', 'DevDown': 'Move :D 1', 'DevLeft': 'Change :D -1', 'DevRight': 'Change :D 1',
                 'DevAccept': 'Accept', 'DevBack': 'Back'}.items():
    name, _, args = call.partition(' ')
    PCG[fn] = f'''
(fn {fn} ()
  {OPEN}
      (GW|Call|{DM}|{name} :self w {args}))))
'''
if DO_PC:
    write_all(pc, PCG)
    compile_bp(pc, quiet=True)
    gw_lib.wire_input(pc, 'IA_DevMenu', {'Started': 'ToggleDevMenu'}, pos=(0, 2800))
    for k, (ia_name, (_, _, fn)) in enumerate(NAV.items()):
        gw_lib.wire_input(pc, ia_name, {'Started': fn}, pos=(0, 3000 + 200 * k))
    compile_bp(pc)
    print('BP_GW_PlayerController', node_problems(pc))
    save(pc)

# ---------------------------------------------------------------- game mode
if DO_PC:
    write(gm, 'ApplyDevOutfit', '''
    (fn ApplyDevOutfit (PC Ch)
      (bind gpc (Utilities|Casting|CastToBP_GW_PlayerController PC)
        (:then
          (if (>= (GW|Get|BP_GW_PlayerController|DevOutfit :self gpc) 0)
            (GW|Set|BP_GW_Character|OutfitIndex :self Ch :OutfitIndex (GW|Get|BP_GW_PlayerController|DevOutfit :self gpc))))
        (:CastFailed)))
    ''', compile_after=False)
    write(gm, 'DevKillNearestNPC', f'''
    (fn DevKillNearestNPC (Loc)
      (Variables|Default|SetBestD 100000000.0)
      (for a (Actor|GetAllActorsOfClass :ActorClass {CHAR})
        (if (and (not (Pawn|IsPlayerControlled :self a)) (not (GW|Get|BP_GW_Character|IsDead :self a)))
          (bind d (Math|Vector|Distance(Vector) (Transformation|GetActorLocation :self a) Loc))
          (if (< d (Variables|Default|GetBestD))
            (Variables|Default|SetBestD d)
            (Variables|Default|SetBestT a))))
      (bind t (Variables|Default|GetBestT))
      (if ({ISVALID} :Object t)
        (GW|Call|BP_GW_Character|Die :self t :Impulse (* (Math|Vector|Normalize (- (Transformation|GetActorLocation :self t) Loc)) 700.0))
        (Utilities|Array|Add :TargetArray (Variables|GW|GetPendingNPCRespawns) :NewItem (+ (CallFunction|Now) (Variables|GW|GetNPCRespawnDelay)))
        (Development|PrintString :InString (cat "GW: dev killed NPC " (Utilities|GetDisplayName :Object t) " at " (Variables|Default|GetBestD) " cm") :bPrintToScreen false)))
    ''', compile_after=False)
    compile_bp(gm)
    print('BP_GW_GameMode', node_problems(gm))
    save(gm)
