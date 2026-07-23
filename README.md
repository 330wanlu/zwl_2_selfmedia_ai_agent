# 美妆自媒体运营 AI Agent

基于 **LangGraph + FastAPI + React** 的美妆内容生产流水线：输入一个内容方向，经人工在关键节点拍板，产出可发小红书的内容包（标题 / 正文 / 标签 / 配图）。

当前进度：**阶段 0～4 已全部完成**（底座 → 工作流 → Debug/导出 → 前端 → 联调与 Prompt 打磨），主链路可直接运营试用。

---

## 能做什么

| 能力 | 说明 |
| --- | --- |
| 选题生成 | 围绕方向生成约 5 个候选选题，可换一批 |
| 文案写作 | 按选题写小红书口语正文，可多轮提意见重写 |
| 分镜 + 出图 | 拆成 3～5 张图，Seedream 生图，可指定某张重绘 |
| 小红书内容包 | 标题、正文、话题标签、图片组 |
| 导出与发布 | JSON 导出、图片 zip 下载、标记已发布 |
| 任务取消 | 未完成任务可随时取消，之后不能再决策 |

---

## 技术栈

| 层 | 技术 |
| --- | --- |
| 后端 | FastAPI、LangGraph（PostgresSaver checkpoint）、SQLAlchemy、Alembic、uv |
| 模型 | 火山方舟：豆包文本 + Seedream 生图 |
| 数据库 | PostgreSQL 18（业务表 + LangGraph checkpoint） |
| 前端 | Vite、React 19、TypeScript、Ant Design、Axios、Zustand、React Router |

---

## 整体流程

```
输入内容方向（如「敏感肌夏季防晒推荐」）
        ↓
① AI 生成候选选题
        ↓ 【人工】选一个 / 换一批
② AI 写文案
        ↓ 【人工】通过 / 提意见重写（可多轮）
③ AI 规划分镜 → Seedream 逐张出图
        ↓ 【人工】全部通过 / 勾选重绘
④ AI 适配小红书内容包
        ↓
⑤ 复制文字、下载图片 zip、导出 JSON、标记已发布
```

中间三个断点靠人工决策；服务重启不丢进度（PostgreSQL checkpoint）。

---

## 仓库结构

```
├── README.md                 # 本说明
├── docs/                     # 方案与阶段开发记录
│   ├── 项目方案设计.md
│   ├── MVP落地方案.md
│   ├── 开发流程.md
│   └── 开发记录-阶段0～4.md
├── backend/                  # FastAPI 后端
│   ├── app/
│   │   ├── agent/            # LangGraph 图、节点、Prompt
│   │   ├── api/              # 任务 / 决策 / 导出 / debug
│   │   ├── llm/              # 豆包文本、Seedream 生图
│   │   ├── models/           # 业务表模型
│   │   └── services/         # 工作流启停与 resume
│   ├── scripts/              # 建库、自测脚本
│   ├── data/images/          # 生成图片本地存储
│   └── .env.example
└── frontend/                 # 运营前端
    ├── src/pages/            # 任务列表 / 详情 / 内容包
    └── scripts/run_e2e.mjs   # Playwright 全流程自测
```

---

## 环境要求

- Windows（本仓库命令按 PowerShell 编写）
- Python 3.12+（用 `uv` 管理）
- Node.js 20+（前端）
- PostgreSQL 18，库名建议 `media_agent`
- 火山方舟 `ARK_API_KEY`（文本 + 生图同一 Key）

---

## 快速开始

### 1. 后端

```powershell
cd backend
copy .env.example .env
# 编辑 .env：填写 DATABASE_URL 密码、ARK_API_KEY

uv sync
uv run python scripts/create_db.py          # 若库已存在可跳过
uv run alembic upgrade head                 # 业务表迁移
uv run python scripts/setup_checkpointer.py  # LangGraph checkpoint 表
uv run uvicorn app.main:app --reload --reload-dir app --port 8001
```

- 健康检查：http://127.0.0.1:8001/health  
- Swagger：http://127.0.0.1:8001/docs  

### 2. 前端

```powershell
cd frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5174
```

- 运营页：http://127.0.0.1:5174  
- 开发期 Vite 已代理 `/api`、`/images` → `:8001`，一般无需配前端 `.env`。

### 3. `.env` 关键项说明

| 变量 | 作用 |
| --- | --- |
| `DATABASE_URL` | PostgreSQL 异步连接串 |
| `ARK_API_KEY` | 方舟 API Key |
| `LLM_MODEL` / `IMAGE_MODEL` | 文本 / 生图模型名 |
| `DEBUG` | `true`：挂载 `/api/debug/*` 并打更细日志；**不影响**主业务流水线。`false` 只关掉调试端点 |
| `IMAGE_DIR` | 生图本地目录，默认 `./data/images` |

---

## 运营人员怎么用（前端）

1. 打开 http://127.0.0.1:5174/tasks  
2. 输入内容方向 →「创建并开始」→ 进入详情页（约 3 秒自动刷新）  
3. **选题**：单选卡片 →「确认选题」（或换一批）  
4. **文案**：阅读正文 →「通过」，或填意见「提交修改意见并重写」  
5. **图片**：预览 →「全部通过」，或勾选需重绘的图提交  
6. 完成后点「查看内容包」→ 复制文字、下载 zip、标记已发布  

详情页运行中可随时「取消任务」；取消后不能再选题/审文案/审图。

也可用 Swagger 走同一套 API（适合排障，不适合日常运营）。

---

## 主要 API（摘要）

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/api/v1/tasks` | 创建任务并启动工作流 |
| GET | `/api/v1/tasks` | 任务列表 |
| GET | `/api/v1/tasks/{id}` | 详情（含 `pending_decision`） |
| POST | `/api/v1/tasks/{id}/decisions/topic` | 选题决策 |
| POST | `/api/v1/tasks/{id}/decisions/content` | 文案审核 |
| POST | `/api/v1/tasks/{id}/decisions/images` | 图片审核 / 重绘 |
| POST | `/api/v1/tasks/{id}/cancel` | 取消任务 |
| GET | `/api/v1/tasks/{id}/platform-contents` | 内容包 |
| GET | `/api/v1/tasks/{id}/export` | 导出 JSON |
| GET | `/api/v1/tasks/{id}/export/images.zip` | 批量下载图片 |
| POST | `/api/v1/tasks/{id}/publish/mark` | 标记已发布 |
| * | `/api/debug/*` | 仅 `DEBUG=true` 时可用 |

---

## 自测命令（可选）

前后端都启动后：

```powershell
# 后端阶段 4 品鉴 / 边界（按需选子命令，all 耗时长）
cd backend
uv run python scripts/test_stage4.py review
uv run python scripts/test_stage4.py cancel
# uv run python scripts/test_stage4.py all

# 前端 Playwright 全流程（消耗 LLM / 生图额度）
cd frontend
npm run test:e2e
```

---

## 文档索引

| 文档 | 内容 |
| --- | --- |
| [docs/项目方案设计.md](docs/项目方案设计.md) | 整体方案 |
| [docs/MVP落地方案.md](docs/MVP落地方案.md) | MVP 范围与技术选型 |
| [docs/开发流程.md](docs/开发流程.md) | 分阶段开发与验收清单 |
| [docs/开发记录-阶段0.md](docs/开发记录-阶段0.md) | 环境与双模型冒烟 |
| [docs/开发记录-阶段1.md](docs/开发记录-阶段1.md) | 核心工作流 |
| [docs/开发记录-阶段2.md](docs/开发记录-阶段2.md) | Debug / 导出 / Prompt 初调 |
| [docs/开发记录-阶段3.md](docs/开发记录-阶段3.md) | 前端三页与 E2E |
| [docs/开发记录-阶段4.md](docs/开发记录-阶段4.md) | 联调、边界、内容品鉴 |

---

## 安全提示

- 请勿把真实 `backend/.env`（含数据库密码、API Key）提交进仓库。  
- 仓库只保留 `backend/.env.example` 作为配置模板。  
- 生成的图片在 `backend/data/images/`，按需自行备份或清理。
