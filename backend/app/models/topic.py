import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPkMixin


class Topic(Base, UUIDPkMixin, TimestampMixin):
    """AI 生成的候选选题。"""

    __tablename__ = "topics"

    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(200), comment="选题标题")
    angle: Mapped[str] = mapped_column(Text, comment="切入角度")
    target_audience: Mapped[str] = mapped_column(String(200), comment="目标人群")
    is_selected: Mapped[bool] = mapped_column(Boolean, default=False)
    batch: Mapped[int] = mapped_column(Integer, default=1, comment="生成批次（重新生成时递增）")
