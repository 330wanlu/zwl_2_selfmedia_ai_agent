"""非 reload 方式启动服务（强制 SelectorEventLoop，兼容 psycopg 异步驱动）。

用法: uv run python scripts/run_server.py
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import uvicorn

if __name__ == "__main__":
    config = uvicorn.Config("app.main:app", host="127.0.0.1", port=8000)
    if sys.platform == "win32":
        # loop_factory 会被直接调用来创建事件循环
        config.get_loop_factory = lambda: asyncio.SelectorEventLoop  # type: ignore[method-assign]
    uvicorn.Server(config).run()
