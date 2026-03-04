#!/usr/bin/env python3
"""
ManaOS v3.0 ⇄ Slack Bridge
Orchestratorの実行結果を自動的にSlackに通知
"""

import requests
from datetime import datetime
from typing import Dict, Any


class ManaOSSlackBridge:
    """ManaOS v3.0とSlackの橋渡し"""
    
    def __init__(self, slack_service_url: str = "http://localhost:5020"):
        self.slack_url = slack_service_url
    
    def notify_orchestrator_result(
        self,
        intent: str,
        actor: str,
        policy: str,
        success: bool,
        result: Dict[str, Any],
        execution_time: float
    ):
        """
        Orchestrator実行結果をSlackに通知
        
        Args:
            intent: 検出された意図
            actor: 実行アクター（remi/luna/mina）
            policy: 適用されたポリシー（SAFE/CONFIRM/BLOCK）
            success: 実行成功/失敗
            result: 実行結果
            execution_time: 実行時間（秒）
        """
        
        # アクター別アイコン
        actor_icons = {
            'remi': '👑',
            'luna': '💼',
            'mina': '📊'
        }
        
        # ポリシー別色
        policy_colors = {
            'SAFE': 'good',
            'CONFIRM': 'warning',
            'BLOCK': 'danger'
        }
        
        status_icon = '✅' if success else '❌'
        actor_icon = actor_icons.get(actor, '🤖')
        
        # リッチメッセージで送信
        payload = {
            "channel": "general",
            "title": f"{status_icon} ManaOS Orchestrator 実行完了",
            "description": f"{actor_icon} **Actor**: {actor.upper()}\n🎯 **Intent**: {intent}\n🔐 **Policy**: {policy}",
            "fields": [
                {
                    "title": "実行時間",
                    "value": f"{execution_time:.2f}秒"
                },
                {
                    "title": "ステータス",
                    "value": "成功 ✅" if success else "失敗 ❌"
                },
                {
                    "title": "結果サマリー",
                    "value": self._format_result(result)
                }
            ],
            "footer": f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        }
        
        try:
            response = requests.post(
                f"{self.slack_url}/send/rich",
                json=payload,
                timeout=5
            )
            return response.json()
        except Exception as e:
            print(f"Slack通知エラー: {e}")
            return {"success": False, "error": str(e)}
    
    def notify_system_alert(
        self,
        level: str,
        title: str,
        message: str,
        with_approval: bool = False
    ):
        """
        システムアラートを送信
        
        Args:
            level: アラートレベル (info/warning/error/critical)
            title: タイトル
            message: メッセージ
            with_approval: 承認ボタンを表示するか
        """
        
        if with_approval:
            # インタラクティブメッセージ
            payload = {
                "channel": "alerts",
                "title": title,
                "message": message,
                "buttons": [
                    {"text": "✅ 承認", "value": "approve", "style": "primary"},
                    {"text": "❌ 却下", "value": "reject", "style": "danger"}
                ]
            }
            endpoint = "/send/interactive"
        else:
            # 通常のアラート
            payload = {
                "level": level,
                "title": title,
                "message": message
            }
            endpoint = "/send/alert"
        
        try:
            response = requests.post(
                f"{self.slack_url}{endpoint}",
                json=payload,
                timeout=5
            )
            return response.json()
        except Exception as e:
            print(f"Slack通知エラー: {e}")
            return {"success": False, "error": str(e)}
    
    def send_system_status(self, services: list):
        """
        システムステータスボードを送信
        
        Args:
            services: サービスリスト [{"name": "API", "status": "healthy", "uptime": "99.9%"}, ...]
        """
        
        payload = {
            "channel": "general",
            "services": services
        }
        
        try:
            response = requests.post(
                f"{self.slack_url}/send/status_board",
                json=payload,
                timeout=5
            )
            return response.json()
        except Exception as e:
            print(f"Slack通知エラー: {e}")
            return {"success": False, "error": str(e)}
    
    def _format_result(self, result: Dict[str, Any]) -> str:
        """実行結果を読みやすくフォーマット"""
        if not result:
            return "N/A"
        
        # 主要な結果のみ抽出
        summary_keys = ['message', 'output', 'status', 'count', 'total']
        summary = []
        
        for key in summary_keys:
            if key in result:
                value = result[key]
                if isinstance(value, str) and len(value) > 100:
                    value = value[:100] + "..."
                summary.append(f"{key}: {value}")
        
        return "\n".join(summary) if summary else str(result)[:200]


# ===== 使用例 =====
if __name__ == '__main__':
    bridge = ManaOSSlackBridge()
    
    # 1. Orchestrator実行結果の通知
    print("📤 Orchestrator実行結果を送信...")
    bridge.notify_orchestrator_result(
        intent="get_calendar_events",
        actor="luna",
        policy="SAFE",
        success=True,
        result={"message": "今日の予定を3件取得しました", "count": 3},
        execution_time=1.24
    )
    
    # 2. システムアラート
    print("📤 システムアラートを送信...")
    bridge.notify_system_alert(
        level="warning",
        title="ストレージ容量警告",
        message="ディスク使用率が80%を超えました。クリーンアップを推奨します。",
        with_approval=False
    )
    
    # 3. ステータスボード
    print("📤 システムステータスを送信...")
    bridge.send_system_status([
        {"name": "ManaOS Orchestrator", "status": "healthy", "uptime": "99.9%"},
        {"name": "Trinity Secretary", "status": "healthy", "uptime": "99.8%"},
        {"name": "AI Learning System", "status": "healthy", "uptime": "100%"},
        {"name": "Slack Integration", "status": "healthy", "uptime": "99.7%"},
    ])
    
    print("✅ 完了！Slackを確認してください。")

