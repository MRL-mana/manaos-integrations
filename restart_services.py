import subprocess
import time
import socket
from pathlib import Path

print('[STOP] Stopping all Python processes...')
subprocess.run(['taskkill', '/F', '/IM', 'python.exe'], capture_output=True)
time.sleep(3)

print('[START] Restarting services...')
subprocess.Popen('python start_vscode_cursor_services.py', shell=True, cwd=str(Path(__file__).resolve().parent))
print('[WAIT] Waiting 45 seconds for startup...')
time.sleep(45)

print('[CHECK] Port status:')
for port in [5105, 5126, 5111, 9510]:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('127.0.0.1', port))
    sock.close()
    status = "Open" if result == 0 else "Closed"
    print('  Port {}: {}'.format(port, status))
