#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
簡易スクリプト: `manaos_integration_config.json` に Mem0 サービスを追加します。
"""
import json
from pathlib import Path

cfg_path = Path(__file__).parent / "manaos_integration_config.json"
if not cfg_path.exists():
    print(f"❌ 設定ファイルが見つかりません: {cfg_path}")
    raise SystemExit(1)

with open(cfg_path, 'r', encoding='utf-8') as f:
    cfg = json.load(f)

services = cfg.setdefault('manaos_services', {})
if 'mem0' in services:
    print("⚠️  mem0 は既に登録済みです")
else:
    services['mem0'] = {
        "port": 5120,
        "name": "Mem0",
        "description": "外部Mem0ストレージ連携サービス"
    }
    with open(cfg_path, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)
    print(f"✅ mem0 を追加しました: ポート 5120 -> {cfg_path}")
