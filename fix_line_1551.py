#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('create_system3_status.py', 'r', encoding='utf-8', errors='replace') as f:
    lines = f.readlines()

# Fix line 1551 (0-indexed: 1550)
if len(lines) > 1550:
    lines[1550] = '    """直近の改善件数をカウント"""\n'

with open('create_system3_status.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print('Fixed line 1551')
