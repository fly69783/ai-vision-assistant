"""系统内部使用的固定枚举。"""

from enum import StrEnum


class TaskType(StrEnum):
    SCENE_DESCRIPTION = "scene_description"
    READ_TEXT = "read_text"
    FIND_OBJECT = "find_object"
    VISUAL_QUESTION = "visual_question"


class AnalysisStatus(StrEnum):
    SUCCESS = "success"
    PARTIAL = "partial"
    NO_RESULT = "no_result"
    UNAVAILABLE = "unavailable"
    REJECTED = "rejected"
    ERROR = "error"


class ProviderName(StrEnum):
    DETECTOR = "detector"
    OCR = "ocr"
    VISION = "vision"


class EvidenceKind(StrEnum):
    OBJECT = "object"
    TEXT = "text"
    SCENE = "scene"
    ANSWER = "answer"


class QualityStatus(StrEnum):
    ACCEPTED = "accepted"
    REJECTED = "rejected"
