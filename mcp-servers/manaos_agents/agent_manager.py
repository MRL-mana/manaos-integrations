#!/usr/bin/env python3
"""
ManaOS Agent Manager
OpenAI Agents SDK風のマルチエージェント管理システム
Trinity達が使えるシンプルなインターフェース
"""

import os
import json
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime
from openai import OpenAI

class Agent:
    """単一エージェントクラス"""
    
    def __init__(
        self,
        name: str,
        role: str,
        instructions: str,
        model: str = "gpt-4",
        tools: Optional[List[Callable]] = None
    ):
        self.name = name
        self.role = role
        self.instructions = instructions
        self.model = model
        self.tools = tools or []
        self.conversation_history = []
        
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "role": self.role,
            "instructions": self.instructions,
            "model": self.model
        }


class AgentManager:
    """エージェント管理システム"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        初期化
        Args:
            api_key: OpenAI APIキー (省略時は環境変数から取得)
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if self.api_key:
            self.client = OpenAI(api_key=self.api_key)
        else:
            self.client = None
            print("⚠️  OpenAI APIキーが設定されていません。")
            print("   環境変数 OPENAI_API_KEY を設定するか、初期化時に渡してください。")
        
        self.agents: Dict[str, Agent] = {}
        self.active_agent: Optional[Agent] = None
        self.log_file = "/root/manaos_agents/agent_activity.log"
        
    def create_agent(
        self,
        name: str,
        role: str,
        instructions: str,
        model: str = "gpt-4",
        tools: Optional[List[Callable]] = None
    ) -> Agent:
        """
        新しいエージェントを作成
        
        Args:
            name: エージェント名
            role: 役割（例: "データ分析", "コード生成"）
            instructions: エージェントへの指示
            model: 使用するモデル
            tools: 使用可能なツール
            
        Returns:
            作成されたエージェント
        """
        agent = Agent(name, role, instructions, model, tools)
        self.agents[name] = agent
        self._log(f"エージェント作成: {name} ({role})")
        return agent
        
    def get_agent(self, name: str) -> Optional[Agent]:
        """エージェントを取得"""
        return self.agents.get(name)
        
    def list_agents(self) -> List[Dict[str, Any]]:
        """全エージェントのリストを取得"""
        return [agent.to_dict() for agent in self.agents.values()]
        
    def set_active_agent(self, name: str) -> bool:
        """アクティブなエージェントを設定"""
        agent = self.get_agent(name)
        if agent:
            self.active_agent = agent
            self._log(f"アクティブエージェント変更: {name}")
            return True
        return False
        
    def run_agent(
        self,
        agent_name: str,
        task: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        エージェントにタスクを実行させる
        
        Args:
            agent_name: エージェント名
            task: 実行するタスク
            context: コンテキスト情報
            
        Returns:
            実行結果
        """
        agent = self.get_agent(agent_name)
        if not agent:
            return {
                "success": False,
                "error": f"エージェント '{agent_name}' が見つかりません"
            }
            
        if not self.client:
            return {
                "success": False,
                "error": "OpenAI APIキーが設定されていません"
            }
            
        try:
            # システムメッセージとタスクを組み立て
            messages = [
                {"role": "system", "content": f"{agent.instructions}\n役割: {agent.role}"},
                {"role": "user", "content": task}
            ]
            
            # コンテキストがあれば追加
            if context:
                messages.insert(1, {
                    "role": "system",
                    "content": f"コンテキスト: {json.dumps(context, ensure_ascii=False)}"
                })
            
            # OpenAI APIを呼び出し
            response = self.client.chat.completions.create(
                model=agent.model,
                messages=messages,
                temperature=0.7,
                max_tokens=2000
            )
            
            result = response.choices[0].message.content
            
            # 会話履歴に追加
            agent.conversation_history.append({
                "task": task,
                "result": result,
                "timestamp": datetime.now().isoformat()
            })
            
            self._log(f"タスク実行: {agent_name} - {task[:50]}...")
            
            return {
                "success": True,
                "agent": agent_name,
                "result": result,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            error_msg = f"エラー: {str(e)}"
            self._log(error_msg)
            return {
                "success": False,
                "error": error_msg
            }
    
    def collaborate(
        self,
        agent_names: List[str],
        task: str,
        orchestrator_instructions: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        複数のエージェントで協力してタスクを実行
        
        Args:
            agent_names: 協力するエージェント名のリスト
            task: 実行するタスク
            orchestrator_instructions: オーケストレーターへの指示
            
        Returns:
            協力実行の結果
        """
        results = []
        
        for agent_name in agent_names:
            result = self.run_agent(agent_name, task)
            results.append(result)
            
        # 結果を統合
        if orchestrator_instructions and self.client:
            combined_results = "\n\n".join([
                f"【{r.get('agent', 'unknown')}の結果】\n{r.get('result', '')}"
                for r in results if r.get('success')
            ])
            
            # 統合タスクを実行
            integration_result = self.run_agent(
                agent_names[0],
                f"{orchestrator_instructions}\n\n各エージェントの結果:\n{combined_results}"
            )
            
            return {
                "success": True,
                "individual_results": results,
                "integrated_result": integration_result.get("result"),
                "timestamp": datetime.now().isoformat()
            }
        
        return {
            "success": True,
            "results": results,
            "timestamp": datetime.now().isoformat()
        }
    
    def save_state(self, filepath: str = "/root/manaos_agents/agent_state.json"):
        """エージェントの状態を保存"""
        state = {
            "agents": [agent.to_dict() for agent in self.agents.values()],
            "active_agent": self.active_agent.name if self.active_agent else None,
            "timestamp": datetime.now().isoformat()
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
            
        self._log(f"状態保存: {filepath}")
        
    def load_state(self, filepath: str = "/root/manaos_agents/agent_state.json"):
        """エージェントの状態を読み込み"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                state = json.load(f)
                
            # エージェントを再作成
            for agent_data in state.get("agents", []):
                self.create_agent(
                    name=agent_data["name"],
                    role=agent_data["role"],
                    instructions=agent_data["instructions"],
                    model=agent_data.get("model", "gpt-4")
                )
            
            # アクティブエージェントを設定
            if state.get("active_agent"):
                self.set_active_agent(state["active_agent"])
                
            self._log(f"状態読み込み: {filepath}")
            return True
            
        except FileNotFoundError:
            self._log(f"状態ファイルが見つかりません: {filepath}")
            return False
            
    def _log(self, message: str):
        """ログを記録"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] {message}\n"
        
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(log_message)
        except Exception as e:
            print(f"ログ記録エラー: {e}")


# デフォルトのエージェント定義
DEFAULT_AGENTS = {
    "researcher": {
        "name": "Researcher",
        "role": "情報収集・調査",
        "instructions": "あなたは優秀なリサーチャーです。与えられたトピックについて詳細に調査し、正確で有用な情報を提供してください。"
    },
    "coder": {
        "name": "Coder",
        "role": "コード生成・レビュー",
        "instructions": "あなたは優秀なプログラマーです。高品質で保守性の高いコードを書き、ベストプラクティスに従ってください。"
    },
    "analyzer": {
        "name": "Analyzer",
        "role": "データ分析",
        "instructions": "あなたはデータアナリストです。データを分析し、インサイトを導き出し、分かりやすく説明してください。"
    },
    "writer": {
        "name": "Writer",
        "role": "文書作成",
        "instructions": "あなたは優秀なライターです。明確で分かりやすく、魅力的な文章を書いてください。"
    }
}


def setup_default_agents(manager: AgentManager):
    """デフォルトエージェントをセットアップ"""
    for agent_data in DEFAULT_AGENTS.values():
        manager.create_agent(**agent_data)


if __name__ == "__main__":
    # テスト実行
    print("🤖 ManaOS Agent Manager テスト")
    print("=" * 50)
    
    manager = AgentManager()
    setup_default_agents(manager)
    
    print("\n作成されたエージェント:")
    for agent in manager.list_agents():
        print(f"  - {agent['name']}: {agent['role']}")
    
    print("\n✅ Agent Manager初期化完了!")

