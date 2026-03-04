"""Pydantic schemas for Reflection Feed payloads."""
from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, validator


def parse_timestamp(value: object) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        normalized = value.rstrip("Z") + ("+00:00" if value.endswith("Z") else "")
        try:
            return datetime.fromisoformat(normalized)
        except ValueError as exc:
            raise ValueError(f"Invalid ISO8601 timestamp: {value}") from exc
    raise TypeError("timestamp must be a datetime or ISO8601 string")


class DecisionCandidate(BaseModel):
    task_id: str
    score: float
    vector: Optional[Dict[str, float]] = None


class DecisionSelection(BaseModel):
    task_id: str
    reason: Optional[str] = None


class DecisionLog(BaseModel):
    id: str = Field(..., alias="id")
    ts: datetime
    loop_id: Optional[str] = None
    task_context: Optional[Dict[str, object]] = None
    candidates: List[DecisionCandidate] = Field(default_factory=list)
    selected: DecisionSelection
    priority_vector: Dict[str, float] = Field(default_factory=dict)
    selected_metric: Optional[str] = None
    trade_offs: List[str] = Field(default_factory=list)

    class Config:
        allow_population_by_field_name = True

    @validator("ts", pre=True)
    def _parse_ts(cls, value: object) -> datetime:
        return parse_timestamp(value)


class LoopEval(BaseModel):
    id: str
    ts: datetime
    loop_id: Optional[str] = None
    inputs: Optional[Dict[str, object]] = None
    actions: List[str] = Field(default_factory=list)
    outcome_score: Dict[str, object] = Field(default_factory=dict)
    self_eval: Dict[str, object] = Field(default_factory=dict)

    @validator("ts", pre=True)
    def _parse_ts(cls, value: object) -> datetime:
        return parse_timestamp(value)


class FutureIntent(BaseModel):
    id: str
    ts: datetime
    loop_id: Optional[str] = None
    intent: str
    confidence: Optional[float] = None
    expected_impact: Optional[Dict[str, object]] = None
    requirements: List[str] = Field(default_factory=list)
    dependencies: List[str] = Field(default_factory=list)
    eta_hint: Optional[str] = None

    @validator("ts", pre=True)
    def _parse_ts(cls, value: object) -> datetime:
        return parse_timestamp(value)


class Capsule(BaseModel):
    capsule_id: str
    capsule: Dict[str, object]
    scores: Dict[str, object]
    decision_ts: datetime

    @validator("decision_ts", pre=True)
    def _parse_ts(cls, value: object) -> datetime:
        return parse_timestamp(value)
