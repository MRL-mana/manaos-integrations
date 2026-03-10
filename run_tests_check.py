"""pytest サマリーを取得して表示する"""
import subprocess, sys, os

os.chdir(r"C:\Users\mana4\Desktop\manaos_integrations")
result = subprocess.run(
    [sys.executable, "-m", "pytest", "tests/", "--tb=no", "-q", "--no-header"],
    capture_output=True, text=True, encoding="utf-8", errors="replace"
)
output = result.stdout + result.stderr
lines = output.splitlines()

# FAILEDとサマリーのみ
failed_lines = [l for l in lines if "FAILED" in l or "ERROR" in l]
summary_lines = [l for l in lines if "passed" in l or "failed" in l or "error" in l.lower()]

print("=== FAILED/ERROR ===")
for l in failed_lines[:50]:
    print(l)
print("=== SUMMARY ===")
for l in summary_lines[-5:]:
    print(l)
print(f"Exit code: {result.returncode}")
