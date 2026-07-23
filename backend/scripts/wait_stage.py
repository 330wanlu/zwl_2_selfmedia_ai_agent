"""轮询等待任务到达指定阶段。用法: uv run python scripts/wait_stage.py <task_id> <stage> [timeout]"""

import json
import sys
import time

import httpx

task_id, stage = sys.argv[1], sys.argv[2]
timeout = int(sys.argv[3]) if len(sys.argv) > 3 else 600
BASE = "http://127.0.0.1:8001"

start = time.time()
while time.time() - start < timeout:
    d = httpx.get(f"{BASE}/api/v1/tasks/{task_id}", timeout=30).json()
    if d["status"] == "failed":
        print("TASK FAILED")
        print(json.dumps(d, ensure_ascii=False).encode("ascii", "replace").decode())
        sys.exit(2)
    if d["current_stage"] == stage and not d["running"]:
        print(f"REACHED {stage} in {int(time.time() - start)}s")
        sys.exit(0)
    print(f"... stage={d['current_stage']} running={d['running']}")
    time.sleep(5)
print("TIMEOUT")
sys.exit(1)
