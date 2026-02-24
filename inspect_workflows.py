import json

for wf_name in ["FLUX1_real2.json", "05_wQween-2512-Real-Random2.json"]:
    wf_path = f"comfyui_workflows/{wf_name}"
    with open(wf_path, encoding='utf-8', errors='replace') as f:
        data = json.load(f)
    
    print(f"\n{wf_name}:")
    print(f"  Total keys: {len(data)}")
    if data:
        first_key = list(data.keys())[0]
        first_val = data[first_key]
        print(f"  First key: '{first_key}'")
        print(f"  Type: {type(first_val).__name__}")
        if isinstance(first_val, dict):
            print(f"  Dict keys: {list(first_val.keys())[:8]}")
