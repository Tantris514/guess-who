"""Non-verbal lines (may repeat with variation): laughs, chuckles, murmurs, sighs, gasps, for every guest voice (direct
VoiceDesign with the voice card + a non-verbal instruction)."""
import sys
from _lib import lines
sys.path.insert(0, __file__.rsplit("\\\\", 2)[0] if "\\\\" in __file__ else "..")
from panic_voices import VOICES

ITEMS = []
STAFF = {"char_barman", "char_junkie", "char_waiter", "char_bandit", "char_bandit2", "char_kamikaze", "char_robot", "char_detective"}
G = [v for v in VOICES if v.startswith("char_") and v not in STAFF]   # the guest characters (voice = character)
LAUGH = {"m": ["Ha ha ha !", "Ho ho ho !", "Ha ha... ha !"], "f": ["Ha ha ha !", "Hi hi hi !", "Ah ha ha !"]}
for i, v in enumerate(G):
    g = VOICES[v][0]
    lines(ITEMS, "laugh", [(g, LAUGH[g][i % 3], "design:laugh", {"voice": v, "nonverbal": True})])
    lines(ITEMS, "laugh", [(g, "Ha ha ha ha !", "design:bigLaugh", {"voice": v, "nonverbal": True})])
    if i % 2 == 0:
        lines(ITEMS, "laugh", [(g, "Hm hm hm.", "design:chuckle", {"voice": v, "nonverbal": True})])
    lines(ITEMS, "murmur", [(g, "Hmm...", "design:murmur", {"voice": v, "nonverbal": True})])
    if i % 2 == 1:
        lines(ITEMS, "murmur", [(g, "Haaah...", "design:sigh", {"voice": v, "nonverbal": True})])
    lines(ITEMS, "gasp", [(g, "Oh !", "design:gasp", {"voice": v, "nonverbal": True})])
