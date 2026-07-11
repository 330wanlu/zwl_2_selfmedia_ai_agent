"""发布与内容包导出 API。"""

import uuid

from fastapi import APIRouter, Depends
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.services import publish_service

router = APIRouter(prefix="/api/v1/tasks", tags=["publish"])


@router.get("/{task_id}/export")
async def export_content_package(
    task_id: uuid.UUID, session: AsyncSession = Depends(get_session)
):
    """导出完整内容包 JSON 文件（含标题/正文/标签/图片详情）。"""
    payload = await publish_service.build_export_payload(task_id, session)
    data = publish_service.export_json_bytes(payload)
    filename = f"task_{task_id}_xiaohongshu.json"
    return Response(
        content=data,
        media_type="application/json; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{task_id}/export/images.zip")
async def export_images_zip(
    task_id: uuid.UUID, session: AsyncSession = Depends(get_session)
):
    """批量下载该任务全部图片（zip）。"""
    data, filename = await publish_service.build_images_zip(task_id, session)
    return Response(
        content=data,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/{task_id}/publish/mark")
async def mark_published(task_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    """人工在小红书发布后，标记该任务内容包为已发布。"""
    record = await publish_service.mark_published(task_id, session)
    return {
        "task_id": str(task_id),
        "platform": record.platform,
        "status": record.status,
        "published_at": record.published_at,
        "content_package": record.content_package,
    }
