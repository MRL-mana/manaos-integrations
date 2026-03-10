#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')  # type: ignore[attr-defined]
import re

with open('create_system3_status.py', 'r', encoding='utf-8', errors='replace') as f:
    lines = f.readlines()

# Fix all problematic docstrings
fixes = {
    1550: '    """直近の改善件数をカウント"""\n',
    1670: '    """System3_Status.mdの内容を生成"""\n',
}

for line_num, replacement in fixes.items():
    if len(lines) > line_num:
        lines[line_num] = replacement

with open('create_system3_status.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print('All docstrings fixed')
