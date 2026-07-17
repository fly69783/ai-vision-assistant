"""Run one real image through the project API with the local Qwen3-VL backend."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("image", type=Path)
    parser.add_argument("--task", default="scene_description")
    parser.add_argument("--query")
    parser.add_argument("--target")
    args = parser.parse_args()

    if not args.image.is_file():
        print(f"Image not found: {args.image}", file=sys.stderr)
        return 2

    os.environ["AI_VISION_LOCAL_VISION_ENABLED"] = "true"
    os.environ["AI_VISION_VISION_BACKEND"] = "ollama"
    os.environ.setdefault(
        "AI_VISION_LOCAL_VISION_MODEL", "qwen3-vl:4b-instruct-q4_K_M"
    )
    # Keep this validation focused on the VLM and avoid loading other model runtimes.
    os.environ["AI_VISION_DETECTOR_ENABLED"] = "false"
    os.environ["AI_VISION_OCR_ENABLED"] = "false"

    root = Path(__file__).resolve().parents[1]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    from fastapi.testclient import TestClient

    from app.main import app

    suffix = args.image.suffix.lower()
    content_type = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
    }.get(suffix)
    if content_type is None:
        print("Image must be JPEG, PNG, or WebP.", file=sys.stderr)
        return 2

    data = {"task": args.task}
    if args.query:
        data["query"] = args.query
    if args.target:
        data["target"] = args.target

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/analyze",
            data=data,
            files={"file": (args.image.name, args.image.read_bytes(), content_type)},
        )
    print(f"HTTP {response.status_code}")
    payload = response.json()
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    if response.status_code != 200:
        return 1
    if not payload.get("evidence"):
        return 1
    metadata = payload["evidence"][0].get("metadata", {})
    return 0 if metadata.get("runtime") == "ollama" else 1


if __name__ == "__main__":
    raise SystemExit(main())
