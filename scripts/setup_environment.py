#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
環境構築自動化スクリプト

本番環境へのデプロイ前に、環境を自動構築
"""

import subprocess
import sys
import os
import io
from pathlib import Path
from typing import List, Dict, Tuple
import shutil

# Windows環境でのエンコーディング対応
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")


class EnvironmentSetup:
    """環境構築自動化"""
    
    def __init__(self):
        self.base_dir = Path(__file__).parent.parent  # manaos_integrations
        self.project_root = self.base_dir.parent      # Desktop
        self.setup_steps: List[Tuple[str, bool]] = []
    
    def run_command(self, command: List[str], description: str, cwd: Path = None) -> bool:
        """コマンド実行"""
        try:
            print(f"  → {description}...", end=" ", flush=True)
            result = subprocess.run(
                command,
                cwd=str(cwd or self.base_dir),
                capture_output=True,
                timeout=300
            )
            
            if result.returncode == 0:
                print("[OK] 成功")
                self.setup_steps.append((description, True))
                return True
            else:
                print(f"[NG] 失敗")
                self.setup_steps.append((description, False))
                return False
        except Exception as e:
            print(f"[NG] エラー: {str(e)}")
            self.setup_steps.append((description, False))
            return False
    
    def setup_python_env(self) -> bool:
        """Python環境セットアップ"""
        print("\n[PKG] Python環境セットアップ")
        
        # 依存関係インストール
        self.run_command(
            [sys.executable, "-m", "pip", "install", "--upgrade", "pip"],
            "pip のアップグレード"
        )
        
        self.run_command(
            [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
            "依存パッケージのインストール"
        )
        
        # 開発用依存関係もインストール
        if (self.base_dir / "requirements-dev.txt").exists():
            self.run_command(
                [sys.executable, "-m", "pip", "install", "-r", "requirements-dev.txt"],
                "開発用依存パッケージのインストール"
            )
        
        return True
    
    def setup_environment_files(self) -> bool:
        """環境ファイルセットアップ"""
        print("\n[FILE] 環境ファイルセットアップ")
        
        # .env ファイルの作成
        env_file = self.base_dir / ".env"
        env_example = self.base_dir / ".env.example"
        
        if env_example.exists() and not env_file.exists():
            print(f"  → .env ファイルを作成中...", end=" ", flush=True)
            try:
                with open(env_example, "r", encoding="utf-8") as src:
                    env_content = src.read()
                
                with open(env_file, "w", encoding="utf-8") as dst:
                    dst.write(env_content)
                
                print("[OK] 成功")
                self.setup_steps.append((".env ファイルの作成", True))
            except Exception as e:
                print(f"[NG] エラー: {str(e)}")
                self.setup_steps.append((".env ファイルの作成", False))
        
        return True
    
    def setup_database(self) -> bool:
        """データベースセットアップ"""
        print("\n🗄️ データベースセットアップ")
        
        # SQLite の初期化（必要に応じて）
        # ここでは、データベースマイグレーションスクリプトを実行
        migration_scripts = list(self.base_dir.glob("migrations/*.py"))
        
        if migration_scripts:
            print(f"  → マイグレーション実行: {len(migration_scripts)} 個のスクリプト")
            for script in migration_scripts:
                self.run_command(
                    [sys.executable, str(script)],
                    f"マイグレーション: {script.name}"
                )
        
        return True
    
    def setup_docker(self) -> bool:
        """Docker セットアップ"""
        print("\n🐳 Docker セットアップ")
        
        # Docker がインストールされているか確認
        if shutil.which("docker") is None:
            print("  ⓘ Docker がインストールされていません（スキップ）")
            return False
        
        # Docker イメージをビルド
        self.run_command(
            ["docker", "build", "-t", "manaos-integrations:latest", "."],
            "Docker イメージのビルド",
            cwd=self.base_dir
        )
        
        return True
    
    def setup_logging(self) -> bool:
        """ロギングセットアップ"""
        print("\n📋 ロギングセットアップ")
        
        logs_dir = self.base_dir / "logs"
        logs_dir.mkdir(exist_ok=True)
        
        # ログディレクトリが作成できたか確認
        if logs_dir.exists():
            print(f"  [OK] ログディレクトリ: {logs_dir}")
            self.setup_steps.append(("ログディレクトリの作成", True))
        else:
            print(f"  [NG] ログディレクトリの作成に失敗")
            self.setup_steps.append(("ログディレクトリの作成", False))
        
        return True
    
    def setup_cache(self) -> bool:
        """キャッシュセットアップ"""
        print("\n💾 キャッシュセットアップ")
        
        for cache_dir in [".cache", ".pytest_cache", ".mypy_cache"]:
            cache_path = self.base_dir / cache_dir
            cache_path.mkdir(exist_ok=True)
        
        self.setup_steps.append(("キャッシュディレクトリの準備", True))
        print("  [OK] キャッシュディレクトリの準備")
        
        return True
    
    def run_tests(self) -> bool:
        """テスト実行"""
        print("\n🧪 テスト実行")
        
        return self.run_command(
            [sys.executable, "-m", "pytest", "tests/unit/", "-q"],
            "単体テストの実行"
        )
    
    def verify_installation(self) -> bool:
        """インストール確認"""
        print("\n✔️ インストール確認")
        
        # 主要なモジュールがインポートできるか確認
        modules_to_check = [
            "flask",
            "pytest",
            "requests",
            "pyyaml",
            "dotenv",
        ]
        
        all_ok = True
        for module in modules_to_check:
            try:
                __import__(module)
                print(f"  [OK] {module}")
                self.setup_steps.append((f"{module} のインポート確認", True))
            except ImportError:
                print(f"  [NG] {module}")
                self.setup_steps.append((f"{module} のインポート確認", False))
                all_ok = False
        
        return all_ok
    
    def report(self) -> int:
        """セットアップレポート"""
        print("\n" + "=" * 70)
        print("環境構築レポート")
        print("=" * 70)
        
        passed = sum(1 for _, status in self.setup_steps if status)
        failed = sum(1 for _, status in self.setup_steps if not status)
        
        for description, status in self.setup_steps:
            if status:
                print(f"  [OK] {description}")
            else:
                print(f"  [NG] {description}")
        
        print("\n" + "=" * 70)
        print(f"成功: {passed} / {len(self.setup_steps)} ステップ")
        print("=" * 70)
        
        if failed == 0:
            print("\n[OK] 環境構築が完了しました！")
            print("\n次のコマンドでサーバーを起動できます：")
            print("  cd manaos_integrations && python unified_api_server.py")
            return 0
        else:
            print(f"\n⚠️  {failed} 個のステップで問題が発生しました")
            return 1


def main():
    """メイン関数"""
    setup = EnvironmentSetup()
    
    print("=" * 70)
    print("ManaOS 統合環境自動構築ツール")
    print("=" * 70)
    
    # セットアップ実行
    setup.setup_python_env()
    setup.setup_environment_files()
    setup.setup_logging()
    setup.setup_cache()
    setup.setup_database()
    setup.setup_docker()
    setup.verify_installation()
    setup.run_tests()
    
    # レポート出力
    exit_code = setup.report()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
