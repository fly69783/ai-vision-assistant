"""为网页和API添加请求追踪、缓存策略与基础安全响应头。"""

from __future__ import annotations

import re
from collections.abc import Awaitable, Callable
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

_REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{8,64}$")
_HTML_PATHS = {"/", "/index.html"}
_REVALIDATE_PATHS = _HTML_PATHS | {"/manifest.webmanifest", "/service-worker.js"}
_CONTENT_SECURITY_POLICY = "; ".join(
    [
        "default-src 'self'",
        "base-uri 'self'",
        "connect-src 'self'",
        "font-src 'self'",
        "form-action 'self'",
        "frame-ancestors 'none'",
        "img-src 'self' blob: data:",
        "manifest-src 'self'",
        "media-src 'self' blob:",
        "object-src 'none'",
        "script-src 'self'",
        "style-src 'self'",
        "worker-src 'self'",
    ]
)


class ResponsePolicyMiddleware(BaseHTTPMiddleware):
    """添加不依赖具体部署平台的响应策略。"""

    def __init__(self, app, api_prefix: str) -> None:  # noqa: ANN001
        super().__init__(app)
        self.api_prefix = api_prefix.rstrip("/")

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        supplied_id = request.headers.get("x-request-id", "").strip()
        request_id = (
            supplied_id if _REQUEST_ID_PATTERN.fullmatch(supplied_id) else uuid4().hex
        )
        request.state.request_id = request_id

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "camera=(self), microphone=(), geolocation=()"
        response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
        response.headers["X-Permitted-Cross-Domain-Policies"] = "none"

        path = request.url.path
        if path.startswith(f"{self.api_prefix}/") or path == self.api_prefix:
            response.headers["Cache-Control"] = "no-store"
        elif path in _REVALIDATE_PATHS:
            response.headers["Cache-Control"] = "no-cache"

        if path in _HTML_PATHS:
            response.headers["Content-Security-Policy"] = _CONTENT_SECURITY_POLICY
        if path == "/service-worker.js":
            response.headers["Service-Worker-Allowed"] = "/"

        return response
