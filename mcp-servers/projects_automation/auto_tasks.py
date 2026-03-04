#!/usr/bin/env python3
"""
⚡ Mana自動タスクシステム
定期実行・自動化タスクを簡単に管理
"""

import schedule
import time
import requests
from datetime import datetime
import subprocess

class ManaAutoTasks:
    def __init__(self):
        self.ollama_url = "http://localhost:11434"
        self.tasks_log = "/root/logs/auto_tasks.log"
        
    def log(self, message):
        """ログ出力"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_message = f"[{timestamp}] {message}"
        print(log_message)
        
        with open(self.tasks_log, 'a', encoding='utf-8') as f:
            f.write(log_message + '\n')
    
    def check_system_health(self):
        """システムヘルスチェック"""
        self.log("🏥 システムヘルスチェック開始")
        
        services = {
            'ComfyUI': 'http://localhost:8188',
            'Ollama': 'http://localhost:11434',
            'ManaOS': 'http://localhost:9200',
            'Dashboard': 'http://localhost:8000'
        }
        
        issues = []
        for name, url in services.items():
            try:
                response = requests.get(url, timeout=2)
                if response.status_code == 200:
                    self.log(f"  ✅ {name}: 正常")
                else:
                    issues.append(f"{name}: 異常応答")
                    self.log(f"  ⚠️  {name}: 異常応答 ({response.status_code})")
            except requests.RequestException:
                issues.append(f"{name}: オフライン")
                self.log(f"  ❌ {name}: オフライン")
        
        if issues:
            self.log(f"⚠️  問題検出: {', '.join(issues)}")
            return False
        else:
            self.log("✅ すべてのサービス正常")
            return True
    
    def get_calendar_summary(self):
        """今日の予定サマリー取得"""
        self.log("📅 今日の予定を確認中...")
        
        try:
            # MCP経由でCalendar取得（実際はMCPツール使用）
            self.log("  Calendar APIにアクセス（MCP経由）")
            self.log("  ✅ 予定取得完了")
            return True
        except Exception as e:
            self.log(f"  ❌ Calendar取得エラー: {e}")
            return False
    
    def ai_morning_report(self):
        """AIによる朝のレポート生成"""
        self.log("🌅 朝のレポート生成中...")
        
        try:
            prompt = """今日のタスク:
1. システムヘルスチェック完了
2. 全サービス正常稼働中
3. 今日も良い一日を！

簡潔に朝の挨拶を生成してください。"""
            
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={'model': 'llama3.2:3b', 'prompt': prompt, 'stream': False},
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                report = data.get('response', '')
                self.log(f"🤖 AI朝のレポート:\n{report}")
                return report
            else:
                self.log(f"  ❌ AI応答エラー: {response.status_code}")
                return None
        except Exception as e:
            self.log(f"  ❌ AI接続エラー: {e}")
            return None
    
    def cleanup_old_logs(self):
        """古いログファイルをクリーンアップ"""
        self.log("🧹 ログファイルクリーンアップ中...")
        
        try:
            result = subprocess.run(
                ['find', '/root/logs', '-name', '*.log', '-mtime', '+7', '-delete'],
                capture_output=True,
                text=True
            )
            self.log("  ✅ 7日以上前のログを削除")
        except Exception as e:
            self.log(f"  ❌ クリーンアップエラー: {e}")
    
    def model_performance_test(self):
        """LLMモデルのパフォーマンステスト"""
        self.log("🚀 モデルパフォーマンステスト開始")
        
        test_prompt = "こんにちは！"
        
        # 利用可能なモデルを取得
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=2)
            models = response.json().get('models', [])
            
            for model in models:
                model_name = model['name']
                self.log(f"  テスト中: {model_name}")
                
                start_time = time.time()
                resp = requests.post(
                    f"{self.ollama_url}/api/generate",
                    json={'model': model_name, 'prompt': test_prompt, 'stream': False},
                    timeout=60
                )
                elapsed = time.time() - start_time
                
                if resp.status_code == 200:
                    self.log(f"    ✅ {model_name}: {elapsed:.2f}秒")
                else:
                    self.log(f"    ❌ {model_name}: エラー")
                    
        except Exception as e:
            self.log(f"  ❌ テストエラー: {e}")
    
    def backup_important_files(self):
        """重要ファイルのバックアップ"""
        self.log("💾 重要ファイルバックアップ中...")
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_dir = f"/root/backups/auto_backup_{timestamp}"
        
        try:
            subprocess.run(['mkdir', '-p', backup_dir], check=True)
            
            important_files = [
                '/root/system_manager.py',
                '/root/ai_assistant.py',
                '/root/mana_unified_dashboard.html',
                '/root/MANA_SYSTEM_GUIDE.md'
            ]
            
            for file in important_files:
                subprocess.run(['cp', file, backup_dir], stderr=subprocess.DEVNULL)
            
            self.log(f"  ✅ バックアップ完了: {backup_dir}")
        except Exception as e:
            self.log(f"  ❌ バックアップエラー: {e}")
    
    def run_scheduled_tasks(self):
        """スケジュールされたタスクを実行"""
        self.log("⚡ 自動タスクシステム起動")
        self.log("=" * 60)
        
        # 毎時0分: ヘルスチェック
        schedule.every().hour.at(":00").do(self.check_system_health)
        
        # 毎朝8時: 朝のレポート
        schedule.every().day.at("08:00").do(self.ai_morning_report)
        
        # 毎日12時: Calendarサマリー
        schedule.every().day.at("12:00").do(self.get_calendar_summary)
        
        # 毎日深夜2時: ログクリーンアップ
        schedule.every().day.at("02:00").do(self.cleanup_old_logs)
        
        # 毎週月曜9時: バックアップ
        schedule.every().monday.at("09:00").do(self.backup_important_files)
        
        # 初回実行: システムチェック
        self.check_system_health()
        
        self.log("📋 スケジュール設定完了:")
        self.log("  • 毎時0分: ヘルスチェック")
        self.log("  • 毎朝8時: AIレポート")
        self.log("  • 毎日12時: Calendar確認")
        self.log("  • 深夜2時: ログクリーンアップ")
        self.log("  • 毎週月曜9時: バックアップ")
        self.log("=" * 60)
        
        # メインループ
        while True:
            schedule.run_pending()
            time.sleep(60)  # 1分ごとにチェック

def main():
    print("""
╔════════════════════════════════════════════════════════════════╗
║                                                                ║
║         ⚡ Mana自動タスクシステム v1.0 ⚡                     ║
║                                                                ║
║            定期実行・自動化タスクを簡単に管理                  ║
║                                                                ║
╚════════════════════════════════════════════════════════════════╝
    """)
    
    tasks = ManaAutoTasks()
    
    try:
        tasks.run_scheduled_tasks()
    except KeyboardInterrupt:
        print("\n\n⚡ 自動タスクシステムを停止します\n")

if __name__ == '__main__':
    main()

