#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Step-Deep-Research 使用例
"""

import json
from pathlib import Path
from step_deep_research.orchestrator import StepDeepResearchOrchestrator

# 設定読み込み
config_path = Path("step_deep_research_config.json")
with open(config_path, "r", encoding="utf-8") as f:
    config = json.load(f)

# オーケストレーター初期化
orchestrator = StepDeepResearchOrchestrator(config)

# 調査依頼
user_query = "Pythonの非同期処理について調べて"

# ジョブ作成
job_id = orchestrator.create_job(user_query)
print(f"Job created: {job_id}")

# ジョブ実行
try:
    result = orchestrator.execute_job(job_id)
    
    print(f"\n{'='*60}")
    print(f"調査完了!")
    print(f"{'='*60}")
    print(f"ジョブID: {result['job_id']}")
    print(f"ステータス: {result['status']}")
    print(f"スコア: {result['score']}/30")
    print(f"合格: {'✅' if result['pass'] else '❌'}")
    print(f"レポートパス: {result['report_path']}")
    print(f"\n予算使用:")
    print(f"  - トークン: {result['budget_used']['tokens']}")
    print(f"  - 検索回数: {result['budget_used']['searches']}")
    print(f"  - 経過時間: {result['budget_used']['elapsed_seconds']:.1f}秒")
    
except Exception as e:
    print(f"エラー: {e}")



