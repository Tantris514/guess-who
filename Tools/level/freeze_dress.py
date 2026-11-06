"""Fige la décoration : chaque prop placé par dress.py devient un objet normal qu'on déplace à la main dans l'éditeur,
et plus aucune reconstruction du niveau ne le remet en place.

À lancer UNE fois, éditeur ouvert sur L_Manor : menu Outils (Tools) > Exécuter un script Python (Execute Python
Script...) > ce fichier. Ou, avec l'éditeur partagé : python -I -X utf8 Tools\\ui\\ue_run.py Tools\\level\\freeze_dress.py
Ajouter « dry » (ue_run ... freeze_dress.py dry) compte seulement, sans rien changer.

Ce qu'il fait :
- chaque instance d'un mesh de /Game/GW/Meshes/Props dans les acteurs GW_Dress devient un StaticMeshActor
  (même position, rotation, taille, matériaux, collision), rangé dans le dossier Outliner « Decor_Manuel/<pièce> »,
  avec le tag GW_Manual ; l'instance d'origine est retirée ;
- les pièces procédurales (bibliothèques, bar, bancs en boîtes...) restent comme elles sont ;
- les lumières des lampes restent ; si tu déplaces une lampe, déplace aussi sa lumière (L_Lamp...) ;
- crée Tools/level/dress_frozen.flag : build_manor.py ne régénère plus la décoration (les autres parties oui) ;
- enregistre le niveau.
Les nouveaux props approuvés ne se placent plus tout seuls : glisse-les depuis /Game/GW/Meshes/Props/<nom>/.
Pour revenir à la décoration générée : supprime le dossier Decor_Manuel, supprime dress_frozen.flag, puis relance
bash Tools/level/update_level.sh.
"""
import os
import unreal

DRY = 'dry' in [a.lower() for a in globals().get('UE_ARGS', [])]
FLAG = os.path.join(os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else
                    r'J:\Projets\Unreal_Projects\Guess Who\Tools\level', 'dress_frozen.flag')
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)


def instance_xf(c, i):
    r = c.get_instance_transform(i, True)
    if isinstance(r, tuple):                       # (ok, transform) or (transform, ok) depending on the binding
        return next(x for x in r if isinstance(x, unreal.Transform))
    return r


made = kept = 0
for a in eas.get_all_level_actors():
    tags = [str(t) for t in a.tags]
    if 'GW_Dress' not in tags:
        continue
    group = a.get_actor_label().replace('GW_', '')
    for c in a.get_components_by_class(unreal.InstancedStaticMeshComponent):
        mesh = c.get_editor_property('static_mesh')
        if not mesh or '/GW/Meshes/Props/' not in mesh.get_path_name():
            kept += c.get_instance_count()
            continue
        n = c.get_instance_count()
        if DRY:
            made += n
            continue
        mats = [c.get_material(m) for m in range(c.get_num_materials())]
        profile = c.get_collision_profile_name()
        for i in range(n):
            xf = instance_xf(c, i)
            sa = eas.spawn_actor_from_class(unreal.StaticMeshActor, xf.translation, xf.rotation.rotator())
            sa.set_actor_scale3d(xf.scale3d)
            smc = sa.static_mesh_component
            smc.set_mobility(unreal.ComponentMobility.MOVABLE)
            smc.set_static_mesh(mesh)
            for m, mat in enumerate(mats):
                if mat:
                    smc.set_material(m, mat)
            smc.set_collision_profile_name(profile)
            smc.set_mobility(unreal.ComponentMobility.STATIC)
            sa.set_actor_label(f'{mesh.get_name()}_{made}')
            sa.set_folder_path(f'Decor_Manuel/{group}')
            sa.tags = [unreal.Name('GW_Manual')]
            made += 1
        for i in reversed(range(n)):
            c.remove_instance(i)
    if not DRY:                                    # the rest of the group (lights, procedural pieces) survives rebuilds too
        a.tags = [unreal.Name(t) for t in tags if t not in ('GW_Gen',)] + [unreal.Name('GW_Frozen')]

if DRY:
    print(f'freeze_dress (essai) : {made} props deviendraient déplaçables ; {kept} pièces procédurales restent')
else:
    open(FLAG, 'w', encoding='utf-8').write('decoration figee : voir Tools/level/freeze_dress.py\n')
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    print(f'freeze_dress : {made} props sont maintenant déplaçables (dossier Decor_Manuel) ; niveau enregistré ; '
          f'la décoration ne sera plus régénérée')
