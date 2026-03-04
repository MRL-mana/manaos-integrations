#!/usr/bin/env python3
"""
ManaOS システムアラート監視
リソース・セキュリティ・サービスの異常を検知して通知
"""
import psutil
import subprocess
import requests
import json
import os
from datetime import datetime
from typing import Dict, List, Any
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("alert_monitor")

class SystemAlertMonitor:
    """システムアラート監視クラス"""

    def __init__(self):
        # 閾値設定
        self.thresholds = {
            'cpu_critical': 95,
            'cpu_warning': 85,
            'memory_critical': 90,
            'memory_warning': 80,
            'disk_critical': 90,
            'disk_warning': 85,
            'service_restart_limit': 50,  # 再起動回数の上限
        }

        # アラート履歴（重複通知防止用）
        self.alert_history = {}
        self.alert_cooldown = 3600  # 1時間は同じアラートを送信しない

        # 通知先設定
        self.slack_webhook = os.getenv('SLACK_WEBHOOK_URL', '')
        self.notification_log = '/root/logs/system_alerts.log'

    def check_system_resources(self) -> List[Dict[str, Any]]:
        """システムリソースチェック"""
        alerts = []

        # CPU使用率
        cpu_percent = psutil.cpu_percent(interval=1)
        if cpu_percent >= self.thresholds['cpu_critical']:
            alerts.append({
                'level': 'CRITICAL',
                'category': 'CPU',
                'message': f'CPU使用率が危険水準: {cpu_percent}%',
                'value': cpu_percent
            })
        elif cpu_percent >= self.thresholds['cpu_warning']:
            alerts.append({
                'level': 'WARNING',
                'category': 'CPU',
                'message': f'CPU使用率が高い: {cpu_percent}%',
                'value': cpu_percent
            })

        # メモリ使用率
        memory = psutil.virtual_memory()
        if memory.percent >= self.thresholds['memory_critical']:
            alerts.append({
                'level': 'CRITICAL',
                'category': 'Memory',
                'message': f'メモリ使用率が危険水準: {memory.percent}%',
                'value': memory.percent
            })
        elif memory.percent >= self.thresholds['memory_warning']:
            alerts.append({
                'level': 'WARNING',
                'category': 'Memory',
                'message': f'メモリ使用率が高い: {memory.percent}%',
                'value': memory.percent
            })

        # ディスク使用率
        disk = psutil.disk_usage('/')
        if disk.percent >= self.thresholds['disk_critical']:
            alerts.append({
                'level': 'CRITICAL',
                'category': 'Disk',
                'message': f'ディスク使用率が危険水準: {disk.percent}%',
                'value': disk.percent
            })
        elif disk.percent >= self.thresholds['disk_warning']:
            alerts.append({
                'level': 'WARNING',
                'category': 'Disk',
                'message': f'ディスク使用率が高い: {disk.percent}%',
                'value': disk.percent
            })

        return alerts

    def check_docker_services(self) -> List[Dict[str, Any]]:
        """Dockerサービスチェック"""
        alerts = []

        try:
            # ManaOS v3.0サービスのヘルスチェック
            services = [
                ('orchestrator', 9200),
                ('intention', 9201),
                ('policy', 9202),
                ('actuator', 9203),
                ('ingestor', 9204),
                ('insight', 9205),
            ]

            for name, port in services:
                try:
                    response = requests.get(f'http://localhost:{port}/health', timeout=5)
                    if not response.ok:
                        alerts.append({
                            'level': 'CRITICAL',
                            'category': 'Service',
                            'message': f'mana-{name}サービスが応答なし（ポート{port}）',
                            'service': f'mana-{name}'
                        })
                except Exception as e:
                    alerts.append({
                        'level': 'CRITICAL',
                        'category': 'Service',
                        'message': f'mana-{name}サービスに接続できません: {str(e)}',
                        'service': f'mana-{name}'
                    })
        except Exception as e:
            logger.error(f"Dockerサービスチェックエラー: {e}")

        return alerts

    def check_pm2_processes(self) -> List[Dict[str, Any]]:
        """PM2プロセスチェック"""
        alerts = []

        try:
            result = subprocess.run(
                ['pm2', 'jlist'],
                capture_output=True, text=True, timeout=10
            )
            processes_data = json.loads(result.stdout)

            for process in processes_data:
                name = process['name']
                status = process['pm2_env']['status']
                restarts = process['pm2_env']['restart_time']

                # プロセスが停止している
                if status != 'online':
                    alerts.append({
                        'level': 'CRITICAL',
                        'category': 'Process',
                        'message': f'{name}プロセスが停止中: {status}',
                        'process': name
                    })

                # 再起動回数が多すぎる
                elif restarts >= self.thresholds['service_restart_limit']:
                    alerts.append({
                        'level': 'WARNING',
                        'category': 'Process',
                        'message': f'{name}プロセスの再起動回数が多い: {restarts}回',
                        'process': name,
                        'restarts': restarts
                    })
        except Exception as e:
            logger.error(f"PM2プロセスチェックエラー: {e}")

        return alerts

    def check_fail2ban_status(self) -> List[Dict[str, Any]]:
        """fail2banステータスチェック"""
        alerts = []

        try:
            result = subprocess.run(
                ['systemctl', 'is-active', 'fail2ban'],
                capture_output=True, text=True, timeout=5
            )

            if result.stdout.strip() != 'active':
                alerts.append({
                    'level': 'CRITICAL',
                    'category': 'Security',
                    'message': 'fail2banサービスが停止しています',
                })

            # 最近のBAN数をチェック
            result = subprocess.run(
                ['fail2ban-client', 'status', 'sshd'],
                capture_output=True, text=True, timeout=10
            )

            for line in result.stdout.split('\n'):
                if 'Currently banned:' in line:
                    banned = int(line.split(':')[1].strip())
                    if banned >= 10:
                        alerts.append({
                            'level': 'WARNING',
                            'category': 'Security',
                            'message': f'多数のIPがBAN中: {banned}個（攻撃が継続中の可能性）',
                            'banned_count': banned
                        })
        except Exception as e:
            logger.error(f"fail2banチェックエラー: {e}")

        return alerts

    def check_systemd_services(self) -> List[Dict[str, Any]]:
        """systemdサービスチェック"""
        alerts = []

        try:
            result = subprocess.run(
                ['systemctl', '--failed', '--no-pager'],
                capture_output=True, text=True, timeout=10
            )

            if '0 loaded units listed' not in result.stdout:
                alerts.append({
                    'level': 'CRITICAL',
                    'category': 'System',
                    'message': 'systemdサービスに失敗があります',
                })
        except Exception as e:
            logger.error(f"systemdチェックエラー: {e}")

        return alerts

    def check_security_services_status(self) -> List[Dict[str, Any]]:
        """セキュリティ関連systemdサービスの稼働確認"""
        alerts: List[Dict[str, Any]] = []
        security_units = [
            ("mana-guard-ai.service", "Mana Guard AI サービス"),
            ("mana-security-dashboard.service", "Security Dashboard"),
            ("mana-security-monitor.service", "Security Monitor"),
        ]

        for unit, label in security_units:
            try:
                result = subprocess.run(
                    ["systemctl", "is-active", unit],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                status = result.stdout.strip()
                if status != "active":
                    alerts.append(
                        {
                            "level": "CRITICAL",
                            "category": "Security",
                            "message": f"{label}({unit}) が停止しています: {status}",
                            "unit": unit,
                        }
                    )
            except Exception as exc:
                logger.error(f"{unit} ステータス確認エラー: {exc}")
        return alerts

    def should_send_alert(self, alert: Dict[str, Any]) -> bool:
        """アラート送信すべきかチェック（クールダウン考慮）"""
        alert_key = f"{alert['category']}_{alert['message']}"
        current_time = time.time()

        if alert_key in self.alert_history:
            last_sent = self.alert_history[alert_key]
            if current_time - last_sent < self.alert_cooldown:
                return False

        self.alert_history[alert_key] = current_time
        return True

    def send_notification(self, alerts: List[Dict[str, Any]]):
        """通知送信"""
        if not alerts:
            return

        # ログに記録
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        try:
            with open(self.notification_log, 'a', encoding='utf-8') as f:
                for alert in alerts:
                    f.write(f"[{timestamp}] {alert['level']}: {alert['message']}\n")
        except Exception as e:
            logger.error(f"ログ書き込みエラー: {e}")

        # Slack通知（設定されている場合）
        if self.slack_webhook:
            self.send_slack_notification(alerts)

        # コンソール出力
        for alert in alerts:
            emoji = '🔴' if alert['level'] == 'CRITICAL' else '⚠️'
            logger.warning(f"{emoji} {alert['level']}: {alert['message']}")

    def send_slack_notification(self, alerts: List[Dict[str, Any]]):
        """Slack通知"""
        try:
            critical_count = sum(1 for a in alerts if a['level'] == 'CRITICAL')
            warning_count = sum(1 for a in alerts if a['level'] == 'WARNING')

            message = {
                "text": "🚨 ManaOSシステムアラート",
                "blocks": [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": "🚨 ManaOSシステムアラート"
                        }
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*Critical:* {critical_count}件 | *Warning:* {warning_count}件"
                        }
                    },
                    {"type": "divider"}
                ]
            }

            for alert in alerts[:10]:  # 最大10件まで
                emoji = '🔴' if alert['level'] == 'CRITICAL' else '⚠️'
                message["blocks"].append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"{emoji} *{alert['category']}*\n{alert['message']}"
                    }
                })

            requests.post(self.slack_webhook, json=message, timeout=10)
        except Exception as e:
            logger.error(f"Slack通知エラー: {e}")

    def run_monitoring_cycle(self):
        """監視サイクル実行"""
        logger.info("監視サイクル開始")

        all_alerts = []

        # 各種チェック実行
        all_alerts.extend(self.check_system_resources())
        all_alerts.extend(self.check_docker_services())
        all_alerts.extend(self.check_pm2_processes())
        all_alerts.extend(self.check_fail2ban_status())
        all_alerts.extend(self.check_systemd_services())
        all_alerts.extend(self.check_security_services_status())

        # クールダウンを考慮してフィルタリング
        alerts_to_send = [a for a in all_alerts if self.should_send_alert(a)]

        if alerts_to_send:
            self.send_notification(alerts_to_send)
            logger.info(f"アラート送信: {len(alerts_to_send)}件")
        else:
            logger.info("異常なし")

    def run(self):
        """監視ループ"""
        logger.info("🚨 システムアラート監視開始")
        logger.info(f"📍 通知ログ: {self.notification_log}")

        while True:
            try:
                self.run_monitoring_cycle()
                time.sleep(300)  # 5分ごとにチェック
            except KeyboardInterrupt:
                logger.info("監視停止")
                break
            except Exception as e:
                logger.error(f"監視エラー: {e}")
                time.sleep(60)

if __name__ == '__main__':
    monitor = SystemAlertMonitor()
    monitor.run()

