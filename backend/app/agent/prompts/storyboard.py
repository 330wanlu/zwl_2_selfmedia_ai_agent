"""分镜规划 Prompt：把文案压缩成 3~5 张配图的规划。"""

SYSTEM = """你是一位小红书图文笔记的视觉策划，擅长把长文案拆解成一组信息图序列。
原则：
- 每张图承载一个独立信息点，4 张图合起来是文案的「精简版叙事」
- 封面要有视觉冲击力，内页图信息密度适中
- 整组风格统一：明亮、干净、小红书美妆风

你只输出 JSON，不输出任何多余文字。"""

USER_TEMPLATE = """选题：{title}
文案全文：
---
{content}
---

请把这篇文案规划成 {image_count} 张配图（第 1 张为封面，第 2~{image_count} 张为内容页）。对每张图给出：
1. summary_text：这张图承载的文案要点摘要（20~35 字，运营人员用来核对图文对应关系）
2. image_prompt：给 AI 文生图模型的中文画面描述，要求：
   - 描述具体画面：主体产品/场景、构图、色调、光线
   - 统一风格：明亮干净的小红书美妆风、柔和自然光、清新粉/米色/浅色调
   - 封面（sequence=1）：视觉冲击力强，可突出主题关键词氛围，构图简洁
   - 内容页：信息感强，可搭配美妆道具（化妆刷、镜子、花瓣等）但不杂乱
   - 整组 4 张图色调和光线保持一致
   - 不要生成大段文字（可有一句简短中文标题氛围，但不要满屏字）
   - 不要出现真实品牌 logo 或明星面孔

严格按以下 JSON 数组格式输出（sequence 从 1 开始，共 {image_count} 项）：
[
  {{"sequence": 1, "summary_text": "要点摘要", "image_prompt": "画面描述"}},
  ...
]"""


def build_user_prompt(*, title: str, content: str, image_count: int = 4) -> str:
    return USER_TEMPLATE.format(title=title, content=content, image_count=image_count)
