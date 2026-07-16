from pathlib import Path

import pytest

from core.config import SettingsError, load_settings


def test_load_default_settings() -> None:
    settings = load_settings()

    assert settings.version == "0.1.0"
    assert settings.server.port == 8000
    assert sum(settings.fusion.as_dict().values()) == pytest.approx(1.0)


def test_environment_overrides_port(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AI_VISION_PORT", "8123")

    assert load_settings().server.port == 8123


def test_missing_config_has_clear_error(tmp_path: Path) -> None:
    with pytest.raises(SettingsError, match="找不到配置文件"):
        load_settings(tmp_path / "missing.yaml")
