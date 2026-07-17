from __future__ import annotations

import asyncio
import sys
from dataclasses import replace
from types import SimpleNamespace

import numpy as np
import pytest

from core.domain.enums import EvidenceKind, ProviderName, TaskType
from core.domain.models import AnalysisContext
from core.providers.rapidocr_provider import RapidOCRProvider


class FakeOCREngine:
    def __init__(self, result) -> None:
        self.result = result
        self.options = None

    def __call__(self, _image, **options):
        self.options = options
        return self.result


def test_ocr_converts_lines_to_text_evidence(settings, sharp_image) -> None:
    result = SimpleNamespace(
        boxes=np.array(
            [
                [[64, 48], [320, 48], [320, 120], [64, 120]],
                [[100, 200], [300, 200], [300, 260], [100, 260]],
            ],
            dtype=np.float32,
        ),
        txts=("安全出口", "模糊文字"),
        scores=(0.96, 0.3),
    )
    engine = FakeOCREngine(result)
    provider = RapidOCRProvider(
        replace(settings.providers, ocr_enabled=True, ocr_min_confidence=0.55),
        engine=engine,
        dependency_available=False,
    )

    provider_result = asyncio.run(
        provider.analyze(sharp_image, AnalysisContext(task=TaskType.READ_TEXT))
    )

    assert provider_result.configured is True
    assert len(provider_result.evidence) == 1
    evidence = provider_result.evidence[0]
    assert evidence.source is ProviderName.OCR
    assert evidence.kind is EvidenceKind.TEXT
    assert evidence.content == "安全出口"
    assert evidence.confidence == 0.96
    assert evidence.bbox.x1 == pytest.approx(0.1)
    assert evidence.position == "画面左侧上方"
    assert engine.options == {"use_det": True, "use_cls": True, "use_rec": True}


def test_ocr_returns_empty_evidence_when_no_text(settings, sharp_image) -> None:
    engine = FakeOCREngine(SimpleNamespace(boxes=None, txts=(), scores=()))
    provider = RapidOCRProvider(
        replace(settings.providers, ocr_enabled=True),
        engine=engine,
    )

    result = asyncio.run(
        provider.analyze(sharp_image, AnalysisContext(task=TaskType.SCENE_DESCRIPTION))
    )

    assert result.configured is True
    assert result.evidence == []


def test_ocr_reports_missing_dependency(settings, sharp_image) -> None:
    provider = RapidOCRProvider(
        replace(settings.providers, ocr_enabled=True),
        dependency_available=False,
    )

    result = asyncio.run(
        provider.analyze(sharp_image, AnalysisContext(task=TaskType.READ_TEXT))
    )

    assert provider.configured is False
    assert result.configured is False
    assert "缺少rapidocr或onnxruntime" in result.warnings[0]


def test_ocr_disabled_is_honest(settings) -> None:
    provider = RapidOCRProvider(settings.providers, engine=FakeOCREngine(None))

    assert provider.configured is False
    assert provider.status_message == "OCR尚未启用。"


def test_ocr_lazily_creates_engine(settings, monkeypatch) -> None:
    fake_engine = FakeOCREngine(None)
    monkeypatch.setitem(sys.modules, "rapidocr", SimpleNamespace(RapidOCR=lambda: fake_engine))
    provider = RapidOCRProvider(
        replace(settings.providers, ocr_enabled=True),
        dependency_available=True,
    )

    assert provider._get_engine() is fake_engine


def test_ocr_ignores_invalid_polygon(settings, sharp_image) -> None:
    engine = FakeOCREngine(
        SimpleNamespace(
            boxes=np.array([[[1, 2], [3, 4]]], dtype=np.float32),
            txts=("不完整框",),
            scores=(0.9,),
        )
    )
    provider = RapidOCRProvider(
        replace(settings.providers, ocr_enabled=True),
        engine=engine,
    )

    result = asyncio.run(
        provider.analyze(sharp_image, AnalysisContext(task=TaskType.READ_TEXT))
    )

    assert result.evidence == []
