"""本地启动入口。

开发时也可以直接运行：
    python -m uvicorn app.main:app --reload
"""

import uvicorn

from core.config import load_settings


def main() -> None:
    settings = load_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.server.host,
        port=settings.server.port,
        reload=False,
        log_level=settings.server.log_level.lower(),
    )


if __name__ == "__main__":
    main()
