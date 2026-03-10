"""
組み合わせテスト - learning_system_api の失敗原因特定
"""
import subprocess
import sys

# -k フィルターなし: unit + performance で失敗するか確認
result = subprocess.run(
    [
        sys.executable, '-m', 'pytest',
        'tests/unit', 'tests/performance',
        '--tb=no', '-q', '--no-header',
        '--override-ini=addopts=--strict-markers --disable-warnings --color=no'
    ],
    cwd=r'C:\Users\mana4\Desktop\manaos_integrations',
    capture_output=True,
    text=True
)
output = result.stdout + result.stderr
with open(r'C:\Temp\combo_test.txt', 'w', encoding='utf-8') as f:
    f.write(output)
lines = output.splitlines()
# Show last 20 lines and any FAILED lines
failed = [l for l in lines if 'FAILED' in l]
print(f"Return code: {result.returncode}")
print(f"Total lines: {len(lines)}")
print("FAILED tests:")
for l in failed[:30]:
    print(l)
print("--- Summary ---")
print('\n'.join(lines[-5:]))
