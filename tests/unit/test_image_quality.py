import numpy as np

from core.domain.enums import QualityStatus
from core.services.image_quality import ImageQualityService


def test_sharp_image_is_accepted(settings, sharp_image) -> None:
    result = ImageQualityService(settings.quality).inspect(sharp_image)

    assert result.status is QualityStatus.ACCEPTED
    assert result.issues == []


def test_dark_small_image_is_rejected(settings) -> None:
    image = np.zeros((100, 100, 3), dtype=np.uint8)

    result = ImageQualityService(settings.quality).inspect(image)

    assert result.status is QualityStatus.REJECTED
    assert any("尺寸过小" in item for item in result.issues)
    assert any("太暗" in item for item in result.issues)
