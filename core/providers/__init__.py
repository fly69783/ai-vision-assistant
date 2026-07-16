"""真实AI模型的可替换接入层。"""

from core.providers.base import AnalysisProvider
from core.providers.registry import ProviderRegistry, build_default_registry

__all__ = ["AnalysisProvider", "ProviderRegistry", "build_default_registry"]
