# 美妆自媒体运营 AI Agent

基于 LangGraph + FastAPI 的美妆内容生产流水线：方向 → 选题 → 文案 → 出图 → 小红书内容包。

## 仓库说明

- `docs/`：项目方案、MVP 落地方案、开发流程与各阶段开发记录
- `backend/`：FastAPI 后端（uv + PostgreSQL + 豆包文本/Seedream 生图）
- `frontend/`：运营前端（Vite + React + Ant Design）

## 快速开始

### 后端

```powershell
cd backend
copy .env.example .env   # 填入 DATABASE_URL 密码与 ARK_API_KEY
uv sync
uv run python scripts/create_db.py
uv run alembic upgrade head
uv run python scripts/setup_checkpointer.py
uv run uvicorn app.main:app --reload --reload-dir app --port 8000
```

Swagger：http://localhost:8000/docs

### 前端

```powershell
cd frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

页面：http://127.0.0.1:5173  

开发期 Vite 已代理 `/api`、`/images` 到后端 8000，一般无需改 `.env`。

## 安全提示

请勿提交真实 `.env`。仓库只保留 `backend/.env.example` 作为配置模板。
