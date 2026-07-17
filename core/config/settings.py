"""从YAML和环境变量读取项目配置。

本模块只处理非敏感配置。API密钥等敏感信息应通过环境变量交给具体模型适配器。
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


class SettingsError(ValueError):
    """配置缺失或配置值不合法。"""


@dataclass(frozen=True)
class ServerSettings:
    host: str = "127.0.0.1"
    port: int = 8000
    log_level: str = "INFO"
    max_upload_mb: int = 8
    max_image_pixels: int = 25_000_000
    allowed_mime_types: tuple[str, ...] = ("image/jpeg", "image/png", "image/webp")


@dataclass(frozen=True)
class QualitySettings:
    min_width: int = 320
    min_height: int = 240
    min_brightness: float = 25.0
    max_brightness: float = 240.0
    min_blur_score: float = 20.0


@dataclass(frozen=True)
class FusionSettings:
    task_relevance: float = 0.35
    importance: float = 0.25
    confidence: float = 0.20
    novelty: float = 0.10
    position: float = 0.10

    def as_dict(self) -> dict[str, float]:
        return {
            "task_relevance": self.task_relevance,
            "importance": self.importance,
            "confidence": self.confidence,
            "novelty": self.novelty,
            "position": self.position,
        }


@dataclass(frozen=True)
class NarrationSettings:
    max_items: int = 3
    low_confidence_threshold: float = 0.55
    unavailable_message: str = "当前任务所需的AI能力尚未配置。"


@dataclass(frozen=True)
class ProviderSettings:
    detector_enabled: bool = False
    ocr_enabled: bool = False
    vision_enabled: bool = False
    timeout_seconds: float = 25.0
    vision_model: str = "glm-4.5v"
    vision_api_url: str = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
    vision_api_key_env: str = "AI_VISION_ZHIPU_API_KEY"
    vision_max_tokens: int = 512
    vision_backend: str = "zhipu"
    local_vision_enabled: bool = False
    local_vision_model: str = "qwen3-vl:4b-instruct-q4_K_M"
    local_vision_api_url: str = "http://127.0.0.1:11434/api/chat"
    local_vision_timeout_seconds: float = 120.0
    local_vision_keep_alive: str = "5m"
    detector_model: str = "ssdlite320_mobilenet_v3_large"
    detector_min_confidence: float = 0.45
    detector_max_results: int = 10
    ocr_model: str = "PP-OCRv6-small"
    ocr_min_confidence: float = 0.55
    ocr_max_lines: int = 12


@dataclass(frozen=True)
class AppSettings:
    name: str = "AI视觉辅助盲人环境理解系统"
    version: str = "0.5.0"
    environment: str = "development"
    api_prefix: str = "/api/v1"
    server: ServerSettings = field(default_factory=ServerSettings)
    quality: QualitySettings = field(default_factory=QualitySettings)
    fusion: FusionSettings = field(default_factory=FusionSettings)
    narration: NarrationSettings = field(default_factory=NarrationSettings)
    providers: ProviderSettings = field(default_factory=ProviderSettings)


def project_root() -> Path:
    """返回仓库根目录。"""

    return Path(__file__).resolve().parents[2]


def _section(data: dict[str, Any], name: str) -> dict[str, Any]:
    value = data.get(name, {})
    if not isinstance(value, dict):
        raise SettingsError(f"配置项 {name!r} 必须是对象。")
    return value


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise SettingsError(f"环境变量 {name} 必须是整数。") from exc


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    normalized = raw.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise SettingsError(f"环境变量 {name} 必须是 true 或 false。")


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError as exc:
        raise SettingsError(f"环境变量 {name} 必须是数字。") from exc


def _validate(settings: AppSettings) -> None:
    if not settings.api_prefix.startswith("/"):
        raise SettingsError("api_prefix 必须以 / 开头。")
    if not 1 <= settings.server.port <= 65535:
        raise SettingsError("端口必须在1到65535之间。")
    if settings.server.max_upload_mb <= 0:
        raise SettingsError("max_upload_mb 必须大于0。")
    if settings.server.max_image_pixels <= 0:
        raise SettingsError("max_image_pixels 必须大于0。")
    if settings.quality.min_width <= 0 or settings.quality.min_height <= 0:
        raise SettingsError("最小图片尺寸必须大于0。")
    if settings.quality.min_brightness >= settings.quality.max_brightness:
        raise SettingsError("最低亮度必须小于最高亮度。")
    weights = settings.fusion.as_dict()
    if any(value < 0 for value in weights.values()):
        raise SettingsError("融合权重不能为负数。")
    if abs(sum(weights.values()) - 1.0) > 0.001:
        raise SettingsError("融合权重之和必须等于1。")
    if settings.narration.max_items <= 0:
        raise SettingsError("max_items 必须大于0。")
    if settings.providers.timeout_seconds <= 0:
        raise SettingsError("模型超时时间必须大于0。")
    if not settings.providers.vision_model.strip():
        raise SettingsError("vision_model 不能为空。")
    if not settings.providers.vision_api_url.startswith("https://"):
        raise SettingsError("vision_api_url 必须使用 https://。")
    if not settings.providers.vision_api_key_env.strip():
        raise SettingsError("vision_api_key_env 不能为空。")
    if settings.providers.vision_max_tokens <= 0:
        raise SettingsError("vision_max_tokens 必须大于0。")
    if settings.providers.vision_backend not in {"ollama", "zhipu", "hybrid"}:
        raise SettingsError("vision_backend 必须是 ollama、zhipu 或 hybrid。")
    if not settings.providers.local_vision_model.strip():
        raise SettingsError("local_vision_model 不能为空。")
    if not settings.providers.local_vision_api_url.startswith(
        ("http://127.0.0.1:", "http://localhost:")
    ):
        raise SettingsError("local_vision_api_url 只能使用本机 127.0.0.1 或 localhost。")
    if settings.providers.local_vision_timeout_seconds <= 0:
        raise SettingsError("local_vision_timeout_seconds 必须大于0。")
    if not 0 <= settings.providers.detector_min_confidence <= 1:
        raise SettingsError("detector_min_confidence 必须在0到1之间。")
    if settings.providers.detector_max_results <= 0:
        raise SettingsError("detector_max_results 必须大于0。")
    if not 0 <= settings.providers.ocr_min_confidence <= 1:
        raise SettingsError("ocr_min_confidence 必须在0到1之间。")
    if settings.providers.ocr_max_lines <= 0:
        raise SettingsError("ocr_max_lines 必须大于0。")


def load_settings(config_path: str | Path | None = None) -> AppSettings:
    """读取配置。

    优先级：环境变量 > 指定YAML > 默认YAML。
    """

    selected = Path(
        config_path
        or os.getenv("AI_VISION_CONFIG")
        or project_root() / "configs" / "default.yaml"
    )
    if not selected.exists():
        raise SettingsError(f"找不到配置文件：{selected}")

    with selected.open("r", encoding="utf-8") as handle:
        loaded = yaml.safe_load(handle) or {}
    if not isinstance(loaded, dict):
        raise SettingsError("配置文件顶层必须是对象。")

    app_data = _section(loaded, "app")
    server_data = _section(loaded, "server")
    quality_data = _section(loaded, "quality")
    fusion_data = _section(loaded, "fusion")
    narration_data = _section(loaded, "narration")
    provider_data = _section(loaded, "providers")

    server = ServerSettings(
        host=os.getenv("AI_VISION_HOST", str(server_data.get("host", "127.0.0.1"))),
        port=_env_int("AI_VISION_PORT", int(server_data.get("port", 8000))),
        log_level=os.getenv("AI_VISION_LOG_LEVEL", str(server_data.get("log_level", "INFO"))),
        max_upload_mb=_env_int(
            "AI_VISION_MAX_UPLOAD_MB", int(server_data.get("max_upload_mb", 8))
        ),
        max_image_pixels=_env_int(
            "AI_VISION_MAX_IMAGE_PIXELS",
            int(server_data.get("max_image_pixels", 25_000_000)),
        ),
        allowed_mime_types=tuple(
            str(item)
            for item in server_data.get(
                "allowed_mime_types", ["image/jpeg", "image/png", "image/webp"]
            )
        ),
    )
    settings = AppSettings(
        name=str(app_data.get("name", "AI视觉辅助盲人环境理解系统")),
        version=str(app_data.get("version", "0.5.0")),
        environment=os.getenv(
            "AI_VISION_ENVIRONMENT", str(app_data.get("environment", "development"))
        ),
        api_prefix=str(app_data.get("api_prefix", "/api/v1")),
        server=server,
        quality=QualitySettings(**quality_data),
        fusion=FusionSettings(**fusion_data),
        narration=NarrationSettings(**narration_data),
        providers=ProviderSettings(
            detector_enabled=_env_bool(
                "AI_VISION_DETECTOR_ENABLED",
                bool(provider_data.get("detector_enabled", False)),
            ),
            ocr_enabled=_env_bool(
                "AI_VISION_OCR_ENABLED",
                bool(provider_data.get("ocr_enabled", False)),
            ),
            vision_enabled=_env_bool(
                "AI_VISION_VISION_ENABLED",
                bool(provider_data.get("vision_enabled", False)),
            ),
            timeout_seconds=float(provider_data.get("timeout_seconds", 25.0)),
            vision_model=os.getenv(
                "AI_VISION_VISION_MODEL",
                str(provider_data.get("vision_model", "glm-4.5v")),
            ),
            vision_api_url=os.getenv(
                "AI_VISION_VISION_API_URL",
                str(
                    provider_data.get(
                        "vision_api_url",
                        "https://open.bigmodel.cn/api/paas/v4/chat/completions",
                    )
                ),
            ),
            vision_api_key_env=str(
                provider_data.get("vision_api_key_env", "AI_VISION_ZHIPU_API_KEY")
            ),
            vision_max_tokens=_env_int(
                "AI_VISION_VISION_MAX_TOKENS",
                int(provider_data.get("vision_max_tokens", 512)),
            ),
            vision_backend=os.getenv(
                "AI_VISION_VISION_BACKEND",
                str(provider_data.get("vision_backend", "zhipu")),
            ).strip().lower(),
            local_vision_enabled=_env_bool(
                "AI_VISION_LOCAL_VISION_ENABLED",
                bool(provider_data.get("local_vision_enabled", False)),
            ),
            local_vision_model=os.getenv(
                "AI_VISION_LOCAL_VISION_MODEL",
                str(
                    provider_data.get(
                        "local_vision_model", "qwen3-vl:4b-instruct-q4_K_M"
                    )
                ),
            ),
            local_vision_api_url=os.getenv(
                "AI_VISION_LOCAL_VISION_API_URL",
                str(
                    provider_data.get(
                        "local_vision_api_url", "http://127.0.0.1:11434/api/chat"
                    )
                ),
            ),
            local_vision_timeout_seconds=_env_float(
                "AI_VISION_LOCAL_VISION_TIMEOUT_SECONDS",
                float(provider_data.get("local_vision_timeout_seconds", 120.0)),
            ),
            local_vision_keep_alive=os.getenv(
                "AI_VISION_LOCAL_VISION_KEEP_ALIVE",
                str(provider_data.get("local_vision_keep_alive", "5m")),
            ),
            detector_model=str(
                provider_data.get("detector_model", "ssdlite320_mobilenet_v3_large")
            ),
            detector_min_confidence=_env_float(
                "AI_VISION_DETECTOR_MIN_CONFIDENCE",
                float(provider_data.get("detector_min_confidence", 0.45)),
            ),
            detector_max_results=_env_int(
                "AI_VISION_DETECTOR_MAX_RESULTS",
                int(provider_data.get("detector_max_results", 10)),
            ),
            ocr_model=str(provider_data.get("ocr_model", "PP-OCRv6-small")),
            ocr_min_confidence=_env_float(
                "AI_VISION_OCR_MIN_CONFIDENCE",
                float(provider_data.get("ocr_min_confidence", 0.55)),
            ),
            ocr_max_lines=_env_int(
                "AI_VISION_OCR_MAX_LINES",
                int(provider_data.get("ocr_max_lines", 12)),
            ),
        ),
    )
    _validate(settings)
    return settings
