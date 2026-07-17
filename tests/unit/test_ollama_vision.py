from __future__ import annotations

import asyncio
import json
from dataclasses import replace

import httpx
import pytest

from core.domain.enums import EvidenceKind, ProviderName, TaskType
from core.domain.models import AnalysisContext
from core.providers.ollama_vision import OllamaVisionProvider


def test_ollama_provider_converts_json_response_to_evidence(settings, sharp_image) -> None:
    provider_settings = replace(
        settings.providers,
        local_vision_enabled=True,
        local_vision_model="qwen3-vl:test",
    )

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url == "http://127.0.0.1:11434/api/chat"
        body = json.loads(request.content)
        assert body["model"] == "qwen3-vl:test"
        assert body["format"] == "json"
        assert body["stream"] is False
        assert body["keep_alive"] == "5m"
        assert len(body["messages"][1]["images"][0]) > 100
        return httpx.Response(
            200,
            json={
                "message": {
                    "content": json.dumps(
                        {
                            "content": "画面中是一只狗，位于草地中央。",
                            "confidence": 0.91,
                            "position": "画面中央",
                            "warnings": [],
                        },
                        ensure_ascii=False,
                    )
                }
            },
        )

    provider = OllamaVisionProvider(
        provider_settings,
        transport=httpx.MockTransport(handler),
    )
    result = asyncio.run(
        provider.analyze(
            sharp_image,
            AnalysisContext(task=TaskType.SCENE_DESCRIPTION),
        )
    )

    assert result.configured is True
    assert result.evidence[0].source is ProviderName.VISION
    assert result.evidence[0].kind is EvidenceKind.SCENE
    assert result.evidence[0].confidence == 0.91
    assert result.evidence[0].metadata["runtime"] == "ollama"
    assert result.evidence[0].metadata["model"] == "qwen3-vl:test"


def test_ollama_provider_disabled_does_not_call_service(settings, sharp_image) -> None:
    provider = OllamaVisionProvider(settings.providers)
    result = asyncio.run(
        provider.analyze(
            sharp_image,
            AnalysisContext(task=TaskType.READ_TEXT),
        )
    )

    assert provider.configured is False
    assert result.configured is False
    assert "尚未启用" in result.warnings[0]


def test_ollama_provider_preserves_plain_text_with_warning(settings, sharp_image) -> None:
    provider_settings = replace(settings.providers, local_vision_enabled=True)

    def handler(request: httpx.Request) -> httpx.Response:
        del request
        return httpx.Response(200, json={"message": {"content": "可能是一扇门。"}})

    provider = OllamaVisionProvider(
        provider_settings,
        transport=httpx.MockTransport(handler),
    )
    result = asyncio.run(
        provider.analyze(
            sharp_image,
            AnalysisContext(task=TaskType.FIND_OBJECT, target="门"),
        )
    )

    assert result.evidence[0].content == "可能是一扇门。"
    assert result.evidence[0].confidence == 0.5
    assert "标准JSON" in result.warnings[0]


def test_ollama_provider_rejects_non_text_content(settings, sharp_image) -> None:
    provider_settings = replace(settings.providers, local_vision_enabled=True)

    def handler(request: httpx.Request) -> httpx.Response:
        del request
        return httpx.Response(200, json={"message": {"content": ["unexpected"]}})

    provider = OllamaVisionProvider(
        provider_settings,
        transport=httpx.MockTransport(handler),
    )
    with pytest.raises(ValueError, match="content 不是文本"):
        asyncio.run(
            provider.analyze(
                sharp_image,
                AnalysisContext(task=TaskType.VISUAL_QUESTION, query="这是什么？"),
            )
        )
