#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
究極統合ダッシュボード
全てのシステムを統合表示する究極のダッシュボード
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

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ultimate_unified_dashboard.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# HTMLテンプレート
DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>究極統合ダッシュボード</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            min-height: 100vh;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }
        
        .header {
            text-align: center;
            margin-bottom: 30px;
            background: rgba(255, 255, 255, 0.1);
            padding: 20px;
            border-radius: 15px;
            backdrop-filter: blur(10px);
        }
        
        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
        
        .header p {
            font-size: 1.2em;
            opacity: 0.9;
        }
        
        .dashboard-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .card {
            background: rgba(255, 255, 255, 0.1);
            border-radius: 15px;
            padding: 25px;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.2);
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }
        
        .card:hover {
            transform: translateY(-5px);
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
        }
        
        .card h3 {
            font-size: 1.5em;
            margin-bottom: 15px;
            color: #ffd700;
            text-align: center;
        }
        
        .metric {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
            padding: 8px 0;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }
        
        .metric:last-child {
            border-bottom: none;
        }
        
        .metric-label {
            font-weight: 500;
            opacity: 0.9;
        }
        
        .metric-value {
            font-weight: bold;
            font-size: 1.1em;
        }
        
        .status-indicator {
            display: inline-block;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            margin-right: 8px;
        }
        
        .status-healthy { background-color: #4CAF50; }
        .status-unhealthy { background-color: #f44336; }
        .status-unknown { background-color: #ff9800; }
        
        .progress-bar {
            width: 100%;
            height: 8px;
            background: rgba(255, 255, 255, 0.2);
            border-radius: 4px;
            overflow: hidden;
            margin-top: 5px;
        }
        
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #4CAF50, #8BC34A);
            transition: width 0.3s ease;
        }
        
        .system-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 15px;
            margin-top: 20px;
        }
        
        .system-item {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 10px;
            padding: 15px;
            border-left: 4px solid #4CAF50;
        }
        
        .system-item.unhealthy {
            border-left-color: #f44336;
        }
        
        .system-item.unknown {
            border-left-color: #ff9800;
        }
        
        .refresh-button {
            position: fixed;
            bottom: 30px;
            right: 30px;
            background: linear-gradient(45deg, #4CAF50, #45a049);
            color: white;
            border: none;
            padding: 15px 25px;
            border-radius: 25px;
            cursor: pointer;
            font-size: 1.1em;
            box-shadow: 0 4px 15px rgba(0,0,0,0.2);
            transition: transform 0.2s ease;
        }
        
        .refresh-button:hover {
            transform: scale(1.05);
        }
        
        .loading {
            text-align: center;
            padding: 40px;
            font-size: 1.2em;
        }
        
        @media (max-width: 768px) {
            .dashboard-grid {
                grid-template-columns: 1fr;
            }
            
            .header h1 {
                font-size: 2em;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 究極統合ダッシュボード</h1>
            <p>次世代AIシステム群の統合監視システム</p>
        </div>
        
        <div id="dashboard-content">
            <div class="loading">データを読み込み中...</div>
        </div>
        
        <button class="refresh-button" onclick="refreshDashboard()">
            🔄 更新
        </button>
    </div>
    
    <script>
        let dashboardData = {};
        
        async function loadDashboardData() {
            try {
                const response = await fetch('/api/unified-dashboard-data');
                dashboardData = await response.json();
                updateDashboard();
            } catch (error) {
                console.error('データの読み込みに失敗:', error);
                document.getElementById('dashboard-content').innerHTML = 
                    '<div class="loading">データの読み込みに失敗しました</div>';
            }
        }
        
        function updateDashboard() {
            const content = document.getElementById('dashboard-content');
            
            if (!dashboardData.system_data) {
                content.innerHTML = '<div class="loading">データが利用できません</div>';
                return;
            }
            
            const data = dashboardData.system_data;
            
            content.innerHTML = `
                <div class="dashboard-grid">
                    <div class="card">
                        <h3>🎯 マスターシステム</h3>
                        <div class="metric">
                            <span class="metric-label">マスターサイクル</span>
                            <span class="metric-value">${data.master_cycle || 0}</span>
                        </div>
                        <div class="metric">
                            <span class="metric-label">統合レベル</span>
                            <span class="metric-value">${(data.integration_level || 0).toFixed(3)}</span>
                        </div>
                        <div class="metric">
                            <span class="metric-label">次元コヒーレンス</span>
                            <span class="metric-value">${(data.dimensional_coherence || 0).toFixed(3)}</span>
                        </div>
                        <div class="metric">
                            <span class="metric-label">オーケストレーションパターン</span>
                            <span class="metric-value">${data.orchestration_pattern || 'N/A'}</span>
                        </div>
                        <div class="metric">
                            <span class="metric-label">システム健全性</span>
                            <span class="metric-value">${(data.system_health || 0).toFixed(1)}%</span>
                        </div>
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: ${data.system_health || 0}%"></div>
                        </div>
                    </div>
                    
                    <div class="card">
                        <h3>⚡ パフォーマンス</h3>
                        <div class="metric">
                            <span class="metric-label">パフォーマンススコア</span>
                            <span class="metric-value">${(data.performance_score || 0).toFixed(1)}</span>
                        </div>
                        <div class="metric">
                            <span class="metric-label">CPU使用率</span>
                            <span class="metric-value">${(data.cpu_percent || 0).toFixed(1)}%</span>
                        </div>
                        <div class="metric">
                            <span class="metric-label">メモリ使用率</span>
                            <span class="metric-value">${(data.memory_percent || 0).toFixed(1)}%</span>
                        </div>
                        <div class="metric">
                            <span class="metric-label">ディスク使用率</span>
                            <span class="metric-value">${(data.disk_percent || 0).toFixed(1)}%</span>
                        </div>
                        <div class="metric">
                            <span class="metric-label">Pythonプロセス数</span>
                            <span class="metric-value">${data.python_processes || 0}</span>
                        </div>
                    </div>
                    
                    <div class="card">
                        <h3>🔗 システム統合</h3>
                        <div class="metric">
                            <span class="metric-label">管理システム数</span>
                            <span class="metric-value">${data.total_managed_systems || 0}</span>
                        </div>
                        <div class="metric">
                            <span class="metric-label">健全システム数</span>
                            <span class="metric-value">${data.healthy_systems || 0}</span>
                        </div>
                        <div class="metric">
                            <span class="metric-label">健全性比率</span>
                            <span class="metric-value">${data.health_ratio || 0}%</span>
                        </div>
                        <div class="metric">
                            <span class="metric-label">平均応答時間</span>
                            <span class="metric-value">${(data.avg_response_time || 0).toFixed(3)}s</span>
                        </div>
                    </div>
                    
                    <div class="card">
                        <h3>🌐 システム状態</h3>
                        <div class="system-grid">
                            ${generateSystemStatusHTML(data.managed_systems || {})}
                        </div>
                    </div>
                </div>
            `;
        }
        
        function generateSystemStatusHTML(systems) {
            return Object.entries(systems).map(([name, config]) => {
                const statusClass = config.status === 'healthy' ? 'healthy' : 
                                  config.status === 'unhealthy' ? 'unhealthy' : 'unknown';
                const statusColor = config.status === 'healthy' ? '#4CAF50' : 
                                  config.status === 'unhealthy' ? '#f44336' : '#ff9800';
                
                return `
                    <div class="system-item ${statusClass}">
                        <div style="display: flex; align-items: center; margin-bottom: 8px;">
                            <span class="status-indicator status-${config.status}"></span>
                            <strong>${name}</strong>
                        </div>
                        <div style="font-size: 0.9em; opacity: 0.8;">
                            ポート: ${config.port || 'N/A'}<br>
                            応答時間: ${(config.response_time || 0).toFixed(3)}s
                        </div>
                    </div>
                `;
            }).join('');
        }
        
        function refreshDashboard() {
            loadDashboardData();
        }
        
        // 初期読み込み
        loadDashboardData();
        
        // 30秒ごとに自動更新
        setInterval(loadDashboardData, 30000);
    </script>
</body>
</html>
"""

class UnifiedDataCollector:
    """統合データ収集システム"""
    
    def __init__(self):
        self.system_endpoints = {
            'ultimate_integration_master': 'http://localhost:5005',
            'dimensional_transcendence': 'http://localhost:5006',
            'advanced_quantum_optimizer': 'http://localhost:5007',
            'ultimate_quantum_transcendence': 'http://localhost:5008',
            'dimensional_integration_master': 'http://localhost:5010'
        }
        self.collected_data = {}
        self.last_collection_time = 0
        
    def collect_system_data(self) -> Dict[str, Any]:
        """全システムのデータ収集"""
        unified_data = {
            'timestamp': time.time(),
            'systems': {},
            'master_data': {},
            'performance_data': {},
            'summary': {}
        }
        
        # 各システムからのデータ収集
        for system_name, endpoint in self.system_endpoints.items():
            try:
                # システムデータの取得
                response = requests.get(f'{endpoint}/api/master-system-data', timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    unified_data['systems'][system_name] = data
                else:
                    unified_data['systems'][system_name] = {'error': f'HTTP {response.status_code}'}
            except Exception as e:
                unified_data['systems'][system_name] = {'error': str(e)}
        
        # マスターシステムからの統合データ
        try:
            master_response = requests.get('http://localhost:5010/api/master-system-data', timeout=5)
            if master_response.status_code == 200:
                unified_data['master_data'] = master_response.json()
        except Exception as e:
            unified_data['master_data'] = {'error': str(e)}
        
        # リソース監視データ
        try:
            resource_response = requests.get('http://localhost:5010/api/resource-monitoring', timeout=5)
            if resource_response.status_code == 200:
                unified_data['performance_data'] = resource_response.json()
        except Exception as e:
            unified_data['performance_data'] = {'error': str(e)}
        
        # 統合サマリーの計算
        unified_data['summary'] = self.calculate_unified_summary(unified_data)
        
        self.collected_data = unified_data
        self.last_collection_time = time.time()
        
        return unified_data
    
    def calculate_unified_summary(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """統合サマリーの計算"""
        summary = {
            'total_systems': len(self.system_endpoints),
            'healthy_systems': 0,
            'total_cycles': 0,
            'avg_performance': 0.0,
            'avg_health': 0.0
        }
        
        # 健全システム数の計算
        for system_name, system_data in data['systems'].items():
            if 'error' not in system_data:
                if 'system_state' in system_data:
                    state = system_data['system_state']
                    if state.get('system_health', 0) > 50:
                        summary['healthy_systems'] += 1
                    summary['total_cycles'] += state.get('evolution_cycle', 0)
        
        # パフォーマンスと健全性の平均
        performance_scores = []
        health_scores = []
        
        for system_data in data['systems'].values():
            if 'error' not in system_data and 'system_state' in system_data:
                state = system_data['system_state']
                performance_scores.append(state.get('performance_score', 0))
                health_scores.append(state.get('system_health', 0))
        
        if performance_scores:
            summary['avg_performance'] = np.mean(performance_scores)
        if health_scores:
            summary['avg_health'] = np.mean(health_scores)
        
        return summary

class UltimateUnifiedDashboard:
    """究極統合ダッシュボード"""
    
    def __init__(self):
        self.data_collector = UnifiedDataCollector()
        self.dashboard_data = {}
        self.running = False
        self.collection_thread = None
        
    def start_data_collection(self):
        """データ収集の開始"""
        if self.running:
            return
            
        self.running = True
        self.collection_thread = threading.Thread(target=self._data_collection_loop, daemon=True)
        self.collection_thread.start()
        logger.info("究極統合ダッシュボードのデータ収集を開始しました")
    
    def stop_data_collection(self):
        """データ収集の停止"""
        self.running = False
        if self.collection_thread:
            self.collection_thread.join(timeout=5)
        logger.info("究極統合ダッシュボードのデータ収集を停止しました")
    
    def _data_collection_loop(self):
        """データ収集ループ"""
        while self.running:
            try:
                self.dashboard_data = self.data_collector.collect_system_data()
                logger.info("統合ダッシュボードデータを更新しました")
                time.sleep(10)  # 10秒間隔でデータ収集
            except Exception as e:
                logger.error(f"データ収集でエラーが発生: {e}")
                time.sleep(5)
    
    def get_unified_dashboard_data(self) -> Dict[str, Any]:
        """統合ダッシュボードデータの取得"""
        if not self.dashboard_data:
            return {'error': 'データが利用できません'}
        
        # マスターシステムの状態を取得
        master_data = self.dashboard_data.get('master_data', {})
        system_data = master_data.get('system_state', {})
        
        # パフォーマンスデータを取得
        performance_data = self.dashboard_data.get('performance_data', {})
        resource_data = performance_data.get('resource_data', {})
        performance_metrics = performance_data.get('performance_metrics', {})
        
        # 管理システムの状態を取得
        managed_systems = {}
        if 'managed_systems' in master_data:
            managed_systems = master_data['managed_systems']
        
        # 統合データの構築
        unified_data = {
            'master_cycle': system_data.get('master_cycle', 0),
            'integration_level': system_data.get('integration_level', 0),
            'dimensional_coherence': system_data.get('dimensional_coherence', 0),
            'orchestration_pattern': system_data.get('orchestration_pattern', 'N/A'),
            'system_health': system_data.get('system_health', 0),
            'performance_score': system_data.get('performance_score', 0),
            'cpu_percent': resource_data.get('cpu_percent', 0),
            'memory_percent': resource_data.get('memory_percent', 0),
            'disk_percent': resource_data.get('disk_percent', 0),
            'python_processes': resource_data.get('python_processes', 0),
            'total_managed_systems': system_data.get('total_managed_systems', 0),
            'healthy_systems': system_data.get('healthy_systems', 0),
            'health_ratio': (system_data.get('healthy_systems', 0) / max(1, system_data.get('total_managed_systems', 1))) * 100,
            'avg_response_time': np.mean([config.get('response_time', 0) for config in managed_systems.values()]) if managed_systems else 0,
            'managed_systems': managed_systems,
            'timestamp': time.time()
        }
        
        return unified_data

# Flask Web API
app = Flask(__name__)
dashboard = UltimateUnifiedDashboard()

@app.route('/')
def dashboard_home():
    """ダッシュボードホームページ"""
    return render_template_string(DASHBOARD_HTML)

@app.route('/health', methods=['GET'])
def health_check():
    """ヘルスチェック"""
    return jsonify({
        'status': 'healthy',
        'system': 'Ultimate Unified Dashboard',
        'timestamp': time.time()
    })

@app.route('/api/unified-dashboard-data', methods=['GET'])
def get_unified_dashboard_data():
    """統合ダッシュボードデータの取得"""
    return jsonify({
        'system_data': dashboard.get_unified_dashboard_data(),
        'raw_data': dashboard.dashboard_data,
        'timestamp': time.time()
    })

@app.route('/api/dashboard-control', methods=['POST'])
def dashboard_control():
    """ダッシュボード制御"""
    data = request.get_json()
    action = data.get('action')
    
    if action == 'start':
        dashboard.start_data_collection()
        return jsonify({'status': 'started'})
    elif action == 'stop':
        dashboard.stop_data_collection()
        return jsonify({'status': 'stopped'})
    else:
        return jsonify({'error': '無効なアクション'}), 400

@app.route('/api/system-status', methods=['GET'])
def get_system_status():
    """システム状態の取得"""
    return jsonify({
        'dashboard_running': dashboard.running,
        'last_collection_time': dashboard.data_collector.last_collection_time,
        'collected_systems': len(dashboard.data_collector.system_endpoints),
        'timestamp': time.time()
    })

if __name__ == '__main__':
    # ダッシュボードの開始
    dashboard.start_data_collection()
    
    # Web APIの開始
    app.run(host='0.0.0.0', port=5011, debug=False) 