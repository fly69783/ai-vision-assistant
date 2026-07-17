from pathlib import Path

import pytest

from core.config import SettingsError, load_settings


def test_load_default_settings() -> None:
    settings = load_settings()

    assert settings.version == "0.4.0"
    assert settings.server.port == 8000
    assert sum(settings.fusion.as_dict().values()) == pytest.approx(1.0)


def test_environment_overrides_server_limits(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AI_VISION_PORT", "8123")
    monkeypatch.setenv("AI_VISION_MAX_IMAGE_PIXELS", "12000000")
    monkeypatch.setenv("AI_VISION_VISION_ENABLED", "true")
    monkeypatch.setenv("AI_VISION_VISION_MAX_TOKENS", "256")
    monkeypatch.setenv("AI_VISION_DETECTOR_ENABLED", "true")
    monkeypatch.setenv("AI_VISION_DETECTOR_MIN_CONFIDENCE", "0.4")
    monkeypatch.setenv("AI_VISION_OCR_ENABLED", "true")
    monkeypatch.setenv("AI_VISION_OCR_MIN_CONFIDENCE", "0.6")

    settings = load_settings()
    assert settings.server.port == 8123
    assert settings.server.max_image_pixels == 12_000_000
    assert settings.providers.vision_enabled is True
    assert settings.providers.vision_max_tokens == 256
    assert settings.providers.detector_enabled is True
    assert settings.providers.detector_min_confidence == 0.4
    assert settings.providers.ocr_enabled is True
    assert settings.providers.ocr_min_confidence == 0.6


def test_invalid_boolean_environment_has_clear_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AI_VISION_VISION_ENABLED", "maybe")

    with pytest.raises(SettingsError, match="true 或 false"):
        load_settings()


def test_missing_config_has_clear_error(tmp_path: Path) -> None:
    with pytest.raises(SettingsError, match="找不到配置文件"):
        load_settings(tmp_path / "missing.yaml")


def test_invalid_float_environment_has_clear_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AI_VISION_OCR_MIN_CONFIDENCE", "high")

    with pytest.raises(SettingsError, match="必须是数字"):
        load_settings()
