"""本地开发：创建或重置可登录前端 / backoffice 的管理员账号（is_staff + is_superuser）。"""

import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = (
        "若不存在则创建超级用户；已存在时仅在使用 --reset 时重置密码。"
        "密码优先取 --password，其次环境变量 BACKEND_DEV_PASSWORD，否则默认 changeme（仅开发）。"
    )

    def add_arguments(self, parser):
        parser.add_argument("--username", default="admin", help="用户名，默认 admin")
        parser.add_argument("--password", default=None, help="密码；不设则用环境变量或默认 changeme")
        parser.add_argument(
            "--reset",
            action="store_true",
            help="用户已存在时重置密码并确保 is_active / is_staff / is_superuser 为 True",
        )

    def handle(self, *args, **options):
        User = get_user_model()
        username = (options["username"] or "").strip()
        password = (
            options["password"]
            or os.environ.get("BACKEND_DEV_PASSWORD")
            or "changeme"
        )

        if not username:
            self.stderr.write(self.style.ERROR("用户名不能为空。"))
            return

        user = User.objects.filter(username=username).first()

        if user is None:
            User.objects.create_superuser(username, email="", password=password)
            self.stdout.write(self.style.SUCCESS(f"已创建用户「{username}」，可登录前端与 django-admin。"))
            if password == "changeme":
                self.stdout.write(self.style.WARNING("当前为默认密码 changeme，生产环境请立即修改。"))
            return

        if not options["reset"]:
            self.stdout.write(
                self.style.WARNING(
                    f"用户「{username}」已存在。若要改密码请执行：\n"
                    f"  python manage.py create_dev_user --username {username} --reset [--password 新密码]\n"
                    "或使用：python manage.py changepassword " + username
                )
            )
            return

        user.set_password(password)
        user.is_active = True
        user.is_staff = True
        user.is_superuser = True
        user.save()
        self.stdout.write(self.style.SUCCESS(f"已重置用户「{username}」的密码并开通职员/超管权限。"))
        if password == "changeme":
            self.stdout.write(self.style.WARNING("当前为默认密码 changeme，生产环境请立即修改。"))
