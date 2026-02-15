#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
📋 OH MY OPENCODE 成功パターンテンプレート
TaskType別の既定プロンプト
"""

from typing import Dict, Any, Optional
from enum import Enum

from unified_logging import get_service_logger
logger = get_service_logger("oh-my-opencode-templates")


class TaskType(str, Enum):
    """タスクタイプ"""
    SPECIFICATION = "specification"  # 仕様策定
    COMPLEX_BUG = "complex_bug"  # 難解バグ
    ARCHITECTURE_DESIGN = "architecture_design"  # 初期アーキ設計
    CODE_GENERATION = "code_generation"  # コード生成
    CODE_REVIEW = "code_review"  # コードレビュー
    REFACTORING = "refactoring"  # リファクタリング
    GENERAL = "general"  # 一般タスク


class OHMyOpenCodeTemplates:
    """OH MY OPENCODE 成功パターンテンプレート"""
    
    def __init__(self):
        """初期化"""
        self.templates = self._load_templates()
        logger.info("✅ Templates initialized")
    
    def _load_templates(self) -> Dict[str, Dict[str, str]]:
        """テンプレートを読み込み"""
        return {
            TaskType.SPECIFICATION.value: {
                "requirement_analysis": """
要件整理テンプレート:
1. 目的の明確化
   - 何を実現したいか
   - なぜ必要か
   - 誰が使うか

2. 機能要件の抽出
   - 必須機能
   - 任意機能
   - 制約条件

3. 非機能要件の定義
   - パフォーマンス
   - セキュリティ
   - スケーラビリティ

4. 成果物の定義
   - ドキュメント形式
   - レビュー基準
""",
                "implementation_template": """
実装テンプレート:
1. アーキテクチャ設計
2. データモデル定義
3. API設計
4. エラーハンドリング
5. テスト戦略
""",
                "verification_template": """
検証テンプレート:
1. 要件充足性チェック
2. 非機能要件チェック
3. レビュー
""",
                "failure_branch_template": """
失敗時の分岐テンプレート:
1. 原因分析
2. 代替案の検討
3. 要件の再確認
4. 段階的実装への切り替え
""",
                "summary_template": """
まとめテンプレート:
- 成果物: [仕様書/設計書]
- 次アクション: [実装/レビュー/承認]
- 注意事項: [リスク/制約]
"""
            },
            TaskType.COMPLEX_BUG.value: {
                "requirement_analysis": """
バグ分析テンプレート:
1. 現象の記録
   - 再現手順
   - エラーメッセージ
   - 環境情報

2. 原因の仮説
   - ログ分析
   - コードレビュー
   - 依存関係チェック

3. 影響範囲の特定
   - 影響を受ける機能
   - データ整合性
   - パフォーマンス影響
""",
                "implementation_template": """
修正テンプレート:
1. 最小限の修正
2. テストケース追加
3. 回帰テスト
4. ドキュメント更新
""",
                "verification_template": """
検証テンプレート:
1. 再現テスト
2. 回帰テスト
3. パフォーマンステスト
4. セキュリティチェック
""",
                "failure_branch_template": """
失敗時の分岐テンプレート:
1. ログの詳細分析
2. 別の原因仮説の検討
3. デバッグツールの使用
4. 専門家への相談
""",
                "summary_template": """
まとめテンプレート:
- 原因: [根本原因]
- 修正内容: [修正内容]
- 予防策: [再発防止策]
- 次アクション: [テスト/デプロイ]
"""
            },
            TaskType.ARCHITECTURE_DESIGN.value: {
                "requirement_analysis": """
アーキテクチャ分析テンプレート:
1. 要件の理解
   - ビジネス要件
   - 技術要件
   - 制約条件

2. 既存システムの分析
   - 現状の課題
   - 技術的負債
   - 改善ポイント

3. 設計原則の定義
   - スケーラビリティ
   - 保守性
   - パフォーマンス
""",
                "implementation_template": """
設計テンプレート:
1. システム全体像
2. コンポーネント設計
3. データフロー設計
4. セキュリティ設計
5. デプロイメント設計
""",
                "verification_template": """
検証テンプレート:
1. 要件充足性チェック
2. スケーラビリティチェック
3. セキュリティレビュー
4. パフォーマンス評価
""",
                "failure_branch_template": """
失敗時の分岐テンプレート:
1. 設計の見直し
2. 要件の再確認
3. 段階的実装への切り替え
4. プロトタイプの作成
""",
                "summary_template": """
まとめテンプレート:
- 設計書: [アーキテクチャ図/設計書]
- 実装計画: [フェーズ/優先順位]
- リスク: [技術的リスク/対策]
- 次アクション: [実装開始/レビュー]
"""
            },
            TaskType.CODE_GENERATION.value: {
                "requirement_analysis": """
要件整理テンプレート:
1. 機能要件
2. 入力/出力仕様
3. エラーハンドリング要件
4. パフォーマンス要件
""",
                "implementation_template": """
実装テンプレート:
1. 関数/クラス設計
2. エラーハンドリング
3. テストコード
4. ドキュメント
""",
                "verification_template": """
検証テンプレート:
1. 単体テスト
2. 統合テスト
3. コードレビュー
4. パフォーマンステスト
""",
                "failure_branch_template": """
失敗時の分岐テンプレート:
1. エラー分析
2. 要件の再確認
3. 実装方法の変更
4. テストの追加
""",
                "summary_template": """
まとめテンプレート:
- 成果物: [コード/テスト]
- 品質: [テストカバレッジ/レビュー結果]
- 次アクション: [統合/デプロイ]
"""
            },
            TaskType.CODE_REVIEW.value: {
                "requirement_analysis": """
レビュー分析テンプレート:
1. コードの理解
2. 要件との照合
3. レビュー観点の定義
""",
                "implementation_template": """
レビューテンプレート:
1. コード品質チェック
2. セキュリティチェック
3. パフォーマンスチェック
4. ベストプラクティスチェック
""",
                "verification_template": """
検証テンプレート:
1. 指摘事項の確認
2. 修正内容のレビュー
3. 再レビュー
""",
                "failure_branch_template": """
失敗時の分岐テンプレート:
1. 指摘事項の優先順位付け
2. 重大な問題の特定
3. 再実装の検討
""",
                "summary_template": """
まとめテンプレート:
- 指摘事項: [重大/軽微]
- 修正状況: [修正済み/要修正]
- 承認: [承認/要再レビュー]
"""
            },
            TaskType.REFACTORING.value: {
                "requirement_analysis": """
リファクタリング分析テンプレート:
1. 現状の課題
2. リファクタリング目標
3. 影響範囲の特定
""",
                "implementation_template": """
リファクタリングテンプレート:
1. 小さなステップに分割
2. テストを先に書く
3. リファクタリング実行
4. テスト実行
""",
                "verification_template": """
検証テンプレート:
1. 既存テストの実行
2. 新規テストの追加
3. パフォーマンス比較
4. コード品質チェック
""",
                "failure_branch_template": """
失敗時の分岐テンプレート:
1. ロールバック
2. 原因分析
3. 段階的リファクタリング
4. テストの強化
""",
                "summary_template": """
まとめテンプレート:
- 改善内容: [リファクタリング内容]
- 品質向上: [メトリクス改善]
- 次アクション: [継続的リファクタリング]
"""
            },
            TaskType.GENERAL.value: {
                "requirement_analysis": """
一般タスク分析テンプレート:
1. タスクの理解
2. 目標の明確化
3. 制約条件の確認
""",
                "implementation_template": """
実装テンプレート:
1. 計画立案
2. 実装
3. 検証
4. まとめ
""",
                "verification_template": """
検証テンプレート:
1. 目標達成チェック
2. 品質チェック
3. 完了確認
""",
                "failure_branch_template": """
失敗時の分岐テンプレート:
1. 原因分析
2. 計画の見直し
3. 代替案の検討
""",
                "summary_template": """
まとめテンプレート:
- 成果物: [成果物]
- 次アクション: [次のステップ]
"""
            }
        }
    
    def get_template(
        self,
        task_type: TaskType,
        template_name: str
    ) -> Optional[str]:
        """
        テンプレートを取得
        
        Args:
            task_type: タスクタイプ
            template_name: テンプレート名
        
        Returns:
            テンプレート（Noneの場合は見つからない）
        """
        templates = self.templates.get(task_type.value, {})
        return templates.get(template_name)
    
    def enhance_prompt(
        self,
        task_type: TaskType,
        base_prompt: str,
        use_requirement_analysis: bool = True,
        use_implementation_template: bool = True,
        use_verification_template: bool = True
    ) -> str:
        """
        プロンプトをテンプレートで強化
        
        Args:
            task_type: タスクタイプ
            base_prompt: ベースプロンプト
            use_requirement_analysis: 要件整理テンプレートを使用するか
            use_implementation_template: 実装テンプレートを使用するか
            use_verification_template: 検証テンプレートを使用するか
        
        Returns:
            強化されたプロンプト
        """
        enhanced = base_prompt
        
        if use_requirement_analysis:
            requirement_template = self.get_template(task_type, "requirement_analysis")
            if requirement_template:
                enhanced += f"\n\n## 要件整理ガイド\n{requirement_template}"
        
        if use_implementation_template:
            implementation_template = self.get_template(task_type, "implementation_template")
            if implementation_template:
                enhanced += f"\n\n## 実装ガイド\n{implementation_template}"
        
        if use_verification_template:
            verification_template = self.get_template(task_type, "verification_template")
            if verification_template:
                enhanced += f"\n\n## 検証ガイド\n{verification_template}"
        
        return enhanced
    
    def get_failure_branch_template(self, task_type: TaskType) -> Optional[str]:
        """
        失敗時の分岐テンプレートを取得
        
        Args:
            task_type: タスクタイプ
        
        Returns:
            失敗時の分岐テンプレート
        """
        return self.get_template(task_type, "failure_branch_template")
    
    def get_summary_template(self, task_type: TaskType) -> Optional[str]:
        """
        まとめテンプレートを取得
        
        Args:
            task_type: タスクタイプ
        
        Returns:
            まとめテンプレート
        """
        return self.get_template(task_type, "summary_template")


# 使用例
if __name__ == "__main__":
    templates = OHMyOpenCodeTemplates()
    
    # テンプレートを取得
    requirement_template = templates.get_template(
        TaskType.CODE_GENERATION,
        "requirement_analysis"
    )
    print("要件整理テンプレート:")
    print(requirement_template)
    
    # プロンプトを強化
    enhanced = templates.enhance_prompt(
        TaskType.CODE_GENERATION,
        "PythonでREST APIを作成してください"
    )
    print("\n強化されたプロンプト:")
    print(enhanced[:500] + "...")
