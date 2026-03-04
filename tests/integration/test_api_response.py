#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import urllib.request
import json

try:
    resp = urllib.request.urlopen('http://127.0.0.1:9601/api/images?filter=all&limit=5', timeout=5)
    data = json.loads(resp.read().decode('utf-8'))
    
    print("改善反映確認:")
    print(f"  型: {type(data).__name__}")
    if isinstance(data, dict):
        print(f"  ページネーション: {'items' in data}")
        print(f"  統計情報: {'stats' in data}")
        print(f"  総数: {data.get('total', 'N/A')}")
        print(f"  返却件数: {len(data.get('items', []))}")
        if 'stats' in data:
            stats = data['stats']
            print(f"  評価済み: {stats.get('evaluated', 0)}件")
            print(f"  未評価: {stats.get('unevaluated', 0)}件")
            print(f"  高評価: {stats.get('high_score', 0)}件")
        print("\n[OK] 改善機能が反映されています！")
    else:
        print("[NG] 改善機能が反映されていません（配列を返しています）")
except Exception as e:
    print(f"[NG] エラー: {e}")
