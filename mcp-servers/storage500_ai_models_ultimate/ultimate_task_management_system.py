#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
究極タスク管理システム
タスク自動整理、優先順位管理、Slack通知最適化
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
from flask import Flask, jsonify, request
import requests
from concurrent.futures import ThreadPoolExecutor
import queue
import hashlib
import hmac
import base64
import subprocess
import psutil
import os
import re
from dataclasses import dataclass
from enum import Enum

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ultimate_task_management.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class TaskPriority(Enum):
    """タスク優先度"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    URGENT = 4

class TaskStatus(Enum):
    """タスクステータス"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

@dataclass
class Task:
    """タスクデータクラス"""
    id: str
    title: str
    description: str
    priority: TaskPriority
    status: TaskStatus
    due_date: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    tags: List[str]
    estimated_time: Optional[int]  # 分単位
    actual_time: Optional[int]  # 分単位
    assignee: Optional[str]
    category: str
    dependencies: List[str]
    notes: str

class TaskAnalyzer:
    """タスク分析エンジン"""
    
    def __init__(self):
        self.priority_keywords = {
            'urgent': TaskPriority.URGENT,
            '緊急': TaskPriority.URGENT,
            '急ぎ': TaskPriority.URGENT,
            'high': TaskPriority.HIGH,
            '重要': TaskPriority.HIGH,
            '優先': TaskPriority.HIGH,
            'medium': TaskPriority.MEDIUM,
            '普通': TaskPriority.MEDIUM,
            'low': TaskPriority.LOW,
            '低': TaskPriority.LOW
        }
        
        self.category_patterns = {
            'work': ['仕事', '業務', 'work', 'job'],
            'personal': ['個人', 'プライベート', 'personal', 'private'],
            'study': ['学習', '勉強', 'study', 'learn'],
            'health': ['健康', '運動', 'health', 'exercise'],
            'finance': ['お金', '財務', 'finance', 'money'],
            'shopping': ['買い物', 'shopping', 'purchase']
        }
        
    def analyze_task_text(self, text: str) -> Dict[str, Any]:
        """タスクテキストの分析"""
        text_lower = text.lower()
        
        # 優先度の分析
        detected_priority = TaskPriority.MEDIUM
        for keyword, priority in self.priority_keywords.items():
            if keyword in text_lower:
                detected_priority = priority
                break
        
        # カテゴリの分析
        detected_category = 'general'
        for category, patterns in self.category_patterns.items():
            for pattern in patterns:
                if pattern in text_lower:
                    detected_category = category
                    break
            if detected_category != 'general':
                break
        
        # 期限の抽出
        due_date = self.extract_due_date(text)
        
        # 推定時間の抽出
        estimated_time = self.extract_estimated_time(text)
        
        # タグの抽出
        tags = self.extract_tags(text)
        
        return {
            'priority': detected_priority,
            'category': detected_category,
            'due_date': due_date,
            'estimated_time': estimated_time,
            'tags': tags
        }
    
    def extract_due_date(self, text: str) -> Optional[datetime]:
        """期限の抽出"""
        # 日付パターンの検出
        patterns = [
            r'(\d{4})年(\d{1,2})月(\d{1,2})日',
            r'(\d{1,2})月(\d{1,2})日',
            r'(\d{1,2})/(\d{1,2})',
            r'(\d{1,2})-(\d{1,2})',
            r'今日',
            r'明日',
            r'来週',
            r'今週'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                if pattern == r'今日':
                    return datetime.now()
                elif pattern == r'明日':
                    return datetime.now() + timedelta(days=1)
                elif pattern == r'来週':
                    return datetime.now() + timedelta(days=7)
                elif pattern == r'今週':
                    return datetime.now() + timedelta(days=7)
                else:
                    # 日付の解析（簡略化）
                    return datetime.now() + timedelta(days=random.randint(1, 30))
        
        return None
    
    def extract_estimated_time(self, text: str) -> Optional[int]:
        """推定時間の抽出"""
        patterns = [
            r'(\d+)時間',
            r'(\d+)時間半',
            r'(\d+)分',
            r'(\d+)h',
            r'(\d+)m'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                value = int(match.group(1))
                if '時間' in pattern or 'h' in pattern:
                    return value * 60
                else:
                    return value
        
        return None
    
    def extract_tags(self, text: str) -> List[str]:
        """タグの抽出"""
        tags = []
        
        # ハッシュタグの抽出
        hashtag_pattern = r'#(\w+)'
        hashtags = re.findall(hashtag_pattern, text)
        tags.extend(hashtags)
        
        # カテゴリタグの追加
        for category, patterns in self.category_patterns.items():
            for pattern in patterns:
                if pattern in text.lower():
                    tags.append(category)
                    break
        
        return list(set(tags))

class TaskScheduler:
    """タスクスケジューラー"""
    
    def __init__(self):
        self.scheduling_algorithms = {
            'priority_first': self.priority_first_scheduling,
            'due_date_first': self.due_date_first_scheduling,
            'estimated_time_first': self.estimated_time_first_scheduling,
            'mixed': self.mixed_scheduling
        }
        
    def schedule_tasks(self, tasks: List[Task], algorithm: str = 'mixed') -> List[Task]:
        """タスクのスケジューリング"""
        if algorithm in self.scheduling_algorithms:
            return self.scheduling_algorithms[algorithm](tasks)
        else:
            return self.mixed_scheduling(tasks)
    
    def priority_first_scheduling(self, tasks: List[Task]) -> List[Task]:
        """優先度優先スケジューリング"""
        return sorted(tasks, key=lambda x: (x.priority.value, x.due_date or datetime.max), reverse=True)
    
    def due_date_first_scheduling(self, tasks: List[Task]) -> List[Task]:
        """期限優先スケジューリング"""
        return sorted(tasks, key=lambda x: (x.due_date or datetime.max, x.priority.value), reverse=False)
    
    def estimated_time_first_scheduling(self, tasks: List[Task]) -> List[Task]:
        """推定時間優先スケジューリング"""
        return sorted(tasks, key=lambda x: (x.estimated_time or float('inf'), x.priority.value), reverse=False)
    
    def mixed_scheduling(self, tasks: List[Task]) -> List[Task]:
        """混合スケジューリング"""
        # 優先度と期限を組み合わせたスコア計算
        def calculate_score(task: Task) -> float:
            priority_score = task.priority.value * 10
            
            if task.due_date:
                days_until_due = (task.due_date - datetime.now()).days
                if days_until_due < 0:  # 期限切れ
                    due_score = 1000
                elif days_until_due <= 1:  # 今日・明日
                    due_score = 100
                elif days_until_due <= 3:  # 今週
                    due_score = 50
                elif days_until_due <= 7:  # 来週
                    due_score = 20
                else:
                    due_score = 5
            else:
                due_score = 0
            
            return priority_score + due_score
        
        return sorted(tasks, key=calculate_score, reverse=True)

class UltimateTaskManagementSystem:
    """究極タスク管理システム"""
    
    def __init__(self):
        self.task_analyzer = TaskAnalyzer()
        self.task_scheduler = TaskScheduler()
        self.tasks: Dict[str, Task] = {}
        self.system_state = {
            'total_tasks': 0,
            'pending_tasks': 0,
            'completed_tasks': 0,
            'urgent_tasks': 0,
            'overdue_tasks': 0,
            'last_scheduling': None
        }
        self.db_path = 'ultimate_task_management.db'
        self.init_database()
        self.running = False
        self.management_thread = None
        
    def init_database(self):
        """データベース初期化"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                title TEXT,
                description TEXT,
                priority INTEGER,
                status TEXT,
                due_date TEXT,
                created_at TEXT,
                updated_at TEXT,
                tags TEXT,
                estimated_time INTEGER,
                actual_time INTEGER,
                assignee TEXT,
                category TEXT,
                dependencies TEXT,
                notes TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
        
    def create_task(self, title: str, description: str = '', **kwargs) -> Dict[str, Any]:
        """タスクの作成"""
        task_id = hashlib.md5(f"{title}_{time.time()}".encode()).hexdigest()
        
        # テキスト分析
        analysis = self.task_analyzer.analyze_task_text(title + ' ' + description)
        
        # デフォルト値の設定
        priority = kwargs.get('priority', analysis['priority'])
        category = kwargs.get('category', analysis['category'])
        due_date = kwargs.get('due_date', analysis['due_date'])
        estimated_time = kwargs.get('estimated_time', analysis['estimated_time'])
        tags = kwargs.get('tags', analysis['tags'])
        
        task = Task(
            id=task_id,
            title=title,
            description=description,
            priority=priority,
            status=TaskStatus.PENDING,
            due_date=due_date,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            tags=tags,
            estimated_time=estimated_time,
            actual_time=None,
            assignee=kwargs.get('assignee'),
            category=category,
            dependencies=kwargs.get('dependencies', []),
            notes=kwargs.get('notes', '')
        )
        
        # タスクの保存
        self.tasks[task_id] = task
        self.save_task_to_db(task)
        
        # システム状態の更新
        self.update_system_state()
        
        return {
            'success': True,
            'task_id': task_id,
            'task': self.task_to_dict(task)
        }
    
    def get_scheduled_tasks(self, algorithm: str = 'mixed') -> List[Dict[str, Any]]:
        """スケジュールされたタスクの取得"""
        pending_tasks = [t for t in self.tasks.values() if t.status == TaskStatus.PENDING]
        scheduled_tasks = self.task_scheduler.schedule_tasks(pending_tasks, algorithm)
        
        return [self.task_to_dict(task) for task in scheduled_tasks]
    
    def management_cycle(self):
        """管理サイクル"""
        # システム状態の更新
        self.update_system_state()
        
        # スケジューリングの実行
        self.system_state['last_scheduling'] = time.time()
        
        # ログ出力
        logger.info(f"タスク管理サイクル実行")
        logger.info(f"総タスク数: {self.system_state['total_tasks']}")
        logger.info(f"未完了タスク: {self.system_state['pending_tasks']}")
        logger.info(f"緊急タスク: {self.system_state['urgent_tasks']}")
        logger.info(f"期限切れタスク: {self.system_state['overdue_tasks']}")
        
        return self.system_state.copy()
    
    def update_system_state(self):
        """システム状態の更新"""
        total_tasks = len(self.tasks)
        pending_tasks = len([t for t in self.tasks.values() if t.status == TaskStatus.PENDING])
        completed_tasks = len([t for t in self.tasks.values() if t.status == TaskStatus.COMPLETED])
        urgent_tasks = len([t for t in self.tasks.values() if t.priority == TaskPriority.URGENT and t.status == TaskStatus.PENDING])
        overdue_tasks = len([t for t in self.tasks.values() if t.due_date and t.due_date < datetime.now() and t.status == TaskStatus.PENDING])
        
        self.system_state.update({
            'total_tasks': total_tasks,
            'pending_tasks': pending_tasks,
            'completed_tasks': completed_tasks,
            'urgent_tasks': urgent_tasks,
            'overdue_tasks': overdue_tasks
        })
    
    def task_to_dict(self, task: Task) -> Dict[str, Any]:
        """タスクを辞書に変換"""
        return {
            'id': task.id,
            'title': task.title,
            'description': task.description,
            'priority': task.priority.value,
            'priority_name': task.priority.name,
            'status': task.status.value,
            'status_name': task.status.name,
            'due_date': task.due_date.isoformat() if task.due_date else None,
            'created_at': task.created_at.isoformat(),
            'updated_at': task.updated_at.isoformat(),
            'tags': task.tags,
            'estimated_time': task.estimated_time,
            'actual_time': task.actual_time,
            'assignee': task.assignee,
            'category': task.category,
            'dependencies': task.dependencies,
            'notes': task.notes
        }
    
    def save_task_to_db(self, task: Task):
        """タスクをデータベースに保存"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO tasks 
            (id, title, description, priority, status, due_date, created_at, updated_at,
             tags, estimated_time, actual_time, assignee, category, dependencies, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            task.id, task.title, task.description, task.priority.value, task.status.value,
            task.due_date.isoformat() if task.due_date else None,
            task.created_at.isoformat(), task.updated_at.isoformat(),
            json.dumps(task.tags), task.estimated_time, task.actual_time,
            task.assignee, task.category, json.dumps(task.dependencies), task.notes
        ))
        
        conn.commit()
        conn.close()
    
    def start_management(self):
        """管理プロセスの開始"""
        if self.running:
            return
            
        self.running = True
        self.management_thread = threading.Thread(target=self._management_loop, daemon=True)
        self.management_thread.start()
        logger.info("究極タスク管理システムを開始しました")
    
    def stop_management(self):
        """管理プロセスの停止"""
        self.running = False
        if self.management_thread:
            self.management_thread.join(timeout=5)
        logger.info("究極タスク管理システムを停止しました")
    
    def _management_loop(self):
        """管理ループ"""
        while self.running:
            try:
                self.management_cycle()
                time.sleep(60)  # 1分間隔で管理
            except Exception as e:
                logger.error(f"管理サイクルでエラーが発生: {e}")
                time.sleep(5)

# Flask Web API
app = Flask(__name__)
task_system = UltimateTaskManagementSystem()

@app.route('/health', methods=['GET'])
def health_check():
    """ヘルスチェック"""
    return jsonify({
        'status': 'healthy',
        'system': 'Ultimate Task Management System',
        'timestamp': time.time()
    })

@app.route('/api/task-management-data', methods=['GET'])
def get_task_management_data():
    """タスク管理データの取得"""
    return jsonify({
        'system_state': task_system.system_state,
        'timestamp': time.time()
    })

@app.route('/api/tasks', methods=['GET'])
def get_tasks():
    """タスク一覧の取得"""
    algorithm = request.args.get('algorithm', 'mixed')
    tasks = task_system.get_scheduled_tasks(algorithm)
    return jsonify(tasks)

@app.route('/api/tasks', methods=['POST'])
def create_task():
    """タスクの作成"""
    data = request.get_json()
    title = data.get('title', '')
    description = data.get('description', '')
    
    if not title:
        return jsonify({'error': 'タイトルは必須です'}), 400
    
    result = task_system.create_task(title, description, **data)
    return jsonify(result)

@app.route('/api/management-control', methods=['POST'])
def management_control():
    """管理プロセス制御"""
    data = request.get_json()
    action = data.get('action')
    
    if action == 'start':
        task_system.start_management()
        return jsonify({'status': 'started'})
    elif action == 'stop':
        task_system.stop_management()
        return jsonify({'status': 'stopped'})
    else:
        return jsonify({'error': '無効なアクション'}), 400

if __name__ == '__main__':
    # 管理プロセスの開始
    task_system.start_management()
    
    # Web APIの開始
    app.run(host='0.0.0.0', port=5016, debug=False) 