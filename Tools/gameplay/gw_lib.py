"""Shared helpers for the gameplay agent's build scripts (run inside the editor via Tools/ue_py.py)."""
import unreal
from editor_toolset.toolsets.blueprint import BlueprintTools as BT, ContainerType

BGE = unreal.BlueprintGraphEditor
EAL = unreal.EditorAssetLibrary
REP = unreal.BlueprintVariableReplication
BP_DIR = '/Game/GW/Blueprints'


def bp_path(name, folder=BP_DIR):
    return f'{folder}/{name}'


def load_bp(name, folder=BP_DIR):
    return unreal.load_asset(bp_path(name, folder))


def load_or_create_bp(name, parent, folder=BP_DIR):
    path = bp_path(name, folder)
    if EAL.does_asset_exist(path):
        return unreal.load_asset(path)
    if isinstance(parent, type):
        parent = parent.static_class()
    bp = BT.create(folder, name, parent)
    print('created', path)
    return bp


def cls(name, folder=BP_DIR):
    bp = load_bp(name, folder)
    return bp.generated_class() if bp else None


def ensure_var(bp, name, type_name=None, rep=None, array=False, obj_class=None, struct=None, category=None):
    """type_name: bool/int/float/string/name/text/Vector/Rotator/LinearColor... or obj_class / struct."""
    cont = ContainerType.ARRAY if array else None
    if name not in BT.list_variables(bp):
        if isinstance(obj_class, type):
            obj_class = obj_class.static_class()
        if obj_class is not None:
            BT.add_object_variable(bp, name, obj_class, container_type=cont)
        elif struct is not None:
            BT.add_struct_variable(bp, name, struct, container_type=cont)
        else:
            BT.add_variable(bp, name, type_name, container_type=cont)
    if rep is not None:
        cur = BT.get_variable_replication(bp, name)
        if cur != rep:
            BT.set_variable_replication(bp, name, rep)
    if category:
        BT.set_variable_category(bp, name, category)


def graph_names(bp):
    return [g.get_name() for g in BT.list_graphs(bp)]


def get_graph(bp, name):
    for g in BT.list_graphs(bp):
        if g.get_name() == name:
            return g
    return None


def _add_param(g, pname, ptype, is_input, array=False):
    cont = ContainerType.ARRAY if array else None
    if isinstance(ptype, str):
        BT.add_function_param(g, pname, ptype, is_input, cont)
    elif isinstance(ptype, unreal.ScriptStruct):
        BT.add_struct_function_param(g, pname, ptype, is_input, cont)
    else:
        if isinstance(ptype, type):
            ptype = ptype.static_class()
        BT.add_object_function_param(g, pname, ptype, is_input, cont)


def ensure_fn(bp, name, inputs=(), outputs=(), exec_fn=False, pure=False, recreate=False):
    """Create (or reuse) a function graph with the given signature.

    inputs/outputs: list of (name, type) where type is a basic type string, a ScriptStruct, a Class,
    or a tuple (type, 'array').
    """
    g = get_graph(bp, name)
    if g is None:
        g = BT.add_function_graph(bp, name)
    for is_in, params in ((True, inputs), (False, outputs)):
        for pname, ptype in params:
            array = False
            if isinstance(ptype, tuple):
                ptype, array = ptype[0], True
            if not BT._param_name_exists(g, pname, is_in):
                _add_param(g, pname, ptype, is_in, array)
    ed = BGE.get_graph_editor(g)
    if exec_fn:
        ed.set_is_exec_function(True)
    if pure:
        ed.set_is_pure_function(True)
    return g


def clean_function_graph(g):
    """Empty a FUNCTION graph before a DSL rewrite. The transpiler only deletes stale nodes unreachable from an exec root,
    so old bodies wired to the entry's parameter pins survived every rewrite (2026-11-02: GameMode.StartEvent had 1054
    nodes, PickSound 703, the GameMode asset 18.6 MB, and compiling it ran the editor out of memory). Keeps the entry
    and result nodes (signature and local variables; links broken). Event graphs are shared by several scripts
    (wire_input, events) and are never emptied here."""
    nodes = list(BT.find_nodes(g))
    if not any(n.get_class().get_name() == 'K2Node_FunctionEntry' for n in nodes):
        return 0
    k = 0
    for node in nodes:
        if node.get_class().get_name() in ('K2Node_FunctionEntry', 'K2Node_FunctionResult'):
            for p in node.list_all_pins():
                for c in list(p.list_connected_pins()):
                    p.break_single_pin_link(c)
            continue
        BT.delete_node(node)
        k += 1
    return k


def write(bp, graph_name, code, compile_after=True):
    import gw_dsl, importlib
    importlib.reload(gw_dsl)
    g = get_graph(bp, graph_name)
    assert g is not None, f'no graph {graph_name} in {bp.get_name()}'
    if graph_name != 'EventGraph':
        clean_function_graph(g)
    try:
        gw_dsl.write_graph(g, code, compile_after)
    except Exception as e:
        msg = str(e)
        print(f'DSL ERROR in {bp.get_name()}.{graph_name}: {msg[-1500:]}')
        raise


def compile_bp(bp, quiet=False):
    try:
        BT.compile_blueprint(bp)
        if not quiet:
            print('compiled OK', bp.get_name())
        return True
    except Exception as e:
        print('COMPILE FAILED', bp.get_name(), str(e)[-2500:])
        return False


def node_problems(bp):
    out = []
    for g in BT.list_graphs(bp):
        ed = BGE.get_graph_editor(g)
        if not ed:
            continue
        for kind, fn in (('ERR', ed.list_nodes_with_errors), ('WARN', ed.list_nodes_with_warnings)):
            try:
                for n in fn():
                    out.append(f'{kind} {g.get_name()}: {n.get_node_title()} :: {n.get_editor_property("error_msg") if hasattr(n, "get_editor_property") else ""}')
            except Exception as e:
                out.append(f'{kind}? {g.get_name()}: {e}')
    return out


def save(*assets):
    for a in assets:
        EAL.save_loaded_asset(a, only_if_is_dirty=False)


def find_types(bp, flt, graph='EventGraph', limit=60):
    g = get_graph(bp, graph)
    res = BT.find_node_types(g, flt)
    return res[:limit]


def pins(bp, type_id, graph='EventGraph'):
    g = get_graph(bp, graph)
    ni = BT.get_node_type_pins(g, type_id)
    ins = [(p.name, p.type_id) for p in ni.input_pins]
    outs = [(p.name, p.type_id) for p in ni.output_pins]
    return ins, outs


def cdo(bp):
    return unreal.get_default_object(bp.generated_class())


def subobjects(bp):
    sub = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    lib = unreal.SubobjectDataBlueprintFunctionLibrary
    out = {}
    for h in sub.k2_gather_subobject_data_for_blueprint(bp):
        d = sub.k2_find_subobject_data_from_handle(h)
        out[str(lib.get_variable_name(d))] = (h, d)
    return out


def ensure_component(bp, name, comp_class, parent_var):
    """Adds an SCS component (child of parent_var) if missing; returns the component template."""
    sub = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    lib = unreal.SubobjectDataBlueprintFunctionLibrary
    objs = subobjects(bp)
    if name not in objs:
        if isinstance(comp_class, type):
            comp_class = comp_class.static_class()
        parent_h = objs[parent_var][0]
        params = unreal.AddNewSubobjectParams(parent_handle=parent_h, new_class=comp_class, blueprint_context=bp)
        h, reason = sub.add_new_subobject(params)
        if not lib.is_handle_valid(h):
            raise RuntimeError(f'add component {name} failed: {reason}')
        sub.rename_subobject(h, unreal.Text(name))
        objs = subobjects(bp)
    return lib.get_object(objs[name][1])


def _pin(node, name, direction):
    for p in node.list_all_pins():
        if p.get_pin_direction() == direction and str(p.get_pin_name()) == name:
            return p
    return None


def wire_input(bp, ia_name, mapping, pos=(0, 2400), args=None):
    """Enhanced Input event node for ia_name; mapping {exec_pin: function_name}; args {fn: {param: data_pin}}."""
    IN, OUT = unreal.EdGraphPinDirection.EGPD_INPUT, unreal.EdGraphPinDirection.EGPD_OUTPUT
    g = get_graph(bp, 'EventGraph')
    ed = BGE.get_graph_editor(g)
    node = None
    for n in BT.find_nodes(g):
        if n.get_class().get_name() == 'K2Node_EnhancedInputAction' and BT.get_node_infos([n])[0].type_id.endswith(ia_name):
            node = n
    if node is None:
        node = BT.create_node(g, f'Input|EnhancedActionEvents|{ia_name}', unreal.IntPoint(*pos))
    args = args or {}
    for k, (exec_name, fn) in enumerate(mapping.items()):
        ep = _pin(node, exec_name, OUT)
        assert ep is not None, f'{ia_name} has no exec pin {exec_name}'
        if any(c.get_owning_node().get_node_title().replace(' ', '') == fn for c in ep.list_connected_pins()):
            continue
        for c in list(ep.list_connected_pins()):
            ep.break_single_pin_link(c)
        call = ed.add_call_function_node(fn)
        assert call is not None, f'no function {fn}'
        p = node.get_node_pos()
        call.set_node_pos(unreal.IntPoint(p.x + 400, p.y + 160 * k))
        assert ep.try_create_connection(_pin(call, 'execute', IN)), 'exec connect failed'
        for param, data_pin in args.get(fn, {}).items():
            src = _pin(node, data_pin, OUT)
            assert src.try_create_connection(_pin(call, param, IN)), f'data connect {data_pin}->{param} failed'
    return node
