#!/usr/bin/env python3
"""
Trinity v2.0 Enhanced Remi Agent
ENHANCE-024: 要件定義フェーズ強化（YouTube手法統合）
"""

import sys
import logging
from pathlib import Path
from typing import Dict, Optional
import json
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from agent_remi import RemiAgent
from agent_manager import TrinityDB

logger = logging.getLogger(__name__)


class EnhancedRemiAgent(RemiAgent):
    """強化版Remi - 要件定義エキスパート"""
    
    def __init__(self, db: TrinityDB, api_key: Optional[str] = None):
        super().__init__(db, api_key)
        
        # 強化版システムプロンプト
        self.system_prompt = """あなたはRemi、Trinity System v2.0の戦略指令AI（強化版）です。

【あなたの役割（強化）】
1. **詳細要件定義書作成**（YouTube手法統合）
   - 機能要件の明確化
   - 非機能要件の定義
   - 技術スタック選定（理由付き）
   - 成功基準の設定
   - 制約条件の洗い出し

2. 最適なタスク分解（30分-2時間/タスク）
3. 並行開発可能な粒度での分割
4. 依存関係の明確化

【重要な原則（YouTube参考）】
- 要件が明確であるほどAIは正確に実装
- 曖昧な指示は必ず詳細化
- 並行開発を前提とした分割
- 人間レビューポイントの明示

【要件定義フォーマット】
```markdown
# プロジェクト要件定義書

## 1. 概要
- プロジェクト名
- 目的
- 対象ユーザー

## 2. 機能要件
### 必須機能
- [ ] 機能1: 説明
- [ ] 機能2: 説明

### オプション機能
- [ ] 機能A: 説明

## 3. 非機能要件
- パフォーマンス: 要求
- セキュリティ: 要求
- 可用性: 要求
- スケーラビリティ: 要求

## 4. 技術スタック
- フロントエンド: React（理由）
- バックエンド: Flask（理由）
- データベース: PostgreSQL（理由）

## 5. 制約条件
- 期限: X日
- 予算: Y円
- 環境: 本番/開発

## 6. 成功基準
- [ ] ユーザーがログインできる
- [ ] 応答時間 < 200ms
- [ ] テストカバレッジ > 80%

## 7. リスクと対策
- リスク1: 対策
- リスク2: 対策
```

【タスク分解原則】
- 1タスク = 30分-2時間
- 並行実行可能な粒度
- 明確な完了条件
- 依存関係を最小化

【人間レビュー必要なタスク】
- セキュリティ関連
- 本番デプロイ
- DBスキーマ変更
- 外部API連携
- 重要な設計決定
"""
        
        logger.info("Enhanced Remi initialized (YouTube手法統合)")
    
    async def create_requirements_document(self, user_request: str) -> Dict:
        """詳細要件定義書作成（YouTube手法）"""
        
        prompt = f"""
以下のユーザーリクエストから、詳細な要件定義書を作成してください。

【ユーザーリクエスト】
{user_request}

【作成する要件定義書】
上記のフォーマットに従って、以下を含めてください：

1. プロジェクト概要
2. 機能要件（必須/オプション）
3. 非機能要件（性能、セキュリティ等）
4. 技術スタック選定（理由付き）
5. 制約条件
6. 成功基準（テスト可能な形で）
7. リスクと対策

**重要**: 
- 曖昧な部分は明確化
- 実装可能な粒度まで具体化
- 並行開発を考慮

Markdown形式で出力してください。
"""
        
        requirements_doc = await self.generate_response(prompt)
        
        # requirements.mdに保存
        req_file = Path('/root/trinity_workspace/shared/requirements.md')
        
        with open(req_file, 'w', encoding='utf-8') as f:
            f.write(f"# 要件定義書\n\n")
            f.write(f"**作成日時**: {datetime.now().isoformat()}\n")
            f.write(f"**作成者**: Remi（強化版）\n\n")
            f.write(requirements_doc)
        
        logger.info("Requirements document created")
        
        return {
            'success': True,
            'document': requirements_doc,
            'file': str(req_file),
            'next_step': 'task_decomposition'
        }
    
    async def decompose_with_granularity_check(self, requirements: str) -> Dict:
        """粒度チェック付きタスク分解"""
        
        prompt = f"""
以下の要件定義から、実装タスクに分解してください。

【要件定義】
{requirements}

【タスク分解の原則】
1. **粒度**: 1タスク = 30分-2時間
   - 2時間超える場合は分割
   - 30分未満の場合は結合

2. **並行実行**: 依存関係を最小化
   - フロントエンド/バックエンド並行可能に
   - データベース設計は先行

3. **完了条件**: 明確に定義
   - 「〇〇ができる」形式
   - テスト可能

4. **人間レビュー**: 必要なタスクをマーク
   - セキュリティ: requires_human_review: true
   - 本番デプロイ: requires_human_review: true

5. **タスク数**: 理想は8-15個
   - 少なすぎる場合は詳細化
   - 多すぎる場合はグループ化

JSON形式で出力：
{{
    "tasks": [
        {{
            "id": "TASK-001",
            "title": "タスク名",
            "description": "詳細（完了条件含む）",
            "priority": "high",
            "assigned_to": "Luna/Mina/Aria",
            "estimated_hours": 1.5,
            "dependencies": [],
            "tags": ["frontend", "api"],
            "requires_human_review": false,
            "parallel_group": 1
        }}
    ],
    "estimated_total_hours": 12.0,
    "parallel_estimated_hours": 6.0,
    "parallel_groups": 3
}}
"""
        
        response = await self.generate_response(prompt)
        
        try:
            tasks_data = json.loads(response)
            tasks_list = tasks_data.get('tasks', [])
            
            # 粒度チェック
            for task in tasks_list:
                hours = task.get('estimated_hours', 1.0)
                
                if hours > 2.0:
                    logger.warning(f"Task {task['id']} too large ({hours}h), consider splitting")
                elif hours < 0.5:
                    logger.warning(f"Task {task['id']} too small ({hours}h), consider merging")
            
            # DBに登録
            for task in tasks_list:
                self.db.create_task(task)
                logger.info(f"Task created: {task['id']}")
            
            return {
                'success': True,
                'tasks_created': len(tasks_list),
                'estimated_total': tasks_data.get('estimated_total_hours'),
                'parallel_estimated': tasks_data.get('parallel_estimated_hours'),
                'efficiency_gain': f"{(1 - tasks_data.get('parallel_estimated_hours', 0) / tasks_data.get('estimated_total_hours', 1)) * 100:.1f}%"
            }
        
        except json.JSONDecodeError:
            logger.error("Failed to parse task decomposition JSON")
            return {
                'success': False,
                'error': 'JSON parse error'
            }
    
    async def process_user_request_with_requirements(self, user_request: str) -> Dict:
        """YouTubeフロー: 要件定義 → タスク分解 → 実装"""
        
        logger.info(f"Enhanced flow: {user_request}")
        
        # Step 1: 要件定義書作成
        print("\n📝 Step 1: Creating requirements document...")
        req_result = await self.create_requirements_document(user_request)
        
        if not req_result['success']:
            return req_result
        
        print(f"   ✅ Requirements: {req_result['file']}")
        
        # Step 2: タスク分解
        print("\n📋 Step 2: Decomposing into tasks...")
        decomp_result = await self.decompose_with_granularity_check(req_result['document'])
        
        if not decomp_result['success']:
            return decomp_result
        
        print(f"   ✅ Tasks created: {decomp_result['tasks_created']}")
        print(f"   ⏱️ Sequential: {decomp_result['estimated_total']:.1f}h")
        print(f"   ⚡ Parallel: {decomp_result['parallel_estimated']:.1f}h")
        print(f"   📈 Efficiency: {decomp_result['efficiency_gain']}")
        
        # Step 3: Lunaに実装依頼
        print("\n⚙️ Step 3: Assigning to Luna for implementation...")
        self.db.send_message('Remi', 'Luna', f"要件定義完了。{decomp_result['tasks_created']}個のタスクを実装してください。")
        
        return {
            'success': True,
            'requirements_file': req_result['file'],
            'tasks_created': decomp_result['tasks_created'],
            'ready_for_implementation': True
        }


# ==================== テスト実行 ====================

async def test_enhanced_remi():
    """強化版Remiテスト"""
    logging.basicConfig(level=logging.INFO)
    
    db = TrinityDB()
    remi = EnhancedRemiAgent(db)
    
    print("\n🎯 Enhanced Remi Agent Test (YouTube手法)")
    print("=" * 60)
    
    # テストリクエスト
    user_request = \"\"\"
タスク管理Webアプリを作成してください。

要望:
- ユーザー登録・ログイン機能
- タスクのCRUD操作
- 優先度・期限設定
- フィルター・検索機能
- レスポンシブデザイン
\"\"\"
    
    result = await remi.process_user_request_with_requirements(user_request)
    
    print("\n📊 Result:")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    
    print("\n✅ Enhanced Remi test complete")


if __name__ == '__main__':
    import asyncio
    asyncio.run(test_enhanced_remi())











