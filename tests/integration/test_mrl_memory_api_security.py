#!/usr/bin/env python3
"""
MRL Memory API Security Test
APIの安全対策が効いてることをテストで証明
"""

import pytest
import os
from mrl_memory_api_security import APISecurity


class TestAPISecurity:
    """API安全対策のテスト"""
    
    @pytest.fixture
    def security(self):
        """APISecurityインスタンス"""
        return APISecurity(
            api_key="test_key",
            rate_limit_per_minute=60,
            max_input_size=1000000
        )
    
    def test_authentication_required(self, security):
        """
        テスト: 認証なし→401
        
        認証が必須であることを確認
        """
        # 正しいAPIキー
        assert security.authenticate("test_key") == True
        
        # 間違ったAPIキー
        assert security.authenticate("wrong_key") == False
        
        # APIキーなし
        assert security.authenticate(None) == False
    
    def test_rate_limit(self, security):
        """
        テスト: レート超過→429
        
        レート制限が効くことを確認
        """
        client_id = "test_client"
        
        # 60回まで許可
        for i in range(60):
            assert security.check_rate_limit(client_id) == True
        
        # 61回目で制限
        assert security.check_rate_limit(client_id) == False
    
    def test_input_size_limit(self, security):
        """
        テスト: 入力サイズ超過→413
        
        入力サイズ制限が効くことを確認
        """
        # 制限内
        small_text = "a" * 1000
        assert security.check_input_size(small_text) == True
        
        # 制限超過
        large_text = "a" * 2000000  # 2MB
        assert security.check_input_size(large_text) == False
    
    def test_pii_masking(self, security):
        """
        テスト: PIIマスキング
        
        PIIがマスキングされることを確認
        """
        text = "メールアドレスは test@example.com です。電話番号は 090-1234-5678 です。"
        
        masked = security.mask_pii(text)
        
        # メールアドレスがマスキングされている
        assert "[EMAIL]" in masked
        assert "test@example.com" not in masked
        
        # 電話番号がマスキングされている
        assert "[PHONE]" in masked
        assert "090-1234-5678" not in masked



