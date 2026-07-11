"""AsyncPostgresSaver 生命周期管理。

在 FastAPI lifespan 启动时创建连接池并编译工作流图，关闭时释放。

注意（Windows）：psycopg 异步模式不支持 ProactorEventLoop。
uvicorn --reload 模式下会使用 SelectorEventLoop，正常工作；
如果以非 reload 方式启动，需保证事件循环为 Selector（见 main.py）。
"""

import logging

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from app.config import settings

logger = logging.getLogger(__name__)

_pool: AsyncConnectionPool | None = None
_saver: AsyncPostgresSaver | None = None


def _conninfo() -> str:
    return settings.sync_database_url.replace("postgresql+psycopg://", "postgresql://")


async def init_checkpointer() -> AsyncPostgresSaver:
    global _pool, _saver
    _pool = AsyncConnectionPool(
        _conninfo(),
        min_size=1,
        max_size=5,
        open=False,
        kwargs={"autocommit": True, "prepare_threshold": 0, "row_factory": dict_row},
    )
    await _pool.open()
    _saver = AsyncPostgresSaver(_pool)
    logger.info("AsyncPostgresSaver 已初始化")
    return _saver


async def close_checkpointer() -> None:
    global _pool, _saver
    if _pool is not None:
        await _pool.close()
        _pool = None
        _saver = None


def get_checkpointer() -> AsyncPostgresSaver:
    if _saver is None:
        raise RuntimeError("checkpointer 尚未初始化（应在 FastAPI lifespan 中调用 init_checkpointer）")
    return _saver
