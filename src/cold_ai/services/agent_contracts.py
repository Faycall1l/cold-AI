from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, ValidationError


class SearchQueryResult(BaseModel):
    query: str = Field(min_length=3, max_length=180)


class RoutingDecision(BaseModel):
    routing_angle: str = Field(min_length=3, max_length=220)
    routing_cta: str = Field(min_length=5, max_length=280)


class RewriteResult(BaseModel):
    subject: str = Field(min_length=4, max_length=180)
    body: str = Field(min_length=40, max_length=4000)
    confidence: float = Field(ge=0.0, le=1.0)


class SupervisorReviewResult(BaseModel):
    status: Literal["approved", "needs_revision"]
    score: float = Field(ge=0.0, le=1.0)
    notes: str = Field(default="", max_length=1200)


class ReflectionResult(BaseModel):
    subject: str = Field(min_length=4, max_length=180)
    body: str = Field(min_length=40, max_length=4000)
    critique: str = Field(min_length=3, max_length=1200)
    confidence: float = Field(ge=0.0, le=1.0)


def validate_search_query(payload: dict | None) -> SearchQueryResult | None:
    if not isinstance(payload, dict):
        return None
    try:
        return SearchQueryResult.model_validate(payload)
    except ValidationError:
        return None


def validate_routing_decision(payload: dict | None) -> RoutingDecision | None:
    if not isinstance(payload, dict):
        return None
    try:
        return RoutingDecision.model_validate(payload)
    except ValidationError:
        return None


def validate_rewrite(payload: dict | None) -> RewriteResult | None:
    if not isinstance(payload, dict):
        return None
    try:
        return RewriteResult.model_validate(payload)
    except ValidationError:
        return None


def validate_supervisor_review(payload: dict | None) -> SupervisorReviewResult | None:
    if not isinstance(payload, dict):
        return None
    try:
        return SupervisorReviewResult.model_validate(payload)
    except ValidationError:
        return None


def validate_reflection(payload: dict | None) -> ReflectionResult | None:
    if not isinstance(payload, dict):
        return None
    try:
        return ReflectionResult.model_validate(payload)
    except ValidationError:
        return None
