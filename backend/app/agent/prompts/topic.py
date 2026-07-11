"""选题生成 Prompt。"""

SYSTEM = """你是一位资深美妆自媒体内容策划，深谙小红书爆款选题的规律：
- 标题有钩子（痛点、反差、数字、场景）
- 切入角度具体、不空泛
- 目标人群清晰

你只输出 JSON，不输出任何多余文字。"""

USER_TEMPLATE = """内容方向：{direction}

请围绕该方向生成 5 个候选选题。要求：
1. 每个选题角度差异明显（如测评、教程、避坑、成分党、场景种草）
2. 标题不超过 20 个字，符合小红书语感
3. 切入角度写清楚这篇内容"讲什么、怎么讲"（50 字以内）
4. 目标人群具体（如"25-35 岁干皮上班族"）
{feedback_section}
严格按以下 JSON 数组格式输出：
[
  {{"title": "选题标题", "angle": "切入角度", "target_audience": "目标人群"}},
  ...
]"""

REGENERATE_FEEDBACK = """
注意：用户对上一批选题不满意，要求重新生成。上一批选题如下（请避免雷同）：
{previous_titles}
用户意见：{feedback}
"""


def build_user_prompt(
    direction: str,
    *,
    previous_titles: list[str] | None = None,
    feedback: str | None = None,
) -> str:
    feedback_section = ""
    if previous_titles:
        feedback_section = REGENERATE_FEEDBACK.format(
            previous_titles="\n".join(f"- {t}" for t in previous_titles),
            feedback=feedback or "无具体意见，换一批新角度",
        )
    return USER_TEMPLATE.format(direction=direction, feedback_section=feedback_section)
