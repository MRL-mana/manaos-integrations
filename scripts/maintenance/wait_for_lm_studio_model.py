#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LM Studioモデルのダウンロード完了を待機"""

import sys
import requests
import time
import os

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

def wait_for_model(model_name: str, check_interval: int = 30, max_wait: int = 3600):
    """
    モデルのダウンロード完了を待機
    
    Args:
        model_name: 待機するモデル名（部分一致可）
        check_interval: チェック間隔（秒）
        max_wait: 最大待機時間（秒）
    """
    print("=" * 60)
    print(f"モデルダウンロード完了待機: {model_name}")
    print("=" * 60)
    print(f"チェック間隔: {check_interval}秒")
    print(f"最大待機時間: {max_wait}秒（{max_wait//60}分）")
    print("\nダウンロード状況を監視中...")
    print("（Ctrl+Cで中断可能）")
    
    start_time = time.time()
    check_count = 0
    
    while True:
        elapsed = time.time() - start_time
        
        if elapsed > max_wait:
            print(f"\n✗ タイムアウト: {max_wait}秒経過しました")
            print("  モデルのダウンロードが完了していない可能性があります")
            return False
        
        try:
            # LM Studio APIからモデル一覧を取得
            r = requests.get(f"{DEFAULT_LM_STUDIO_URL}/v1/models", timeout=5)
            if r.status_code == 200:
                models_data = r.json().get('data', [])
                available_models = [model.get('id', '') for model in models_data]
                
                # モデル名で部分一致検索
                found = False
                matched_model = None
                for available in available_models:
                    if model_name.lower() in available.lower() or available.lower() in model_name.lower():
                        found = True
                        matched_model = available
                        break
                
                if found:
                    print(f"\n✓ モデルダウンロード完了！")
                    print(f"  モデル名: {matched_model}")
                    print(f"  待機時間: {elapsed:.0f}秒（{elapsed/60:.1f}分）")
                    print(f"  チェック回数: {check_count}回")
                    return True
                else:
                    check_count += 1
                    if check_count % 2 == 0:  # 2回に1回表示
                        print(f"  待機中... ({elapsed:.0f}秒経過, {check_count}回チェック)")
            
        except requests.exceptions.ConnectionError:
            print(f"\n✗ LM Studioサーバーに接続できません")
            print("  LM Studioのサーバーが起動しているか確認してください")
            return False
        except Exception as e:
            print(f"\n✗ エラー: {e}")
            return False
        
        time.sleep(check_interval)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='LM Studioモデルのダウンロード完了を待機')
    parser.add_argument('model_name', help='待機するモデル名（部分一致可）')
    parser.add_argument('--interval', type=int, default=30, help='チェック間隔（秒、デフォルト: 30）')
    parser.add_argument('--max-wait', type=int, default=3600, help='最大待機時間（秒、デフォルト: 3600）')
    
    args = parser.parse_args()
    
    wait_for_model(args.model_name, args.interval, args.max_wait)
