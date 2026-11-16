"""日元充值汇率：从公开汇率接口取「1 美元 = 多少日元 / 人民币」，按汇率日期存一条。

数据源按顺序尝试（见 backend/apps/catalog/card_fx.py 的 SOURCES）：
frankfurter → er-api → currency-api，第一个成功的就用。全部失败：不动数据库，退出码非 0。

crontab（CRON_TZ=Asia/Shanghai，推送前取两次）::

    30 23 * * * cd /var/www/xinhuo/app && PYTHONPATH=. .venv/bin/python backend/manage.py fetch_card_fx_rate >> /var/log/xinhuo-card-fx.log 2>&1
    0 8 * * *   cd /var/www/xinhuo/app && PYTHONPATH=. .venv/bin/python backend/manage.py fetch_card_fx_rate >> /var/log/xinhuo-card-fx.log 2>&1

用法：
  --dry-run          只取数、打印，不写数据库
  --test             逐个测试每个数据源能不能连上（不写数据库）
  --source NAME      只用某一个数据源
"""

from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from backend.apps.catalog import card_fx


class Command(BaseCommand):
    help = "取日元充值汇率（USD/JPY、USD/CNY）并保存"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--test", action="store_true")
        parser.add_argument("--source", default="")

    def handle(self, *args, **opts):
        now = timezone.localtime().strftime("%Y-%m-%d %H:%M:%S")
        if opts["test"]:
            ok = 0
            for name, fn in card_fx.SOURCES.items():
                try:
                    q = card_fx.validate(fn())
                    ok += 1
                    self.stdout.write(f"[OK]   {name}: 日期 {q.rate_date}  USD/JPY {q.usd_jpy}  USD/CNY {q.usd_cny}")
                except card_fx.CardFxError as e:
                    self.stdout.write(f"[FAIL] {name}: {e}")
            self.stdout.write(f"{ok}/{len(card_fx.SOURCES)} 个数据源可用")
            if not ok:
                raise CommandError("没有一个数据源能连上")
            return

        try:
            q, errors = card_fx.fetch_quote(opts["source"] or None)
        except card_fx.CardFxError as e:
            raise CommandError(f"[{now}] 取数失败，数据库未改动：{e}") from e
        for err in errors:
            self.stdout.write(f"[{now}] 跳过 {err}")
        info = f"来源 {q.source}  日期 {q.rate_date}  USD/JPY {q.usd_jpy}  USD/CNY {q.usd_cny}"
        if opts["dry_run"]:
            self.stdout.write(f"[{now}] [dry-run] {info}")
            return
        _, created = card_fx.save_quote(q)
        self.stdout.write(f"[{now}] {'新增' if created else '更新'} {info}")
