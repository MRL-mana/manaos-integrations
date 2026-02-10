#!/usr/bin/env python3
"""
拡張AI統合システム
================

機能:
- 複数AIモデルの統合管理
- 自動タスク実行
- 学習・最適化
- ダッシュボード統合
- パフォーマンス監視

作者: Mana
作成日: 2024-09-03
"""

import asyncio
import logging
import json
import sqlite3
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
import requests
import schedule
import threading
from dataclasses import dataclass
import psutil

@dataclass
class AIModule:
    """AIモジュールの情報"""
    name: str
    type: str
    status: str
    last_used: datetime
    performance_score: float
    config: Dict[str, Any]

class EnhancedAISystem:
    """拡張AI統合システム"""

    def __init__(self):
        self.setup_logging()
        self.config = self.load_config()
        self.modules = {}
        self.task_queue = []
        self.performance_history = []
        self.db_path = Path("integrated_ai_system/enhanced_ai_system.db")

        self.logger.info("拡張AI統合システムを初期化中...")
        self.initialize_database()
        self.load_existing_modules()

    def setup_logging(self):
        """ログ設定"""
        log_dir = Path("/root/logs")
        log_dir.mkdir(exist_ok=True)

        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_dir / "enhanced_ai_system.log"),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger('EnhancedAISystem')

    def load_config(self) -> Dict[str, Any]:
        """設定ファイルの読み込み"""
        config_file = Path("integrated_ai_system/enhanced_ai_config.json")

        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.error(f"設定ファイル読み込みエラー: {e}")

        # デフォルト設定
        return {
            'system': {
                'auto_optimization': True,
                'performance_threshold': 0.8,
                'max_concurrent_tasks': 5,
                'backup_interval_hours': 24
            },
            'modules': {
                'ollama': {
                    'enabled': True,
                    'base_url': 'http://localhost:11434',
                    'models': ['llama2', 'codellama', 'mistral']
                },
                'openai': {
                    'enabled': False,
                    'api_key': '',
                    'models': ['gpt-4', 'gpt-3.5-turbo']
                },
                'local_models': {
                    'enabled': True,
                    'path': '/root/models'
                }
            },
            'monitoring': {
                'enabled': True,
                'interval_seconds': 60,
                'alert_threshold': 0.9
            }
        }

    def initialize_database(self):
        """データベースの初期化"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # AIモジュールテーブル
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS ai_modules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    type TEXT NOT NULL,
                    status TEXT DEFAULT 'inactive',
                    last_used TIMESTAMP,
                    performance_score REAL DEFAULT 0.0,
                    config TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # タスク履歴テーブル
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS task_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    module_name TEXT NOT NULL,
                    task_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    start_time TIMESTAMP,
                    end_time TIMESTAMP,
                    performance_score REAL,
                    error_message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # パフォーマンス履歴テーブル
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS performance_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    module_name TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    cpu_usage REAL,
                    memory_usage REAL,
                    response_time REAL,
                    accuracy REAL
                )
            ''')

            conn.commit()
            conn.close()
            self.logger.info("データベース初期化完了")

        except Exception as e:
            self.logger.error(f"データベース初期化エラー: {e}")

    def load_existing_modules(self):
        """既存のAIモジュールを読み込み"""
        try:
            # Ollamaモジュール
            if self.config['modules']['ollama']['enabled']:
                self.add_module('ollama', 'ollama', {
                    'base_url': self.config['modules']['ollama']['base_url'],
                    'models': self.config['modules']['ollama']['models']
                })

            # ローカルモデル
            if self.config['modules']['local_models']['enabled']:
                local_models_path = Path(self.config['modules']['local_models']['path'])
                if local_models_path.exists():
                    for model_dir in local_models_path.iterdir():
                        if model_dir.is_dir():
                            self.add_module(f"local_{model_dir.name}", 'local', {
                                'path': str(model_dir),
                                'type': 'local_model'
                            })

            self.logger.info(f"{len(self.modules)}個のAIモジュールを読み込みました")

        except Exception as e:
            self.logger.error(f"モジュール読み込みエラー: {e}")

    def add_module(self, name: str, module_type: str, config: Dict[str, Any]):
        """AIモジュールを追加"""
        try:
            module = AIModule(
                name=name,
                type=module_type,
                status='active',
                last_used=datetime.now(),
                performance_score=0.0,
                config=config
            )

            self.modules[name] = module

            # データベースに保存
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                INSERT OR REPLACE INTO ai_modules
                (name, type, status, last_used, performance_score, config)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (name, module_type, 'active', datetime.now(), 0.0, json.dumps(config)))

            conn.commit()
            conn.close()

            self.logger.info(f"AIモジュール '{name}' を追加しました")

        except Exception as e:
            self.logger.error(f"モジュール追加エラー: {e}")

    async def execute_task(self, task_type: str, module_name: str, **kwargs) -> Dict[str, Any]:
        """AIタスクを実行"""
        try:
            if module_name not in self.modules:
                raise ValueError(f"モジュール '{module_name}' が見つかりません")

            module = self.modules[module_name]
            start_time = datetime.now()

            # タスク実行
            result = await self._execute_task_internal(task_type, module, **kwargs)

            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()

            # パフォーマンススコアを計算
            performance_score = self._calculate_performance_score(execution_time, result)

            # 履歴を記録
            self._record_task_execution(module_name, task_type, 'completed',
                                      start_time, end_time, performance_score)

            # モジュールのパフォーマンスを更新
            self._update_module_performance(module_name, performance_score)

            return {
                'success': True,
                'result': result,
                'execution_time': execution_time,
                'performance_score': performance_score
            }

        except Exception as e:
            self.logger.error(f"タスク実行エラー: {e}")

            # エラー履歴を記録
            self._record_task_execution(module_name, task_type, 'failed',
                                      start_time, datetime.now(), 0.0, str(e))

            return {
                'success': False,
                'error': str(e)
            }

    async def _execute_task_internal(self, task_type: str, module: AIModule, **kwargs):
        """内部タスク実行"""
        if module.type == 'ollama':
            return await self._execute_ollama_task(task_type, module, **kwargs)
        elif module.type == 'local':
            return await self._execute_local_task(task_type, module, **kwargs)
        else:
            raise ValueError(f"サポートされていないモジュールタイプ: {module.type}")

    async def _execute_ollama_task(self, task_type: str, module: AIModule, **kwargs):
        """Ollamaタスクの実行"""
        try:
            base_url = module.config['base_url']
            model = kwargs.get('model', module.config['models'][0])
            prompt = kwargs.get('prompt', '')

            url = f"{base_url}/api/generate"
            data = {
                'model': model,
                'prompt': prompt,
                'stream': False
            }

            response = requests.post(url, json=data, timeout=30)

            if response.status_code == 200:
                result = response.json()
                return result.get('response', '')
            else:
                raise Exception(f"Ollama API エラー: {response.status_code}")

        except Exception as e:
            self.logger.error(f"Ollamaタスク実行エラー: {e}")
            raise

    async def _execute_local_task(self, task_type: str, module: AIModule, **kwargs):
        """ローカルタスクの実行"""
        try:
            # ローカルモデルの実行（簡易版）
            if task_type == 'text_generation':
                return f"ローカルモデル '{module.name}' による生成結果"
            elif task_type == 'analysis':
                return f"ローカルモデル '{module.name}' による分析結果"
            else:
                return f"ローカルモデル '{module.name}' による処理結果"

        except Exception as e:
            self.logger.error(f"ローカルタスク実行エラー: {e}")
            raise

    def _calculate_performance_score(self, execution_time: float, result: Any) -> float:
        """パフォーマンススコアを計算"""
        # 実行時間が短いほど高スコア
        time_score = max(0, 1.0 - (execution_time / 60.0))  # 60秒以内で満点

        # 結果の品質スコア（簡易版）
        quality_score = 0.8 if result else 0.0

        # 総合スコア
        total_score = (time_score * 0.6) + (quality_score * 0.4)

        return min(1.0, max(0.0, total_score))

    def _record_task_execution(self, module_name: str, task_type: str, status: str,
                              start_time: datetime, end_time: datetime,
                              performance_score: float, error_message: str = None):
        """タスク実行履歴を記録"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO task_history
                (module_name, task_type, status, start_time, end_time, performance_score, error_message)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (module_name, task_type, status, start_time, end_time, performance_score, error_message))

            conn.commit()
            conn.close()

        except Exception as e:
            self.logger.error(f"履歴記録エラー: {e}")

    def _update_module_performance(self, module_name: str, performance_score: float):
        """モジュールのパフォーマンスを更新"""
        try:
            if module_name in self.modules:
                self.modules[module_name].performance_score = performance_score
                self.modules[module_name].last_used = datetime.now()

                # データベースも更新
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()

                cursor.execute('''
                    UPDATE ai_modules
                    SET performance_score = ?, last_used = ?
                    WHERE name = ?
                ''', (performance_score, datetime.now(), module_name))

                conn.commit()
                conn.close()

        except Exception as e:
            self.logger.error(f"パフォーマンス更新エラー: {e}")

    async def monitor_system_performance(self):
        """システムパフォーマンスの監視"""
        try:
            for module_name, module in self.modules.items():
                # CPU・メモリ使用量を取得
                cpu_usage = psutil.cpu_percent(interval=1)
                memory_usage = psutil.virtual_memory().percent

                # パフォーマンス履歴に記録
                self._record_performance_metrics(module_name, cpu_usage, memory_usage)

                # アラートチェック
                if cpu_usage > self.config['monitoring']['alert_threshold'] * 100:
                    self.logger.warning(f"モジュール '{module_name}' のCPU使用量が高い: {cpu_usage}%")

                if memory_usage > self.config['monitoring']['alert_threshold'] * 100:
                    self.logger.warning(f"モジュール '{module_name}' のメモリ使用量が高い: {memory_usage}%")

        except Exception as e:
            self.logger.error(f"パフォーマンス監視エラー: {e}")

    def _record_performance_metrics(self, module_name: str, cpu_usage: float,
                                   memory_usage: float, response_time: float = 0.0,
                                   accuracy: float = 0.0):
        """パフォーマンス指標を記録"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO performance_history
                (module_name, cpu_usage, memory_usage, response_time, accuracy)
                VALUES (?, ?, ?, ?, ?)
            ''', (module_name, cpu_usage, memory_usage, response_time, accuracy))

            conn.commit()
            conn.close()

        except Exception as e:
            self.logger.error(f"パフォーマンス指標記録エラー: {e}")

    async def optimize_system(self):
        """システムの最適化"""
        try:
            self.logger.info("システム最適化を開始します")

            # パフォーマンスの低いモジュールを特定
            low_performance_modules = [
                name for name, module in self.modules.items()
                if module.performance_score < self.config['system']['performance_threshold']
            ]

            if low_performance_modules:
                self.logger.info(f"最適化が必要なモジュール: {low_performance_modules}")

                # 最適化処理（簡易版）
                for module_name in low_performance_modules:
                    await self._optimize_module(module_name)

            # 古いログ・履歴のクリーンアップ
            await self._cleanup_old_data()

            self.logger.info("システム最適化完了")

        except Exception as e:
            self.logger.error(f"システム最適化エラー: {e}")

    async def _optimize_module(self, module_name: str):
        """個別モジュールの最適化"""
        try:
            if module_name in self.modules:
                module = self.modules[module_name]

                # モジュールタイプに応じた最適化
                if module.type == 'ollama':
                    # Ollamaの最適化
                    await self._optimize_ollama_module(module)
                elif module.type == 'local':
                    # ローカルモジュールの最適化
                    await self._optimize_local_module(module)

        except Exception as e:
            self.logger.error(f"モジュール最適化エラー: {e}")

    async def _optimize_ollama_module(self, module: AIModule):
        """Ollamaモジュールの最適化"""
        try:
            # モデルの再読み込み
            base_url = module.config['base_url']
            url = f"{base_url}/api/tags"

            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                self.logger.info(f"Ollamaモジュール '{module.name}' の最適化完了")

        except Exception as e:
            self.logger.error(f"Ollama最適化エラー: {e}")

    async def _optimize_local_module(self, module: AIModule):
        """ローカルモジュールの最適化"""
        try:
            # ローカルファイルの整合性チェック
            model_path = Path(module.config.get('path', ''))
            if model_path.exists():
                self.logger.info(f"ローカルモジュール '{module.name}' の最適化完了")

        except Exception as e:
            self.logger.error(f"ローカル最適化エラー: {e}")

    async def _cleanup_old_data(self):
        """古いデータのクリーンアップ"""
        try:
            # 30日以上前の履歴を削除
            cutoff_date = datetime.now() - timedelta(days=30)

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                DELETE FROM task_history
                WHERE created_at < ?
            ''', (cutoff_date,))

            cursor.execute('''
                DELETE FROM performance_history
                WHERE timestamp < ?
            ''', (cutoff_date,))

            conn.commit()
            conn.close()

            self.logger.info("古いデータのクリーンアップ完了")

        except Exception as e:
            self.logger.error(f"データクリーンアップエラー: {e}")

    def get_system_status(self) -> Dict[str, Any]:
        """システム状態を取得"""
        try:
            status = {
                'timestamp': datetime.now().isoformat(),
                'total_modules': len(self.modules),
                'active_modules': len([m for m in self.modules.values() if m.status == 'active']),
                'average_performance': sum(m.performance_score for m in self.modules.values()) / len(self.modules) if self.modules else 0,
                'modules': {}
            }

            for name, module in self.modules.items():
                status['modules'][name] = {
                    'type': module.type,
                    'status': module.status,
                    'performance_score': module.performance_score,
                    'last_used': module.last_used.isoformat()
                }

            return status

        except Exception as e:
            self.logger.error(f"システム状態取得エラー: {e}")
            return {}

    async def start_monitoring(self):
        """監視の開始"""
        try:
            self.logger.info("システム監視を開始します")

            # 定期的な監視タスク
            schedule.every(self.config['monitoring']['interval_seconds']).seconds.do(
                lambda: asyncio.create_task(self.monitor_system_performance())
            )

            # 毎日午前2時に最適化
            schedule.every().day.at("02:00").do(
                lambda: asyncio.create_task(self.optimize_system())
            )

            # 毎日午前8時にバックアップ
            schedule.every().day.at("08:00").do(
                lambda: asyncio.create_task(self._backup_system())
            )

            while True:
                schedule.run_pending()
                await asyncio.sleep(1)

        except Exception as e:
            self.logger.error(f"監視エラー: {e}")

    async def _backup_system(self):
        """システムのバックアップ"""
        try:
            import os
            backup_dir = Path("/root/backups/enhanced_ai_system")
            backup_dir.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = backup_dir / f"ai_system_backup_{timestamp}.tar.gz"

            # データベースとログをバックアップ
            os.system(f"tar -czf {backup_file} -C /root integrated_ai_system/ logs/")

            self.logger.info(f"システムバックアップ完了: {backup_file}")

        except Exception as e:
            self.logger.error(f"バックアップエラー: {e}")

    async def run(self):
        """システムの実行"""
        try:
            self.logger.info("拡張AI統合システムを開始します")

            # 初期化
            await self.initialize_system()

            # 監視開始
            await self.start_monitoring()

        except Exception as e:
            self.logger.error(f"システム実行エラー: {e}")

    async def initialize_system(self):
        """システムの初期化"""
        try:
            # 既存モジュールの読み込み
            self.load_existing_modules()

            # 初期パフォーマンスチェック
            await self.monitor_system_performance()

            self.logger.info("システム初期化完了")

        except Exception as e:
            self.logger.error(f"システム初期化エラー: {e}")

def main():
    """メイン関数"""
    import os

    # 必要なディレクトリを作成
    os.makedirs("/root/logs", exist_ok=True)
    os.makedirs("/root/backups/enhanced_ai_system", exist_ok=True)

    # システム開始
    system = EnhancedAISystem()
    asyncio.run(system.run())

if __name__ == "__main__":
    main()
