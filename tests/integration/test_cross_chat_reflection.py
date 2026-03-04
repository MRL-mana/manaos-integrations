#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
別チャットからの画像生成でも自動反省が動作するかテスト
"""

import sys
import os
import requests
import time
import json
from pathlib import Path

# Windowsでのエンコーディング問題を回避
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'

from _paths import GALLERY_PORT

GALLERY_API = os.getenv("GALLERY_API_URL", f"http://127.0.0.1:{GALLERY_PORT}")

def check_api_server():
    """APIサーバーが起動しているか確認"""
    print("="*60)
    print("[1] APIサーバーの確認")
    print("="*60)
    
    try:
        response = requests.get(f"{GALLERY_API}/api/images", timeout=5)
        if response.status_code == 200:
            print("[OK] Gallery APIサーバーが起動しています")
            return True
        else:
            print(f"[WARN] APIサーバーが応答していますが、エラー: {response.status_code}")
            return False
    except Exception as e:
        print(f"[ERROR] Gallery APIサーバーが起動していません: {e}")
        print("\n[解決方法]")
        print("gallery_api_server.py を起動してください:")
        print("  python gallery_api_server.py")
        return False

def check_reflection_system():
    """自動反省システムが利用可能か確認"""
    print("\n" + "="*60)
    print("[2] 自動反省システムの確認")
    print("="*60)
    
    try:
        response = requests.get(f"{GALLERY_API}/api/reflection/statistics", timeout=5)
        if response.status_code == 200:
            stats = response.json().get("statistics", {})
            print("[OK] 自動反省システムが利用可能です")
            print(f"  総評価数: {stats.get('total_evaluations', 0)}")
            print(f"  平均スコア: {stats.get('average_score', 0):.2f}")
            return True
        else:
            print(f"[WARN] 統計情報取得エラー: {response.status_code}")
            return False
    except Exception as e:
        print(f"[WARN] 自動反省システムの確認エラー: {e}")
        print("（APIサーバーが起動していない可能性）")
        return False

def test_image_generation():
    """画像生成をテスト（自動反省が実行されるか確認）"""
    print("\n" + "="*60)
    print("[3] 画像生成テスト（自動反省確認）")
    print("="*60)
    
    print("\n[画像生成リクエスト送信]")
    try:
        response = requests.post(
            f"{GALLERY_API}/api/generate",
            json={
                "prompt": "cute anime girl, test image for auto reflection",
                "model": "realisian_v60.safetensors",
                "mufufu_mode": True,
                "width": 1024,
                "height": 1024,
                "steps": 50
            },
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                job_id = result.get("job_id")
                print(f"[OK] 画像生成リクエスト成功")
                print(f"  ジョブID: {job_id}")
                
                # 生成完了を待つ
                print(f"\n[生成完了を待機中...]")
                return wait_for_completion(job_id)
            else:
                print(f"[ERROR] 画像生成リクエスト失敗: {result.get('error')}")
                return False
        else:
            print(f"[ERROR] HTTPエラー: {response.status_code}")
            print(f"レスポンス: {response.text[:200]}")
            return False
            
    except Exception as e:
        print(f"[ERROR] 画像生成エラー: {e}")
        return False

def wait_for_completion(job_id, max_wait=300):
    """生成完了と評価結果を待つ"""
    print(f"  最大待機時間: {max_wait}秒")
    
    for i in range(max_wait // 5):
        try:
            response = requests.get(f"{GALLERY_API}/api/job/{job_id}", timeout=5)
            if response.status_code == 200:
                status = response.json()
                job_status = status.get("status", "unknown")
                
                if job_status == "completed":
                    print(f"\n[OK] 画像生成完了")
                    
                    # 評価結果を確認
                    if "reflection" in status:
                        evaluation = status["reflection"]["evaluation"]
                        print(f"\n[OK] 自動反省が実行されました！")
                        print(f"  総合スコア: {evaluation.get('overall_score', 0):.2f}")
                        print(f"  身体崩れスコア: {evaluation.get('anatomy_score', 0):.2f}")
                        print(f"  品質スコア: {evaluation.get('quality_score', 0):.2f}")
                        
                        if status["reflection"].get("should_regenerate"):
                            improvement = status["reflection"]["improvement"]
                            print(f"\n[再生成推奨]")
                            print(f"  理由: {improvement.get('reason', '')}")
                            print(f"  期待される改善度: {improvement.get('expected_improvement', 0):.2f}")
                        
                        return True
                    else:
                        print(f"[WARN] 評価結果が見つかりません")
                        print(f"  ジョブステータス: {status}")
                        return False
                elif job_status == "failed":
                    error = status.get("error", "不明なエラー")
                    print(f"[ERROR] 画像生成失敗: {error}")
                    return False
                else:
                    # まだ処理中
                    if i % 6 == 0:  # 30秒ごとに表示
                        print(f"  待機中... ({i*5}秒経過)")
            
            time.sleep(5)
            
        except Exception as e:
            print(f"[WARN] ステータス確認エラー: {e}")
            time.sleep(5)
    
    print(f"\n[ERROR] タイムアウト: {max_wait}秒以内に完了しませんでした")
    return False

def main():
    """メインテスト"""
    print("="*60)
    print("別チャットからの自動反省動作確認テスト")
    print("="*60)
    
    # 1. APIサーバーの確認
    if not check_api_server():
        print("\n[テスト中断] APIサーバーが起動していません")
        return False
    
    # 2. 自動反省システムの確認
    check_reflection_system()
    
    # 3. 画像生成テスト
    print("\n" + "="*60)
    print("[テスト実行]")
    print("="*60)
    print("\n別チャットから画像生成を実行した場合でも、")
    print("自動反省・改善システムが動作するか確認します。")
    print("\n実行しますか？ (y/n): ", end="")
    
    # 自動実行（テスト用）
    # user_input = input().strip().lower()
    # if user_input != 'y':
    #     print("[テスト中断] ユーザーによって中断されました")
    #     return False
    
    success = test_image_generation()
    
    # 結果サマリー
    print("\n" + "="*60)
    print("[テスト結果]")
    print("="*60)
    
    if success:
        print("[OK] 別チャットからの画像生成でも自動反省が動作しました！")
        print("\n[確認ポイント]")
        print("  - 画像生成APIを使用すると、自動的に評価が実行される")
        print("  - 評価結果はジョブステータスに含まれる")
        print("  - データベースに保存される")
    else:
        print("[ERROR] テストが失敗しました")
        print("\n[確認事項]")
        print("  - Gallery APIサーバーが起動しているか")
        print("  - 画像生成が正常に完了したか")
        print("  - ログにエラーがないか")
    
    print("\n" + "="*60)
    
    return success

