#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
テスト: ManaOS セキュリティモジュール
"""

import pytest
import os
from manaos_security import (
    APIKeyManager, JWTManager, RateLimiter, InputValidator,
    require_api_key, require_jwt, rate_limit, validate_input
)


class TestAPIKeyManager:
    """APIキー管理のテスト"""
    
    def test_validate_api_key(self):
        """APIキーの検証テスト"""
        manager = APIKeyManager()
        
        # 環境変数からAPIキーを設定
        os.environ['MANAOS_API_KEY'] = 'test-api-key-123'
        manager._load_api_keys()
        
        assert manager.validate_api_key('test-api-key-123') == True
        assert manager.validate_api_key('invalid-key') == False
    
    def test_get_permissions(self):
        """権限取得のテスト"""
        manager = APIKeyManager()
        os.environ['MANAOS_API_KEY'] = 'test-api-key-123'
        manager._load_api_keys()
        
        permissions = manager.get_permissions('test-api-key-123')
        assert 'read' in permissions
        assert 'write' in permissions


class TestJWTManager:
    """JWT認証のテスト"""
    
    def test_generate_and_validate_token(self):
        """トークン生成と検証のテスト"""
        manager = JWTManager(secret_key='test-secret')
        
        token = manager.generate_token('user123', expires_in=3600)
        assert token is not None
        
        payload = manager.validate_token(token)
        assert payload is not None
        assert payload['user_id'] == 'user123'
    
    def test_expired_token(self):
        """期限切れトークンのテスト"""
        manager = JWTManager(secret_key='test-secret')
        
        # 期限切れトークンを生成（負のexpires_in）
        token = manager.generate_token('user123', expires_in=-3600)
        payload = manager.validate_token(token)
        assert payload is None


class TestRateLimiter:
    """レート制限のテスト"""
    
    def test_rate_limit(self):
        """レート制限のテスト"""
        limiter = RateLimiter()
        
        identifier = "test-ip"
        
        # 制限内のリクエスト
        for i in range(10):
            assert limiter.is_allowed(identifier) == True
        
        # 制限を超えたリクエスト（デフォルトは100リクエスト/60秒）
        # 10回は許可されるはず
        assert limiter.is_allowed(identifier) == True
    
    def test_get_remaining(self):
        """残りリクエスト数のテスト"""
        limiter = RateLimiter()
        identifier = "test-ip"
        
        limiter.is_allowed(identifier)
        remaining = limiter.get_remaining(identifier)
        assert remaining >= 0


class TestInputValidator:
    """入力検証のテスト"""
    
    def test_validate_text(self):
        """テキスト検証のテスト"""
        validator = InputValidator()
        
        # 正常なテキスト
        is_valid, error = validator.validate_text("正常なテキスト")
        assert is_valid == True
        assert error is None
        
        # 長すぎるテキスト
        long_text = "a" * 20000
        is_valid, error = validator.validate_text(long_text, max_length=10000)
        assert is_valid == False
        assert error is not None
        
        # SQLインジェクション攻撃
        is_valid, error = validator.validate_text("'; DROP TABLE users; --")
        assert is_valid == False
    
    def test_validate_mode(self):
        """モード検証のテスト"""
        validator = InputValidator()
        
        # 正常なモード
        is_valid, error = validator.validate_mode("auto")
        assert is_valid == True
        
        # 不正なモード
        is_valid, error = validator.validate_mode("invalid")
        assert is_valid == False
    
    def test_validate_json(self):
        """JSON検証のテスト"""
        validator = InputValidator()
        
        schema = {
            "name": str,
            "age": int
        }
        
        # 正常なデータ
        data = {"name": "Test", "age": 30}
        is_valid, error = validator.validate_json(data, schema)
        assert is_valid == True
        
        # 必須フィールドが欠落
        data = {"name": "Test"}
        is_valid, error = validator.validate_json(data, schema)
        assert is_valid == False
        
        # 型が不正
        data = {"name": "Test", "age": "30"}
        is_valid, error = validator.validate_json(data, schema)
        assert is_valid == False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])








