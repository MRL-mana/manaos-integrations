"""pytest unit を全件実行して失敗の traceback を取得"""
import subprocess, sys

result = subprocess.run(
    [sys.executable, "-m", "pytest", "tests/unit/", "-p", "no:warnings",
     "--tb=long", "-q",
     "--override-ini=addopts=--strict-markers --disable-warnings --color=no"],
    capture_output=True, text=True, encoding="utf-8", errors="replace",
    cwd=r"C:\Users\mana4\Desktop\manaos_integrations"
)
output = result.stdout + result.stderr
with open("pytest_unit_tb.txt", "w", encoding="utf-8") as f:
    f.write(output)
lines = output.splitlines()
failed = [l for l in lines if l.startswith("FAILED")]
print(f"FAILED: {len(failed)}")
for l in failed:
    print(l)
print("---SUMMARY---")
for l in lines[-3:]:
    print(l)
print(f"\nFull output saved to pytest_unit_tb.txt")
