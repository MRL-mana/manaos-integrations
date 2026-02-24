#!/usr/bin/env python3.10
"""Validate ComfyUI Qwen-Image workflow JSONs"""

import json
from pathlib import Path

workflows_dir = Path("comfyui_workflows")
workflows = sorted(workflows_dir.glob("*.json"))

print("=" * 70)
print("WORKFLOW VALIDATION REPORT")
print("=" * 70)

valid_count = 0
details = []

for wf in workflows:
    try:
        with open(wf, encoding='utf-8', errors='replace') as f:
            data = json.load(f)
        
        # ComfyUI workflows are dicts with numeric string keys (node IDs)
        is_valid = isinstance(data, dict)
        node_keys = [k for k in data.keys() if k.isdigit()]
        
        result = {
            "name": wf.name,
            "status": "✓",
            "size_kb": f"{wf.stat().st_size / 1024:.1f}",
            "nodes": len(node_keys),
        }
        
        # Check for common ComfyUI node types
        node_types = set()
        for node in data.values():
            if isinstance(node, dict) and "class_type" in node:
                node_types.add(node["class_type"])
        
        result["node_types"] = len(node_types)
        result["sample_types"] = list(sorted(node_types))[:3]
        
        details.append(result)
        valid_count += 1
        
    except json.JSONDecodeError as e:
        details.append({
            "name": wf.name,
            "status": "✗",
            "error": f"JSON parse error"
        })
    except Exception as e:
        details.append({
            "name": wf.name,
            "status": "✗",
            "error": str(type(e).__name__)
        })

# Print results
for d in details:
    print(f"\n{d['status']} {d['name']}")
    if d['status'] == '✓':
        print(f"    Size: {d['size_kb']} KB | Nodes: {d['nodes']} | Types: {d['node_types']}")
        if d['sample_types']:
            print(f"    Sample node types: {', '.join(d['sample_types'][:2])}")
    else:
        print(f"    Error: {d.get('error', 'Unknown')}")

print("\n" + "=" * 70)
print(f"RESULT: {valid_count}/{len(workflows)} workflows valid ✓")
print("=" * 70)
