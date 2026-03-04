"""FastAPI application for the MachiOS Reflection Feed."""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import secrets
from datetime import datetime
from typing import Any, Dict, Optional, AsyncIterator

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from prometheus_client import make_asgi_app

from .collector import ReflectionCollector
from .config import FeedConfig, load_config
from .event_stream import EventHub
from .schemas import Capsule, FutureIntent


def _parse_iso_timestamp(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    normalized = value.rstrip("Z") + ("+00:00" if value.endswith("Z") else "")
    try:
        return datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise HTTPException(
            status_code=400, detail=f"Invalid ISO8601 timestamp: {value}") from exc


def _json_default(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


class AuthDependency:
    def __init__(self, token: Optional[str]) -> None:
        self.token = token

    def __call__(
        self,
        authorization: str = Header(default=""),
        token: Optional[str] = Query(default=None),
    ) -> None:
        if not self.token:
            return
        candidate: Optional[str] = None
        if authorization.startswith("Bearer "):
            candidate = authorization.split(" ", 1)[1].strip()
        elif token:
            candidate = token.strip()
        if not candidate or not secrets.compare_digest(candidate, self.token):
            raise HTTPException(
                status_code=401, detail="Authorization header missing or invalid")


def create_app(config: FeedConfig) -> FastAPI:
    event_hub = EventHub()
    collector = ReflectionCollector(config, event_hub=event_hub)
    auth_dependency = AuthDependency(config.auth_token)

    allowed_origins = ["*"]
    if config.auth_token:
        env_origins = os.getenv(
            "MACHI_FEED_ALLOWED_ORIGINS",
            "http://127.0.0.1:5050,http://localhost:5050",
        )
        allowed_origins = [origin.strip()
                           for origin in env_origins.split(",") if origin.strip()]

    app = FastAPI(title="MachiOS Reflection Feed", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=[
            "*"] if not config.auth_token else ["Authorization", "Content-Type"],
    )
    app.state.event_hub = event_hub

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

    @app.post("/ingest/commentary")
    async def ingest_commentary(
        payload: Dict[str, Any],
        _: None = Depends(auth_dependency),
    ) -> Dict[str, Any]:
        record = collector.ingest_commentary(payload)
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
        capsules = collector.fetch_capsules(
            limit=limit, offset=offset, since=since_ts, until=until_ts)
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

    @app.get("/feed/commentary")
    async def feed_commentary(
        limit: int = Query(default=20, ge=1, le=200),
        _: None = Depends(auth_dependency),
    ) -> Dict[str, Any]:
        entries = collector.fetch_recent_commentary(limit)
        return {"items": [entry.dict() for entry in entries], "count": len(entries)}

    @app.get("/feed/priority/vector")
    async def feed_priority_vector(
        window: int = Query(default=20, ge=1, le=200),
        _: None = Depends(auth_dependency),
    ) -> Dict[str, Any]:
        averages = collector.priority_vector_average(window)
        return {"averages": averages}

    @app.get("/feed/events/stream")
    async def feed_events_stream(
        request: Request,
        _: None = Depends(auth_dependency),
    ) -> StreamingResponse:
        hub: EventHub = app.state.event_hub
        queue = await hub.connect()

        async def event_generator() -> AsyncIterator[str]:
            try:
                while True:
                    try:
                        event = await asyncio.wait_for(queue.get(), timeout=25)
                        payload = json.dumps(event, default=_json_default)
                        yield f"data: {payload}\n\n"
                    except asyncio.TimeoutError:
                        if await request.is_disconnected():
                            break
                        yield "event: ping\ndata: {}\n\n"
            finally:
                await hub.disconnect(queue)

        return StreamingResponse(event_generator(), media_type="text/event-stream")

    if config.metrics_enable:
        metrics_app = make_asgi_app()
        app.mount("/metrics", metrics_app)

    return app


def main(argv: Optional[list[str]] = None) -> None:
    parser = argparse.ArgumentParser(
        description="Run the MachiOS Reflection Feed server")
    parser.add_argument(
        "--config", help="Path to YAML config file", default=None)
    args = parser.parse_args(argv)

    config = load_config(args.config)
    app = create_app(config)

    import uvicorn

    uvicorn.run(app, host=config.bind, port=config.port)


if __name__ == "__main__":  # pragma: no cover
    main()
