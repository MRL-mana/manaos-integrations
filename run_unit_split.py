"""
unit テストを2分割して実行するスクリプト。各部分の結果を保存。
"""
import subprocess, sys, os

os.chdir(r"C:\Users\mana4\Desktop\manaos_integrations")

def run_tests(label, args):
    print(f"\n{'='*60}")
    print(f"Running: {label}")
    print('='*60)
    r = subprocess.run(
        [sys.executable, "-m", "pytest"] + args + [
            "-o", "addopts=--strict-markers --disable-warnings --color=no",
            "--tb=short", "-q", "--no-header"
        ],
        capture_output=True, text=True,
        cwd=r"C:\Users\mana4\Desktop\manaos_integrations",
        timeout=300
    )
    out = r.stdout + r.stderr
    lines = out.splitlines()
    failed = [l for l in lines if l.startswith("FAILED")]
    print(f"Exit: {r.returncode}, FAILED: {len(failed)}")
    for l in failed: print(f"  {l}")
    if lines:
        print("Last 3:", lines[-3:])
    return failed

all_failed = []
try:
    # Part 1: a-m files
    f1 = run_tests("Part1 (a-m)", [
        "tests/unit/",
        "-k", "test_a or test_b or test_c or test_d or test_e or "
              "test_f or test_g or test_h or test_i or test_j or "
              "test_k or test_l or test_m"
    ])
    all_failed.extend(f1)
except Exception as e:
    print(f"Part1 error: {e}")

try:
    # Part 2: n-z files
    f2 = run_tests("Part2 (n-z)", [
        "tests/unit/",
        "-k", "test_n or test_o or test_p or test_q or test_r or "
              "test_s or test_t or test_u or test_v or test_w or "
              "test_x or test_y or test_z"
    ])
    all_failed.extend(f2)
except Exception as e:
    print(f"Part2 error: {e}")

print(f"\nTotal FAILED: {len(all_failed)}")
for f in all_failed:
    print(f"  {f}")
