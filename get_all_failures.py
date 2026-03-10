"""全テスト失敗を収集してファイルに保存"""
import subprocess, sys, os

os.chdir(r"C:\Users\mana4\Desktop\manaos_integrations")
result = subprocess.run(
    [sys.executable, "-m", "pytest", "tests/", "--tb=short", "-q",
     "--no-header", "-p", "no:warnings", "--override-ini=addopts="],
    capture_output=True, text=True, encoding="utf-8", errors="replace"
)
output = result.stdout + result.stderr

with open("all_failures.txt", "w", encoding="utf-8") as f:
    f.write(output)

lines = output.splitlines()
failed = [l for l in lines if l.startswith("FAILED")]
print(f"Total FAILED: {len(failed)}")
from collections import Counter
files = Counter(l.split("::")[0].replace("FAILED ","") for l in failed)
for fn, n in sorted(files.items(), key=lambda x:-x[1]):
    print(f"  {n:3d}x {fn}")
for l in lines[-3:]:
    print(l)
print(f"Exit code: {result.returncode}")
