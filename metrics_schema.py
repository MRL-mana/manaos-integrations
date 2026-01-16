#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
System 3 メトリクスSchema統一
- メトリクスJSON/JSONLの項目名を固定
- 日次ログ/週次レビューが同じキーを参照
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, date
from pathlib import Path
import json

# メトリクスSchema定義
METRICS_SCHEMA = {
    "score": {
        "score_today": float,
        "score_7d_avg": float,
        "score_trend": str,  # "↑" | "→" | "↓"
        "score_history": List[Dict[str, Any]],  # [{date: str, score: float}]
    },
    "todo": {
        "proposed": int,
        "approved": int,
        "executed": int,
        "expired": int,
        "approval_rate": float,  # approved / proposed
        "execution_rate": float,  # executed / approved
        "noise_index": float,  # expired / proposed
    },
    "system": {
        "timestamp": str,  # ISO format
        "services_running": int,
        "services_total": int,
        "uptime_seconds": Optional[int],
    },
}

# JSONLスキーマ（1行1メトリクス）
JSONL_SCHEMA = {
    "timestamp": str,  # ISO format
    "type": str,  # "score" | "todo" | "system"
    "data": Dict[str, Any],
}


def validate_metrics(data: Dict[str, Any], schema_type: str) -> bool:
    """メトリクスデータの検証"""
    if schema_type not in METRICS_SCHEMA:
        return False

    schema = METRICS_SCHEMA[schema_type]

    for key, expected_type in schema.items():
        if key not in data:
            continue  # オプショナルフィールドはスキップ

        value = data[key]

        if expected_type == List[Dict[str, Any]]:
            if not isinstance(value, list):
                return False
        elif expected_type == Optional[int]:
            if value is not None and not isinstance(value, int):
                return False
        elif not isinstance(value, expected_type):
            return False

    return True


def normalize_score_metrics(score_today: float, score_7d_avg: Optional[float] = None,
                           score_trend: str = "→", score_history: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """スコアメトリクスを正規化"""
    return {
        "score_today": float(score_today),
        "score_7d_avg": float(score_7d_avg) if score_7d_avg is not None else None,
        "score_trend": str(score_trend),
        "score_history": score_history or [],
    }


def normalize_todo_metrics(proposed: int, approved: int, executed: int, expired: int) -> Dict[str, Any]:
    """ToDoメトリクスを正規化"""
    approval_rate = (approved / proposed) if proposed > 0 else None
    execution_rate = (executed / approved) if approved > 0 else None
    noise_index = (expired / proposed) if proposed > 0 else None

    return {
        "proposed": int(proposed),
        "approved": int(approved),
        "executed": int(executed),
        "expired": int(expired),
        "approval_rate": float(approval_rate) if approval_rate is not None else None,
        "execution_rate": float(execution_rate) if execution_rate is not None else None,
        "noise_index": float(noise_index) if noise_index is not None else None,
    }


def normalize_system_metrics(services_running: int, services_total: int,
                            uptime_seconds: Optional[int] = None) -> Dict[str, Any]:
    """システムメトリクスを正規化"""
    return {
        "timestamp": datetime.now().isoformat(),
        "services_running": int(services_running),
        "services_total": int(services_total),
        "uptime_seconds": uptime_seconds,
    }


def write_jsonl_metrics(file_path: Path, metrics_type: str, data: Dict[str, Any]) -> None:
    """JSONL形式でメトリクスを書き込み"""
    entry = {
        "timestamp": datetime.now().isoformat(),
        "type": metrics_type,
        "data": data,
    }

    # 検証
    if not validate_metrics(data, metrics_type):
        raise ValueError(f"Invalid metrics data for type: {metrics_type}")

    # 追記モードで書き込み
    file_path.parent.mkdir(parents=True, exist_ok=True)

    with open(file_path, 'a', encoding='utf-8') as f:
        f.write(json.dumps(entry, ensure_ascii=False) + '\n')


def read_jsonl_metrics(file_path: Path, metrics_type: Optional[str] = None,
                       limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """JSONL形式のメトリクスを読み込み"""
    if not file_path.exists():
        return []

    results = []

    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                entry = json.loads(line.strip())

                if metrics_type and entry.get("type") != metrics_type:
                    continue

                results.append(entry)

                if limit and len(results) >= limit:
                    break
            except json.JSONDecodeError:
                continue

    return results


def write_json_metrics(file_path: Path, metrics: Dict[str, Any]) -> None:
    """JSON形式でメトリクスを書き込み"""
    file_path.parent.mkdir(parents=True, exist_ok=True)

    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2)


def read_json_metrics(file_path: Path) -> Optional[Dict[str, Any]]:
    """JSON形式のメトリクスを読み込み"""
    if not file_path.exists():
        return None

    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


# 使用例・テスト
if __name__ == "__main__":
    import sys
    import io
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

    # テスト: スコアメトリクス
    score_metrics = normalize_score_metrics(
        score_today=10.5,
        score_7d_avg=10.2,
        score_trend="↑",
    )
    print("Score metrics:", json.dumps(score_metrics, ensure_ascii=False, indent=2))

    # テスト: ToDoメトリクス
    todo_metrics = normalize_todo_metrics(
        proposed=10,
        approved=8,
        executed=6,
        expired=2,
    )
    print("\nTodo metrics:", json.dumps(todo_metrics, ensure_ascii=False, indent=2))

    # テスト: システムメトリクス
    system_metrics = normalize_system_metrics(
        services_running=12,
        services_total=18,
        uptime_seconds=3600,
    )
    print("\nSystem metrics:", json.dumps(system_metrics, ensure_ascii=False, indent=2))

    print("\nSchema validation tests:")
    print(f"Score valid: {validate_metrics(score_metrics, 'score')}")
    print(f"Todo valid: {validate_metrics(todo_metrics, 'todo')}")
    print(f"System valid: {validate_metrics(system_metrics, 'system')}")
