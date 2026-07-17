"""跨模块传递的统一数据结构。"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from core.domain.enums import (
    AnalysisStatus,
    EvidenceKind,
    ProviderName,
    QualityStatus,
    TaskType,
)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class BoundingBox(StrictModel):
    """归一化坐标，左上角为(0, 0)，右下角为(1, 1)。"""

    x1: float = Field(ge=0, le=1)
    y1: float = Field(ge=0, le=1)
    x2: float = Field(ge=0, le=1)
    y2: float = Field(ge=0, le=1)


class AnalysisContext(StrictModel):
    task: TaskType
    query: str | None = Field(default=None, max_length=200)
    target: str | None = Field(default=None, max_length=80)


class ImageQuality(StrictModel):
    status: QualityStatus
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    brightness: float = Field(ge=0, le=255)
    blur_score: float = Field(ge=0)
    issues: list[str] = Field(default_factory=list)


class Evidence(StrictModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    source: ProviderName
    kind: EvidenceKind
    content: str = Field(min_length=1, max_length=500)
    confidence: float = Field(default=0.0, ge=0, le=1)
    task_relevance: float = Field(default=0.5, ge=0, le=1)
    importance: float = Field(default=0.5, ge=0, le=1)
    novelty: float = Field(default=1.0, ge=0, le=1)
    position_importance: float = Field(default=0.5, ge=0, le=1)
    position: str | None = Field(default=None, max_length=80)
    bbox: BoundingBox | None = None
    score: float = Field(default=0.0, ge=0, le=1)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ProviderResult(StrictModel):
    provider: ProviderName
    configured: bool
    evidence: list[Evidence] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    latency_ms: float = Field(default=0.0, ge=0)


class CapabilityStatus(StrictModel):
    provider: ProviderName
    configured: bool
    message: str


class AnalysisResponse(StrictModel):
    request_id: str = Field(default_factory=lambda: uuid4().hex)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    status: AnalysisStatus
    task: TaskType
    message: str
    narration: str
    quality: ImageQuality
    evidence: list[Evidence] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    capabilities: list[CapabilityStatus] = Field(default_factory=list)
    latency_ms: float = Field(ge=0)


class HealthResponse(StrictModel):
    status: str = "ok"
    service: str
    version: str
    environment: str
    capabilities: list[CapabilityStatus]
    safety_notice: str


class ApiError(StrictModel):
    code: str
    message: str
    detail: str | None = None
