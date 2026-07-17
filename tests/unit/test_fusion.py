from core.domain.enums import EvidenceKind, ProviderName
from core.domain.models import Evidence
from core.services.fusion import FusionService


def test_fusion_sorts_and_deduplicates(settings) -> None:
    low = Evidence(
        source=ProviderName.VISION,
        kind=EvidenceKind.OBJECT,
        content="右侧有水杯",
        confidence=0.4,
        task_relevance=0.9,
    )
    high = Evidence(
        source=ProviderName.DETECTOR,
        kind=EvidenceKind.OBJECT,
        content="右侧有水杯",
        confidence=0.9,
        task_relevance=1.0,
        importance=0.8,
    )
    other = Evidence(
        source=ProviderName.OCR,
        kind=EvidenceKind.TEXT,
        content="安全出口",
        confidence=0.95,
        task_relevance=0.2,
    )

    ranked = FusionService(settings.fusion).rank([low, other, high])

    assert len(ranked) == 2
    assert ranked[0].source is ProviderName.DETECTOR
    assert ranked[0].score >= ranked[1].score
