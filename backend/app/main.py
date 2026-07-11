import asyncio
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.core.logging import setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()

    # psycopg 异步模式不支持 Windows ProactorEventLoop：
    # uvicorn --reload 下默认就是 SelectorEventLoop；若直接启动命中 Proactor，给出明确提示。
    if sys.platform == "win32":
        loop = asyncio.get_running_loop()
        if isinstance(loop, asyncio.ProactorEventLoop):
            raise RuntimeError(
                "当前为 ProactorEventLoop，psycopg 异步驱动无法工作。"
                "请使用 `uv run uvicorn app.main:app --reload` 启动，"
                "或 `uv run python scripts/run_server.py`。"
            )

    from app.agent.checkpointer import close_checkpointer, init_checkpointer
    from app.agent.graph import init_graph
    from app.services.workflow_service import recover_running_tasks

    await init_checkpointer()
    init_graph()
    await recover_running_tasks()
    yield
    await close_checkpointer()


app = FastAPI(title="美妆自媒体运营 AI Agent", version="0.2.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 生成的图片通过静态目录直接对外
app.mount("/images", StaticFiles(directory=str(settings.image_dir_path)), name="images")


@app.get("/health")
async def health():
    return {"status": "ok", "debug": settings.debug}


from app.api.v1.decisions import router as decisions_router  # noqa: E402
from app.api.v1.tasks import router as tasks_router  # noqa: E402

app.include_router(tasks_router)
app.include_router(decisions_router)

if settings.debug:
    from app.api.debug import router as debug_router

    app.include_router(debug_router)
