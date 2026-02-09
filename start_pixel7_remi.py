"""
Pixel 7 Remi - Auto Start Script
PC起動時に全サービスを立ち上げる
"""
import subprocess
import time
import sys
import os
import urllib.request
import json

SERVICES = [
    {
        "name": "Open WebUI (Docker)",
        "check_url": "http://localhost:3001",
        "start_cmd": None,  # Already in docker-compose
    },
    {
        "name": "VOICEVOX (Docker)",
        "check_url": "http://localhost:50021/version",
        "start_cmd": None,  # Already in docker-compose
    },
    {
        "name": "Local Remi API",
        "check_url": "http://localhost:5050/health",
        "start_cmd": [sys.executable, os.path.join(os.path.dirname(__file__), "local_remi_api.py")],
    },
]

COMPOSE_FILE = os.path.join(os.path.dirname(__file__), "docker-compose.always-ready-llm.yml")


def check_service(url, timeout=3):
    try:
        req = urllib.request.urlopen(url, timeout=timeout)
        return req.status == 200
    except Exception:
        return False


def start_docker_services():
    print("[*] Starting Docker services...")
    subprocess.run(
        ["docker-compose", "-f", COMPOSE_FILE, "up", "-d", "openwebui", "voicevox"],
        capture_output=True, text=True
    )
    # Inject voice script
    time.sleep(5)
    subprocess.run([
        "docker", "exec", "open-webui",
        "sh", "-c",
        "grep -q 'voice.js' /app/build/index.html || sed -i 's|</head>|<script src=\"/static/voice.js\"></script></head>|' /app/build/index.html"
    ], capture_output=True, text=True)
    print("[+] Docker services started, voice script injected")


def start_remi_api():
    print("[*] Starting Local Remi API...")
    env = os.environ.copy()
    env["REMI_API_TOKEN"] = os.getenv("REMI_API_TOKEN", "remi-pixel7-2026")
    subprocess.Popen(
        [sys.executable, os.path.join(os.path.dirname(__file__), "local_remi_api.py")],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env=env,
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
    )
    print("[+] Remi API started on port 5050")


def main():
    print("=" * 50)
    print("  Pixel 7 Remi - Service Startup")
    print("=" * 50)
    print()

    # 1. Docker services
    start_docker_services()

    # 2. Wait for Docker services
    print("\n[*] Waiting for services...")
    for i in range(30):
        owui_ok = check_service("http://localhost:3001")
        vv_ok = check_service("http://localhost:50021/version")
        if owui_ok and vv_ok:
            break
        time.sleep(2)

    # 3. Remi API (host)
    if not check_service("http://localhost:5050/health"):
        start_remi_api()
        time.sleep(3)

    # 4. Status check
    print("\n" + "=" * 50)
    print("  Service Status")
    print("=" * 50)
    for svc in SERVICES:
        ok = check_service(svc["check_url"])
        status = "OK" if ok else "NG"
        icon = "[+]" if ok else "[-]"
        print(f"  {icon} {svc['name']}: {status}")

    print()
    print("  Dashboard: http://100.73.247.100:5050/dashboard")
    print("  Chat:      http://100.73.247.100:3001")
    print("  VOICEVOX:  http://100.73.247.100:50021")
    print("=" * 50)


if __name__ == "__main__":
    main()
