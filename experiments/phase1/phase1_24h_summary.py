#!/usr/bin/env python3
"""
Phase 1 24時間運用 集計スクリプト
最小運用セット（集計・チェック・自動停止のコツ）
"""

import json
import sys
import re
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple

def load_snapshot(json_path: Path) -> dict:
    """スナップショットを読み込む"""
    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def collect_snapshots(snapshot_dir: Path, hours: int = 24) -> List[Path]:
    """
    指定時間範囲のスナップショットを収集（日付ディレクトリ対応）
    
    対応パターン:
    - フラット: snapshots/hourly/phase1_metrics_snapshot_*.json
    - 日付ディレクトリ: snapshots/YYYY-MM-DD/*.json
    """
    cutoff_time = datetime.now().timestamp() - (hours * 3600)
    
    snapshot_files = []
    
    # パターン1: フラット構造（phase1_metrics_snapshot_*.json）
    snapshot_files.extend(snapshot_dir.glob("phase1_metrics_snapshot_*.json"))
    
    # パターン2: 日付ディレクトリ構造（YYYY-MM-DD/*.json）
    for date_dir in snapshot_dir.iterdir():
        if date_dir.is_dir() and re.match(r"\d{4}-\d{2}-\d{2}", date_dir.name):
            snapshot_files.extend(date_dir.glob("*.json"))
    
    # 時系列順にソート
    snapshot_files = sorted(
        snapshot_files,
        key=lambda p: p.stat().st_mtime
    )
    
    # 指定時間範囲内のスナップショットを取得
    recent_snapshots = [
        p for p in snapshot_files
        if p.stat().st_mtime >= cutoff_time
    ]
    
    return recent_snapshots

def calculate_summary(snapshots: List[Path], baseline: Optional[Path] = None) -> Dict:
    """
    24時間運用の集計を計算
    
    Returns:
        集計結果（dict）
    """
    if not snapshots:
        return {
            "error": "スナップショットがありません",
            "snapshot_count": 0
        }
    
    # ベースラインを読み込む
    baseline_data = None
    if baseline and baseline.exists():
        baseline_data = load_snapshot(baseline)
    
    # メトリクスを収集
    p95_values = []
    contradiction_rates = []
    gate_block_rates = []
    writes_per_min_values = []
    http_5xx_counts = []
    storage_deltas = []
    
    for snapshot_path in snapshots:
        try:
            snapshot = load_snapshot(snapshot_path)
            metrics = snapshot.get("metrics", {})
            errors = snapshot.get("errors", {})
            storage_delta = snapshot.get("storage_delta", {})
            
            p95 = metrics.get("e2e_p95_sec", 0)
            contradiction_rate = metrics.get("contradiction_rate", 0)
            gate_block_rate = metrics.get("gate_block_rate", 0)
            writes_per_min = metrics.get("writes_per_min", 0)
            http_5xx = errors.get("http_5xx_last_60min", 0)
            
            p95_values.append(p95)
            contradiction_rates.append(contradiction_rate)
            gate_block_rates.append(gate_block_rate)
            writes_per_min_values.append(writes_per_min)
            http_5xx_counts.append(http_5xx)
            
            # storage_deltaの合計（絶対値）
            if storage_delta:
                total_delta = abs(storage_delta.get("scratchpad_entries", 0)) + \
                             abs(storage_delta.get("quarantine_entries", 0)) + \
                             abs(storage_delta.get("promoted_entries", 0))
                storage_deltas.append(total_delta)
        except Exception as e:
            print(f"[WARN] スナップショット読み込みエラー: {snapshot_path}: {e}")
            continue
    
    # 集計計算
    summary = {
        "snapshot_count": len(snapshots),
        "time_range_hours": hours,  # type: ignore[name-defined]
        "metrics": {
            "p95": {
                "max": max(p95_values) if p95_values else 0,
                "avg": sum(p95_values) / len(p95_values) if p95_values else 0,
                "min": min(p95_values) if p95_values else 0,
            },
            "contradiction_rate": {
                "max": max(contradiction_rates) if contradiction_rates else 0,
                "avg": sum(contradiction_rates) / len(contradiction_rates) if contradiction_rates else 0,
            },
            "gate_block_rate": {
                "max": max(gate_block_rates) if gate_block_rates else 0,
                "avg": sum(gate_block_rates) / len(gate_block_rates) if gate_block_rates else 0,
            },
            "writes_per_min": {
                "max": max(writes_per_min_values) if writes_per_min_values else 0,
                "avg": sum(writes_per_min_values) / len(writes_per_min_values) if writes_per_min_values else 0,
            },
            "http_5xx": {
                "total": sum(http_5xx_counts),
                "max": max(http_5xx_counts) if http_5xx_counts else 0,
            },
            "storage_delta": {
                "max": max(storage_deltas) if storage_deltas else 0,
                "total": sum(storage_deltas) if storage_deltas else 0,
            },
        },
        "baseline": {
            "p95": baseline_data.get("metrics", {}).get("e2e_p95_sec", 0) if baseline_data else 0,
            "writes_per_min": baseline_data.get("metrics", {}).get("writes_per_min", 0) if baseline_data else 0,
        } if baseline_data else None,
    }
    
    return summary

def check_go_conditions(summary: Dict, baseline: Optional[Path] = None) -> Tuple[bool, List[str]]:
    """
    Phase 2 Go条件をチェック
    
    Returns:
        (can_go, reasons)
    """
    reasons = []
    can_go = True
    
    if summary.get("error"):
        reasons.append(summary["error"])
        return False, reasons
    
    metrics = summary["metrics"]
    baseline_data = load_snapshot(baseline) if baseline and baseline.exists() else None
    baseline_p95 = baseline_data.get("metrics", {}).get("e2e_p95_sec", 0.000263) if baseline_data else 0.000263
    
    # 1. Read-only健全性
    if metrics["writes_per_min"]["max"] > 0:
        reasons.append(f"Read-only違反: writes_per_min最大値={metrics['writes_per_min']['max']} > 0")
        can_go = False
    
    if metrics["storage_delta"]["max"] > 0:
        reasons.append(f"Read-only違反: storage_delta最大値={metrics['storage_delta']['max']} > 0")
        can_go = False
    
    # 2. 安定性
    http_5xx_total = metrics["http_5xx"]["total"]
    if http_5xx_total >= 3:
        reasons.append(f"重大エラー: http_5xx合計={http_5xx_total} >= 3")
        can_go = False
    
    p95_max = metrics["p95"]["max"]
    p95_threshold = baseline_p95 * 3.0  # baseline × 3.0
    if p95_max >= p95_threshold:
        reasons.append(
            f"レイテンシ悪化: p95最大値={p95_max:.6f}秒 >= {p95_threshold:.6f}秒（baseline×3.0）"
        )
        can_go = False
    
    # 3. 品質シグナル
    contradiction_max = metrics["contradiction_rate"]["max"]
    if contradiction_max >= 0.05:  # 5%
        reasons.append(
            f"矛盾検出率悪化: contradiction_rate最大値={contradiction_max:.1%} >= 5%"
        )
        can_go = False
    
    gate_max = metrics["gate_block_rate"]["max"]
    if gate_max >= 0.95:  # 95%
        reasons.append(
            f"ゲート遮断率悪化: gate_block_rate最大値={gate_max:.1%} >= 95%"
        )
        can_go = False
    
    return can_go, reasons

def main():
    """メイン処理"""
    print("=" * 60)
    print("Phase 1 24時間運用 集計")
    print("=" * 60)
    print()
    
    if len(sys.argv) < 2:
        print("使用方法: python phase1_24h_summary.py <snapshot_dir> [baseline_snapshot.json] [hours]")
        return
    
    snapshot_dir = Path(sys.argv[1])
    baseline_path = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("phase1_metrics_snapshot_baseline.json")
    hours = int(sys.argv[3]) if len(sys.argv) > 3 else 24
    
    if not snapshot_dir.exists():
        print(f"[ERROR] スナップショットディレクトリが見つかりません: {snapshot_dir}")
        return
    
    # スナップショットを収集
    print(f"スナップショットを収集中...（{hours}時間分）")
    snapshots = collect_snapshots(snapshot_dir, hours)
    print(f"収集完了: {len(snapshots)}個のスナップショット")
    print()
    
    if not snapshots:
        print("[WARN] スナップショットがありません")
        return
    
    # 集計を計算
    print("集計を計算中...")
    summary = calculate_summary(snapshots, baseline_path)
    print("計算完了")
    print()
    
    # 集計結果を表示
    print("=" * 60)
    print("集計結果")
    print("=" * 60)
    print(f"スナップショット数: {summary['snapshot_count']}個")
    print(f"時間範囲: {summary['time_range_hours']}時間")
    print()
    
    metrics = summary["metrics"]
    print("メトリクス:")
    print(f"  - p95: max={metrics['p95']['max']:.6f}秒, avg={metrics['p95']['avg']:.6f}秒")
    print(f"  - contradiction_rate: max={metrics['contradiction_rate']['max']:.1%}, avg={metrics['contradiction_rate']['avg']:.1%}")
    print(f"  - gate_block_rate: max={metrics['gate_block_rate']['max']:.1%}, avg={metrics['gate_block_rate']['avg']:.1%}")
    print(f"  - writes_per_min: max={metrics['writes_per_min']['max']}, avg={metrics['writes_per_min']['avg']:.2f}")
    print(f"  - http_5xx: total={metrics['http_5xx']['total']}, max={metrics['http_5xx']['max']}")
    print(f"  - storage_delta: max={metrics['storage_delta']['max']}, total={metrics['storage_delta']['total']}")
    print()
    
    # Go条件をチェック
    can_go, reasons = check_go_conditions(summary, baseline_path)
    
    print("=" * 60)
    print("Phase 2 Go条件チェック")
    print("=" * 60)
    
    if can_go:
        print("[GO] Phase 2へ進むことができます")
        print()
        print("→ Phase 2（Write 10%）へ進む準備ができています")
    else:
        print("[NO-GO] Phase 2へ進む条件を満たしていません:")
        for reason in reasons:
            print(f"  - {reason}")
        print()
        print("→ 上記の問題を解決してからPhase 2へ進んでください")
    
    # JSON出力
    output_path = snapshot_dir / f"phase1_24h_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "summary": summary,
            "go_decision": {
                "can_go": can_go,
                "reasons": reasons,
            }
        }, f, ensure_ascii=False, indent=2)
    print()
    print(f"集計結果を保存: {output_path}")

if __name__ == "__main__":
    main()
