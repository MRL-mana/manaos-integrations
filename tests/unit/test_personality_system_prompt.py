from scripts.misc.personality_system import PersonalitySystem
import sys
import types


def test_report_context_keeps_philosophy_sections():
    system = PersonalitySystem()

    result = system.apply_personality_to_prompt(
        "このタスクの進捗を報告してください。",
        context="report",
    )

    assert "【思想（価値観）】" in result
    assert "【判断原則】" in result
    assert "報告時は事実のみを淡々と伝えてください。" in result


def test_conversation_context_with_memory_snippets():
    system = PersonalitySystem()

    result = system.apply_personality_to_prompt(
        "今日は何を優先すべき？",
        context="conversation",
        memory_snippets=["以前は朝に監視チェックを先に実施していた"],
    )

    assert "【思想（価値観）】" in result
    assert "【判断原則】" in result
    assert "【関連記憶（要約）】" in result
    assert "以前は朝に監視チェックを先に実施していた" in result


def test_fetch_memory_snippets_supports_value_field(monkeypatch):
    system = PersonalitySystem()

    class _FakeResponse:
        status_code = 200

        @staticmethod
        def json():
            return {
                "results": [
                    {"value": "Webhookカナリア健全性チェックを最優先する"},
                ]
            }

    class _FakeRequests:
        @staticmethod
        def post(*args, **kwargs):
            return _FakeResponse()

    monkeypatch.setitem(sys.modules, "requests", types.SimpleNamespace(post=_FakeRequests.post))

    snippets = system._fetch_memory_snippets("Webhookカナリア", limit=3)
    assert snippets
    assert "Webhookカナリア健全性チェック" in snippets[0]


def test_fetch_memory_snippets_retries_with_tokenized_query(monkeypatch):
    system = PersonalitySystem()
    called_queries = []

    class _FakeResponse:
        def __init__(self, payload, status_code=200):
            self._payload = payload
            self.status_code = status_code

        def json(self):
            return self._payload

    def _fake_post(*args, **kwargs):
        body = kwargs.get("json") or {}
        query = body.get("query", "")
        called_queries.append(query)

        if query == "運用優先順位 health status":
            return _FakeResponse({"results": []})
        if query == "運用優先順位":
            return _FakeResponse({"results": [{"value": "運用優先順位はhealth/status確認を先に行う"}]})
        return _FakeResponse({"results": []})

    monkeypatch.setitem(sys.modules, "requests", types.SimpleNamespace(post=_fake_post))

    snippets = system._fetch_memory_snippets("運用優先順位 health status", limit=3)
    assert snippets
    assert "運用優先順位" in snippets[0]
    assert called_queries[0] == "運用優先順位 health status"
    assert "運用優先順位" in called_queries
