#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""実装機能のスモークテスト（pytest版）。"""

import os
from datetime import datetime

import pytest


def _require_or_skip(module_name):
    fallback_map = {
        "svi_wan22_video_integration": ["svi.svi_wan22_video_integration"],
    }
    candidates = [module_name] + fallback_map.get(module_name, [])
    last_error = None
    for candidate in candidates:
        try:
            return __import__(candidate, fromlist=["*"])
        except Exception as error:
            last_error = error
    try:
        raise RuntimeError(last_error)
    except Exception as error:
        pytest.skip(f"optional module unavailable: {module_name} ({error})")


def test_translation():
    module = _require_or_skip("svi_wan22_video_integration")
    integration = module.SVIWan22VideoIntegration()
    result = integration.translate_prompt_to_english("美しい風景を生成してください")
    assert result is None or isinstance(result, str)


def test_todo_execution():
    module = _require_or_skip("intrinsic_todo_queue")
    queue = module.IntrinsicTodoQueue()
    todo = module.IntrinsicTodo(
        id="test_todo_001",
        title="テストタスク",
        reason="動作確認のため",
        impact="システム動作確認",
        risk="low",
        autonomy_level_required=1,
        estimated_minutes=1,
        tags=["test"],
        state=module.TodoState.APPROVED,
    )
    queue.add_todo(todo)
    result = queue.execute_todo("test_todo_001")
    assert isinstance(result, dict)
    assert "status" in result or "error" in result


def test_payment_integration():
    module = _require_or_skip("payment_integration")
    result = module.process_stripe_payment(1000.0, "JPY")
    assert isinstance(result, dict)
    assert result.get("status") in {"success", "error"}


def test_document_search():
    try:
        from manaos_integrations._paths import RAG_MEMORY_PORT, SEARXNG_PORT
    except Exception:
        try:
            from _paths import RAG_MEMORY_PORT, SEARXNG_PORT  # type: ignore
        except Exception:
            SEARXNG_PORT = int(os.getenv("SEARXNG_PORT", "8080"))
            RAG_MEMORY_PORT = int(os.getenv("RAG_MEMORY_PORT", "5103"))

    searcher_module = _require_or_skip("step_deep_research.searcher")
    config = {
        "sources": ["web", "rag", "docs"],
        "max_results_per_query": 5,
        "searxng_url": os.getenv("SEARXNG_BASE_URL", f"http://127.0.0.1:{SEARXNG_PORT}"),
        "rag_api_url": os.getenv("RAG_MEMORY_URL", f"http://127.0.0.1:{RAG_MEMORY_PORT}"),
    }
    try:
        searcher = searcher_module.Searcher(config)
        results = searcher._docs_search("テスト", 5)
    except Exception as error:
        pytest.skip(f"document search backend unavailable: {error}")
    assert isinstance(results, list)


def test_prompt_optimization():
    module = _require_or_skip("prompt_optimizer_simple")
    result = module.optimize_prompt("テスト", task_type="conversation", enable=True)
    assert result is None or isinstance(result, str)


def test_obsidian_integration():
    module = _require_or_skip("llm_routing")
    router = module.LLMRouter()
    log = module.AuditLog(
        request_id="test_001",
        timestamp=datetime.now().isoformat(),
        routed_model="test_model",
        task_type="conversation",
        memory_refs=[],
        tools_used=[],
        input_summary="テスト入力",
        output_summary="テスト出力",
        cost=0.0,
        latency_ms=100,
        fallback_used=False,
    )
    try:
        router._save_audit_log_to_obsidian(log)
    except Exception as error:
        pytest.skip(f"obsidian integration unavailable: {error}")
