#!/usr/bin/env python3
"""
🧠 AI Learning Predictive System
学習・予測・最適化の循環システム

統合システム:
- AI Learning System (パターン学習・知識蓄積)
- Predictive Analytics (予測分析・トレンド予測)
- Auto-Scaling (自動スケーリング・最適化)
"""

import os
import asyncio
import json
import logging
import time
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
import sqlite3
import threading
from dataclasses import dataclass, asdict
from enum import Enum
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from flask import Flask, jsonify, request
from flask_cors import CORS
import websockets

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/root/logs/ai_learning_predictive.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class LearningMode(Enum):
    SUPERVISED = "supervised"
    UNSUPERVISED = "unsupervised"
    REINFORCEMENT = "reinforcement"
    CONTINUOUS = "continuous"

class PredictionType(Enum):
    PERFORMANCE = "performance"
    RESOURCE_USAGE = "resource_usage"
    USER_BEHAVIOR = "user_behavior"
    SYSTEM_LOAD = "system_load"
    ERROR_RATE = "error_rate"

@dataclass
class LearningData:
    timestamp: datetime
    feature_vector: List[float]
    target_value: Optional[float]
    context: Dict[str, Any]
    source: str

@dataclass
class Prediction:
    prediction_type: PredictionType
    predicted_value: float
    confidence: float
    time_horizon: int  # 秒
    features_used: List[str]
    model_version: str
    timestamp: datetime

@dataclass
class ScalingDecision:
    action: str  # "scale_up", "scale_down", "maintain"
    target_resources: Dict[str, float]
    confidence: float
    reasoning: str
    expected_improvement: float
    timestamp: datetime

class AILearningPredictiveSystem:
    """AI学習・予測・最適化システム"""
    
    def __init__(self):
        self.system_name = "AI Learning Predictive System"
        self.version = "1.0.0"
        self.port = 9003
        
        # 学習データストア
        self.learning_data: List[LearningData] = []
        self.models: Dict[str, Any] = {}
        self.scalers: Dict[str, StandardScaler] = {}
        
        # 予測履歴
        self.predictions: List[Prediction] = []
        self.scaling_decisions: List[ScalingDecision] = []
        
        # システム状態
        self.current_resources = {
            "cpu_usage": 0.0,
            "memory_usage": 0.0,
            "disk_usage": 0.0,
            "network_io": 0.0,
            "active_connections": 0
        }
        
        # パフォーマンス指標
        self.performance_metrics = {
            "response_time": [],
            "throughput": [],
            "error_rate": [],
            "user_satisfaction": []
        }
        
        # データベース初期化
        self.init_database()
        
        # WebSocket接続
        self.websocket_clients = set()
        
        # Flask アプリケーション
        self.app = Flask(__name__)
        CORS(self.app)
        self.setup_routes()
        
        # 学習ループ開始
        self.learning_active = True
        
        logger.info(f"🧠 {self.system_name} v{self.version} 初期化完了")

    def init_database(self):
        """データベース初期化"""
        try:
            conn = sqlite3.connect('/root/ai_learning_predictive.db')
            cursor = conn.cursor()
            
            # 学習データテーブル
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS learning_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP,
                    feature_vector TEXT,
                    target_value REAL,
                    context TEXT,
                    source TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 予測履歴テーブル
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS predictions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    prediction_type TEXT,
                    predicted_value REAL,
                    confidence REAL,
                    time_horizon INTEGER,
                    features_used TEXT,
                    model_version TEXT,
                    timestamp TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # スケーリング決定テーブル
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS scaling_decisions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    action TEXT,
                    target_resources TEXT,
                    confidence REAL,
                    reasoning TEXT,
                    expected_improvement REAL,
                    timestamp TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # パフォーマンス指標テーブル
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS performance_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    metric_name TEXT,
                    metric_value REAL,
                    timestamp TIMESTAMP,
                    context TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
            conn.close()
            logger.info("✅ データベース初期化完了")
            
        except Exception as e:
            logger.error(f"❌ データベース初期化エラー: {e}")

    def setup_routes(self):
        """Flask ルート設定"""
        
        @self.app.route('/api/status', methods=['GET'])
        def get_system_status():
            """システム状態取得"""
            return jsonify({
                "system_name": self.system_name,
                "version": self.version,
                "status": "operational",
                "learning_active": self.learning_active,
                "data_points": len(self.learning_data),
                "models_trained": len(self.models),
                "predictions_made": len(self.predictions),
                "scaling_decisions": len(self.scaling_decisions),
                "current_resources": self.current_resources,
                "timestamp": datetime.now().isoformat()
            })
        
        @self.app.route('/api/learning/data', methods=['POST'])
        def add_learning_data():
            """学習データ追加"""
            try:
                data = request.get_json()
                
                learning_data = LearningData(
                    timestamp=datetime.now(),
                    feature_vector=data.get('features', []),
                    target_value=data.get('target'),
                    context=data.get('context', {}),
                    source=data.get('source', 'api')
                )
                
                self.learning_data.append(learning_data)
                self.save_learning_data_to_db(learning_data)
                
                return jsonify({
                    "message": "学習データを追加しました",
                    "data_id": len(self.learning_data),
                    "timestamp": datetime.now().isoformat()
                })
                
            except Exception as e:
                logger.error(f"学習データ追加エラー: {e}")
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/api/predictions', methods=['GET'])
        def get_predictions():
            """予測履歴取得"""
            return jsonify({
                "predictions": [
                    {
                        "type": p.prediction_type.value,
                        "value": p.predicted_value,
                        "confidence": p.confidence,
                        "time_horizon": p.time_horizon,
                        "timestamp": p.timestamp.isoformat()
                    }
                    for p in self.predictions[-50:]  # 最新50件
                ],
                "total_predictions": len(self.predictions)
            })
        
        @self.app.route('/api/predict', methods=['POST'])
        def make_prediction():
            """予測実行"""
            try:
                data = request.get_json()
                prediction_type = PredictionType(data.get('type', 'performance'))
                
                # 非同期で予測実行
                asyncio.create_task(self.execute_prediction(prediction_type))
                
                return jsonify({
                    "message": "予測を開始しました",
                    "type": prediction_type.value,
                    "timestamp": datetime.now().isoformat()
                })
                
            except Exception as e:
                logger.error(f"予測実行エラー: {e}")
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/api/scaling/recommend', methods=['GET'])
        def get_scaling_recommendation():
            """スケーリング推奨取得"""
            try:
                recommendation = self.generate_scaling_recommendation()
                return jsonify({
                    "recommendation": asdict(recommendation),
                    "timestamp": datetime.now().isoformat()
                })
                
            except Exception as e:
                logger.error(f"スケーリング推奨エラー: {e}")
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/api/learning/train', methods=['POST'])
        def trigger_learning():
            """学習実行"""
            try:
                asyncio.create_task(self.execute_learning_cycle())
                return jsonify({
                    "message": "学習サイクルを開始しました",
                    "timestamp": datetime.now().isoformat()
                })
                
            except Exception as e:
                logger.error(f"学習実行エラー: {e}")
                return jsonify({"error": str(e)}), 500

    def save_learning_data_to_db(self, data: LearningData):
        """学習データをデータベースに保存"""
        try:
            conn = sqlite3.connect('/root/ai_learning_predictive.db')
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO learning_data 
                (timestamp, feature_vector, target_value, context, source)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                data.timestamp,
                json.dumps(data.feature_vector),
                data.target_value,
                json.dumps(data.context),
                data.source
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"学習データ保存エラー: {e}")

    async def execute_learning_cycle(self):
        """学習サイクル実行"""
        try:
            logger.info("🧠 学習サイクル開始")
            
            # 1. データ収集・前処理
            processed_data = self.preprocess_learning_data()
            
            if len(processed_data) < 10:
                logger.warning("⚠️ 学習データが不足しています（10件未満）")
                return
            
            # 2. モデル学習
            await self.train_models(processed_data)
            
            # 3. モデル評価
            evaluation_results = await self.evaluate_models()
            
            # 4. 学習結果をWebSocketで配信
            await self.broadcast_result({
                "type": "learning_completed",
                "data_points": len(processed_data),
                "models_trained": len(self.models),
                "evaluation_results": evaluation_results,
                "timestamp": datetime.now().isoformat()
            })
            
            logger.info("✅ 学習サイクル完了")
            
        except Exception as e:
            logger.error(f"❌ 学習サイクルエラー: {e}")

    def preprocess_learning_data(self) -> List[Tuple[List[float], Optional[float]]]:
        """学習データの前処理"""
        processed = []
        
        for data in self.learning_data:
            if len(data.feature_vector) > 0:
                # 特徴量の正規化
                normalized_features = self.normalize_features(data.feature_vector)
                processed.append((normalized_features, data.target_value))
        
        return processed

    def normalize_features(self, features: List[float]) -> List[float]:
        """特徴量の正規化"""
        if len(features) == 0:
            return features
        
        # 簡単なMin-Max正規化
        min_val = min(features)
        max_val = max(features)
        
        if max_val == min_val:
            return [0.5] * len(features)
        
        return [(x - min_val) / (max_val - min_val) for x in features]

    async def train_models(self, processed_data: List[Tuple[List[float], Optional[float]]]):
        """モデル学習"""
        try:
            # 特徴量とターゲットを分離
            X = [data[0] for data in processed_data if data[1] is not None]
            y = [data[1] for data in processed_data if data[1] is not None]
            
            if len(X) < 5:
                logger.warning("⚠️ 教師あり学習データが不足しています")
                return
            
            # データをnumpy配列に変換
            X = np.array(X)
            y = np.array(y)
            
            # 特徴量の標準化
            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(X)
            
            # 訓練・テストデータ分割
            X_train, X_test, y_train, y_test = train_test_split(
                X_scaled, y, test_size=0.2, random_state=42
            )
            
            # ランダムフォレストモデルの学習
            model = RandomForestRegressor(
                n_estimators=100,
                random_state=42,
                max_depth=10
            )
            
            model.fit(X_train, y_train)
            
            # モデルとスケーラーを保存
            model_id = f"performance_model_{int(time.time())}"
            self.models[model_id] = model
            self.scalers[model_id] = scaler
            
            logger.info(f"✅ モデル学習完了: {model_id}")
            
            # テスト精度を計算
            test_score = model.score(X_test, y_test)
            logger.info(f"📊 テストスコア: {test_score:.3f}")
            
        except Exception as e:
            logger.error(f"❌ モデル学習エラー: {e}")

    async def evaluate_models(self) -> Dict[str, Any]:
        """モデル評価"""
        evaluation_results = {}
        
        for model_id, model in self.models.items():
            try:
                # 簡単な評価指標を計算
                evaluation_results[model_id] = {
                    "feature_importance": model.feature_importances_.tolist() if hasattr(model, 'feature_importances_') else [],
                    "n_estimators": model.n_estimators if hasattr(model, 'n_estimators') else 0,
                    "model_type": type(model).__name__
                }
                
            except Exception as e:
                logger.error(f"モデル評価エラー {model_id}: {e}")
        
        return evaluation_results

    async def execute_prediction(self, prediction_type: PredictionType):
        """予測実行"""
        try:
            logger.info(f"🔮 予測実行開始: {prediction_type.value}")
            
            # 現在のシステム状態から特徴量を生成
            current_features = self.generate_current_features()
            
            if not current_features:
                logger.warning("⚠️ 特徴量生成に失敗しました")
                return
            
            # 最も新しいモデルを選択
            if not self.models:
                logger.warning("⚠️ 学習済みモデルがありません")
                return
            
            latest_model_id = max(self.models.keys())
            model = self.models[latest_model_id]
            scaler = self.scalers.get(latest_model_id)
            
            # 特徴量を正規化
            if scaler:
                features_scaled = scaler.transform([current_features])
            else:
                features_scaled = [current_features]
            
            # 予測実行
            predicted_value = model.predict(features_scaled)[0]
            
            # 信頼度を計算（簡易版）
            confidence = min(0.95, max(0.1, abs(predicted_value) / 100))
            
            # 予測結果を作成
            prediction = Prediction(
                prediction_type=prediction_type,
                predicted_value=float(predicted_value),
                confidence=confidence,
                time_horizon=300,  # 5分後
                features_used=[f"feature_{i}" for i in range(len(current_features))],
                model_version=latest_model_id,
                timestamp=datetime.now()
            )
            
            self.predictions.append(prediction)
            self.save_prediction_to_db(prediction)
            
            # 予測結果をWebSocketで配信
            await self.broadcast_result({
                "type": "prediction_completed",
                "prediction": asdict(prediction),
                "timestamp": datetime.now().isoformat()
            })
            
            logger.info(f"✅ 予測完了: {predicted_value:.3f} (信頼度: {confidence:.3f})")
            
        except Exception as e:
            logger.error(f"❌ 予測実行エラー: {e}")

    def generate_current_features(self) -> List[float]:
        """現在のシステム状態から特徴量を生成"""
        try:
            features = [
                self.current_resources["cpu_usage"],
                self.current_resources["memory_usage"],
                self.current_resources["disk_usage"],
                self.current_resources["network_io"],
                self.current_resources["active_connections"],
                len(self.learning_data) / 1000.0,  # データ量
                len(self.predictions) / 100.0,     # 予測回数
                time.time() % (24 * 3600) / (24 * 3600)  # 時間特徴
            ]
            
            return features
            
        except Exception as e:
            logger.error(f"特徴量生成エラー: {e}")
            return []

    def generate_scaling_recommendation(self) -> ScalingDecision:
        """スケーリング推奨生成"""
        try:
            # 現在のリソース使用率を分析
            cpu_usage = self.current_resources["cpu_usage"]
            memory_usage = self.current_resources["memory_usage"]
            
            # 最近の予測を確認
            recent_predictions = [
                p for p in self.predictions 
                if (datetime.now() - p.timestamp).total_seconds() < 3600
            ]
            
            # スケーリング決定ロジック
            if cpu_usage > 0.8 or memory_usage > 0.8:
                action = "scale_up"
                target_resources = {
                    "cpu_limit": min(2.0, cpu_usage * 1.5),
                    "memory_limit": min(8.0, memory_usage * 1.5)
                }
                confidence = 0.8
                reasoning = "高リソース使用率のためスケールアップを推奨"
                expected_improvement = 0.3
                
            elif cpu_usage < 0.3 and memory_usage < 0.3:
                action = "scale_down"
                target_resources = {
                    "cpu_limit": max(0.5, cpu_usage * 0.8),
                    "memory_limit": max(1.0, memory_usage * 0.8)
                }
                confidence = 0.7
                reasoning = "低リソース使用率のためスケールダウンを推奨"
                expected_improvement = 0.2
                
            else:
                action = "maintain"
                target_resources = self.current_resources.copy()
                confidence = 0.9
                reasoning = "現在のリソース使用率が適切"
                expected_improvement = 0.0
            
            # 予測結果を考慮
            if recent_predictions:
                avg_predicted_usage = np.mean([p.predicted_value for p in recent_predictions])
                if avg_predicted_usage > 0.7 and action == "maintain":
                    action = "scale_up"
                    confidence = 0.75
                    reasoning += " (予測値に基づく調整)"
            
            decision = ScalingDecision(
                action=action,
                target_resources=target_resources,
                confidence=confidence,
                reasoning=reasoning,
                expected_improvement=expected_improvement,
                timestamp=datetime.now()
            )
            
            self.scaling_decisions.append(decision)
            self.save_scaling_decision_to_db(decision)
            
            return decision
            
        except Exception as e:
            logger.error(f"スケーリング推奨生成エラー: {e}")
            # デフォルトの決定を返す
            return ScalingDecision(
                action="maintain",
                target_resources=self.current_resources.copy(),
                confidence=0.5,
                reasoning="エラーによりデフォルト決定",
                expected_improvement=0.0,
                timestamp=datetime.now()
            )

    def save_prediction_to_db(self, prediction: Prediction):
        """予測結果をデータベースに保存"""
        try:
            conn = sqlite3.connect('/root/ai_learning_predictive.db')
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO predictions 
                (prediction_type, predicted_value, confidence, time_horizon, features_used, model_version, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                prediction.prediction_type.value,
                prediction.predicted_value,
                prediction.confidence,
                prediction.time_horizon,
                json.dumps(prediction.features_used),
                prediction.model_version,
                prediction.timestamp
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"予測結果保存エラー: {e}")

    def save_scaling_decision_to_db(self, decision: ScalingDecision):
        """スケーリング決定をデータベースに保存"""
        try:
            conn = sqlite3.connect('/root/ai_learning_predictive.db')
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO scaling_decisions 
                (action, target_resources, confidence, reasoning, expected_improvement, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                decision.action,
                json.dumps(decision.target_resources),
                decision.confidence,
                decision.reasoning,
                decision.expected_improvement,
                decision.timestamp
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"スケーリング決定保存エラー: {e}")

    async def update_system_metrics(self):
        """システム指標の更新"""
        try:
            # 模擬的なシステム指標更新
            current_time = time.time()
            
            # CPU使用率（正弦波 + ノイズ）
            self.current_resources["cpu_usage"] = max(0, min(1, 
                0.5 + 0.3 * np.sin(current_time / 100) + np.random.normal(0, 0.1)
            ))
            
            # メモリ使用率
            self.current_resources["memory_usage"] = max(0, min(1,
                0.4 + 0.2 * np.sin(current_time / 150) + np.random.normal(0, 0.05)
            ))
            
            # ディスク使用率
            self.current_resources["disk_usage"] = max(0, min(1,
                0.3 + 0.1 * np.sin(current_time / 200)
            ))
            
            # ネットワークI/O
            self.current_resources["network_io"] = max(0,
                abs(np.sin(current_time / 50)) * 100 + np.random.normal(0, 10)
            )
            
            # アクティブ接続数
            self.current_resources["active_connections"] = max(0, int(
                10 + 5 * np.sin(current_time / 80) + np.random.normal(0, 2)
            ))
            
            # パフォーマンス指標を更新
            response_time = 100 + 50 * np.sin(current_time / 120) + np.random.normal(0, 10)
            self.performance_metrics["response_time"].append(response_time)
            
            # 古いデータを削除（最新1000件を保持）
            for metric in self.performance_metrics.values():
                if len(metric) > 1000:
                    metric.pop(0)
            
        except Exception as e:
            logger.error(f"システム指標更新エラー: {e}")

    async def continuous_learning_loop(self):
        """継続学習ループ"""
        while self.learning_active:
            try:
                # システム指標更新
                await self.update_system_metrics()
                
                # 学習データを自動生成
                if len(self.learning_data) < 1000:  # データが少ない場合は自動生成
                    await self.generate_synthetic_learning_data()
                
                # 定期的に学習実行
                if len(self.learning_data) % 100 == 0 and len(self.learning_data) > 0:
                    await self.execute_learning_cycle()
                
                # 定期的に予測実行
                if len(self.predictions) % 10 == 0:
                    await self.execute_prediction(PredictionType.PERFORMANCE)
                
                await asyncio.sleep(30)  # 30秒間隔
                
            except Exception as e:
                logger.error(f"継続学習ループエラー: {e}")
                await asyncio.sleep(10)

    async def generate_synthetic_learning_data(self):
        """合成学習データ生成"""
        try:
            current_time = time.time()
            
            # 模擬的な特徴量生成
            features = [
                np.random.uniform(0, 1),  # CPU使用率
                np.random.uniform(0, 1),  # メモリ使用率
                np.random.uniform(0, 1),  # ディスク使用率
                np.random.uniform(0, 100),  # ネットワークI/O
                np.random.uniform(0, 20),   # アクティブ接続数
                current_time % (24 * 3600) / (24 * 3600),  # 時間特徴
                len(self.learning_data) / 1000.0  # データ量特徴
            ]
            
            # ターゲット値（パフォーマンス指標）を生成
            target = 100 + 50 * np.sin(current_time / 100) + np.random.normal(0, 10)
            
            learning_data = LearningData(
                timestamp=datetime.now(),
                feature_vector=features,
                target_value=target,
                context={"source": "synthetic", "generation_time": current_time},
                source="synthetic_generator"
            )
            
            self.learning_data.append(learning_data)
            self.save_learning_data_to_db(learning_data)
            
        except Exception as e:
            logger.error(f"合成学習データ生成エラー: {e}")

    async def broadcast_result(self, data: Dict[str, Any]):
        """WebSocketで結果をブロードキャスト"""
        if self.websocket_clients:
            message = json.dumps(data, ensure_ascii=False, default=str)
            disconnected = set()
            
            for client in self.websocket_clients:
                try:
                    await client.send(message)
                except websockets.exceptions.ConnectionClosed:
                    disconnected.add(client)
                except Exception as e:
                    logger.error(f"WebSocket送信エラー: {e}")
                    disconnected.add(client)
            
            # 切断されたクライアントを削除
            self.websocket_clients -= disconnected

    async def websocket_handler(self, websocket, path):
        """WebSocket接続ハンドラー"""
        self.websocket_clients.add(websocket)
        logger.info(f"🔌 WebSocket接続追加: {len(self.websocket_clients)} clients")
        
        try:
            await websocket.wait_closed()
        finally:
            self.websocket_clients.remove(websocket)
            logger.info(f"🔌 WebSocket接続削除: {len(self.websocket_clients)} clients")

    def run(self):
        """システム起動"""
        logger.info(f"🧠 {self.system_name} 起動中...")
        
        # Flaskアプリを別スレッドで実行
        flask_thread = threading.Thread(
            target=lambda: self.app.run(host='0.0.0.0', port=self.port, debug=os.getenv("DEBUG", "False").lower() == "true")
        )
        flask_thread.daemon = True
        flask_thread.start()
        
        logger.info(f"✅ {self.system_name} 起動完了!")
        logger.info(f"🌐 Web API: http://localhost:{self.port}")
        
        # 非同期タスクを開始
        asyncio.run(self.start_async_tasks())
    
    async def start_async_tasks(self):
        """非同期タスク開始"""
        # WebSocketサーバーを開始
        start_server = websockets.serve(self.websocket_handler, "localhost", 9004)  # type: ignore[misc]
        
        # 継続学習ループを開始
        learning_task = asyncio.create_task(self.continuous_learning_loop())
        
        try:
            # WebSocketサーバーを開始
            await start_server
            
            logger.info("🔌 WebSocket: ws://localhost:9004")
            
            # 継続学習ループを待機
            await learning_task
            
        except KeyboardInterrupt:
            logger.info("🛑 システム停止中...")
            self.learning_active = False
        except Exception as e:
            logger.error(f"❌ 非同期タスクエラー: {e}")

if __name__ == "__main__":
    system = AILearningPredictiveSystem()
    system.run()
