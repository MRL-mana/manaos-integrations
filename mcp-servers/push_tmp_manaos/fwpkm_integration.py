#!/usr/bin/env python3
"""
FWPKM統合システム
既存RAGメモリシステムとの統合
"""

from typing import Dict, Any, Optional, List
from pathlib import Path
import os
import yaml

try:
    from manaos_integrations._paths import OLLAMA_PORT
except Exception:  # pragma: no cover
    try:
        from _paths import OLLAMA_PORT  # type: ignore
    except Exception:  # pragma: no cover
        OLLAMA_PORT = int(os.getenv("OLLAMA_PORT", "11434"))


DEFAULT_OLLAMA_URL = os.getenv("OLLAMA_URL", f"http://127.0.0.1:{OLLAMA_PORT}")

# 既存システムのインポート
try:
    from rag_memory_enhanced import RAGMemoryEnhanced
    RAG_MEMORY_AVAILABLE = True
except ImportError:
    RAG_MEMORY_AVAILABLE = False

try:
    from memory_unified import UnifiedMemory
    UNIFIED_MEMORY_AVAILABLE = True
except ImportError:
    UNIFIED_MEMORY_AVAILABLE = False

from fwpkm_core import ChunkMemoryProcessor, InferenceMemoryUpdater

# 統一モジュールのインポート
try:
    from unified_logging import get_service_logger
    logger = get_service_logger("fwpkm-integration")
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class UnifiedMemorySystem:
    """
    長期記憶（RAG）と短期記憶（FWPKM）を統合
    """
    
    def __init__(
        self,
        config_path: Optional[Path] = None,
        rag_memory: Optional[RAGMemoryEnhanced] = None,
        chunk_processor: Optional[ChunkMemoryProcessor] = None
    ):
        """
        初期化
        
        Args:
            config_path: 設定ファイルのパス
            rag_memory: RAGメモリインスタンス（Noneの場合は自動初期化）
            chunk_processor: チャンクプロセッサ（Noneの場合は自動初期化）
        """
        # 設定を読み込み
        if config_path is None:
            config_path = Path(__file__).parent / "fwpkm_config.yaml"
        
        self.config = self._load_config(config_path)
        
        # 長期記憶（RAG）の初期化
        if rag_memory is None and RAG_MEMORY_AVAILABLE:
            try:
                self.rag_memory = RAGMemoryEnhanced()  # type: ignore[possibly-unbound]
                logger.info("✅ RAGメモリシステムを初期化しました")
            except Exception as e:
                logger.warning(f"RAGメモリの初期化に失敗: {e}")
                self.rag_memory = None
        else:
            self.rag_memory = rag_memory
        
        # 短期記憶（FWPKM）の初期化
        if chunk_processor is None:
            chunk_config = self.config.get("memory", {}).get("short_term", {})
            self.chunk_processor = ChunkMemoryProcessor(
                chunk_size=self.config.get("chunk_processing", {}).get("chunk_size", 2048),
                memory_slots=chunk_config.get("memory_slots", 10000),
                key1_slots=chunk_config.get("key1_slots", 100),
                key2_slots=chunk_config.get("key2_slots", 100),
                value_dim=chunk_config.get("value_dim", 768),
                update_rate=chunk_config.get("update_rate", 0.1),
                learning_rate=chunk_config.get("learning_rate", 0.01)
            )
            logger.info("✅ チャンクメモリプロセッサを初期化しました")
        else:
            self.chunk_processor = chunk_processor
        
        # 推論時メモリ更新器
        self.memory_updater = InferenceMemoryUpdater(
            chunk_processor=self.chunk_processor,
            ollama_url=self.config.get("ollama_url", DEFAULT_OLLAMA_URL)
        )
        
        # 統合設定
        self.unified_config = self.config.get("memory", {}).get("unified", {})
        self.balance_weight = self.unified_config.get("balance_weight", 0.5)
        
        logger.info("✅ 統合メモリシステム初期化完了")
    
    def _load_config(self, config_path: Path) -> Dict[str, Any]:
        """設定ファイルを読み込み"""
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f)
            except Exception as e:
                logger.warning(f"設定ファイルの読み込みエラー: {e}")
        
        # デフォルト設定
        return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """デフォルト設定"""
        return {
            "ollama_url": DEFAULT_OLLAMA_URL,
            "chunk_processing": {
                "enabled": True,
                "chunk_size": 2048,
                "overlap": 256,
                "min_chunk_size": 512
            },
            "memory": {
                "short_term": {
                    "enabled": True,
                    "memory_slots": 10000,
                    "key1_slots": 100,
                    "key2_slots": 100,
                    "value_dim": 768,
                    "update_rate": 0.1,
                    "learning_rate": 0.01
                },
                "long_term": {
                    "enabled": True,
                    "importance_threshold": 0.7,
                    "auto_promote": True
                },
                "unified": {
                    "enabled": True,
                    "balance_weight": 0.5
                }
            },
            "collapse_prevention": {
                "enabled": True,
                "usage_variance_threshold": 0.8,
                "rebalance_interval": 100,
                "unused_slot_threshold": 0.1
            },
            "gating": {
                "enabled": True,
                "confidence_threshold": 0.7,
                "high_gate_weight": 0.8,
                "low_gate_weight": 0.3,
                "adaptive": True
            },
            "long_context": {
                "enabled": True,
                "max_context_length": 128000,
                "chunk_processing_threshold": 4096,
                "accumulation_strategy": "important_only"
            },
            "review_effect": {
                "enabled": True,
                "review_threshold": 2,
                "memory_enhancement_rate": 0.2
            }
        }
    
    def process_with_memory(
        self,
        text: str,
        session_id: str,
        use_long_term: bool = True,
        use_short_term: bool = True
    ) -> Dict[str, Any]:
        """
        長期記憶と短期記憶の両方を使用して処理
        
        Args:
            text: 入力テキスト
            session_id: セッションID
            use_long_term: 長期記憶を使用するか
            use_short_term: 短期記憶を使用するか
        
        Returns:
            処理結果
        """
        results = {
            "long_term_results": [],
            "short_term_results": [],
            "unified_context": ""
        }
        
        # 長期記憶から検索
        if use_long_term and self.rag_memory:
            try:
                long_term_results = self.rag_memory.search_memories(text, limit=5)
                results["long_term_results"] = [
                    {
                        "entry_id": m.entry_id,
                        "content": m.content[:200],  # 最初の200文字
                        "importance_score": m.importance_score
                    }
                    for m in long_term_results
                ]
            except Exception as e:
                logger.warning(f"長期記憶検索エラー: {e}")
        
        # 短期記憶から検索
        if use_short_term:
            try:
                short_term_results = self.chunk_processor.retrieve_from_memory(
                    text,
                    session_id,
                    top_k=5
                )
                results["short_term_results"] = short_term_results
            except Exception as e:
                logger.warning(f"短期記憶検索エラー: {e}")
        
        # 統合コンテキストを構築
        results["unified_context"] = self._build_unified_context(
            results["long_term_results"],
            results["short_term_results"]
        )
        
        return results
    
    def _build_unified_context(
        self,
        long_term_results: List[Dict[str, Any]],
        short_term_results: List[Dict[str, Any]]
    ) -> str:
        """
        統合コンテキストを構築
        
        Args:
            long_term_results: 長期記憶の検索結果
            short_term_results: 短期記憶の検索結果
        
        Returns:
            統合コンテキスト
        """
        context_parts = []
        
        # 長期記憶のコンテキスト
        if long_term_results:
            context_parts.append("## 長期記憶（関連情報）")
            for result in long_term_results:
                context_parts.append(f"- {result['content']}")
        
        # 短期記憶のコンテキスト
        if short_term_results:
            context_parts.append("## 短期記憶（最近の情報）")
            for result in short_term_results[:3]:  # 上位3件
                context_parts.append(
                    f"- スロット{result['slot_index']}: "
                    f"類似度={result['similarity']:.3f}"
                )
        
        return "\n".join(context_parts)
    
    def update_memory_hierarchy(
        self,
        content: str,
        importance: float,
        session_id: str
    ):
        """
        メモリ階層を更新
        
        - 重要度が高い → 長期記憶（RAG）に保存
        - 重要度が低い → 短期記憶（FWPKM）のみ
        
        Args:
            content: コンテンツ
            importance: 重要度（0.0-1.0）
            session_id: セッションID
        """
        threshold = self.config.get("memory", {}).get("long_term", {}).get(
            "importance_threshold", 0.7
        )
        
        if importance >= threshold and self.rag_memory:
            # 長期記憶に保存
            try:
                self.rag_memory.add_memory(
                    content=content,
                    force_importance=importance
                )
                logger.info(f"長期記憶に保存: 重要度={importance:.2f}")
            except Exception as e:
                logger.warning(f"長期記憶への保存エラー: {e}")
        
        # 短期記憶にも一時的に保存（セッション中）
        # これは推論中に自動的に行われる
    
    def process_long_text(
        self,
        text: str,
        model: str,
        session_id: str,
        use_memory: bool = True
    ):
        """
        長文を処理（チャンク処理 + メモリ更新）
        
        Args:
            text: 入力テキスト
            model: 使用モデル
            session_id: セッションID
            use_memory: メモリを使用するか
        
        Yields:
            処理結果
        """
        # メモリから関連情報を取得
        memory_context = ""
        if use_memory:
            memory_results = self.process_with_memory(text, session_id)
            memory_context = memory_results["unified_context"]
        
        # 長文をチャンク処理
        for result in self.memory_updater.process_long_text(
            text=text,
            model=model,
            session_id=session_id
        ):
            # メモリコンテキストを追加
            result["memory_context"] = memory_context
            yield result
    
    def search_memory(
        self,
        query: str,
        session_id: Optional[str] = None,
        scope: str = "all"
    ) -> Dict[str, Any]:
        """
        メモリから検索
        
        Args:
            query: 検索クエリ
            session_id: セッションID
            scope: スコープ（"all", "long_term", "short_term"）
        
        Returns:
            検索結果
        """
        results = {
            "long_term": [],
            "short_term": [],
            "unified": []
        }
        
        # 長期記憶から検索
        if scope in ["all", "long_term"] and self.rag_memory:
            try:
                long_term_results = self.rag_memory.search_memories(query, limit=10)
                results["long_term"] = [
                    {
                        "entry_id": m.entry_id,
                        "content": m.content,
                        "importance_score": m.importance_score
                    }
                    for m in long_term_results
                ]
            except Exception as e:
                logger.warning(f"長期記憶検索エラー: {e}")
        
        # 短期記憶から検索
        if scope in ["all", "short_term"]:
            try:
                short_term_results = self.chunk_processor.retrieve_from_memory(
                    query,
                    session_id,
                    top_k=10
                )
                results["short_term"] = short_term_results
            except Exception as e:
                logger.warning(f"短期記憶検索エラー: {e}")
        
        # 統合結果
        results["unified"] = self._merge_search_results(
            results["long_term"],
            results["short_term"]
        )
        
        return results
    
    def _merge_search_results(
        self,
        long_term: List[Dict[str, Any]],
        short_term: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """検索結果を統合"""
        merged = []
        
        # 長期記憶を追加
        for result in long_term:
            merged.append({
                "type": "long_term",
                "source": "rag_memory",
                **result
            })
        
        # 短期記憶を追加
        for result in short_term:
            merged.append({
                "type": "short_term",
                "source": "fwpkm",
                **result
            })
        
        # 重要度/類似度でソート
        merged.sort(
            key=lambda x: x.get("importance_score", x.get("similarity", 0)),
            reverse=True
        )
        
        return merged
    
    def apply_review_effect(
        self,
        text: str,
        session_id: str,
        review_count: int = 1
    ) -> Dict[str, Any]:
        """
        復習効果を適用
        
        Args:
            text: 復習するテキスト
            session_id: セッションID
            review_count: 復習回数
        
        Returns:
            復習結果
        """
        review_config = self.config.get("review_effect", {})
        enhancement_rate = review_config.get("memory_enhancement_rate", 0.2)
        
        # 復習回数に応じてメモリを強化
        for i in range(review_count):
            # チャンク処理を実行（メモリが強化される）
            chunks = self.memory_updater._split_into_chunks(text)
            
            for chunk in chunks:
                # メモリを更新（強化率を適用）
                # 簡易実装：学習率を増やす
                original_lr = self.chunk_processor.learning_rate
                self.chunk_processor.learning_rate = original_lr * (1 + enhancement_rate * (i + 1))
                
                # チャンクを処理
                self.chunk_processor.process_chunk(
                    chunk_text=chunk,
                    model_output="",  # 復習時は出力なし
                    session_id=session_id,
                    target=None
                )
                
                # 学習率を戻す
                self.chunk_processor.learning_rate = original_lr
        
        return {
            "review_count": review_count,
            "enhancement_rate": enhancement_rate,
            "memory_state": self.chunk_processor._get_memory_state()
        }
    
    def get_session_memory_state(
        self,
        session_id: str
    ) -> Dict[str, Any]:
        """
        セッションのメモリ状態を取得
        
        Args:
            session_id: セッションID
        
        Returns:
            メモリ状態
        """
        session_state = self.chunk_processor.session_states.get(session_id, {})
        
        return {
            "session_id": session_id,
            "chunk_count": session_state.get("chunk_count", 0),
            "slots_used": len(session_state.get("slots_used", set())),
            "created_at": session_state.get("created_at"),
            "last_updated": session_state.get("last_updated"),
            "memory_state": self.chunk_processor._get_memory_state()
        }
    
    def save_state(self, file_path: Path):
        """メモリ状態を保存"""
        self.chunk_processor.save_state(file_path)
        logger.info(f"メモリ状態を保存: {file_path}")
    
    def load_state(self, file_path: Path):
        """メモリ状態を読み込み"""
        self.chunk_processor.load_state(file_path)
        logger.info(f"メモリ状態を読み込み: {file_path}")
