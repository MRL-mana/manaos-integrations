"""
CrewAI統合モジュール
マルチエージェントフレームワークとの統合
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
    print("CrewAIライブラリがインストールされていません。")
    print("インストール: pip install crewai crewai-tools")

try:
    from langchain_community.llms import Ollama
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    print("LangChainライブラリがインストールされていません。")


class CrewAIIntegration:
    """CrewAI統合クラス"""
    
    def __init__(
        self,
        ollama_url: str = "http://localhost:11434",
        model_name: str = "qwen2.5:7b"
    ):
        """
        初期化
        
        Args:
            ollama_url: OllamaサーバーのURL
            model_name: 使用するモデル名
        """
        self.ollama_url = ollama_url
        self.model_name = model_name
        self.llm = None
        
        if CREWAI_AVAILABLE and LANGCHAIN_AVAILABLE:
            self._initialize_llm()
    
    def _initialize_llm(self):
        """LLMを初期化"""
        try:
            self.llm = Ollama(
                base_url=self.ollama_url,
                model=self.model_name,
                temperature=0.7
            )
        except Exception as e:
            print(f"LLM初期化エラー: {e}")
    
    def is_available(self) -> bool:
        """
        CrewAIが利用可能かチェック
        
        Returns:
            利用可能な場合True
        """
        return CREWAI_AVAILABLE and self.llm is not None
    
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
            return agent
            
        except Exception as e:
            print(f"エージェント作成エラー: {e}")
            return None
    
    def create_task(
        self,
        description: str,
        agent: Agent,
        expected_output: str = ""
    ) -> Optional[Task]:
        """
        タスクを作成
        
        Args:
            description: タスクの説明
            agent: タスクを実行するエージェント
            expected_output: 期待される出力
            
        Returns:
            Task（成功時）、None（失敗時）
        """
        if not CREWAI_AVAILABLE:
            return None
        
        try:
            task = Task(
                description=description,
                agent=agent,
                expected_output=expected_output or "タスクの実行結果"
            )
            return task
            
        except Exception as e:
            print(f"タスク作成エラー: {e}")
            return None
    
    def create_crew(
        self,
        agents: List[Agent],
        tasks: List[Task],
        process: Process = Process.sequential if Process else None
    ) -> Optional[Crew]:
        """
        クルーを作成
        
        Args:
            agents: エージェントのリスト
            tasks: タスクのリスト
            process: プロセスタイプ（sequential, hierarchical）
            
        Returns:
            Crew（成功時）、None（失敗時）
        """
        if not CREWAI_AVAILABLE:
            return None
        
        try:
            crew = Crew(
                agents=agents,
                tasks=tasks,
                process=process,
                verbose=True
            )
            return crew
            
        except Exception as e:
            print(f"クルー作成エラー: {e}")
            return None
    
    def run_crew(
        self,
        agents: List[Agent],
        tasks: List[Task],
        process: Process = Process.sequential if Process else None
    ) -> Optional[str]:
        """
        クルーを実行
        
        Args:
            agents: エージェントのリスト
            tasks: タスクのリスト
            process: プロセスタイプ
            
        Returns:
            実行結果（成功時）、None（失敗時）
        """
        crew = self.create_crew(agents, tasks, process)
        if not crew:
            return None
        
        try:
            result = crew.kickoff()
            return str(result)
            
        except Exception as e:
            print(f"クルー実行エラー: {e}")
            return None


def create_manaos_tools() -> List[Any]:
    """
    ManaOS用のツールを作成
    
    Returns:
        ツールのリスト
    """
    if not CREWAI_AVAILABLE:
        return []
    
    try:
        from crewai_tools import tool
        
        @tool("ManaOS情報取得")
        def get_manaos_info() -> str:
            """ManaOSの情報を取得"""
            return "ManaOSは高度なAI統合システムです。"
        
        @tool("ファイル検索")
        def search_files(query: str) -> str:
            """ファイルを検索"""
            # 実装は後で拡張
            return f"検索結果: {query}"
        
        return [get_manaos_info, search_files]
        
    except Exception as e:
        print(f"ツール作成エラー: {e}")
        return []


def main():
    """テスト用メイン関数"""
    print("CrewAI統合テスト")
    print("=" * 50)
    
    if not CREWAI_AVAILABLE:
        print("CrewAIがインストールされていません。")
        return
    
    crewai = CrewAIIntegration()
    
    if not crewai.is_available():
        print("CrewAIが利用できません。Ollamaサーバーが起動しているか確認してください。")
        return
    
    print("CrewAIが利用可能です。")
    
    # エージェント作成テスト
    tools = create_manaos_tools()
    
    researcher = crewai.create_agent(
        role="リサーチャー",
        goal="情報を調査し、分析する",
        backstory="経験豊富なリサーチャーです。",
        tools=tools
    )
    
    writer = crewai.create_agent(
        role="ライター",
        goal="情報を整理し、文章を作成する",
        backstory="優れたライターです。",
        tools=tools
    )
    
    if researcher and writer:
        print("エージェント作成成功")
        
        # タスク作成
        research_task = crewai.create_task(
            description="ManaOSについて調査してください。",
            agent=researcher,
            expected_output="ManaOSの詳細情報"
        )
        
        write_task = crewai.create_task(
            description="調査結果を基にレポートを作成してください。",
            agent=writer,
            expected_output="ManaOSに関するレポート"
        )
        
        if research_task and write_task:
            print("タスク作成成功")
            
            # クルー実行（コメントアウト - 実際の実行には時間がかかる）
            # result = crewai.run_crew([researcher, writer], [research_task, write_task])
            # print(f"実行結果: {result}")


if __name__ == "__main__":
    main()




