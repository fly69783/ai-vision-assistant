"""验证目标检测和OCR运行时，并提前缓存本地模型。"""

from __future__ import annotations

import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path


def package_version(name: str) -> str:
    try:
        return version(name)
    except PackageNotFoundError:
        return "未安装"


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    root = Path(__file__).resolve().parents[1]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    print("本地AI运行时检查")
    print(f"Python：{sys.version.split()[0]} ({sys.executable})")
    print(f"torch：{package_version('torch')}")
    print(f"torchvision：{package_version('torchvision')}")
    print(f"rapidocr：{package_version('rapidocr')}")
    print(f"onnxruntime：{package_version('onnxruntime')}")

    try:
        import torch
        from torchvision.models.detection import (
            SSDLite320_MobileNet_V3_Large_Weights,
            ssdlite320_mobilenet_v3_large,
        )

        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        model = ssdlite320_mobilenet_v3_large(
            weights=SSDLite320_MobileNet_V3_Large_Weights.DEFAULT
        )
        model.to(device).eval()
        print(f"[OK] SSDLite目标检测权重已缓存，运行设备：{device}")
        del model
    except Exception as exc:  # noqa: BLE001 - 安装检查需要给出完整失败类型
        print(f"[失败] 目标检测：{type(exc).__name__}：{exc}")
        return 1

    try:
        from rapidocr import RapidOCR

        RapidOCR()
        print("[OK] RapidOCR与PP-OCRv6模型加载成功，运行设备：CPU")
    except Exception as exc:  # noqa: BLE001 - 安装检查需要给出完整失败类型
        print(f"[失败] OCR：{type(exc).__name__}：{exc}")
        return 1

    print("\n本地目标检测和OCR检查通过。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
