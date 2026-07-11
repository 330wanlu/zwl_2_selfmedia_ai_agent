"""文案生成 Prompt。"""

SYSTEM = """你是一位小红书头部美妆博主的御用文案，写作特点：
- 口语化、有网感，像闺蜜聊天
- 善用 emoji 增强情绪，但不堆砌
- 结构清晰：开头钩子 → 干货主体 → 结尾互动引导
- 真实感强，不写夸张广告腔

直接输出文案正文，不要输出标题、标签或任何解释。"""

USER_TEMPLATE = """选题：{title}
切入角度：{angle}
目标人群：{target_audience}
内容方向：{direction}

请写一篇 500~800 字的小红书图文笔记正文。要求：
1. 开头 2 行内抓住注意力
2. 主体分 3~5 个小段落，每段一个重点，可以用小标题或 emoji 分隔
3. 结尾引导互动（提问/求评论）
4. 全文口语化，适度用 emoji"""

REVISE_TEMPLATE = """选题：{title}
切入角度：{angle}
目标人群：{target_audience}

这是当前版本的文案：
---
{current_content}
---

用户的修改意见（按时间顺序，越靠后越新，最新一条最重要）：
{feedback_list}

请根据全部修改意见重写这篇文案，保持小红书图文笔记风格，500~800 字。
直接输出重写后的正文，不要解释改了什么。"""


def build_user_prompt(
    *,
    title: str,
    angle: str,
    target_audience: str,
    direction: str,
    current_content: str | None = None,
    feedbacks: list[str] | None = None,
) -> str:
    if current_content and feedbacks:
        feedback_list = "\n".join(f"{i + 1}. {f}" for i, f in enumerate(feedbacks))
        return REVISE_TEMPLATE.format(
            title=title,
            angle=angle,
            target_audience=target_audience,
            current_content=current_content,
            feedback_list=feedback_list,
        )
    return USER_TEMPLATE.format(
        title=title, angle=angle, target_audience=target_audience, direction=direction
    )
