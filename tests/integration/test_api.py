from __future__ import annotations

import asyncio

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
