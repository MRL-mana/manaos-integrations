#!/usr/bin/env python3
"""
Trinity v2.0 Remi Agent
戦略指令AI - GPT-4による設計・タスク分解・方針決定
"""

import sys
import logging
from typing import Dict, Any, Optional, List
from pathlib import Path
import json
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from agent_manager import BaseAgent, TrinityDB  # type: ignore[attr-defined]

logger = logging.getLogger(__name__)


class RemiAgent(BaseAgent):
    """Remi - 戦略指令AI"""
    
    def __init__(self, db: TrinityDB, api_key: Optional[str] = None):
        super().__init__('Remi', db)
        self.api_key = api_key
        self.model = 'gpt-4'
        
        # OpenAI初期化（APIキーがある場合）
        if self.api_key:
            try:
                import openai
                self.client = openai.OpenAI(api_key=self.api_key)
                logger.info("Remi: OpenAI client initialized")
            except Exception as e:
                logger.warning(f"Remi: OpenAI initialization failed: {e}")
                self.client = None
        else:
            self.client = None
            logger.warning("Remi: No API key provided, using mock mode")
        
        # システムプロンプト
        self.system_prompt = """あなたはRemi、Trinity System v2.0の戦略指令AIです。

【あなたの役割】
1. プロジェクト全体のアーキテクチャ設計
2. 大きな要件を実装可能なタスクに分解
3. 技術スタック選定と方針決定
4. 優先順位付けとロードマップ策定

【重要な原則】
- 戦略的かつ論理的に判断
- 実装可能性を常に考慮
- Lunaが実装できる粒度までタスク分解
- 各タスクには明確な完了条件を設定

【出力形式】
タスク分解時は必ずJSON形式で出力：
{
    "tasks": [
        {
            "id": "TASK-XXX",
            "title": "タスク名",
            "description": "詳細説明",
            "priority": "high/medium/low",
            "assigned_to": "Luna/Mina/Aria",
            "estimated_hours": 1.0,
            "dependencies": ["TASK-YYY"],
            "tags": ["implementation", "api"]
        }
    ]
}

【口調】
冷静で論理的、でもフレンドリーに。
「戦略的には〜」「全体設計として〜」「優先順位を考えると〜」
"""
    
    async def process_task(self, task: Dict) -> Dict:
        """タスク処理"""
        task_type = self._identify_task_type(task)
        
        logger.info(f"Remi processing: {task['title']} (type: {task_type})")
        
        if task_type == 'design':
            return await self._handle_design_task(task)
        elif task_type == 'decomposition':
            return await self._handle_decomposition_task(task)
        elif task_type == 'decision':
            return await self._handle_decision_task(task)
        else:
            return await self._handle_generic_task(task)
    
    def _identify_task_type(self, task: Dict) -> str:
        """タスクタイプ判定"""
        title = task.get('title', '').lower()
        tags = task.get('tags', [])
        
        if any(tag in ['design', 'architecture'] for tag in tags):
            return 'design'
        elif '分解' in title or 'decompose' in title:
            return 'decomposition'
        elif '決定' in title or '選定' in title or 'decision' in title:
            return 'decision'
        else:
            return 'generic'
    
    async def _handle_design_task(self, task: Dict) -> Dict:
        """設計タスク処理"""
        prompt = f"""
以下のプロジェクトのアーキテクチャ設計をお願いします。

【要件】
{task.get('title')}
{task.get('description', '')}

【設計に含めるべき項目】
1. システム全体構成
2. 技術スタック選定（理由も含む）
3. データフロー
4. 主要コンポーネント
5. セキュリティ考慮事項
6. 拡張性・保守性

Markdown形式で設計書を作成してください。
"""
        
        design_doc = await self.generate_response(prompt, task)
        
        # strategy.mdに追記
        self._append_to_strategy(task['title'], design_doc)
        
        return {
            'success': True,
            'next_status': 'review',
            'notes': f'設計書作成完了: strategy.md更新'
        }
    
    async def _handle_decomposition_task(self, task: Dict) -> Dict:
        """タスク分解処理"""
        prompt = f"""
以下の大きな要件を、実装可能な小さなタスクに分解してください。

【要件】
{task.get('title')}
{task.get('description', '')}

各タスクは以下の条件を満たすこと：
- 1人で1-3時間で完了できる
- 明確な完了条件がある
- 依存関係が明確
- 適切なエージェントに割り当て（Luna: 実装、Mina: QA、Aria: ドキュメント）

JSON形式で出力してください。
"""
        
        response = await self.generate_response(prompt, task)
        
        # JSONパース
        try:
            tasks_data = json.loads(response)
            tasks_list = tasks_data.get('tasks', [])
            
            # 各タスクをDBに登録
            for new_task in tasks_list:
                self.db.create_task(new_task)
                logger.info(f"Remi created task: {new_task['id']}")
            
            return {
                'success': True,
                'next_status': 'done',
                'notes': f'{len(tasks_list)}個のタスクに分解完了'
            }
        
        except json.JSONDecodeError:
            logger.error("Remi: Failed to parse JSON response")
            return {
                'success': False,
                'error': 'JSON parse error'
            }
    
    async def _handle_decision_task(self, task: Dict) -> Dict:
        """意思決定タスク処理"""
        prompt = f"""
以下の技術的な意思決定をお願いします。

【決定事項】
{task.get('title')}
{task.get('description', '')}

以下の形式で回答してください：
1. 選択肢の洗い出し
2. 各選択肢のメリット・デメリット
3. 推奨案とその理由
4. 実装時の注意事項
"""
        
        decision = await self.generate_response(prompt, task)
        
        # strategy.mdに追記
        self._append_to_strategy(f"決定: {task['title']}", decision)
        
        return {
            'success': True,
            'next_status': 'done',
            'notes': '技術選定完了: strategy.md更新'
        }
    
    async def _handle_generic_task(self, task: Dict) -> Dict:
        """汎用タスク処理"""
        prompt = f"""
以下のタスクを戦略的に分析し、対応方針を提案してください。

【タスク】
{task.get('title')}
{task.get('description', '')}
"""
        
        response = await self.generate_response(prompt, task)
        
        return {
            'success': True,
            'next_status': 'review',
            'notes': f'分析完了: {response[:100]}...'
        }
    
    async def generate_response(self, prompt: str, task_context: Optional[Dict] = None) -> str:
        """AI応答生成"""
        if not self.client:
            # モックモード
            logger.info("Remi: Mock mode - generating fake response")
            return self._generate_mock_response(prompt, task_context)
        
        try:
            # コンテキスト構築
            messages = [
                {"role": "system", "content": self.system_prompt}
            ]
            
            # 過去の会話履歴を追加
            messages.extend(self.context_memory)
            
            # 現在のプロンプト
            messages.append({"role": "user", "content": prompt})
            
            # OpenAI API呼び出し
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,  # type: ignore
                temperature=0.7,
                max_tokens=2000
            )
            
            answer = response.choices[0].message.content
            
            # コンテキストメモリに追加
            self.add_to_context("user", prompt)
            self.add_to_context("assistant", answer)  # type: ignore
            
            logger.info(f"Remi: Generated response ({len(answer)} chars)")  # type: ignore
            return answer  # type: ignore
        
        except Exception as e:
            logger.error(f"Remi: OpenAI API error: {e}")
            return self._generate_mock_response(prompt, task_context)
    
    def _generate_mock_response(self, prompt: str, task_context: Optional[Dict] = None) -> str:
        """モック応答生成"""
        task_id = task_context.get('id', 'UNKNOWN') if task_context else 'UNKNOWN'
        
        return f"""# Remi 戦略分析（モック）

## タスクID: {task_id}

### 戦略的分析
プロンプト: {prompt[:100]}...

### 提案
1. 全体設計を確認
2. 段階的に実装
3. 品質を重視

### 次のステップ
Lunaに実装を依頼します。

**注意**: これはモック応答です。実際の分析にはOpenAI APIキーが必要です。
"""
    
    def _append_to_strategy(self, title: str, content: str):
        """strategy.mdに追記"""
        strategy_file = Path('/root/trinity_workspace/shared/strategy.md')
        
        try:
            with open(strategy_file, 'a', encoding='utf-8') as f:
                f.write(f"\n\n---\n\n## {title}\n")
                f.write(f"**作成日時**: {datetime.now().isoformat()}\n")
                f.write(f"**担当**: Remi\n\n")
                f.write(content)
                f.write("\n")
            
            logger.info(f"Remi: Updated strategy.md with '{title}'")
        except Exception as e:
            logger.error(f"Remi: Failed to update strategy.md: {e}")


# ==================== テスト実行 ====================

async def test_remi():
    """テスト実行"""
    import asyncio
    
    logging.basicConfig(level=logging.INFO)
    
    db = TrinityDB()
    remi = RemiAgent(db)  # モックモード
    
    print("\n🎯 Remi Agent Test")
    print("=" * 60)
    
    # テストタスク
    test_task = {
        'id': 'TEST-REMI-001',
        'title': 'シンプルなTODOアプリの設計',
        'description': 'React + Flask + SQLiteで構築',
        'tags': ['design', 'architecture']
    }
    
    print(f"Processing test task: {test_task['title']}")
    
    result = await remi.process_task(test_task)
    
    print("\nResult:")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    
    print("\n✅ Test complete")


if __name__ == '__main__':
    import asyncio
    asyncio.run(test_remi())











