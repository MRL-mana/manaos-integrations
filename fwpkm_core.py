#!/usr/bin/env python3
"""
FWPKM Core Implementation
推論中メモリ更新システム（プロトタイプ）
"""

import numpy as np
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from pathlib import Path
import json
import hashlib
from datetime import datetime
import os

try:
    from manaos_integrations._paths import OLLAMA_PORT
except Exception:  # pragma: no cover
    try:
        from _paths import OLLAMA_PORT  # type: ignore
    except Exception:  # pragma: no cover
        OLLAMA_PORT = int(os.getenv("OLLAMA_PORT", "11434"))


DEFAULT_OLLAMA_URL = os.getenv("OLLAMA_URL", f"http://127.0.0.1:{OLLAMA_PORT}")

# 統一モジュールのインポート
try:
    from manaos_logger import get_logger
    logger = get_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


@dataclass
class MemorySlot:
    """メモリスロット"""
    key1_index: int
    key2_index: int
    value: np.ndarray
    usage_count: int
    last_updated: str
    confidence: float


@dataclass
class ChunkProcessResult:
    """チャンク処理結果"""
    chunk_index: int
    chunk_length: int
    slots_updated: int
    memory_state: Dict[str, Any]
    processing_time: float


class ChunkMemoryProcessor:
    """
    推論中のチャンク処理とメモリ更新
    FWPKMの核心実装
    """
    
    def __init__(
        self,
        chunk_size: int = 2048,
        memory_slots: int = 10000,
        key1_slots: int = 100,
        key2_slots: int = 100,
        value_dim: int = 768,
        update_rate: float = 0.1,
        learning_rate: float = 0.01
    ):
        """
        初期化
        
        Args:
            chunk_size: チャンクサイズ（トークン数）
            memory_slots: メモリスロット数
            key1_slots: Key1スロット数
            key2_slots: Key2スロット数
            value_dim: Value次元
            update_rate: 更新率
            learning_rate: 学習率
        """
        self.chunk_size = chunk_size
        self.memory_slots = memory_slots
        self.key1_slots = key1_slots
        self.key2_slots = key2_slots
        self.value_dim = value_dim
        self.update_rate = update_rate
        self.learning_rate = learning_rate
        
        # メモリ構造（Product Key方式）
        # Value行列: [key1_slots, key2_slots, value_dim]
        self.value_matrix = np.random.normal(
            0, 0.1, 
            (key1_slots, key2_slots, value_dim)
        )
        
        # 使用頻度追跡（崩壊防止用）
        self.slot_usage = np.zeros((key1_slots, key2_slots))
        
        # ゲーティング機構
        self.gate_weight = 0.5  # デフォルトゲート重み
        self.confidence_threshold = 0.7
        
        # セッション管理
        self.session_states: Dict[str, Dict[str, Any]] = {}
        
        logger.info(f"✅ ChunkMemoryProcessor初期化完了: {memory_slots}スロット")
    
    def process_chunk(
        self,
        chunk_text: str,
        model_output: str,
        session_id: str,
        target: Optional[str] = None
    ) -> ChunkProcessResult:
        """
        チャンクを処理してメモリを更新
        
        Args:
            chunk_text: 入力チャンク
            model_output: モデルの出力
            session_id: セッションID
            target: 教師信号（オプション）
        
        Returns:
            処理結果
        """
        import time
        start_time = time.time()
        
        # 1. チャンクから重要情報を抽出（簡易実装）
        key_vectors = self._extract_keys(chunk_text)
        
        # 2. メモリスロットを選択（Product Key方式）
        slot_indices = self._select_slots(key_vectors)
        
        # 3. MSE lossでメモリを更新
        if target:
            self._update_memory_mse(slot_indices, model_output, target)
        else:
            # 自己教師学習的な更新
            self._update_memory_self_supervised(
                slot_indices, 
                chunk_text, 
                model_output
            )
        
        # 4. 使用頻度を更新
        self._update_usage(slot_indices)
        
        # 5. メモリ崩壊防止チェック
        self._prevent_collapse()
        
        # 6. セッション状態を更新
        self._update_session_state(session_id, slot_indices)
        
        processing_time = time.time() - start_time
        
        return ChunkProcessResult(
            chunk_index=self.session_states.get(session_id, {}).get("chunk_count", 0),
            chunk_length=len(chunk_text),
            slots_updated=len(slot_indices),
            memory_state=self._get_memory_state(),
            processing_time=processing_time
        )
    
    def _extract_keys(self, text: str) -> np.ndarray:
        """
        テキストからキーベクトルを抽出
        
        Note: 簡易実装。本番では専用のエンコーダーを使用
        """
        # 簡易実装：テキストのハッシュからベクトルを生成
        text_hash = hashlib.sha256(text.encode()).hexdigest()
        
        # ハッシュから固定長ベクトルを生成
        vector = np.zeros(self.value_dim)
        for i in range(min(len(text_hash), self.value_dim)):
            vector[i] = ord(text_hash[i]) / 255.0
        
        # 正規化
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm
        
        return vector
    
    def _select_slots(
        self, 
        key_vector: np.ndarray,
        top_k: int = 5
    ) -> List[Tuple[int, int]]:
        """
        Product Key方式でスロットを選択
        
        Args:
            key_vector: キーベクトル
            top_k: 選択するスロット数
        
        Returns:
            選択されたスロットのインデックスリスト
        """
        # Key1とKey2を別々に選択
        # 簡易実装：コサイン類似度で選択
        
        # Key1の選択（最初の半分の次元を使用）
        key1_dim = self.value_dim // 2
        key1_vector = key_vector[:key1_dim]
        
        # Key2の選択（後半の次元を使用）
        key2_dim = self.value_dim - key1_dim
        key2_vector = key_vector[key1_dim:]
        
        # 各Keyスロットとの類似度を計算
        # 簡易実装：ランダム選択（本番では適切な類似度計算を実装）
        selected_slots = []
        
        for _ in range(top_k):
            # ランダムにスロットを選択（本番では類似度ベース）
            i = np.random.randint(0, self.key1_slots)
            j = np.random.randint(0, self.key2_slots)
            selected_slots.append((i, j))
        
        return selected_slots
    
    def _update_memory_mse(
        self,
        slot_indices: List[Tuple[int, int]],
        model_output: str,
        target: str
    ):
        """
        MSE lossでメモリを更新
        
        Args:
            slot_indices: 更新するスロットのインデックス
            model_output: モデルの出力
            target: ターゲット値
        """
        # 簡易実装：テキストをベクトル化
        output_vector = self._text_to_vector(model_output)
        target_vector = self._text_to_vector(target)
        
        # MSE lossを計算
        mse_loss = np.mean((output_vector - target_vector) ** 2)
        
        # 勾配を計算
        gradient = 2 * (output_vector - target_vector) / len(output_vector)
        
        # 各スロットを更新
        for i, j in slot_indices:
            # ゲーティングで更新量を調整
            gate = self._calculate_gate(i, j)
            update = self.learning_rate * gate * gradient
            
            # Value行列を更新
            self.value_matrix[i, j] += update
            
            logger.debug(f"スロット({i},{j})を更新: gate={gate:.3f}, mse={mse_loss:.4f}")
    
    def _update_memory_self_supervised(
        self,
        slot_indices: List[Tuple[int, int]],
        chunk_text: str,
        model_output: str
    ):
        """
        自己教師学習的なメモリ更新
        
        Args:
            slot_indices: 更新するスロットのインデックス
            chunk_text: チャンクテキスト
            model_output: モデルの出力
        """
        # チャンクテキストから重要情報を抽出
        chunk_vector = self._text_to_vector(chunk_text)
        output_vector = self._text_to_vector(model_output)
        
        # 出力がチャンクの情報を反映しているかを学習
        # 簡易実装：出力とチャンクの類似度を最大化
        similarity = np.dot(chunk_vector, output_vector) / (
            np.linalg.norm(chunk_vector) * np.linalg.norm(output_vector) + 1e-8
        )
        
        # 類似度を高める方向に更新
        gradient = (chunk_vector - output_vector) * (1 - similarity)
        
        for i, j in slot_indices:
            gate = self._calculate_gate(i, j)
            update = self.learning_rate * gate * gradient * self.update_rate
            
            self.value_matrix[i, j] += update
    
    def _text_to_vector(self, text: str) -> np.ndarray:
        """テキストをベクトルに変換（簡易実装）"""
        # 簡易実装：文字コードの平均
        if len(text) == 0:
            return np.zeros(self.value_dim)
        
        vector = np.zeros(self.value_dim)
        for i, char in enumerate(text[:self.value_dim]):
            vector[i] = ord(char) / 255.0
        
        # 正規化
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm
        
        return vector
    
    def _calculate_gate(
        self,
        slot_index: Tuple[int, int],
        confidence_threshold: Optional[float] = None
    ) -> float:
        """
        ゲート重みを計算
        
        Args:
            slot_index: スロットインデックス
            confidence_threshold: 信頼度閾値
        
        Returns:
            ゲート重み（0.0-1.0）
        """
        if confidence_threshold is None:
            confidence_threshold = self.confidence_threshold
        
        i, j = slot_index
        
        # スロットの信頼度を計算（使用頻度ベース）
        usage = self.slot_usage[i, j]
        confidence = min(1.0, usage / 10.0)  # 簡易実装
        
        # 信頼度が閾値以上なら高ゲート、以下なら低ゲート
        if confidence >= confidence_threshold:
            return 0.8  # 高ゲート
        else:
            return 0.3  # 低ゲート
    
    def _update_usage(self, slot_indices: List[Tuple[int, int]]):
        """使用頻度を更新"""
        for i, j in slot_indices:
            self.slot_usage[i, j] += 1
    
    def _prevent_collapse(self, threshold: float = 0.8):
        """
        メモリ崩壊を防止
        
        Args:
            threshold: 使用頻度分散の閾値
        """
        # 使用頻度の分散を計算
        usage_variance = np.var(self.slot_usage)
        
        # 分散が大きすぎる場合（偏りがある）
        if usage_variance > threshold:
            logger.warning(f"メモリ崩壊の可能性: 分散={usage_variance:.3f}")
            
            # 未使用スロットを活性化
            unused_slots = np.where(self.slot_usage < 0.1)
            
            if len(unused_slots[0]) > 0:
                # ランダムにいくつかの未使用スロットを活性化
                num_to_activate = min(10, len(unused_slots[0]))
                indices = np.random.choice(
                    len(unused_slots[0]), 
                    num_to_activate, 
                    replace=False
                )
                
                for idx in indices:
                    i, j = unused_slots[0][idx], unused_slots[1][idx]
                    # ランダムな初期化で活性化
                    self.value_matrix[i, j] = np.random.normal(
                        0, 0.1, 
                        self.value_dim
                    )
                    self.slot_usage[i, j] = 0.5  # 中間値に設定
                
                logger.info(f"未使用スロット{num_to_activate}個を活性化")
    
    def _update_session_state(
        self,
        session_id: str,
        slot_indices: List[Tuple[int, int]]
    ):
        """セッション状態を更新"""
        if session_id not in self.session_states:
            self.session_states[session_id] = {
                "chunk_count": 0,
                "slots_used": set(),
                "created_at": datetime.now().isoformat()
            }
        
        state = self.session_states[session_id]
        state["chunk_count"] += 1
        state["slots_used"].update(slot_indices)
        state["last_updated"] = datetime.now().isoformat()
    
    def _get_memory_state(self) -> Dict[str, Any]:
        """メモリ状態を取得"""
        return {
            "total_slots": self.memory_slots,
            "used_slots": np.count_nonzero(self.slot_usage),
            "usage_variance": float(np.var(self.slot_usage)),
            "usage_mean": float(np.mean(self.slot_usage)),
            "active_sessions": len(self.session_states)
        }
    
    def retrieve_from_memory(
        self,
        query: str,
        session_id: Optional[str] = None,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        メモリから情報を検索
        
        Args:
            query: 検索クエリ
            session_id: セッションID（Noneの場合は全セッション）
            top_k: 取得する結果数
        
        Returns:
            検索結果
        """
        # クエリをベクトル化
        query_vector = self._text_to_vector(query)
        
        # セッション固有のスロットを優先
        if session_id and session_id in self.session_states:
            session_slots = self.session_states[session_id]["slots_used"]
        else:
            session_slots = None
        
        # 全スロットから類似度を計算
        similarities = []
        
        for i in range(self.key1_slots):
            for j in range(self.key2_slots):
                # セッション固有のスロットを優先
                if session_slots and (i, j) not in session_slots:
                    continue
                
                slot_value = self.value_matrix[i, j]
                similarity = np.dot(query_vector, slot_value) / (
                    np.linalg.norm(query_vector) * np.linalg.norm(slot_value) + 1e-8
                )
                
                similarities.append({
                    "slot_index": (i, j),
                    "similarity": float(similarity),
                    "usage": float(self.slot_usage[i, j])
                })
        
        # 類似度でソート
        similarities.sort(key=lambda x: x["similarity"], reverse=True)
        
        return similarities[:top_k]
    
    def save_state(self, file_path: Path):
        """メモリ状態を保存"""
        state = {
            "value_matrix": self.value_matrix.tolist(),
            "slot_usage": self.slot_usage.tolist(),
            "session_states": {
                sid: {
                    **state,
                    "slots_used": list(state["slots_used"])
                }
                for sid, state in self.session_states.items()
            },
            "config": {
                "chunk_size": self.chunk_size,
                "memory_slots": self.memory_slots,
                "key1_slots": self.key1_slots,
                "key2_slots": self.key2_slots,
                "value_dim": self.value_dim
            }
        }
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        
        logger.info(f"メモリ状態を保存: {file_path}")
    
    def load_state(self, file_path: Path):
        """メモリ状態を読み込み"""
        with open(file_path, 'r', encoding='utf-8') as f:
            state = json.load(f)
        
        self.value_matrix = np.array(state["value_matrix"])
        self.slot_usage = np.array(state["slot_usage"])
        
        # セッション状態を復元
        self.session_states = {}
        for sid, sstate in state["session_states"].items():
            self.session_states[sid] = {
                **sstate,
                "slots_used": set(tuple(s) for s in sstate["slots_used"])
            }
        
        logger.info(f"メモリ状態を読み込み: {file_path}")


class InferenceMemoryUpdater:
    """
    推論中のメモリ更新を管理
    """
    
    def __init__(
        self,
        chunk_processor: ChunkMemoryProcessor,
        ollama_url: str = DEFAULT_OLLAMA_URL
    ):
        self.chunk_processor = chunk_processor
        self.ollama_url = ollama_url
    
    def process_long_text(
        self,
        text: str,
        model: str,
        session_id: str
    ):
        """
        長文をチャンクに分けて処理
        
        Args:
            text: 入力テキスト
            model: 使用モデル
            session_id: セッションID
        
        Yields:
            処理結果
        """
        import requests
        
        # チャンクに分割（簡易実装）
        chunks = self._split_into_chunks(text)
        
        accumulated_context = ""
        
        for i, chunk in enumerate(chunks):
            # 前のチャンクのコンテキストを追加
            full_chunk = accumulated_context + chunk
            
            # LLMで処理
            try:
                response = requests.post(
                    f"{self.ollama_url}/api/generate",
                    json={
                        "model": model,
                        "prompt": full_chunk,
                        "stream": False
                    },
                    timeout=60
                )
                
                if response.status_code == 200:
                    model_output = response.json().get("response", "")
                else:
                    model_output = ""
            except Exception as e:
                logger.error(f"LLM呼び出しエラー: {e}")
                model_output = ""
            
            # メモリを更新
            update_info = self.chunk_processor.process_chunk(
                chunk_text=chunk,
                model_output=model_output,
                session_id=session_id,
                target=None
            )
            
            # コンテキストを蓄積（重要情報のみ）
            accumulated_context = self._accumulate_context(
                accumulated_context,
                chunk,
                update_info
            )
            
            yield {
                "chunk_index": i,
                "chunk_length": len(chunk),
                "update_info": update_info,
                "accumulated_context_length": len(accumulated_context)
            }
    
    def _split_into_chunks(
        self,
        text: str,
        chunk_size: Optional[int] = None,
        overlap: int = 256
    ) -> List[str]:
        """
        テキストをチャンクに分割
        
        Args:
            text: 入力テキスト
            chunk_size: チャンクサイズ（Noneの場合はプロセッサの設定を使用）
            overlap: オーバーラップサイズ
        
        Returns:
            チャンクのリスト
        """
        if chunk_size is None:
            chunk_size = self.chunk_processor.chunk_size
        
        # 簡易実装：文字数ベースで分割
        chunks = []
        start = 0
        
        while start < len(text):
            end = min(start + chunk_size, len(text))
            chunk = text[start:end]
            chunks.append(chunk)
            
            # オーバーラップ
            start = end - overlap if end < len(text) else end
        
        return chunks
    
    def _accumulate_context(
        self,
        accumulated: str,
        new_chunk: str,
        update_info: ChunkProcessResult
    ) -> str:
        """
        コンテキストを蓄積（重要情報のみ）
        
        Args:
            accumulated: 既存の蓄積コンテキスト
            new_chunk: 新しいチャンク
            update_info: 更新情報
        
        Returns:
            更新されたコンテキスト
        """
        # 簡易実装：最後のN文字を保持
        max_context_length = self.chunk_processor.chunk_size * 2
        
        # 新しいチャンクを追加
        new_accumulated = accumulated + new_chunk
        
        # 最大長を超える場合は古い部分を削除
        if len(new_accumulated) > max_context_length:
            new_accumulated = new_accumulated[-max_context_length:]
        
        return new_accumulated
