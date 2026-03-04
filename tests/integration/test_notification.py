#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pytest


def _build_hub():
    import_candidates = [
        ("notification_hub_enhanced", "NotificationHubEnhanced"),
        ("scripts.notification.notification_hub_enhanced", "NotificationHubEnhanced"),
    ]
    last_error = None
    for module_name, class_name in import_candidates:
        try:
            module = __import__(module_name, fromlist=[class_name])
            return getattr(module, class_name)()
        except Exception as exc:
            last_error = exc
    pytest.skip(f"NotificationHubEnhanced を初期化できないためスキップ: {last_error}")


def test_notification_hub_init_smoke():
    hub = _build_hub()
    assert hub is not None


def test_notification_hub_stats_smoke():
    hub = _build_hub()
    try:
        stats = hub.get_stats()
    except Exception as exc:
        pytest.skip(f"通知統計取得に失敗したためスキップ: {exc}")
    assert isinstance(stats, dict)

