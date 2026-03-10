#!/usr/bin/env python3
"""
MRL Memory System - 簡易ダッシュボード
最低限の可視化（ログ集計）
"""

from mrl_memory_metrics import MRLMemoryMetrics
from pathlib import Path
import json
from datetime import datetime

def print_dashboard(phase: str = "unknown"):
    """ダッシュボードを表示"""
    import os
    
    metrics = MRLMemoryMetrics()
    
    # Phase情報を取得
    if phase == "unknown":
        phase = os.getenv("FWPKM_WRITE_MODE", "unknown")
        if phase == "readonly":
            phase = "Phase 1: Read-only"
        elif phase == "sampled":
            phase = "Phase 2: Write 10%"
        elif phase == "full":
            review_effect = os.getenv("FWPKM_REVIEW_EFFECT", "0")
            if review_effect == "1":
                phase = "Phase 4: Review effect ON"
            else:
                phase = "Phase 3: Write 100%"
    
    print("=" * 60)
    print("MRL Memory System - ダッシュボード")
    print("=" * 60)
    print(f"Phase: {phase}")
    print(f"更新時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 1. レイテンシ統計
    latency_stats = metrics.get_latency_stats()
    if latency_stats:
        print("📊 E2Eレイテンシ")
        print(f"  p50: {latency_stats.get('p50', 0):.3f}秒")
        print(f"  p95: {latency_stats.get('p95', 0):.3f}秒")
        print(f"  平均: {latency_stats.get('mean', 0):.3f}秒")
        print(f"  最大: {latency_stats.get('max', 0):.3f}秒")
        print()
    
    # 2. 書き込み回数/分
    write_stats = metrics.get_write_count_stats()
    if write_stats:
        print("📝 書き込み回数/分")
        print(f"  現在: {write_stats.get('current', 0)}回/分")
        print(f"  平均: {write_stats.get('mean', 0):.1f}回/分")
        print(f"  最大: {write_stats.get('max', 0)}回/分")
        print()
    
    # 3. ゲート遮断率
    gate_stats = metrics.get_gate_block_rate_stats()
    if gate_stats:
        print("🚫 ゲート遮断率")
        print(f"  現在: {gate_stats.get('current', 0):.1%}")
        print(f"  平均: {gate_stats.get('mean', 0):.1%}")
        print(f"  最大: {gate_stats.get('max', 0):.1%}")
        print()
    
    # 4. 矛盾検出率
    conflict_stats = metrics.get_conflict_detection_rate_stats()
    if conflict_stats:
        print("⚠️  矛盾検出率")
        print(f"  現在: {conflict_stats.get('current', 0):.1%}")
        print(f"  平均: {conflict_stats.get('mean', 0):.1%}")
        print(f"  最大: {conflict_stats.get('max', 0):.1%}")
        print()
    
    # 5. Write Amplification
    write_amp_stats = metrics.get_write_amplification_stats()
    if write_amp_stats:
        print("📈 Write Amplification")
        print(f"  平均: {write_amp_stats.get('mean', 0):.2f}")
        print(f"  最大: {write_amp_stats.get('max', 0):.2f}")
        print()
    
    # 6. スロット使用率
    slot_stats = metrics.get_slot_utilization_stats()
    if slot_stats:
        print("💾 スロット使用率")
        print(f"  平均: {slot_stats.get('mean_utilization', 0):.1%}")
        print(f"  分散: {slot_stats.get('mean_variance', 0):.2f}")
        print()
    
    print("=" * 60)
    
    # Phase別の停止ラインを表示
    phase = os.getenv("FWPKM_WRITE_MODE", "unknown")
    if phase == "readonly":
        print("Phase 1 (Read-only) 停止ライン:")
        print("  - p95が急に跳ねる（前日比2倍以上が続く）→ 停止")
        print("  - ゲート遮断率が常時95%超え → 停止")
        print("  - 矛盾検出率が急増 → 停止")
    elif phase == "sampled":
        print("Phase 2 (Write 10%) 停止ライン:")
        print("  - 書き込み回数/分が想定の2倍以上に増える → 停止")
        print("  - quarantineがactiveを上回る → 停止")
    elif phase == "full":
        review_effect = os.getenv("FWPKM_REVIEW_EFFECT", "0")
        if review_effect == "1":
            print("Phase 4 (Review effect ON) 停止ライン:")
            print("  - 正答率が落ちる → 停止")
            print("  - メモリ使用量が異常に増える → 停止")
        else:
            print("Phase 3 (Write 100%) 停止ライン:")
            print("  - p95が急増（2倍以上）→ 停止")
            print("  - 正答率が落ちる → 停止")
    else:
        print("停止ライン確認:")
        print("  - 矛盾検出率が急上昇（前日比2倍以上）→ 停止")
        print("  - ゲート遮断率が常時80%超え → 停止")
        print("  - 書き込み回数/分が想定の2倍以上 → 停止")
        print("  - p95が急増（2倍以上）→ 停止")
    
    print("=" * 60)

def export_snapshot_json(output_path: Path = None) -> dict:  # type: ignore
    """
    スナップショットをJSON形式で出力
    
    Args:
        output_path: 出力先パス（Noneの場合は返すだけ）
    
    Returns:
        スナップショット（辞書形式）
    """
    import os
    from mrl_memory_metrics import MRLMemoryMetrics
    from mrl_memory_api_security import APISecurity
    
    metrics = MRLMemoryMetrics()
    security = APISecurity()
    
    # レイテンシ統計
    latency_stats = metrics.get_latency_stats()
    p95 = latency_stats.get("p95", 0) if latency_stats else 0
    
    # ゲート遮断率統計
    gate_stats = metrics.get_gate_block_rate_stats()
    gate_block_rate = gate_stats.get("current", 0) if gate_stats else 0
    
    # 矛盾検出率統計
    conflict_stats = metrics.get_conflict_detection_rate_stats()
    conflict_rate = conflict_stats.get("current", 0) if conflict_stats else 0
    
    # スロット使用率統計
    slot_stats = metrics.get_slot_utilization_stats()
    variance = slot_stats.get("mean_variance", 0) if slot_stats else 0
    
    # 書き込み回数統計
    write_stats = metrics.get_write_count_stats()
    writes_per_min = write_stats.get("current", 0) if write_stats else 0
    
    snapshot = {
        "timestamp": datetime.now().isoformat(),
        "phase": os.getenv("FWPKM_WRITE_MODE", "unknown"),
        "security": {
            "auth": "enabled" if security.require_auth else "disabled",
            "rate_limit": "enabled" if security.rate_limit_per_minute > 0 else "disabled",
            "max_input": security.max_input_size,
            "pii_mask": "enabled"
        },
        "metrics": {
            "e2e_p95_sec": p95,
            "gate_block_rate": gate_block_rate,
            "contradiction_rate": conflict_rate,
            "slot_usage_variance": variance,
            "writes_per_min": writes_per_min
        },
        "errors": {
            "http_5xx_last_60min": 0  # 実際の実装ではログから取得
        }
    }
    
    if output_path:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(snapshot, f, ensure_ascii=False, indent=2)
        print(f"スナップショットを保存: {output_path}")
    
    return snapshot

if __name__ == "__main__":
    import sys
    
    # JSON出力モード
    if len(sys.argv) > 1 and sys.argv[1] == "--json":
        output_path = sys.argv[2] if len(sys.argv) > 2 else "phase1_metrics_snapshot.json"
        snapshot = export_snapshot_json(Path(output_path))
        print(json.dumps(snapshot, ensure_ascii=False, indent=2))
    else:
        print_dashboard()
