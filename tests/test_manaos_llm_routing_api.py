import sys
from pathlib import Path


repo_root = str(Path(__file__).resolve().parents[1])
misc_root = str(Path(__file__).resolve().parents[1] / "scripts" / "misc")
llm_root = str(Path(__file__).resolve().parents[1] / "llm")
if misc_root not in sys.path:
    sys.path.insert(0, misc_root)
if llm_root not in sys.path:
    sys.path.insert(0, llm_root)
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

import manaos_llm_routing_api as api  # noqa: E402


def test_chat_completions_passes_generation_options(monkeypatch):
    captured = {}

    def fake_route(prompt, context, preferences):
        captured["prompt"] = prompt
        captured["context"] = context
        captured["preferences"] = preferences
        return {
            "success": True,
            "model": "llama3-uncensored:latest",
            "response": "ok",
        }

    monkeypatch.setattr(api.router, "route", fake_route)  # type: ignore[attr-defined]

    with api.app.test_client() as client:  # type: ignore[attr-defined]
        response = client.post(
            "/v1/chat/completions",
            json={
                "model": "auto-local",
                "messages": [{"role": "user", "content": "hello"}],
                "temperature": 0.15,
                "max_tokens": 123,
                "top_p": 0.8,
                "stop": ["END"],
                "timeout_sec": 91,
            },
        )

    assert response.status_code == 200
    generation = captured["context"]["_generation"]
    assert generation["temperature"] == 0.15
    assert generation["max_tokens"] == 123
    assert generation["top_p"] == 0.8
    assert generation["stop"] == ["END"]
    assert generation["timeout_sec"] == 91


def test_chat_completions_applies_max_tokens_soft_cap(monkeypatch):
    def fake_route(_prompt, _context, _preferences):
        return {
            "success": True,
            "model": "llama3-uncensored:latest",
            "response": "x" * 1000,
        }

    monkeypatch.setattr(api.router, "route", fake_route)  # type: ignore[attr-defined]

    with api.app.test_client() as client:  # type: ignore[attr-defined]
        response = client.post(
            "/v1/chat/completions",
            json={
                "model": "auto-local",
                "messages": [{"role": "user", "content": "hello"}],
                "max_tokens": 10,
            },
        )

    assert response.status_code == 200
    content = response.get_json()["choices"][0]["message"]["content"]
    assert len(content) <= 60


def test_chat_completions_streaming_returns_done(monkeypatch):
    def fake_route(_prompt, _context, _preferences):
        return {
            "success": True,
            "model": "llama3-uncensored:latest",
            "response": "stream-ok",
        }

    monkeypatch.setattr(api.router, "route", fake_route)  # type: ignore[attr-defined]

    with api.app.test_client() as client:  # type: ignore[attr-defined]
        response = client.post(
            "/v1/chat/completions",
            json={
                "model": "auto-local",
                "messages": [{"role": "user", "content": "hello"}],
                "stream": True,
            },
        )

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "data: [DONE]" in body
