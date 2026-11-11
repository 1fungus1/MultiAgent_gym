# MultiAgent_gym

这是面向多智能体演进的健身房管理系统。当前包含 Python FastAPI 后端和 Vue 3 + Vite 前端。

## 技术栈

- Python 3.12
- FastAPI
- SQLAlchemy 2
- MySQL + PyMySQL
- Alembic
- Pydantic 2
- PyJWT
- Argon2 密码哈希

## 在 PyCharm 中启动

1. 用 PyCharm 打开项目根目录。
2. 将解释器选择为 Conda 环境 `gym_pro`。
3. 把 `.env.example` 复制为 `.env`，填写数据库密码和 JWT 密钥。
4. 在 PyCharm 终端安装依赖：

   ```powershell
   python -m pip install -e ".[dev]"
   ```

5. 启动后端：

   ```powershell
   uvicorn app.main:app --reload --port 9000
   ```

   也可以直接在 PyCharm 中运行根目录的 `run.py`。

6. 打开 `http://127.0.0.1:9000/docs` 查看自动生成的接口文档。

前端开发：

```powershell
cd frontend
npm install
npm run dev
```

Vite 已配置把 `/api` 代理到 `http://localhost:9000`，因此前端接口代码不需要修改。

## 数据库

项目使用小写数据库名 `multiagent_gym`。后端启动时默认只创建不存在的表，不会删除或覆盖已有数据。

项目内提供了一份重新设计的演示数据
[`database/MultiAgent_gym.sql`](database/MultiAgent_gym.sql)，包含 18 名会员、
8 名教练、20 门课程和 68 条预约。所有会员卡统一有效至 2026-12-31。

全新数据库可以选择以下任一方式：

```powershell
alembic upgrade head
```

或者执行：

```text
database/schema.sql
```

如果数据库是空的，可以在 `.env` 中设置：

```dotenv
SEED_DEMO_DATA=true
```

首次启动会生成管理员 `admin / 123456` 和会员 `zhangsan / 123456`。只在本地开发环境使用这组账号。

旧数据库中的 MD5 密码可正常登录，并会在登录成功后自动升级为 Argon2。通过原 `data.sql` 写入的明文演示密码也支持一次性兼容升级，正式环境应把 `ALLOW_LEGACY_PLAINTEXT_PASSWORDS` 设为 `false`。

## Agent 体系

登录后的页面右下角会显示可拖拽的主助手。它会优先检索
[`data/健身知识大全_核心版_v0.5.md`](data/健身知识大全_核心版_v0.5.md)，
再根据意图把会话权转移给以下子 Agent：

- Mira（主助手）：聊天、健身知识问答和会话分诊。
- Nova（课程助手）：读取数据库中的可预约课程并进行推荐。
- Vera（预约助手）：查询、预约、取消和改约当前会员自己的课程。
- Atlas（运营助手）：管理员专属，分析今日课程、预约人数和满员课程。

预约、取消和改约采用两步确认。子 Agent 先生成带签名的待确认操作，用户确认后才通过事务写入数据库。
前端会保存当前会话所属 Agent 和待确认令牌，并按 Agent 传输协议继续对话。

## 会员与课程业务

- 预约前检查会员状态和会员卡有效期；管理员可办理续费。
- 课程满员后支持候补队列；取消预约会触发自动递补和站内通知。
- 管理员可展示动态课程签到二维码，会员在有效时间窗口内扫码签到。
- 课程结束后未签到会自动标记爽约，并生成会员通知。
- 通知中心支持未读数、单条已读和全部已读。
- 运营日报汇总今日课程、预约、取消、候补、签到、爽约、容量和会员到期数据。

会员扫码时使用的地址由 `.env` 中的 `FRONTEND_PUBLIC_URL` 决定。若要用真实手机扫码，
需要将其设置为手机可访问的局域网地址，而不是 `127.0.0.1`。

知识检索采用混合方案：

- 本地 BM25 关键字检索；
- 火山多模态向量模型生成 1024 维查询向量；
- Milvus 中执行稠密向量检索；
- 使用 Reciprocal Rank Fusion 合并两路排名后交给 Agent。

应用首次启动时会检测 `gym_knowledge_v1` 集合，并自动将 50 条健身知识
向量化写入 Milvus。知识文件变化后会写入新的文档版本，旧版本数据不会被自动删除。
Milvus 不可用时自动回退到关键字检索。

模型配置位于 `.env`：

```dotenv
AGENT_PROVIDER=ark
AGENT_MODEL=deepseek-v4-flash-ga-260731
ARK_API_KEY=你的密钥
```

## 测试

```powershell
pytest
ruff check .
```

测试使用内存 SQLite，不依赖本机 MySQL。正式运行仍使用 MySQL。

## 目录说明

```text
app/
├── api/routes/      HTTP 路由与权限依赖
├── agent/           主 Agent、子 Agent、会话转移、确认令牌和业务工具
├── core/            配置、JWT、密码和统一响应
├── db/              数据库会话、建表和演示数据
├── services/        业务逻辑
├── main.py          FastAPI 入口
├── models.py        SQLAlchemy 模型
└── schemas.py       Pydantic 请求与响应模型
frontend/            Vue 前端
data/                健身知识库
alembic/             数据库迁移
database/            全新数据库建表脚本
tests/               自动化测试
```

业务服务没有依赖 FastAPI 路由对象，Agent 工具复用同一套事务服务，避免模型直接生成 SQL。
