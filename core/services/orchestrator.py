"""将画面质量、AI能力、融合和播报串成一次完整任务。"""

from __future__ import annotations

import asyncio
import logging
from time import perf_counter

import numpy as np
from numpy.typing import NDArray

from core.config.settings import AppSettings
from core.domain.enums import AnalysisStatus, QualityStatus, TaskType
from core.domain.models import AnalysisContext, AnalysisResponse, ProviderResult
from core.providers.base import AnalysisProvider
from core.providers.registry import ProviderRegistry
from core.services.fusion import FusionService
from core.services.image_quality import ImageQualityService
from core.services.narration import NarrationService

logger = logging.getLogger(__name__)


class AnalysisOrchestrator:
    def __init__(self, settings: AppSettings, providers: ProviderRegistry) -> None:
        self.settings = settings
        self.providers = providers
        self.quality_service = ImageQualityService(settings.quality)
        self.fusion_service = FusionService(settings.fusion)
        self.narration_service = NarrationService(settings.narration)

    async def _run_provider(
        self,
        provider: AnalysisProvider,
        image: NDArray[np.uint8],
        context: AnalysisContext,
    ) -> ProviderResult:
        started = perf_counter()
        try:
            result = await asyncio.wait_for(
                provider.analyze(image, context),
                timeout=self.settings.providers.timeout_seconds,
            )
            return result.model_copy(
                update={"latency_ms": round((perf_counter() - started) * 1000, 2)}
            )
        except TimeoutError:
            message = f"{provider.name.value}处理超时。"
            logger.warning(message)
            return ProviderResult(
                provider=provider.name,
                configured=provider.configured,
                warnings=[message],
                latency_ms=round((perf_counter() - started) * 1000, 2),
            )
        except Exception as exc:  # noqa: BLE001 - 适配器错误必须转为安全响应
            logger.exception("能力适配器运行失败：%s", provider.name.value)
            return ProviderResult(
                provider=provider.name,
                configured=provider.configured,
                warnings=[f"{provider.name.value}运行失败：{type(exc).__name__}"],
                latency_ms=round((perf_counter() - started) * 1000, 2),
            )

    async def analyze(
        self,
        image: NDArray[np.uint8],
        task: TaskType,
        query: str | None = None,
        target: str | None = None,
    ) -> AnalysisResponse:
        started = perf_counter()
        context = AnalysisContext(task=task, query=query, target=target)
        quality = self.quality_service.inspect(image)
        capabilities = self.providers.capabilities()

        if quality.status is QualityStatus.REJECTED:
            return AnalysisResponse(
                status=AnalysisStatus.REJECTED,
                task=task,
                message="画面质量不符合分析条件。",
                narration=self.narration_service.from_quality_issues(quality.issues),
                quality=quality,
                warnings=quality.issues,
                capabilities=capabilities,
                latency_ms=round((perf_counter() - started) * 1000, 2),
            )

        selected = self.providers.for_task(task)
        results = await asyncio.gather(
            *(self._run_provider(provider, image, context) for provider in selected)
        )
        warnings = list(dict.fromkeys(warning for result in results for warning in result.warnings))
        ranked = self.fusion_service.rank(
            [item for result in results for item in result.evidence]
        )
        any_configured = any(result.configured for result in results)

        if ranked:
            status = AnalysisStatus.PARTIAL if warnings else AnalysisStatus.SUCCESS
            message = "分析完成，但部分能力有提示。" if warnings else "分析完成。"
            narration = self.narration_service.from_evidence(ranked)
        elif any_configured:
            status = AnalysisStatus.NO_RESULT
            message = "已运行配置的能力，但没有得到足够可靠的结果。"
            narration = "暂时没有发现可靠结果，请调整角度后重试。"
        else:
            status = AnalysisStatus.UNAVAILABLE
            message = self.settings.narration.unavailable_message
            narration = self.settings.narration.unavailable_message

        latency_ms = round((perf_counter() - started) * 1000, 2)
        logger.info(
            "analysis task=%s status=%s evidence=%d latency_ms=%.2f",
            task.value,
            status.value,
            len(ranked),
            latency_ms,
        )
        return AnalysisResponse(
            status=status,
            task=task,
            message=message,
            narration=narration,
            quality=quality,
            evidence=ranked,
            warnings=warnings,
            capabilities=capabilities,
            latency_ms=latency_ms,
        )
