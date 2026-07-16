"""用通俗输出检查项目基础环境。"""

from __future__ import annotations

import importlib
import platform
import sys
from pathlib import Path

REQUIRED = {
    "fastapi": "FastAPI接口",
    "uvicorn": "开发服务器",
    "pydantic": "数据校验",
    "cv2": "OpenCV图像处理",
    "numpy": "NumPy数组",
    "yaml": "YAML配置",
}


def package_version(module: object) -> str:
    return str(getattr(module, "__version__", "版本未知"))


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    root = Path(__file__).resolve().parents[1]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    print("AI视觉辅助项目：环境检查")
    print(f"仓库：{root}")
    print(f"系统：{platform.system()} {platform.release()}")
    print(f"Python：{platform.python_version()} ({sys.executable})")

    failures: list[str] = []
    if sys.version_info[:2] != (3, 11):
        failures.append("项目固定使用Python 3.11，请切换到ai-vision环境。")

    for module_name, purpose in REQUIRED.items():
        try:
            module = importlib.import_module(module_name)
            print(f"[OK] {purpose}：{module_name} {package_version(module)}")
        except ImportError:
            message = f"[缺少] {purpose}：{module_name}"
            print(message)
            failures.append(message)

    try:
        from core.config import load_settings

        settings = load_settings()
        print(f"[OK] 配置：{settings.name} {settings.version}")
    except Exception as exc:  # noqa: BLE001 - 环境检查需要汇总所有问题
        message = f"[配置错误] {type(exc).__name__}：{exc}"
        print(message)
        failures.append(message)

    try:
        torch = importlib.import_module("torch")
        cuda = bool(torch.cuda.is_available())
        print(f"[可选] PyTorch：{package_version(torch)}，CUDA可用：{cuda}")
        if cuda:
            print(f"[可选] GPU：{torch.cuda.get_device_name(0)}")
    except ImportError:
        print("[可选] 尚未安装PyTorch；基础API仍可运行。")

    if failures:
        print("\n检查未通过：")
        for item in failures:
            print(f"- {item}")
        return 1

    print("\n基础环境检查通过。真实AI能力是否可用，请查看 /api/v1/health。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
