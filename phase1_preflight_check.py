#!/usr/bin/env python3
"""
Phase 1 (Read-only) デプロイ前の最終チェック
5分で終わる確認スクリプト
"""

import os
from pathlib import Path

def check_env_file():
    """環境変数ファイルのチェック"""
    env_path = Path(".env")
    
    if not env_path.exists():
        print("[ERROR] .envファイルが存在しません")
        print("   → env.production.templateをコピーして.envを作成してください")
        return False
    
    print("[OK] .envファイルが存在します")
    return True

def check_required_vars():
    """必須環境変数のチェック"""
    required_vars = {
        "REQUIRE_AUTH": "1",
        "API_KEY": None,  # 空でないことを確認
        "RATE_LIMIT_PER_MIN": None,  # 数値であることを確認
        "MAX_INPUT_CHARS": None,  # 数値であることを確認
        "FWPKM_WRITE_MODE": "readonly",
        "FWPKM_REVIEW_EFFECT": "0",
        "FWPKM_ENABLED": "1",
        "FWPKM_WRITE_ENABLED": "0"
    }
    
    errors = []
    warnings = []
    
    # .envファイルを読み込み
    env_path = Path(".env")
    if env_path.exists():
        env_vars = {}
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    if '=' in line:
                        key, value = line.split('=', 1)
                        env_vars[key.strip()] = value.strip()
        
        # 環境変数に反映
        for key, value in env_vars.items():
            os.environ[key] = value
    
    for var_name, expected_value in required_vars.items():
        actual_value = os.getenv(var_name)
        
        if actual_value is None:
            errors.append(f"[ERROR] {var_name} が設定されていません")
            continue
        
        if expected_value is None:
            # 値の検証
            if var_name == "API_KEY":
                if actual_value == "your_secure_api_key_here" or len(actual_value) < 10:
                    warnings.append(f"[WARN] {var_name} が弱いキーです（長さ: {len(actual_value)}）")
                else:
                    print(f"[OK] {var_name} が設定されています（長さ: {len(actual_value)}）")
            elif var_name in ["RATE_LIMIT_PER_MIN", "MAX_INPUT_CHARS"]:
                try:
                    int_value = int(actual_value)
                    if var_name == "RATE_LIMIT_PER_MIN" and (int_value < 10 or int_value > 1000):
                        warnings.append(f"[WARN] {var_name} が異常な値です: {int_value}（推奨: 30-60）")
                    elif var_name == "MAX_INPUT_CHARS" and int_value < 10000:
                        warnings.append(f"[WARN] {var_name} が小さすぎます: {int_value}（推奨: 200000以上）")
                    else:
                        print(f"[OK] {var_name} = {int_value}")
                except ValueError:
                    errors.append(f"[ERROR] {var_name} が数値ではありません: {actual_value}")
            else:
                print(f"[OK] {var_name} = {actual_value}")
        else:
            # 期待値と比較
            if actual_value.lower() == expected_value.lower():
                print(f"[OK] {var_name} = {actual_value}（期待値: {expected_value}）")
            else:
                errors.append(f"[ERROR] {var_name} = {actual_value}（期待値: {expected_value}）")
    
    if errors:
        print("\n[ERROR] エラー:")
        for error in errors:
            print(f"  {error}")
        return False
    
    if warnings:
        print("\n[WARN] 警告:")
        for warning in warnings:
            print(f"  {warning}")
    
    return True

def main():
    """メイン処理"""
    print("=" * 60)
    print("Phase 1 (Read-only) デプロイ前の最終チェック")
    print("=" * 60)
    print()
    
    # 1. .envファイルの存在確認
    if not check_env_file():
        return False
    
    print()
    
    # 2. 必須環境変数のチェック
    if not check_required_vars():
        print("\n[ERROR] チェック失敗。上記のエラーを修正してください。")
        return False
    
    print()
    print("=" * 60)
    print("[OK] すべてのチェックが完了しました")
    print("=" * 60)
    print()
    print("次のステップ:")
    print("1. 起動してSECURITYログを確認")
    print("2. 疎通確認を実行（phase1_connectivity_test.py）")
    print("3. ダッシュボードで初期値を確認")
    
    return True

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
