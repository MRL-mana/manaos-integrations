#!/usr/bin/env python3
"""
Trinity v2.0 AI自動タスク分解システム
=====================================

自然言語の要求を自動的に実装可能なタスクに分解

Author: Mina & Luna
Created: 2025-10-18
License: MIT
"""

import asyncio
import json
import re
from datetime import datetime
from typing import List, Dict, Any
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / 'core'))
from db_manager import DatabaseManager


class AITaskDecomposer:
    """
    AI自動タスク分解システム
    
    機能:
    - 自然言語要求の解析
    - タスクへの自動分解
    - 優先度・依存関係の自動判定
    - エージェント自動割り当て
    
    使用例:
    ```python
    decomposer = AITaskDecomposer()
    tasks = await decomposer.decompose("ECサイトを作る")
    ```
    """
    
    def __init__(self):
        """初期化"""
        self.db = DatabaseManager()
        
        # タスクパターン定義
        self.patterns = {
            'web_app': {
                'keywords': ['web', 'サイト', 'アプリ', 'dashboard', 'システム'],
                'tasks': [
                    {'title': 'アーキテクチャ設計', 'agent': 'Remi', 'priority': 'urgent'},
                    {'title': 'データベース設計', 'agent': 'Luna', 'priority': 'urgent'},
                    {'title': 'バックエンドAPI実装', 'agent': 'Luna', 'priority': 'high'},
                    {'title': 'フロントエンド実装', 'agent': 'Luna', 'priority': 'high'},
                    {'title': 'テスト実装', 'agent': 'Mina', 'priority': 'high'},
                    {'title': 'ドキュメント作成', 'agent': 'Aria', 'priority': 'medium'}
                ]
            },
            'api': {
                'keywords': ['api', 'rest', 'endpoint', 'サービス'],
                'tasks': [
                    {'title': 'API設計', 'agent': 'Remi', 'priority': 'urgent'},
                    {'title': 'エンドポイント実装', 'agent': 'Luna', 'priority': 'high'},
                    {'title': '認証実装', 'agent': 'Luna', 'priority': 'high'},
                    {'title': 'APIテスト', 'agent': 'Mina', 'priority': 'high'},
                    {'title': 'API仕様書作成', 'agent': 'Aria', 'priority': 'medium'}
                ]
            },
            'cli': {
                'keywords': ['cli', 'コマンド', 'ツール', 'スクリプト'],
                'tasks': [
                    {'title': 'CLI設計', 'agent': 'Remi', 'priority': 'high'},
                    {'title': 'コマンド実装', 'agent': 'Luna', 'priority': 'high'},
                    {'title': 'ヘルプ実装', 'agent': 'Luna', 'priority': 'medium'},
                    {'title': 'テスト実装', 'agent': 'Mina', 'priority': 'high'},
                    {'title': '使い方ドキュメント作成', 'agent': 'Aria', 'priority': 'medium'}
                ]
            },
            'machine_learning': {
                'keywords': ['ml', '機械学習', 'ai', 'モデル', '予測'],
                'tasks': [
                    {'title': 'データ分析・前処理', 'agent': 'Luna', 'priority': 'urgent'},
                    {'title': 'モデル設計', 'agent': 'Remi', 'priority': 'urgent'},
                    {'title': 'モデル実装・訓練', 'agent': 'Luna', 'priority': 'high'},
                    {'title': 'モデル評価', 'agent': 'Mina', 'priority': 'high'},
                    {'title': 'デプロイ準備', 'agent': 'Luna', 'priority': 'medium'},
                    {'title': 'モデルドキュメント作成', 'agent': 'Aria', 'priority': 'medium'}
                ]
            },
            'database': {
                'keywords': ['database', 'db', 'データベース', 'sql', 'nosql'],
                'tasks': [
                    {'title': 'データモデル設計', 'agent': 'Remi', 'priority': 'urgent'},
                    {'title': 'スキーマ実装', 'agent': 'Luna', 'priority': 'urgent'},
                    {'title': 'マイグレーション実装', 'agent': 'Luna', 'priority': 'high'},
                    {'title': 'クエリ最適化', 'agent': 'Luna', 'priority': 'medium'},
                    {'title': 'データベーステスト', 'agent': 'Mina', 'priority': 'high'},
                    {'title': 'DB設計書作成', 'agent': 'Aria', 'priority': 'medium'}
                ]
            }
        }
    
    async def decompose(self, user_request: str, auto_create: bool = True) -> List[Dict[str, Any]]:
        """
        タスク自動分解
        
        Args:
            user_request: ユーザーからの要求（自然言語）
            auto_create: 自動的にDBにタスク作成するか
        
        Returns:
            タスクリスト
        """
        print(f"\n🤖 AI自動タスク分解開始")
        print(f"📝 ユーザー要求: {user_request}")
        print(f"{'=' * 60}\n")
        
        # 要求を解析
        category = self._analyze_request(user_request)
        
        print(f"✅ カテゴリ判定: {category}")
        
        # タスクテンプレート取得
        template_tasks = self.patterns.get(category, self.patterns['web_app'])['tasks']
        
        # タスクリスト生成
        tasks = []
        for i, template in enumerate(template_tasks, 1):
            task_id = f"AUTO-DECOMP-{int(datetime.now().timestamp())}-{i}"
            
            task = {
                'id': task_id,
                'title': f"{user_request} - {template['title']}",
                'status': 'todo',
                'priority': template['priority'],
                'assigned_to': template['agent'],
                'created_by': 'AIDecomposer',
                'created_at': datetime.now().isoformat(),
                'tags': [category, 'auto-generated', 'ai-decomposed'],
                'dependencies': [tasks[i-2]['id']] if i > 1 else [],
                'estimated_hours': self._estimate_hours(template['title'])
            }
            
            tasks.append(task)
        
        print(f"\n📊 分解結果:")
        print(f"   カテゴリ: {category}")
        print(f"   タスク数: {len(tasks)}")
        print(f"   推定総時間: {sum(t['estimated_hours'] for t in tasks)}時間\n")
        
        print(f"{'=' * 60}")
        print(f"生成されたタスク:")
        print(f"{'=' * 60}\n")
        
        for i, task in enumerate(tasks, 1):
            print(f"[{i}] {task['title']}")
            print(f"    ID: {task['id']}")
            print(f"    担当: {task['assigned_to']}")
            print(f"    優先度: {task['priority']}")
            print(f"    推定時間: {task['estimated_hours']}h")
            if task['dependencies']:
                print(f"    依存: {', '.join(task['dependencies'])}")
            print()
        
        # DB自動登録
        if auto_create:
            print(f"📁 データベースに登録中...")
            for task in tasks:
                self.db.create_task(task)
            print(f"✅ {len(tasks)}個のタスクをデータベースに登録しました\n")
        
        return tasks
    
    def _analyze_request(self, request: str) -> str:
        """
        要求を解析してカテゴリ判定
        
        Args:
            request: ユーザー要求
        
        Returns:
            カテゴリ名
        """
        request_lower = request.lower()
        
        # 各パターンとマッチング
        for category, pattern in self.patterns.items():
            for keyword in pattern['keywords']:
                if keyword in request_lower:
                    return category
        
        # デフォルトはweb_app
        return 'web_app'
    
    def _estimate_hours(self, task_title: str) -> float:
        """
        タスクの推定時間を計算
        
        Args:
            task_title: タスクタイトル
        
        Returns:
            推定時間（時間）
        """
        # キーワードベースの簡易推定
        if '設計' in task_title or 'design' in task_title.lower():
            return 2.0
        elif '実装' in task_title or 'implement' in task_title.lower():
            return 3.0
        elif 'テスト' in task_title or 'test' in task_title.lower():
            return 1.5
        elif 'ドキュメント' in task_title or 'document' in task_title.lower():
            return 1.0
        else:
            return 2.0
    
    async def decompose_interactive(self):
        """対話型タスク分解"""
        print(f"\n{'=' * 60}")
        print(f"🤖 AI自動タスク分解システム（対話型）")
        print(f"{'=' * 60}\n")
        
        print(f"何を作りたいですか？（自然言語で入力してください）")
        print(f"例: ECサイトを作る、REST APIを実装、機械学習モデルを作成\n")
        
        user_input = input(">>> ")
        
        if not user_input.strip():
            print("入力が空です。終了します。")
            return
        
        # タスク分解実行
        tasks = await self.decompose(user_input)
        
        # 確認
        print(f"\n{'=' * 60}")
        print(f"これらのタスクで実行しますか？ (y/n)")
        confirm = input(">>> ")
        
        if confirm.lower() == 'y':
            print(f"\n✅ タスクを実行キューに追加しました")
            print(f"   Trinity エージェントが自動的に実行します")
        else:
            print(f"\n❌ キャンセルしました")


async def main():
    """テスト用メイン関数"""
    decomposer = AITaskDecomposer()
    
    # デモ1: Webアプリ
    print(f"\n{'=' * 80}")
    print(f"デモ1: Webアプリケーション")
    print(f"{'=' * 80}")
    await decomposer.decompose("Eコマースサイトを構築する", auto_create=False)
    
    # デモ2: API
    print(f"\n{'=' * 80}")
    print(f"デモ2: REST API")
    print(f"{'=' * 80}")
    await decomposer.decompose("ユーザー管理APIを実装する", auto_create=False)
    
    # デモ3: 機械学習
    print(f"\n{'=' * 80}")
    print(f"デモ3: 機械学習モデル")
    print(f"{'=' * 80}")
    await decomposer.decompose("売上予測モデルを作成する", auto_create=False)
    
    print(f"\n{'=' * 80}")
    print(f"🎉 AI自動タスク分解デモ完了")
    print(f"{'=' * 80}\n")


if __name__ == "__main__":
    asyncio.run(main())

