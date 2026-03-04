"""
Unit Tests — image_generation_service.queue
=============================================
SQLite ジョブキューの単体テスト。
"""

import asyncio
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

_tmp_dir = tempfile.mkdtemp()
os.environ["QUEUE_DB_PATH"] = os.path.join(_tmp_dir, "test_queue.db")

from image_generation_service.queue import JobQueue, QueueState


def _run(coro):
    return asyncio.run(coro)


@pytest.fixture(autouse=True)
def fresh_db(tmp_path):
    import image_generation_service.queue as queue_mod
    db_path = tmp_path / "queue.db"
    queue_mod._DB_PATH = db_path
    return db_path


class TestJobQueue:

    def test_enqueue_dequeue(self, fresh_db):
        q = JobQueue()
        _run(q.enqueue("job-1", priority=1, payload={"prompt": "cat"}))
        job = _run(q.dequeue())
        assert job is not None
        assert job["job_id"] == "job-1"
        assert job["payload"]["prompt"] == "cat"

    def test_priority_ordering(self, fresh_db):
        """Enterprise (3) > Pro (2) > Free (1)"""
        q = JobQueue()
        _run(q.enqueue("free-job", priority=1))
        _run(q.enqueue("ent-job", priority=3))
        _run(q.enqueue("pro-job", priority=2))

        # priority DESC → enterprise が先
        job1 = _run(q.dequeue())
        assert job1["job_id"] == "ent-job"
        _run(q.complete("ent-job"))

        job2 = _run(q.dequeue())
        assert job2["job_id"] == "pro-job"
        _run(q.complete("pro-job"))

        job3 = _run(q.dequeue())
        assert job3["job_id"] == "free-job"

    def test_max_concurrent_limit(self, fresh_db):
        """同時処理制限: 1個処理中は次を取れない"""
        q = JobQueue()
        _run(q.enqueue("job-a", priority=1))
        _run(q.enqueue("job-b", priority=1))

        job1 = _run(q.dequeue())
        assert job1["job_id"] == "job-a"

        # 処理中が 1 → _MAX_CONCURRENT=1 のため None
        job2 = _run(q.dequeue())
        assert job2 is None

        # complete → 取れるようになる
        _run(q.complete("job-a"))
        job2 = _run(q.dequeue())
        assert job2["job_id"] == "job-b"

    def test_complete(self, fresh_db):
        q = JobQueue()
        _run(q.enqueue("job-c", priority=1))
        _run(q.dequeue())
        _run(q.complete("job-c", result={"url": "/images/test.png"}))
        stats = _run(q.get_stats())
        assert stats["completed"] == 1

    def test_fail(self, fresh_db):
        q = JobQueue()
        _run(q.enqueue("job-d", priority=1))
        _run(q.dequeue())
        _run(q.fail("job-d", "ComfyUI down"))
        stats = _run(q.get_stats())
        assert stats["failed"] == 1

    def test_empty_dequeue(self, fresh_db):
        q = JobQueue()
        job = _run(q.dequeue())
        assert job is None

    def test_queue_length(self, fresh_db):
        q = JobQueue()
        _run(q.enqueue("j1", priority=1))
        _run(q.enqueue("j2", priority=2))
        _run(q.enqueue("j3", priority=3))
        length = _run(q.get_queue_length())
        assert length == 3

    def test_get_position(self, fresh_db):
        q = JobQueue()
        _run(q.enqueue("low", priority=1))
        _run(q.enqueue("high", priority=3))

        # high (priority 3) は先頭 → position 0
        pos = _run(q.get_position("high"))
        assert pos == 0

        # low (priority 1) は 2番目 → position 1
        pos = _run(q.get_position("low"))
        assert pos == 1

    def test_get_stats(self, fresh_db):
        q = JobQueue()
        _run(q.enqueue("s1", priority=1))
        _run(q.enqueue("s2", priority=2))

        stats = _run(q.get_stats())
        assert stats["total_jobs"] == 2
        assert stats["waiting"] == 2
        assert stats["max_concurrent"] == 1

    def test_processing_count(self, fresh_db):
        q = JobQueue()
        _run(q.enqueue("p1", priority=1))
        assert _run(q.get_processing_count()) == 0
        _run(q.dequeue())
        assert _run(q.get_processing_count()) == 1
        _run(q.complete("p1"))
        assert _run(q.get_processing_count()) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
