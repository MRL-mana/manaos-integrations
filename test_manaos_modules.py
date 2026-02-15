#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🧪 ManaOS モジュールテスト
統一モジュールの動作確認
"""

import sys
from pathlib import Path

# テスト対象モジュール
sys.path.insert(0, str(Path(__file__).parent))

from manaos_error_handler import ManaOSErrorHandler, ErrorCategory, ErrorSeverity
from manaos_timeout_config import get_timeout_config, get_timeout
from manaos_config_validator import ConfigValidator, COMMON_SCHEMAS
from manaos_logger import get_logger
from manaos_process_manager import get_process_manager


def test_error_handler():
    """エラーハンドラーのテスト"""
    print("Testing Error Handler...")
    
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
    
    config = get_timeout_config()
    
    # デフォルト値取得テスト
    timeout = get_timeout("health_check")
    assert timeout == 2.0
    print(f"  [OK] Default timeout: {timeout}s")
    
    # 設定値取得テスト
    timeout = get_timeout("llm_call")
    assert timeout == 30.0
    print(f"  [OK] LLM call timeout: {timeout}s")
    
    # 存在しないキーのテスト
    timeout = get_timeout("nonexistent", default=10.0)
    assert timeout == 10.0
    print("  [OK] Default value fallback: OK")


def test_config_validator():
    """設定検証のテスト"""
    print("Testing Config Validator...")
    
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
    
    logger = get_logger("TestService")
    logger.info("Test log message")
    logger.warning("Test warning")
    logger.error("Test error")
    print("  [OK] Logger: OK")


def test_process_manager():
    """プロセス管理のテスト"""
    print("Testing Process Manager...")
    
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


if __name__ == "__main__":
    sys.exit(main())

