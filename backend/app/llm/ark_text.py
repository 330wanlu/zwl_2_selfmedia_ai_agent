import time
import uuid

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.config import settings
from app.llm.call_logger import log_llm_call


def get_chat_model(temperature: float = 0.8) -> ChatOpenAI:
    """豆包文本模型（火山方舟 OpenAI 兼容接口）。"""
    return ChatOpenAI(
        model=settings.llm_model,
        api_key=settings.ark_api_key,
        base_url=settings.llm_base_url,
        temperature=temperature,
    )


async def chat(
    user_prompt: str,
    *,
    system_prompt: str | None = None,
    node: str = "adhoc",
    task_id: uuid.UUID | None = None,
    temperature: float = 0.8,
) -> str:
    """带调用日志的文本生成入口，工作流节点和调试端点统一走这里。"""
    messages = []
    if system_prompt:
        messages.append(SystemMessage(content=system_prompt))
    messages.append(HumanMessage(content=user_prompt))

    prompt_record = {"system": system_prompt, "user": user_prompt}
    start = time.monotonic()
    try:
        result = await get_chat_model(temperature).ainvoke(messages)
    except Exception as e:
        await log_llm_call(
            node=node, call_type="text", model=settings.llm_model,
            prompt=prompt_record, task_id=task_id,
            duration_ms=int((time.monotonic() - start) * 1000), error=str(e),
        )
        raise

    usage = result.usage_metadata or {}
    text = result.text if isinstance(result.text, str) else result.text()
    await log_llm_call(
        node=node, call_type="text", model=settings.llm_model,
        prompt=prompt_record, response=text, task_id=task_id,
        duration_ms=int((time.monotonic() - start) * 1000),
        prompt_tokens=usage.get("input_tokens"),
        completion_tokens=usage.get("output_tokens"),
    )
    return text
