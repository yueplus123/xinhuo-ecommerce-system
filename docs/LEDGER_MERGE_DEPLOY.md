# 记账并入薪火（单库单进程）— 安全部署步骤

目标：记账数据进 `backend.sqlite3`，API 走 Django `/api/ledger/*`，验证后可 `systemctl stop ledger-app`。

**绝不覆盖：** `backend/data/backend.sqlite3`（导入前自动备份）、`/opt/ledger-app/server/data/store.json`（导入命令会先复制备份）。

---

## 第 1 步：服务器备份（SSH）

```bash
cd /var/www/xinhuo/app
mkdir -p backups
cp -a backend/data/backend.sqlite3 backups/backend-sqlite-pre-ledger-merge-$(date +%Y%m%d-%H%M).sqlite3
cp -a /opt/ledger-app/server/data/store.json backups/store-json-pre-ledger-merge-$(date +%Y%m%d-%H%M).json
```

## 第 2 步：本地上传后端框架（scp，不含 data/media/.env）

上传：`backend/apps`、`backend/config`、`backend/manage.py` 等，**不要**上传 `backend/data/`、`backend/media/`、`.env`。

## 第 3 步：迁移 + 试运行导入（服务器）

```bash
cd /var/www/xinhuo/app
export PYTHONPATH=/var/www/xinhuo/app

/var/www/xinhuo/app/.venv/bin/python backend/manage.py migrate catalog

# 仅统计，不写入
/var/www/xinhuo/app/.venv/bin/python backend/manage.py import_ledger_store \
  --file /opt/ledger-app/server/data/store.json --dry-run
```

确认 `store.json` 条数与预期后，正式导入：

```bash
/var/www/xinhuo/app/.venv/bin/python backend/manage.py import_ledger_store \
  --file /opt/ledger-app/server/data/store.json \
  --backup-db
```

## 第 4 步：核对导入结果

```bash
/var/www/xinhuo/app/.venv/bin/python backend/manage.py shell -c "
from backend.apps.catalog.ledger_utils import import_counts
print(import_counts())
"
```

应与 `store.json` 中 businesses / ledger / usdt / wallet 数量一致。

## 第 5 步：上传新前端 dist + 重启 Gunicorn

```bash
# 本机 npm run build 后 scp frontend/dist/*
systemctl restart <你的 gunicorn 服务名>
```

## 第 6 步：浏览器验证（CEO 登录）

- 打开记账系统，数据大屏、记账填写、USDT、钱包均可读写。
- F12 → Network：请求应为 `/api/ledger/...`，且带 `Authorization: Bearer`。

## 第 7 步：确认无误后关闭 Node 记账（可选）

```bash
systemctl stop ledger-app
systemctl disable ledger-app
```

保留 `/opt/ledger-app/server/data/store.json` 备份，勿删。

Nginx 中 `/ledger-api/` 反代可保留或删除，不再必需。

---

## 回滚

1. 恢复数据库备份：`cp backups/backend-sqlite-pre-ledger-merge-*.sqlite3 backend/data/backend.sqlite3`
2. 恢复旧 `frontend/dist` 备份
3. `systemctl start ledger-app`
4. 恢复 Nginx 使用 `/ledger-api/`（若已删）
