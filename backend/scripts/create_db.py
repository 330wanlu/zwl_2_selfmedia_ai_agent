"""创建 media_agent 数据库（幂等）。用法: uv run python scripts/create_db.py"""

import psycopg

conn = psycopg.connect(
    "postgresql://postgres:love6364@localhost:5432/postgres",
    autocommit=True,
    connect_timeout=5,
)
cur = conn.cursor()
cur.execute("SELECT 1 FROM pg_database WHERE datname='media_agent'")
if cur.fetchone():
    print("media_agent 已存在")
else:
    cur.execute("CREATE DATABASE media_agent")
    print("media_agent 创建成功")
conn.close()
