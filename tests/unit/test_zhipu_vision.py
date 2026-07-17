from __future__ import annotations

import asyncio
import json
from dataclasses import replace

import httpx
import pytest

from core.domain.enums import EvidenceKind, ProviderName, TaskType
from core.domain.models import AnalysisContext
from core.providers.zhipu_vision import ZhipuVisionProvider


def test_zhipu_provider_converts_json_response_to_evidence(settings, sharp_image) -> None:
    provider_settings = replace(
        settings.providers,
        vision_enabled=True,
        vision_model="glm-4.5v",
    )

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer test-api-key"
        body = json.loads(request.content)
        assert body["model"] == "glm-4.5v"
        assert body["thinking"] == {"type": "disabled"}
        assert body["messages"][1]["content"][0]["type"] == "image_url"
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "content": "画面中是一间教室，前方有桌椅。",
                                    "confidence": 0.88,
                                    "position": "画面中央",
                                    "warnings": [],
                                },
                                ensure_ascii=False,
                            )
                        }
                    }
                ]
            },
        )

    provider = ZhipuVisionProvider(
        provider_settings,
        api_key="test-api-key",
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
    assert result.evidence[0].confidence == 0.88
    assert result.evidence[0].position == "画面中央"
    assert result.evidence[0].metadata["model"] == "glm-4.5v"


def test_zhipu_provider_without_key_stays_unconfigured(settings, sharp_image) -> None:
    provider = ZhipuVisionProvider(replace(settings.providers, vision_enabled=True))

    result = asyncio.run(
        provider.analyze(
            sharp_image,
            AnalysisContext(task=TaskType.VISUAL_QUESTION, query="这里是什么地方？"),
        )
    )

    assert provider.configured is False
    assert result.configured is False
    assert result.evidence == []
    assert "未配置环境变量" in result.warnings[0]


def test_zhipu_provider_preserves_non_json_text_with_warning(settings, sharp_image) -> None:
    provider_settings = replace(settings.providers, vision_enabled=True)

    def handler(request: httpx.Request) -> httpx.Response:
        del request
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "可能是一扇门。"}}]},
        )

    provider = ZhipuVisionProvider(
        provider_settings,
        api_key="test-api-key",
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
    assert "未返回标准JSON" in result.warnings[0]


def test_zhipu_provider_disabled_reports_status(settings, sharp_image) -> None:
    provider = ZhipuVisionProvider(settings.providers, api_key="test-api-key")

    result = asyncio.run(
        provider.analyze(
            sharp_image,
            AnalysisContext(task=TaskType.READ_TEXT),
        )
    )

    assert provider.configured is False
    assert provider.status_message == "视觉理解尚未启用。"
    assert result.configured is False


def test_zhipu_provider_parses_code_fence_and_sanitizes_fields(settings, sharp_image) -> None:
    provider_settings = replace(settings.providers, vision_enabled=True)
    response_content = """```json
{"content":"出口","confidence":"not-a-number","position":"画面上方","warnings":["字迹较小",""]}
```"""

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert "只抄录" in body["messages"][1]["content"][1]["text"]
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": response_content}}]},
        )

    provider = ZhipuVisionProvider(
        provider_settings,
        api_key="test-api-key",
        transport=httpx.MockTransport(handler),
    )
    result = asyncio.run(
        provider.analyze(
            sharp_image,
            AnalysisContext(task=TaskType.READ_TEXT),
        )
    )

    assert result.evidence[0].kind is EvidenceKind.TEXT
    assert result.evidence[0].confidence == 0.5
    assert result.warnings == ["字迹较小"]


def test_zhipu_provider_handles_empty_structured_result(settings, sharp_image) -> None:
    provider_settings = replace(settings.providers, vision_enabled=True)

    def handler(request: httpx.Request) -> httpx.Response:
        del request
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": '{"content":"","confidence":2,"warnings":"none"}'
                        }
                    }
                ]
            },
        )

    provider = ZhipuVisionProvider(
        provider_settings,
        api_key="test-api-key",
        transport=httpx.MockTransport(handler),
    )
    result = asyncio.run(
        provider.analyze(
            sharp_image,
            AnalysisContext(task=TaskType.VISUAL_QUESTION, query="这是什么？"),
        )
    )

    assert result.evidence == []
    assert result.warnings == ["视觉模型未返回可用文本。"]


def test_zhipu_provider_rejects_non_text_content(settings, sharp_image) -> None:
    provider_settings = replace(settings.providers, vision_enabled=True)

    def handler(request: httpx.Request) -> httpx.Response:
        del request
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": ["unexpected"]}}]},
        )

    provider = ZhipuVisionProvider(
        provider_settings,
        api_key="test-api-key",
        transport=httpx.MockTransport(handler),
    )
    with pytest.raises(ValueError, match="content不是文本"):
        asyncio.run(
            provider.analyze(
                sharp_image,
                AnalysisContext(task=TaskType.SCENE_DESCRIPTION),
            )
        )
