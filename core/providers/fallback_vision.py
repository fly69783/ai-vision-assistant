"""本地视觉模型优先、云端模型可选降级的组合适配器。"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from core.domain.enums import ProviderName
from core.domain.models import AnalysisContext, ProviderResult
from core.providers.base import AnalysisProvider


class FallbackVisionProvider(AnalysisProvider):
    name = ProviderName.VISION

    def __init__(self, primary: AnalysisProvider, fallback: AnalysisProvider) -> None:
        self.primary = primary
        self.fallback = fallback
        self.timeout_seconds = max(
            float(getattr(primary, "timeout_seconds", 0)),
            float(getattr(fallback, "timeout_seconds", 0)),
        )

    @property
    def configured(self) -> bool:
        return self.primary.configured or self.fallback.configured

    @property
    def status_message(self) -> str:
        if self.primary.configured and self.fallback.configured:
            return "本地 Qwen3-VL 优先；本地失败时允许使用云端 GLM 降级。"
        if self.primary.configured:
            return self.primary.status_message
        if self.fallback.configured:
            return f"本地模型未启用；{self.fallback.status_message}"
        return "本地 Qwen3-VL 与云端 GLM 均未配置。"

    async def analyze(
        self,
        image: NDArray[np.uint8],
        context: AnalysisContext,
    ) -> ProviderResult:
        primary_error: Exception | None = None
        if self.primary.configured:
            try:
                return await self.primary.analyze(image, context)
            except Exception as exc:  # noqa: BLE001 - 组合适配器负责明确降级
                primary_error = exc

        if self.fallback.configured:
            result = await self.fallback.analyze(image, context)
            warning = (
                f"本地视觉模型运行失败（{type(primary_error).__name__}），已使用云端 GLM。"
                if primary_error
                else "本地视觉模型未启用，已使用云端 GLM。"
            )
            return result.model_copy(update={"warnings": [warning, *result.warnings]})

        warning = self.status_message
        if primary_error:
            warning = f"本地视觉模型运行失败：{type(primary_error).__name__}；云端降级未配置。"
        return ProviderResult(provider=self.name, configured=False, warnings=[warning])
