"""Pydantic schemas for Reflection Feed payloads."""
from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


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
    model_config = ConfigDict()

    task_id: str
    score: float
    vector: Optional[Dict[str, float]] = None


class DecisionSelection(BaseModel):
    model_config = ConfigDict()

    task_id: str
    reason: Optional[str] = None


class DecisionLog(BaseModel):
    model_config = ConfigDict(validate_by_name=True)

    id: str = Field(..., alias="id")
    ts: datetime
    loop_id: Optional[str] = None
    task_context: Optional[Dict[str, object]] = None
    candidates: List[DecisionCandidate] = Field(default_factory=list)
    selected: DecisionSelection
    priority_vector: Dict[str, float] = Field(default_factory=dict)
    selected_metric: Optional[str] = None
    trade_offs: List[str] = Field(default_factory=list)

    @field_validator("ts", mode="before")
    @classmethod
    def _parse_ts(cls, value: object) -> datetime:
        return parse_timestamp(value)


class LoopEval(BaseModel):
    model_config = ConfigDict()

    id: str
    ts: datetime
    loop_id: Optional[str] = None
    inputs: Optional[Dict[str, object]] = None
    actions: List[str] = Field(default_factory=list)
    outcome_score: Dict[str, object] = Field(default_factory=dict)
    self_eval: Dict[str, object] = Field(default_factory=dict)

    @field_validator("ts", mode="before")
    @classmethod
    def _parse_ts(cls, value: object) -> datetime:
        return parse_timestamp(value)


class FutureIntent(BaseModel):
    model_config = ConfigDict()

    id: str
    ts: datetime
    loop_id: Optional[str] = None
    intent: str
    confidence: Optional[float] = None
    expected_impact: Optional[Dict[str, object]] = None
    requirements: List[str] = Field(default_factory=list)
    dependencies: List[str] = Field(default_factory=list)
    eta_hint: Optional[str] = None

    @field_validator("ts", mode="before")
    @classmethod
    def _parse_ts(cls, value: object) -> datetime:
        return parse_timestamp(value)


class Capsule(BaseModel):
    model_config = ConfigDict()

    capsule_id: str
    capsule: Dict[str, object]
    scores: Dict[str, object]
    decision_ts: datetime

    @field_validator("decision_ts", mode="before")
    @classmethod
    def _parse_ts(cls, value: object) -> datetime:
        return parse_timestamp(value)


class CommentaryEntry(BaseModel):
    model_config = ConfigDict()

    id: str
    ts: datetime
    message: str
    channel: Optional[str] = Field(default="thought")
    level: Optional[str] = None
    metadata: Dict[str, object] = Field(default_factory=dict)

    @field_validator("ts", mode="before")
    @classmethod
    def _parse_ts(cls, value: object) -> datetime:
        return parse_timestamp(value)
