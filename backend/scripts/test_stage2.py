"""阶段 2 自测：Debug 端点、内容包导出、标记已发布。

前置：存在一个已 completed 的任务（阶段 1 全流程跑完）。
用法:
  uv run python scripts/test_stage2.py                    # 自动找最近 completed 任务
  uv run python scripts/test_stage2.py <task_id>          # 指定任务
详细日志写入 scripts/out/test_stage2.log（UTF-8）。
"""

import json
import sys
import zipfile
from io import BytesIO
from pathlib import Path

import httpx
import psycopg

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings

BASE = "http://127.0.0.1:8000"
OUT = Path(__file__).parent / "out"
OUT.mkdir(exist_ok=True)
LOG = OUT / "test_stage2.log"
log_lines: list[str] = []


def log(msg: str, echo_ascii: str | None = None):
    log_lines.append(msg)
    print(echo_ascii if echo_ascii is not None else msg.encode("ascii", "replace").decode())


def dump(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2, default=str)


def find_completed_task_id() -> str:
    conninfo = settings.sync_database_url.replace("postgresql+psycopg://", "postgresql://")
    with psycopg.connect(conninfo, connect_timeout=5) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM tasks WHERE status='completed' ORDER BY updated_at DESC LIMIT 1"
            )
            row = cur.fetchone()
    if not row:
        raise RuntimeError("没有 completed 任务，请先跑完阶段 1 全流程")
    return str(row[0])


def main():
    client = httpx.Client(timeout=60)
    task_id = sys.argv[1] if len(sys.argv) > 1 else find_completed_task_id()
    log(f"== Stage 2 test, task_id={task_id} ==")

    # health
    r = client.get(f"{BASE}/health")
    assert r.status_code == 200, r.text
    log("health OK")

    # debug state
    r = client.get(f"{BASE}/api/debug/tasks/{task_id}/state")
    assert r.status_code == 200, r.text
    state = r.json()
    assert "state" in state
    log(f"debug state OK, keys={list(state.get('state', {}).keys())}")

    # debug history
    r = client.get(f"{BASE}/api/debug/tasks/{task_id}/history")
    assert r.status_code == 200, r.text
    history = r.json()
    assert history["count"] > 0, "checkpoint history should not be empty"
    log(f"debug history OK, count={history['count']}")
    log(dump(history["history"][:3]), "(history sample -> log)")

    # debug llm-calls
    r = client.get(f"{BASE}/api/debug/tasks/{task_id}/llm-calls")
    assert r.status_code == 200, r.text
    calls = r.json()
    assert calls["count"] > 0, "llm_call_logs should have records"
    for c in calls["calls"]:
        assert c["prompt"], "each log should have prompt"
        assert c["response"] or c["error"], "each log should have response or error"
    log(f"debug llm-calls OK, count={calls['count']}, nodes={[c['node'] for c in calls['calls']]}")

    # platform contents (existing API)
    r = client.get(f"{BASE}/api/v1/tasks/{task_id}/platform-contents")
    assert r.status_code == 200, r.text
    pkg = r.json()
    assert pkg["content_package"].get("title")
    assert pkg["content_package"].get("body")
    log(f"platform-contents OK, title_len={len(pkg['content_package']['title'])}")

    # export JSON
    r = client.get(f"{BASE}/api/v1/tasks/{task_id}/export")
    assert r.status_code == 200, r.text
    assert "attachment" in r.headers.get("content-disposition", "")
    export_data = r.json()
    assert export_data["task_id"] == task_id
    assert export_data["content_package"]["title"]
    assert len(export_data["images_detail"]) >= 1
    export_path = OUT / f"export_{task_id}.json"
    export_path.write_bytes(r.content)
    log(f"export JSON OK, saved {export_path.name}, images={len(export_data['images_detail'])}")

    # export images zip
    r = client.get(f"{BASE}/api/v1/tasks/{task_id}/export/images.zip")
    assert r.status_code == 200, r.text
    assert r.headers.get("content-type", "").startswith("application/zip")
    zip_path = OUT / f"images_{task_id}.zip"
    zip_path.write_bytes(r.content)
    with zipfile.ZipFile(BytesIO(r.content)) as zf:
        names = zf.namelist()
    assert len(names) >= 1
    log(f"export zip OK, saved {zip_path.name}, files={len(names)}")
    log(dump(names), "(zip entries -> log)")

    # mark published
    r = client.post(f"{BASE}/api/v1/tasks/{task_id}/publish/mark")
    assert r.status_code == 200, r.text
    marked = r.json()
    assert marked["status"] == "published"
    assert marked["published_at"] is not None
    log(f"mark published OK, at={marked['published_at']}")

    # idempotent mark
    r2 = client.post(f"{BASE}/api/v1/tasks/{task_id}/publish/mark")
    assert r2.status_code == 200
    assert r2.json()["status"] == "published"
    log("mark published idempotent OK")

    log("== Stage 2 ALL PASSED ==")
    LOG.write_text("\n".join(log_lines), encoding="utf-8")
    print(f"detail log -> {LOG}")


if __name__ == "__main__":
    main()
