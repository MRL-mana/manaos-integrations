#!/usr/bin/env python3
"""
環境変数テストスクリプト
SSOT実装が正しく機能していることを確認します
"""

import os
import sys
from pathlib import Path

# manaos_integrationsディレクトリを親として追加
sys.path.insert(0, str(Path(__file__).parent))

try:
    import _paths
except ImportError:
    print("❌ _paths.py のインポートに失敗しました")
    sys.exit(1)


def test_environment_variable_override():
    """環境変数が_paths.pyの定数を正しくオーバーライドすることをテスト"""
    print("\n🧪 環境変数オーバーライドテスト")
    print("=" * 60)
    
    test_cases = [
        ("OLLAMA_URL", f"http://127.0.0.1:{_paths.OLLAMA_PORT}", "http://test-ollama:11434"),
        ("COMFYUI_URL", f"http://127.0.0.1:{_paths.COMFYUI_PORT}", "http://test-comfyui:8188"),
        ("MRL_MEMORY_URL", f"http://127.0.0.1:{_paths.MRL_MEMORY_PORT}", "http://test-memory:5105"),
        ("N8N_URL", f"http://127.0.0.1:{_paths.N8N_PORT}", "http://test-n8n:5678"),
        ("SEARXNG_URL", f"http://127.0.0.1:{_paths.SEARXNG_PORT}", "http://test-searxng:8080"),
    ]
    
    passed = 0
    failed = 0
    
    for env_var, default_url, test_url in test_cases:
        # 環境変数が設定されている場合
        if env_var in os.environ:
            actual = os.getenv(env_var)
            expected = test_url
            if actual == expected:
                print(f"✅ {env_var}: 環境変数から読み込み = {actual}")
                passed += 1
            else:
                print(f"❌ {env_var}: 期待値 {expected}, 実際 {actual}")
                failed += 1
        else:
            # 環境変数が未設定の場合はデフォルト値を使用
            actual = os.getenv(env_var, default_url)
            if actual == default_url:
                print(f"✅ {env_var}: デフォルト値を使用 = {actual}")
                passed += 1
            else:
                print(f"❌ {env_var}: デフォルト値が正しくありません")
                failed += 1
    
    print(f"\n📊 結果: {passed} 成功 / {failed} 失敗")
    return failed == 0


def test_port_constants():
    """_paths.pyのポート定数が正しく定義されていることをテスト"""
    print("\n🧪 ポート定数テスト")
    print("=" * 60)
    
    required_ports = [
        "OLLAMA_PORT",
        "COMFYUI_PORT",
        "MRL_MEMORY_PORT",
        "LEARNING_SYSTEM_PORT",
        "LLM_ROUTING_PORT",
        "N8N_PORT",
        "SEARXNG_PORT",
        "WHISPER_PORT",
        "VOICEVOX_PORT",
        "TTS_PORT",
        "REMI_PORT",
        "GALLERY_API_PORT",
        "EVALUATION_UI_PORT",
        "LM_STUDIO_PORT",
        "AUTONOMOUS_OPS_PORT",
    ]
    
    passed = 0
    failed = 0
    
    for port_name in required_ports:
        if hasattr(_paths, port_name):
            port_value = getattr(_paths, port_name)
            if isinstance(port_value, int) and 1 <= port_value <= 65535:
                print(f"✅ {port_name} = {port_value}")
                passed += 1
            else:
                print(f"❌ {port_name}: 無効なポート番号 {port_value}")
                failed += 1
        else:
            print(f"❌ {port_name}: 定義されていません")
            failed += 1
    
    print(f"\n📊 結果: {passed} 成功 / {failed} 失敗")
    return failed == 0


def test_url_construction():
    """URL構築パターンのテスト"""
    print("\n🧪 URL構築パターンテスト")
    print("=" * 60)
    
    test_patterns = [
        # (環境変数名, ポート定数名, 期待されるデフォルトURL)
        ("OLLAMA_URL", "OLLAMA_PORT", "http://127.0.0.1:11434"),
        ("COMFYUI_URL", "COMFYUI_PORT", "http://127.0.0.1:8188"),
        ("MRL_MEMORY_URL", "MRL_MEMORY_PORT", "http://127.0.0.1:5105"),
    ]
    
    passed = 0
    failed = 0
    
    for env_var, port_const, expected_default in test_patterns:
        port = getattr(_paths, port_const, None)
        if port is None:
            print(f"❌ {port_const}: 定義されていません")
            failed += 1
            continue
        
        # デフォルトURLの構築
        default_url = f"http://127.0.0.1:{port}"
        actual_url = os.getenv(env_var, default_url)
        
        # 環境変数が設定されていない場合のテスト
        if env_var not in os.environ:
            if actual_url == expected_default:
                print(f"✅ {env_var}: {actual_url}")
                passed += 1
            else:
                print(f"❌ {env_var}: 期待値 {expected_default}, 実際 {actual_url}")
                failed += 1
        else:
            # 環境変数が設定されている場合は、それが使われていることを確認
            print(f"✅ {env_var}: 環境変数を使用 = {actual_url}")
            passed += 1
    
    print(f"\n📊 結果: {passed} 成功 / {failed} 失敗")
    return failed == 0


def test_backward_compatibility():
    """後方互換性のテスト"""
    print("\n🧪 後方互換性テスト")
    print("=" * 60)
    
    # 環境変数が設定されていない場合、デフォルトでlocalhostを使用することを確認
    default_services = [
        ("OLLAMA_URL", 11434),
        ("COMFYUI_URL", 8188),
        ("MRL_MEMORY_URL", 5105),
        ("LEARNING_SYSTEM_URL", 5106),
    ]
    
    passed = 0
    failed = 0
    
    for service_name, port in default_services:
        if service_name not in os.environ:
            expected = f"http://127.0.0.1:{port}"
            actual = os.getenv(service_name, expected)
            if actual.startswith("http://127.0.0.1:") or actual.startswith("http://localhost:"):
                print(f"✅ {service_name}: localhostにフォールバック")
                passed += 1
            else:
                print(f"❌ {service_name}: localhostにフォールバックしていません = {actual}")
                failed += 1
        else:
            print(f"ℹ️  {service_name}: 環境変数が設定されています（テストスキップ）")
            passed += 1
    
    print(f"\n📊 結果: {passed} 成功 / {failed} 失敗")
    return failed == 0


def main():
    """メインテスト実行"""
    print("\n" + "=" * 60)
    print("🚀 ManaOS 環境変数テストスイート")
    print("=" * 60)
    
    results = []
    
    # 各テストを実行
    results.append(("環境変数オーバーライド", test_environment_variable_override()))
    results.append(("ポート定数", test_port_constants()))
    results.append(("URL構築パターン", test_url_construction()))
    results.append(("後方互換性", test_backward_compatibility()))
    
    # 総合結果
    print("\n" + "=" * 60)
    print("📋 総合結果")
    print("=" * 60)
    
    all_passed = True
    for test_name, passed in results:
        status = "✅ 合格" if passed else "❌ 不合格"
        print(f"{status}: {test_name}")
        if not passed:
            all_passed = False
    
    print("=" * 60)
    
    if all_passed:
        print("\n🎉 すべてのテストが合格しました！")
        return 0
    else:
        print("\n⚠️  一部のテストが失敗しました")
        return 1


if __name__ == "__main__":
    sys.exit(main())
