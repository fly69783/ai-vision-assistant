from __future__ import annotations

import asyncio

import numpy as np
from numpy.typing import NDArray

from core.domain.enums import (
    AnalysisStatus,
    EvidenceKind,
    ProviderName,
    TaskType,
)
from core.domain.models import AnalysisContext, Evidence, ProviderResult
from core.providers.base import AnalysisProvider
from core.providers.registry import ProviderRegistry, build_default_registry
from core.providers.unavailable import UnavailableProvider
from core.services.orchestrator import AnalysisOrchestrator


class FakeDetector(AnalysisProvider):
    name = ProviderName.DETECTOR

    @property
    def configured(self) -> bool:
        return True

    @property
    def status_message(self) -> str:
        return "测试检测器已配置。"

    async def analyze(
        self,
        image: NDArray[np.uint8],
        context: AnalysisContext,
    ) -> ProviderResult:
        del image, context
        return ProviderResult(
            provider=self.name,
            configured=True,
            evidence=[
                Evidence(
                    source=self.name,
                    kind=EvidenceKind.OBJECT,
                    content="发现水杯",
                    confidence=0.92,
                    task_relevance=1.0,
                    position="画面右侧",
                )
            ],
        )


def test_unconfigured_providers_return_honest_status(settings, sharp_image) -> None:
    orchestrator = AnalysisOrchestrator(settings, build_default_registry(settings))

    result = asyncio.run(orchestrator.analyze(sharp_image, TaskType.READ_TEXT))

    assert result.status is AnalysisStatus.UNAVAILABLE
    assert result.evidence == []
    assert "尚未配置" in result.message


def test_fake_provider_flows_through_fusion_and_narration(settings, sharp_image) -> None:
    registry = ProviderRegistry(
        [
            FakeDetector(),
            UnavailableProvider(ProviderName.OCR, "测试中未配置OCR。"),
            UnavailableProvider(ProviderName.VISION, "测试中未配置视觉理解。"),
        ]
    )
    orchestrator = AnalysisOrchestrator(settings, registry)

    result = asyncio.run(
        orchestrator.analyze(sharp_image, TaskType.FIND_OBJECT, target="水杯")
    )

    assert result.status is AnalysisStatus.PARTIAL
    assert result.evidence[0].content == "发现水杯"
    assert "画面右侧" in result.narration
