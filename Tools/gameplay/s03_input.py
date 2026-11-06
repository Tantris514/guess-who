import unreal
EAL = unreal.EditorAssetLibrary
at = unreal.AssetToolsHelpers.get_asset_tools()
def mk(name, cls, factory):
    p = f'/Game/GW/Input/{name}'
    if EAL.does_asset_exist(p):
        return unreal.load_asset(p)
    return at.create_asset(name, '/Game/GW/Input', cls, factory)
acts = {}
for n in ['IA_Fire', 'IA_Sprint', 'IA_Scoreboard', 'IA_Menu']:
    acts[n] = mk(n, unreal.InputAction, unreal.InputAction_Factory())
    print(n, acts[n].get_editor_property('value_type'))
imc = mk('IMC_GW', unreal.InputMappingContext, unreal.InputMappingContext_Factory())
def key(n):
    k = unreal.Key()
    k.set_editor_property('key_name', n)
    return k
existing = [ (m.action.get_name() if m.action else None) for m in imc.get_editor_property('default_key_mappings').get_editor_property('mappings')] if hasattr(imc,'get_editor_property') else []
print('existing', existing)
for a, k in [('IA_Fire','LeftMouseButton'), ('IA_Sprint','LeftShift'), ('IA_Scoreboard','Tab'), ('IA_Menu','Escape')]:
    if a not in existing:
        imc.map_key(acts[a], key(k))
for a in list(acts.values()) + [imc]:
    EAL.save_loaded_asset(a, False)
print([ (m.action.get_name(), str(m.key.get_editor_property('key_name'))) for m in imc.get_editor_property('default_key_mappings').get_editor_property('mappings')])
