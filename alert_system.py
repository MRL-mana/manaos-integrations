#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🚨 ManaOS アラートシステム
閾値ベースのアラート、通知機能
"""

import os
from manaos_logger import get_logger
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import json
from pathlib import Path

logger = get_logger(__name__)


class AlertSeverity(Enum):
    """アラートの深刻度"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass


class AlertRule:
    """アラートルール"""
    rule_id: str
    name: str
    metric_name: str
    threshold: float
    comparison: str  # "gt", "lt", "eq", "gte", "lte"
    severity: AlertSeverity
    duration: int = 60  # 秒（この期間閾値を超え続けたらアラート）
    enabled: bool = True
    notification_channels: List[str] = field(default_factory=list)


@dataclass


class Alert:
    """アラート"""
    alert_id: str
    rule_id: str
    severity: AlertSeverity
    message: str
    metric_name: str
    metric_value: float
    threshold: float
    triggered_at: datetime = field(default_factory=datetime.now)
    resolved_at: Optional[datetime] = None
    acknowledged: bool = False


class AlertSystem:
    """アラートシステム"""
    
    def __init__(self):
        self.rules: Dict[str, AlertRule] = {}
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: List[Alert] = []
        self.notification_handlers: Dict[str, Callable] = {}
        
        # デフォルトルール
        self._setup_default_rules()
        
        # ストレージ
        self.storage_path = Path(__file__).parent / "data" / "alerts"
        self.storage_path.mkdir(parents=True, exist_ok=True)
    
    def _setup_default_rules(self):
        """デフォルトルールを設定"""
        default_rules = [
            AlertRule(
                rule_id="cpu_high",
                name="CPU使用率が高い",
                metric_name="system.cpu.percent",
                threshold=90.0,
                comparison="gte",
                severity=AlertSeverity.WARNING,
                duration=300  # 5分間
            ),
            AlertRule(
                rule_id="memory_high",
                name="メモリ使用率が高い",
                metric_name="system.memory.percent",
                threshold=90.0,
                comparison="gte",
                severity=AlertSeverity.WARNING,
                duration=300
            ),
            AlertRule(
                rule_id="disk_high",
                name="ディスク使用率が高い",
                metric_name="system.disk.percent",
                threshold=90.0,
                comparison="gte",
                severity=AlertSeverity.WARNING,
                duration=600  # 10分間
            ),
            AlertRule(
                rule_id="error_rate_high",
                name="エラー率が高い",
                metric_name="errors.rate",
                threshold=0.1,  # 10%
                comparison="gte",
                severity=AlertSeverity.ERROR,
                duration=60
            ),
            AlertRule(
                rule_id="service_down",
                name="サービスがダウン",
                metric_name="service.health",
                threshold=0.0,
                comparison="eq",
                severity=AlertSeverity.CRITICAL,
                duration=30
            )
        ]
        
        for rule in default_rules:
            self.add_rule(rule)
    
    def add_rule(self, rule: AlertRule):
        """ルールを追加"""
        self.rules[rule.rule_id] = rule
        logger.info(f"✅ アラートルールを追加: {rule.name}")
    
    def remove_rule(self, rule_id: str):
        """ルールを削除"""
        if rule_id in self.rules:
            del self.rules[rule_id]
            logger.info(f"✅ アラートルールを削除: {rule_id}")
    
    def register_notification_handler(self, channel: str, handler: Callable):
        """通知ハンドラーを登録"""
        self.notification_handlers[channel] = handler
        logger.info(f"✅ 通知ハンドラーを登録: {channel}")
    
    def check_metric(self, metric_name: str, metric_value: float):
        """メトリクスをチェックしてアラートを発火"""
        for rule_id, rule in self.rules.items():
            if not rule.enabled:
                continue
            
            if rule.metric_name != metric_name:
                continue
            
            # 閾値チェック
            should_alert = False
            if rule.comparison == "gt" and metric_value > rule.threshold:
                should_alert = True
            elif rule.comparison == "lt" and metric_value < rule.threshold:
                should_alert = True
            elif rule.comparison == "eq" and metric_value == rule.threshold:
                should_alert = True
            elif rule.comparison == "gte" and metric_value >= rule.threshold:
                should_alert = True
            elif rule.comparison == "lte" and metric_value <= rule.threshold:
                should_alert = True
            
            if should_alert:
                self._trigger_alert(rule, metric_value)
            else:
                # アラートを解決
                if rule_id in self.active_alerts:
                    self._resolve_alert(rule_id)
    
    def _trigger_alert(self, rule: AlertRule, metric_value: float):
        """アラートを発火"""
        rule_id = rule.rule_id
        
        # 既にアクティブなアラートがある場合はスキップ
        if rule_id in self.active_alerts:
            return
        
        alert = Alert(
            alert_id=f"{rule_id}_{int(datetime.now().timestamp())}",
            rule_id=rule_id,
            severity=rule.severity,
            message=f"{rule.name}: {metric_value} {rule.comparison} {rule.threshold}",
            metric_name=rule.metric_name,
            metric_value=metric_value,
            threshold=rule.threshold
        )
        
        self.active_alerts[rule_id] = alert
        self.alert_history.append(alert)
        
        # 通知を送信
        self._send_notification(alert, rule)
        
        logger.warning(f"🚨 アラート発火: {alert.message}")
    
    def _resolve_alert(self, rule_id: str):
        """アラートを解決"""
        if rule_id in self.active_alerts:
            alert = self.active_alerts[rule_id]
            alert.resolved_at = datetime.now()
            del self.active_alerts[rule_id]
            logger.info(f"✅ アラート解決: {alert.message}")
    
    def _send_notification(self, alert: Alert, rule: AlertRule):
        """通知を送信"""
        for channel in rule.notification_channels:
            if channel in self.notification_handlers:
                try:
                    self.notification_handlers[channel](alert)
                except Exception as e:
                    logger.error(f"通知送信エラー ({channel}): {e}")
    
    def acknowledge_alert(self, alert_id: str):
        """アラートを確認済みにする"""
        for alert in self.active_alerts.values():
            if alert.alert_id == alert_id:
                alert.acknowledged = True
                logger.info(f"✅ アラートを確認済みにしました: {alert_id}")
                return True
        return False
    
    def get_active_alerts(self) -> List[Alert]:
        """アクティブなアラートを取得"""
        return list(self.active_alerts.values())
    
    def get_alert_history(self, limit: int = 100) -> List[Alert]:
        """アラート履歴を取得"""
        return self.alert_history[-limit:]
    
    def save_alerts(self):
        """アラートを保存"""
        try:
            alerts_data = {
                "active_alerts": [
                    {
                        "alert_id": alert.alert_id,
                        "rule_id": alert.rule_id,
                        "severity": alert.severity.value,
                        "message": alert.message,
                        "triggered_at": alert.triggered_at.isoformat(),
                        "acknowledged": alert.acknowledged
                    }
                    for alert in self.active_alerts.values()
                ],
                "alert_history": [
                    {
                        "alert_id": alert.alert_id,
                        "rule_id": alert.rule_id,
                        "severity": alert.severity.value,
                        "message": alert.message,
                        "triggered_at": alert.triggered_at.isoformat(),
                        "resolved_at": alert.resolved_at.isoformat() if alert.resolved_at else None
                    }
                    for alert in self.alert_history[-100:]
                ]
            }
            
            file_path = self.storage_path / "alerts.json"
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(alerts_data, f, ensure_ascii=False, indent=2)
            
        except Exception as e:
            logger.error(f"アラート保存エラー: {e}")


# 通知ハンドラー例


def email_notification_handler(alert: Alert):
    """メール通知ハンドラー（例）"""
    # 実装は環境に応じて
    logger.info(f"📧 メール通知: {alert.message}")


def slack_notification_handler(alert: Alert):
    """Slack通知ハンドラー（例）"""
    # 実装は環境に応じて
    logger.info(f"💬 Slack通知: {alert.message}")


# シングルトンインスタンス
_alert_system: Optional[AlertSystem] = None


def get_alert_system() -> AlertSystem:
    """アラートシステムのシングルトン取得"""
    global _alert_system
    if _alert_system is None:
        _alert_system = AlertSystem()
    return _alert_system

