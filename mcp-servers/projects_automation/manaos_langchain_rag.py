#!/usr/bin/env python3
"""
🤖 ManaOS LangChain RAG System
RAG + LLMを統合した高度なAI応答システム

機能:
- ChromaDBとLangChainの統合
- コンテキスト強化応答
- 会話履歴管理
- マルチモーダル対応
"""

from typing import List, Dict, Any, Optional
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory
from langchain_community.llms import Ollama
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ManaOSLangChainRAG:
    """LangChain RAGシステム"""
    
    def __init__(self, chroma_host: str = "localhost", chroma_port: int = 8001):
        """初期化"""
        logger.info("🤖 ManaOS LangChain RAG初期化中...")
        
        # Embeddings
        self.embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            model_kwargs={'device': 'cpu'}
        )
        
        # Vector Store
        try:
            self.vectorstore = Chroma(
                collection_name="manaos_knowledge",
                embedding_function=self.embeddings,
                persist_directory="/root/chroma_data"
            )
            logger.info("✅ ChromaDB接続成功")
        except Exception as e:
            logger.warning(f"⚠️ ChromaDB接続エラー: {e}")
            self.vectorstore = None
        
        # LLM（Ollamaを使用、なければダミー）
        try:
            self.llm = Ollama(model="llama2", base_url="http://localhost:11434")
            logger.info("✅ Ollama LLM接続")
        except sqlite3.Error:  # type: ignore[name-defined]
            logger.info("ℹ️ Ollama未検出。ダミーモードで動作")
            self.llm = None
        
        # Memory
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True,
            output_key='answer'
        )
        
        # Chain
        if self.vectorstore and self.llm:
            self.chain = ConversationalRetrievalChain.from_llm(
                llm=self.llm,
                retriever=self.vectorstore.as_retriever(search_kwargs={"k": 5}),
                memory=self.memory,
                return_source_documents=True
            )
        else:
            self.chain = None
    
    def query(self, question: str) -> Dict[str, Any]:
        """質問に回答"""
        logger.info(f"🔍 質問: {question}")
        
        if not self.vectorstore:
            return {
                'answer': "RAGシステムが初期化されていません。",
                'sources': []
            }
        
        # ベクトル検索
        docs = self.vectorstore.similarity_search(question, k=3)
        
        if not self.chain:
            # LLMなしの場合は検索結果のみ返す
            context = "\n\n".join([doc.page_content for doc in docs])
            return {
                'answer': f"関連情報:\n\n{context[:500]}...",
                'sources': [doc.metadata for doc in docs],
                'mode': 'retrieval_only'
            }
        
        # LLM + RAG
        try:
            result = self.chain({
                "question": question
            })
            
            return {
                'answer': result['answer'],
                'sources': [doc.metadata for doc in result.get('source_documents', [])],
                'mode': 'rag_llm'
            }
        except Exception as e:
            logger.error(f"❌ RAG処理エラー: {e}")
            context = "\n\n".join([doc.page_content for doc in docs])
            return {
                'answer': f"関連情報:\n\n{context[:500]}...",
                'sources': [doc.metadata for doc in docs],
                'mode': 'fallback'
            }
    
    def add_documents(self, texts: List[str], metadatas: Optional[List[Dict]] = None):
        """ドキュメント追加"""
        if not self.vectorstore:
            logger.error("❌ VectorStoreが初期化されていません")
            return False
        
        try:
            # テキスト分割
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=200
            )
            
            chunks = []
            chunk_metadatas = []
            
            for i, text in enumerate(texts):
                text_chunks = text_splitter.split_text(text)
                chunks.extend(text_chunks)
                
                metadata = metadatas[i] if metadatas and i < len(metadatas) else {}
                chunk_metadatas.extend([metadata] * len(text_chunks))
            
            self.vectorstore.add_texts(chunks, metadatas=chunk_metadatas)
            logger.info(f"✅ {len(chunks)}個のチャンクを追加")
            return True
            
        except Exception as e:
            logger.error(f"❌ ドキュメント追加エラー: {e}")
            return False
    
    def chat(self, message: str) -> str:
        """会話形式で応答"""
        result = self.query(message)
        return result['answer']

def main():
    """メイン実行"""
    print("🤖 ManaOS LangChain RAG System")
    print("="*80)
    
    rag = ManaOSLangChainRAG()
    
    # テストクエリ
    test_queries = [
        "ManaOSの主な機能は何ですか？",
        "システムの状態を確認する方法",
        "Grafanaへのアクセス方法"
    ]
    
    print("\n🧪 テストクエリ:")
    for i, query in enumerate(test_queries, 1):
        print(f"\n{i}. {query}")
        result = rag.query(query)
        print(f"   回答: {result['answer'][:200]}...")
        print(f"   モード: {result.get('mode', 'unknown')}")
    
    print("\n✅ LangChain RAGシステム準備完了！")
    print("="*80)

if __name__ == "__main__":
    main()








