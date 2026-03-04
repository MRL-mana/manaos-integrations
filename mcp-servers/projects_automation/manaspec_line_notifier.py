#!/usr/bin/env python3
"""
ManaSpec × LINE Notify
Archive完了時やProposal作成時にLINE通知
"""

import os
import requests
from datetime import datetime
from typing import Dict, List

class ManaSpecLINENotifier:
    """LINE Notify統合"""
    
    def __init__(self, token: str = None):
        self.token = token or os.getenv("LINE_NOTIFY_TOKEN", "")
        self.api_url = "https://notify-api.line.me/api/notify"
        
        if not self.token:
            print("⚠️ LINE_NOTIFY_TOKEN が設定されていません")
            print("設定方法: export LINE_NOTIFY_TOKEN='your_token'")
    
    def send_notification(self, message: str) -> bool:
        """LINE通知を送信"""
        if not self.token:
            print(f"⚠️ LINE未設定: {message}")
            return False
        
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            data = {"message": message}
            
            response = requests.post(self.api_url, headers=headers, data=data)
            
            if response.status_code == 200:
                print("✅ LINE通知送信成功")
                return True
            else:
                print(f"❌ LINE通知失敗: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ LINE通知エラー: {e}")
            return False
    
    def notify_proposal_created(self, change_id: str, feature: str):
        """Proposal作成通知"""
        message = f"""
🎯 ManaSpec - 新しいProposal作成

📋 Change ID: {change_id}
✨ 機能: {feature}
👩‍💼 担当: Remi（戦略指令AI）

次のステップ: レビュー & Apply実行
🔗 Dashboard: http://localhost:9302
"""
        return self.send_notification(message.strip())
    
    def notify_apply_started(self, change_id: str):
        """Apply開始通知"""
        message = f"""
⚙️ ManaSpec - 実装開始

📋 Change ID: {change_id}
👩‍🔧 担当: Luna（実務遂行AI）
🔄 ステータス: 実装中

🔗 Dashboard: http://localhost:9302
"""
        return self.send_notification(message.strip())
    
    def notify_archive_completed(self, change_id: str, specs_updated: List[str]):
        """Archive完了通知"""
        specs_list = '\n'.join([f"  • {spec}" for spec in specs_updated])
        
        message = f"""
📦 ManaSpec - Archive完了！

📋 Change ID: {change_id}
👩‍🎓 担当: Mina（洞察記録AI）

✅ 更新されたSpecs:
{specs_list}

🧠 AI Learning Systemに保存完了
📝 Obsidianに同期完了

🔗 Dashboard: http://localhost:9302
"""
        return self.send_notification(message.strip())
    
    def notify_validation_failed(self, change_id: str, errors: str):
        """Validation失敗通知"""
        message = f"""
⚠️ ManaSpec - Validation失敗

📋 Change ID: {change_id}
❌ エラー:
{errors[:200]}

修正が必要です
🔗 Dashboard: http://localhost:9302
"""
        return self.send_notification(message.strip())
    
    def notify_daily_summary(self, stats: Dict):
        """日次サマリー通知"""
        message = f"""
📊 ManaSpec - 日次レポート

📅 {datetime.now().strftime('%Y-%m-%d')}

【統計】
📋 Active Changes: {stats.get('active_changes', 0)}
📚 Total Specs: {stats.get('total_specs', 0)}
📦 Archives: {stats.get('total_archives', 0)}
🧠 AI Patterns: {stats.get('total_patterns', 0)}

【MRL Trinity】
👩‍💼 Remi: {stats.get('remi_status', 'Unknown')}
👩‍🔧 Luna: {stats.get('luna_status', 'Unknown')}
👩‍🎓 Mina: {stats.get('mina_status', 'Unknown')}

🔗 Dashboard: http://localhost:9302
"""
        return self.send_notification(message.strip())


def main():
    """テスト実行"""
    notifier = ManaSpecLINENotifier()
    
    print("\n🔔 LINE Notify テスト\n")
    
    # テスト通知
    notifier.notify_proposal_created("add-test-feature", "テスト機能の追加")
    notifier.notify_archive_completed("add-test-feature", ["greeting", "user-auth"])
    notifier.notify_daily_summary({
        "active_changes": 0,
        "total_specs": 1,
        "total_archives": 1,
        "total_patterns": 1,
        "remi_status": "Online",
        "luna_status": "Offline",
        "mina_status": "Offline"
    })


if __name__ == '__main__':
    main()

