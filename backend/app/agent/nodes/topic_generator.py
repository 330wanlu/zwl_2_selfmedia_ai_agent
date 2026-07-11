"""选题节点：根据内容方向生成 5 个候选选题。"""

import uuid

from app.agent import db_ops
from app.agent.json_utils import parse_llm_json
from app.agent.prompts import topic as topic_prompt
from app.agent.state import ContentTaskState
from app.llm.ark_text import chat


async def topic_generator(state: ContentTaskState) -> dict:
    task_id = uuid.UUID(state["task_id"])
    batch = state.get("topic_batch", 0) + 1
    await db_ops.set_task_stage(task_id, "topic_generating")

    previous_titles = [t["title"] for t in state.get("topics") or []]
    user_prompt = topic_prompt.build_user_prompt(
        state["direction"],
        previous_titles=previous_titles if batch > 1 else None,
        feedback=state.get("topic_feedback"),
    )
    reply = await chat(
        user_prompt,
        system_prompt=topic_prompt.SYSTEM,
        node="topic_generator",
        task_id=task_id,
        temperature=0.9,
    )
    raw_topics = parse_llm_json(reply)
    if not isinstance(raw_topics, list) or not raw_topics:
        raise ValueError(f"选题节点返回格式异常：{reply[:200]}")

    topics = await db_ops.save_topics(task_id, raw_topics, batch)
    return {"topics": topics, "topic_batch": batch, "topic_feedback": None}
