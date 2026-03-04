#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔗 ManaOS統合ベースクラス
全統合クラスの共通機能を提供
"""

from typing import Dict, Any, Optional
from abc import ABC, abstractmethod
from datetime import datetime

# 統一モジュールのインポート
from manaos_logger import get_logger
from manaos_error_handler import ManaOSErrorHandler, ErrorCategory, ErrorSeverity
from manaos_timeout_config import get_timeout_config
from manaos_config_validator import ConfigValidator
from config_validator_enhanced import ConfigValidatorEnhanced


class BaseIntegration(ABC):
    """統合クラスのベースクラス"""
    
    def __init__(self, name: str, config_path: Optional[str] = None):
        """
        初期化
        
        Args:
            name: 統合名
            config_path: 設定ファイルのパス（オプション）
        """
        self.name = name
        self.logger = get_logger(f"Integration.{name}")
        self.error_handler = ManaOSErrorHandler(name)
        self.timeout_config = get_timeout_config()
        self.config_validator = ConfigValidator(f"Integration.{name}")
        self.config_validator_enhanced = ConfigValidatorEnhanced()
        
        self._initialized = False
        self._available = False
        self._config = {}
        self._config_path = config_path
        
        # 設定ファイルの読み込み
        if config_path:
            self._load_config()
    
    def _load_config(self):
        """設定ファイルを読み込み"""
        if self._config_path:
            try:
                from pathlib import Path
                config_path = Path(self._config_path)
                # ConfigValidatorEnhancedを使用（validate_config_fileメソッドあり）
                is_valid, errors, config_data = self.config_validator_enhanced.validate_config_file(config_path)
                if is_valid:
                    self._config = config_data
                    self.logger.info(f"設定ファイルを読み込みました: {self._config_path}")
                else:
                    self.logger.warning(f"設定ファイル検証エラー: {errors}")
                    self._config = config_data if config_data else {}
            except Exception as e:
                error = self.error_handler.handle_exception(
                    e,
                    context={"config_path": self._config_path},
                    user_message=f"設定ファイルの読み込みに失敗しました: {self._config_path}"
                )
                self.logger.warning(f"設定ファイルの読み込みに失敗: {error.message}")
                self._config = {}
    
    @abstractmethod
    def _initialize_internal(self) -> bool:
        """
        内部初期化（サブクラスで実装）
        
        Returns:
            初期化成功かどうか
        """
        pass
    
    @abstractmethod
    def _check_availability_internal(self) -> bool:
        """
        内部の利用可能性チェック（サブクラスで実装）
        
        Returns:
            利用可能かどうか
        """
        pass
    
    def initialize(self) -> bool:
        """
        初期化
        
        Returns:
            初期化成功かどうか
        """
        if self._initialized:
            return True
        
        try:
            self.logger.info(f"{self.name}の初期化を開始...")
            success = self._initialize_internal()
            
            if success:
                self._initialized = True
                self.logger.info(f"{self.name}の初期化が完了しました")
            else:
                self.logger.warning(f"{self.name}の初期化に失敗しました")
            
            return success
        
        except Exception as e:
            error = self.error_handler.handle_exception(
                e,
                context={"integration": self.name, "action": "initialize"},
                user_message=f"{self.name}の初期化に失敗しました"
            )
            self.logger.error(f"初期化エラー: {error.message}")
            return False
    
    def is_available(self) -> bool:
        """
        利用可能性チェック
        
        Returns:
            利用可能かどうか
        """
        try:
            # 初期化されていない場合は初期化を試みる
            if not self._initialized:
                self.initialize()
            
            # 内部チェックを実行
            self._available = self._check_availability_internal()
            return bool(self._available)  # 必ず bool を返す
        
        except Exception as e:
            error = self.error_handler.handle_exception(
                e,
                context={"integration": self.name, "action": "check_availability"},
                user_message=f"{self.name}の利用可能性チェックに失敗しました"
            )
            self.logger.error(f"利用可能性チェックエラー: {error.message}")
            return False
    
    def check_health(self) -> Dict[str, Any]:
        """
        ヘルスチェック
        
        Returns:
            ヘルス状態の辞書
        """
        try:
            available = self.is_available()
            
            return {
                "name": self.name,
                "available": available,
                "initialized": self._initialized,
                "status": "healthy" if available else "unavailable",
                "timestamp": datetime.now().isoformat()
            }
        
        except Exception as e:
            error = self.error_handler.handle_exception(
                e,
                context={"integration": self.name, "action": "check_health"},
                user_message=f"{self.name}のヘルスチェックに失敗しました"
            )
            return {
                "name": self.name,
                "available": False,
                "initialized": self._initialized,
                "status": "error",
                "error": error.user_message or error.message,
                "timestamp": datetime.now().isoformat()
            }
    
    def get_config(self, key: Optional[str] = None, default: Any = None) -> Any:
        """
        設定値を取得
        
        Args:
            key: 設定キー（Noneの場合は全設定を返す）
            default: デフォルト値
        
        Returns:
            設定値
        """
        if key is None:
            return self._config
        return self._config.get(key, default)
    
    def get_timeout(self, operation: str) -> float:
        """
        タイムアウト値を取得
        
        Args:
            operation: 操作名
        
        Returns:
            タイムアウト値（秒）
        """
        return self.timeout_config.get(operation, 10.0)
    
    def get_status(self) -> Dict[str, Any]:
        """
        状態を取得
        
        Returns:
            状態の辞書
        """
        return {
            "name": self.name,
            "initialized": self._initialized,
            "available": self._available,
            "config_loaded": bool(self._config),
            "health": self.check_health()
        }

