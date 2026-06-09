# Render 环境变量配置（vocab-pwa-api）

在 [Render Dashboard](https://dashboard.render.com) → **vocab-pwa-api** → **Environment** 添加：

| Key | Value |
|-----|-------|
| `PYTHON_VERSION` | `3.12` |
| `ALLOWED_ORIGINS` | `https://seanzombias.github.io` |
| `TURSO_DATABASE_URL` | `libsql://vocab-pwa-seanzombias.aws-ap-northeast-1.turso.io` |
| `TURSO_AUTH_TOKEN` | （Turso Dashboard → Database → Create Token → 粘贴，勿提交 Git） |
| `VOCAB_API_TOKEN` | 随机长字符串（Render 可自动生成；**手机 PWA「添加」页填同一值**） |
| `SECRET_KEY` | 随机字符串（Render 可自动生成） |

**部署方式：** Dashboard → **New → Blueprint** → 连接 `seanzombias/vocab_pwa` → 识别根目录 `render.yaml`。

部署成功后验证：

```powershell
Invoke-WebRequest https://vocab-pwa-api.onrender.com/api/health
# 期望: {"status":"ok","db":"turso","db_ok":true}
```

导入词汇到 Turso（经 Render API）：

```powershell
cd C:\Users\Administrator\Desktop\vocab_pwa
$token = "你的VOCAB_API_TOKEN"
python scripts/import_vocab.py backend/data/axios_article_vocab.json --api https://vocab-pwa-api.onrender.com --token $token
python scripts/import_vocab.py backend/data/sample_import.json --api https://vocab-pwa-api.onrender.com --token $token
```

## 安全提醒

Turso Token 曾在聊天中明文出现，**部署完成后请在 Turso Dashboard 撤销旧 Token 并生成新 Token**，再更新 Render 环境变量。

## 本地开发说明

本机若无法直连 Turso（东京区域可能超时），本地开发请**清空** `backend/.env` 中的 `TURSO_*`，使用 SQLite `backend/data/vocab.db`。生产环境仅 Render 连接 Turso。
