"""
ManaOS ユニットテストサンプル

このファイルは、ユニットテストの作成例を示しています。
"""

import pytest
from datetime import datetime
from typing import Dict, Any


# ===========================
# テスト用のモック関数
# ===========================

def validate_memory_key(key: str) -> bool:
    """メモリキーの検証"""
    if not key or not isinstance(key, str):
        return False
    if len(key) > 255:
        return False
    return True


def calculate_ttl_expiration(ttl_seconds: int) -> datetime:
    """TTL有効期限の計算"""
    from datetime import timedelta
    return datetime.utcnow() + timedelta(seconds=ttl_seconds)


def format_api_response(success: bool, data: Any = None, error: str = None) -> Dict:
    """API レスポンスのフォーマット"""
    response = {
        "success": success,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    if success:
        response["data"] = data
    else:
        response["error"] = error
    
    return response


# ===========================
# ユニットテスト
# ===========================

class TestMemoryKeyValidation:
    """メモリキー検証のテスト"""
    
    def test_valid_key(self):
        """有効なキーのテスト"""
        assert validate_memory_key("valid_key") == True
        assert validate_memory_key("user_123") == True
        assert validate_memory_key("test-key_001") == True
    
    def test_empty_key(self):
        """空のキーは無効"""
        assert validate_memory_key("") == False
        assert validate_memory_key(None) == False
    
    def test_invalid_type(self):
        """文字列以外は無効"""
        assert validate_memory_key(123) == False
        assert validate_memory_key([]) == False
        assert validate_memory_key({}) == False
    
    def test_too_long_key(self):
        """長すぎるキーは無効"""
        long_key = "a" * 256
        assert validate_memory_key(long_key) == False
    
    @pytest.mark.parametrize("key,expected", [
        ("valid", True),
        ("a" * 255, True),
        ("a" * 256, False),
        ("", False),
        (None, False),
    ])
    def test_parametrized_validation(self, key, expected):
        """パラメータ化テスト"""
        assert validate_memory_key(key) == expected


class TestTTLCalculation:
    """TTL計算のテスト"""
    
    def test_calculate_future_time(self):
        """未来の時刻を正しく計算"""
        ttl = 3600  # 1時間
        expiration = calculate_ttl_expiration(ttl)
        
        assert expiration > datetime.utcnow()
    
    def test_ttl_difference(self):
        """TTLの差分が正しい"""
        from datetime import timedelta
        
        ttl = 7200  # 2時間
        expiration = calculate_ttl_expiration(ttl)
        now = datetime.utcnow()
        
        diff = (expiration - now).total_seconds()
        
        # 誤差1秒以内
        assert abs(diff - ttl) < 1
    
    @pytest.mark.parametrize("ttl_seconds", [60, 3600, 86400])
    def test_various_ttl_values(self, ttl_seconds):
        """様々なTTL値でテスト"""
        expiration = calculate_ttl_expiration(ttl_seconds)
        assert expiration > datetime.utcnow()


class TestAPIResponseFormat:
    """APIレスポンスフォーマットのテスト"""
    
    def test_success_response(self):
        """成功レスポンス"""
        data = {"key": "value"}
        response = format_api_response(True, data=data)
        
        assert response["success"] == True
        assert response["data"] == data
        assert "timestamp" in response
        assert "error" not in response
    
    def test_error_response(self):
        """エラーレスポンス"""
        error = "Something went wrong"
        response = format_api_response(False, error=error)
        
        assert response["success"] == False
        assert response["error"] == error
        assert "timestamp" in response
        assert "data" not in response
    
    def test_response_has_timestamp(self):
        """タイムスタンプが含まれる"""
        response = format_api_response(True)
        
        assert "timestamp" in response
        # ISO形式の検証
        datetime.fromisoformat(response["timestamp"].replace('Z', '+00:00'))


# ===========================
# フィクスチャのテスト
# ===========================

@pytest.fixture
def sample_memory_data():
    """サンプルメモリデータ"""
    return {
        "key": "test_key_123",
        "value": {"user": "testuser", "score": 100},
        "ttl": 3600,
        "tags": ["test", "sample"]
    }


@pytest.fixture
def mock_api_response():
    """モックAPIレスポンス"""
    return {
        "success": True,
        "data": {"result": "ok"},
        "timestamp": datetime.utcnow().isoformat()
    }


class TestWithFixtures:
    """フィクスチャを使用したテスト"""
    
    def test_memory_data_structure(self, sample_memory_data):
        """メモリデータ構造のテスト"""
        assert "key" in sample_memory_data
        assert "value" in sample_memory_data
        assert isinstance(sample_memory_data["value"], dict)
    
    def test_api_response_structure(self, mock_api_response):
        """APIレスポンス構造のテスト"""
        assert mock_api_response["success"] == True
        assert "data" in mock_api_response
        assert "timestamp" in mock_api_response


# ===========================
# 非同期テスト
# ===========================

@pytest.mark.asyncio
async def test_async_operation():
    """非同期操作のテスト"""
    import asyncio
    
    async def async_function():
        await asyncio.sleep(0.1)
        return "result"
    
    result = await async_function()
    assert result == "result"


# ===========================
# エラーハンドリングのテスト
# ===========================

def function_that_raises():
    """例外を発生させる関数"""
    raise ValueError("Test error")


def test_exception_handling():
    """例外のテスト"""
    with pytest.raises(ValueError) as exc_info:
        function_that_raises()
    
    assert "Test error" in str(exc_info.value)


# ===========================
# マーカーのテスト
# ===========================

@pytest.mark.unit
def test_marked_as_unit():
    """ユニットテストマーカー"""
    assert True


@pytest.mark.slow
def test_slow_operation():
    """遅いテストのマーカー"""
    import time
    time.sleep(0.1)
    assert True


if __name__ == "__main__":
    # 単独実行
    pytest.main([__file__, "-v"])
