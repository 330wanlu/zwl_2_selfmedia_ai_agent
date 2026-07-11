"""初始化 LangGraph PostgresSaver 的 checkpoint 表（幂等，可重复执行）。

用法: uv run python scripts/setup_checkpointer.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from langgraph.checkpoint.postgres import PostgresSaver

from app.config import settings

# PostgresSaver 使用 psycopg 原生连接串（不带 SQLAlchemy 前缀）
conninfo = settings.sync_database_url.replace("postgresql+psycopg://", "postgresql://")

with PostgresSaver.from_conn_string(conninfo) as saver:
    saver.setup()

print("LangGraph checkpoint 表初始化完成")
