"""任务 API：创建 / 列表 / 详情 / 内容查询。"""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.models.image import Image
from app.models.publish_record import PublishRecord
from app.models.task import Task
from app.schemas.task import TaskBrief, TaskCreateRequest, TaskDetail
from app.services import workflow_service

router = APIRouter(prefix="/api/v1/tasks", tags=["tasks"])


async def get_task_or_404(task_id: uuid.UUID, session: AsyncSession) -> Task:
    task = await session.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    return task


@router.post("", response_model=TaskBrief, status_code=201)
async def create_task(
    req: TaskCreateRequest, session: AsyncSession = Depends(get_session)
):
    task = Task(
        direction=req.direction.strip(),
        status="running",
        current_stage="topic_generating",
        thread_id=f"task-{uuid.uuid4().hex}",
    )
    session.add(task)
    await session.commit()
    await session.refresh(task)

    workflow_service.start_workflow(task.id, task.thread_id, task.direction)
    return task


@router.get("", response_model=list[TaskBrief])
async def list_tasks(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Task).order_by(Task.created_at.desc()))
    return list(result.scalars())


@router.get("/{task_id}", response_model=TaskDetail)
async def get_task(task_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    task = await get_task_or_404(task_id, session)
    running = workflow_service.is_running(task.thread_id)
    pending = None
    if not running and task.status == "running":
        pending = await workflow_service.get_pending_interrupt(task.thread_id)
    return TaskDetail(
        id=task.id,
        direction=task.direction,
        status=task.status,
        current_stage=task.current_stage,
        created_at=task.created_at,
        updated_at=task.updated_at,
        running=running,
        pending_decision=pending,
    )


@router.get("/{task_id}/images")
async def get_task_images(task_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    await get_task_or_404(task_id, session)
    result = await session.execute(
        select(Image).where(Image.task_id == task_id).order_by(Image.sequence)
    )
    return [
        {
            "sequence": img.sequence,
            "summary_text": img.summary_text,
            "file_path": img.file_path,
            "url": f"/images/{img.file_path}",
            "status": img.status,
            "retry_count": img.retry_count,
        }
        for img in result.scalars()
    ]


@router.get("/{task_id}/platform-contents")
async def get_platform_contents(
    task_id: uuid.UUID, session: AsyncSession = Depends(get_session)
):
    await get_task_or_404(task_id, session)
    result = await session.execute(
        select(PublishRecord)
        .where(PublishRecord.task_id == task_id)
        .order_by(PublishRecord.created_at.desc())
    )
    records = list(result.scalars())
    if not records:
        raise HTTPException(status_code=404, detail="内容包尚未生成")
    record = records[0]
    return {
        "platform": record.platform,
        "status": record.status,
        "published_at": record.published_at,
        "content_package": record.content_package,
    }


@router.post("/{task_id}/cancel", response_model=TaskBrief)
async def cancel_task(task_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    """取消未完成任务：停止后台执行，之后不能再提交决策。"""
    task = await get_task_or_404(task_id, session)
    if task.status in ("completed", "cancelled"):
        raise HTTPException(
            status_code=409, detail=f"任务已是 {task.status}，无需取消"
        )
    task.status = "cancelled"
    task.current_stage = "cancelled"
    await session.commit()
    await session.refresh(task)
    workflow_service.cancel_background_run(task.thread_id)
    return task
