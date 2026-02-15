"""
LLMストリーミング対応
Server-Sent Events (SSE) によるリアルタイム回答
"""

import json
from manaos_logger import get_logger
import time
from typing import Iterator, Dict, Any, Optional
from flask import Response, stream_with_context
import requests
import os

try:
    from _paths import OLLAMA_PORT
except Exception:
    OLLAMA_PORT = int(os.getenv("OLLAMA_PORT", "11434"))

logger = get_logger(__name__)


class StreamingLLM:
    """ストリーミング対応LLMクラス"""
    
    def __init__(self, base_url: Optional[str] = None):
        """
        初期化
        
        Args:
            base_url: OllamaのベースURL
        """
        self.base_url = base_url or os.getenv("OLLAMA_URL", f"http://127.0.0.1:{OLLAMA_PORT}")
    
    def stream_chat(
        self,
        model: str,
        messages: list,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> Iterator[Dict[str, Any]]:
        """
        チャットをストリーミング実行
        
        Args:
            model: モデル名
            messages: メッセージリスト
            temperature: 温度パラメータ
            max_tokens: 最大トークン数
            
        Yields:
            ストリーミングチャンク
        """
        url = f"{self.base_url}/api/chat"
        
        payload = {
            "model": model,
            "messages": messages,
            "stream": True,
            "options": {
                "temperature": temperature
            }
        }
        
        if max_tokens:
            payload["options"]["num_predict"] = max_tokens
        
        try:
            response = requests.post(
                url,
                json=payload,
                stream=True,
                timeout=300
            )
            
            response.raise_for_status()
            
            for line in response.iter_lines():
                if line:
                    try:
                        chunk = json.loads(line.decode('utf-8'))
                        yield chunk
                    except json.JSONDecodeError:
                        continue
                        
        except Exception as e:
            logger.error(f"ストリーミングエラー: {e}")
            yield {
                "error": str(e),
                "done": True
            }
    
    def stream_generate(
        self,
        model: str,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> Iterator[Dict[str, Any]]:
        """
        テキスト生成をストリーミング実行
        
        Args:
            model: モデル名
            prompt: プロンプト
            temperature: 温度パラメータ
            max_tokens: 最大トークン数
            
        Yields:
            ストリーミングチャンク
        """
        url = f"{self.base_url}/api/generate"
        
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": True,
            "options": {
                "temperature": temperature
            }
        }
        
        if max_tokens:
            payload["options"]["num_predict"] = max_tokens
        
        try:
            response = requests.post(
                url,
                json=payload,
                stream=True,
                timeout=300
            )
            
            response.raise_for_status()
            
            for line in response.iter_lines():
                if line:
                    try:
                        chunk = json.loads(line.decode('utf-8'))
                        yield chunk
                    except json.JSONDecodeError:
                        continue
                        
        except Exception as e:
            logger.error(f"ストリーミングエラー: {e}")
            yield {
                "error": str(e),
                "done": True
            }


def create_sse_response(stream_generator: Iterator[Dict[str, Any]]) -> Response:
    """
    Server-Sent Events (SSE) レスポンスを作成
    
    Args:
        stream_generator: ストリーミングジェネレータ
        
    Returns:
        Flask Response
    """
    def generate():
        try:
            for chunk in stream_generator:
                if "error" in chunk:
                    yield f"data: {json.dumps(chunk)}\n\n"
                    break
                
                # SSE形式で送信
                data = json.dumps(chunk, ensure_ascii=False)
                yield f"data: {data}\n\n"
                
                # 完了したら終了
                if chunk.get("done", False):
                    break
                    
        except Exception as e:
            error_chunk = {"error": str(e), "done": True}
            yield f"data: {json.dumps(error_chunk)}\n\n"
    
    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
            'Connection': 'keep-alive'
        }
    )


def format_streaming_chunk(chunk: Dict[str, Any]) -> str:
    """
    ストリーミングチャンクをフォーマット
    
    Args:
        chunk: チャンクデータ
        
    Returns:
        フォーマットされた文字列
    """
    if "error" in chunk:
        return f"エラー: {chunk['error']}"
    
    if "message" in chunk:
        return chunk["message"].get("content", "")
    
    if "response" in chunk:
        return chunk["response"]
    
    return ""


class StreamingRAG:
    """ストリーミング対応RAGクラス"""
    
    def __init__(self, rag_system):
        """
        初期化
        
        Args:
            rag_system: RAGシステムインスタンス
        """
        self.rag_system = rag_system
        self.streaming_llm = StreamingLLM()
    
    def stream_query(
        self,
        question: str,
        model: Optional[str] = None,
        enable_multi_hop: bool = True
    ) -> Iterator[Dict[str, Any]]:
        """
        RAGクエリをストリーミング実行
        
        Args:
            question: 質問
            model: モデル名（Noneの場合はデフォルト）
            enable_multi_hop: マルチホップ検索を有効にするか
            
        Yields:
            ストリーミングチャンク
        """
        # 検索フェーズ
        yield {
            "type": "search",
            "status": "searching",
            "message": "関連情報を検索中..."
        }
        
        try:
            # ベクトル検索
            if not self.rag_system.vectorstore:
                yield {
                    "type": "error",
                    "message": "VectorStoreが利用できません"
                }
                return
            
            docs = self.rag_system.vectorstore.similarity_search(question, k=5)
            
            yield {
                "type": "search",
                "status": "found",
                "count": len(docs),
                "message": f"{len(docs)}件の関連情報が見つかりました"
            }
            
            # コンテキスト構築
            context = "\n\n".join([doc.page_content for doc in docs])
            
            # ストリーミング生成フェーズ
            yield {
                "type": "generation",
                "status": "starting",
                "message": "回答を生成中..."
            }
            
            # モデル名を取得
            if model is None:
                model = getattr(self.rag_system, 'ollama_model_name', 'qwen3:4b')
            
            # プロンプト構築
            prompt = f"""以下の情報を基に質問に回答してください。

コンテキスト:
{context}

質問: {question}

回答:"""
            
            messages = [
                {"role": "user", "content": prompt}
            ]
            
            # ストリーミング生成
            full_response = ""
            for chunk in self.streaming_llm.stream_chat(model=model, messages=messages):
                if "error" in chunk:
                    yield {
                        "type": "error",
                        "message": chunk["error"]
                    }
                    break
                
                if "message" in chunk:
                    content = chunk["message"].get("content", "")
                    if content:
                        full_response += content
                        yield {
                            "type": "token",
                            "content": content,
                            "full_response": full_response
                        }
                
                if chunk.get("done", False):
                    yield {
                        "type": "done",
                        "full_response": full_response,
                        "sources": [doc.metadata for doc in docs] if hasattr(docs[0], 'metadata') else []
                    }
                    break
                    
        except Exception as e:
            logger.error(f"ストリーミングRAGエラー: {e}")
            yield {
                "type": "error",
                "message": str(e)
            }

