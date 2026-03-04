import requests, json, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

pid = 'd432c0e0-3d68-4a4e-857f-ac28e804b5f3'
r = requests.get(f'http://127.0.0.1:8188/history/{pid}', timeout=10)
data = r.json()

if pid in data:
    entry = data[pid]
    status = entry.get('status', {})
    outputs = entry.get('outputs', {})
    print(f"Status: {status.get('status_str', '?')}")
    print(f"Completed: {status.get('completed', False)}")
    
    if outputs:
        for nid, out in outputs.items():
            for img in out.get('images', []):
                fname = img['filename']
                subfolder = img.get('subfolder', '')
                print(f"Image: {fname}")
                dl = requests.get('http://127.0.0.1:8188/view',
                    params={'filename': fname, 'subfolder': subfolder, 'type': 'output'}, timeout=30)
                if dl.status_code == 200:
                    out_path = r'c:\Users\mana4\Desktop\manaos_integrations\generated_nsfw.png'
                    with open(out_path, 'wb') as f:
                        f.write(dl.content)
                    print(f"Saved: {out_path} ({len(dl.content)} bytes)")
    else:
        print("No outputs yet")
else:
    print(f"Prompt {pid} not in history yet")
    # Check queue
    rq = requests.get('http://127.0.0.1:8188/queue', timeout=5)
    q = rq.json()
    print(f"Running: {len(q.get('queue_running', []))}, Pending: {len(q.get('queue_pending', []))}")
