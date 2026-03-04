#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
究極システムマネージャー
全てのシステムを一括管理する究極のマネージャー
"""

import asyncio
import json
import logging
import random
import sqlite3
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import numpy as np
from flask import Flask, jsonify, request, render_template_string
import requests
from concurrent.futures import ThreadPoolExecutor
import queue
import hashlib
import hmac
import base64
import subprocess
import psutil
import os
import signal

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ultimate_system_manager.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class SystemProcessManager:
    """システムプロセス管理"""
    
    def __init__(self):
        self.managed_processes = {
            'ultimate_integration_master': {
                'script': 'ultimate_integration_master.py',
                'port': 5005,
                'pid_file': '.ultimate_integration_master.pid',
                'log_file': 'ultimate_integration_master.log',
                'status': 'unknown'
            },
            'dimensional_transcendence': {
                'script': 'dimensional_transcendence_system.py',
                'port': 5006,
                'pid_file': '.dimensional_transcendence.pid',
                'log_file': 'dimensional_transcendence.log',
                'status': 'unknown'
            },
            'advanced_quantum_optimizer': {
                'script': 'advanced_quantum_optimizer.py',
                'port': 5007,
                'pid_file': '.advanced_quantum_optimizer.pid',
                'log_file': 'advanced_quantum_optimizer.log',
                'status': 'unknown'
            },
            'ultimate_quantum_transcendence': {
                'script': 'ultimate_quantum_transcendence_system.py',
                'port': 5008,
                'pid_file': '.ultimate_quantum_transcendence.pid',
                'log_file': 'ultimate_quantum_transcendence.log',
                'status': 'unknown'
            },
            'system_optimization_integrator': {
                'script': 'system_optimization_integrator.py',
                'port': 5009,
                'pid_file': '.system_optimization_integrator.pid',
                'log_file': 'system_optimization.log',
                'status': 'unknown'
            },
            'dimensional_integration_master': {
                'script': 'dimensional_integration_master_system.py',
                'port': 5010,
                'pid_file': '.dimensional_integration_master.pid',
                'log_file': 'dimensional_integration_master.log',
                'status': 'unknown'
            },
            'ultimate_unified_dashboard': {
                'script': 'ultimate_unified_dashboard.py',
                'port': 5011,
                'pid_file': '.ultimate_unified_dashboard.pid',
                'log_file': 'ultimate_unified_dashboard.log',
                'status': 'unknown'
            }
        }
        self.process_pids = {}
        self.management_history = []
        
    def start_system(self, system_name: str) -> Dict[str, Any]:
        """システムの開始"""
        if system_name not in self.managed_processes:
            return {'error': f'システム {system_name} が見つかりません'}
        
        config = self.managed_processes[system_name]
        
        try:
            # 既存プロセスの確認
            if self.is_system_running(system_name):
                return {'status': 'already_running', 'message': f'{system_name} は既に実行中です'}
            
            # プロセスの開始
            cmd = f"python3 {config['script']} > {config['log_file']} 2>&1 & echo $!"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            if result.returncode == 0:
                pid = int(result.stdout.strip())
                self.process_pids[system_name] = pid
                
                # PIDファイルの作成
                with open(config['pid_file'], 'w') as f:
                    f.write(str(pid))
                
                # 状態の更新
                config['status'] = 'starting'
                
                # 履歴の記録
                self.management_history.append({
                    'timestamp': time.time(),
                    'action': 'start',
                    'system': system_name,
                    'pid': pid,
                    'status': 'success'
                })
                
                logger.info(f"システム {system_name} を開始しました (PID: {pid})")
                return {'status': 'started', 'pid': pid}
            else:
                return {'error': f'システム {system_name} の開始に失敗しました'}
                
        except Exception as e:
            logger.error(f"システム {system_name} の開始でエラー: {e}")
            return {'error': str(e)}
    
    def stop_system(self, system_name: str) -> Dict[str, Any]:
        """システムの停止"""
        if system_name not in self.managed_processes:
            return {'error': f'システム {system_name} が見つかりません'}
        
        config = self.managed_processes[system_name]
        
        try:
            # PIDファイルからPIDを取得
            pid = None
            if os.path.exists(config['pid_file']):
                with open(config['pid_file'], 'r') as f:
                    pid = int(f.read().strip())
            
            if pid and self.is_process_running(pid):
                # プロセスの停止
                os.kill(pid, signal.SIGTERM)
                time.sleep(2)
                
                # 強制終了が必要な場合
                if self.is_process_running(pid):
                    os.kill(pid, signal.SIGKILL)
                
                # PIDファイルの削除
                if os.path.exists(config['pid_file']):
                    os.remove(config['pid_file'])
                
                # 状態の更新
                config['status'] = 'stopped'
                if system_name in self.process_pids:
                    del self.process_pids[system_name]
                
                # 履歴の記録
                self.management_history.append({
                    'timestamp': time.time(),
                    'action': 'stop',
                    'system': system_name,
                    'pid': pid,
                    'status': 'success'
                })
                
                logger.info(f"システム {system_name} を停止しました (PID: {pid})")
                return {'status': 'stopped', 'pid': pid}
            else:
                return {'error': f'システム {system_name} は実行中ではありません'}
                
        except Exception as e:
            logger.error(f"システム {system_name} の停止でエラー: {e}")
            return {'error': str(e)}
    
    def restart_system(self, system_name: str) -> Dict[str, Any]:
        """システムの再起動"""
        stop_result = self.stop_system(system_name)
        if 'error' in stop_result:
            return stop_result
        
        time.sleep(2)  # 停止待機
        return self.start_system(system_name)
    
    def is_process_running(self, pid: int) -> bool:
        """プロセスが実行中かチェック"""
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False
    
    def is_system_running(self, system_name: str) -> bool:
        """システムが実行中かチェック"""
        if system_name not in self.managed_processes:
            return False
        
        config = self.managed_processes[system_name]
        
        # PIDファイルの確認
        if os.path.exists(config['pid_file']):
            try:
                with open(config['pid_file'], 'r') as f:
                    pid = int(f.read().strip())
                return self.is_process_running(pid)
            except:
                pass
        
        # ポートの確認
        try:
            response = requests.get(f'http://localhost:{config["port"]}/health', timeout=2)
            return response.status_code == 200
        except:
            pass
        
        return False
    
    def get_system_status(self, system_name: str) -> Dict[str, Any]:
        """システム状態の取得"""
        if system_name not in self.managed_processes:
            return {'error': f'システム {system_name} が見つかりません'}
        
        config = self.managed_processes[system_name]
        is_running = self.is_system_running(system_name)
        
        status_info = {
            'name': system_name,
            'running': is_running,
            'port': config['port'],
            'script': config['script'],
            'log_file': config['log_file']
        }
        
        if is_running:
            # 実行中の詳細情報
            try:
                response = requests.get(f'http://localhost:{config["port"]}/health', timeout=2)
                if response.status_code == 200:
                    status_info['health'] = response.json()
            except:
                status_info['health'] = {'status': 'unreachable'}
            
            # PID情報
            if os.path.exists(config['pid_file']):
                try:
                    with open(config['pid_file'], 'r') as f:
                        pid = int(f.read().strip())
                    status_info['pid'] = pid
                except:
                    pass
        
        return status_info
    
    def get_all_system_status(self) -> Dict[str, Any]:
        """全システムの状態取得"""
        statuses = {}
        for system_name in self.managed_processes.keys():
            statuses[system_name] = self.get_system_status(system_name)
        return statuses

class SystemHealthMonitor:
    """システム健全性監視"""
    
    def __init__(self):
        self.health_history = {}
        self.performance_metrics = {}
        
    def check_system_health(self, system_name: str, port: int) -> Dict[str, Any]:
        """システム健全性チェック"""
        try:
            start_time = time.time()
            response = requests.get(f'http://localhost:{port}/health', timeout=5)
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                health_data = response.json()
                return {
                    'status': 'healthy',
                    'response_time': response_time,
                    'data': health_data,
                    'timestamp': time.time()
                }
            else:
                return {
                    'status': 'unhealthy',
                    'response_time': response_time,
                    'error': f'HTTP {response.status_code}',
                    'timestamp': time.time()
                }
        except Exception as e:
            return {
                'status': 'unreachable',
                'error': str(e),
                'timestamp': time.time()
            }
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """パフォーマンス指標の取得"""
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Pythonプロセスの統計
        python_processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                if 'python' in proc.info['name'].lower():
                    python_processes.append(proc.info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        return {
            'cpu_percent': cpu_percent,
            'memory_percent': memory.percent,
            'memory_available': memory.available,
            'memory_total': memory.total,
            'disk_percent': disk.percent,
            'disk_free': disk.free,
            'disk_total': disk.total,
            'python_processes': len(python_processes),
            'timestamp': time.time()
        }

class UltimateSystemManager:
    """究極システムマネージャー"""
    
    def __init__(self):
        self.process_manager = SystemProcessManager()
        self.health_monitor = SystemHealthMonitor()
        self.management_state = {
            'total_systems': len(self.process_manager.managed_processes),
            'running_systems': 0,
            'healthy_systems': 0,
            'management_cycle': 0,
            'last_update': time.time()
        }
        self.db_path = 'ultimate_system_manager.db'
        self.init_database()
        self.running = False
        self.management_thread = None
        
    def init_database(self):
        """データベース初期化"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS management_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL,
                action TEXT,
                system_name TEXT,
                status TEXT,
                details TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS system_health_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL,
                system_name TEXT,
                status TEXT,
                response_time REAL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        
    def save_management_log(self, action: str, system_name: str, status: str, details: str = ''):
        """管理ログの保存"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO management_log 
            (timestamp, action, system_name, status, details)
            VALUES (?, ?, ?, ?, ?)
        ''', (time.time(), action, system_name, status, details))
        
        conn.commit()
        conn.close()
        
    def start_all_systems(self) -> Dict[str, Any]:
        """全システムの開始"""
        results = {}
        for system_name in self.process_manager.managed_processes.keys():
            result = self.process_manager.start_system(system_name)
            results[system_name] = result
            self.save_management_log('start', system_name, 
                                   'success' if 'status' in result else 'error',
                                   json.dumps(result))
            time.sleep(1)  # システム間の起動間隔
        
        return results
    
    def stop_all_systems(self) -> Dict[str, Any]:
        """全システムの停止"""
        results = {}
        for system_name in self.process_manager.managed_processes.keys():
            result = self.process_manager.stop_system(system_name)
            results[system_name] = result
            self.save_management_log('stop', system_name,
                                   'success' if 'status' in result else 'error',
                                   json.dumps(result))
            time.sleep(1)  # システム間の停止間隔
        
        return results
    
    def restart_all_systems(self) -> Dict[str, Any]:
        """全システムの再起動"""
        stop_results = self.stop_all_systems()
        time.sleep(5)  # 停止待機
        start_results = self.start_all_systems()
        
        return {
            'stop_results': stop_results,
            'start_results': start_results
        }
    
    def management_cycle(self):
        """管理サイクル"""
        # 全システムの状態確認
        all_statuses = self.process_manager.get_all_system_status()
        
        running_count = 0
        healthy_count = 0
        
        for system_name, status in all_statuses.items():
            if status.get('running', False):
                running_count += 1
                
                # 健全性チェック
                if system_name in self.process_manager.managed_processes:
                    port = self.process_manager.managed_processes[system_name]['port']
                    health_result = self.health_monitor.check_system_health(system_name, port)
                    
                    if health_result['status'] == 'healthy':
                        healthy_count += 1
                    
                    # 健全性ログの保存
                    conn = sqlite3.connect(self.db_path)
                    cursor = conn.cursor()
                    cursor.execute('''
                        INSERT INTO system_health_log 
                        (timestamp, system_name, status, response_time)
                        VALUES (?, ?, ?, ?)
                    ''', (
                        time.time(),
                        system_name,
                        health_result['status'],
                        health_result.get('response_time', 0)
                    ))
                    conn.commit()
                    conn.close()
        
        # 管理状態の更新
        self.management_state.update({
            'management_cycle': self.management_state['management_cycle'] + 1,
            'running_systems': running_count,
            'healthy_systems': healthy_count,
            'last_update': time.time()
        })
        
        # パフォーマンス指標の更新
        self.health_monitor.performance_metrics = self.health_monitor.get_performance_metrics()
        
        # ログ出力
        logger.info(f"管理サイクル: {self.management_state['management_cycle']}")
        logger.info(f"実行中システム: {running_count}/{self.management_state['total_systems']}")
        logger.info(f"健全システム: {healthy_count}/{self.management_state['total_systems']}")
        
        return self.management_state.copy()
    
    def start_management(self):
        """管理プロセスの開始"""
        if self.running:
            return
            
        self.running = True
        self.management_thread = threading.Thread(target=self._management_loop, daemon=True)
        self.management_thread.start()
        logger.info("究極システムマネージャーの管理プロセスを開始しました")
    
    def stop_management(self):
        """管理プロセスの停止"""
        self.running = False
        if self.management_thread:
            self.management_thread.join(timeout=5)
        logger.info("究極システムマネージャーの管理プロセスを停止しました")
    
    def _management_loop(self):
        """管理ループ"""
        while self.running:
            try:
                self.management_cycle()
                time.sleep(20)  # 20秒間隔で管理
            except Exception as e:
                logger.error(f"管理サイクルでエラーが発生: {e}")
                time.sleep(5)

# Flask Web API
app = Flask(__name__)
manager = UltimateSystemManager()

@app.route('/health', methods=['GET'])
def health_check():
    """ヘルスチェック"""
    return jsonify({
        'status': 'healthy',
        'system': 'Ultimate System Manager',
        'timestamp': time.time()
    })

@app.route('/api/management-status', methods=['GET'])
def get_management_status():
    """管理状態の取得"""
    return jsonify({
        'management_state': manager.management_state,
        'all_system_status': manager.process_manager.get_all_system_status(),
        'performance_metrics': manager.health_monitor.performance_metrics,
        'timestamp': time.time()
    })

@app.route('/api/system-control', methods=['POST'])
def system_control():
    """システム制御"""
    data = request.get_json()
    action = data.get('action')
    system_name = data.get('system_name')
    
    if action == 'start_all':
        results = manager.start_all_systems()
        return jsonify({'status': 'started_all', 'results': results})
    elif action == 'stop_all':
        results = manager.stop_all_systems()
        return jsonify({'status': 'stopped_all', 'results': results})
    elif action == 'restart_all':
        results = manager.restart_all_systems()
        return jsonify({'status': 'restarted_all', 'results': results})
    elif action == 'start' and system_name:
        result = manager.process_manager.start_system(system_name)
        return jsonify(result)
    elif action == 'stop' and system_name:
        result = manager.process_manager.stop_system(system_name)
        return jsonify(result)
    elif action == 'restart' and system_name:
        result = manager.process_manager.restart_system(system_name)
        return jsonify(result)
    else:
        return jsonify({'error': '無効なアクションまたはシステム名'}), 400

@app.route('/api/management-control', methods=['POST'])
def management_control():
    """管理プロセス制御"""
    data = request.get_json()
    action = data.get('action')
    
    if action == 'start':
        manager.start_management()
        return jsonify({'status': 'started'})
    elif action == 'stop':
        manager.stop_management()
        return jsonify({'status': 'stopped'})
    else:
        return jsonify({'error': '無効なアクション'}), 400

@app.route('/api/system-status/<system_name>', methods=['GET'])
def get_system_status(system_name):
    """特定システムの状態取得"""
    status = manager.process_manager.get_system_status(system_name)
    return jsonify(status)

if __name__ == '__main__':
    # 管理プロセスの開始
    manager.start_management()
    
    # Web APIの開始
    app.run(host='0.0.0.0', port=5013, debug=False) 