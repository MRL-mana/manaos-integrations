#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""評価APIのテスト"""

import urllib.request
import json

# テスト用の画像パスを取得
try:
    resp = urllib.request.urlopen('http://127.0.0.1:9601/api/images?filter=unevaluated&limit=1', timeout=5)
    data = json.loads(resp.read().decode('utf-8'))
    
    if isinstance(data, dict) and data.get('items'):
        test_image = data['items'][0]
        test_path = test_image['path']
        
        print(f"テスト画像: {test_image['name']}")
        print(f"パス: {test_path}")
        print()
        
        # 評価APIをテスト
        print("評価APIをテスト中...")
        eval_data = {
            "image_path": test_path,
            "score": 2,
            "comment": "テスト評価"
        }
        
        req = urllib.request.Request(
            'http://127.0.0.1:9601/api/evaluate',
            data=json.dumps(eval_data).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        
        resp = urllib.request.urlopen(req, timeout=5)
        result = json.loads(resp.read().decode('utf-8'))
        
        print(f"結果: {result}")
        
        if result.get('success'):
            print("[OK] 評価APIは正常に動作しています")
        else:
            print(f"[NG] 評価APIエラー: {result.get('error')}")
    else:
        print("[NG] テスト用の画像が見つかりません")
        
except Exception as e:
    print(f"[NG] エラー: {e}")
    import traceback
    traceback.print_exc()
