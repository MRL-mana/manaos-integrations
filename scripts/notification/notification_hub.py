"""
通知ハブ（NotificationHub）
Slackを一次通知先に固定、Discord/メールを転送
送信失敗は再送＆保存
"""

import json
from manaos_logger import get_logger, get_service_logger
import time
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid

logger = get_service_logger("notification-hub")
# 既存の通知システムをインポート
try:
    from notification_system import NotificationSystem
    NOTIFICATION_SYSTEM_AVAILABLE = True
except ImportError:
    NOTIFICATION_SYSTEM_AVAILABLE = False
    logger.debug("通知システムが利用できません")


class NotificationHub:
    """通知ハブ（Slackを一次通知先に固定）"""
    
    # 優先度別ルーティング設定
    ROUTING_CONFIG = {
        "critical": {
            "slack": True,  # 必ず送信
            "discord": True,  # 転送
            "email": True  # 転送
        },
        "important": {
            "slack": True,  # 必ず送信
            "discord": True,  # 転送
            "email": False
        },
        "normal": {
            "slack": True,  # 必ず送信
            "discord": False,
            "email": False
        },
        "low": {
            "slack": True,  # 必ず送信（ただし優先度低）
            "discord": False,
            "email": False
        }
    }
    
    def __init__(self, failed_notifications_dir: Optional[str] = None):
        """
        初期化
        
        Args:
            failed_notifications_dir: 失敗通知の保存ディレクトリ（Noneの場合はデフォルト）
        """
        # 既存の通知システム
        self.notification_system = None
        if NOTIFICATION_SYSTEM_AVAILABLE:
            try:
                self.notification_system = NotificationSystem()  # type: ignore[possibly-unbound]
            except Exception as e:
                logger.warning(f"通知システムの初期化エラー: {e}")
        
        # 失敗通知の保存ディレクトリ
        if failed_notifications_dir is None:
            failed_notifications_dir = Path(__file__).parent.parent / "data" / "failed_notifications"  # type: ignore
        self.failed_notifications_dir = Path(failed_notifications_dir)  # type: ignore
        self.failed_notifications_dir.mkdir(parents=True, exist_ok=True)
        
        # 再送試行設定
        self.max_retries = 3
        self.retry_delay = 5  # 秒
    
    def _send_slack(self, message: str, retry_count: int = 0) -> bool:
        """
        Slackに送信（再送機能付き）
        
        Args:
            message: メッセージ
            retry_count: 再送試行回数
        
        Returns:
            成功時True
        """
        if not self.notification_system:
            logger.warning("通知システムが利用できません")
            return False
        
        if not self.notification_system.slack_webhook_url:
            logger.warning("Slack Webhook URLが設定されていません")
            return False
        
        try:
            success = self.notification_system.send_slack(message)
            
            if success:
                logger.info(f"[NotificationHub] Slack送信成功")
                return True
            else:
                # 再送を試みる
                if retry_count < self.max_retries:
                    logger.warning(f"[NotificationHub] Slack送信失敗、再送試行 {retry_count + 1}/{self.max_retries}")
                    time.sleep(self.retry_delay)
                    return self._send_slack(message, retry_count + 1)
                else:
                    logger.error(f"[NotificationHub] Slack送信失敗（最大再送回数に達しました）")
                    return False
        
        except Exception as e:
            logger.error(f"[NotificationHub] Slack送信エラー: {e}")
            
            # 再送を試みる
            if retry_count < self.max_retries:
                logger.warning(f"[NotificationHub] Slack送信エラー、再送試行 {retry_count + 1}/{self.max_retries}")
                time.sleep(self.retry_delay)
                return self._send_slack(message, retry_count + 1)
            else:
                logger.error(f"[NotificationHub] Slack送信エラー（最大再送回数に達しました）")
                return False
    
    def _forward_discord(self, message: str) -> bool:
        """
        Discordに転送
        
        Args:
            message: メッセージ
        
        Returns:
            成功時True
        """
        if not self.notification_system:
            return False
        
        if not self.notification_system.discord_webhook_url:
            return False
        
        try:
            success = self.notification_system.send_discord(message)
            if success:
                logger.info(f"[NotificationHub] Discord転送成功")
            return success
        except Exception as e:
            logger.warning(f"[NotificationHub] Discord転送エラー: {e}")
            return False
    
    def _forward_email(self, message: str, subject: str = "ManaOS通知") -> bool:
        """
        メールに転送
        
        Args:
            message: メッセージ
            subject: 件名
        
        Returns:
            成功時True
        """
        if not self.notification_system:
            return False
        
        if not self.notification_system.email_config:
            return False
        
        try:
            # メール送信先を取得（設定から）
            to_email = self.notification_system.email_config.get("to_email", "")
            if not to_email:
                logger.warning("メール送信先が設定されていません")
                return False
            
            success = self.notification_system.send_email(
                to_email=to_email,
                subject=subject,
                body=message
            )
            if success:
                logger.info(f"[NotificationHub] メール転送成功")
            return success
        except Exception as e:
            logger.warning(f"[NotificationHub] メール転送エラー: {e}")
            return False
    
    def _save_failed_notification(
        self,
        message: str,
        priority: str,
        target: str,
        error: str
    ):
        """
        失敗通知を保存
        
        Args:
            message: メッセージ
            priority: 優先度
            target: 送信先（slack/discord/email）
            error: エラーメッセージ
        """
        failed_notification = {
            "id": str(uuid.uuid4()),
            "message": message,
            "priority": priority,
            "target": target,
            "error": error,
            "timestamp": datetime.now().isoformat(),
            "retry_count": 0
        }
        
        try:
            # 日付別ファイルに保存
            date_str = datetime.now().strftime("%Y%m%d")
            failed_file = self.failed_notifications_dir / f"failed_{date_str}.jsonl"
            
            with open(failed_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(failed_notification, ensure_ascii=False) + '\n')
            
            logger.warning(f"[NotificationHub] 失敗通知を保存: {failed_file}")
        
        except Exception as e:
            logger.error(f"[NotificationHub] 失敗通知の保存エラー: {e}")
    
    def notify(
        self,
        message: str,
        priority: str = "normal"
    ) -> Dict[str, bool]:
        """
        通知を送信（Slackを一次通知先に固定）
        
        Args:
            message: メッセージ
            priority: 優先度（"critical", "important", "normal", "low"）
        
        Returns:
            各送信先の送信結果
        """
        if priority not in self.ROUTING_CONFIG:
            priority = "normal"
        
        routing = self.ROUTING_CONFIG[priority]
        results = {}
        
        # 1. Slackに必ず送信（一次通知先）
        slack_success = self._send_slack(message)
        results["slack"] = slack_success
        
        # Slack送信失敗時は保存
        if not slack_success:
            self._save_failed_notification(
                message=message,
                priority=priority,
                target="slack",
                error="Slack送信失敗"
            )
            
            # イベント発行（通知）
            try:
                import manaos_core_api as manaos
                manaos.emit(
                    "notification_failed",
                    {
                        "target": "slack",
                        "priority": priority,
                        "message": message[:100]
                    },
                    "critical"
                )
            except Exception:
                logger.debug("MRL Memory APIへの通知記録に失敗")
        
        # 2. 優先度に応じて転送（Slack成功後）
        if slack_success:
            # Discord転送
            if routing.get("discord", False):
                discord_success = self._forward_discord(message)
                results["discord"] = discord_success
                
                if not discord_success:
                    self._save_failed_notification(
                        message=message,
                        priority=priority,
                        target="discord",
                        error="Discord転送失敗"
                    )
            
            # メール転送
            if routing.get("email", False):
                email_success = self._forward_email(
                    message=message,
                    subject=f"[ManaOS {priority.upper()}] {message[:50]}"
                )
                results["email"] = email_success
                
                if not email_success:
                    self._save_failed_notification(
                        message=message,
                        priority=priority,
                        target="email",
                        error="メール転送失敗"
                    )
        
        logger.info(
            f"[NotificationHub] 通知送信完了: priority={priority}, "
            f"slack={results.get('slack', False)}, "
            f"discord={results.get('discord', False)}, "
            f"email={results.get('email', False)}"
        )
        
        return results
    
    def retry_failed_notifications(self, limit: int = 10) -> Dict[str, int]:
        """
        失敗通知を再送
        
        Args:
            limit: 再送する最大件数
        
        Returns:
            再送結果の統計
        """
        stats = {
            "total": 0,
            "success": 0,
            "failed": 0
        }
        
        try:
            # 最新の失敗通知ファイルを読み込む
            date_str = datetime.now().strftime("%Y%m%d")
            failed_file = self.failed_notifications_dir / f"failed_{date_str}.jsonl"
            
            if not failed_file.exists():
                logger.info("再送する失敗通知がありません")
                return stats
            
            failed_notifications = []
            with open(failed_file, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        notification = json.loads(line.strip())
                        if notification.get("retry_count", 0) < self.max_retries:
                            failed_notifications.append(notification)
                    except (json.JSONDecodeError, KeyError):
                        continue
            
            # 再送
            for notification in failed_notifications[:limit]:
                stats["total"] += 1
                
                target = notification.get("target", "slack")
                message = notification.get("message", "")
                priority = notification.get("priority", "normal")
                
                if target == "slack":
                    success = self._send_slack(message)
                elif target == "discord":
                    success = self._forward_discord(message)
                elif target == "email":
                    success = self._forward_email(message)
                else:
                    success = False
                
                if success:
                    stats["success"] += 1
                    # 成功した通知を削除（実装は省略）
                else:
                    stats["failed"] += 1
                    # 再送回数を更新
                    notification["retry_count"] = notification.get("retry_count", 0) + 1
        
        except Exception as e:
            logger.error(f"失敗通知の再送エラー: {e}")
        
        return stats


# 使用例
if __name__ == "__main__":
    hub = NotificationHub()
    
    # 通常通知
    results = hub.notify("テスト通知です", priority="normal")
    print(f"通知結果: {results}")
    
    # 重要通知
    results = hub.notify("重要な通知です", priority="important")
    print(f"通知結果: {results}")
    
    # クリティカル通知
    results = hub.notify("緊急通知です", priority="critical")
    print(f"通知結果: {results}")


















