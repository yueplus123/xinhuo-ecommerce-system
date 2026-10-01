"""从 dumpdata 导出的 JSON 合并用户与组（按 username / group name，避免 loaddata 主键冲突）。"""

import json
from pathlib import Path

from django.contrib.auth.models import Group, Permission, User
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.dateparse import parse_datetime


def _dt(val):
    if not val:
        return None
    if isinstance(val, str):
        dt = parse_datetime(val)
        if dt is not None and timezone.is_naive(dt):
            dt = timezone.make_aware(dt, timezone.get_current_timezone())
        return dt
    return val


class Command(BaseCommand):
    help = (
        "读取 dumpdata 生成的 auth.User / auth.Group JSON，按 username 合并到当前库；"
        "组按名称 get_or_create。跨库 Permission 主键通常不一致，仅同步本库已存在的 permission id。"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "path",
            nargs="?",
            default="",
            help="JSON 路径；留空则使用 apps/catalog/fixtures/xinhuo_users_and_groups.json",
        )

    def handle(self, *args, **options):
        raw = (options["path"] or "").strip()
        if raw:
            path = Path(raw).expanduser().resolve()
        else:
            catalog = Path(__file__).resolve().parent.parent.parent
            path = catalog / "fixtures" / "xinhuo_users_and_groups.json"
        if not path.is_file():
            self.stderr.write(self.style.ERROR(f"找不到文件：{path}"))
            return

        data = json.loads(path.read_text(encoding="utf-8"))
        group_old_pk: dict[int, Group] = {}
        skipped_perm_refs = 0
        applied_perm_refs = 0

        for row in data:
            if row.get("model") != "auth.group":
                continue
            pk = row["pk"]
            f = row["fields"]
            g, _ = Group.objects.get_or_create(name=f["name"])
            group_old_pk[pk] = g

        n_user = 0
        for row in data:
            if row.get("model") != "auth.user":
                continue
            f = row["fields"]
            username = (f.get("username") or "").strip()
            if not username:
                self.stderr.write(self.style.WARNING("跳过一条无用户名的记录。"))
                continue

            defaults = {
                "password": f["password"],
                "last_login": _dt(f.get("last_login")),
                "is_superuser": bool(f.get("is_superuser")),
                "first_name": f.get("first_name") or "",
                "last_name": f.get("last_name") or "",
                "email": f.get("email") or "",
                "is_staff": bool(f.get("is_staff")),
                "is_active": bool(f.get("is_active", True)),
                "date_joined": _dt(f.get("date_joined")) or timezone.now(),
            }
            user, _ = User.objects.update_or_create(username=username, defaults=defaults)
            n_user += 1

            gids = f.get("groups") or []
            if gids:
                user.groups.set([group_old_pk[gid] for gid in gids if gid in group_old_pk])

            perm_objs = []
            for pid in f.get("user_permissions") or []:
                perm = Permission.objects.filter(pk=pid).first()
                if perm:
                    perm_objs.append(perm)
                    applied_perm_refs += 1
                else:
                    skipped_perm_refs += 1
            user.user_permissions.set(perm_objs)

        self.stdout.write(self.style.SUCCESS(f"已处理用户 {n_user} 个（按 username 新建或覆盖）。"))
        if skipped_perm_refs:
            self.stdout.write(
                self.style.WARNING(
                    f"有 {skipped_perm_refs} 条 user_permissions 引用在本地库无对应 Permission（已忽略）；"
                    f"成功挂上 {applied_perm_refs} 条。"
                )
            )
