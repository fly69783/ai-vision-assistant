"""集中管理检测、OCR和视觉理解适配器。"""

from __future__ import annotations

from collections.abc import Iterable

from core.config.settings import AppSettings
from core.domain.enums import ProviderName, TaskType
from core.domain.models import CapabilityStatus
from core.providers.base import AnalysisProvider
from core.providers.rapidocr_provider import RapidOCRProvider
from core.providers.torchvision_detector import TorchvisionDetectorProvider
from core.providers.zhipu_vision import ZhipuVisionProvider


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
            TaskType.READ_TEXT: [ProviderName.OCR, ProviderName.VISION],
            TaskType.FIND_OBJECT: [ProviderName.DETECTOR, ProviderName.VISION],
            TaskType.VISUAL_QUESTION: [ProviderName.VISION],
        }
        return [self.get(name) for name in mapping[task]]


def build_default_registry(settings: AppSettings) -> ProviderRegistry:
    """根据配置构建能力注册表；没有密钥的能力保持未配置。"""

    return ProviderRegistry(
        [
            TorchvisionDetectorProvider(settings.providers),
            RapidOCRProvider(settings.providers),
            ZhipuVisionProvider(settings.providers),
        ]
    )
