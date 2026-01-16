#!/usr/bin/env python3
"""
🔄 ManaOS 劣化運転システム
リソース不足やサービス障害時の最小機能モード
"""

import json
import time
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum

# 統一モジュールのインポート
from manaos_logger import get_logger
from manaos_error_handler import ManaOSErrorHandler
from manaos_timeout_config import get_timeout_config
from manaos_config_validator import ConfigValidator

# ロガーの初期化
logger = get_logger(__name__)

# エラーハンドラーの初期化
error_handler = ManaOSErrorHandler("DegradedModeSystem")

# タイムアウト設定の取得
timeout_config = get_timeout_config()

# 設定ファイル検証の初期化
config_validator = ConfigValidator("DegradedModeSystem")


class DegradedModeLevel(str, Enum):
    """劣化運転レベル"""
    NORMAL = "normal"  # 通常運転
    DEGRADED = "degraded"  # 劣化運転
    MINIMAL = "minimal"  # 最小機能モード
    EMERGENCY = "emergency"  # 緊急モード


@dataclass
class ServiceStatus:
    """サービス状態"""
    service_name: str
    available: bool
    degraded: bool
    fallback_available: bool
    last_check: str


class DegradedModeSystem:
    """劣化運転システム"""
    
    def __init__(self, config_path: Optional[Path] = None):
        """
        初期化
        
        Args:
            config_path: 設定ファイルのパス
        """
        self.config_path = config_path or Path(__file__).parent / "degraded_mode_config.json"
        self.config = self._load_config()
        
        # 現在のモード
        self.current_mode = DegradedModeLevel.NORMAL
        
        # サービス状態
        self.service_statuses: Dict[str, ServiceStatus] = {}
        
        # モード履歴
        self.mode_history: List[Dict[str, Any]] = []
        self.mode_history_storage = Path("degraded_mode_history.json")
        self._load_mode_history()
        
        logger.info("✅ Degraded Mode System初期化完了")
    
    def _load_config(self) -> Dict[str, Any]:
        """設定を読み込む"""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"設定読み込みエラー: {e}")
        
        return {
            "enable_degraded_mode": True,
            "enable_minimal_mode": True,
            "enable_cache_based_responses": True,
            "cache_ttl_hours": 24,
            "degraded_threshold_cpu": 90,
            "degraded_threshold_memory": 90,
            "minimal_threshold_cpu": 95,
            "minimal_threshold_memory": 95
        }
    
    def _load_mode_history(self):
        """モード履歴を読み込む"""
        if self.mode_history_storage.exists():
            try:
                with open(self.mode_history_storage, 'r', encoding='utf-8') as f:
                    self.mode_history = json.load(f)
            except Exception as e:
                logger.warning(f"モード履歴読み込みエラー: {e}")
    
    def _save_mode_history(self):
        """モード履歴を保存"""
        try:
            # 最新100件のみ保存
            recent_history = self.mode_history[-100:]
            with open(self.mode_history_storage, 'w', encoding='utf-8') as f:
                json.dump(recent_history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"モード履歴保存エラー: {e}")
    
    def check_system_status(self) -> DegradedModeLevel:
        """
        システム状態をチェックしてモードを決定
        
        Returns:
            現在のモード
        """
        if not self.config.get("enable_degraded_mode", True):
            return DegradedModeLevel.NORMAL
        
        import psutil
        
        # CPU使用率
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # メモリ使用率
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        
        # モードの決定
        if cpu_percent >= self.config.get("minimal_threshold_cpu", 95) or \
           memory_percent >= self.config.get("minimal_threshold_memory", 95):
            new_mode = DegradedModeLevel.MINIMAL
        elif cpu_percent >= self.config.get("degraded_threshold_cpu", 90) or \
             memory_percent >= self.config.get("degraded_threshold_memory", 90):
            new_mode = DegradedModeLevel.DEGRADED
        else:
            new_mode = DegradedModeLevel.NORMAL
        
        # モード変更を記録
        if new_mode != self.current_mode:
            self._record_mode_change(self.current_mode, new_mode, {
                "cpu_percent": cpu_percent,
                "memory_percent": memory_percent
            })
            self.current_mode = new_mode
        
        return self.current_mode
    
    def _record_mode_change(self, old_mode: DegradedModeLevel, new_mode: DegradedModeLevel, context: Dict[str, Any]):
        """モード変更を記録"""
        change_record = {
            "old_mode": old_mode.value,
            "new_mode": new_mode.value,
            "timestamp": datetime.now().isoformat(),
            "context": context
        }
        
        self.mode_history.append(change_record)
        self._save_mode_history()
        
        logger.info(f"モード変更: {old_mode.value} -> {new_mode.value}")
    
    def check_service_availability(self, service_name: str) -> ServiceStatus:
        """
        サービスの可用性をチェック
        
        Args:
            service_name: サービス名
            
        Returns:
            サービス状態
        """
        # 簡易的なサービスチェック（実際の実装では、各サービスのヘルスチェックエンドポイントを呼び出す）
        status = ServiceStatus(
            service_name=service_name,
            available=True,
            degraded=False,
            fallback_available=False,
            last_check=datetime.now().isoformat()
        )
        
        self.service_statuses[service_name] = status
        
        return status
    
    def get_available_features(self) -> Dict[str, bool]:
        """
        現在のモードで利用可能な機能を取得
        
        Returns:
            機能の可用性
        """
        features = {}
        
        if self.current_mode == DegradedModeLevel.NORMAL:
            # 通常モード: すべての機能が利用可能
            features = {
                "llm_chat": True,
                "llm_reasoning": True,
                "llm_automation": True,
                "obsidian_save": True,
                "slack_notification": True,
                "google_drive_save": True,
                "memory_search": True,
                "cache_responses": True
            }
        elif self.current_mode == DegradedModeLevel.DEGRADED:
            # 劣化モード: 一部機能が制限
            features = {
                "llm_chat": True,
                "llm_reasoning": False,  # 推論機能は無効化
                "llm_automation": False,  # 自動処理は無効化
                "obsidian_save": True,
                "slack_notification": True,
                "google_drive_save": False,  # Google Drive保存は無効化
                "memory_search": True,
                "cache_responses": True
            }
        elif self.current_mode == DegradedModeLevel.MINIMAL:
            # 最小機能モード: キャッシュベース応答のみ
            features = {
                "llm_chat": False,
                "llm_reasoning": False,
                "llm_automation": False,
                "obsidian_save": False,
                "slack_notification": False,
                "google_drive_save": False,
                "memory_search": True,  # メモリ検索は可能
                "cache_responses": True  # キャッシュベース応答は可能
            }
        else:  # EMERGENCY
            # 緊急モード: 最小限の機能のみ
            features = {
                "llm_chat": False,
                "llm_reasoning": False,
                "llm_automation": False,
                "obsidian_save": False,
                "slack_notification": False,
                "google_drive_save": False,
                "memory_search": False,
                "cache_responses": True  # キャッシュベース応答のみ
            }
        
        return features
    
    def get_cache_based_response(self, query: str) -> Optional[Dict[str, Any]]:
        """
        キャッシュベースの応答を取得
        
        Args:
            query: クエリ
            
        Returns:
            キャッシュベースの応答（見つからない場合はNone）
        """
        if not self.config.get("enable_cache_based_responses", True):
            return None
        
        # キャッシュから類似のクエリを検索（簡易版）
        # 実際の実装では、ベクトル検索や類似度計算を使用
        cache_path = Path("data/cache/responses")
        if not cache_path.exists():
            return None
        
        # キャッシュファイルを検索
        cache_files = list(cache_path.glob("*.json"))
        for cache_file in cache_files[-100:]:  # 最新100件を確認
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                
                cached_query = cache_data.get("query", "")
                # 簡易的な類似度チェック（実際の実装では、より高度な類似度計算を使用）
                if query.lower() in cached_query.lower() or cached_query.lower() in query.lower():
                    return {
                        "response": cache_data.get("response", ""),
                        "source": "cache",
                        "cached_at": cache_data.get("timestamp", ""),
                        "similarity": 0.7  # 簡易的な類似度
                    }
            except Exception as e:
                logger.warning(f"キャッシュ読み込みエラー: {e}")
        
        return None
    
    def get_status(self) -> Dict[str, Any]:
        """状態を取得"""
        return {
            "current_mode": self.current_mode.value,
            "available_features": self.get_available_features(),
            "service_statuses": {name: asdict(status) for name, status in self.service_statuses.items()},
            "mode_history_count": len(self.mode_history),
            "config": self.config,
            "timestamp": datetime.now().isoformat()
        }


def main():
    """テスト用メイン関数"""
    system = DegradedModeSystem()
    
    # テスト: システム状態チェック
    mode = system.check_system_status()
    print(f"現在のモード: {mode.value}")
    
    # テスト: 利用可能な機能
    features = system.get_available_features()
    print(json.dumps(features, ensure_ascii=False, indent=2))
    
    # テスト: 状態取得
    status = system.get_status()
    print(json.dumps(status, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()








