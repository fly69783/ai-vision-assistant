"""对不同AI能力返回的证据进行去重和排序。"""

from __future__ import annotations

from core.config.settings import FusionSettings
from core.domain.models import Evidence


class FusionService:
    def __init__(self, settings: FusionSettings) -> None:
        self.settings = settings

    def rank(self, evidence: list[Evidence]) -> list[Evidence]:
        """计算可解释分数，并保留相同内容中分数最高的一条。"""

        best_by_content: dict[str, Evidence] = {}
        for item in evidence:
            score = (
                self.settings.task_relevance * item.task_relevance
                + self.settings.importance * item.importance
                + self.settings.confidence * item.confidence
                + self.settings.novelty * item.novelty
                + self.settings.position * item.position_importance
            )
            scored = item.model_copy(update={"score": round(min(max(score, 0.0), 1.0), 4)})
            key = " ".join(scored.content.lower().split())
            previous = best_by_content.get(key)
            if previous is None or scored.score > previous.score:
                best_by_content[key] = scored

        return sorted(best_by_content.values(), key=lambda item: item.score, reverse=True)
