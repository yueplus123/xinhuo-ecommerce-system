# 后端（Django）

与 Vue 前端配套的业务 API 与管理后台（`/backoffice/`）。

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

- 管理后台：`http://127.0.0.1:8001/backoffice/`
- Django Admin：`http://127.0.0.1:8001/django-admin/`
- API：`http://127.0.0.1:8001/api/`

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
**大厅板块、自建平台账号等**不在上述规则内的，请自行在后台删除或编辑。
