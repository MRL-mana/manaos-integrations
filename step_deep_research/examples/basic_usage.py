#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Step-Deep-Research 基本的な使い方の例
"""

import json
from pathlib import Path
from step_deep_research.orchestrator import StepDeepResearchOrchestrator


def example_1_technical_selection():
    """例1: 技術選定"""
    print("=" * 60)
    print("例1: 技術選定")
    print("=" * 60)
    
    # 設定読み込み
    config_path = Path("step_deep_research_config.json")
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
    
    # オーケストレーター初期化
    orchestrator = StepDeepResearchOrchestrator(config)
    
    # ジョブ作成
    query = "RDPとTailscaleを比較して"
    job_id = orchestrator.create_job(query)
    print(f"ジョブID: {job_id}")
    print(f"クエリ: {query}")
    
    # 実行
    print("\n実行中...")
    result = orchestrator.execute_job(job_id)
    
    # 結果表示
    print(f"\nスコア: {result['score']}/30")
    print(f"合格: {result['pass']}")
    print(f"レポートパス: {result['report_path']}")
    print(f"使用予算: {result['spent_budget']}")
    print(f"停止理由: {result.get('stop_reason', 'completed')}")
    
    # レポートの一部を表示
    if result.get('report'):
        print("\nレポート（最初の500文字）:")
        print(result['report'][:500] + "...")


def example_2_troubleshooting():
    """例2: トラブル調査"""
    print("\n" + "=" * 60)
    print("例2: トラブル調査")
    print("=" * 60)
    
    # 設定読み込み
    config_path = Path("step_deep_research_config.json")
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
    
    # オーケストレーター初期化
    orchestrator = StepDeepResearchOrchestrator(config)
    
    # ジョブ作成
    query = "RDP接続がタイムアウトする原因を調べて"
    job_id = orchestrator.create_job(query)
    print(f"ジョブID: {job_id}")
    print(f"クエリ: {query}")
    
    # 実行
    print("\n実行中...")
    result = orchestrator.execute_job(job_id)
    
    # 結果表示
    print(f"\nスコア: {result['score']}/30")
    print(f"合格: {result['pass']}")
    print(f"レポートパス: {result['report_path']}")


def example_3_latest_trends():
    """例3: 最新動向チェック"""
    print("\n" + "=" * 60)
    print("例3: 最新動向チェック")
    print("=" * 60)
    
    # 設定読み込み
    config_path = Path("step_deep_research_config.json")
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
    
    # オーケストレーター初期化
    orchestrator = StepDeepResearchOrchestrator(config)
    
    # ジョブ作成
    query = "2026年のWindowsの変更点を調べて"
    job_id = orchestrator.create_job(query)
    print(f"ジョブID: {job_id}")
    print(f"クエリ: {query}")
    
    # 実行
    print("\n実行中...")
    result = orchestrator.execute_job(job_id)
    
    # 結果表示
    print(f"\nスコア: {result['score']}/30")
    print(f"合格: {result['pass']}")
    print(f"レポートパス: {result['report_path']}")


def example_4_cache():
    """例4: キャッシュの活用"""
    print("\n" + "=" * 60)
    print("例4: キャッシュの活用")
    print("=" * 60)
    
    # 設定読み込み
    config_path = Path("step_deep_research_config.json")
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
    
    # オーケストレーター初期化
    orchestrator = StepDeepResearchOrchestrator(config)
    
    # 1回目: 通常実行
    query = "Pythonの非同期処理について調べて"
    job_id1 = orchestrator.create_job(query)
    print(f"1回目ジョブID: {job_id1}")
    print(f"クエリ: {query}")
    
    print("\n1回目実行中（通常）...")
    result1 = orchestrator.execute_job(job_id1, use_cache=False)
    print(f"スコア: {result1['score']}/30")
    print(f"キャッシュ: {result1.get('cached', False)}")
    
    # 2回目: キャッシュヒット
    job_id2 = orchestrator.create_job(query)
    print(f"\n2回目ジョブID: {job_id2}")
    
    print("\n2回目実行中（キャッシュ使用）...")
    result2 = orchestrator.execute_job(job_id2, use_cache=True)
    print(f"スコア: {result2['score']}/30")
    print(f"キャッシュ: {result2.get('cached', False)}")
    print(f"停止理由: {result2.get('stop_reason', 'completed')}")
    
    if result2.get('cached'):
        print("\n✅ キャッシュヒット！高速・低コストで結果を取得")


def example_5_budget_limit():
    """例5: 予算制限"""
    print("\n" + "=" * 60)
    print("例5: 予算制限")
    print("=" * 60)
    
    # 設定読み込み
    config_path = Path("step_deep_research_config.json")
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
    
    # 予算を制限
    config['orchestrator']['max_iterations'] = 3
    config['orchestrator']['max_search_queries'] = 5
    config['orchestrator']['token_budget'] = 10000
    
    # オーケストレーター初期化
    orchestrator = StepDeepResearchOrchestrator(config)
    
    # ジョブ作成
    query = "RDPとTailscaleを比較して"
    job_id = orchestrator.create_job(query)
    print(f"ジョブID: {job_id}")
    print(f"クエリ: {query}")
    print(f"予算制限: 最大反復={config['orchestrator']['max_iterations']}, "
          f"最大検索={config['orchestrator']['max_search_queries']}, "
          f"トークン予算={config['orchestrator']['token_budget']}")
    
    # 実行
    print("\n実行中...")
    result = orchestrator.execute_job(job_id)
    
    # 結果表示
    print(f"\nスコア: {result['score']}/30")
    print(f"合格: {result['pass']}")
    print(f"使用予算: {result['spent_budget']}")
    print(f"停止理由: {result.get('stop_reason', 'completed')}")


if __name__ == "__main__":
    print("Step-Deep-Research 基本的な使い方の例")
    print("=" * 60)
    
    # 例を実行（コメントアウトで選択）
    example_1_technical_selection()
    # example_2_troubleshooting()
    # example_3_latest_trends()
    # example_4_cache()
    # example_5_budget_limit()

