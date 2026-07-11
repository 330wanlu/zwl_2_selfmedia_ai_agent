"""发布与内容包导出服务。"""

import io
import json
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.image import Image
from app.models.publish_record import PublishRecord
from app.models.task import Task


async def get_task_or_404(task_id: uuid.UUID, session: AsyncSession) -> Task:
    task = await session.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    return task


async def get_latest_publish_record(
    task_id: uuid.UUID, session: AsyncSession
) -> PublishRecord:
    result = await session.execute(
        select(PublishRecord)
        .where(PublishRecord.task_id == task_id)
        .order_by(PublishRecord.created_at.desc())
        .limit(1)
    )
    record = result.scalar_one_or_none()
    if record is None:
        raise HTTPException(status_code=404, detail="内容包尚未生成，请等待任务完成")
    return record


async def build_export_payload(task_id: uuid.UUID, session: AsyncSession) -> dict:
    """组装可下载的完整内容包 JSON（含图片 URL 与本地路径）。"""
    task = await get_task_or_404(task_id, session)
    record = await get_latest_publish_record(task_id, session)

    img_result = await session.execute(
        select(Image).where(Image.task_id == task_id).order_by(Image.sequence)
    )
    images = [
        {
            "sequence": img.sequence,
            "summary_text": img.summary_text,
            "file_path": img.file_path,
            "url": f"/images/{img.file_path}",
            "status": img.status,
            "retry_count": img.retry_count,
        }
        for img in img_result.scalars()
    ]

    package = dict(record.content_package or {})
    package["images"] = package.get("images") or [img["url"] for img in images]

    return {
        "task_id": str(task.id),
        "direction": task.direction,
        "platform": record.platform,
        "status": record.status,
        "published_at": record.published_at.isoformat() if record.published_at else None,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "content_package": package,
        "images_detail": images,
    }


def export_json_bytes(payload: dict) -> bytes:
    return json.dumps(payload, ensure_ascii=False, indent=2, default=str).encode("utf-8")


async def build_images_zip(task_id: uuid.UUID, session: AsyncSession) -> tuple[bytes, str]:
    """把任务全部图片打成 zip，返回 (bytes, 文件名)。"""
    await get_task_or_404(task_id, session)
    result = await session.execute(
        select(Image).where(Image.task_id == task_id).order_by(Image.sequence)
    )
    images = list(result.scalars())
    if not images:
        raise HTTPException(status_code=404, detail="该任务尚无图片")

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for img in images:
            path = Path(settings.image_dir_path) / img.file_path
            if not path.is_file():
                raise HTTPException(
                    status_code=404,
                    detail=f"图片文件缺失: {img.file_path}",
                )
            arcname = f"{img.sequence:02d}_{path.name}"
            zf.write(path, arcname=arcname)
    filename = f"task_{task_id}_images.zip"
    return buf.getvalue(), filename


async def mark_published(task_id: uuid.UUID, session: AsyncSession) -> PublishRecord:
    record = await get_latest_publish_record(task_id, session)
    if record.status == "published":
        return record
    record.status = "published"
    record.published_at = datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(record)
    return record
