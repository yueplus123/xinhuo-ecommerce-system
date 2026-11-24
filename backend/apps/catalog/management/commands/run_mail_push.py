"""邮件推送收信服务：QQ 邮箱里符合规则的新邮件 → 企业微信群。

常驻运行，由 systemd 服务 xinhuo-mailpush 管理（deploy/xinhuo-mailpush.service）。
邮箱、规则、Webhook、观察模式都在管理后台「邮件推送」页设置，改完下一轮自动生效，不用重启。

用法：
  PYTHONPATH=. .venv/bin/python backend/manage.py run_mail_push                 常驻运行
  PYTHONPATH=. .venv/bin/python backend/manage.py run_mail_push --once          只检查一轮
  PYTHONPATH=. .venv/bin/python backend/manage.py run_mail_push --test-message  发一条测试消息到群里
"""

from __future__ import annotations

import logging
import sys
import time

from django.core.management.base import BaseCommand, CommandError
from django.db import close_old_connections
from django.utils import timezone

from backend.apps.catalog import mail_push
from backend.apps.catalog import mail_push_engine as eng
from backend.apps.catalog.models import MailPushAccount, MailPushSettings

TICK_SECONDS = 5


class Command(BaseCommand):
    help = "邮件推送收信服务（QQ 邮箱 → 企业微信群），常驻运行"

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true", help="只检查一轮就退出")
        parser.add_argument("--test-message", action="store_true", help="发一条测试消息到企微群")

    def handle(self, *args, **opts):
        log = eng.log
        if not log.handlers:
            h = logging.StreamHandler(sys.stdout)
            h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s", "%m-%d %H:%M:%S"))
            log.addHandler(h)
            log.setLevel(logging.INFO)
            log.propagate = False

        if opts["test_message"]:
            s = MailPushSettings.load()
            if not s.webhook_url:
                raise CommandError("还没有在管理后台「邮件推送 → 推送设置」里填写 Webhook")
            eng.WeComSender(s.webhook_url).send_markdown("**【邮件推送】测试消息**\n> 收信服务可以正常发消息到这个群。")
            self.stdout.write("测试消息已发送")
            return

        runner = mail_push.Runner()
        if opts["once"]:
            runner.run_round()
            return

        log.info("邮件推送收信服务已启动")
        last_start = None
        last_cleanup_day = None
        while True:
            close_old_connections()
            try:
                s = MailPushSettings.load()
                now = timezone.now()
                MailPushSettings.objects.filter(pk=s.pk).update(worker_heartbeat_at=now)

                requested = bool(s.check_requested_at and (last_start is None or s.check_requested_at > last_start))
                due = last_start is None or (now - last_start).total_seconds() >= max(30, s.poll_interval)
                if due or requested:
                    last_start = now
                    if MailPushAccount.objects.filter(enabled=True).exists():
                        runner.run_round()

                today = timezone.localdate()
                if last_cleanup_day != today:
                    last_cleanup_day = today
                    n = mail_push.cleanup_old_records()
                    if n:
                        log.info("清理 %d 天前的推送记录 %d 条", mail_push.KEEP_DAYS, n)
            except Exception as e:  # 单轮出错不退出，下一轮继续
                log.exception("收信服务出错：%s", e)
            time.sleep(TICK_SECONDS)
