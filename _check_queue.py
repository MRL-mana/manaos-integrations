import requests, json, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')  # type: ignore[attr-defined]
r = requests.get('http://127.0.0.1:8188/queue', timeout=5)
q = r.json()
running = q.get('queue_running', [])
pending = q.get('queue_pending', [])
print(f"Running: {len(running)}, Pending: {len(pending)}")

r2 = requests.get('http://127.0.0.1:8188/history', timeout=5)
data = r2.json()
print(f"History entries: {len(data)}")
for pid, v in data.items():
    s = v.get('status', {})
    o = v.get('outputs', {})
    has_out = any(out.get('images') for out in o.values())
    print(f"  {pid[:16]}  status={s.get('status_str','?')}  has_output={has_out}")
