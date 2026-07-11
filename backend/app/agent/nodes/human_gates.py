"""三个人工审核断点（interrupt gate 节点）。

注意：interrupt() 恢复时会从节点开头重新执行，因此 gate 节点在
interrupt 之前只做幂等操作（更新任务阶段）。
"""

import uuid

from langgraph.types import interrupt

from app.agent import db_ops
from app.agent.state import ContentTaskState


async def topic_gate(state: ContentTaskState) -> dict:
    """选题决策：等待人工从候选选题中选一个，或要求重新生成。"""
    task_id = uuid.UUID(state["task_id"])
    await db_ops.set_task_stage(task_id, "waiting_topic_selection")

    decision = interrupt(
        {
            "type": "topic_selection",
            "topics": state["topics"],
            "batch": state.get("topic_batch", 1),
        }
    )
    # decision: {"action": "select", "topic_id": "..."} 或 {"action": "regenerate", "feedback": "..."}
    if decision.get("action") == "regenerate":
        return {"selected_topic": None, "topic_feedback": decision.get("feedback")}

    topic_id = decision["topic_id"]
    selected = next((t for t in state["topics"] if t["id"] == topic_id), None)
    if selected is None:
        raise ValueError(f"topic_id {topic_id} 不在候选选题中")
    await db_ops.mark_topic_selected(uuid.UUID(topic_id))
    return {"selected_topic": selected}


async def content_gate(state: ContentTaskState) -> dict:
    """文案审核：通过则进入分镜；否则记录修改意见回到文案节点。"""
    task_id = uuid.UUID(state["task_id"])
    await db_ops.set_task_stage(task_id, "waiting_content_review")

    decision = interrupt(
        {
            "type": "content_review",
            "content": state["content"],
            "version": state.get("content_version", 1),
            "feedback_history": state.get("review_feedbacks") or [],
        }
    )
    # decision: {"approved": true} 或 {"approved": false, "feedback": "..."}
    version = state.get("content_version", 1)
    if decision.get("approved"):
        await db_ops.review_content_version(task_id, version, approved=True)
        return {"content_approved": True}

    feedback = (decision.get("feedback") or "").strip()
    if not feedback:
        raise ValueError("驳回文案时必须提供修改意见 feedback")
    await db_ops.review_content_version(task_id, version, approved=False, feedback=feedback)
    feedbacks = list(state.get("review_feedbacks") or [])
    feedbacks.append(feedback)
    return {"content_approved": False, "review_feedbacks": feedbacks}


async def image_gate(state: ContentTaskState) -> dict:
    """图片审核：全部通过进入小红书适配；否则按清单单张重绘。"""
    task_id = uuid.UUID(state["task_id"])
    await db_ops.set_task_stage(task_id, "waiting_image_review")

    decision = interrupt(
        {
            "type": "image_review",
            "images": [
                {
                    "sequence": img["sequence"],
                    "file_path": img["file_path"],
                    "url": f"/images/{img['file_path']}",
                    "retry_count": img.get("retry_count", 0),
                }
                for img in sorted(state["images"], key=lambda x: x["sequence"])
            ],
        }
    )
    # decision: {"approved": true} 或 {"approved": false, "redraw": [{"sequence": 2, "hint": "..."}]}
    if decision.get("approved"):
        await db_ops.approve_all_images(task_id)
        return {"images_approved": True, "redraw_requests": []}

    redraw = decision.get("redraw") or []
    if not redraw:
        raise ValueError("驳回图片时必须提供重绘清单 redraw")
    return {"images_approved": False, "redraw_requests": redraw}
