"""Notification helper for MachiOS Reflection Feed expressive mode."""
from __future__ import annotations

import json
import logging
import os
import random
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Dict, Optional, TYPE_CHECKING, Any, Iterable

import requests  # type: ignore[import]

if TYPE_CHECKING:
    from .schemas import CommentaryEntry, DecisionLog, FutureIntent, LoopEval

from .metrics import NOTIFICATION_DELIVERED, NOTIFICATION_FAILURE

TEMPLATE_ENV_KEY = "MACHI_FEED_NOTIFICATION_TEMPLATE"
LOG_PATH_ENV_KEY = "MACHI_FEED_NOTIFICATION_LOG_PATH"
DEFAULT_TEMPLATE_PATH = Path.home() / ".mana_vault" / \
    "machi_feed_notifications.json"
logger = logging.getLogger(__name__)
_registered_handlers: set[Path] = set()

DEFAULT_TEMPLATES: Dict[str, str] = {
    "decision": (
        "🧠 *New Decision*\n"
        "Task: `{task_id}`\n"
        "Metric: {metric}\n"
        "Priority: {priority}\n"
        "{tradeoffs}"
    ),
    "future": (
        "🔮 *Future Intent*\n"
        "Intent: {intent}{confidence}\n"
        "Dependencies: {dependencies}\n"
        "{eta}"
    ),
    "reflection": (
        "⚠️ *Reflection Alert*\n"
        "Task: {task_id}\n"
        "Issues: {issues}"
    ),
    "commentary": (
        "💭 *{channel}*\n"
        "{message}\n"
        "{metadata}"
    ),
    "commentary_digest": (
        "🗣️ *Commentary Digest*\n"
        "⏱️ 過去{span_minutes}分 / {count}件\n"
        "{summary}"
    ),
}


def load_templates() -> Dict[str, str]:
    """Load notification templates from disk if available."""
    candidate = os.getenv(TEMPLATE_ENV_KEY)
    if candidate:
        path = Path(candidate)
    else:
        path = DEFAULT_TEMPLATE_PATH
    if path.is_file():
        try:
            with path.open(encoding="utf-8") as fp:
                data = json.load(fp)
                if isinstance(data, dict):
                    merged = DEFAULT_TEMPLATES.copy()
                    merged.update({k: str(v) for k, v in data.items()})
                    return merged
        except Exception as exc:
            logger.warning(
                "Failed to load notification templates from %s: %s", path, exc)
    return DEFAULT_TEMPLATES.copy()


@dataclass
class NotificationChannel:
    slack_webhook: Optional[str]
    line_token: Optional[str]

    def has_targets(self) -> bool:
        return bool(self.slack_webhook or self.line_token)


class NotificationManager:
    """Send compact summaries to Slack / LINE when expressive mode is active."""

    def __init__(
        self,
        enabled: bool,
        channel: NotificationChannel,
        templates: Dict[str, str],
        *,
        dry_run: bool = False,
        digest_interval: float = 300.0,
        digest_size: int = 5,
        max_retries: int = 2,
        backoff_base: float = 1.0,
        backoff_cap: float = 30.0,
        backoff_jitter: float = 0.25,
        request_timeout: float = 5.0,
    ) -> None:
        self.logger = logging.getLogger(__name__)
        has_targets = channel.has_targets()
        self._has_targets = has_targets
        self.enabled = enabled and (has_targets or dry_run)
        self.channel = channel
        self.templates = templates
        self.session = requests.Session()
        self._commentary_buffer: list[dict[str, str]] = []
        self._last_commentary_digest: float = 0.0
        self._commentary_interval = digest_interval  # seconds
        self._commentary_digest_size = max(1, digest_size)
        self.dry_run = dry_run
        self._dry_run_log: list[str] = []
        if dry_run and enabled and not has_targets:
            # Dry-run still considered enabled for logging/metrics
            self.logger.info(
                "Notification dry-run mode active (no external dispatch).")
        self._max_retries = max(0, int(max_retries))
        self._backoff_base = max(0.1, float(backoff_base))
        self._backoff_cap = max(self._backoff_base, float(backoff_cap))
        self._backoff_jitter = min(max(0.0, float(backoff_jitter)), 1.0)
        self._request_timeout = max(0.5, float(request_timeout))

    @classmethod
    def from_env(cls, mode: str) -> "NotificationManager":
        enabled = mode.lower() == "expressive"
        channel = NotificationChannel(
            slack_webhook=os.getenv("MACHI_FEED_SLACK_WEBHOOK"),
            line_token=os.getenv("MACHI_FEED_LINE_TOKEN"),
        )
        templates = load_templates()
        dry_run_raw = os.getenv("MACHI_FEED_NOTIFICATION_DRY_RUN", "").lower()
        dry_run = dry_run_raw in {"1", "true", "yes", "on"}
        interval_raw = os.getenv("MACHI_FEED_COMMENTARY_INTERVAL")
        digest_interval = cls._parse_float(
            interval_raw, default=300.0, minimum=30.0)
        digest_size_raw = os.getenv("MACHI_FEED_COMMENTARY_DIGEST_SIZE")
        digest_size = cls._parse_int(digest_size_raw, default=5, minimum=1)
        max_retries = cls._parse_int(
            os.getenv("MACHI_FEED_NOTIFICATION_MAX_RETRIES"),
            default=2,
            minimum=0,
        )
        backoff_base = cls._parse_float(
            os.getenv("MACHI_FEED_NOTIFICATION_RETRY_BASE"),
            default=1.0,
            minimum=0.1,
        )
        backoff_cap = cls._parse_float(
            os.getenv("MACHI_FEED_NOTIFICATION_RETRY_CAP"),
            default=30.0,
            minimum=backoff_base,
        )
        backoff_jitter = cls._parse_float(
            os.getenv("MACHI_FEED_NOTIFICATION_RETRY_JITTER"),
            default=0.25,
            minimum=0.0,
        )
        request_timeout = cls._parse_float(
            os.getenv("MACHI_FEED_NOTIFICATION_TIMEOUT"),
            default=5.0,
            minimum=0.5,
        )
        log_path_raw = os.getenv(LOG_PATH_ENV_KEY)
        if log_path_raw:
            cls._ensure_file_handler(Path(log_path_raw))
        return cls(
            enabled,
            channel,
            templates,
            dry_run=dry_run,
            digest_interval=digest_interval,
            digest_size=digest_size,
            max_retries=max_retries,
            backoff_base=backoff_base,
            backoff_cap=backoff_cap,
            backoff_jitter=backoff_jitter,
            request_timeout=request_timeout,
        )

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def notify_decision(self, decision: DecisionLog) -> None:
        if not self.enabled:
            return
        tradeoffs = ""
        if decision.trade_offs:
            tradeoffs = "Trade-offs: " + ", ".join(decision.trade_offs)
        message = self._render(
            "decision",
            task_id=getattr(decision.selected, "task_id", "unknown"),
            metric=decision.selected_metric or "n/a",
            priority=self._format_vector(decision.priority_vector),
            tradeoffs=tradeoffs,
        )
        self._dispatch(message, template_key="decision")

    def notify_future_intent(self, intent: FutureIntent) -> None:
        if not self.enabled:
            return
        confidence = ""
        if intent.confidence is not None:
            confidence = f" ({intent.confidence*100:.0f}% confidence)"
        eta_line = ""
        if intent.eta_hint:
            eta_line = f"ETA: {intent.eta_hint}"
        message = self._render(
            "future",
            intent=intent.intent,
            confidence=confidence,
            dependencies=", ".join(intent.dependencies) or "none",
            eta=eta_line,
        )
        self._dispatch(message, template_key="future")

    def notify_reflection(self, loop_eval: LoopEval) -> None:
        if not self.enabled:
            return
        issues = loop_eval.self_eval.get("issues")
        if not issues:
            return
        issues_text = ", ".join(issues) if isinstance(
            issues, list) else str(issues)
        inputs = loop_eval.inputs or {}
        message = (
            "⚠️ *Reflection Alert*\n"
            f"Task: {inputs.get('task_id', 'unknown')}\n"
            f"Issues: {issues_text}"
        )
        self._dispatch(message, template_key="reflection")

    def notify_commentary(self, entry: CommentaryEntry) -> None:
        if not self.enabled:
            return
        metadata = ""
        highlight = ""
        if entry.metadata:
            try:
                metadata_obj = entry.metadata
                metadata = json.dumps(metadata_obj, ensure_ascii=False)
            except Exception:
                metadata_obj = None
                metadata = str(entry.metadata)
            else:
                highlight = self._build_commentary_highlight(metadata_obj)
            metadata = f"meta: {metadata}"
        message = self._render(
            "commentary",
            channel=entry.channel or "thought",
            message=self._compose_commentary_message(entry.message, highlight),
            metadata=metadata,
        )
        self._dispatch(message, template_key="commentary")
        self._buffer_commentary(entry, highlight)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _render(self, key: str, **values: str) -> str:
        template = self.templates.get(key) or DEFAULT_TEMPLATES[key]
        try:
            return template.format(**values).strip()
        except KeyError:
            # Fallback to default template if user template is missing keys
            self.logger.warning(
                "Template '%s' missing keys; falling back to default.", key)
            return DEFAULT_TEMPLATES[key].format(**values).strip()

    def _dispatch(self, text: str, *, template_key: str) -> None:
        if not text:
            return
        if self.dry_run:
            self._dry_run_log.append(text)
            self._record_delivery("dry_run", template_key)
            self.logger.info(
                "Dry-run notification",
                extra={
                    "template": template_key,
                    "payload": text,
                    "target": "dry_run",
                },
            )
            return
        if not self.enabled:
            self.logger.debug("Dispatch skipped (notifications disabled).")
            return
        slack_webhook = self.channel.slack_webhook
        delivered = False
        if slack_webhook is not None:
            delivered |= self._send_slack(slack_webhook, text, template_key)
        line_token = self.channel.line_token
        if line_token is not None:
            delivered |= self._send_line(line_token, text, template_key)
        if slack_webhook is None and line_token is None:
            self.logger.debug(
                "Dispatch skipped (no notification targets configured).")
        elif not delivered:
            self.logger.debug(
                "Notification delivery failed for template '%s'.", template_key)

    def _send_slack(self, webhook: str, text: str, template_key: str) -> bool:
        return self._request_with_retries(
            method="POST",
            url=webhook,
            target="slack",
            template_key=template_key,
            headers={"Content-Type": "application/json"},
            json_payload={"text": text},
        )

    def _send_line(self, token: str, text: str, template_key: str) -> bool:
        return self._request_with_retries(
            method="POST",
            url="https://notify-api.line.me/api/notify",
            target="line",
            template_key=template_key,
            headers={"Authorization": f"Bearer {token}"},
            data={"message": text},
        )

    def _request_with_retries(
        self,
        *,
        method: str,
        url: str,
        target: str,
        template_key: str,
        headers: Optional[Dict[str, str]] = None,
        json_payload: Optional[Dict[str, object]] = None,
        data: Optional[Dict[str, str]] = None,
    ) -> bool:
        attempts = self._max_retries + 1
        last_error: Optional[str] = None
        for attempt in range(1, attempts + 1):
            try:
                response = self.session.request(
                    method,
                    url,
                    headers=headers,
                    json=json_payload,
                    data=data,
                    timeout=self._request_timeout,
                )
            except Exception as exc:
                last_error = str(exc)
                self.logger.warning(
                    "Notification request failed (%s attempt %d/%d): %s",
                    target,
                    attempt,
                    attempts,
                    last_error,
                )
            else:
                if response.status_code < 400:
                    self._record_delivery(target, template_key)
                    self.logger.info(
                        "Notification delivered",
                        extra={
                            "target": target,
                            "template": template_key,
                            "attempt": attempt,
                            "status": response.status_code,
                        },
                    )
                    return True
                last_error = f"HTTP {response.status_code}"
                self.logger.warning(
                    "Notification returned %s (%s attempt %d/%d) for template '%s'.",
                    last_error,
                    target,
                    attempt,
                    attempts,
                    template_key,
                )
            if attempt < attempts:
                delay = self._compute_backoff_delay(attempt)
                self.logger.debug(
                    "Retrying notification (%s) in %.2fs (attempt %d/%d).",
                    target,
                    delay,
                    attempt + 1,
                    attempts,
                )
                time.sleep(delay)
        self._record_failure(target, template_key)
        self.logger.error(
            "Notification delivery failed after %d attempts (%s): %s",
            attempts,
            target,
            last_error,
        )
        return False

    def _compute_backoff_delay(self, attempt: int) -> float:
        base_delay = min(self._backoff_cap,
                         self._backoff_base * (2 ** (attempt - 1)))
        jitter = base_delay * self._backoff_jitter * random.random()
        return base_delay + jitter

    @staticmethod
    def _format_vector(vector: dict[str, float]) -> str:
        if not vector:
            return "n/a"
        pieces = [f"{k}:{v:.2f}" for k, v in vector.items()]
        return ", ".join(pieces)

    def _compose_commentary_message(self, base: str, highlight: str) -> str:
        if not highlight:
            return base
        return f"{base}\n👉 {highlight}"

    def _build_commentary_highlight(self, metadata: Dict[str, Any]) -> str:
        plan = metadata.get("remi_plan") or metadata.get("plan") or {}
        if isinstance(plan, dict):
            plan_items = plan.get("plan")
        else:
            plan_items = plan
        highlight_parts: list[str] = []
        if isinstance(plan_items, Iterable):
            for item in plan_items:
                if not isinstance(item, dict):
                    continue
                title = item.get("title")
                detail = item.get("detail")
                owner = item.get("owner")
                if owner and owner not in {"luna", "shared", "mina"}:
                    continue
                if title and detail:
                    highlight_parts.append(f"{title}: {detail}")
                elif detail:
                    highlight_parts.append(detail)
        if not highlight_parts:
            message = metadata.get("message")
            if isinstance(message, str):
                highlight_parts.append(message)
        if not highlight_parts:
            return ""
        return highlight_parts[0]

    def _buffer_commentary(self, entry: "CommentaryEntry", highlight: str = "") -> None:
        now = time.time()
        timestamp_obj = getattr(entry, "ts", None)
        if timestamp_obj is not None and hasattr(timestamp_obj, "isoformat"):
            timestamp = timestamp_obj.isoformat()
        else:
            timestamp = str(timestamp_obj) if timestamp_obj is not None else ""
        self._commentary_buffer.append({
            "channel": entry.channel or "thought",
            "message": entry.message,
            "timestamp": timestamp,
            "level": getattr(entry, "level", "") or "",
            "highlight": highlight,
        })
        if not self._last_commentary_digest:
            self._last_commentary_digest = now
        if now - self._last_commentary_digest >= self._commentary_interval:
            self._send_commentary_digest()
            self._commentary_buffer.clear()
            self._last_commentary_digest = now

    def _send_commentary_digest(self) -> None:
        if not self.enabled or not self._commentary_buffer:
            return
        latest = self._commentary_buffer[-self._commentary_digest_size:]
        lines = []
        now = datetime.now(timezone.utc)
        parsed_times = []
        for item in latest:
            ts = item.get("timestamp")
            dt = None
            if ts:
                try:
                    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                except ValueError:
                    dt = None
            if dt is not None and dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            if dt is not None:
                parsed_times.append(dt)
                ts_text = dt.astimezone().strftime("%H:%M:%S")
            else:
                ts_text = ts or "--:--"
            level = item.get("level") or "info"
            highlight = item.get("highlight")
            if highlight:
                lines.append(
                    f"• {ts_text} [{item['channel']}] ({level}) {item['message']} ｜ {highlight}")
            else:
                lines.append(
                    f"• {ts_text} [{item['channel']}] ({level}) {item['message']}")

        span_minutes = 5
        if parsed_times:
            oldest = min(parsed_times)
            delta = now - oldest
            span_minutes = max(1, int(delta.total_seconds() // 60) or 1)

        summary = "\n".join(lines)
        digest = self._render(
            "commentary_digest",
            summary=summary,
            count=str(len(latest)),
            span_minutes=str(span_minutes),
        )
        self._dispatch(digest, template_key="commentary_digest")

    @staticmethod
    def _record_delivery(target: str, template_key: str) -> None:
        try:
            NOTIFICATION_DELIVERED.labels(
                target=target, template=template_key).inc()
        except Exception:
            pass

    @staticmethod
    def _record_failure(target: str, template_key: str) -> None:
        try:
            NOTIFICATION_FAILURE.labels(
                target=target, template=template_key).inc()
        except Exception:
            pass

    @staticmethod
    def _parse_float(raw: Optional[str], *, default: float, minimum: float) -> float:
        if not raw:
            return default
        try:
            value = float(raw)
        except ValueError:
            logging.getLogger(__name__).warning(
                "Invalid float for notification interval '%s'; using default %.2f",
                raw,
                default,
            )
            return default
        return max(minimum, value)

    @staticmethod
    def _parse_int(raw: Optional[str], *, default: int, minimum: int) -> int:
        if not raw:
            return default
        try:
            value = int(raw)
        except ValueError:
            logging.getLogger(__name__).warning(
                "Invalid int for notification digest size '%s'; using default %d",
                raw,
                default,
            )
            return default
        return max(minimum, value)

    @classmethod
    def _ensure_file_handler(cls, log_path: Path) -> None:
        try:
            log_path.parent.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            logger.warning(
                "Unable to create log directory for %s: %s", log_path, exc)
            return
        normalized = log_path.resolve()
        if normalized in _registered_handlers:
            return
        handler = RotatingFileHandler(
            normalized, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8")
        handler.setLevel(logging.INFO)
        formatter = logging.Formatter(
            fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S%z",
        )
        handler.setFormatter(formatter)
        logging.getLogger().addHandler(handler)
        _registered_handlers.add(normalized)
