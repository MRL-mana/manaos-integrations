#!/usr/bin/env python3
"""
ManaOS ポリシーシステム 通知統合
ポリシー違反、競合検出、重大な問題を通知
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from datetime import datetime
import json

class PolicyNotifier:
    """ポリシーシステム通知クラス"""

    def __init__(self):
        self.notification_file = Path("/root/logs/policy_notifications.log")
        self.notification_file.parent.mkdir(parents=True, exist_ok=True)

    def notify_policy_violation(self, pr_number: int, violations: list, pr_author: str):
        """ポリシー違反を通知"""
        message = f"""
{'='*60}
❌ ポリシー違反検出
{'='*60}

PR番号: #{pr_number}
作成者: {pr_author}
検出時刻: {datetime.now().strftime('%Y/%m/%d %H:%M:%S')}

違反内容:
"""
        for violation in violations:
            message += f"  - {violation.get('message', '')}\n"

        message += f"""
{'='*60}
詳細は /root/infra/policies/manaos-policies.yaml を参照してください。
"""

        self._log_notification("policy_violation", message, {
            "pr_number": pr_number,
            "pr_author": pr_author,
            "violations": violations
        })

        return message

    def notify_conflict(self, pr_number: int, conflicts: list):
        """競合を通知"""
        message = f"""
{'='*60}
⚠️  競合検出
{'='*60}

PR番号: #{pr_number}
検出時刻: {datetime.now().strftime('%Y/%m/%d %H:%M:%S')}

競合内容:
"""
        for conflict in conflicts:
            message += f"  - PR #{conflict.get('pr_number')}: {conflict.get('conflict_type')}\n"
            message += f"    重複ファイル: {', '.join(conflict.get('overlapping_files', [])[:3])}\n"

        message += f"""
{'='*60}
協調して変更を進めるか、重複部分を分離してください。
"""

        self._log_notification("conflict", message, {
            "pr_number": pr_number,
            "conflicts": conflicts
        })

        return message

    def notify_queue_overflow(self, queue_status: dict):
        """キュー溢れを通知"""
        message = f"""
{'='*60}
⚠️  アクションキューが詰まっています
{'='*60}

検出時刻: {datetime.now().strftime('%Y/%m/%d %H:%M:%S')}

キュー状態:
  待機中: {queue_status['pending']}件
  処理中: {queue_status['processing']}件
  失敗: {queue_status['failed']}件

{'='*60}
キューを確認して処理を進めてください。
"""

        self._log_notification("queue_overflow", message, queue_status)

        return message

    def notify_pause_activated(self):
        """PAUSE_AUTOフラグ有効化を通知"""
        message = f"""
{'='*60}
🛑 PAUSE_AUTOフラグが有効化されました
{'='*60}

検出時刻: {datetime.now().strftime('%Y/%m/%d %H:%M:%S')}

すべての自動アクションが停止しています。

解除方法:
  rm /root/infra/flags/PAUSE_AUTO

{'='*60}
"""

        self._log_notification("pause_activated", message)

        return message

    def notify_health_check_failed(self, errors: int):
        """ヘルスチェック失敗を通知"""
        message = f"""
{'='*60}
❌ ヘルスチェック失敗
{'='*60}

検出時刻: {datetime.now().strftime('%Y/%m/%d %H:%M:%S')}

エラー数: {errors}

詳細を確認:
  /root/scripts/health_all.sh
  journalctl -u manaos-policy-health-check.service

{'='*60}
"""

        self._log_notification("health_check_failed", message, {"errors": errors})

        return message

    def _log_notification(self, notification_type: str, message: str, data: dict = None):  # type: ignore
        """通知をログに記録"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "type": notification_type,
            "message": message,
            "data": data or {}
        }

        with open(self.notification_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')

        # コンソールにも出力
        print(message)

    def get_recent_notifications(self, hours: int = 24, notification_type: str = None):  # type: ignore
        """最近の通知を取得"""
        if not self.notification_file.exists():
            return []

        cutoff = datetime.now() - timedelta(hours=hours)
        notifications = []

        with open(self.notification_file, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    entry_time = datetime.fromisoformat(entry.get("timestamp", ""))
                    if entry_time > cutoff:
                        if notification_type is None or entry.get("type") == notification_type:
                            notifications.append(entry)
                except IOError:
                    pass

        return notifications

def main():
    """通知システムのテスト"""
    notifier = PolicyNotifier()

    print("🧪 通知システムのテスト\n")

    # テスト通知
    notifier.notify_policy_violation(
        pr_number=123,
        violations=[{"message": "テスト違反"}],
        pr_author="test"
    )

    notifier.notify_conflict(
        pr_number=124,
        conflicts=[{
            "pr_number": 125,
            "conflict_type": "partial_overlap",
            "overlapping_files": ["test.py"]
        }]
    )

    # 最近の通知を取得
    recent = notifier.get_recent_notifications(hours=1)
    print(f"\n📊 過去1時間の通知: {len(recent)}件")

if __name__ == "__main__":
    from datetime import timedelta
    main()



