"""Node type finder: UE_ARGS = [asset_path, (graph=Name)?, filter|?typeid ...]. '?' prefix dumps the pins of a type id."""
from editor_toolset.toolsets.blueprint import BlueprintTools as BT
args = list(UE_ARGS)
bp = unreal.load_asset(args.pop(0))
gname = 'EventGraph'
if args and args[0].startswith('graph='):
    gname = args.pop(0)[6:]
g = [x for x in BT.list_graphs(bp) if x.get_name() == gname][0]
for f in args:
    if f.startswith('?'):
        try:
            ni = BT.get_node_type_pins(g, f[1:])
            print('PINS', f[1:], '\n  IN :', [(p.name, p.type_id) for p in ni.input_pins], '\n  OUT:', [(p.name, p.type_id) for p in ni.output_pins])
        except Exception as e:
            print('PINS FAIL', f[1:], str(e)[-300:])
    else:
        r = BT.find_node_types(g, f)
        r = [x for x in r if not x.startswith('Utilities|Casting|')] if 'Cast' not in f else r
        print(f'[{f}] ({len(r)}) ->', r[:25])
