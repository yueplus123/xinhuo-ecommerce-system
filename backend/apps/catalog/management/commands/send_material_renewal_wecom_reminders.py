"""物料续费到期提醒：推送到企业微信内部群（群机器人 / 消息推送 Webhook）。

两次固定推送（只看「启用」的物料，按 Django TIME_ZONE=Asia/Shanghai 的日期算）：
  --due tomorrow   到期前一天晚上 22:00：明天到期的物料
  --due today      到期当天下午 15:00：今天到期的物料
当天没有要提醒的就不发。

crontab（服务器上 crontab -e）::

    CRON_TZ=Asia/Shanghai
    0 15 * * * cd /var/www/xinhuo/app && PYTHONPATH=. .venv/bin/python backend/manage.py send_material_renewal_wecom_reminders --due today >> /var/log/xinhuo-material-remind.log 2>&1
    0 22 * * * cd /var/www/xinhuo/app && PYTHONPATH=. .venv/bin/python backend/manage.py send_material_renewal_wecom_reminders --due tomorrow >> /var/log/xinhuo-material-remind.log 2>&1

环境变量（写在项目根目录 .env，不要提交到 GitHub）：
  WECOM_REMINDER_ENABLED=1                      # 总开关（和订阅提醒共用）
  MATERIAL_WECOM_WEBHOOK_URL=https://qyapi...   # 物料提醒群的 Webhook；不填则用 WECOM_GROUP_WEBHOOK_URL
  MATERIAL_REMIND_MENTION=@all                  # 可选：另发一条文本消息 @ 人（@all 或手机号，逗号分隔）
  STAFF_FRONTEND_BASE_URL=http://...            # 消息末尾「去续费登记」链接用的职员端地址

用法：
  --due today|tomorrow   提醒哪一天到期的（必填，除非 --test-message）
  --dry-run              只打印，不发送
  --test-message         发一条测试消息，验证 Webhook
  --date YYYY-MM-DD      把“今天”当成这一天来算（测试用）
"""

from __future__ import annotations

import os
from datetime import date, timedelta

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.utils.dateparse import parse_date

from backend.apps.catalog.models import MaterialRenewal
from backend.apps.catalog.wecom_webhook import WecomWebhookError, post_webhook_json, send_markdown

_WEEKDAY_CN = ("周一", "周二", "周三", "周四", "周五", "周六", "周日")
_CUR_SYMBOL = {"CNY": "¥", "USD": "$", "JPY": "JP¥", "HKD": "HK$", "EUR": "€"}


def _webhook_url() -> str:
    own = (os.environ.get("MATERIAL_WECOM_WEBHOOK_URL") or "").strip()
    return own or (getattr(settings, "WECOM_GROUP_WEBHOOK_URL", None) or "").strip()


def _page_url() -> str:
    base = (getattr(settings, "STAFF_FRONTEND_BASE_URL", None) or "").strip().rstrip("/")
    if not base or "localhost" in base or "127.0.0.1" in base:
        return ""
    return f"{base}/material-renewal"


def _day_cn(d: date) -> str:
    return f"{d.month}月{d.day}日 {_WEEKDAY_CN[d.weekday()]}"


def _money(obj: MaterialRenewal) -> str:
    if obj.amount is None:
        return ""
    amt = f"{obj.amount:,.2f}".rstrip("0").rstrip(".")
    cur = (obj.currency or "").upper()
    text = f"{_CUR_SYMBOL[cur]}{amt}" if cur in _CUR_SYMBOL else f"{amt} {cur}".strip()
    if obj.cycle_type == MaterialRenewal.CYCLE_MONTHLY:
        return text + "/月"
    if obj.cycle_type == MaterialRenewal.CYCLE_YEARLY:
        return text + "/年"
    if obj.cycle_days:
        return text + f"/{obj.cycle_days}天"
    return text


def _item_lines(i: int, obj: MaterialRenewal) -> list[str]:
    head = f"> {i}. **{obj.name}**"
    meta = [x for x in ((obj.category or "").strip(), _money(obj)) if x]
    if meta:
        head += "　" + " · ".join(meta)
    lines = [head]
    remark = (obj.remark or "").strip().replace("\n", " ")
    if remark:
        lines.append(f'> <font color="comment">　　备注：{remark[:60]}</font>')
    return lines


def due_items(target: date) -> list[MaterialRenewal]:
    return list(MaterialRenewal.objects.filter(is_active=True, next_due_at=target).order_by("category", "name", "id"))


def build_markdown(mode: str, today: date, items: list[MaterialRenewal], page_url: str) -> str:
    """mode: 'tomorrow'（前一天 22:00）/ 'today'（当天 15:00）。"""
    if mode == "tomorrow":
        target = today + timedelta(days=1)
        lines = [
            "**⏰ 物料明天到期 · 请提前续费**",
            f'<font color="comment">到期日：{_day_cn(target)}</font>',
            "",
            f'明天有 <font color="warning">{len(items)} 项</font>物料到期：',
        ]
        tail = "请今晚或明天上午安排续费，续费后在系统里点「登记续费」。"
    else:
        target = today
        lines = [
            '**🔴 物料今天到期 · <font color="warning">请尽快续费</font>**',
            f'<font color="comment">到期日：{_day_cn(target)}（今天）</font>',
            "",
            f'今天有 <font color="warning">{len(items)} 项</font>物料到期：',
        ]
        tail = "今天下班前务必续费，避免停用；续费后在系统里点「登记续费」，下次到期日会自动顺延。"
    for i, obj in enumerate(items, 1):
        lines += _item_lines(i, obj)
    lines += ["", tail]
    if page_url:
        lines.append(f"[👉 打开物料续费提醒]({page_url})")
    text = "\n".join(lines)
    raw = text.encode("utf-8")
    if len(raw) > 4000:  # 企业微信 markdown 上限 4096 字节
        text = raw[:3850].decode("utf-8", "ignore").rstrip() + "\n\n> 内容太多已截断，请打开系统查看全部。"
    return text


class Command(BaseCommand):
    help = "物料续费到期提醒：--due tomorrow（前一天 22:00）/ --due today（当天 15:00），推送到企业微信群。"

    def add_arguments(self, parser):
        parser.add_argument("--due", choices=("today", "tomorrow"), help="提醒今天到期的，还是明天到期的。")
        parser.add_argument("--dry-run", action="store_true", help="只打印，不发送。")
        parser.add_argument("--test-message", action="store_true", help="只发一条测试消息。")
        parser.add_argument("--date", dest="today", default="", help="把今天当成指定日期（YYYY-MM-DD），测试用。")

    def handle(self, *args, **opts):
        if not getattr(settings, "WECOM_REMINDER_ENABLED", False):
            self.stdout.write(self.style.WARNING("未开启：请在 .env 设置 WECOM_REMINDER_ENABLED=1"))
            return
        url = _webhook_url()
        if not url:
            raise CommandError("缺少 Webhook：请在 .env 设置 MATERIAL_WECOM_WEBHOOK_URL")

        if opts["test_message"]:
            md = "**✅ 物料续费提醒 · 测试消息**\n> Webhook 配置正确。\n> 到期前一天 22:00、到期当天 15:00 会在这里提醒。"
            if opts["dry_run"]:
                self.stdout.write(f"[dry-run] 将发送：\n{md}")
                return
            try:
                send_markdown(url, md)
            except WecomWebhookError as e:
                raise CommandError(f"发送失败：{e}") from e
            self.stdout.write(self.style.SUCCESS("测试消息已发送，去群里看看。"))
            return

        mode = opts.get("due")
        if not mode:
            raise CommandError("请加上 --due today 或 --due tomorrow")
        today = timezone.localdate()
        if opts["today"]:
            today = parse_date(opts["today"])
            if today is None:
                raise CommandError("--date 格式应为 YYYY-MM-DD")

        target = today + timedelta(days=1) if mode == "tomorrow" else today
        items = due_items(target)
        stamp = timezone.localtime().strftime("%Y-%m-%d %H:%M")
        if not items:
            self.stdout.write(f"[{stamp}] {target} 没有到期的物料，不发送。")
            return

        md = build_markdown(mode, today, items, _page_url())
        self.stdout.write(f"[{stamp}] {target} 到期 {len(items)} 项：\n{md}")
        if opts["dry_run"]:
            self.stdout.write(self.style.WARNING("[dry-run] 未发送。"))
            return
        try:
            send_markdown(url, md)
            mention = (os.environ.get("MATERIAL_REMIND_MENTION") or "").strip()
            if mention:
                # markdown 消息不能 @ 人，另发一条短文本来 @
                mobiles = [m.strip() for m in mention.replace("，", ",").split(",") if m.strip()]
                word = "明天" if mode == "tomorrow" else "今天"
                post_webhook_json(url, {"msgtype": "text", "text": {
                    "content": f"{word}有 {len(items)} 项物料到期，请看上一条提醒。",
                    "mentioned_mobile_list": mobiles,
                }})
        except WecomWebhookError as e:
            raise CommandError(f"推送失败：{e}") from e
        self.stdout.write(self.style.SUCCESS("已推送到企业微信群。"))
