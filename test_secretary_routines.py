"""
秘書機能のテスト
"""

import sys
from pathlib import Path

# パスを追加
sys.path.insert(0, str(Path(__file__).parent))

from secretary_routines import SecretaryRoutines


def test_secretary_routines():
    """秘書機能のテスト"""
    print("=" * 60)
    print("秘書機能 テスト")
    print("=" * 60)
    
    secretary = SecretaryRoutines()
    
    # 1. 朝のルーチン
    print("\n[1] 朝のルーチン")
    print("-" * 60)
    try:
        result = secretary.morning_routine()
        print("✅ 朝のルーチン完了")
        print(f"   予定: {len(result['schedule'])}件")
        print(f"   タスク: {len(result['tasks'])}件")
        print(f"   ログ差分: {result['log_diff']['total']}件")
    except Exception as e:
        print(f"❌ エラー: {e}")
    
    # 2. 昼のルーチン
    print("\n[2] 昼のルーチン")
    print("-" * 60)
    try:
        result = secretary.noon_routine()
        print("✅ 昼のルーチン完了")
        print(f"   総タスク: {result['progress']['total']}件")
        print(f"   完了: {result['progress']['completed']}件")
        print(f"   未完了: {result['progress']['incomplete']}件")
    except Exception as e:
        print(f"❌ エラー: {e}")
    
    # 3. 夜のルーチン
    print("\n[3] 夜のルーチン")
    print("-" * 60)
    try:
        result = secretary.evening_routine()
        print("✅ 夜のルーチン完了")
        print(f"   日報: {len(result['daily_report'])}文字")
        print(f"   明日の予定: {len(result['tomorrow_prep']['schedule'])}件")
        print(f"   明日のタスク: {len(result['tomorrow_prep']['tasks'])}件")
    except Exception as e:
        print(f"❌ エラー: {e}")


if __name__ == "__main__":
    test_secretary_routines()
    
    print("\n" + "=" * 60)
    print("テスト完了")
    print("=" * 60)


















