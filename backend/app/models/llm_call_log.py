import uuid

from sqlalchemy import Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPkMixin


class LlmCallLog(Base, UUIDPkMixin, TimestampMixin):
    """每一次 LLM / 生图调用的完整记录，用于调试回溯。"""

    __tablename__ = "llm_call_logs"

    task_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True, comment="关联任务，冒烟测试等场景可为空"
    )
    node: Mapped[str] = mapped_column(String(100), comment="调用来源节点名，如 content_writer")
    call_type: Mapped[str] = mapped_column(String(20), comment="text / image")
    model: Mapped[str] = mapped_column(String(100))
    prompt: Mapped[dict] = mapped_column(JSONB, comment="完整输入（system + user 等）")
    response: Mapped[str | None] = mapped_column(Text, nullable=True, comment="完整响应文本或图片路径")
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    prompt_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completion_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
