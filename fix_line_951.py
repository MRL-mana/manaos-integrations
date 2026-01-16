#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('create_system3_status.py', 'r', encoding='utf-8', errors='replace') as f:
    lines = f.readlines()

# Fix line 951 (0-indexed: 950)
if len(lines) > 950:
    lines[950] = '    """ToDoキューからメトリクスを取得"""\n'

with open('create_system3_status.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print('Fixed line 951')
