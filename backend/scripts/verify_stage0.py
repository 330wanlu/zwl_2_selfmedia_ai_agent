"""阶段 0 验证：表清单 + LLM 调用日志。用法: uv run python scripts/verify_stage0.py"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import psycopg

from app.config import settings

conninfo = settings.sync_database_url.replace("postgresql+psycopg://", "postgresql://")
conn = psycopg.connect(conninfo, connect_timeout=5)
cur = conn.cursor()

cur.execute("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename")
print("== 数据库表 ==")
for (name,) in cur.fetchall():
    print(" -", name)

cur.execute(
    "SELECT node, call_type, model, duration_ms, error IS NULL AS ok "
    "FROM llm_call_logs ORDER BY created_at"
)
print("== LLM 调用日志 ==")
for row in cur.fetchall():
    print(" -", row)

conn.close()
