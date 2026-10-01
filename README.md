# 薪火电商管理系统

项目由 Django API/管理后台与 Vue 职员端组成。

## 目录

- `backend/`：Django 项目，配置入口为 `config.settings`
- `frontend/`：Vue 3 + Vite 前端
- `deploy/`：Nginx 等部署示例
- `docs/`：业务部署和数据迁移文档

## 本地运行后端

```bash
python3 -m venv .venv
.venv/bin/pip install -e .
cd backend
../.venv/bin/python manage.py migrate
../.venv/bin/python manage.py runserver 8001
```

## 生产部署

1. 将 `.env.example` 复制为 `.env`，填写真实域名和密钥。
2. 保留并备份 `backend/data/` 与 `backend/media/`。
3. 执行 `sudo bash deploy.sh --install-service`。
4. 使用 `deploy/nginx-xinhuo.conf.example` 配置 Nginx。

部署脚本会在迁移前使用 SQLite 在线备份 API 将数据库保存到 `backups/`，不会删除或重建现有数据库。Docker 容器启动时不会自动迁移数据库，避免未经确认修改生产库。

Docker 部署需要先备份数据，再明确执行一次迁移和静态文件收集：

```bash
docker compose run --rm web python manage.py migrate --noinput
docker compose run --rm web python manage.py collectstatic --noinput
docker compose up -d
```

## 已有定时命令

```bash
cd backend
../.venv/bin/python manage.py cleanup_old_payment_screenshots --days 60 --dry-run
../.venv/bin/python manage.py send_subscription_wecom_reminders --dry-run
```

首次执行清理命令必须使用 `--dry-run` 核对结果。
