#!/usr/bin/env python3
"""
ManaOS Computer Use - 本格運用テスト
実用的なタスクを実行
"""

import requests
import time

BASE_URL = "http://localhost:9103"

def test_actuator_health():
    """Actuatorサービスのヘルスチェック"""
    print("📍 Test 1: Actuatorサービス ヘルスチェック")
    try:
        response = requests.get(f"{BASE_URL}/")
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ {data['actor']}")
            print(f"   ステータス: {data['status']}")
            return True
        else:
            print(f"   ❌ ステータスコード: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ エラー: {e}")
        return False

def test_x280_connection():
    """X280接続確認"""
    print("\n📍 Test 2: X280接続確認")
    try:
        response = requests.post(
            f"{BASE_URL}/execute",
            json={
                "intent_type": "gui_automation",
                "payload": {
                    "task": "接続テスト",
                    "max_steps": 1
                }
            },
            timeout=10
        )
        result = response.json()
        
        if result.get('ok'):
            print("   ✅ X280接続成功")
            return True
        else:
            error = result.get('error', '')
            if 'X280 GUI APIに接続できません' in error:
                print("   ⚠️ X280未接続（予想通り）")
                print("   → X280でサーバーを起動してください")
            else:
                print(f"   ❌ エラー: {error}")
            return False
    except Exception as e:
        print(f"   ❌ エラー: {e}")
        return False

def execute_production_task(task_name, task):
    """本格運用タスクを実行"""
    print(f"\n📍 実行: {task_name}")
    print(f"   タスク: {task}")
    
    try:
        response = requests.post(
            f"{BASE_URL}/execute",
            json={
                "intent_type": "gui_automation",
                "payload": {
                    "task": task,
                    "max_steps": 20,
                    "step_delay": 2.0
                }
            },
            timeout=180  # 3分
        )
        
        result = response.json()
        
        if result.get('ok'):
            print("   ✅ 実行成功")
            if result.get('result'):
                r = result['result']
                print(f"   ステップ数: {r.get('total_steps')}")
                print(f"   成功率: {r.get('success_rate', 0) * 100:.1f}%")
                print(f"   実行時間: {r.get('duration_seconds', 0):.1f}秒")
            return True
        else:
            print(f"   ❌ 実行失敗: {result.get('error')}")
            return False
            
    except requests.exceptions.Timeout:
        print("   ⏱️ タイムアウト（長時間実行中）")
        return False
    except Exception as e:
        print(f"   ❌ エラー: {e}")
        return False

def main():
    print("=" * 60)
    print("🚀 ManaOS Computer Use - 本格運用テスト")
    print("=" * 60)
    
    # Test 1: Actuatorヘルスチェック
    if not test_actuator_health():
        print("\n❌ Actuatorサービスが起動していません")
        print("   起動方法: cd /root/manaos_v3/services/actuator && nohup python3 main.py &")
        return
    
    # Test 2: X280接続確認
    x280_ready = test_x280_connection()
    
    if not x280_ready:
        print("\n" + "=" * 60)
        print("📝 X280サーバー起動方法:")
        print("=" * 60)
        print("X280で以下を実行:")
        print("  cd C:\\Users\\mana.DESKTOP-ASMRKIM")
        print("  python server.py")
        print("")
        print("または、このはサーバーから:")
        print("  bash /root/start_x280_server.sh")
        print("=" * 60)
        return
    
    # 本格運用タスク実行
    print("\n" + "=" * 60)
    print("🎯 本格運用タスク実行")
    print("=" * 60)
    
    tasks = [
        ("メモ帳テキスト作成", "X280でメモ帳を開いて、以下の内容を入力:\n\nManaOS Computer Use - 本格運用開始\n日付: 2025年10月12日\nステータス: Production Ready"),
        ("ブラウザ起動", "X280でブラウザを開いてexample.comにアクセス"),
    ]
    
    success_count = 0
    for task_name, task in tasks:
        if execute_production_task(task_name, task):
            success_count += 1
        time.sleep(2)
    
    # サマリー
    print("\n" + "=" * 60)
    print("📊 実行結果サマリー")
    print("=" * 60)
    print(f"実行タスク数: {len(tasks)}")
    print(f"成功: {success_count}")
    print(f"失敗: {len(tasks) - success_count}")
    print(f"成功率: {success_count / len(tasks) * 100:.1f}%")
    print("=" * 60)
    
    if success_count == len(tasks):
        print("\n🎉 本格運用準備完了！")
    else:
        print("\n⚠️ 一部タスクが失敗しました")

if __name__ == "__main__":
    main()


