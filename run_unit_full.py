"""
全 unit テストを --maxfail なし --tb=long で実行し、結果を2つのファイルに保存するスクリプト
"""
import subprocess, sys, os

os.chdir(r"C:\Users\mana4\Desktop\manaos_integrations")

result = subprocess.run(
    [sys.executable, "-m", "pytest", "tests/unit/",
     "-o", "addopts=--strict-markers --disable-warnings --color=no",
     "--tb=long", "-q", "--no-header"],
    capture_output=True, text=True,
    cwd=r"C:\Users\mana4\Desktop\manaos_integrations",
    timeout=600
)
full_output = result.stdout + result.stderr

# 保存
with open("pytest_unit_full.txt", "w", encoding="utf-8") as f:
    f.write(full_output)

lines = full_output.splitlines()
failed = [l for l in lines if l.startswith("FAILED")]
print(f"Exit code: {result.returncode}")
print(f"FAILED count: {len(failed)}")
for l in failed:
    print(l)
print()
print("=== LAST 10 ===")
for l in lines[-10:]:
    print(l)
