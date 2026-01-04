"""
LangChain/LangGraph統合モジュール
AIエージェントフレームワークとの統合
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
    print("LangChainライブラリがインストールされていません。")
    print("インストール: pip install langchain langchain-community langchain-core")

try:
    from langgraph.graph import StateGraph, END
    from langgraph.graph.message import add_messages
    LANGRAPH_AVAILABLE = True
except ImportError:
    LANGRAPH_AVAILABLE = False
    print("LangGraphライブラリがインストールされていません。")
    print("インストール: pip install langgraph")


class LangChainIntegration:
    """LangChain統合クラス"""
    
    def __init__(self, ollama_url: str = "http://localhost:11434", model_name: str = "qwen2.5:7b"):
        """
        初期化
        
        Args:
            ollama_url: OllamaサーバーのURL
            model_name: 使用するモデル名
        """
        self.ollama_url = ollama_url
        self.model_name = model_name
        self.llm = None
        self.memory = None
        
        if LANGCHAIN_AVAILABLE:
            self._initialize_llm()
    
    def _initialize_llm(self):
        """LLMを初期化"""
        try:
            self.llm = Ollama(
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
        except Exception as e:
            print(f"LLM初期化エラー: {e}")
    
    def is_available(self) -> bool:
        """
        LangChainが利用可能かチェック
        
        Returns:
            利用可能な場合True
        """
        if not LANGCHAIN_AVAILABLE:
            return False
        
        # LLMが初期化されていない場合、初期化を試みる
        if self.llm is None:
            try:
                self._initialize_llm()
            except Exception:
                pass
        
        # 実際にOllamaに接続できるかテスト
        if self.llm is not None:
            try:
                import requests
                response = requests.get(f"{self.ollama_url}/api/tags", timeout=2)
                return response.status_code == 200
            except Exception:
                return False
        
        return False
    
    def chat(self, message: str, system_prompt: Optional[str] = None) -> str:
        """
        チャットを実行
        
        Args:
            message: ユーザーメッセージ
            system_prompt: システムプロンプト（オプション）
            
        Returns:
            AIの応答
        """
        if not self.is_available():
            return "LangChainが利用できません。"
        
        try:
            messages = []
            
            if system_prompt:
                messages.append(SystemMessage(content=system_prompt))
            
            # メモリから履歴を取得
            if self.memory:
                history = self.memory.chat_memory.messages
                messages.extend(history)
            
            messages.append(HumanMessage(content=message))
            
            # LLMを呼び出し
            response = self.llm.invoke(messages)
            
            # メモリに保存
            if self.memory:
                self.memory.chat_memory.add_user_message(message)
                self.memory.chat_memory.add_ai_message(response)
            
            return response.content if hasattr(response, 'content') else str(response)
            
        except Exception as e:
            return f"エラー: {e}"
    
    def create_agent(self, tools: List[Any], system_prompt: str = "You are a helpful assistant.") -> Optional[Any]:
        """
        エージェントを作成
        
        Args:
            tools: 使用可能なツールのリスト
            system_prompt: システムプロンプト
            
        Returns:
            AgentExecutor（成功時）、None（失敗時）
        """
        if not self.is_available() or AgentExecutor is None:
            return None
        
        try:
            # シンプルなエージェントを作成
            # 注意: 完全なエージェント機能には追加の設定が必要
            prompt = f"{system_prompt}\n\n使用可能なツール: {', '.join([getattr(tool, 'name', str(tool)) for tool in tools])}"
            
            # ここでは簡易的な実装
            # 完全なエージェント機能には、より複雑な設定が必要
            return None  # 実装は後で拡張
            
        except Exception as e:
            print(f"エージェント作成エラー: {e}")
            return None


class LangGraphIntegration:
    """LangGraph統合クラス"""
    
    def __init__(self, ollama_url: str = "http://localhost:11434", model_name: str = "qwen2.5:7b"):
        """
        初期化
        
        Args:
            ollama_url: OllamaサーバーのURL
            model_name: 使用するモデル名
        """
        self.ollama_url = ollama_url
        self.model_name = model_name
        self.graph = None
        
        if LANGRAPH_AVAILABLE and LANGCHAIN_AVAILABLE:
            self._initialize_graph()
    
    def _initialize_graph(self):
        """グラフを初期化"""
        try:
            from langchain_community.llms import Ollama
            
            llm = Ollama(
                base_url=self.ollama_url,
                model=self.model_name
            )
            
            # シンプルなグラフを作成
            workflow = StateGraph(dict)
            
            def process_message(state: dict) -> dict:
                """メッセージを処理"""
                messages = state.get("messages", [])
                if messages:
                    last_message = messages[-1]
                    response = llm.invoke([last_message])
                    return {"messages": add_messages(messages, [response])}
                return state
            
            workflow.add_node("process", process_message)
            workflow.set_entry_point("process")
            workflow.add_edge("process", END)
            
            self.graph = workflow.compile()
            
        except Exception as e:
            print(f"グラフ初期化エラー: {e}")
    
    def is_available(self) -> bool:
        """
        LangGraphが利用可能かチェック
        
        Returns:
            利用可能な場合True
        """
        if not (LANGRAPH_AVAILABLE and LANGCHAIN_AVAILABLE):
            return False
        
        # グラフが初期化されていない場合、初期化を試みる
        if self.graph is None:
            try:
                self._initialize_graph()
            except Exception:
                pass
        
        # 実際にOllamaに接続できるかテスト
        try:
            import requests
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=2)
            return response.status_code == 200
        except Exception:
            return False
    
    def run(self, message: str, initial_state: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        グラフを実行
        
        Args:
            message: 入力メッセージ
            initial_state: 初期状態（オプション）
            
        Returns:
            実行結果
        """
        if not self.is_available():
            return {"error": "LangGraphが利用できません。"}
        
        try:
            try:
                from langchain_core.messages import HumanMessage
            except ImportError:
                from langchain.schema import HumanMessage
            
            state = initial_state or {}
            state["messages"] = [HumanMessage(content=message)]
            
            result = self.graph.invoke(state)
            return result
            
        except Exception as e:
            return {"error": str(e)}


def main():
    """テスト用メイン関数"""
    print("LangChain統合テスト")
    print("=" * 50)
    
    if not LANGCHAIN_AVAILABLE:
        print("LangChainがインストールされていません。")
        return
    
    # LangChain統合テスト
    langchain = LangChainIntegration()
    
    if langchain.is_available():
        print("\nLangChainチャットテスト:")
        response = langchain.chat("こんにちは！", system_prompt="あなたは親切なアシスタントです。")
        print(f"応答: {response}")
    else:
        print("LangChainが利用できません。Ollamaサーバーが起動しているか確認してください。")
    
    # LangGraph統合テスト
    if LANGRAPH_AVAILABLE:
        print("\nLangGraph統合テスト:")
        langgraph = LangGraphIntegration()
        
        if langgraph.is_available():
            result = langgraph.run("こんにちは！")
            print(f"結果: {result}")
        else:
            print("LangGraphが利用できません。")


if __name__ == "__main__":
    main()




