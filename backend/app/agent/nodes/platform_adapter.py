"""小红书适配节点：定稿文案 → 发布内容包。"""

import uuid

from app.agent import db_ops
from app.agent.json_utils import parse_llm_json
from app.agent.prompts import xiaohongshu as xhs_prompt
from app.agent.state import ContentTaskState
from app.llm.ark_text import chat


async def platform_adapter(state: ContentTaskState) -> dict:
    task_id = uuid.UUID(state["task_id"])
    await db_ops.set_task_stage(task_id, "platform_adapting")

    topic = state["selected_topic"]
    assert topic is not None
    reply = await chat(
        xhs_prompt.build_user_prompt(title=topic["title"], content=state["content"]),
        system_prompt=xhs_prompt.SYSTEM,
        node="platform_adapter",
        task_id=task_id,
        temperature=0.7,
    )
    package = parse_llm_json(reply)
    if not isinstance(package, dict) or "title" not in package:
        raise ValueError(f"小红书适配节点返回格式异常：{reply[:200]}")

    package["images"] = [
        {"sequence": img["sequence"], "file_path": img["file_path"]}
        for img in sorted(state["images"], key=lambda x: x["sequence"])
    ]
    await db_ops.save_publish_record(task_id, package)
    await db_ops.set_task_stage(task_id, "completed", status="completed")
    return {"xhs_package": package}
