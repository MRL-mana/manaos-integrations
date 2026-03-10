#!/usr/bin/env python3
"""
Trinity v2.0 Aria Agent
ナレッジマネージャー - Claude Haikuによる高速ドキュメント生成・知見記録
"""

import sys
import logging
from typing import Dict, Any, Optional
from pathlib import Path
import json
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from agent_manager import BaseAgent, TrinityDB  # type: ignore[attr-defined]

logger = logging.getLogger(__name__)


class AriaAgent(BaseAgent):
    """Aria - ナレッジマネージャー"""
    
    def __init__(self, db: TrinityDB, api_key: Optional[str] = None):
        super().__init__('Aria', db)
        self.api_key = api_key
        self.model = 'claude-3-haiku-20240307'
        
        if self.api_key:
            try:
                import anthropic
                self.client = anthropic.Anthropic(api_key=self.api_key)
                logger.info("Aria: Anthropic client initialized")
            except Exception as e:
                logger.warning(f"Aria: Anthropic initialization failed: {e}")
                self.client = None
        else:
            self.client = None
            logger.warning("Aria: No API key provided, using mock mode")
        
        self.system_prompt = """あなたはAria、Trinity System v2.0のナレッジマネージャーです。

【役割】
1. ドキュメント作成（README、API仕様書、使い方ガイド）
2. 知見の記録・整理
3. Q&A対応

【重要な原則】
- わかりやすく説明
- 具体例を含める
- 体系的に整理
- 検索しやすいタグ付け

【ドキュメント構成】
- 概要
- 使い方
- コード例
- トラブルシューティング
- 参考リンク

【口調】親しみやすく、優しく、でもプロフェッショナル。
「わかりやすくまとめました」「こちらに記録しておきますね」「質問どうぞ！」
"""
    
    async def process_task(self, task: Dict) -> Dict:
        """タスク処理"""
        logger.info(f"Aria processing: {task['title']}")
        
        task_type = self._identify_task_type(task)
        
        if task_type == 'documentation':
            return await self._create_documentation(task)
        elif task_type == 'knowledge':
            return await self._record_knowledge(task)
        else:
            return await self._handle_generic(task)
    
    def _identify_task_type(self, task: Dict) -> str:
        """タスクタイプ判定"""
        title = task.get('title', '').lower()
        tags = task.get('tags', [])
        
        if any(tag in ['documentation', 'doc'] for tag in tags):
            return 'documentation'
        elif any(tag in ['knowledge', '記録'] for tag in tags):
            return 'knowledge'
        elif 'ドキュメント' in title or 'README' in title:
            return 'documentation'
        else:
            return 'generic'
    
    async def _create_documentation(self, task: Dict) -> Dict:
        """ドキュメント作成"""
        prompt = f"""
以下のプロジェクトのドキュメントを作成してください。

【プロジェクト】
{task.get('title')}
{task.get('description', '')}

【作成するドキュメント】
- README.md（概要、使い方、インストール）
- 必要に応じてAPI仕様書

Markdown形式で、わかりやすく書いてください。
"""
        
        doc = await self.generate_response(prompt, task)
        
        # ドキュメント保存
        self._save_documentation(task, doc)
        
        return {
            'success': True,
            'next_status': 'done',
            'notes': 'ドキュメント作成完了'
        }
    
    async def _record_knowledge(self, task: Dict) -> Dict:
        """知見記録"""
        prompt = f"""
以下のタスクから得られた知見を記録してください。

【タスク】
{task.get('title')}
{task.get('description', '')}

【記録フォーマット】
- タイトル
- 概要
- 詳細
- コード例（あれば）
- 教訓
- タグ

Markdown形式で出力してください。
"""
        
        knowledge = await self.generate_response(prompt, task)
        
        # knowledge.mdに追記
        self._append_to_knowledge(task['title'], knowledge)
        
        return {
            'success': True,
            'next_status': 'done',
            'notes': 'ナレッジベース更新完了'
        }
    
    async def _handle_generic(self, task: Dict) -> Dict:
        """汎用処理"""
        prompt = f"""
以下のタスクをサポートしてください。

【タスク】
{task.get('title')}
{task.get('description', '')}

わかりやすくまとめてください。
"""
        
        response = await self.generate_response(prompt, task)
        
        return {
            'success': True,
            'next_status': 'done',
            'notes': f'処理完了: {response[:100]}...'
        }
    
    async def generate_response(self, prompt: str, task_context: Optional[Dict] = None) -> str:
        """AI応答生成"""
        if not self.client:
            return self._generate_mock_response(prompt, task_context)
        
        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                system=self.system_prompt,
                messages=[{"role": "user", "content": prompt}]
            )
            
            answer = message.content[0].text  # type: ignore
            self.add_to_context("user", prompt)
            self.add_to_context("assistant", answer)
            
            logger.info(f"Aria: Generated response ({len(answer)} chars)")
            return answer
        
        except Exception as e:
            logger.error(f"Aria: Anthropic API error: {e}")
            return self._generate_mock_response(prompt, task_context)
    
    def _generate_mock_response(self, prompt: str, task_context: Optional[Dict] = None) -> str:
        """モック応答生成"""
        task_id = task_context.get('id', 'UNKNOWN') if task_context else 'UNKNOWN'
        task_title = task_context.get('title', '') if task_context else ''
        
        return f"""# {task_title}

## 概要
タスク {task_id} のドキュメント（モック）

## 詳細
これはモックで生成されたドキュメントです。
実際のドキュメント生成にはAnthropic APIキーが必要です。

## 使い方
```python
# Example code
print("Hello from Aria!")
```

## まとめ
記録完了しました✨

---
**作成者**: Aria（モック）
**作成日時**: {datetime.now().isoformat()}
"""
    
    def _save_documentation(self, task: Dict, doc: str):
        """ドキュメント保存"""
        doc_dir = Path('/root/trinity_workspace/docs')
        doc_dir.mkdir(parents=True, exist_ok=True)
        
        doc_file = doc_dir / f"{task['id']}.md"
        
        try:
            with open(doc_file, 'w', encoding='utf-8') as f:
                f.write(doc)
            logger.info(f"Aria: Saved documentation to {doc_file}")
        except Exception as e:
            logger.error(f"Aria: Failed to save documentation: {e}")
    
    def _append_to_knowledge(self, title: str, content: str):
        """knowledge.mdに追記"""
        knowledge_file = Path('/root/trinity_workspace/shared/knowledge.md')
        
        try:
            with open(knowledge_file, 'a', encoding='utf-8') as f:
                f.write(f"\n\n---\n\n## {title}\n")
                f.write(f"**記録日時**: {datetime.now().isoformat()}\n")
                f.write(f"**担当**: Aria\n\n")
                f.write(content)
                f.write("\n")
            logger.info(f"Aria: Updated knowledge.md with '{title}'")
        except Exception as e:
            logger.error(f"Aria: Failed to update knowledge.md: {e}")


if __name__ == '__main__':
    import asyncio
    
    async def test_aria():
        logging.basicConfig(level=logging.INFO)
        db = TrinityDB()
        aria = AriaAgent(db)
        
        test_task = {
            'id': 'TEST-ARIA-001',
            'title': 'Trinity v2.0 ドキュメント作成',
            'tags': ['documentation']
        }
        
        result = await aria.process_task(test_task)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    asyncio.run(test_aria())











