"""阶段 4 自测：真实内容品鉴 + 边界 + Prompt 调优后全流程。

前置：后端已启动
用法:
  uv run python scripts/test_stage4.py                  # 全部（耗时长，含 LLM）
  uv run python scripts/test_stage4.py review           # 只品鉴已完成内容包
  uv run python scripts/test_stage4.py cancel           # 任务取消
  uv run python scripts/test_stage4.py concurrent       # 并发两任务
  uv run python scripts/test_stage4.py revise5          # 文案改 5 轮
  uv run python scripts/test_stage4.py redraw3          # 单张重绘 3 次
  uv run python scripts/test_stage4.py e2e              # 新方向全流程（调优后 Prompt）

日志：scripts/out/test_stage4.log / stage4_review.json
"""

from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

import httpx

BASE = "http://127.0.0.1:8001"
OUT = Path(__file__).parent / "out"
OUT.mkdir(exist_ok=True)
LOG = OUT / "test_stage4.log"
REVIEW = OUT / "stage4_review.json"

log_lines: list[str] = []


def log(msg: str, echo_ascii: str | None = None):
    log_lines.append(msg)
    print(echo_ascii if echo_ascii is not None else msg.encode("ascii", "replace").decode())


def dump(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2, default=str)


def wait_for(client: httpx.Client, task_id: str, predicate, desc: str, timeout: int = 600) -> dict:
    start = time.time()
    while time.time() - start < timeout:
        r = client.get(f"{BASE}/api/v1/tasks/{task_id}")
        r.raise_for_status()
        detail = r.json()
        if detail["status"] == "failed":
            raise RuntimeError(f"任务失败: {dump(detail)}")
        if detail["status"] == "cancelled":
            if predicate(detail):
                return detail
            raise RuntimeError(f"任务已取消，无法等待 {desc}")
        if predicate(detail):
            return detail
        time.sleep(4)
    raise TimeoutError(f"等待 {desc} 超时（{timeout}s）")


def char_len(s: str) -> int:
    """近似「展示长度」：去掉 emoji 后按字符计。"""
    no_emoji = re.sub(
        r"[\U0001F300-\U0001F9FF\u2600-\u27BF\U0001FA00-\U0001FAFF]",
        "",
        s or "",
    )
    return len(no_emoji.replace(" ", ""))


def review_package(pkg: dict, direction: str) -> dict:
    title = pkg.get("title") or ""
    body = pkg.get("body") or ""
    tags = pkg.get("tags") or []
    images = pkg.get("images") or []
    issues: list[str] = []
    notes: list[str] = []

    tl = char_len(title)
    if tl > 22:
        issues.append(f"标题偏长({tl}): {title}")
    elif tl < 8:
        issues.append(f"标题偏短({tl}): {title}")
    else:
        notes.append(f"标题长度 OK ({tl})")

    if not (400 <= len(body) <= 1500):
        issues.append(f"正文字数异常: {len(body)}")
    else:
        notes.append(f"正文长度 OK ({len(body)})")

    if "?" not in body and "？" not in body:
        issues.append("正文缺少互动提问")
    else:
        notes.append("含互动提问")

    if not (5 <= len(tags) <= 10):
        issues.append(f"标签数量异常: {len(tags)}")
    else:
        notes.append(f"标签 {len(tags)} 个")

    if len(images) < 3:
        issues.append(f"图片过少: {len(images)}")
    else:
        notes.append(f"图片 {len(images)} 张")

    # 可发水准：无硬伤即可（阶段4人工品鉴口径）
    publishable = len(issues) == 0
    return {
        "direction": direction,
        "publishable": publishable,
        "issues": issues,
        "notes": notes,
        "title": title,
        "tags": tags,
        "body_preview": body[:200],
    }


def cmd_review(client: httpx.Client) -> dict:
    log("== review completed packages ==")
    tasks = client.get(f"{BASE}/api/v1/tasks").json()
    completed = [t for t in tasks if t["status"] == "completed"]
    results = []
    for t in completed:
        r = client.get(f"{BASE}/api/v1/tasks/{t['id']}/platform-contents")
        if r.status_code != 200:
            continue
        pkg = r.json()["content_package"]
        item = review_package(pkg, t["direction"])
        item["task_id"] = t["id"]
        results.append(item)
        log(
            f"task={t['id']} publishable={item['publishable']} issues={item['issues']}",
            f"review {t['id'][:8]} publishable={item['publishable']}",
        )
    publishable_n = sum(1 for x in results if x["publishable"])
    summary = {
        "completed_count": len(results),
        "publishable_count": publishable_n,
        "items": results,
    }
    REVIEW.write_text(dump(summary), encoding="utf-8")
    log(f"publishable {publishable_n}/{len(results)}")
    assert publishable_n >= 3, f"可发内容不足 3 篇: {publishable_n}"
    return summary


def cmd_cancel(client: httpx.Client):
    log("== cancel task ==")
    r = client.post(f"{BASE}/api/v1/tasks", json={"direction": "阶段4取消测试-控油喷雾"})
    assert r.status_code == 201, r.text
    task_id = r.json()["id"]
    log(f"created {task_id}")

    detail = wait_for(
        client,
        task_id,
        lambda d: d["current_stage"] == "waiting_topic_selection" and not d["running"],
        "waiting_topic_selection",
        timeout=300,
    )
    topics = detail["pending_decision"]["topics"]
    assert topics

    r = client.post(f"{BASE}/api/v1/tasks/{task_id}/cancel")
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "cancelled"
    log("cancel OK")

    # 再决策应 409
    r = client.post(
        f"{BASE}/api/v1/tasks/{task_id}/decisions/topic",
        json={"action": "select", "topic_id": topics[0]["id"]},
    )
    assert r.status_code == 409, r.text
    log("decision after cancel correctly rejected")

    # 幂等：再取消应 409
    r = client.post(f"{BASE}/api/v1/tasks/{task_id}/cancel")
    assert r.status_code == 409
    log("double cancel correctly rejected")


def cmd_concurrent(client: httpx.Client):
    log("== concurrent two tasks ==")
    r1 = client.post(f"{BASE}/api/v1/tasks", json={"direction": "阶段4并发A-水光唇釉"})
    r2 = client.post(f"{BASE}/api/v1/tasks", json={"direction": "阶段4并发B-哑光唇泥"})
    assert r1.status_code == 201 and r2.status_code == 201
    id1, id2 = r1.json()["id"], r2.json()["id"]
    log(f"created {id1} & {id2}")

    d1 = wait_for(
        client,
        id1,
        lambda d: d["current_stage"] == "waiting_topic_selection" and not d["running"],
        "task1 topic",
        timeout=360,
    )
    d2 = wait_for(
        client,
        id2,
        lambda d: d["current_stage"] == "waiting_topic_selection" and not d["running"],
        "task2 topic",
        timeout=360,
    )
    assert len(d1["pending_decision"]["topics"]) >= 3
    assert len(d2["pending_decision"]["topics"]) >= 3
    log("both reached topic selection concurrently OK")

    # 清理：取消，避免堆积
    client.post(f"{BASE}/api/v1/tasks/{id1}/cancel")
    client.post(f"{BASE}/api/v1/tasks/{id2}/cancel")
    log("cancelled both concurrent tasks")


def cmd_revise5(client: httpx.Client):
    log("== content revise 5 rounds ==")
    r = client.post(f"{BASE}/api/v1/tasks", json={"direction": "阶段4边界-敏感肌卸妆"})
    assert r.status_code == 201
    task_id = r.json()["id"]
    log(f"created {task_id}")

    detail = wait_for(
        client,
        task_id,
        lambda d: d["current_stage"] == "waiting_topic_selection" and not d["running"],
        "topic",
    )
    topic_id = detail["pending_decision"]["topics"][0]["id"]
    assert client.post(
        f"{BASE}/api/v1/tasks/{task_id}/decisions/topic",
        json={"action": "select", "topic_id": topic_id},
    ).status_code == 202

    feedbacks = [
        "开头改成提问式",
        "再口语一点",
        "多加 emoji",
        "补充一个具体使用场景",
        "结尾互动问得更具体一点",
    ]
    for i, fb in enumerate(feedbacks, start=1):
        detail = wait_for(
            client,
            task_id,
            lambda d: d["current_stage"] == "waiting_content_review" and not d["running"],
            f"content v{i}",
            timeout=300,
        )
        pending = detail["pending_decision"]
        assert pending["version"] == i, dump(pending)
        log(f"content v{i} len={len(pending['content'])}")
        assert (
            client.post(
                f"{BASE}/api/v1/tasks/{task_id}/decisions/content",
                json={"approved": False, "feedback": fb},
            ).status_code
            == 202
        )

    detail = wait_for(
        client,
        task_id,
        lambda d: d["current_stage"] == "waiting_content_review" and not d["running"],
        "content v6",
        timeout=300,
    )
    pending = detail["pending_decision"]
    assert pending["version"] == 6, dump(pending)
    assert pending["feedback_history"] == feedbacks, dump(pending["feedback_history"])
    log("revise5 + history OK, cancelling to save image cost")
    client.post(f"{BASE}/api/v1/tasks/{task_id}/cancel")


def cmd_redraw3(client: httpx.Client):
    log("== image redraw 3 times ==")
    r = client.post(f"{BASE}/api/v1/tasks", json={"direction": "阶段4边界-平价腮红推荐"})
    assert r.status_code == 201
    task_id = r.json()["id"]
    log(f"created {task_id}")

    detail = wait_for(
        client,
        task_id,
        lambda d: d["current_stage"] == "waiting_topic_selection" and not d["running"],
        "topic",
    )
    assert (
        client.post(
            f"{BASE}/api/v1/tasks/{task_id}/decisions/topic",
            json={"action": "select", "topic_id": detail["pending_decision"]["topics"][0]["id"]},
        ).status_code
        == 202
    )

    detail = wait_for(
        client,
        task_id,
        lambda d: d["current_stage"] == "waiting_content_review" and not d["running"],
        "content",
    )
    assert (
        client.post(
            f"{BASE}/api/v1/tasks/{task_id}/decisions/content",
            json={"approved": True},
        ).status_code
        == 202
    )

    detail = wait_for(
        client,
        task_id,
        lambda d: d["current_stage"] == "waiting_image_review" and not d["running"],
        "images",
        timeout=600,
    )
    images = {img["sequence"]: img for img in detail["pending_decision"]["images"]}
    seq = 2
    path_before = images[seq]["file_path"]

    for i in range(1, 4):
        assert (
            client.post(
                f"{BASE}/api/v1/tasks/{task_id}/decisions/images",
                json={
                    "approved": False,
                    "redraw": [{"sequence": seq, "hint": f"第{i}次重绘：整体更明亮"}],
                },
            ).status_code
            == 202
        )
        detail = wait_for(
            client,
            task_id,
            lambda d: d["current_stage"] == "waiting_image_review" and not d["running"],
            f"redraw {i}",
            timeout=360,
        )
        imgs = {img["sequence"]: img for img in detail["pending_decision"]["images"]}
        assert imgs[seq]["retry_count"] == i, dump(imgs[seq])
        assert imgs[seq]["file_path"] != path_before
        path_before = imgs[seq]["file_path"]
        # 其他图不变
        for s, old in images.items():
            if s != seq:
                assert imgs[s]["file_path"] == old["file_path"]
        log(f"redraw round {i} OK, retry_count={i}")

    assert (
        client.post(
            f"{BASE}/api/v1/tasks/{task_id}/decisions/images",
            json={"approved": True},
        ).status_code
        == 202
    )
    detail = wait_for(
        client, task_id, lambda d: d["status"] == "completed", "completed", timeout=300
    )
    log(f"redraw3 completed task={task_id}")
    return task_id


def cmd_e2e(client: httpx.Client, direction: str = "油皮夏季控油底妆"):
    log(f"== e2e after prompt tune, direction={direction} ==")
    t0 = time.time()
    r = client.post(f"{BASE}/api/v1/tasks", json={"direction": direction})
    assert r.status_code == 201
    task_id = r.json()["id"]
    log(f"created {task_id}")

    detail = wait_for(
        client,
        task_id,
        lambda d: d["current_stage"] == "waiting_topic_selection" and not d["running"],
        "topic",
    )
    topics = detail["pending_decision"]["topics"]
    assert len(topics) >= 5
    # 痛点/数字钩子启发式
    titles = " ".join(t["title"] for t in topics)
    log(dump(topics), "(topics -> log)")

    assert (
        client.post(
            f"{BASE}/api/v1/tasks/{task_id}/decisions/topic",
            json={"action": "select", "topic_id": topics[0]["id"]},
        ).status_code
        == 202
    )

    detail = wait_for(
        client,
        task_id,
        lambda d: d["current_stage"] == "waiting_content_review" and not d["running"],
        "content",
    )
    assert (
        client.post(
            f"{BASE}/api/v1/tasks/{task_id}/decisions/content",
            json={"approved": True},
        ).status_code
        == 202
    )

    detail = wait_for(
        client,
        task_id,
        lambda d: d["current_stage"] == "waiting_image_review" and not d["running"],
        "images",
        timeout=600,
    )
    assert len(detail["pending_decision"]["images"]) >= 3
    assert (
        client.post(
            f"{BASE}/api/v1/tasks/{task_id}/decisions/images",
            json={"approved": True},
        ).status_code
        == 202
    )

    detail = wait_for(
        client, task_id, lambda d: d["status"] == "completed", "completed", timeout=300
    )
    elapsed = int(time.time() - t0)
    pkg = client.get(f"{BASE}/api/v1/tasks/{task_id}/platform-contents").json()[
        "content_package"
    ]
    q = review_package(pkg, direction)
    q["task_id"] = task_id
    q["elapsed_sec"] = elapsed
    q["topic_titles"] = [t["title"] for t in topics]
    log(dump(q), "(e2e quality -> log)")
    assert q["publishable"], q["issues"]
    log(f"e2e OK elapsed={elapsed}s task={task_id}")

    # 导出/标记冒烟
    assert client.get(f"{BASE}/api/v1/tasks/{task_id}/export").status_code == 200
    assert client.get(f"{BASE}/api/v1/tasks/{task_id}/export/images.zip").status_code == 200
    assert client.post(f"{BASE}/api/v1/tasks/{task_id}/publish/mark").status_code == 200
    return q


def main():
    client = httpx.Client(timeout=60)
    assert client.get(f"{BASE}/health").status_code == 200

    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    log(f"== Stage4 mode={mode} ==")

    if mode in ("review", "all"):
        cmd_review(client)
    if mode in ("cancel", "all"):
        cmd_cancel(client)
    if mode in ("concurrent", "all"):
        cmd_concurrent(client)
    if mode in ("revise5", "all"):
        cmd_revise5(client)
    if mode in ("redraw3", "all"):
        cmd_redraw3(client)
    if mode in ("e2e", "all"):
        cmd_e2e(client)

    log("== Stage4 ALL PASSED ==")


if __name__ == "__main__":
    try:
        main()
    finally:
        LOG.write_text("\n".join(log_lines), encoding="utf-8")
        print(f"log -> {LOG}")
