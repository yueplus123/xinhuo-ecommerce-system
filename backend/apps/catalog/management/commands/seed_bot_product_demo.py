from django.core.management.base import BaseCommand

from backend.apps.api.bot_product_query import seed_bot_product_demo


class Command(BaseCommand):
    help = "写入 BOT 查商品测试数据（平台名 + 商品名；前缀「BOT演示-」）"

    def add_arguments(self, parser):
        parser.add_argument(
            "--keep",
            action="store_true",
            help="保留已有 BOT演示-* 平台（默认先删再写）",
        )

    def handle(self, *args, **options):
        result = seed_bot_product_demo(replace=not options["keep"])
        self.stdout.write(
            self.style.SUCCESS(
                f"已写入平台 {result['platforms']} 个、商品 {result['skus']} 个"
                f"（名称前缀 {result['prefix']}）"
            )
        )
