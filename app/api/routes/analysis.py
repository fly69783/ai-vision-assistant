"""图片环境分析接口。"""

from typing import Annotated

import cv2
import numpy as np
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from app.dependencies import get_orchestrator, get_settings
from core.config.settings import AppSettings
from core.domain.enums import TaskType
from core.domain.models import AnalysisResponse
from core.services.orchestrator import AnalysisOrchestrator

router = APIRouter()


@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_image(
    file: Annotated[UploadFile, File(description="JPEG、PNG或WebP图片")],
    task: Annotated[TaskType, Form(description="需要执行的任务")],
    settings: Annotated[AppSettings, Depends(get_settings)],
    orchestrator: Annotated[AnalysisOrchestrator, Depends(get_orchestrator)],
    query: Annotated[str | None, Form(max_length=200)] = None,
    target: Annotated[str | None, Form(max_length=80)] = None,
) -> AnalysisResponse:
    content_type = file.content_type or ""
    if content_type not in settings.server.allowed_mime_types:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"不支持{content_type or '未知'}格式，请上传JPEG、PNG或WebP图片。",
        )
    if task is TaskType.VISUAL_QUESTION and not query:
        raise HTTPException(status_code=422, detail="视觉追问任务必须填写问题。")
    if task is TaskType.FIND_OBJECT and not (target or query):
        raise HTTPException(status_code=422, detail="物品查找任务必须填写目标物品。")

    max_bytes = settings.server.max_upload_mb * 1024 * 1024
    content = await file.read(max_bytes + 1)
    await file.close()
    if not content:
        raise HTTPException(status_code=400, detail="上传的图片为空。")
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"图片不能超过{settings.server.max_upload_mb}MB。",
        )

    encoded = np.frombuffer(content, dtype=np.uint8)
    image = cv2.imdecode(encoded, cv2.IMREAD_COLOR)
    if image is None:
        raise HTTPException(status_code=400, detail="图片损坏或无法解码。")

    return await orchestrator.analyze(
        image=image,
        task=task,
        query=query,
        target=target or query,
    )
