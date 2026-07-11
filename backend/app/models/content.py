import uuid

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPkMixin


class ContentVersion(Base, UUIDPkMixin, TimestampMixin):
    """文案版本，每轮人工反馈 + AI 重写都留档。"""

    __tablename__ = "content_versions"

    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), index=True
    )
    version: Mapped[int] = mapped_column(Integer, comment="版本号，从 1 开始")
    content: Mapped[str] = mapped_column(Text, comment="文案内容")
    feedback: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="人工对该版本的修改意见（通过则为空）"
    )
    status: Mapped[str] = mapped_column(
        String(20), default="draft", comment="draft / rejected / approved"
    )
