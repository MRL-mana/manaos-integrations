"""pytest unit tests を全件実行して失敗一覧を出力"""
import subprocess, sys

result = subprocess.run(
    [sys.executable, "-m", "pytest", "tests/unit/", "-p", "no:warnings",
     "--tb=no", "-q",
     "--override-ini=addopts=--strict-markers --disable-warnings --color=no"],
    capture_output=True, text=True, encoding="utf-8", errors="replace",
    cwd=r"C:\Users\mana4\Desktop\manaos_integrations"
)
output = result.stdout + result.stderr
lines = output.splitlines()
failed = [l for l in lines if l.startswith("FAILED")]
print(f"FAILED: {len(failed)}")
for l in failed:
    print(l)
print("---")
for l in lines[-3:]:
    print(l)
