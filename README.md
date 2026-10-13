# 薪火电商管理系统

前后端分离，三个独立部分：

| 目录 | 是什么 | 线上地址 | 本地开发 |
|---|---|---|---|
| `backend/` | Django **纯 API**（不含任何页面） | `/api/` | `:8001` |
| `frontend/` | **职员端**前端（Vue 3 + Element Plus） | `/` | `:5173` |
| `admin/` | **管理后台**前端（独立应用，自己的登录页，仅超级管理员） | `/admin/` | `:5174/admin/` |

其它：`deploy/` Nginx 等部署示例，`docs/` 业务部署与数据迁移文档，`scripts/` 运维脚本。

三者通过 `/api/` 通信；`frontend` 与 `admin` 互不依赖、各自登录、各自构建，改一边不影响另一边。

## 本地开发

```bash
# 1) 后端（纯 API）
python3 -m venv .venv && .venv/bin/pip install -e .
cd backend && ../.venv/bin/python manage.py migrate && ../.venv/bin/python manage.py runserver 8001

# 2) 职员端
cd frontend && pnpm install && pnpm run dev        # http://localhost:5173

# 3) 管理后台
cd admin && pnpm install && pnpm run dev           # http://localhost:5174/admin/
```

两个前端的 Vite 都会把 `/api`、`/media` 代理到 `127.0.0.1:8001`。

没有超级管理员账号时：`cd backend && python manage.py create_dev_user`（见 `backend/README.md`）。

## 生产部署

1. 将 `.env.example` 复制为 `.env`，填写真实域名和密钥。
2. 保留并备份 `backend/data/` 与 `backend/media/`。
3. 后端：`sudo bash deploy.sh --install-service`（gunicorn 监听 `127.0.0.1:8001`）。
4. 构建前端并上传：
   - `cd frontend && pnpm run build:pro`，把 `dist-pro/` 放到服务器 `frontend/dist/`
   - `cd admin && pnpm run build:fast`，把 `dist/` 放到服务器 `admin/dist/`
5. 用 `deploy/nginx-xinhuo.conf.example` 配置 Nginx：`/` → 职员端，`/admin/` → 管理后台，`/api/` → 后端。

部署脚本会在迁移前使用 SQLite 在线备份 API 将数据库保存到 `backups/`，不会删除或重建现有数据库。Docker 容器启动时不会自动迁移数据库，避免未经确认修改生产库。

Docker 部署需要先备份数据，再明确执行一次迁移：

```bash
docker compose run --rm web python manage.py migrate --noinput
docker compose up -d
```

## 已有定时命令

```bash
cd backend
../.venv/bin/python manage.py cleanup_old_payment_screenshots --days 60 --dry-run
../.venv/bin/python manage.py send_subscription_wecom_reminders --dry-run
```

首次执行清理命令必须使用 `--dry-run` 核对结果。
