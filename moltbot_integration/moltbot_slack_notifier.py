#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ManaOS Moltbot Plan 実行結果を Slack に通知する
"""

import os
import json
import requests
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

# .env をロード
from dotenv import load_dotenv
env_file = Path(__file__).parent / ".env"
if env_file.exists():
    load_dotenv(env_file)


class MoltbotSlackNotifier:
    """Moltbot 実行結果の Slack 通知機能"""

    def __init__(self):
        self.webhook_url = os.getenv("SLACK_WEBHOOK_URL")
        self.bot_token = os.getenv("SLACK_BOT_TOKEN")
        
        if not self.webhook_url:
            raise ValueError("SLACK_WEBHOOK_URL not set in .env")

    def notify_plan_execution(
        self, 
        plan_id: str,
        status: str,
        intent: str,
        steps_done: int = 0,
        steps_total: int = 0,
        duration_seconds: float = 0.0,
        execute_events: Optional[list] = None,
        error_message: Optional[str] = None
    ) -> bool:
        """
        計画実行結果を Slack に通知
        
        Args:
            plan_id: 計画ID
            status: 実行状態 (completed, failed, pending)
            intent: 計画の意図
            steps_done: 完了ステップ数
            steps_total: 総ステップ数
            duration_seconds: 実行時間
            execute_events: 実行イベントリスト
            error_message: エラーメッセージ
            
        Returns:
            bool: 通知成功の可否
        """
        
        # ステータスに応じた色・絵文字を決定
        if status == "completed":
            color = "good"  # 緑
            emoji = "✅"
            title = "計画が正常に実行されました"
        elif status == "failed":
            color = "danger"  # 赤
            emoji = "❌"
            title = "計画の実行に失敗しました"
        else:
            color = "warning"  # 黄色
            emoji = "⏳"
            title = "計画が処理中です"

        # イベント要約
        events_text = ""
        if execute_events:
            for evt in execute_events:
                tool = evt.get("tool", "unknown")
                event = evt.get("event", "unknown")
                evt_status = evt.get("status", "unknown")
                events_text += f"• {event} (tool: `{tool}`) - {evt_status}\n"

        # Slack メッセージ構築
        payload = {
            "attachments": [
                {
                    "color": color,
                    "title": f"{emoji} {title}",
                    "title_link": f"x-manaos://moltbot/audit/{plan_id}",
                    "text": f"*意図*: _{intent}_",
                    "fields": [
                        {
                            "title": "計画ID",
                            "value": f"`{plan_id}`",
                            "short": True
                        },
                        {
                            "title": "状態",
                            "value": status.upper(),
                            "short": True
                        },
                        {
                            "title": "進行状況",
                            "value": f"{steps_done}/{steps_total} ステップ",
                            "short": True
                        },
                        {
                            "title": "実行時間",
                            "value": f"{duration_seconds:.2f} 秒",
                            "short": True
                        }
                    ],
                    "footer": "ManaOS Moltbot Gateway",
                    "ts": int(datetime.now().timestamp())
                }
            ]
        }

        # イベント詳細があれば追加
        if events_text:
            payload["attachments"][0]["fields"].append({
                "title": "実行イベント",
                "value": events_text,
                "short": False
            })

        # エラーが発生している場合
        if error_message:
            payload["attachments"][0]["fields"].append({
                "title": "エラー",
                "value": f"```\n{error_message}\n```",
                "short": False
            })

        # Slack に送信
        try:
            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                print(f"✅ Slack 通知送信成功 ({plan_id})")
                return True
            else:
                print(f"❌ Slack 通知送信失敗 ({response.status_code})")
                return False
                
        except Exception as e:
            print(f"❌ Slack 通知エラー: {e}")
            return False

    def notify_from_audit_log(self, audit_dir: str) -> bool:
        """
        監査ログから計画情報を読み込んで Slack に通知
        
        Args:
            audit_dir: 監査ログディレクトリ (plan-xxxxxxx の絶対パス)
            
        Returns:
            bool: 通知成功の可否
        """
        audit_path = Path(audit_dir)
        
        # plan.json と result.json を読み込む
        plan_file = audit_path / "plan.json"
        result_file = audit_path / "result.json"
        
        if not plan_file.exists() or not result_file.exists():
            print(f"❌ 監査ログが不完全です: {audit_dir}")
            return False

        try:
            with open(plan_file) as f:
                plan = json.load(f)
            with open(result_file) as f:
                result = json.load(f)

            # Slack 通知を送信
            return self.notify_plan_execution(
                plan_id=result.get("plan_id", "unknown"),
                status=result.get("status", "unknown"),
                intent=plan.get("intent", "不明"),
                steps_done=result.get("steps_done", 0),
                steps_total=result.get("steps_total", 0),
                duration_seconds=result.get("duration_seconds", 0.0),
                execute_events=result.get("execute_events", [])
            )
            
        except Exception as e:
            print(f"❌ 監査ログ読み込みエラー: {e}")
            return False


def test_slack_notification():
    """Slack 通知テスト実行"""
    
    print('╔═══════════════════════════════════════════════════════╗')
    print('║  🔔 Slack 通知 テスト実行                             ║')
    print('╚═══════════════════════════════════════════════════════╝')
    print()

    notifier = MoltbotSlackNotifier()

    # テスト通知1: 成功パターン
    print('📤 テスト1: 計画成功時の通知')
    success = notifier.notify_plan_execution(
        plan_id="plan-20260216-000000-test",
        status="completed",
        intent="本格運用のテスト実行 - Slack 通知確認",
        steps_done=3,
        steps_total=3,
        duration_seconds=2.345,
        execute_events=[
            {"step_id": "scan", "event": "list_files", "tool": "exec", "status": "ok"},
            {"step_id": "classify", "event": "classify_files", "tool": "skills.classify", "status": "ok"},
            {"step_id": "move", "event": "move_files", "tool": "skills.fs.move", "status": "ok"}
        ]
    )
    print(f"  結果: {'✅ 送信成功' if success else '❌ 送信失敗'}")
    print()

    # テスト通知2: 失敗パターン
    print('📤 テスト2: 計画失敗時の通知')
    failure = notifier.notify_plan_execution(
        plan_id="plan-20260216-000001-test",
        status="failed",
        intent="テスト用の失敗パターン通知",
        steps_done=1,
        steps_total=3,
        duration_seconds=0.5,
        execute_events=[
            {"step_id": "scan", "event": "list_files", "tool": "exec", "status": "ok"},
        ],
        error_message="ファイルアクセス権限エラー: /restricted/folder へのアクセスが拒否されました"
    )
    print(f"  結果: {'✅ 送信成功' if failure else '❌ 送信失敗'}")
    print()

    print('✅ Slack 通知テスト完了！')
    print()
    print('💡 実際の運用では、各計画実行後に以下のように使用します：')
    print('   result = integration.submit_file_organize_plan(...)')
    print('   notifier.notify_from_audit_log(result["audit_dir"])')


if __name__ == "__main__":
    test_slack_notification()
