"""文案节点：首次生成 / 根据反馈重写。"""

import uuid

from app.agent import db_ops
from app.agent.prompts import content as content_prompt
from app.agent.state import ContentTaskState
from app.llm.ark_text import chat


async def content_writer(state: ContentTaskState) -> dict:
    task_id = uuid.UUID(state["task_id"])
    await db_ops.set_task_stage(task_id, "content_generating")

    topic = state["selected_topic"]
    assert topic is not None
    feedbacks = state.get("review_feedbacks") or []
    version = state.get("content_version", 0) + 1

    user_prompt = content_prompt.build_user_prompt(
        title=topic["title"],
        angle=topic["angle"],
        target_audience=topic["target_audience"],
        direction=state["direction"],
        current_content=state.get("content") if feedbacks else None,
        feedbacks=feedbacks or None,
    )
    text = await chat(
        user_prompt,
        system_prompt=content_prompt.SYSTEM,
        node="content_writer",
        task_id=task_id,
        temperature=0.8,
    )
    content = text.strip()
    await db_ops.save_content_version(task_id, version, content)
    return {"content": content, "content_version": version}
