#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ManaOS 全強化ポイント動作確認スクリプト
"""

import sys
import os

# WindowsのコンソールエンコーディングをUTF-8に設定
if sys.platform == 'win32':
    import io
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

print("=" * 60)
print("ManaOS 全強化ポイント動作確認")
print("=" * 60)

# 1. 認証・認可システム
print("\n[1] 認証・認可システムテスト...")
try:
    from auth_system import AuthSystem, Role
    import time
    auth = AuthSystem()
    
    # ユーザー作成（既存ユーザーを避けるためタイムスタンプを使用）
    timestamp = int(time.time())
    username = f"test_user_{timestamp}"
    email = f"test_{timestamp}@example.com"
    user = auth.create_user(username, email, Role.USER)
    print(f"[OK] ユーザー作成成功: {user.user_id}")
    
    # APIキー作成
    api_key = auth.create_api_key(user.user_id, Role.USER)
    print(f"[OK] APIキー作成成功: {api_key[:20]}...")
    
    # APIキー検証
    verified = auth.verify_api_key(api_key)
    if verified:
        print(f"[OK] APIキー検証成功: {verified.user_id}")
    else:
        print("[NG] APIキー検証失敗")
    
    # トークン作成
    token = auth.create_token(user.user_id)
    print(f"[OK] トークン作成成功: {token[:30]}...")
    
    # トークン検証
    payload = auth.verify_token(token)
    if payload:
        print(f"[OK] トークン検証成功: {payload.get('user_id')}")
    else:
        print("[NG] トークン検証失敗")
    
    print("[OK] 認証・認可システム: 正常動作")
except Exception as e:
    print(f"[NG] 認証・認可システムエラー: {e}")
    import traceback
    traceback.print_exc()

# 2. 入力検証システム
print("\n[2] 入力検証システムテスト...")
try:
    from input_validator import InputValidator
    validator = InputValidator()
    
    # メール検証
    is_valid, error = validator.validate_input("test@example.com", input_type="email")
    if is_valid:
        print("[OK] メール検証成功")
    else:
        print(f"[NG] メール検証失敗: {error}")
    
    # SQLインジェクションチェック
    is_safe = validator.validate_sql_injection("SELECT * FROM users")
    if not is_safe:
        print("[OK] SQLインジェクション検出成功")
    else:
        print("[NG] SQLインジェクション検出失敗")
    
    # XSSチェック
    is_safe = validator.validate_xss("<script>alert('XSS')</script>")
    if not is_safe:
        print("[OK] XSS検出成功")
    else:
        print("[NG] XSS検出失敗")
    
    # サニタイズ
    sanitized = validator.sanitize_string("<script>alert('XSS')</script>")
    if "&lt;script&gt;" in sanitized:
        print("[OK] サニタイズ成功")
    else:
        print("[NG] サニタイズ失敗")
    
    print("[OK] 入力検証システム: 正常動作")
except Exception as e:
    print(f"[NG] 入力検証システムエラー: {e}")
    import traceback
    traceback.print_exc()

# 3. Redis分散キャッシュシステム
print("\n[3] Redis分散キャッシュシステムテスト...")
try:
    from redis_cache import RedisCache
    redis_cache = RedisCache()
    
    if redis_cache.redis_client:
        # キャッシュ保存
        redis_cache.set("test_cache", {"result": "test_value"}, test_key="test")
        print("[OK] Redisキャッシュ保存成功")
        
        # キャッシュ取得
        value = redis_cache.get("test_cache", test_key="test")
        if value and value.get("result") == "test_value":
            print("[OK] Redisキャッシュ取得成功")
        else:
            print("[NG] Redisキャッシュ取得失敗")
        
        print("[OK] Redis分散キャッシュシステム: 正常動作")
    else:
        print("[WARN] Redisが利用できません（ローカルキャッシュのみ使用可能）")
except Exception as e:
    print(f"[NG] Redis分散キャッシュシステムエラー: {e}")
    import traceback
    traceback.print_exc()

# 4. 自動バックアップ・復旧システム
print("\n[4] 自動バックアップ・復旧システムテスト...")
try:
    from backup_system import BackupSystem
    backup = BackupSystem()
    
    # バックアップ作成
    backup_info = backup.create_backup(backup_type="full")
    print(f"[OK] バックアップ作成成功: {backup_info.backup_id}")
    
    # バックアップ検証
    is_valid = backup.verify_backup(backup_info)
    if is_valid:
        print("[OK] バックアップ検証成功")
    else:
        print("[NG] バックアップ検証失敗")
    
    print("[OK] 自動バックアップ・復旧システム: 正常動作")
except Exception as e:
    print(f"[NG] 自動バックアップ・復旧システムエラー: {e}")
    import traceback
    traceback.print_exc()

# 5. 動的レート制限システム
print("\n[5] 動的レート制限システムテスト...")
try:
    from dynamic_rate_limiter import DynamicRateLimiter, Priority
    limiter = DynamicRateLimiter()
    
    # レート制限チェック
    allowed = limiter.check_rate_limit("test_user", Priority.MEDIUM)
    if allowed:
        print("[OK] レート制限チェック成功")
    else:
        print("[NG] レート制限チェック失敗")
    
    # レート制限情報取得
    info = limiter.get_rate_limit_info("test_user")
    if info:
        print(f"[OK] レート制限情報取得成功: {info.get('current_rate')}")
    else:
        print("[NG] レート制限情報取得失敗")
    
    print("[OK] 動的レート制限システム: 正常動作")
except Exception as e:
    print(f"[NG] 動的レート制限システムエラー: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("全強化ポイント動作確認完了")
print("=" * 60)

