"""The score panel's column titles for the last-one-standing rules, on the live WBP_HUD (other scripts add widgets to its tree, so u14's tree part is not re-run for a label)."""
import sys
sys.path.insert(0, r'J:\Projets\Unreal_Projects\Guess Who\Tools\ui')
import importlib, uilib
importlib.reload(uilib)
from uilib import *

W = get_or_create('WBP_HUD')
w = infos(W)
for name, txt in (('ColRoleHdr', 'ÉTAT'), ('ColKillsHdr', 'RIVAUX'), ('ColErrHdr', '')):
    w[name].widget.set_editor_property('text', unreal.Text(txt))
compile_widget(W)
print('headers', [str(w[n].widget.get_editor_property('text')) for n in ('ColRoleHdr', 'ColKillsHdr', 'ColErrHdr')], unreal.EditorAssetLibrary.save_loaded_asset(W))
