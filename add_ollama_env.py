#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ollama環境変数を.envファイルに追加"""

from pathlib import Path

env_path = Path('.env')
content = ""

if env_path.exists():
    content = env_path.read_text(encoding='utf-8')

if 'OLLAMA_URL' not in content:
    if content and not content.endswith('\n'):
        content += '\n'
    content += '\n# Ollama設定（Mem0統合用）\n'
    content += 'OLLAMA_URL=http://localhost:11434\n'
    content += 'OLLAMA_MODEL=qwen2.5:7b\n'
    
    env_path.write_text(content, encoding='utf-8')
    print('✅ Ollama環境変数を追加しました')
else:
    print('ℹ️  Ollama環境変数は既に設定されています')
