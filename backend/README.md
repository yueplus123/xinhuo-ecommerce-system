# 后端（Django）

纯 API 服务：为职员端（`frontend/`）和管理后台（`admin/`）提供接口，**不含任何页面**。

## 运行

```bash
cd backend
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver 8001
```

### 本地登录账号（可选）

若还没有用户，或 `admin` 密码不对，可一键创建或重置（默认密码 `changeme`，也可用环境变量 `BACKEND_DEV_PASSWORD` 或 `--password`）：

```bash
cd backend
python manage.py create_dev_user
python manage.py create_dev_user --username admin --reset --password 你的新密码
```

## 入口

- API：`http://127.0.0.1:8001/api/`（登录：`POST /api/auth/token/`，刷新：`/api/auth/token/refresh/`）
- 页面都在前端：职员端 `frontend/`，管理后台 `admin/`（线上 `/admin/`）。后端本身没有页面，访问 `/` 得到 404 属正常。

接口分区：职员端 `views.py`；记账 `ledger_views.py`；管理后台 `manage_*.py`、`admin_catalog_views.py`；机器人 / 外部系统 `/api/external/…`（API Key 鉴权）。

## 数据库

默认 SQLite：`backend/data/backend.sqlite3`（环境变量见项目根目录 `.env.example`）。

## 清除演示 / 假数据

若曾运行过 `seed_demo_data`、`seed_platform_channel_tags`，可先预览再清空：

```bash
cd backend
python manage.py clear_demo_data --dry-run
python manage.py clear_demo_data
```

默认会同时删除 `example.com/tutorial` 的演示支付教程；若要保留请加 `--keep-example-tutorials`。  
**大厅板块、自建平台账号等**不在上述规则内的，请自行在管理后台（`/admin/`）删除或编辑。
