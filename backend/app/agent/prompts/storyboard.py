"""分镜规划 Prompt：把文案压缩成 3~5 张配图的规划。"""

SYSTEM = """你是一位小红书图文笔记的视觉策划，擅长把长文案拆解成一组信息图。
你只输出 JSON，不输出任何多余文字。"""

USER_TEMPLATE = """选题：{title}
文案全文：
---
{content}
---

请把这篇文案规划成 {image_count} 张配图（第 1 张为封面）。对每张图给出：
1. summary_text：这张图承载的文案要点摘要（30 字以内，将展示给运营人员看）
2. image_prompt：给 AI 文生图模型的中文画面描述，要求：
   - 描述具体画面：主体、构图、色调、光线、风格
   - 统一风格：明亮干净的小红书美妆风、柔和自然光、清新色调
   - 封面图要有视觉冲击力，突出主题
   - 不要在画面中生成大段文字（可以有简短中文标题点缀）
   - 不要出现真实品牌 logo

严格按以下 JSON 数组格式输出（sequence 从 1 开始）：
[
  {{"sequence": 1, "summary_text": "要点摘要", "image_prompt": "画面描述"}},
  ...
]"""


def build_user_prompt(*, title: str, content: str, image_count: int = 4) -> str:
    return USER_TEMPLATE.format(title=title, content=content, image_count=image_count)
