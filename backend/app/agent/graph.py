"""StateGraph 组装：方向 → 选题 → 文案 → 分镜 → 出图 → 小红书内容包。

拓扑（三个人工断点）：

topic_generator → topic_gate ──重新生成──→ topic_generator
                      │选定
                      ▼
             content_writer → content_gate ──修改意见──→ content_writer
                                   │通过
                                   ▼
                        storyboard_planner → image_generator → image_gate ──重绘──→ image_generator
                                                                    │通过
                                                                    ▼
                                                            platform_adapter → END
"""

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.agent.checkpointer import get_checkpointer
from app.agent.nodes.content_writer import content_writer
from app.agent.nodes.human_gates import content_gate, image_gate, topic_gate
from app.agent.nodes.image_generator import image_generator
from app.agent.nodes.platform_adapter import platform_adapter
from app.agent.nodes.storyboard_planner import storyboard_planner
from app.agent.nodes.topic_generator import topic_generator
from app.agent.state import ContentTaskState

_graph: CompiledStateGraph | None = None


def _route_after_topic_gate(state: ContentTaskState) -> str:
    return "content_writer" if state.get("selected_topic") else "topic_generator"


def _route_after_content_gate(state: ContentTaskState) -> str:
    return "storyboard_planner" if state.get("content_approved") else "content_writer"


def _route_after_image_gate(state: ContentTaskState) -> str:
    return "platform_adapter" if state.get("images_approved") else "image_generator"


def build_graph() -> CompiledStateGraph:
    builder = StateGraph(ContentTaskState)

    builder.add_node("topic_generator", topic_generator)
    builder.add_node("topic_gate", topic_gate)
    builder.add_node("content_writer", content_writer)
    builder.add_node("content_gate", content_gate)
    builder.add_node("storyboard_planner", storyboard_planner)
    builder.add_node("image_generator", image_generator)
    builder.add_node("image_gate", image_gate)
    builder.add_node("platform_adapter", platform_adapter)

    builder.add_edge(START, "topic_generator")
    builder.add_edge("topic_generator", "topic_gate")
    builder.add_conditional_edges(
        "topic_gate", _route_after_topic_gate, ["topic_generator", "content_writer"]
    )
    builder.add_edge("content_writer", "content_gate")
    builder.add_conditional_edges(
        "content_gate", _route_after_content_gate, ["content_writer", "storyboard_planner"]
    )
    builder.add_edge("storyboard_planner", "image_generator")
    builder.add_edge("image_generator", "image_gate")
    builder.add_conditional_edges(
        "image_gate", _route_after_image_gate, ["image_generator", "platform_adapter"]
    )
    builder.add_edge("platform_adapter", END)

    return builder.compile(checkpointer=get_checkpointer())


def init_graph() -> None:
    """在 checkpointer 初始化后编译图（FastAPI lifespan 调用）。"""
    global _graph
    _graph = build_graph()


def get_graph() -> CompiledStateGraph:
    if _graph is None:
        raise RuntimeError("工作流图尚未初始化（应在 FastAPI lifespan 中调用 init_graph）")
    return _graph
