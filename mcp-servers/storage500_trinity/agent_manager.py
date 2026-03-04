#!/usr/bin/env python3
"""
Trinity v2.0 Agent Manager
AIエージェント統合管理システム
"""

import os
import sys
import logging
from typing import Dict, Optional, List
from pathlib import Path
from abc import ABC, abstractmethod
import asyncio

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent / 'core'))

from db_manager import TrinityDB

logger = logging.getLogger(__name__)

# Phase 7統合: AIキャッシュ＋Ollama
try:
    from ai_cache import ai_cache
    from ollama_integration import ollama
    AI_CACHE_AVAILABLE = True
    OLLAMA_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Phase 7 features not available: {e}")
    AI_CACHE_AVAILABLE = False
    OLLAMA_AVAILABLE = False
    ai_cache = None
    ollama = None


class BaseAgent(ABC):
    """エージェント基底クラス"""
    
    def __init__(self, name: str, db: TrinityDB, use_cache: bool = True, use_ollama: bool = True):
        self.name = name
        self.db = db
        self.status = 'offline'
        self.current_task_id: Optional[str] = None
        self.context_memory: List[Dict] = []  # 会話履歴

        # Phase 7: キャッシュ＋Ollama
        self.use_cache = use_cache and AI_CACHE_AVAILABLE
        self.use_ollama = use_ollama and OLLAMA_AVAILABLE
        self.ai_cache = ai_cache if self.use_cache else None
        self.ollama = ollama if self.use_ollama else None

        logger.info(f"{self.name} agent initialized (cache:{self.use_cache}, ollama:{self.use_ollama})")
    
    def set_status(self, status: str):
        """ステータス更新"""
        self.status = status
        self.db.update_agent_status(self.name, status, self.current_task_id)
        logger.info(f"{self.name} status: {status}")
    
    def add_to_context(self, role: str, content: str):
        """コンテキストメモリに追加"""
        self.context_memory.append({
            'role': role,
            'content': content
        })
        
        # メモリ管理（最新10件のみ保持）
        if len(self.context_memory) > 10:
            self.context_memory = self.context_memory[-10:]
    
    @abstractmethod
    async def process_task(self, task: Dict) -> Dict:
        """タスク処理（各エージェントで実装）"""
        pass
    
    @abstractmethod
    async def generate_response(self, prompt: str, task_context: Optional[Dict] = None) -> str:
        """AI応答生成（各エージェントで実装）"""
        pass

    async def generate_with_cache(self, model: str, prompt: str, task: Optional[Dict] = None) -> str:
        """
        AI応答生成（キャッシュ＋Ollama対応）

        Args:
            model: モデル名
            prompt: プロンプト
            task: タスクデータ（Ollama判定用）

        Returns:
            生成された応答
        """
        # キャッシュチェック
        if self.use_cache and self.ai_cache:
            cached = self.ai_cache.get(model, prompt)
            if cached:
                logger.info(f"{self.name}: Cache HIT")
                return cached

        # Ollama判定（簡単なタスクはローカルLLMで処理）
        if self.use_ollama and self.ollama and task:
            if self.ollama.is_simple_task(task):
                selected_model = self.ollama.select_model_for_task(task)
                logger.info(f"{self.name}: Using Ollama ({selected_model}) for simple task")

                response = await self.ollama.generate(selected_model, prompt)

                # キャッシュ保存
                if self.use_cache and self.ai_cache:
                    self.ai_cache.set(model, prompt, response)

                return response

        # 通常のAI API呼び出し（各エージェントの実装）
        response = await self.generate_response(prompt, task)

        # キャッシュ保存
        if self.use_cache and self.ai_cache:
            self.ai_cache.set(model, prompt, response)

        return response
    
    async def handle_task(self, task_id: str) -> bool:
        """タスク処理メイン"""
        task = self.db.get_task(task_id)
        
        if not task:
            logger.error(f"Task not found: {task_id}")
            return False
        
        logger.info(f"{self.name} handling task: {task_id}")
        
        # ステータス更新
        self.current_task_id = task_id
        self.set_status('busy')
        self.db.update_task(task_id, {'status': 'in_progress'})
        
        try:
            # タスク処理実行
            result = await self.process_task(task)
            
            if result.get('success', False):
                # 成功
                self.db.update_task(task_id, {
                    'status': result.get('next_status', 'review'),
                    'notes': result.get('notes', '')
                })
                logger.info(f"{self.name} completed task: {task_id}")
                return True
            else:
                # 失敗
                self.db.update_task(task_id, {
                    'status': 'blocked',
                    'notes': f"Error: {result.get('error', 'Unknown error')}"
                })
                logger.error(f"{self.name} failed task: {task_id}")
                return False
        
        except Exception as e:
            logger.error(f"{self.name} task error: {e}")
            self.db.update_task(task_id, {
                'status': 'blocked',
                'notes': f"Exception: {str(e)}"
            })
            return False
        
        finally:
            # ステータスリセット
            self.current_task_id = None
            self.set_status('online')


class AgentManager:
    """エージェント統合マネージャー"""
    
    def __init__(self, db: Optional[TrinityDB] = None):
        self.db = db or TrinityDB()
        self.agents: Dict[str, BaseAgent] = {}
        self.api_keys = self._load_api_keys()
        
        logger.info("AgentManager initialized")
    
    def _load_api_keys(self) -> Dict[str, str]:
        """APIキー読み込み"""
        api_keys = {}
        
        vault_dir = Path('/root/.mana_vault')
        
        # OpenAI
        openai_key_file = vault_dir / 'openai_api_key.enc'
        if openai_key_file.exists():
            try:
                # TODO: 実際には復号化処理
                with open(openai_key_file, 'r') as f:
                    api_keys['openai'] = f.read().strip()
            except Exception as e:
                logger.error(f"Failed to load OpenAI key: {e}")
        
        # 環境変数からも取得
        if 'OPENAI_API_KEY' in os.environ:
            api_keys['openai'] = os.environ['OPENAI_API_KEY']
        
        if 'ANTHROPIC_API_KEY' in os.environ:
            api_keys['anthropic'] = os.environ['ANTHROPIC_API_KEY']
        
        # セキュリティ注意: APIキーの値は絶対にログに出力しない
        # キー名のリストのみログに記録（値は含まない）
        logger.info(f"Loaded API keys: {list(api_keys.keys())}")
        return api_keys
    
    def register_agent(self, agent: BaseAgent):
        """エージェント登録"""
        self.agents[agent.name] = agent
        agent.set_status('online')
        logger.info(f"Agent registered: {agent.name}")
    
    def get_agent(self, agent_name: str) -> Optional[BaseAgent]:
        """エージェント取得"""
        return self.agents.get(agent_name)
    
    async def dispatch_task(self, task_id: str) -> bool:
        """タスクを適切なエージェントにディスパッチ"""
        task = self.db.get_task(task_id)
        
        if not task:
            logger.error(f"Task not found: {task_id}")
            return False
        
        assigned_to = task.get('assigned_to')
        
        if not assigned_to:
            logger.warning(f"Task {task_id} has no assigned agent")
            return False
        
        agent = self.get_agent(assigned_to)
        
        if not agent:
            logger.error(f"Agent not found: {assigned_to}")
            return False
        
        # エージェントにタスク処理を依頼
        success = await agent.handle_task(task_id)
        
        return success
    
    async def process_pending_tasks(self):
        """保留中のタスクを処理"""
        # 各エージェントの todo タスクを取得
        for agent_name in self.agents.keys():
            tasks = self.db.get_tasks(status='todo', assigned_to=agent_name)
            
            for task in tasks:
                logger.info(f"Processing pending task: {task['id']} -> {agent_name}")
                await self.dispatch_task(task['id'])
    
    def shutdown(self):
        """シャットダウン"""
        logger.info("Shutting down agents...")
        
        for agent in self.agents.values():
            agent.set_status('offline')
        
        logger.info("All agents offline")


# ==================== Mock Agent（開発用）====================

class MockAgent(BaseAgent):
    """開発・テスト用のモックエージェント"""
    
    async def process_task(self, task: Dict) -> Dict:
        """タスク処理（モック）"""
        logger.info(f"{self.name} mock processing: {task['title']}")
        
        # 2秒待機（処理シミュレーション）
        await asyncio.sleep(2)
        
        return {
            'success': True,
            'next_status': 'review',
            'notes': f"{self.name} completed (mock)"
        }
    
    async def generate_response(self, prompt: str, task_context: Optional[Dict] = None) -> str:
        """AI応答生成（モック）"""
        return f"Mock response from {self.name}: {prompt[:50]}..."


# ==================== テスト実行 ====================

async def test_agent_manager():
    """テスト実行"""
    logging.basicConfig(level=logging.INFO)
    
    db = TrinityDB()
    manager = AgentManager(db)
    
    # モックエージェント登録
    for agent_name in ['Remi', 'Luna', 'Mina', 'Aria']:
        agent = MockAgent(agent_name, db)
        manager.register_agent(agent)
    
    print("\n🤖 Agent Manager Test")
    print("=" * 60)
    print("Registered agents:", list(manager.agents.keys()))
    
    # 保留タスクを処理
    print("\nProcessing pending tasks...")
    await manager.process_pending_tasks()
    
    print("\n✅ Test complete")
    
    manager.shutdown()


if __name__ == '__main__':
    asyncio.run(test_agent_manager())

