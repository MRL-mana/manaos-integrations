"""モック実行（即時で結果を返す）。EXECUTOR=mock のとき使う。"""

import time
from typing import Any, Dict, List


class MockExecutor:
    """今の「モック即時実行」をそのまま executor に切り出したもの。"""

    def run(self, plan: Dict[str, Any]) -> tuple[Dict[str, Any], List[Dict[str, Any]]]:
        plan_id = plan.get("plan_id", "")
        steps = plan.get("steps") or []
        dry_run = False
        for s in steps:
            params = s.get("params") or {}
            if params.get("dry_run") is True:
                dry_run = True
                break

        finished_at = time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime())
        execute_events = [
            {"ts": time.time(), "step_id": "scan_downloads", "event": "list_files", "status": "ok"},
            {
                "ts": time.time(),
                "step_id": "classify",
                "event": "classify_files",
                "status": "ok",
                "dry_run": dry_run,
            },
            {"ts": time.time(), "step_id": "apply_moves", "event": "move_files", "status": "ok"},
        ]
        result = {
            "plan_id": plan_id,
            "success": True,
            "status": "completed",
            "dry_run": dry_run,
            "summary": "mock execution completed",
            "finished_at": finished_at,
            "steps_done": len(steps),
            "steps_total": len(steps),
            "duration_seconds": 0.1,
            "execute_events": execute_events,
            "outputs": {
                "moved": (
                    []
                    if dry_run
                    else [{"from": "~/Downloads/a.pdf", "to": "~/Documents/PDF/a.pdf"}]
                ),
                "classified": [{"file": "a.pdf", "bucket": "PDF"}],
            },
        }
        return result, execute_events
