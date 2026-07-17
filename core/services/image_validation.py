"""上传图片的轻量格式与尺寸校验。"""

from __future__ import annotations

import numpy as np


def detect_image_mime(content: bytes) -> str | None:
    """根据文件头识别当前支持的图片格式。"""

    if content.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return "image/webp"
    return None


def image_pixel_count(image: np.ndarray) -> int:
    """返回解码图片的像素总数。"""

    height, width = image.shape[:2]
    return int(height * width)
