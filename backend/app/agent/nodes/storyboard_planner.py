"""分镜节点：把定稿文案压缩成 3~5 张配图规划。"""

import uuid

from app.agent import db_ops
from app.agent.json_utils import parse_llm_json
from app.agent.prompts import storyboard as storyboard_prompt
from app.agent.state import ContentTaskState
from app.llm.ark_text import chat

IMAGE_COUNT = 4


async def storyboard_planner(state: ContentTaskState) -> dict:
    task_id = uuid.UUID(state["task_id"])
    await db_ops.set_task_stage(task_id, "storyboard_planning")

    topic = state["selected_topic"]
    assert topic is not None
    user_prompt = storyboard_prompt.build_user_prompt(
        title=topic["title"], content=state["content"], image_count=IMAGE_COUNT
    )
    reply = await chat(
        user_prompt,
        system_prompt=storyboard_prompt.SYSTEM,
        node="storyboard_planner",
        task_id=task_id,
        temperature=0.7,
    )
    boards = parse_llm_json(reply)
    if not isinstance(boards, list) or not boards:
        raise ValueError(f"分镜节点返回格式异常：{reply[:200]}")

    storyboards = [
        {
            "sequence": int(b.get("sequence", i + 1)),
            "summary_text": b["summary_text"],
            "image_prompt": b["image_prompt"],
        }
        for i, b in enumerate(boards)
    ]
    return {"storyboards": storyboards}
