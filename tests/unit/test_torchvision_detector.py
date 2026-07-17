from __future__ import annotations

import asyncio
from dataclasses import replace
from types import SimpleNamespace

from core.domain.enums import EvidenceKind, ProviderName, TaskType
from core.domain.models import AnalysisContext
from core.providers.torchvision_detector import TorchvisionDetectorProvider


def _detections(_image):
    return [
        {"label": "cup", "score": 0.92, "bbox": [360, 120, 600, 400]},
        {"label": "chair", "score": 0.81, "bbox": [40, 80, 240, 460]},
        {"label": "book", "score": 0.2, "bbox": [200, 200, 300, 300]},
    ]


def test_detector_converts_predictions_to_normalized_evidence(settings, sharp_image) -> None:
    provider_settings = replace(
        settings.providers,
        detector_enabled=True,
        detector_min_confidence=0.45,
    )
    provider = TorchvisionDetectorProvider(
        provider_settings,
        predictor=_detections,
        dependency_available=False,
    )

    result = asyncio.run(
        provider.analyze(sharp_image, AnalysisContext(task=TaskType.SCENE_DESCRIPTION))
    )

    assert result.configured is True
    assert len(result.evidence) == 2
    assert result.evidence[0].source is ProviderName.DETECTOR
    assert result.evidence[0].kind is EvidenceKind.OBJECT
    assert result.evidence[0].content == "检测到杯子"
    assert result.evidence[0].bbox.x1 == 0.5625
    assert result.evidence[0].position == "画面右侧"
    assert result.evidence[0].metadata["label_en"] == "cup"


def test_detector_find_object_filters_other_categories(settings, sharp_image) -> None:
    provider = TorchvisionDetectorProvider(
        replace(settings.providers, detector_enabled=True),
        predictor=_detections,
    )

    result = asyncio.run(
        provider.analyze(
            sharp_image,
            AnalysisContext(task=TaskType.FIND_OBJECT, target="我的水杯"),
        )
    )

    assert [item.content for item in result.evidence] == ["找到杯子"]
    assert result.evidence[0].task_relevance == 1.0


def test_detector_reports_missing_dependency(settings, sharp_image) -> None:
    provider = TorchvisionDetectorProvider(
        replace(settings.providers, detector_enabled=True),
        dependency_available=False,
    )

    result = asyncio.run(
        provider.analyze(sharp_image, AnalysisContext(task=TaskType.SCENE_DESCRIPTION))
    )

    assert provider.configured is False
    assert result.configured is False
    assert "缺少torch或torchvision" in result.warnings[0]


def test_detector_disabled_is_honest(settings) -> None:
    provider = TorchvisionDetectorProvider(settings.providers, predictor=_detections)

    assert provider.configured is False
    assert provider.status_message == "目标检测尚未启用。"


def test_detector_internal_predictor_converts_model_tensors(settings, sharp_image) -> None:
    class FakeTensor:
        def __init__(self, value=None) -> None:
            self.value = value

        def permute(self, *_axes):
            return self

        def to(self, _device):
            return self

        def detach(self):
            return self

        def cpu(self):
            return self

        def tolist(self):
            return self.value

    class FakeInferenceMode:
        def __enter__(self):
            return None

        def __exit__(self, *_args):
            return False

    fake_torch = SimpleNamespace(
        from_numpy=lambda _array: FakeTensor(),
        inference_mode=lambda: FakeInferenceMode(),
    )
    fake_weights = SimpleNamespace(
        transforms=lambda: (lambda tensor: tensor),
        meta={"categories": ["background", "dog"]},
    )

    def fake_model(_images):
        return [
            {
                "boxes": FakeTensor([[10, 20, 30, 40]]),
                "labels": FakeTensor([1]),
                "scores": FakeTensor([0.9]),
            }
        ]

    provider = TorchvisionDetectorProvider(
        replace(settings.providers, detector_enabled=True),
        dependency_available=True,
    )
    provider._model = fake_model
    provider._weights = fake_weights
    provider._torch = fake_torch
    provider._device = "cpu"

    provider._load_runtime()
    predictions = provider._predict(sharp_image)

    assert predictions == [{"label": "dog", "score": 0.9, "bbox": [10, 20, 30, 40]}]
