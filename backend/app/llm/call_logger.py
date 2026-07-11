import logging
import uuid
from typing import Any

from app.core.database import async_session_factory
from app.models.llm_call_log import LlmCallLog

logger = logging.getLogger(__name__)


async def log_llm_call(
    *,
    node: str,
    call_type: str,
    model: str,
    prompt: dict[str, Any],
    response: str | None = None,
    task_id: uuid.UUID | None = None,
    duration_ms: int | None = None,
    prompt_tokens: int | None = None,
    completion_tokens: int | None = None,
    error: str | None = None,
) -> None:
    """把一次 LLM / 生图调用落库，同时在控制台输出摘要。日志失败不影响主流程。"""
    logger.debug(
        "[LLM %s] node=%s model=%s duration=%sms error=%s",
        call_type, node, model, duration_ms, error,
    )
    try:
        async with async_session_factory() as session:
            session.add(
                LlmCallLog(
                    task_id=task_id,
                    node=node,
                    call_type=call_type,
                    model=model,
                    prompt=prompt,
                    response=response,
                    duration_ms=duration_ms,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    error=error,
                )
            )
            await session.commit()
    except Exception:
        logger.exception("写入 llm_call_logs 失败（不影响主流程）")
