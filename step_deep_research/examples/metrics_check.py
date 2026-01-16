#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
メトリクス確認の例
"""

from step_deep_research.metrics_dashboard import MetricsDashboard


def check_metrics():
    """メトリクスを確認"""
    print("=" * 60)
    print("Step-Deep-Research メトリクス確認")
    print("=" * 60)
    
    # ダッシュボード初期化
    dashboard = MetricsDashboard()
    
    # メトリクス計算（過去7日間）
    print("\n過去7日間のメトリクスを計算中...")
    metrics = dashboard.calculate_metrics(days=7)
    
    # 基本情報
    print(f"\n総ジョブ数: {metrics['total_jobs']}")
    print(f"集計期間: {metrics['period_days']}日間")
    
    if metrics['total_jobs'] == 0:
        print("\n⚠️  データがありません。まずジョブを実行してください。")
        return
    
    # 主要指標
    print("\n" + "=" * 60)
    print("主要指標")
    print("=" * 60)
    
    m = metrics['metrics']
    print(f"平均コスト/リクエスト: {m['avg_cost_per_request']:.0f} トークン")
    print(f"中央値レイテンシ: {m['median_latency_sec']:.1f} 秒")
    print(f"平均スコア: {m['avg_score']:.1f}/30")
    print(f"Critic差し戻し率: {m['critic_reject_rate']:.1%}")
    print(f"致命エラー率: {m['fatal_error_rate']:.1%}")
    print(f"引用カバレッジ: {m['citation_coverage']:.1%}")
    
    # 内訳
    print("\n" + "=" * 60)
    print("内訳")
    print("=" * 60)
    
    breakdown = metrics['breakdown']
    
    print("\nコスト:")
    print(f"  最小: {breakdown['costs']['min']:.0f} トークン")
    print(f"  最大: {breakdown['costs']['max']:.0f} トークン")
    print(f"  平均: {breakdown['costs']['avg']:.0f} トークン")
    print(f"  中央値: {breakdown['costs']['median']:.0f} トークン")
    
    print("\nレイテンシ:")
    print(f"  最小: {breakdown['latencies']['min']:.1f} 秒")
    print(f"  最大: {breakdown['latencies']['max']:.1f} 秒")
    print(f"  平均: {breakdown['latencies']['avg']:.1f} 秒")
    print(f"  中央値: {breakdown['latencies']['median']:.1f} 秒")
    
    print("\nスコア:")
    print(f"  最小: {breakdown['scores']['min']:.1f}")
    print(f"  最大: {breakdown['scores']['max']:.1f}")
    print(f"  平均: {breakdown['scores']['avg']:.1f}")
    print(f"  中央値: {breakdown['scores']['median']:.1f}")
    
    # 目標値との比較
    print("\n" + "=" * 60)
    print("目標値との比較")
    print("=" * 60)
    
    checks = [
        ("平均コスト", m['avg_cost_per_request'], 30000, "<"),
        ("中央値レイテンシ", m['median_latency_sec'], 300, "<"),
        ("Critic差し戻し率", m['critic_reject_rate'], 0.4, "<"),
        ("致命エラー率", m['fatal_error_rate'], 0.05, "<"),
        ("引用カバレッジ", m['citation_coverage'], 0.9, ">"),
    ]
    
    for name, value, target, op in checks:
        if op == "<":
            passed = value < target
        else:
            passed = value > target
        
        status = "✅" if passed else "⚠️"
        print(f"{status} {name}: {value:.1f} (目標: {op} {target})")


def generate_dashboard_report():
    """ダッシュボードレポートを生成"""
    print("\n" + "=" * 60)
    print("ダッシュボードレポート生成")
    print("=" * 60)
    
    dashboard = MetricsDashboard()
    report = dashboard.generate_dashboard_report(days=7)
    
    print(report)
    
    # ファイルに保存
    output_path = "logs/step_deep_research/dashboard_report.md"
    from pathlib import Path
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report)
    
    print(f"\nレポートを保存しました: {output_path}")


if __name__ == "__main__":
    check_metrics()
    # generate_dashboard_report()

