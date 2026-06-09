# vocab_pwa

英文词汇轻量 PWA：同步每日精读的关键词汇、短语与原句，支持手机浏览与 Anki 导出。

## 架构

| 部分 | 托管 | 地址 |
| ---- | ---- | ---- |
| 前端 PWA | GitHub Pages | https://seanzombias.github.io/vocab_pwa/ |
| 后端 API | Cloudflare Workers | https://vocab-pwa-api.\<账号\>.workers.dev |
| 数据库 | Turso | 生产环境 |

Worker 部署见 [docs/CLOUDFLARE_SETUP.md](docs/CLOUDFLARE_SETUP.md)。本机仍可用 Flask `backend/` 开发。

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
python scripts/import_vocab.py backend/data/sample_import.json --api https://vocab-pwa-api.<账号>.workers.dev --token YOUR_TOKEN
```

## 部署

1. 推送 Public 仓库到 `github.com/seanzombias/vocab_pwa`
2. GitHub Pages：`.github/workflows/pages.yml`
3. Cloudflare Worker：见 [docs/CLOUDFLARE_SETUP.md](docs/CLOUDFLARE_SETUP.md)
4. 配置 Turso 环境变量并 `import_vocab.py` 导入词汇
