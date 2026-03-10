"""Full test suite runner - captures failures and skips."""
import subprocess
import sys
import os

os.chdir(r'C:\Users\mana4\Desktop\manaos_integrations')

result = subprocess.run(
    [sys.executable, '-m', 'pytest', 'tests/',
     '-p', 'no:cacheprovider',
     '--tb=line',
     '-q',
     '--no-header',
     '-p', 'no:warnings',
     '--override-ini=addopts=--strict-markers',
    ],
    capture_output=True,
    text=True,
    encoding='utf-8',
    errors='replace',
    cwd=r'C:\Users\mana4\Desktop\manaos_integrations'
)

output = result.stdout + result.stderr

# Write full output
with open(r'C:\Users\mana4\Desktop\test_output.txt', 'w', encoding='utf-8') as f:
    f.write(output)

# Print summary lines
lines = output.splitlines()
print(f"Total lines: {len(lines)}")

# Find FAILED lines
failed_lines = [l for l in lines if 'FAILED' in l]
print(f"\n=== FAILURES ({len(failed_lines)}) ===")
for l in failed_lines:
    print(l)

# Find error/traceback lines
error_lines = [l for l in lines if l.strip().startswith('FAILED') or 'ERROR' in l or 'Error' in l]

# Print last 30 lines for summary
print("\n=== LAST 30 LINES ===")
for l in lines[-30:]:
    print(l)

print("\nReturn code:", result.returncode)
