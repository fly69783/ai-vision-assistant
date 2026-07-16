"""集中管理检测、OCR和视觉理解适配器。"""

from __future__ import annotations

from collections.abc import Iterable

from core.config.settings import AppSettings
from core.domain.enums import ProviderName, TaskType
from core.domain.models import CapabilityStatus
from core.providers.base import AnalysisProvider
from core.providers.unavailable import UnavailableProvider


class ProviderRegistry:
    def __init__(self, providers: Iterable[AnalysisProvider]) -> None:
        self._providers = {provider.name: provider for provider in providers}
        missing = set(ProviderName) - set(self._providers)
        if missing:
            names = ", ".join(sorted(item.value for item in missing))
            raise ValueError(f"缺少能力适配器：{names}")

    def get(self, name: ProviderName) -> AnalysisProvider:
        return self._providers[name]

    def capabilities(self) -> list[CapabilityStatus]:
        return [self._providers[name].capability() for name in ProviderName]

    def for_task(self, task: TaskType) -> list[AnalysisProvider]:
        mapping = {
            TaskType.SCENE_DESCRIPTION: [
                ProviderName.DETECTOR,
                ProviderName.OCR,
                ProviderName.VISION,
            ],
            TaskType.READ_TEXT: [ProviderName.OCR],
            TaskType.FIND_OBJECT: [ProviderName.DETECTOR, ProviderName.VISION],
            TaskType.VISUAL_QUESTION: [ProviderName.VISION],
        }
        return [self.get(name) for name in mapping[task]]


def _reason(name: str, enabled: bool) -> str:
    if enabled:
        return f"{name}已在配置中启用，但真实模型适配器尚未接入。"
    return f"{name}尚未启用。"


def build_default_registry(settings: AppSettings) -> ProviderRegistry:
    """构建安全的默认注册表；所有能力都明确处于未配置状态。"""

    return ProviderRegistry(
        [
            UnavailableProvider(
                ProviderName.DETECTOR,
                _reason("目标检测", settings.providers.detector_enabled),
            ),
            UnavailableProvider(
                ProviderName.OCR,
                _reason("OCR", settings.providers.ocr_enabled),
            ),
            UnavailableProvider(
                ProviderName.VISION,
                _reason("视觉理解", settings.providers.vision_enabled),
            ),
        ]
    )
