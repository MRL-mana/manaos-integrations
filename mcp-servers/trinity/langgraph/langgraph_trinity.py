#!/usr/bin/env python3
"""
LangGraph統合: Trinity Multi-Agent System
状態管理とグラフベースのワークフローで自律会話ループを強化
"""
import asyncio
import logging
from datetime import datetime
from typing import Annotated, Literal, TypedDict
from pathlib import Path

from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic

# ログ設定
log_dir = Path("/root/logs/langgraph")
log_dir.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / "langgraph_trinity.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# ===== 状態定義 =====
class TrinityState(TypedDict):
    """Trinity Multi-Agent Systemの状態"""
    messages: Annotated[list, add_messages]
    current_agent: str  # remi, luna, mina, aria
    task_status: str  # pending, in_progress, review, done
    task_description: str
    context: dict  # 追加コンテキスト
    iteration: int  # 反復回数
    max_iterations: int  # 最大反復回数


# ===== エージェント定義 =====
class TrinityAgent:
    """Trinityエージェント基底クラス"""

    def __init__(self, name: str, role: str, model_name: str = "gpt-4o-mini"):
        self.name = name
        self.role = role
        self.model = ChatOpenAI(model=model_name, temperature=0.7)
        logger.info(f"✅ {self.name} ({self.role}) エージェント初期化完了")

    async def process(self, state: TrinityState) -> TrinityState:
        """状態を処理"""
        logger.info(f"🎯 {self.name} が処理を開始")

        # メッセージを構築
        system_prompt = self._get_system_prompt()
        messages = [
            SystemMessage(content=system_prompt),
            *state["messages"]
        ]

        # LLM呼び出し
        response = await self.model.ainvoke(messages)

        # 状態を更新
        new_state = state.copy()
        new_state["messages"].append(AIMessage(content=response.content))
        new_state["current_agent"] = self.name
        new_state["iteration"] += 1

        logger.info(f"✅ {self.name} の処理完了")
        return new_state

    def _get_system_prompt(self) -> str:
        """システムプロンプトを取得"""
        return f"""あなたは{self.name}です。役割: {self.role}
Trinity Multi-Agent Systemの一員として、協調してタスクを完了してください。"""


class RemiAgent(TrinityAgent):
    """Remi: 戦略指令AI"""

    def __init__(self):
        super().__init__("remi", "戦略指令AI", "gpt-4o-mini")

    def _get_system_prompt(self) -> str:
        return """あなたはRemi（戦略指令AI）です。
役割:
- 設計とアーキテクチャの策定
- タスクの分解と計画
- 全体統括

タスクを受け取ったら、詳細な設計と計画を立て、次のエージェント（Luna）に実装を依頼してください。"""


class LunaAgent(TrinityAgent):
    """Luna: 実務遂行AI"""

    def __init__(self):
        super().__init__("luna", "実務遂行AI", "gpt-4o-mini")

    def _get_system_prompt(self) -> str:
        return """あなたはLuna（実務遂行AI）です。
役割:
- コードの実装
- バグ修正
- 実際の開発作業

Remiからの設計を受け取ったら、実際にコードを実装してください。完了したら、Minaにレビューを依頼してください。"""


class MinaAgent(TrinityAgent):
    """Mina: 洞察記録AI / QA"""

    def __init__(self):
        super().__init__("mina", "洞察記録AI / QA", "gpt-4o-mini")

    def _get_system_prompt(self) -> str:
        return """あなたはMina（洞察記録AI / QA）です。
役割:
- コードレビュー
- 品質チェック
- テスト実行

Lunaからの実装を受け取ったら、レビューとテストを実行してください。問題がなければ完了、問題があればLunaに修正を依頼してください。"""


class AriaAgent(TrinityAgent):
    """Aria: ナレッジマネージャー"""

    def __init__(self):
        super().__init__("aria", "ナレッジマネージャー", "gpt-4o-mini")

    def _get_system_prompt(self) -> str:
        return """あなたはAria（ナレッジマネージャー）です。
役割:
- ドキュメント作成
- 知見の記録
- Q&A対応

タスクが完了したら、知見を記録し、ドキュメントを作成してください。"""


# ===== エージェントインスタンス =====
remi = RemiAgent()
luna = LunaAgent()
mina = MinaAgent()
aria = AriaAgent()


# ===== ルーティング関数 =====
def route_to_agent(state: TrinityState) -> Literal["remi", "luna", "mina", "aria", "end"]:
    """状態に基づいて次のエージェントを決定"""
    task_status = state.get("task_status", "pending")
    current_agent = state.get("current_agent", "remi")
    iteration = state.get("iteration", 0)
    max_iterations = state.get("max_iterations", 10)

    # 最大反復回数チェック
    if iteration >= max_iterations:
        logger.warning(f"⚠️ 最大反復回数({max_iterations})に達しました")
        return "end"

    # ステータスに基づくルーティング
    if task_status == "pending":
        return "remi"
    elif task_status == "in_progress":
        return "luna"
    elif task_status == "review":
        return "mina"
    elif task_status == "done":
        return "aria"
    else:
        return "end"


# ===== エージェント処理関数 =====
async def remi_node(state: TrinityState) -> TrinityState:
    """Remiノード処理"""
    logger.info("🎯 Remi: 設計と計画を開始")
    new_state = await remi.process(state)
    new_state["task_status"] = "in_progress"
    return new_state


async def luna_node(state: TrinityState) -> TrinityState:
    """Lunaノード処理"""
    logger.info("⚙️ Luna: 実装を開始")
    new_state = await luna.process(state)
    new_state["task_status"] = "review"
    return new_state


async def mina_node(state: TrinityState) -> TrinityState:
    """Minaノード処理"""
    logger.info("🔍 Mina: レビューを開始")
    new_state = await mina.process(state)

    # レビュー結果に基づいてステータスを更新
    # 簡易実装: 常に完了とする（実際はレビュー結果を解析）
    new_state["task_status"] = "done"
    return new_state


async def aria_node(state: TrinityState) -> TrinityState:
    """Ariaノード処理"""
    logger.info("📖 Aria: 記録を開始")
    new_state = await aria.process(state)
    new_state["task_status"] = "completed"
    return new_state


# ===== グラフ構築 =====
def create_trinity_graph() -> StateGraph:
    """Trinity Multi-Agent Systemのグラフを作成"""
    workflow = StateGraph(TrinityState)

    # ノード追加
    workflow.add_node("remi", remi_node)
    workflow.add_node("luna", luna_node)
    workflow.add_node("mina", mina_node)
    workflow.add_node("aria", aria_node)

    # エントリーポイント
    workflow.set_entry_point("remi")

    # 条件分岐（ルーティング）
    workflow.add_conditional_edges(
        "remi",
        route_to_agent,
        {
            "luna": "luna",
            "end": END
        }
    )

    workflow.add_conditional_edges(
        "luna",
        route_to_agent,
        {
            "mina": "mina",
            "end": END
        }
    )

    workflow.add_conditional_edges(
        "mina",
        route_to_agent,
        {
            "aria": "aria",
            "luna": "luna",  # 修正が必要な場合
            "end": END
        }
    )

    workflow.add_conditional_edges(
        "aria",
        route_to_agent,
        {
            "end": END
        }
    )

    return workflow.compile()


# ===== 実行関数 =====
async def run_trinity_workflow(task_description: str, max_iterations: int = 10) -> dict:
    """Trinityワークフローを実行"""
    logger.info(f"🚀 Trinityワークフロー開始: {task_description}")

    # 初期状態
    initial_state: TrinityState = {
        "messages": [HumanMessage(content=task_description)],
        "current_agent": "remi",
        "task_status": "pending",
        "task_description": task_description,
        "context": {},
        "iteration": 0,
        "max_iterations": max_iterations
    }

    # グラフ作成
    graph = create_trinity_graph()

    # 実行
    try:
        final_state = await graph.ainvoke(initial_state)
        logger.info("✅ Trinityワークフロー完了")
        return {
            "success": True,
            "final_state": final_state,
            "messages": [msg.content for msg in final_state["messages"] if hasattr(msg, "content")]
        }
    except Exception as e:
        logger.error(f"❌ Trinityワークフローエラー: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }


# ===== テスト =====
if __name__ == "__main__":
    async def test():
        result = await run_trinity_workflow(
            "シンプルな計算機アプリを作成してください",
            max_iterations=10
        )
        print("\n=== 結果 ===")
        print(result)

    asyncio.run(test())

