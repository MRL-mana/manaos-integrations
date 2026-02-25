"""
RLAnything – ManaOS 自己進化フレームワーク
==========================================
プリンストン大学「RLAnything」論文に基づく 3 要素同時最適化:
  1. Policy  (方策)     → エージェントの行動戦略
  2. Reward  (報酬)     → 自動採点・一貫性フィードバック
  3. Environment (環境) → カリキュラム / 動的難易度調整

フェーズ:
  Phase 1  観測    observation_hook   post_tool_use ログ収集
  Phase 2  分析    feedback_engine    統合・一貫性・評価フィードバック
  Phase 3  進化    evolution_engine   スキル抽出 / MEMORY.md 更新 / 難易度調整
"""

__version__ = "0.1.0"
