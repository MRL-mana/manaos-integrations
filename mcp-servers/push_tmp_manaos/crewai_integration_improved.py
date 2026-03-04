"""
CrewAI統合モジュール（改善版）
マルチエージェントフレームワークとの統合
ベースクラスを使用して統一モジュールを活用
"""

import os
from typing import Optional, Dict, List, Any, Callable
from datetime import datetime

try:
    from crewai import Agent, Task, Crew, Process
    from crewai_tools import tool
    CREWAI_AVAILABLE = True
except ImportError:
    CREWAI_AVAILABLE = False
    Agent = None
    Task = None
    Crew = None
    Process = None

try:
    from langchain_community.llms import Ollama
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False

# ベースクラスのインポート
from base_integration import BaseIntegration


class CrewAIIntegration(BaseIntegration):
    """CrewAI統合クラス（改善版）"""
    
    def __init__(
        self,
        ollama_url: str = "http://127.0.0.1:11434",
        model_name: str = "qwen2.5:7b"
    ):
        """
        初期化
        
        Args:
            ollama_url: OllamaサーバーのURL
            model_name: 使用するモデル名
        """
        super().__init__("CrewAI")
        self.ollama_url = ollama_url
        self.model_name = model_name
        self.llm = None
    
    def _initialize_internal(self) -> bool:
        """
        内部初期化
        
        Returns:
            初期化成功かどうか
        """
        if not CREWAI_AVAILABLE:
            self.logger.warning("CrewAIライブラリがインストールされていません")
            return False
        
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
        return CREWAI_AVAILABLE and LANGCHAIN_AVAILABLE and self.llm is not None
    
    def _initialize_llm(self) -> bool:
        """
        LLMを初期化
        
        Returns:
            初期化成功かどうか
        """
        try:
            self.llm = Ollama(
                base_url=self.ollama_url,
                model=self.model_name,
                temperature=0.7
            )
            self.logger.info(f"CrewAI LLMを初期化しました: {self.model_name}")
            return True
        except Exception as e:
            error = self.error_handler.handle_exception(
                e,
                context={"ollama_url": self.ollama_url, "model_name": self.model_name, "action": "initialize_llm"},
                user_message="CrewAI LLMの初期化に失敗しました"
            )
            self.logger.error(f"LLM初期化エラー: {error.message}")
            return False
    
    def create_agent(
        self,
        role: str,
        goal: str,
        backstory: str = "",
        tools: Optional[List[Any]] = None
    ) -> Optional[Any]:
        """
        エージェントを作成
        
        Args:
            role: エージェントの役割
            goal: エージェントの目標
            backstory: エージェントの背景
            tools: 使用可能なツールのリスト
            
        Returns:
            Agent（成功時）、None（失敗時）
        """
        if not self.is_available():
            return None
        
        try:
            agent = Agent(
                role=role,
                goal=goal,
                backstory=backstory or f"{role}として活動するエージェントです。",
                llm=self.llm,
                tools=tools or [],
                verbose=True
            )
            self.logger.info(f"エージェントを作成しました: {role}")
            return agent
        except Exception as e:
            error = self.error_handler.handle_exception(
                e,
                context={"role": role, "action": "create_agent"},
                user_message="エージェントの作成に失敗しました"
            )
            self.logger.error(f"エージェント作成エラー: {error.message}")
            return None
    
    def create_task(
        self,
        description: str,
        agent: Any,
        expected_output: str = ""
    ) -> Optional[Any]:
        """
        タスクを作成
        
        Args:
            description: タスクの説明
            agent: 実行するエージェント
            expected_output: 期待される出力
            
        Returns:
            Task（成功時）、None（失敗時）
        """
        if not self.is_available():
            return None
        
        try:
            task = Task(
                description=description,
                agent=agent,
                expected_output=expected_output or "タスクの実行結果"
            )
            self.logger.info(f"タスクを作成しました: {description[:50]}")
            return task
        except Exception as e:
            error = self.error_handler.handle_exception(
                e,
                context={"description": description[:50], "action": "create_task"},
                user_message="タスクの作成に失敗しました"
            )
            self.logger.error(f"タスク作成エラー: {error.message}")
            return None
    
    def execute_crew(
        self,
        agents: List[Any],
        tasks: List[Any],
        process: Process = Process.sequential
    ) -> Optional[Dict[str, Any]]:
        """
        クルーを実行
        
        Args:
            agents: エージェントのリスト
            tasks: タスクのリスト
            process: プロセスタイプ
            
        Returns:
            実行結果（成功時）、None（失敗時）
        """
        if not self.is_available():
            return None
        
        try:
            crew = Crew(
                agents=agents,
                tasks=tasks,
                process=process,
                verbose=True
            )
            
            timeout = self.get_timeout("workflow_execution")
            result = crew.kickoff()
            
            self.logger.info("クルーの実行が完了しました")
            return {
                "result": str(result),
                "tasks_completed": len(tasks)
            }
        except Exception as e:
            error = self.error_handler.handle_exception(
                e,
                context={"agents_count": len(agents), "tasks_count": len(tasks), "action": "execute_crew"},
                user_message="クルーの実行に失敗しました"
            )
            self.logger.error(f"クルー実行エラー: {error.message}")
            return None






















