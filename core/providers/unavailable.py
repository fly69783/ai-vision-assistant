"""尚未接入真实模型时使用的明确占位实现。"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from core.domain.enums import ProviderName
from core.domain.models import AnalysisContext, ProviderResult
from core.providers.base import AnalysisProvider


class UnavailableProvider(AnalysisProvider):
    """返回“未配置”，绝不生成模拟识别结果。"""

    def __init__(self, name: ProviderName, reason: str) -> None:
        self.name = name
        self._reason = reason

    @property
    def configured(self) -> bool:
        return False

    @property
    def status_message(self) -> str:
        return self._reason

    async def analyze(
        self,
        image: NDArray[np.uint8],
        context: AnalysisContext,
    ) -> ProviderResult:
        del image, context
        return ProviderResult(
            provider=self.name,
            configured=False,
            warnings=[self._reason],
        )
