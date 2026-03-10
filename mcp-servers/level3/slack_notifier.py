#!/usr/bin/env python3
"""
Slack通知Bot - Level 3運用支援
"""

import json
import requests
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict

class SlackNotifier:
    """Slack通知クラス"""
    
    def __init__(self):
        self.config_file = Path("/root/.mana_vault/slack_webhook.json")
        self.webhook_url = self._load_webhook_url()
        self.enabled = bool(self.webhook_url)
    
    def _load_webhook_url(self) -> Optional[str]:
        """Webhook URL読み込み"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                return config.get('webhook_url')
            except:
                pass
        
        # 環境変数からも取得可能
        import os
        return os.getenv('SLACK_WEBHOOK_URL')
    
    def send(self, message: str, level: str = "info", title: Optional[str] = None) -> bool:
        """Slack通知送信"""
        if not self.enabled:
            print(f"[Slack] 未設定のためログ出力のみ: {message}")
            return False
        
        # レベル別の絵文字とカラー
        emoji_map = {
            "success": "✅",
            "info": "ℹ️",
            "warning": "⚠️",
            "error": "❌",
            "night": "🌙",
            "morning": "🌅"
        }
        
        color_map = {
            "success": "good",      # 緑
            "info": "#36a64f",      # 青
            "warning": "warning",   # 黄
            "error": "danger",      # 赤
            "night": "#5865F2",     # 紫
            "morning": "#FEE75C"    # 黄
        }
        
        emoji = emoji_map.get(level, "🤖")
        color = color_map.get(level, "#808080")
        
        # タイトル自動生成
        if not title:
            title_map = {
                "success": "実装完了",
                "info": "情報",
                "warning": "警告",
                "error": "エラー発生",
                "night": "夜間モード",
                "morning": "朝のレポート"
            }
            title = title_map.get(level, "Level 3通知")
        
        # Slackメッセージ構築
        payload = {
            "text": f"{emoji} {title}",
            "attachments": [{
                "color": color,
                "text": message,
                "footer": "ManaOS Level 3",
                "ts": int(datetime.now().timestamp())
            }]
        }
        
        try:
            response = requests.post(
                self.webhook_url,  # type: ignore
                json=payload,
                timeout=10
            )
            response.raise_for_status()
            return True
        except Exception as e:
            print(f"[Slack] 送信失敗: {e}")
            return False
    
    def send_decision_report(self, decision: Dict) -> bool:
        """判断結果を通知"""
        action = decision.get('action', 'unknown')
        proposal = decision.get('proposal', {})
        decision_info = decision.get('decision_info', {})
        
        title = proposal.get('title', '不明な提案')
        confidence = decision_info.get('confidence', 0) * 100
        risk_level = decision_info.get('risk_level', 'unknown')
        
        # アクション別のレベル
        level_map = {
            'auto_implement': 'success',
            'auto_with_notify': 'info',
            'request_approval': 'warning'
        }
        level = level_map.get(action, 'info')
        
        # メッセージ作成
        action_text = {
            'auto_implement': '自動実装しました',
            'auto_with_notify': '実装しました（事後通知）',
            'request_approval': '承認待ちです'
        }.get(action, action)
        
        message = f"""
*{title}*

• アクション: {action_text}
• 信頼度: {confidence:.1f}%
• リスクレベル: {risk_level}

{proposal.get('description', '')[:200]}
"""
        
        return self.send(message, level, "Level 3自律判断")
    
    def send_morning_report(self, report: Dict) -> bool:
        """朝のレポート通知"""
        message = f"""
*Level 3 夜間活動レポート*

📊 統計:
• 提案: {report.get('proposals', 0)}件
• 実装: {report.get('implemented', 0)}件
• 承認待ち: {report.get('pending', 0)}件
• バグ修正: {report.get('bugs_fixed', 0)}件

🛡️ 健全性:
• CIパス率: {report.get('ci_pass_rate', 100)}%
• リバート率: {report.get('revert_rate', 0)}%
• 総合ヘルス: {report.get('health_score', 0)}/100

詳細: `bash /root/daily_operations.sh morning`
"""
        return self.send(message, "morning", "おはようございます")
    
    def send_night_report(self) -> bool:
        """夜間モード開始通知"""
        message = """
*夜間モード開始*

🌙 これから自動で:
• GitHub Issues分析
• 使用パターン分析
• エラーパターン分析
• 実装機会の提案（最大3件）

明日朝レポートします。おやすみなさい。
"""
        return self.send(message, "night", "Level 3 夜間モード")
    
    def send_emergency(self, reason: str) -> bool:
        """緊急停止通知"""
        message = f"""
*🚨 Level 3 緊急停止*

理由: {reason}

対応が必要です。
`python3 /root/level3/level3_master_controller.py status`
"""
        return self.send(message, "error", "緊急停止")

# グローバルインスタンス
_notifier = None

def get_notifier() -> SlackNotifier:
    """グローバルnotifierを取得"""
    global _notifier
    if _notifier is None:
        _notifier = SlackNotifier()
    return _notifier

def notify(message: str, level: str = "info", title: Optional[str] = None) -> bool:
    """簡易通知関数"""
    return get_notifier().send(message, level, title)

# テスト実行
if __name__ == "__main__":
    notifier = SlackNotifier()
    
    if not notifier.enabled:
        print("\n" + "=" * 70)
        print("⚠️  Slack Webhook未設定")
        print("=" * 70)
        print("\n設定方法:")
        print("1. Slackでwebhook URLを取得")
        print("   https://api.slack.com/messaging/webhooks")
        print("")
        print("2. 設定ファイル作成:")
        print(f"   mkdir -p {notifier.config_file.parent}")
        print(f'   echo \'{{"webhook_url": "YOUR_WEBHOOK_URL"}}\' > {notifier.config_file}')
        print("")
        print("または環境変数:")
        print('   export SLACK_WEBHOOK_URL="YOUR_WEBHOOK_URL"')
        print("")
    else:
        print("\n" + "=" * 70)
        print("🧪 Slack通知テスト")
        print("=" * 70)
        print("")
        
        # テスト通知
        tests = [
            ("テスト: Level 3起動完了", "success"),
            ("テスト: 情報通知", "info"),
            ("テスト: 警告通知", "warning")
        ]
        
        for msg, level in tests:
            print(f"送信中: {msg}")
            result = notifier.send(msg, level)
            print(f"  → {'成功' if result else '失敗'}")
        
        print("\n" + "=" * 70)
        print("✅ テスト完了")
        print("=" * 70)

