"""基于Torchvision预训练权重的本地目标检测适配器。"""

from __future__ import annotations

import asyncio
import importlib.util
from collections.abc import Callable, Mapping, Sequence
from threading import Lock
from typing import Any

import numpy as np
from numpy.typing import NDArray

from core.config.settings import ProviderSettings
from core.domain.enums import EvidenceKind, ProviderName, TaskType
from core.domain.models import AnalysisContext, BoundingBox, Evidence, ProviderResult
from core.providers.base import AnalysisProvider

Detection = Mapping[str, Any]
DetectorPredictor = Callable[[NDArray[np.uint8]], Sequence[Detection]]

_LABELS_ZH = {
    "person": "人",
    "bicycle": "自行车",
    "car": "汽车",
    "motorcycle": "摩托车",
    "airplane": "飞机",
    "bus": "公交车",
    "train": "火车",
    "truck": "卡车",
    "boat": "船",
    "traffic light": "交通信号灯",
    "fire hydrant": "消防栓",
    "stop sign": "停止标志",
    "parking meter": "停车计时器",
    "bench": "长椅",
    "bird": "鸟",
    "cat": "猫",
    "dog": "狗",
    "horse": "马",
    "sheep": "羊",
    "cow": "牛",
    "elephant": "大象",
    "bear": "熊",
    "zebra": "斑马",
    "giraffe": "长颈鹿",
    "backpack": "背包",
    "umbrella": "雨伞",
    "handbag": "手提包",
    "tie": "领带",
    "suitcase": "行李箱",
    "frisbee": "飞盘",
    "skis": "滑雪板",
    "snowboard": "单板滑雪板",
    "sports ball": "球",
    "kite": "风筝",
    "baseball bat": "棒球棒",
    "baseball glove": "棒球手套",
    "skateboard": "滑板",
    "surfboard": "冲浪板",
    "tennis racket": "网球拍",
    "bottle": "瓶子",
    "wine glass": "酒杯",
    "cup": "杯子",
    "fork": "叉子",
    "knife": "刀",
    "spoon": "勺子",
    "bowl": "碗",
    "banana": "香蕉",
    "apple": "苹果",
    "sandwich": "三明治",
    "orange": "橙子",
    "broccoli": "西兰花",
    "carrot": "胡萝卜",
    "hot dog": "热狗",
    "pizza": "披萨",
    "donut": "甜甜圈",
    "cake": "蛋糕",
    "chair": "椅子",
    "couch": "沙发",
    "potted plant": "盆栽",
    "bed": "床",
    "dining table": "餐桌",
    "toilet": "马桶",
    "tv": "电视",
    "laptop": "笔记本电脑",
    "mouse": "鼠标",
    "remote": "遥控器",
    "keyboard": "键盘",
    "cell phone": "手机",
    "microwave": "微波炉",
    "oven": "烤箱",
    "toaster": "烤面包机",
    "sink": "水槽",
    "refrigerator": "冰箱",
    "book": "书",
    "clock": "时钟",
    "vase": "花瓶",
    "scissors": "剪刀",
    "teddy bear": "玩具熊",
    "hair drier": "吹风机",
    "toothbrush": "牙刷",
}

_TARGET_ALIASES = {
    "cup": {"cup", "杯", "杯子", "水杯", "茶杯"},
    "bottle": {"bottle", "瓶", "瓶子", "水瓶", "矿泉水"},
    "cell phone": {"cellphone", "phone", "手机", "电话"},
    "chair": {"chair", "椅", "椅子", "座椅"},
    "couch": {"couch", "sofa", "沙发"},
    "backpack": {"backpack", "背包", "书包"},
    "handbag": {"handbag", "手提包", "包"},
    "suitcase": {"suitcase", "行李箱", "箱子"},
    "dining table": {"table", "diningtable", "桌", "桌子", "餐桌"},
    "book": {"book", "书", "书本"},
    "laptop": {"laptop", "笔记本电脑", "电脑"},
    "keyboard": {"keyboard", "键盘"},
    "mouse": {"mouse", "鼠标"},
    "remote": {"remote", "遥控器"},
}


def _module_available(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def _normalized(value: str) -> str:
    return "".join(value.lower().split())


def _position(box: BoundingBox) -> str:
    center_x = (box.x1 + box.x2) / 2
    center_y = (box.y1 + box.y2) / 2
    horizontal = "左侧" if center_x < 1 / 3 else "右侧" if center_x > 2 / 3 else "中央"
    vertical = "上方" if center_y < 1 / 3 else "下方" if center_y > 2 / 3 else ""
    return f"画面{horizontal}{vertical}"


class TorchvisionDetectorProvider(AnalysisProvider):
    """使用SSDLite MobileNetV3 COCO权重进行本地目标检测。"""

    name = ProviderName.DETECTOR

    def __init__(
        self,
        settings: ProviderSettings,
        *,
        predictor: DetectorPredictor | None = None,
        dependency_available: bool | None = None,
    ) -> None:
        self.settings = settings
        self._predictor = predictor
        self._dependency_available = (
            dependency_available
            if dependency_available is not None
            else _module_available("torch") and _module_available("torchvision")
        )
        self._runtime_lock = Lock()
        self._model: Any | None = None
        self._weights: Any | None = None
        self._torch: Any | None = None
        self._device = "首次推理自动加载"

    @property
    def configured(self) -> bool:
        return self.settings.detector_enabled and (
            self._predictor is not None or self._dependency_available
        )

    @property
    def status_message(self) -> str:
        if not self.settings.detector_enabled:
            return "目标检测尚未启用。"
        if not self._dependency_available and self._predictor is None:
            return "目标检测已启用，但缺少torch或torchvision。"
        return f"本地目标检测 {self.settings.detector_model} 已配置（{self._device}）。"

    def _load_runtime(self) -> None:
        if self._model is not None:
            return
        import torch
        from torchvision.models.detection import (
            SSDLite320_MobileNet_V3_Large_Weights,
            ssdlite320_mobilenet_v3_large,
        )

        weights = SSDLite320_MobileNet_V3_Large_Weights.DEFAULT
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        model = ssdlite320_mobilenet_v3_large(weights=weights)
        model.to(device).eval()
        self._torch = torch
        self._weights = weights
        self._model = model
        self._device = str(device)

    def _predict(self, image: NDArray[np.uint8]) -> list[Detection]:
        with self._runtime_lock:
            self._load_runtime()
            rgb = np.ascontiguousarray(image[:, :, ::-1])
            tensor = self._torch.from_numpy(rgb).permute(2, 0, 1)
            prepared = self._weights.transforms()(tensor).to(self._device)
            with self._torch.inference_mode():
                output = self._model([prepared])[0]
            boxes = output["boxes"].detach().cpu().tolist()
            labels = output["labels"].detach().cpu().tolist()
            scores = output["scores"].detach().cpu().tolist()
            categories = self._weights.meta["categories"]

        return [
            {
                "label": categories[int(label)] if int(label) < len(categories) else str(label),
                "score": float(score),
                "bbox": box,
            }
            for box, label, score in zip(boxes, labels, scores, strict=True)
        ]

    @staticmethod
    def _matches_target(target: str, label_en: str, label_zh: str) -> bool:
        normalized_target = _normalized(target)
        candidates = {_normalized(label_en), _normalized(label_zh)}
        candidates.update(_normalized(item) for item in _TARGET_ALIASES.get(label_en, set()))
        return any(
            candidate and (candidate in normalized_target or normalized_target in candidate)
            for candidate in candidates
        )

    def _to_evidence(
        self,
        detection: Detection,
        context: AnalysisContext,
        width: int,
        height: int,
    ) -> Evidence | None:
        score = float(detection.get("score", 0.0))
        if score < self.settings.detector_min_confidence:
            return None
        raw_box = detection.get("bbox")
        if not isinstance(raw_box, Sequence) or len(raw_box) != 4:
            return None
        x1, y1, x2, y2 = (float(value) for value in raw_box)
        box = BoundingBox(
            x1=min(max(x1 / width, 0.0), 1.0),
            y1=min(max(y1 / height, 0.0), 1.0),
            x2=min(max(x2 / width, 0.0), 1.0),
            y2=min(max(y2 / height, 0.0), 1.0),
        )
        label_en = str(detection.get("label", "object")).strip().lower() or "object"
        label_zh = _LABELS_ZH.get(label_en, label_en)
        if context.task is TaskType.FIND_OBJECT and context.target:
            if not self._matches_target(context.target, label_en, label_zh):
                return None
            content = f"找到{label_zh}"
            relevance = 1.0
        else:
            content = f"检测到{label_zh}"
            relevance = 0.75
        return Evidence(
            source=self.name,
            kind=EvidenceKind.OBJECT,
            content=content,
            confidence=min(max(score, 0.0), 1.0),
            task_relevance=relevance,
            importance=0.75,
            position=_position(box),
            bbox=box,
            metadata={
                "label_en": label_en,
                "label_zh": label_zh,
                "model": self.settings.detector_model,
                "device": self._device,
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
        predictor = self._predictor or self._predict
        detections = await asyncio.to_thread(predictor, image.copy())
        height, width = image.shape[:2]
        evidence = [
            item
            for detection in detections
            if (item := self._to_evidence(detection, context, width, height)) is not None
        ][: self.settings.detector_max_results]
        return ProviderResult(provider=self.name, configured=True, evidence=evidence)
