"""阶段 1 自测：里程碑 A（选题流程）+ 里程碑 B（文案审核循环）。

前置：后端已启动（uv run uvicorn app.main:app --reload --port 8001）
用法: uv run python scripts/test_stage1_ab.py
详细日志写入 scripts/out/test_ab.log（UTF-8），控制台只打 ASCII 摘要。
"""

import json
import sys
import time
from pathlib import Path

import httpx

BASE = "http://127.0.0.1:8001"
OUT = Path(__file__).parent / "out"
OUT.mkdir(exist_ok=True)
LOG = OUT / "test_ab.log"
log_lines: list[str] = []


def log(msg: str, echo_ascii: str | None = None):
    log_lines.append(msg)
    print(echo_ascii if echo_ascii is not None else msg.encode("ascii", "replace").decode())


def dump(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2, default=str)


def wait_for_stage(client: httpx.Client, task_id: str, stage: str, timeout: int = 300) -> dict:
    """轮询任务详情直到 current_stage 达到指定值且不在 running。"""
    start = time.time()
    while time.time() - start < timeout:
        r = client.get(f"{BASE}/api/v1/tasks/{task_id}")
        r.raise_for_status()
        detail = r.json()
        if detail["status"] == "failed":
            raise RuntimeError(f"任务失败: {dump(detail)}")
        if detail["current_stage"] == stage and not detail["running"]:
            return detail
        time.sleep(3)
    raise TimeoutError(f"等待 {stage} 超时（{timeout}s）")


def main():
    client = httpx.Client(timeout=30)

    # ---------- 里程碑 A：创建任务 → 生成选题 → 人工选题 ----------
    if len(sys.argv) > 1:
        task_id = sys.argv[1]
        log(f"reuse existing task: {task_id}")
    else:
        log("== Milestone A: create task ==", "== Milestone A: create task ==")
        r = client.post(f"{BASE}/api/v1/tasks", json={"direction": "秋冬干皮粉底液推荐"})
        assert r.status_code == 201, r.text
        task = r.json()
        task_id = task["id"]
        log(f"task created: {task_id}")

    detail = wait_for_stage(client, task_id, "waiting_topic_selection")
    pending = detail["pending_decision"]
    assert pending and pending["type"] == "topic_selection", dump(detail)
    topics = pending["topics"]
    assert len(topics) >= 3, f"候选选题数量异常: {len(topics)}"
    log(f"topics generated: {len(topics)}")
    log(dump(topics), f"(topics detail -> log file)")

    # 选第一个选题
    r = client.post(
        f"{BASE}/api/v1/tasks/{task_id}/decisions/topic",
        json={"action": "select", "topic_id": topics[0]["id"]},
    )
    assert r.status_code == 202, r.text
    log("topic selected -> resume", "topic selected -> resume")

    # ---------- 里程碑 B：文案生成 → 驳回一轮 → 通过 ----------
    log("== Milestone B: content review loop ==", "== Milestone B: content review loop ==")
    detail = wait_for_stage(client, task_id, "waiting_content_review")
    pending = detail["pending_decision"]
    assert pending["type"] == "content_review", dump(detail)
    assert pending["version"] == 1
    v1 = pending["content"]
    log(f"content v1 generated, len={len(v1)}")
    log(v1, "(content v1 -> log file)")

    # 驳回：提修改意见
    feedback = "语气太硬，要更口语化，多加 emoji，开头改成提问式钩子"
    r = client.post(
        f"{BASE}/api/v1/tasks/{task_id}/decisions/content",
        json={"approved": False, "feedback": feedback},
    )
    assert r.status_code == 202, r.text
    log("content v1 rejected with feedback", "content v1 rejected with feedback")

    detail = wait_for_stage(client, task_id, "waiting_content_review")
    pending = detail["pending_decision"]
    assert pending["version"] == 2, dump(pending)
    assert pending["feedback_history"] == [feedback], dump(pending)
    v2 = pending["content"]
    assert v2 != v1
    log(f"content v2 generated, len={len(v2)}, feedback history OK")
    log(v2, "(content v2 -> log file)")

    # 通过
    r = client.post(
        f"{BASE}/api/v1/tasks/{task_id}/decisions/content", json={"approved": True}
    )
    assert r.status_code == 202, r.text
    log("content v2 approved -> storyboard/images start",
        "content v2 approved -> storyboard/images start")

    log(f"MILESTONE A+B PASSED, task_id={task_id}")
    (OUT / "task_id.txt").write_text(task_id, encoding="utf-8")


if __name__ == "__main__":
    try:
        main()
    finally:
        LOG.write_text("\n".join(log_lines), encoding="utf-8")
        print(f"log written to {LOG}")
