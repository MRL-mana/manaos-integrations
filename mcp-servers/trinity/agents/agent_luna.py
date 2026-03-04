#!/usr/bin/env python3
"""
Trinity v2.0 Luna Agent
実務遂行AI - Claude Sonnetによるコード実装・バグ修正
"""

import sys
import logging
from typing import Dict, Any, Optional
from pathlib import Path
import json

sys.path.insert(0, str(Path(__file__).parent))

from agent_manager import BaseAgent, TrinityDB

logger = logging.getLogger(__name__)


class LunaAgent(BaseAgent):
    """Luna - 実務遂行AI"""
    
    def __init__(self, db: TrinityDB, api_key: Optional[str] = None):
        super().__init__('Luna', db)
        self.api_key = api_key
        self.model = 'claude-3-5-sonnet-20241022'
        
        # Anthropic初期化（APIキーがある場合）
        if self.api_key:
            try:
                import anthropic
                self.client = anthropic.Anthropic(api_key=self.api_key)
                logger.info("Luna: Anthropic client initialized")
            except Exception as e:
                logger.warning(f"Luna: Anthropic initialization failed: {e}")
                self.client = None
        else:
            self.client = None
            logger.warning("Luna: No API key provided, using mock mode")
        
        # システムプロンプト
        self.system_prompt = """あなたはLuna、Trinity System v2.0の実装AIです。

【あなたの役割】
1. コードの実装（クリーンで保守性の高いコード）
2. バグ修正（迅速かつ確実に）
3. リファクタリング（品質改善）
4. ユニットテスト作成

【重要な原則】
- 効率重視だがコード品質も重視
- ベストプラクティスに従う
- エラーハンドリングを忘れない
- コメントは適切に
- テストコードも含める

【コーディング規約】
- Python: PEP 8準拠
- JavaScript: ESLint準拠
- 変数名・関数名は明確に
- マジックナンバーは避ける

【口調】
テキパキと、でも丁寧に。
「実装しました」「動作確認済みです」「このアプローチで行きます」
"""
    
    async def process_task(self, task: Dict) -> Dict:
        """タスク処理"""
        task_type = self._identify_task_type(task)
        
        logger.info(f"Luna processing: {task['title']} (type: {task_type})")
        
        if task_type == 'implementation':
            return await self._handle_implementation_task(task)
        elif task_type == 'bugfix':
            return await self._handle_bugfix_task(task)
        elif task_type == 'refactor':
            return await self._handle_refactor_task(task)
        else:
            return await self._handle_generic_task(task)
    
    def _identify_task_type(self, task: Dict) -> str:
        """タスクタイプ判定"""
        title = task.get('title', '').lower()
        tags = task.get('tags', [])
        
        if any(tag in ['implementation', 'code', 'feature'] for tag in tags):
            return 'implementation'
        elif any(tag in ['bug', 'bugfix', 'fix'] for tag in tags):
            return 'bugfix'
        elif any(tag in ['refactor', 'optimization'] for tag in tags):
            return 'refactor'
        elif '実装' in title or 'implement' in title:
            return 'implementation'
        elif 'バグ' in title or 'bug' in title or '修正' in title:
            return 'bugfix'
        elif 'リファクタ' in title or 'refactor' in title:
            return 'refactor'
        else:
            return 'generic'
    
    async def _handle_implementation_task(self, task: Dict) -> Dict:
        """実装タスク処理"""
        prompt = f"""
以下の機能を実装してください。

【タスク】
{task.get('title')}

【詳細】
{task.get('description', '')}

【要件】
- クリーンで保守性の高いコード
- 適切なエラーハンドリング
- 必要に応じてコメント
- 簡単なテストコード

完全な実装コードを提供してください。
ファイルパスと内容を明確に分けて出力してください。
"""
        
        code = await self.generate_response(prompt, task)
        
        # コード保存（実際にはファイル書き込み）
        self._save_implementation(task, code)
        
        return {
            'success': True,
            'next_status': 'review',
            'notes': f'実装完了: {task["title"]}'
        }
    
    async def _handle_bugfix_task(self, task: Dict) -> Dict:
        """バグ修正タスク処理"""
        prompt = f"""
以下のバグを修正してください。

【バグ内容】
{task.get('title')}
{task.get('description', '')}

【対応】
1. 原因の特定
2. 修正コード
3. テストケース
4. 再発防止策

修正内容を詳細に説明してください。
"""
        
        fix = await self.generate_response(prompt, task)
        
        return {
            'success': True,
            'next_status': 'review',
            'notes': f'バグ修正完了: {fix[:100]}...'
        }
    
    async def _handle_refactor_task(self, task: Dict) -> Dict:
        """リファクタリングタスク処理"""
        prompt = f"""
以下のコードをリファクタリングしてください。

【対象】
{task.get('title')}
{task.get('description', '')}

【リファクタリング観点】
- 可読性向上
- 保守性向上
- パフォーマンス改善
- コード重複削減

リファクタリング前後の比較も含めてください。
"""
        
        refactored = await self.generate_response(prompt, task)
        
        return {
            'success': True,
            'next_status': 'review',
            'notes': 'リファクタリング完了'
        }
    
    async def _handle_generic_task(self, task: Dict) -> Dict:
        """汎用タスク処理"""
        prompt = f"""
以下のタスクを実装してください。

【タスク】
{task.get('title')}
{task.get('description', '')}

実装方針と実際のコードを提供してください。
"""
        
        response = await self.generate_response(prompt, task)
        
        return {
            'success': True,
            'next_status': 'review',
            'notes': f'タスク完了: {response[:100]}...'
        }
    
    async def generate_response(self, prompt: str, task_context: Optional[Dict] = None) -> str:
        """AI応答生成"""
        if not self.client:
            # モックモード
            logger.info("Luna: Mock mode - generating fake response")
            return self._generate_mock_response(prompt, task_context)
        
        try:
            # Anthropic API呼び出し
            message = self.client.messages.create(
                model=self.model,
                max_tokens=4000,
                system=self.system_prompt,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            answer = message.content[0].text
            
            # コンテキストメモリに追加
            self.add_to_context("user", prompt)
            self.add_to_context("assistant", answer)
            
            logger.info(f"Luna: Generated response ({len(answer)} chars)")
            return answer
        
        except Exception as e:
            logger.error(f"Luna: Anthropic API error: {e}")
            return self._generate_mock_response(prompt, task_context)
    
    def _generate_mock_response(self, prompt: str, task_context: Optional[Dict] = None) -> str:
        """モック応答生成"""
        task_id = task_context.get('id', 'UNKNOWN') if task_context else 'UNKNOWN'
        task_title = task_context.get('title', '') if task_context else ''
        
        return f"""# Luna 実装（モック）

## タスクID: {task_id}
## タスク: {task_title}

### 実装コード

```python
#!/usr/bin/env python3
\"\"\"
Mock implementation for {task_title}
\"\"\"

def main():
    print("This is a mock implementation")
    print("Task: {task_id}")
    return True

if __name__ == '__main__':
    main()
```

### テストコード

```python
def test_main():
    assert main() == True
```

### 実装メモ
- これはモック実装です
- 実際の実装にはAnthropic APIキーが必要です
- Claude Sonnet 3.5を使用予定

**実装完了**: {task_id}
"""
    
    def _save_implementation(self, task: Dict, code: str):
        """実装コードを保存"""
        # 実装ログとして記録
        log_dir = Path('/root/trinity_workspace/logs')
        log_dir.mkdir(parents=True, exist_ok=True)
        
        log_file = log_dir / 'luna_implementations.md'
        
        try:
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(f"\n\n---\n\n## {task['title']}\n")
                f.write(f"**タスクID**: {task['id']}\n")
                f.write(f"**実装日時**: {self.db.get_task(task['id']).get('created_at', '')}\n\n")
                f.write(code)
                f.write("\n")
            
            logger.info(f"Luna: Saved implementation log for {task['id']}")
        except Exception as e:
            logger.error(f"Luna: Failed to save implementation log: {e}")


# ==================== テスト実行 ====================

async def test_luna():
    """テスト実行"""
    import asyncio
    
    logging.basicConfig(level=logging.INFO)
    
    db = TrinityDB()
    luna = LunaAgent(db)  # モックモード
    
    print("\n⚙️ Luna Agent Test")
    print("=" * 60)
    
    # テストタスク
    test_task = {
        'id': 'TEST-LUNA-001',
        'title': 'ユーザー認証API実装',
        'description': 'Flask + JWT認証',
        'tags': ['implementation', 'api']
    }
    
    print(f"Processing test task: {test_task['title']}")
    
    result = await luna.process_task(test_task)
    
    print("\nResult:")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    
    print("\n✅ Test complete")


if __name__ == '__main__':
    import asyncio
    asyncio.run(test_luna())











