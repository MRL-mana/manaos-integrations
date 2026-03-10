"""
AI Simulator Alert System
アラート管理と通知システム
"""

import time
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass
from datetime import datetime
import threading

@dataclass
class Alert:
    """アラート情報"""
    id: str
    rule_name: str
    severity: str
    message: str
    timestamp: float
    resolved: bool = False
    resolved_at: Optional[float] = None

@dataclass
class NotificationConfig:
    """通知設定"""
    email_enabled: bool = False
    email_smtp_server: str = ""
    email_smtp_port: int = 587
    email_username: str = ""
    email_password: str = ""
    email_recipients: List[str] = None  # type: ignore
    webhook_enabled: bool = False
    webhook_url: str = ""
    log_enabled: bool = True

class AlertSystem:
    """アラートシステム"""
    
    def __init__(self, config: NotificationConfig):
        self.config = config
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: List[Alert] = []
        self.notification_callbacks: List[Callable] = []
        self.logger = self._setup_logger()
        
        # 通知スレッド
        self.notification_thread = None
        self.notification_queue = []
        self.is_running = False
    
    def _setup_logger(self) -> logging.Logger:
        """ログ設定"""
        logger = logging.getLogger('alert_system')
        logger.setLevel(logging.INFO)
        
        handler = logging.FileHandler('/app/logs/alert_system.log')
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        return logger
    
    def create_alert(self, rule_name: str, severity: str, message: str) -> str:
        """アラート作成"""
        alert_id = f"{rule_name}_{int(time.time())}"
        
        alert = Alert(
            id=alert_id,
            rule_name=rule_name,
            severity=severity,
            message=message,
            timestamp=time.time()
        )
        
        # アクティブアラートに追加
        self.active_alerts[alert_id] = alert
        self.alert_history.append(alert)
        
        # ログ出力
        log_level = getattr(logging, severity.upper())
        self.logger.log(log_level, f"ALERT CREATED: {rule_name} - {message}")
        
        # 通知キューに追加
        self.notification_queue.append(alert)
        
        return alert_id
    
    def resolve_alert(self, alert_id: str) -> bool:
        """アラート解決"""
        if alert_id in self.active_alerts:
            alert = self.active_alerts[alert_id]
            alert.resolved = True
            alert.resolved_at = time.time()
            
            # アクティブアラートから削除
            del self.active_alerts[alert_id]
            
            self.logger.info(f"ALERT RESOLVED: {alert.rule_name}")
            return True
        
        return False
    
    def get_active_alerts(self) -> List[Alert]:
        """アクティブアラート取得"""
        return list(self.active_alerts.values())
    
    def get_alert_history(self, hours: int = 24) -> List[Alert]:
        """アラート履歴取得"""
        cutoff_time = time.time() - (hours * 3600)
        return [alert for alert in self.alert_history if alert.timestamp >= cutoff_time]
    
    def add_notification_callback(self, callback: Callable):
        """通知コールバック追加"""
        self.notification_callbacks.append(callback)
    
    def send_email_notification(self, alert: Alert) -> bool:
        """メール通知送信"""
        if not self.config.email_enabled:
            return False
        
        try:
            # メール作成
            msg = MIMEMultipart()
            msg['From'] = self.config.email_username
            msg['To'] = ', '.join(self.config.email_recipients)
            msg['Subject'] = f"AI Simulator Alert: {alert.rule_name}"
            
            # メール本文
            body = f"""
AI Simulator Alert Notification

Alert ID: {alert.id}
Rule Name: {alert.rule_name}
Severity: {alert.severity}
Message: {alert.message}
Timestamp: {datetime.fromtimestamp(alert.timestamp).isoformat()}

Please check the AI Simulator dashboard for more details.
            """
            
            msg.attach(MIMEText(body, 'plain'))
            
            # SMTP送信
            server = smtplib.SMTP(self.config.email_smtp_server, self.config.email_smtp_port)
            server.starttls()
            server.login(self.config.email_username, self.config.email_password)
            
            text = msg.as_string()
            server.sendmail(self.config.email_username, self.config.email_recipients, text)
            server.quit()
            
            self.logger.info(f"Email notification sent for alert: {alert.id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to send email notification: {e}")
            return False
    
    def send_webhook_notification(self, alert: Alert) -> bool:
        """Webhook通知送信"""
        if not self.config.webhook_enabled:
            return False
        
        try:
            import requests
            
            payload = {
                'alert_id': alert.id,
                'rule_name': alert.rule_name,
                'severity': alert.severity,
                'message': alert.message,
                'timestamp': datetime.fromtimestamp(alert.timestamp).isoformat()
            }
            
            response = requests.post(
                self.config.webhook_url,
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                self.logger.info(f"Webhook notification sent for alert: {alert.id}")
                return True
            else:
                self.logger.error(f"Webhook notification failed: {response.status_code}")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to send webhook notification: {e}")
            return False
    
    def _process_notifications(self):
        """通知処理"""
        while self.is_running:
            try:
                if self.notification_queue:
                    alert = self.notification_queue.pop(0)
                    
                    # メール通知
                    if self.config.email_enabled:
                        self.send_email_notification(alert)
                    
                    # Webhook通知
                    if self.config.webhook_enabled:
                        self.send_webhook_notification(alert)
                    
                    # コールバック実行
                    for callback in self.notification_callbacks:
                        try:
                            callback(alert)
                        except Exception as e:
                            self.logger.error(f"Notification callback failed: {e}")
                
                time.sleep(1)
                
            except Exception as e:
                self.logger.error(f"Notification processing error: {e}")
                time.sleep(5)
    
    def start_notification_service(self):
        """通知サービス開始"""
        if not self.is_running:
            self.is_running = True
            self.notification_thread = threading.Thread(target=self._process_notifications)
            self.notification_thread.daemon = True
            self.notification_thread.start()
            self.logger.info("Notification service started")
    
    def stop_notification_service(self):
        """通知サービス停止"""
        self.is_running = False
        if self.notification_thread:
            self.notification_thread.join(timeout=5)
        self.logger.info("Notification service stopped")
    
    def get_alert_statistics(self) -> Dict:
        """アラート統計取得"""
        total_alerts = len(self.alert_history)
        active_alerts = len(self.active_alerts)
        resolved_alerts = total_alerts - active_alerts
        
        # 重要度別統計
        severity_counts = {}
        for alert in self.alert_history:
            severity_counts[alert.severity] = severity_counts.get(alert.severity, 0) + 1
        
        return {
            'total_alerts': total_alerts,
            'active_alerts': active_alerts,
            'resolved_alerts': resolved_alerts,
            'severity_breakdown': severity_counts,
            'uptime_hours': len(self.alert_history) * 0.1  # 仮の値
        }

if __name__ == "__main__":
    # ログディレクトリ作成
    import os
    os.makedirs('/app/logs', exist_ok=True)
    
    # 通知設定
    config = NotificationConfig(
        email_enabled=False,  # テスト時は無効
        webhook_enabled=False,  # テスト時は無効
        log_enabled=True
    )
    
    # アラートシステム起動
    alert_system = AlertSystem(config)
    alert_system.start_notification_service()
    
    try:
        # テストアラート作成
        alert_id = alert_system.create_alert(
            "Test Rule",
            "warning",
            "This is a test alert"
        )
        
        print(f"Created alert: {alert_id}")
        
        # 5秒待機
        time.sleep(5)
        
        # アラート解決
        alert_system.resolve_alert(alert_id)
        print("Alert resolved")
        
        # 統計表示
        stats = alert_system.get_alert_statistics()
        print(f"Alert statistics: {stats}")
        
    except KeyboardInterrupt:
        print("Stopping alert system...")
    finally:
        alert_system.stop_notification_service()