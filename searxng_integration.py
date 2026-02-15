#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SearXNG統合モジュール
ローカルLLM用の「実質無制限」Web検索エンジン統合
"""

import os
import json
import hashlib
import time
from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta
from pathlib import Path

import httpx

# ベースクラスのインポート
from base_integration import BaseIntegration

try:
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


class SearXNGIntegration(BaseIntegration):
    """SearXNG統合クラス"""
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        cache_dir: Optional[str] = None,
        cache_ttl: int = 3600,  # キャッシュ有効期限（秒、デフォルト1時間）
        enable_cache: bool = True
    ):
        """
        初期化
        
        Args:
            base_url: SearXNGサーバーのベースURL
            cache_dir: キャッシュディレクトリ（Noneの場合は自動生成）
            cache_ttl: キャッシュ有効期限（秒）
            enable_cache: キャッシュを有効にするか
        """
        super().__init__("SearXNG")
        
        # 環境変数から読み込む
        try:
            from dotenv import load_dotenv
            from pathlib import Path
            env_file = Path(__file__).parent / '.env'
            if env_file.exists():
                load_dotenv(env_file)
        except ImportError:
            pass
        
        self.base_url = (base_url or os.getenv("SEARXNG_BASE_URL", "http://127.0.0.1:8080")).rstrip("/")
        self.enable_cache = enable_cache
        self.cache_ttl = cache_ttl
        
        # キャッシュディレクトリの設定
        if cache_dir:
            self.cache_dir = Path(cache_dir)
        else:
            self.cache_dir = Path(__file__).parent / "data" / "searxng_cache"
        
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # HTTPクライアント
        self.client = None
        if REQUESTS_AVAILABLE:
            timeout = self.get_timeout("api_call")
            self.client = httpx.Client(timeout=timeout)
        
        # レート制限管理（連打防止）
        self._last_request_time = 0
        self._min_request_interval = 0.5  # 最低0.5秒間隔
    
    def _initialize_internal(self) -> bool:
        """
        内部初期化
        
        Returns:
            初期化成功かどうか
        """
        if not REQUESTS_AVAILABLE:
            self.logger.warning("httpxライブラリがインストールされていません")
            return False
        
        # 接続テスト
        try:
            response = self.client.get(f"{self.base_url}/", timeout=5)
            if response.status_code == 200:
                self.logger.info(f"SearXNGサーバーに接続しました: {self.base_url}")
                return True
            else:
                self.logger.warning(f"SearXNGサーバーへの接続に失敗: {response.status_code}")
                return False
        except Exception as e:
            self.logger.warning(f"SearXNGサーバーへの接続テストに失敗: {e}")
            return False
    
    def _check_availability_internal(self) -> bool:
        """
        内部の利用可能性チェック
        
        Returns:
            利用可能かどうか
        """
        return REQUESTS_AVAILABLE and self.client is not None
    
    def _get_cache_key(self, query: str, **kwargs) -> str:
        """
        キャッシュキーを生成
        
        Args:
            query: 検索クエリ
            **kwargs: その他のパラメータ
        
        Returns:
            キャッシュキー（ハッシュ）
        """
        cache_data = {
            "query": query.lower().strip(),
            **kwargs
        }
        cache_str = json.dumps(cache_data, sort_keys=True)
        return hashlib.md5(cache_str.encode()).hexdigest()
    
    def _get_cache_path(self, cache_key: str) -> Path:
        """
        キャッシュファイルのパスを取得
        
        Args:
            cache_key: キャッシュキー
        
        Returns:
            キャッシュファイルのパス
        """
        return self.cache_dir / f"{cache_key}.json"
    
    def _load_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """
        キャッシュから結果を読み込む
        
        Args:
            cache_key: キャッシュキー
        
        Returns:
            キャッシュされた結果（有効期限内の場合）、またはNone
        """
        if not self.enable_cache:
            return None
        
        cache_path = self._get_cache_path(cache_key)
        
        if not cache_path.exists():
            return None
        
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                cached_data = json.load(f)
            
            # 有効期限チェック
            cached_time = datetime.fromisoformat(cached_data.get("timestamp", ""))
            if datetime.now() - cached_time > timedelta(seconds=self.cache_ttl):
                # 期限切れの場合は削除
                cache_path.unlink()
                return None
            
            self.logger.debug(f"キャッシュから結果を読み込み: {cache_key[:16]}...")
            return cached_data.get("results")
        
        except Exception as e:
            self.logger.warning(f"キャッシュ読み込みエラー: {e}")
            return None
    
    def _save_cache(self, cache_key: str, results: Dict[str, Any]):
        """
        結果をキャッシュに保存
        
        Args:
            cache_key: キャッシュキー
            results: 検索結果
        """
        if not self.enable_cache:
            return
        
        cache_path = self._get_cache_path(cache_key)
        
        try:
            cache_data = {
                "timestamp": datetime.now().isoformat(),
                "results": results
            }
            
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
            
            self.logger.debug(f"結果をキャッシュに保存: {cache_key[:16]}...")
        
        except Exception as e:
            self.logger.warning(f"キャッシュ保存エラー: {e}")
    
    def _rate_limit(self):
        """レート制限（連打防止）"""
        current_time = time.time()
        elapsed = current_time - self._last_request_time
        
        if elapsed < self._min_request_interval:
            sleep_time = self._min_request_interval - elapsed
            time.sleep(sleep_time)
        
        self._last_request_time = time.time()
    
    def search(
        self,
        query: str,
        categories: Optional[List[str]] = None,
        engines: Optional[List[str]] = None,
        language: str = "ja",
        safesearch: int = 1,  # 0=off, 1=moderate, 2=strict
        time_range: Optional[str] = None,  # "day", "week", "month", "year"
        max_results: int = 10
    ) -> Dict[str, Any]:
        """
        Web検索を実行
        
        Args:
            query: 検索クエリ
            categories: 検索カテゴリ（例: ["general", "images"]）
            engines: 使用する検索エンジン（例: ["google", "bing"]）
            language: 言語コード（デフォルト: "ja"）
            safesearch: セーフサーチレベル（0=off, 1=moderate, 2=strict）
            time_range: 時間範囲フィルタ
            max_results: 最大結果数
        
        Returns:
            検索結果の辞書
        """
        if not self.is_available():
            return {
                "error": "SearXNGが利用できません",
                "results": [],
                "count": 0
            }
        
        # レート制限
        self._rate_limit()
        
        # キャッシュキー生成
        cache_key = self._get_cache_key(
            query,
            categories=categories,
            engines=engines,
            language=language,
            safesearch=safesearch,
            time_range=time_range,
            max_results=max_results
        )
        
        # キャッシュから読み込み
        cached_results = self._load_cache(cache_key)
        if cached_results is not None:
            self.logger.info(f"キャッシュから検索結果を返却: {query[:50]}...")
            return cached_results
        
        # SearXNG APIを呼び出し
        try:
            params = {
                "q": query,
                "format": "json",
                "language": language,
                "safesearch": safesearch
            }
            
            if categories:
                params["categories"] = ",".join(categories)
            
            if engines:
                params["engines"] = ",".join(engines)
            
            if time_range:
                params["time_range"] = time_range
            
            self.logger.info(f"SearXNGで検索実行: {query[:50]}...")
            response = self.client.get(
                f"{self.base_url}/search",
                params=params,
                timeout=self.get_timeout("api_call")
            )
            
            if response.status_code != 200:
                return {
                    "error": f"SearXNG APIエラー: HTTP {response.status_code}",
                    "results": [],
                    "count": 0
                }
            
            data = response.json()
            
            # 結果を整形
            results = []
            for result in data.get("results", [])[:max_results]:
                results.append({
                    "title": result.get("title", ""),
                    "url": result.get("url", ""),
                    "content": result.get("content", ""),
                    "engine": result.get("engine", ""),
                    "score": result.get("score", 0)
                })
            
            formatted_results = {
                "query": query,
                "results": results,
                "count": len(results),
                "total_results": data.get("number_of_results", 0),
                "timestamp": datetime.now().isoformat()
            }
            
            # キャッシュに保存
            self._save_cache(cache_key, formatted_results)
            
            return formatted_results
        
        except Exception as e:
            error = self.error_handler.handle_exception(
                e,
                context={"query": query, "base_url": self.base_url},
                user_message=f"検索の実行に失敗しました: {query}"
            )
            self.logger.error(f"検索エラー: {error.message}")
            return {
                "error": error.user_message or error.message,
                "results": [],
                "count": 0
            }
    
    def search_simple(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """
        シンプルな検索（結果のみ返す）
        
        Args:
            query: 検索クエリ
            max_results: 最大結果数
        
        Returns:
            検索結果のリスト
        """
        result = self.search(query, max_results=max_results)
        return result.get("results", [])
    
    def get_engines(self) -> List[str]:
        """
        利用可能な検索エンジンの一覧を取得
        
        Returns:
            検索エンジン名のリスト
        """
        if not self.is_available():
            return []
        
        try:
            response = self.client.get(
                f"{self.base_url}/engines",
                timeout=self.get_timeout("api_call")
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("engines", [])
            else:
                return []
        
        except Exception as e:
            self.logger.warning(f"検索エンジン一覧の取得に失敗: {e}")
            return []
    
    def clear_cache(self, older_than_days: Optional[int] = None):
        """
        キャッシュをクリア
        
        Args:
            older_than_days: 指定日数より古いキャッシュのみ削除（Noneの場合は全削除）
        """
        if not self.cache_dir.exists():
            return
        
        deleted_count = 0
        
        for cache_file in self.cache_dir.glob("*.json"):
            try:
                if older_than_days:
                    # ファイルの更新日時をチェック
                    file_time = datetime.fromtimestamp(cache_file.stat().st_mtime)
                    if datetime.now() - file_time < timedelta(days=older_than_days):
                        continue
                
                cache_file.unlink()
                deleted_count += 1
            
            except Exception as e:
                self.logger.warning(f"キャッシュファイル削除エラー: {e}")
        
        self.logger.info(f"キャッシュをクリアしました: {deleted_count}件削除")
    
    def get_status(self) -> Dict[str, Any]:
        """
        状態を取得
        
        Returns:
            状態の辞書
        """
        base_status = super().get_status()
        
        # キャッシュ統計
        cache_stats = {
            "enabled": self.enable_cache,
            "cache_dir": str(self.cache_dir),
            "cache_files": 0,
            "cache_size_mb": 0
        }
        
        if self.cache_dir.exists():
            cache_files = list(self.cache_dir.glob("*.json"))
            cache_stats["cache_files"] = len(cache_files)
            
            total_size = sum(f.stat().st_size for f in cache_files)
            cache_stats["cache_size_mb"] = round(total_size / (1024 * 1024), 2)
        
        # 検索エンジン情報
        engines = []
        try:
            engines = self.get_engines()
        except Exception:
            pass
        
        base_status.update({
            "base_url": self.base_url,
            "cache": cache_stats,
            "available_engines": len(engines),
            "engines": engines[:10] if engines else []  # 最初の10個のみ
        })
        
        return base_status

















