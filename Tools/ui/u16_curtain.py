"""WBP_Curtain: a black "Le bal se prépare…" screen over the first seconds of the manor, with a progress bar and %.

The first frames after the map loads stall (world setup, then Lumen compute shaders compiled on first use, about 1 s
at ~1.8 s in Tools/qa/pkg_logs/startup.csv). The curtain stays up until the frame rate has settled -- 30 frames in a
row under 33 ms, at least 1.5 s, at most 6 s -- then fades out in 0.6 s and removes itself.
Progress (asked by the user so the wait never looks frozen): the larger of the time used out of the 6 s cap and the
steady frames out of 30 (scaled by the 1.5 s minimum); it never goes back down (a hitch resets the steady count) and
shows 100 % when the fade starts. Added by BP_GW_PlayerController.SetupLocal (s13_pc.py). Usage: ue_run.py u16_curtain.py
"""
import sys
sys.path.insert(0, r'J:\Projets\Unreal_Projects\Guess Who\Tools\ui')
import importlib, uilib
importlib.reload(uilib)
from uilib import *

BAR_W = 420.0
W = get_or_create('WBP_Curtain')
clear_tree(W)
add(W, unreal.CanvasPanel, 'Root')
bg = add(W, unreal.Image, 'Black', 'Root', var=True)
bg.widget.set_editor_property('brush', brush(None, (8, 8), 'image', tint=(0.008, 0.006, 0.005, 1))); canvas(bg, FILL, z=0)
t = add(W, unreal.TextBlock, 'Msg', 'Root', var=True)
text(t, 'Le bal se prépare…', 'Display', 'Regular', 34, GOLD_HI, spacing=400, just='center')
canvas(t, ((0.5, 0.5), (0.5, 0.5)), (0.5, 0.5), pos=(0, -34), auto=True, z=1)
back = add(W, unreal.Image, 'BarBack', 'Root', var=True)
back.widget.set_editor_property('brush', brush(None, (8, 8), 'image', tint=(GOLD[0], GOLD[1], GOLD[2], 0.25)))
canvas(back, ((0.5, 0.5), (0.5, 0.5)), (0.5, 0.5), pos=(0, 22), size=(BAR_W, 3), z=1)
fill = add(W, unreal.Image, 'BarFill', 'Root', var=True)
fill.widget.set_editor_property('brush', brush(None, (8, 8), 'image', tint=GOLD_HI))
canvas(fill, ((0.5, 0.5), (0.5, 0.5)), (0.5, 0.5), pos=(0, 22), size=(BAR_W, 3), z=2)
pivot(fill, 0.0, 0.5)                                  # grows from the left edge
fill.widget.set_editor_property('render_transform', unreal.WidgetTransform(scale=unreal.Vector2D(0.0, 1.0)))
pct = add(W, unreal.TextBlock, 'Pct', 'Root', var=True)
text(pct, '0 %', 'Display', 'Regular', 18, GOLD, spacing=200, just='center')
canvas(pct, ((0.5, 0.5), (0.5, 0.5)), (0.5, 0.5), pos=(0, 50), auto=True, z=1)
compile_widget(W)
for v, typ in (('Age', 'float'), ('SteadyF', 'float'), ('FadeAt', 'float'), ('Shown', 'float')):
    ensure_var(W, v, typ, category='Curtain')
ensure_fn(W, 'CurtainTick', inputs=[('Dt', 'float')])
compile_bp(W, quiet=True)
write(W, 'CurtainTick', f'''
(fn CurtainTick (Dt)
  (Variables|Curtain|SetAge (+ (Variables|Curtain|GetAge) Dt))
  (bind age (Variables|Curtain|GetAge))
  (Variables|Curtain|SetSteadyF (select (< Dt 0.033) (+ (Variables|Curtain|GetSteadyF) 1.0) 0.0))
  (if (and (<= (Variables|Curtain|GetFadeAt) 0.0) (or (> age 6.0) (and (> age 1.5) (>= (Variables|Curtain|GetSteadyF) 30.0))))
    (Variables|Curtain|SetFadeAt age)
    (Development|PrintString :InString (cat "GW: curtain lifts after " age " s") :bPrintToScreen false))
  ; progress: time out of the 6 s cap, or steady frames out of 30 (not before the 1.5 s minimum); never backwards
  (bind est (Math|Float|Max(Float) (/ age 6.0) (* (Math|Float|Min(Float) (/ age 1.5) 1.0) (/ (Variables|Curtain|GetSteadyF) 30.0))))
  (Variables|Curtain|SetShown (select (> (Variables|Curtain|GetFadeAt) 0.0) 1.0 (Math|Float|Min(Float) (Math|Float|Max(Float) (Variables|Curtain|GetShown) est) 0.99)))
  (Widget|Transform|SetRenderScale :self (Variables|WBP_Curtain|GetBarFill) :Scale (Math|Vector2D|MakeVector2D (Variables|Curtain|GetShown) 1.0))
  (Widget|SetText(Text) :self (Variables|WBP_Curtain|GetPct) :InText (Utilities|Text|ToText(String) (cat (Math|Float|Truncate (* (Variables|Curtain|GetShown) 100.0)) " %")))
  (if (> (Variables|Curtain|GetFadeAt) 0.0)
    (bind k (/ (- age (Variables|Curtain|GetFadeAt)) 0.6))
    (Widget|SetRenderOpacity :self self :InOpacity (Math|Float|Max(Float) 0.0 (- 1.0 k)))
    (if (>= k 1.0)
      (Widget|RemovefromParent :self self))))
''', compile_after=False)
write(W, 'EventGraph', '''
(event UserInterface|EventTick (MyGeometry InDeltaTime)
  (CallFunction|CurtainTick :Dt InDeltaTime))
''', compile_after=False)
compile_bp(W)
print('WBP_Curtain', node_problems(W))
compile_widget(W)
