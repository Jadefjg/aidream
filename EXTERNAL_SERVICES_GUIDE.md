# AiDream 外部服务详细配置手册

本文说明如何为 AiDream 配置真实支付、密钥管理和模型供应商。所有示例中的值均为占位符。不要把真实 API Key、私钥、商户证书或 webhook secret 发给任何人，也不要提交到 Git。

## 0. 配置原则

生产环境至少应有三套配置：

```text
development  本地演示，不连接真实支付
staging       沙箱支付、测试数据库、测试模型 Key
production    正式域名、正式支付、正式模型 Key
```

建议使用部署平台 Secret 管理：AWS Secrets Manager、Vault、Kubernetes Secret、云厂商密钥管理服务或 CI/CD Secret。不要依赖明文 `.env` 作为生产密钥仓库。

应用基础配置示例：

```env
APP_NAME=THINK-AI
SECRET_KEY=<openssl rand -hex 32 的结果>
DATABASE_URL=postgresql+psycopg://aidream:<password>@db.internal:5432/aidream
REDIS_URL=rediss://:<password>@redis.internal:6379/0
CORS_ORIGINS=https://ai.example.com
SERVER_ADDRESS=https://ai.example.com
```

## 1. Stripe 配置

适合国际信用卡、Apple Pay、Google Pay 等场景。正式收款前需要完成 Stripe 账户验证和业务审核。

### 1.1 注册和启用

1. 注册 Stripe Dashboard。
2. 完成企业/个人身份验证。
3. 填写业务网站、退款政策、隐私政策和服务描述。
4. 在 Test mode 下先配置测试产品。
5. 正式上线前切换到 Live mode，并重新生成正式环境密钥。

### 1.2 创建产品和价格

在 Product catalog 中建立充值产品，例如：

| 商品 | 金额 | 额度映射 |
|---|---:|---:|
| AI Wallet 10 | USD 10 | 10 美元额度 |
| AI Wallet 50 | USD 50 | 50 美元额度 |
| AI Wallet 100 | USD 100 | 100 美元额度 |

保存每个 Price ID，例如 `price_xxx`。金额不能由前端传入后直接信任，后端必须通过 Price ID 查询 Stripe 金额。

### 1.3 创建 API Key 和 webhook secret

Stripe Dashboard -> Developers -> API keys：

- 测试环境使用 `sk_test_...`
- 生产环境使用 `sk_live_...`

Stripe Dashboard -> Developers -> Webhooks：

添加：

```text
https://ai.example.com/api/payment/stripe/webhook
```

至少监听：

- `checkout.session.completed`
- `payment_intent.payment_failed`
- `charge.refunded`

保存 Signing secret：

```text
whsec_...
```

### 1.4 环境变量

```env
PAYMENT_PROVIDER=stripe
STRIPE_SECRET_KEY=sk_test_xxx
STRIPE_WEBHOOK_SECRET=whsec_xxx
STRIPE_PRICE_MAP={"10":"price_test_10","50":"price_test_50","100":"price_test_100"}
```

### 1.5 正确支付流程

```text
前端选择面额
 -> 后端根据面额选择固定 Price ID
 -> 后端创建 Checkout Session
 -> 用户跳转 Stripe 付款
 -> Stripe webhook 回调
 -> 验证签名
 -> 校验金额和订单号
 -> 幂等更新订单
 -> 增加用户额度
```

不能在 `success_url` 页面直接给用户充值。浏览器跳转可以被伪造，只有签名验证通过的 webhook 才能改变余额。

### 1.6 本地测试

安装 Stripe CLI 后：

```bash
stripe login
stripe listen --forward-to http://127.0.0.1:8000/api/payment/stripe/webhook
```

CLI 会打印临时 `whsec_...`，只用于本地 webhook 转发。

测试卡号：

```text
4242 4242 4242 4242
有效期：任意未来日期
CVC：任意三位数字
```

## 2. 微信支付配置

微信支付需要商户主体、商户号、API 证书和回调域名。个人开发者通常无法直接使用完整的正式支付能力。

### 2.1 申请资料

准备：

- 企业或个体工商户主体
- 营业执照
- 法人信息
- 对公账户或结算账户
- 已备案 HTTPS 域名
- 商品和服务说明
- 退款/隐私/用户协议页面

### 2.2 获取商户信息

在微信支付商户平台获取：

- `MCHID`：商户号
- `APPID`：公众号/小程序/开放平台 AppID
- `API V3 KEY`
- 商户私钥 `apiclient_key.pem`
- 商户证书序列号

API V3 Key 必须保存到 Secret 管理系统，不能直接提交仓库。

### 2.3 推荐接口

网页支付通常使用 Native 支付或 JSAPI：

```text
后端创建订单
 -> 微信返回 code_url 或支付参数
 -> 前端展示二维码/调起支付
 -> 微信回调商户 notify_url
 -> 后端使用 API V3 Key 解密回调
 -> 校验订单金额
 -> 幂等入账
```

回调地址示例：

```text
https://ai.example.com/api/payment/wechat/notify
```

### 2.4 环境变量

```env
PAYMENT_PROVIDER=wechat
WECHAT_APP_ID=wx123456
WECHAT_MCH_ID=1900000001
WECHAT_CERT_SERIAL=xxxxxxxx
WECHAT_API_V3_KEY=<32字节字符串>
WECHAT_PRIVATE_KEY_PATH=/run/secrets/wechat/apiclient_key.pem
WECHAT_NOTIFY_URL=https://ai.example.com/api/payment/wechat/notify
```

### 2.5 沙箱和测试

微信支付沙箱能力受产品类型限制，不能假设所有正式接口都有完整沙箱。建议：

1. 先使用服务商提供的测试商户。
2. 使用小额真实测试订单。
3. 限制测试用户和测试金额。
4. 验证回调重试、重复回调和退款流程。

## 3. 支付宝配置

支付宝电脑网站支付、手机网站支付和当面付的申请条件不同。

### 3.1 开放平台准备

1. 注册支付宝开放平台。
2. 创建网页/移动应用。
3. 配置应用公钥。
4. 获取支付宝公钥。
5. 完成应用签约和产品开通。
6. 配置授权回调地址和异步通知地址。

### 3.2 关键文件

- 应用私钥：只保存在服务器
- 应用公钥：上传到支付宝
- 支付宝公钥：下载后用于验签

不要把应用私钥放在 Vue 前端，也不要把私钥放在数据库普通字段中。

### 3.3 环境变量

```env
PAYMENT_PROVIDER=alipay
ALIPAY_APP_ID=2024000000000000
ALIPAY_PRIVATE_KEY_PATH=/run/secrets/alipay/app_private_key.pem
ALIPAY_PUBLIC_KEY_PATH=/run/secrets/alipay/alipay_public_key.pem
ALIPAY_NOTIFY_URL=https://ai.example.com/api/payment/alipay/notify
ALIPAY_RETURN_URL=https://ai.example.com/console/topup
ALIPAY_SIGN_TYPE=RSA2
```

### 3.4 异步通知处理

必须使用官方 SDK 验签，并检查：

- `trade_status`
- `out_trade_no`
- `trade_no`
- `total_amount`
- `app_id`
- `seller_id`

只有 `TRADE_SUCCESS` 或明确允许的交易状态才可入账。`return_url` 只能显示结果，不能作为充值依据。

## 4. AWS KMS 配置

KMS 用于加密渠道 API Key、支付私密配置或数据库字段。

### 4.1 创建 KMS Key

1. AWS Console -> KMS -> Customer managed keys。
2. 创建对称加密密钥。
3. 设置别名，例如 `alias/aidream-production`。
4. 配置 Key Policy，仅允许应用 IAM Role 使用加解密权限。

最小权限示例：

```json
{
  "Effect": "Allow",
  "Action": ["kms:Encrypt", "kms:Decrypt", "kms:GenerateDataKey"],
  "Resource": "arn:aws:kms:ap-southeast-1:123456789:key/xxxx"
}
```

不要给应用 `kms:*` 或管理员权限。

### 4.2 环境变量

```env
KMS_PROVIDER=aws
AWS_REGION=ap-southeast-1
AWS_KMS_KEY_ID=alias/aidream-production
```

优先使用 EC2/ECS/EKS IAM Role，不要配置长期 `AWS_ACCESS_KEY_ID` 和 `AWS_SECRET_ACCESS_KEY`。

### 4.3 加密策略

推荐 envelope encryption：

```text
KMS GenerateDataKey
 -> 获得明文数据密钥和密文数据密钥
 -> 本地使用 AES-256-GCM 加密 API Key
 -> 数据库保存 API Key 密文 + 数据密钥密文 + nonce
```

应用只在请求上游时短暂解密，并且不在日志中输出明文。

## 5. HashiCorp Vault 配置

Vault 适合自建或已有 DevOps 平台的团队。

### 5.1 启用 Transit

```bash
vault secrets enable transit
vault write -f transit/keys/aidream
```

### 5.2 创建最小权限策略

`aidream-policy.hcl`：

```hcl
path "transit/encrypt/aidream" {
  capabilities = ["update"]
}

path "transit/decrypt/aidream" {
  capabilities = ["update"]
}
```

```bash
vault policy write aidream-policy aidream-policy.hcl
```

使用 Kubernetes Auth、AppRole 或云 IAM 登录 Vault，不要把长期 root token 放在 `.env`。

### 5.3 环境变量

```env
KMS_PROVIDER=vault
VAULT_ADDR=https://vault.internal:8200
VAULT_ROLE=aidream-production
VAULT_TRANSIT_KEY=aidream
```

## 6. 真实模型供应商配置

### 6.1 OpenAI

准备：

- OpenAI Platform 账户
- 已验证的付款方式
- Project API Key
- 使用限制和预算告警

```env
UPSTREAM_BASE_URL=https://api.openai.com/v1
UPSTREAM_API_KEY=sk-proj-xxxx
```

建议在数据库渠道管理页配置，而不是所有渠道共用环境变量：

```text
名称：openai-primary
provider：openai
groups：Codex（推荐）,default
models：gpt-4o,gpt-4.1,gpt-5
priority：100
```

### 6.2 Anthropic

准备 Anthropic Console API Key，并记录可用模型名。

原生 Anthropic 请求需要：

```text
x-api-key: sk-ant-...
anthropic-version: 2023-06-01
content-type: application/json
```

渠道配置：

```text
provider：anthropic
base_url：https://api.anthropic.com
groups：Claude Lite
models：claude-3-5-sonnet-latest
```

不要把 Anthropic Key 伪装成 OpenAI Bearer Key 后直接发送。适配器必须根据 provider 生成正确请求头和 body。

### 6.3 Google Gemini

可使用 Google AI Studio API Key 或 Vertex AI 服务账号。两者协议不同：

- AI Studio：API Key
- Vertex AI：OAuth2 服务账号、项目 ID、区域

AI Studio 示例：

```text
provider：gemini
base_url：https://generativelanguage.googleapis.com
groups：Gemini
models：gemini-1.5-pro,gemini-1.5-flash
```

Gemini 请求结构是 `contents[].parts[]`，不能直接把 OpenAI `messages[]` 原样发送。

## 7. 密钥轮换

每类密钥都应定期轮换：

| 密钥 | 建议周期 |
|---|---:|
| JWT SECRET_KEY | 发生泄露时立即轮换 |
| 模型 API Key | 30～90 天 |
| 支付 API Key | 按供应商政策 |
| KMS/Vault 凭据 | 30～90 天 |
| 数据库密码 | 90 天 |

轮换顺序：

```text
新增新密钥 -> 部署并验证 -> 切换流量 -> 撤销旧密钥
```

不要先撤销旧密钥再部署新密钥。

## 8. 上线验收

### 支付验收

- [ ] 创建订单金额来自后端固定配置
- [ ] webhook 签名验证通过
- [ ] 重复 webhook 不重复入账
- [ ] 金额篡改被拒绝
- [ ] 退款能正确扣回余额
- [ ] 支付失败不会增加额度

### 模型验收

- [ ] OpenAI 普通请求
- [ ] OpenAI 流式请求
- [ ] Anthropic 原生请求
- [ ] Gemini 原生请求
- [ ] 上游 401/429/500 能正确处理
- [ ] 渠道失败能自动切换
- [ ] 余额不足在请求前被拒绝
- [ ] usage 和扣费日志一致

### 密钥验收

- [ ] 数据库中看不到明文 API Key
- [ ] 管理列表只显示掩码
- [ ] KMS/Vault 权限不是管理员权限
- [ ] 应用日志没有打印 Authorization
- [ ] 轮换后旧 Key 失效

## 9. 常见错误

### 支付成功但余额未增加

检查：

1. webhook 是否能从公网访问；
2. 签名 secret 是否对应当前环境；
3. 事件是否被重复事件幂等逻辑跳过；
4. 订单金额、币种和用户 ID 是否匹配；
5. 数据库事务是否回滚。

### 模型返回 401

检查：

- API Key 是否属于正确供应商；
- Base URL 是否带正确版本路径；
- Anthropic 是否使用 `x-api-key`；
- Gemini 是否使用正确的 API Key/OAuth；
- 渠道模型名是否与供应商实际模型名一致。

### KMS AccessDenied

检查：

- 应用实例使用的 IAM Role；
- KMS Key Policy；
- AWS Region；
- Key ID 或 alias 是否正确；
- 是否误用了开发账号的密钥。

### webhook 重复充值

数据库必须对支付供应商事件 ID 建立唯一索引，并在同一事务中完成：

```text
插入事件记录 -> 更新订单 -> 增加额度 -> 写充值日志
```

任何一步失败都应整体回滚。

## 10. 推荐上线顺序

```text
1. 先启用 staging 数据库
2. 配置 Redis
3. 配置 KMS/Vault
4. 配置 OpenAI/Anthropic/Gemini 测试 Key
5. 完成普通/流式模型验收
6. 配置支付沙箱
7. 验证 webhook 和幂等充值
8. 配置备份与恢复演练
9. 切换正式域名和 HTTPS
10. 更换正式模型 Key、支付 Key 和 webhook secret
11. 小范围灰度上线
12. 观察错误率、余额变更和支付对账
```

没有商户资质、云权限或供应商账户时，只能完成本地代码和沙箱验证；不要在生产环境用“模拟支付成功”替代真实 webhook，也不要用伪造模型结果代替真实供应商调用。
