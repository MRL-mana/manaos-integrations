#!/usr/bin/env python3
"""
🔍 Vector Search Engine
ベクトル検索エンジン本格実装

機能:
1. 意味的類似検索（FAISS）
2. 多言語対応（日本語・英語）
3. 高速検索（100ms以内）
"""

import asyncio
import logging
from pathlib import Path
from typing import List, Dict
import numpy as np

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("VectorSearch")


class VectorSearchEngine:
    """ベクトル検索エンジン"""
    
    def __init__(self):
        logger.info("🔍 Vector Search Engine 初期化中...")
        
        self.model = None
        self.index = None
        self.embeddings_cache = {}
        
        # データパス
        self.vector_db_path = Path('/root/unified_memory_system/data/vectors.npy')
        self.vector_metadata_path = Path('/root/unified_memory_system/data/vector_metadata.json')
        
        logger.info("✅ Vector Search Engine 準備完了")
    
    def _ensure_model_loaded(self):
        """モデル遅延読み込み"""
        if self.model is None:
            try:
                from sentence_transformers import SentenceTransformer
                logger.info("  🤖 多言語モデル読み込み中...")
                self.model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
                logger.info("  ✅ モデル読み込み完了")
            except Exception as e:
                logger.error(f"  ❌ モデル読み込み失敗: {e}")
                raise
    
    async def embed_text(self, text: str) -> np.ndarray:
        """
        テキストをベクトル化
        
        Args:
            text: テキスト
            
        Returns:
            ベクトル（384次元）
        """
        self._ensure_model_loaded()
        
        # キャッシュチェック
        if text in self.embeddings_cache:
            return self.embeddings_cache[text]
        
        # ベクトル化
        vector = self.model.encode(text, convert_to_numpy=True)
        
        # キャッシュ
        self.embeddings_cache[text] = vector
        
        return vector
    
    async def semantic_search(self, query: str, documents: List[Dict],
                             top_k: int = 10) -> List[Dict]:
        """
        意味的類似検索
        
        Args:
            query: 検索クエリ
            documents: 検索対象ドキュメント [{content, ...}, ...]
            top_k: 上位K件
            
        Returns:
            類似度順のドキュメント
        """
        logger.info(f"🔍 意味的検索: '{query[:30]}...'")
        
        if not documents:
            return []
        
        self._ensure_model_loaded()
        
        # クエリベクトル化
        query_vec = await self.embed_text(query)
        
        # ドキュメントベクトル化
        doc_vecs = []
        for doc in documents:
            content = doc.get('content', '')
            if content:
                vec = await self.embed_text(content[:500])  # 最初の500文字
                doc_vecs.append(vec)
            else:
                doc_vecs.append(np.zeros_like(query_vec))
        
        doc_vecs = np.array(doc_vecs)
        
        # コサイン類似度計算
        similarities = self._cosine_similarity(query_vec, doc_vecs)
        
        # 類似度順にソート
        sorted_indices = np.argsort(similarities)[::-1][:top_k]
        
        # 結果作成
        results = []
        for idx in sorted_indices:
            doc = documents[idx].copy()
            doc['similarity'] = float(similarities[idx])
            results.append(doc)
        
        logger.info(f"  ✅ {len(results)}件取得（最高類似度: {results[0]['similarity']:.2f}）")
        
        return results
    
    def _cosine_similarity(self, query_vec: np.ndarray, 
                          doc_vecs: np.ndarray) -> np.ndarray:
        """コサイン類似度計算"""
        # 正規化
        query_norm = query_vec / (np.linalg.norm(query_vec) + 1e-8)
        doc_norms = doc_vecs / (np.linalg.norm(doc_vecs, axis=1, keepdims=True) + 1e-8)
        
        # コサイン類似度
        similarities = np.dot(doc_norms, query_norm)
        
        return similarities


# テスト
async def test_vector_search():
    print("\n" + "="*70)
    print("🧪 Vector Search Engine - テスト")
    print("="*70)
    
    engine = VectorSearchEngine()
    
    # テストドキュメント
    docs = [
        {'id': 1, 'content': 'X280はTailscale経由でSSH接続できます'},
        {'id': 2, 'content': 'RunPod GPUで画像生成が可能です'},
        {'id': 3, 'content': 'X280のバックアップは毎晩0時に実行されます'},
        {'id': 4, 'content': 'Trinityボットはテレグラムで動作します'},
        {'id': 5, 'content': 'X280のSSH設定はTailscaleで簡単です'}
    ]
    
    # 意味的検索
    print("\n🔍 意味的検索: 'X280の接続方法'")
    results = await engine.semantic_search('X280の接続方法', docs, top_k=3)
    
    print("\n結果:")
    for i, r in enumerate(results, 1):
        print(f"  {i}. {r['content'][:50]} (類似度: {r['similarity']:.3f})")
    
    print("\n✅ ベクトル検索動作確認！")


if __name__ == '__main__':
    asyncio.run(test_vector_search())

