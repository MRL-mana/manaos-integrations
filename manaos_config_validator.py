#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
✅ ManaOS 設定ファイル検証モジュール
設定ファイルの読み込み時に検証を行う
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
from manaos_error_handler import ManaOSErrorHandler, ErrorCategory, ErrorSeverity

logger = logging.getLogger(__name__)


class ConfigValidator:
    """設定ファイル検証クラス"""
    
    def __init__(self, service_name: str):
        """
        初期化
        
        Args:
            service_name: サービス名
        """
        self.service_name = service_name
        self.error_handler = ManaOSErrorHandler(service_name)
    
    def validate_config(
        self,
        config: Dict[str, Any],
        schema: Dict[str, Any],
        config_file: Optional[Path] = None
    ) -> tuple[bool, List[str]]:
        """
        設定を検証
        
        Args:
            config: 設定辞書
            schema: スキーマ定義
            config_file: 設定ファイルパス（エラーメッセージ用）
        
        Returns:
            (is_valid, errors)
        """
        errors = []
        
        # 必須フィールドチェック
        required_fields = schema.get("required", [])
        for field in required_fields:
            if field not in config:
                errors.append(f"必須フィールドが不足しています: {field}")
        
        # フィールドタイプチェック
        field_types = schema.get("types", {})
        for field, expected_type in field_types.items():
            if field in config:
                if not self._check_type(config[field], expected_type):
                    errors.append(
                        f"フィールド '{field}' の型が不正です。"
                        f"期待: {expected_type}, 実際: {type(config[field]).__name__}"
                    )
        
        # フィールド値チェック
        field_validators = schema.get("validators", {})
        for field, validator in field_validators.items():
            if field in config:
                validation_result = validator(config[field])
                if not validation_result[0]:
                    errors.append(f"フィールド '{field}': {validation_result[1]}")
        
        # エラーがある場合はログ出力
        if errors:
            error_message = f"設定検証エラー ({len(errors)}件): " + "; ".join(errors)
            if config_file:
                error_message += f" (ファイル: {config_file})"
            
            self.error_handler.handle_config_error(
                config_key="validation",
                reason=error_message,
                context={
                    "errors": errors,
                    "config_file": str(config_file) if config_file else None
                }
            )
        
        return len(errors) == 0, errors
    
    def _check_type(self, value: Any, expected_type: Union[type, str]) -> bool:
        """
        型チェック
        
        Args:
            value: 値
            expected_type: 期待される型
        
        Returns:
            型が一致するか
        """
        if isinstance(expected_type, str):
            type_map = {
                "str": str,
                "int": int,
                "float": float,
                "bool": bool,
                "dict": dict,
                "list": list
            }
            expected_type = type_map.get(expected_type, type(None))
        
        return isinstance(value, expected_type)
    
    def validate_and_load(
        self,
        config_file: Path,
        schema: Dict[str, Any],
        default_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        設定ファイルを読み込み・検証
        
        Args:
            config_file: 設定ファイルパス
            schema: スキーマ定義
            default_config: デフォルト設定
        
        Returns:
            検証済み設定辞書
        
        Raises:
            ValueError: 検証エラー時
        """
        # 設定ファイル読み込み
        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            except json.JSONDecodeError as e:
                error = self.error_handler.handle_config_error(
                    config_key=str(config_file),
                    reason=f"JSON解析エラー: {e}",
                    context={"config_file": str(config_file)}
                )
                raise ValueError(error.message)
            except Exception as e:
                error = self.error_handler.handle_config_error(
                    config_key=str(config_file),
                    reason=f"ファイル読み込みエラー: {e}",
                    context={"config_file": str(config_file)}
                )
                raise ValueError(error.message)
        else:
            if default_config:
                config = default_config.copy()
                logger.warning(f"設定ファイルが見つかりません: {config_file}。デフォルト設定を使用します。")
            else:
                error = self.error_handler.handle_config_error(
                    config_key=str(config_file),
                    reason="設定ファイルが見つかりません",
                    context={"config_file": str(config_file)}
                )
                raise ValueError(error.message)
        
        # デフォルト値のマージ
        if default_config:
            for key, value in default_config.items():
                if key not in config:
                    config[key] = value
        
        # 検証
        is_valid, errors = self.validate_config(config, schema, config_file)
        if not is_valid:
            raise ValueError(f"設定検証エラー: {'; '.join(errors)}")
        
        return config


# 共通スキーマ定義
COMMON_SCHEMAS = {
    "ollama_config": {
        "required": ["ollama_url"],
        "types": {
            "ollama_url": "str",
            "model": "str"
        },
        "validators": {
            "ollama_url": lambda v: (
                v.startswith("http://") or v.startswith("https://"),
                "ollama_urlはhttp://またはhttps://で始まる必要があります"
            )
        }
    },
    "service_config": {
        "required": [],
        "types": {
            "port": "int",
            "timeout_seconds": (int, float)
        },
        "validators": {
            "port": lambda v: (
                1024 <= v <= 65535,
                "portは1024-65535の範囲である必要があります"
            ),
            "timeout_seconds": lambda v: (
                v > 0,
                "timeout_secondsは0より大きい必要があります"
            )
        }
    }
}


def validate_ollama_config(config: Dict[str, Any], config_file: Optional[Path] = None) -> bool:
    """
    Ollama設定を検証
    
    Args:
        config: 設定辞書
        config_file: 設定ファイルパス
    
    Returns:
        検証成功か
    """
    validator = ConfigValidator("ConfigValidator")
    is_valid, errors = validator.validate_config(config, COMMON_SCHEMAS["ollama_config"], config_file)
    return is_valid


def validate_service_config(config: Dict[str, Any], config_file: Optional[Path] = None) -> bool:
    """
    サービス設定を検証
    
    Args:
        config: 設定辞書
        config_file: 設定ファイルパス
    
    Returns:
        検証成功か
    """
    validator = ConfigValidator("ConfigValidator")
    is_valid, errors = validator.validate_config(config, COMMON_SCHEMAS["service_config"], config_file)
    return is_valid

