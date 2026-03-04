"""Configuration helpers for the MachiOS Reflection Feed."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass
class FeedConfig:
    """Runtime configuration for the Reflection Feed."""

    store_path: str = "/var/lib/machi/feed.db"
    capsule_merge_window_sec: int = 300
    expose_api: bool = True
    bind: str = "127.0.0.1"
    port: int = 5057
    auth_token: Optional[str] = None
    metrics_enable: bool = True
    metrics_port: int = 9107
    mode: str = "observer"

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FeedConfig":
        feed_section = data.get("feed", {})
        metrics_section = data.get("metrics", {})
        auth_token = feed_section.get("auth_token")
        if not auth_token:
            env_key = feed_section.get("auth_token_env")
            if env_key:
                auth_token = os.getenv(env_key)

        defaults = cls()

        return cls(
            store_path=str(feed_section.get("store_path", defaults.store_path)),
            capsule_merge_window_sec=int(
                feed_section.get("capsule_merge_window_sec", defaults.capsule_merge_window_sec)
            ),
            expose_api=bool(feed_section.get("expose_api", defaults.expose_api)),
            bind=str(feed_section.get("bind", defaults.bind)),
            port=int(feed_section.get("port", defaults.port)),
            auth_token=auth_token,
            metrics_enable=bool(metrics_section.get("enable", defaults.metrics_enable)),
            metrics_port=int(metrics_section.get("port", defaults.metrics_port)),
            mode=str(feed_section.get("mode", defaults.mode)).lower(),
        )


def load_config(path: Optional[str]) -> FeedConfig:
    """Load configuration from YAML if provided, otherwise use defaults."""

    if not path:
        return FeedConfig()

    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    try:
        import yaml  # type: ignore
    except ImportError as exc:  # pragma: no cover - library missing at runtime
        raise RuntimeError("PyYAML is required to load the Reflection Feed config") from exc

    with config_path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}

    if not isinstance(data, dict):
        raise ValueError("Configuration file must define a mapping at the top level")

    return FeedConfig.from_dict(data)
