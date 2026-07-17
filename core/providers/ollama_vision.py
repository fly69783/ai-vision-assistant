"""通过本机 Ollama 调用 Qwen3-VL 的视觉理解适配器。"""

from __future__ import annotations

import base64
import json
from typing import Any

import cv2
import httpx
import numpy as np
from numpy.typing import NDArray

from core.config.settings import ProviderSettings
from core.domain.enums import EvidenceKind, ProviderName, TaskType
from core.domain.models import AnalysisContext, Evidence, ProviderResult
from core.providers.base import AnalysisProvider

_SYSTEM_PROMPT = """你是面向视障用户的环境理解辅助模块。只描述图片中有直接视觉证据的事实。
不要猜测人物身份、情绪、精确距离或画面外信息，不得承诺道路、楼梯或通行安全。
不确定时必须明确说“不确定”或“可能”。只返回一个JSON对象，不要使用Markdown代码块。
JSON字段必须是：content（简短中文结果）、confidence（0到1）、position（可为空）、warnings（字符串数组）。"""


class OllamaVisionProvider(AnalysisProvider):
    """调用只监听本机回环地址的 Ollama Qwen3-VL 模型。"""

    name = ProviderName.VISION

    def __init__(
        self,
        settings: ProviderSettings,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.settings = settings
        self._transport = transport
        self.timeout_seconds = settings.local_vision_timeout_seconds

    @property
    def configured(self) -> bool:
        return self.settings.local_vision_enabled

    @property
    def status_message(self) -> str:
        if not self.settings.local_vision_enabled:
            return "本地 Qwen3-VL 视觉理解尚未启用。"
        return (
            f"本地模型 {self.settings.local_vision_model} 已配置；"
            "图片仅发送到本机 Ollama。"
        )

    def _task_prompt(self, context: AnalysisContext) -> str:
        prompts = {
            TaskType.SCENE_DESCRIPTION: (
                "概括当前环境。先说明场景类型和主要物体，再说明与用户当前行动有关的信息，"
                "最多3句。"
            ),
            TaskType.READ_TEXT: (
                "只抄录图片中能够清楚确认的文字，按照自然阅读顺序输出。"
                "看不清的部分不要补写。"
            ),
            TaskType.FIND_OBJECT: (
                f"查找目标物品：{context.target}。说明是否看见，以及它在画面中的大致位置。"
            ),
            TaskType.VISUAL_QUESTION: f"根据图片回答问题：{context.query}",
        }
        return prompts[context.task]

    @staticmethod
    def _encode_image(image: NDArray[np.uint8]) -> str:
        success, encoded = cv2.imencode(
            ".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, 88]
        )
        if not success:
            raise ValueError("图片编码失败。")
        return base64.b64encode(encoded.tobytes()).decode("ascii")

    def _request_body(
        self, image: NDArray[np.uint8], context: AnalysisContext
    ) -> dict[str, Any]:
        return {
            "model": self.settings.local_vision_model,
            "messages": [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": self._task_prompt(context),
                    "images": [self._encode_image(image)],
                },
            ],
            "stream": False,
            "format": "json",
            "keep_alive": self.settings.local_vision_keep_alive,
            "options": {
                "temperature": 0.1,
                "num_ctx": 4096,
                "num_predict": self.settings.vision_max_tokens,
            },
        }

    @staticmethod
    def _json_payload(content: str) -> dict[str, Any] | None:
        cleaned = content.strip()
        if cleaned.startswith("```"):
            lines = cleaned.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            cleaned = "\n".join(lines).strip()
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start < 0 or end <= start:
            return None
        try:
            parsed = json.loads(cleaned[start : end + 1])
        except json.JSONDecodeError:
            return None
        return parsed if isinstance(parsed, dict) else None

    @staticmethod
    def _kind(task: TaskType) -> EvidenceKind:
        return {
            TaskType.SCENE_DESCRIPTION: EvidenceKind.SCENE,
            TaskType.READ_TEXT: EvidenceKind.TEXT,
            TaskType.FIND_OBJECT: EvidenceKind.OBJECT,
            TaskType.VISUAL_QUESTION: EvidenceKind.ANSWER,
        }[task]

    def _provider_result(self, raw_content: str, context: AnalysisContext) -> ProviderResult:
        payload = self._json_payload(raw_content)
        if payload is None:
            content = raw_content.strip()
            confidence = 0.5
            position = None
            warnings = ["本地视觉模型未返回标准JSON，已保留原始文本结果。"]
            confidence_source = "fallback"
        else:
            content = str(
                payload.get("content")
                or payload.get("summary")
                or payload.get("answer")
                or payload.get("text")
                or ""
            ).strip()
            try:
                confidence = float(payload.get("confidence", 0.5))
            except (TypeError, ValueError):
                confidence = 0.5
            position_value = payload.get("position")
            position = str(position_value).strip() if position_value else None
            raw_warnings = payload.get("warnings", [])
            warnings = (
                [str(item)[:200] for item in raw_warnings if str(item).strip()]
                if isinstance(raw_warnings, list)
                else []
            )
            confidence_source = "model_self_report"

        if not content:
            return ProviderResult(
                provider=self.name,
                configured=True,
                warnings=[*warnings, "本地视觉模型未返回可用文本。"],
            )

        evidence = Evidence(
            source=self.name,
            kind=self._kind(context.task),
            content=content[:500],
            confidence=min(max(confidence, 0.0), 1.0),
            task_relevance=1.0,
            importance=0.8,
            position=position[:80] if position else None,
            metadata={
                "model": self.settings.local_vision_model,
                "runtime": "ollama",
                "confidence_source": confidence_source,
            },
        )
        return ProviderResult(
            provider=self.name,
            configured=True,
            evidence=[evidence],
            warnings=warnings,
        )

    async def analyze(
        self,
        image: NDArray[np.uint8],
        context: AnalysisContext,
    ) -> ProviderResult:
        if not self.configured:
            return ProviderResult(
                provider=self.name,
                configured=False,
                warnings=[self.status_message],
            )

        timeout = httpx.Timeout(self.settings.local_vision_timeout_seconds)
        async with httpx.AsyncClient(timeout=timeout, transport=self._transport) as client:
            response = await client.post(
                self.settings.local_vision_api_url,
                json=self._request_body(image, context),
            )
            response.raise_for_status()
            body = response.json()

        raw_content = body["message"]["content"]
        if not isinstance(raw_content, str):
            raise ValueError("本地视觉模型返回的 content 不是文本。")
        return self._provider_result(raw_content, context)
