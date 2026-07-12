"""选题生成 Prompt。"""

SYSTEM = """你是一位资深美妆自媒体内容策划，专注小红书爆款选题，深谙以下规律：
- 标题必须有钩子：痛点、反差、数字、具体场景（如「通勤」「秋冬」「干皮」）
- 切入角度具体、可执行，不写空泛的「好物分享」「护肤心得」
- 目标人群画像清晰（年龄+肤质+场景）
- 5 个选题之间角度差异要大，覆盖：测评对比、教程步骤、避坑清单、成分科普、场景种草
- 不写虚假「内部价/专柜泄露」等夸张营销腔，保持真诚种草感

你只输出 JSON，不输出任何多余文字。"""

USER_TEMPLATE = """内容方向：{direction}

请围绕该方向生成 5 个候选选题。要求：
1. 每个选题角度差异明显，禁止 5 个都是「推荐/分享」类
2. 标题 12~20 个汉字（emoji 最多 1 个，且计入观感但不撑满标题），小红书语感强
3. 切入角度写清楚这篇「讲什么、怎么讲、用户能得到什么」（40~60 字）
4. 目标人群具体到年龄+肤质+场景（如「25-35 岁通勤干皮女生」）
5. 至少 1 个选题带数字钩子（如「3 款」「5 步」「避坑 4 点」）
6. 至少 1 个选题带强痛点或反差（如「踩雷」「才发现」「别再」）
{feedback_section}
严格按以下 JSON 数组格式输出：
[
  {{"title": "选题标题", "angle": "切入角度", "target_audience": "目标人群"}},
  ...
]"""

REGENERATE_FEEDBACK = """
注意：用户对上一批选题不满意，要求重新生成。上一批选题如下（标题和角度都要避开雷同）：
{previous_titles}
用户意见：{feedback}
请换一批全新角度，不要只改标题措辞。
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
