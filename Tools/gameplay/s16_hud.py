"""WBP_HUD graphs: Refresh(PC) reads GameState/PlayerState and fills the French HUD."""
import sys, importlib
sys.path.insert(0, r'J:\Projets\Unreal_Projects\Guess Who\Tools\gameplay')
import gw_lib; importlib.reload(gw_lib)
from gw_lib import *

hud = unreal.load_asset('/Game/GW/UI/WBP_HUD')
ISVALID = 'GW|Call|/Script/Engine.KismetSystemLibrary|IsValid'


def local(fn, name, typ):
    g = get_graph(hud, fn)
    if name not in BT.list_variables(hud, g):
        BT.add_variable(hud, name, typ, graph=g)


for n in ['RoleT', 'InfoT', 'TimerT', 'CenterT', 'EventT']:
    local('RefreshWith', n, 'string')
local('BuildScores', 'Acc', 'string')


def gs(v):
    return f'(GW|Get|BP_GW_GameState|{v} :self GS)'


def txt(widget, expr):
    return f'(Widget|SetText(Text) :self (Variables|WBP_HUD|Get{widget}) :InText (Utilities|Text|ToText(String) {expr}))'


W = {}
W['ShowW'] = '''
(fn ShowW (W Show)
  (if Show
    (Widget|SetVisibility :self W :InVisibility "HitTestInvisible")
    (else
      (Widget|SetVisibility :self W :InVisibility "Hidden"))))
'''
W['HealthOf'] = '''
(fn HealthOf (PC)
  (bind ch (Utilities|Casting|CastToBP_GW_Character (Pawn|GetControlledPawn :self PC))
    (:then (return (GW|Get|BP_GW_Character|Health :self ch)))
    (:CastFailed (return -1.0))))
'''
W['FormatTime'] = '''
(fn FormatTime (Seconds)
  (bind total (Math|Float|Truncate (+ Seconds 0.999)))
  (bind s (% total 60))
  (return (cat (/ total 60) (select (< s 10) ":0" ":") s)))
'''
W['BuildScores'] = f'''
(fn BuildScores ()
  (Variables|Default|SetAcc (cat (Utilities|String|RightPad :SourceString "JOUEUR" :ChCount 18) (Utilities|String|RightPad :SourceString "RÔLE" :ChCount 11) (Utilities|String|RightPad :SourceString "SCORE" :ChCount 7) (Utilities|String|RightPad :SourceString "DÉMASQUÉS" :ChCount 11) "ERREURS"))
  (for p (Class|GameStateBase|GetPlayerArray :self (Game|GetGameState))
    (bind ps (Utilities|Casting|CastToBP_GW_PlayerState p)
      (:then
        (bind role (GW|Get|BP_GW_PlayerState|GWRole :self ps))
        (Variables|Default|SetAcc (cat (Variables|Default|GetAcc) "
" (Utilities|String|RightPad :SourceString (Utilities|String|Left :SourceString (PlayerState|GetPlayerName :self ps) :Count 16) :ChCount 18) (Utilities|String|RightPad :SourceString (select (== role 2) "Détective" (select (== role 1) "Invité" "—")) :ChCount 11) (Utilities|String|RightPad :SourceString (Utilities|String|ToString(Integer) (GW|Get|BP_GW_PlayerState|GWScore :self ps)) :ChCount 7) (Utilities|String|RightPad :SourceString (Utilities|String|ToString(Integer) (GW|Get|BP_GW_PlayerState|Kills :self ps)) :ChCount 11) (GW|Get|BP_GW_PlayerState|Mistakes :self ps) (select (GW|Get|BP_GW_PlayerState|IsAlive :self ps) "" "   (éliminé)"))))
      (:CastFailed)))
  (return (Variables|Default|GetAcc)))
'''
W['DebugDump'] = '''
(fn DebugDump ()
  (return (cat "role=" (Utilities|String|ToString(Text) (Widget|GetText(Text) :self (Variables|WBP_HUD|GetTxtRole))) " | timer=" (Utilities|String|ToString(Text) (Widget|GetText(Text) :self (Variables|WBP_HUD|GetTxtTimer))) " | " (Utilities|String|ToString(Text) (Widget|GetText(Text) :self (Variables|WBP_HUD|GetTxtHiders))) " | " (Utilities|String|ToString(Text) (Widget|GetText(Text) :self (Variables|WBP_HUD|GetTxtHealth))) " | center=" (Utilities|String|ToString(Text) (Widget|GetText(Text) :self (Variables|WBP_HUD|GetTxtCenter))) " | event=" (Utilities|String|ToString(Text) (Widget|GetText(Text) :self (Variables|WBP_HUD|GetTxtEvent))) " | blind=" (Widget|IsVisible :self (Variables|WBP_HUD|GetBlindfold)) " cross=" (Widget|IsVisible :self (Variables|WBP_HUD|GetCrosshair)) " scores=" (Widget|IsVisible :self (Variables|WBP_HUD|GetScorePanel)) " | info=" (Utilities|String|ToString(Text) (Widget|GetText(Text) :self (Variables|WBP_HUD|GetTxtInfo))))))
'''
W['Refresh'] = '''
(fn Refresh (PC ShowScores)
  (bind gsx (Utilities|Casting|CastToBP_GW_GameState (Game|GetGameState))
    (:then
      (bind psx (Utilities|Casting|CastToBP_GW_PlayerState (GW|Get|/Script/Engine.Controller|PlayerState :self PC))
        (:then
          (CallFunction|RefreshWith :GS gsx :PS psx :PC PC :ShowScores ShowScores))
        (:CastFailed)))
    (:CastFailed)))
'''
W['RefreshWith'] = f'''
(fn RefreshWith (GS PS PC ShowScores)
  (bind phase {gs('Phase')})
  (bind role (GW|Get|BP_GW_PlayerState|GWRole :self PS))
  (bind alive (GW|Get|BP_GW_PlayerState|IsAlive :self PS))
  (bind now (GameState|GetServerWorldTimeSeconds :self GS))
  (bind rem (Math|Float|Max(Float) (- {gs('PhaseEndTime')} now) 0.0))
  (bind remS (Math|Float|Truncate (+ rem 0.999)))
  (bind np (Utilities|Array|Length (Class|GameStateBase|GetPlayerArray :self GS)))
  (bind isSeeker (== role 2))
  (bind playing (or (== phase 1) (== phase 2)))
  (bind ghost (and playing (or (not alive) (== role 0))))
  (bind winner {gs('Winner')})
  (if (== phase 0)
    (Variables|Default|SetRoleT "SALLE D'ATTENTE")
    (elif ghost
      (Variables|Default|SetRoleT (select (== role 0) "SPECTATEUR" "FANTÔME"))
      (elif isSeeker
        (Variables|Default|SetRoleT "DÉTECTIVE")
        (else
          (Variables|Default|SetRoleT "INVITÉ")))))
  (if (== phase 0)
    (Variables|Default|SetInfoT (select (< np 2) "En attente d'un autre joueur (2 minimum). Promenez-vous parmi les invités en attendant." (cat "Assez de joueurs ! La partie commence dans " remS " s.")))
    (elif (== phase 3)
      (Variables|Default|SetInfoT {gs('Message')})
      (elif ghost
        (Variables|Default|SetInfoT (select (== role 0) "Partie en cours : vous jouerez à la prochaine manche. Volez librement (WASD + souris)." "Vous êtes éliminé. Volez librement (WASD + souris) et observez la fin de la manche."))
        (elif isSeeker
          (Variables|Default|SetInfoT (select (== phase 1) "Les invités se dispersent pendant que vous avez les yeux bandés. Patience…" "Repérez les joueurs déguisés et tirez (clic gauche). Chaque innocent abattu vous coûte 25 PV."))
          (else
            (Variables|Default|SetInfoT (select (== phase 1) "Fondez-vous dans la foule ! Marchez, flânez et arrêtez-vous comme les autres invités." "Les détectives vous cherchent. Restez naturel : courir (Maj) est louche !")))))))
  (if (== phase 1)
    (Variables|Default|SetTimerT (cat "Cachette   " (CallFunction|FormatTime :Seconds rem)))
    (elif (== phase 2)
      (Variables|Default|SetTimerT (cat "Chasse   " (CallFunction|FormatTime :Seconds rem)))
      (elif (== phase 3)
        (Variables|Default|SetTimerT (cat "Manche suivante dans " remS " s"))
        (else
          (Variables|Default|SetTimerT "")))))
  (if (== phase 3)
    (Variables|Default|SetCenterT (select (== winner 1) "LES DÉTECTIVES ONT GAGNÉ" (select (== winner 2) "LES INVITÉS ONT GAGNÉ" "MANCHE ANNULÉE")))
    (else
      (Variables|Default|SetCenterT "")))
  (Variables|Default|SetEventT (select (and (< (- now {gs('LastEventTime')}) 4.0) (!= phase 3)) {gs('LastEvent')} ""))
  (if (< (- (Utilities|Time|GetRealTimeSeconds) (Variables|GW|GetLocalNoticeTime)) 3.0)
    (Variables|Default|SetEventT (Variables|GW|GetLocalNotice)))
  {txt('TxtRole', '(Variables|Default|GetRoleT)')}
  {txt('TxtInfo', '(Variables|Default|GetInfoT)')}
  {txt('TxtTimer', '(Variables|Default|GetTimerT)')}
  {txt('TxtCenter', '(Variables|Default|GetCenterT)')}
  {txt('TxtEvent', '(Variables|Default|GetEventT)')}
  {txt('TxtHiders', '(select playing (cat "Invités-joueurs restants : " ' + gs('HidersAlive') + ' "     Détectives : " ' + gs('SeekersAlive') + ') "")')}
  {txt('TxtHealth', '(select (and isSeeker (and alive playing)) (cat "Santé : " (Math|Float|Round (CallFunction|HealthOf :PC PC)) " / 100") "")')}
  (bind blind (and isSeeker (and alive (== phase 1))))
  (CallFunction|ShowW :W (Variables|WBP_HUD|GetBlindfold) :Show blind)
  (if blind
    {txt('BlindText', '(cat "Vous avez les yeux bandés…    La chasse commence dans " remS " s")')})
  (CallFunction|ShowW :W (Variables|WBP_HUD|GetCrosshair) :Show (and isSeeker (and alive (== phase 2))))
  (bind scores (or ShowScores (== phase 3)))
  (CallFunction|ShowW :W (Variables|WBP_HUD|GetScorePanel) :Show scores)
  (if scores
    (bind sc (CallFunction|BuildScores))
    {txt('TxtScores', 'sc')}))
'''

only = UE_ARGS[0] if UE_ARGS else None
for name, code in W.items():
    if only and name != only:
        continue
    write(hud, name, code, compile_after=False)
    print('wrote', name)
compile_bp(hud)
print(node_problems(hud))
save(hud)
