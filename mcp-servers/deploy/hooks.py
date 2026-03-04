"""Convenience emitters for integrating MachiOS loops with the feed server."""
from __future__ import annotations

import json
import logging
import os
import queue
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import requests

LOGGER = logging.getLogger("machi_reflection_feed.hooks")

_DEFAULT_OUTBOX = Path(os.getenv("MACHI_FEED_OUTBOX", "/var/lib/machi/feed_outbox.jsonl"))


def _default_base_url() -> str:
    return os.getenv("MACHI_FEED_BASE_URL", "http://127.0.0.1:5057")


def _default_token() -> Optional[str]:
    return os.getenv("MACHI_FEED_TOKEN")


class ReflectionEmitter:
    """HTTP-based emitter that forwards JSON payloads to the feed server.

    The emitter buffers payloads in-memory and flushes them asynchronously.
    When the HTTP endpoint is unreachable, payloads are persisted to a JSONL outbox.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        token: Optional[str] = None,
        timeout: float = 5.0,
        *,
        max_queue_size: int = 1024,
        outbox_path: Optional[Path] = None,
    ) -> None:
        self.base_url = base_url or _default_base_url()
        self.token = token or _default_token()
        self.timeout = timeout
        self.outbox_path = outbox_path or _DEFAULT_OUTBOX
        self._queue: "queue.Queue[Tuple[str, Dict[str, Any]]]" = queue.Queue(maxsize=max_queue_size)
        self._session = requests.Session()
        self._worker_thread = threading.Thread(target=self._worker, name="ReflectionEmitter", daemon=True)
        self._worker_thread.start()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def emit(self, topic: str, payload: Dict[str, Any]) -> None:
        try:
            self._queue.put_nowait((topic, payload))
        except queue.Full:
            LOGGER.warning("Outbox queue is full, persisting %s payload", topic)
            self._persist_outbox(topic, payload)

    def emit_decision_log(self, payload: Dict[str, Any]) -> None:
        self.emit("decision_log", payload)

    def emit_loop_eval(self, payload: Dict[str, Any]) -> None:
        self.emit("loop_eval", payload)

    def emit_future_intent(self, payload: Dict[str, Any]) -> None:
        self.emit("future_intents", payload)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def _worker(self) -> None:
        while True:
            topic, payload = self._queue.get()
            try:
                if not self._send_with_retry(topic, payload):
                    self._persist_outbox(topic, payload)
            finally:
                self._queue.task_done()

    def _send_with_retry(self, topic: str, payload: Dict[str, Any]) -> bool:
        endpoint = f"{self.base_url.rstrip('/')}/ingest/{topic}"
        backoff = 0.5
        for attempt in range(6):
            try:
                response = self._session.post(
                    endpoint,
                    headers=self._headers(),
                    json=payload,
                    timeout=self.timeout,
                )
                if response.status_code < 400:
                    return True
                LOGGER.warning(
                    "Feed ingest returned %s for %s: %s",
                    response.status_code,
                    topic,
                    response.text,
                )
            except Exception as exc:  # pragma: no cover - network failure path
                LOGGER.warning("Error emitting %s payload (attempt %s): %s", topic, attempt + 1, exc)
            time.sleep(backoff)
            backoff = min(backoff * 2, 8.0)
        return False

    def _persist_outbox(self, topic: str, payload: Dict[str, Any]) -> None:
        try:
            self.outbox_path.parent.mkdir(parents=True, exist_ok=True)
            record = {
                "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "topic": topic,
                "payload": payload,
            }
            with self.outbox_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        except Exception as exc:  # pragma: no cover - disk failure path
            LOGGER.error("Failed to write Reflection Feed outbox: %s", exc)


_default_emitter = ReflectionEmitter()


def configure_emitter(
    base_url: Optional[str] = None,
    token: Optional[str] = None,
    timeout: float = 5.0,
    *,
    max_queue_size: int = 1024,
    outbox_path: Optional[str] = None,
) -> None:
    """Override emitter settings at runtime."""

    global _default_emitter
    resolved_outbox = Path(outbox_path) if outbox_path else None
    _default_emitter = ReflectionEmitter(
        base_url=base_url,
        token=token,
        timeout=timeout,
        max_queue_size=max_queue_size,
        outbox_path=resolved_outbox,
    )


def emit_decision_log(payload: Dict[str, Any]) -> None:
    _default_emitter.emit_decision_log(payload)


def emit_loop_eval(payload: Dict[str, Any]) -> None:
    _default_emitter.emit_loop_eval(payload)


def emit_future_intent(payload: Dict[str, Any]) -> None:
    _default_emitter.emit_future_intent(payload)
