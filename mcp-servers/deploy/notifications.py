"""Notification helper for MachiOS Reflection Feed expressive mode."""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

import requests


@dataclass
class NotificationChannel:
    slack_webhook: Optional[str]
    line_token: Optional[str]

    def has_targets(self) -> bool:
        return bool(self.slack_webhook or self.line_token)


class NotificationManager:
    """Send compact summaries to Slack / LINE when expressive mode is active."""

    def __init__(self, enabled: bool, channel: NotificationChannel) -> None:
        self.enabled = enabled and channel.has_targets()
        self.channel = channel
        self.session = requests.Session()

    @classmethod
    def from_env(cls, mode: str) -> "NotificationManager":
        enabled = mode.lower() == "expressive"
        channel = NotificationChannel(
            slack_webhook=os.getenv("MACHI_FEED_SLACK_WEBHOOK"),
            line_token=os.getenv("MACHI_FEED_LINE_TOKEN"),
        )
        return cls(enabled, channel)

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def notify_decision(self, decision: "DecisionLog") -> None:
        if not self.enabled:
            return
        message = (
            "🧠 *New Decision*\n"
            f"Task: `{decision.selected.task_id}`\n"
            f"Metric: {decision.selected_metric or 'n/a'}\n"
            f"Priority: {self._format_vector(decision.priority_vector)}"
        )
        if decision.trade_offs:
            message += "\nTrade-offs: " + ", ".join(decision.trade_offs)
        self._dispatch(message)

    def notify_future_intent(self, intent: "FutureIntent") -> None:
        if not self.enabled:
            return
        confidence = (
            f" ({intent.confidence*100:.0f}% confidence)" if intent.confidence is not None else ""
        )
        message = (
            "🔮 *Future Intent*\n"
            f"Intent: {intent.intent}{confidence}\n"
            f"Dependencies: {', '.join(intent.dependencies) or 'none'}"
        )
        if intent.eta_hint:
            message += f"\nETA: {intent.eta_hint}"
        self._dispatch(message)

    def notify_reflection(self, loop_eval: "LoopEval") -> None:
        if not self.enabled:
            return
        issues = loop_eval.self_eval.get("issues")
        if not issues:
            return
        issues_text = ", ".join(issues) if isinstance(issues, list) else str(issues)
        message = (
            "⚠️ *Reflection Alert*\n"
            f"Task: {loop_eval.inputs.get('task_id', 'unknown')}\n"
            f"Issues: {issues_text}"
        )
        self._dispatch(message)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _dispatch(self, text: str) -> None:
        if self.channel.slack_webhook:
            self._send_slack(text)
        if self.channel.line_token:
            self._send_line(text)

    def _send_slack(self, text: str) -> None:
        try:
            self.session.post(self.channel.slack_webhook, json={"text": text}, timeout=5)
        except Exception:
            pass

    def _send_line(self, text: str) -> None:
        try:
            self.session.post(
                "https://notify-api.line.me/api/notify",
                data={"message": text},
                headers={"Authorization": f"Bearer {self.channel.line_token}"},
                timeout=5,
            )
        except Exception:
            pass

    @staticmethod
    def _format_vector(vector: dict[str, float]) -> str:
        if not vector:
            return "n/a"
        pieces = [f"{k}:{v:.2f}" for k, v in vector.items()]
        return ", ".join(pieces)
