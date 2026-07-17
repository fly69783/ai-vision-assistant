from __future__ import annotations

import asyncio
import json
from dataclasses import replace

import cv2
import httpx

from app.main import create_app


async def request(app, method: str, path: str, **kwargs) -> httpx.Response:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        return await client.request(method, path, **kwargs)


def test_health_reports_unconfigured_capabilities() -> None:
    response = asyncio.run(request(create_app(), "GET", "/api/v1/health"))

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert all(item["configured"] is False for item in body["capabilities"])


def test_valid_image_reaches_unavailable_provider_status(sharp_image) -> None:
    success, encoded = cv2.imencode(".png", sharp_image)
    assert success

    response = asyncio.run(
        request(
            create_app(),
            "POST",
            "/api/v1/analyze",
            data={"task": "read_text"},
            files={"file": ("test.png", encoded.tobytes(), "image/png")},
        )
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "unavailable"
    assert body["quality"]["status"] == "accepted"
    assert body["evidence"] == []


def test_invalid_file_type_is_rejected() -> None:
    response = asyncio.run(
        request(
            create_app(),
            "POST",
            "/api/v1/analyze",
            data={"task": "read_text"},
            files={"file": ("notes.txt", b"not an image", "text/plain")},
        )
    )

    assert response.status_code == 415
    assert "不支持" in response.json()["detail"]


def test_find_object_requires_target(sharp_image) -> None:
    success, encoded = cv2.imencode(".png", sharp_image)
    assert success

    response = asyncio.run(
        request(
            create_app(),
            "POST",
            "/api/v1/analyze",
            data={"task": "find_object"},
            files={"file": ("test.png", encoded.tobytes(), "image/png")},
        )
    )

    assert response.status_code == 422
    assert "目标物品" in response.json()["detail"]


def test_find_object_rejects_whitespace_target(sharp_image) -> None:
    success, encoded = cv2.imencode(".png", sharp_image)
    assert success

    response = asyncio.run(
        request(
            create_app(),
            "POST",
            "/api/v1/analyze",
            data={"task": "find_object", "target": "   "},
            files={"file": ("test.png", encoded.tobytes(), "image/png")},
        )
    )

    assert response.status_code == 422
    assert "目标物品" in response.json()["detail"]


def test_visual_question_rejects_whitespace_query(sharp_image) -> None:
    success, encoded = cv2.imencode(".png", sharp_image)
    assert success

    response = asyncio.run(
        request(
            create_app(),
            "POST",
            "/api/v1/analyze",
            data={"task": "visual_question", "query": "   "},
            files={"file": ("test.png", encoded.tobytes(), "image/png")},
        )
    )

    assert response.status_code == 422
    assert "必须填写问题" in response.json()["detail"]


def test_empty_image_is_rejected() -> None:
    response = asyncio.run(
        request(
            create_app(),
            "POST",
            "/api/v1/analyze",
            data={"task": "read_text"},
            files={"file": ("empty.png", b"", "image/png")},
        )
    )

    assert response.status_code == 400
    assert "为空" in response.json()["detail"]


def test_unknown_image_header_is_rejected() -> None:
    response = asyncio.run(
        request(
            create_app(),
            "POST",
            "/api/v1/analyze",
            data={"task": "read_text"},
            files={"file": ("fake.png", b"not-an-image", "image/png")},
        )
    )

    assert response.status_code == 400
    assert "无法识别图片格式" in response.json()["detail"]


def test_corrupt_image_with_valid_header_is_rejected() -> None:
    response = asyncio.run(
        request(
            create_app(),
            "POST",
            "/api/v1/analyze",
            data={"task": "read_text"},
            files={"file": ("broken.png", b"\x89PNG\r\n\x1a\ninvalid", "image/png")},
        )
    )

    assert response.status_code == 400
    assert "损坏或无法解码" in response.json()["detail"]


def test_upload_size_limit_is_enforced(settings) -> None:
    limited = replace(settings, server=replace(settings.server, max_upload_mb=1))
    oversized = b"\x89PNG\r\n\x1a\n" + bytes(1024 * 1024)

    response = asyncio.run(
        request(
            create_app(settings=limited),
            "POST",
            "/api/v1/analyze",
            data={"task": "read_text"},
            files={"file": ("large.png", oversized, "image/png")},
        )
    )

    assert response.status_code == 413
    assert "不能超过1MB" in response.json()["detail"]


def test_spoofed_image_type_is_rejected(sharp_image) -> None:
    success, encoded = cv2.imencode(".png", sharp_image)
    assert success

    response = asyncio.run(
        request(
            create_app(),
            "POST",
            "/api/v1/analyze",
            data={"task": "read_text"},
            files={"file": ("fake.jpg", encoded.tobytes(), "image/jpeg")},
        )
    )

    assert response.status_code == 400
    assert "格式不一致" in response.json()["detail"]


def test_pixel_limit_is_enforced(settings, sharp_image) -> None:
    limited = replace(settings, server=replace(settings.server, max_image_pixels=100))
    success, encoded = cv2.imencode(".png", sharp_image)
    assert success

    response = asyncio.run(
        request(
            create_app(settings=limited),
            "POST",
            "/api/v1/analyze",
            data={"task": "read_text"},
            files={"file": ("test.png", encoded.tobytes(), "image/png")},
        )
    )

    assert response.status_code == 413
    assert "像素过高" in response.json()["detail"]


def test_api_responses_are_not_cached_and_have_request_id() -> None:
    response = asyncio.run(
        request(
            create_app(),
            "GET",
            "/api/v1/health",
            headers={"X-Request-ID": "browser-test-123"},
        )
    )

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-request-id"] == "browser-test-123"
    assert response.headers["x-content-type-options"] == "nosniff"


def test_invalid_request_id_is_replaced() -> None:
    response = asyncio.run(
        request(
            create_app(),
            "GET",
            "/api/v1/health",
            headers={"X-Request-ID": "bad id"},
        )
    )

    assert response.status_code == 200
    assert response.headers["x-request-id"] != "bad id"
    assert len(response.headers["x-request-id"]) == 32


def test_frontend_exposes_mobile_pwa_shell() -> None:
    app = create_app()
    page = asyncio.run(request(app, "GET", "/"))
    manifest = asyncio.run(request(app, "GET", "/manifest.webmanifest"))
    service_worker = asyncio.run(request(app, "GET", "/service-worker.js"))

    assert page.status_code == 200
    assert 'capture="environment"' in page.text
    assert 'rel="manifest"' in page.text
    assert "default-src 'self'" in page.headers["content-security-policy"]
    assert page.headers["x-frame-options"] == "DENY"

    assert manifest.status_code == 200
    manifest_data = json.loads(manifest.text)
    assert manifest_data["display"] == "standalone"
    assert manifest_data["start_url"] == "/"

    assert service_worker.status_code == 200
    assert service_worker.headers["cache-control"] == "no-cache"
    assert service_worker.headers["service-worker-allowed"] == "/"
    assert 'url.pathname.startsWith("/api/")' in service_worker.text
