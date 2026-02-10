#!/usr/bin/env python3
"""
ComfyUI の nodes/links 形式のワークフローを API 形式（prompt）に変換する。
サブグラフ（UUIDノード）を展開してフラットなAPI形式にマージする。
"""
import json
import sys
from pathlib import Path


def _normalize_links(links_raw):
    """links を [link_id, origin_id, origin_slot, target_id, target_slot] の形で link_by_id にする"""
    link_by_id = {}
    for item in links_raw:
        if isinstance(item, dict):
            link_id = item.get("id")
            o_id, o_slot = item.get("origin_id"), item.get("origin_slot")
            t_id, t_slot = item.get("target_id"), item.get("target_slot")
            if link_id is not None and o_id is not None and o_slot is not None:
                link_by_id[link_id] = (o_id, o_slot)
        elif len(item) >= 5:
            link_id, origin_id, origin_slot = item[0], item[1], item[2]
            link_by_id[link_id] = (origin_id, origin_slot)
    return link_by_id


def _nodes_links_to_prompt(nodes: list, links_raw: list, prefix: str = "") -> dict:
    """nodes + links を API prompt に変換。prefix でノードIDをプレフィックス付きにする"""
    link_by_id = _normalize_links(links_raw)
    prompt = {}
    for node in nodes:
        nid = node.get("id")
        if nid is None:
            continue
        if nid in (-10, -20):
            continue
        nid_str = prefix + str(nid)
        class_type = node.get("type") or ""
        inputs_list = node.get("inputs") or []
        widgets_values = node.get("widgets_values") or []
        inp_dict = {}
        widget_idx = 0
        for inp in inputs_list:
            name = inp.get("name") or inp.get("input_name")
            if not name:
                continue
            if "link" in inp and inp["link"] is not None:
                link_id = inp["link"]
                if link_id in link_by_id:
                    orig_id, orig_slot = link_by_id[link_id]
                    inp_dict[name] = [prefix + str(orig_id), int(orig_slot)]
            else:
                if widget_idx < len(widgets_values):
                    inp_dict[name] = widgets_values[widget_idx]
                    widget_idx += 1
        prompt[nid_str] = {"class_type": class_type, "inputs": inp_dict}
    return prompt


def workflow_to_api(workflow: dict, expand_subgraphs: bool = True) -> dict:
    """
    nodes + links 形式を API prompt 形式に変換する。
    expand_subgraphs が True のとき、サブグラフ（definitions.subgraphs）を展開してマージする。
    """
    nodes = workflow.get("nodes") or []
    links_raw = workflow.get("links") or []
    prompt = _nodes_links_to_prompt(nodes, links_raw)

    if not expand_subgraphs:
        return prompt

    definitions = workflow.get("definitions") or {}
    subgraphs = definitions.get("subgraphs") or []
    subgraph_by_id = {s.get("id"): s for s in subgraphs if s.get("id")}

    # サブグラフノード（class_type が UUID）を展開
    to_remove = []
    to_add = {}
    output_remap = {}  # (uuid_node_id, output_slot) -> (prefixed_origin_id, origin_slot)

    for nid, node in list(prompt.items()):
        ct = node.get("class_type", "")
        if ct not in subgraph_by_id:
            continue
        sub = subgraph_by_id[ct]
        sub_nodes = sub.get("nodes") or []
        sub_links = sub.get("links") or []
        if not sub_nodes:
            continue
        prefix = str(nid) + "_"
        sub_prompt = _nodes_links_to_prompt(sub_nodes, sub_links, prefix=prefix)
        # サブグラフの入力ノード -10 のスロットをメインのこのノードの入力で置き換え
        main_inputs = node.get("inputs") or {}
        sub_inputs = sub.get("inputs") or []
        sub_nodes_by_id = {n.get("id"): n for n in sub_nodes if n.get("id") is not None}
        for link in sub_links:
            if isinstance(link, dict):
                o_id, o_slot = link.get("origin_id"), link.get("origin_slot")
                t_id, t_slot = link.get("target_id"), link.get("target_slot")
            elif len(link) >= 5:
                o_id, o_slot, t_id, t_slot = link[1], link[2], link[3], link[4]
            else:
                continue
            if o_id != -10:
                continue
            if o_slot >= len(sub_inputs):
                continue
            name = sub_inputs[o_slot].get("name")
            if name not in main_inputs:
                continue
            main_val = main_inputs[name]
            target_node = sub_nodes_by_id.get(t_id)
            if not target_node:
                continue
            inps = target_node.get("inputs") or []
            if t_slot >= len(inps):
                continue
            inp_name = inps[t_slot].get("name") or inps[t_slot].get("input_name")
            if not inp_name:
                continue
            key = prefix + str(t_id)
            if key in sub_prompt:
                sub_prompt[key]["inputs"][inp_name] = main_val
        # サブグラフの出力ノード -20: 誰が -20 に繋がっているか
        sub_outputs = sub.get("outputs") or []
        for out_idx in range(len(sub_outputs)):
            for link in sub_links:
                if isinstance(link, dict):
                    if link.get("target_id") == -20 and link.get("target_slot") == out_idx:
                        output_remap[(nid, out_idx)] = (
                            prefix + str(link.get("origin_id")),
                            link.get("origin_slot"),
                        )
                        break
                elif len(link) >= 5 and link[3] == -20 and link[4] == out_idx:
                    output_remap[(nid, out_idx)] = (prefix + str(link[1]), link[2])
                    break
        to_remove.append(nid)
        for k, v in sub_prompt.items():
            if k in (prefix + "-10", prefix + "-20"):
                continue
            to_add[k] = v

    for nid in to_remove:
        prompt.pop(nid, None)
    prompt.update(to_add)

    to_remove_set = set(to_remove)
    for node in prompt.values():
        inp = node.get("inputs") or {}
        for k, v in list(inp.items()):
            if isinstance(v, list) and len(v) == 2 and str(v[0]) in to_remove_set:
                ref_id, slot = str(v[0]), v[1]
                new = (
                    output_remap.get((ref_id, slot))
                    or output_remap.get((ref_id, 0))
                    or output_remap.get((ref_id, 1))
                )
                if new:
                    node["inputs"][k] = list(new)

    return prompt


def main():
    if len(sys.argv) < 2:
        in_path = r"C:\ComfyUI\custom_nodes\ComfyUI-LTXVideo\example_workflows\LTX-2_I2V_Distilled_wLora.json"
        out_path = None
    else:
        in_path = sys.argv[1]
        out_path = sys.argv[2] if len(sys.argv) > 2 else None
    with open(in_path, encoding="utf-8") as f:
        w = json.load(f)
    if "nodes" in w and "links" in w:
        api = workflow_to_api(w, expand_subgraphs=True)
    elif isinstance(w, dict) and all(
        isinstance(v, dict) and "class_type" in v for v in w.values() if isinstance(v, dict)
    ):
        api = w
    else:
        print("Unsupported workflow format", file=sys.stderr)
        return 1
    if out_path:
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(api, f, indent=2, ensure_ascii=False)
        print("Wrote", out_path)
    else:
        print(json.dumps(api, indent=2, ensure_ascii=False)[:2000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
