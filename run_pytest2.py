"""pytest を subprocess で実行して結果ファイルに書き出す"""
import subprocess, sys, os

os.chdir(r"C:\Users\mana4\Desktop\manaos_integrations")

result = subprocess.run(
    [sys.executable, "-m", "pytest", "tests/", "--tb=line", "-q",
     "-p", "no:warnings", "--no-header"],
    capture_output=True, text=True, encoding="utf-8", errors="replace"
)
output = result.stdout + result.stderr
with open("pytest_run2.txt", "w", encoding="utf-8") as f:
    f.write(output)

lines = output.splitlines()
failed = [l for l in lines if l.startswith("FAILED")]
print(f"TOTAL FAILED: {len(failed)}")
for l in failed:
    print(l)
print("---")
for l in lines[-3:]:
    print(l)
print(f"Exit: {result.returncode}")
