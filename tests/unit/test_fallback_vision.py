from __future__ import annotations

import asyncio
from dataclasses import replace

import numpy as np
from numpy.typing import NDArray

from core.domain.enums import EvidenceKind, ProviderName, TaskType
from core.domain.models import AnalysisContext, Evidence, ProviderResult
from core.providers.base import AnalysisProvider
from core.providers.fallback_vision import FallbackVisionProvider
from core.providers.ollama_vision import OllamaVisionProvider
from core.providers.registry import build_default_registry
from core.providers.zhipu_vision import ZhipuVisionProvider


class StubVisionProvider(AnalysisProvider):
    name = ProviderName.VISION

    def __init__(self, *, configured: bool, fail: bool = False, label: str = "结果") -> None:
        self._configured = configured
        self.fail = fail
        self.label = label
        self.calls = 0

    @property
    def configured(self) -> bool:
        return self._configured

    @property
    def status_message(self) -> str:
        return self.label

    async def analyze(
        self,
        image: NDArray[np.uint8],
        context: AnalysisContext,
    ) -> ProviderResult:
        del image, context
        self.calls += 1
        if self.fail:
            raise httpx_error()
        return ProviderResult(
            provider=self.name,
            configured=True,
            evidence=[
                Evidence(
                    source=self.name,
                    kind=EvidenceKind.SCENE,
                    content=self.label,
                )
            ],
        )


def httpx_error() -> RuntimeError:
    return RuntimeError("local service unavailable")


def test_hybrid_uses_local_result_without_calling_cloud(sharp_image) -> None:
    local = StubVisionProvider(configured=True, label="本地结果")
    cloud = StubVisionProvider(configured=True, label="云端结果")
    provider = FallbackVisionProvider(local, cloud)

    result = asyncio.run(
        provider.analyze(
            sharp_image,
            AnalysisContext(task=TaskType.SCENE_DESCRIPTION),
        )
    )

    assert result.evidence[0].content == "本地结果"
    assert local.calls == 1
    assert cloud.calls == 0


def test_hybrid_falls_back_to_cloud_with_explicit_warning(sharp_image) -> None:
    local = StubVisionProvider(configured=True, fail=True, label="本地")
    cloud = StubVisionProvider(configured=True, label="云端结果")
    provider = FallbackVisionProvider(local, cloud)

    result = asyncio.run(
        provider.analyze(
            sharp_image,
            AnalysisContext(task=TaskType.SCENE_DESCRIPTION),
        )
    )

    assert result.evidence[0].content == "云端结果"
    assert "已使用云端 GLM" in result.warnings[0]
    assert cloud.calls == 1


def test_hybrid_reports_unavailable_when_neither_is_configured(sharp_image) -> None:
    provider = FallbackVisionProvider(
        StubVisionProvider(configured=False, label="本地"),
        StubVisionProvider(configured=False, label="云端"),
    )
    result = asyncio.run(
        provider.analyze(
            sharp_image,
            AnalysisContext(task=TaskType.SCENE_DESCRIPTION),
        )
    )

    assert result.configured is False
    assert "均未配置" in result.warnings[0]


def test_registry_selects_configured_vision_backend(settings) -> None:
    local_settings = replace(
        settings,
        providers=replace(settings.providers, vision_backend="ollama"),
    )
    cloud_settings = replace(
        settings,
        providers=replace(settings.providers, vision_backend="zhipu"),
    )
    hybrid_settings = replace(
        settings,
        providers=replace(settings.providers, vision_backend="hybrid"),
    )

    assert isinstance(
        build_default_registry(local_settings).get(ProviderName.VISION),
        OllamaVisionProvider,
    )
    assert isinstance(
        build_default_registry(cloud_settings).get(ProviderName.VISION),
        ZhipuVisionProvider,
    )
    assert isinstance(
        build_default_registry(hybrid_settings).get(ProviderName.VISION),
        FallbackVisionProvider,
    )
