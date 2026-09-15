# AiDream · THINK-AI 本地复刻

1:1  **New API 风格大模型网关**：统一 Base URL、令牌额度、模型广场、操练场、GPT-Image2 生图工作台。

技术栈：**Python + FastAPI**（后端）+ **Vue 3 + Vite**（前端）。

## 功能对照

- 首页网关入口、供应商墙、系统公告
- 登录 / 注册 / JWT 会话
- 数据看板（余额、消耗、RPM/TPM、趋势）
- API 密钥（创建、复制、禁用、删除、分组）
- 使用日志（时间、模型、token、花费）
- 钱包充值（兑换码 + 邀请）
- 模型广场（供应商/计费筛选、官方价与折扣）
- 操练场流式对话
- GPT-Image2 生图工作台
- OpenAI 兼容接口：`/v1/chat/completions`、`/v1/responses`、`/v1/models`、`/v1/images/generations`、`/v1/embeddings`

## 启动

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

另开终端：

```bash
cd frontend
npm install
npm run dev
```

浏览器打开 http://127.0.0.1:5180

## 演示账号

| 用户 | 密码 | 说明 |
| --- | --- | --- |
| FengYu | Feng1010 | 普通用户，已预置余额与密钥 |
| admin | admin123 | 管理员 |

兑换码：`WELCOME100`（到账 $100）

## 调用示例

```bash
curl http://127.0.0.1:8000/v1/chat/completions \
  -H "Authorization: Bearer <密钥管理页复制的 sk-...>" \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-5.4-mini","messages":[{"role":"user","content":"你好"}]}'
```

未配置上游时，网关返回本地演示回复并照常扣费、写日志。若要转发真实模型：

```bash
export UPSTREAM_BASE_URL=https://api.openai.com/v1
export UPSTREAM_API_KEY=sk-...
```

（当前 `Settings` 读取环境变量需在 `backend/.env` 中配置 `upstream_base_url` / `upstream_api_key`。）
