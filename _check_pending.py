import requests, json, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')  # type: ignore[attr-defined]
r = requests.get('http://127.0.0.1:8188/queue', timeout=5)
q = r.json()

running = q.get('queue_running', [])
pending = q.get('queue_pending', [])

print(f"Running: {len(running)}")
for item in running:
    if len(item) > 1:
        print(f"  prompt_id: {item[1]}")
        if len(item) > 2 and isinstance(item[2], dict):
            for nid, node in item[2].items():
                ct = node.get('class_type', '')
                if ct == 'CheckpointLoaderSimple':
                    print(f"    Model: {node['inputs'].get('ckpt_name')}")

print(f"\nPending: {len(pending)}")
for item in pending:
    if len(item) > 1:
        pid = item[1]
        print(f"  prompt_id: {pid}")
        if len(item) > 2 and isinstance(item[2], dict):
            for nid, node in item[2].items():
                ct = node.get('class_type', '')
                if ct == 'CheckpointLoaderSimple':
                    print(f"    Model: {node['inputs'].get('ckpt_name')}")

# Cancel extra pending if they look like duplicates
if len(pending) > 1:
    print(f"\nClearing {len(pending)} pending items to avoid queue buildup...")
    requests.post('http://127.0.0.1:8188/queue', json={'clear': True}, timeout=5)
    print("Queue cleared (keeping running job)")
