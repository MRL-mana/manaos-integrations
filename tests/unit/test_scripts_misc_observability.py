"""
Unit tests for scripts/misc/observability.py
"""
import sys
from unittest.mock import MagicMock, patch, AsyncMock

import pytest

# ── opentelemetry モジュールモック（インポート前に設定）────────────────────────

# opentelemetry core
_ot_trace = MagicMock()
_ot_metrics = MagicMock()
_ot_logs = MagicMock()
sys.modules.setdefault("opentelemetry", MagicMock())
sys.modules.setdefault("opentelemetry.trace", _ot_trace)
sys.modules.setdefault("opentelemetry.metrics", _ot_metrics)
sys.modules.setdefault("opentelemetry.logs", _ot_logs)

# sdk
_sdk_trace = MagicMock()
_tracer_provider_cls = MagicMock()
_sdk_trace.TracerProvider = _tracer_provider_cls
sys.modules.setdefault("opentelemetry.sdk", MagicMock())
sys.modules.setdefault("opentelemetry.sdk.trace", _sdk_trace)
sys.modules.setdefault("opentelemetry.sdk.trace.export", MagicMock())

_sdk_metrics = MagicMock()
_meter_provider_cls = MagicMock()
_sdk_metrics.MeterProvider = _meter_provider_cls
sys.modules.setdefault("opentelemetry.sdk.metrics", _sdk_metrics)
sys.modules.setdefault("opentelemetry.sdk.metrics.export", MagicMock())

_sdk_resources = MagicMock()
_sdk_resources.SERVICE_NAME = "service.name"
_resource_cls = MagicMock()
_resource_cls.create = MagicMock(return_value=MagicMock())
_sdk_resources.Resource = _resource_cls
sys.modules.setdefault("opentelemetry.sdk.resources", _sdk_resources)

# exporters
sys.modules.setdefault("opentelemetry.exporter", MagicMock())
sys.modules.setdefault("opentelemetry.exporter.jaeger", MagicMock())
sys.modules.setdefault("opentelemetry.exporter.jaeger.thrift", MagicMock())
sys.modules.setdefault("opentelemetry.exporter.prometheus", MagicMock())

# instrumentation
sys.modules.setdefault("opentelemetry.instrumentation", MagicMock())
sys.modules.setdefault("opentelemetry.instrumentation.fastapi", MagicMock())
sys.modules.setdefault("opentelemetry.instrumentation.requests", MagicMock())
sys.modules.setdefault("opentelemetry.instrumentation.sqlalchemy", MagicMock())
sys.modules.setdefault("opentelemetry.instrumentation.redis", MagicMock())
sys.modules.setdefault("opentelemetry.instrumentation.aiohttp_client", MagicMock())
sys.modules.setdefault("opentelemetry.instrumentation.logging", MagicMock())

from scripts.misc.observability import (
    OpenTelemetrySetup,
    TelemetryMetrics,
    TraceDecorator,
    OpenTelemetryMiddleware,
    initialize_observability,
)


# ─── OpenTelemetrySetup ────────────────────────────────────────────────────────
class TestOpenTelemetrySetupTracing:
    def test_setup_tracing_returns_provider(self):
        result = OpenTelemetrySetup.setup_tracing("test-service")
        assert result is not None

    def test_setup_tracing_default_service_name(self):
        result = OpenTelemetrySetup.setup_tracing()
        assert result is not None

    def test_setup_tracing_does_not_raise(self):
        # Just verifying no exception is raised with arbitrary service name
        OpenTelemetrySetup.setup_tracing("my-service")


class TestOpenTelemetrySetupMetrics:
    def test_setup_metrics_returns_provider(self):
        result = OpenTelemetrySetup.setup_metrics("test-service")
        assert result is not None

    def test_setup_metrics_does_not_raise(self):
        OpenTelemetrySetup.setup_metrics("svc")


class TestOpenTelemetrySetupLogging:
    def test_setup_logging_does_not_raise(self):
        # Should not raise even if logging instrumentation is mocked
        OpenTelemetrySetup.setup_logging()


class TestOpenTelemetrySetupAutoInstrumentation:
    def test_setup_auto_instrumentation_does_not_raise(self):
        OpenTelemetrySetup.setup_auto_instrumentation()


# ─── TelemetryMetrics ─────────────────────────────────────────────────────────
class TestTelemetryMetrics:
    def setup_method(self):
        # Always create fresh meter mock to prevent cross-test contamination
        fake_meter = MagicMock()
        fake_meter.create_counter.return_value = MagicMock()
        fake_meter.create_histogram.return_value = MagicMock()
        fake_meter.create_up_down_counter.return_value = MagicMock()
        _ot_metrics.get_meter.return_value = fake_meter
        self.metrics = TelemetryMetrics()
        # observability.py does "from opentelemetry import metrics" which binds
        # to the opentelemetry mock's auto-attribute, NOT _ot_metrics.
        # Replace each counter/histogram with a fresh MagicMock so cross-test
        # call counts don't accumulate on the shared auto-generated mock.
        self.metrics.request_counter = MagicMock()
        self.metrics.error_counter = MagicMock()
        self.metrics.response_time_histogram = MagicMock()
        self.metrics.active_requests_gauge = MagicMock()

    def test_record_request_calls_counter_add(self):
        self.metrics.record_request("GET", "/api/health")
        self.metrics.request_counter.add.assert_called_once()  # type: ignore

    def test_record_request_calls_active_requests_add(self):
        self.metrics.record_request("POST", "/api/data")
        self.metrics.active_requests_gauge.add.assert_called()  # type: ignore

    def test_record_response_calls_histogram_record(self):
        self.metrics.record_response(42.5, 200, "/api/health")
        self.metrics.response_time_histogram.record.assert_called_once()  # type: ignore

    def test_record_response_decrements_active_requests(self):
        self.metrics.record_response(10.0, 200, "/api/x")
        # add should be called with -1
        calls = [str(c) for c in self.metrics.active_requests_gauge.add.call_args_list]  # type: ignore
        assert any("-1" in c for c in calls)

    def test_record_error_calls_counter_add(self):
        self.metrics.record_error("ValueError", "/api/broken")
        self.metrics.error_counter.add.assert_called_once()  # type: ignore


# ─── TraceDecorator ───────────────────────────────────────────────────────────
class TestTraceDecorator:
    def test_trace_function_wraps_and_calls(self):
        fake_span = MagicMock()
        fake_span.__enter__ = MagicMock(return_value=fake_span)
        fake_span.__exit__ = MagicMock(return_value=False)
        fake_tracer = MagicMock()
        fake_tracer.start_as_current_span.return_value = fake_span
        _ot_trace.get_tracer.return_value = fake_tracer

        @TraceDecorator.trace_function("test_span")
        def my_func(x):
            return x * 2

        result = my_func(5)
        assert result == 10

    def test_trace_function_returns_decorator(self):
        decorator = TraceDecorator.trace_function("my_span")
        assert callable(decorator)


# ─── OpenTelemetryMiddleware ──────────────────────────────────────────────────
class TestOpenTelemetryMiddleware:
    def test_non_http_scope_passes_through(self):
        import asyncio
        fake_app = AsyncMock()
        fake_metrics = MagicMock()
        middleware = OpenTelemetryMiddleware(fake_app, fake_metrics)
        scope = {"type": "websocket"}
        asyncio.run(middleware(scope, None, None))
        fake_app.assert_called_once_with(scope, None, None)


# ─── initialize_observability ──────────────────────────────────────────────────
class TestInitializeObservability:
    def test_no_app_does_not_raise(self):
        initialize_observability()

    def test_with_app_calls_add_middleware(self):
        fake_app = MagicMock()
        _meter_provider_cls.return_value = MagicMock()
        initialize_observability(app=fake_app)
        fake_app.add_middleware.assert_called_once()
