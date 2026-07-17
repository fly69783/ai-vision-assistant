"""基于RapidOCR和ONNX Runtime的本地文字识别适配器。"""

from __future__ import annotations

import asyncio
import importlib.util
from collections.abc import Callable
from threading import Lock
from typing import Any

import numpy as np
from numpy.typing import NDArray

from core.config.settings import ProviderSettings
from core.domain.enums import EvidenceKind, ProviderName, TaskType
from core.domain.models import AnalysisContext, BoundingBox, Evidence, ProviderResult
from core.providers.base import AnalysisProvider

OCREngine = Callable[..., Any]


def _module_available(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def _position(box: BoundingBox) -> str:
    center_x = (box.x1 + box.x2) / 2
    center_y = (box.y1 + box.y2) / 2
    horizontal = "左侧" if center_x < 1 / 3 else "右侧" if center_x > 2 / 3 else "中央"
    vertical = "上方" if center_y < 1 / 3 else "下方" if center_y > 2 / 3 else ""
    return f"画面{horizontal}{vertical}"


class RapidOCRProvider(AnalysisProvider):
    """识别中文和英文场景文字，并保留文本框与置信度。"""

    name = ProviderName.OCR

    def __init__(
        self,
        settings: ProviderSettings,
        *,
        engine: OCREngine | None = None,
        dependency_available: bool | None = None,
    ) -> None:
        self.settings = settings
        self._engine = engine
        self._dependency_available = (
            dependency_available
            if dependency_available is not None
            else _module_available("rapidocr") and _module_available("onnxruntime")
        )
        self._runtime_lock = Lock()

    @property
    def configured(self) -> bool:
        return self.settings.ocr_enabled and (
            self._engine is not None or self._dependency_available
        )

    @property
    def status_message(self) -> str:
        if not self.settings.ocr_enabled:
            return "OCR尚未启用。"
        if not self._dependency_available and self._engine is None:
            return "OCR已启用，但缺少rapidocr或onnxruntime。"
        return f"本地OCR {self.settings.ocr_model} 已配置。"

    def _get_engine(self) -> OCREngine:
        if self._engine is None:
            from rapidocr import RapidOCR

            self._engine = RapidOCR()
        return self._engine

    def _run_ocr(self, image: NDArray[np.uint8]) -> list[dict[str, Any]]:
        with self._runtime_lock:
            result = self._get_engine()(
                image,
                use_det=True,
                use_cls=True,
                use_rec=True,
            )
        if result is None or result.boxes is None:
            return []
        return [
            {"box": box, "text": text, "score": score}
            for box, text, score in zip(
                result.boxes,
                result.txts,
                result.scores,
                strict=True,
            )
        ]

    def _to_evidence(
        self,
        row: dict[str, Any],
        context: AnalysisContext,
        width: int,
        height: int,
        index: int,
    ) -> Evidence | None:
        text = str(row.get("text", "")).strip()
        score = float(row.get("score", 0.0))
        points = row.get("box")
        if not text or score < self.settings.ocr_min_confidence:
            return None
        try:
            point_array = np.asarray(points, dtype=np.float32)
        except (TypeError, ValueError):
            return None
        if point_array.ndim != 2 or point_array.shape[0] < 4 or point_array.shape[1] != 2:
            return None
        xs = point_array[:, 0]
        ys = point_array[:, 1]
        box = BoundingBox(
            x1=min(max(min(xs) / width, 0.0), 1.0),
            y1=min(max(min(ys) / height, 0.0), 1.0),
            x2=min(max(max(xs) / width, 0.0), 1.0),
            y2=min(max(max(ys) / height, 0.0), 1.0),
        )
        return Evidence(
            source=self.name,
            kind=EvidenceKind.TEXT,
            content=text[:500],
            confidence=min(max(score, 0.0), 1.0),
            task_relevance=1.0 if context.task is TaskType.READ_TEXT else 0.75,
            importance=0.7,
            position=_position(box),
            bbox=box,
            metadata={
                "model": self.settings.ocr_model,
                "engine": "onnxruntime",
                "line_index": index,
            },
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
        rows = await asyncio.to_thread(self._run_ocr, image.copy())
        height, width = image.shape[:2]
        evidence = [
            item
            for index, row in enumerate(rows)
            if (item := self._to_evidence(row, context, width, height, index)) is not None
        ][: self.settings.ocr_max_lines]
        return ProviderResult(provider=self.name, configured=True, evidence=evidence)
