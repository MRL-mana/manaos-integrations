"""
LangChain/LangGraph統合モジュール（改善版）
AIエージェントフレームワークとの統合
ベースクラスを使用して統一モジュールを活用
"""

import os
from typing import Optional, Dict, Any, List, Callable
from datetime import datetime

try:
    from langchain_community.llms import Ollama
    try:
        from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
    except ImportError:
        from langchain.schema import HumanMessage, AIMessage, SystemMessage
    try:
        from langchain.memory import ConversationBufferMemory
    except ImportError:
        ConversationBufferMemory = None
    try:
        from langchain.agents import AgentExecutor, create_openai_functions_agent
    except ImportError:
        try:
            from langchain.agents import AgentExecutor
            create_openai_functions_agent = None
        except ImportError:
            AgentExecutor = None
            create_openai_functions_agent = None
    try:
        from langchain.tools import Tool
    except ImportError:
        try:
            from langchain_core.tools import Tool
        except ImportError:
            Tool = None
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    Tool = None
    AgentExecutor = None
    create_openai_functions_agent = None

try:
    from langgraph.graph import StateGraph, END
    from langgraph.graph.message import add_messages
    LANGRAPH_AVAILABLE = True
except ImportError:
    LANGRAPH_AVAILABLE = False

# ベースクラスのインポート
from base_integration import BaseIntegration


class LangChainIntegration(BaseIntegration):
    """LangChain統合クラス（改善版）"""
    
    def __init__(self, ollama_url: str = "http://127.0.0.1:11434", model_name: str = "qwen2.5:7b"):
        """
        初期化
        
        Args:
            ollama_url: OllamaサーバーのURL
            model_name: 使用するモデル名
        """
        super().__init__("LangChain")
        self.ollama_url = ollama_url
        self.model_name = model_name
        self.llm = None
        self.memory = None
    
    def _initialize_internal(self) -> bool:
        """
        内部初期化
        
        Returns:
            初期化成功かどうか
        """
        if not LANGCHAIN_AVAILABLE:
            self.logger.warning("LangChainライブラリがインストールされていません")
            return False
        
        return self._initialize_llm()
    
    def _check_availability_internal(self) -> bool:
        """
        内部の利用可能性チェック
        
        Returns:
            利用可能かどうか
        """
        return LANGCHAIN_AVAILABLE and self.llm is not None
    
    def _initialize_llm(self) -> bool:
        """
        LLMを初期化
        
        Returns:
            初期化成功かどうか
        """
        try:
            self.llm = Ollama(  # type: ignore[possibly-unbound]
                base_url=self.ollama_url,
                model=self.model_name,
                temperature=0.7
            )
            if ConversationBufferMemory is not None:
                self.memory = ConversationBufferMemory(
                    return_messages=True,
                    memory_key="chat_history"
                )
            else:
                self.memory = None
            
            self.logger.info(f"LangChain LLMを初期化しました: {self.model_name}")
            return True
        except Exception as e:
            error = self.error_handler.handle_exception(
                e,
                context={"ollama_url": self.ollama_url, "model_name": self.model_name, "action": "initialize_llm"},
                user_message="LangChain LLMの初期化に失敗しました"
            )
            self.logger.error(f"LLM初期化エラー: {error.message}")
            return False
    
    def chat(self, message: str, system_prompt: Optional[str] = None) -> Optional[str]:
        """
        チャットを実行
        
        Args:
            message: ユーザーメッセージ
            system_prompt: システムプロンプト（オプション）
            
        Returns:
            応答テキスト（成功時）、None（失敗時）
        """
        if not self.is_available():
            return None
        
        try:
            messages = []
            if system_prompt:
                messages.append(SystemMessage(content=system_prompt))  # type: ignore[possibly-unbound]
            messages.append(HumanMessage(content=message))  # type: ignore[possibly-unbound]
            
            if self.memory:
                self.memory.chat_memory.add_user_message(message)
            
            timeout = self.get_timeout("llm_call")
            response = self.llm.invoke(messages)  # type: ignore[union-attr]
            
            if self.memory:
                self.memory.chat_memory.add_ai_message(response.content if hasattr(response, 'content') else str(response))
            
            result = response.content if hasattr(response, 'content') else str(response)
            self.logger.info(f"チャット完了: {len(result)}文字")
            return result
            
        except Exception as e:
            error = self.error_handler.handle_exception(
                e,
                context={"message": message[:50], "action": "chat"},
                user_message="チャットの実行に失敗しました"
            )
            self.logger.error(f"チャットエラー: {error.message}")
            return None


class LangGraphIntegration(BaseIntegration):
    """LangGraph統合クラス（改善版）"""
    
    def __init__(self, ollama_url: str = "http://127.0.0.1:11434", model_name: str = "qwen2.5:7b"):
        """
        初期化
        
        Args:
            ollama_url: OllamaサーバーのURL
            model_name: 使用するモデル名
        """
        super().__init__("LangGraph")
        self.ollama_url = ollama_url
        self.model_name = model_name
        self.graph = None
    
    def _initialize_internal(self) -> bool:
        """
        内部初期化
        
        Returns:
            初期化成功かどうか
        """
        if not LANGRAPH_AVAILABLE:
            self.logger.warning("LangGraphライブラリがインストールされていません")
            return False
        
        try:
            # 簡易グラフの作成
            self.graph = StateGraph(dict)  # type: ignore[possibly-unbound]
            self.logger.info("LangGraphを初期化しました")
            return True
        except Exception as e:
            error = self.error_handler.handle_exception(
                e,
                context={"action": "initialize"},
                user_message="LangGraphの初期化に失敗しました"
            )
            self.logger.error(f"LangGraph初期化エラー: {error.message}")
            return False
    
    def _check_availability_internal(self) -> bool:
        """
        内部の利用可能性チェック
        
        Returns:
            利用可能かどうか
        """
        return LANGRAPH_AVAILABLE and self.graph is not None






















