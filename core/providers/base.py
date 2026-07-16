"""所有检测、OCR和视觉模型适配器必须遵守的接口。"""

from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np
from numpy.typing import NDArray

from core.domain.enums import ProviderName
from core.domain.models import AnalysisContext, CapabilityStatus, ProviderResult


class AnalysisProvider(ABC):
    """AI能力适配器基类。

    后续接入真实模型时，新建子类并实现`analyze`，不要修改任务编排服务。
    """

    name: ProviderName

    @property
    @abstractmethod
    def configured(self) -> bool:
        """是否已经完成模型、密钥和运行环境配置。"""

    @property
    @abstractmethod
    def status_message(self) -> str:
        """给健康检查和前端显示的通俗状态说明。"""

    def capability(self) -> CapabilityStatus:
        return CapabilityStatus(
            provider=self.name,
            configured=self.configured,
            message=self.status_message,
        )

    @abstractmethod
    async def analyze(
        self,
        image: NDArray[np.uint8],
        context: AnalysisContext,
    ) -> ProviderResult:
        """分析一张已经解码的BGR图片。"""
