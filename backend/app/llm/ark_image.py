import base64
import time
import uuid

import httpx

from app.config import settings
from app.llm.call_logger import log_llm_call


async def generate_image(
    prompt: str,
    *,
    filename: str | None = None,
    size: str = "2K",
    node: str = "adhoc",
    task_id: uuid.UUID | None = None,
) -> str:
    """调用 Seedream 生图并保存到本地 image_dir，返回相对文件名。"""
    payload = {
        "model": settings.image_model,
        "prompt": prompt,
        "size": size,
        "response_format": "b64_json",
        "watermark": False,
    }
    headers = {"Authorization": f"Bearer {settings.ark_api_key}"}
    url = f"{settings.llm_base_url}/images/generations"

    start = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
        b64 = data["data"][0]["b64_json"]
    except httpx.HTTPStatusError as e:
        detail = f"{e.response.status_code}: {e.response.text[:500]}"
        await log_llm_call(
            node=node, call_type="image", model=settings.image_model,
            prompt={"prompt": prompt, "size": size}, task_id=task_id,
            duration_ms=int((time.monotonic() - start) * 1000), error=detail,
        )
        raise RuntimeError(f"生图接口报错 {detail}") from e
    except Exception as e:
        await log_llm_call(
            node=node, call_type="image", model=settings.image_model,
            prompt={"prompt": prompt, "size": size}, task_id=task_id,
            duration_ms=int((time.monotonic() - start) * 1000), error=str(e),
        )
        raise

    if filename is None:
        filename = f"{uuid.uuid4().hex}.png"
    file_path = settings.image_dir_path / filename
    file_path.write_bytes(base64.b64decode(b64))

    await log_llm_call(
        node=node, call_type="image", model=settings.image_model,
        prompt={"prompt": prompt, "size": size}, response=str(filename),
        task_id=task_id, duration_ms=int((time.monotonic() - start) * 1000),
    )
    return filename
