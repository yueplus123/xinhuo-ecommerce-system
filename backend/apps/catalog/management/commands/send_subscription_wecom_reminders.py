"""将「当天到期」的订阅提醒按职员汇总后推送到企业微信内部群（消息推送 Webhook）。

规则：
  - 仅 `next_reminder_at` 等于汇总日（按 Django `TIME_ZONE`，默认 Asia/Shanghai 的本地日历日）的记录；
  - 同一职员的多条提醒合并为一条 markdown；无当日记录的职员不推送；
  - 消息末尾附带职员端「订阅到期提醒」页链接（需配置环境变量）；
  - 同一职员同一自然日仅发送一次（见 `SubscriptionReminderWecomDailyDigest`），可用 `--force` 重发。

建议 crontab（每天 15:00，服务器时区建议设为 Asia/Shanghai 或与业务一致）::

    0 15 * * * cd /path/to/repo && PYTHONPATH=. .venv/bin/python backend/manage.py send_subscription_wecom_reminders

环境变量：
  WECOM_REMINDER_ENABLED=1
  WECOM_GROUP_WEBHOOK_URL=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=...
  STAFF_FRONTEND_SUBSCRIPTION_REMINDERS_URL=...  # 完整 URL，推荐
  # 或仅配基址（将自动拼接 /subscription-reminders）：
  # STAFF_FRONTEND_BASE_URL=https://staff.example.com

官方文档：https://developer.work.weixin.qq.com/document/path/91770
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.dateparse import parse_date

from backend.apps.catalog.models import (
    SubscriptionReminder,
    SubscriptionReminderWecomDailyDigest,
)
from backend.apps.catalog.wecom_webhook import WecomWebhookError, send_markdown

_WEEKDAY_CN = ("星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日")


def _staff_subscription_reminders_url() -> str:
    u = (getattr(settings, "STAFF_FRONTEND_SUBSCRIPTION_REMINDERS_URL", None) or "").strip()
    return u.rstrip("/") if u else ""


def _user_display_name(user) -> str:
    fn = (user.get_full_name() or "").strip()
    if fn:
        return fn
    un = (getattr(user, "username", None) or "").strip()
    return un or str(user.pk)


def _format_digest_date(d: date) -> str:
    wd = _WEEKDAY_CN[d.weekday()]
    return f"{d.year}年{d.month:02d}月{d.day:02d}日 {wd}"


def _build_user_markdown(*, digest_date: date, user, rows: list[SubscriptionReminder], page_url: str) -> str:
    """企微 markdown 正文；换行用 \\n 拼接；末尾为可点击的 markdown 链接。"""
    display = _user_display_name(user)
    date_line = _format_digest_date(digest_date)
    lines: list[str] = [
        date_line,
        "",
        f"@{display}",
        "",
    ]
    for r in rows:
        pname = (getattr(r.platform_option, "name", None) or "").strip() or "—"
        lines.append(f"用户：{r.wechat_label} 在 {pname} 的订阅即将到期")
    lines.extend(
        [
            "",
            f"[点击跳转]({page_url})",
        ]
    )
    return "\n".join(lines)


def _truncate_utf8(text: str, max_bytes: int = 4000) -> str:
    raw = text.encode("utf-8")
    if len(raw) <= max_bytes:
        return text
    lo, hi = 0, len(text)
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if text[:mid].encode("utf-8") <= max_bytes:
            lo = mid
        else:
            hi = mid - 1
    return text[:lo].rstrip() + "\n\n>内容过长已截断，请打开链接在系统中查看全部记录。"


class Command(BaseCommand):
    help = "按职员汇总「当日到期」订阅提醒并推送到企微群 Webhook（无记录不推；同职员同日仅推一次）。"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="只打印将推送人数与摘要，不调用 Webhook、不写库。",
        )
        parser.add_argument(
            "--test-message",
            action="store_true",
            help="仅发送一条固定测试文案（用于验证 Webhook），不扫描订阅表。",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="忽略「同职员同日已推送」记录，重新发送（仍会真实请求 Webhook）。",
        )
        parser.add_argument(
            "--no-record",
            action="store_true",
            help="真实推送但不写入「每日汇总」去重表，便于试发后仍可在定时任务（如 15:00）再推一次。",
        )
        parser.add_argument(
            "--date",
            dest="digest_date",
            default="",
            help="按指定日期汇总（YYYY-MM-DD），默认使用当前本地日期；用于补发或测试。",
        )

    def handle(self, *args, **options):
        dry_run = bool(options["dry_run"])
        test_only = bool(options["test_message"])
        force = bool(options["force"])
        no_record = bool(options["no_record"])
        raw_date = (options.get("digest_date") or "").strip()

        if not getattr(settings, "WECOM_REMINDER_ENABLED", False):
            self.stdout.write(self.style.WARNING("未开启：请设置环境变量 WECOM_REMINDER_ENABLED=1"))
            return

        url = (getattr(settings, "WECOM_GROUP_WEBHOOK_URL", None) or "").strip()
        if not url:
            self.stdout.write(self.style.ERROR("缺少 WECOM_GROUP_WEBHOOK_URL"))
            return

        if test_only:
            body = "**薪火系统**\n>Webhook 测试消息：配置正确。"
            if dry_run:
                self.stdout.write("[dry-run] 将发送测试 markdown，不实际请求。")
                return
            try:
                send_markdown(url, body)
            except WecomWebhookError as e:
                self.stdout.write(self.style.ERROR(str(e)))
                raise SystemExit(1) from e
            self.stdout.write(self.style.SUCCESS("测试消息已发送。"))
            return

        page_url = _staff_subscription_reminders_url()
        if not page_url:
            self.stdout.write(
                self.style.ERROR(
                    "缺少职员端订阅页 URL：请设置 STAFF_FRONTEND_SUBSCRIPTION_REMINDERS_URL，"
                    "或设置 STAFF_FRONTEND_BASE_URL（将拼接 /subscription-reminders）。"
                )
            )
            return

        if raw_date:
            digest_date = parse_date(raw_date)
            if digest_date is None:
                self.stdout.write(self.style.ERROR(f"--date 无法解析: {raw_date!r}，请使用 YYYY-MM-DD"))
                raise SystemExit(2)
        else:
            digest_date = timezone.localdate()

        qs = (
            SubscriptionReminder.objects.select_related("user", "platform_option")
            .filter(next_reminder_at=digest_date)
            .order_by("user_id", "id")
        )
        by_user: dict[int, list[SubscriptionReminder]] = defaultdict(list)
        for r in qs:
            by_user[r.user_id].append(r)

        if not by_user:
            self.stdout.write(f"{digest_date} 无当日到期的订阅提醒，跳过。")
            return

        User = get_user_model()
        user_map = {u.pk: u for u in User.objects.filter(pk__in=by_user.keys())}
        ordered_uids = sorted(by_user.keys(), key=lambda uid: _user_display_name(user_map.get(uid)).lower())

        planned: list[tuple[int, list[SubscriptionReminder]]] = []
        skipped_dup = 0
        for uid in ordered_uids:
            rows = by_user[uid]
            user = user_map.get(uid)
            if user is None:
                continue
            if not force and SubscriptionReminderWecomDailyDigest.objects.filter(
                user_id=uid, digest_date=digest_date
            ).exists():
                skipped_dup += 1
                continue
            planned.append((uid, rows))

        if not planned:
            self.stdout.write(
                f"{digest_date} 共 {len(by_user)} 位职员有记录，均在库中标记为已推送（可用 --force 重发）。"
                f" 因去重跳过 {skipped_dup} 人。"
            )
            return

        self.stdout.write(
            f"{digest_date} 本地日汇总：{len(planned)} 人将推送，{skipped_dup} 人因已推送跳过。"
            f" TIME_ZONE={getattr(settings, 'TIME_ZONE', '')}"
        )

        for uid, rows in planned:
            user = user_map[uid]
            md = _build_user_markdown(digest_date=digest_date, user=user, rows=rows, page_url=page_url)
            md = _truncate_utf8(md, max_bytes=4000)
            preview = md[:800] + ("…" if len(md) > 800 else "")
            self.stdout.write(f"\n--- 职员 {_user_display_name(user)} ({user.username}) {len(rows)} 条 ---\n{preview}")

            if dry_run:
                continue

            try:
                send_markdown(url, md)
            except WecomWebhookError as e:
                self.stdout.write(self.style.ERROR(f"推送失败 uid={uid}: {e}"))
                raise SystemExit(1) from e

            if not no_record:
                SubscriptionReminderWecomDailyDigest.objects.get_or_create(
                    user_id=uid,
                    digest_date=digest_date,
                )

        if dry_run:
            self.stdout.write(self.style.WARNING("\n[dry-run] 未调用 Webhook，未写入每日汇总表。"))
            return

        suffix = "（未写入去重表，定时任务到点仍会再推）" if no_record else ""
        self.stdout.write(self.style.SUCCESS(f"\n已完成推送 {len(planned)} 条企微消息。{suffix}"))
