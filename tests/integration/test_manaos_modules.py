#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🧪 ManaOS モジュールテスト
統一モジュールの動作確認
"""

import sys
from pathlib import Path
import importlib
import pytest
from unittest.mock import MagicMock

# テスト対象モジュール
sys.path.insert(0, str(Path(__file__).parent))


def _require(module_name: str):
    # 他のテストがstubやMockをsys.modulesに注入している場合は削除して実モジュールを取得
    # types.ModuleType のstub（属性が少ない）かMagicMockの場合は強制的に再インポート
    existing = sys.modules.get(module_name)
    if existing is not None:
        # MagicMockか、実モジュールでない(ファイルパスなし)stub モジュールは除去
        if isinstance(existing, MagicMock) or not getattr(existing, "__file__", None):
            del sys.modules[module_name]
    try:
        return importlib.import_module(module_name)
    except ImportError as exc:
        pytest.skip(f"{module_name} unavailable: {exc}")


def test_error_handler():
    """エラーハンドラーのテスト"""
    print("Testing Error Handler...")
    mod = _require("manaos_error_handler")
    ManaOSErrorHandler = mod.ManaOSErrorHandler
    ErrorCategory = mod.ErrorCategory
    
    handler = ManaOSErrorHandler("TestService")
    
    # 例外処理テスト
    try:
        raise ValueError("Test error")
    except Exception as e:
        error = handler.handle_exception(e, context={"test": True})
        assert error.error_code is not None
        assert error.message == "Test error"
        assert error.category == ErrorCategory.UNKNOWN
        print("  [OK] Error Handler: OK")
    
    # httpxエラーテスト
    import httpx
    try:
        raise httpx.TimeoutException("Timeout")
    except Exception as e:
        error = handler.handle_httpx_error(e, url="http://test.com")
        assert error.category == ErrorCategory.TIMEOUT
        assert error.retryable == True
        print("  [OK] HTTPX Error Handler: OK")
    
    # バリデーションエラーテスト
    error = handler.handle_validation_error("test_field", "invalid", "Invalid value")
    assert error.category == ErrorCategory.VALIDATION
    assert error.retryable == False
    print("  [OK] Validation Error Handler: OK")


def test_timeout_config():
    """タイムアウト設定のテスト"""
    print("Testing Timeout Config...")
    mod = _require("manaos_timeout_config")
    get_timeout_config = mod.get_timeout_config
    get_timeout = mod.get_timeout

    config = get_timeout_config()
    
    # デフォルト値取得テスト
    timeout = get_timeout("health_check")
    assert timeout == 2.0
    print(f"  [OK] Default timeout: {timeout}s")
    
    # 設定値取得テスト
    timeout = get_timeout("llm_call")
    assert isinstance(timeout, (int, float))
    assert timeout > 0
    print(f"  [OK] LLM call timeout: {timeout}s")
    
    # 存在しないキーのテスト
    timeout = get_timeout("nonexistent", default=10.0)
    assert timeout == 10.0
    print("  [OK] Default value fallback: OK")


def test_config_validator():
    """設定検証のテスト"""
    print("Testing Config Validator...")
    mod = _require("manaos_config_validator")
    ConfigValidator = mod.ConfigValidator
    COMMON_SCHEMAS = mod.COMMON_SCHEMAS

    validator = ConfigValidator("TestService")
    
    # 正常な設定のテスト
    valid_config = {
        "ollama_url": "http://127.0.0.1:11434",
        "model": "llama3.2:3b"
    }
    is_valid, errors = validator.validate_config(valid_config, COMMON_SCHEMAS["ollama_config"])
    assert is_valid == True
    assert len(errors) == 0
    print("  [OK] Valid config: OK")
    
    # 不正な設定のテスト
    invalid_config = {
        "ollama_url": "invalid_url"
    }
    is_valid, errors = validator.validate_config(invalid_config, COMMON_SCHEMAS["ollama_config"])
    assert is_valid == False
    assert len(errors) > 0
    print("  [OK] Invalid config detection: OK")


def test_logger():
    """ロガーのテスト"""
    print("Testing Logger...")
    mod = _require("manaos_logger")
    get_logger = mod.get_logger

    logger = get_logger("TestService")
    logger.info("Test log message")
    logger.warning("Test warning")
    logger.error("Test error")
    print("  [OK] Logger: OK")


def test_process_manager():
    """プロセス管理のテスト"""
    print("Testing Process Manager...")
    mod = _require("manaos_process_manager")
    get_process_manager = mod.get_process_manager

    manager = get_process_manager("TestService")
    
    # プロセス情報取得テスト（存在しないプロセス）
    info = manager.get_process_info("nonexistent_script.py")
    assert info is None or isinstance(info, dict)
    print("  [OK] Process info retrieval: OK")
    
    # 全プロセス情報取得テスト
    all_processes = manager.get_all_processes()
    assert isinstance(all_processes, dict)
    print("  [OK] All processes retrieval: OK")


def main():
    """メインテスト関数"""
    print("=" * 80)
    print("ManaOS Module Tests")
    print("=" * 80)
    print()
    
    try:
        test_error_handler()
        test_timeout_config()
        test_config_validator()
        test_logger()
        test_process_manager()
        
        print()
        print("=" * 80)
        print("[SUCCESS] All tests passed!")
        print("=" * 80)
        return 0
    except Exception as e:
        print()
        print("=" * 80)
        print(f"[FAILED] Test failed: {e}")
        print("=" * 80)
        import traceback
        traceback.print_exc()
        return 1



