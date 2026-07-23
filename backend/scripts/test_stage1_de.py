"""阶段 1 自测：里程碑 D（图片审核 + 单张重绘）+ 里程碑 E（小红书内容包）。

前置：任务已通过文案审核，正在出图或已挂在 waiting_image_review。
用法: uv run python scripts/test_stage1_de.py <task_id>
详细日志写入 scripts/out/test_de.log（UTF-8）。
"""

import json
import sys
import time
from pathlib import Path

import httpx

BASE = "http://127.0.0.1:8001"
OUT = Path(__file__).parent / "out"
OUT.mkdir(exist_ok=True)
LOG = OUT / "test_de.log"
log_lines: list[str] = []


def log(msg: str, echo_ascii: str | None = None):
    log_lines.append(msg)
    print(echo_ascii if echo_ascii is not None else msg.encode("ascii", "replace").decode())


def dump(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2, default=str)


def wait_for(client, task_id, predicate, desc, timeout=600):
    start = time.time()
    while time.time() - start < timeout:
        r = client.get(f"{BASE}/api/v1/tasks/{task_id}")
        r.raise_for_status()
        detail = r.json()
        if detail["status"] == "failed":
            raise RuntimeError(f"任务失败: {dump(detail)}")
        if predicate(detail):
            return detail
        time.sleep(5)
    raise TimeoutError(f"等待 {desc} 超时（{timeout}s）")


def main():
    client = httpx.Client(timeout=30)
    task_id = sys.argv[1]

    # ---------- 里程碑 D：等待出图完成 → 单张重绘 → 通过 ----------
    log("== Milestone D: image review ==", "== Milestone D: image review ==")
    detail = wait_for(
        client, task_id,
        lambda d: d["current_stage"] == "waiting_image_review" and not d["running"],
        "waiting_image_review",
    )
    pending = detail["pending_decision"]
    assert pending["type"] == "image_review", dump(detail)
    images_before = {img["sequence"]: img for img in pending["images"]}
    log(f"images generated: {len(images_before)}")
    log(dump(pending["images"]), "(images detail -> log file)")

    # 重绘第 2 张
    r = client.post(
        f"{BASE}/api/v1/tasks/{task_id}/decisions/images",
        json={"approved": False, "redraw": [{"sequence": 2, "hint": "背景换成粉色，整体更明亮"}]},
    )
    assert r.status_code == 202, r.text
    log("redraw seq=2 submitted", "redraw seq=2 submitted")

    detail = wait_for(
        client, task_id,
        lambda d: d["current_stage"] == "waiting_image_review" and not d["running"],
        "waiting_image_review after redraw",
    )
    images_after = {img["sequence"]: img for img in detail["pending_decision"]["images"]}
    assert images_after[2]["file_path"] != images_before[2]["file_path"], "第2张应已重绘"
    assert images_after[2]["retry_count"] == 1
    for seq in images_before:
        if seq != 2:
            assert images_after[seq]["file_path"] == images_before[seq]["file_path"], \
                f"第{seq}张不应变化"
    log("redraw check OK: only seq=2 changed, others kept",
        "redraw check OK: only seq=2 changed, others kept")

    # 全部通过
    r = client.post(
        f"{BASE}/api/v1/tasks/{task_id}/decisions/images", json={"approved": True}
    )
    assert r.status_code == 202, r.text
    log("images approved -> platform adapter", "images approved -> platform adapter")

    # ---------- 里程碑 E：小红书内容包 ----------
    log("== Milestone E: xhs package ==", "== Milestone E: xhs package ==")
    detail = wait_for(
        client, task_id, lambda d: d["status"] == "completed", "task completed", timeout=300
    )
    log(f"task completed, stage={detail['current_stage']}")

    r = client.get(f"{BASE}/api/v1/tasks/{task_id}/platform-contents")
    assert r.status_code == 200, r.text
    pkg = r.json()["content_package"]
    assert pkg.get("title") and pkg.get("body") and pkg.get("tags"), dump(pkg)
    assert len(pkg["images"]) == len(images_after), dump(pkg["images"])
    log(f"package: title_len={len(pkg['title'])}, body_len={len(pkg['body'])}, "
        f"tags={len(pkg['tags'])}, images={len(pkg['images'])}")
    log(dump(pkg), "(package detail -> log file)")

    r = client.get(f"{BASE}/api/v1/tasks/{task_id}/images")
    imgs = r.json()
    assert all(i["status"] == "approved" for i in imgs), dump(imgs)
    log(f"images endpoint OK: {len(imgs)} approved")
    log(dump(imgs), "(images endpoint -> log file)")

    # 校验图片文件真实存在
    image_dir = Path(__file__).parent.parent / "data" / "images"
    for i in imgs:
        f = image_dir / i["file_path"]
        assert f.exists() and f.stat().st_size > 10000, f"图片文件异常: {f}"
    log("all image files exist on disk", "all image files exist on disk")

    log(f"MILESTONE D+E PASSED, task_id={task_id}")


if __name__ == "__main__":
    try:
        main()
    finally:
        LOG.write_text("\n".join(log_lines), encoding="utf-8")
        print(f"log written to {LOG}")
