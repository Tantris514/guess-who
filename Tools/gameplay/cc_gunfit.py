"""Recompute only the revolver's hand fit (BP_GW_Character FitRels entry of RevolverMesh) with s25's own fit() code.

s25_costume_import.py (coordinator's) is the source of truth for the fit maths; a full s25 run also rebuilds every pool
and the GM's NumOutfits, so for the gun alone this runs s25's definitions (up to its main body) and rewrites one
FitRels entry. The detective's GunMesh (s26 ApplySlot) and the shop's BP_GW_GuestGun read that entry at attach time.
Usage: ue_run.py cc_gunfit.py ['{"revolver": {"tilt": 35, "along": 0.4}}']   (camera & combat agent)"""
import unreal, json

P = r'J:\Projets\Unreal_Projects\Guess Who\Tools\gameplay\s25_costume_import.py'
src = open(P, encoding='utf-8').read()
head = src.split('# ---------------------------------------------------------------------------------------------------------\nch = load_bp(', 1)[0]
g = {'__name__': '__main__', 'unreal': unreal, 'UE_ARGS': UE_ARGS, '__file__': P}
exec(compile(head, P + ' (definitions)', 'exec'), g)
ch = g['load_bp']('BP_GW_Character')
c = g['cdo'](ch)
rev = c.get_editor_property('RevolverMesh')
meshes = list(c.get_editor_property('FitMeshes'))
rels = list(c.get_editor_property('FitRels'))
bones = list(c.get_editor_property('FitBones'))
i = meshes.index(rev)
entry = next((a for a in g['MAN']['assets'] if a.get('name') == 'revolver'), None)
name = rev.get_name()
b, rel, body = g['fit']('revolver', rev, 'revolver', entry)
print('revolver fit', i, 'bone', bones[i], '->', b, 'old', rels[i].translation, rels[i].rotation.rotator(),
      'new', rel.translation, rel.rotation.rotator(), rel.scale3d)
rels[i] = rel
bones[i] = unreal.Name(b)
c.set_editor_property('FitRels', rels)
c.set_editor_property('FitBones', bones)
g['compile_bp'](ch)
g['save'](ch)
