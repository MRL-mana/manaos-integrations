#!/usr/bin/env python3
"""
Phase 9: AI予測による自動最適化システム
- 自己学習システムの強化
- パフォーマンス自動調整
- 予測ベース最適化
- 機械学習による改善
"""

import os
import sys
import json
import time
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import logging
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
import joblib

class Phase9AIOptimizer:
    def __init__(self):
        self.vault_dir = Path("/root/.mana_vault")
        self.tools_dir = Path("/root/trinity_workspace/tools")
        self.config_file = self.vault_dir / "phase9_ai_config.json"
        self.model_file = self.vault_dir / "ai_optimization_model.pkl"
        self.scaler_file = self.vault_dir / "ai_scaler.pkl"
        
        # ログ設定
        self.setup_logging()
        
        # 設定読み込み
        self.config = self.load_config()
        
        # AIモデル
        self.model = None
        self.scaler = StandardScaler()
        self.training_data = []
        self.prediction_history = []
        
        # 学習パラメータ
        self.learning_enabled = True
        self.prediction_accuracy = 0.0

    def setup_logging(self):
        """ログ設定"""
        log_file = self.vault_dir / "phase9_ai_optimizer.log"
        logging.basicConfig(
            filename=log_file,
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
        # コンソール出力も追加
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(message)s')
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

    def load_config(self):
        """設定ファイル読み込み"""
        default_config = {
            "ai_optimization": {
                "enabled": True,
                "learning_rate": 0.01,
                "prediction_window_hours": 24,
                "retraining_interval_hours": 168,  # 1週間
                "min_training_samples": 100
            },
            "prediction": {
                "cpu_threshold": 80.0,
                "memory_threshold": 85.0,
                "response_time_threshold": 2.0,
                "confidence_threshold": 0.7
            },
            "optimization": {
                "auto_adjust": True,
                "aggressive_mode": False,
                "safety_margin": 0.1
            }
        }
        
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                # デフォルト設定とマージ
                for key, value in default_config.items():
                    if key not in config:
                        config[key] = value
                return config
            except Exception as e:
                self.logger.error(f"設定ファイル読み込みエラー: {e}")
                return default_config
        else:
            self.save_config(default_config)
            return default_config

    def save_config(self, config=None):
        """設定ファイル保存"""
        if config is None:
            config = self.config
        
        try:
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            self.logger.info("AI設定ファイルを保存しました")
        except Exception as e:
            self.logger.error(f"設定ファイル保存エラー: {e}")

    def load_training_data(self):
        """学習データ読み込み"""
        try:
            # パフォーマンス履歴から学習データを構築
            performance_files = list(self.vault_dir.glob("performance_report_*.json"))
            
            training_data = []
            for file_path in sorted(performance_files)[-1000:]:  # 最新1000件
                try:
                    with open(file_path, 'r') as f:
                        data = json.load(f)
                    
                    if 'metrics' in data:
                        metrics = data['metrics']
                        features = self.extract_features(metrics)
                        target = self.calculate_target_value(metrics)
                        
                        training_data.append({
                            'features': features,
                            'target': target,
                            'timestamp': data.get('timestamp', ''),
                            'metrics': metrics
                        })
                        
                except Exception as e:
                    self.logger.warning(f"学習データ読み込みエラー {file_path}: {e}")
                    continue
            
            self.training_data = training_data
            self.logger.info(f"学習データ読み込み完了: {len(training_data)}件")
            return True
            
        except Exception as e:
            self.logger.error(f"学習データ読み込みエラー: {e}")
            return False

    def extract_features(self, metrics):
        """特徴量抽出"""
        try:
            features = [
                metrics.get('cpu_percent', 0),
                metrics.get('memory_percent', 0),
                metrics.get('disk_percent', 0),
                metrics.get('process_count', 0),
                metrics.get('load_avg_1min', 0),
                metrics.get('load_avg_5min', 0),
                metrics.get('load_avg_15min', 0),
                metrics.get('response_time_ms', 0),
                metrics.get('memory_available_gb', 0)
            ]
            
            # 時間特徴量
            timestamp = metrics.get('timestamp', '')
            if timestamp:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                features.extend([
                    dt.hour,
                    dt.weekday(),
                    dt.day,
                    dt.month
                ])
            else:
                features.extend([0, 0, 0, 0])
            
            return np.array(features, dtype=np.float32)
            
        except Exception as e:
            self.logger.error(f"特徴量抽出エラー: {e}")
            return np.zeros(13, dtype=np.float32)

    def calculate_target_value(self, metrics):
        """ターゲット値計算（最適化が必要かどうか）"""
        try:
            score = 0
            
            # CPU使用率が閾値を超えている場合
            if metrics.get('cpu_percent', 0) > self.config['prediction']['cpu_threshold']:
                score += 1
            
            # メモリ使用率が閾値を超えている場合
            if metrics.get('memory_percent', 0) > self.config['prediction']['memory_threshold']:
                score += 1
            
            # レスポンス時間が閾値を超えている場合
            if metrics.get('response_time_ms', 0) > self.config['prediction']['response_time_threshold'] * 1000:
                score += 1
            
            return score
            
        except Exception as e:
            self.logger.error(f"ターゲット値計算エラー: {e}")
            return 0

    def train_model(self):
        """AIモデル学習"""
        try:
            if len(self.training_data) < self.config['ai_optimization']['min_training_samples']:
                self.logger.warning(f"学習データ不足: {len(self.training_data)}件")
                return False
            
            self.logger.info("AIモデル学習を開始")
            
            # 特徴量とターゲットを分離
            X = np.array([data['features'] for data in self.training_data])
            y = np.array([data['target'] for data in self.training_data])
            
            # データ正規化
            X_scaled = self.scaler.fit_transform(X)
            
            # モデル学習（Random Forest）
            self.model = RandomForestRegressor(
                n_estimators=100,
                max_depth=10,
                random_state=42,
                n_jobs=-1
            )
            
            self.model.fit(X_scaled, y)
            
            # モデル保存
            joblib.dump(self.model, self.model_file)
            joblib.dump(self.scaler, self.scaler_file)
            
            # 精度評価
            train_score = self.model.score(X_scaled, y)
            self.prediction_accuracy = train_score
            
            self.logger.info(f"AIモデル学習完了: 精度 {train_score:.3f}")
            return True
            
        except Exception as e:
            self.logger.error(f"AIモデル学習エラー: {e}")
            return False

    def load_model(self):
        """保存されたモデル読み込み"""
        try:
            if self.model_file.exists() and self.scaler_file.exists():
                self.model = joblib.load(self.model_file)
                self.scaler = joblib.load(self.scaler_file)
                self.logger.info("AIモデル読み込み完了")
                return True
            else:
                self.logger.warning("AIモデルファイルが見つかりません")
                return False
                
        except Exception as e:
            self.logger.error(f"AIモデル読み込みエラー: {e}")
            return False

    def predict_optimization_need(self, current_metrics):
        """最適化必要性予測"""
        try:
            if not self.model:
                self.logger.warning("AIモデルが読み込まれていません")
                return False, 0.0
            
            # 現在のメトリクスから特徴量抽出
            features = self.extract_features(current_metrics)
            features_scaled = self.scaler.transform([features])
            
            # 予測実行
            prediction = self.model.predict(features_scaled)[0]
            confidence = self.model.predict_proba(features_scaled)[0].max() if hasattr(self.model, 'predict_proba') else 0.5
            
            # 予測結果を履歴に追加
            self.prediction_history.append({
                'timestamp': datetime.now().isoformat(),
                'prediction': prediction,
                'confidence': confidence,
                'metrics': current_metrics
            })
            
            # 履歴保持（最新100件）
            if len(self.prediction_history) > 100:
                self.prediction_history = self.prediction_history[-100:]
            
            # 最適化が必要かどうか判定
            needs_optimization = (
                prediction > 0.5 and 
                confidence > self.config['prediction']['confidence_threshold']
            )
            
            return needs_optimization, confidence
            
        except Exception as e:
            self.logger.error(f"最適化予測エラー: {e}")
            return False, 0.0

    def generate_optimization_plan(self, current_metrics, prediction_confidence):
        """最適化プラン生成"""
        try:
            plan = {
                "timestamp": datetime.now().isoformat(),
                "confidence": prediction_confidence,
                "optimizations": [],
                "priority": "medium"
            }
            
            # CPU最適化判定
            if current_metrics.get('cpu_percent', 0) > 80:
                plan["optimizations"].append({
                    "type": "cpu_optimization",
                    "priority": "high",
                    "actions": [
                        "プロセス優先度調整",
                        "CPU周波数最適化",
                        "不要プロセス終了"
                    ]
                })
            
            # メモリ最適化判定
            if current_metrics.get('memory_percent', 0) > 85:
                plan["optimizations"].append({
                    "type": "memory_optimization",
                    "priority": "high",
                    "actions": [
                        "ガベージコレクション実行",
                        "メモリキャッシュクリア",
                        "不要プロセス終了"
                    ]
                })
            
            # レスポンス時間最適化判定
            if current_metrics.get('response_time_ms', 0) > 2000:
                plan["optimizations"].append({
                    "type": "response_optimization",
                    "priority": "medium",
                    "actions": [
                        "ネットワーク最適化",
                        "TCP設定調整",
                        "バッファサイズ最適化"
                    ]
                })
            
            # 優先度設定
            if any(opt["priority"] == "high" for opt in plan["optimizations"]):
                plan["priority"] = "high"
            elif len(plan["optimizations"]) > 2:
                plan["priority"] = "medium"
            else:
                plan["priority"] = "low"
            
            return plan
            
        except Exception as e:
            self.logger.error(f"最適化プラン生成エラー: {e}")
            return None

    def execute_optimization_plan(self, plan):
        """最適化プラン実行"""
        try:
            if not plan or not plan.get('optimizations'):
                return False
            
            self.logger.info(f"最適化プラン実行開始: {plan['priority']}優先度")
            
            executed_optimizations = []
            
            for optimization in plan['optimizations']:
                try:
                    if optimization['type'] == 'cpu_optimization':
                        result = self.execute_cpu_optimization(optimization['actions'])
                    elif optimization['type'] == 'memory_optimization':
                        result = self.execute_memory_optimization(optimization['actions'])
                    elif optimization['type'] == 'response_optimization':
                        result = self.execute_response_optimization(optimization['actions'])
                    else:
                        result = False
                    
                    executed_optimizations.append({
                        'type': optimization['type'],
                        'success': result,
                        'actions': optimization['actions']
                    })
                    
                except Exception as e:
                    self.logger.error(f"最適化実行エラー {optimization['type']}: {e}")
                    executed_optimizations.append({
                        'type': optimization['type'],
                        'success': False,
                        'error': str(e)
                    })
            
            # 実行結果レポート
            success_count = sum(1 for opt in executed_optimizations if opt['success'])
            total_count = len(executed_optimizations)
            
            self.logger.info(f"最適化実行完了: {success_count}/{total_count}成功")
            
            return success_count > 0
            
        except Exception as e:
            self.logger.error(f"最適化プラン実行エラー: {e}")
            return False

    def execute_cpu_optimization(self, actions):
        """CPU最適化実行"""
        try:
            # プロセス優先度調整
            if "プロセス優先度調整" in actions:
                self.adjust_process_priorities()
            
            # CPU周波数最適化
            if "CPU周波数最適化" in actions:
                self.optimize_cpu_frequency()
            
            # 不要プロセス終了
            if "不要プロセス終了" in actions:
                self.terminate_unnecessary_processes()
            
            return True
            
        except Exception as e:
            self.logger.error(f"CPU最適化実行エラー: {e}")
            return False

    def execute_memory_optimization(self, actions):
        """メモリ最適化実行"""
        try:
            import gc
            
            # ガベージコレクション実行
            if "ガベージコレクション実行" in actions:
                collected = gc.collect()
                self.logger.info(f"ガベージコレクション: {collected}オブジェクト回収")
            
            # メモリキャッシュクリア
            if "メモリキャッシュクリア" in actions:
                self.clear_memory_caches()
            
            # 不要プロセス終了
            if "不要プロセス終了" in actions:
                self.terminate_unnecessary_processes()
            
            return True
            
        except Exception as e:
            self.logger.error(f"メモリ最適化実行エラー: {e}")
            return False

    def execute_response_optimization(self, actions):
        """レスポンス最適化実行"""
        try:
            # ネットワーク最適化
            if "ネットワーク最適化" in actions:
                self.optimize_network_settings()
            
            # TCP設定調整
            if "TCP設定調整" in actions:
                self.optimize_tcp_settings()
            
            # バッファサイズ最適化
            if "バッファサイズ最適化" in actions:
                self.optimize_buffer_sizes()
            
            return True
            
        except Exception as e:
            self.logger.error(f"レスポンス最適化実行エラー: {e}")
            return False

    def adjust_process_priorities(self):
        """プロセス優先度調整"""
        try:
            import psutil
            
            for proc in psutil.process_iter(['pid', 'name', 'nice']):
                try:
                    if proc.info['name'] in ['chrome', 'firefox', 'thunderbird']:
                        proc.nice(19)  # 最低優先度
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
                    
        except Exception as e:
            self.logger.error(f"プロセス優先度調整エラー: {e}")

    def optimize_cpu_frequency(self):
        """CPU周波数最適化"""
        try:
            import psutil
            
            cpu_count = psutil.cpu_count()
            for i in range(cpu_count):
                governor_file = f'/sys/devices/system/cpu/cpu{i}/cpufreq/scaling_governor'
                if os.path.exists(governor_file):
                    with open(governor_file, 'w') as f:
                        f.write('ondemand')
            
        except Exception as e:
            self.logger.error(f"CPU周波数最適化エラー: {e}")

    def terminate_unnecessary_processes(self):
        """不要プロセス終了"""
        try:
            import psutil
            
            for proc in psutil.process_iter(['pid', 'name', 'status']):
                try:
                    if proc.info['status'] in ['zombie', 'defunct']:
                        proc.terminate()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
                    
        except Exception as e:
            self.logger.error(f"不要プロセス終了エラー: {e}")

    def clear_memory_caches(self):
        """メモリキャッシュクリア"""
        try:
            import subprocess
            
            subprocess.run(['sync'], check=True)
            subprocess.run(['echo', '3'], stdout=open('/proc/sys/vm/drop_caches', 'w'), check=True)
            
        except Exception as e:
            self.logger.error(f"メモリキャッシュクリアエラー: {e}")

    def optimize_network_settings(self):
        """ネットワーク設定最適化"""
        try:
            network_settings = {
                '/proc/sys/net/core/rmem_max': '16777216',
                '/proc/sys/net/core/wmem_max': '16777216'
            }
            
            for setting, value in network_settings.items():
                if os.path.exists(setting):
                    with open(setting, 'w') as f:
                        f.write(value)
            
        except Exception as e:
            self.logger.error(f"ネットワーク設定最適化エラー: {e}")

    def optimize_tcp_settings(self):
        """TCP設定最適化"""
        try:
            tcp_settings = {
                '/proc/sys/net/ipv4/tcp_rmem': '4096 65536 16777216',
                '/proc/sys/net/ipv4/tcp_wmem': '4096 65536 16777216'
            }
            
            for setting, value in tcp_settings.items():
                if os.path.exists(setting):
                    with open(setting, 'w') as f:
                        f.write(value)
            
        except Exception as e:
            self.logger.error(f"TCP設定最適化エラー: {e}")

    def optimize_buffer_sizes(self):
        """バッファサイズ最適化"""
        try:
            buffer_settings = {
                '/proc/sys/net/core/netdev_max_backlog': '5000',
                '/proc/sys/net/core/netdev_budget': '600'
            }
            
            for setting, value in buffer_settings.items():
                if os.path.exists(setting):
                    with open(setting, 'w') as f:
                        f.write(value)
            
        except Exception as e:
            self.logger.error(f"バッファサイズ最適化エラー: {e}")

    def run_ai_optimization_cycle(self, current_metrics):
        """AI最適化サイクル実行"""
        try:
            self.logger.info("=== Phase 9: AI最適化サイクル開始 ===")
            
            # 学習データ読み込み
            if self.learning_enabled:
                self.load_training_data()
                
                # 十分なデータがある場合は再学習
                if len(self.training_data) >= self.config['ai_optimization']['min_training_samples']:
                    self.train_model()
            
            # モデル読み込み
            if not self.model:
                self.load_model()
            
            # 最適化必要性予測
            needs_optimization, confidence = self.predict_optimization_need(current_metrics)
            
            if needs_optimization and confidence > self.config['prediction']['confidence_threshold']:
                self.logger.info(f"最適化が必要と予測: 信頼度 {confidence:.3f}")
                
                # 最適化プラン生成
                plan = self.generate_optimization_plan(current_metrics, confidence)
                
                if plan:
                    # 最適化実行
                    success = self.execute_optimization_plan(plan)
                    
                    if success:
                        self.logger.info("AI最適化実行成功")
                    else:
                        self.logger.warning("AI最適化実行失敗")
                else:
                    self.logger.warning("最適化プラン生成失敗")
            else:
                self.logger.info("最適化は不要と予測")
            
            self.logger.info("=== Phase 9: AI最適化サイクル完了 ===")
            return True
            
        except Exception as e:
            self.logger.error(f"AI最適化サイクルエラー: {e}")
            return False

if __name__ == "__main__":
    ai_optimizer = Phase9AIOptimizer()
    
    # テスト用のメトリクス
    test_metrics = {
        'cpu_percent': 75.0,
        'memory_percent': 80.0,
        'disk_percent': 60.0,
        'process_count': 200,
        'load_avg_1min': 2.5,
        'load_avg_5min': 2.0,
        'load_avg_15min': 1.8,
        'response_time_ms': 1500.0,
        'memory_available_gb': 2.0,
        'timestamp': datetime.now().isoformat()
    }
    
    ai_optimizer.run_ai_optimization_cycle(test_metrics)
