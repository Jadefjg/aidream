# AiDream / THINK-AI 生产部署与外部服务接入指南

本文说明如何把当前本地复刻项目部署为可上线的多渠道模型网关。文中的配置示例使用占位符，真实密钥只应通过部署平台的 Secret 管理注入，不能提交到 Git。

## 1. 推荐生产架构

```text
浏览器 -> Nginx/云负载均衡 -> Vue 静态文件
                           -> FastAPI 多实例
                                |-> PostgreSQL/MySQL
                                |-> Redis（限流、会话、熔断、任务）
                                |-> KMS/Vault（密钥加密）
                                |-> Stripe/微信/支付宝（支付回调）
                                |-> 上游模型渠道
```

建议首版使用：PostgreSQL + Redis + Stripe（国际卡）或微信/支付宝服务商支付（中国大陆），部署在 HTTPS 域名下。SQLite 仅适合单实例本地或低流量演示。

## 2. 部署前准备

需要准备：

- 一个域名，例如 `ai.example.com`
- HTTPS 证书（Let's Encrypt 或云厂商证书）
- PostgreSQL 15+ 或 MySQL 8+
- Redis 7+
- 一个 KMS/Vault 实例
- 一个支付商户账号
- 至少一个真实模型供应商 API Key
- 服务器时间同步（NTP）

生产环境安装依赖：

```bash
cd backend
source .venv/bin/activate
pip install -r requirements.txt
pip install psycopg[binary] redis cryptography apscheduler
# MySQL 项目使用：pip install pymysql
```

## 3. 环境变量

创建 `backend/.env`，并设置严格权限：

```bash
chmod 600 backend/.env
```

建议配置：

```env
APP_NAME=THINK-AI
SECRET_KEY=<至少32字节随机值>
DATABASE_URL=postgresql+psycopg://aidream:<password>@127.0.0.1:5432/aidream
REDIS_URL=redis://:password@127.0.0.1:6379/0
CORS_ORIGINS=https://ai.example.com
SERVER_ADDRESS=https://ai.example.com
DOCS_LINK=https://docs.example.com

# 没有配置数据库渠道时的默认 OpenAI 兼容渠道
UPSTREAM_BASE_URL=https://api.openai.com/v1
UPSTREAM_API_KEY=<secret>

# 安全策略
LOGIN_RATE_LIMIT=10
LOGIN_RATE_WINDOW_SECONDS=300
CHANNEL_CIRCUIT_THRESHOLD=3
CHANNEL_CIRCUIT_COOLDOWN_SECONDS=60

# 备份
DATABASE_BACKUP_DIR=/var/backups/aidream
BACKUP_RETENTION_DAYS=14

# KMS/Vault，二选一
KMS_PROVIDER=aws
AWS_REGION=ap-southeast-1
AWS_KMS_KEY_ID=<kms-key-id>
# VAULT_ADDR=https://vault.example.com
# VAULT_TOKEN=<通过部署平台注入>

# 支付适配器
PAYMENT_PROVIDER=stripe
STRIPE_SECRET_KEY=<secret>
STRIPE_WEBHOOK_SECRET=<secret>
STRIPE_PRICE_MAP={"10":"price_xxx","50":"price_yyy","100":"price_zzz"}
```

随机生成 `SECRET_KEY`：

```bash
openssl rand -hex 32
```

## 4. PostgreSQL / MySQL

### PostgreSQL 推荐配置

创建数据库和专用用户：

```sql
CREATE USER aidream WITH PASSWORD 'use-a-secret-manager-password';
CREATE DATABASE aidream OWNER aidream;
REVOKE ALL ON DATABASE aidream FROM PUBLIC;
```

连接串：

```env
DATABASE_URL=postgresql+psycopg://aidream:password@db-host:5432/aidream
```

### MySQL 配置

```sql
CREATE DATABASE aidream CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'aidream'@'%' IDENTIFIED BY 'strong-password';
GRANT ALL PRIVILEGES ON aidream.* TO 'aidream'@'%';
FLUSH PRIVILEGES;
```

连接串：

```env
DATABASE_URL=mysql+pymysql://aidream:password@db-host:3306/aidream?charset=utf8mb4
```

生产环境应引入 Alembic：

```bash
pip install alembic
alembic init migrations
alembic revision --autogenerate -m "initial schema"
alembic upgrade head
```

不要在生产环境依赖 `Base.metadata.create_all()` 作为迁移工具。每次发布前先执行迁移，发布后再启动应用。

## 5. Redis 分布式基础设施

Redis 用于：

- 登录失败计数和 IP 限流
- 多实例共享熔断状态
- 幂等支付 webhook
- 异步图片/音频任务队列
- 短期会话和缓存

实现原则：

```text
INCR login:fail:<ip>
EXPIRE login:fail:<ip> 300
SET payment:event:<event_id> 1 NX EX 86400
```

支付 webhook 必须使用 `SET ... NX` 做幂等，否则支付商重试会重复充值。限流不能只使用 Python 进程内字典，否则多实例时每台服务器都有独立计数。

生产 Redis 要开启密码、TLS（如跨主机）、持久化和内网访问控制；不要把 Redis 端口暴露到公网。

## 6. KMS / Vault 密钥管理

### 推荐策略

数据库只保存：

- 密文 `encrypted_api_key`
- nonce/iv
- KMS key id
- 密钥版本

应用启动时只读取 KMS/Vault 的解密权限，不把主密钥写入数据库。

### AWS KMS

1. 创建对称加密 KMS Key。
2. 给应用实例绑定最小权限 IAM Role，仅允许 `kms:Encrypt` 和 `kms:Decrypt`。
3. 使用 KMS GenerateDataKey 生成数据密钥。
4. 使用 AES-GCM 在应用内加密 API Key。
5. 将数据密钥密文和 API Key 密文一起保存。

不要每次请求都调用 KMS 解密；可在进程内缓存短时间明文，并在密钥更新时主动清理缓存。

### HashiCorp Vault

使用 Transit Engine：

```bash
vault secrets enable transit
vault write -f transit/keys/aidream
vault policy write aidream-policy policy.hcl
```

应用只获得 `transit/encrypt/aidream` 和 `transit/decrypt/aidream` 权限。API Key 列表接口必须继续只返回掩码。

## 7. 支付系统接入

支付不能由前端直接修改余额。正确流程：

```text
用户创建订单 -> 支付商下单 -> 用户付款 -> 支付商 webhook
             -> 验签 -> 幂等检查 -> 更新订单 -> 增加额度 -> 写充值日志
```

建议新增 `payments` 表：

- `id`
- `user_id`
- `provider`
- `provider_order_id`（唯一）
- `amount`
- `quota`
- `status`：pending/paid/failed/refunded
- `raw_event_id`（唯一）
- `created_at`、`paid_at`

Webhook 必须：

1. 校验签名；
2. 校验商户号、币种和金额；
3. 校验订单状态；
4. 通过数据库事务更新订单和用户额度；
5. 记录充值日志；
6. 对重复事件返回 200，但不得重复加余额。

Stripe 需要配置：

```text
POST /api/payment/stripe/webhook
```

本地测试：

```bash
stripe listen --forward-to localhost:8000/api/payment/stripe/webhook
```

微信/支付宝接入时，签名算法、证书和回调格式必须使用官方 SDK，不能自行拼接验签。

## 8. Anthropic 与 Gemini 原生协议

建议按 `provider` 写独立适配器，不在单个路由中堆叠条件：

```text
ProviderAdapter
  - build_request()
  - parse_response()
  - parse_stream_chunk()
  - estimate_usage()
```

Anthropic：

- 请求头使用 `x-api-key` 和 `anthropic-version`
- `/v1/messages` 使用 `system`、`messages`、`max_tokens`
- 流式事件解析 `content_block_delta`

Gemini：

- 使用 `contents[].parts[]`
- 模型路径通常为 `models/{model}:generateContent`
- 流式接口使用 `streamGenerateContent`
- API Key 通常通过 query 参数或 Google SDK 传递

每种协议都应分别增加普通响应、流式响应、错误响应和 usage 计费测试。

## 9. 独立 token 计费

不要只按统一 OpenAI 规则估算。建议在 `ModelPrice` 或独立 `billing_rules` 表中保存：

- provider
- model
- input_price_per_million
- output_price_per_million
- cached_input_price
- request_price
- image_size_price
- audio_seconds_price
- currency

上游返回 usage 后，以真实 usage 进行最终结算；预估额度只用于请求前余额检查。若上游不返回 usage，则记录 `usage_source=estimated`，并保留修正能力。

## 10. 线上模型和价格同步

同步任务应具备：

- provider 级适配器
- ETag/Last-Modified 或 hash 比较
- 失败重试和退避
- 数据校验（价格不能为负、模型名不能为空）
- 变更审计日志
- 手工回滚

建议使用 APScheduler、Celery Beat 或 Kubernetes CronJob，每 10～30 分钟同步一次。同步失败不能清空现有目录，只记录错误并保留上一版本。

## 11. 备份、恢复与定时任务

SQLite 本地备份：

```bash
cd backend
.venv/bin/python scripts/backup_db.py backup /var/backups/aidream
```

生产 PostgreSQL 使用：

```bash
pg_dump "$DATABASE_URL" | gzip > /var/backups/aidream/aidream-$(date +%F-%H%M).sql.gz
```

恢复前必须：

1. 停止写入流量；
2. 验证备份文件 checksum；
3. 在临时数据库先恢复并执行健康检查；
4. 再切换生产连接；
5. 保留恢复记录。

定时任务可使用 systemd timer、CronJob 或 APScheduler。备份至少遵循 3-2-1 原则：3 份副本、2 种介质、1 份异地。

## 12. Nginx 与进程管理

Nginx 负责：

- HTTPS 终止
- Vue 静态文件
- `/api` 和 `/v1` 反向代理
- 请求体大小限制
- 基础访问日志

FastAPI 使用 Gunicorn/Uvicorn 多进程：

```bash
gunicorn app.main:app -k uvicorn.workers.UvicornWorker -w 4 --bind 127.0.0.1:8000
```

发布流程：

```text
备份 -> 数据库迁移 -> 启动新实例 -> 健康检查 /health -> 切换流量 -> 观察错误率
```

## 13. 上线前安全清单

- [ ] 更换默认 `SECRET_KEY`
- [ ] 删除或修改默认管理员密码
- [ ] 删除默认兑换码 `WELCOME100`
- [ ] 仅允许正式前端域名 CORS
- [ ] API Key 使用 KMS/Vault 加密
- [ ] Redis 和数据库不暴露公网
- [ ] 登录限流改为 Redis 分布式实现
- [ ] 支付 webhook 已验签并实现幂等
- [ ] 管理接口启用审计日志
- [ ] 数据库迁移已纳入发布流程
- [ ] 已完成备份恢复演练
- [ ] 已配置监控、告警和日志留存
- [ ] 已验证上游渠道失败切换
- [ ] 已验证余额不足、过期令牌、重复支付等异常场景

## 14. 建议实施顺序

1. 先切换 PostgreSQL，并建立 Alembic 迁移。
2. 接入 Redis，将登录限流、支付幂等和熔断状态迁移到 Redis。
3. 实现 KMS/Vault 加密存储渠道 API Key。
4. 实现支付订单和 webhook，先使用支付沙箱。
5. 完成 Anthropic/Gemini 原生适配器和流式测试。
6. 增加模型/价格同步任务。
7. 配置自动备份、恢复演练和监控告警。
8. 最后进行灰度发布和压力测试。

支付、KMS 和真实模型上游都需要用户自己的第三方账户、商户资质或云权限。没有这些凭据时，只能完成代码适配和沙箱测试，不能安全地模拟“支付成功”或伪造真实模型结果。
