#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
⏱️ ManaOS タイムアウト設定管理
統一されたタイムアウト設定を提供
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# デフォルトタイムアウト設定
DEFAULT_TIMEOUTS = {
    "health_check": 2.0,
    "api_call": 5.0,
    "llm_call": 30.0,
    "llm_call_heavy": 60.0,
    "workflow_execution": 300.0,
    "script_execution": 60.0,
    "command_execution": 30.0,
    "database_query": 10.0,
    "file_operation": 30.0,
    "network_request": 10.0,
    "external_service": 30.0
}

# タイムアウト設定ファイルパス
TIMEOUT_CONFIG_FILE = Path(__file__).parent / "manaos_timeout_config.json"


class TimeoutConfig:
    """タイムアウト設定管理クラス"""
    
    def __init__(self, config_file: Optional[Path] = None):
        """
        初期化
        
        Args:
            config_file: 設定ファイルパス（オプション）
        """
        self.config_file = config_file or TIMEOUT_CONFIG_FILE
        self.timeouts = self._load_config()
    
    def _load_config(self) -> Dict[str, float]:
        """
        設定を読み込み
        
        Returns:
            タイムアウト設定辞書
        """
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    # デフォルトとマージ
                    timeouts = DEFAULT_TIMEOUTS.copy()
                    timeouts.update(config.get("timeouts", {}))
                    return timeouts
            except Exception as e:
                logger.warning(f"タイムアウト設定読み込みエラー: {e}。デフォルト値を使用します。")
                return DEFAULT_TIMEOUTS.copy()
        else:
            # デフォルト設定を保存
            self._save_default_config()
            return DEFAULT_TIMEOUTS.copy()
    
    def _save_default_config(self):
        """デフォルト設定を保存"""
        try:
            config = {
                "version": "1.0",
                "description": "ManaOS Timeout Configuration",
                "timeouts": DEFAULT_TIMEOUTS
            }
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            logger.info(f"デフォルトタイムアウト設定を保存: {self.config_file}")
        except Exception as e:
            logger.error(f"タイムアウト設定保存エラー: {e}")
    
    def get(self, key: str, default: Optional[float] = None) -> float:
        """
        タイムアウト値を取得
        
        Args:
            key: タイムアウトキー
            default: デフォルト値（設定ファイルにもデフォルトにもない場合）
        
        Returns:
            タイムアウト値（秒）
        """
        timeout = self.timeouts.get(key)
        if timeout is None:
            if default is not None:
                return default
            logger.warning(f"タイムアウト設定が見つかりません: {key}。デフォルト値を使用します。")
            return DEFAULT_TIMEOUTS.get(key, 10.0)
        return float(timeout)
    
    def set(self, key: str, value: float):
        """
        タイムアウト値を設定
        
        Args:
            key: タイムアウトキー
            value: タイムアウト値（秒）
        """
        self.timeouts[key] = float(value)
        self._save_config()
    
    def _save_config(self):
        """設定を保存"""
        try:
            config = {
                "version": "1.0",
                "description": "ManaOS Timeout Configuration",
                "timeouts": self.timeouts
            }
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"タイムアウト設定保存エラー: {e}")
    
    def get_all(self) -> Dict[str, float]:
        """
        全タイムアウト設定を取得
        
        Returns:
            タイムアウト設定辞書
        """
        return self.timeouts.copy()


# グローバルインスタンス
_timeout_config: Optional[TimeoutConfig] = None


def get_timeout_config() -> TimeoutConfig:
    """
    タイムアウト設定インスタンスを取得
    
    Returns:
        TimeoutConfigインスタンス
    """
    global _timeout_config
    if _timeout_config is None:
        _timeout_config = TimeoutConfig()
    return _timeout_config


def get_timeout(key: str, default: Optional[float] = None) -> float:
    """
    タイムアウト値を取得（簡易関数）
    
    Args:
        key: タイムアウトキー
        default: デフォルト値
    
    Returns:
        タイムアウト値（秒）
    """
    return get_timeout_config().get(key, default)


# 環境変数による上書きサポート
def _apply_env_overrides():
    """環境変数からタイムアウト設定を読み込み"""
    config = get_timeout_config()
    for key in DEFAULT_TIMEOUTS.keys():
        env_key = f"MANAOS_TIMEOUT_{key.upper()}"
        env_value = os.getenv(env_key)
        if env_value:
            try:
                config.set(key, float(env_value))
                logger.info(f"環境変数からタイムアウト設定を読み込み: {key} = {env_value}")
            except ValueError:
                logger.warning(f"無効なタイムアウト値（環境変数）: {env_key} = {env_value}")


# 初期化時に環境変数を適用
_apply_env_overrides()

