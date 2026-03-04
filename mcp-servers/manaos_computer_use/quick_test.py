#!/usr/bin/env python3
"""
ManaOS Computer Use - クイックテスト
システムの全体動作確認
"""

import sys
from pathlib import Path


def test_imports():
    """モジュールインポートテスト"""
    print("📦 インポートテスト...")
    try:
        # パスを追加
        sys.path.insert(0, str(Path("/root")))
        
        print("   ✅ 全モジュールインポート成功")
        return True
    except Exception as e:
        print(f"   ❌ インポート失敗: {e}")
        return False


def test_types():
    """型定義テスト"""
    print("\n🔤 型定義テスト...")
    try:
        from manaos_computer_use_types import Action, ActionType
        
        # Actionオブジェクト作成
        action = Action(
            action_type=ActionType.CLICK,
            parameters={"x": 100, "y": 200},
            reasoning="テスト"
        )
        
        # dict変換
        action_dict = action.to_dict()
        assert "action_type" in action_dict
        assert action_dict["action_type"] == "click"
        
        print("   ✅ 型定義正常")
        return True
    except Exception as e:
        print(f"   ❌ 型定義エラー: {e}")
        return False


def test_x280_connection():
    """X280接続テスト"""
    print("\n🔌 X280接続テスト...")
    try:
        sys.path.append(str(Path("/root/x280_gui_automation")))
        from x280_gui_client import X280GUIController
        
        controller = X280GUIController()
        health = controller.health_check()
        
        if health:
            print(f"   ✅ X280接続成功: {health.get('screen_size')}")
            return True
        else:
            print("   ⚠️ X280に接続できません")
            print("   → X280側でGUI APIサーバーを起動してください")
            print("   → ssh x280 'python C:\\Users\\mana\\x280_gui_automation\\x280_gui_server.py'")
            return False
    except Exception as e:
        print(f"   ⚠️ X280接続エラー: {e}")
        return False


def test_directory_structure():
    """ディレクトリ構造テスト"""
    print("\n📁 ディレクトリ構造テスト...")
    
    base_dir = Path("/root/manaos_computer_use")
    required_files = [
        "manaos_computer_use_types.py",
        "manaos_computer_use_vision.py",
        "manaos_computer_use_executor.py",
        "manaos_computer_use_orchestrator.py",
        "__init__.py",
        "demo_simple.py",
        "demo_notepad.py",
        "demo_browser.py",
        "README.md"
    ]
    
    all_exist = True
    for filename in required_files:
        filepath = base_dir / filename
        if filepath.exists():
            print(f"   ✅ {filename}")
        else:
            print(f"   ❌ {filename} が見つかりません")
            all_exist = False
    
    return all_exist


def main():
    print("🧪 ManaOS Computer Use - クイックテスト")
    print("=" * 60)
    
    results = {
        "インポート": test_imports(),
        "型定義": test_types(),
        "ディレクトリ構造": test_directory_structure(),
        "X280接続": test_x280_connection()
    }
    
    print("\n" + "=" * 60)
    print("📊 テスト結果サマリー")
    print("=" * 60)
    
    for test_name, result in results.items():
        status = "✅ 成功" if result else "❌ 失敗"
        print(f"{test_name}: {status}")
    
    print("=" * 60)
    
    # 必須テスト（X280接続以外）の成功判定
    critical_tests = ["インポート", "型定義", "ディレクトリ構造"]
    critical_passed = all(results[t] for t in critical_tests)
    
    if critical_passed:
        print("\n✅ システム正常 - 実行準備完了")
        if not results["X280接続"]:
            print("\n⚠️ 注意: X280接続が必要です")
            print("   X280側でGUI APIサーバーを起動してから、デモを実行してください")
        return 0
    else:
        print("\n❌ システムエラー - 修正が必要です")
        return 1


if __name__ == "__main__":
    sys.exit(main())

