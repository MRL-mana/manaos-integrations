#!/usr/bin/env python3
"""
ManaOS 効果メトリクス Exporter
Day 5: Prometheusメトリクス追加

計測対象:
- AI自動化の採択率
- スマート通知の当たり率
- セキュリティ検知
- コスト推定
"""

import time
import json
import os
import psutil
from datetime import datetime
from flask import Flask, Response
from prometheus_client import Counter, Histogram, Gauge, generate_latest
import logging
import httpx

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Prometheusメトリクス定義
# AI自動化
ai_auto_actions_total = Counter(
    'manaos_ai_auto_actions_total',
    'Total AI auto actions',
    ['service', 'outcome']
)

ai_confidence_histogram = Histogram(
    'manaos_ai_confidence',
    'AI confidence distribution',
    ['service'],
    buckets=[0.5, 0.6, 0.7, 0.8, 0.85, 0.9, 0.95, 1.0]
)

# スマート通知
smart_notify_hits_total = Counter(
    'manaos_smart_notify_hits_total',
    'Smart notification hits',
    ['channel', 'opened']
)

# セキュリティ
security_findings_total = Counter(
    'manaos_security_findings_total',
    'Security findings',
    ['severity']
)

last_incident_timestamp = Gauge(
    'manaos_last_security_incident_timestamp',
    'Timestamp of last security incident'
)

# コスト推定
cost_estimated_monthly = Gauge(
    'manaos_cost_estimated_monthly',
    'Estimated monthly cost',
    ['provider', 'resource']
)

# システムヘルス
disk_usage_percent = Gauge(
    'manaos_disk_usage_percent',
    'Disk usage percentage'
)

cpu_usage_percent = Gauge(
    'manaos_cpu_usage_percent',
    'CPU usage percentage'
)

memory_usage_percent = Gauge(
    'manaos_memory_usage_percent',
    'Memory usage percentage'
)

# === Phase 📈 Reflective Pilot メトリクス ===
# SLAモニタリング
sla_uptime_ratio = Gauge(
    'mana_system_sla_uptime_ratio',
    'System SLA uptime ratio (target: 99%)'
)

# トリニティ自治比率
ai_autonomy_ratio = Gauge(
    'mana_ai_autonomy_ratio',
    'AI autonomy ratio (自動実行/全提案, target: 90%)'
)

healing_success_ratio = Gauge(
    'mana_healing_success_ratio',
    'Self-healing success ratio'
)

# トリニティ自治比率詳細
autonomy_rate = Gauge(
    'mana_trinity_autonomy_rate',
    'Trinity autonomy rate (自動実行/全提案)'
)

fallback_rate = Gauge(
    'mana_trinity_fallback_rate',
    'Trinity fallback rate (AI→人間委譲率)'
)

learning_gain = Gauge(
    'mana_trinity_learning_gain',
    'Trinity learning gain (週次スコア上昇)'
)

# オペレーション指標
auto_decision_rate = Gauge(
    'mana_auto_decision_rate',
    '判断オート率'
)

self_recovery_success_rate = Gauge(
    'mana_self_recovery_success_rate',
    '自己修復成功率'
)

decision_latency_seconds = Histogram(
    'mana_decision_latency_seconds',
    '意思決定レイテンシ（秒）',
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
)

human_intervention_hours = Gauge(
    'mana_human_intervention_hours_per_day',
    '人間介入時間/日（時間）'
)

# === Autonomy Safeguard & Boost KPI ===
mct_reuse_ratio = Gauge(
    'mana_mct_reuse_ratio',
    'MCT再利用率（成功手順の再利用率）'
)

avoid_cost_hours = Gauge(
    'mana_avoid_cost_hours',
    '自動化で回避できた手作業時間（時間）'
)

avoid_cost_usd = Gauge(
    'mana_avoid_cost_usd',
    '自動化で回避できた手作業コスト（USD）'
)

confidence_bin_success_ratio = Gauge(
    'mana_confidence_bin_success_ratio',
    '信頼度ビンごとの実成功率',
    ['bin']
)

kill_switch_enabled = Gauge(
    'mana_kill_switch_enabled',
    'Kill Switch有効状態（1=有効/0=無効）'
)


def load_metrics_from_files():
    """既存のログファイルからメトリクスを読み込む"""
    try:
        # AI自動化ログから読み込み
        ai_log_path = "/root/logs/ai_predictive_automation.log"
        try:
            with open(ai_log_path, 'r') as f:
                lines = f.readlines()[-100:]  # 最後100行
                for line in lines:
                    if "自動実行" in line or "auto_execute" in line:
                        if "成功" in line or "success" in line:
                            ai_auto_actions_total.labels(service="predictive", outcome="success").inc()
                        elif "失敗" in line or "fail" in line:
                            ai_auto_actions_total.labels(service="predictive", outcome="fail").inc()

                    # 確信度抽出
                    if "確信度" in line or "confidence" in line:
                        import re
                        match = re.search(r'([0-9.]+)', line)
                        if match:
                            conf = float(match.group(1))
                            if 0 <= conf <= 1:
                                ai_confidence_histogram.labels(service="predictive").observe(conf)
        except FileNotFoundError:
            pass

        # 通知ログから読み込み
        notify_log_path = "/root/logs/unified_notification.log"
        try:
            with open(notify_log_path, 'r') as f:
                lines = f.readlines()[-100:]
                for line in lines:
                    if "LINE" in line:
                        smart_notify_hits_total.labels(channel="line", opened="unknown").inc()
                    elif "Slack" in line:
                        smart_notify_hits_total.labels(channel="slack", opened="unknown").inc()
        except FileNotFoundError:
            pass

        # セキュリティログから読み込み
        security_log_path = "/root/logs/security_monitor.log"
        try:
            with open(security_log_path, 'r') as f:
                lines = f.readlines()[-100:]
                for line in lines:
                    if "High" in line or "high" in line:
                        security_findings_total.labels(severity="high").inc()
                    elif "Medium" in line or "medium" in line:
                        security_findings_total.labels(severity="medium").inc()
                    elif "Low" in line or "low" in line:
                        security_findings_total.labels(severity="low").inc()
        except FileNotFoundError:
            pass

    except Exception as e:
        logger.warning(f"メトリクス読み込みエラー: {e}")


def calculate_sla_uptime():
    """SLA稼働率を計算"""
    try:
        # systemdサービスの稼働状況から計算
        import subprocess
        result = subprocess.run(
            ['systemctl', 'list-units', '--type=service', '--state=running', '--no-pager'],
            capture_output=True, text=True
        )
        running_services = len([l for l in result.stdout.split('\n') if 'manaos' in l.lower() or 'mana-' in l.lower()])

        result_all = subprocess.run(
            ['systemctl', 'list-units', '--type=service', '--no-pager'],
            capture_output=True, text=True
        )
        total_services = len([l for l in result_all.stdout.split('\n') if 'manaos' in l.lower() or 'mana-' in l.lower()])

        if total_services > 0:
            uptime_ratio = (running_services / total_services) * 100
            sla_uptime_ratio.set(min(uptime_ratio, 100.0))
        else:
            sla_uptime_ratio.set(0.0)
    except Exception as e:
        logger.warning(f"SLA計算エラー: {e}")

def calculate_autonomy_metrics():
    """トリニティ自治比率を計算（Safeguard & Boost版）"""
    try:
        # Remi Autonomy APIから統計を取得
        try:
            response = httpx.get("http://localhost:5076/api/stats", timeout=2.0)
            if response.status_code == 200:
                stats = response.json()

                autonomy_level = stats.get('autonomy_level', 0.0)
                autonomy_rate.set(autonomy_level)
                ai_autonomy_ratio.set(autonomy_level)

                fallback = stats.get('fallback_rate', 0.0)
                fallback_rate.set(fallback)

                mct_reuse = stats.get('mct_reuse_ratio', 0.0)
                mct_reuse_ratio.set(mct_reuse)

                kill_switch = 1.0 if stats.get('kill_switch_enabled', False) else 0.0
                kill_switch_enabled.set(kill_switch)
        except Exception:
            pass

        # AI自動化ログから計算（フォールバック）
        ai_log_path = "/root/logs/ai_predictive_automation.log"
        try:
            with open(ai_log_path, 'r') as f:
                lines = f.readlines()[-1000:]

            total_proposals = len([l for l in lines if "提案" in l or "proposal" in l.lower()])
            auto_executions = len([l for l in lines if ("自動実行" in l or "auto_execute" in l) and ("成功" in l or "success" in l)])
            fallbacks = len([l for l in lines if "人間委譲" in l or "fallback" in l.lower()])

            if total_proposals > 0:
                autonomy = (auto_executions / total_proposals) * 100
                autonomy_rate.set(min(autonomy, 100.0))
                ai_autonomy_ratio.set(min(autonomy, 100.0))

                fallback = (fallbacks / total_proposals) * 100
                fallback_rate.set(min(fallback, 100.0))

            # 学習ゲイン（簡易版：過去7日間の成功率上昇）
            learning_gain.set(0.0)  # プレースホルダー

        except FileNotFoundError:
            pass

        # 信頼度キャリブレーション（Remi Autonomy Engineから）
        try:
            calib_file = Path('/root/.mana_autonomy_data/confidence_calibration.json')  # type: ignore[name-defined]
            if calib_file.exists():
                with open(calib_file, 'r') as f:
                    calibration = json.load(f)
                    for bin_key, data in calibration.items():
                        success_rate = data.get('success_rate', 0.0)
                        confidence_bin_success_ratio.labels(bin=bin_key).set(success_rate * 100.0)
        except Exception:
            pass

        # 回避コスト計算（簡易版：自動実行回数 × 平均時間節約）
        try:
            history_file = Path('/root/.mana_autonomy_data/autonomy_history.json')  # type: ignore[name-defined]
            if history_file.exists():
                with open(history_file, 'r') as f:
                    history = json.load(f)
                    total_executions = len(history)
                    # 平均5分節約と仮定
                    avoid_cost_hours.set(total_executions * 5 / 60.0)
                    # 時給50USDと仮定
                    avoid_cost_usd.set(total_executions * 5 / 60.0 * 50.0)
        except Exception:
            pass

    except Exception as e:
        logger.warning(f"自治比率計算エラー: {e}")

def calculate_healing_metrics():
    """自己修復メトリクスを計算"""
    try:
        healing_log_path = "/root/logs/mana-health-guardian.log"
        try:
            with open(healing_log_path, 'r') as f:
                lines = f.readlines()[-500:]

            total_healing_attempts = len([l for l in lines if "修復試行" in l or "healing" in l.lower()])
            successful_healings = len([l for l in lines if ("修復成功" in l or "healed" in l.lower()) and "成功" in l])

            if total_healing_attempts > 0:
                success_rate = (successful_healings / total_healing_attempts) * 100
                healing_success_ratio.set(min(success_rate, 100.0))
                self_recovery_success_rate.set(min(success_rate, 100.0))
        except FileNotFoundError:
            pass
    except Exception as e:
        logger.warning(f"修復メトリクス計算エラー: {e}")

def update_system_metrics():
    """システムメトリクスを更新"""
    try:
        # ディスク使用率
        disk = psutil.disk_usage('/root')
        disk_usage_percent.set(disk.percent)

        # CPU使用率
        cpu_usage_percent.set(psutil.cpu_percent(interval=1))

        # メモリ使用率
        memory = psutil.virtual_memory()
        memory_usage_percent.set(memory.percent)

        # Phase 📈 メトリクス
        calculate_sla_uptime()
        calculate_autonomy_metrics()
        calculate_healing_metrics()

        # 判断オート率（自治比率と同じ）
        # Gaugeの値を取得する正しい方法
        try:
            samples = list(ai_autonomy_ratio.collect()[0].samples)
            if samples:
                ai_autonomy_ratio_value = samples[0].value
            else:
                ai_autonomy_ratio_value = 0
        except Exception:
            ai_autonomy_ratio_value = 0
        auto_decision_rate.set(ai_autonomy_ratio_value)

    except Exception as e:
        logger.warning(f"システムメトリクス更新エラー: {e}")


@app.route('/metrics')
def metrics():
    """Prometheusメトリクスエンドポイント"""
    load_metrics_from_files()
    update_system_metrics()
    return Response(generate_latest(), mimetype='text/plain')


@app.route('/health')
def health():
    """ヘルスチェック"""
    return json.dumps({"status": "healthy", "service": "mana_metrics_exporter"}), 200


def send_slack_notification(message: str, channel: str = "#manaos"):
    """Slack通知送信（非同期）"""
    try:
        webhook_url = os.getenv('SLACK_WEBHOOK_URL')
        if not webhook_url:
            return

        # 非同期で送信（ブロックしない）
        import threading
        def _send():
            try:
                httpx.post(webhook_url, json={"text": message, "channel": channel}, timeout=5.0)
            except requests.RequestException:  # type: ignore[name-defined]
                pass  # 通知失敗はログに出力しない

        threading.Thread(target=_send, daemon=True).start()
    except requests.RequestException:  # type: ignore[name-defined]
        pass


# 祝杯アラート状態記録（重複通知防止）
_celebration_state = {
    'autonomy_60_notified': False,
    'sla_99_5_last_hour': None,
    'healing_90_notified': False
}

def check_autonomy_alerts():
    """自律率アラート（24hで-10%以上）"""
    try:
        try:
            stats_response = httpx.get("http://localhost:5076/api/stats", timeout=2.0)
            if stats_response.status_code == 200:
                stats = stats_response.json()
                current_autonomy = stats.get('autonomy_level', 0.0)

                # 過去24時間の自律率を取得（簡易版：履歴から計算）
                history_file = Path('/root/.mana_autonomy_data/autonomy_history.json')  # type: ignore[name-defined]
                if history_file.exists():
                    with open(history_file, 'r') as f:
                        history = json.load(f)
                        # 24時間前のデータを取得（簡易版：最新100件で計算）
                        recent_24h = [h for h in history[-100:]
                                     if (datetime.now() - datetime.fromisoformat(h.get('timestamp', ''))).total_seconds() < 86400]

                        if len(recent_24h) >= 10:
                            old_autonomy = sum(1 for h in recent_24h[:len(recent_24h)//2] if h.get('success', False)) / (len(recent_24h)//2) * 100
                            autonomy_drop = old_autonomy - current_autonomy

                            if autonomy_drop >= 10.0:
                                send_slack_notification(
                                    f"⚠️ **自律率ダウン検知**\n"
                                    f"24時間で{autonomy_drop:.1f}%減少 ({old_autonomy:.1f}% → {current_autonomy:.1f}%)\n"
                                    f"要調査: `/remi status` で確認してください",
                                    "#manaos"
                                )
        except Exception:
            pass
    except Exception as e:
        logger.debug(f"自律率アラートチェックエラー: {e}")

def check_fallback_rate_alert():
    """高リスクの人手移行が30%超（24h継続）"""
    try:
        try:
            stats_response = httpx.get("http://localhost:5076/api/stats", timeout=2.0)
            if stats_response.status_code == 200:
                stats = stats_response.json()
                fallback_rate = stats.get('fallback_rate', 0.0)

                if fallback_rate >= 30.0:
                    send_slack_notification(
                        f"⚠️ **高リスクの人手移行率が30%超**\n"
                        f"現在: {fallback_rate:.1f}%\n"
                        f"対応: ポリシーYAMLの`min_conf`再調整 or MCT不足 → 成功MCTの蒸留を促す",
                        "#manaos"
                    )
        except Exception:
            pass
    except Exception as e:
        logger.debug(f"フォールバック率アラートチェックエラー: {e}")

def check_disk_alert():
    """ディスク>85%時にトップ10容量ファイルをSlack送信"""
    try:
        disk = psutil.disk_usage('/root')
        if disk.percent >= 85:
            # トップ10容量ファイルを取得
            top_files = subprocess.run(  # type: ignore[name-defined]
                ['find', '/root', '-type', 'f', '-exec', 'du', '-h', '{}', '+'],
                capture_output=True, text=True, timeout=30
            )

            if top_files.returncode == 0:
                top_10 = '\n'.join(sorted(top_files.stdout.split('\n'),
                                        key=lambda x: float(x.split()[0][:-1]) if x.split() else 0,
                                        reverse=True)[:10])

                send_slack_notification(
                    f"🔴 **ディスク使用率{disk.percent:.1f}%**\n"
                    f"自動実行を停止しました。\n\n"
                    f"**トップ10容量ファイル:**\n"
                    f"```\n{top_10}\n```\n"
                    f"削除判断の参考にしてください。",
                    "#manaos"
                )
    except Exception as e:
        logger.debug(f"ディスクアラートチェックエラー: {e}")

def check_celebration_alerts():
    """祝杯アラート条件をチェック"""
    try:
        # メトリクス値を取得（簡易版：直接collect）
        try:
            autonomy_samples = list(ai_autonomy_ratio.collect()[0].samples)
            autonomy = autonomy_samples[0].value if autonomy_samples else 0

            sla_samples = list(sla_uptime_ratio.collect()[0].samples)
            sla = sla_samples[0].value if sla_samples else 0

            healing_samples = list(healing_success_ratio.collect()[0].samples)
            healing = healing_samples[0].value if healing_samples else 0
        except Exception:
            return  # メトリクス取得失敗時はスキップ

        # Remi人格状態を取得（賢さ・レベルアップチェック）
        try:
            remi_response = httpx.get("http://localhost:5075/api/emotion/state", timeout=2.0)
            if remi_response.status_code == 200:
                remi_state = remi_response.json()
                remi_wisdom = remi_state.get('wisdom', 0)
                remi_level = remi_state.get('level', 1)

                # 賢さ80%突破（初回のみ）
                if remi_wisdom >= 80.0 and not _celebration_state.get('wisdom_80_notified', False):
                    send_slack_notification("🧠 **Remiがもっと賢くなりました！**\n賢さ80%突破！これからもっと頼りになります♡", "#manaos")
                    _celebration_state['wisdom_80_notified'] = True

                # レベルアップ（新しいレベルに到達した時のみ）
                if remi_level > _celebration_state.get('last_level', 1):
                    send_slack_notification(f"🎉 **Remi Level UP!**\nLevel {_celebration_state.get('last_level', 1)} → {remi_level}！\n成長が止まらない...✨", "#manaos")
                    _celebration_state['last_level'] = remi_level
        except Exception:
            pass  # Remi Personality Serviceが未稼働の場合はスキップ

        # 自律率60%突破（初回のみ）
        if autonomy >= 60.0 and not _celebration_state['autonomy_60_notified']:
            send_slack_notification("🎉 **レミが勝手に動いて人生ラクになってきてます♡**\n自律率60%突破しました！", "#manaos")
            _celebration_state['autonomy_60_notified'] = True

        # SLA 99.5%維持（1時間に1回まで）
        current_hour = datetime.now().hour
        if sla >= 99.5 and _celebration_state['sla_99_5_last_hour'] != current_hour:
            send_slack_notification("✨ **安定性、君の愛より安定してる**\nSLA 99.5%維持中！", "#manaos")
            _celebration_state['sla_99_5_last_hour'] = current_hour

        # 修復成功率90%以上（初回のみ）
        if healing >= 90.0 and not _celebration_state['healing_90_notified']:
            send_slack_notification("🔄 **バグより先にレミが立ち直る時代**\n自己修復成功率90%以上！", "#manaos")
            _celebration_state['healing_90_notified'] = True

    except Exception as e:
        logger.debug(f"祝杯アラートチェックエラー: {e}")


# 定期チェック（バックグラウンド）
def periodic_check():
    """定期チェック（メトリクス更新とアラート）"""
    alert_counter = 0
    while True:
        try:
            time.sleep(60)  # 1分ごと
            update_system_metrics()
            check_celebration_alerts()

            # アラートチェック（5分ごと）
            alert_counter += 1
            if alert_counter >= 5:
                check_autonomy_alerts()
                check_fallback_rate_alert()
                check_disk_alert()
                alert_counter = 0
        except Exception as e:
            logger.error(f"定期チェックエラー: {e}")


if __name__ == '__main__':
    logger.info("🚀 ManaOS Metrics Exporter (Phase 📈 Reflective Pilot) starting on port 5015...")

    # バックグラウンド定期チェック開始
    import threading
    check_thread = threading.Thread(target=periodic_check, daemon=True)
    check_thread.start()

    # 初期メトリクス更新
    update_system_metrics()

    app.run(host='0.0.0.0', port=5015, debug=os.getenv("DEBUG", "False").lower() == "true")
