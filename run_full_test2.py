"""Full test suite runner - incremental output to file."""
import subprocess
import sys
import os

os.chdir(r'C:\Users\mana4\Desktop\manaos_integrations')

outfile = r'C:\Users\mana4\Desktop\test_output.txt'

# Run and write output incrementally
cmd = [
    sys.executable, '-m', 'pytest', 'tests/',
    '-p', 'no:cacheprovider',
    '--tb=line',
    '-q',
    '--no-header',
    '-p', 'no:warnings',
    '--override-ini=addopts=--strict-markers',
]

with open(outfile, 'w', encoding='utf-8', buffering=1) as f:
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding='utf-8',
        errors='replace',
        cwd=r'C:\Users\mana4\Desktop\manaos_integrations',
    )
    for line in proc.stdout:
        f.write(line)
        f.flush()
    proc.wait()

# Print summary
lines = []
with open(outfile, 'r', encoding='utf-8') as f:
    lines = f.readlines()

failed = [l.strip() for l in lines if 'FAILED' in l]
print(f"Total output lines: {len(lines)}")
print(f"Failures: {len(failed)}")
for l in failed:
    print(l)
print("\n=== LAST 20 LINES ===")
for l in lines[-20:]:
    print(l.rstrip())
print(f"\nReturn code: {proc.returncode}")
