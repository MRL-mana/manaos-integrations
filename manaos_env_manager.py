#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
⚙️ ManaOS環境変数統一管理システム
環境変数の一元管理と検証
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from threading import Lock

# 統一モジュールのインポート
from manaos_logger import get_logger
from manaos_error_handler import ManaOSErrorHandler, ErrorCategory, ErrorSeverity

# ロガーの初期化
logger = get_logger(__name__)

# エラーハンドラーの初期化
error_handler = ManaOSErrorHandler("EnvManager")

# グローバル設定
_env_cache: Dict[str, Any] = {}
_env_lock = Lock()
_env_validated = False


class EnvManager:
    """環境変数管理クラス"""
    
    def __init__(self, env_file: Optional[Path] = None):
        """
        初期化
        
        Args:
            env_file: .envファイルのパス（Noneの場合は自動検出）
        """
        self.env_file = env_file or self._find_env_file()
        self.env_vars: Dict[str, Any] = {}
        self.validated_vars: Dict[str, bool] = {}
        
        # 環境変数の定義
        self.required_vars: List[str] = []
        self.optional_vars: Dict[str, Any] = {}
        
        # 環境変数を読み込む
        self._load_env()
    
    def _find_env_file(self) -> Optional[Path]:
        """.envファイルを検出"""
        current_dir = Path(__file__).parent
        
        # 現在のディレクトリから順に検索
        for path in [current_dir, current_dir.parent]:
            env_file = path / ".env"
            if env_file.exists():
                return env_file
        
        return None
    
    def _load_env(self):
        """環境変数を読み込む"""
        # .envファイルから読み込み
        if self.env_file and self.env_file.exists():
            try:
                with open(self.env_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            if '=' in line:
                                key, value = line.split('=', 1)
                                key = key.strip()
                                value = value.strip().strip('"').strip("'")
                                os.environ[key] = value
                                self.env_vars[key] = value
                
                logger.info(f"環境変数ファイルを読み込みました: {self.env_file}")
            except Exception as e:
                error = error_handler.handle_exception(
                    e,
                    context={"env_file": str(self.env_file)},
                    user_message="環境変数ファイルの読み込みに失敗しました"
                )
                logger.warning(f"環境変数読み込みエラー: {error.message}")
        
        # 既存の環境変数をキャッシュ
        with _env_lock:
            for key, value in os.environ.items():
                if key.startswith("MANAOS_") or key.startswith("OLLAMA_") or key.startswith("SLACK_"):
                    _env_cache[key] = value
    
    def get(self, key: str, default: Optional[Any] = None, required: bool = False) -> Optional[str]:
        """
        環境変数を取得
        
        Args:
            key: 環境変数名
            default: デフォルト値
            required: 必須かどうか
        
        Returns:
            環境変数の値
        """
        value = os.getenv(key, default)
        
        if required and value is None:
            error = error_handler.handle_exception(
                ValueError(f"必須環境変数が設定されていません: {key}"),
                context={"env_var": key},
                user_message=f"環境変数 '{key}' が設定されていません"
            )
            raise ValueError(error.user_message or error.message)
        
        return value
    
    def get_int(self, key: str, default: Optional[int] = None) -> Optional[int]:
        """整数の環境変数を取得"""
        value = self.get(key)
        if value is None:
            return default
        try:
            return int(value)
        except ValueError:
            logger.warning(f"環境変数 '{key}' の値が整数ではありません: {value}")
            return default
    
    def get_float(self, key: str, default: Optional[float] = None) -> Optional[float]:
        """浮動小数点数の環境変数を取得"""
        value = self.get(key)
        if value is None:
            return default
        try:
            return float(value)
        except ValueError:
            logger.warning(f"環境変数 '{key}' の値が数値ではありません: {value}")
            return default
    
    def get_bool(self, key: str, default: Optional[bool] = None) -> bool:
        """ブール値の環境変数を取得"""
        value = self.get(key)
        if value is None:
            return default if default is not None else False
        return value.lower() in ("true", "1", "yes", "on")
    
    def validate(self, required_vars: List[str], optional_vars: Optional[Dict[str, Any]] = None) -> Dict[str, bool]:
        """
        環境変数を検証
        
        Args:
            required_vars: 必須環境変数のリスト
            optional_vars: オプション環境変数の辞書（デフォルト値付き）
        
        Returns:
            検証結果の辞書
        """
        results = {}
        
        # 必須変数の検証
        for var in required_vars:
            value = self.get(var)
            results[var] = value is not None
            if not results[var]:
                logger.warning(f"必須環境変数が設定されていません: {var}")
        
        # オプション変数の検証
        if optional_vars:
            for var, default in optional_vars.items():
                value = self.get(var, default)
                results[var] = value is not None
        
        self.validated_vars.update(results)
        return results
    
    def get_all(self, prefix: Optional[str] = None) -> Dict[str, str]:
        """
        環境変数をすべて取得
        
        Args:
            prefix: プレフィックス（指定した場合、そのプレフィックスで始まる変数のみ）
        
        Returns:
            環境変数の辞書
        """
        if prefix:
            return {
                k: v for k, v in os.environ.items()
                if k.startswith(prefix)
            }
        return dict(os.environ)
    
    def set(self, key: str, value: Any, persist: bool = False):
        """
        環境変数を設定
        
        Args:
            key: 環境変数名
            value: 値
            persist: .envファイルに保存するか
        """
        os.environ[key] = str(value)
        
        with _env_lock:
            _env_cache[key] = str(value)
        
        if persist and self.env_file:
            try:
                # .envファイルに追加
                with open(self.env_file, 'a', encoding='utf-8') as f:
                    f.write(f"\n{key}={value}\n")
                logger.info(f"環境変数を保存しました: {key}")
            except Exception as e:
                logger.warning(f"環境変数の保存に失敗しました: {e}")


# グローバルインスタンス
_env_manager: Optional[EnvManager] = None


def get_env_manager() -> EnvManager:
    """環境変数管理のシングルトンインスタンスを取得"""
    global _env_manager
    if _env_manager is None:
        _env_manager = EnvManager()
    return _env_manager


def get_env(key: str, default: Optional[Any] = None, required: bool = False) -> Optional[str]:
    """
    環境変数を取得（簡易関数）
    
    Args:
        key: 環境変数名
        default: デフォルト値
        required: 必須かどうか
    
    Returns:
        環境変数の値
    """
    return get_env_manager().get(key, default, required)


def main():
    """テスト用メイン関数"""
    print("ManaOS環境変数管理システムテスト")
    print("=" * 60)
    
    manager = get_env_manager()
    
    # 環境変数を取得
    ollama_url = manager.get("OLLAMA_URL", "http://localhost:11434")
    print(f"OLLAMA_URL: {ollama_url}")
    
    # 検証
    results = manager.validate(
        required_vars=["OLLAMA_URL"],
        optional_vars={"MANAOS_LOG_LEVEL": "INFO"}
    )
    print(f"\n検証結果: {results}")


if __name__ == "__main__":
    main()






















