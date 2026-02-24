#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpenRouter APIキー設定スクリプト
"""

import os
import sys
from pathlib import Path

# APIキー（環境変数または引数から取得）
API_KEY = os.getenv("OPENROUTER_API_KEY", "")
if not API_KEY:
    print("[ERROR] OPENROUTER_API_KEY 環境変数を設定してください")
    print("  例: $env:OPENROUTER_API_KEY='sk-or-v1-...' ; python set_openrouter_api_key.py")
    sys.exit(1)

def set_environment_variable():
    """環境変数を設定"""
    try:
        # Windows環境変数に設定
        import winreg
        
        # ユーザー環境変数に設定
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            "Environment",
            0,
            winreg.KEY_WRITE
        )
        
        # OPENROUTER_API_KEYを設定
        winreg.SetValueEx(key, "OPENROUTER_API_KEY", 0, winreg.REG_SZ, API_KEY)
        
        # OH_MY_OPENCODE_API_KEYも設定（後方互換性）
        winreg.SetValueEx(key, "OH_MY_OPENCODE_API_KEY", 0, winreg.REG_SZ, API_KEY)
        
        winreg.CloseKey(key)
        
        print("[OK] 環境変数を設定しました")
        print(f"   OPENROUTER_API_KEY: {API_KEY[:20]}...")
        print(f"   OH_MY_OPENCODE_API_KEY: {API_KEY[:20]}...")
        
        return True
    except Exception as e:
        print(f"[NG] 環境変数の設定に失敗: {e}")
        return False

def update_env_file():
    """ .envファイルを更新"""
    env_file = Path(__file__).parent / ".env"
    
    try:
        if env_file.exists():
            content = env_file.read_text(encoding="utf-8")
            
            # OPENROUTER_API_KEYを更新または追加
            if "OPENROUTER_API_KEY=" in content:
                # 既存の値を置き換え
                lines = content.splitlines()
                new_lines = []
                for line in lines:
                    if line.startswith("OPENROUTER_API_KEY="):
                        new_lines.append(f"OPENROUTER_API_KEY={API_KEY}")
                    else:
                        new_lines.append(line)
                env_file.write_text("\n".join(new_lines), encoding="utf-8")
                print("[OK] .envファイルを更新しました")
            else:
                # 新規追加
                env_file.write_text(content + f"\nOPENROUTER_API_KEY={API_KEY}\n", encoding="utf-8")
                print("[OK] .envファイルに追加しました")
        else:
            # 新規作成
            env_file.write_text(f"OPENROUTER_API_KEY={API_KEY}\nOH_MY_OPENCODE_API_KEY={API_KEY}\n", encoding="utf-8")
            print("[OK] .envファイルを作成しました")
        
        return True
    except Exception as e:
        print(f"[NG] .envファイルの更新に失敗: {e}")
        return False

def main():
    """メイン処理"""
    print("=" * 60)
    print("OpenRouter APIキー設定")
    print("=" * 60)
    print()
    
    # 環境変数を設定
    env_success = set_environment_variable()
    
    # .envファイルを更新
    env_file_success = update_env_file()
    
    print()
    print("=" * 60)
    if env_success and env_file_success:
        print("[OK] 設定完了！")
    else:
        print("[WARN] 一部の設定に失敗しました")
    print("=" * 60)
    print()
    print("次のステップ:")
    print("1. 新しいPowerShellウィンドウを開く（環境変数を反映）")
    print("2. 統合APIサーバーを起動: python unified_api_server.py")
    print("3. 動作確認")
    print()

if __name__ == "__main__":
    main()
