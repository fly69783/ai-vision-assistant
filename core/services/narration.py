"""把结构化证据转换成适合语音播报的短句。"""

from __future__ import annotations

from core.config.settings import NarrationSettings
from core.domain.models import Evidence


class NarrationService:
    def __init__(self, settings: NarrationSettings) -> None:
        self.settings = settings

    def from_evidence(self, evidence: list[Evidence]) -> str:
        if not evidence:
            return self.settings.unavailable_message

        sentences: list[str] = []
        for item in evidence[: self.settings.max_items]:
            prefix = "可能" if item.confidence < self.settings.low_confidence_threshold else ""
            position = f"{item.position}，" if item.position else ""
            content = item.content.rstrip("。！？；")
            sentences.append(f"{prefix}{position}{content}。")
        return "".join(sentences)

    @staticmethod
    def from_quality_issues(issues: list[str]) -> str:
        if not issues:
            return "画面无法分析，请重新拍摄。"
        return issues[0]
