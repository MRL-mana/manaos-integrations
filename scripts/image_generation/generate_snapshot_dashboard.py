#!/usr/bin/env python3
"""
スナップショットを読み込み、簡易ダッシュボード HTML を生成する。
出力: snapshot_dashboard.html（ブラウザで開く）
"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

_DATE_DIR_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_HOUR_JSON_RE = re.compile(r"^\d{2}\.json$")


def _list_snapshot_files(snapshot_dir: Path):
    if not snapshot_dir.exists():
        return []
    out = []
    for p in snapshot_dir.rglob("*.json"):
        if not p.is_file():
            continue
        if not _DATE_DIR_RE.match(p.parent.name) or not _HOUR_JSON_RE.match(p.name):
            continue
        out.append(p)
    return sorted(out, key=lambda p: (p.parent.name, p.name), reverse=True)


def main() -> int:
    base = Path(__file__).resolve().parent
    snapshots_dir = base / "snapshots"
    rows = []
    seen = set()
    max_rows = 24 * 7  # 直近7日分程度
    for path in _list_snapshot_files(snapshots_dir):
        if len(rows) >= max_rows:
            break
        key = (path.parent.name, path.name)
        if key in seen:
            continue
        seen.add(key)
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            continue
        ts = data.get("timestamp", "")
        metrics = data.get("metrics", {})
        rows.append(
            {
                "date": path.parent.name,
                "hour": path.stem,
                "timestamp": ts,
                "e2e_p95_sec": metrics.get("e2e_p95_sec", 0),
                "writes_per_min": metrics.get("writes_per_min", 0),
                "contradiction_rate": metrics.get("contradiction_rate", 0),
                "gate_block_rate": metrics.get("gate_block_rate", 0),
            }
        )

    rows.reverse()

    html_rows = []
    for r in rows:
        html_rows.append(
            f"    <tr><td>{r['date']}</td><td>{r['hour']}</td>"
            f"<td>{r['e2e_p95_sec']:.6f}</td><td>{r['writes_per_min']}</td>"
            f"<td>{r['contradiction_rate']:.2%}</td><td>{r['gate_block_rate']:.2%}</td></tr>"
        )

    html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <title>MRL Memory Phase 2 Snapshot Dashboard</title>
  <style>
    body {{ font-family: sans-serif; margin: 1rem; }}
    table {{ border-collapse: collapse; }}
    th, td {{ border: 1px solid #ccc; padding: 0.3rem 0.6rem; text-align: right; }}
    th {{ background: #eee; }}
    .updated {{ color: #666; font-size: 0.9rem; }}
  </style>
</head>
<body>
  <h1>MRL Memory Phase 2 Snapshot Dashboard</h1>
  <p class="updated">Generated: {datetime.now().isoformat()}</p>
  <table>
    <thead><tr>
      <th>Date</th><th>Hour</th>
      <th>e2e_p95_sec</th><th>writes_per_min</th>
      <th>contradiction_rate</th><th>gate_block_rate</th>
    </tr></thead>
    <tbody>
{chr(10).join(html_rows)}
    </tbody>
  </table>
</body>
</html>
"""

    out_path = base / "snapshot_dashboard.html"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[OK] Written: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
