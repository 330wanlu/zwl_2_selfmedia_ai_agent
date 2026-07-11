"""从 LLM 回复中稳健地解析 JSON（容忍 ```json 代码块、前后废话）。"""

import json
from typing import Any


def parse_llm_json(text: str) -> Any:
    text = text.strip()
    # 去掉 markdown 代码块包裹
    if text.startswith("```"):
        first_newline = text.find("\n")
        if first_newline != -1:
            text = text[first_newline + 1 :]
        if text.rstrip().endswith("```"):
            text = text.rstrip()[:-3]
        text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 截取首个 JSON 数组或对象
    for open_ch, close_ch in (("[", "]"), ("{", "}")):
        start = text.find(open_ch)
        end = text.rfind(close_ch)
        if start != -1 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                continue

    raise ValueError(f"无法从 LLM 回复中解析 JSON：{text[:200]}")
