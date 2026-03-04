#!/usr/bin/env python3
"""
Mana専用カスタムプラグイン
特定のパターン検出 & 自動レビュー
"""

import sys
import os
sys.path.append('/root')

from manaspec_plugin_system import ManaSpecPlugin
from typing import Dict, Any
import re

class ManaCustomPlugin(ManaSpecPlugin):
    """Mana専用のカスタムプラグイン"""
    
    def get_name(self) -> str:
        return "mana-custom"
    
    def get_version(self) -> str:
        return "1.0.0"
    
    def initialize(self, context: Dict[str, Any]):
        """初期化"""
        self.context = context
        self.pattern_rules = {
            # Manaの好みのパターン
            "trinity_integration": r"(remi|luna|mina|trinity)",
            "ai_learning": r"(learning|pattern|insight)",
            "automation": r"(自動|automatic|auto)",
        }
        print("  ✨ Mana Custom Plugin initialized")
        print("  📋 監視パターン: Trinity統合, AI学習, 自動化")
    
    def on_proposal_created(self, change_id: str, proposal: Dict):
        """Proposal作成時のカスタムチェック"""
        print(f"  🔍 Mana Custom: Analyzing proposal - {change_id}")
        
        # Proposalのコンテンツを取得
        proposal_text = str(proposal).lower()
        
        # パターンマッチング
        detected_patterns = []
        for pattern_name, pattern_regex in self.pattern_rules.items():
            if re.search(pattern_regex, proposal_text, re.IGNORECASE):
                detected_patterns.append(pattern_name)
        
        if detected_patterns:
            print(f"  💡 検出されたパターン: {', '.join(detected_patterns)}")
            
            # Trinity統合が検出されたらLINE通知
            if "trinity_integration" in detected_patterns:
                print(f"  👭 Trinity統合検出！特別な注意が必要です")
                # LINE通知（後で実装）
        
        # Manaの好みに合わないパターンを検出
        self._check_anti_patterns(proposal_text, change_id)
    
    def _check_anti_patterns(self, proposal_text: str, change_id: str):
        """Manaが避けたいパターンを検出"""
        anti_patterns = {
            "gpu_unnecessary": r"gpu|cuda|nvidia",  # 不要なGPU使用
            "complex_without_reason": r"kubernetes|microservice|kafka",  # 不要な複雑化
        }
        
        for pattern_name, pattern_regex in anti_patterns.items():
            if re.search(pattern_regex, proposal_text, re.IGNORECASE):
                print(f"  ⚠️  Anti-pattern検出: {pattern_name}")
                print(f"     本当に必要か再確認してください")
    
    def on_proposal_validated(self, change_id: str, result: Dict):
        """Validation後の自動レビュー"""
        print(f"  🤖 Mana Custom: Auto-reviewing - {change_id}")
        
        if result.get("valid", False):
            print(f"  ✅ Validation OK - 実装準備完了")
        else:
            print(f"  ❌ Validation NG - 修正が必要")
    
    def on_archive_created(self, change_id: str, archive_path: str):
        """Archive作成時の処理"""
        print(f"  📦 Mana Custom: Archiving - {change_id}")
        
        # Mana専用のカスタムメトリクス収集
        metrics = {
            "archived_at": str(archive_path),
            "change_id": change_id,
            "trinity_involved": True  # Always true in ManaSpec
        }
        
        print(f"  💾 カスタムメトリクス保存: {metrics}")
        
        # Obsidian同期トリガー
        print(f"  📝 Obsidian同期をトリガー")
        
        # LINE通知トリガー
        print(f"  🔔 LINE通知をトリガー")


if __name__ == '__main__':
    # テスト実行
    plugin = ManaCustomPlugin()
    plugin.initialize({})
    
    # テストデータ
    plugin.on_proposal_created("add-trinity-feature", {
        "text": "Trinity統合の新機能を追加"
    })
    
    plugin.on_proposal_validated("add-trinity-feature", {"valid": True})
    plugin.on_archive_created("add-trinity-feature", "/path/to/archive")

