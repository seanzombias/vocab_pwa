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

### 自动抓取 Axios 新闻

从 Axios RSS 抓取文章，按主题过滤（世界杯 / LLM / 科技），排除伊朗战争、美国中期选举等话题，并避免重复导入。

```bash
# 预览将抓取的文章
python scripts/fetch_axios_news.py --dry-run

# 抓取并保存到 backend/data/axios_articles/
python scripts/fetch_axios_news.py --max-items 5

# 抓取并导入词汇（本地 SQLite）
python scripts/fetch_axios_news.py --max-items 5 --import --local

# 抓取并导入到线上 API（在 backend/.env 设置 OPENROUTER_API_KEY，使用免费模型）
python scripts/fetch_axios_news.py --max-items 5 --import --api https://vocab-pwa-api.<账号>.workers.dev --token YOUR_TOKEN
```

主题与排除词可在 `backend/data/axios_news_config.json` 中调整。已抓取 URL 记录在 `backend/data/axios_fetched_state.json`，重复运行不会重复抓取同一篇文章。

词汇提取默认使用 [OpenRouter](https://openrouter.ai) 免费模型（`openrouter/free`，自动选用可用免费模型）。在 [OpenRouter Keys](https://openrouter.ai/keys) 创建 API Key 后写入 `backend/.env`：

```bash
OPENROUTER_API_KEY=sk-or-v1-...
OPENROUTER_MODEL=openrouter/free
```

也可指定其他免费模型，例如 `google/gemma-2-9b-it:free`、`meta-llama/llama-3.3-70b-instruct:free`。免费账号约 50 次/天，建议 `--max-items` 控制在 5 以内。

## 部署

1. 推送 Public 仓库到 `github.com/seanzombias/vocab_pwa`
2. GitHub Pages：`.github/workflows/pages.yml`
3. Cloudflare Worker：见 [docs/CLOUDFLARE_SETUP.md](docs/CLOUDFLARE_SETUP.md)
4. 配置 Turso 环境变量并 `import_vocab.py` 导入词汇
