#!/usr/bin/env python3
"""
🛡️ ManaOS 入力検証システム
SQLインジェクション対策・XSS対策・入力サニタイゼーション
"""

import re
import html
import json
from typing import Dict, Any, Optional, List, Union
from functools import wraps

# 統一モジュールのインポート
from manaos_logger import get_logger, get_service_logger
from manaos_error_handler import ManaOSErrorHandler, ErrorCategory, ErrorSeverity

# ロガーの初期化
logger = get_service_logger("input-validator")

# エラーハンドラーの初期化
error_handler = ManaOSErrorHandler("InputValidator")


class InputValidator:
    """入力検証システム"""
    
    def __init__(self):
        """初期化"""
        # SQLインジェクションパターン
        self.sql_patterns = [
            r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|EXECUTE|UNION|SCRIPT)\b)",
            r"(--|#|/\*|\*/)",
            r"(\bor\b|\band\b)\s+\d+\s*=\s*\d+",
            r"('|;|\\)",
        ]
        
        # XSSパターン
        self.xss_patterns = [
            r"<script[^>]*>.*?</script>",
            r"<iframe[^>]*>.*?</iframe>",
            r"javascript:",
            r"on\w+\s*=",
            r"<img[^>]*src\s*=\s*['\"]javascript:",
            r"<svg[^>]*onload\s*=",
        ]
        
        logger.info(f"✅ Input Validator初期化完了")
    
    def sanitize_string(self, value: str, max_length: Optional[int] = None) -> str:
        """
        文字列をサニタイズ
        
        Args:
            value: 入力値
            max_length: 最大長
        
        Returns:
            サニタイズされた文字列
        """
        if not isinstance(value, str):
            value = str(value)
        
        # HTMLエスケープ
        value = html.escape(value)
        
        # 長さ制限
        if max_length and len(value) > max_length:
            value = value[:max_length]
        
        return value
    
    def validate_sql_injection(self, value: str) -> bool:
        """
        SQLインジェクションをチェック
        
        Args:
            value: 入力値
        
        Returns:
            安全な場合True
        """
        if not isinstance(value, str):
            value = str(value)
        
        value_upper = value.upper()
        
        for pattern in self.sql_patterns:
            if re.search(pattern, value_upper, re.IGNORECASE):
                logger.warning(f"SQLインジェクションの可能性を検出: {value[:50]}")
                return False
        
        return True
    
    def validate_xss(self, value: str) -> bool:
        """
        XSSをチェック
        
        Args:
            value: 入力値
        
        Returns:
            安全な場合True
        """
        if not isinstance(value, str):
            value = str(value)
        
        for pattern in self.xss_patterns:
            if re.search(pattern, value, re.IGNORECASE):
                logger.warning(f"XSSの可能性を検出: {value[:50]}")
                return False
        
        return True
    
    def validate_email(self, email: str) -> bool:
        """
        メールアドレスを検証
        
        Args:
            email: メールアドレス
        
        Returns:
            有効な場合True
        """
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    def validate_url(self, url: str) -> bool:
        """
        URLを検証
        
        Args:
            url: URL
        
        Returns:
            有効な場合True
        """
        pattern = r'^https?://[^\s/$.?#].[^\s]*$'
        return bool(re.match(pattern, url))
    
    def validate_json(self, value: str) -> bool:
        """
        JSONを検証
        
        Args:
            value: JSON文字列
        
        Returns:
            有効な場合True
        """
        try:
            json.loads(value)
            return True
        except (json.JSONDecodeError, TypeError):
            return False
    
    def validate_input(
        self,
        value: Any,
        input_type: str = "string",
        required: bool = False,
        max_length: Optional[int] = None,
        min_length: Optional[int] = None,
        pattern: Optional[str] = None,
        check_sql: bool = True,
        check_xss: bool = True
    ) -> tuple[bool, Optional[str]]:
        """
        入力を検証
        
        Args:
            value: 入力値
            input_type: 入力タイプ（string, email, url, json, int, float）
            required: 必須かどうか
            max_length: 最大長
            min_length: 最小長
            pattern: 正規表現パターン
            check_sql: SQLインジェクションチェック
            check_xss: XSSチェック
        
        Returns:
            (検証結果, エラーメッセージ)
        """
        # 必須チェック
        if required and (value is None or value == ""):
            return False, "必須項目です"
        
        if value is None or value == "":
            return True, None
        
        # 型チェック
        if input_type == "string":
            if not isinstance(value, str):
                value = str(value)
            
            # 長さチェック
            if min_length and len(value) < min_length:
                return False, f"最小長は{min_length}文字です"
            if max_length and len(value) > max_length:
                return False, f"最大長は{max_length}文字です"
            
            # SQLインジェクションチェック
            if check_sql and not self.validate_sql_injection(value):
                return False, "SQLインジェクションの可能性があります"
            
            # XSSチェック
            if check_xss and not self.validate_xss(value):
                return False, "XSSの可能性があります"
            
            # パターンチェック
            if pattern and not re.match(pattern, value):
                return False, "形式が正しくありません"
        
        elif input_type == "email":
            if not self.validate_email(str(value)):
                return False, "メールアドレスの形式が正しくありません"
        
        elif input_type == "url":
            if not self.validate_url(str(value)):
                return False, "URLの形式が正しくありません"
        
        elif input_type == "json":
            if not self.validate_json(str(value)):
                return False, "JSONの形式が正しくありません"
        
        elif input_type == "int":
            try:
                int(value)
            except (ValueError, TypeError):
                return False, "整数値が必要です"
        
        elif input_type == "float":
            try:
                float(value)
            except (ValueError, TypeError):
                return False, "数値が必要です"
        
        return True, None
    
    def sanitize_dict(self, data: Dict[str, Any], schema: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        辞書をサニタイズ
        
        Args:
            data: 入力データ
            schema: スキーマ（検証ルール）
        
        Returns:
            サニタイズされたデータ
        """
        sanitized = {}
        
        for key, value in data.items():
            # スキーマがある場合は検証
            if schema and key in schema:
                rule = schema[key]
                is_valid, error = self.validate_input(
                    value,
                    input_type=rule.get("type", "string"),
                    required=rule.get("required", False),
                    max_length=rule.get("max_length"),
                    min_length=rule.get("min_length"),
                    pattern=rule.get("pattern"),
                    check_sql=rule.get("check_sql", True),
                    check_xss=rule.get("check_xss", True)
                )
                
                if not is_valid:
                    logger.warning(f"入力検証エラー ({key}): {error}")
                    continue
            
            # サニタイズ
            if isinstance(value, str):
                sanitized[key] = self.sanitize_string(value)
            elif isinstance(value, dict):
                sanitized[key] = self.sanitize_dict(value, schema.get(key, {}).get("schema") if schema else None)
            elif isinstance(value, list):
                sanitized[key] = [self.sanitize_string(str(v)) if isinstance(v, str) else v for v in value]
            else:
                sanitized[key] = value
        
        return sanitized
    
    def validate_decorator(self, schema: Dict[str, Any]):
        """
        入力検証デコレータ
        
        Args:
            schema: 検証スキーマ
        """
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                from flask import request
                
                # リクエストデータを取得
                if request.is_json:
                    data = request.get_json() or {}
                else:
                    data = request.form.to_dict()
                
                # 検証とサニタイズ
                sanitized_data = self.sanitize_dict(data, schema)
                
                # 検証エラーがある場合はエラーを返す
                # （簡易版：実際にはより詳細なエラーハンドリングが必要）
                
                # サニタイズされたデータをkwargsに追加
                kwargs["validated_data"] = sanitized_data
                
                return func(*args, **kwargs)
            
            return wrapper
        return decorator


# グローバルインスタンス
input_validator = InputValidator()

# デコレータのエクスポート
validate_input = input_validator.validate_decorator

