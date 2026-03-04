#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Trinity v2.0 Auto Monitor - リアルタイムシステム監視
====================================================

機能:
- リアルタイムタスク監視
- エージェント状態監視
- システムリソース監視
- WebSocket経由でダッシュボード更新
- アラート機能（異常検知）
- グラフ表示対応

Author: Luna (Trinity Implementation AI)
Created: 2025-10-18
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import asyncio
import socketio
import json
import psutil
from datetime import datetime
from typing import Dict, Any, List
from pathlib import Path
import logging
from core.db_manager import DatabaseManager

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/root/trinity_workspace/logs/auto_monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class TrinityAutoMonitor:
    """
    Trinity v2.0 自動監視システム
    
    機能:
    - タスク状態の自動監視
    - エージェント状態の自動監視
    - システムリソース監視（CPU/メモリ/ディスク）
    - WebSocket経由でリアルタイム更新
    - 異常検知＋アラート発行
    """
    
    def __init__(self, dashboard_url: str = 'http://localhost:5100'):
        self.dashboard_url = dashboard_url
        self.db = DatabaseManager()
        self.sio = socketio.AsyncClient()
        self.running = False
        
        # 前回の状態を保存（変更検知用）
        self.previous_tasks_state = {}
        self.previous_agents_state = {}
        
        # アラート閾値
        self.alert_thresholds = {
            'cpu_percent': 90.0,
            'memory_percent': 90.0,
            'disk_percent': 95.0,
            'task_stuck_hours': 24  # 24時間以上in_progressのタスクを検知
        }
        
        # 統計データ（グラフ用）
        self.metrics_history = {
            'timestamps': [],
            'cpu_usage': [],
            'memory_usage': [],
            'tasks_count': {
                'todo': [],
                'in_progress': [],
                'review': [],
                'done': []
            }
        }
        
        # WebSocketイベントハンドラ登録
        self.setup_socketio_handlers()
    
    def setup_socketio_handlers(self):
        """WebSocketイベントハンドラ設定"""
        
        @self.sio.on('connect')
        async def on_connect():
            logger.info(f"✅ Connected to Dashboard: {self.dashboard_url}")
            print(f"🔗 Connected to Trinity Dashboard")
        
        @self.sio.on('disconnect')
        async def on_disconnect():
            logger.warning("⚠️ Disconnected from Dashboard")
            print("❌ Disconnected from Dashboard")
        
        @self.sio.on('connected')
        async def on_server_hello(data):
            logger.info(f"Server says: {data.get('message')}")
    
    async def connect(self):
        """ダッシュボードに接続"""
        try:
            await self.sio.connect(self.dashboard_url)
            logger.info("WebSocket connection established")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to dashboard: {e}")
            return False
    
    async def disconnect(self):
        """接続解除"""
        if self.sio.connected:
            await self.sio.disconnect()
            logger.info("WebSocket disconnected")
    
    async def start_monitoring(self):
        """監視開始"""
        self.running = True
        
        print("=" * 60)
        print("🔍 Trinity Auto Monitor v2.0 Starting...")
        print("=" * 60)
        print(f"📊 Dashboard: {self.dashboard_url}")
        print(f"⏱️  Update Interval: 5 seconds")
        print(f"🚨 Alert Mode: Enabled")
        print("=" * 60)
        print()
        
        # ダッシュボードに接続
        connected = await self.connect()
        if not connected:
            logger.error("Failed to connect. Running in offline mode.")
        
        try:
            while self.running:
                # 1. タスク監視
                await self.monitor_tasks()
                
                # 2. エージェント監視
                await self.monitor_agents()
                
                # 3. システムリソース監視
                await self.monitor_system_resources()
                
                # 4. 統計データ更新（グラフ用）
                await self.update_metrics_history()
                
                # 5. アラートチェック
                await self.check_alerts()
                
                # 6. コンソール表示
                self.display_status()
                
                # 7. 5秒待機
                await asyncio.sleep(5)
        
        except KeyboardInterrupt:
            logger.info("Monitoring stopped by user")
            print("\n👋 Monitoring stopped.")
        
        finally:
            await self.disconnect()
    
    async def monitor_tasks(self):
        """タスク監視"""
        try:
            tasks = self.db.get_tasks()
            
            # 状態変更を検知
            for task in tasks:
                task_id = task['id']
                current_status = task['status']
                
                if task_id in self.previous_tasks_state:
                    previous_status = self.previous_tasks_state[task_id]
                    
                    if previous_status != current_status:
                        # 状態変更を検知
                        logger.info(f"📋 Task {task_id}: {previous_status} → {current_status}")
                        
                        # WebSocketで通知
                        if self.sio.connected:
                            await self.sio.emit('monitor_alert', {
                                'type': 'task_status_changed',
                                'task_id': task_id,
                                'old_status': previous_status,
                                'new_status': current_status,
                                'timestamp': datetime.now().isoformat()
                            })
                
                # 現在の状態を保存
                self.previous_tasks_state[task_id] = current_status
        
        except Exception as e:
            logger.error(f"Task monitoring error: {e}")
    
    async def monitor_agents(self):
        """エージェント監視"""
        try:
            agents = self.db.get_all_agent_status()
            
            for agent in agents:
                agent_name = agent['agent_name']
                current_status = agent['status']
                
                if agent_name in self.previous_agents_state:
                    previous_status = self.previous_agents_state[agent_name]
                    
                    if previous_status != current_status:
                        # 状態変更を検知
                        logger.info(f"🤖 Agent {agent_name}: {previous_status} → {current_status}")
                        
                        # WebSocketで通知
                        if self.sio.connected:
                            await self.sio.emit('monitor_alert', {
                                'type': 'agent_status_changed',
                                'agent': agent_name,
                                'old_status': previous_status,
                                'new_status': current_status,
                                'timestamp': datetime.now().isoformat()
                            })
                
                # 現在の状態を保存
                self.previous_agents_state[agent_name] = current_status
        
        except Exception as e:
            logger.error(f"Agent monitoring error: {e}")
    
    async def monitor_system_resources(self):
        """システムリソース監視"""
        try:
            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # メモリ使用率
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # ディスク使用率
            disk = psutil.disk_usage('/root')
            disk_percent = disk.percent
            
            # WebSocketで送信
            if self.sio.connected:
                await self.sio.emit('system_metrics', {
                    'cpu_percent': cpu_percent,
                    'memory_percent': memory_percent,
                    'memory_used_gb': memory.used / (1024**3),
                    'memory_total_gb': memory.total / (1024**3),
                    'disk_percent': disk_percent,
                    'disk_used_gb': disk.used / (1024**3),
                    'disk_total_gb': disk.total / (1024**3),
                    'timestamp': datetime.now().isoformat()
                })
        
        except Exception as e:
            logger.error(f"System resource monitoring error: {e}")
    
    async def update_metrics_history(self):
        """統計データ更新（グラフ表示用）"""
        try:
            # タイムスタンプ
            timestamp = datetime.now().isoformat()
            self.metrics_history['timestamps'].append(timestamp)
            
            # CPU/メモリ
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory_percent = psutil.virtual_memory().percent
            
            self.metrics_history['cpu_usage'].append(cpu_percent)
            self.metrics_history['memory_usage'].append(memory_percent)
            
            # タスク数
            tasks = self.db.get_tasks()
            for status in ['todo', 'in_progress', 'review', 'done']:
                count = len([t for t in tasks if t['status'] == status])
                self.metrics_history['tasks_count'][status].append(count)
            
            # 直近100件のみ保持（メモリ節約）
            if len(self.metrics_history['timestamps']) > 100:
                for key in ['timestamps', 'cpu_usage', 'memory_usage']:
                    self.metrics_history[key] = self.metrics_history[key][-100:]
                
                for status in self.metrics_history['tasks_count']:
                    self.metrics_history['tasks_count'][status] = \
                        self.metrics_history['tasks_count'][status][-100:]
            
            # WebSocketで送信
            if self.sio.connected:
                await self.sio.emit('metrics_history', self.metrics_history)
        
        except Exception as e:
            logger.error(f"Metrics history update error: {e}")
    
    async def check_alerts(self):
        """アラートチェック"""
        alerts = []
        
        try:
            # 1. CPU過負荷チェック
            cpu_percent = psutil.cpu_percent(interval=0.1)
            if cpu_percent > self.alert_thresholds['cpu_percent']:
                alerts.append({
                    'level': 'warning',
                    'type': 'cpu_overload',
                    'message': f"CPU使用率が高い: {cpu_percent:.1f}%",
                    'value': cpu_percent
                })
            
            # 2. メモリ過負荷チェック
            memory_percent = psutil.virtual_memory().percent
            if memory_percent > self.alert_thresholds['memory_percent']:
                alerts.append({
                    'level': 'warning',
                    'type': 'memory_overload',
                    'message': f"メモリ使用率が高い: {memory_percent:.1f}%",
                    'value': memory_percent
                })
            
            # 3. ディスク容量チェック
            disk_percent = psutil.disk_usage('/root').percent
            if disk_percent > self.alert_thresholds['disk_percent']:
                alerts.append({
                    'level': 'critical',
                    'type': 'disk_full',
                    'message': f"ディスク使用率が危険: {disk_percent:.1f}%",
                    'value': disk_percent
                })
            
            # 4. スタックタスクチェック（24時間以上in_progress）
            tasks = self.db.get_tasks(status='in_progress')
            for task in tasks:
                updated_at = datetime.fromisoformat(task.get('updated_at', task['created_at']))
                hours_stuck = (datetime.now() - updated_at).total_seconds() / 3600
                
                if hours_stuck > self.alert_thresholds['task_stuck_hours']:
                    alerts.append({
                        'level': 'warning',
                        'type': 'task_stuck',
                        'message': f"タスク {task['id']} が {hours_stuck:.1f}時間停滞中",
                        'task_id': task['id'],
                        'hours': hours_stuck
                    })
            
            # アラート発行
            for alert in alerts:
                logger.warning(f"🚨 ALERT: {alert['message']}")
                
                if self.sio.connected:
                    await self.sio.emit('alert', {
                        **alert,
                        'timestamp': datetime.now().isoformat()
                    })
        
        except Exception as e:
            logger.error(f"Alert check error: {e}")
    
    def display_status(self):
        """コンソールにステータス表示"""
        try:
            # システムリソース
            cpu = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/root')
            
            # タスク統計
            tasks = self.db.get_tasks()
            task_stats = {
                'todo': len([t for t in tasks if t['status'] == 'todo']),
                'in_progress': len([t for t in tasks if t['status'] == 'in_progress']),
                'review': len([t for t in tasks if t['status'] == 'review']),
                'done': len([t for t in tasks if t['status'] == 'done'])
            }
            
            # エージェント統計
            agents = self.db.get_all_agent_status()
            agents_online = len([a for a in agents if a['status'] == 'online'])
            
            # クリア＋表示
            print("\033[H\033[J")  # ターミナルクリア
            print("=" * 60)
            print(f"🔍 Trinity Auto Monitor v2.0 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print("=" * 60)
            print()
            
            print("📊 System Resources:")
            print(f"  CPU:    {cpu:5.1f}% {'🔥' if cpu > 80 else '✅'}")
            print(f"  Memory: {memory.percent:5.1f}% ({memory.used/(1024**3):.1f}GB / {memory.total/(1024**3):.1f}GB) {'🔥' if memory.percent > 80 else '✅'}")
            print(f"  Disk:   {disk.percent:5.1f}% ({disk.used/(1024**3):.1f}GB / {disk.total/(1024**3):.1f}GB) {'🔥' if disk.percent > 90 else '✅'}")
            print()
            
            print("📋 Tasks:")
            print(f"  TODO:        {task_stats['todo']:3d}")
            print(f"  In Progress: {task_stats['in_progress']:3d}")
            print(f"  Review:      {task_stats['review']:3d}")
            print(f"  Done:        {task_stats['done']:3d}")
            print(f"  Total:       {len(tasks):3d}")
            print()
            
            print("🤖 Agents:")
            print(f"  Online:      {agents_online}/{len(agents)}")
            for agent in agents:
                status_icon = '✅' if agent['status'] == 'online' else '⚪'
                print(f"  {status_icon} {agent['agent_name']:8s} - {agent['status']:10s} " + 
                      (f"(Task: {agent['current_task_id']})" if agent.get('current_task_id') else "(Idle)"))
            print()
            
            print("🔗 WebSocket:")
            print(f"  Status: {'🟢 Connected' if self.sio.connected else '🔴 Disconnected'}")
            print()
            
            print("Press Ctrl+C to stop monitoring")
            print("=" * 60)
        
        except Exception as e:
            logger.error(f"Display status error: {e}")
    
    def stop(self):
        """監視停止"""
        self.running = False
        logger.info("Monitoring stopped")


async def main():
    """メイン実行"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Trinity Auto Monitor v2.0')
    parser.add_argument(
        '--dashboard',
        type=str,
        default='http://localhost:5100',
        help='Dashboard URL (default: http://localhost:5100)'
    )
    parser.add_argument(
        '--interval',
        type=int,
        default=5,
        help='Update interval in seconds (default: 5)'
    )
    
    args = parser.parse_args()
    
    # モニター起動
    monitor = TrinityAutoMonitor(dashboard_url=args.dashboard)
    
    try:
        await monitor.start_monitoring()
    except KeyboardInterrupt:
        monitor.stop()
        print("\n👋 Goodbye!")


if __name__ == '__main__':
    asyncio.run(main())


