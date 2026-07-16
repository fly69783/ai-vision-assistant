"""FastAPI依赖注入入口。"""

from fastapi import Request

from core.config.settings import AppSettings
from core.services.orchestrator import AnalysisOrchestrator


def get_settings(request: Request) -> AppSettings:
    return request.app.state.settings


def get_orchestrator(request: Request) -> AnalysisOrchestrator:
    return request.app.state.orchestrator
