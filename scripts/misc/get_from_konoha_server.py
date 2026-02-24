#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
このはサーバーから設定情報を取得するスクリプト
"""

import subprocess
import os
from pathlib import Path
from typing import Dict, List, Optional

def run_ssh_command(command: str) -> Optional[str]:
    """SSH経由でコマンドを実行"""
    try:
        result = subprocess.run(
            ["ssh", "konoha", command],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            return result.stdout.strip()
        else:
            print(f"[WARN] SSHコマンド実行エラー: {result.stderr}")
            return None
    except subprocess.TimeoutExpired:
        print(f"[WARN] SSHコマンドがタイムアウトしました: {command}")
        return None
    except FileNotFoundError:
        print("[WARN] SSHコマンドが見つかりません。手動で実行してください。")
        return None
    except Exception as e:
        print(f"[WARN] SSHコマンド実行エラー: {e}")
        return None

def scp_file(remote_path: str, local_path: str) -> bool:
    """SCP経由でファイルをコピー"""
    try:
        result = subprocess.run(
            ["scp", f"konoha:{remote_path}", local_path],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            return True
        else:
            print(f"[WARN] SCPコマンド実行エラー: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        print(f"[WARN] SCPコマンドがタイムアウトしました: {remote_path}")
        return False
    except FileNotFoundError:
        print("[WARN] SCPコマンドが見つかりません。手動で実行してください。")
        return False
    except Exception as e:
        print(f"[WARN] SCPコマンド実行エラー: {e}")
        return False

def get_konoha_env_vars() -> Dict[str, str]:
    """このはサーバーから環境変数を取得"""
    print("[1] このはサーバーから環境変数を取得中...")
    print("-" * 70)
    
    env_vars = {}
    
    # .envファイルを取得
    print("  .envファイルを取得中...")
    if scp_file("/root/.env", ".env.konoha"):
        print("  [OK] .envファイルを取得しました: .env.konoha")
        try:
            with open(".env.konoha", 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        env_vars[key.strip()] = value.strip()
            print(f"  [OK] {len(env_vars)}件の環境変数を読み込みました")
        except Exception as e:
            print(f"  [WARN] .envファイルの読み込みに失敗: {e}")
    else:
        print("  [WARN] .envファイルの取得に失敗しました")
    
    # 環境変数を直接取得
    print("  環境変数を直接取得中...")
    env_output = run_ssh_command("env | grep -E '(API|TOKEN|KEY|SECRET)'")
    if env_output:
        print("  [OK] 環境変数を取得しました")
        for line in env_output.split('\n'):
            if '=' in line:
                key, value = line.split('=', 1)
                env_vars[key.strip()] = value.strip()
    
    return env_vars

def get_konoha_config_files() -> List[str]:
    """このはサーバーから設定ファイルを取得"""
    print("[2] このはサーバーから設定ファイルを取得中...")
    print("-" * 70)
    
    config_files = []
    
    # 設定ファイルの場所を確認
    paths_to_check = [
        "/root/manaos_integrations/.env",
        "/root/.mana_vault/",
        "/root/manaos_integrations/configs/",
    ]
    
    for path in paths_to_check:
        print(f"  {path}を確認中...")
        result = run_ssh_command(f"test -f {path} && echo 'exists' || test -d {path} && echo 'dir' || echo 'not_found'")
        if result == "exists":
            print(f"  [OK] ファイルが見つかりました: {path}")
            config_files.append(path)
        elif result == "dir":
            print(f"  [OK] ディレクトリが見つかりました: {path}")
            config_files.append(path)
        else:
            print(f"  [INFO] 見つかりませんでした: {path}")
    
    return config_files

def update_local_env(env_vars: Dict[str, str]) -> bool:
    """ローカルの.envファイルを更新"""
    print("[3] ローカルの.envファイルを更新中...")
    print("-" * 70)
    
    env_file = Path(".env")
    
    # 既存の.envファイルを読み込む
    existing_vars = {}
    if env_file.exists():
        try:
            with open(env_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        existing_vars[key.strip()] = value.strip()
        except Exception as e:
            print(f"  [WARN] 既存の.envファイルの読み込みに失敗: {e}")
    
    # このはサーバーから取得した環境変数を追加/更新
    updated = False
    new_vars = []
    
    for key, value in env_vars.items():
        if key not in existing_vars or existing_vars[key] != value:
            existing_vars[key] = value
            updated = True
            new_vars.append(key)
            print(f"  [OK] {key}を設定しました")
    
    # .envファイルに書き込む
    if updated:
        try:
            with open(env_file, 'w', encoding='utf-8') as f:
                for key, value in existing_vars.items():
                    f.write(f"{key}={value}\n")
            print(f"  [OK] .envファイルを更新しました: {len(new_vars)}件の環境変数を追加/更新")
            return True
        except Exception as e:
            print(f"  [ERROR] .envファイルの書き込みに失敗: {e}")
            return False
    else:
        print("  [INFO] 更新する項目がありませんでした")
        return False

def main():
    """メイン処理"""
    print("=" * 70)
    print("このはサーバーから設定情報を取得")
    print("=" * 70)
    print()
    
    # このはサーバーへの接続確認
    print("[0] このはサーバーへの接続確認中...")
    print("-" * 70)
    test_output = run_ssh_command("echo 'connected'")
    if test_output == "connected":
        print("  [OK] このはサーバーに接続できました")
    else:
        print("  [ERROR] このはサーバーに接続できませんでした")
        print("  手動で以下のコマンドを実行してください:")
        print("  ssh konoha")
        print("  cat /root/.env")
        print("  scp konoha:/root/.env .env.konoha")
        return
    
    print()
    
    # 環境変数を取得
    env_vars = get_konoha_env_vars()
    
    print()
    
    # 設定ファイルを取得
    config_files = get_konoha_config_files()
    
    print()
    
    # ローカルの.envファイルを更新
    if env_vars:
        update_local_env(env_vars)
    else:
        print("[WARN] 取得した環境変数がありませんでした")
    
    print()
    
    # 結果を表示
    print("=" * 70)
    print("取得結果")
    print("=" * 70)
    print(f"環境変数: {len(env_vars)}件")
    print(f"設定ファイル: {len(config_files)}件")
    
    if env_vars:
        print()
        print("取得した環境変数:")
        for key in sorted(env_vars.keys()):
            value = env_vars[key]
            # セキュリティのため、値の一部のみ表示
            if len(value) > 20:
                display_value = value[:10] + "..." + value[-5:]
            else:
                display_value = value
            print(f"  - {key}: {display_value}")
    
    print()
    print("=" * 70)
    print("完了")
    print("=" * 70)
    print()
    print("次のステップ:")
    print("1. .envファイルを確認: notepad .env")
    print("2. 設定を確認: python check_unconfigured.py")
    print("3. 動作確認: python -c \"from manaos_complete_integration import ManaOSCompleteIntegration; integration = ManaOSCompleteIntegration(); print(integration.get_complete_status())\"")

if __name__ == "__main__":
    main()






















