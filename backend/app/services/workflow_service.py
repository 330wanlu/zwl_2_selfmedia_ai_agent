"""工作流服务：启动 / resume / 查询挂起状态。

LLM 链路一次要跑几十秒到几分钟，因此启动和 resume 都放到后台
asyncio 任务里执行，API 立即返回；前端通过轮询任务详情获取进展。
"""

import asyncio
import logging
import uuid
from typing import Any

from langgraph.types import Command

from app.agent import db_ops
from app.agent.graph import get_graph

logger = logging.getLogger(__name__)

# 进行中的后台任务引用（防 GC；也用于判断"是否正在跑"）
_running_tasks: dict[str, asyncio.Task] = {}


def _thread_config(thread_id: str) -> dict:
    return {"configurable": {"thread_id": thread_id}}


async def _run_graph(task_id: uuid.UUID, thread_id: str, payload: Any) -> None:
    """后台执行图直到 END 或下一个 interrupt。payload 为初始 State 或 Command。"""
    try:
        await get_graph().ainvoke(payload, config=_thread_config(thread_id))
    except asyncio.CancelledError:
        logger.info("任务 %s 后台工作流被取消", task_id)
        raise
    except Exception:
        logger.exception("任务 %s 工作流执行失败", task_id)
        try:
            from app.core.database import async_session_factory
            from app.models.task import Task

            async with async_session_factory() as session:
                row = await session.get(Task, task_id)
                if row is not None and row.status == "cancelled":
                    return
            await db_ops.set_task_stage(task_id, "failed", status="failed")
        except Exception:
            logger.exception("标记任务失败状态时出错")
    finally:
        _running_tasks.pop(thread_id, None)


def start_workflow(task_id: uuid.UUID, thread_id: str, direction: str) -> None:
    initial_state = {
        "task_id": str(task_id),
        "direction": direction,
        "topics": [],
        "topic_batch": 0,
        "review_feedbacks": [],
        "content_version": 0,
    }
    task = asyncio.create_task(_run_graph(task_id, thread_id, initial_state))
    _running_tasks[thread_id] = task


def resume_workflow(task_id: uuid.UUID, thread_id: str, decision: dict) -> None:
    if is_running(thread_id):
        raise RuntimeError("任务正在执行中，不能提交决策")
    task = asyncio.create_task(_run_graph(task_id, thread_id, Command(resume=decision)))
    _running_tasks[thread_id] = task


def is_running(thread_id: str) -> bool:
    task = _running_tasks.get(thread_id)
    return task is not None and not task.done()


def cancel_background_run(thread_id: str) -> bool:
    """取消正在执行的后台 ainvoke（若有）。返回是否发出了 cancel。"""
    task = _running_tasks.get(thread_id)
    if task is None or task.done():
        return False
    task.cancel()
    return True


async def get_pending_interrupt(thread_id: str) -> dict | None:
    """读取 checkpoint，返回当前挂起的 interrupt 载荷（无挂起返回 None）。"""
    snapshot = await get_graph().aget_state(_thread_config(thread_id))
    if snapshot is None or not snapshot.interrupts:
        return None
    return snapshot.interrupts[0].value


async def get_state_values(thread_id: str) -> dict:
    snapshot = await get_graph().aget_state(_thread_config(thread_id))
    if snapshot is None:
        return {}
    return dict(snapshot.values or {})


async def get_state_history(thread_id: str) -> list[dict]:
    """返回 checkpoint 历史（从新到旧），用于调试工作流走向。"""
    history: list[dict] = []
    async for snapshot in get_graph().aget_state_history(_thread_config(thread_id)):
        history.append(
            {
                "checkpoint_id": snapshot.config.get("configurable", {}).get("checkpoint_id"),
                "created_at": getattr(snapshot, "created_at", None),
                "next": list(snapshot.next) if snapshot.next else [],
                "has_interrupts": bool(snapshot.interrupts),
                "interrupt_types": [
                    (i.value or {}).get("type") for i in (snapshot.interrupts or [])
                ],
                "current_stage": (snapshot.values or {}).get("current_stage"),
                "values_summary": {
                    k: (v if not isinstance(v, str) or len(v) < 200 else v[:200] + "…")
                    for k, v in (snapshot.values or {}).items()
                    if k in (
                        "direction",
                        "topic_batch",
                        "content_version",
                        "revision_count",
                        "current_stage",
                    )
                },
            }
        )
    return history


async def recover_running_tasks() -> None:
    """服务启动时恢复孤儿任务。

    服务重启（含 --reload 热重载）会杀掉正在执行的后台工作流协程。
    对 status=running 的任务：
    - 挂在 interrupt 上 → 无需处理，等人工决策；
    - 有 checkpoint 但没挂起 → 从最近 checkpoint 续跑（ainvoke None）；
    - 完全没有 checkpoint → 用任务行里的 direction 重新启动。
    """
    from sqlalchemy import select

    from app.core.database import async_session_factory
    from app.models.task import Task

    async with async_session_factory() as session:
        result = await session.execute(select(Task).where(Task.status == "running"))
        tasks = list(result.scalars())

    for t in tasks:
        if is_running(t.thread_id):
            continue
        snapshot = await get_graph().aget_state(_thread_config(t.thread_id))
        if snapshot is not None and snapshot.interrupts:
            continue  # 正常挂起，等人工决策
        if snapshot is not None and snapshot.next:
            logger.info("恢复孤儿任务 %s（从 checkpoint 续跑）", t.id)
            job = asyncio.create_task(_run_graph(t.id, t.thread_id, None))
            _running_tasks[t.thread_id] = job
        elif snapshot is None or not (snapshot.values or {}):
            logger.info("恢复孤儿任务 %s（无 checkpoint，重新启动）", t.id)
            start_workflow(t.id, t.thread_id, t.direction)
