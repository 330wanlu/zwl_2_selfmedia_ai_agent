"""人工决策 API：选题 / 文案审核 / 图片审核 → resume 工作流。"""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.tasks import get_task_or_404
from app.core.database import get_session
from app.models.task import Task
from app.schemas.task import (
    ContentDecisionRequest,
    ImageDecisionRequest,
    TopicDecisionRequest,
)
from app.services import workflow_service

router = APIRouter(prefix="/api/v1/tasks/{task_id}/decisions", tags=["decisions"])


async def _ensure_waiting(task: Task, expected_type: str) -> None:
    """校验任务当前确实挂起在指定类型的 interrupt 上。"""
    if task.status != "running":
        raise HTTPException(status_code=409, detail=f"任务状态为 {task.status}，不能提交决策")
    if workflow_service.is_running(task.thread_id):
        raise HTTPException(status_code=409, detail="任务正在执行中，请稍后（可轮询任务详情）")
    pending = await workflow_service.get_pending_interrupt(task.thread_id)
    if pending is None:
        raise HTTPException(status_code=409, detail="任务当前没有等待决策的断点")
    if pending.get("type") != expected_type:
        raise HTTPException(
            status_code=409,
            detail=f"任务当前等待的决策是 {pending.get('type')}，不是 {expected_type}",
        )


@router.post("/topic", status_code=202)
async def decide_topic(
    task_id: uuid.UUID,
    req: TopicDecisionRequest,
    session: AsyncSession = Depends(get_session),
):
    task = await get_task_or_404(task_id, session)
    await _ensure_waiting(task, "topic_selection")

    if req.action == "regenerate":
        decision = {"action": "regenerate", "feedback": req.feedback}
    else:
        if req.topic_id is None:
            raise HTTPException(status_code=422, detail="选定选题时必须提供 topic_id")
        decision = {"action": "select", "topic_id": str(req.topic_id)}

    workflow_service.resume_workflow(task.id, task.thread_id, decision)
    return {"ok": True, "message": "决策已提交，工作流继续执行"}


@router.post("/content", status_code=202)
async def decide_content(
    task_id: uuid.UUID,
    req: ContentDecisionRequest,
    session: AsyncSession = Depends(get_session),
):
    task = await get_task_or_404(task_id, session)
    await _ensure_waiting(task, "content_review")

    if not req.approved and not (req.feedback or "").strip():
        raise HTTPException(status_code=422, detail="不通过文案时必须填写修改意见 feedback")

    decision = {"approved": req.approved, "feedback": req.feedback}
    workflow_service.resume_workflow(task.id, task.thread_id, decision)
    return {"ok": True, "message": "决策已提交，工作流继续执行"}


@router.post("/images", status_code=202)
async def decide_images(
    task_id: uuid.UUID,
    req: ImageDecisionRequest,
    session: AsyncSession = Depends(get_session),
):
    task = await get_task_or_404(task_id, session)
    await _ensure_waiting(task, "image_review")

    if not req.approved and not req.redraw:
        raise HTTPException(status_code=422, detail="不通过图片时必须提供重绘清单 redraw")

    decision = {
        "approved": req.approved,
        "redraw": [item.model_dump() for item in req.redraw],
    }
    workflow_service.resume_workflow(task.id, task.thread_id, decision)
    return {"ok": True, "message": "决策已提交，工作流继续执行"}
