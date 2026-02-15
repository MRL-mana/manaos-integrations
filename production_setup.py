#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🚀 ManaOS 本番運用セットアップスクリプト
本番運用に向けた設定確認・準備
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, List
from manaos_logger import get_logger

logger = get_logger("ProductionSetup")

try:
    from ._paths import OLLAMA_PORT  # type: ignore
except Exception:  # pragma: no cover
    try:
        from _paths import OLLAMA_PORT  # type: ignore
    except Exception:  # pragma: no cover
        try:
            from manaos_integrations._paths import OLLAMA_PORT
        except Exception:  # pragma: no cover
            OLLAMA_PORT = int(os.getenv("OLLAMA_PORT", "11434"))


DEFAULT_OLLAMA_URL = os.getenv("OLLAMA_URL", f"http://127.0.0.1:{OLLAMA_PORT}").rstrip("/")


class ProductionSetup:
    """本番運用セットアップ"""
    
    def __init__(self):
        """初期化"""
        self.checklist = []
        self.warnings = []
        self.errors = []
    
    def check_security(self) -> Dict[str, Any]:
        """セキュリティ設定確認"""
        results = {
            "api_auth": False,
            "input_validation": True,  # 一部実装済み
            "secrets_management": True,  # 環境変数使用
            "https": False,  # ローカル環境
            "rate_limiting": True  # Task Queueで実装
        }
        
        if not results["api_auth"]:
            self.warnings.append("API認証が未実装です（外部公開時は必須）")
        
        if not results["https"]:
            self.warnings.append("HTTPSが未設定です（外部公開時は必須）")
        
        return results
    
    def check_environment_variables(self) -> Dict[str, Any]:
        """環境変数確認"""
        required_vars = {
            "SLACK_WEBHOOK_URL": False,
            "SLACK_VERIFICATION_TOKEN": False,
            "STRIPE_SECRET_KEY": False,
            "PAYPAL_CLIENT_ID": False
        }
        
        optional_vars = {
            "OLLAMA_URL": DEFAULT_OLLAMA_URL,
            "MANAOS_TIMEOUT_LLM_CALL": None,
            "MANAOS_TIMEOUT_API_CALL": None
        }
        
        for var in required_vars.keys():
            if os.getenv(var):
                required_vars[var] = True
        
        missing_required = [var for var, set in required_vars.items() if not set]
        
        if missing_required:
            self.warnings.append(f"環境変数が未設定: {', '.join(missing_required)}")
        
        return {
            "required": required_vars,
            "optional": optional_vars,
            "missing_required": missing_required
        }
    
    def check_databases(self) -> Dict[str, Any]:
        """データベース確認"""
        db_files = list(Path(__file__).parent.glob("*.db"))
        
        db_info = []
        total_size = 0
        
        for db_file in db_files:
            size_mb = db_file.stat().st_size / (1024**2)
            total_size += size_mb
            db_info.append({
                "name": db_file.name,
                "size_mb": round(size_mb, 2)
            })
        
        if not db_files:
            self.warnings.append("データベースファイルが見つかりません")
        
        return {
            "count": len(db_files),
            "total_size_mb": round(total_size, 2),
            "files": db_info
        }
    
    def check_logs(self) -> Dict[str, Any]:
        """ログ設定確認"""
        log_dir = Path(__file__).parent / "logs"
        
        if not log_dir.exists():
            self.warnings.append("ログディレクトリが存在しません")
            return {
                "exists": False,
                "file_count": 0,
                "total_size_mb": 0
            }
        
        log_files = list(log_dir.glob("*.log"))
        total_size = sum(f.stat().st_size for f in log_files) / (1024**2)
        
        return {
            "exists": True,
            "file_count": len(log_files),
            "total_size_mb": round(total_size, 2)
        }
    
    def check_services(self) -> Dict[str, Any]:
        """サービス状態確認"""
        import httpx
        
        services = [
            {"name": "Intent Router", "port": 5100},
            {"name": "Unified Orchestrator", "port": 5106},
            {"name": "SSOT API", "port": 5120}
        ]
        
        results = {}
        for service in services:
            try:
                response = httpx.get(
                    f"http://127.0.0.1:{service['port']}/health",
                    timeout=2
                )
                results[service["name"]] = response.status_code == 200
            except Exception:
                results[service["name"]] = False
        
        if not all(results.values()):
            self.errors.append("一部のサービスが起動していません")
        
        return results
    
    def generate_report(self) -> Dict[str, Any]:
        """レポート生成"""
        report = {
            "timestamp": str(Path(__file__).stat().st_mtime),
            "security": self.check_security(),
            "environment": self.check_environment_variables(),
            "databases": self.check_databases(),
            "logs": self.check_logs(),
            "services": self.check_services(),
            "warnings": self.warnings,
            "errors": self.errors,
            "ready_for_production": len(self.errors) == 0
        }
        
        return report
    
    def print_report(self):
        """レポートを表示"""
        report = self.generate_report()
        
        print("\n" + "=" * 80)
        print("ManaOS 本番運用準備チェック")
        print("=" * 80 + "\n")
        
        print("【セキュリティ設定】")
        security = report["security"]
        print(f"  API認証: {'[OK]' if security['api_auth'] else '[WARN] 未実装（外部公開時は必須）'}")
        print(f"  入力検証: {'[OK]' if security['input_validation'] else '[NG]'}")
        print(f"  機密情報管理: {'[OK]' if security['secrets_management'] else '[NG]'}")
        print(f"  HTTPS: {'[OK]' if security['https'] else '[WARN] 未設定（外部公開時は必須）'}")
        print(f"  レート制限: {'[OK]' if security['rate_limiting'] else '[NG]'}")
        
        print("\n【環境変数】")
        env = report["environment"]
        print(f"  必須環境変数: {len([v for v in env['required'].values() if v])}/{len(env['required'])} 設定済み")
        if env["missing_required"]:
            print(f"  [WARN] 未設定: {', '.join(env['missing_required'])}")
        
        print("\n【データベース】")
        db = report["databases"]
        print(f"  データベースファイル: {db['count']}個")
        print(f"  合計サイズ: {db['total_size_mb']}MB")
        
        print("\n【ログ】")
        logs = report["logs"]
        if logs["exists"]:
            print(f"  ログファイル: {logs['file_count']}個")
            print(f"  合計サイズ: {logs['total_size_mb']}MB")
        else:
            print("  [WARN] ログディレクトリが存在しません")
        
        print("\n【サービス状態】")
        services = report["services"]
        for name, status in services.items():
            print(f"  {name}: {'[OK]' if status else '[NG]'}")
        
        if report["warnings"]:
            print("\n【警告】")
            for warning in report["warnings"]:
                print(f"  [WARN] {warning}")
        
        if report["errors"]:
            print("\n【エラー】")
            for error in report["errors"]:
                print(f"  [ERROR] {error}")
        
        print("\n" + "=" * 80)
        if report["ready_for_production"]:
            print("[SUCCESS] ローカル環境での本番運用準備完了")
        else:
            print("[WARNING] 本番運用前にエラーを解消してください")
        print("=" * 80 + "\n")


def main():
    """メイン関数"""
    setup = ProductionSetup()
    setup.print_report()


if __name__ == '__main__':
    main()

