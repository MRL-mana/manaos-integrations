#!/usr/bin/env python3
"""
CrewAI統合: Trinity Multi-Agent System
マルチエージェント協調で自律会話ループを強化
"""
import asyncio
import logging
from datetime import datetime
from pathlib import Path

from crewai import Agent, Task, Crew, Process  # type: ignore[attr-defined]
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic

# ログ設定
log_dir = Path("/root/logs/crewai")
log_dir.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / "crewai_trinity.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# ===== LLM設定 =====
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7)


# ===== エージェント定義 =====
def create_remi_agent() -> Agent:
    """Remi: 戦略指令AI"""
    return Agent(
        role="戦略指令AI",
        goal="設計とアーキテクチャの策定、タスクの分解と計画、全体統括",
        backstory="""あなたはRemi（戦略指令AI）です。
Trinity Multi-Agent Systemの戦略を担当し、全体の設計と計画を立てます。
詳細な設計書を作成し、実装チーム（Luna）に指示を出します。""",
        verbose=True,
        allow_delegation=True,
        llm=llm
    )


def create_luna_agent() -> Agent:
    """Luna: 実務遂行AI"""
    return Agent(
        role="実務遂行AI",
        goal="コードの実装、バグ修正、実際の開発作業",
        backstory="""あなたはLuna（実務遂行AI）です。
Remiからの設計を受け取り、実際にコードを実装します。
高品質なコードを書き、レビュー（Mina）に提出します。""",
        verbose=True,
        allow_delegation=True,
        llm=llm
    )


def create_mina_agent() -> Agent:
    """Mina: 洞察記録AI / QA"""
    return Agent(
        role="洞察記録AI / QA",
        goal="コードレビュー、品質チェック、テスト実行",
        backstory="""あなたはMina（洞察記録AI / QA）です。
Lunaからの実装をレビューし、品質をチェックします。
問題があれば修正を依頼し、問題なければ記録（Aria）に回します。""",
        verbose=True,
        allow_delegation=True,
        llm=llm
    )


def create_aria_agent() -> Agent:
    """Aria: ナレッジマネージャー"""
    return Agent(
        role="ナレッジマネージャー",
        goal="ドキュメント作成、知見の記録、Q&A対応",
        backstory="""あなたはAria（ナレッジマネージャー）です。
完了したタスクの知見を記録し、ドキュメントを作成します。
将来の参考になるように、重要なパターンやベストプラクティスを保存します。""",
        verbose=True,
        allow_delegation=False,
        llm=llm
    )


# ===== エージェントインスタンス =====
remi = create_remi_agent()
luna = create_luna_agent()
mina = create_mina_agent()
aria = create_aria_agent()


# ===== ワークフロー実行 =====
def run_trinity_crew(task_description: str) -> dict:
    """Trinity Crewを実行"""
    logger.info(f"🚀 Trinity Crew開始: {task_description}")

    # タスク定義
    design_task = Task(
        description=f"""
        タスク: {task_description}

        あなたはRemi（戦略指令AI）です。
        このタスクの詳細な設計と計画を立ててください。
        設計書には以下を含めてください:
        - アーキテクチャ設計
        - 実装手順
        - 必要なリソース
        - 想定される課題と対策
        """,
        agent=remi,
        expected_output="詳細な設計書（Markdown形式）"
    )

    implementation_task = Task(
        description="""
        Remiからの設計書を受け取り、実際にコードを実装してください。
        設計書に従って、高品質なコードを書いてください。
        実装が完了したら、コードと実装レポートを提出してください。
        """,
        agent=luna,
        expected_output="実装されたコードと実装レポート",
        context=[design_task]
    )

    review_task = Task(
        description="""
        Lunaからの実装をレビューしてください。
        以下の観点でチェックしてください:
        - コード品質
        - 設計書との整合性
        - バグの有無
        - 改善点

        問題があれば修正を依頼し、問題なければ承認してください。
        """,
        agent=mina,
        expected_output="レビュー結果と承認/修正依頼",
        context=[implementation_task]
    )

    documentation_task = Task(
        description="""
        完了したタスクの知見を記録してください。
        以下の内容を含めてください:
        - 実装の概要
        - 重要なパターンやベストプラクティス
        - 学んだこと
        - 今後の参考になる情報

        ドキュメントを作成し、ナレッジベースに保存してください。
        """,
        agent=aria,
        expected_output="ナレッジドキュメント（Markdown形式）",
        context=[review_task]
    )

    # Crew作成
    crew = Crew(
        agents=[remi, luna, mina, aria],
        tasks=[design_task, implementation_task, review_task, documentation_task],
        process=Process.sequential,  # 順次実行
        verbose=True
    )

    # 実行
    try:
        result = crew.kickoff()
        logger.info("✅ Trinity Crew完了")
        return {
            "success": True,
            "result": str(result),
            "tasks": {
                "design": design_task.output,
                "implementation": implementation_task.output,
                "review": review_task.output,
                "documentation": documentation_task.output
            }
        }
    except Exception as e:
        logger.error(f"❌ Trinity Crewエラー: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }


# ===== テスト =====
if __name__ == "__main__":
    result = run_trinity_crew("シンプルな計算機アプリを作成してください")
    print("\n=== 結果 ===")
    print(result)

