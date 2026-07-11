"""DEBUG 模式专属调试端点，仅在 settings.debug=True 时挂载。"""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import engine, get_session
from app.llm.ark_image import generate_image
from app.llm.ark_text import chat

router = APIRouter(prefix="/api/debug", tags=["debug"])


@router.get("/tasks/{task_id}/state")
async def task_state(task_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    """查看任务的 LangGraph checkpoint State（调试用）。"""
    from app.models.task import Task
    from app.services import workflow_service

    task = await session.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    values = await workflow_service.get_state_values(task.thread_id)
    pending = await workflow_service.get_pending_interrupt(task.thread_id)
    return {
        "thread_id": task.thread_id,
        "running": workflow_service.is_running(task.thread_id),
        "pending_interrupt": pending,
        "state": values,
    }


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
