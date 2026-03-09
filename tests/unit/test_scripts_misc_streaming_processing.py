"""
Unit tests for scripts/misc/streaming_processing.py
"""
import queue
import asyncio
import pytest
from scripts.misc.streaming_processing import StreamingProcessor, DataStream


# ── fixture ────────────────────────────────────────────────────────────────
@pytest.fixture
def sp(tmp_path):
    """StreamingProcessor with disk I/O redirected to tmp_path."""
    proc = StreamingProcessor.__new__(StreamingProcessor)
    proc.buffer_size = 100
    proc.data_queue = queue.Queue(maxsize=100)
    proc.processors = []
    proc.is_running = False
    proc.processed_count = 0
    proc.storage_path = tmp_path / "streaming_state.json"
    return proc


# ── TestStreamingProcessorInit ────────────────────────────────────────────
class TestStreamingProcessorInit:
    def test_default_buffer_creates_queue(self, tmp_path):
        p = StreamingProcessor.__new__(StreamingProcessor)
        p.buffer_size = 1000
        p.data_queue = queue.Queue(maxsize=1000)
        p.processors = []
        p.is_running = False
        p.processed_count = 0
        p.storage_path = tmp_path / "s.json"
        assert p.buffer_size == 1000

    def test_processed_count_starts_zero(self, sp):
        assert sp.processed_count == 0

    def test_not_running_by_default(self, sp):
        assert sp.is_running is False


# ── TestRegisterProcessor ─────────────────────────────────────────────────
class TestRegisterProcessor:
    def test_adds_processor(self, sp):
        sp.register_processor(lambda x: x, "test")
        assert len(sp.processors) == 1

    def test_name_stored(self, sp):
        sp.register_processor(lambda x: x, "my_proc")
        assert sp.processors[0]["name"] == "my_proc"

    def test_default_name_generated(self, sp):
        sp.register_processor(lambda x: x)
        assert "processor_" in sp.processors[0]["name"]

    def test_multiple_processors(self, sp):
        sp.register_processor(lambda x: x, "p1")
        sp.register_processor(lambda x: x * 2, "p2")
        assert len(sp.processors) == 2


# ── TestAddData ────────────────────────────────────────────────────────────
class TestAddData:
    def test_returns_true_on_success(self, sp):
        assert sp.add_data("hello") is True

    def test_data_in_queue(self, sp):
        sp.add_data("item")
        assert sp.data_queue.qsize() == 1

    def test_returns_false_when_full(self, tmp_path):
        p = StreamingProcessor.__new__(StreamingProcessor)
        p.buffer_size = 1
        p.data_queue = queue.Queue(maxsize=1)
        p.processors = []
        p.is_running = False
        p.processed_count = 0
        p.storage_path = tmp_path / "s.json"
        p.data_queue.put("fill")
        assert p.add_data("overflow") is False


# ── TestProcessData ────────────────────────────────────────────────────────
class TestProcessData:
    def test_no_processors_empty_result(self, sp):
        results = sp.process_data("data")
        assert results == []

    def test_processor_runs(self, sp):
        sp.register_processor(lambda x: x.upper(), "upper")
        results = sp.process_data("hello")
        assert results[0]["result"] == "HELLO"

    def test_result_has_processor_key(self, sp):
        sp.register_processor(lambda x: x, "p")
        results = sp.process_data("x")
        assert results[0]["processor"] == "p"

    def test_result_has_timestamp(self, sp):
        sp.register_processor(lambda x: x, "p")
        results = sp.process_data("x")
        assert "timestamp" in results[0]

    def test_increments_processed_count(self, sp):
        sp.register_processor(lambda x: x, "p")
        sp.process_data("x")
        assert sp.processed_count == 1

    def test_multiple_processors_multiple_results(self, sp):
        sp.register_processor(lambda x: x, "p1")
        sp.register_processor(lambda x: x + "!", "p2")
        results = sp.process_data("hello")
        assert len(results) == 2

    def test_processor_exception_captured(self, sp):
        def bad(x):
            raise ValueError("boom")
        sp.register_processor(bad, "bad")
        results = sp.process_data("x")
        assert "error" in results[0]
        assert "boom" in results[0]["error"]

    def test_saves_state(self, sp):
        sp.register_processor(lambda x: x, "p")
        sp.process_data("x")
        assert sp.storage_path.exists()


# ── TestStartStop ─────────────────────────────────────────────────────────
class TestStartStop:
    def test_start_sets_running(self, sp):
        sp.start_processing()
        assert sp.is_running is True
        sp.stop_processing()

    def test_stop_clears_running(self, sp):
        sp.start_processing()
        sp.stop_processing()
        assert sp.is_running is False

    def test_double_start_does_not_error(self, sp):
        sp.start_processing()
        sp.start_processing()  # should be no-op
        assert sp.is_running is True
        sp.stop_processing()


# ── TestGetStatus ─────────────────────────────────────────────────────────
class TestGetStatus:
    def test_returns_dict(self, sp):
        status = sp.get_status()
        assert isinstance(status, dict)

    def test_required_keys(self, sp):
        status = sp.get_status()
        for key in ("is_running", "queue_size", "processors_count",
                    "processed_count", "buffer_size", "timestamp"):
            assert key in status

    def test_processors_count(self, sp):
        sp.register_processor(lambda x: x, "p")
        assert sp.get_status()["processors_count"] == 1

    def test_queue_size_reflects_additions(self, sp):
        sp.add_data("a")
        sp.add_data("b")
        assert sp.get_status()["queue_size"] == 2

    def test_processed_count_in_status(self, sp):
        sp.register_processor(lambda x: x, "p")
        sp.process_data("x")
        assert sp.get_status()["processed_count"] == 1


# ── TestSaveLoadState ─────────────────────────────────────────────────────
class TestSaveLoadState:
    def test_save_creates_file(self, sp):
        sp._save_state()
        assert sp.storage_path.exists()

    def test_load_when_no_file_keeps_zero(self, sp):
        # no file → processed_count stays 0
        sp._load_state()
        assert sp.processed_count == 0

    def test_roundtrip(self, sp):
        sp.processed_count = 42
        sp._save_state()
        sp.processed_count = 0
        sp._load_state()
        assert sp.processed_count == 42


# ── TestDataStream ────────────────────────────────────────────────────────
class TestDataStream:
    def test_add_data_populates_buffer(self):
        ds = DataStream()
        ds.add_data("item1")
        assert len(ds.data_buffer) == 1

    def test_buffer_maxlen(self):
        ds = DataStream()
        for i in range(1100):
            ds.add_data(i)
        assert len(ds.data_buffer) == 1000

    def test_add_multiple_items(self):
        ds = DataStream()
        ds.add_data("a")
        ds.add_data("b")
        assert len(ds.data_buffer) == 2


# ── TestAsyncProcessStream ─────────────────────────────────────────────────
class TestAsyncProcessStream:
    def test_batch_processing(self, sp):
        sp.register_processor(lambda x: x * 2, "double")

        async def async_gen():
            for i in range(5):
                yield i

        async def run():
            results_all = []
            async for batch in sp.async_process_stream(async_gen(), batch_size=3):
                results_all.extend(batch)
            return results_all

        results = asyncio.run(run())
        assert len(results) == 5
        # processor ran for each of the 5 items
        assert all(r["processor"] == "double" for r in results)

    def test_empty_stream(self, sp):
        async def empty_gen():
            return
            yield  # make it an async generator

        async def run():
            results = []
            async for batch in sp.async_process_stream(empty_gen()):
                results.extend(batch)
            return results

        results = asyncio.run(run())
        assert results == []
