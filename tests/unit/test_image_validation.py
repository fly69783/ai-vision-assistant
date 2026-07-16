from __future__ import annotations

import numpy as np

from core.services.image_validation import detect_image_mime, image_pixel_count


def test_detect_image_mime_recognizes_supported_headers() -> None:
    assert detect_image_mime(b"\xff\xd8\xffmore") == "image/jpeg"
    assert detect_image_mime(b"\x89PNG\r\n\x1a\nmore") == "image/png"
    assert detect_image_mime(b"RIFF\x04\x00\x00\x00WEBPmore") == "image/webp"


def test_detect_image_mime_rejects_unknown_header() -> None:
    assert detect_image_mime(b"not-an-image") is None


def test_image_pixel_count_uses_height_and_width() -> None:
    image = np.zeros((120, 240, 3), dtype=np.uint8)

    assert image_pixel_count(image) == 28_800
