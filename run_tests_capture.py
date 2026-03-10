"""全unit テストを実行して結果を capture するスクリプト"""
import subprocess, sys, os

os.chdir(r"C:\Users\mana4\Desktop\manaos_integrations")

result = subprocess.run(
    [sys.executable, "-m", "pytest", "tests/unit/",
     "-o", "addopts=--strict-markers --disable-warnings --color=no",
     "--tb=short", "-q", "--no-header"],
    capture_output=True, text=True,
    cwd=r"C:\Users\mana4\Desktop\manaos_integrations"
)
out = result.stdout + result.stderr
lines = out.splitlines()
failed = [l for l in lines if l.startswith("FAILED")]

with open("pytest_unit_result.txt", "w", encoding="utf-8") as f:
    f.write(out)

print(f"FAILED count: {len(failed)}")
for l in failed:
    print(l)
print()
print("=== LAST 10 LINES ===")
for l in lines[-10:]:
    print(l)
