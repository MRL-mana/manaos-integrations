#!/usr/bin/env python3
"""
🤖 AI予測メンテナンスシステム - 故障予測とメンテナンス推奨
既存のpredictive_maintenance.pyを拡張し、LLM統合と高度な予測機能を追加
"""

import json
import os
import time
import psutil
from manaos_logger import get_logger, get_service_logger
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from pathlib import Path
from collections import deque
from dataclasses import dataclass, asdict

from _paths import LLM_ROUTING_PORT, OLLAMA_PORT

# 既存の予測メンテナンスシステムをインポート
try:
    from predictive_maintenance import PredictiveMaintenance
    PREDICTIVE_MAINTENANCE_AVAILABLE = True
except ImportError:
    PREDICTIVE_MAINTENANCE_AVAILABLE = False

# LLM統合（ManaOSのLLMを使用）
try:
    import httpx
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False

logger = get_service_logger("ai-predictive-maintenance")

DEFAULT_OLLAMA_GENERATE_URL = f"http://127.0.0.1:{OLLAMA_PORT}/api/generate"
DEFAULT_DEVICE_HEALTH_MONITOR_URL = f"http://127.0.0.1:{LLM_ROUTING_PORT}"


@dataclass
class MaintenanceRecommendation:
    """メンテナンス推奨"""
    device_name: str
    recommendation_type: str  # "preventive", "corrective", "optimization"
    priority: str  # "low", "medium", "high", "critical"
    description: str
    predicted_failure_time: Optional[str]
    confidence: float
    actions: List[str]
    estimated_cost: Optional[float]


class AIPredictiveMaintenance:
    """AI予測メンテナンスシステム"""
    
    def __init__(self, config_path: str = "ai_predictive_maintenance_config.json"):
        """
        初期化
        
        Args:
            config_path: 設定ファイルのパス
        """
        self.config_path = Path(config_path)
        self.config = self._load_config()
        
        # 既存の予測メンテナンスシステム
        self.base_system = None
        if PREDICTIVE_MAINTENANCE_AVAILABLE:
            try:
                self.base_system = PredictiveMaintenance()
            except Exception as e:
                logger.warning(f"既存の予測メンテナンスシステムの初期化エラー: {e}")
        
        # LLM設定（環境変数優先）
        ollama_base = os.getenv("OLLAMA_URL")
        if ollama_base:
            self.llm_url = f"{ollama_base.rstrip('/')}/api/generate"
        else:
            self.llm_url = self.config.get("llm_url", DEFAULT_OLLAMA_GENERATE_URL)
        self.llm_model = self.config.get("llm_model", "llama3.2:3b")
        
        # デバイス監視設定（環境変数優先）
        self.device_health_monitor_url = os.getenv(
            "MANAOS_INTEGRATION_API_URL",
            self.config.get("device_health_monitor_url", DEFAULT_DEVICE_HEALTH_MONITOR_URL)
        )
        
        # メンテナンス推奨履歴
        self.recommendations_file = Path(self.config.get("recommendations_file", "maintenance_recommendations.json"))
        self.recommendations: List[MaintenanceRecommendation] = self._load_recommendations()
        
        # 予測履歴
        self.predictions_file = Path(self.config.get("predictions_file", "maintenance_predictions.json"))
        self.predictions_history: List[Dict[str, Any]] = self._load_predictions()
    
    def _load_config(self) -> Dict[str, Any]:
        """設定ファイルを読み込む"""
        if self.config_path.exists():
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            # デフォルト設定を作成
            default_config = {
                "llm_url": DEFAULT_OLLAMA_GENERATE_URL,
                "llm_model": "llama3.2:3b",
                "device_health_monitor_url": DEFAULT_DEVICE_HEALTH_MONITOR_URL,
                "recommendations_file": "maintenance_recommendations.json",
                "predictions_file": "maintenance_predictions.json",
                "prediction_thresholds": {
                    "cpu_warning": 80.0,
                    "cpu_critical": 95.0,
                    "memory_warning": 85.0,
                    "memory_critical": 95.0,
                    "disk_warning": 85.0,
                    "disk_critical": 95.0
                },
                "maintenance_intervals": {
                    "preventive": 30,  # 日
                    "corrective": 7,   # 日
                    "optimization": 14  # 日
                }
            }
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=2, ensure_ascii=False)
            return default_config
    
    def _load_recommendations(self) -> List[MaintenanceRecommendation]:
        """メンテナンス推奨を読み込む"""
        if self.recommendations_file.exists():
            with open(self.recommendations_file, 'r', encoding='utf-8') as f:
                recommendations_data = json.load(f)
                return [MaintenanceRecommendation(**r) for r in recommendations_data]
        return []
    
    def _save_recommendations(self):
        """メンテナンス推奨を保存"""
        recommendations_data = [asdict(r) for r in self.recommendations]
        with open(self.recommendations_file, 'w', encoding='utf-8') as f:
            json.dump(recommendations_data, f, indent=2, ensure_ascii=False)
    
    def _load_predictions(self) -> List[Dict[str, Any]]:
        """予測履歴を読み込む"""
        if self.predictions_file.exists():
            with open(self.predictions_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []
    
    def _save_predictions(self):
        """予測履歴を保存"""
        with open(self.predictions_file, 'w', encoding='utf-8') as f:
            json.dump(self.predictions_history[-100:], f, indent=2, ensure_ascii=False)
    
    def _query_llm(self, prompt: str) -> Optional[str]:
        """LLMにクエリを送信"""
        if not LLM_AVAILABLE:
            return None
        
        try:
            response = httpx.post(
                self.llm_url,
                json={
                    "model": self.llm_model,
                    "prompt": prompt,
                    "stream": False
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("response", "")
        except Exception as e:
            logger.error(f"LLMクエリエラー: {e}")
        
        return None
    
    def _get_device_health_data(self) -> Optional[Dict[str, Any]]:
        """デバイス健康状態データを取得"""
        try:
            response = httpx.get(
                f"{self.device_health_monitor_url}/api/status",
                timeout=10
            )
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.warning(f"デバイス健康状態データ取得エラー: {e}")
        
        return None
    
    def analyze_device_health(self, device_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        デバイス健康状態を分析
        
        Args:
            device_data: デバイスデータ
        
        Returns:
            分析結果
        """
        analysis = {
            "device_name": device_data.get("device_name", "Unknown"),
            "status": device_data.get("status", "unknown"),
            "risks": [],
            "trends": {},
            "predictions": {}
        }
        
        # CPU分析
        cpu_percent = device_data.get("cpu_percent", 0.0)
        if cpu_percent >= self.config["prediction_thresholds"]["cpu_critical"]:
            analysis["risks"].append({
                "type": "cpu",
                "level": "critical",
                "message": f"CPU使用率が危険レベル: {cpu_percent:.1f}%"
            })
        elif cpu_percent >= self.config["prediction_thresholds"]["cpu_warning"]:
            analysis["risks"].append({
                "type": "cpu",
                "level": "warning",
                "message": f"CPU使用率が警告レベル: {cpu_percent:.1f}%"
            })
        
        # メモリ分析
        memory_percent = device_data.get("memory_percent", 0.0)
        if memory_percent >= self.config["prediction_thresholds"]["memory_critical"]:
            analysis["risks"].append({
                "type": "memory",
                "level": "critical",
                "message": f"メモリ使用率が危険レベル: {memory_percent:.1f}%"
            })
        
        # ディスク分析
        disk_percent = device_data.get("disk_percent", 0.0)
        if disk_percent >= self.config["prediction_thresholds"]["disk_critical"]:
            analysis["risks"].append({
                "type": "disk",
                "level": "critical",
                "message": f"ディスク使用率が危険レベル: {disk_percent:.1f}%"
            })
        
        # トレンド分析（既存システムを使用）
        if self.base_system:
            try:
                trends = self.base_system.analyze_trends()
                analysis["trends"] = trends
            except Exception as e:
                logger.warning(f"トレンド分析エラー: {e}")
        
        return analysis
    
    def predict_failure(self, device_data: Dict[str, Any], analysis: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        故障を予測
        
        Args:
            device_data: デバイスデータ
            analysis: 分析結果
        
        Returns:
            予測結果
        """
        # LLMを使用して予測
        prompt = f"""
デバイスの健康状態データを分析して、故障の可能性を予測してください。

デバイス名: {device_data.get('device_name', 'Unknown')}
CPU使用率: {device_data.get('cpu_percent', 0.0)}%
メモリ使用率: {device_data.get('memory_percent', 0.0)}%
ディスク使用率: {device_data.get('disk_percent', 0.0)}%
アップタイム: {device_data.get('uptime_seconds', 0.0)}秒
リスク: {json.dumps(analysis.get('risks', []), ensure_ascii=False)}

以下の形式で回答してください:
- 故障の可能性: 低/中/高/非常に高い
- 予測される故障タイプ: CPU/メモリ/ディスク/ネットワーク/その他
- 予測される故障までの時間: 日数または時間
- 信頼度: 0.0-1.0
- 推奨される対策: 具体的なアクション
"""
        
        llm_response = self._query_llm(prompt)
        
        if llm_response:
            prediction = {
                "device_name": device_data.get("device_name", "Unknown"),
                "timestamp": datetime.now().isoformat(),
                "llm_analysis": llm_response,
                "risks": analysis.get("risks", []),
                "confidence": 0.7  # デフォルト値
            }
            
            self.predictions_history.append(prediction)
            self._save_predictions()
            
            return prediction
        
        return None
    
    def generate_recommendation(self, device_data: Dict[str, Any], analysis: Dict[str, Any], prediction: Optional[Dict[str, Any]]) -> Optional[MaintenanceRecommendation]:
        """
        メンテナンス推奨を生成
        
        Args:
            device_data: デバイスデータ
            analysis: 分析結果
            prediction: 予測結果
        
        Returns:
            メンテナンス推奨
        """
        device_name = device_data.get("device_name", "Unknown")
        risks = analysis.get("risks", [])
        
        if not risks:
            return None
        
        # リスクレベルを判定
        critical_risks = [r for r in risks if r.get("level") == "critical"]
        warning_risks = [r for r in risks if r.get("level") == "warning"]
        
        if critical_risks:
            priority = "critical"
            recommendation_type = "corrective"
        elif warning_risks:
            priority = "high"
            recommendation_type = "preventive"
        else:
            priority = "medium"
            recommendation_type = "optimization"
        
        # LLMを使用して推奨を生成
        prompt = f"""
デバイスのメンテナンス推奨を生成してください。

デバイス名: {device_name}
リスク: {json.dumps(risks, ensure_ascii=False)}
予測: {json.dumps(prediction.get('llm_analysis', '') if prediction else '', ensure_ascii=False)}

以下の形式で回答してください:
- 推奨タイプ: preventive/corrective/optimization
- 優先度: low/medium/high/critical
- 説明: メンテナンスの理由と内容
- 予測される故障時間: 日数または時間（該当する場合）
- 信頼度: 0.0-1.0
- 推奨アクション: 具体的なアクションのリスト
- 推定コスト: 金額（該当する場合）
"""
        
        llm_response = self._query_llm(prompt)
        
        if llm_response:
            # LLMレスポンスをパース（簡易実装）
            actions = []
            if "再起動" in llm_response:
                actions.append("デバイスを再起動")
            if "クリーンアップ" in llm_response or "削除" in llm_response:
                actions.append("不要ファイルを削除")
            if "アップグレード" in llm_response or "更新" in llm_response:
                actions.append("ソフトウェアを更新")
            
            recommendation = MaintenanceRecommendation(
                device_name=device_name,
                recommendation_type=recommendation_type,
                priority=priority,
                description=llm_response[:200],  # 簡易実装
                predicted_failure_time=None,
                confidence=0.7,
                actions=actions if actions else ["詳細な診断を実行"],
                estimated_cost=None
            )
            
            self.recommendations.append(recommendation)
            self._save_recommendations()
            
            return recommendation
        
        return None
    
    def analyze_all_devices(self) -> List[MaintenanceRecommendation]:
        """全デバイスを分析してメンテナンス推奨を生成"""
        health_data = self._get_device_health_data()
        if not health_data:
            logger.warning("デバイス健康状態データを取得できませんでした")
            return []
        
        recommendations = []
        
        for device in health_data.get("devices", []):
            # デバイスを分析
            analysis = self.analyze_device_health(device)
            
            # 故障を予測
            prediction = self.predict_failure(device, analysis)
            
            # メンテナンス推奨を生成
            recommendation = self.generate_recommendation(device, analysis, prediction)
            if recommendation:
                recommendations.append(recommendation)
        
        return recommendations
    
    def get_stats(self) -> Dict[str, Any]:
        """統計情報を取得"""
        return {
            "total_recommendations": len(self.recommendations),
            "critical_recommendations": sum(1 for r in self.recommendations if r.priority == "critical"),
            "high_recommendations": sum(1 for r in self.recommendations if r.priority == "high"),
            "total_predictions": len(self.predictions_history),
            "recent_recommendations": [asdict(r) for r in self.recommendations[-10:]]
        }


def main():
    """メイン関数（テスト用）"""
    system = AIPredictiveMaintenance()
    
    # 全デバイスを分析
    recommendations = system.analyze_all_devices()
    
    print(f"メンテナンス推奨: {len(recommendations)}件")
    for rec in recommendations:
        print(f"\n{rec.device_name}: {rec.priority} - {rec.description[:100]}")
    
    # 統計を表示
    stats = system.get_stats()
    print(json.dumps(stats, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

