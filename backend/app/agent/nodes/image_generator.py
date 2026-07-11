"""图片生成节点：首次整批出图 / 按 redraw_requests 单张重绘。"""

import asyncio
import uuid

from app.agent import db_ops
from app.agent.state import ContentTaskState
from app.llm.ark_image import generate_image

# 生图串行执行、单张之间稍作间隔，避免触发方舟并发/限流
_GEN_INTERVAL_SECONDS = 1


async def image_generator(state: ContentTaskState) -> dict:
    task_id = uuid.UUID(state["task_id"])
    await db_ops.set_task_stage(task_id, "image_generating")

    redraw_requests = state.get("redraw_requests") or []
    if redraw_requests:
        return await _redraw(task_id, state, redraw_requests)
    return await _generate_all(task_id, state)


async def _generate_all(task_id: uuid.UUID, state: ContentTaskState) -> dict:
    images = []
    for board in state["storyboards"]:
        filename = f"{task_id.hex}_{board['sequence']}_{uuid.uuid4().hex[:8]}.png"
        await generate_image(
            board["image_prompt"],
            filename=filename,
            node="image_generator",
            task_id=task_id,
        )
        images.append(
            {
                "sequence": board["sequence"],
                "file_path": filename,
                "gen_prompt": board["image_prompt"],
                "summary_text": board["summary_text"],
                "status": "generated",
                "retry_count": 0,
            }
        )
        await asyncio.sleep(_GEN_INTERVAL_SECONDS)

    await db_ops.save_images(task_id, images)
    return {"images": images}


async def _redraw(
    task_id: uuid.UUID, state: ContentTaskState, redraw_requests: list[dict]
) -> dict:
    images = [dict(img) for img in state["images"]]
    by_seq = {img["sequence"]: img for img in images}

    for req in redraw_requests:
        seq = int(req["sequence"])
        img = by_seq.get(seq)
        if img is None:
            continue
        hint = (req.get("hint") or "").strip()
        new_prompt = img["gen_prompt"]
        if hint:
            new_prompt = f"{img['gen_prompt']}\n\n重绘调整要求：{hint}"
        filename = f"{task_id.hex}_{seq}_{uuid.uuid4().hex[:8]}.png"
        await generate_image(
            new_prompt, filename=filename, node="image_generator", task_id=task_id
        )
        img["file_path"] = filename
        img["gen_prompt"] = new_prompt
        img["retry_count"] = img.get("retry_count", 0) + 1
        img["status"] = "generated"
        await db_ops.update_image_redraw(
            task_id,
            seq,
            file_path=filename,
            gen_prompt=new_prompt,
            retry_count=img["retry_count"],
        )
        await asyncio.sleep(_GEN_INTERVAL_SECONDS)

    return {"images": images, "redraw_requests": []}
