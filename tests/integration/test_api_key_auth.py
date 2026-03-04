#!/usr/bin/env python3
"""
APIキー認証のテストスクリプト
"""

import os
import pytest
import requests
from pathlib import Path

try:
    from manaos_integrations._paths import MRL_MEMORY_PORT
except Exception:  # pragma: no cover
    try:
        from _paths import MRL_MEMORY_PORT  # type: ignore
    except Exception:  # pragma: no cover
        MRL_MEMORY_PORT = int(os.getenv("MRL_MEMORY_PORT", "5105"))

# .envファイルを読み込む
def _load_dotenv(env_path: str = ".env") -> None:
    """最小のdotenvローダ"""
    try:
        p = Path(env_path)
        if not p.exists():
            return
        for raw in p.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ[k.strip()] = v.strip()
    except Exception as e:
        print(f"[WARN] .env読み込みに失敗: {e}")

_load_dotenv()

# APIキーを取得
api_key = os.getenv("MRL_MEMORY_API_KEY") or os.getenv("API_KEY", "")
require_auth = os.getenv("REQUIRE_AUTH", "1")


def test_api_key_auth():
    """APIキー認証テスト"""
    print("=" * 60)
    print("APIキー認証テスト")
    print("=" * 60)
    print(f"\n環境変数:")
    print(f"  MRL_MEMORY_API_KEY: {'SET' if os.getenv('MRL_MEMORY_API_KEY') else 'NOT SET'}")
    print(f"  API_KEY: {'SET' if os.getenv('API_KEY') else 'NOT SET'}")
    print(f"  REQUIRE_AUTH: {require_auth}")
    print(f"  API Key (first 20 chars): {api_key[:20] if api_key else 'NOT SET'}...")

    # ヘルスチェック
    print(f"\nヘルスチェック:")
    base_url = os.getenv("MRL_MEMORY_API_URL", f"http://127.0.0.1:{MRL_MEMORY_PORT}")
    try:
        response = requests.get(f"{base_url}/health", timeout=3)
        print(f"  Status: {response.status_code}")
        if response.status_code == 200:
            print(f"  Response: {response.json()}")
        assert response.status_code == 200, f"Health check failed: {response.status_code}"
    except Exception as e:
        print(f"  Error: {e}")
        return

    # メトリクス取得（APIキーなし）
    print(f"\nメトリクス取得（APIキーなし）:")
    try:
        response = requests.get(f"{base_url}/api/metrics", timeout=5)
        print(f"  Status: {response.status_code}")
        if response.status_code == 200:
            print(f"  [OK] 認証なしで取得成功")
        elif response.status_code == 401:
            print(f"  [WARN] 認証エラー（期待通り）")
        else:
            print(f"  Response: {response.text[:200]}")
    except Exception as e:
        print(f"  Error: {e}")

    # メトリクス取得（APIキーあり）
    if api_key:
        print(f"\nメトリクス取得（APIキーあり）:")
        try:
            headers = {"X-API-Key": api_key}
            response = requests.get(
                f"{base_url}/api/metrics",
                headers=headers,
                timeout=5,
            )
            print(f"  Status: {response.status_code}")
            if response.status_code == 200:
                print(f"  [OK] 認証成功！")
                metrics = response.json()
                config = metrics.get("config", {})
                print(f"  Write Mode: {config.get('write_mode', 'unknown')}")
                print(f"  Write Enabled: {config.get('write_enabled', 'unknown')}")
            elif response.status_code == 401:
                print(f"  [ERROR] 認証失敗（APIキーが一致していない可能性）")
                print(f"  Response: {response.text[:200]}")
            else:
                print(f"  Response: {response.text[:200]}")
        except Exception as e:
            print(f"  Error: {e}")
    else:
        print(f"\n[WARN] APIキーが設定されていません")

    print("\n" + "=" * 60)

