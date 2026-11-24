# 邮件推送（QQ 邮箱 → 企业微信群）

把几个 QQ 邮箱里**符合规则的新邮件**（比如 PayPal 收款、Fanbox 通知、验证码）推送到企业微信内部群。

- 设置都在管理后台「账号与数据 → 邮件推送」（仅超级管理员）：邮箱、规则、排除规则、Webhook、观察模式。
- 收信由常驻服务 `xinhuo-mailpush`（`manage.py run_mail_push`）完成，和网站后端分开运行：邮箱连接出问题不会影响网站。
- 后台改了设置，下一轮自动生效，不用重启服务。

## 工作方式

- 每 60 秒（可改）用 IMAP 只读检查一次，按邮件 UID 判断新邮件；**不会把邮件标成已读**，也不删除、不移动邮件。
- 新加的邮箱第一次检查只记住当前位置，**不推历史邮件**。
- 规则：发件人（完整地址或 `@域名`）+ 标题关键词，同一条规则两项都填时需同时满足；多条规则满足任意一条就推。排除规则优先级最高。
- 观察模式（默认开启）：只记录"会推送"，不发群；在「推送记录」里核对后再切换正式推送。
- 推送失败会在后续几轮自动重试（最多 5 次），也可以在记录里点「重新推送」。
- 某个邮箱连续 3 次检查失败（授权码失效、网络问题），往群里发一次告警，恢复后再通知一次。
- 每个企微机器人每分钟最多 20 条，程序按 18 条/分钟排队发送。
- 记录只存发件人、标题和结果，不存正文，保留 90 天。授权码存在数据库里，接口不返回。

## 代码

| 文件 | 作用 |
|---|---|
| `backend/apps/catalog/mail_push_engine.py` | 收信、解析、规则匹配、消息格式、企微发送（不依赖 Django） |
| `backend/apps/catalog/mail_push.py` | 把引擎接到数据库（DbStore、Runner） |
| `backend/apps/catalog/management/commands/run_mail_push.py` | 常驻收信服务 |
| `backend/apps/api/mail_push_views.py` | 管理接口 `/api/mail-push/…` |
| `admin/src/views/Tools/MailPushPage.vue` | 管理后台页面 |
| `deploy/xinhuo-mailpush.service` | systemd 服务 |

## 首次部署

```bash
cd /var/www/xinhuo/app
# 1. 跑测试（用临时数据库，不碰线上数据）
PYTHONPATH=. .venv/bin/python backend/manage.py test backend.apps.api.tests.test_mail_push
# 2. 备份数据库后迁移（0085_mail_push：只新建 4 张表）
mkdir -p backups && .venv/bin/python -c "import sqlite3;s=sqlite3.connect('backend/data/backend.sqlite3');t=sqlite3.connect('backups/backend-pre-mailpush.sqlite3');s.backup(t)"
PYTHONPATH=. .venv/bin/python backend/manage.py migrate
systemctl restart xinhuo-backend
# 3. 安装收信服务（User 跟后端服务一致）
U=$(systemctl show -p User --value xinhuo-backend); U=${U:-root}
sed "s/^User=.*/User=$U/" deploy/xinhuo-mailpush.service > /etc/systemd/system/xinhuo-mailpush.service
systemctl daemon-reload && systemctl enable --now xinhuo-mailpush
# 4. 管理后台页面（GitHub Actions 打包好之后）
bash scripts/deploy_admin.sh
```

## 常用命令

```bash
systemctl status xinhuo-mailpush            # 状态
journalctl -u xinhuo-mailpush -f            # 实时日志
systemctl restart xinhuo-mailpush           # 更新代码后重启
PYTHONPATH=. .venv/bin/python backend/manage.py run_mail_push --once          # 手动检查一轮
PYTHONPATH=. .venv/bin/python backend/manage.py run_mail_push --test-message  # 测试企微群
```

**更新代码后**，除了 `systemctl restart xinhuo-backend`，也要 `systemctl restart xinhuo-mailpush`。
