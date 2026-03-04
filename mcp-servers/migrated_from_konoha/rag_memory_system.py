#!/usr/bin/env python3
"""
RAG Memory System - Retrieval-Augmented Generation Memory
過去の会話・知見をベクトル検索で活用
"""

import os
import json
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime
import numpy as np

logger = logging.getLogger(__name__)

# Sentence Transformers for embeddings
try:
    from sentence_transformers import SentenceTransformer
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    EMBEDDINGS_AVAILABLE = False
    logger.warning("sentence-transformers not available")

# ChromaDB for vector storage
try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False
    logger.warning("chromadb not available")


class RAGMemorySystem:
    """RAG Memory統合システム"""
    
    def __init__(self, workspace_path: str = "/root/trinity_workspace"):
        self.workspace = Path(workspace_path)
        self.memory_dir = self.workspace / "memory"
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        
        self.db_path = self.memory_dir / "rag_chroma"
        self.memories_file = self.memory_dir / "memories.jsonl"
        
        # Embedding model
        if EMBEDDINGS_AVAILABLE:
            self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("✅ Embedding model loaded: all-MiniLM-L6-v2")
        else:
            self.embedding_model = None
            logger.warning("⚠️  Embeddings not available")
        
        # ChromaDB client
        if CHROMADB_AVAILABLE:
            self.client = chromadb.PersistentClient(
                path=str(self.db_path),
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            
            # Collection作成
            try:
                self.collection = self.client.get_or_create_collection(
                    name="trinity_memories",
                    metadata={"description": "Trinity知見・会話メモリ"}
                )
                logger.info(f"✅ ChromaDB collection ready: {self.collection.count()} memories")
            except Exception as e:
                logger.error(f"ChromaDB collection error: {e}")
                self.collection = None
        else:
            self.client = None
            self.collection = None
            logger.warning("⚠️  ChromaDB not available")
    
    def add_memory(self, content: str, metadata: Dict[str, Any] = {}) -> str:
        """メモリ追加"""
        if not self.embedding_model or not self.collection:
            logger.warning("RAG not available - saving to file only")
            return self._save_to_file(content, metadata)
        
        try:
            # メモリID生成
            memory_id = f"mem_{datetime.now().strftime('%Y%m%d%H%M%S')}_{hash(content) % 10000:04d}"
            
            # Embedding生成
            embedding = self.embedding_model.encode(content).tolist()
            
            # メタデータ準備
            memory_metadata = {
                'timestamp': datetime.now().isoformat(),
                'source': metadata.get('source', 'unknown'),
                'agent': metadata.get('agent', 'unknown'),
                'category': metadata.get('category', 'general'),
                **metadata
            }
            
            # ChromaDBに追加
            self.collection.add(
                ids=[memory_id],
                embeddings=[embedding],
                documents=[content],
                metadatas=[memory_metadata]
            )
            
            # ファイルにも保存（バックアップ）
            self._save_to_file(content, memory_metadata, memory_id)
            
            logger.info(f"✅ Memory added: {memory_id}")
            return memory_id
        
        except Exception as e:
            logger.error(f"❌ Failed to add memory: {e}")
            return self._save_to_file(content, metadata)
    
    def search(self, query: str, top_k: int = 5, 
               filter_metadata: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """メモリ検索"""
        if not self.embedding_model or not self.collection:
            logger.warning("RAG not available - returning empty results")
            return []
        
        try:
            # クエリのEmbedding生成
            query_embedding = self.embedding_model.encode(query).tolist()
            
            # ChromaDBで検索
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=filter_metadata
            )
            
            # 結果整形
            memories = []
            if results['ids'] and len(results['ids']) > 0:
                for i in range(len(results['ids'][0])):
                    memory = {
                        'id': results['ids'][0][i],
                        'content': results['documents'][0][i],
                        'metadata': results['metadatas'][0][i],
                        'distance': results['distances'][0][i] if 'distances' in results else None,
                        'relevance': 1.0 - (results['distances'][0][i] if 'distances' in results else 0.5)
                    }
                    memories.append(memory)
            
            logger.info(f"✅ Found {len(memories)} relevant memories")
            return memories
        
        except Exception as e:
            logger.error(f"❌ Search failed: {e}")
            return []
    
    def get_context(self, query: str, max_tokens: int = 2000) -> str:
        """クエリに関連するコンテキストを取得"""
        memories = self.search(query, top_k=10)
        
        context_parts = []
        total_length = 0
        
        for memory in memories:
            content = memory['content']
            if total_length + len(content) > max_tokens:
                break
            
            context_parts.append(f"[{memory['metadata'].get('agent', 'Unknown')}]: {content}")
            total_length += len(content)
        
        if context_parts:
            return "\n\n".join(context_parts)
        else:
            return ""
    
    def import_from_knowledge_md(self, knowledge_file: Path = None):
        """knowledge.mdからインポート"""
        if knowledge_file is None:
            knowledge_file = self.workspace / "shared" / "knowledge.md"
        
        if not knowledge_file.exists():
            logger.warning(f"Knowledge file not found: {knowledge_file}")
            return 0
        
        try:
            with open(knowledge_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # セクション分割
            sections = content.split('---')
            count = 0
            
            for section in sections:
                section = section.strip()
                if len(section) > 50:  # 最小長チェック
                    self.add_memory(
                        content=section,
                        metadata={
                            'source': 'knowledge.md',
                            'agent': 'Aria',
                            'category': 'knowledge'
                        }
                    )
                    count += 1
            
            logger.info(f"✅ Imported {count} memories from knowledge.md")
            return count
        
        except Exception as e:
            logger.error(f"❌ Import failed: {e}")
            return 0
    
    def import_from_dev_qa(self, dev_qa_file: Path = None):
        """dev_qa.mdからインポート"""
        if dev_qa_file is None:
            dev_qa_file = Path("/root/dev_qa.md")
        
        if not dev_qa_file.exists():
            logger.warning(f"dev_qa.md not found: {dev_qa_file}")
            return 0
        
        try:
            with open(dev_qa_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Q&A分割
            qa_blocks = content.split('---')
            count = 0
            
            for block in qa_blocks:
                block = block.strip()
                if '**質問**' in block and '**回答**' in block:
                    self.add_memory(
                        content=block,
                        metadata={
                            'source': 'dev_qa.md',
                            'agent': 'Aria',
                            'category': 'qa'
                        }
                    )
                    count += 1
            
            logger.info(f"✅ Imported {count} Q&A from dev_qa.md")
            return count
        
        except Exception as e:
            logger.error(f"❌ Import failed: {e}")
            return 0
    
    def _save_to_file(self, content: str, metadata: Dict, memory_id: str = None) -> str:
        """ファイルに保存（バックアップ）"""
        if memory_id is None:
            memory_id = f"mem_{datetime.now().strftime('%Y%m%d%H%M%S')}_{hash(content) % 10000:04d}"
        
        entry = {
            'id': memory_id,
            'content': content,
            'metadata': metadata,
            'timestamp': datetime.now().isoformat()
        }
        
        with open(self.memories_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')
        
        return memory_id
    
    def get_stats(self) -> Dict[str, Any]:
        """統計情報"""
        stats = {
            'available': self.embedding_model is not None and self.collection is not None,
            'total_memories': 0,
            'embedding_model': 'all-MiniLM-L6-v2' if self.embedding_model else None,
            'vector_db': 'ChromaDB' if self.collection else None
        }
        
        if self.collection:
            try:
                stats['total_memories'] = self.collection.count()
            except:
                pass
        
        return stats


# グローバルインスタンス
rag_memory = RAGMemorySystem()


# 便利関数
def add_memory(content: str, metadata: Dict[str, Any] = {}) -> str:
    return rag_memory.add_memory(content, metadata)

def search_memory(query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    return rag_memory.search(query, top_k)

def get_context(query: str, max_tokens: int = 2000) -> str:
    return rag_memory.get_context(query, max_tokens)

def import_knowledge() -> int:
    count1 = rag_memory.import_from_knowledge_md()
    count2 = rag_memory.import_from_dev_qa()
    return count1 + count2

def get_rag_stats() -> Dict[str, Any]:
    return rag_memory.get_stats()

