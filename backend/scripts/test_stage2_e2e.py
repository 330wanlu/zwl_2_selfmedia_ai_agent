"""阶段 2 端到端：新真实方向跑完全流程 + Debug/导出/标记已发布 + Prompt 可读性抽检。

前置：后端已启动
用法: uv run python scripts/test_stage2_e2e.py [方向]
默认方向：敏感肌夏季防晒推荐
详细日志：scripts/out/test_stage2_e2e.log（UTF-8）
产出快照：scripts/out/stage2_prompt_review.json
"""

from __future__ import annotations

import json
import re
import sys
import time
import zipfile
from io import BytesIO
from pathlib import Path

import httpx

BASE = "http://127.0.0.1:8000"
OUT = Path(__file__).parent / "out"
OUT.mkdir(exist_ok=True)
LOG = OUT / "test_stage2_e2e.log"
REVIEW = OUT / "stage2_prompt_review.json"
DIRECTION = sys.argv[1] if len(sys.argv) > 1 else "敏感肌夏季防晒推荐"

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
        if predicate(detail):
            return detail
        time.sleep(4)
    raise TimeoutError(f"等待 {desc} 超时（{timeout}s）")


def quality_checks(topics: list, content: str, package: dict, storyboards_hint: str = "") -> dict:
    """Prompt 第一轮调优的可读性/结构抽检（启发式，不替代人工品鉴）。"""
    title = package.get("title") or ""
    body = package.get("body") or ""
    tags = package.get("tags") or []
    issues: list[str] = []
    notes: list[str] = []

    # 选题：角度差异（简单用标题前缀/关键词集合）
    titles = [t.get("title", "") for t in topics]
    if len(set(titles)) < len(titles):
        issues.append("选题标题存在完全重复")
    if len(topics) < 5:
        issues.append(f"候选选题不足 5 个：{len(topics)}")
    audiences = [t.get("target_audience") or "" for t in topics]
    if any(len(a) < 6 for a in audiences):
        issues.append("部分选题目标人群过于空泛")
    else:
        notes.append("选题均有目标人群字段")

    # 文案
    if not (400 <= len(content) <= 1200):
        issues.append(f"文案长度异常: {len(content)}")
    else:
        notes.append(f"文案长度合理: {len(content)}")
    if "?" not in content and "？" not in content:
        issues.append("文案缺少提问式互动")
    else:
        notes.append("文案含提问/互动")

    # 内容包
    if not (8 <= len(title) <= 24):
        issues.append(f"标题长度偏离预期(8~24): {len(title)} — {title}")
    else:
        notes.append(f"标题长度 OK: {len(title)}")
    if not (6 <= len(tags) <= 10):
        issues.append(f"标签数量偏离预期(6~10): {len(tags)}")
    else:
        notes.append(f"标签数量 OK: {len(tags)}")
    if not body or len(body) < 300:
        issues.append("正文过短")
    emoji = re.findall(
        r"[\U0001F300-\U0001F9FF\u2600-\u27BF\U0001FA00-\U0001FAFF]",
        body + title,
    )
    if len(emoji) < 2:
        issues.append("标题/正文 emoji 偏少（可能调性不够小红书）")
    else:
        notes.append(f"emoji 数量约 {len(emoji)}")

    readable = len(issues) == 0
    return {
        "readable": readable,
        "issues": issues,
        "notes": notes,
        "sample": {
            "direction": DIRECTION,
            "topic_titles": titles,
            "content_len": len(content),
            "package_title": title,
            "package_tags": tags,
            "body_preview": body[:280],
            "storyboards_hint": storyboards_hint,
        },
    }


def main():
    client = httpx.Client(timeout=60)
    review: dict = {"direction": DIRECTION}

    log(f"== Stage2 E2E direction={DIRECTION} ==")

    # 1) 创建任务
    r = client.post(f"{BASE}/api/v1/tasks", json={"direction": DIRECTION})
    assert r.status_code == 201, r.text
    task_id = r.json()["id"]
    review["task_id"] = task_id
    log(f"task created: {task_id}")

    # 2) 选题
    detail = wait_for(
        client,
        task_id,
        lambda d: d["current_stage"] == "waiting_topic_selection" and not d["running"],
        "waiting_topic_selection",
        timeout=300,
    )
    topics = detail["pending_decision"]["topics"]
    assert len(topics) >= 3, dump(detail)
    log(f"topics: {len(topics)}")
    log(dump(topics), "(topics -> log)")

    r = client.post(
        f"{BASE}/api/v1/tasks/{task_id}/decisions/topic",
        json={"action": "select", "topic_id": topics[0]["id"]},
    )
    assert r.status_code == 202, r.text
    log("topic selected")

    # 3) 文案：驳回一轮再通过（验证循环 + 口语化调优）
    detail = wait_for(
        client,
        task_id,
        lambda d: d["current_stage"] == "waiting_content_review" and not d["running"],
        "waiting_content_review v1",
        timeout=300,
    )
    v1 = detail["pending_decision"]["content"]
    log(f"content v1 len={len(v1)}")
    log(v1, "(content v1 -> log)")

    feedback = "再口语一点，多一点敏感肌真实痛点共鸣，结尾提问更具体"
    r = client.post(
        f"{BASE}/api/v1/tasks/{task_id}/decisions/content",
        json={"approved": False, "feedback": feedback},
    )
    assert r.status_code == 202, r.text

    detail = wait_for(
        client,
        task_id,
        lambda d: d["current_stage"] == "waiting_content_review" and not d["running"],
        "waiting_content_review v2",
        timeout=300,
    )
    pending = detail["pending_decision"]
    assert pending["version"] == 2
    assert feedback in pending.get("feedback_history", [])
    v2 = pending["content"]
    assert v2 != v1
    log(f"content v2 len={len(v2)}")
    log(v2, "(content v2 -> log)")

    r = client.post(
        f"{BASE}/api/v1/tasks/{task_id}/decisions/content",
        json={"approved": True},
    )
    assert r.status_code == 202, r.text
    log("content approved")

    # 4) 出图后直接通过（本轮不重绘，节省额度；流程连通性阶段1已验）
    detail = wait_for(
        client,
        task_id,
        lambda d: d["current_stage"] == "waiting_image_review" and not d["running"],
        "waiting_image_review",
        timeout=600,
    )
    images = detail["pending_decision"]["images"]
    assert len(images) >= 3, dump(detail)
    log(f"images: {len(images)}")
    log(dump(images), "(images -> log)")

    r = client.post(
        f"{BASE}/api/v1/tasks/{task_id}/decisions/images",
        json={"approved": True},
    )
    assert r.status_code == 202, r.text

    detail = wait_for(
        client,
        task_id,
        lambda d: d["status"] == "completed",
        "completed",
        timeout=300,
    )
    log("task completed")

    # 5) 内容包
    r = client.get(f"{BASE}/api/v1/tasks/{task_id}/platform-contents")
    assert r.status_code == 200, r.text
    package = r.json()["content_package"]
    assert package.get("title") and package.get("body") and package.get("tags")
    log(
        f"package title_len={len(package['title'])} body_len={len(package['body'])} "
        f"tags={len(package['tags'])} images={len(package.get('images') or [])}"
    )
    log(dump(package), "(package -> log)")

    # 6) 阶段 2 Debug / 导出 / 标记
    r = client.get(f"{BASE}/api/debug/tasks/{task_id}/state")
    assert r.status_code == 200, r.text
    state = r.json()["state"]
    assert state.get("xhs_package") or state.get("content")
    log(f"debug state OK, keys={list(state.keys())}")

    r = client.get(f"{BASE}/api/debug/tasks/{task_id}/history")
    assert r.status_code == 200, r.text
    hist = r.json()
    assert hist["count"] > 0
    log(f"debug history OK, count={hist['count']}")

    r = client.get(f"{BASE}/api/debug/tasks/{task_id}/llm-calls")
    assert r.status_code == 200, r.text
    calls = r.json()
    assert calls["count"] > 0
    for c in calls["calls"]:
        assert c["prompt"]
        assert c["response"] or c["error"]
        assert c["node"]
    # 工作流节点调用应带 task_id 关联（debug 端点按 task_id 过滤已通过）
    nodes = [c["node"] for c in calls["calls"]]
    log(f"debug llm-calls OK, count={calls['count']}, nodes={nodes}")

    r = client.get(f"{BASE}/api/v1/tasks/{task_id}/export")
    assert r.status_code == 200, r.text
    export_data = r.json()
    assert export_data["content_package"]["title"]
    export_path = OUT / f"export_{task_id}.json"
    export_path.write_bytes(r.content)
    log(f"export JSON OK -> {export_path.name}")

    r = client.get(f"{BASE}/api/v1/tasks/{task_id}/export/images.zip")
    assert r.status_code == 200, r.text
    zip_path = OUT / f"images_{task_id}.zip"
    zip_path.write_bytes(r.content)
    with zipfile.ZipFile(BytesIO(r.content)) as zf:
        names = zf.namelist()
    assert len(names) >= 3
    log(f"export zip OK, files={names}")

    r = client.post(f"{BASE}/api/v1/tasks/{task_id}/publish/mark")
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "published"
    log("mark published OK")

    # 7) Prompt 可读性抽检
    q = quality_checks(topics, v2, package)
    review["quality"] = q
    review["llm_call_count"] = calls["count"]
    review["llm_nodes"] = nodes
    REVIEW.write_text(dump(review), encoding="utf-8")
    log(dump(q), "(quality review -> log)")
    if not q["readable"]:
        raise AssertionError(f"Prompt 可读性抽检未通过: {q['issues']}")
    log("prompt quality heuristic PASSED")

    log(f"== Stage2 E2E ALL PASSED, task_id={task_id} ==")
    (OUT / "stage2_task_id.txt").write_text(task_id, encoding="utf-8")


if __name__ == "__main__":
    try:
        main()
    finally:
        LOG.write_text("\n".join(log_lines), encoding="utf-8")
        print(f"log written to {LOG}")
        print(f"review written to {REVIEW}")
