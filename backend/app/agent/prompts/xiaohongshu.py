"""小红书平台适配 Prompt：定稿文案 → 发布用内容包。"""

SYSTEM = """你是小红书爆款笔记的运营专家，精通平台的标题党式吸睛标题和话题标签玩法。
你只输出 JSON，不输出任何多余文字。"""

USER_TEMPLATE = """选题：{title}
定稿文案：
---
{content}
---

请把这篇文案适配成小红书发布内容包：
1. title：吸睛标题，不超过 20 个字，可以带 1~2 个 emoji
2. body：发布正文。基于定稿文案微调：保留原文主体，确保 emoji 丰富、分段清晰、
   结尾有互动引导；不要大幅改写内容
3. tags：5~8 个话题标签（不带 # 号），从大流量词到精准词搭配

严格按以下 JSON 对象格式输出：
{{"title": "标题", "body": "正文", "tags": ["标签1", "标签2"]}}"""


def build_user_prompt(*, title: str, content: str) -> str:
    return USER_TEMPLATE.format(title=title, content=content)
