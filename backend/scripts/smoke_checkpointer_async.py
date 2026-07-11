"""预检：验证 AsyncPostgresSaver 在 Windows SelectorEventLoop 下可正常连接读写。

用法: uv run python scripts/smoke_checkpointer_async.py
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from app.config import settings

conninfo = settings.sync_database_url.replace("postgresql+psycopg://", "postgresql://")


async def main():
    loop = asyncio.get_running_loop()
    print(f"事件循环类型: {type(loop).__name__}")
    async with AsyncPostgresSaver.from_conn_string(conninfo) as saver:
        config = {"configurable": {"thread_id": "smoke-test-thread"}}
        result = await saver.aget_tuple(config)
        print(f"aget_tuple 返回: {result}")
    print("AsyncPostgresSaver 连接读写正常")


if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
asyncio.run(main())
