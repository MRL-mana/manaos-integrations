#!/usr/bin/env python3
"""
Phase 2 (Write 10%) 停止判定スクリプト
実測値ベースの停止ラインをチェック（継続判定対応）
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Tuple, Optional

# 実測値（Phase 1 baseline）
BASELINE_P95 = 0.000263  # baseline p95
BASELINE_WRITES_PER_MIN = 0  # baseline writes_per_min

# 停止閾値（実測値ベース）
STOP_THRESHOLDS = {
    "writes_per_min_multiplier": 10.0,  # Phase1比で10倍以上
    "writes_per_min_absolute": 50,  # Phase2での絶対値（sample_rate=0.1なら数十/min想定）
    "p95_multiplier": 4.0,  # Phase1比で4倍以上（0.001052秒）
    "p95_go_multiplier": 3.0,  # Phase1比で3倍以上（0.000789秒）が継続したらNG
    "contradiction_rate_max": 0.10,  # 10%（停止ライン）
    "contradiction_rate_go": 0.05,  # 5%（Go判定ライン）
    "gate_block_rate_go": 0.95,  # 95%（Go判定ライン）
    "http_5xx_max": 3,  # 3以上
    "quarantine_dominance": True,  # quarantine > scratchpad
    "consecutive_violations": 3,  # 3回連続（=3時間）で継続と判定
    "max_missing_snapshots": 1,  # 24hのうち欠損が1回まで許容
    "max_consecutive_missing": 2,  # 連続欠損が2回以上で判定不能
}

def load_snapshot(json_path: Path) -> dict:
    """スナップショットを読み込む"""
    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def check_consecutive_violations(
    snapshot_paths: List[Path],
    check_func,
    baseline: Optional[dict] = None
) -> Tuple[bool, List[str], int]:
    """
    連続違反をチェック（欠損を考慮）
    
    Args:
        snapshot_paths: スナップショットパスのリスト（時系列順、新しい順）
        check_func: 違反チェック関数（snapshot, baseline -> bool, reason）
        baseline: ベースラインスナップショット（オプション）
    
    Returns:
        (has_consecutive_violations, reasons, violation_count)
    """
    violations = 0
    max_consecutive = 0
    current_consecutive = 0
    all_reasons = []
    
    for path in snapshot_paths:
        try:
            snapshot = load_snapshot(path)
            is_violation, reason = check_func(snapshot, baseline)
            
            if is_violation:
                violations += 1
                current_consecutive += 1
                max_consecutive = max(max_consecutive, current_consecutive)
                if reason:
                    all_reasons.append(f"{path.name}: {reason}")
            else:
                current_consecutive = 0
        except Exception as e:
            # スナップショット読み込みエラーは欠損として扱う（連続カウントをリセット）
            # 欠損は違反としてカウントしない（無視）
            current_consecutive = 0
            continue
    
    consecutive_threshold = STOP_THRESHOLDS["consecutive_violations"]
    has_consecutive = max_consecutive >= consecutive_threshold
    
    return has_consecutive, all_reasons, max_consecutive

def check_p95_go_violation(snapshot: dict, baseline: Optional[dict] = None) -> Tuple[bool, Optional[str]]:
    """p95 Go判定ライン違反をチェック"""
    metrics = snapshot.get("metrics", {})
    current_p95 = metrics.get("e2e_p95_sec", 0)
    baseline_p95 = baseline.get("metrics", {}).get("e2e_p95_sec", BASELINE_P95) if baseline else BASELINE_P95
    p95_threshold = baseline_p95 * STOP_THRESHOLDS["p95_go_multiplier"]
    
    if current_p95 >= p95_threshold:
        return True, f"e2e_p95_sec={current_p95:.6f}秒 >= {p95_threshold:.6f}秒（baseline×{STOP_THRESHOLDS['p95_go_multiplier']}）"
    return False, None

def check_contradiction_rate_go_violation(snapshot: dict, baseline: Optional[dict] = None) -> Tuple[bool, Optional[str]]:
    """矛盾検出率 Go判定ライン違反をチェック"""
    metrics = snapshot.get("metrics", {})
    contradiction_rate = metrics.get("contradiction_rate", 0)
    
    if contradiction_rate >= STOP_THRESHOLDS["contradiction_rate_go"]:
        return True, f"contradiction_rate={contradiction_rate:.1%} >= {STOP_THRESHOLDS['contradiction_rate_go']:.1%}"
    return False, None

def check_gate_block_rate_go_violation(snapshot: dict, baseline: Optional[dict] = None) -> Tuple[bool, Optional[str]]:
    """ゲート遮断率 Go判定ライン違反をチェック"""
    metrics = snapshot.get("metrics", {})
    gate_block_rate = metrics.get("gate_block_rate", 0)
    
    if gate_block_rate >= STOP_THRESHOLDS["gate_block_rate_go"]:
        return True, f"gate_block_rate={gate_block_rate:.1%} >= {STOP_THRESHOLDS['gate_block_rate_go']:.1%}"
    return False, None

def check_stop_conditions(current: dict, baseline: dict = None) -> tuple[bool, list[str]]:
    """
    停止条件をチェック（単一スナップショット）
    
    Args:
        current: 現在のスナップショット
        baseline: ベースラインスナップショット（オプション）
    
    Returns:
        (should_stop, reasons)
    """
    reasons = []
    should_stop = False
    
    metrics = current.get("metrics", {})
    storage = current.get("storage", {})
    errors = current.get("errors", {})
    storage_delta = current.get("storage_delta", {})
    
    # 1. 書き込み暴走（絶対値と比率の両方でチェック）
    current_writes = metrics.get("writes_per_min", 0)
    baseline_writes = baseline.get("metrics", {}).get("writes_per_min", BASELINE_WRITES_PER_MIN) if baseline else BASELINE_WRITES_PER_MIN
    
    # 絶対値チェック（Phase2での想定値を超えた場合）
    if current_writes >= STOP_THRESHOLDS["writes_per_min_absolute"]:
        reasons.append(
            f"書き込み暴走（絶対値）: writes_per_min={current_writes} >= {STOP_THRESHOLDS['writes_per_min_absolute']}"
        )
        should_stop = True
    
    # 比率チェック（Phase1比で10倍以上、かつbaseline > 0の場合のみ有効）
    if baseline_writes > 0 and current_writes > baseline_writes * STOP_THRESHOLDS["writes_per_min_multiplier"]:
        reasons.append(
            f"書き込み暴走（比率）: writes_per_min={current_writes} "
            f"（baseline={baseline_writes}の{current_writes/baseline_writes:.1f}倍）"
        )
        should_stop = True
    
    # 2. ストレージ汚染（quarantineがscratchpadを上回る）
    quarantine_entries = storage.get("quarantine_entries", 0)
    scratchpad_entries = storage.get("scratchpad_entries", 0)
    
    if quarantine_entries > scratchpad_entries and scratchpad_entries > 0:
        reasons.append(
            f"ストレージ汚染: quarantine_entries={quarantine_entries} > "
            f"scratchpad_entries={scratchpad_entries}"
        )
        should_stop = True
    
    # 3. 矛盾検出率の暴走
    contradiction_rate = metrics.get("contradiction_rate", 0)
    if contradiction_rate >= STOP_THRESHOLDS["contradiction_rate_max"]:
        reasons.append(
            f"矛盾検出率暴走: contradiction_rate={contradiction_rate:.1%} "
            f"（閾値: {STOP_THRESHOLDS['contradiction_rate_max']:.1%}）"
        )
        should_stop = True
    
    # 4. レイテンシの暴走
    current_p95 = metrics.get("e2e_p95_sec", 0)
    baseline_p95 = baseline.get("metrics", {}).get("e2e_p95_sec", BASELINE_P95) if baseline else BASELINE_P95
    p95_threshold = baseline_p95 * STOP_THRESHOLDS["p95_multiplier"]
    
    if current_p95 >= p95_threshold:
        reasons.append(
            f"レイテンシ暴走: e2e_p95_sec={current_p95:.6f}秒 "
            f"（baseline={baseline_p95:.6f}秒の{current_p95/baseline_p95 if baseline_p95 > 0 else 'N/A'}倍、"
            f"閾値: {p95_threshold:.6f}秒）"
        )
        should_stop = True
    
    # 5. 重大エラー
    http_5xx = errors.get("http_5xx_last_60min", 0)
    if http_5xx >= STOP_THRESHOLDS["http_5xx_max"]:
        reasons.append(
            f"重大エラー: http_5xx_last_60min={http_5xx} "
            f"（閾値: {STOP_THRESHOLDS['http_5xx_max']}）"
        )
        should_stop = True
    
    return should_stop, reasons

def check_go_conditions(
    snapshot_dir: Path,
    baseline: Optional[dict] = None,
    hours: int = 24
) -> Tuple[bool, List[str]]:
    """
    Phase 2 Go条件をチェック（継続判定）
    
    Args:
        snapshot_dir: スナップショットディレクトリ
        baseline: ベースラインスナップショット（オプション）
        hours: チェックする時間範囲（デフォルト: 24時間）
    
    Returns:
        (can_go, reasons)
    """
    reasons = []
    can_go = True
    
    # スナップショットファイルを時系列順（新しい順）に取得
    snapshot_files = sorted(
        snapshot_dir.glob("phase1_metrics_snapshot_*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True
    )
    
    # 直近hours時間分のスナップショットを取得
    cutoff_time = datetime.now().timestamp() - (hours * 3600)
    recent_snapshots = [
        p for p in snapshot_files
        if p.stat().st_mtime >= cutoff_time
    ][:hours]  # 最大hours個まで
    
    # 欠損チェック（保険①：メトリクス欠損の扱いルール）
    expected_count = hours
    actual_count = len(recent_snapshots)
    missing_count = expected_count - actual_count
    
    # 連続欠損をチェック（時系列順にソート）
    sorted_snapshots = sorted(recent_snapshots, key=lambda p: p.stat().st_mtime)
    max_consecutive_missing = 0
    current_consecutive_missing = 0
    last_timestamp = None
    
    for snapshot_path in sorted_snapshots:
        current_timestamp = snapshot_path.stat().st_mtime
        if last_timestamp is not None:
            # 1時間（3600秒）以上の間隔があれば欠損とみなす
            if current_timestamp - last_timestamp > 3600 * 1.5:  # 1.5時間のバッファ
                gap_hours = int((current_timestamp - last_timestamp) / 3600)
                current_consecutive_missing += gap_hours - 1
                max_consecutive_missing = max(max_consecutive_missing, current_consecutive_missing)
            else:
                current_consecutive_missing = 0
        last_timestamp = current_timestamp
    
    # 連続欠損が2回以上なら判定不能
    if max_consecutive_missing >= STOP_THRESHOLDS["max_consecutive_missing"]:
        reasons.append(
            f"判定不能（計測経路の問題）: 連続欠損={max_consecutive_missing}回 >= {STOP_THRESHOLDS['max_consecutive_missing']}回"
        )
        reasons.append("→ 観測復旧を優先してください（Go/No-Go判定は一旦停止）")
        return False, reasons
    
    # 総欠損が許容範囲を超える場合
    if missing_count > STOP_THRESHOLDS["max_missing_snapshots"]:
        reasons.append(
            f"スナップショット欠損が許容範囲を超えています: 欠損={missing_count}回 > {STOP_THRESHOLDS['max_missing_snapshots']}回"
        )
        # ただし、継続判定に必要な数があれば続行
    
    # 継続判定に必要な最小数が不足している場合
    if actual_count < STOP_THRESHOLDS["consecutive_violations"]:
        reasons.append(
            f"スナップショットが不足: {actual_count}個 < {STOP_THRESHOLDS['consecutive_violations']}個（継続判定に必要な数）"
        )
        return False, reasons
    
    # 1. p95 Go判定ラインの継続違反チェック
    has_p95_violations, p95_reasons, p95_count = check_consecutive_violations(
        recent_snapshots, check_p95_go_violation, baseline
    )
    if has_p95_violations:
        reasons.append(
            f"p95 Go判定ライン違反が継続: {p95_count}回連続違反 >= {STOP_THRESHOLDS['consecutive_violations']}回"
        )
        if p95_reasons:
            reasons.extend(p95_reasons[:3])  # 最新3件のみ表示
        can_go = False
    
    # 2. contradiction_rate Go判定ラインの継続違反チェック
    has_contradiction_violations, contradiction_reasons, contradiction_count = check_consecutive_violations(
        recent_snapshots, check_contradiction_rate_go_violation, baseline
    )
    if has_contradiction_violations:
        reasons.append(
            f"矛盾検出率 Go判定ライン違反が継続: {contradiction_count}回連続違反 >= {STOP_THRESHOLDS['consecutive_violations']}回"
        )
        if contradiction_reasons:
            reasons.extend(contradiction_reasons[:3])
        can_go = False
    
    # 3. gate_block_rate Go判定ラインの継続違反チェック
    has_gate_violations, gate_reasons, gate_count = check_consecutive_violations(
        recent_snapshots, check_gate_block_rate_go_violation, baseline
    )
    if has_gate_violations:
        reasons.append(
            f"ゲート遮断率 Go判定ライン違反が継続: {gate_count}回連続違反 >= {STOP_THRESHOLDS['consecutive_violations']}回"
        )
        if gate_reasons:
            reasons.extend(gate_reasons[:3])
        can_go = False
    
    return can_go, reasons

def main():
    """メイン処理"""
    print("=" * 60)
    print("Phase 2 (Write 10%) 停止判定")
    print("=" * 60)
    print()
    
    if len(sys.argv) < 2:
        print("使用方法:")
        print("  python phase2_stop_checker.py <current_snapshot.json> [baseline_snapshot.json]")
        print("  python phase2_stop_checker.py --go <snapshot_dir> [baseline_snapshot.json] [hours]")
        return False
    
    # Go条件チェックモード
    if sys.argv[1] == "--go":
        if len(sys.argv) < 3:
            print("[ERROR] スナップショットディレクトリを指定してください")
            return False
        
        snapshot_dir = Path(sys.argv[2])
        baseline_path = Path(sys.argv[3]) if len(sys.argv) > 3 else None
        hours = int(sys.argv[4]) if len(sys.argv) > 4 else 24
        
        if not snapshot_dir.exists():
            print(f"[ERROR] スナップショットディレクトリが見つかりません: {snapshot_dir}")
            return False
        
        baseline = load_snapshot(baseline_path) if baseline_path and baseline_path.exists() else None
        
        can_go, reasons = check_go_conditions(snapshot_dir, baseline, hours)
        
        if not can_go:
            print("[NO-GO] Phase 2 Go条件を満たしていません:")
            for reason in reasons:
                print(f"  - {reason}")
            print()
            print("→ Phase 2へ進む前に、上記の問題を解決してください")
            return False
        else:
            print("[GO] Phase 2 Go条件を満たしています")
            print()
            print(f"→ Phase 2（Write 10%）へ進むことができます")
            return True
    
    # 停止条件チェックモード（従来通り）
    current_path = Path(sys.argv[1])
    baseline_path = Path(sys.argv[2]) if len(sys.argv) > 2 else None
    
    if not current_path.exists():
        print(f"[ERROR] スナップショットが見つかりません: {current_path}")
        return False
    
    # スナップショットを読み込む
    current = load_snapshot(current_path)
    baseline = load_snapshot(baseline_path) if baseline_path and baseline_path.exists() else None
    
    # 停止条件をチェック
    should_stop, reasons = check_stop_conditions(current, baseline)
    
    if should_stop:
        print("[STOP] 停止条件に該当しました:")
        for reason in reasons:
            print(f"  - {reason}")
        print()
        print("→ 即停止が必要です")
        print()
        print("停止手順:")
        print("1. Kill Switchを有効化: export FWPKM_ENABLED=0")
        print("2. サービス再起動")
        print("3. ログを確認して原因を特定")
        return False
    else:
        print("[OK] 停止条件に該当していません")
        print()
        print("現在の状態:")
        metrics = current.get("metrics", {})
        print(f"  - e2e_p95_sec: {metrics.get('e2e_p95_sec', 0):.6f}秒")
        print(f"  - writes_per_min: {metrics.get('writes_per_min', 0)}")
        print(f"  - contradiction_rate: {metrics.get('contradiction_rate', 0):.1%}")
        print(f"  - http_5xx_last_60min: {current.get('errors', {}).get('http_5xx_last_60min', 0)}")
        print()
        print("→ Phase 2を継続できます")
        return True

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
