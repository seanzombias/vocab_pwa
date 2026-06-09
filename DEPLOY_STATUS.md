# vocab_pwa 部署状态

> 最后更新：2026-06-09（本机自动部署脚本执行结果）

## 目标 URL

| 组件 | URL |
|------|-----|
| 前端 PWA | https://seanzombias.github.io/vocab_pwa/ |
| 后端 API | https://vocab-pwa-api.onrender.com |
| GitHub 仓库 | https://github.com/seanzombias/vocab_pwa |

---

## 已完成（本机）

- [x] Git 仓库初始化，分支 **`main`**
- [x] 初始提交：`34b5305` — Flask API、PWA 前端、Pages workflow、`backend/render.yaml`
- [x] **未提交** `backend/.env`（已被 `.gitignore` 中 `.env` 规则忽略）
- [x] **未提交** `backend/data/vocab.db`、`__pycache__/`
- [x] 本地 Git 用户（仅本仓库）：`seanzombias` / `zjy1987zjy@gmail.com`（未改 global git config）
- [x] 本地 API 自检：`GET /api/health` → 200 `{"status":"ok"}`
- [x] 已安装 **GitHub CLI**（`gh` 2.93.0，winget）
- [x] 已在仓库根目录添加 **`render.yaml`**（与 `backend/render.yaml` 相同，便于 Render Blueprint 自动发现）
- [x] 审阅 **`.github/workflows/pages.yml`**：push `main` 时上传 `frontend/` 并 deploy-pages
- [x] 审阅 **`backend/render.yaml`**：服务名 `vocab-pwa-api`，`rootDir: backend`，gunicorn，Turso 与 Token 环境变量

## 进行中

### 1. GitHub 登录与推送

**状态：** 已启动 `gh auth login` 设备码流程。

**请立即在浏览器完成：**

1. 打开 https://github.com/login/device
2. 输入一次性验证码：**`9476-FA33`**
3. 授权 GitHub CLI 访问账户 `seanzombias`

完成后在终端执行（或运行 `.\scripts\deploy_online.ps1`）：

```powershell
cd C:\Users\Administrator\Desktop\vocab_pwa
gh repo create seanzombias/vocab_pwa --public --source=. --remote=origin --push
```

若不用 `gh`，在 GitHub 网页新建空仓库 `vocab_pwa` 后：

```powershell
git remote add origin https://github.com/seanzombias/vocab_pwa.git
git push -u origin main
```

推送后确认 Actions 里 **Deploy GitHub Pages** workflow 能跑通。

---

### 2. GitHub Pages 启用

**状态：** workflow 已就绪，但需在仓库设置里启用一次。

**操作：**

1. 仓库 → **Settings** → **Pages**
2. **Build and deployment** → Source 选 **GitHub Actions**
3. 等待 workflow 成功；访问 https://seanzombias.github.io/vocab_pwa/

---

### 3. Turso 数据库

**状态：** 本机 **未安装** `turso` CLI，无法自动建库。

**操作（Dashboard，推荐）：**

1. 注册/登录 [Turso](https://turso.tech)
2. 创建数据库，名称建议：**`vocab-pwa`**
3. 在数据库页面复制：
   - **Database URL** → Render 环境变量 `TURSO_DATABASE_URL`（形如 `libsql://...`）
   - **Auth Token** → `TURSO_AUTH_TOKEN`
4. （可选）本地 CLI 安装后：

```powershell
# 安装后
turso auth login
turso db create vocab-pwa
turso db show vocab-pwa --url
turso db tokens create vocab-pwa
```

**勿将 token 提交到 Git。** 可写入本机 `backend/.env` 做联调；生产只放在 Render。

**凭证存放建议：**

- 生产：`TURSO_*` 仅 Render Dashboard → vocab-pwa-api → Environment
- 本地：`C:\Users\Administrator\Desktop\vocab_pwa\backend\.env`（已在 .gitignore）

---

### 4. Render 后端

**状态：** 本机无 `render` CLI；`https://vocab-pwa-api.onrender.com/api/health` 当前 **404**（服务未部署或未就绪）。

**方式 A — Blueprint（推荐，使用根目录 `render.yaml`）：**

1. [Render Dashboard](https://dashboard.render.com) → **New** → **Blueprint**
2. 连接 GitHub 仓库 `seanzombias/vocab_pwa`
3. 识别 `render.yaml` 后创建服务 **vocab-pwa-api**
4. 在创建/服务环境变量中**手动填入**（Blueprint 里 `sync: false` 的项）：
   - `TURSO_DATABASE_URL`
   - `TURSO_AUTH_TOKEN`
5. 保存并等待首次 deploy

**方式 B — 手动 Web Service：**

1. **New Web Service** → 同一仓库
2. **Root Directory：** `backend`
3. **Build：** `pip install -r requirements.txt`
4. **Start：** `gunicorn app:app --bind 0.0.0.0:$PORT`
5. 环境变量见下表

| 变量 | 说明 |
|------|------|
| `PYTHON_VERSION` | `3.12` |
| `ALLOWED_ORIGINS` | `https://seanzombias.github.io`（与 `render.yaml` 一致；本地调试可加逗号分隔 origin） |
| `SECRET_KEY` | Render 可自动生成或自设 |
| `VOCAB_API_TOKEN` | **API 与 PWA 鉴权用** — 部署后在 Render 复制，**手机 PWA 设置里填写同一值** |
| `TURSO_DATABASE_URL` | Turso 库 URL |
| `TURSO_AUTH_TOKEN` | Turso token |

**部署后验证：**

```powershell
curl https://vocab-pwa-api.onrender.com/api/health
# 期望: {"status":"ok"}
```

**import 脚本示例：**

```powershell
python scripts/import_vocab.py backend/data/sample_import.json --api https://vocab-pwa-api.onrender.com --token <VOCAB_API_TOKEN>
```

---

### 5. 手机 / PWA 配置

- [ ] 打开 https://seanzombias.github.io/vocab_pwa/
- [ ] 在应用设置中填入与 Render **`VOCAB_API_TOKEN`** 相同的 token
- [ ] （可选）添加到主屏幕

---

## 工具链摘要

| 工具 | 本机状态 |
|------|----------|
| `git` | 可用 |
| `gh` | 已安装，**需 `gh auth login`** |
| `turso` | 未安装 |
| `render` CLI | 未安装 |

---

## 本地开发速查

```powershell
cd C:\Users\Administrator\Desktop\vocab_pwa\backend
pip install -r requirements.txt
# .env 已存在则直接：
python app.py
```

另开终端：

```powershell
cd C:\Users\Administrator\Desktop\vocab_pwa\frontend
python -m http.server 8080
```

---

## 变更日志（部署脚本）

- 2026-06-09：初始 commit、安装 gh、添加根目录 `render.yaml`、生成本文件
