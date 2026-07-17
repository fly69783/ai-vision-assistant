from core.domain.enums import EvidenceKind, ProviderName
from core.domain.models import Evidence
from core.services.narration import NarrationService


def test_low_confidence_uses_uncertain_wording(settings) -> None:
    evidence = Evidence(
        source=ProviderName.DETECTOR,
        kind=EvidenceKind.OBJECT,
        content="有一把椅子",
        confidence=0.3,
        position="画面左侧",
    )

    text = NarrationService(settings.narration).from_evidence([evidence])

    assert text == "可能画面左侧，有一把椅子。"


def test_narration_respects_item_limit(settings) -> None:
    evidence = [
        Evidence(
            source=ProviderName.VISION,
            kind=EvidenceKind.SCENE,
            content=f"信息{i}",
            confidence=0.9,
        )
        for i in range(5)
    ]

    text = NarrationService(settings.narration).from_evidence(evidence)

    assert text.count("。") == settings.narration.max_items
