"""将 fixtures 中的「微信备注 + 中文日期」清单导入为某位职员的订阅提醒。

默认读取：apps/catalog/fixtures/li_dongmei_subscription_paste.txt
默认负责人：用户名或姓名包含「李冬梅」的职员账号（is_staff=True）。

用法（在 backend 目录）::

    python manage.py import_li_dongmei_subscriptions --dry-run
    python manage.py import_li_dongmei_subscriptions

未提供订阅平台时，统一使用「客户清单导入」选项（若不存在会自动创建）。
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q

from backend.apps.catalog.models import SubscriptionPlatformOption, SubscriptionReminder

DATE_RE = re.compile(r"(\d{4})年(\d{1,2})月(\d{1,2})日")


def _parse_records(text: str) -> list[tuple[str, date]]:
    """解析「微信备注 + 日期」；支持每行 `备注\\tYYYY年M月D日`，也兼容多行块格式。"""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    records: list[tuple[str, date]] = []

    def _append(label: str, m: re.Match[str]) -> None:
        label = label.strip().strip("\t")
        if not label or label in ("微信号", "下次续费日期"):
            return
        if "微信号" in label and "下次续费" in label:
            return
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if len(label) > 200:
            label = label[:200]
        records.append((label, date(y, mo, d)))

    for line in text.splitlines():
        if not line.strip():
            continue
        m = DATE_RE.search(line)
        if m and "\t" in line:
            _append(line[: m.start()], m)

    if records:
        return records

    last_end = 0
    for m in DATE_RE.finditer(text):
        label_raw = text[last_end : m.start()]
        last_end = m.end()
        label = " ".join(
            part.strip() for part in re.split(r"[\t\n]+", label_raw) if part.strip()
        ).strip()
        _append(label, m)
    return records


def _resolve_staff(*, username: str, hint: str):
    User = get_user_model()
    qs = User.objects.filter(is_staff=True, is_active=True)
    if username:
        u = qs.filter(username=username).first()
        if u:
            return u
    if hint:
        u = (
            qs.filter(
                Q(username__icontains=hint)
                | Q(first_name__icontains=hint)
                | Q(last_name__icontains=hint)
            )
            .order_by("id")
            .first()
        )
        if u:
            return u
    return None


class Command(BaseCommand):
    help = "从 fixtures 文本解析订阅提醒并归属到指定职员（默认李冬梅）。"

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            dest="path",
            default="",
            help="清单文件路径（UTF-8）；默认使用 apps/catalog/fixtures/li_dongmei_subscription_paste.txt",
        )
        parser.add_argument(
            "--username",
            default="",
            help="负责人登录名（精确匹配）；与 --hint 二选一或同时提供",
        )
        parser.add_argument(
            "--hint",
            default="李冬梅",
            help="在 username / first_name / last_name 中模糊匹配（默认：李冬梅）",
        )
        parser.add_argument(
            "--platform",
            default="客户清单导入",
            help="订阅平台选项名称（不存在则创建，默认：客户清单导入）",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="只打印解析条数与前几条预览，不写库。",
        )

    def handle(self, *args, **options):
        dry = bool(options["dry_run"])
        raw_path = (options.get("path") or "").strip()
        base = Path(__file__).resolve().parents[2]  # apps/catalog
        default_file = base / "fixtures" / "li_dongmei_subscription_paste.txt"
        path = Path(raw_path) if raw_path else default_file
        if not path.is_file():
            self.stderr.write(self.style.ERROR(f"找不到文件: {path}"))
            raise SystemExit(1)

        text = path.read_text(encoding="utf-8")
        rows = _parse_records(text)
        if not rows:
            self.stderr.write(self.style.ERROR("未解析到任何「备注 + 日期」记录，请检查文件格式。"))
            raise SystemExit(2)

        user = _resolve_staff(username=(options.get("username") or "").strip(), hint=(options.get("hint") or "").strip())
        if not user:
            self.stderr.write(
                self.style.ERROR(
                    "未找到职员账号：请用 --username 指定登录名，或确认存在姓名/用户名包含「李冬梅」的职员。"
                )
            )
            raise SystemExit(3)

        pname = (options.get("platform") or "客户清单导入").strip() or "客户清单导入"
        opt, _ = SubscriptionPlatformOption.objects.get_or_create(name=pname, defaults={"sort_order": 900})

        self.stdout.write(f"负责人: {user.username} (id={user.pk})，平台选项: {opt.name}，解析 {len(rows)} 条。")
        for i, (lab, d) in enumerate(rows[:8], 1):
            self.stdout.write(f"  {i}. {lab!r} -> {d.isoformat()}")
        if len(rows) > 8:
            self.stdout.write(f"  … 共 {len(rows)} 条")

        if dry:
            self.stdout.write(self.style.WARNING("[dry-run] 未写入数据库。"))
            return

        objs = [
            SubscriptionReminder(
                user=user,
                platform_option=opt,
                wechat_label=lab,
                next_reminder_at=d,
                remark="",
            )
            for lab, d in rows
        ]
        with transaction.atomic():
            SubscriptionReminder.objects.bulk_create(objs, batch_size=300)
        self.stdout.write(self.style.SUCCESS(f"已写入 {len(objs)} 条订阅提醒。"))
