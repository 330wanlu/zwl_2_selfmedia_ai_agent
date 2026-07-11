"""LangGraph 工作流 State 定义。

整个流水线是单线顺序执行（无并发写同一字段），因此不需要 reducer，
每个节点直接整体覆盖自己负责的字段。
"""

from typing import Any, TypedDict


class TopicItem(TypedDict):
    """候选选题（与 topics 表一行对应）。"""

    id: str
    title: str
    angle: str
    target_audience: str


class StoryboardItem(TypedDict):
    """分镜：一张配图的内容规划。"""

    sequence: int
    summary_text: str
    image_prompt: str


class ImageItem(TypedDict):
    """已生成的图片（当前有效版本）。"""

    sequence: int
    file_path: str
    gen_prompt: str
    status: str  # generated / approved
    retry_count: int


class ContentTaskState(TypedDict, total=False):
    # 基础
    task_id: str
    direction: str

    # 选题阶段
    topics: list[TopicItem]
    topic_batch: int
    topic_feedback: str | None  # 重新生成选题时用户给的意见
    selected_topic: TopicItem | None

    # 文案阶段
    content: str
    content_version: int
    review_feedbacks: list[str]
    content_approved: bool

    # 分镜与出图阶段
    storyboards: list[StoryboardItem]
    images: list[ImageItem]
    redraw_requests: list[dict[str, Any]]  # [{"sequence": 2, "hint": "背景换成粉色"}]
    images_approved: bool

    # 小红书内容包
    xhs_package: dict[str, Any] | None
