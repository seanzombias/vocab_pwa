# vocab_pwa

英文词汇轻量 PWA：同步每日精读的关键词汇、短语与原句，支持手机浏览与 Anki 导出。

## 架构

| 部分 | 托管 | 地址 |
| ---- | ---- | ---- |
| 前端 PWA | GitHub Pages | https://seanzombias.github.io/vocab_pwa/ |
| 后端 API | Render `vocab-pwa-api` | https://vocab-pwa-api.onrender.com |
| 数据库 | Turso | 生产环境 |

详细方案见 [PLAN.md](PLAN.md)。

## 本地开发

### 后端

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
python app.py
```

默认 API：`http://localhost:8765`

### 前端

```bash
cd frontend
python -m http.server 8080
```

浏览器打开 `http://localhost:8080`，前端会自动连本地 API。

### 批量导入

```bash
python scripts/import_vocab.py backend/data/sample_import.json --local
python scripts/import_vocab.py backend/data/sample_import.json --api https://vocab-pwa-api.onrender.com --token YOUR_TOKEN
```

## 部署

1. 推送 Public 仓库到 `github.com/seanzombias/vocab_pwa`
2. GitHub Pages 使用 `.github/workflows/pages.yml`
3. Render 连接同一仓库，Root Directory 设为 `backend`，服务名 `vocab-pwa-api`
4. 在 Render 配置 `TURSO_DATABASE_URL` 与 `TURSO_AUTH_TOKEN`
