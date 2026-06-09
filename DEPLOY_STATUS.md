# vocab_pwa 部署状态

> 最后更新：2026-06-09

## 线上地址

| 组件 | URL | 状态 |
|------|-----|------|
| 前端 PWA | https://seanzombias.github.io/vocab_pwa/ | 已上线 |
| 后端 API | https://vocab-pwa-api.onrender.com | **待部署 Render** |
| GitHub 仓库 | https://github.com/seanzombias/vocab_pwa | 已推送 |

---

## 已完成

- [x] GitHub Public 仓库 + `main` 推送
- [x] GitHub Pages（workflow 部署成功）
- [x] Turso 数据库已创建：`vocab-pwa-seanzombias`（东京区域）
- [x] Turso 凭证已写入本机 `backend/.env`（未提交 Git）
- [x] `db.py` 支持 `libsql://` → `https://` 自动转换
- [x] `/api/health` 返回 `db` / `db_ok` 状态

## 待完成（需你在 Render Dashboard 操作）

### 1. 部署 Render 服务 `vocab-pwa-api`

1. 打开 https://dashboard.render.com → **New → Blueprint**
2. 连接仓库 `seanzombias/vocab_pwa`
3. 确认识别根目录 `render.yaml`，服务名 **vocab-pwa-api**
4. 填入环境变量（详见 [docs/RENDER_SETUP.md](docs/RENDER_SETUP.md)）：

| 变量 | 值 |
|------|-----|
| `TURSO_DATABASE_URL` | `libsql://vocab-pwa-seanzombias.aws-ap-northeast-1.turso.io` |
| `TURSO_AUTH_TOKEN` | Turso Dashboard 中的 token |
| `ALLOWED_ORIGINS` | `https://seanzombias.github.io` |
| `VOCAB_API_TOKEN` | 自设或 Render 自动生成 |
| `SECRET_KEY` | 自设或 Render 自动生成 |

5. 等待 Deploy 成功

### 2. 验证 API

```powershell
(Invoke-WebRequest https://vocab-pwa-api.onrender.com/api/health).Content
# 期望: {"status":"ok","db":"turso","db_ok":true}
```

### 3. 导入 Axios 词汇（35 条）

```powershell
cd C:\Users\Administrator\Desktop\vocab_pwa
python scripts/import_vocab.py backend/data/axios_article_vocab.json `
  --api https://vocab-pwa-api.onrender.com --token <VOCAB_API_TOKEN>
```

### 4. 手机 PWA

1. 打开 https://seanzombias.github.io/vocab_pwa/
2. 「添加」页填入与 Render 相同的 **VOCAB_API_TOKEN**
3. 添加到主屏幕

---

## 本机说明

- **Turso 直连**：本机访问东京 Turso 可能超时；属网络问题，**Render 上通常正常**。
- **本地开发**：清空 `backend/.env` 中 `TURSO_*` 即用 SQLite；或只用 `http://localhost:8765` + 本地库。
- **安全**：Turso Token 曾在聊天中出现，**部署后请轮换 Token** 并更新 Render 环境变量。

---

## 变更日志

- 2026-06-09：GitHub + Pages 上线；Turso 凭证配置；Render 待部署
- 2026-06-09：db 健康检查、Turso URL 规范化
