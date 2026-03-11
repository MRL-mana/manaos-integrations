"""
タスク実行制御（タイムアウト、並行実行数制限、リトライ）
"""

import os
import asyncio
from typing import Dict, Any, Callable
from concurrent.futures import ThreadPoolExecutor
import logging

logger = logging.getLogger(__name__)

# 設定
MAX_CONCURRENT_TASKS = int(os.getenv("AISIM_MAX_CONCURRENT_TASKS", "5"))
TASK_TIMEOUT_SECONDS = float(os.getenv("AISIM_TASK_TIMEOUT_SECONDS", "300"))  # 5分
MAX_RETRY_ATTEMPTS = int(os.getenv("AISIM_MAX_RETRY_ATTEMPTS", "3"))
RETRY_DELAY_SECONDS = float(os.getenv("AISIM_RETRY_DELAY_SECONDS", "5"))

# 実行中のタスク数カウンター
running_tasks = 0
running_tasks_lock = None  # 遅延初期化

def _get_lock():
    """Lockを遅延初期化"""
    global running_tasks_lock
    if running_tasks_lock is None:
        try:
            running_tasks_lock = asyncio.Lock()
        except RuntimeError:
            # イベントループが存在しない場合は新規作成
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            running_tasks_lock = asyncio.Lock()
    return running_tasks_lock

async def execute_task_with_control(
    task_name: str,
    parameters: Dict[str, Any],
    task_func: Callable[[str, Dict[str, Any]], Dict[str, Any]],
    task_id: str
) -> Dict[str, Any]:
    """タスク実行（タイムアウト、並行実行数制限、リトライ対応）"""
    global running_tasks

    # Lock取得
    lock = _get_lock()

    # 並行実行数チェック
    async with lock:
        if running_tasks >= MAX_CONCURRENT_TASKS:
            raise RuntimeError(
                f"Maximum concurrent tasks ({MAX_CONCURRENT_TASKS}) reached. "
                f"Please wait for running tasks to complete."
            )
        running_tasks += 1

    try:
        # リトライループ
        last_error = None
        for attempt in range(1, MAX_RETRY_ATTEMPTS + 1):
            try:
                # タイムアウト付きで実行
                loop = asyncio.get_running_loop()
                executor = ThreadPoolExecutor(max_workers=1)

                try:
                    result = await asyncio.wait_for(
                        loop.run_in_executor(
                            executor,
                            lambda: task_func(task_name, parameters)
                        ),
                        timeout=TASK_TIMEOUT_SECONDS
                    )
                    executor.shutdown(wait=False)
                    return result

                except asyncio.TimeoutError:
                    executor.shutdown(wait=False)
                    raise TimeoutError(
                        f"Task {task_name} (ID: {task_id}) timed out after {TASK_TIMEOUT_SECONDS} seconds"
                    )

            except (TimeoutError, Exception) as e:
                last_error = e
                if attempt < MAX_RETRY_ATTEMPTS:
                    logger.warning(
                        f"Task {task_name} (ID: {task_id}) failed (attempt {attempt}/{MAX_RETRY_ATTEMPTS}): {e}. "
                        f"Retrying in {RETRY_DELAY_SECONDS} seconds..."
                    )
                    await asyncio.sleep(RETRY_DELAY_SECONDS)
                else:
                    logger.error(
                        f"Task {task_name} (ID: {task_id}) failed after {MAX_RETRY_ATTEMPTS} attempts: {e}"
                    )
                    raise last_error

        # ここには到達しないはず
        raise RuntimeError("Unexpected retry loop exit")

    finally:
        lock = _get_lock()
        async with lock:
            running_tasks -= 1

def get_running_tasks_count() -> int:
    """現在実行中のタスク数を取得"""
    return running_tasks

def get_max_concurrent_tasks() -> int:
    """最大並行実行数を取得"""
    return MAX_CONCURRENT_TASKS

