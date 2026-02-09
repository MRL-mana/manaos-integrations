"""Remi API quick system check."""
import urllib.request
import json

BASE = "http://127.0.0.1:5050"
TOKEN = "remi-pixel7-2026"
results = []
VERSION = "4.1.0"  # Updated with security fixes

def check(name, path, method="GET", need_auth=True, body=None, timeout=5):
    url = BASE + path
    headers = {}
    if need_auth:
        headers["Authorization"] = f"Bearer {TOKEN}"
    if body:
        headers["Content-Type"] = "application/json"
    try:
        data = json.dumps(body).encode() if body else None
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            ct = resp.headers.get("Content-Type", "")
            if "json" in ct:
                result = json.loads(resp.read().decode())
            else:
                result = resp.read().decode()
            results.append((name, "OK", resp.status))
            return result
    except Exception as e:
        err = str(e).split("\n")[0][:60]
        results.append((name, "FAIL", err))
        return None

# Tests
print("Running Remi system checks...\n")

check("Health", "/health", need_auth=False)

r = check("Status", "/status")
if r:
    g = r.get("gpu", {})
    print(f"  GPU: {g.get('name')} VRAM:{g.get('vram_used_gb')}/{g.get('vram_total_gb')}GB")
    print(f"  CPU:{r.get('cpu',{}).get('percent')}% RAM:{r.get('memory',{}).get('percent')}% Disk:{r.get('disk',{}).get('percent')}%")
    print(f"  Docker:{len(r.get('docker',{}).get('containers',[]))} Ollama:{len(r.get('ollama',{}).get('models',[]))}")

check("Actions", "/actions")
check("Suggestions", "/suggestions")
check("Notifications", "/notifications")
check("Chat history", "/chat/history")
check("TTS speakers", "/tts/speakers")

h = check("Dashboard", "/dashboard", need_auth=False)
if h and isinstance(h, str):
    print(f"  URL token: {'YES' if '_urlToken' in h else 'NO'} | Voice: {'YES' if 'webkitSpeech' in h else 'NO'}")

h = check("Widget", "/widget?token=" + TOKEN, need_auth=False)

print("  Testing Ollama chat (30s timeout)...")
r = check("Chat/Ollama", "/chat?message=hi", method="POST", timeout=30)
if r and isinstance(r, dict):
    print(f"  Response: {str(r.get('reply',''))[:50]}")

r = check("TTS/VOICEVOX", "/tts?text=ok&speaker=0", method="POST", timeout=15)
if r is None:
    # Check if it failed because WAV binary was returned (which is success)
    last = results[-1]
    if "codec" in str(last[2]) or "decode" in str(last[2]):
        results[-1] = ("TTS/VOICEVOX", "OK", "WAV audio returned")
        print("  TTS OK (WAV audio stream)")

# Summary
print("\n" + "=" * 50)
ok = sum(1 for _, s, _ in results if s == "OK")
ng = sum(1 for _, s, _ in results if s == "FAIL")
for name, status, detail in results:
    icon = "OK" if status == "OK" else "NG"
    print(f"  [{icon}] {name}: {detail}")
print(f"\n  {ok} OK / {ng} FAIL")
if ng == 0:
    print("  ALL SYSTEMS GO!")
