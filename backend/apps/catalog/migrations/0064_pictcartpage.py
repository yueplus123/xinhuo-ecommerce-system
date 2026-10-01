from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0063_wechatbotrecord_quantity_amount_usd"),
    ]

    operations = [
        migrations.CreateModel(
            name="PictCartPage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=200, verbose_name="页面名称")),
                ("share_url", models.URLField(verbose_name="页面链接")),
                (
                    "sort_order",
                    models.PositiveIntegerField(
                        default=0,
                        help_text="数字越小越靠前；职员端「pict加购物车」按此顺序展示。",
                        verbose_name="排序",
                    ),
                ),
                ("is_active", models.BooleanField(default=True, verbose_name="启用")),
            ],
            options={
                "verbose_name": "pict加购物车页面",
                "verbose_name_plural": "pict加购物车页面",
                "ordering": ["sort_order", "id"],
            },
        ),
    ]
