"""3つの失敗テストを個別回転して出力"""
import subprocess, sys, os

os.chdir(r"C:\Users\mana4\Desktop\manaos_integrations")
venv_python = r"C:\Users\mana4\Desktop\.venv\Scripts\python.exe"

tests = [
    "tests/e2e/test_ultra_integrated.py::test_ultra_integrated_chat_smoke",
    "tests/integration/test_auto_reflection.py::test_statistics",
    "tests/integration/test_drive_indexer.py::test_drive_indexer_smoke",
]

for t in tests:
    print(f"\n=== {t} ===")
    res = subprocess.run(
        [venv_python, "-m", "pytest", t, "--tb=long", "-s", "-q",
         "--override-ini=addopts=--strict-markers --disable-warnings --color=no"],
        capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    out = (res.stdout + res.stderr)
    lines = out.splitlines()
    # Print last 30 lines
    for l in lines[-30:]:
        print(l)
