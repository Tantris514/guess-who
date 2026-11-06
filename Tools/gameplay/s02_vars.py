import sys, importlib
sys.path.insert(0, r'J:\Projets\Unreal_Projects\Guess Who\Tools\gameplay')
import gw_lib; importlib.reload(gw_lib)
from gw_lib import *
R, N = REP.REPLICATED, REP.REP_NOTIFY
ps = load_bp('BP_GW_PlayerState')
for n, t in [('GWRole','int'),('IsAlive','bool'),('GWScore','int'),('SeekCount','int'),('Kills','int'),('Mistakes','int')]:
    ensure_var(ps, n, t, R, category='GW')
gs = load_bp('BP_GW_GameState')
for n, t in [('Phase','int'),('PhaseEndTime','float'),('HidersAlive','int'),('SeekersAlive','int'),('Winner','int'),('RoundNumber','int'),('Message','string')]:
    ensure_var(gs, n, t, R, category='GW')
for bp in (ps, gs):
    compile_bp(bp); save(bp)
