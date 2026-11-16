"""日元充值汇率：每天早上推送到企业微信群（周末也发）。

crontab（CRON_TZ=Asia/Shanghai）::

    30 8 * * * cd /var/www/xinhuo/app && PYTHONPATH=. .venv/bin/python backend/manage.py send_card_fx_wecom >> /var/log/xinhuo-card-fx.log 2>&1

环境变量（写在服务器项目根目录 .env，不要提交到 GitHub）：
  WECOM_REMINDER_ENABLED=1            总开关（和其它企微提醒共用）
  CARD_FX_WECOM_WEBHOOK_URL=https://qyapi...   汇率推送群；不填则用 WECOM_GROUP_WEBHOOK_URL
  STAFF_FRONTEND_BASE_URL=http://...  消息末尾「打开大厅查看」链接

用法：
  --dry-run          只打印，不发送
  --test-message     发一条测试消息，验证 Webhook
  --date YYYY-MM-DD  把“今天”当成这一天（测试用）
"""

from __future__ import annotations

import os

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.utils.dateparse import parse_date

from backend.apps.catalog import card_fx
from backend.apps.catalog.wecom_webhook import WecomWebhookError, send_markdown

NO_DATA_TEXT = "日元汇率还没有数据，请检查取数任务"


def _webhook_url() -> str:
    own = (os.environ.get("CARD_FX_WECOM_WEBHOOK_URL") or "").strip()
    return own or (getattr(settings, "WECOM_GROUP_WEBHOOK_URL", None) or "").strip()


def _page_url() -> str:
    base = (getattr(settings, "STAFF_FRONTEND_BASE_URL", None) or "").strip().rstrip("/")
    if not base or "localhost" in base or "127.0.0.1" in base:
        return ""
    return f"{base}/hall"


class Command(BaseCommand):
    help = "推送日元充值汇率到企业微信群"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--test-message", action="store_true")
        parser.add_argument("--date", default="")

    def handle(self, *args, **opts):
        now = timezone.localtime().strftime("%Y-%m-%d %H:%M:%S")
        today = timezone.localdate()
        if opts["date"]:
            today = parse_date(opts["date"])
            if today is None:
                raise CommandError("--date 格式应为 YYYY-MM-DD")

        if opts["test_message"]:
            content = f"**日元充值汇率**\n测试消息：Webhook 可用（{now}）"
        else:
            content = card_fx.build_wecom_markdown(today, _page_url())
        no_data = content is None
        if no_data:
            content = NO_DATA_TEXT

        if opts["dry_run"]:
            self.stdout.write(f"[{now}] [dry-run]\n{content}")
            if no_data:
                raise CommandError(NO_DATA_TEXT)
            return

        if not getattr(settings, "WECOM_REMINDER_ENABLED", False):
            self.stdout.write(f"[{now}] WECOM_REMINDER_ENABLED 未开启，不发送。内容：\n{content}")
            return
        url = _webhook_url()
        if not url:
            raise CommandError("没有配置 CARD_FX_WECOM_WEBHOOK_URL（或 WECOM_GROUP_WEBHOOK_URL）")
        try:
            send_markdown(url, content)
        except WecomWebhookError as e:
            raise CommandError(f"[{now}] 发送失败：{e}") from e
        if no_data:
            raise CommandError(f"[{now}] {NO_DATA_TEXT}（已发到群里）")
        self.stdout.write(f"[{now}] 已发送")
