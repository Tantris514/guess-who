eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
acts = eas.get_all_level_actors()
isl = [a for a in acts if a.actor_has_tag("GW_Island")]
print("all", len(acts), "island", len(isl))
for a in isl:
    if "Storm" in a.get_actor_label() or "Storm" in a.get_class().get_name():
        print(a.get_actor_label(), a.get_class().get_name(), a.get_editor_property("BoltLux"))
w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
print([l.get_path_name() for l in unreal.EditorLevelUtils.get_levels(w)])
