import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPkMixin


class PublishRecord(Base, UUIDPkMixin, TimestampMixin):
    """发布记录：MVP 记录内容包导出与人工「已发布」标记。"""

    __tablename__ = "publish_records"

    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), index=True
    )
    platform: Mapped[str] = mapped_column(String(50), comment="平台标识，如 xiaohongshu")
    content_package: Mapped[dict] = mapped_column(JSONB, comment="平台适配后的内容包")
    status: Mapped[str] = mapped_column(
        String(20), default="pending", comment="pending / published"
    )
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="人工标记已发布的时间"
    )
