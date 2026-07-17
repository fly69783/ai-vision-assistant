"""在调用模型前检查图片是否过小、过暗、过亮或明显模糊。"""

from __future__ import annotations

import cv2
import numpy as np
from numpy.typing import NDArray

from core.config.settings import QualitySettings
from core.domain.enums import QualityStatus
from core.domain.models import ImageQuality


class ImageQualityService:
    def __init__(self, settings: QualitySettings) -> None:
        self.settings = settings

    def inspect(self, image: NDArray[np.uint8]) -> ImageQuality:
        if image.size == 0 or image.ndim not in (2, 3):
            raise ValueError("图片数组为空或维度不正确。")

        height, width = image.shape[:2]
        gray = image if image.ndim == 2 else cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        brightness = float(np.mean(gray))
        blur_score = float(cv2.Laplacian(gray, cv2.CV_64F).var())

        issues: list[str] = []
        if width < self.settings.min_width or height < self.settings.min_height:
            issues.append(
                f"图片尺寸过小，至少需要{self.settings.min_width}×{self.settings.min_height}像素。"
            )
        if brightness < self.settings.min_brightness:
            issues.append("画面太暗，请增加光线或靠近目标后重拍。")
        if brightness > self.settings.max_brightness:
            issues.append("画面过亮，请避开强光或反光后重拍。")
        if blur_score < self.settings.min_blur_score:
            issues.append("画面可能模糊，请稳定设备后重拍。")

        return ImageQuality(
            status=QualityStatus.REJECTED if issues else QualityStatus.ACCEPTED,
            width=width,
            height=height,
            brightness=round(brightness, 2),
            blur_score=round(blur_score, 2),
            issues=issues,
        )
