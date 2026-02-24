"""
ManaOS OpenTelemetry統合

分散トレーシング・メトリクス・ログの統合可観測性
"""

from opentelemetry import trace, metrics, logs
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.aiohttp_client import AioHttpClientInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
import logging
import os


class OpenTelemetrySetup:
    """OpenTelemetry セットアップ"""
    
    @staticmethod
    def setup_tracing(service_name: str = "manaos") -> TracerProvider:
        """トレーシング設定"""
        
        # Jaeger Exporter作成
        jaeger_exporter = JaegerExporter(
            agent_host_name=os.environ.get("JAEGER_HOST", "localhost"),
            agent_port=int(os.environ.get("JAEGER_PORT", 6831)),
        )
        
        # TracerProvider作成
        trace_provider = TracerProvider(
            resource=Resource.create({
                SERVICE_NAME: service_name,
                "environment": os.environ.get("ENVIRONMENT", "development"),
                "version": os.environ.get("APP_VERSION", "2.6.0")
            })
        )
        
        # BatchSpanProcessor追加
        trace_provider.add_span_processor(
            BatchSpanProcessor(jaeger_exporter)
        )
        
        # グローバルTracerProvider設定
        trace.set_tracer_provider(trace_provider)
        
        return trace_provider
    
    @staticmethod
    def setup_metrics(service_name: str = "manaos") -> MeterProvider:
        """メトリクス設定"""
        
        # PrometheusMetricReader作成
        prometheus_reader = PrometheusMetricReader()
        
        # MeterProvider作成
        meter_provider = MeterProvider(
            resource=Resource.create({
                SERVICE_NAME: service_name
            }),
            metric_readers=[prometheus_reader]
        )
        
        # グローバルMeterProvider設定
        metrics.set_meter_provider(meter_provider)
        
        return meter_provider
    
    @staticmethod
    def setup_logging(service_name: str = "manaos"):
        """ロギング設定"""
        
        # LoggingInstrumentor設定
        LoggingInstrumentor().instrument()
        
        # ログレベル設定
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    @staticmethod
    def setup_auto_instrumentation():
        """自動計装設定"""
        
        # FastAPI計装
        FastAPIInstrumentor().instrument()
        
        # requests計装
        RequestsInstrumentor().instrument()
        
        # Redis計装
        try:
            RedisInstrumentor().instrument()
        except Exception:
            pass
        
        # aiohttp計装
        AioHttpClientInstrumentor().instrument()
        
        # SQLAlchemy計装
        try:
            SQLAlchemyInstrumentor().instrument()
        except Exception:
            pass


class TelemetryMetrics:
    """カスタムテレメトリメトリクス"""
    
    def __init__(self):
        self.meter = metrics.get_meter(__name__)
        
        # リクエストカウンタ
        self.request_counter = self.meter.create_counter(
            name="manaos.requests",
            description="Total number of requests",
            unit="1"
        )
        
        # レスポンスタイム
        self.response_time_histogram = self.meter.create_histogram(
            name="manaos.response_time",
            description="Response time in milliseconds",
            unit="ms"
        )
        
        # エラーカウンタ
        self.error_counter = self.meter.create_counter(
            name="manaos.errors",
            description="Total number of errors",
            unit="1"
        )
        
        # アクティブリクエスト
        self.active_requests_gauge = self.meter.create_up_down_counter(
            name="manaos.active_requests",
            description="Number of active requests",
            unit="1"
        )
    
    def record_request(self, method: str, path: str):
        """リクエスト記録"""
        self.request_counter.add(1, {
            "http.method": method,
            "http.path": path
        })
        self.active_requests_gauge.add(1)
    
    def record_response(self, response_time_ms: float, status_code: int, path: str):
        """レスポンス記録"""
        self.response_time_histogram.record(response_time_ms, {
            "http.status_code": str(status_code),
            "http.path": path
        })
        self.active_requests_gauge.add(-1)
    
    def record_error(self, error_type: str, path: str):
        """エラー記録"""
        self.error_counter.add(1, {
            "error.type": error_type,
            "http.path": path
        })


class TraceDecorator:
    """トレーシングデコレータ"""
    
    @staticmethod
    def trace_function(name: str):
        """関数トレース"""
        def decorator(func):
            def wrapper(*args, **kwargs):
                tracer = trace.get_tracer(__name__)
                with tracer.start_as_current_span(name) as span:
                    span.set_attribute("function.name", func.__name__)
                    span.set_attribute("function.module", func.__module__)
                    return func(*args, **kwargs)
            return wrapper
        return decorator
    
    @staticmethod
    async def trace_async_function(name: str):
        """非同期関数トレース"""
        def decorator(func):
            async def wrapper(*args, **kwargs):
                tracer = trace.get_tracer(__name__)
                with tracer.start_as_current_span(name) as span:
                    span.set_attribute("function.name", func.__name__)
                    span.set_attribute("function.async", True)
                    return await func(*args, **kwargs)
            return wrapper
        return decorator


# FastAPIミドルウェア
class OpenTelemetryMiddleware:
    """OpenTelemetry FastAPIミドルウェア"""
    
    def __init__(self, app, telemetry_metrics: TelemetryMetrics):
        self.app = app
        self.metrics = telemetry_metrics
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        import time
        request_start_time = time.time()
        
        path = scope.get("path", "")
        method = scope.get("method", "")
        
        # リクエスト記録
        self.metrics.record_request(method, path)
        
        # レスポンス処理
        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                status_code = message["status"]
                response_time_ms = (time.time() - request_start_time) * 1000
                self.metrics.record_response(response_time_ms, status_code, path)
                
                # ログ記録
                logging.info(
                    f"{method} {path} {status_code} {response_time_ms:.2f}ms"
                )
            
            await send(message)
        
        await self.app(scope, receive, send_wrapper)


# 初期化関数
def initialize_observability(app=None):
    """可観測性の初期化"""
    
    # トレーシング設定
    OpenTelemetrySetup.setup_tracing()
    
    # メトリクス設定
    OpenTelemetrySetup.setup_metrics()
    
    # ロギング設定
    OpenTelemetrySetup.setup_logging()
    
    # 自動計装
    OpenTelemetrySetup.setup_auto_instrumentation()
    
    # FastAppにミドルウェア追加
    if app:
        metrics = TelemetryMetrics()
        app.add_middleware(OpenTelemetryMiddleware, telemetry_metrics=metrics)
    
    logging.info("✅ OpenTelemetry observability initialized")
