#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
デプロイメント準備チェックリスト

本番環境へのデプロイ前に実施すべき項目を確認
"""

import subprocess
import sys
import os
from pathlib import Path
from typing import Dict, List, Tuple


class DeploymentChecklist:
    """デプロイメント準備チェック"""
    
    def __init__(self):
        self.items: Dict[str, Tuple[bool, str]] = {}
        # manaos_integrations ディレクトリを基準に設定
        self.base_dir = Path(__file__).parent.parent  # scripts/../ = manaos_integrations
        self.project_root = self.base_dir.parent      # manaos_integrations/.. = Desktop
    
    def check_python_version(self) -> bool:
        """Python バージョン確認"""
        version = sys.version_info
        if version.major == 3 and version.minor >= 9:
            self.items["Python Version (3.9+)"] = (True, f"Python {version.major}.{version.minor}")
            return True
        else:
            self.items["Python Version (3.9+)"] = (False, f"Python {version.major}.{version.minor} (要 3.9+)")
            return False
    
    def check_git_status(self) -> bool:
        """Git ステータス確認"""
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.stdout.strip():
                self.items["Git Clean"] = (False, "未コミット変更がある")
                return False
            else:
                self.items["Git Clean"] = (True, "すべてコミット済み")
                return True
        except:
            self.items["Git Clean"] = (False, "Git が初期化されていない")
            return False
    
    def check_tests_passing(self) -> bool:
        """テスト成功確認"""
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pytest", "tests/unit/", "-q"],
                cwd=str(self.base_dir),
                capture_output=True,
                timeout=60
            )
            
            if result.returncode == 0:
                self.items["Tests Passing"] = (True, "全テスト成功")
                return True
            else:
                self.items["Tests Passing"] = (False, "テスト失敗あり")
                return False
        except:
            self.items["Tests Passing"] = (False, "テスト実行失敗")
            return False
    
    def check_config_files(self) -> bool:
        """設定ファイル確認"""
        required_files = [
            self.base_dir / ".env.example",
            self.base_dir / "pytest.ini",
            self.base_dir / ".pre-commit-config.yaml",
            self.base_dir / "README.md",
        ]
        
        missing = []
        for file in required_files:
            if not file.exists():
                missing.append(file.name)
        
        if missing:
            self.items["Config Files"] = (False, f"不足: {', '.join(missing)}")
            return False
        else:
            self.items["Config Files"] = (True, "すべて存在")
            return True
    
    def check_documentation(self) -> bool:
        """ドキュメント確認"""
        required_docs = [
            self.base_dir / "README.md",
            self.base_dir / "ENHANCEMENT_REPORT.md",
        ]
        
        missing = []
        for doc in required_docs:
            if not doc.exists():
                missing.append(doc.name)
        
        if missing:
            self.items["Documentation"] = (False, f"不足: {', '.join(missing)}")
            return False
        else:
            self.items["Documentation"] = (True, "完備")
            return True
    
    def check_dependencies(self) -> bool:
        """依存関係セット確認"""
        required = [
            "flask", "pytest", "requests",
            "pyyaml", "python-dotenv", "cryptography"
        ]
        
        try:
            result = subprocess.run(
                ["pip", "list", "--format=json"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            import json
            installed = {pkg["name"].lower() for pkg in json.loads(result.stdout)}
            
            missing = [pkg for pkg in required if pkg.lower() not in installed]
            
            if missing:
                self.items["Dependencies"] = (False, f"不足: {', '.join(missing)}")
                return False
            else:
                self.items["Dependencies"] = (True, "すべてインストール済み")
                return True
        except:
            self.items["Dependencies"] = (False, "確認失敗")
            return False
    
    def check_docker_ready(self) -> bool:
        """Docker 準備確認"""
        docker_files = [
            self.base_dir / "Dockerfile",
            self.base_dir / ".dockerignore",
            self.base_dir / "docker-compose.yml",
        ]
        
        missing = []
        for file in docker_files:
            if not file.exists():
                missing.append(file.name)
        
        if missing:
            self.items["Docker Ready"] = (False, f"ファイル不足: {', '.join(missing)}")
            return False
        else:
            self.items["Docker Ready"] = (True, "Docker 設定ファイル完備")
            return True
    
    def check_environment_variables(self) -> bool:
        """環境変数設定確認"""
        required_env_vars = [
            "PYTHONPATH",  # オプション（設定されていなければ自動設定）
        ]
        
        # .env ファイルまたは環境変数で設定されているかチェック
        env_file_exists = (
            (self.base_dir / ".env").exists() or 
            (self.base_dir / ".env.local").exists() or
            (self.project_root / ".env").exists() or 
            (self.project_root / ".env.local").exists()
        )
        
        if not env_file_exists:
            self.items["Environment Variables"] = (False, ".env ファイルが見つかりません")
            return False
        else:
            self.items["Environment Variables"] = (True, ".env ファイル存在")
            return True
    
    def check_ssl_configuration(self) -> bool:
        """SSL/TLS 設定確認"""
        ssl_files = (
            list(self.base_dir.rglob("*.pem")) + 
            list(self.base_dir.rglob("*.crt")) +
            list(self.project_root.rglob("*.pem")) + 
            list(self.project_root.rglob("*.crt"))
        )
        
        if ssl_files:
            self.items["SSL/TLS Configuration"] = (True, f"{len(ssl_files)} 証明書ファイル")
            return True
        else:
            #開発環境でも最低限チェックするが、必須ではない
            self.items["SSL/TLS Configuration"] = (False, "SSL 証明書なし（本番環境では必須）")
            return False
    
    def check_source_code_quality(self) -> bool:
        """ソースコード品質確認"""
        try:
            result = subprocess.run(
                [sys.executable, "-m", "flake8", "--count", "."],
                cwd=str(self.base_dir),
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # flake8 の出力から警告数を取得
            if result.returncode == 0:
                self.items["Source Code Quality"] = (True, "スタイルチェック合格")
                return True
            else:
                self.items["Source Code Quality"] = (False, "スタイルエラーあり（警告レベル）")
                return False  # 警告のみ、デプロイを防ぐほどではない
        except:
            # flake8 がインストールされていない場合はスキップ
            self.items["Source Code Quality"] = (False, "チェックツール未インストール")
            return False
    
    def report(self) -> int:
        """チェックリストレポート"""
        print("\n" + "=" * 70)
        print("デプロイメント準備チェックリスト")
        print("=" * 70)
        
        passed = 0
        failed = 0
        
        for item, (status, message) in self.items.items():
            if status:
                print(f"  ✅ {item:<40} {message}")
                passed += 1
            else:
                print(f"  ❌ {item:<40} {message}")
                failed += 1
        
        print("\n" + "=" * 70)
        print(f"合格: {passed}/{len(self.items)} 項目")
        print("=" * 70)
        
        if failed == 0:
            print("✅ デプロイメント準備完了")
            return 0
        else:
            print(f"⚠️  {failed} 項目の修正が必要です")
            return 1


def main():
    """メイン関数"""
    checklist = DeploymentChecklist()
    
    # チェック実行
    checklist.check_python_version()
    checklist.check_git_status()
    checklist.check_tests_passing()
    checklist.check_config_files()
    checklist.check_documentation()
    checklist.check_dependencies()
    checklist.check_docker_ready()
    checklist.check_environment_variables()
    checklist.check_ssl_configuration()
    checklist.check_source_code_quality()
    
    # レポート出力
    exit_code = checklist.report()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
