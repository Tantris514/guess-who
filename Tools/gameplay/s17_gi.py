"""BP_GW_GameInstance: keeps the chosen player name across maps and the last network error for the menu."""
import sys, importlib
sys.path.insert(0, r'J:\Projets\Unreal_Projects\Guess Who\Tools\gameplay')
import gw_lib; importlib.reload(gw_lib)
from gw_lib import *
gi = load_or_create_bp('BP_GW_GameInstance', unreal.GameInstance)
ensure_var(gi, 'PlayerName', 'string', category='GW')
ensure_var(gi, 'LastError', 'string', category='GW')
compile_bp(gi, quiet=True)
write(gi, 'EventGraph', '''
(event EventInit
  (bind cmd (Utilities|GetCommandLine))
  (bind (val found) (Utilities|ParseParamValue :InString cmd :InParam "GWName="))
  (if found
    (Variables|GW|SetPlayerName val)))

(event EventNetworkError (FailureType bIsServer)
  ; the host also gets this when one client times out: only clients go back to the menu with a message
  (if (not bIsServer)
    (Variables|GW|SetLastError "La connexion avec l'hôte a été perdue (ou l'hôte est introuvable).")
    (Development|PrintString :InString "GW: network error (client)" :bPrintToScreen false)))

(event EventTravelError (FailureType)
  (Variables|GW|SetLastError "Impossible de rejoindre la partie : vérifiez l'adresse IP et le port 7777/UDP.")
  (Development|PrintString :InString "GW: travel error" :bPrintToScreen false))
''')
print(node_problems(gi))
save(gi)
