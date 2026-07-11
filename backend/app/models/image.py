import uuid

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPkMixin


class Image(Base, UUIDPkMixin, TimestampMixin):
    """分镜图片。"""

    __tablename__ = "images"

    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), index=True
    )
    sequence: Mapped[int] = mapped_column(Integer, comment="序号（第几张）")
    summary_text: Mapped[str] = mapped_column(Text, comment="该图承载的文案摘要")
    gen_prompt: Mapped[str] = mapped_column(Text, comment="生成图片使用的 Prompt")
    file_path: Mapped[str] = mapped_column(String(500), comment="本地文件相对路径")
    status: Mapped[str] = mapped_column(
        String(20), default="generated", comment="generated / rejected / approved"
    )
    retry_count: Mapped[int] = mapped_column(Integer, default=0, comment="重绘次数")
