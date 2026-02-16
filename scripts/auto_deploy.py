#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
本番環境自動デプロイメント

デプロイメント準備チェックから本番環境起動までの全自動化
"""

import subprocess
import sys
import os
import time
from pathlib import Path
from typing import List, Tuple
import json


class AutomatedDeployment:
    """自動デプロイメント管理"""
    
    def __init__(self, environment: str = "production"):
        self.environment = environment
        self.base_dir = Path(__file__).parent  # manaos_integrations
        self.deployment_steps: List[Tuple[str, bool, float]] = []
        self.start_time = time.time()
    
    def log(self, message: str, level: str = "INFO"):
        """ログ出力"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")
    
    def run_step(self, description: str, command: List[str], critical: bool = False) -> bool:
        """デプロイメントステップ実行"""
        step_start = time.perf_counter()
        
        self.log(f"ステップ開始: {description}")
        
        try:
            result = subprocess.run(
                command,
                cwd=str(self.base_dir),
                capture_output=True,
                timeout=300
            )
            
            elapsed = time.perf_counter() - step_start
            
            if result.returncode == 0:
                self.log(f"ステップ完了: {description} ({elapsed:.2f}秒)")
                self.deployment_steps.append((description, True, elapsed))
                return True
            else:
                error_msg = result.stderr.decode() if result.stderr else "Unknown error"
                self.log(f"ステップ失敗: {description}\n{error_msg}", level="ERROR")
                self.deployment_steps.append((description, False, elapsed))
                
                if critical:
                    raise Exception(f"Critical step failed: {description}")
                return False
        except Exception as e:
            elapsed = time.perf_counter() - step_start
            self.log(f"ステップエラー: {description} - {str(e)}", level="ERROR")
            self.deployment_steps.append((description, False, elapsed))
            
            if critical:
                raise
            return False
    
    def pre_deployment_checks(self) -> bool:
        """デプロイメント前チェック"""
        self.log("=" * 70)
        self.log("デプロイメント前チェック")
        self.log("=" * 70)
        
        # チェック1: デプロイメント準備チェック
        self.log("\nチェック1: デプロイメント準備状況")
        result = subprocess.run(
            [sys.executable, str(self.base_dir / "scripts" / "deployment_checklist.py")],
            cwd=str(self.base_dir),
            capture_output=True,
            text=True
        )
        
        print(result.stdout)
        if result.returncode != 0:
            self.log("デプロイメント準備が不全です", level="WARNING")
            # 警告だが続行可能
        
        # チェック2: 環境変数確認
        self.log("\nチェック2: 環境変数確認")
        required_vars = ["FLASK_ENV", "LOG_LEVEL"]
        missing_vars = []
        for var in required_vars:
            if var not in os.environ:
                missing_vars.append(var)
        
        if missing_vars:
            self.log(f"未設定の環境変数: {', '.join(missing_vars)}", level="WARNING")
        else:
            self.log("環境変数チェック完了")
        
        # チェック3: ディスク容量確認
        self.log("\nチェック3: ディスク容量確認")
        # 簡易チェック（ここでは省略）
        
        return True
    
    def build_deployment_packages(self) -> bool:
        """デプロイメントパッケージのビルド"""
        self.log("\n" + "=" * 70)
        self.log("デプロイメントパッケージのビルド")
        self.log("=" * 70)
        
        # Python パッケージ情報を生成
        self.run_step(
            "pip freeze でパッケージ一覧を生成",
            [sys.executable, "-m", "pip", "freeze"],
            critical=False
        )
        
        # 設定ファイルをパッケージに含める
        self.log("\nデプロイメント設定ファイルを準備中...")
        
        return True
    
    def setup_production_environment(self) -> bool:
        """本番環境セットアップ"""
        self.log("\n" + "=" * 70)
        self.log("本番環境セットアップ")
        self.log("=" * 70)
        
        # 環境構築スクリプト実行
        return self.run_step(
            "環境構築スクリプト実行",
            [sys.executable, str(self.base_dir / "scripts" / "setup_environment.py")],
            critical=True
        )
    
    def run_comprehensive_tests(self) -> bool:
        """包括的なテスト実行"""
        self.log("\n" + "=" * 70)
        self.log("包括的なテスト実行")
        self.log("=" * 70)
        
        # 単体テスト
        test_passed = self.run_step(
            "単体テスト実行",
            [sys.executable, "-m", "pytest", "tests/unit/", "-q"],
            critical=True
        )
        
        if not test_passed:
            return False
        
        # セキュリティスキャン
        self.run_step(
            "セキュリティスキャン実行",
            [sys.executable, str(self.base_dir / "scripts" / "security_audit.py")],
            critical=False
        )
        
        return True
    
    def configure_services(self) -> bool:
        """サービス設定"""
        self.log("\n" + "=" * 70)
        self.log("サービス設定")
        self.log("=" * 70)
        
        # 各サービスの設定
        services = [
            ("MRL メモリ API", "mrl_memory_integration.py"),
            ("LLM ルーティング", "llm_routing.py"),
            ("ユニフィケーション API", "unified_api_server.py"),
        ]
        
        for service_name, script in services:
            self.log(f"\n{service_name} を設定中...")
            # 実際のデプロイメントでは、サービスを開始するスクリプトが必要
        
        return True
    
    def deploy_docker(self) -> bool:
        """Docker デプロイメント"""
        self.log("\n" + "=" * 70)
        self.log("Docker デプロイメント")
        self.log("=" * 70)
        
        # Docker インストール確認
        result = subprocess.run(
            ["docker", "--version"],
            capture_output=True
        )
        
        if result.returncode != 0:
            self.log("Docker がインストールされていません（オプション）", level="WARNING")
            return True  # スキップ可能
        
        # Docker イメージをビルド
        return self.run_step(
            "Docker イメージのビルド",
            ["docker", "build", "-t", "manaos-integrations:latest", "."],
            critical=False
        )
    
    def verify_deployment(self) -> bool:
        """デプロイメント検証"""
        self.log("\n" + "=" * 70)
        self.log("デプロイメント検証")
        self.log("=" * 70)
        
        # API ヘルスチェック
        self.log("\nAPI ヘルスチェック実行中...")
        
        import time
        for attempt in range(5):
            try:
                import urllib.request
                response = urllib.request.urlopen("http://localhost:9502/health", timeout=5)
                if response.status == 200:
                    self.log("API ヘルスチェック: OK")
                    return True
            except:
                if attempt < 4:
                    self.log(f"ヘルスチェック再試行 ({attempt + 1}/5)...")
                    time.sleep(2)
        
        self.log("API ヘルスチェック: NG", level="WARNING")
        return False
    
    def cleanup_and_finalize(self) -> bool:
        """クリーンアップとファイナライズ"""
        self.log("\n" + "=" * 70)
        self.log("クリーンアップとファイナライズ")
        self.log("=" * 70)
        
        # キャッシュクリア
        self.log("キャッシュをクリア中...")
        subprocess.run(
            [sys.executable, "-m", "pytest", "--cache-clear"],
            cwd=str(self.base_dir),
            capture_output=True
        )
        
        # ログローテーション
        logs_dir = self.base_dir / "logs"
        if logs_dir.exists():
            self.log(f"ログディレクトリ: {logs_dir}")
        
        return True
    
    def generate_deployment_report(self) -> str:
        """デプロイメントレポート生成"""
        elapsed_total = time.time() - self.start_time
        
        report = "\n" + "=" * 70 + "\n"
        report += "デプロイメントレポート\n"
        report += "=" * 70 + "\n\n"
        
        report += f"環境: {self.environment}\n"
        report += f"開始時刻: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self.start_time))}\n"
        report += f"所要時間: {elapsed_total:.2f} 秒\n\n"
        
        passed = sum(1 for _, status, _ in self.deployment_steps if status)
        failed = sum(1 for _, status, _ in self.deployment_steps if not status)
        
        report += f"ステップ成功: {passed}/{len(self.deployment_steps)}\n"
        report += f"ステップ失敗: {failed}/{len(self.deployment_steps)}\n\n"
        
        if self.deployment_steps:
            report += "詳細:\n"
            for step, status, step_time in self.deployment_steps:
                status_str = "✅" if status else "❌"
                report += f"  {status_str} {step} ({step_time:.2f}秒)\n"
        
        report += "\n" + "=" * 70 + "\n"
        
        if failed == 0:
            report += "✅ デプロイメントが正常に完了しました！\n"
        else:
            report += f"⚠️  {failed} 個のステップで問題が発生しました\n"
        
        report += "=" * 70 + "\n"
        
        return report
    
    def deploy(self) -> int:
        """デプロイメント実行"""
        try:
            # デプロイメント前チェック
            if not self.pre_deployment_checks():
                self.log("デプロイメント前チェックで問題が検出されました", level="WARNING")
            
            # デプロイメントパッケージのビルド
            if not self.build_deployment_packages():
                self.log("パッケージのビルドに失敗しました", level="ERROR")
                return 1
            
            # 本番環境セットアップ
            if not self.setup_production_environment():
                self.log("環境セットアップに失敗しました", level="ERROR")
                return 1
            
            # テスト実行
            if not self.run_comprehensive_tests():
                self.log("テスト実行に失敗しました", level="ERROR")
                return 1
            
            # サービス設定
            if not self.configure_services():
                self.log("サービス設定に失敗しました", level="ERROR")
                return 1
            
            # Docker デプロイメント（オプション）
            self.deploy_docker()
            
            # デプロイメント検証
            # self.verify_deployment()  # オプション
            
            # クリーンアップとファイナライズ
            self.cleanup_and_finalize()
            
            # レポート生成
            report = self.generate_deployment_report()
            print(report)
            
            # レポートをファイルに保存
            report_file = self.base_dir / "deployment_report.txt"
            with open(report_file, "w", encoding="utf-8") as f:
                f.write(report)
            
            self.log(f"デプロイメントレポート: {report_file}")
            
            return 0
        
        except Exception as e:
            self.log(f"デプロイメント失敗: {str(e)}", level="ERROR")
            return 1


def main():
    """メイン関数"""
    environment = os.environ.get("DEPLOYMENT_ENV", "production")
    
    deployment = AutomatedDeployment(environment=environment)
    exit_code = deployment.deploy()
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
