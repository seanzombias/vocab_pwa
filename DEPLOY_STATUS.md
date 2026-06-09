# vocab_pwa 部署状态

> 最后更新：2026-06-09

## 线上地址

| 组件 | URL | 状态 |
|------|-----|------|
| 前端 PWA | https://seanzombias.github.io/vocab_pwa/ | 已上线 |
| 后端 API | https://vocab-pwa-api.<账号>.workers.dev | **待部署 Cloudflare Worker** |
| 数据库 | Turso `vocab-pwa-seanzombias` | 已创建 |
| GitHub 仓库 | https://github.com/seanzombias/vocab_pwa | 已推送 |

---

## 已完成

- [x] GitHub Pages 前端
- [x] Turso 数据库（东京）
- [x] 静态词汇回退（`frontend/data/vocab.json`，Worker 未就绪时可用）
- [x] Cloudflare Worker 代码（`worker/`，Hono + Turso）
- [x] GitHub Actions：`.github/workflows/worker.yml`

## 待完成（Cloudflare，无需信用卡）

详见 **[docs/CLOUDFLARE_SETUP.md](docs/CLOUDFLARE_SETUP.md)**

### 1. Cloudflare 账号 + Token

1. 注册 https://dash.cloudflare.com
2. 创建 API Token（Edit Cloudflare Workers）
3. GitHub 仓库 Secrets 添加 `CLOUDFLARE_API_TOKEN`、`CLOUDFLARE_ACCOUNT_ID`

### 2. 配置 Worker Secrets

```powershell
cd worker
npx wrangler login
npx wrangler secret put TURSO_DATABASE_URL
npx wrangler secret put TURSO_AUTH_TOKEN
npx wrangler secret put VOCAB_API_TOKEN
npm run deploy
```

或使用 GitHub Actions 自动部署（需先配置 Secrets）。

### 3. 更新前端 API 地址

`wrangler deploy` 输出的 URL 填入 `frontend/config.js` 的 `API_BASE`，push 到 `main`。

### 4. 导入词汇到 Turso

```powershell
python scripts/import_vocab.py backend/data/axios_article_vocab.json `
  --api https://vocab-pwa-api.<账号>.workers.dev `
  --token <VOCAB_API_TOKEN>
```

### 5. 验证

```powershell
(Invoke-WebRequest "https://vocab-pwa-api.<账号>.workers.dev/api/health").Content
# {"status":"ok","db":"turso","db_ok":true}
```

---

## 架构

```
GitHub Pages → Cloudflare Worker → Turso
     ↑ Worker 失败时回退 frontend/data/vocab.json
```

---

## 变更日志

- 2026-06-09：Cloudflare Worker 后端（替代 Render）
- 2026-06-09：静态词汇模式 + Pages 上线
- 2026-06-09：Turso 凭证、db 健康检查
