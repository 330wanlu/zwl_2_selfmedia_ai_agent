# MVP 落地方案（修订版）

> 版本：v1.3　|　日期：2026-07-09　|　基于《项目方案设计.md》，针对问题答复与 MVP 裁剪
>
> 目标：**用最短路径跑通「方向 → 选题 → 人工选题 → 文案 → 人工审核循环 → 出图 → 人工确认 → 小红书内容包导出」全流程**，其余能力全部延后。
>
> v1.3 变更：**数据库改为本机原生 PostgreSQL（方案 A）**，不依赖 Docker。经环境检查：本机已安装 PostgreSQL 18 且服务正在运行，Docker 未安装。
>
> v1.2 变更：① 补充 PostgreSQL 后期迁移说明；② 明确文案/生图为两个模型两个 API；③ **发布平台改为小红书优先（内容包导出 + 人工发布），微信公众号直发延后**。

---

## 0. 问题答复与方案确认

### 0.1 数据库方案：本机原生 PostgreSQL（方案 A，已确认）

经环境检查，本机现状如下：


| 项目         | 状态                                |
| ---------- | --------------------------------- |
| Docker     | ❌ 未安装                             |
| PostgreSQL | ✅ 已安装，服务 `postgresql-x64-18` 正在运行 |
| 版本         | PostgreSQL 18                     |


**MVP 采用方案 A：直接连本机原生 PostgreSQL**，不安装 Docker，也不使用 `docker-compose`。

- 应用只认 `.env` 里的 `DATABASE_URL`，连 `localhost:5432` 即可。
- 为本项目单独建一个库 `media_agent`，与现有其他库互不干扰。
- 将来若要迁到服务器或云数据库，改 `DATABASE_URL` + `pg_dump`/`pg_restore` 即可，应用代码不用动。

### 0.2 文案和图片是两个模型、两个 API 吗？

是的，**两个不同的模型、两个不同的 API 接口，但同一个平台、同一个 API Key**：


| 用途                | 模型                           | 调用的 API                    | 接入方式                              |
| ----------------- | ---------------------------- | -------------------------- | --------------------------------- |
| 选题/文案/分镜/平台适配（文本） | `doubao-seed-1-8-251228`     | 对话接口 `/chat/completions`   | `langchain-openai` 的 `ChatOpenAI` |
| 文案 → 图片（文生图）      | `doubao-seedream-4-5-251128-251128` | 生图接口 `/images/generations` | 火山方舟 SDK 或 HTTP 直调                |


两者都走火山方舟平台（`https://ark.cn-beijing.volces.com/api/v3`），共用一个 `ARK_API_KEY`，只是模型名和接口路径不同，按各自模型单独计费。工作流里的分工：`topic_generator`、`content_writer`、`storyboard_planner`、`platform_adapter` 四个节点用文本模型；`image_generator` 节点用生图模型。

### 0.3 MVP 第一个发布平台改为小红书

确认调整：**MVP 不做微信公众号直发**，小红书作为第一个（也是唯一一个）发布平台，形态为：

- `platform_adapter` 节点只产出**小红书内容包**：吸睛标题（≤20 字）+ 正文（emoji + 话题标签）+ 3-5 张图片；
- 前端内容包页提供 **一键复制文字 + 批量下载图片**，运营人员打开小红书创作者中心粘贴发布，30 秒完成一篇；
- 公众号直发、抖音/快手适配，后续按需在 `publishers/` 和 `prompts/platform/` 各加一个文件即可，主流程零改动。

### 0.4 本机数据库初始化步骤（D1 前置）

在 pgAdmin 或 `psql` 中执行一次即可：

```sql
CREATE DATABASE media_agent;
```

`.env` 中配置连接串（密码替换为你安装 PostgreSQL 时设置的密码）：

```env
DATABASE_URL=postgresql+asyncpg://postgres:你的密码@localhost:5432/media_agent
```

确认服务已启动（Windows 服务管理器中 `postgresql-x64-18` 状态为 Running，或 PowerShell）：

```powershell
Get-Service postgresql-x64-18
```

本文档以下章节已按方案 A 更新（数据库方案、代码结构、开发顺序、环境变量）。

---

## 1. 平台发布接口现状（问题 1 答复）

结论先行：**四个平台里只有微信公众号能真正做到"服务端 API 直发"**，其余三个平台对普通企业开发者都没有开放服务端直发接口。已核实的现状（2026-07）：


| 平台        | 官方能力       | 现状说明                                                                                                                                                                                             | MVP 采用方案                            |
| --------- | ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ----------------------------------- |
| **微信公众号** | ✅ 完整发布 API | 官方接口链路成熟：新增草稿 → 发布/群发，图片走素材上传接口。需认证服务号/订阅号                                                                                                                                                       | 延后（二期接 API 直发，`publishers/` 加适配器即可） |
| **抖音**    | ⚠️ 仅"拉起发布" | ① 普通开发者可申请「发布内容至抖音」能力：App 通过 SDK、网页通过 **H5 扫码** 方式，把图文/视频传入抖音 App 的发布页，**由用户在抖音里手动点发布**，无法全自动。② 真正的服务端直发接口「代替用户发布内容到抖音」（`/api/douyin/v1/video/create_image_text/` 等）**只对党政机关/事业单位主体开放**，普通公司申请不了 | 内容包导出 + 人工发布；二期可接 H5 扫码投稿（半自动）      |
| **快手**    | ⚠️ 仅视频     | 开放平台有 `openapi/photo/publish` 发布接口，但**只支持视频**，且需申请 `USER_VIDEO_PUBLISH` 权限 + 用户 OAuth 授权。图文类内容无接口                                                                                                | 内容包导出 + 人工发布                        |
| **小红书**   | ❌ 无        | 没有对外开放的内容发布 API。仅有分享 JS SDK 可唤起 App 由用户确认发布。市面上宣称"API 发布小红书"的第三方工具，本质是 RPA 浏览器自动化（模拟人工操作创作者中心网页），**有封号风险**                                                                                       | **内容包导出 + 人工发布（MVP 首发平台）**          |


**MVP 的发布形态（v1.2 调整：小红书优先）**：

- **小红书（MVP 唯一平台）**：系统生成小红书适配好的**内容包页面**（标题、正文、话题标签、图片组），提供"一键复制文字 + 批量下载图片"，运营人员打开小红书创作者中心粘贴发布，30 秒完成一篇。
- 公众号 API 直发、抖音/快手内容包：延后，需要时在 `publishers/` 加适配器即可。
- 二期再评估：抖音 H5 扫码投稿（官方合规、半自动）、RPA 自动化（如 Playwright 操作网页版创作者中心，需自担风控风险）。

架构上不受影响：`publishers/` 适配器接口不变，`publish()` 的实现从"导出内容包"升级为"自动发布"时，上层代码零改动。

---

## 2. 本地运行方式（方案 A：不用 Docker）

MVP 期所有组件都在本机直接运行，**不需要安装 Docker**：


| 组件             | 运行方式                                   | 说明                                                              |
| -------------- | -------------------------------------- | --------------------------------------------------------------- |
| **PostgreSQL** | 本机已安装的 PostgreSQL 18                   | 服务 `postgresql-x64-18`，端口 `localhost:5432`，为本项目建库 `media_agent` |
| **后端**         | `uv run uvicorn app.main:app --reload` | 热重载 + 断点调试                                                      |
| **前端**         | `npm run dev`                          | Vite 热更新                                                        |


为什么不用 Docker：

- 本机已有 PostgreSQL 18 在跑，直接复用最省事。
- 未安装 Docker，为数据库单独装 Docker Desktop 性价比低（体积大、需配 WSL2）。
- MVP 目标是快速跑通流程，不是做容器化部署。

生产部署期（以后）再考虑 Docker 容器化；届时应用仍只认 `DATABASE_URL`，切换成本低。

---

## 3. 依赖管理：uv（问题 3 确认）

- 后端使用 **uv** 管理：`pyproject.toml` 声明依赖 + `uv.lock` 锁版本。
- 常用命令约定：
  - 初始化：`uv init` / 安装依赖：`uv sync`
  - 加依赖：`uv add langgraph langgraph-checkpoint-postgres langchain-openai fastapi ...`
  - 运行：`uv run uvicorn app.main:app --reload`
- Python 版本固定 3.12（写入 `.python-version`，uv 自动管理解释器）。

---

## 4. LLM 选型：豆包双模型（文本 + 生图）

豆包模型通过**火山方舟（Ark）调用。MVP 用两个模型、两个 API 接口**（详见 0.2 节），共用同一平台和同一个 `ARK_API_KEY`：

- **文本模型 `doubao-seed-1-8-251228`**：负责选题、文案、分镜脚本、平台适配四类文本生成。方舟对话接口是 **OpenAI 兼容协议**，用 `langchain-openai` 的 `ChatOpenAI` 接入：
  - `base_url = https://ark.cn-beijing.volces.com/api/v3`
  - `api_key = ARK_API_KEY`（方舟控制台获取）
  - `model = doubao-seed-1-8-251228`（或在方舟创建的推理接入点 endpoint ID）
- **生图模型 `doubao-seedream-4-5-251128`**：负责"分镜脚本 → 图片"，走方舟的生图接口 `/images/generations`（火山方舟 SDK 或 HTTP 直调）。Seedream 对**中文文字直出**支持较好，MVP 可先尝试图片直出文字，效果不满意再上"底图 + Pillow 排版"方案。
- `.env` 配置项收敛为：

```
ARK_API_KEY=xxx
LLM_MODEL=doubao-seed-1-8-251228
IMAGE_MODEL=doubao-seedream-4-5-251128   # 以方舟控制台实际可用型号为准
LLM_BASE_URL=https://ark.cn-beijing.volces.com/api/v3
```

- 原方案中的 `llm/` 网关层保留但简化：MVP 只写一个 `ark_provider`，`factory` 里也只注册这一个；将来换模型/加模型再扩展，接口不变。

---

## 5. 前端：React + TypeScript（问题 5 确认）

- 技术栈：**Vite + React 18 + TypeScript + Ant Design 5 + Zustand**（状态管理）+ Axios。
- MVP 只做 3 个页面，砍掉原方案中的看板统计等锦上添花功能：


| 页面        | 功能                                                                |
| --------- | ----------------------------------------------------------------- |
| 任务列表页     | 创建任务（输入方向）、任务列表（状态标签：待选题/待审文案/生成图片中/待审图片/已完成）                     |
| 任务详情页（核心） | 分步条展示流水线进度；根据当前挂起阶段渲染对应操作区：选题卡片单选 / 文案展示+通过或填修改意见 / 图片九宫格+通过或勾选重绘 |
| 小红书内容包页   | 展示适配后的标题/正文/话题标签/图片组，一键复制文字、批量下载图片，并可标记"已发布"                      |


- 实时性简化：MVP 用**前端轮询**（任务详情页 3 秒轮询一次状态接口）代替 SSE，实现成本低一个量级；体验不够再升级 SSE。

---

## 6. MVP 裁剪清单（问题 6 确认）

**明确砍掉、需要时再加**的能力（架构上都已留好位置，加回来不伤筋动骨）：


| 裁掉的能力                   | MVP 替代做法                              | 未来加回位置                                     |
| ----------------------- | ------------------------------------- | ------------------------------------------ |
| 用户认证/鉴权（登录、权限）          | 无登录，单人使用                              | `core/security.py` + API 依赖注入              |
| 凭证/数据加密                 | 无平台凭证需要存储（小红书为人工发布）                   | `platform_accounts` 表 + 应用层加密              |
| 微信公众号 API 直发            | 不做，MVP 只出小红书内容包                       | `publishers/wechat_mp.py`                  |
| 抖音/快手内容包适配              | 不做，只适配小红书                             | `prompts/platform/` + `publishers/` 各加一个文件 |
| 平台账号管理模块                | 无需配置平台账号                              | `api/v1/platforms.py`                      |
| SSE 实时推送                | 前端轮询                                  | `api/v1/events.py`                         |
| 定时/批量发布、排产调度            | 手动逐篇操作，内容包页标记"已发布"                    | 任务服务 + APScheduler                         |
| Docker / docker-compose | 不用，本机已有 PostgreSQL 18                 | 生产部署期再评估                                   |
| 对象存储                    | 图片存本地 `data/images/`，FastAPI 静态目录直接对外 | `core/storage.py` 抽象已预留                    |
| 多模型路由                   | 文本一个豆包模型 + 生图一个 Seedream 模型，固定搭配      | `llm/factory.py`                           |
| 数据回流分析、记忆偏好学习           | 无                                     | 独立模块                                       |


**保留不砍**的核心（这些是流程骨架，砍了 MVP 就不成立）：LangGraph 三断点工作流、PostgresSaver 持久化、文案版本留档（`content_versions` 表）、分镜与出图两阶段设计。

---

## 7. LLM 交互调试方案（问题 7 答复）

调试是 MVP 期最高频的活动，设计三层调试手段，从轻到重：

### 7.1 第一层：结构化 LLM 调用日志（默认开启）

在 `llm/` 网关层统一埋点，**每一次** LLM/生图调用自动记录：

- 记录内容：`task_id`、节点名、完整 prompt（system + user）、完整响应、耗时、token 用量、错误信息。
- 落地方式：双写
  - 控制台：DEBUG 级别彩色输出（开发时直接看）；
  - PostgreSQL `llm_call_logs` 表：可回溯任意任务的任意一次调用，排查"为什么这篇文案跑偏了"。
- 好处：出问题时不用复现，直接查这次调用喂给模型的完整 prompt。

### 7.2 第二层：FastAPI 调试端点（DEBUG 模式专属）

`config.py` 增加 `DEBUG=true` 开关，开启后额外暴露一组 `/api/debug/`* 端点：


| 端点                                    | 用途                                                               |
| ------------------------------------- | ---------------------------------------------------------------- |
| `GET /api/debug/tasks/{id}/state`     | 直接吐出 LangGraph 当前 checkpoint 的完整 State（JSON），看工作流卡在哪、State 里存了什么 |
| `GET /api/debug/tasks/{id}/history`   | 该任务的 checkpoint 历史（每一步的状态快照），追溯流程走向                              |
| `GET /api/debug/tasks/{id}/llm-calls` | 该任务全部 LLM 调用日志                                                   |
| `POST /api/debug/llm/chat`            | 直接透传调用豆包（自定义 prompt），用于快速试 prompt，不必跑整个工作流                       |


配合 `uvicorn --reload` 热重载 + FastAPI 自带的 `/docs`（Swagger UI），改完节点代码可以立即在浏览器里手动触发调试。

### 7.3 第三层：LangSmith / LangGraph Studio（可选，零代码接入）

- **LangSmith**：设置两个环境变量（`LANGSMITH_TRACING=true` + API Key）即可，全链路 trace 可视化——每个节点的输入输出、每次 LLM 调用、耗时瀑布图。免费额度对 MVP 足够，强烈建议开着。
- **LangGraph Studio**（`langgraph dev` 本地启动）：图形化查看工作流拓扑、单步执行节点、在 interrupt 断点处手动注入 resume 值，适合调工作流本身的流转逻辑。

---

## 8. MVP 版代码结构（简化版）

在原方案结构上做减法（去掉 `security.py`、`platforms.py`、`events.py`、多 provider 等），MVP 实际要写的文件如下：

```
media-ai-agent/
├── .env.example                  # 含本机 PostgreSQL 连接串
│
├── backend/
│   ├── pyproject.toml            # uv 管理
│   ├── .python-version           # 3.12
│   ├── alembic/                  # 数据库迁移
│   └── app/
│       ├── main.py               # FastAPI 入口（挂静态图片目录、注册路由）
│       ├── config.py             # Pydantic Settings（含 DEBUG 开关）
│       ├── api/v1/
│       │   ├── tasks.py          # 创建/列表/详情（详情含挂起阶段+待决策数据）
│       │   ├── decisions.py      # 三个人工决策接口（选题/文案/图片）→ resume
│       │   ├── contents.py       # 选题/文案版本/图片/内容包查询
│       │   ├── publish.py        # 小红书内容包导出 + 标记已发布
│       │   └── debug.py          # DEBUG 模式调试端点
│       ├── schemas/              # Pydantic 请求/响应模型
│       ├── services/
│       │   ├── task_service.py
│       │   ├── workflow_service.py   # 启动/resume/查 State
│       │   └── publish_service.py
│       ├── agent/
│       │   ├── graph.py          # StateGraph 组装
│       │   ├── state.py
│       │   ├── checkpointer.py   # PostgresSaver
│       │   ├── nodes/            # 5 个业务节点 + human_gates.py
│       │   └── prompts/          # 选题/文案/分镜/小红书适配 prompt
│       ├── llm/
│       │   ├── ark_text.py       # 豆包文本模型（chat/completions，ChatOpenAI）
│       │   ├── ark_image.py      # Seedream 生图（images/generations）
│       │   └── call_logger.py    # llm_call_logs 落库（两个模型的调用都埋点）
│       ├── publishers/
│       │   ├── base.py
│       │   └── xiaohongshu.py    # 小红书内容包导出（MVP 唯一适配器）
│       ├── models/               # tasks / topics / content_versions / images
│       │                         # / publish_records / llm_call_logs
│       ├── repositories/
│       └── core/
│           ├── database.py
│           └── logging.py
│
├── frontend/                     # Vite + React + TS + AntD + Zustand
│   └── src/
│       ├── api/                  # Axios 封装 + 轮询 hook
│       ├── pages/
│       │   ├── TaskList/
│       │   ├── TaskDetail/       # 核心：分步流水线 + 三种决策操作区
│       │   └── ContentPackage/   # 小红书内容包：复制/下载/标记已发布
│       └── stores/
│
└── docs/
    ├── 项目方案设计.md
    └── MVP落地方案.md            # 本文档
```

数据库相对原方案的变化：去掉 `platform_accounts` 表（小红书人工发布，无凭证需要存储），新增 `llm_call_logs` 表（调试用）；`publish_records` 表保留，用于记录内容包导出与"已发布"标记。

---

## 9. MVP 开发顺序（建议 2 周内跑通）


| 步骤     | 内容                                                                                                | 验证标准                                                    |
| ------ | ------------------------------------------------------------------------------------------------- | ------------------------------------------------------- |
| D1     | 确认本机 PostgreSQL 18 服务运行；创建 `media_agent` 库；uv 初始化后端骨架；Alembic 建表；豆包文本 + Seedream 生图两个 API 连通性冒烟测试 | 后端能连上本机库；`POST /api/debug/llm/chat` 能拿到豆包回复，生图接口能出一张测试图 |
| D2-D3  | LangGraph 工作流：State + 选题节点 + 选题 interrupt + 文案节点 + 文案审核 interrupt（含修改循环），接 PostgresSaver          | 用 Swagger 手动走完"创建任务→选题→审文案 3 轮→定稿"，重启服务后任务能续            |
| D4-D5  | 分镜节点 + Seedream 出图 + 图片审核 interrupt（单张重绘）+ 小红书适配节点                                                | 全流程产出小红书内容包 JSON + 本地图片文件                               |
| D6-D8  | 前端：任务列表 + 任务详情（三种决策操作区）+ 轮询                                                                       | 运营人员不碰 Swagger 也能走完全流程                                  |
| D9-D10 | 小红书内容包页（一键复制文字/批量下载图片/标记已发布）                                                                      | 小红书内容 30 秒内人工发布完成                                       |
| 机动     | Prompt 调优（重点：选题质量、分镜压缩质量、图片风格一致性、小红书文案调性）                                                         | 产出内容达到可发布水准                                             |


---

## 附：MVP 环境变量全集（`.env.example`）

```
# 数据库（本机原生 PostgreSQL 18，方案 A）
# 密码替换为安装 PostgreSQL 时设置的密码；需先 CREATE DATABASE media_agent;
DATABASE_URL=postgresql+asyncpg://postgres:你的密码@localhost:5432/media_agent

# 豆包（火山方舟，一个 Key 两个模型）
ARK_API_KEY=
LLM_BASE_URL=https://ark.cn-beijing.volces.com/api/v3
LLM_MODEL=doubao-seed-1-8-251228     # 文本：选题/文案/分镜/小红书适配
IMAGE_MODEL=doubao-seedream-4-5-251128      # 生图：分镜脚本 → 图片（以方舟控制台实际型号为准）

# 调试
DEBUG=true
LANGSMITH_TRACING=false        # 可选：true + 下方 Key 开启全链路 trace
LANGSMITH_API_KEY=

# 存储
IMAGE_DIR=./data/images
```

