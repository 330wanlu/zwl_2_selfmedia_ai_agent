"""DEBUG 模式专属调试端点，仅在 settings.debug=True 时挂载。"""

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import text

from app.core.database import engine
from app.llm.ark_image import generate_image
from app.llm.ark_text import chat

router = APIRouter(prefix="/api/debug", tags=["debug"])


@router.get("/db/ping")
async def db_ping():
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT version()"))
        version = result.scalar_one()
    return {"ok": True, "postgres": version}


class ChatRequest(BaseModel):
    prompt: str
    system_prompt: str | None = None
    temperature: float = 0.8


@router.post("/llm/chat")
async def llm_chat(req: ChatRequest):
    reply = await chat(
        req.prompt,
        system_prompt=req.system_prompt,
        node="debug_chat",
        temperature=req.temperature,
    )
    return {"reply": reply}


class ImageRequest(BaseModel):
    prompt: str
    size: str = "2K"


@router.post("/llm/image")
async def llm_image(req: ImageRequest):
    filename = await generate_image(req.prompt, size=req.size, node="debug_image")
    return {"file": filename, "url": f"/images/{filename}"}
