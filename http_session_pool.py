#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🌐 ManaOS HTTPセッションプール
HTTPセッションの再利用と最適化
"""

import requests
from typing import Dict, Optional, Any
from threading import Lock
from datetime import datetime, timedelta

# 統一モジュールのインポート
from manaos_logger import get_logger
from manaos_error_handler import ManaOSErrorHandler, ErrorCategory, ErrorSeverity
from manaos_timeout_config import get_timeout_config

# ロガーの初期化
logger = get_logger(__name__)

# エラーハンドラーの初期化
error_handler = ManaOSErrorHandler("HTTPSessionPool")

# タイムアウト設定の取得
timeout_config = get_timeout_config()


class HTTPSessionPool:
    """HTTPセッションプール"""
    
    def __init__(self, max_sessions: int = 20):
        """
        初期化
        
        Args:
            max_sessions: 最大セッション数
        """
        self.max_sessions = max_sessions
        self.sessions: Dict[str, requests.Session] = {}
        self.session_metadata: Dict[str, Dict[str, Any]] = {}
        self.lock = Lock()
        
        # 統計情報
        self.stats = {
            "sessions_created": 0,
            "sessions_reused": 0,
            "requests_made": 0
        }
        
        logger.info(f"HTTPセッションプールを初期化しました (最大セッション数: {max_sessions})")
    
    def get_session(
        self,
        base_url: str,
        headers: Optional[Dict[str, str]] = None,
        auth: Optional[tuple] = None,
        timeout: Optional[float] = None
    ) -> requests.Session:
        """
        セッションを取得（再利用可能）
        
        Args:
            base_url: ベースURL
            headers: ヘッダー
            auth: 認証情報
            timeout: タイムアウト
        
        Returns:
            HTTPセッション
        """
        # セッションキーを生成
        session_key = self._generate_session_key(base_url, headers, auth)
        
        with self.lock:
            # 既存のセッションをチェック
            if session_key in self.sessions:
                session = self.sessions[session_key]
                metadata = self.session_metadata[session_key]
                
                # セッションが有効かチェック（30分以内に使用されたか）
                last_used = datetime.fromisoformat(metadata["last_used"])
                if datetime.now() - last_used < timedelta(minutes=30):
                    metadata["last_used"] = datetime.now().isoformat()
                    metadata["use_count"] += 1
                    self.stats["sessions_reused"] += 1
                    logger.debug(f"セッションを再利用: {base_url}")
                    return session
                else:
                    # 期限切れのセッションを閉じる
                    try:
                        session.close()
                    except Exception:
                        logger.debug("期限切れセッションのクローズに失敗")
                    del self.sessions[session_key]
                    del self.session_metadata[session_key]
            
            # 新しいセッションを作成
            if len(self.sessions) >= self.max_sessions:
                # 最も古いセッションを削除
                oldest_key = min(
                    self.session_metadata.keys(),
                    key=lambda k: self.session_metadata[k]["last_used"]
                )
                try:
                    self.sessions[oldest_key].close()
                except Exception:
                    logger.debug("最古セッションのクローズに失敗")
                del self.sessions[oldest_key]
                del self.session_metadata[oldest_key]
            
            session = requests.Session()
            
            # デフォルトヘッダー
            default_headers = {
                "User-Agent": "ManaOS-HTTP-Client/1.0",
                "Accept": "application/json"
            }
            if headers:
                default_headers.update(headers)
            session.headers.update(default_headers)
            
            # 認証情報
            if auth:
                session.auth = auth
            
            # タイムアウト設定
            if timeout:
                session.timeout = timeout
            else:
                session.timeout = timeout_config.get("api_call", 10.0)
            
            # セッションを保存
            self.sessions[session_key] = session
            self.session_metadata[session_key] = {
                "base_url": base_url,
                "created_at": datetime.now().isoformat(),
                "last_used": datetime.now().isoformat(),
                "use_count": 1
            }
            
            self.stats["sessions_created"] += 1
            logger.debug(f"新しいセッションを作成: {base_url}")
            return session
    
    def _generate_session_key(
        self,
        base_url: str,
        headers: Optional[Dict[str, str]] = None,
        auth: Optional[tuple] = None
    ) -> str:
        """セッションキーを生成"""
        key_parts = [base_url]
        if headers:
            key_parts.append(str(sorted(headers.items())))
        if auth:
            key_parts.append(f"auth:{auth[0]}")
        return "|".join(key_parts)
    
    def request(
        self,
        method: str,
        url: str,
        base_url: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        auth: Optional[tuple] = None,
        **kwargs
    ) -> requests.Response:
        """
        HTTPリクエストを実行
        
        Args:
            method: HTTPメソッド
            url: URL
            base_url: ベースURL（セッションキー生成用）
            headers: ヘッダー
            auth: 認証情報
            **kwargs: その他のリクエストパラメータ
        
        Returns:
            HTTPレスポンス
        """
        if base_url is None:
            # URLからベースURLを抽出
            from urllib.parse import urlparse
            parsed = urlparse(url)
            base_url = f"{parsed.scheme}://{parsed.netloc}"
        
        session = self.get_session(base_url, headers, auth)
        
        self.stats["requests_made"] += 1
        
        try:
            response = session.request(method, url, **kwargs)
            response.raise_for_status()
            return response
        except Exception as e:
            error = error_handler.handle_exception(
                e,
                context={"method": method, "url": url},
                user_message="HTTPリクエストの実行に失敗しました"
            )
            logger.error(f"HTTPリクエストエラー: {error.message}")
            raise
    
    def close_all(self):
        """すべてのセッションを閉じる"""
        with self.lock:
            for session in self.sessions.values():
                try:
                    session.close()
                except Exception:
                    logger.debug("セッションのクローズに失敗")
            self.sessions.clear()
            self.session_metadata.clear()
        
        logger.info("すべてのセッションを閉じました")
    
    def get_stats(self) -> Dict[str, Any]:
        """統計情報を取得"""
        total_sessions = self.stats["sessions_created"]
        reuse_rate = (
            self.stats["sessions_reused"] / (self.stats["sessions_reused"] + total_sessions) * 100
            if (self.stats["sessions_reused"] + total_sessions) > 0 else 0
        )
        
        return {
            **self.stats,
            "active_sessions": len(self.sessions),
            "reuse_rate": reuse_rate
        }


# グローバルインスタンス
_http_session_pool: Optional[HTTPSessionPool] = None


def get_http_session_pool() -> HTTPSessionPool:
    """HTTPセッションプールのシングルトンインスタンスを取得"""
    global _http_session_pool
    if _http_session_pool is None:
        _http_session_pool = HTTPSessionPool()
    return _http_session_pool


def main():
    """テスト用メイン関数"""
    print("HTTPセッションプールテスト")
    print("=" * 60)
    
    pool = get_http_session_pool()
    
    # テストリクエスト
    try:
        response = pool.request(
            "GET",
            "https://httpbin.org/get",
            base_url="https://httpbin.org"
        )
        print(f"レスポンスステータス: {response.status_code}")
    except Exception as e:
        print(f"リクエストエラー: {e}")
    
    # 統計情報
    print("\n統計情報:")
    stats = pool.get_stats()
    print(f"  作成されたセッション: {stats['sessions_created']}")
    print(f"  再利用されたセッション: {stats['sessions_reused']}")
    print(f"  再利用率: {stats['reuse_rate']:.1f}%")
    
    pool.close_all()


if __name__ == "__main__":
    main()






















