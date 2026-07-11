"""工作流节点使用的数据库落库操作。

节点内的 DB 写入独立开短会话，避免与 LangGraph checkpoint 事务纠缠。
"""

import uuid
from typing import Any

from sqlalchemy import update

from app.core.database import async_session_factory
from app.models.content import ContentVersion
from app.models.image import Image
from app.models.publish_record import PublishRecord
from app.models.task import Task
from app.models.topic import Topic


async def set_task_stage(task_id: uuid.UUID, stage: str, status: str | None = None) -> None:
    values: dict[str, Any] = {"current_stage": stage}
    if status:
        values["status"] = status
    async with async_session_factory() as session:
        await session.execute(update(Task).where(Task.id == task_id).values(**values))
        await session.commit()


async def save_topics(task_id: uuid.UUID, topics: list[dict], batch: int) -> list[dict]:
    """落库候选选题，返回带 id 的 TopicItem 列表。"""
    items = []
    async with async_session_factory() as session:
        for t in topics:
            # 显式生成主键：mapped_column 的 Python 默认值在 flush 时才生效，
            # 这里 commit 前就要把 id 放进返回值
            row = Topic(
                id=uuid.uuid4(),
                task_id=task_id,
                title=t["title"],
                angle=t["angle"],
                target_audience=t["target_audience"],
                batch=batch,
            )
            session.add(row)
            items.append(
                {
                    "id": str(row.id),
                    "title": row.title,
                    "angle": row.angle,
                    "target_audience": row.target_audience,
                }
            )
        await session.commit()
    return items


async def mark_topic_selected(topic_id: uuid.UUID) -> None:
    async with async_session_factory() as session:
        await session.execute(
            update(Topic).where(Topic.id == topic_id).values(is_selected=True)
        )
        await session.commit()


async def save_content_version(task_id: uuid.UUID, version: int, content: str) -> None:
    async with async_session_factory() as session:
        session.add(
            ContentVersion(task_id=task_id, version=version, content=content, status="draft")
        )
        await session.commit()


async def review_content_version(
    task_id: uuid.UUID, version: int, *, approved: bool, feedback: str | None = None
) -> None:
    async with async_session_factory() as session:
        await session.execute(
            update(ContentVersion)
            .where(ContentVersion.task_id == task_id, ContentVersion.version == version)
            .values(status="approved" if approved else "rejected", feedback=feedback)
        )
        await session.commit()


async def save_images(task_id: uuid.UUID, images: list[dict]) -> None:
    """首次出图整批落库（sequence 唯一标识一张图）。"""
    async with async_session_factory() as session:
        for img in images:
            session.add(
                Image(
                    task_id=task_id,
                    sequence=img["sequence"],
                    summary_text=img["summary_text"],
                    gen_prompt=img["gen_prompt"],
                    file_path=img["file_path"],
                    status="generated",
                )
            )
        await session.commit()


async def update_image_redraw(
    task_id: uuid.UUID, sequence: int, *, file_path: str, gen_prompt: str, retry_count: int
) -> None:
    async with async_session_factory() as session:
        await session.execute(
            update(Image)
            .where(Image.task_id == task_id, Image.sequence == sequence)
            .values(
                file_path=file_path,
                gen_prompt=gen_prompt,
                retry_count=retry_count,
                status="generated",
            )
        )
        await session.commit()


async def approve_all_images(task_id: uuid.UUID) -> None:
    async with async_session_factory() as session:
        await session.execute(
            update(Image).where(Image.task_id == task_id).values(status="approved")
        )
        await session.commit()


async def save_publish_record(task_id: uuid.UUID, package: dict) -> None:
    async with async_session_factory() as session:
        session.add(
            PublishRecord(
                task_id=task_id,
                platform="xiaohongshu",
                content_package=package,
                status="pending",
            )
        )
        await session.commit()
