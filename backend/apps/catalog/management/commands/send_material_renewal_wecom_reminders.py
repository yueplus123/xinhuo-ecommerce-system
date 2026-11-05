"""物料续费到期提醒：把快到期 / 已过期的物料汇总成一条消息，推送到企业微信群（消息推送 Webhook）。

提醒规则（按 Django TIME_ZONE 的本地日期算）：
  - 距离到期还剩 N 天，且 N 在提醒天数里（默认 7、3、1、0 天）时提醒；
  - 已经过期、还没登记续费的，每天都提醒，直到在系统里点「登记续费」；
  - 只看「启用」的物料；当天没有要提醒的就不发。

建议 crontab（每天 10:00 发一次）::

    0 10 * * * cd /var/www/xinhuo/app && PYTHONPATH=. .venv/bin/python backend/manage.py send_material_renewal_wecom_reminders

环境变量：
  WECOM_REMINDER_ENABLED=1                      # 与订阅提醒共用的总开关
  MATERIAL_WECOM_WEBHOOK_URL=https://qyapi...   # 可选：物料提醒单独发到另一个群；不填则用 WECOM_GROUP_WEBHOOK_URL
  MATERIAL_REMIND_DAYS=7,3,1,0                  # 可选：提前几天提醒
  MATERIAL_REMIND_MENTION=@all                  # 可选：@all 或手机号（逗号分隔），会另发一条文本消息来 @ 人
  STAFF_FRONTEND_BASE_URL=https://...           # 消息末尾「去续费」链接的站点地址

用法：
  --dry-run        只打印，不发送
  --test-message   发一条测试消息，验证 Webhook
  --date YYYY-MM-DD  按指定日期计算（测试用）
"""

from __future__ import annotations

import os
from datetime import date

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.dateparse import parse_date

from backend.apps.catalog.models import MaterialRenewal
from backend.apps.catalog.wecom_webhook import WecomWebhookError, post_webhook_json, send_markdown

_WEEKDAY_CN = ("周一", "周二", "周三", "周四", "周五", "周六", "周日")


def _remind_days() -> set[int]:
    raw = (os.environ.get("MATERIAL_REMIND_DAYS") or "7,3,1,0").replace("，", ",")
    out: set[int] = set()
    for part in raw.split(","):
        part = part.strip()
        if part.isdigit():
            out.add(int(part))
    return out or {7, 3, 1, 0}


def _webhook_url() -> str:
    own = (os.environ.get("MATERIAL_WECOM_WEBHOOK_URL") or "").strip()
    return own or (getattr(settings, "WECOM_GROUP_WEBHOOK_URL", None) or "").strip()


def _page_url() -> str:
    base = (getattr(settings, "STAFF_FRONTEND_BASE_URL", None) or "").strip().rstrip("/")
    return f"{base}/material-renewal" if base else ""


def _fmt_amount(obj: MaterialRenewal) -> str:
    if obj.amount is None:
        return ""
    amt = f"{obj.amount:,.2f}".rstrip("0").rstrip(".")
    cur = (obj.currency or "").upper()
    sym = {"CNY": "¥", "USD": "$", "JPY": "JP¥", "HKD": "HK$", "EUR": "€"}.get(cur)
    return f"{sym}{amt}" if sym else f"{amt} {cur}".strip()


def _line(obj: MaterialRenewal, left: int) -> str:
    if left < 0:
        when = f'<font color="warning">已过期 {-left} 天</font>'
    elif left == 0:
        when = '<font color="warning">今天到期</font>'
    else:
        when = f"还剩 {left} 天"
    d = obj.next_due_at
    parts = [f"**{obj.name}**", f"{d.month}月{d.day}日{_WEEKDAY_CN[d.weekday()]}", when]
    money = _fmt_amount(obj)
    if money:
        if obj.cycle_type == MaterialRenewal.CYCLE_MONTHLY:
            money += "/月"
        elif obj.cycle_type == MaterialRenewal.CYCLE_YEARLY:
            money += "/年"
        elif obj.cycle_days:
            money += f"/{obj.cycle_days}天"
        parts.append(money)
    text = "> " + " · ".join(parts)
    extra = " ".join(x for x in [(obj.category or "").strip(), (obj.remark or "").strip()] if x)
    if extra:
        text += f"\n> <font color=\"comment\">{extra[:80]}</font>"
    return text


def build_digest(today: date, remind_days: set[int]) -> tuple[list[tuple[MaterialRenewal, int]], list[tuple[MaterialRenewal, int]]]:
    """返回 (已过期列表, 即将到期列表)，元素为 (物料, 剩余天数)。"""
    overdue: list[tuple[MaterialRenewal, int]] = []
    upcoming: list[tuple[MaterialRenewal, int]] = []
    for obj in MaterialRenewal.objects.filter(is_active=True).order_by("next_due_at", "id"):
        left = (obj.next_due_at - today).days
        if left < 0:
            overdue.append((obj, left))
        elif left in remind_days:
            upcoming.append((obj, left))
    return overdue, upcoming


def build_markdown(today: date, overdue, upcoming, page_url: str) -> str:
    lines = [f"**物料续费提醒** <font color=\"comment\">{today.month}月{today.day}日{_WEEKDAY_CN[today.weekday()]}</font>", ""]
    if overdue:
        lines.append(f"已过期 {len(overdue)} 项（续费后请在系统里点「登记续费」）：")
        lines += [_line(o, d) for o, d in overdue]
        lines.append("")
    if upcoming:
        lines.append(f"即将到期 {len(upcoming)} 项：")
        lines += [_line(o, d) for o, d in upcoming]
        lines.append("")
    if page_url:
        lines.append(f"[去续费登记]({page_url})")
    text = "\n".join(lines).rstrip()
    raw = text.encode("utf-8")
    if len(raw) > 4000:
        text = raw[:3900].decode("utf-8", "ignore").rstrip() + "\n\n>内容过长已截断，请打开系统查看全部。"
    return text


class Command(BaseCommand):
    help = "把快到期 / 已过期的物料续费汇总后推送到企业微信群。"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="只打印，不发送。")
        parser.add_argument("--test-message", action="store_true", help="只发一条测试消息。")
        parser.add_argument("--date", dest="today", default="", help="按指定日期计算（YYYY-MM-DD），测试用。")

    def handle(self, *args, **opts):
        if not getattr(settings, "WECOM_REMINDER_ENABLED", False):
            self.stdout.write(self.style.WARNING("未开启：请设置环境变量 WECOM_REMINDER_ENABLED=1"))
            return
        url = _webhook_url()
        if not url:
            self.stdout.write(self.style.ERROR("缺少 Webhook：请设置 MATERIAL_WECOM_WEBHOOK_URL 或 WECOM_GROUP_WEBHOOK_URL"))
            return

        if opts["test_message"]:
            if opts["dry_run"]:
                self.stdout.write("[dry-run] 将发送测试消息。")
                return
            try:
                send_markdown(url, "**薪火系统 · 物料续费提醒**\n>测试消息：Webhook 配置正确，到期前会在这里提醒。")
            except WecomWebhookError as e:
                self.stdout.write(self.style.ERROR(str(e)))
                raise SystemExit(1) from e
            self.stdout.write(self.style.SUCCESS("测试消息已发送。"))
            return

        today = timezone.localdate()
        if opts["today"]:
            today = parse_date(opts["today"]) or None
            if today is None:
                self.stdout.write(self.style.ERROR("--date 格式应为 YYYY-MM-DD"))
                raise SystemExit(2)

        days = _remind_days()
        overdue, upcoming = build_digest(today, days)
        if not overdue and not upcoming:
            self.stdout.write(f"{today} 没有需要提醒的物料（提醒天数 {sorted(days, reverse=True)}），不发送。")
            return

        md = build_markdown(today, overdue, upcoming, _page_url())
        self.stdout.write(f"{today} 已过期 {len(overdue)} 项，即将到期 {len(upcoming)} 项：\n{md}")
        if opts["dry_run"]:
            self.stdout.write(self.style.WARNING("\n[dry-run] 未发送。"))
            return

        try:
            send_markdown(url, md)
            mention = (os.environ.get("MATERIAL_REMIND_MENTION") or "").strip()
            if mention:
                # 企微 markdown 消息不能 @ 人，用一条短文本消息来 @
                mobiles = [m.strip() for m in mention.replace("，", ",").split(",") if m.strip()]
                post_webhook_json(url, {"msgtype": "text", "text": {
                    "content": f"有 {len(overdue) + len(upcoming)} 项物料需要续费，请查看上一条提醒。",
                    "mentioned_mobile_list": mobiles,
                }})
        except WecomWebhookError as e:
            self.stdout.write(self.style.ERROR(f"推送失败：{e}"))
            raise SystemExit(1) from e
        self.stdout.write(self.style.SUCCESS("\n已推送到企业微信群。"))
