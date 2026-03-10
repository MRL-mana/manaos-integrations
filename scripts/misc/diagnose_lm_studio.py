#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LM Studioの問題を診断"""

import sys
import os
import requests
import json

try:
    from manaos_integrations._paths import LM_STUDIO_PORT
except Exception:  # pragma: no cover
    try:
        from _paths import LM_STUDIO_PORT  # type: ignore
    except Exception:  # pragma: no cover
        LM_STUDIO_PORT = int(os.getenv("LM_STUDIO_PORT", "1234"))


DEFAULT_LM_STUDIO_URL = os.getenv("LM_STUDIO_URL", f"http://127.0.0.1:{LM_STUDIO_PORT}")

if sys.platform == 'win32':
    import io
    sys.stdout.reconfigure(encoding='utf-8')  # type: ignore[attr-defined]

print("=" * 60)
print("LM Studio 診断ツール")
print("=" * 60)

# 1. LM Studioサーバー確認
print("\n【1】LM Studioサーバー確認")
try:
    r = requests.get(f"{DEFAULT_LM_STUDIO_URL}/v1/models", timeout=5)
    if r.status_code == 200:
        print("✓ LM Studioサーバー: 起動中")
        models_data = r.json().get('data', [])
        print(f"  利用可能なモデル: {len(models_data)}個")
    else:
        print(f"✗ LM Studioサーバー: エラー HTTP {r.status_code}")
except Exception as e:
    print(f"✗ LM Studioサーバー: 接続エラー - {e}")
    print("\n【対処】LM Studioの「Server」タブで「Start Server」をクリックしてください")
    sys.exit(1)

# 2. モデルファイルの存在確認
print("\n【2】モデルファイル確認")
lm_studio_path = os.path.expanduser("~/.lmstudio")
print(f"LM Studioパス: {lm_studio_path}")

if os.path.exists(lm_studio_path):
    print("✓ LM Studioディレクトリ: 存在")
    
    # モデルディレクトリを確認
    models_dir = os.path.join(lm_studio_path, "models")
    if os.path.exists(models_dir):
        print(f"✓ モデルディレクトリ: 存在 ({models_dir})")
        # サブディレクトリを確認
        subdirs = [d for d in os.listdir(models_dir) if os.path.isdir(os.path.join(models_dir, d))]
        print(f"  モデルフォルダ数: {len(subdirs)}")
        if subdirs:
            print(f"  例: {subdirs[0]}")
    else:
        print(f"✗ モデルディレクトリ: 存在しない ({models_dir})")
else:
    print(f"✗ LM Studioディレクトリ: 存在しない ({lm_studio_path})")

# 3. バックエンドエンジン確認
print("\n【3】バックエンドエンジン確認")
extensions_dir = os.path.join(lm_studio_path, "extensions", "backends")
if os.path.exists(extensions_dir):
    print(f"✓ バックエンドディレクトリ: 存在")
    backends = [d for d in os.listdir(extensions_dir) if os.path.isdir(os.path.join(extensions_dir, d))]
    print(f"  バックエンド数: {len(backends)}")
    for backend in backends[:3]:
        backend_path = os.path.join(extensions_dir, backend)
        print(f"  - {backend}")
        # 実行ファイルを確認
        exe_files = [f for f in os.listdir(backend_path) if f.endswith('.exe') or f.endswith('.dll')]
        if exe_files:
            print(f"    実行ファイル: {len(exe_files)}個")
        else:
            print(f"    ⚠ 実行ファイルが見つかりません")
else:
    print(f"✗ バックエンドディレクトリ: 存在しない ({extensions_dir})")
    print("  【対処】LM Studioを再インストールするか、設定をリセットしてください")

# 4. モデルロードテスト（JITロード）
print("\n【4】JITロードテスト（推論時に自動ロード）")
test_model = "qwen2.5-coder-32b-instruct"
print(f"テストモデル: {test_model}")

try:
    url = f"{DEFAULT_LM_STUDIO_URL}/v1/chat/completions"
    data = {
        "model": test_model,
        "messages": [{"role": "user", "content": "test"}],
        "max_tokens": 5,
        "temperature": 0.7
    }
    
    print("  推論リクエスト送信中...（初回はモデルロードに時間がかかります）")
    response = requests.post(url, json=data, timeout=60)
    
    if response.status_code == 200:
        result = response.json()
        content = result["choices"][0]["message"]["content"]
        print(f"  ✓ 成功！モデルがロードされました")
        print(f"  応答: {content[:50]}")
    else:
        error_data = response.json() if response.content else {}
        error_msg = error_data.get('error', {}).get('message', '')
        print(f"  ✗ エラー: HTTP {response.status_code}")
        print(f"  詳細: {error_msg[:300]}")
        
        # エラーの種類を判定
        if 'load' in error_msg.lower() and 'engine' in error_msg.lower():
            print("\n  【問題】バックエンドエンジンの問題")
            print("  【対処方法】")
            print("    1. LM Studioを再起動")
            print("    2. LM Studioの設定で「Backend」を確認")
            print("    3. LM Studioを最新版に更新")
            print("    4. 必要に応じてLM Studioを再インストール")
        elif 'not found' in error_msg.lower() or 'missing' in error_msg.lower():
            print("\n  【問題】モデルファイルが見つからない")
            print("  【対処方法】")
            print("    1. LM Studioでモデルを再ダウンロード")
            print("    2. モデルファイルのパスを確認")
        elif 'cuda' in error_msg.lower() or 'gpu' in error_msg.lower():
            print("\n  【問題】GPU/CUDAの問題")
            print("  【対処方法】")
            print("    1. NVIDIAドライバーを最新版に更新")
            print("    2. CUDAが正しくインストールされているか確認")
            print("    3. LM Studioの設定でCPUモードに切り替え")
except requests.exceptions.Timeout:
    print("  ✗ タイムアウト（60秒）")
    print("  【対処】モデルのロードに時間がかかっています。もう一度試してください。")
except Exception as e:
    print(f"  ✗ エラー: {e}")

# 5. 推奨対処方法
print("\n" + "=" * 60)
print("推奨対処方法")
print("=" * 60)
print("1. LM Studioを再起動")
print("2. LM Studioの「Settings」→「Backend」でバックエンドを確認")
print("3. モデルを再ダウンロード（必要に応じて）")
print("4. LM Studioを最新版に更新")
print("5. それでも解決しない場合は、LM Studioを再インストール")

print("\n" + "=" * 60)
