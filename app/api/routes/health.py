"""健康检查接口。"""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.dependencies import get_orchestrator, get_settings
from core.config.settings import AppSettings
from core.domain.models import HealthResponse
from core.services.orchestrator import AnalysisOrchestrator

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health(
    settings: Annotated[AppSettings, Depends(get_settings)],
    orchestrator: Annotated[AnalysisOrchestrator, Depends(get_orchestrator)],
) -> HealthResponse:
    return HealthResponse(
        service=settings.name,
        version=settings.version,
        environment=settings.environment,
        capabilities=orchestrator.providers.capabilities(),
        safety_notice="本系统仅用于环境理解辅助，不可替代盲杖、导盲犬或专业导航设备。",
    )
