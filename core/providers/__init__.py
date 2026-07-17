"""真实AI模型的可替换接入层。"""

from core.providers.base import AnalysisProvider
from core.providers.rapidocr_provider import RapidOCRProvider
from core.providers.registry import ProviderRegistry, build_default_registry
from core.providers.torchvision_detector import TorchvisionDetectorProvider
from core.providers.zhipu_vision import ZhipuVisionProvider

__all__ = [
    "AnalysisProvider",
    "ProviderRegistry",
    "RapidOCRProvider",
    "TorchvisionDetectorProvider",
    "ZhipuVisionProvider",
    "build_default_registry",
]
