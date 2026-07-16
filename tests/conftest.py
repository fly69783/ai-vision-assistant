from __future__ import annotations

import numpy as np
import pytest

from core.config import AppSettings, load_settings


@pytest.fixture
def settings() -> AppSettings:
    return load_settings()


@pytest.fixture
def sharp_image() -> np.ndarray:
    """生成不含真实用户数据的高对比测试图。"""

    rows, columns = np.indices((480, 640))
    checkerboard = ((rows // 20 + columns // 20) % 2 * 255).astype(np.uint8)
    return np.repeat(checkerboard[:, :, None], 3, axis=2)
