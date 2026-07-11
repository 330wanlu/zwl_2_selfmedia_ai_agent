"""DEBUG 模式专属调试端点，仅在 settings.debug=True 时挂载。"""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import engine, get_session
from app.llm.ark_image import generate_image
from app.llm.ark_text import chat
from app.models.llm_call_log import LlmCallLog
from app.models.task import Task
from app.services import workflow_service

router = APIRouter(prefix="/api/debug", tags=["debug"])


@router.get("/tasks/{task_id}/state")
async def task_state(task_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    """查看任务的 LangGraph checkpoint State（调试用）。"""
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


@router.get("/tasks/{task_id}/history")
async def task_history(task_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    """查看任务的 checkpoint 历史（从新到旧），追溯工作流走向。"""
    task = await session.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    history = await workflow_service.get_state_history(task.thread_id)
    return {"thread_id": task.thread_id, "count": len(history), "history": history}


@router.get("/tasks/{task_id}/llm-calls")
async def task_llm_calls(task_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    """查看该任务全部 LLM / 生图调用日志。"""
    task = await session.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    result = await session.execute(
        select(LlmCallLog)
        .where(LlmCallLog.task_id == task_id)
        .order_by(LlmCallLog.created_at)
    )
    logs = result.scalars().all()
    return {
        "task_id": str(task_id),
        "count": len(logs),
        "calls": [
            {
                "id": str(log.id),
                "node": log.node,
                "call_type": log.call_type,
                "model": log.model,
                "duration_ms": log.duration_ms,
                "prompt_tokens": log.prompt_tokens,
                "completion_tokens": log.completion_tokens,
                "error": log.error,
                "prompt": log.prompt,
                "response": log.response,
                "created_at": log.created_at,
            }
            for log in logs
        ],
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
