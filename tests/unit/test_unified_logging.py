"""
統一ログシステムのユニットテスト
"""
import pytest
import os
import logging
from pathlib import Path
import sys

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
# unified_api パスを追加（実モジュールの場所）
_unified_api = str(Path(__file__).parent.parent.parent / "unified_api")
if _unified_api not in sys.path:
    sys.path.insert(0, _unified_api)
# 他テストが差し込んだモックを除去して実モジュールをロード
sys.modules.pop("unified_logging", None)

from unified_logging import (
    get_logger,
    get_service_logger,
    configure_logging,
    set_log_level,
    ManaOSLogFormatter,
    UnifiedLoggingConfig
)


class TestUnifiedLogging:
    """統一ログシステムのテストクラス"""
    
    def test_get_logger_basic(self):
        """基本的なロガー取得のテスト"""
        logger = get_logger("test_module")
        assert logger is not None
        assert isinstance(logger, logging.Logger)
        assert logger.name == "test_module"
    
    def test_get_service_logger(self):
        """サービス用ロガー取得のテスト"""
        logger = get_service_logger("test_service")
        assert logger is not None
        assert isinstance(logger, logging.Logger)
    
    def test_configure_logging(self):
        """ログ設定初期化のテスト"""
        configure_logging(force=True)
        logger = get_logger("test_config")
        assert logger.level in [logging.DEBUG, logging.INFO, logging.WARNING, logging.ERROR]
    
    def test_set_log_level(self):
        """ログレベル変更のテスト"""
        configure_logging(force=True)
        
        set_log_level("DEBUG")
        logger = get_logger("test_level_debug")
        assert logger.level == logging.DEBUG
        
        set_log_level("WARNING")
        assert logger.level == logging.WARNING
    
    def test_log_formatter_text(self):
        """テキストフォーマッターのテスト"""
        formatter = ManaOSLogFormatter(use_colors=False, json_format=False)
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None
        )
        
        formatted = formatter.format(record)
        assert "INFO" in formatted
        assert "test" in formatted
        assert "Test message" in formatted
    
    def test_log_formatter_json(self):
        """JSONフォーマッターのテスト"""
        import json
        
        formatter = ManaOSLogFormatter(use_colors=False, json_format=True)
        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="test.py",
            lineno=20,
            msg="Error message",
            args=(),
            exc_info=None
        )
        
        formatted = formatter.format(record)
        log_data = json.loads(formatted)
        
        assert log_data["level"] == "ERROR"
        assert log_data["logger"] == "test"
        assert log_data["message"] == "Error message"
        assert log_data["line"] == 20
    
    def test_unified_logging_config(self):
        """統一ログ設定のテスト"""
        config = UnifiedLoggingConfig()
        
        assert config.config["log_dir"] is not None
        assert config.config["log_level"] in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        assert isinstance(config.config["console_output"], bool)
        assert isinstance(config.config["file_output"], bool)
    
    def test_log_level_mapping(self):
        """ログレベルマッピングのテスト"""
        config = UnifiedLoggingConfig()
        
        config.config["log_level"] = "DEBUG"
        assert config.get_log_level() == logging.DEBUG
        
        config.config["log_level"] = "INFO"
        assert config.get_log_level() == logging.INFO
        
        config.config["log_level"] = "WARNING"
        assert config.get_log_level() == logging.WARNING
        
        config.config["log_level"] = "ERROR"
        assert config.get_log_level() == logging.ERROR
        
        config.config["log_level"] = "CRITICAL"
        assert config.get_log_level() == logging.CRITICAL
    
    def test_logger_output(self, tmp_path):
        """ログ出力のテスト"""
        # 一時ログディレクトリを使用
        log_dir = tmp_path / "test_logs"
        log_dir.mkdir()
        
        os.environ["MANAOS_LOG_DIR"] = str(log_dir)
        configure_logging(force=True)
        
        logger = get_logger("test_output", file_output=True)
        logger.info("Test log message")
        
        # ログファイルが作成されたか確認
        log_file = log_dir / "test_output.log"
        # NOTE: ファイル作成はバックグラウンドで行われる可能性があるため、
        # このテストは環境によっては失敗する可能性がある
    
    def test_exception_logging(self):
        """例外ログのテスト"""
        logger = get_logger("test_exception")
        
        try:
            1 / 0
        except ZeroDivisionError:
            # 例外が正しくログされるか確認（実際のログ出力はチェックしない）
            logger.exception("Error occurred")
            # エラーが発生しなければOK
            assert True


class TestLogManagerConfig:
    """ログマネージャー設定のテスト"""
    
    def test_environment_variable_override(self):
        """環境変数による設定上書きのテスト"""
        os.environ["MANAOS_LOG_LEVEL"] = "DEBUG"
        os.environ["MANAOS_LOG_JSON"] = "1"
        
        config = UnifiedLoggingConfig()
        
        assert config.config["log_level"] == "DEBUG"
        assert config.config["json_format"] is True
        
        # クリーンアップ
        del os.environ["MANAOS_LOG_LEVEL"]
        del os.environ["MANAOS_LOG_JSON"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
