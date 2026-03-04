#!/usr/bin/env python3
"""
ManaOS アクションキューシステム
衝突を防ぐための順番待ちキューとリソースロック
"""

import json
import uuid
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict
import threading

QUEUE_DIR = Path("/root/actions/queue")
LOCKS_DIR = Path("/root/actions/locks")
MAX_RETRIES = 3
BASE_DELAY = 5  # 秒
TIMEOUT_MINUTES = 30

class ActionQueue:
    """アクションキュー管理"""

    def __init__(self, queue_dir: Path = QUEUE_DIR, locks_dir: Path = LOCKS_DIR):
        self.queue_dir = queue_dir
        self.locks_dir = locks_dir
        self.queue_dir.mkdir(parents=True, exist_ok=True)
        self.locks_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def enqueue(self, action: Dict) -> str:
        """アクションをキューに追加"""
        action_id = str(uuid.uuid4())
        action["id"] = action_id
        action["created_at"] = datetime.now().isoformat()
        action["status"] = "pending"
        action["retries"] = 0

        queue_file = self.queue_dir / f"{action_id}.json"
        with open(queue_file, 'w', encoding='utf-8') as f:
            json.dump(action, f, indent=2, ensure_ascii=False)

        return action_id

    def acquire_lock(self, resource: str, action_id: str, timeout_minutes: int = TIMEOUT_MINUTES) -> bool:
        """リソースロックを取得"""
        # ディレクトリを確実に作成
        self.locks_dir.mkdir(parents=True, exist_ok=True)

        # リソース名に含まれるスラッシュを適切に処理
        safe_resource = resource.replace("/", "_").replace("\\", "_")
        lock_file = self.locks_dir / f"{safe_resource}.lock"

        with self._lock:
            # 既存のロックをチェック
            if lock_file.exists():
                lock_data = json.loads(lock_file.read_text(encoding='utf-8'))
                lock_time = datetime.fromisoformat(lock_data["acquired_at"])

                # タイムアウトチェック
                if datetime.now() - lock_time > timedelta(minutes=timeout_minutes):
                    # タイムアウトしているロックを解放
                    lock_file.unlink()
                else:
                    # まだ有効なロックが存在
                    return False

            # 新しいロックを取得
            lock_data = {
                "resource": resource,
                "action_id": action_id,
                "acquired_at": datetime.now().isoformat(),
                "timeout_minutes": timeout_minutes
            }
            lock_file.write_text(json.dumps(lock_data, indent=2, ensure_ascii=False), encoding='utf-8')
            return True

    def release_lock(self, resource: str):
        """リソースロックを解放"""
        lock_file = self.locks_dir / f"{resource}.lock"
        if lock_file.exists():
            lock_file.unlink()

    def process_queue(self, processor_callback):
        """キューを処理"""
        queue_files = sorted(self.queue_dir.glob("*.json"))

        for queue_file in queue_files:
            try:
                action = json.loads(queue_file.read_text(encoding='utf-8'))

                # リソースロックを取得
                resource = action.get("resource", "default")
                if not self.acquire_lock(resource, action["id"]):
                    continue  # ロック取得失敗、次へ

                try:
                    # アクションを処理
                    result = processor_callback(action)

                    # 成功
                    action["status"] = "completed"
                    action["completed_at"] = datetime.now().isoformat()
                    action["result"] = result

                except Exception as e:
                    # 失敗
                    action["retries"] += 1
                    action["last_error"] = str(e)

                    if action["retries"] >= MAX_RETRIES:
                        action["status"] = "failed"
                        action["failed_at"] = datetime.now().isoformat()
                        # 人へ通知（ここではログに記録）
                        print(f"⚠️  Action {action['id']} failed after {MAX_RETRIES} retries. Manual intervention required.")
                    else:
                        action["status"] = "pending"
                        # 指数バックオフ
                        delay = BASE_DELAY * (2 ** action["retries"])
                        action["retry_after"] = (datetime.now() + timedelta(seconds=delay)).isoformat()

                finally:
                    # ロックを解放
                    self.release_lock(resource)

                    # キューファイルを更新
                    queue_file.write_text(json.dumps(action, indent=2, ensure_ascii=False), encoding='utf-8')

                    # 完了したアクションをアーカイブ
                    if action["status"] in ["completed", "failed"]:
                        archive_dir = self.queue_dir / "archive"
                        archive_dir.mkdir(exist_ok=True)
                        queue_file.rename(archive_dir / queue_file.name)

            except Exception as e:
                print(f"⚠️  Error processing {queue_file}: {e}")

    def get_queue_status(self) -> Dict:
        """キュー状態を取得"""
        queue_files = list(self.queue_dir.glob("*.json"))
        lock_files = list(self.locks_dir.glob("*.lock"))

        pending = 0
        processing = 0
        failed = 0

        for queue_file in queue_files:
            try:
                action = json.loads(queue_file.read_text(encoding='utf-8'))
                status = action.get("status", "unknown")
                if status == "pending":
                    pending += 1
                elif status == "processing":
                    processing += 1
                elif status == "failed":
                    failed += 1
            except IOError:
                pass

        return {
            "total": len(queue_files),
            "pending": pending,
            "processing": processing,
            "failed": failed,
            "locks": len(lock_files)
        }

def main():
    """テスト用"""
    queue = ActionQueue()

    # テストアクションを追加
    test_action = {
        "agent": "trinity",
        "resource": "adapters/model_v1",
        "intent": "update_learning_adapter",
        "data": {"learning_rate": 0.001}
    }

    action_id = queue.enqueue(test_action)
    print(f"✅ Enqueued action: {action_id}")

    # キューステータスを表示
    status = queue.get_queue_status()
    print(f"📊 Queue status: {status}")

if __name__ == "__main__":
    main()

