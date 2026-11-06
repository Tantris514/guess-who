"""Shared Blueprint DSL snippets for the ui widgets (procedural animation: no UMG animation assets needed).

Every widget that uses them gets variables T (float), Btns (Button array), BtnHov (float array) and the functions
C01 (clamp 0..1), Ease (smoothstep), AddBtn (register a button), AnimButtons (hover scale on every registered button).
"""
import unreal
from uilib import ensure_var, ensure_fn, write

FUNCS = {
    'C01': '''
(fn C01 (V)
  (return (Math|Float|Max(Float) 0.0 (Math|Float|Min(Float) V 1.0))))
''',
    'Ease': '''
(fn Ease (V)
  (bind c (Math|Float|Max(Float) 0.0 (Math|Float|Min(Float) V 1.0)))
  (return (* (* c c) (- 3.0 (* 2.0 c)))))
''',
    'AddBtn': '''
(fn AddBtn (B)
  (Utilities|Array|Add :TargetArray (Variables|UI|GetBtns) :NewItem B)
  (Utilities|Array|Add :TargetArray (Variables|UI|GetBtnHov) :NewItem 0.0))
''',
    'AnimButtons': '''
(fn AnimButtons (Dt)
  (bind btns (Variables|UI|GetBtns))
  (for i (range (Utilities|Array|Length btns))
    (bind b (Utilities|Array|Get(acopy) btns i))
    (bind h0 (Utilities|Array|Get(acopy) (Variables|UI|GetBtnHov) i))
    (bind h (Math|Interpolation|FInterpTo :Current h0 :Target (select (and (Widget|IsHovered :self b) (Widget|GetIsEnabled :self b)) 1.0 0.0) :DeltaTime Dt :InterpSpeed 14.0))
    (Utilities|Array|SetArrayElem :TargetArray (Variables|UI|GetBtnHov) :Index i :Item h)
    (bind s (+ 1.0 (* h 0.035)))
    (Widget|Transform|SetRenderScale :self b :Scale (Math|Vector2D|MakeVector2D s s))))
''',
}
SIGS = {
    'C01': ([('V', 'float')], [('R', 'float')]),
    'Ease': ([('V', 'float')], [('R', 'float')]),
    'AddBtn': ([('B', unreal.Button)], []),
    'AnimButtons': ([('Dt', 'float')], []),
}


def install(wbp):
    ensure_var(wbp, 'T', 'float', category='UI')
    ensure_var(wbp, 'Btns', obj_class=unreal.Button, array=True, category='UI')
    ensure_var(wbp, 'BtnHov', 'float', array=True, category='UI')
    for name, (ins, outs) in SIGS.items():
        ensure_fn(wbp, name, inputs=ins, outputs=outs, pure=name in ('C01', 'Ease'))


def write_all(wbp):
    for name, code in FUNCS.items():
        write(wbp, name, code, compile_after=False)
