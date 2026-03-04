#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitHub日常自動化スクリプト
定期的に実行する自動化タスク
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from github_helper import GitHubHelper
from github_integration import GitHubIntegration
from datetime import datetime
import schedule
import time

class GitHubDailyAutomation:
    """GitHub日常自動化クラス"""
    
    def __init__(self, owner: str = "MRL-mana", repo: str = "manaos-integrations"):
        self.owner = owner
        self.repo = repo
        self.helper = GitHubHelper()
        self.github = GitHubIntegration()
    
    def daily_sync(self):
        """毎日の同期タスク"""
        print(f"\n[{datetime.now()}] 毎日の同期を開始...")
        
        try:
            result = self.helper.sync_with_github(self.owner, self.repo, "master")
            
            print(f"  プル: {'成功' if result['pull'] else '失敗'}")
            print(f"  コミット: {'成功' if result['commit'] else '失敗'}")
            print(f"  プッシュ: {'成功' if result['push'] else '失敗'}")
            
            if result['errors']:
                print(f"  エラー: {result['errors']}")
            
            return result
        except Exception as e:
            print(f"  エラー: {e}")
            return None
    
    def weekly_report(self):
        """週次レポート生成"""
        print(f"\n[{datetime.now()}] 週次レポートを生成...")
        
        try:
            from github_advanced_features import GitHubAdvancedFeatures
            features = GitHubAdvancedFeatures()
            
            report = features.generate_project_report(self.owner, self.repo)
            
            # レポートを保存
            report_path = Path(f"reports/weekly_report_{datetime.now().strftime('%Y%m%d')}.md")
            report_path.parent.mkdir(exist_ok=True)
            report_path.write_text(report, encoding="utf-8")
            
            print(f"  レポートを保存: {report_path}")
            
            # イシューとして作成（オプション）
            # issue = self.github.create_issue(
            #     self.owner, self.repo,
            #     f"週次レポート {datetime.now().strftime('%Y-%m-%d')}",
            #     report,
            #     labels=["report", "automated"]
            # )
            
            return report_path
        except Exception as e:
            print(f"  エラー: {e}")
            return None
    
    def check_security(self):
        """セキュリティチェック"""
        print(f"\n[{datetime.now()}] セキュリティチェックを実行...")
        
        issues = []
        
        # .envファイルがコミットされていないか確認
        import subprocess
        result = subprocess.run(
            ["git", "log", "--all", "--full-history", "--", ".env"],
            capture_output=True,
            text=True,
            check=False
        )
        
        if result.stdout:
            issues.append("⚠️ .envファイルがGit履歴に含まれています")
        
        # 認証情報ファイルの確認
        for file in [".env", "credentials.json", "token.json"]:
            result = subprocess.run(
                ["git", "check-ignore", "-v", file],
                capture_output=True,
                text=True,
                check=False
            )
            if result.returncode != 0:
                issues.append(f"⚠️ {file}が.gitignoreに含まれていません")
        
        if issues:
            print("  セキュリティ問題を検出:")
            for issue in issues:
                print(f"    {issue}")
        else:
            print("  ✅ セキュリティチェック完了（問題なし）")
        
        return issues
    
    def start_scheduler(self):
        """スケジューラーを開始"""
        print("=" * 60)
        print("GitHub自動化スケジューラーを開始")
        print("=" * 60)
        
        # 毎日午前2時に同期
        schedule.every().day.at("02:00").do(self.daily_sync)
        
        # 毎週月曜日の午前9時にレポート生成
        schedule.every().monday.at("09:00").do(self.weekly_report)
        
        # 毎日午前1時にセキュリティチェック
        schedule.every().day.at("01:00").do(self.check_security)
        
        print("\nスケジュール:")
        print("  毎日 02:00 - 同期")
        print("  毎週月曜 09:00 - 週次レポート")
        print("  毎日 01:00 - セキュリティチェック")
        print("\nスケジューラーを実行中... (Ctrl+Cで停止)")
        
        try:
            while True:
                schedule.run_pending()
                time.sleep(60)
        except KeyboardInterrupt:
            print("\nスケジューラーを停止しました")

def main():
    """メイン関数"""
    automation = GitHubDailyAutomation()
    
    # 一度だけ実行（テスト用）
    print("テスト実行:")
    automation.daily_sync()
    automation.check_security()
    
    # スケジューラーを開始する場合は以下をコメントアウト
    # automation.start_scheduler()

if __name__ == "__main__":
    main()






















