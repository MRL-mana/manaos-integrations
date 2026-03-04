#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🌟 究極の監視ダッシュボード - 全てのシステムを統合監視する究極のダッシュボード
全ての究極システムの状態をリアルタイムで監視・表示する
"""

import asyncio
import json
import logging
import sqlite3
import time
import random
import math
import numpy as np
import threading
import queue
import os
import sys
import psutil
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple

# 究極の監視設定
ULTIMATE_MONITORING_CONFIG = {
    "monitoring_interval": 5,  # 秒
    "dashboard_refresh_rate": 2,  # 秒
    "system_health_threshold": 0.95,
    "performance_alert_threshold": 0.8,
    "ultimate_level_threshold": 100000000
}

class UltimateMonitoringDashboard:
    """究極の監視ダッシュボード"""
    
    def __init__(self):
        self.logger = self._setup_logging()
        self.database = UltimateMonitoringDatabase()
        self.system_monitor = SystemMonitor()
        self.performance_analyzer = PerformanceAnalyzer()
        self.alert_manager = AlertManager()
        self.visualization_engine = VisualizationEngine()
        
        self.running = False
        self.logger.info("🌟 究極の監視ダッシュボード初期化完了")
        
    def _setup_logging(self) -> logging.Logger:
        """究極の監視ダッシュボードログ設定"""
        os.makedirs("/var/log/ultimate-monitoring", exist_ok=True)
        
        logger = logging.getLogger("ultimate_monitoring")
        logger.setLevel(logging.INFO)
        
        # 既存ハンドラーをクリア
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
            
        # ファイルハンドラー
        file_handler = logging.FileHandler("/var/log/ultimate-monitoring/ultimate_monitoring.log")
        file_handler.setLevel(logging.INFO)
        
        # フォーマッター
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        return logger

class SystemMonitor:
    """システム監視器"""
    
    def __init__(self):
        self.monitoring_interval = ULTIMATE_MONITORING_CONFIG["monitoring_interval"]
        
    def get_system_metrics(self) -> Dict:
        """システムメトリクスの取得"""
        # CPU使用率
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # メモリ使用率
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        memory_available_gb = memory.available / (1024**3)
        
        # ディスク使用率
        disk = psutil.disk_usage('/')
        disk_percent = disk.percent
        disk_free_gb = disk.free / (1024**3)
        
        # ネットワーク統計
        network = psutil.net_io_counters()
        network_bytes_sent = network.bytes_sent
        network_bytes_recv = network.bytes_recv
        
        # プロセス統計
        processes = len(psutil.pids())
        
        return {
            "timestamp": datetime.now().isoformat(),
            "cpu_percent": cpu_percent,
            "memory_percent": memory_percent,
            "memory_available_gb": memory_available_gb,
            "disk_percent": disk_percent,
            "disk_free_gb": disk_free_gb,
            "network_bytes_sent": network_bytes_sent,
            "network_bytes_recv": network_bytes_recv,
            "processes": processes
        }
    
    def get_python_processes(self) -> List[Dict]:
        """Pythonプロセスの取得"""
        python_processes = []
        
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'create_time']):
            try:
                if 'python' in proc.info['name'].lower():
                    python_processes.append({
                        "pid": proc.info['pid'],
                        "name": proc.info['name'],
                        "cpu_percent": proc.info['cpu_percent'],
                        "memory_percent": proc.info['memory_percent'],
                        "create_time": datetime.fromtimestamp(proc.info['create_time']).isoformat()
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        return python_processes

class PerformanceAnalyzer:
    """性能分析器"""
    
    def __init__(self):
        self.performance_history = []
        self.analysis_window = 100
        
    def analyze_performance(self, metrics: Dict) -> Dict:
        """性能分析の実行"""
        # 性能履歴に追加
        self.performance_history.append(metrics)
        
        # 履歴が長すぎる場合は古いものを削除
        if len(self.performance_history) > self.analysis_window:
            self.performance_history.pop(0)
        
        # 性能指標の計算
        if len(self.performance_history) > 1:
            cpu_trend = self._calculate_trend([m['cpu_percent'] for m in self.performance_history])
            memory_trend = self._calculate_trend([m['memory_percent'] for m in self.performance_history])
            disk_trend = self._calculate_trend([m['disk_percent'] for m in self.performance_history])
        else:
            cpu_trend = memory_trend = disk_trend = 0.0
        
        # 性能評価
        performance_score = self._calculate_performance_score(metrics)
        health_score = self._calculate_health_score(metrics)
        
        return {
            "performance_score": performance_score,
            "health_score": health_score,
            "cpu_trend": cpu_trend,
            "memory_trend": memory_trend,
            "disk_trend": disk_trend,
            "analysis_timestamp": datetime.now().isoformat()
        }
    
    def _calculate_trend(self, values: List[float]) -> float:
        """トレンド計算"""
        if len(values) < 2:
            return 0.0
        
        # 線形回帰によるトレンド計算
        x = np.arange(len(values))
        y = np.array(values)
        
        if len(x) > 1:
            slope = np.polyfit(x, y, 1)[0]
            return slope
        else:
            return 0.0
    
    def _calculate_performance_score(self, metrics: Dict) -> float:
        """性能スコア計算"""
        # CPU使用率（低いほど良い）
        cpu_score = max(0, 100 - metrics['cpu_percent']) / 100
        
        # メモリ使用率（低いほど良い）
        memory_score = max(0, 100 - metrics['memory_percent']) / 100
        
        # ディスク使用率（低いほど良い）
        disk_score = max(0, 100 - metrics['disk_percent']) / 100
        
        # 総合スコア
        total_score = (cpu_score + memory_score + disk_score) / 3
        
        return total_score
    
    def _calculate_health_score(self, metrics: Dict) -> float:
        """健康スコア計算"""
        # 基本的な健康指標
        health_indicators = []
        
        # CPU使用率が80%以下
        if metrics['cpu_percent'] <= 80:
            health_indicators.append(1.0)
        else:
            health_indicators.append(0.0)
        
        # メモリ使用率が90%以下
        if metrics['memory_percent'] <= 90:
            health_indicators.append(1.0)
        else:
            health_indicators.append(0.0)
        
        # ディスク使用率が95%以下
        if metrics['disk_percent'] <= 95:
            health_indicators.append(1.0)
        else:
            health_indicators.append(0.0)
        
        # 利用可能メモリが1GB以上
        if metrics['memory_available_gb'] >= 1.0:
            health_indicators.append(1.0)
        else:
            health_indicators.append(0.0)
        
        # 総合健康スコア
        health_score = sum(health_indicators) / len(health_indicators)
        
        return health_score

class AlertManager:
    """アラート管理システム"""
    
    def __init__(self):
        self.alerts = []
        self.alert_thresholds = {
            "cpu_high": 80.0,
            "memory_high": 90.0,
            "disk_high": 95.0,
            "performance_low": 0.6,
            "health_low": 0.7
        }
    
    def check_alerts(self, metrics: Dict, performance: Dict) -> List[Dict]:
        """アラートチェック"""
        alerts = []
        
        # CPU使用率アラート
        if metrics['cpu_percent'] > self.alert_thresholds['cpu_high']:
            alerts.append({
                "type": "warning",
                "message": f"CPU使用率が高いです: {metrics['cpu_percent']:.1f}%",
                "timestamp": datetime.now().isoformat(),
                "severity": "high"
            })
        
        # メモリ使用率アラート
        if metrics['memory_percent'] > self.alert_thresholds['memory_high']:
            alerts.append({
                "type": "warning",
                "message": f"メモリ使用率が高いです: {metrics['memory_percent']:.1f}%",
                "timestamp": datetime.now().isoformat(),
                "severity": "high"
            })
        
        # ディスク使用率アラート
        if metrics['disk_percent'] > self.alert_thresholds['disk_high']:
            alerts.append({
                "type": "warning",
                "message": f"ディスク使用率が高いです: {metrics['disk_percent']:.1f}%",
                "timestamp": datetime.now().isoformat(),
                "severity": "critical"
            })
        
        # 性能スコアアラート
        if performance['performance_score'] < self.alert_thresholds['performance_low']:
            alerts.append({
                "type": "warning",
                "message": f"性能スコアが低いです: {performance['performance_score']:.2f}",
                "timestamp": datetime.now().isoformat(),
                "severity": "medium"
            })
        
        # 健康スコアアラート
        if performance['health_score'] < self.alert_thresholds['health_low']:
            alerts.append({
                "type": "warning",
                "message": f"健康スコアが低いです: {performance['health_score']:.2f}",
                "timestamp": datetime.now().isoformat(),
                "severity": "high"
            })
        
        # アラート履歴に追加
        self.alerts.extend(alerts)
        
        # 古いアラートを削除（100件まで保持）
        if len(self.alerts) > 100:
            self.alerts = self.alerts[-100:]
        
        return alerts

class VisualizationEngine:
    """可視化エンジン"""
    
    def __init__(self):
        self.dashboard_data = {}
        self.update_interval = ULTIMATE_MONITORING_CONFIG["dashboard_refresh_rate"]
    
    def update_dashboard(self, metrics: Dict, performance: Dict, alerts: List[Dict], processes: List[Dict]) -> Dict:
        """ダッシュボードデータの更新"""
        self.dashboard_data = {
            "timestamp": datetime.now().isoformat(),
            "metrics": metrics,
            "performance": performance,
            "alerts": alerts,
            "processes": processes,
            "summary": self._generate_summary(metrics, performance, alerts)
        }
        
        return self.dashboard_data
    
    def _generate_summary(self, metrics: Dict, performance: Dict, alerts: List[Dict]) -> Dict:
        """サマリー生成"""
        # アクティブなアラート数
        active_alerts = len(alerts)
        
        # システム状態
        if performance['health_score'] >= 0.9:
            system_status = "excellent"
        elif performance['health_score'] >= 0.7:
            system_status = "good"
        elif performance['health_score'] >= 0.5:
            system_status = "fair"
        else:
            system_status = "poor"
        
        # 性能評価
        if performance['performance_score'] >= 0.8:
            performance_status = "excellent"
        elif performance['performance_score'] >= 0.6:
            performance_status = "good"
        elif performance['performance_score'] >= 0.4:
            performance_status = "fair"
        else:
            performance_status = "poor"
        
        return {
            "active_alerts": active_alerts,
            "system_status": system_status,
            "performance_status": performance_status,
            "total_processes": len(metrics.get('processes', [])),
            "python_processes": len(processes)
        }

class UltimateMonitoringDatabase:
    """究極の監視データベース"""
    
    def __init__(self):
        self.db_path = "ultimate_monitoring_dashboard.db"
        self._init_database()
    
    def _init_database(self):
        """データベース初期化"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # システムメトリクステーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS system_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                cpu_percent REAL,
                memory_percent REAL,
                memory_available_gb REAL,
                disk_percent REAL,
                disk_free_gb REAL,
                network_bytes_sent INTEGER,
                network_bytes_recv INTEGER,
                processes INTEGER,
                created_at TEXT
            )
        """)
        
        # 性能分析テーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS performance_analysis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                performance_score REAL,
                health_score REAL,
                cpu_trend REAL,
                memory_trend REAL,
                disk_trend REAL,
                created_at TEXT
            )
        """)
        
        # アラートテーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                alert_type TEXT,
                message TEXT,
                severity TEXT,
                created_at TEXT
            )
        """)
        
        # プロセス情報テーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS process_info (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                pid INTEGER,
                name TEXT,
                cpu_percent REAL,
                memory_percent REAL,
                create_time TEXT,
                created_at TEXT
            )
        """)
        
        conn.commit()
        conn.close()
    
    def save_system_metrics(self, metrics: Dict):
        """システムメトリクスの保存"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO system_metrics (
                timestamp, cpu_percent, memory_percent, memory_available_gb,
                disk_percent, disk_free_gb, network_bytes_sent,
                network_bytes_recv, processes, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            metrics.get("timestamp", datetime.now().isoformat()),
            metrics.get("cpu_percent", 0.0),
            metrics.get("memory_percent", 0.0),
            metrics.get("memory_available_gb", 0.0),
            metrics.get("disk_percent", 0.0),
            metrics.get("disk_free_gb", 0.0),
            metrics.get("network_bytes_sent", 0),
            metrics.get("network_bytes_recv", 0),
            metrics.get("processes", 0),
            datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
    
    def save_performance_analysis(self, performance: Dict):
        """性能分析の保存"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO performance_analysis (
                timestamp, performance_score, health_score,
                cpu_trend, memory_trend, disk_trend, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            performance.get("analysis_timestamp", datetime.now().isoformat()),
            performance.get("performance_score", 0.0),
            performance.get("health_score", 0.0),
            performance.get("cpu_trend", 0.0),
            performance.get("memory_trend", 0.0),
            performance.get("disk_trend", 0.0),
            datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
    
    def save_alerts(self, alerts: List[Dict]):
        """アラートの保存"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for alert in alerts:
            cursor.execute("""
                INSERT INTO alerts (
                    timestamp, alert_type, message, severity, created_at
                ) VALUES (?, ?, ?, ?, ?)
            """, (
                alert.get("timestamp", datetime.now().isoformat()),
                alert.get("type", ""),
                alert.get("message", ""),
                alert.get("severity", ""),
                datetime.now().isoformat()
            ))
        
        conn.commit()
        conn.close()

class UltimateMonitoringDashboardMain:
    """究極の監視ダッシュボードメイン"""
    
    def __init__(self):
        self.dashboard = UltimateMonitoringDashboard()
        self.running = False
        
    async def start_ultimate_monitoring_dashboard(self):
        """究極の監視ダッシュボードの開始"""
        self.running = True
        self.dashboard.logger.info("🌟 究極の監視ダッシュボード開始")
        
        # 並行タスクの開始
        tasks = [
            self._monitoring_loop(),
            self._dashboard_display_loop()
        ]
        
        await asyncio.gather(*tasks)
    
    async def _monitoring_loop(self):
        """監視ループ"""
        while self.running:
            try:
                # システムメトリクスの取得
                metrics = self.dashboard.system_monitor.get_system_metrics()
                
                # 性能分析の実行
                performance = self.dashboard.performance_analyzer.analyze_performance(metrics)
                
                # アラートチェック
                alerts = self.dashboard.alert_manager.check_alerts(metrics, performance)
                
                # Pythonプロセスの取得
                processes = self.dashboard.system_monitor.get_python_processes()
                
                # データの保存
                self.dashboard.database.save_system_metrics(metrics)
                self.dashboard.database.save_performance_analysis(performance)
                self.dashboard.database.save_alerts(alerts)
                
                # ダッシュボードデータの更新
                dashboard_data = self.dashboard.visualization_engine.update_dashboard(
                    metrics, performance, alerts, processes
                )
                
                await asyncio.sleep(self.dashboard.system_monitor.monitoring_interval)
                
            except Exception as e:
                self.dashboard.logger.error(f"監視ループエラー: {e}")
                await asyncio.sleep(5)
    
    async def _dashboard_display_loop(self):
        """ダッシュボード表示ループ"""
        while self.running:
            try:
                # ダッシュボードの表示
                self._display_dashboard()
                
                await asyncio.sleep(ULTIMATE_MONITORING_CONFIG["dashboard_refresh_rate"])
                
            except Exception as e:
                self.dashboard.logger.error(f"ダッシュボード表示エラー: {e}")
                await asyncio.sleep(5)
    
    def _display_dashboard(self):
        """ダッシュボードの表示"""
        dashboard_data = self.dashboard.visualization_engine.dashboard_data
        
        if not dashboard_data:
            return
        
        # 画面クリア
        os.system('clear')
        
        # ダッシュボードヘッダー
        print("=" * 100)
        print("🌟 究極の監視ダッシュボード - 統合システム監視")
        print("=" * 100)
        print(f"🕐 更新時刻: {dashboard_data['timestamp']}")
        print("=" * 100)
        
        # システムサマリー
        summary = dashboard_data['summary']
        print("🚀 システムサマリー:")
        print("-" * 50)
        print(f"  システム状態: {summary['system_status'].upper()}")
        print(f"  性能状態: {summary['performance_status'].upper()}")
        print(f"  アクティブアラート: {summary['active_alerts']}")
        print(f"  総プロセス数: {summary['total_processes']}")
        print(f"  Pythonプロセス数: {summary['python_processes']}")
        print()
        
        # システムメトリクス
        metrics = dashboard_data['metrics']
        print("📊 システムメトリクス:")
        print("-" * 50)
        print(f"  CPU使用率: {metrics['cpu_percent']:.1f}%")
        print(f"  メモリ使用率: {metrics['memory_percent']:.1f}%")
        print(f"  利用可能メモリ: {metrics['memory_available_gb']:.1f}GB")
        print(f"  ディスク使用率: {metrics['disk_percent']:.1f}%")
        print(f"  空きディスク容量: {metrics['disk_free_gb']:.1f}GB")
        print(f"  ネットワーク送信: {metrics['network_bytes_sent'] / (1024**2):.1f}MB")
        print(f"  ネットワーク受信: {metrics['network_bytes_recv'] / (1024**2):.1f}MB")
        print()
        
        # 性能分析
        performance = dashboard_data['performance']
        print("🔬 性能分析:")
        print("-" * 50)
        print(f"  性能スコア: {performance['performance_score']:.3f}")
        print(f"  健康スコア: {performance['health_score']:.3f}")
        print(f"  CPUトレンド: {performance['cpu_trend']:.3f}")
        print(f"  メモリトレンド: {performance['memory_trend']:.3f}")
        print(f"  ディスクトレンド: {performance['disk_trend']:.3f}")
        print()
        
        # アクティブアラート
        alerts = dashboard_data['alerts']
        if alerts:
            print("⚠️  アクティブアラート:")
            print("-" * 50)
            for alert in alerts[-5:]:  # 最新5件のみ表示
                severity_icon = "🔴" if alert['severity'] == 'critical' else "🟡" if alert['severity'] == 'high' else "🟢"
                print(f"  {severity_icon} {alert['message']}")
            print()
        
        # Pythonプロセス
        processes = dashboard_data['processes']
        if processes:
            print("🐍 Pythonプロセス:")
            print("-" * 50)
            for proc in processes[:10]:  # 上位10件のみ表示
                print(f"  PID {proc['pid']}: {proc['name']} (CPU: {proc['cpu_percent']:.1f}%, Mem: {proc['memory_percent']:.1f}%)")
            print()
        
        print("=" * 100)
        print("Ctrl+C でダッシュボードを停止")
        print("=" * 100)

async def main():
    """メイン関数"""
    print("🌟 究極の監視ダッシュボード起動中...")
    
    dashboard_main = UltimateMonitoringDashboardMain()
    
    try:
        await dashboard_main.start_ultimate_monitoring_dashboard()
    except KeyboardInterrupt:
        print("\n🌟 究極の監視ダッシュボード停止中...")
        dashboard_main.running = False
    except Exception as e:
        print(f"🌟 究極の監視ダッシュボードエラー: {e}")

if __name__ == "__main__":
    asyncio.run(main()) 