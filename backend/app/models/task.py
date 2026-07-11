from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPkMixin


class Task(Base, UUIDPkMixin, TimestampMixin):
    """内容生产任务，一个任务对应一个 LangGraph 工作流线程。"""

    __tablename__ = "tasks"

    direction: Mapped[str] = mapped_column(String(500), comment="用户输入的内容方向")
    status: Mapped[str] = mapped_column(
        String(50), default="running", comment="running / completed / cancelled / failed"
    )
    current_stage: Mapped[str] = mapped_column(
        String(50), default="topic_generating", comment="当前阶段，供前端展示"
    )
    thread_id: Mapped[str] = mapped_column(
        String(100), unique=True, comment="LangGraph checkpoint 线程 ID"
    )
