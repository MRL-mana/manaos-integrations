#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
未設定の環境変数や統合システムを確認するスクリプト
"""

import os
from pathlib import Path
from typing import Dict, List, Any

# .envファイルから環境変数を読み込む
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass

def check_environment_variables() -> Dict[str, Any]:
    """環境変数の設定状況を確認"""
    required_vars = {
        # GitHub統合
        "GITHUB_TOKEN": "GitHub統合",
        
        # CivitAI統合
        "CIVITAI_API_KEY": "CivitAI統合",
        
        # Mem0統合
        
        # Google Drive統合
        "GOOGLE_DRIVE_CREDENTIALS": "Google Drive統合（credentials.json）",
        "GOOGLE_DRIVE_TOKEN": "Google Drive統合（token.json）",
        
        # Slack統合
        "SLACK_WEBHOOK_URL": "Slack統合（Webhook URL）",
        "SLACK_VERIFICATION_TOKEN": "Slack統合（Verification Token）",
        
        # 決済統合
        "STRIPE_SECRET_KEY": "Stripe決済統合",
        "STRIPE_PUBLISHABLE_KEY": "Stripe決済統合（公開キー）",
        "PAYPAL_CLIENT_ID": "PayPal決済統合",
        "PAYPAL_CLIENT_SECRET": "PayPal決済統合",
        
        # Rows統合
        "ROWS_API_KEY": "Rows統合",
        
        # その他
        "OBSIDIAN_VAULT_PATH": "Obsidian統合（Vaultパス）",
        "OLLAMA_URL": "Ollama統合（URL）",
        "OLLAMA_MODEL": "Ollama統合（モデル名）",
    }
    
    optional_vars = {
        "COMFYUI_URL": "ComfyUI統合（URL）",
        "MANAOS_INTEGRATION_PORT": "ManaOS統合APIサーバー（ポート）",
        "MANAOS_INTEGRATION_HOST": "ManaOS統合APIサーバー（ホスト）",
        "OPENAI_API_KEY": "Mem0統合（OpenAI API・任意）",
    }
    
    results = {
        "configured": [],
        "unconfigured": [],
        "optional": []
    }
    
    for var, description in required_vars.items():
        value = os.getenv(var)
        if value:
            results["configured"].append({
                "variable": var,
                "description": description,
                "set": True
            })
        else:
            results["unconfigured"].append({
                "variable": var,
                "description": description,
                "set": False
            })
    
    for var, description in optional_vars.items():
        value = os.getenv(var)
        results["optional"].append({
            "variable": var,
            "description": description,
            "set": bool(value),
            "value": value if value else "デフォルト値を使用"
        })
    
    return results

def check_integration_files() -> Dict[str, Any]:
    """統合に必要なファイルの存在確認"""
    files_to_check = {
        "credentials.json": "Google Drive統合（認証情報）",
        "token.json": "Google Drive統合（トークン）",
        ".env": "環境変数ファイル",
    }
    
    results = {
        "exists": [],
        "missing": []
    }
    
    base_path = Path(__file__).parent
    
    for filename, description in files_to_check.items():
        file_path = base_path / filename
        if file_path.exists():
            results["exists"].append({
                "file": filename,
                "description": description,
                "path": str(file_path)
            })
        else:
            results["missing"].append({
                "file": filename,
                "description": description,
                "path": str(file_path)
            })
    
    return results

def check_integration_status() -> Dict[str, Any]:
    """統合システムの利用可能性を確認"""
    integrations = {}
    
    # GitHub統合
    try:
        from github_integration import GitHubIntegration
        gh = GitHubIntegration()
        integrations["GitHub"] = {
            "available": gh.is_available(),
            "module": "github_integration"
        }
    except Exception as e:
        integrations["GitHub"] = {
            "available": False,
            "error": str(e)
        }
    
    # CivitAI統合
    try:
        from civitai_integration import CivitAIIntegration
        civitai = CivitAIIntegration()
        integrations["CivitAI"] = {
            "available": civitai.is_available(),
            "module": "civitai_integration"
        }
    except Exception as e:
        integrations["CivitAI"] = {
            "available": False,
            "error": str(e)
        }
    
    # Mem0統合
    try:
        from mem0_integration import Mem0Integration
        mem0 = Mem0Integration()
        integrations["Mem0"] = {
            "available": mem0.is_available(),
            "module": "mem0_integration"
        }
    except Exception as e:
        integrations["Mem0"] = {
            "available": False,
            "error": str(e)
        }
    
    # Google Drive統合
    try:
        from google_drive_integration import GoogleDriveIntegration
        drive = GoogleDriveIntegration()
        integrations["Google Drive"] = {
            "available": drive.is_available(),
            "module": "google_drive_integration"
        }
    except Exception as e:
        integrations["Google Drive"] = {
            "available": False,
            "error": str(e)
        }
    
    # Rows統合
    try:
        from rows_integration import RowsIntegration
        rows = RowsIntegration()
        available = rows.is_available()
        if available:
            # 形式チェックだけだと「キーはあるが権限/キー不正で404」のケースを見逃すため、軽く疎通
            probe = rows.list_spreadsheets(limit=1)
            if probe is None:
                integrations["Rows"] = {
                    "available": False,
                    "module": "rows_integration",
                    "error": "Rows API call failed (check ROWS_API_KEY / permissions)",
                    "details": getattr(rows, "last_error", None),
                }
            else:
                integrations["Rows"] = {
                    "available": True,
                    "module": "rows_integration",
                }
        else:
            integrations["Rows"] = {
                "available": False,
                "module": "rows_integration",
            }
    except Exception as e:
        integrations["Rows"] = {
            "available": False,
            "error": str(e)
        }
    
    # ComfyUI統合
    try:
        from comfyui_integration import ComfyUIIntegration
        comfyui = ComfyUIIntegration()
        integrations["ComfyUI"] = {
            "available": comfyui.is_available(),
            "module": "comfyui_integration"
        }
    except Exception as e:
        integrations["ComfyUI"] = {
            "available": False,
            "error": str(e)
        }
    
    return integrations

def main():
    """メイン処理"""
    print("=" * 70)
    print("未設定の環境変数・統合システム確認")
    print("=" * 70)
    
    # 環境変数の確認
    print("\n[1] 環境変数の設定状況")
    print("-" * 70)
    env_results = check_environment_variables()
    
    print(f"\n[OK] 設定済み ({len(env_results['configured'])}件):")
    for item in env_results["configured"]:
        print(f"  - {item['variable']}: {item['description']}")
    
    print(f"\n[WARN] 未設定 ({len(env_results['unconfigured'])}件):")
    for item in env_results["unconfigured"]:
        print(f"  - {item['variable']}: {item['description']}")
    
    print(f"\n[INFO] オプション設定 ({len(env_results['optional'])}件):")
    for item in env_results["optional"]:
        status = "[OK]" if item["set"] else "[DEF]"
        print(f"  {status} {item['variable']}: {item['description']} ({item['value']})")
    
    # ファイルの確認
    print("\n[2] 統合に必要なファイル")
    print("-" * 70)
    file_results = check_integration_files()
    
    print(f"\n[OK] 存在するファイル ({len(file_results['exists'])}件):")
    for item in file_results["exists"]:
        print(f"  - {item['file']}: {item['description']}")
    
    if file_results["missing"]:
        print(f"\n[WARN] 存在しないファイル ({len(file_results['missing'])}件):")
        for item in file_results["missing"]:
            print(f"  - {item['file']}: {item['description']}")
    
    # 統合システムの確認
    print("\n[3] 統合システムの利用可能性")
    print("-" * 70)
    integration_results = check_integration_status()
    
    available = [name for name, info in integration_results.items() if info.get("available")]
    unavailable = [name for name, info in integration_results.items() if not info.get("available")]
    
    print(f"\n[OK] 利用可能 ({len(available)}件):")
    for name in available:
        print(f"  - {name}")
    
    if unavailable:
        print(f"\n[WARN] 利用不可 ({len(unavailable)}件):")
        for name in unavailable:
            info = integration_results[name]
            error = info.get("error", "不明")
            print(f"  - {name}: {error}")
    
    # まとめ
    print("\n" + "=" * 70)
    print("まとめ")
    print("=" * 70)
    print(f"設定済み環境変数: {len(env_results['configured'])}件")
    print(f"未設定環境変数: {len(env_results['unconfigured'])}件")
    print(f"利用可能な統合: {len(available)}件")
    print(f"利用不可な統合: {len(unavailable)}件")
    
    if env_results["unconfigured"]:
        print("\n[TIP] 設定を推奨する統合:")
        for item in env_results["unconfigured"][:5]:  # 上位5件
            print(f"  - {item['description']} ({item['variable']})")

if __name__ == "__main__":
    main()

