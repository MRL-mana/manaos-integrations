"""FastAPI application for the MachiOS Reflection Feed."""
from __future__ import annotations

import argparse
import os
import secrets
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import make_asgi_app

from .collector import ReflectionCollector
from .config import FeedConfig, load_config
from .schemas import Capsule, FutureIntent


def _parse_iso_timestamp(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    normalized = value.rstrip("Z") + ("+00:00" if value.endswith("Z") else "")
    try:
        return datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid ISO8601 timestamp: {value}") from exc


class AuthDependency:
    def __init__(self, token: Optional[str]) -> None:
        self.token = token

    def __call__(self, authorization: str = Header(default="")) -> None:
        if not self.token:
            return
        if not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Authorization header missing or invalid")
        received_token = authorization.split(" ", 1)[1].strip()
        if not secrets.compare_digest(received_token, self.token):
            raise HTTPException(status_code=401, detail="Invalid token")


def create_app(config: FeedConfig) -> FastAPI:
    collector = ReflectionCollector(config)
    auth_dependency = AuthDependency(config.auth_token)

    allowed_origins = ["*"]
    if config.auth_token:
        env_origins = os.getenv(
            "MACHI_FEED_ALLOWED_ORIGINS",
            "http://127.0.0.1:5050,http://localhost:5050",
        )
        allowed_origins = [origin.strip() for origin in env_origins.split(",") if origin.strip()]

    app = FastAPI(title="MachiOS Reflection Feed", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"] if not config.auth_token else ["Authorization", "Content-Type"],
    )

    @app.exception_handler(ValueError)
    async def value_error_handler(_: Any, exc: ValueError) -> JSONResponse:  # pragma: no cover - defensive
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    # ------------------------------------------------------------------
    # Ingestion endpoints
    # ------------------------------------------------------------------

    @app.post("/ingest/decision_log")
    async def ingest_decision_log(
        payload: Dict[str, Any],
        _: None = Depends(auth_dependency),
    ) -> Dict[str, Any]:
        record = collector.ingest_decision_log(payload)
        return {"status": "ok", "id": record.id}

    @app.post("/ingest/loop_eval")
    async def ingest_loop_eval(
        payload: Dict[str, Any],
        _: None = Depends(auth_dependency),
    ) -> Dict[str, Any]:
        record = collector.ingest_loop_eval(payload)
        return {"status": "ok", "id": record.id}

    @app.post("/ingest/future_intents")
    async def ingest_future_intents(
        payload: Dict[str, Any],
        _: None = Depends(auth_dependency),
    ) -> Dict[str, Any]:
        record = collector.ingest_future_intent(payload)
        return {"status": "ok", "id": record.id}

    # ------------------------------------------------------------------
    # Feed endpoints
    # ------------------------------------------------------------------

    @app.get("/feed/summary")
    async def feed_summary(
        since: Optional[str] = Query(default=None),
        until: Optional[str] = Query(default=None),
        _: None = Depends(auth_dependency),
    ) -> Dict[str, Any]:
        since_ts = _parse_iso_timestamp(since)
        until_ts = _parse_iso_timestamp(until)
        return collector.summarize(since_ts, until_ts)

    @app.get("/feed/capsules")
    async def feed_capsules(
        limit: int = Query(default=50, ge=1, le=500),
        offset: int = Query(default=0, ge=0),
        since: Optional[str] = Query(default=None),
        until: Optional[str] = Query(default=None),
        _: None = Depends(auth_dependency),
    ) -> Dict[str, Any]:
        since_ts = _parse_iso_timestamp(since)
        until_ts = _parse_iso_timestamp(until)
        capsules = collector.fetch_capsules(limit=limit, offset=offset, since=since_ts, until=until_ts)
        return {
            "items": [capsule.dict() for capsule in capsules],
            "count": len(capsules),
        }

    @app.get("/feed/future")
    async def feed_future(
        limit: int = Query(default=50, ge=1, le=500),
        _: None = Depends(auth_dependency),
    ) -> Dict[str, Any]:
        intents = collector.fetch_future_intents(limit)
        return {"items": [intent.dict() for intent in intents], "count": len(intents)}

    @app.get("/feed/learning/recent")
    async def feed_recent_learning(
        top: int = Query(default=3, ge=1, le=20),
        _: None = Depends(auth_dependency),
    ) -> Dict[str, Any]:
        patterns = collector.recent_learning(top)
        return {"items": patterns}

    @app.get("/feed/priority/vector")
    async def feed_priority_vector(
        window: int = Query(default=20, ge=1, le=200),
        _: None = Depends(auth_dependency),
    ) -> Dict[str, Any]:
        averages = collector.priority_vector_average(window)
        return {"averages": averages}

    if config.metrics_enable:
        metrics_app = make_asgi_app()
        app.mount("/metrics", metrics_app)

    return app


def main(argv: Optional[list[str]] = None) -> None:
    parser = argparse.ArgumentParser(description="Run the MachiOS Reflection Feed server")
    parser.add_argument("--config", help="Path to YAML config file", default=None)
    args = parser.parse_args(argv)

    config = load_config(args.config)
    app = create_app(config)

    import uvicorn

    uvicorn.run(app, host=config.bind, port=config.port)


if __name__ == "__main__":  # pragma: no cover
    main()
