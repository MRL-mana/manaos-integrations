#!/usr/bin/env python3
"""
Phase 1 (Read-only) Go/No-Go 判定スクリプト
SECURITYログとダッシュボード初期値から判定
"""

import os
import sys
import json
from pathlib import Path

def check_security_log(security_log_line: str) -> tuple[bool, list[str]]:
    """
    SECURITYログをチェック
    
    Args:
        security_log_line: SECURITYログの1行
    
    Returns:
        (is_go, issues)
    """
    issues = []
    
    if not security_log_line:
        return False, ["SECURITYログが提供されていません"]
    
    # 必須項目をチェック
    required_items = {
        "auth": "enabled",
        "rate_limit": "enabled",
        "pii_mask": "enabled"
    }
    
    for key, expected_value in required_items.items():
        if f"{key}={expected_value}" not in security_log_line:
            issues.append(f"{key}が{expected_value}ではありません")
    
    # max_inputをチェック
    if "max_input=" in security_log_line:
        try:
            # max_input=200000 から数値を抽出
            max_input_part = security_log_line.split("max_input=")[1].split(",")[0].split()[0]
            max_input = int(max_input_part)
            
            if max_input < 10000:
                issues.append(f"max_inputが小さすぎます: {max_input}（推奨: 200000以上）")
        except (ValueError, IndexError):
            issues.append("max_inputの値が読み取れません")
    else:
        issues.append("max_inputが設定されていません")
    
    is_go = len(issues) == 0
    return is_go, issues

def check_dashboard_metrics(metrics: dict) -> tuple[bool, list[str], list[str]]:
    """
    ダッシュボード初期値をチェック
    
    Args:
        metrics: ダッシュボードの指標（辞書形式）
    
    Returns:
        (is_go, warnings, errors)
    """
    warnings = []
    errors = []
    
    # 1. E2E p95
    p95 = metrics.get("p95", 0)
    if p95 > 0.3:
        errors.append(f"E2E p95が高すぎます: {p95:.3f}秒（No-Go: > 0.3秒）")
    elif p95 > 0.1:
        warnings.append(f"E2E p95が注意範囲です: {p95:.3f}秒（注意: 0.1〜0.3秒）")
    
    # 2. ゲート遮断率
    gate_block_rate = metrics.get("gate_block_rate", 0)
    if gate_block_rate >= 0.95:
        errors.append(f"ゲート遮断率が高すぎます: {gate_block_rate:.1%}（No-Go: >= 95%）")
    elif gate_block_rate >= 0.80:
        warnings.append(f"ゲート遮断率が注意範囲です: {gate_block_rate:.1%}（注意: 80〜95%）")
    
    # 3. 矛盾検出率
    conflict_rate = metrics.get("conflict_rate", 0)
    if conflict_rate > 0.10:
        errors.append(f"矛盾検出率が高すぎます: {conflict_rate:.1%}（No-Go: > 10%）")
    elif conflict_rate > 0.05:
        warnings.append(f"矛盾検出率が注意範囲です: {conflict_rate:.1%}（注意: 5〜10%）")
    
    # 4. スロット使用率（分散）
    variance = metrics.get("variance", 0)
    if variance > 1000:
        errors.append(f"スロット使用率の分散が大きすぎます: {variance:.2f}（No-Go: > 1000）")
    elif variance > 100:
        warnings.append(f"スロット使用率の分散が注意範囲です: {variance:.2f}（注意: 100〜1000）")
    
    # 5. 書き込み回数/分（Read-onlyの重要チェック）
    write_count = metrics.get("write_count_per_min", 0)
    if write_count > 0:
        errors.append(f"書き込み回数/分が0ではありません: {write_count}（Read-onlyなのに書き込みが発生しています）")
    
    is_go = len(errors) == 0
    return is_go, warnings, errors

def check_phase2_conditions(metrics_history: list[dict]) -> tuple[bool, list[str]]:
    """
    Phase 2 Go条件をチェック
    
    Args:
        metrics_history: 24〜48時間の指標履歴
    
    Returns:
        (is_go, issues)
    """
    issues = []
    
    if not metrics_history:
        return False, ["指標履歴が提供されていません"]
    
    # 最新の指標を取得
    latest = metrics_history[-1]
    
    # 1. p95が安定（急増なし）
    if len(metrics_history) >= 2:
        previous_p95 = metrics_history[-2].get("p95", 0)
        current_p95 = latest.get("p95", 0)
        if current_p95 > previous_p95 * 2:
            issues.append(f"p95が急増しています: {previous_p95:.3f}秒 → {current_p95:.3f}秒（前回比2倍以上）")
    
    # 2. 矛盾検出率が安定（急増なし）
    if len(metrics_history) >= 2:
        previous_conflict = metrics_history[-2].get("conflict_rate", 0)
        current_conflict = latest.get("conflict_rate", 0)
        if current_conflict > previous_conflict * 2:
            issues.append(f"矛盾検出率が急増しています: {previous_conflict:.1%} → {current_conflict:.1%}（前回比2倍以上）")
    
    # 3. ゲート遮断率が95%貼り付きじゃない
    gate_block_rate = latest.get("gate_block_rate", 0)
    if gate_block_rate >= 0.95:
        issues.append(f"ゲート遮断率が95%貼り付きです: {gate_block_rate:.1%}")
    
    # 4. 書き込み回数/分が0
    write_count = latest.get("write_count_per_min", 0)
    if write_count > 0:
        issues.append(f"書き込み回数/分が0ではありません: {write_count}（Read-onlyなのに書き込みが発生しています）")
    
    is_go = len(issues) == 0
    return is_go, issues

def load_snapshot_from_json(json_path: Path) -> tuple[dict, dict]:
    """
    JSONスナップショットからデータを読み込み
    
    Args:
        json_path: JSONファイルのパス
    
    Returns:
        (security_dict, metrics_dict)
    """
    with open(json_path, 'r', encoding='utf-8') as f:
        snapshot = json.load(f)
    
    security_dict = snapshot.get("security", {})
    metrics_dict = snapshot.get("metrics", {})
    
    return security_dict, metrics_dict

def check_security_from_dict(security_dict: dict) -> tuple[bool, list[str]]:
    """
    SECURITY設定（辞書形式）をチェック
    
    Args:
        security_dict: SECURITY設定の辞書
    
    Returns:
        (is_go, issues)
    """
    issues = []
    
    required_items = {
        "auth": "enabled",
        "rate_limit": "enabled",
        "pii_mask": "enabled"
    }
    
    for key, expected_value in required_items.items():
        actual_value = security_dict.get(key, "")
        if actual_value != expected_value:
            issues.append(f"{key}が{expected_value}ではありません（実際: {actual_value}）")
    
    max_input = security_dict.get("max_input", 0)
    if max_input < 10000:
        issues.append(f"max_inputが小さすぎます: {max_input}（推奨: 200000以上）")
    
    is_go = len(issues) == 0
    return is_go, issues

def check_metrics_from_dict(metrics_dict: dict) -> tuple[bool, list[str], list[str]]:
    """
    メトリクス（辞書形式）をチェック
    
    Args:
        metrics_dict: メトリクスの辞書
    
    Returns:
        (is_go, warnings, errors)
    """
    warnings = []
    errors = []
    
    # JSONのキー名に合わせる
    p95 = metrics_dict.get("e2e_p95_sec", 0)
    if p95 > 0.3:
        errors.append(f"E2E p95が高すぎます: {p95:.3f}秒（No-Go: > 0.3秒）")
    elif p95 > 0.1:
        warnings.append(f"E2E p95が注意範囲です: {p95:.3f}秒（注意: 0.1〜0.3秒）")
    
    gate_block_rate = metrics_dict.get("gate_block_rate", 0)
    if gate_block_rate >= 0.95:
        errors.append(f"ゲート遮断率が高すぎます: {gate_block_rate:.1%}（No-Go: >= 95%）")
    elif gate_block_rate >= 0.80:
        warnings.append(f"ゲート遮断率が注意範囲です: {gate_block_rate:.1%}（注意: 80〜95%）")
    
    conflict_rate = metrics_dict.get("contradiction_rate", 0)
    if conflict_rate > 0.10:
        errors.append(f"矛盾検出率が高すぎます: {conflict_rate:.1%}（No-Go: > 10%）")
    elif conflict_rate > 0.05:
        warnings.append(f"矛盾検出率が注意範囲です: {conflict_rate:.1%}（注意: 5〜10%）")
    
    variance = metrics_dict.get("slot_usage_variance", 0)
    if variance > 1000:
        errors.append(f"スロット使用率の分散が大きすぎます: {variance:.2f}（No-Go: > 1000）")
    elif variance > 100:
        warnings.append(f"スロット使用率の分散が注意範囲です: {variance:.2f}（注意: 100〜1000）")
    
    writes_per_min = metrics_dict.get("writes_per_min", 0)
    if writes_per_min > 0:
        errors.append(f"書き込み回数/分が0ではありません: {writes_per_min}（Read-onlyなのに書き込みが発生しています）")
    
    is_go = len(errors) == 0
    return is_go, warnings, errors

def main():
    """メイン処理"""
    print("=" * 60)
    print("Phase 1 (Read-only) Go/No-Go 判定")
    print("=" * 60)
    print()
    
    # JSONファイルから読み込む（優先）
    json_path = None
    if len(sys.argv) > 1:
        json_path = Path(sys.argv[1])
        if json_path.exists():
            print(f"JSONスナップショットから読み込み: {json_path}")
            security_dict, metrics_dict = load_snapshot_from_json(json_path)
            
            # SECURITY設定をチェック
            security_go, security_issues = check_security_from_dict(security_dict)
            
            if not security_go:
                print()
                print("[NO-GO] SECURITY設定のチェックに失敗しました:")
                for issue in security_issues:
                    print(f"  - {issue}")
                print()
                print("→ 即停止・修正が必要です")
                return False
            
            print()
            print("[OK] SECURITY設定のチェックに成功しました")
            print()
            
            # メトリクスをチェック
            metrics_go, warnings, errors = check_metrics_from_dict(metrics_dict)
            
            if errors:
                print("[NO-GO] メトリクスのチェックに失敗しました:")
                for error in errors:
                    print(f"  - {error}")
                print()
                print("→ 即停止・修正が必要です")
                return False
            
            if warnings:
                print("[WARN] メトリクスに注意事項があります:")
                for warning in warnings:
                    print(f"  - {warning}")
                print()
                print("→ 監視を強化してください")
            
            if metrics_go:
                print("[GO] メトリクスのチェックに成功しました")
                print()
                print("判定結果: Phase 1を継続できます")
                print()
                print("次のステップ:")
                print("1. Phase 1を24〜48時間継続")
                print("2. 定期的にダッシュボードを確認")
                print("3. Phase 2 Go条件を満たしたらPhase 2へ")
                return True
            
            return False
    
    # 手動入力モード（フォールバック）
    print("JSONファイルが指定されていないため、手動入力モードです")
    print("（JSONファイルを指定する場合は: python phase1_decision_maker.py phase1_metrics_snapshot.json）")
    print()
    
    # SECURITYログを入力
    print("SECURITYログを入力してください（1行）:")
    print("例: SECURITY: auth=enabled, rate_limit=enabled, max_input=200000, pii_mask=enabled")
    security_log = input().strip()
    
    # SECURITYログをチェック
    security_go, security_issues = check_security_log(security_log)
    
    if not security_go:
        print()
        print("[NO-GO] SECURITYログのチェックに失敗しました:")
        for issue in security_issues:
            print(f"  - {issue}")
        print()
        print("→ 即停止・修正が必要です")
        return False
    
    print()
    print("[OK] SECURITYログのチェックに成功しました")
    print()
    
    # ダッシュボード初期値を入力
    print("ダッシュボード初期値を入力してください:")
    print("（各項目を数値で入力、不明な場合は空欄）")
    print()
    
    metrics = {}
    
    p95_input = input("E2E p95 (秒): ").strip()
    if p95_input:
        try:
            metrics["p95"] = float(p95_input)
        except ValueError:
            print("  [WARN] p95の値が無効です")
    
    gate_block_input = input("ゲート遮断率 (%): ").strip()
    if gate_block_input:
        try:
            metrics["gate_block_rate"] = float(gate_block_input) / 100
        except ValueError:
            print("  [WARN] ゲート遮断率の値が無効です")
    
    conflict_input = input("矛盾検出率 (%): ").strip()
    if conflict_input:
        try:
            metrics["conflict_rate"] = float(conflict_input) / 100
        except ValueError:
            print("  [WARN] 矛盾検出率の値が無効です")
    
    variance_input = input("スロット使用率の分散: ").strip()
    if variance_input:
        try:
            metrics["variance"] = float(variance_input)
        except ValueError:
            print("  [WARN] 分散の値が無効です")
    
    write_count_input = input("書き込み回数/分: ").strip()
    if write_count_input:
        try:
            metrics["write_count_per_min"] = int(write_count_input)
        except ValueError:
            print("  [WARN] 書き込み回数/分の値が無効です")
    
    print()
    
    # ダッシュボード初期値をチェック（手動入力用の変換）
    metrics_for_check = {
        "p95": metrics.get("p95", 0),
        "gate_block_rate": metrics.get("gate_block_rate", 0),
        "conflict_rate": metrics.get("conflict_rate", 0),
        "variance": metrics.get("variance", 0),
        "write_count_per_min": metrics.get("write_count_per_min", 0)
    }
    
    metrics_go, warnings, errors = check_dashboard_metrics(metrics_for_check)
    
    if errors:
        print("[NO-GO] ダッシュボード初期値のチェックに失敗しました:")
        for error in errors:
            print(f"  - {error}")
        print()
        print("→ 即停止・修正が必要です")
        return False
    
    if warnings:
        print("[WARN] ダッシュボード初期値に注意事項があります:")
        for warning in warnings:
            print(f"  - {warning}")
        print()
        print("→ 監視を強化してください")
    
    if metrics_go:
        print("[GO] ダッシュボード初期値のチェックに成功しました")
        print()
        print("判定結果: Phase 1を継続できます")
        print()
        print("次のステップ:")
        print("1. Phase 1を24〜48時間継続")
        print("2. 定期的にダッシュボードを確認")
        print("3. Phase 2 Go条件を満たしたらPhase 2へ")
        return True
    
    return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
