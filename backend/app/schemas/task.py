"""任务与决策相关的请求/响应模型。"""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class TaskCreateRequest(BaseModel):
    direction: str = Field(min_length=1, max_length=500, description="内容方向")


class TaskBrief(BaseModel):
    id: uuid.UUID
    direction: str
    status: str
    current_stage: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TaskDetail(TaskBrief):
    running: bool = Field(description="工作流是否正在后台执行")
    pending_decision: dict[str, Any] | None = Field(
        default=None, description="当前等待人工决策的数据（interrupt 载荷）"
    )


class TopicDecisionRequest(BaseModel):
    """选题决策：给 topic_id 表示选定；action=regenerate 表示重新生成一批。"""

    action: str = Field(default="select", description="select / regenerate")
    topic_id: uuid.UUID | None = None
    feedback: str | None = Field(default=None, description="regenerate 时的意见（可选）")


class ContentDecisionRequest(BaseModel):
    approved: bool
    feedback: str | None = Field(default=None, description="不通过时必填的修改意见")


class RedrawItem(BaseModel):
    sequence: int
    hint: str | None = Field(default=None, description="重绘调整要求（可选）")


class ImageDecisionRequest(BaseModel):
    approved: bool
    redraw: list[RedrawItem] = Field(default_factory=list, description="不通过时的重绘清单")
