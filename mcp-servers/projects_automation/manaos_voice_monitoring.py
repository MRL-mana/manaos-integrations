#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ManaOS 完全監視＋音声統合システム (Phase 12)
リアルタイム音声監視エンジン

機能:
- システムメトリクス監視 + 音声フィードバック
- 異常検知 + 即座に音声アラート
- 定期音声レポート
- 音声クエリ対応
- インテリジェント通知（重要度判定）
"""

import os
import time
import psutil
import requests
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List
import threading
import subprocess
from collections import deque

# 音声アシスタントをインポート
try:
    from manaos_voice_assistant import ManaOSVoiceAssistant
except ImportError:
    print("⚠️ 音声アシスタントが見つかりません。基本機能のみ動作します。")
    ManaOSVoiceAssistant = None


class VoiceMonitoringEngine:
    """音声統合監視エンジン"""
    
    def __init__(self, language='ja', enable_voice=True):
        self.language = language
        self.enable_voice = enable_voice
        self.db_path = '/root/manaos_voice_monitoring.db'
        self.log_path = '/root/logs/voice_monitoring.log'
        
        # 音声アシスタント初期化
        if enable_voice and ManaOSVoiceAssistant:
            try:
                self.voice = ManaOSVoiceAssistant(language=language)
            except Exception as e:
                print(f"⚠️ 音声初期化失敗: {e}")
                self.voice = None
        else:
            self.voice = None
        
        # 監視履歴（リングバッファ）
        self.metrics_history = deque(maxlen=100)
        self.alerts_history = deque(maxlen=50)
        
        # 閾値設定
        self.thresholds = {
            'cpu_warning': 80.0,
            'cpu_critical': 95.0,
            'memory_warning': 85.0,
            'memory_critical': 95.0,
            'disk_warning': 85.0,
            'disk_critical': 95.0,
            'process_warning': 200,
            'process_critical': 250
        }
        
        # 前回の状態
        self.last_alert_time = {}
        self.alert_cooldown = 300  # 5分間は同じアラートを出さない
        
        # データベース初期化
        self._init_db()
        
        # ログディレクトリ作成
        os.makedirs('/root/logs', exist_ok=True)
    
    def _init_db(self):
        """データベース初期化"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # メトリクステーブル
        c.execute('''
            CREATE TABLE IF NOT EXISTS metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                cpu_percent REAL,
                memory_percent REAL,
                disk_percent REAL,
                process_count INTEGER,
                status TEXT,
                voice_report TEXT
            )
        ''')
        
        # アラートテーブル
        c.execute('''
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                level TEXT NOT NULL,
                category TEXT NOT NULL,
                message TEXT NOT NULL,
                value REAL,
                threshold REAL,
                voice_announced BOOLEAN DEFAULT 0
            )
        ''')
        
        # 音声クエリログ
        c.execute('''
            CREATE TABLE IF NOT EXISTS voice_queries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                query TEXT NOT NULL,
                response TEXT NOT NULL,
                audio_file TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def collect_metrics(self) -> Dict:
        """システムメトリクス収集"""
        metrics = {
            'timestamp': datetime.now().isoformat(),
            'cpu_percent': psutil.cpu_percent(interval=1),
            'memory_percent': psutil.virtual_memory().percent,
            'disk_percent': psutil.disk_usage('/').percent,
            'process_count': len(psutil.pids()),
            'uptime': time.time() - psutil.boot_time(),
            'load_avg': os.getloadavg() if hasattr(os, 'getloadavg') else [0, 0, 0]
        }
        
        # ManaOS v3ステータス取得
        try:
            manaos_status = self._get_manaos_status()
            metrics['manaos'] = manaos_status
        except Exception:
            metrics['manaos'] = None
        
        # Docker状態
        try:
            docker_containers = self._get_docker_status()
            metrics['docker'] = docker_containers
        except Exception:
            metrics['docker'] = None
        
        self.metrics_history.append(metrics)
        return metrics
    
    def _get_manaos_status(self) -> Dict:
        """ManaOS v3ステータス取得"""
        try:
            response = requests.get('http://localhost:9200/health', timeout=3)
            return response.json()
        except requests.RequestException:
            return {'status': 'unknown'}
    
    def _get_docker_status(self) -> Dict:
        """Dockerステータス取得"""
        try:
            result = subprocess.run(
                ['docker', 'ps', '--format', '{{.Names}}\t{{.Status}}'],
                capture_output=True, text=True, timeout=5
            )
            containers = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    name, status = line.split('\t', 1)
                    containers.append({'name': name, 'status': status})
            return {
                'total': len(containers),
                'running': len([c for c in containers if 'Up' in c['status']]),
                'containers': containers
            }
        except Exception:
            return {'total': 0, 'running': 0, 'containers': []}
    
    def analyze_metrics(self, metrics: Dict) -> List[Dict]:
        """メトリクス分析＋異常検知"""
        alerts = []
        
        # CPU チェック
        if metrics['cpu_percent'] >= self.thresholds['cpu_critical']:
            alerts.append({
                'level': 'critical',
                'category': 'cpu',
                'message': f"CPUが危機的状態です！ {metrics['cpu_percent']:.1f}%",
                'value': metrics['cpu_percent'],
                'threshold': self.thresholds['cpu_critical']
            })
        elif metrics['cpu_percent'] >= self.thresholds['cpu_warning']:
            alerts.append({
                'level': 'warning',
                'category': 'cpu',
                'message': f"CPU使用率が高めです。 {metrics['cpu_percent']:.1f}%",
                'value': metrics['cpu_percent'],
                'threshold': self.thresholds['cpu_warning']
            })
        
        # メモリ チェック
        if metrics['memory_percent'] >= self.thresholds['memory_critical']:
            alerts.append({
                'level': 'critical',
                'category': 'memory',
                'message': f"メモリが危機的状態です！ {metrics['memory_percent']:.1f}%",
                'value': metrics['memory_percent'],
                'threshold': self.thresholds['memory_critical']
            })
        elif metrics['memory_percent'] >= self.thresholds['memory_warning']:
            alerts.append({
                'level': 'warning',
                'category': 'memory',
                'message': f"メモリ使用率が高めです。 {metrics['memory_percent']:.1f}%",
                'value': metrics['memory_percent'],
                'threshold': self.thresholds['memory_warning']
            })
        
        # ディスク チェック
        if metrics['disk_percent'] >= self.thresholds['disk_critical']:
            alerts.append({
                'level': 'critical',
                'category': 'disk',
                'message': f"ディスクが危機的状態です！ {metrics['disk_percent']:.1f}%",
                'value': metrics['disk_percent'],
                'threshold': self.thresholds['disk_critical']
            })
        elif metrics['disk_percent'] >= self.thresholds['disk_warning']:
            alerts.append({
                'level': 'warning',
                'category': 'disk',
                'message': f"ディスク使用率が高めです。 {metrics['disk_percent']:.1f}%",
                'value': metrics['disk_percent'],
                'threshold': self.thresholds['disk_warning']
            })
        
        # プロセス数 チェック
        if metrics['process_count'] >= self.thresholds['process_critical']:
            alerts.append({
                'level': 'warning',
                'category': 'process',
                'message': f"プロセス数が多いです。 {metrics['process_count']}個",
                'value': metrics['process_count'],
                'threshold': self.thresholds['process_critical']
            })
        
        # ManaOS チェック
        if metrics.get('manaos'):
            if metrics['manaos'].get('status') != 'healthy':
                alerts.append({
                    'level': 'critical',
                    'category': 'manaos',
                    'message': "ManaOS v3に問題が発生しています！",
                    'value': 0,
                    'threshold': 0
                })
        
        return alerts
    
    def handle_alerts(self, alerts: List[Dict]):
        """アラート処理＋音声通知"""
        for alert in alerts:
            alert_key = f"{alert['category']}_{alert['level']}"
            current_time = time.time()
            
            # クールダウンチェック
            if alert_key in self.last_alert_time:
                if current_time - self.last_alert_time[alert_key] < self.alert_cooldown:
                    continue  # まだクールダウン中
            
            # アラート記録
            self._save_alert(alert)
            
            # 音声通知
            if self.voice and alert['level'] in ['critical', 'warning']:
                self._voice_announce_alert(alert)
            
            # LINE通知（criticalのみ）
            if alert['level'] == 'critical':
                self._send_line_notification(alert)
            
            # ログ出力
            self._log(f"🚨 [{alert['level'].upper()}] {alert['category']}: {alert['message']}")
            
            # クールダウン更新
            self.last_alert_time[alert_key] = current_time
            self.alerts_history.append(alert)
    
    def _voice_announce_alert(self, alert: Dict):
        """音声でアラート通知"""
        if not self.voice:
            return
        
        try:
            # 音声メッセージ生成
            if alert['level'] == 'critical':
                message = f"緊急アラート！{alert['message']}"
            else:
                message = f"警告。{alert['message']}"
            
            # 音声合成＋再生
            audio_file = self.voice.speak(message)
            
            # 再生（バックグラウンド）
            if audio_file and os.path.exists(audio_file):
                threading.Thread(
                    target=self._play_audio,
                    args=(audio_file,),
                    daemon=True
                ).start()
            
            # DB記録
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute(
                'UPDATE alerts SET voice_announced = 1 WHERE id = (SELECT MAX(id) FROM alerts)'
            )
            conn.commit()
            conn.close()
            
        except Exception as e:
            self._log(f"⚠️ 音声通知失敗: {e}")
    
    def _play_audio(self, audio_file: str):
        """音声ファイル再生（非同期）"""
        try:
            # mpg123がインストールされている場合
            subprocess.run(['mpg123', '-q', audio_file], timeout=30)
        except IOError:
            try:
                # ffplayがある場合
                subprocess.run(['ffplay', '-nodisp', '-autoexit', audio_file], timeout=30)
            except IOError:
                pass  # 再生できなくてもOK
    
    def _send_line_notification(self, alert: Dict):
        """LINE通知送信"""
        try:
            # Trinity MCP経由でLINE通知
            message = f"🚨 {alert['level'].upper()}\n{alert['category']}: {alert['message']}"
            
            # LINE通知スクリプト実行
            subprocess.run(
                ['python3', '/root/trinity_automation/line_notifier.py', message],
                timeout=10
            )
        except Exception as e:
            self._log(f"⚠️ LINE通知失敗: {e}")
    
    def generate_voice_report(self, metrics: Dict) -> str:
        """音声レポート生成"""
        status = "正常" if not self.analyze_metrics(metrics) else "注意が必要"
        
        report = f"システム状態は{status}です。"
        report += f"CPU使用率は{metrics['cpu_percent']:.0f}パーセント、"
        report += f"メモリは{metrics['memory_percent']:.0f}パーセント、"
        report += f"ディスクは{metrics['disk_percent']:.0f}パーセントです。"
        
        if metrics.get('docker'):
            docker = metrics['docker']
            report += f"Dockerコンテナは{docker['running']}個稼働中です。"
        
        if metrics.get('manaos'):
            if metrics['manaos'].get('status') == 'healthy':
                report += "ManaOSは正常に動作しています。"
        
        return report
    
    def voice_query(self, query: str) -> Dict:
        """音声クエリ処理"""
        query_lower = query.lower()
        
        # 最新メトリクス取得
        if not self.metrics_history:
            self.collect_metrics()
        
        latest = self.metrics_history[-1]
        
        # クエリ解析＋応答生成
        if 'ステータス' in query or '状態' in query or 'status' in query_lower:
            response = self.generate_voice_report(latest)
        
        elif 'cpu' in query_lower:
            response = f"CPU使用率は{latest['cpu_percent']:.1f}パーセントです。"
        
        elif 'メモリ' in query or 'memory' in query_lower:
            response = f"メモリ使用率は{latest['memory_percent']:.1f}パーセントです。"
        
        elif 'ディスク' in query or 'disk' in query_lower:
            response = f"ディスク使用率は{latest['disk_percent']:.1f}パーセントです。"
        
        elif 'プロセス' in query or 'process' in query_lower:
            response = f"現在{latest['process_count']}個のプロセスが動作中です。"
        
        elif 'docker' in query_lower or 'コンテナ' in query:
            if latest.get('docker'):
                docker = latest['docker']
                response = f"Dockerコンテナは{docker['running']}個稼働中、合計{docker['total']}個です。"
            else:
                response = "Dockerの状態を取得できませんでした。"
        
        elif 'manaos' in query_lower:
            if latest.get('manaos'):
                status = latest['manaos'].get('status', 'unknown')
                response = f"ManaOSの状態は{status}です。"
            else:
                response = "ManaOSの状態を取得できませんでした。"
        
        else:
            response = "申し訳ありません。その質問には答えられません。"
        
        # 音声合成
        audio_file = None
        if self.voice:
            try:
                audio_file = self.voice.speak(response)
            except IOError:
                pass
        
        # クエリログ保存
        self._save_voice_query(query, response, audio_file)
        
        return {
            'query': query,
            'response': response,
            'audio_file': audio_file,
            'metrics': latest
        }
    
    def _save_alert(self, alert: Dict):
        """アラート保存"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''
            INSERT INTO alerts (timestamp, level, category, message, value, threshold)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            datetime.now().isoformat(),
            alert['level'],
            alert['category'],
            alert['message'],
            alert['value'],
            alert['threshold']
        ))
        conn.commit()
        conn.close()
    
    def _save_voice_query(self, query: str, response: str, audio_file: str):
        """音声クエリ保存"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''
            INSERT INTO voice_queries (timestamp, query, response, audio_file)
            VALUES (?, ?, ?, ?)
        ''', (datetime.now().isoformat(), query, response, audio_file))
        conn.commit()
        conn.close()
    
    def _save_metrics(self, metrics: Dict, status: str, voice_report: str):
        """メトリクス保存"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''
            INSERT INTO metrics (timestamp, cpu_percent, memory_percent, disk_percent, 
                                process_count, status, voice_report)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            metrics['timestamp'],
            metrics['cpu_percent'],
            metrics['memory_percent'],
            metrics['disk_percent'],
            metrics['process_count'],
            status,
            voice_report
        ))
        conn.commit()
        conn.close()
    
    def _log(self, message: str):
        """ログ出力"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_message = f"[{timestamp}] {message}"
        print(log_message)
        
        try:
            with open(self.log_path, 'a', encoding='utf-8') as f:
                f.write(log_message + '\n')
        except IOError:
            pass
    
    def monitor_loop(self, interval: int = 60, voice_interval: int = 3600):
        """監視ループ（メイン）"""
        self._log("🎤 音声統合監視システム起動")
        
        last_voice_report = 0
        iteration = 0
        
        try:
            while True:
                iteration += 1
                current_time = time.time()
                
                # メトリクス収集
                metrics = self.collect_metrics()
                
                # 異常検知
                alerts = self.analyze_metrics(metrics)
                
                # アラート処理
                if alerts:
                    self.handle_alerts(alerts)
                    status = 'alert'
                else:
                    status = 'normal'
                
                # 定期音声レポート
                voice_report = ""
                if current_time - last_voice_report >= voice_interval:
                    voice_report = self.generate_voice_report(metrics)
                    if self.voice:
                        try:
                            self.voice.speak(voice_report)
                            self._log(f"📢 音声レポート: {voice_report}")
                        except Exception as e:
                            self._log(f"⚠️ 音声レポート失敗: {e}")
                    last_voice_report = current_time
                
                # DB保存
                self._save_metrics(metrics, status, voice_report)
                
                # ステータス表示
                if iteration % 10 == 0:
                    self._log(
                        f"✅ CPU:{metrics['cpu_percent']:.1f}% "
                        f"MEM:{metrics['memory_percent']:.1f}% "
                        f"DISK:{metrics['disk_percent']:.1f}% "
                        f"PROC:{metrics['process_count']}"
                    )
                
                # 待機
                time.sleep(interval)
                
        except KeyboardInterrupt:
            self._log("👋 監視システム停止")
        except Exception as e:
            self._log(f"❌ エラー: {e}")
            raise
    
    def get_recent_alerts(self, limit: int = 10) -> List[Dict]:
        """最近のアラート取得"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''
            SELECT timestamp, level, category, message, value, threshold, voice_announced
            FROM alerts
            ORDER BY id DESC
            LIMIT ?
        ''', (limit,))
        
        alerts = []
        for row in c.fetchall():
            alerts.append({
                'timestamp': row[0],
                'level': row[1],
                'category': row[2],
                'message': row[3],
                'value': row[4],
                'threshold': row[5],
                'voice_announced': bool(row[6])
            })
        
        conn.close()
        return alerts
    
    def get_statistics(self, hours: int = 24) -> Dict:
        """統計情報取得"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        since = (datetime.now() - timedelta(hours=hours)).isoformat()
        
        # メトリクス統計
        c.execute('''
            SELECT 
                AVG(cpu_percent), MAX(cpu_percent),
                AVG(memory_percent), MAX(memory_percent),
                AVG(disk_percent), MAX(disk_percent),
                COUNT(*)
            FROM metrics
            WHERE timestamp > ?
        ''', (since,))
        
        row = c.fetchone()
        metrics_stats = {
            'cpu_avg': row[0] if row[0] else 0,
            'cpu_max': row[1] if row[1] else 0,
            'memory_avg': row[2] if row[2] else 0,
            'memory_max': row[3] if row[3] else 0,
            'disk_avg': row[4] if row[4] else 0,
            'disk_max': row[5] if row[5] else 0,
            'count': row[6] if row[6] else 0
        }
        
        # アラート統計
        c.execute('''
            SELECT level, COUNT(*)
            FROM alerts
            WHERE timestamp > ?
            GROUP BY level
        ''', (since,))
        
        alert_stats = {}
        for row in c.fetchall():
            alert_stats[row[0]] = row[1]
        
        conn.close()
        
        return {
            'period_hours': hours,
            'metrics': metrics_stats,
            'alerts': alert_stats,
            'total_alerts': sum(alert_stats.values())
        }


def main():
    """メイン関数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='ManaOS 音声統合監視システム')
    parser.add_argument('--interval', type=int, default=60, help='監視間隔（秒）')
    parser.add_argument('--voice-interval', type=int, default=3600, help='音声レポート間隔（秒）')
    parser.add_argument('--no-voice', action='store_true', help='音声無効化')
    parser.add_argument('--query', type=str, help='音声クエリ実行')
    parser.add_argument('--stats', action='store_true', help='統計表示')
    parser.add_argument('--alerts', action='store_true', help='最近のアラート表示')
    
    args = parser.parse_args()
    
    # エンジン初期化
    engine = VoiceMonitoringEngine(enable_voice=not args.no_voice)
    
    # クエリモード
    if args.query:
        result = engine.voice_query(args.query)
        print(f"\n📝 クエリ: {result['query']}")
        print(f"💬 応答: {result['response']}")
        if result['audio_file']:
            print(f"🔊 音声: {result['audio_file']}")
        return
    
    # 統計モード
    if args.stats:
        stats = engine.get_statistics()
        print(f"\n📊 過去{stats['period_hours']}時間の統計:")
        print(f"  CPU平均: {stats['metrics']['cpu_avg']:.1f}% (最大: {stats['metrics']['cpu_max']:.1f}%)")
        print(f"  メモリ平均: {stats['metrics']['memory_avg']:.1f}% (最大: {stats['metrics']['memory_max']:.1f}%)")
        print(f"  ディスク平均: {stats['metrics']['disk_avg']:.1f}% (最大: {stats['metrics']['disk_max']:.1f}%)")
        print(f"  総アラート: {stats['total_alerts']}件")
        for level, count in stats['alerts'].items():
            print(f"    {level}: {count}件")
        return
    
    # アラート表示モード
    if args.alerts:
        alerts = engine.get_recent_alerts(20)
        print(f"\n🚨 最近のアラート ({len(alerts)}件):")
        for alert in alerts:
            voice_mark = "🔊" if alert['voice_announced'] else "🔇"
            print(f"  {voice_mark} [{alert['level']}] {alert['category']}: {alert['message']}")
            print(f"     時刻: {alert['timestamp']}, 値: {alert['value']:.1f}, 閾値: {alert['threshold']:.1f}")
        return
    
    # 監視モード（デフォルト）
    print(f"""
╔══════════════════════════════════════════════════════╗
║  🎤 ManaOS 完全監視＋音声統合システム v1.0          ║
╚══════════════════════════════════════════════════════╝

設定:
  監視間隔:     {args.interval}秒
  音声レポート: {args.voice_interval}秒ごと
  音声機能:     {'有効' if not args.no_voice else '無効'}

起動中...
""")
    
    engine.monitor_loop(interval=args.interval, voice_interval=args.voice_interval)


if __name__ == '__main__':
    main()


