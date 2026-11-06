"""WBP_KeyPrompt: a key cap and a short action label, shown in the world above whatever can be used (piano, barman,
turret, bomb...) by BP_GW_KeyPrompt (a local, non-replicated actor with a screen-space widget component, built by
s33_piano.py). SetPrompt(Key, Label) sets both texts. Usage: ue_run.py u18_key_prompt.py
"""
import sys
sys.path.insert(0, r'J:\Projets\Unreal_Projects\Guess Who\Tools\ui')
import importlib, uilib
importlib.reload(uilib)
from uilib import *

W = get_or_create('WBP_KeyPrompt')
clear_tree(W)
add(W, unreal.CanvasPanel, 'Root')
row = add(W, unreal.HorizontalBox, 'Row', 'Root', var=True)
canvas(row, ((0.5, 0.5), (0.5, 0.5)), (0.5, 0.5), auto=True, z=1)
key = add(W, unreal.Overlay, 'Key', 'Row'); box_slot(key, (0, 0, 10, 0), H.H_ALIGN_LEFT, VA.V_ALIGN_CENTER)
rim = add(W, unreal.Image, 'Rim', 'Key')
rim.widget.set_editor_property('brush', brush(None, (46, 46), 'image', tint=GOLD_HI)); overlay_slot(rim)
face = add(W, unreal.Image, 'Face', 'Key')
face.widget.set_editor_property('brush', brush(None, (40, 40), 'image', tint=(0.02, 0.015, 0.01, 0.9)))
overlay_slot(face, H.H_ALIGN_CENTER, VA.V_ALIGN_CENTER)
kt = add(W, unreal.TextBlock, 'TxtKey', 'Key', var=True)
text(kt, 'E', 'Display', 'Regular', 26, GOLD_HI, just='center'); overlay_slot(kt, H.H_ALIGN_CENTER, VA.V_ALIGN_CENTER)
lb = add(W, unreal.TextBlock, 'TxtLabel', 'Row', var=True)
text(lb, '', 'Serif', 'Bold', 20, IVORY, outline=1); box_slot(lb, (0, 0, 0, 0), H.H_ALIGN_LEFT, VA.V_ALIGN_CENTER)
compile_widget(W)
ensure_fn(W, 'SetPrompt', inputs=[('Key', 'string'), ('Label', 'string')])
compile_bp(W, quiet=True)
write(W, 'SetPrompt', '''
(fn SetPrompt (Key Label)
  (Widget|SetText(Text) :self (Variables|WBP_KeyPrompt|GetTxtLabel) :InText (Utilities|Text|ToText(String) Label))
  (Widget|SetText(Text) :self (Variables|WBP_KeyPrompt|GetTxtKey) :InText (Utilities|Text|ToText(String) Key))
  ; callers pass the default key ("E"): show the one the player chose in the options
  (bind gi (Utilities|Casting|CastToBP_GW_GameInstance (Widget|GetGameInstance))
    (:then (Widget|SetText(Text) :self (Variables|WBP_KeyPrompt|GetTxtKey) :InText (Utilities|Text|ToText(String) (GW|Call|BP_GW_GameInstance|GWKeyLabel :self gi :Key Key))))
    (:CastFailed)))
''', compile_after=False)
compile_bp(W)
print('WBP_KeyPrompt', node_problems(W))
compile_widget(W)
