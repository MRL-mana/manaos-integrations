#!/usr/bin/env python3
"""
🤖 ManaOS RAG (Retrieval-Augmented Generation) System
ベクトルDBを活用した高度なAI応答システム

機能:
- ChromaDBベクトルストア
- 文書の自動インデックス化
- セマンティック検索
- コンテキスト強化応答
"""

import sys
from typing import List, Dict, Any
from pathlib import Path
import chromadb
from chromadb.config import Settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ManaOSRAG:
    """RAGシステム"""
    
    def __init__(self, chroma_host="localhost", chroma_port=8000):
        """初期化"""
        try:
            self.client = chromadb.HttpClient(
                host=chroma_host,
                port=chroma_port,
                settings=Settings(anonymized_telemetry=False)
            )
            self.collection = self.client.get_or_create_collection(
                name="manaos_knowledge",
                metadata={"description": "ManaOS知識ベース"}
            )
            logger.info("✅ ChromaDB接続成功")
        except Exception as e:
            logger.error(f"❌ ChromaDB接続失敗: {e}")
            raise
    
    def add_documents(self, documents: List[str], metadatas: List[Dict] = None):
        """ドキュメント追加"""
        try:
            ids = [f"doc_{i}" for i in range(len(documents))]
            self.collection.add(
                documents=documents,
                metadatas=metadatas or [{}] * len(documents),
                ids=ids
            )
            logger.info(f"✅ {len(documents)}個のドキュメントを追加")
            return True
        except Exception as e:
            logger.error(f"❌ ドキュメント追加失敗: {e}")
            return False
    
    def search(self, query: str, n_results: int = 5) -> Dict[str, Any]:
        """セマンティック検索"""
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results
            )
            logger.info(f"✅ 検索完了: {len(results['documents'][0])}件")
            return results
        except Exception as e:
            logger.error(f"❌ 検索失敗: {e}")
            return {}
    
    def index_directory(self, directory: str, extensions: List[str] = ['.txt', '.md', '.py']):
        """ディレクトリ内のファイルをインデックス化"""
        documents = []
        metadatas = []
        
        for ext in extensions:
            for file_path in Path(directory).rglob(f'*{ext}'):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if content.strip():
                            documents.append(content[:5000])  # 最大5000文字
                            metadatas.append({
                                'file_path': str(file_path),
                                'file_type': ext
                            })
                except Exception as e:
                    logger.warning(f"⚠️ ファイル読み込み失敗: {file_path}: {e}")
        
        if documents:
            return self.add_documents(documents, metadatas)
        return False

def main():
    """メイン実行"""
    print("🤖 ManaOS RAG System - セットアップ")
    print("="*60)
    
    try:
        rag = ManaOSRAG()
        
        # サンプルドキュメント追加
        sample_docs = [
            "ManaOSは自動化とAI駆動の統合システムです。",
            "Dockerコンテナで14個のサービスが稼働中です。",
            "Grafanaはポート3002でアクセスできます。",
            "自動改善エンジンは毎時0分に実行されます。",
            "セキュリティスコアは100/100を維持しています。"
        ]
        
        rag.add_documents(sample_docs)
        
        # テスト検索
        query = "Grafanaへのアクセス方法"
        results = rag.search(query)
        
        print("\n🔍 テスト検索:")
        print(f"クエリ: {query}")
        print(f"結果: {results['documents'][0][0] if results else 'なし'}")
        
        print("\n✅ RAGシステム初期化完了！")
        print("="*60)
        
    except Exception as e:
        print(f"❌ エラー: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())








