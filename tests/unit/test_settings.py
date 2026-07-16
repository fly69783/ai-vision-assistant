from pathlib import Path

import pytest

from core.config import SettingsError, load_settings


def test_load_default_settings() -> None:
    settings = load_settings()

    assert settings.version == "0.2.0"
    assert settings.server.port == 8000
    assert sum(settings.fusion.as_dict().values()) == pytest.approx(1.0)


def test_environment_overrides_server_limits(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AI_VISION_PORT", "8123")
    monkeypatch.setenv("AI_VISION_MAX_IMAGE_PIXELS", "12000000")

    settings = load_settings()
    assert settings.server.port == 8123
    assert settings.server.max_image_pixels == 12_000_000


def test_missing_config_has_clear_error(tmp_path: Path) -> None:
    with pytest.raises(SettingsError, match="找不到配置文件"):
        load_settings(tmp_path / "missing.yaml")
