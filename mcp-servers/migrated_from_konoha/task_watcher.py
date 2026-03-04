#!/usr/bin/env python3
"""
Trinity Orchestrator Task Watcher

tasks.json を監視し、`auto_orchestrate: true` のタスクを検出して
Trinity Orchestratorを起動する。実行後は TicketManager のチケット情報を
反映しつつ、タスクの automation フィールドへ詳細を保存する。
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

CURRENT_DIR = Path(__file__).resolve().parent
ROOT = Path("/root")
WORKSPACE_SHARED = ROOT / "trinity_workspace" / "shared"
TASKS_PATH = WORKSPACE_SHARED / "tasks.json"
LOG_DIR = ROOT / "trinity_workspace" / "logs"
LOG_FILE = LOG_DIR / "task_watcher.log"

# orchestrator modules
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from core import TrinityOrchestrator  # type: ignore  # noqa: E402
from ticket_manager import TicketManager  # type: ignore  # noqa: E402

AUTOMATION_DIR = ROOT / "trinity_workspace" / "automation"
if str(AUTOMATION_DIR) not in sys.path:
    sys.path.insert(0, str(AUTOMATION_DIR))

try:  # pragma: no cover - 通知周りは環境依存
    from notify_channels import broadcast as channel_broadcast  # type: ignore
except Exception:
    channel_broadcast = None


def log(message: str) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted = f"[{timestamp}] {message}"
    print(formatted)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with LOG_FILE.open("a", encoding="utf-8") as fp:
        fp.write(formatted + "\n")


def send_notification(message: str, level: str = "info") -> None:
    if not channel_broadcast:
        return
    try:
        result = channel_broadcast(message, level)
        log(f"📣 通知送信 result={result}")
    except Exception as exc:  # pragma: no cover
        log(f"⚠️ 通知送信エラー: {exc}")


def load_tasks() -> List[Dict[str, Any]]:
    if not TASKS_PATH.exists():
        raise FileNotFoundError(f"tasks.json not found at {TASKS_PATH}")
    with TASKS_PATH.open("r", encoding="utf-8") as fp:
        return json.load(fp)


def save_tasks(tasks: List[Dict[str, Any]]) -> None:
    tmp = TASKS_PATH.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as fp:
        json.dump(tasks, fp, ensure_ascii=False, indent=2)
    tmp.replace(TASKS_PATH)


def ensure_api_key() -> bool:
    if os.getenv("OPENAI_API_KEY"):
        return True

    vault_env = ROOT / ".mana_vault" / "unified_api_keys.env"
    if vault_env.exists():
        with vault_env.open("r", encoding="utf-8") as fp:
            for line in fp:
                line = line.strip()
                if line.startswith("OPENAI_API_KEY="):
                    os.environ["OPENAI_API_KEY"] = line.split("=", 1)[1].strip().strip('"')
                    break

    env_file = ROOT / ".env"
    if not os.getenv("OPENAI_API_KEY") and env_file.exists():
        with env_file.open("r", encoding="utf-8") as fp:
            for line in fp:
                line = line.strip()
                if line.startswith("OPENAI_API_KEY="):
                    os.environ["OPENAI_API_KEY"] = line.split("=", 1)[1].strip().strip('"')
                    break

    return bool(os.getenv("OPENAI_API_KEY"))


def find_candidates(tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    candidates: List[Dict[str, Any]] = []
    for task in tasks:
        if not task.get("auto_orchestrate"):
            continue
        if task.get("automation", {}).get("in_progress"):
            continue
        if task.get("status") not in {"todo", "planning"}:
            continue
        candidates.append(task)
    return candidates


def update_task(tasks: List[Dict[str, Any]], task_id: str, data: Dict[str, Any]) -> None:
    for task in tasks:
        if task.get("id") == task_id:
            task.update(data)
            return
    raise ValueError(f"task_id={task_id} not found in tasks.json")


class TaskWatcher:
    def __init__(self, interval: int = 30):
        self.interval = interval
        self.ticket_manager = TicketManager()

    def run_once(self) -> None:
        tasks = load_tasks()
        targets = find_candidates(tasks)
        if not targets:
            return

        log(f"📦 {len(targets)} 件のタスクを処理します")
        for task in targets:
            self.process_task(tasks, task)

    def process_task(self, tasks: List[Dict[str, Any]], task: Dict[str, Any]) -> None:
        task_id = task["id"]
        automation = task.get("automation", {})
        automation.update(
            {
                "in_progress": True,
                "started_at": datetime.now().isoformat(),
            }
        )
        update_task(
            tasks,
            task_id,
            {
                "status": "in_progress",
                "automation": automation,
            },
        )
        save_tasks(tasks)

        if not ensure_api_key():
            log("⚠️ OPENAI_API_KEY not available. skipping execution.")
            send_notification(
                f"Task {task_id} スキップ: OPENAI_API_KEY が見つからないよ",
                level="warning",
            )
            automation.update(
                {
                    "in_progress": False,
                    "final_status": "skipped",
                    "last_error": "OPENAI_API_KEY missing",
                    "last_run_at": datetime.now().isoformat(),
                }
            )
            update_task(
                tasks,
                task_id,
                {
                    "status": "todo",
                    "automation": automation,
                },
            )
            save_tasks(tasks)
            return

        goal = task.get("title") or task_id
        context = [task.get("description", "")]
        if task.get("priority"):
            context.append(f"priority:{task['priority']}")
        if task.get("assigned_to"):
            context.append(f"assigned_to:{task['assigned_to']}")

        # 統合システム: タスク実行前の処理
        try:
            sys.path.insert(0, str(ROOT / "trinity_workspace" / "systems"))
            from integration_coordinator import IntegrationCoordinator
            coordinator = IntegrationCoordinator()
            before_result = coordinator.before_task_execution(
                task.get("description", ""),
                task.get("title", "")
            )
            if before_result.get("recommendations"):
                log(f"💡 統合システムからの推奨: {', '.join(before_result['recommendations'])}")
        except Exception as e:
            log(f"⚠️ 統合システム前処理エラー: {e}")

        orchestrator = TrinityOrchestrator()
        orchestrator.verbose = False

        log(f"🎯 Task {task_id} のオーケストレーションを開始します (goal={goal})")
        send_notification(f"Task {task_id} 開始: goal={goal}", level="info")
        try:
            result = orchestrator.run(
                goal=goal,
                context=[c for c in context if c],
                budget_turns=task.get("budget_turns", 12),
            )

            # 統合システム: タスク実行後の処理（成功時）
            try:
                if 'coordinator' in locals():
                    coordinator.after_task_execution(
                        task_id,
                        task.get("description", ""),
                        {
                            "status": "success",
                            "assigned_to": task.get("assigned_to"),
                            "result": result
                        }
                    )
            except Exception as e:
                log(f"⚠️ 統合システム後処理エラー: {e}")

        except Exception as exc:  # pragma: no cover
            log(f"❌ Task {task_id} でエラー発生: {exc}")
            send_notification(f"Task {task_id} 失敗: {exc}", level="error")

            # 統合システム: タスク実行後の処理（失敗時）
            try:
                if 'coordinator' in locals():
                    coordinator.after_task_execution(
                        task_id,
                        task.get("description", ""),
                        {
                            "status": "failed",
                            "assigned_to": task.get("assigned_to"),
                            "failed": True,
                            "failure_type": "execution_error",
                            "error_message": str(exc)
                        }
                    )
            except Exception as e:
                log(f"⚠️ 統合システム後処理エラー: {e}")

            automation.update(
                {
                    "in_progress": False,
                    "final_status": "failed",
                    "last_error": str(exc),
                    "last_run_at": datetime.now().isoformat(),
                }
            )
            update_task(
                tasks,
                task_id,
                {
                    "status": "todo",
                    "automation": automation,
                },
            )
            save_tasks(tasks)
            return

        # ticket sync
        ticket_id = result.get("ticket_id")
        ticket_summary = result.get("summary")
        confidence = result.get("confidence")
        final_status = result.get("final_status", "unknown")
        stage = "done"
        history_count = None
        artifacts_count = None

        if ticket_id:
            ticket = self.ticket_manager.get_ticket(ticket_id)
            if ticket:
                status_info = ticket.get("status", {})
                stage = status_info.get("stage", stage)
                history = ticket.get("history", [])
                artifacts = ticket.get("artifacts", [])
                history_count = len(history)
                artifacts_count = len(artifacts)
                # close ticket if orchestrator already closed
                if final_status in {"completed", "failed"} and ticket_id in self.ticket_manager.list_active_tickets():
                    self.ticket_manager.close_ticket(ticket_id, final_status if final_status in {"completed", "failed"} else "completed")

        automation.update(
            {
                "in_progress": False,
                "final_status": final_status,
                "ticket_id": ticket_id,
                "confidence": confidence,
                "last_run_at": datetime.now().isoformat(),
                "summary": ticket_summary,
                "stage": stage,
                "history_count": history_count,
                "artifacts_count": artifacts_count,
            }
        )

        next_status = "done" if final_status == "completed" else "review"
        update_task(
            tasks,
            task_id,
            {
                "status": next_status,
                "automation": automation,
            },
        )
        save_tasks(tasks)
        confidence_msg = f"{confidence:.2f}" if confidence is not None else "n/a"
        if final_status == "completed":
            notify_level = "success"
        elif final_status == "failed":
            notify_level = "error"
        else:
            notify_level = "warning"
        send_notification(
            (
                f"Task {task_id} 結果: status={final_status} "
                f"ticket={ticket_id or 'なし'} stage={stage} confidence={confidence_msg}"
            ),
            level=notify_level,
        )
        log(
            f"✅ Task {task_id} 完了: ticket={ticket_id} "
            f"status={final_status} confidence={confidence_msg}"
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Trinity Orchestrator Task Watcher",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--interval", type=int, default=30, help="監視間隔（秒）")
    parser.add_argument("--once", action="store_true", help="1度だけ実行して終了する")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    watcher = TaskWatcher(interval=args.interval)
    log(f"🔄 Task watcher を起動しました (interval={args.interval}s, run_once={args.once})")

    if args.once:
        watcher.run_once()
        return

    while True:
        watcher.run_once()
        time.sleep(args.interval)


if __name__ == "__main__":
    main()


