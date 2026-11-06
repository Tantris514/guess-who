"""Print the input links of selected nodes in a ComfyUI frontend-format workflow.

  python -I -X utf8 wf_inspect.py WORKFLOW.json [node ids...]
"""
import json
import sys

wf = json.load(open(sys.argv[1], encoding="utf-8"))
nodes = {n["id"]: n for n in wf["nodes"]}
links = {l[0]: l for l in wf["links"]}
ids = [int(x) for x in sys.argv[2:]] or sorted(nodes)
for nid in ids:
    n = nodes.get(nid)
    if not n:
        continue
    srcs = []
    for i in n.get("inputs", []):
        if i.get("link") is not None:
            l = links[i["link"]]
            srcs.append(f"{i['name']} <- {l[1]}:{nodes.get(l[1], {}).get('type', '?')}[{l[2]}]")
    print(nid, n["type"], "|", ", ".join(srcs), "| w=", json.dumps(n.get("widgets_values"))[:90])
print("subgraphs:", [(s.get("name"), len(s.get("nodes", []))) for s in wf.get("definitions", {}).get("subgraphs", [])])
