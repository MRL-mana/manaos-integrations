"""
3連続テスト（運用完了の証明）
"""

import sys
import time
import subprocess
from pathlib import Path
from datetime import datetime

# UTF-8エンコーディング設定
sys.stdout.reconfigure(encoding='utf-8')  # type: ignore[attr-defined]

TEST_SCRIPT = Path(__file__).parent / "test_final_checklist_stable.py"


def run_test(attempt: int) -> bool:
    """テストを1回実行"""
    print(f"\n{'=' * 60}")
    print(f" テスト実行 #{attempt}")
    print(f"{'=' * 60}")
    
    try:
        result = subprocess.run(
            [sys.executable, str(TEST_SCRIPT)],
            capture_output=True,
            text=True,
            timeout=120,
            encoding='utf-8'
        )
        
        # 出力を表示
        print(result.stdout)
        if result.stderr:
            print("エラー出力:", result.stderr)
        
        # 合格率を確認
        if "合格率: 5/5 (100.0%)" in result.stdout:
            print(f"✅ テスト #{attempt}: 合格")
            return True
        else:
            print(f"❌ テスト #{attempt}: 不合格")
            return False
    
    except subprocess.TimeoutExpired:
        print(f"❌ テスト #{attempt}: タイムアウト（120秒）")
        return False
    except Exception as e:
        print(f"❌ テスト #{attempt}: エラー - {e}")
        return False


def main():
    """メイン関数"""
    print("\n" + "=" * 60)
    print(" manaOS拡張フェーズ 3連続テスト")
    print("=" * 60)
    print(f"実行日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"テストスクリプト: {TEST_SCRIPT}")
    print("\n3連続で合格すれば、「運用できる」の証明になります。")
    print("=" * 60)
    
    results = []
    
    for i in range(1, 4):
        print(f"\n⏳ テスト #{i} を開始します...")
        time.sleep(5)  # テスト間の待機（負荷軽減のため延長）
        
        success = run_test(i)
        results.append(success)
        
        if not success:
            print(f"\n❌ テスト #{i} が不合格でした。3連続テストを中断します。")
            break
    
    # 結果サマリー
    print("\n" + "=" * 60)
    print(" 3連続テスト結果")
    print("=" * 60)
    
    passed = sum(results)
    total = len(results)
    
    for i, success in enumerate(results, 1):
        status = "✅ 合格" if success else "❌ 不合格"
        print(f"テスト #{i}: {status}")
    
    print(f"\n合格数: {passed}/{total}")
    
    if passed == 3:
        print("\n🎉🎉🎉 3連続テストに合格しました！")
        print("   manaOSは「運用できる」状態です。")
        print("   もう誰も文句言えません。")
    elif passed == 2:
        print("\n⚠️  2/3合格。あと1回で完全勝利です。")
    elif passed == 1:
        print("\n⚠️  1/3合格。安定性に課題があります。")
    else:
        print("\n❌ 0/3合格。改善が必要です。")
    
    # 結果を保存
    result_file = Path(__file__).parent / "data" / "3_consecutive_test_results.json"
    result_file.parent.mkdir(parents=True, exist_ok=True)
    
    import json
    with open(result_file, 'w', encoding='utf-8') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "results": results,
            "passed": passed,
            "total": total,
            "all_passed": (passed == 3)
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n結果を保存しました: {result_file}")



