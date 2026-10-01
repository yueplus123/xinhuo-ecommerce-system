from django.core.management.base import BaseCommand

from backend.apps.api.wechat_bot_push import seed_wechat_bot_demo


class Command(BaseCommand):
    help = "为「微信BOT数据」每个业务表写入演示假数据（默认每表 10 条）"

    def add_arguments(self, parser):
        parser.add_argument("--per-table", type=int, default=10)
        parser.add_argument(
            "--keep",
            action="store_true",
            help="保留已有 demo-wbot-* 记录（默认先删再写）",
        )

    def handle(self, *args, **options):
        result = seed_wechat_bot_demo(
            per_table=int(options["per_table"] or 10),
            replace=not options["keep"],
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"已写入 {result['created']} 条（{result['tables']} 表 × {result['per_table']}）"
            )
        )
