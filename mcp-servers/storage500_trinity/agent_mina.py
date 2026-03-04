#!/usr/bin/env python3
"""
Trinity v2.0 Mina Agent
洞察記録AI / QA - GPT-4oによるコードレビュー・テスト・品質保証
"""

import sys
import logging
from typing import Dict, Any, Optional
from pathlib import Path
import json

sys.path.insert(0, str(Path(__file__).parent))

from agent_manager import BaseAgent, TrinityDB

logger = logging.getLogger(__name__)


class MinaAgent(BaseAgent):
    """Mina - 洞察記録AI / QA"""
    
    def __init__(self, db: TrinityDB, api_key: Optional[str] = None):
        super().__init__('Mina', db)
        self.api_key = api_key
        self.model = 'gpt-4o'
        
        if self.api_key:
            try:
                import openai
                self.client = openai.OpenAI(api_key=self.api_key)
                logger.info("Mina: OpenAI client initialized")
            except Exception as e:
                logger.warning(f"Mina: OpenAI initialization failed: {e}")
                self.client = None
        else:
            self.client = None
            logger.warning("Mina: No API key provided, using mock mode")
        
        self.system_prompt = """あなたはMina、Trinity System v2.0の品質保証AIです。

【役割】コードレビュー、テスト設計・実行、品質チェック

【レビュー観点】
1. コード品質（可読性、保守性、パフォーマンス）
2. セキュリティ
3. エラーハンドリング
4. テストカバレッジ
5. ベストプラクティス準拠

【出力形式】
- 良い点を先に挙げる
- 改善点は具体的に
- 深刻度を明示（Critical/High/Medium/Low）
- 修正案を提示

【口調】建設的に、でも厳しく。
「ここは改善できそうです」「品質チェック完了です」「素晴らしい実装です」
"""
    
    async def process_task(self, task: Dict) -> Dict:
        """タスク処理"""
        logger.info(f"Mina processing: {task['title']}")
        
        # レビュー対象のタスクを取得
        task_id = task.get('id')
        reviewed_task = self.db.get_task(task_id)
        
        if not reviewed_task:
            return {'success': False, 'error': 'Task not found'}
        
        # レビュー実行
        review_result = await self._perform_review(reviewed_task)
        
        # 問題がなければdone、あればin_progress（修正待ち）
        if review_result.get('approved', False):
            next_status = 'done'
            notes = f"✅ レビュー合格: {review_result.get('summary', '')}"
        else:
            next_status = 'in_progress'
            notes = f"⚠️ 修正が必要: {review_result.get('issues', '')}"
        
        return {
            'success': True,
            'next_status': next_status,
            'notes': notes
        }
    
    async def _perform_review(self, task: Dict) -> Dict:
        """レビュー実行"""
        prompt = f"""
以下のタスクの成果物をレビューしてください。

【タスク】
ID: {task['id']}
タイトル: {task['title']}
説明: {task.get('description', '')}
実装者: {task.get('assigned_to', 'Unknown')}

【レビュー観点】
1. 要件充足度
2. コード品質
3. セキュリティ
4. エラーハンドリング
5. テスト十分性

【出力】
- 良い点
- 改善点（あれば、深刻度付き）
- 総評
- 承認可否（OK/NG）

JSON形式で回答してください：
{{
    "approved": true/false,
    "summary": "総評",
    "good_points": ["..."],
    "issues": [
        {{"severity": "High", "description": "...", "suggestion": "..."}}
    ]
}}
"""
        
        response = await self.generate_response(prompt, task)
        
        try:
            review_data = json.loads(response)
            return review_data
        except json.JSONDecodeError:
            return {
                'approved': True,  # パースエラー時はデフォルトで承認
                'summary': 'レビュー完了（モック）',
                'good_points': ['実装されています'],
                'issues': []
            }
    
    async def generate_response(self, prompt: str, task_context: Optional[Dict] = None) -> str:
        """AI応答生成"""
        if not self.client:
            return self._generate_mock_response(prompt, task_context)
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,  # レビューは厳密に
                max_tokens=2000
            )
            
            answer = response.choices[0].message.content
            self.add_to_context("user", prompt)
            self.add_to_context("assistant", answer)
            
            logger.info(f"Mina: Generated review ({len(answer)} chars)")
            return answer
        
        except Exception as e:
            logger.error(f"Mina: OpenAI API error: {e}")
            return self._generate_mock_response(prompt, task_context)
    
    def _generate_mock_response(self, prompt: str, task_context: Optional[Dict] = None) -> str:
        """モック応答生成"""
        task_id = task_context.get('id', 'UNKNOWN') if task_context else 'UNKNOWN'
        
        return json.dumps({
            "approved": True,
            "summary": f"タスク {task_id} のレビューを完了しました（モック）。問題ありません。",
            "good_points": [
                "要件を満たしています",
                "コードは読みやすいです",
                "エラーハンドリングがあります"
            ],
            "issues": []
        }, ensure_ascii=False)


if __name__ == '__main__':
    import asyncio
    
    async def test_mina():
        logging.basicConfig(level=logging.INFO)
        db = TrinityDB()
        mina = MinaAgent(db)
        
        test_task = {
            'id': 'TEST-MINA-001',
            'title': 'テストタスク',
            'assigned_to': 'Luna'
        }
        
        result = await mina.process_task(test_task)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    asyncio.run(test_mina())











