# Cloudflare Workers 部署指南

后端 API 运行在 Cloudflare Workers，连接 Turso 数据库。无需 Render、无需信用卡。

## 架构

```
GitHub Pages (前端)  →  Cloudflare Worker (API)  →  Turso
```

Worker 地址示例：`https://vocab-pwa-api.<你的账号>.workers.dev`

---

## 1. 准备 Cloudflare 账号

1. 注册 https://dash.cloudflare.com （免费）
2. 记下 **Account ID**：Dashboard 右侧 Overview → Account ID

## 2. 创建 API Token

1. My Profile → API Tokens → Create Token
2. 使用模板 **Edit Cloudflare Workers**
3. 保存 Token（只显示一次）

## 3. 本地部署（首次）

```powershell
cd C:\Users\Administrator\Desktop\vocab_pwa\worker
npm install

# 复制并填写 Turso 凭证（与 backend/.env 相同）
copy .dev.vars.example .dev.vars
# 编辑 .dev.vars：TURSO_AUTH_TOKEN、VOCAB_API_TOKEN

# 登录 Cloudflare（浏览器授权）
npx wrangler login

# 上传 secrets（生产环境）
npx wrangler secret put TURSO_DATABASE_URL
# 输入: libsql://vocab-pwa-seanzombias.aws-ap-northeast-1.turso.io

npx wrangler secret put TURSO_AUTH_TOKEN
npx wrangler secret put VOCAB_API_TOKEN

# 部署
npm run deploy
```

部署成功后终端会显示 URL，例如：

```
https://vocab-pwa-api.seanzombias.workers.dev
```

## 4. 更新前端 API 地址

若 Worker URL 与默认不同，修改 `frontend/config.js` 中的 `API_BASE` 生产地址，然后 push 到 GitHub。

## 5. 导入词汇到 Turso

```powershell
cd C:\Users\Administrator\Desktop\vocab_pwa
python scripts/import_vocab.py backend/data/axios_article_vocab.json `
  --api https://vocab-pwa-api.seanzombias.workers.dev `
  --token <你的 VOCAB_API_TOKEN>
```

## 6. 验证

```powershell
(Invoke-WebRequest "https://vocab-pwa-api.seanzombias.workers.dev/api/health").Content
# 期望: {"status":"ok","db":"turso","db_ok":true}

(Invoke-WebRequest "https://vocab-pwa-api.seanzombias.workers.dev/api/vocab").Content
# 期望: {"items":[...],"count":35}
```

浏览器打开 https://seanzombias.github.io/vocab_pwa/ ，应显示 Turso 中的词汇。

---

## GitHub Actions 自动部署（可选）

在 GitHub 仓库 Settings → Secrets 添加：

| Secret | 说明 |
|--------|------|
| `CLOUDFLARE_API_TOKEN` | 上一步创建的 Token |
| `CLOUDFLARE_ACCOUNT_ID` | Cloudflare Account ID |

推送 `worker/` 变更到 `main` 会自动部署（见 `.github/workflows/worker.yml`）。

---

## 本地调试 Worker

```powershell
cd worker
copy .dev.vars.example .dev.vars
# 填好 .dev.vars
npm run dev
# 本地 API: http://localhost:8787
```

---

## Secrets 说明

| 变量 | 必填 | 说明 |
|------|------|------|
| `TURSO_DATABASE_URL` | 是 | `libsql://...` 或 `https://...` |
| `TURSO_AUTH_TOKEN` | 是 | Turso Dashboard → Database → Create Token |
| `VOCAB_API_TOKEN` | 是 | 自设，写操作 Bearer 鉴权 |
| `ALLOWED_ORIGINS` | 否 | 已在 `wrangler.toml` 配置 CORS |

---

## 与 Render 对比

| | Cloudflare Workers | Render |
|--|-------------------|--------|
| 免费档 | ✅ 无需信用卡 | ❌ 需绑卡 |
| 冷启动 | 无（边缘即时） | 免费档会休眠 |
| Turso | ✅ HTTP 连接 | ✅ |

Flask `backend/` 仍可用于本机开发（`python app.py`），生产推荐 Worker。
