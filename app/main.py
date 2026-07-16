"""FastAPI应用工厂。"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.router import api_router
from core.config.settings import AppSettings, load_settings
from core.observability import configure_logging
from core.providers import ProviderRegistry, build_default_registry
from core.services import AnalysisOrchestrator


def create_app(
    settings: AppSettings | None = None,
    providers: ProviderRegistry | None = None,
) -> FastAPI:
    selected = settings or load_settings()
    configure_logging(selected.server.log_level)
    registry = providers or build_default_registry(selected)

    application = FastAPI(
        title=selected.name,
        version=selected.version,
        description="环境理解辅助系统基础API；真实AI能力需通过providers适配器接入。",
        docs_url=f"{selected.api_prefix}/docs",
        redoc_url=f"{selected.api_prefix}/redoc",
    )
    application.state.settings = selected
    application.state.orchestrator = AnalysisOrchestrator(selected, registry)
    application.include_router(api_router, prefix=selected.api_prefix)

    frontend_dir = Path(__file__).resolve().parents[1] / "frontend" / "web"
    if frontend_dir.exists():
        application.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")

    return application


app = create_app()
