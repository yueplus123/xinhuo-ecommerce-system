from decimal import Decimal

from django.db import migrations, models


DEFAULT_USD_PROXY_TIERS = (
    ("1-5美金", Decimal("60")),
    ("5.01-10美金", Decimal("40")),
    ("10.01-15美金", Decimal("35")),
    ("15.01-20美金", Decimal("30")),
    ("20.01-30美金", Decimal("25")),
    ("30.01-60美金", Decimal("23")),
    ("60.01-80美金", Decimal("20")),
    ("80.01-100美金", Decimal("18")),
    ("100.01-150美金", Decimal("15")),
    ("150+美金", Decimal("13")),
)


def seed_usd_proxy_price_tiers(apps, schema_editor):
    UsdProxyPriceTier = apps.get_model("catalog", "UsdProxyPriceTier")
    if UsdProxyPriceTier.objects.exists():
        return
    for idx, (usd_range, rate_percent) in enumerate(DEFAULT_USD_PROXY_TIERS, start=1):
        UsdProxyPriceTier.objects.create(
            usd_range=usd_range,
            rate_percent=rate_percent,
            sort_order=idx * 10,
        )


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0051_remove_sku_platform_tags"),
    ]

    operations = [
        migrations.AlterField(
            model_name="sku",
            name="price_type",
            field=models.CharField(
                blank=True,
                choices=[
                    ("cny_single", "单一人民币"),
                    ("usd_single", "美金（单一）"),
                    ("usd_tier", "美金（多档）"),
                    ("package", "套餐"),
                    ("jpy_recharge", "日元充值"),
                    ("usd_proxy", "按美金代付收费"),
                ],
                default="",
                max_length=20,
                verbose_name="价格类型",
            ),
        ),
        migrations.CreateModel(
            name="UsdProxyPriceTier",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("usd_range", models.CharField(max_length=100, verbose_name="美金区间")),
                ("rate_percent", models.DecimalField(decimal_places=2, max_digits=5, verbose_name="费率（%）")),
                (
                    "sort_order",
                    models.PositiveIntegerField(
                        default=0,
                        help_text="数字越小越靠前。",
                        verbose_name="排序",
                    ),
                ),
            ],
            options={
                "verbose_name": "美金代付价格档",
                "verbose_name_plural": "美金代付价格池",
                "ordering": ["sort_order", "id"],
            },
        ),
        migrations.RunPython(seed_usd_proxy_price_tiers, migrations.RunPython.noop),
    ]
