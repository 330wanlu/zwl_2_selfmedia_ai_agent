from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.core.logging import setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    yield


app = FastAPI(title="美妆自媒体运营 AI Agent", version="0.1.0", lifespan=lifespan)

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


if settings.debug:
    from app.api.debug import router as debug_router

    app.include_router(debug_router)
