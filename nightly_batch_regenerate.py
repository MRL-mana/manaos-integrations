"""
Nightly Batch Regenerate — 夜間自動品質改善バッチ
===================================================
低スコア画像を自動的に再生成して品質改善するスクリプト。

cron 登録:
  0 2 * * * cd /path/to/manaos_integrations && python nightly_batch_regenerate.py

機能:
  - 品質スコアが閾値以下の画像を自動検出
  - 改善パラメータで再生成
  - 改善前後のスコア比較ログ
  - Slack 通知（オプション）
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sqlite3
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

_log = logging.getLogger("manaos.nightly_batch")

IMAGE_GEN_URL = os.getenv("IMAGE_GENERATION_URL", "http://127.0.0.1:5560")
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_NIGHTLY", "")
BILLING_DB = Path(__file__).resolve().parent / "billing.db"
JOB_QUEUE_DB = Path(__file__).resolve().parent / "job_queue.db"
REPORT_DIR = Path(__file__).resolve().parent / "reports"

# 閾値
QUALITY_THRESHOLD = float(os.getenv("NIGHTLY_QUALITY_THRESHOLD", "5.0"))
MAX_REGENERATIONS = int(os.getenv("NIGHTLY_MAX_REGEN", "20"))
IMPROVE_CFG_BOOST = 2.0
IMPROVE_STEPS_BOOST = 10


@contextmanager
def _open_db(path: Path):
    if not path.exists():
        yield None
        return
    conn = sqlite3.connect(str(path), timeout=5)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def _find_low_quality_jobs(db_path: Path, threshold: float, limit: int) -> List[Dict]:
    """低品質ジョブを取得（job_queue.db から）"""
    with _open_db(db_path) as conn:
        if conn is None:
            _log.warning("job_queue.db not found")
            return []
        try:
            rows = conn.execute(
                """SELECT job_id, payload, state, created_at
                   FROM job_queue 
                   WHERE state = 'completed'
                   ORDER BY created_at DESC
                   LIMIT ?""",
                (limit * 3,),  # 多めに取得してフィルタ
            ).fetchall()
        except sqlite3.OperationalError:
            _log.warning("job_queue table not accessible")
            return []

    candidates = []
    for row in rows:
        try:
            payload = json.loads(row["payload"]) if row["payload"] else {}
            quality = payload.get("quality_score", {}).get("overall")
            if quality is not None and quality < threshold:
                candidates.append({
                    "job_id": row["job_id"],
                    "prompt": payload.get("prompt", ""),
                    "quality_score": quality,
                    "created_at": row["created_at"],
                    "original_params": payload,
                })
        except (json.JSONDecodeError, TypeError):
            continue

    return candidates[:limit]


def _regenerate_job(prompt: str, original_params: Dict, client: httpx.Client) -> Dict:
    """改善パラメータで再生成"""
    payload = {
        "prompt": prompt,
        "steps": min(100, (original_params.get("steps", 20) + IMPROVE_STEPS_BOOST)),
        "cfg_scale": min(30, (original_params.get("cfg_scale", 7.0) + IMPROVE_CFG_BOOST)),
        "quality_mode": "best",
        "auto_improve": True,
        "width": original_params.get("width", 512),
        "height": original_params.get("height", 512),
    }

    try:
        resp = client.post(f"{IMAGE_GEN_URL}/api/v1/images/generate", json=payload, timeout=120)
        if resp.status_code == 200:
            return resp.json()
        return {"error": f"HTTP {resp.status_code}", "status": "failed"}
    except Exception as e:
        return {"error": str(e), "status": "failed"}


def _poll_result(job_id: str, client: httpx.Client, timeout: int = 180) -> Dict:
    """結果をポーリング"""
    start = time.time()
    while time.time() - start < timeout:
        try:
            resp = client.get(f"{IMAGE_GEN_URL}/api/v1/images/{job_id}")
            data = resp.json()
            if data.get("status") in ("completed", "failed"):
                return data
        except Exception:
            pass
        time.sleep(5)
    return {"status": "timeout"}


def run_nightly_batch(
    threshold: float = QUALITY_THRESHOLD,
    max_regen: int = MAX_REGENERATIONS,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """夜間バッチを実行"""
    _log.info("=== Nightly Batch Start: threshold=%.1f, max=%d ===", threshold, max_regen)
    start_time = time.time()

    # 低品質ジョブを検出
    candidates = _find_low_quality_jobs(JOB_QUEUE_DB, threshold, max_regen)
    _log.info("Found %d low-quality jobs (< %.1f)", len(candidates), threshold)

    if dry_run:
        _log.info("DRY RUN — skipping regeneration")
        return {
            "mode": "dry_run",
            "candidates": len(candidates),
            "details": candidates,
        }

    results = []
    improved = 0
    failed = 0

    with httpx.Client(timeout=120) as client:
        for i, candidate in enumerate(candidates):
            _log.info("[%d/%d] Regenerating: %s (score=%.1f)",
                      i + 1, len(candidates), candidate["job_id"], candidate["quality_score"])

            regen = _regenerate_job(
                candidate["prompt"],
                candidate.get("original_params", {}),
                client,
            )

            new_job_id = regen.get("job_id")
            if not new_job_id or regen.get("status") == "failed":
                _log.warning("Regeneration failed for %s: %s", candidate["job_id"], regen.get("error"))
                failed += 1
                results.append({
                    "original_job_id": candidate["job_id"],
                    "status": "failed",
                    "error": regen.get("error"),
                })
                continue

            # ポーリング
            final = _poll_result(new_job_id, client)
            new_score = None
            if final.get("result", {}).get("quality_score"):
                new_score = final["result"]["quality_score"].get("overall")

            score_diff = (new_score or 0) - candidate["quality_score"]
            if new_score and new_score > candidate["quality_score"]:
                improved += 1

            results.append({
                "original_job_id": candidate["job_id"],
                "new_job_id": new_job_id,
                "old_score": candidate["quality_score"],
                "new_score": new_score,
                "score_diff": round(score_diff, 2),
                "improved": score_diff > 0,
                "status": final.get("status", "unknown"),
            })

            _log.info("  → new_score=%.1f (diff=%+.1f) %s",
                      new_score or 0, score_diff,
                      "✅ IMPROVED" if score_diff > 0 else "⏸️ no improvement")

    elapsed = time.time() - start_time

    report = {
        "timestamp": datetime.now().isoformat(),
        "elapsed_seconds": round(elapsed, 1),
        "threshold": threshold,
        "candidates_found": len(candidates),
        "regenerated": len(results),
        "improved": improved,
        "failed": failed,
        "improvement_rate": round(improved / len(results) * 100, 1) if results else 0,
        "results": results,
    }

    _log.info(
        "=== Nightly Batch Done: %d regenerated, %d improved (%.1f%%), %d failed, %.1fs ===",
        len(results), improved, report["improvement_rate"], failed, elapsed,
    )

    return report


def _save_report(report: Dict):
    """レポートを保存"""
    REPORT_DIR.mkdir(exist_ok=True)
    filename = f"nightly_batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    path = REPORT_DIR / filename
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    _log.info("Report saved: %s", path)


def _notify_slack(report: Dict):
    """Slack に結果通知"""
    if not SLACK_WEBHOOK_URL:
        return
    try:
        text = (
            f"🌙 *夜間バッチ品質改善完了*\n"
            f"• 候補: {report['candidates_found']} 件\n"
            f"• 再生成: {report['regenerated']} 件\n"
            f"• 改善: {report['improved']} 件 ({report['improvement_rate']}%)\n"
            f"• 失敗: {report['failed']} 件\n"
            f"• 所要時間: {report['elapsed_seconds']}s"
        )
        httpx.post(SLACK_WEBHOOK_URL, json={"text": text}, timeout=10)
    except Exception as e:
        _log.warning("Slack notify failed: %s", e)


def main():
    parser = argparse.ArgumentParser(description="ManaOS Nightly Batch Regenerate")
    parser.add_argument("--threshold", type=float, default=QUALITY_THRESHOLD,
                        help="Quality score threshold")
    parser.add_argument("--max", type=int, default=MAX_REGENERATIONS,
                        help="Max regenerations")
    parser.add_argument("--dry-run", action="store_true", help="List candidates only")
    parser.add_argument("--slack", action="store_true", help="Send Slack notification")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")

    report = run_nightly_batch(
        threshold=args.threshold,
        max_regen=args.max,
        dry_run=args.dry_run,
    )

    _save_report(report)
    print(json.dumps(report, indent=2, ensure_ascii=False))

    if args.slack and not args.dry_run:
        _notify_slack(report)


if __name__ == "__main__":
    main()
