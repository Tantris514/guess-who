"""DSL transpiler extension (no context-pin node creation: that crashed the editor).

Extra node type ids understood by write_graph():
  GW|Get|<BPName>|<Var>    member variable getter on another /Game/GW/Blueprints class (wire :self)
  GW|Set|<BPName>|<Var>    member variable setter on another class (wire :self)
  GW|Call|<BPName>|<Fn>    call a function defined on another class (wire :self)
<BPName> may also be a full class path like /Game/GW/UI/WBP_HUD.WBP_HUD_C.
"""
import unreal
from editor_toolset.toolsets import blueprint_dsl as D
from editor_toolset.toolsets.blueprint import BlueprintTools as BT

BP_DIR = '/Game/GW/Blueprints'
# The generic Modulo operator node does not exist in this engine build: use the integer one.
D._BIN_OPS[D.Symbol('%')] = 'Math|Integer|%(Integer)'


def _class_path(name):
    if name.startswith('/'):
        return name
    return f'{BP_DIR}/{name}.{name}_C'


def create_node(graph, type_id, pos):
    if type_id.startswith('GW|'):
        _, kind, cname, member = type_id.split('|', 3)
        ed = unreal.BlueprintGraphEditor.get_graph_editor(graph)
        cp = _class_path(cname)
        if kind == 'Get':
            node = ed.add_get_member_variable_node(unreal.Name(member), cp)
        elif kind == 'Set':
            node = ed.add_set_member_variable_node(unreal.Name(member), cp)
        elif kind == 'Call':
            node = ed.add_call_function_node(f'{cp}:{member}')
        else:
            raise RuntimeError(f'bad GW node kind {kind}')
        if not isinstance(node, unreal.EdGraphNode):
            raise RuntimeError(f'Could not create {type_id}')
        node.set_node_pos(pos)
        return node
    return BT.create_node(graph, type_id, pos)


def connect_tolerant(out_pin, in_pin):
    out = BT._resolve_pin(out_pin)
    inp = BT._resolve_pin(in_pin)
    if not out.try_create_connection(inp):
        raise RuntimeError(
            f'Could not connect pin {out.get_pin_name()} ({out.get_pin_type_display_string()}) to '
            f'{inp.get_pin_name()} ({inp.get_pin_type_display_string()}) on {inp.get_owning_node().get_node_title()}')


class GWTranspiler(D.Transpiler):
    """Adds (cat a b c ...) -> chained Utilities|String|Append."""

    def _eval_expr(self, expr, bindings, ctx):
        if isinstance(expr, list) and expr and isinstance(expr[0], D.Symbol) and str(expr[0]) == 'cat':
            args = expr[1:]
            if len(args) < 2:
                raise RuntimeError('(cat) needs at least 2 arguments')
            acc = [D.Symbol('Utilities|String|Append'), args[0], args[1]]
            for a in args[2:]:
                acc = [D.Symbol('Utilities|String|Append'), acc, a]
            return super()._eval_expr(acc, bindings, ctx)
        return super()._eval_expr(expr, bindings, ctx)


def write_graph(graph, code, compile_after=True):
    import toolset_registry
    with toolset_registry.tool_raising_exceptions():
        GWTranspiler(
            graph, create_node, connect_tolerant, BT._get_node_info, BT.set_pin_value,
            lambda g: BT.find_nodes(g), delete_node_fn=BT.delete_node,
            find_node_types_fn=lambda f: BT.find_node_types(graph, f)).transpile(code)
    if compile_after:
        bp = unreal.Blueprint.cast(graph.get_outer())
        if bp:
            BT.compile_blueprint(bp)
